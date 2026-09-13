# 5.1 计算属性与缓存

## 一个具体的场景

活动列表页要显示这样一段文字：

> 共有 37 场活动，其中报名中 12 场，本周截止 5 场。

数据在 `activities` 数组里，三个数字都要从它算出来。用普通函数写：

```vue
<script setup>
import { ref } from 'vue'

const activities = ref([ /* 活动数组 */ ])

function totalCount() {
  return activities.value.length
}

function signingCount() {
  return activities.value.filter((a) => a.status === 'signing').length
}

function closingThisWeek() {
  const now = Date.now()
  const weekLater = now + 7 * 24 * 60 * 60 * 1000
  return activities.value.filter((a) => {
    const t = new Date(a.deadline).getTime()
    return t >= now && t <= weekLater
  }).length
}
</script>

<template>
  <p>
    共有 {{ totalCount() }} 场活动，其中报名中 {{ signingCount() }} 场，
    本周截止 {{ closingThisWeek() }} 场。
  </p>
</template>
```

能跑。但如果模板里同一个数字用了三次：

```vue
<template>
  <p>报名中 {{ signingCount() }} 场</p>
  <div class="badge">{{ signingCount() }}</div>
  <p>占比 {{ (signingCount() / totalCount() * 100).toFixed(1) }}%</p>
</template>
```

**这个 `filter` 会跑三遍。** 每次组件重新渲染，还要再跑三遍。
数据上千条的时候，这就是真实的性能损耗。

换成计算属性：

```vue
<script setup>
import { ref, computed } from 'vue'

const activities = ref([ /* 活动数组 */ ])

const totalCount = computed(() => activities.value.length)

const signingCount = computed(
  () => activities.value.filter((a) => a.status === 'signing').length
)

const closingThisWeek = computed(() => {
  const now = Date.now()
  const weekLater = now + 7 * 24 * 60 * 60 * 1000
  return activities.value.filter((a) => {
    const t = new Date(a.deadline).getTime()
    return t >= now && t <= weekLater
  }).length
})
</script>

<template>
  <p>
    共有 {{ totalCount }} 场活动，其中报名中 {{ signingCount }} 场，
    本周截止 {{ closingThisWeek }} 场。
  </p>
</template>
```

两个变化：

1. 模板里不再写括号 —— **计算属性当属性用，不当函数用**；
2. 无论引用几次，**计算只跑一次**，结果被缓存下来。

## 原理与写法

### 缓存机制：用 `console.log` 实测一次

口说无凭，自己跑一遍。下面这个组件同时在模板里引用函数和计算属性各三次：

```vue [src/components/NameCompare.vue]
<script setup>
import { ref, computed } from 'vue'

const lastName = ref('林')
const firstName = ref('一鸣')

function fullNameByFn() {
  console.log('方法被调用')
  return lastName.value + firstName.value
}

const fullName = computed(() => {
  console.log('计算属性被求值')
  return lastName.value + firstName.value
})
</script>

<template>
  <p>函数：{{ fullNameByFn() }}</p>
  <p>函数：{{ fullNameByFn() }}</p>
  <p>函数：{{ fullNameByFn() }}</p>

  <hr />

  <p>计算属性：{{ fullName }}</p>
  <p>计算属性：{{ fullName }}</p>
  <p>计算属性：{{ fullName }}</p>
</template>
```

首次渲染，控制台输出：

```text
方法被调用
方法被调用
方法被调用
计算属性被求值
```

**函数打印三次，计算属性打印一次。**

改动 `firstName`，比如 `firstName.value = '小雨'`，控制台输出：

```text
方法被调用
方法被调用
方法被调用
计算属性被求值
```

又是函数三次、计算属性一次。再改一次 `firstName`，如果你改成了**同样的值**
（`firstName.value = '小雨'`），计算属性**不会再打印** —— 因为依赖没有真正变化。

把结论提炼出来：

| | 普通函数 | 计算属性 |
| --- | --- | --- |
| 每次渲染 | 每个引用点都执行一次 | 不重新执行，直接返回缓存 |
| 依赖变化时 | 下次渲染时执行 | 标记为“脏”，下次被读取时重新求值 |
| 依赖没变时 | 照样执行 | 直接用缓存 |
| 模板里的写法 | `fn()` | `prop`（不加括号） |

::: tip 缓存的准确说法
计算属性的缓存不是“算一次就永远不动”，而是**依赖没变就不重算**。

依赖变了之后，计算属性会把缓存标记为“过期”，但**不会立刻重算** ——
要等到下次有人真的读它才重算。这个策略保证：改了一堆数据但界面没用到，
就不会白算。
:::

### 什么时候该用计算属性，什么时候不该

**该用**：从已有状态**算出一个新值**，用来显示或给下一步用。

```js
// ✓ 典型的计算属性
const signedRatio = computed(() => signedCount.value / capacity.value)
const isFull = computed(() => signedCount.value >= capacity.value)
const filteredList = computed(() => list.value.filter(match))
const sortedList = computed(() => [...filteredList.value].sort(byDeadline))
const statusText = computed(() => STATUS_TEXT[status.value] ?? '未知')
```

判断标准很简单：**它是“算出来的”，不是“独立存在的”。**
只有 `keyword`、`statusFilter`、`list` 这些原始数据需要 `ref`；
筛选结果、排序结果、统计数字全都是算出来的。

**不该用**：计算属性里不要做两件事。

**第一，不要发请求。**

```js
// ✗ 错
const detail = computed(async () => {
  const res = await fetch(`/api/activity/${id.value}`)
  return res.json()
})
```

三个问题：

- 计算属性是**同步**的，你把 `Promise` 返回出去，模板拿到的是一个 `Promise` 对象，
  不是数据；
- 计算属性可能在任何时候被重新求值，你没法控制请求发几次；
- 计算属性应该是**纯函数**（同样的输入给同样的输出），而请求会受网络影响。

正确做法：用 `watch` + 请求函数，或者[单元 10 的请求层](/unit10/04-request-layer)。

**第二，不要改其他状态。**

```js
// ✗ 错：计算属性里改了别的状态
const filteredList = computed(() => {
  const result = list.value.filter((a) => a.status === statusFilter.value)
  totalCount.value = result.length   // 改了别的响应式数据
  return result
})
```

危险在于：这会让“读一个值”产生副作用。别的计算属性或渲染过程读到它，
可能又触发 `totalCount` 变化，进而触发新的更新 —— 更新链条变得不可预测，
严重时会造成无限循环。

**正确做法**：`totalCount` 本身也用计算属性算出来，不要人工赋值。

```js
// ✓ 对：各自算各自的
const filteredList = computed(() => list.value.filter((a) => a.status === statusFilter.value))
const totalCount = computed(() => filteredList.value.length)
```

::: details 计算属性里能写 console.log 吗
可以，**但要知道它会带来什么。** `console.log` 是一种副作用，
它会让你观察到“重算了没有”，是调试的好办法。

但也要注意：它本身不影响计算结果，所以一般可以接受。
真正要避免的是“改数据”和“发请求”这两类会改变外部世界的操作。

**判断原则：计算属性里只能读，不能写外部状态。**
:::

### 计算属性能写吗：getter 与 setter

默认的计算属性是只读的。想写，就要提供 `get` 和 `set`：

```js
const fullName = computed({
  get() {
    return `${lastName.value}${firstName.value}`
  },
  set(newValue) {
    // 把新值拆开，分别写回两个源状态
    lastName.value = newValue.slice(0, 1)
    firstName.value = newValue.slice(1)
  }
})

fullName.value = '张小明'
console.log(lastName.value)   // 张
console.log(firstName.value)  // 小明
```

写计算属性的典型场景是**做双向绑定的中间层**。项目里最常见的例子是
“活动时间段”：数据里存的是开始时间和结束时间，界面上要显示成
`09:00 - 11:00` 这种格式，并且可以编辑。

```vue [src/components/TimeRangeInput.vue]
<script setup>
import { ref, computed } from 'vue'

const startTime = ref('09:00')
const endTime = ref('11:00')

// 对外表现为一个可读写的字符串
const timeRange = computed({
  get: () => `${startTime.value} - ${endTime.value}`,
  set: (val) => {
    const [start, end] = val.split(' - ')
    startTime.value = (start ?? '').trim()
    endTime.value = (end ?? '').trim()
  }
})
</script>

<template>
  <!-- v-model 会读 timeRange，写的时候也会调 setter -->
  <input v-model="timeRange" />
  <p>开始：{{ startTime }}，结束：{{ endTime }}</p>
</template>
```

`v-model` 用在计算属性上时，**必须提供 setter**，否则赋值时控制台会警告
`Write operation failed: computed value is readonly`。

::: warning setter 里不要漏了写回源状态
setter 的职责是“把新值拆解，写回源状态”。如果你在 setter 里只是
`console.log(newValue)`，界面上的输入框会立刻弹回旧值 ——
因为 `v-model` 读完发现 `get` 的结果没变。

**排查这类问题的入口**：输入之后值弹回去，先看 setter 有没有真的写回源状态。
:::

### 计算属性、方法、侦听器怎么选

三个都能实现“根据数据做点事”，但适用场景不同：

| 需求 | 用什么 | 例子 |
| --- | --- | --- |
| 从已有状态算出一个值，用于显示 | **计算属性** | 总数、比例、格式化后的文字 |
| 需要传参数、需要在事件里处理 | **方法** | `formatDate(date)`、`submit(form)` |
| 数据变化时要**做事**（而不是算出值） | **侦听器** | 关键词变了之后发请求、自动保存草稿 |
| 结果需要缓存 | **计算属性** | 大数组的筛选排序 |
| 每次都要重新执行 | **方法** | 点击时读当前时间 |

一句话区分：

- **要一个值 → 计算属性**
- **要用参数拿一个值 → 方法**
- **要做一个动作 → 侦听器**

::: details 一个常见误用：用侦听器去算值
```js
// ✗ 错：用 watch 维护一份“派生状态”
const keyword = ref('')
const filteredList = ref([])

watch(keyword, () => {
  filteredList.value = list.value.filter((a) => a.title.includes(keyword.value))
}, { immediate: true })
```

这段代码能跑，但它是**错的思路**。问题有三：

1. 多了一份需要手动维护的状态（`filteredList`）；
2. `immediate: true` 是为了补上首次渲染，忘记写就出 bug；
3. 如果筛选条件以后变成两个（关键词 + 状态），你要么加一个 `watch` 监听两个来源，
   要么在回调里把两个都写一遍。

**正确写法**：

```js
// ✓ 对：派生值就用计算属性
const filteredList = computed(
  () => list.value.filter((a) => a.title.includes(keyword.value))
)
```

加一个筛选条件，就在 `computed` 里加一个 `&&`。**这是这一单元最重要的一个判断。**
:::

## 小结

- 计算属性用于从已有状态算出新值，**结果会被缓存**，依赖不变就不重算。
- 实测差别：模板引用三次，方法打印三次，计算属性只打印一次。
- 模板里计算属性**不加括号**，方法是加括号的。
- 计算属性里不要发请求、不要改其他状态 —— 它应该是一个只读别人、不改别人的纯计算。
- 可写计算属性要提供 `get` / `set`，典型用途是 `v-model` 的中间层。
- 选择口诀：**要一个值 → 计算属性；要用参数取一个值 → 方法；要做一个动作 → 侦听器。**
- 派生数据一律用计算属性，不要用 `watch` 去维护第二份状态。

## 常见坑

::: details 坑 1：模板里把计算属性当成函数调用
```vue
<!-- ✗ 错：计算属性不是函数 -->
<p>{{ totalCount() }}</p>

<!-- ✓ 对：当属性用 -->
<p>{{ totalCount }}</p>
```

**现象**：报 `totalCount is not a function`。

**原因**：`computed` 返回的是一个 ref 对象，模板自动解包后是值本身，不是函数。

**怎么处理**：去掉括号。**如果加上括号能跑**，说明它其实是个方法，不是计算属性 ——
那就该考虑要不要改成计算属性。
:::

::: details 坑 2：在计算属性里改别的状态导致死循环
```js
const a = computed(() => b.value + 1)
const b = computed(() => a.value + 1)
```

**现象**：控制台报 `Maximum recursive updates exceeded` 或者页面卡死。

**原因**：两个计算属性互相依赖，形成循环。Vue 检测到更新次数过多就会停下来报错。

**怎么处理**：检查依赖关系，理清“谁是源、谁是派生”。
应该是单向的：源 → 派生一 → 派生二，绝不能回头。

**更隐蔽的情况**：计算属性里调了一个函数，那个函数改了状态。
排查时注意“计算属性里调用的东西”有没有副作用。
:::

::: details 坑 3：计算属性依赖了非响应式数据，于是永远不更新
```js
// ✗ 有隐患：Date.now() 不是响应式数据
const closingThisWeek = computed(() => {
  const now = Date.now()
  const weekLater = now + 7 * 24 * 60 * 60 * 1000
  return activities.value.filter((a) => {
    const t = new Date(a.deadline).getTime()
    return t >= now && t <= weekLater
  })
})
```

**现象**：页面打开时算得对，过了几分钟、跨过某个截止时间点，
数字**不会自动变化**。要等 `activities` 变了才重算。

**原因**：计算属性只追踪**响应式依赖**。`Date.now()` 是一个普通函数调用，
Vue 不知道“时间在流逝”，所以不会把它计入依赖。

**怎么处理**：有两种需求要分开。

- **只要“进页面时算一次”** —— 现在的写法就够了，不用改；
- **要随时间自动刷新** —— 需要一个定时器把当前时间变成响应式状态：

```js
const now = ref(Date.now())
setInterval(() => { now.value = Date.now() }, 60 * 1000)   // 每分钟更新一次
const closingThisWeek = computed(() => {
  return activities.value.filter((a) => {
    const t = new Date(a.deadline).getTime()
    return t >= now.value && t <= now.value + 7 * 24 * 60 * 60 * 1000
  })
})
```

**这个坑的通性**：计算属性只对响应式数据敏感。用了 `Math.random()`、
`window.innerWidth`、`localStorage.getItem()` 这类非响应式来源，
都会出现“不更新”的现象。
:::

::: details 坑 4：把 `toFixed` 的返回当成数字
```js
const ratio = computed(() => (signed / capacity).toFixed(2))
// ratio 是字符串 "0.85"，不是数字
if (ratio.value > 0.5) { /* 字符串和数字比较，结果可能不符合预期 */ }
```

**现象**：比较结果不对，或者传给图表库时类型报错。

**原因**：`toFixed` 返回**字符串**。

**怎么处理**：需要数字就保留数字，只在最后显示时 `toFixed`。
这也是一个通用的取舍：**计算属性里存“数据”，格式化放到渲染时或用单独的格式化计算属性。**
:::

## 课后练习

::: details 练习 1：实测缓存
照着上面的 `NameCompare.vue` 敲一遍，完成三个实验：

1. 首次渲染，函数和计算属性各打印几次？
2. 改动 `firstName`（改成不同的值），各打印几次？
3. 改动 `firstName`（改成**相同的值**），各打印几次？

**参考思路**：第 3 问的答案取决于你怎么写。如果写成 `firstName.value = '一鸣'`
（和当前值一样），Vue 在 `set` 时会比较新旧值，相同就不触发更新，
所以**两个都不打印**。

**进一步**：如果 `firstName` 是一个对象，你改了它的属性而不是替换它，
情况会怎样？这就是 `deep` 选项的由来，[5.2](/unit05/02-watch) 会讲。
:::

::: details 练习 2：把 watch 改成 computed
下面这段代码用 `watch` 维护了一个派生值，请改成计算属性，并说明为什么这样更好。

```vue
<script setup>
import { ref, watch } from 'vue'

const activities = ref([ /* ... */ ])
const signingList = ref([])
const signingCount = ref(0)

watch(activities, () => {
  signingList.value = activities.value.filter((a) => a.status === 'signing')
  signingCount.value = signingList.value.length
}, { immediate: true, deep: true })
</script>
```

**参考思路**：改成两个计算属性，`signingList` 和 `signingCount`，
后者依赖前者。好处是：不用 `immediate`、不用 `deep`
（`computed` 会自动追踪依赖）、少一份需要手动同步的状态。

**再想一步**：如果需求变成“报名中且名额未满”，两个版本各要改几行？
:::

::: details 练习 3：写一个可写的计算属性
实现一个“活动时间段”的输入组件：

1. 内部状态是 `startTime` 和 `endTime` 两个字符串；
2. 对外用一个计算属性 `timeRange` 表示，格式是 `09:00 - 11:00`；
3. 用 `v-model` 绑到输入框上，用户可以编辑整个字符串；
4. 编辑之后，`startTime` 和 `endTime` 要同步更新。

**参考思路**：`get` 里拼字符串，`set` 里 `split(' - ')` 再写回。
注意处理用户输入不规范的情况（没有分隔符、多个分隔符），
写完之后在输入框里乱输一通测试一下 —— **不要相信用户会按格式输入。**
:::

---

上一节：[单元导学](/unit05/) ·
下一节：[5.2 侦听器](/unit05/02-watch)
