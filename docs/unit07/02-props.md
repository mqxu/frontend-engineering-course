# 7.2 父子通信：props

## 子组件改了数据，父组件的数据也跟着变了

把报名记录表格拆成 `SignupTable.vue` 之后，表格里有一段“全部选中”的逻辑：

```vue [src/components/business/SignupTable.vue（有问题）]
<script setup>
const props = defineProps({
  rows: { type: Array, required: true }
})

function selectAll() {
  // ✗ 想给每行加一个“已选中”标记
  props.rows.forEach((row) => {
    row.checked = true
  })
}
</script>
```

点击“全选”，表格上的复选框确实都勾上了。但运营同学发现一个奇怪的现象：

> 我只在这个页面上点了“全选”，返回列表页一看，列表页的报名记录也变成选中状态了。

原因在于：`props.rows` 只是**父组件那个数组的一个引用**，不是它的副本。
`row.checked = true` 改的是父组件数据里那个真实的对象。

更麻烦的是：**控制台没有报任何错。** 因为 Vue 只把 `props` 对象本身设成了只读，
数组里的元素并没有。

这一节讲两件事：**怎么声明属性**（让组件知道该收到什么），
以及**为什么绝对不能在子组件里改属性**。

## 声明：两种写法

### 运行时声明

用 JavaScript 对象描述每个属性的类型与规则。这是最常用的写法：

```js [src/components/business/SignupTable.vue]
const props = defineProps({
  // 必填的数组
  columns: { type: Array, required: true },
  // 数组，默认是空数组
  rows: { type: Array, default: () => [] },
  // 布尔，默认是 false
  loading: { type: Boolean, default: false },
  // 字符串，有默认值
  emptyText: { type: String, default: '暂无报名记录' },
  // 可以是多种类型
  rowKey: { type: [String, Function], default: 'id' }
})
```

每个属性的配置项：

| 配置项 | 作用 | 说明 |
| --- | --- | --- |
| `type` | 声明类型 | 可以是构造函数或由它们组成的数组 |
| `required` | 是否必填 | 为 `true` 时缺失会在控制台警告 |
| `default` | 默认值 | 不传时使用；**对象与数组必须写成函数** |
| `validator` | 自定义校验 | 一个返回布尔值的函数，返回 `false` 时警告 |

也可以只写类型，用简写形式：

```js [简写形式]
// columns 是必填的（数组类型默认必填），rows 是可选的
defineProps({
  columns: Array,
  rows: Array
})
```

::: tip 什么时候用简写
只在**快速原型**里用。实际项目里建议一律写完整对象形式，
因为 `required` 和 `default` 这两个信息非常重要 —— 它们是接口的一部分。

**判断标准**：读你组件的人能不能只看 `defineProps` 就知道该怎么用它？
:::

### 类型声明（TS 项目）

如果项目开了 TypeScript，可以用泛型直接声明：

```vue [src/components/business/SignupTable.vue]
<script setup lang="ts">
interface SignupRow {
  id: number
  studentName: string
  studentId: string
  status: 'pending' | 'approved' | 'rejected'
}

const props = defineProps<{
  columns: TableColumn[]
  rows: SignupRow[]
  loading?: boolean
  emptyText?: string
}>()
</script>
```

类型声明的好处是**属性和类型定义绑在一起**，编辑器补全更准。代价是**没法写默认值**
（因为泛型是纯类型，编译后不存在）。

3.5 之前要用 `withDefaults` 来补默认值：

```vue [Vue 3.4 及之前的写法]
const props = withDefaults(
  defineProps<{ rows?: SignupRow[]; loading?: boolean }>(),
  {
    rows: () => [],
    loading: false
  }
)
```

3.5 起可以直接解构时给默认值，更简洁：

```vue [Vue 3.5 起的写法]
const { rows = [], loading = false } = defineProps<{
  rows?: SignupRow[]
  loading?: boolean
}>()
```

::: tip 本课程用哪种
本课程主用 JavaScript，所以**默认用运行时声明**（对象形式）。
看到 TS 项目里出现 `defineProps<...>()` 时不用慌，它和对象形式是一回事，
只是把“类型”这一项交给了 TypeScript。
:::

### 对象与数组的默认值必须用函数

这是最容易记错的一条。先看错的写法：

```js [✗ 错误示范]
defineProps({
  rows: { type: Array, default: [] },
  options: { type: Object, default: {} }
})
```

再看对的写法：

```js [✓ 正确示范]
defineProps({
  rows: { type: Array, default: () => [] },
  options: { type: Object, default: () => ({}) }
})
```

**为什么必须用函数？** 因为 `default` 的值在模块加载时就要确定。如果直接写 `[]`，
那么**所有用到这个组件的实例会共享同一个数组**：

```js [共享引用会出什么问题]
// 组件 A 里 push 了一条数据
props.rows.push(item)

// 组件 B 里的 rows 也会多出这条 —— 因为它们是同一个数组
```

写成 `() => []` 之后，每次创建组件实例都会**调用一次函数，得到一个全新的数组**，互不影响。

::: danger 这种 bug 特别难查
现象是“组件 A 操作了一下，组件 B 的显示莫名其妙变了”，而且**只在同一个页面里
出现两个相同组件时才复现**。单个组件测试时完全正常。

**记住一条：`Array` 和 `Object` 类型的 `default` 一律写成返回新值的函数。**
箭头函数 `() => []` 是最常用的形式，写起来最短。
:::

### 布尔属性的特殊行为

布尔类型的属性有个约定：**不传值时会被当作 `false`**（相当于默认值就是 `false`）。
所以下面两行是同一个意思：

```vue
<SignupTable :loading="false" />
<SignupTable />
```

但要注意一个容易踩的地方：**写 `loading` 而不写 `:loading`，传的是字符串 `"false"`**。

```vue
<!-- ✗ 传的是字符串 "false"，它转成布尔是 true -->
<SignupTable loading="false" />

<!-- ✓ 用 v-bind（简写冒号）才是真正的布尔值 -->
<SignupTable :loading="false" />
```

**只要属性值不是字符串，就必须用 `:`。** 数字、布尔、对象、数组、表达式，全都要加冒号。

## `v-bind` 批量传属性

如果属性很多，一个一个写会很啰嗦。可以用 `v-bind` 传一个对象，把对象里的键展开成属性：

```vue [src/views/SignupReviewView.vue]
<script setup>
import { reactive } from 'vue'
import SignupTable from '@/components/business/SignupTable.vue'

const tableProps = reactive({
  columns: [
    { key: 'studentName', title: '姓名', width: 120 },
    { key: 'studentId', title: '学号', width: 160 },
    { key: 'status', title: '审核状态', width: 120 }
  ],
  rows: [],
  loading: false,
  emptyText: '本次活动的报名记录为空'
})
</script>

<template>
  <!-- 把 tableProps 里的每一项当作一个属性传进去 -->
  <SignupTable v-bind="tableProps" />
</template>
```

还可以混用，后面的会覆盖前面的：

```vue [混用时后面的优先]
<SignupTable v-bind="tableProps" :loading="true" empty-text="正在加载……" />
```

::: warning `v-bind` 批量传属性要克制
它很方便，但**易读性明显下降**：读模板的人看不出这个组件到底收到了哪些属性，
必须跳到 `tableProps` 的定义处。

建议只在两种情况用：
1. 属性确实很多（超过 6 个），且它们来自同一个配置对象。
2. 要做“透传”：把父组件收到的属性原样传给子组件。

**属性少于 5 个时，老老实实一个个写。** 一眼能看全比少打几个字重要。
:::

## 单向数据流：为什么不能改 props

这是本单元最重要的一条规则。

### 数据是往下流的

```text [单向数据流]
   父组件 ActivityDetailView
   ┌──────────────────────┐
   │  const rows = ref([]) │
   └───────────┬──────────┘
               │ props 往下传
               ▼
   ┌──────────────────────┐
   │   子组件 SignupTable   │
   │   props.rows          │  ← 只能读，不能写
   └───────────┬──────────┘
               │ emit 事件往上抛
               ▲
               │
   父组件收到事件后自己改数据，再通过 props 流下来
```

**规则：数据从父组件流向子组件，子组件要改数据，只能“请求”父组件来改。**

### 直接赋值：有警告，不生效

```vue [src/components/business/SignupTable.vue]
<script setup>
const props = defineProps({
  rows: { type: Array, default: () => [] }
})

function clearRows() {
  // ✗ 直接赋值
  props.rows = []
}
</script>
```

控制台会打印类似这样的警告：

```text [控制台输出]
[Vue warn] Set operation on key "rows" failed: target is readonly.
```

赋值的动作被拦下了，数据没变。**这种错误至少能自己发现。**

### 改内部成员：没有警告，但父组件数据被改了

```vue [src/components/business/SignupTable.vue]
function selectAll() {
  // ✗ 没有警告，但改的是父组件的数据
  props.rows.forEach((row) => {
    row.checked = true
  })
}
```

`props.rows` 是父组件那个数组的引用。往里 push、给元素加字段、改元素属性，
**都会改到父组件的数据上**，而且 Vue 不会给警告 ——
因为 `props` 本身只做了浅层的只读处理，数组里的元素没有。

::: danger 为什么这件事必须彻底搞清楚
它的破坏性是“隐蔽”的：

1. **数据来源变得不可追踪**：父组件的数据被改了，但改动发生在子组件里，
   你顺着父组件的代码找不到是谁改的。
2. **同样的数据被多个组件共享时，一个组件的操作会影响另一个**。
3. **调试时最费时间**：因为没有任何警告，只能靠“二分法”一个个排除。
:::

### 正确做法：把决定权交回父组件

```vue [src/components/business/SignupTable.vue]
<script setup>
const props = defineProps({
  rows: { type: Array, default: () => [] }
})

// ✓ 只声明“用户想全选”，不自己改数据
const emit = defineEmits(['select-all'])

function handleSelectAll() {
  // 把最新的选择状态抛给父组件，由它决定怎么改
  const allChecked = props.rows.every((row) => row.checked)
  emit('select-all', !allChecked)
}
</script>

<template>
  <button type="button" @click="handleSelectAll">全部选中 / 取消</button>
</template>
```

父组件收到事件后修改自己的数据：

```vue [src/views/SignupReviewView.vue]
<script setup>
import { ref } from 'vue'
import SignupTable from '@/components/business/SignupTable.vue'

const rows = ref([/* ... */])

// ✓ 数据是父组件的，改动也发生在父组件里
function onSelectAll(checked) {
  rows.value.forEach((row) => {
    row.checked = checked
  })
}
</script>

<template>
  <SignupTable :rows="rows" @select-all="onSelectAll" />
</template>
```

::: tip 一个可以记住的口诀
**“谁的数据谁负责改。”**

`rows` 是在父组件里 `ref` 出来的，那它的所有改动都在父组件里发生。
子组件只能做两件事：**读它**、**告诉父组件该怎么改**。
:::

### 只读的数据也要注意

有些属性你只是拿来显示，但它是对象，同样不要在里面加字段：

```js [子组件里不该做的事]
// ✗ 即使只是“临时加一个显示用的字段”也不行
props.row.displayIndex = index

// ✓ 需要派生数据就用 computed，别往原数据里塞
const displayRows = computed(() =>
  props.rows.map((row, index) => ({ ...row, displayIndex: index }))
)
```

**判断标准：我的代码在修改别人传进来的东西吗？** 是的话就换种做法。

## props 解构的响应性

这是一个版本差异问题，必须知道，否则会写出“数据不更新”的代码。

### 3.5 之前：解构会丢响应性

```vue [Vue 3.4 及之前（有问题）]
<script setup>
const props = defineProps({
  title: { type: String, default: '' }
})

// ✗ 解构出来的 title 是“当时的值”，之后 props.title 变化它不会更新
const { title } = props
</script>

<template>
  <!-- 页面第一次显示正常，父组件改了 title 之后这里不再变 -->
  <h2>{{ title }}</h2>
</template>
```

现象很典型：**首次渲染是对的，之后父组件更新了属性，子组件里解构出来的变量永远停在旧值。**
因为解构的那一刻，`title` 只是一个普通变量，和 `props` 之间的响应式关联断了。

当时的两种正确写法：

```vue [Vue 3.4 及之前的正确写法]
// 写法一：不解构，直接用 props.xxx
const props = defineProps({ title: String })
// 模板里写 props.title

// 写法二：用 toRef 保持响应性
import { toRef } from 'vue'
const title = toRef(props, 'title')
```

### 3.5 起：支持响应式解构

Vue 3.5 让解构出来的属性**默认保持响应性**，编译器会自动把它转成对 `props` 的访问：

```vue [Vue 3.5 起]
<script setup>
// ✓ 解构后仍然是响应式的，父组件更新会自动反映
const { title, rows = [], loading = false } = defineProps({
  title: { type: String, default: '' },
  rows: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false }
})
</script>

<template>
  <h2>{{ title }}</h2>
  <p v-if="loading">加载中……</p>
</template>
```

而且**默认值可以直接写在解构里**，不用再单独写 `default`。

### 两种写法对比

| 对比项 | `props.xxx`（所有版本） | 解构（3.5 起） |
| --- | --- | --- |
| 响应性 | 有 | 有 |
| 写法简洁度 | 要一直写 `props.` | 直接写变量名 |
| 默认值 | 在 `defineProps` 里写 `default` | 可以写在解构里 |
| 版本要求 | 无 | **必须 3.5 及以上** |
| 误用风险 | 低 | 在 3.4 项目里写会悄悄丢响应性 |

::: warning 在一个老项目里该怎么写
先看 `package.json` 里的 `vue` 版本。

- 是 `3.5.42` 或更高 → 可以用解构，写起来更清爽。
- 是 `3.4.x` 或更低 → **不要解构**，用 `props.xxx`。

最危险的情况是：在 3.4 项目里照着网上的新文章写了解构，代码不报错，
但“属性变了页面不刷新”。这类 bug 排查起来很花时间。
:::

## 属性命名：模板用 kebab-case，JS 用 camelCase

JavaScript 里属性名用驼峰：

```js [子组件里声明]
defineProps({
  emptyText: { type: String, default: '暂无数据' },
  rowKey: { type: String, default: 'id' }
})
```

模板里用连字符：

```vue [父组件里传递]
<!-- ✓ 推荐：模板里用 kebab-case -->
<SignupTable :empty-text="'暂无报名记录'" row-key="id" />
```

两边 Vue 会自动对应上：`empty-text` 会绑定到 `emptyText`。

::: tip 为什么模板里推荐 kebab-case
因为 **HTML 属性名本来就不区分大小写**。浏览器会把 `emptyText` 全部转成小写，
变成 `emptytext`，和 `emptyText` 对不上。

在单文件组件的 `<template>` 里，Vue 的编译器能正确识别驼峰，
所以写 `:emptyText="..."` 也能用。但**如果你把组件放到 DOM 模板里用
（比如直接在 `index.html` 里写），驼峰就一定失效**。

**统一用 kebab-case，不用想“这里行不行”。**
:::

## 小结

- `defineProps` 有两种声明方式：**运行时对象声明**（JS 项目常用）和**类型声明**（TS 项目）；
  3.5 起类型声明还可以在解构时给默认值。
- **`Array` 与 `Object` 的 `default` 必须写成函数**，否则多个实例会共享同一个引用。
- 布尔属性不传值时为 `false`；**传非字符串值一定要用 `:`**。
- `v-bind="obj"` 可以批量传属性，但属性少时不要用，易读性更重要。
- **单向数据流**：子组件只能读 `props`，不能改。直接赋值会警告且不生效；
  **改内部成员不警告但会改到父组件数据**，这是最危险的一种。
- 正确做法：子组件用 `emit` 表达“请父组件改”，数据改动发生在父组件里。
- 3.5 之前解构 props 会丢响应性，要用 `props.xxx` 或 `toRef`；
  **3.5 起解构默认就是响应式的**。
- 属性名在 JS 里用 camelCase，**在模板里用 kebab-case**。

## 常见坑

::: details 坑 1：子组件里 push 了 props 数组
**现象**：子组件操作了一下，父组件的数据跟着变了；没有警告。

**原因**：`props` 只是浅层只读，数组内部的元素和嵌套对象都能被改。

**处理**：把改动逻辑挪到父组件，子组件用 `emit`。
如果子组件只是需要“加工后的数据”，用 `computed` 生成新数组（`map`、`filter` 都返回新数组）。
:::

::: details 坑 2：对象类型的 `default` 写成了字面量
**现象**：同一个页面里放两个相同组件，操作一个，另一个也跟着变。

**原因**：`default: []` 让所有实例共享同一个数组。

**处理**：写成 `default: () => []`、`default: () => ({})`。
:::

::: details 坑 3：布尔属性传了字符串
**现象**：`<SignupTable loading="false" />`，结果 `loading` 是 `true`，一直显示加载中。

**原因**：`loading="false"` 传的是字符串 `"false"`，非空字符串转布尔是 `true`。

**处理**：用 `:loading="false"` 传真正的布尔值。**非字符串值一律加冒号。**
:::

::: details 坑 4：在 3.4 项目里解构 props，数据不更新
**现象**：子组件里 `const { title } = props`，父组件改了 `title`，子组件不刷新。

**原因**：3.5 之前解构会丢掉响应性。

**处理**：改用 `const title = toRef(props, 'title')`，或者直接用 `props.title`。
**遇到“首次渲染对、后续不更新”的现象，先检查有没有解构。**
:::

::: details 坑 5：属性声明了但父组件没传，模板里报错
**现象**：子组件里写 `props.columns.map(...)`，父组件忘了传，直接报
`Cannot read properties of undefined`。

**原因**：没有给数组或对象类型的属性写默认值。

**处理**：给所有**非必填**的对象、数组类属性一个默认值：
```js
columns: { type: Array, default: () => [] }
```
然后用 `required: true` 明确标出哪些是**必须传**的。
**必填就报错（有警告），非必填就给安全默认值**，两者要分开。
:::

## 课后练习

::: details 练习 1：给表格组件写一份属性表
设计 `SignupTable` 组件的属性，要求：

- 数据源是数组，必填
- 列配置是数组，必填
- 加载状态，布尔，可不传
- 空数据文案，字符串，可不传
- 每行的唯一标识字段名，字符串或函数，可不传

写出完整的 `defineProps` 声明，并在注释里写清每个属性“必填还是可选、不传时是什么”。

**参考思路**：注意两个数组类型属性的 `default` 写法。
第三、四个属性想想布尔类型的默认行为，第五个想想怎么声明两种类型。

:::

::: details 练习 2：把这段“改 props”的代码改对
```vue [src/components/business/SignupTable.vue]
<script setup>
const props = defineProps({
  rows: { type: Array, default: () => [] }
})

function approveFirst() {
  const first = props.rows.find((r) => r.status === 'pending')
  if (first) {
    first.status = 'approved'
  }
}
</script>
```

改成符合单向数据流的写法，写出**子组件**和**父组件**两边的代码。

**参考思路**：子组件只负责“找到是哪一个”并 `emit` 出去（建议带 `id`），
父组件负责改状态。想一想：如果状态的合法性有规则（比如“已截止的活动不能审核”），
这条规则应该写在哪一边？

:::

::: details 练习 3：解释一个现象
有一段代码，父组件这样用：

```vue
<TitleBar :title="title" />
<button @click="title = '新标题'">改名</button>
```

子组件有两种写法：

```js
// 写法 A
const props = defineProps({ title: String })
// 模板里写 {{ props.title }}

// 写法 B
const { title } = defineProps({ title: String })
// 模板里写 {{ title }}
```

在 Vue 3.4 和 Vue 3.5 两个版本下，两种写法分别会有什么效果？整理成一张表。

**参考思路**：四种组合逐个判断。3.5 的那一栏如果都是“正常”，
就说明为什么现在推荐写解构 —— 也要说明**前提是版本够新**。

:::

---

上一节：[7.1 单文件组件与拆分依据](/unit07/01-sfc) ·
下一节：[7.3 父子通信：emits](/unit07/03-emits)
