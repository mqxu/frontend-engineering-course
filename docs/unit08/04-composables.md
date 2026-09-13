# 8.4 组合式函数

## 三段复制了三遍的代码

把第七周写的页面翻一遍，会发现三处几乎一样的代码。

活动编辑页：

```js [src/views/ActivityEditView.vue（片段）]
const draft = ref(JSON.parse(localStorage.getItem('activity-draft') || 'null'))

watch(
  draft,
  (val) => {
    localStorage.setItem('activity-draft', JSON.stringify(val))
  },
  { deep: true }
)
```

报名表单页：

```js [src/views/SignupFormView.vue（片段）]
const form = ref(JSON.parse(localStorage.getItem('signup-form') || 'null'))

watch(
  form,
  (val) => {
    localStorage.setItem('signup-form', JSON.stringify(val))
  },
  { deep: true }
)
```

还有报名审核页里那段鼠标跟随的提示框，以及每个页面里长得几乎一样的异步请求代码：

```js [每页都有的一份“加载态 + 错误态 + 数据”]
const loading = ref(false)
const error = ref(null)
const data = ref(null)

async function load() {
  loading.value = true
  error.value = null
  try {
    data.value = await fetchActivities()
  } catch (e) {
    error.value = e
  } finally {
    loading.value = false
  }
}
```

三段代码，逻辑完全一样，只是变量名和接口地址不同。**每加一个页面就复制一遍，
改的时候要一个个改。** 这就是“重复逻辑”，是时候把它抽出来了。

抽出来的东西叫**组合式函数**（Composable）：一个以 `use` 开头的函数，
内部把“状态 + 逻辑”打包好，返回给你用的值。

## 组合式函数是什么

它本质上就是一个普通的 JavaScript 函数，只是遵守两条约定：

1. 名字以 `use` 开头。
2. 函数体里用了 Vue 的响应式 API（`ref`、`computed`、`watch` 等）或生命周期钩子。

先看从上面那段请求代码抽出来的第一个版本：

```js [src/composables/useLoading.js（最简版）]
import { ref } from 'vue'

export function useLoading() {
  const loading = ref(false)
  const error = ref(null)

  async function run(task) {
    loading.value = true
    error.value = null
    try {
      return await task()
    } catch (e) {
      error.value = e
      throw e
    } finally {
      loading.value = false
    }
  }

  return { loading, error, run }
}
```

用起来是这样：

```vue [在任何组件里]
<script setup>
import { ref } from 'vue'
import { useLoading } from '@/composables/useLoading'

const activities = ref([])
const { loading, error, run } = useLoading()

async function load() {
  activities.value = await run(() => fetchActivities())
}
</script>

<template>
  <p v-if="loading">加载中…</p>
  <p v-else-if="error" class="error">加载失败：{{ error.message }}</p>
  <ul v-else>
    <li v-for="a in activities" :key="a.id">{{ a.title }}</li>
  </ul>
</template>
```

注意 `loading` 和 `error` 是 `ref` —— 组件里直接用，模板里自动解包。
**组件拿到的是一个独立的状态副本**：两个组件各调一次 `useLoading()`，它们各自的 `loading`
互不影响。这一点很重要：**组合式函数每次调用都会创建一份新状态，不是单例。**

## 与 React Hooks 的差别

如果你了解 React，会立刻想到 Hooks。两者确实像：都是把逻辑打包成函数，都用 `use` 开头。
但有一个关键差别：

**React Hooks 有“调用顺序不能变”的硬限制，Vue 的组合式函数没有。**

React 的 `useState`、`useEffect` 靠“调用顺序”来对应组件的内部存储 —— 第 1 次调的是哪个、
第 2 次调的是哪个。所以不能在 `if` 里调用 Hook：

```js [React：✗ 会报错或状态错乱]
function Component({ show }) {
  if (show) {
    const [name, setName] = useState('')  // ✗ 条件调用 Hook
  }
  return null
}
```

Vue 不需要这套机制。**组合式函数调用的每一个 `ref` 都是一个独立的响应式对象**，
它和你调用几次、在哪个分支里调用没有任何关系：

```js [Vue：✓ 条件调用没有问题]
export function useActivityForm(show) {
  const name = ref('')

  if (show) {
    const urgent = ref(false)  // ✓ 完全合法
    return { name, urgent }
  }
  return { name, urgent: null }
}
```

为什么？因为 Vue 的响应式系统靠 `Proxy` 追踪“谁读了、谁写了”，
状态是**跟着对象走**的，不是跟着调用顺序走的。你可以把 `ref` 传给另一个函数、
存进数组、在循环里创建 —— 都不会出问题。

::: tip 这条差别带来的实际好处
Vue 里可以用“条件逻辑 + 循环”自由组合逻辑，写起来更像普通函数。
React 里为了绕开顺序限制，要用很多额外技巧。

这不是说 Vue 更强，只是机制不同带来的写法差异。理解它，你在迁移代码时才不会把
React 的限制硬套到 Vue 上（比如为了“顺序稳定”写一堆没有必要的代码）。
:::

## 命名约定与文件组织

**命名**：一律 `use` 开头，动词或名词都行，要能一眼看出“用了它会得到什么”。

| 名字 | 含义 |
| --- | --- |
| `useLocalStorage` | 与本地存储同步的响应式值 |
| `useMouse` | 鼠标位置 |
| `useRequest` | 异步请求的状态 |
| `usePermission` | 权限判断 |

放在 `src/composables/` 目录下，**一个函数一个文件，文件名和函数名一致**：

```text
src/composables/
├── keys.js               注入键（不是组合式函数，是常量，放这里也可以）
├── useLocalStorage.js
├── useMouse.js
├── useRequest.js
├── usePermission.js
└── useToast.js
```

::: details 为什么一个函数一个文件
组合式函数往往几十行甚至有依赖，混在一起的文件会越滚越大。分开的好处：

1. 找的时候直接搜文件名。
2. 每个文件可以单独测试（将来写单元测试时）。
3. import 路径稳定，重构时改动面小。

小函数（比如只有五行）可以例外，两个相关的放一起也行。
**但要有一套自己的规则并坚持，不要“有的分开有的不分开”。**
:::

## 参数与返回值的封装原则

**返回对象，不返回数组。**

```js [✗ 返回数组：取什么靠位置，加字段容易错]
export function useCounter() {
  const count = ref(0)
  function inc() { count.value++ }
  return [count, inc]
}
// 用的时候：const [count, inc] = useCounter()，再加一个 reset 就要改所有调用处
```

```js [✓ 返回对象：按名字取，可以只取需要的，扩展不影响使用方]
export function useCounter() {
  const count = ref(0)
  const double = computed(() => count.value * 2)
  function inc() { count.value++ }
  function reset() { count.value = 0 }
  return { count, double, inc, reset }
}
// 用的时候：const { count, inc } = useCounter()
```

**为什么对象更好？**

- 使用方按名字取，不用数位置。
- 只取需要的字段，剩下的不用管。
- 以后加字段，老代码一行不用改。

**参数的封装**：参数能少就少，能带默认值就带；多个相关参数用一个配置对象收。

```js [参数用配置对象]
export function useLocalStorage(key, defaultValue = '', options = {}) {
  const { deep = true } = options
  // …
}
```

**不要在组合式函数里写业务。** `useRequest` 不该知道“活动列表接口地址是什么”，
它只负责“发一个请求并管理状态”；地址由调用方传进来。这是能不能复用的分界线。

## 实战一：useLocalStorage

目标：读写本地存储，且和 `ref` 一样响应；自动处理序列化和解析失败。

```js [src/composables/useLocalStorage.js]
import { ref, watch } from 'vue'

/**
 * 与 localStorage 同步的响应式值
 * @param {string} key       存储的键名
 * @param {*} defaultValue   没有存过时的默认值
 * @param {object} options   配置：deep 是否深度侦听、storage 用哪种存储
 */
export function useLocalStorage(key, defaultValue = null, options = {}) {
  const { deep = true, storage = localStorage } = options
  // 存储读出来的原始字符串，判断“这次变化是不是自己写进去的”
  let raw = ''

  function read() {
    raw = storage.getItem(key)
    if (raw === null) return defaultValue

    try {
      return JSON.parse(raw)
    } catch {
      // 存的不是 JSON（比如手动存过一个字符串），原样返回
      return raw
    }
  }

  const data = ref(read())

  watch(
    data,
    (val) => {
      try {
        const next = JSON.stringify(val)
        // 值没变就不写，避免别处改动触发的重复写入
        if (next === raw) return
        storage.setItem(key, next)
        raw = next
      } catch (e) {
        console.warn(`[useLocalStorage] 序列化 "${key}" 失败：`, e)
      }
    },
    { deep }
  )

  // 提供手动清除的方法
  function remove() {
    storage.removeItem(key)
    raw = ''
    data.value = defaultValue
  }

  return { data, remove }
}
```

用起来：

```js [src/views/ActivityEditView.vue]
<script setup>
import { useLocalStorage } from '@/composables/useLocalStorage'

// 草稿自动保存到本地，刷新页面还在
const { data: draft, remove: clearDraft } = useLocalStorage('activity-draft', {
  title: '',
  type: 'lecture',
  capacity: 100,
  sessions: []
})
</script>

<template>
  <input v-model="draft.title" placeholder="活动标题" />
  <button @click="clearDraft">清空草稿</button>
</template>
```

几个关键设计：

- **解析失败要兜住**。用户手动改过、上一个版本存了别的格式，`JSON.parse` 都可能抛错。
  用 `try / catch` 并原样返回，别让页面白屏。
- **写之前判断值有没有变**。否则多个标签页同时打开时，会来回触发。
- **`deep: true`** 让对象内部的字段变化也能保存。
- **返回值也是对象**，所以 `{ data, remove }`，使用方可以给 `data` 改名成 `draft`。

## 实战二：useMouse

目标：拿到鼠标位置，挂载时开始监听、卸载时移除监听。

```js [src/composables/useMouse.js]
import { ref, onMounted, onUnmounted } from 'vue'

/**
 * 跟踪鼠标位置
 * @param {object} options target 监听目标，默认 window
 * @returns {{ x, y, sourceType }}
 */
export function useMouse(options = {}) {
  const { target = window } = options

  const x = ref(0)
  const y = ref(0)

  function update(event) {
    x.value = event.pageX
    y.value = event.pageY
  }

  // 组合式函数里可以直接用生命周期钩子，
  // 它绑定的是“调用这个函数的那个组件”
  onMounted(() => {
    target.addEventListener('mousemove', update)
  })

  onUnmounted(() => {
    // 一定要移除，否则组件销毁后监听器还在，内存泄漏
    target.removeEventListener('mousemove', update)
  })

  return { x, y }
}
```

用在报名审核页的悬浮提示上：

```vue [src/components/SignupHint.vue]
<script setup>
import { useMouse } from '@/composables/useMouse'

const { x, y } = useMouse()
</script>

<template>
  <div class="hint" :style="{ left: x + 'px', top: y + 'px' }">
    悬停查看学生信息
  </div>
</template>
```

::: warning 清理是组合式函数的责任
组件卸载后监听器没被移除，是很常见的内存泄漏来源。好在**写在组合式函数里的
`onUnmounted` 会在使用它的组件卸载时执行**，所以“注册监听 + 清理监听”这对操作
最适合放进组合式函数 —— 使用方再也不用记得清理。

这条原则推广开：**凡是在组合式函数里启动了某个持续存在的东西（定时器、事件监听、
WebSocket），都要在同一个函数里负责关掉它。**
:::

## 实战三：useRequest

目标：把异步请求的加载态、错误态、数据、重试、取消一次包好。这是三个里最实用的。

```js [src/composables/useRequest.js]
import { ref, shallowRef, onUnmounted } from 'vue'

/**
 * 封装异步请求的状态
 * @param {Function} service  返回 Promise 的函数
 * @param {object} options    配置：immediate 是否立即执行、initialData 初始数据
 */
export function useRequest(service, options = {}) {
  const { immediate = false, initialData = null } = options

  const data = shallowRef(initialData)  // 大对象用 shallowRef，避免深层追踪的开销
  const loading = ref(false)
  const error = ref(null)

  // 每次请求一个 AbortController，方便取消
  let controller = null

  async function run(...args) {
    // 如果上一次还没结束，先取消掉，避免“后发先至”的竞态问题
    controller?.abort()
    controller = new AbortController()

    loading.value = true
    error.value = null

    try {
      const result = await service(...args, { signal: controller.signal })
      data.value = result
      return result
    } catch (e) {
      // 主动取消不算错误，不写进 error
      if (e.name === 'AbortError') return
      error.value = e
      throw e
    } finally {
      loading.value = false
    }
  }

  /** 重试：再调一次 run，可以传入一份自定义的指数退避 */
  async function retry(times = 1, ...args) {
    let lastError
    for (let i = 0; i <= times; i++) {
      try {
        return await run(...args)
      } catch (e) {
        lastError = e
        // 第 1 次重试等 300ms，第 2 次等 600ms，以此类推
        if (i < times) await new Promise((r) => setTimeout(r, 300 * 2 ** i))
      }
    }
    throw lastError
  }

  function cancel() {
    controller?.abort()
    loading.value = false
  }

  // 组件卸载时取消未完成的请求
  onUnmounted(cancel)

  if (immediate) run()

  return { data, loading, error, run, retry, cancel }
}
```

在活动列表页用起来：

```js [src/views/ActivityListView.vue]
<script setup>
import { useRequest } from '@/composables/useRequest'
import { fetchActivities } from '@/api/activity'

const { data, loading, error, run, retry, cancel } = useRequest(
  (params) => fetchActivities(params),
  { immediate: true, initialData: [] }
)

const query = ref({ page: 1, keyword: '' })

function search() {
  run({ ...query.value })
}
</script>

<template>
  <input v-model="query.keyword" @keyup.enter="search" />

  <p v-if="loading">加载中…</p>
  <p v-else-if="error">
    加载失败：{{ error.message }}
    <button @click="retry(2, query)">重试</button>
  </p>
  <ul v-else>
    <li v-for="a in data" :key="a.id">{{ a.title }}</li>
  </ul>
</template>
```

几个关键点：

- **`shallowRef` 而不是 `ref`**：接口返回的列表通常很大，深层响应式会给每个字段
  都加追踪，开销大且没必要。`shallowRef` 只在“整个值被替换”时触发更新，刚好够用。
- **`AbortController` 解决竞态**：用户快速点两次搜索，两个请求返回顺序不定，
  后返回的旧结果会覆盖新结果。每次 `run` 前取消上一个请求，就不会串。
- **取消不算错误**：`AbortError` 不写进 `error`，否则用户点了取消，界面会闪一下错误提示。
- **`onUnmounted` 取消请求**：组件已经销毁了还去改它的状态，是另一个常见的内存泄漏点。

::: details 为什么不用现成的 @vueuse/core
`@vueuse/core` 14.4.0 里有现成的 `useMouse`、`useLocalStorage`、`useFetch`，
项目里也应该优先用它们。

但**自己写一遍的意义在于理解里面发生了什么** —— 知道 `AbortController` 怎么取消请求、
`shallowRef` 和 `ref` 的差别、清理逻辑写在哪，你才能在看不懂库文档时自己判断，
也才能在库不满足需求时改出自己的一份。这个单元的练习要求你自己实现，
项目实战时用 `@vueuse/core` 完全可以。
:::

## 什么逻辑值得抽

不是所有重复代码都值得抽。三条判断标准：

| 标准 | 说明 | 反例 |
| --- | --- | --- |
| **被两处以上用** | 只用一次的逻辑先别抽 | 某页面独有的排序规则 |
| **逻辑自成一体** | 有明确的输入和输出，中间不掺业务 | “获取活动列表并更新选中态”混了两件事 |
| **与视图无关** | 不依赖某个具体的模板结构 | 依赖 `ref` 到某个 DOM 元素的逻辑 |

再补两条经验：

- **抽象要在第三次出现时做。** 第二次出现时可能只是巧合，第三次才说明它真的通用。
  过早抽出来的函数，往往参数越加越多，最后比复制还难维护。
- **抽出来的函数要能原样搬到另一个项目。** 如果它的参数里出现“活动”“报名”这类业务词，
  说明抽象层次不够，或者它本来就不该抽。

对照看看这三条：

| 逻辑 | 值得抽吗 | 理由 |
| --- | --- | --- |
| 本地存储同步 | 值得 | 三处在用、自成一体、与视图无关 |
| 鼠标位置 | 值得 | 多处用、与视图无关 |
| 请求状态管理 | 值得 | 每个页面都在重复 |
| “把活动状态翻译成中文” | 看情况 | 被多处用，但和业务有关，放 `utils/` 更合适 |
| “点击行高亮并同步详情面板” | 不值得 | 和这个页面强绑定，抽出去反而难用 |

::: tip 组合式函数 vs 工具函数
两者都放函数，区别在于**有没有响应式状态**：

- `formatDate(ts)` 只做纯计算，没有任何 `ref`，放 `src/utils/`，叫工具函数。
- `useRequest(fn)` 内部有 `loading`、`error` 这些响应式状态，放 `src/composables/`。

判断方法：函数里有没有 `ref` / `computed` / `watch` / 生命周期钩子，
有就是组合式函数。
:::

## 小结

- 组合式函数 = 以 `use` 开头的普通函数 + 内部使用响应式 API，用来打包“状态 + 逻辑”。
- 每次调用都会创建一份独立状态，天然可复用；Vue 里没有 React Hooks 的调用顺序限制。
- 一个函数一个文件放在 `src/composables/`，文件名与函数名一致。
- 返回**对象**不返回数组，方便按名取值和扩展；参数能少就少，配置项用对象收。
- 函数里启动的持续存在的东西（监听、定时器、请求），要在同一个函数里负责清理。
- 抽象时机：出现三次、自成一体、与业务和视图解耦；有响应式状态放 `composables/`，
  纯计算放 `utils/`。

## 常见坑

::: details 坑 1：在组合式函数外面调用生命周期钩子
现象：`onMounted is called when there is no active component instance`。

原因：`onMounted` 只能在组件初始化期间（`setup` 同步执行过程中）调用。
如果在一个 `setTimeout` 回调里调 `onMounted`，就没有“当前组件”了。

处理：把钩子调用放在组合式函数的**同步执行路径**上，别放进异步回调里。
:::

::: details 坑 2：返回了一个普通对象的字段，而不是 ref
现象：改了值，界面不更新。

原因：返回时写了 `return { count: count.value }`，把 `ref` 解包成了普通值。

处理：返回 `return { count }`，把 `ref` 本身交出去。让使用方在 `<script setup>`
里自己用 `.value`，模板里自动解包。
:::

::: details 坑 3：把请求函数当成普通函数，忘了它返回 Promise
现象：`data` 一直是 `null`。

原因：调用 `useRequest(fetchActivities)`，而 `fetchActivities` 需要参数，或者忘了
打开 `immediate`。

处理：确认 `service` 是个**返回 Promise 的函数**，并用 `{ immediate: true }`
或手动 `run()` 触发。
:::

::: details 坑 4：在组合式函数里直接写死了接口地址
现象：这个函数只能在活动列表页用。

原因：函数里 import 了具体的业务 API。

处理：把 `service` 作为参数传进来，函数只负责“管理状态”，不负责“知道请求什么”。
:::

::: details 坑 5：忘了处理并发，后发先至覆盖了结果
现象：快速切页时列表闪回上一个页面的数据。

原因：两个请求同时在飞，先发的后到。

处理：用 `AbortController` 在发新请求前取消旧的，或用一个自增的 `requestId`
比对“这次结果是不是最新那次”。
:::

## 课后练习

::: details 练习 1：做一个 useFetch 并在活动列表页用上
参考 `useRequest`，实现一个更简单的 `useFetch(url)`：传入 URL，自动在挂载时请求，
返回 `data`、`loading`、`error`、`refresh`。

**思路**：内部用 `fetch` 或项目里的 axios 实例。重点是 `refresh` 要能重新请求并更新状态。
写完后思考：它和 `useRequest` 的分工应该怎么划，哪个更适合项目里用。
:::

::: details 练习 2：做一个 useToggle
实现 `useToggle(initial = false)`，返回 `{ state, toggle, setTrue, setFalse }`。

**思路**：这是最简单的组合式函数，用它把“开关状态 + 三个操作”的接口设计练熟。
想想为什么返回对象而不是 `[state, toggle]`。
:::

::: details 练习 3：把 useMouse 扩展到 usePointer
让 `useMouse` 支持触摸事件，返回 `{ x, y, type }`，`type` 是 `'mouse'` 或 `'touch'`。

**思路**：监听 `pointermove`（指针事件同时覆盖鼠标和触摸），
用 `event.pointerType` 区分类型。注意 `pointermove` 在移动端滚动时的行为，
必要时用 `touch-action` 配合。这个练习为[案例 08 画板](/unit08/07-case-canvas)打基础。
:::

---

上一节：[8.3 内置组件](/unit08/03-builtin) ·
下一节：[8.5 自定义指令](/unit08/05-directives)
