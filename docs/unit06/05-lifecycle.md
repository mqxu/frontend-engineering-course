# 6.5 生命周期与副作用清理

## 一个“每次回来都多一条日志”的页面

数据看板页需要在窗口尺寸变化时重算图表宽度。第一版是这么写的：

```vue [src/views/DashboardView.vue（有问题）]
<script setup>
import { onMounted } from 'vue'

onMounted(() => {
  window.addEventListener('resize', handleResize)
  console.log('挂上了 resize 监听')
})

function handleResize() {
  console.log('窗口尺寸变了，重算图表')
}
</script>
```

测试时一切正常。上线两天后，问题来了：

- 先进看板页，再进活动列表页，调整窗口大小 —— **控制台里“重算图表”打印了两次**。
- 反复进出看板页十次，再调整窗口 —— 打印了十次，页面明显卡顿。

原因在于：**组件卸载时，`resize` 监听器还挂在 `window` 上，它不知道组件已经不在了。**
每进入一次页面就多挂一个监听器，越积越多；而且这些监听器里访问的已经是销毁了的组件数据。

修法是加一个清理动作：

```vue [src/views/DashboardView.vue（修好了）]
<script setup>
import { onMounted, onUnmounted } from 'vue'

onMounted(() => {
  window.addEventListener('resize', handleResize)
})

// ✓ 组件卸载时，把挂上去的监听器摘掉
onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
})

function handleResize() {
  console.log('窗口尺寸变了，重算图表')
}
</script>
```

这一节就讲两件事：**什么时候做什么**（生命周期钩子），以及**做过的事什么时候收尾**（副作用清理）。

## 生命周期钩子：什么时候被调用

一个组件从创建到销毁，会经过几个固定阶段。Vue 在每个阶段提供了钩子函数，让你能把代码放到正确的时机。

| 钩子 | 调用时机 | 典型用途 |
| --- | --- | --- |
| `onBeforeMount` | 组件挂载**前**，DOM 还没生成 | 少见，挂载前最后一次准备数据 |
| `onMounted` | 组件挂载**后**，DOM 已可用 | 发初始请求、操作 DOM、初始化定时器与监听 |
| `onBeforeUpdate` | 数据变化、DOM 更新**前** | 更新前记录旧值（比如滚动位置） |
| `onUpdated` | DOM 更新**后** | 更新后读取 DOM（很少用） |
| `onBeforeUnmount` | 组件卸载**前**，实例还可访问 | 清理前的收尾（少见） |
| `onUnmounted` | 组件卸载**后** | **清理副作用**：定时器、监听器、请求、第三方实例 |

另外三个在特定场景才用：

| 钩子 | 用途 |
| --- | --- |
| `onActivated` / `onDeactivated` | 配合 `<KeepAlive>` 缓存组件，进入/离开缓存时触发 |
| `onErrorCaptured` | 捕获子孙组件的错误，做统一兜底 |

::: tip 记不住全部没关系
日常开发**百分之九十的场景只用两个：`onMounted` 和 `onUnmounted`**。
一个是“开始干活”，一个是“收尾擦干净”。先把这两个用熟。
:::

## 每个阶段能做什么、不能做什么

### 挂载前拿不到 DOM

这是最常踩的一条。看这段：

```vue [src/components/SearchBar.vue（错误示范）]
<script setup>
import { ref } from 'vue'

const inputRef = ref(null)

// ✗ 在 setup 顶层就访问，此时 DOM 还不存在
inputRef.value.focus() // 报错：Cannot read properties of null
</script>

<template>
  <input ref="inputRef" />
</template>
```

`setup` 执行时，Vue 还在“准备渲染”，DOM 元素还不存在，所以 `inputRef.value` 是 `null`。
必须在 `onMounted` 里访问：

```vue [src/components/SearchBar.vue]
<script setup>
import { ref, onMounted } from 'vue'

const inputRef = ref(null)

onMounted(() => {
  // ✓ 挂载完成，DOM 已经在了
  inputRef.value.focus()
})
</script>

<template>
  <input ref="inputRef" placeholder="输入关键词" />
</template>
```

同理，`onBeforeMount` 里也拿不到 DOM。**需要读 DOM 或者操作 DOM 的代码，统一放 `onMounted`。**

### 更新钩子里不要再改状态

`onUpdated` 里如果修改了响应式数据，会再次触发更新，可能形成无限循环：

```vue [src/components/ActivityList.vue（错误示范）]
import { onUpdated, ref } from 'vue'

const count = ref(0)

onUpdated(() => {
  // ✗ 每次更新都改数据，改完又触发更新，无限循环
  count.value++
})
```

Vue 检测不到“这个修改和刚才的更新是不是同一件事”，它会一直更新下去直到浏览器卡死
（通常表现为控制台报 “Maximum recursive updates exceeded”）。

**规则：`onUpdated` 里只读，不写。** 真需要“更新后根据结果改状态”，应该从数据源头解决，
而不是在钩子里打补丁。

::: warning `onUpdated` 比你想的更少用
它的调用时机是“**这个组件的 DOM 更新之后**”，而不是“某个字段变了”。父组件传入的
`props` 变化导致重渲染，也会触发它。

绝大多数“想在更新后做点什么”的需求，其实用 `watch` 更合适：
`watch` 能明确指定监听哪个数据，触发时机也更好控制。**能不写 `onUpdated` 就不写。**
:::

### 卸载时做清理

`onUnmounted` 是副作用清理的标准位置。它调用时组件实例还在（能访问到闭包里的变量），
DOM 已经被移除了。

## `onMounted` 里发请求合适吗

这是被问得最多的一个问题。先把讨论摆开。

**支持在 `onMounted` 发的理由：**

- 此时组件已经渲染，四态页面（加载中 / 空 / 错误 / 有数据）能正常工作。
- 拿得到路由参数、模板引用、父组件传进来的 `props`，请求参数拼装是完整的。
- 写法直白，谁看都懂。

**反对的理由：**

- 请求要等组件挂载完才开始，首屏会先显示“加载中”再变成内容，多一次切换。
- 如果用服务端渲染（SSR），`onMounted` 里的代码**不会在服务端执行**，
  首屏 HTML 里就没有数据。

**结论：在我们这个校园活动管理端（纯客户端渲染的单页应用）里，用 `onMounted` 发初始请求是完全合适的，
也是推荐做法。** 唯一要注意的是必须把“加载中”状态先摆好 —— 否则用户会看到从空白的突然跳变。

```vue [src/views/ActivityListView.vue]
<script setup>
import { ref, onMounted } from 'vue'
import { fetchActivityList } from '@/api/activity'

const loading = ref(false)
const list = ref([])
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await fetchActivityList()
    list.value = res.data
  } catch (e) {
    error.value = e.message || '加载失败'
  } finally {
    loading.value = false
  }
}

// ✓ 挂载后拉取第一页数据
onMounted(load)
</script>

<template>
  <p v-if="loading">加载中……</p>
  <p v-else-if="error" class="error">{{ error }}</p>
  <p v-else-if="list.length === 0">暂无活动</p>
  <ul v-else>
    <li v-for="item in list" :key="item.id">{{ item.title }}</li>
  </ul>
</template>
```

::: tip `onMounted` 的回调可以是 `async`
`onMounted(async () => { await load() })` 是合法的。但要知道 **Vue 不会等这个 Promise**，
它只是“启动了”这个异步过程。这不影响使用，只要你的加载状态处理对了。

另外，如果要做“组件卸载时取消请求”，需要像 6.4 讲的那样用 `AbortController`，
而不是指望 Vue 帮你取消。

四态页面的完整规范见[单元 5](/unit05/05-four-states)。
:::

## 模板引用：拿到真实的 DOM 元素

有些事必须直接操作 DOM：让输入框自动聚焦、测量元素宽高、把内容滚动到某个位置、
或者把 DOM 交给第三方库（图表、地图、富文本编辑器）。

Vue 提供了模板引用来拿到 DOM 元素。

### 旧写法：`ref(null)` 靠命名对上

```vue [src/components/ActivitySearch.vue（旧写法，仍可用）]
<script setup>
import { ref, onMounted } from 'vue'

// 变量名必须和模板里的 ref="inputRef" 字符串一致
const inputRef = ref(null)

onMounted(() => {
  inputRef.value?.focus()
})
</script>

<template>
  <input ref="inputRef" placeholder="搜索活动" />
</template>
```

这种写法的毛病是**靠字符串名字对上**：变量改个名，模板里忘了改，运行时就是 `null`，
而且编辑器不会报错。

### 新写法：`useTemplateRef`（Vue 3.5 起）

```vue [src/components/ActivitySearch.vue]
<script setup>
import { useTemplateRef, onMounted } from 'vue'

// 变量名与模板里的 ref 字符串不再需要一致
const searchInput = useTemplateRef('inputEl')

onMounted(() => {
  searchInput.value?.focus()
})
</script>

<template>
  <!-- 模板里这个字符串，就是 useTemplateRef 的参数 -->
  <input ref="inputEl" placeholder="搜索活动" />
</template>
```

对比一下：

| 对比项 | `ref(null)` | `useTemplateRef('名字')` |
| --- | --- | --- |
| 变量名与模板 | **必须一致** | 无要求，靠参数关联 |
| 可读性 | 名字被绑死，想改语义要和模板一起改 | 变量名可以随意取，比如 `searchInput` |
| 类型提示 | 需要手写泛型 | 3.5 的写法更清晰 |
| 可用版本 | 所有 Vue 3 | **Vue 3.5 起** |

::: warning 项目里两种写法会同时存在
`useTemplateRef` 是 Vue 3.5 才有的。看别人的项目时会看到大量 `ref(null)` 的老写法，
那是历史原因，**不是错误**。你写新代码时优先用 `useTemplateRef`；维护老项目时跟着它的风格走。

在 `v-for` 里拿模板引用会拿到一个数组，这一点两种写法一致：
`const itemRefs = useTemplateRef('itemEls')`，模板里给循环项写 `ref="itemEls"`，
`itemRefs.value` 就是一个元素数组。
:::

### 什么时候必须直接操作 DOM

能用数据驱动解决的，就不要碰 DOM。下面这几类**只能**直接操作 DOM：

| 场景 | 为什么必须操作 DOM | 用到的 API |
| --- | --- | --- |
| 输入框自动聚焦 | 焦点不是数据，没法用 `v-bind` 表达 | `el.focus()` |
| 获取元素尺寸与位置 | 由浏览器布局决定，JS 里算不出来 | `el.getBoundingClientRect()` |
| 滚动到指定位置 | 滚动位置不在 Vue 的响应式体系里 | `el.scrollTop`、`el.scrollIntoView()` |
| 往输入框光标处插入文本 | 光标位置是 DOM 的内部状态 | `el.selectionStart` |
| 交给第三方库初始化 | 图表库、地图库要求传真实元素 | `new Chart(el, options)` |

::: danger 一个反向提醒
不要用 `document.querySelector('.activity-title').textContent = 'xxx'` 这种方式改页面。
你绕过了 Vue 的响应式系统，下一次数据更新时 Vue 会把你的修改覆盖掉，而且你会以为“Vue 有 bug”。

**改内容走数据，改浏览器状态（焦点、滚动、尺寸测量）才碰 DOM。**
:::

## 副作用清理的正确时机

“副作用”是相对于“纯渲染”来说的：渲染之外还影响了外部世界的东西，都算副作用。
常见的三类是**定时器、事件监听、在途请求**。

### 定时器

活动详情页需要每 30 秒刷新一次报名人数：

```vue [src/views/ActivityDetailView.vue]
<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { fetchSignupCount } from '@/api/activity'

const count = ref(0)
let timer = null

onMounted(() => {
  fetchSignupCount().then((n) => (count.value = n))
  // ✓ 启动轮询
  timer = setInterval(async () => {
    count.value = await fetchSignupCount()
  }, 30000)
})

onUnmounted(() => {
  // ✓ 组件走了，轮询必须停
  clearInterval(timer)
  timer = null
})
</script>
```

::: warning 定时器不清的后果
- **内存泄漏**：定时器的回调闭包一直持有组件数据，垃圾回收收不掉。
- **无效请求**：用户早就离开页面了，还在每 30 秒发一次请求。
- **报错**：回调里访问已经卸载的组件数据，可能抛错。

这三条里，**无效请求**最容易被忽略 —— 因为它在开发时不报错，只在服务器日志里留下痕迹。
:::

### 事件监听

除了本节开头讲的 `resize`，还有两类高频监听：

```vue [src/components/KeyboardShortcut.vue]
<script setup>
import { onMounted, onUnmounted } from 'vue'

function handleKeydown(e) {
  if (e.key === 'Escape') {
    console.log('关闭弹窗')
  }
}

onMounted(() => {
  // 键盘监听挂在 window 上，不在组件的 DOM 里
  window.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
})
</script>
```

**判断标准：监听器挂在了组件外部的对象上吗？** 挂到 `window`、`document`、`body`
或者第三方实例上的，都要在 `onUnmounted` 里摘掉。挂在组件自身模板元素上的
（`@click` 那种）由 Vue 管，不用手动清理。

滚动监听还要额外加“节流”，否则滚动时处理函数每帧都跑：

```vue [src/components/BackToTop.vue]
<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const visible = ref(false)
let ticking = false

function onScroll() {
  if (ticking) return
  ticking = true
  // 用 requestAnimationFrame 把处理频率限制到每帧一次
  requestAnimationFrame(() => {
    visible.value = window.scrollY > 300
    ticking = false
  })
}

onMounted(() => window.addEventListener('scroll', onScroll))
onUnmounted(() => window.removeEventListener('scroll', onScroll))
</script>

<template>
  <button v-if="visible" @click="window.scrollTo({ top: 0, behavior: 'smooth' })">
    回到顶部
  </button>
</template>
```

::: warning 清理时函数必须是同一个引用
```js
// ✗ 摘不掉：addEventListener 和 removeEventListener 拿到的是两个不同的函数
window.addEventListener('resize', () => handleResize())
window.removeEventListener('resize', () => handleResize())
```

```js
// ✓ 用同一个函数引用
function handleResize() { /* ... */ }
window.addEventListener('resize', handleResize)
window.removeEventListener('resize', handleResize)
```

**匿名函数摘不掉**，这是清理不生效最常见的原因。写监听时就把处理函数定义成具名函数。
:::

### 请求取消

请求本身也是一种副作用。用 `AbortController` 在组件卸载时取消在途请求：

```vue [src/composables/useActivityDetail.js]
import { ref, onMounted, onUnmounted } from 'vue'
import { fetchActivityDetail } from '@/api/activity'

export function useActivityDetail(id) {
  const detail = ref(null)
  const loading = ref(false)
  let controller = null

  async function load() {
    controller?.abort() // 取消上一次
    controller = new AbortController()
    loading.value = true
    try {
      detail.value = await fetchActivityDetail(id, { signal: controller.signal })
    } catch (e) {
      if (e.name !== 'CanceledError' && e.name !== 'AbortError') throw e
    } finally {
      loading.value = false
    }
  }

  onMounted(load)
  // ✓ 卸载时把在途请求一起取消
  onUnmounted(() => controller?.abort())

  return { detail, loading, reload: load }
}
```

::: tip 一个整理副作用的习惯
组件里每写一个“对外部世界的改动”，就在 `onUnmounted` 里立刻写对应的清理，**不要等到出问题再补**。

可以按这个清单自查：

| 我做了这件事 | 对应的清理 |
| --- | --- |
| `setInterval` / `setTimeout` | `clearInterval` / `clearTimeout` |
| `addEventListener` 到组件外部对象 | `removeEventListener`，**同一个函数引用** |
| 发起请求（`load`） | `AbortController.abort()` |
| 初始化第三方库实例（图表、编辑器） | 调用它的 `destroy()` / `dispose()` |
| 订阅外部数据源 | 调用它的取消订阅函数 |
:::

## 小结

- 日常只用两个钩子：**`onMounted` 开始干活，`onUnmounted` 收尾清理**。
- **挂载前拿不到 DOM**（`setup` 顶层和 `onBeforeMount` 都不行），操作 DOM 放 `onMounted`。
- **`onUpdated` 里只读不写**，写数据会导致无限更新；多数“更新后做点什么”的需求用 `watch` 更好。
- 在纯客户端渲染的应用里，**`onMounted` 发初始请求是合适做法**，前提是把加载中 / 空 / 错误态摆好。
- 模板引用：新代码用 `useTemplateRef('名字')`，老代码的 `ref(null)` 仍可用；
  `v-for` 里会拿到元素数组。
- 只有**焦点、尺寸测量、滚动位置、光标位置、第三方库初始化**这些必须碰 DOM，改内容一律走数据。
- 副作用三件套是**定时器、事件监听、在途请求**；监听器清理必须用**同一个函数引用**。

## 常见坑

::: details 坑 1：在 `setup` 顶层读 DOM
**现象**：`Cannot read properties of null (reading 'focus')`。

**原因**：`setup` 执行时 DOM 还没渲染，模板引用还是 `null`。

**处理**：把读 DOM 的代码放进 `onMounted`。如果是 `v-if` 控制的元素，
还要等条件为真之后再读 —— 可以在 `watch` 里监听那个条件，或者用 `nextTick()`。
:::

::: details 坑 2：匿名函数摘监听器摘不掉
**现象**：写了 `removeEventListener`，但监听还在，日志仍然重复打印。

**原因**：`addEventListener` 和 `removeEventListener` 收到的是两个不同的函数对象。

**处理**：处理函数写成具名函数（或存进变量），两边用同一个引用。
:::

::: details 坑 3：在 `onUnmounted` 里访问已经卸载的 DOM
**现象**：清理代码里读 `el.getBoundingClientRect()` 报错，或者拿到的是 0。

**原因**：`onUnmounted` 触发时 DOM 已经被移除，元素上读不到布局信息。

**处理**：需要在卸载前读取状态，用 `onBeforeUnmount`。`onUnmounted` 只做“释放资源”的动作。
:::

::: details 坑 4：`<KeepAlive>` 缓存组件时 `onUnmounted` 不触发
**现象**：组件被缓存了，切换页面时发现定时器还在跑。

**原因**：被 `<KeepAlive>` 缓存的组件不会卸载，只会在“激活 / 停用”之间切换，
所以 `onUnmounted` 不执行。

**处理**：用 `onDeactivated` 做暂停、`onActivated` 做恢复：

```js
onActivated(() => startTimer())
onDeactivated(() => clearTimer())
onUnmounted(() => clearTimer()) // 真正的卸载路径也别落下
```
:::

::: details 坑 5：`onMounted` 里发请求，但数据永远不刷新
**现象**：第一次进入页面有数据，从详情页返回列表页时数据是旧的。

**原因**：组件被 `<KeepAlive>` 缓存了，`onMounted` 只执行一次，返回时不会重新拉取。

**处理**：如果需要每次进入都刷新，用 `onActivated` 触发加载。
**先判断需求**：是要“每次进入都刷新”，还是“保留用户上次的筛选和滚动位置”？
两者做法不同，不要一律加 `onActivated`。
:::

## 课后练习

::: details 练习 1：给这三个组件补上清理
分别写出它们的 `onUnmounted`：

1. 一个每 5 秒轮询“报名人数”的组件。
2. 一个监听 `window` 的 `scroll` 来做“回到顶部”按钮的组件。
3. 一个用 `AbortController` 取消在途请求的组件。

**参考思路**：第 1 题注意把 `timer` 声明在 `setup` 顶层而不是 `onMounted` 里，
否则清理时拿不到；第 2 题处理函数要具名；第 3 题注意“主动取消”不算错误，别把它当成失败上报。

:::

::: details 练习 2：判断哪些写法有问题
逐条判断，说明理由：

```js
// A
onMounted(() => { document.title = '活动详情' })
onUnmounted(() => { document.title = '' })

// B
onMounted(() => { setTimeout(() => { list.value = [] }, 1000) })

// C
onUpdated(() => { count.value = list.value.length })

// D
onMounted(() => { el.value.focus() }) // el 是模板引用，元素在 v-if 里
```

**参考思路**：A 想想“离开页面后标题应该是什么”；B 想想“用户 1 秒内切走了会怎样”；
C 回到“更新钩子里只读不写”；D 想想“`v-if` 为假时 `el.value` 是什么”。

:::

::: details 练习 3：写一个“自动聚焦的搜索框”组件
要求：

1. 组件挂载后输入框自动获得焦点。
2. 用 `useTemplateRef` 拿元素（不用老写法）。
3. 按 Esc 清空内容并保持焦点。
4. 组件卸载时不留任何监听。

**参考思路**：模板引用 + `onMounted` 聚焦；Esc 用 `@keydown.esc`；
第 4 点先想清楚“我到底挂了什么监听”——如果监听是通过 `@keydown` 写在模板元素上的，
那不需要手动清理。

:::

---

上一节：[6.4 表单校验](/unit06/04-validation) ·
下一节：[案例 05 · Markdown 编辑器](/unit06/06-case-markdown)
