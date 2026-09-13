# 5.3 条件渲染

## 一个具体的场景

活动详情页底部有一排操作按钮，显示哪些按钮取决于活动状态：

| 活动状态 | 显示的按钮 |
| --- | --- |
| `draft` | 编辑、提交审核、删除 |
| `signing` | 编辑名额、截止报名、下架 |
| `closed` | 查看报名名单、下架 |
| `finished` | 查看数据复盘 |
| 其他（非法状态） | 不显示，并提示“状态异常” |

用上一单元学的插值表达式能不能做到？可以，但会很啰嗦：

```vue
<template>
  <span>{{ status === 'draft' ? '编辑' : '' }}</span>
  <span>{{ status === 'signing' ? '编辑名额' : '' }}</span>
  <!-- 每个按钮都要写一遍判断，而且隐藏的是内容而不是元素本身 -->
</template>
```

问题在于：**插值只能控制“显示什么文字”，不能控制“元素存不存在”。**
用三元表达式渲染空字符串，元素还在 DOM 里，只是看不见内容 ——
按钮的边框、间距、占位都还在。

控制“元素要不要出现”，用的是条件渲染指令：`v-if`。

```vue
<template>
  <button v-if="status === 'draft'">编辑</button>
  <button v-if="status === 'draft'">提交审核</button>
  <button v-if="status === 'draft'">删除</button>
  <!-- ... -->
</template>
```

但这样重复判断三次也不好。往下看。

## 原理与写法

### v-if / v-else-if / v-else

`v-if` 是一个“真值判断”：表达式为真，元素被渲染；为假，元素**根本不存在**。

`v-else-if` 和 `v-else` 配合使用，它们必须**紧跟在带 `v-if` 或 `v-else-if` 的元素后面**，
中间不能有其他元素（注释可以，其他标签不行）。

```vue
<script setup>
import { ref } from 'vue'
const status = ref('signing')
</script>

<template>
  <template v-if="status === 'draft'">
    <button>编辑</button>
    <button>提交审核</button>
    <button>删除</button>
  </template>

  <template v-else-if="status === 'signing'">
    <button>编辑名额</button>
    <button>截止报名</button>
    <button>下架</button>
  </template>

  <template v-else-if="status === 'closed'">
    <button>查看报名名单</button>
    <button>下架</button>
  </template>

  <template v-else-if="status === 'finished'">
    <button>查看数据复盘</button>
  </template>

  <p v-else>状态异常，请联系管理员</p>
</template>
```

这里出现了 `<template v-if>`，下一小节专门讲它。

### v-show 与 v-if 的差别

`v-show` 也能控制显示，但它做的事完全不同：

```vue
<template>
  <!-- v-if：条件为假时，元素不存在 -->
  <p v-if="isLoading">加载中…</p>

  <!-- v-show：元素始终存在，只是加了 display: none -->
  <p v-show="isLoading">加载中…</p>
</template>
```

打开浏览器的元素检查面板看 `v-show` 渲染的结果：

```html
<p style="display: none;">加载中…</p>
```

元素在 DOM 里，只是不显示。

差别带来四个实际影响：

| 对比项 | `v-if` | `v-show` |
| --- | --- | --- |
| 是否创建 / 销毁元素 | **是**，条件切换时重建 | 否，只切换 `display` |
| 初始渲染成本 | 条件为假时几乎为零（不创建） | 无论真假都要先渲染出来 |
| 切换成本 | 高（销毁 + 重建整棵子树） | 低（改一个样式属性） |
| 能否保留内部状态 | **不能** —— 重建后输入框内容、组件状态全丢 | **能** —— 元素没被销毁 |
| 能否用在 `<template>` 上 | 能 | **不能**（`<template>` 不渲染成元素，没法改样式） |
| 是否支持 `v-else` | 支持 | 不支持 |

决策表：

| 场景 | 用哪个 | 理由 |
| --- | --- | --- |
| 权限分支、状态分支（登录 / 未登录） | `v-if` | 条件不常变，且不同分支内容差别大 |
| 折叠面板、标签页切换 | `v-show` | 切换频繁，重建 DOM 会明显卡顿 |
| 弹窗、抽屉 | `v-if` 或 `v-show` | 看是否需要保留表单内容，见下 |
| 一个表单区域要不要显示 | 看需求 | 需要保留用户已填内容 → `v-show` |
| 加载中 / 出错 / 空数据 / 有数据 | `v-if` / `v-else-if` | 四态互斥，用同一组指令表达最清楚 |

::: warning “保留输入内容”是最容易被忽略的差别
```vue
<template>
  <input v-show="showAdvanced" v-model="advancedNote" />
  <!-- 切换很多次，用户输入的内容都还在 -->
</template>
```

换成 `v-if`：

```vue
<template>
  <input v-if="showAdvanced" v-model="advancedNote" />
  <!-- 每次隐藏再显示，输入框都是空的 -->
</template>
```

**注意**：`advancedNote` 这个数据本身没丢，丢的是“输入框没来得及同步的内容”
和输入框自身的位置、焦点等状态。如果 `v-model` 已经同步了，数据是安全的；
但如果用户在输入过程中被隐藏（还没触发同步），内容就丢了。

**排查这类“输入框内容莫名清空”的问题时，第一件事就是看外层是 `v-if` 还是 `v-show`。**
:::

### 用 key 强制重建分支

有两个分支结构很像时，Vue 会**尽量复用**元素而不是重新创建。
这在大多数时候是好事（更快），但在下面这种场景会出问题。

```vue
<script setup>
import { ref } from 'vue'
const target = ref('activity')   // activity / session
</script>

<template>
  <!-- 两个分支的元素结构完全一样：一个 label + 一个 input -->
  <template v-if="target === 'activity'">
    <label>活动标题</label>
    <input placeholder="输入活动标题" />
  </template>
  <template v-else>
    <label>场次名称</label>
    <input placeholder="输入场次名称" />
  </template>
</template>
```

复现步骤：

1. 在输入框里敲几个字（比如“校园歌手”）；
2. 点击按钮把 `target` 切成 `session`。

**现象**：`label` 和 `placeholder` 都变了，但输入框里“校园歌手”四个字**还在**。

**原因**：两个分支的元素类型完全相同（`<label>` + `<input>`），
Vue 判断“可以复用”，于是把同一个 `<input>` 留下来，只更新它的属性。
`placeholder` 是会跟着更新的属性，而用户敲进去的 `value` **不是数据驱动的**，
就留在了原地。

**怎么处理**：给两个分支加上不同的 `key`，告诉 Vue“这两个不要复用”。

```vue
<template>
  <template v-if="target === 'activity'" key="activity">
    <label>活动标题</label>
    <input placeholder="输入活动标题" />
  </template>
  <template v-else key="session">
    <label>场次名称</label>
    <input placeholder="输入场次名称" />
  </template>
</template>
```

**加上 `key` 之后，切换时 Vue 会销毁旧分支、创建新分支，
输入框里不会再残留内容。**

::: tip 什么时候需要给分支加 key
判断标准：**两个分支长得像不像。**

- 结构差异很大（一个是列表、一个是空状态）→ 不需要 key；
- 结构几乎一样、只是绑的数据不同 → 加 key，避免状态串台。

**这个坑还有更常见的一种表现形式**：切换标签页时，上一个标签页的滚动位置、
展开状态、第三方组件的内部状态跑到了新标签页上。
**排查这类“状态串台”问题的第一反应，就是看两个分支有没有不同的 key。**
:::

### `<template v-if>`：不产生多余标签的分组

上面那段按钮组用到了 `<template>`。它的作用是**把多个元素当成一组**，
但 `<template>` 本身**不会渲染成任何元素**：

```vue
<template>
  <!-- 如果外层用 <div>，会在页面上多一个 div -->
  <div v-if="isDraft">
    <button>编辑</button>
    <button>删除</button>
  </div>

  <!-- 用 <template>，页面上只有两个 button，没有多余容器 -->
  <template v-if="isDraft">
    <button>编辑</button>
    <button>删除</button>
  </template>
</template>
```

什么时候需要它：

- **不想在页面上多出一层容器**（会影响布局和 CSS 选择器）；
- **想让多个元素共享同一个条件**，而不是每个都写一遍 `v-if`；
- **想在列表里的每一项内部做条件分组**（[5.4](/unit05/04-list) 会用到）。

```vue
<script setup>
import { ref } from 'vue'
const user = ref({ name: '林一鸣', isAuditor: true })
</script>

<template>
  <template v-if="user.isAuditor">
    <p>{{ user.name }}（审核员）</p>
    <p>可审核所有活动</p>
  </template>
  <p v-else>普通用户，暂无审核权限</p>
</template>
```

::: tip `<template>` 的三个限制
1. **不能挂 `v-show`** —— 它不产生元素，没法设 `display`；
2. **不能作为组件根节点**（单个根元素的要求下）；Vue 3 支持多根节点，
   但 `<template>` 作为根节点有特殊行为，初学阶段避开；
3. **不能给它加 `class` / `style`** —— 属性没有落脚的地方。

**它只用来“分组”，不要把它当成容器用。**
:::

### 为什么条件判断和列表循环不要写在同一个元素上

这是一个非常容易踩的坑。

需求：只显示未完成的任务。有同学这么写：

```vue
<template>
  <!-- ✗ 报错：item 未定义 -->
  <li v-for="item in list" :key="item.id" v-if="!item.done">
    {{ item.text }}
  </li>
</template>
```

**报错现象**（Vue 3）：

```text
Property "item" was accessed during render but is not defined on instance.
```

或者：

```text
Cannot read properties of undefined (reading 'done')
```

**原因**：**Vue 3 里 `v-if` 的优先级高于 `v-for`。**

编译时，`v-if` 会被先处理，`v-for` 的循环变量 `item` 此时根本还没有定义。
所以 `v-if="!item.done"` 里的 `item` 是找 `item` 这个变量，找不到就报错。

对比一下：**Vue 2 里优先级是反过来的**（`v-for` 高于 `v-if`），
所以在 Vue 2 里这段代码不报错，只是性能差（先渲染整个列表再一个个隐藏）。
**从 Vue 2 迁移过来的代码，这里经常需要改。**

两种正确改法。

**改法一：加一层 `<template>`，把 `v-for` 放在外层。**

```vue
<template>
  <template v-for="item in list" :key="item.id">
    <li v-if="!item.done">{{ item.text }}</li>
  </template>
</template>
```

注意 `:key` 要放在**带 `v-for` 的那个元素上**（这里是 `<template>`）。

**改法二（更推荐）：用计算属性先筛出来。**

```vue
<script setup>
import { computed } from 'vue'
const undoneList = computed(() => list.value.filter((item) => !item.done))
</script>

<template>
  <li v-for="item in undoneList" :key="item.id">{{ item.text }}</li>
</template>
```

推荐改法二的理由：

1. **模板更干净** —— 只有一层 `v-for`，没有内嵌条件；
2. **筛选逻辑可复用** —— 底部的“未完成 3 项”统计可以直接用 `undoneList.length`；
3. **性能更好** —— 筛选只做一次，而不是在渲染每个元素时判断。

::: tip 一条可以记住的规则
**`v-for` 和 `v-if` 永远不要写在同一个元素上。**

需要“循环 + 过滤”，就在计算属性里过滤；需要在循环里做条件显示，
就把 `v-if` 放到循环体内部的元素上（或包一层 `<template>`）。

**这条规则在代码评审里是硬要求**，因为它同时涉及正确性和可读性。
:::

::: details 那“只显示前 5 条”怎么做
也可以用计算属性：

```js
const topFive = computed(() => list.value.slice(0, 5))
```

**能在计算属性里做的数组处理（filter、slice、sort），一律不要在模板里做。**
:::

## 小结

- `v-if` 控制元素**存不存在**；插值表达式只能控制“显示什么文字”。
- `v-else-if` / `v-else` 必须紧跟在同级的前一个分支后面，中间不能有其他元素。
- `v-show` 只切换 `display`，元素始终在 DOM 里；`v-if` 会真正创建和销毁。
- 选择：条件不常变、分支差别大 → `v-if`；切换频繁 → `v-show`；
  需要保留输入内容 → `v-show`。
- `<template v-if>` 用来给多个元素分组，本身不会渲染成元素，也不能挂 `v-show`。
- **Vue 3 里 `v-if` 优先级高于 `v-for`**，写在同一个元素上会拿不到循环变量而报错。
- 正确做法：`v-for` 放在 `<template>` 外层，或者用计算属性先筛出结果。

## 常见坑

::: details 坑 1：`v-else` 前面多了个元素
```vue
<template>
  <p v-if="isLoading">加载中…</p>
  <span>分隔线</span>
  <!-- ✗ 报错：v-else 没有对应的 v-if -->
  <p v-else>加载完成</p>
</template>
```

**现象**：编译报错，提示 `v-else/v-else-if has no adjacent v-if`。

**原因**：`v-else` 必须紧邻前面的分支元素，中间插了元素就断了联系。

**怎么处理**：把中间的元素移走，或者给 `v-else` 分支自己加一个独立的 `v-if` 条件。
**注释不影响**，可以插注释。
:::

::: details 坑 2：用 `v-show` 处理四态页面
```vue
<!-- ✗ 有问题 -->
<template>
  <p v-show="isLoading">加载中…</p>
  <p v-show="!isLoading && !error && list.length === 0">暂无数据</p>
  <ul v-show="!isLoading && !error && list.length > 0">...</ul>
</template>
```

**现象**：能跑，但条件越写越长，加一种状态就要改每一行。

**原因**：`v-show` 各自独立，无法表达“互斥且完整”的分支关系。

**怎么处理**：四态是用 `v-if` / `v-else-if` / `v-else` 表达的，见
[5.5 四态页面规范](/unit05/05-four-states)。**四态页面一律用 `v-if` 系列。**
:::

::: details 坑 3：以为 `v-if` 里的表达式可以写复杂逻辑
```vue
<!-- ✗ 模板里塞了太多东西 -->
<button v-if="user.role === 'admin' || (user.role === 'organizer' && activity.ownerId === user.id && activity.status !== 'finished')">
```

**现象**：能跑，但没人读得懂，改条件时容易改错。

**怎么处理**：抽成计算属性，名字就是这段逻辑的说明。

```js
const canEdit = computed(() => { /* 上面那一长串 */ })
```

```vue
<button v-if="canEdit">编辑</button>
```

**判断标准：模板里的条件如果读不出“业务含义”，就该抽出去。**
`canEdit` 比那串 `&&` `||` 好读一百倍，而且能被多个地方复用。
:::

::: details 坑 4：切换 `v-if` 时数据看起来“丢了”
```vue
<template>
  <div v-if="activeTab === 'basic'">
    <input v-model="form.title" />
  </div>
  <div v-else>
    <input v-model="form.capacity" />
  </div>
</template>
```

**现象**：在第一个输入框输入一半，切到另一个标签再切回来，内容没了。

**原因**：`v-if` 把元素销毁了，输入框里的**未同步内容**（正在输入、
还没触发 `change` 的部分）随元素一起消失。

**怎么处理**：需要保留输入中间态，用 `v-show`。
注意 `v-model` 在 `input` 事件上是实时同步的，所以常规输入不会丢；
真正会丢的是那些只在 `blur` / `change` 时同步的表单控件（比如某些日期选择器）。
:::

::: details 坑 5：同一个元素上同时写了 `v-if` 和 `v-show`
```vue
<!-- ✗ 不要这样写 -->
<div v-if="isReady" v-show="isVisible">内容</div>
```

**现象**：`v-show` 看起来没起作用；控制台可能有编译器警告。

**原因**：Vue 3 里 `v-if` 的优先级更高。`isReady` 为假时元素根本不会被创建，
`v-show` 没有元素可以切换 `display`；`isReady` 为真时，
`v-show` 才会按 `isVisible` 起作用 —— 结果就是两个条件被串起来，
语义变得难以理解。

**怎么处理**：想清楚你要的是“存不存在”还是“显不显示”，只留一个。

```vue
<div v-if="isReady && isVisible">内容</div>
```

**如果确实两个条件都要，就把它们合并成一个表达式**，
而不是把两个指令叠在一起。
:::

## 课后练习

::: details 练习 1：给按钮组选方案
活动详情页的按钮组，四个状态各显示不同按钮。请分别用两种方式实现：

1. 用 `v-if` / `v-else-if` / `v-else`；
2. 用一张“状态 → 按钮列表”的映射表，配合 `v-for` 渲染。

**然后比较**：
- 加一个新状态，两个版本各要改哪里？
- 哪个版本更符合“数据驱动”的思路？

**参考思路**：映射表版本大概是：

```js
const ACTIONS = {
  draft: [{ text: '编辑', action: 'edit' }, /* ... */],
  signing: [{ text: '编辑名额', action: 'editCapacity' }, /* ... */]
}
const actions = computed(() => ACTIONS[status.value] ?? [])
```

模板里只需要一个 `v-for`。

**结论**：**“同一组元素、内容随状态变”适合映射表；“元素结构差异很大”适合 `v-if`。**
按钮组属于前者，所以映射表更好。但 `v-if` 版本更直观，初学阶段先会写 `v-if`。
:::

::: details 练习 2：修一个 v-if / v-for 混用的 bug
```vue
<template>
  <ul>
    <li v-for="signup in signups" :key="signup.id" v-if="signup.audited">
      {{ signup.studentName }}
    </li>
  </ul>
  <p>已通过 {{ signups.filter(s => s.audited).length }} 人</p>
</template>
```

1. 报什么错？为什么？
2. 用两种方式修好（`<template>` 分组、计算属性）；
3. 顺便把下面那行统计也改成计算属性。

**参考思路**：报 `Property "signup" was accessed during render but is not defined`。
根因是 Vue 3 中 `v-if` 优先级高于 `v-for`。

计算属性版本的额外好处是：**列表和统计共用同一个 `auditedList`，
不用在模板里再 filter 一次。**
:::

::: details 练习 3：设计一个折叠区域
做一个“高级设置”折叠区域，里面有两个输入框和一个下拉框。

要求：
1. 点击标题切换展开 / 收起；
2. 展开状态下用户填了内容，收起再展开，内容**不能丢**；
3. 说明你为什么选 `v-if` 或 `v-show`。

**参考思路**：这个需求必须用 `v-show`，因为要保留输入内容。
但如果需求改成“收起时清空已填内容”，就该用 `v-if`（顺便把数据也重置）。

**这道题的重点是：技术选择取决于需求，而不是“哪个更常用”。**
:::

---

上一节：[5.2 侦听器](/unit05/02-watch) ·
下一节：[5.4 列表渲染与键值](/unit05/04-list)
