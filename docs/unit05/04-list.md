# 5.4 列表渲染与键值

## 一个具体的场景

活动详情页要显示报名名单。名单是一个数组，每个元素有学号、姓名、审核状态、备注。
用 `v-for` 渲染：

```vue
<script setup>
import { ref } from 'vue'

const signups = ref([
  { id: '2023010101', name: '林一鸣', status: 'approved' },
  { id: '2023010102', name: '周小雨', status: 'pending' },
  { id: '2023010103', name: '陈思远', status: 'rejected' }
])
</script>

<template>
  <ul>
    <li v-for="signup in signups" :key="signup.id">
      {{ signup.name }}（{{ signup.id }}）
    </li>
  </ul>
</template>
```

`v-for="signup in signups"` 的意思是：把 `signups` 的每一项依次赋给 `signup`，
为每一项渲染一个 `<li>`。

`:key="signup.id"` 是这一节的重点。**它看起来可有可无，实际上决定了列表更新时会不会出错。**

## 原理与写法

### v-for 的三种遍历

**遍历数组** —— 最常用。可以用两个变量拿到下标：

```vue
<template>
  <!-- 只要每一项 -->
  <li v-for="item in list" :key="item.id">{{ item.name }}</li>

  <!-- 需要下标时（注意下标写在后面） -->
  <li v-for="(item, index) in list" :key="item.id">
    第 {{ index + 1 }} 名：{{ item.name }}
  </li>
</template>
```

**遍历对象** —— 拿到值、键、下标：

```vue
<script setup>
import { reactive } from 'vue'
const summary = reactive({ draft: 3, signing: 12, closed: 5 })
</script>

<template>
  <ul>
    <!-- 顺序是 (值, 键, 下标) -->
    <li v-for="(count, status, index) in summary" :key="status">
      {{ index }}. {{ status }}：{{ count }} 场
    </li>
  </ul>
</template>
```

**遍历数字** —— 从 1 数到 n：

```vue
<template>
  <!-- 从 1 开始，不是从 0 -->
  <span v-for="n in 5" :key="n">{{ n }}</span>
  <!-- 渲染出 1 2 3 4 5 -->
</template>
```

::: warning 数组和对象不要用同一个变量名
`v-for` 的作用域只在它所在的元素内部。嵌套循环时第二层会覆盖第一层的变量名，
这是常见的错误来源：

```vue
<!-- ✗ 内层的 item 覆盖了外层 -->
<li v-for="activity in activities" :key="activity.id">
  <span v-for="item in activity.sessions" :key="item.id">{{ activity.title }}</span>
</li>

<!-- ✓ 变量名区分开 -->
<li v-for="activity in activities" :key="activity.id">
  <span v-for="session in activity.sessions" :key="session.id">{{ activity.title }}</span>
</li>
```

**报错现象**：内层拿到了外层的数据，或者渲染出意料之外的内容。
`v-for` 的变量名建议带业务含义，不要一律叫 `item`。
:::

### key 的作用：决定“哪个 DOM 对应哪条数据”

#### 现象：删除中间一项，输入框内容错位

先看一个能复现问题的例子。

```vue
<script setup>
import { ref } from 'vue'

const signups = ref([
  { id: 1, name: '林一鸣' },
  { id: 2, name: '周小雨' },
  { id: 3, name: '陈思远' }
])

function remove(index) {
  signups.value.splice(index, 1)
}
</script>

<template>
  <ul>
    <!-- 注意这里用 index 作为 key -->
    <li v-for="(signup, index) in signups" :key="index">
      <span>{{ signup.name }}</span>
      <input placeholder="填写备注" />
      <button @click="remove(index)">删除</button>
    </li>
  </ul>
</template>
```

复现步骤：

1. 在三个输入框里分别填 “A”“B”“C”；
2. 点第一行的“删除”。

**预期**：名单变成两个人，“B”和“C”跟着各自的名字留在页面上。

**实际**：名字变成了“周小雨”“陈思远”，但输入框里的内容还是 “A”“B”。
**备注和人对不上了。**

#### 为什么会这样

Vue 在更新列表时，需要判断“新列表里的每一项，对应旧列表里的哪一个元素”。
`key` 就是这个判断依据。

**用索引做 key 时**，`key` 的值是 `0, 1, 2`。
删除第一项之后，新的列表仍然是 `0, 1`：

| 新旧对比 | `key=0` | `key=1` |
| --- | --- | --- |
| 旧列表 | 林一鸣（备注 A） | 周小雨（备注 B） |
| 新列表 | 周小雨 | 陈思远 |

Vue 看到 `key=0` 还在，就**复用**原来那个 `<li>`，只把里面的文字从“林一鸣”
改成“周小雨”。但输入框里用户手打的 “A” **不是数据驱动的**，
它只存在 DOM 里，于是留在了原地 —— 备注就串到别人身上了。

用 `id` 做 key 时，`key` 的值是 `1, 2, 3`。
删除 `id=1` 之后，Vue 发现 `key=1` 消失了，就把对应的 `<li>` 整块销毁，
剩下的 `key=2`、`key=3` 元素原地不动。**备注和名字一起保持配对。**

#### 三条选键原则

| 原则 | 说明 |
| --- | --- |
| **用业务上唯一且稳定的标识** | 后端返回的 `id`、学号、活动编号。它唯一，而且不会因为位置变化而改变 |
| **不要用索引** | 除非列表是**纯静态**的：永不增删、永不排序、永不筛选 |
| **不要用随机数或时间戳** | `:key="Math.random()"` 每次渲染都生成新值，Vue 会销毁并重建所有元素 —— 比用索引更糟 |

“唯一且稳定”里的**稳定**两个字最容易被忽略。
下面这种 key 就不稳定：

```vue
<!-- ✗ 不稳定：同一个列表项，每次筛选后 key 可能变化 -->
<li v-for="item in list" :key="item.name">...</li>
```

如果两个学生的名字重复，`key` 就重复了；名字改了，`key` 就变了。
**唯一性要靠“标识”，不能靠“描述性字段”。**

::: tip 什么情况下用索引 key 是可以的
**纯展示、永不变化的列表。** 比如一个写死的“技能标签”列表：

```vue
<span v-for="(skill, index) in ['需求梳理', '活动执行', '数据复盘']" :key="index">
  {{ skill }}
</span>
```

数据源是字面量数组，不可能增删改序，用索引没有问题。

**但只要列表的数据来自接口、可能被增删改序，就必须给业务 id。**
实际写代码时，一个更省事的规则是：**能用 id 就用 id，不要给自己留下判断的机会。**
:::

### 列表的更新方式：可变与不可变

Vue 3 的响应式是**深层**的，所以下面这些“直接改数组”的写法**也能触发界面更新**：

```js
const list = ref([{ id: 1, done: false }])

list.value.push({ id: 2, done: false })      // ✓ 界面会更新
list.value.splice(0, 1)                       // ✓ 界面会更新
list.value[0].done = true                     // ✓ 界面会更新
```

> 注意：这一点和 Vue 2 不同。Vue 2 因为 `defineProperty` 的限制，
> 需要重写数组方法才能拦截，所以有“某些操作不触发更新”的说法。
> Vue 3 改用 `Proxy`，这些限制都没有了。

**但是，业务代码里仍然推荐用“不可变”的写法** —— 不修改原数组，
而是生成一个新数组再赋值。

```js
const list = ref([
  { id: 1, name: '林一鸣', done: false },
  { id: 2, name: '周小雨', done: true }
])

// 新增：展开生成新数组
list.value = [...list.value, { id: 3, name: '陈思远', done: false }]

// 删除：filter 生成新数组
list.value = list.value.filter((item) => item.id !== 1)

// 修改：map 生成新数组，命中的项用展开生成新对象
list.value = list.value.map((item) =>
  item.id === 2 ? { ...item, done: !item.done } : item
)

// 排序：toSorted 生成新数组（不改动原数组）
list.value = list.value.toSorted((a, b) => a.id - b.id)
// 如果不支持 toSorted，用展开 + sort
list.value = [...list.value].sort((a, b) => a.id - b.id)
```

对比表：

| 操作 | 不可变写法 | 可变写法 |
| --- | --- | --- |
| 新增 | `list.value = [...list.value, item]` | `list.value.push(item)` |
| 删除 | `list.value = list.value.filter(...)` | `list.value.splice(index, 1)` |
| 修改 | `list.value = list.value.map(...)` | `list.value[i].done = true` |
| 排序 | `list.value = list.value.toSorted(...)` | `list.value.sort(...)` |

**为什么推荐不可变？三个理由：**

**理由一：和计算属性的派生链配合得更好。**

```js
const sortedList = computed(() => list.value.toSorted(byDeadline))
```

`computed` 靠“依赖变了”来重算。你换了一个新数组，依赖明确地变了；
而 `push` 这种操作，虽然也能触发，但“这个数组被就地改了”这件事，
在派生链变长之后更难追踪。

**理由二：便于实现撤销、重做、历史记录。**

```js
// 每次修改都留下快照
const history = ref([])

function updateList(nextList) {
  history.value = [...history.value, list.value]
  list.value = nextList
}
```

如果每次都 `push` / `splice` 就地改，历史快照就得深拷贝一份，成本和复杂度都更高。

**理由三：避免多个地方共享同一个数组引用。**

```js
// ✗ 危险：传出去的引用被别处改了，源头也跟着变
const copy = list.value
copy.push(newItem)        // list.value 也被改了
```

**排查“数据莫名其妙变了”时，先看有没有别的地方拿到了数组引用并且就地修改。**

::: details 那 push 就完全不能用吗
可以用。**只是要区分场景：**

- **表单里收集临时数据**（比如多选时拼接一个 `selectedIds`），用 `push` 完全没问题；
- **作为页面主数据、要参与派生链和撤销逻辑**，用不可变写法更清晰。

判断标准：**这份数据会不会被拿去“记录历史”或被多处引用。** 会，就不可变。
:::

### v-for 与 v-if 配合的正确姿势

[5.3](/unit05/03-conditional) 讲过：**Vue 3 里 `v-if` 优先级高于 `v-for`，
写在同一个元素上会拿不到循环变量。** 这里补上列表场景的三种正确写法。

**写法一：先在计算属性里筛，再循环（最推荐）。**

```js
const approvedList = computed(() => signups.value.filter((s) => s.status === 'approved'))
```

```vue
<li v-for="signup in approvedList" :key="signup.id">{{ signup.name }}</li>
```

**写法二：`v-for` 放外层 `<template>`，`v-if` 放里面的元素。**

```vue
<template v-for="signup in signups" :key="signup.id">
  <li v-if="signup.status === 'approved'">{{ signup.name }}</li>
</template>
```

注意 `:key` 放在 `<template>` 上。

**写法三：`v-if` 在循环体内部，用于控制单项里的一部分内容。**

```vue
<li v-for="signup in signups" :key="signup.id">
  <span>{{ signup.name }}</span>
  <!-- 只对已通过的显示这个标签 -->
  <span v-if="signup.status === 'approved'" class="tag">已通过</span>
</li>
```

这种是合法的，因为它用的是循环变量，而且 `v-if` 在循环体内部。

**什么时候用哪种？**

| 需求 | 用哪种 |
| --- | --- |
| 只渲染符合条件的一部分数据 | 写法一（计算属性） |
| 需要在循环里控制元素是否出现 | 写法二或三 |
| 单项内部的小块内容按条件显示 | 写法三 |

**分界线在于：条件是“决定这一项要不要渲染”，还是“决定这一项里的某个部分要不要渲染”。**
前者用计算属性，后者用内层 `v-if`。

## 小结

- `v-for` 可以遍历数组、对象、数字；数组的写法是 `(item, index)`，对象的写法是 `(value, key, index)`。
- `key` 决定“新列表里的每一项对应旧列表的哪个元素”，是列表更新的依据。
- 用索引做 `key`，删除或排序后会出现“备注和人对不上”这类错位；正确做法是用业务唯一标识。
- 选键三条原则：用业务唯一标识、不用索引（除非纯静态）、不用随机数。
- Vue 3 里 `push` / `splice` / 改下标都能触发更新，但业务代码推荐不可变写法：
  新增用展开、删除用 `filter`、修改用 `map`、排序用 `toSorted`。
- 不可变写法的三个好处：配合派生链、便于撤销、避免共享引用被意外修改。
- `v-for` 和 `v-if` 不写在同一个元素上；筛选交给计算属性，单项内部的条件显示写在循环体里。

## 常见坑

::: details 坑 1：忘了写 key
```vue
<!-- ✗ 没有 key -->
<li v-for="item in list">{{ item.name }}</li>
```

**现象**：控制台警告 `[Vue warn]: <li> elements in a v-for should have unique "key"`；
列表更新时可能出现状态错位。

**原因**：没有 key 时 Vue 会退化成“按位置复用”，效果和用索引一样。

**怎么处理**：一律补上 `:key`。**把这条当成硬性习惯，不要等警告出来才加。**
:::

::: details 坑 2：key 用了重复的值
```vue
<!-- ✗ 两个学生的 name 都叫“张伟”，key 重复 -->
<li v-for="item in list" :key="item.name">...</li>
```

**现象**：控制台警告 `Duplicate keys found during update`，
更新时可能删错元素或渲染出重复内容。

**原因**：`key` 必须在同一个列表里唯一。

**怎么处理**：用 `id`、学号这类真正唯一的字段。
**如果接口没返回 id 怎么办？** 在数据加载时补一个：

```js
function normalize(rawList) {
  return rawList.map((item, i) => ({ ...item, _rowKey: item.id ?? `row-${i}` }))
}
```

注意 `_rowKey` 只在“数据不会增删”时可靠。**最佳做法还是让后端返回主键。**
:::

::: details 坑 3：用 `v-if` 判断整个列表是否为空，写在了 `v-for` 的元素上
```vue
<!-- ✗ 循环变量拿不到，且逻辑也不对 -->
<li v-for="item in list" v-if="list.length > 0" :key="item.id">...</li>
```

**现象**：报错，或者渲染结果不符合预期。

**怎么处理**：空状态是独立的一支，用 `v-if` / `v-else` 包在 list 外面：

```vue
<ul v-if="list.length > 0">
  <li v-for="item in list" :key="item.id">{{ item.name }}</li>
</ul>
<p v-else>暂无报名记录</p>
```

**这是四态页面的雏形**，见 [5.5](/unit05/05-four-states)。
:::

::: details 坑 4：以为 `v-for` 的变量名可以随便取
```vue
<!-- ✗ 用了和外面同名的变量 -->
<li v-for="item in list" :key="item.id">
  <span v-for="item in item.children" :key="item.id">{{ item.name }}</span>
</li>
```

**现象**：内层把外层的 `item` 覆盖了，`item.children` 变成在内层 `item` 上找。

**原因**：`v-for` 的变量是普通变量，内层作用域会遮蔽外层同名变量。

**怎么处理**：变量名带业务含义并避免重复。**嵌套两层时尤其要注意。**
:::

## 课后练习

::: details 练习 1：复现并修复错位问题
照着上面的例子，自己搭一个“三个输入框 + 删除按钮”的页面：

1. 用 `index` 作为 key，复现“删除第一行后备注和名字对不上”的现象；
2. 换成 `id` 作为 key，确认问题消失；
3. 再试一次：**不删除，而是把列表倒序**（`list.value.reverse()`），
   看看 index 作为 key 时会出现什么现象。

**参考思路**：倒序时用 index 做 key，元素位置全部复用，
DOM 原地不动，但文字被重新赋值 —— 表现和删除类似。
如果列表里有动画（`<TransitionGroup>`），错位会更明显。

**第 3 问的意义**：**不只是“删除”会出问题，任何改变顺序的操作都会。**
所以“不增删就不用管 key”这个想法是不对的，还要加上“不排序、不筛选”。
:::

::: details 练习 2：把可变操作改成不可变
把下面的写法改成不可变写法，并说明每一步对应哪个数组方法。

```js
const list = ref([
  { id: 1, name: 'A', done: false },
  { id: 2, name: 'B', done: false }
])

function add(name) {
  list.value.push({ id: Date.now(), name, done: false })
}

function remove(id) {
  const index = list.value.findIndex((item) => item.id === id)
  if (index > -1) list.value.splice(index, 1)
}

function toggle(id) {
  const target = list.value.find((item) => item.id === id)
  if (target) target.done = !target.done
}

function sortByName() {
  list.value.sort((a, b) => a.name.localeCompare(b.name))
}
```

**参考思路**：`add` → 展开；`remove` → `filter`（顺便省掉了 `findIndex`）；
`toggle` → `map` + 展开；`sortByName` → `toSorted`（或展开 + `sort`）。

**额外收获**：`remove` 改成 `filter` 之后，`findIndex` 和 `if (index > -1)`
都不需要了 —— **不可变写法经常能顺带简化代码。**
:::

::: details 练习 3：选 key
下面五份数据，哪些可以用索引作为 `key`？说明理由。

1. 一个写死的技能标签数组 `['需求梳理', '活动执行']`；
2. 从接口拿到的活动列表，每条有 `id`；
3. 从接口拿到的报名名单，后端只返回了学号和姓名；
4. 一个根据用户输入实时生成的“搜索建议”列表；
5. 分页后的当前页数据，每条有 `id`。

**参考思路**：

1. 可以 —— 纯静态；
2. 用 `id`；
3. 用学号（学号本身唯一，是合格的标识）；
4. 看情况。建议用“建议文本”或“文本 + 类型”组合的 key，
   因为建议列表会随着输入频繁整体替换，用索引会复用错误的元素；
5. 用 `id`。**注意分页场景下用索引会导致“翻页后动画错乱、行内状态残留”**，
   因为第二页的第一项会复用第一页第一项的 DOM。

**第 5 问是分页表格里最常见的坑**，[案例 02](/unit05/07-case-grid) 会遇到。
:::

---

上一节：[5.3 条件渲染](/unit05/03-conditional) ·
下一节：[5.5 四态页面规范](/unit05/05-four-states)
