# 5.2 侦听器

## 一个具体的场景

活动列表页顶部有一个搜索框。需求是：**用户停止输入 500 毫秒之后，再去请求接口。**

为什么要停 500 毫秒？因为每敲一个字就发一次请求，输入“校园歌手大赛”这六个字
就是六次请求。用户打字快的时候，前五次的结果都被最后一次覆盖，
白耗带宽和服务端资源。

计算属性做不了这件事 —— 计算属性是“算出一个值”，
而这里要做的是“**在某个数据变化之后，去做一件事**”。这件事就是发请求。

Vue 里做这件事的工具是**侦听器**：

```vue
<script setup>
import { ref, watch } from 'vue'

const keyword = ref('')
let timer = null

watch(keyword, (newValue) => {
  clearTimeout(timer)
  timer = setTimeout(() => {
    fetchActivityList(newValue)
  }, 500)
})
</script>

<template>
  <input v-model="keyword" placeholder="搜索活动" />
</template>
```

`watch(keyword, 回调)` 的意思是：**`keyword` 变化时，执行这个回调。**

## 原理与写法

### 侦听一个来源

`watch` 的第一个参数是**来源**，第二个是**回调**。
来源可以是三种东西：

```js
import { ref, reactive, watch, computed } from 'vue'

const keyword = ref('')
const query = reactive({ status: 'all', page: 1 })
const list = ref([1, 2, 3])
const total = computed(() => list.value.length)

// 1. 一个 ref
watch(keyword, (val) => console.log('关键词变成', val))

// 2. 一个 getter 函数：返回你要观察的值
watch(() => query.status, (val) => console.log('状态变成', val))

// 3. 一个 computed 计算属性
watch(total, (val) => console.log('总数变成', val))
```

**注意第二种写法**：`reactive` 对象本身不能直接当来源（直接传会隐式变成深层侦听），
要观察它的某个属性，得写成一个函数 `() => query.status`。

```js
// ✗ 不推荐：隐式深度侦听，性能差且容易触发过多次
watch(query, () => { /* ... */ })

// ✓ 推荐：只观察你关心的那个属性
watch(() => query.status, () => { /* ... */ })
```

回调收到的第一个参数是新值，第二个是旧值：

```js
watch(keyword, (newValue, oldValue) => {
  console.log(`从 “${oldValue}” 变成了 “${newValue}”`)
})
```

### 侦听多个来源

第一个参数传数组，就同时观察多个来源。回调收到的也是数组：

```js
// 关键词或状态任一变化，都要重新搜索
watch([keyword, () => query.status], ([newKeyword, newStatus], [oldKeyword, oldStatus]) => {
  console.log('当前条件：', newKeyword, newStatus)
  query.page = 1        // 条件变了，回到第一页
})
```

**用数组形式的一个典型好处**：把“条件变化后要重置页码”这个动作统一处理。
如果写成两个 `watch`，这段逻辑要写两遍。

::: tip 什么时候该合并成一个 watch
如果多个来源变化后要执行**同一件事**，用数组形式合并；
如果各自要做**不同的事**，分开写。

判断标准：**回调体是不是同一段代码。** 是同一段，就合并。
:::

### 深层变化：deep

默认情况下，`watch` 只观察**引用是否变化**。一个对象的属性改了，引用没变，
侦听器不会触发：

```js
const activity = ref({ title: 'A', capacity: 100 })

watch(activity, () => {
  console.log('触发了')
})

activity.value.title = 'B'   // 不会打印 —— 对象的引用没变
activity.value = { title: 'B' } // 会打印 —— 整个对象被替换了
```

要监听内部的属性变化，加 `deep: true`：

```js
watch(activity, () => {
  console.log('内部属性变了')
}, { deep: true })

activity.value.title = 'B'   // 现在会打印了
```

`deep` 的代价：Vue 需要**递归遍历**整个对象来追踪每一层，
对象越大越深，开销越大。所以：

- **能精确观察某个属性，就不要用 `deep`**；
- 确实需要整体监听（比如一个复杂表单的草稿保存），再用。

```js
// ✓ 更好：只观察你真正关心的属性
watch(() => activity.value.capacity, (val) => {
  if (val > 500) console.warn('名额设置过大')
})
```

### 立即执行：immediate

默认情况下，`watch` **不会在初始化时执行**，只有数据变化才执行。
如果希望“一进页面就先跑一次”，加 `immediate: true`：

```js
// 进页面就加载第一页数据，之后页码变化也重新加载
watch(() => query.page, loadPage, { immediate: true })
```

不加 `immediate` 的话，首次进入页面需要另外写一次 `loadPage()` 调用，
容易忘。**“需要在初始化时也执行一次”的场景，一律加 `immediate`。**

### 回调参数的坑：对象类型时新旧值相同

侦听一个基本类型时，新旧值是不同的：

```js
watch(keyword, (newVal, oldVal) => {
  console.log(newVal)   // '校'
  console.log(oldVal)   // ''
})
```

但侦听对象时，**新旧值会是同一个引用**：

```js
const form = reactive({ name: '林一鸣' })

watch(() => form.name, (newVal, oldVal) => {
  console.log(newVal, oldVal)   // 都是 '林一鸣'，无法比较
})
```

再极端一点，用 `deep` 侦听整个对象：

```js
const activity = reactive({ title: 'A', capacity: 100 })

watch(activity, (newVal, oldVal) => {
  console.log(newVal === oldVal)   // true
}, { deep: true })
```

**原因**：`watch` 记录的是“上一次触发时的值”。对于对象，这个“值”是**引用**。
两次触发之间，引用没有变（变的是内部属性），所以新旧值指向同一个对象。
等你拿到回调时，这个对象已经被改完了，`oldVal` 里看到的也是新内容。

**怎么绕过这个坑**：

```js
// 方案一：用 getter 返回一个不可变的快照
watch(
  () => ({ ...activity }),
  (newVal, oldVal) => {
    console.log(newVal.title, oldVal.title)   // 能区分了
  }
)
```

```js
// 方案二：业务上只需要新值时，就不要依赖旧值
watch(activity, (newVal) => { saveDraft(newVal) }, { deep: true })
```

**实际写代码时的建议**：如果旧值对你的逻辑是必需的，就别直接侦听对象，
用 getter 侦听那个具体的属性。**旧值只能用来做展示或对比，不要用它做业务判断**
—— 它很容易是“已经被改过的对象”。

### watchEffect：自动收集依赖

`watchEffect` 的写法和 `watch` 完全不同：**你只写回调，不写来源。**

```js
import { watchEffect } from 'vue'

watchEffect(() => {
  // 这个函数里读到了谁，就自动侦听谁
  console.log('当前关键词：', keyword.value)
  console.log('当前状态：', query.status)
})
```

它有两个特点：

1. **立即执行一次**（相当于天生带 `immediate`）；
2. **自动收集依赖** —— 回调里读过的响应式数据都会成为侦听来源。

依赖变了就重新执行，而且是**用最新的依赖集合重新判定**。
这带来一个很有用的特性：**条件依赖会自动调整。**

```js
watchEffect(() => {
  if (isDetailOpen.value) {
    // 只有详情打开时，才去读 activityId；关闭时不读，也就不会侦听它
    loadDetail(activityId.value)
  }
})
```

用 `watch` 写同样的逻辑，要写两个侦听器（一个监听 `isDetailOpen`，
一个监听 `activityId`），还要在回调里判断状态。

::: warning watchEffect 的两个注意点
1. **不要写异步的第一行读取。** `watchEffect` 只能在**同步执行阶段**收集依赖。
   如果在 `await` 之后才第一次读某个数据，那个数据不会被侦听：

```js
// ✗ 有隐患：await 之后读到的 count 不会被侦听
watchEffect(async () => {
  await someThing()
  console.log(count.value)
})

// ✓ 对：先同步读一次，或者用 watch
watchEffect(() => {
  const c = count.value     // 同步阶段读到
  someAsync(c)
})
```

2. **依赖不直观。** 读代码时不容易一眼看出它侦听什么，需要通读整个回调。
   可以用 `onTrack` 调试（[附录](/appendix/cheatsheet)有说明），
   但日常更简单的做法是：**依赖关系不明显的场景，用 `watch` 显式写出来。**
:::

### watch 与 watchEffect 怎么选

| 对比项 | `watch` | `watchEffect` |
| --- | --- | --- |
| 来源 | 显式指定 | 自动收集 |
| 首次执行 | 默认不执行，要加 `immediate` | 一定执行 |
| 新旧值 | 能拿到 | 拿不到 |
| 依赖可见性 | 一眼可见 | 要读回调 |
| 适合 | 逻辑依赖明确、需要旧值、需要精确控制 | 一组依赖变化后做同一件事、依赖较集中 |

选择口诀：

- **能说清“我在观察谁” → 用 `watch`。** 这是绝大多数业务场景。
- **只是“这些数据谁变了都做同一件事” → 用 `watchEffect`。**

::: details 一个用 watchEffect 更合适的例子
表单草稿自动保存：表单里有十几个字段，任何一个变化都要保存。

```js
// ✗ 用 watch：要把十几个字段全列出来，加字段就要改这里
watch([a, b, c, d, /* ... */], saveDraft)

// ✓ 用 watchEffect：读一遍表单，改了哪个都能感知
watchEffect(() => {
  saveDraft(JSON.stringify(form.value))
})
```

不过要注意：`JSON.stringify` 会读到对象的每个属性，
所以 `form` 是深层的 `ref` 时也能收集到依赖。**这正是它适合的场景。**
:::

### 清理副作用

这是侦听器里最容易忽略、也最重要的一环。

场景：关键词变了就发请求。用户输入“校园”，请求发出去了；
还没返回，用户改成了“校园歌手”，第二个请求发出去了。
**如果第一个请求比第二个晚返回，界面就会显示“校园”的结果** ——
这就是典型的竞态问题。

`watch` 的回调可以接收第三个参数 `onCleanup`，用来注册**清理函数**。
清理函数会在**下一次回调执行之前**被调用：

```js
watch(keyword, async (newKeyword, oldKeyword, onCleanup) => {
  const controller = new AbortController()

  // 注册清理：下次关键词变化时，把这个还没完成的请求取消掉
  onCleanup(() => controller.abort())

  const res = await fetch(`/api/activity?keyword=${newKeyword}`, {
    signal: controller.signal
  })
  const data = await res.json()
  list.value = data.list
})
```

也可以用来清理定时器：

```js
watch(keyword, (val, oldVal, onCleanup) => {
  const timer = setTimeout(() => search(val), 500)
  onCleanup(() => clearTimeout(timer))
})
```

**`onCleanup` 的执行时机**：在**下一次回调开始之前**，以及**侦听器被停止时**。
所以它正好用来取消“上一次还没做完的事”。

::: tip 判断“要不要写清理”的一句话
问自己：**这个回调里有没有“发出去还没收回来”的东西？**

有，就要清理。常见的有三类：

- 定时器（`setTimeout` / `setInterval`）；
- 网络请求（`fetch` / `axios`）；
- 事件监听（`addEventListener`）。

**没有清理，就会出现“上一次的结果覆盖这一次”的问题。**
:::

### 实战：搜索防抖

把上面的东西合起来，做一个完整的搜索输入：

```vue [src/components/ActivitySearchBar.vue]
<script setup>
import { ref, watch } from 'vue'

const emit = defineEmits(['search'])
const keyword = ref('')

watch(keyword, (newKeyword, _oldKeyword, onCleanup) => {
  // 关键词变了，先把这个待执行的搜索取消掉
  const timer = setTimeout(() => {
    emit('search', newKeyword.trim())
  }, 500)

  // 下次变化或组件卸载时，清掉定时器
  onCleanup(() => clearTimeout(timer))
})
</script>

<template>
  <input v-model="keyword" placeholder="搜索活动标题" />
</template>
```

这段代码的行为是：

- 每敲一个字，都设一个 500 毫秒后执行的定时器；
- 500 毫秒内又敲了一个字，上一次的定时器被 `onCleanup` 清掉；
- 停止输入 500 毫秒后，最后一次定时器执行，发出搜索。

如果搜索要发请求，再加上 `AbortController` 处理竞态，
用 `onCleanup` 同时清定时器和取消请求：

```js
watch(keyword, (newKeyword, _oldKeyword, onCleanup) => {
  const controller = new AbortController()
  const timer = setTimeout(async () => {
    const res = await fetch(`/api/activity?keyword=${encodeURIComponent(newKeyword)}`, {
      signal: controller.signal
    })
    list.value = (await res.json()).list
  }, 500)

  onCleanup(() => {
    clearTimeout(timer)      // 还没发出去，就别发了
    controller.abort()       // 已经发出去了，就取消
  })
})
```

::: details 为什么用 onCleanup 而不是手动 clearTimeout
两种写法都能实现防抖：

```js
// 写法 A：在回调开头手动清
let timer = null
watch(keyword, (val) => {
  clearTimeout(timer)
  timer = setTimeout(() => search(val), 500)
})
```

```js
// 写法 B：用 onCleanup
watch(keyword, (val, _old, onCleanup) => {
  const timer = setTimeout(() => search(val), 500)
  onCleanup(() => clearTimeout(timer))
})
```

写法 B 更好，原因有两个：

1. **`timer` 不再需要写在外层作用域**，代码更内聚，多个侦听器不会互相干扰；
2. **组件卸载时也会执行清理** —— 写法 A 的 `timer` 在组件卸载后还可能触发一次，
   往一个已经不存在的组件里写数据，会带来警告甚至报错。

**结论：需要清理的东西，一律交给 `onCleanup`。**
:::

## 小结

- `watch` 用来“在数据变化后做一件事”，来源可以是 ref、getter 或 computed。
- 观察 `reactive` 的某个属性，写成 `() => state.xxx`，不要直接侦听整个对象。
- 多个来源用数组形式；回调参数也是数组。
- `deep: true` 才监听对象内部属性变化，代价是递归遍历，能精确侦听就别用。
- `immediate: true` 让侦听器在初始化时也执行一次。
- **对象类型的新旧值会是同一个引用**，需要旧值时用 getter 返回一个快照。
- `watchEffect` 自动收集依赖、立即执行一次，但必须在同步阶段读数据。
- 回调里“发出去还没收回来”的东西，用 `onCleanup` 清理 —— 尤其是请求防抖。
- 选择口诀：**说得出观察谁 → `watch`；一组数据谁变都做同一件事 → `watchEffect`。**

## 常见坑

::: details 坑 1：侦听 reactive 的属性却写成了整个对象
```js
const query = reactive({ keyword: '', status: 'all' })

// ✗ 会深度侦听整个对象，任何属性变化都触发
watch(query, () => { search() })

// ✓ 只侦听关键词
watch(() => query.keyword, () => { search() })
```

**现象**：改了 `status` 也触发了“按关键词搜索”，或者侦听器触发次数远超预期。

**原因**：直接侦听 `reactive` 对象会隐式变成深度侦听。

**怎么处理**：写成 getter。**这个坑在排查“为什么发了多次请求”时经常遇到。**
:::

::: details 坑 2：用旧值做业务判断
```js
watch(() => form.name, (newVal, oldVal) => {
  // ✗ oldVal 可能已经不可靠了
  if (oldVal === '') { /* 认为这是第一次输入 */ }
})
```

**现象**：判断结果不符合预期。

**原因**：侦听对象属性时，新旧值可能指向同一个对象，`oldVal` 里看到的是修改后的内容。

**怎么处理**：需要“第一次”这种语义，自己用一个标志位记录。

```js
let isFirst = true
watch(() => form.name, () => {
  if (isFirst) { isFirst = false; return }
  // 后续的处理
})
```

**这类“需要知道是第一次还是第几次”的需求，靠 watch 的参数做不可靠，要用自己的状态。**
:::

::: details 坑 3：watchEffect 里 await 之后才读数据
```js
// ✗ 有隐患：activityId 在 await 之后才被读到，不会被收集为依赖
watchEffect(async () => {
  await someAsyncThing()
  console.log(activityId.value)   // 这次读取发生在异步阶段，漏掉了
})
```

**现象**：改了 `activityId`，侦听器不重新执行。

**原因**：`watchEffect` 只在同步执行阶段收集依赖，`await` 之后已经不在同步阶段。

**怎么处理**：把要侦听的数据在 `await` 之前读出来，或者改用 `watch` 显式声明来源。
**推荐后者**，因为异步逻辑用 `watch` 表达得更清楚。
:::

::: details 坑 4：忘了停止侦听
`watch` 返回一个停止函数：

```js
const stop = watch(keyword, () => { /* ... */ })
// 需要时停止
stop()
```

在组件的 `<script setup>` 里创建的侦听器，**会随组件卸载自动停止**，
一般不用手动处理。但两种情况要手动停：

1. **在异步回调里创建的侦听器**，它不属于组件的初始化同步流程，可能泄漏；
2. **自己封装的组合式函数里创建的侦听器**，需要暴露停止方法给调用方。

**排查现象**：页面关闭了，控制台还在打印侦听器的日志 —— 说明没停。
:::

## 课后练习

::: details 练习 1：给搜索加一个“取消”
下面这段代码有竞态问题：快速输入时，可能显示旧关键词的结果。
请用 `onCleanup` 修复，并说明为什么原来的写法会出错。

```js
watch(keyword, async (val) => {
  const res = await fetch(`/api/activity?keyword=${val}`)
  list.value = (await res.json()).list
})
```

**参考思路**：加 `AbortController`，在 `onCleanup` 里 `abort()`；
同时记得处理 `fetch` 被取消时抛出的 `AbortError`（用 `try / catch` 吞掉）。

**为什么原来的写法会错**：输入“校”时发出请求 A；马上输入“校园”发出请求 B。
如果 A 比 B 晚返回，`list.value` 会被 A 的结果覆盖，
界面上显示的是“校”的结果，而已输入框里是“校园”。**这就是竞态。**
:::

::: details 练习 2：三个需求，选 watch 还是 watchEffect
1. 用户切换活动状态筛选后，把页码重置为 1；
2. 表单里任意一个字段变化，都自动把草稿存进 `localStorage`；
3. 用户选了“需要场地”之后，才去加载场地列表，并且场地筛选条件变化时重新加载。

**参考思路**：

1. 用 `watch`，来源明确（`() => query.status`），动作明确；
2. 用 `watchEffect`，回调里 `JSON.stringify(form)` 读一遍表单即可，
   不用列字段；
3. 两种都可以。用 `watch` 的话要侦听两个来源并在回调里判断 `needVenue`；
   用 `watchEffect` 更自然，因为“只在需要时才读场地相关的数据”这个条件依赖
   正好是 `watchEffect` 的强项。

**第 3 题的重点是理解“条件依赖”**：`watch` 要显式列出所有可能变化的东西，
`watchEffect` 是“读到才侦听”。
:::

::: details 练习 3：实现一个防抖输入
做一个搜索框组件，要求：

1. 用户停止输入 500 毫秒后才触发 `search` 事件；
2. 组件卸载时不能有遗留的定时器；
3. 额外加一个“立即搜索”按钮，点击时不管防抖，立刻触发。

**参考思路**：主体用 `watch` + `onCleanup` 清定时器。
“立即搜索”按钮需要能拿到待执行的定时器，所以要把定时器存在一个外层变量里，
点击时 `clearTimeout` 再直接触发。

**做完之后想想**：如果把这个组件封装成组合式函数 `useDebouncedRef`，
对外暴露什么接口比较合适？这是[单元 8 组合式函数](/unit08/04-composables)的内容。
:::

---

上一节：[5.1 计算属性与缓存](/unit05/01-computed) ·
下一节：[5.3 条件渲染](/unit05/03-conditional)
