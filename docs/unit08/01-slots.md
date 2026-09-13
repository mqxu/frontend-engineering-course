# 8.1 插槽

## 一个写了两遍的弹窗组件

第七周你做了一个 `ConfirmDialog.vue`，用来做二次确认。用了没几天，需求来了：

- 活动列表页要问：“确定下架这个活动吗？”
- 报名审核页要问：“确定通过这条报名吗？将通过后名额自动扣减。”
- 场次管理页要问：“确定删除这个场次吗？”而且删除后要显示一个红色的警告图标。

你打开组件一看，里面写的是：

```vue [src/components/ConfirmDialog.vue（问题版本）]
<template>
  <div class="dialog-mask">
    <div class="dialog">
      <h3>{{ title }}</h3>
      <p>{{ content }}</p>
      <div class="dialog-actions">
        <button @click="$emit('cancel')">取消</button>
        <button @click="$emit('confirm')">确定</button>
      </div>
    </div>
  </div>
</template>
```

`title` 和 `content` 都是字符串 props。第三个需求就卡住了：要显示一个红色图标，
字符串里塞不进一个图标组件。你只能再加一个 `showWarning` 布尔 prop，
下次再要“自定义按钮文案 + 自定义图标位置”，props 会越加越多。

**问题出在哪？** 这个组件的“内容”是写死的结构，只留了两个字符串的口子。
使用它的人想要控制的其实不是两个字符串，而是**弹窗中间那一整块界面**。

插槽就是为这件事准备的：**组件留出一块位置，内容由使用它的人来填。**

## 默认插槽

最简单的形式。组件里用 `<slot>` 占位，使用时把内容写在组件标签中间：

```vue [src/components/AppCard.vue]
<template>
  <div class="card">
    <slot />
  </div>
</template>
```

```vue [使用方]
<template>
  <AppCard>
    <h3>春季运动会</h3>
    <p>报名截止时间：3 月 20 日</p>
  </AppCard>
</template>
```

`<AppCard>` 标签中间的所有内容会替换掉组件里的 `<slot />`。这个位置叫**默认插槽**
（也叫匿名插槽），因为一个组件只能有一个。

::: tip 插槽内容是在哪一层编译的
关键概念：**插槽内容在父组件的作用域里编译，但渲染在子组件的位置上。**

意思是，写在 `<AppCard>` 中间的内容，能访问父组件的数据，不能访问 `AppCard` 内部的数据：

```vue [使用方 —— 内容能访问父组件的 activity]
<AppCard>
  <h3>{{ activity.title }}</h3>
</AppCard>
```

这里的 `activity` 来自使用方的组件，不是 `AppCard` 里的。这一点在讲作用域插槽时会反过来用到。
:::

## 具名插槽

一个组件常常有好几块位置。比如卡片有头部、主体、底部：

```vue [src/components/AppCard.vue]
<template>
  <div class="card">
    <header class="card-head">
      <slot name="header" />
    </header>

    <div class="card-body">
      <slot />
    </div>

    <footer class="card-foot">
      <slot name="footer" />
    </footer>
  </div>
</template>
```

使用时用 `<template #名字>` 指定往哪个位置填：

```vue [使用方]
<template>
  <AppCard>
    <template #header>
      <h3>春季运动会</h3>
    </template>

    <!-- 没写名字的内容进默认插槽 -->
    <p>报名截止时间：3 月 20 日</p>

    <template #footer>
      <button @click="edit">编辑活动</button>
    </template>
  </AppCard>
</template>
```

`#header` 是 `v-slot:header` 的简写，两种写法等价。**推荐用简写**，`.vue` 文件里更清爽。

写起来像不像 props 里面每一块都是？区别在于：props 只能传值，插槽传的是一整段模板，
里面可以有标签、有组件、有事件绑定。

::: warning 顺序不敏感
具名插槽的填入顺序不影响渲染位置 —— 渲染位置由子组件模板里 `<slot name="xxx">` 的位置决定。
上面例子里 `#footer` 写在最后，但如果子组件把它放在最前面，它就会渲染在最前面。
:::

## 后备内容

插槽可以不填。不填的时候显示什么？在 `<slot>` 标签中间写默认内容即可：

```vue [src/components/AppCard.vue]
<template>
  <div class="card">
    <header class="card-head">
      <slot name="header">
        <!-- 不填 #header 时，显示这段 -->
        <span>未命名卡片</span>
      </slot>
    </header>
    <slot />
  </div>
</template>
```

用到“可选区域”时会很省事。比如一个带操作栏的列表容器，默认不显示操作栏，
传了 `#actions` 才显示 —— 不用再写一个 `v-if`。

## 作用域插槽：把数据交给父级模板

前面说过，插槽内容在父组件作用域编译，拿不到子组件的数据。那如果**子组件手里有数据，
但显示方式想交给父组件决定**呢？

典型场景是表格。子组件负责“有哪些行、有哪些列的数据”，父组件负责“每一列显示成什么样”。
子组件在 `<slot>` 上把数据传出去：

```vue [src/components/DataTable.vue]
<script setup>
defineProps({
  rows: { type: Array, default: () => [] }
})
</script>

<template>
  <table class="data-table">
    <tbody>
      <tr v-for="(row, index) in rows" :key="row.id">
        <!-- 把行数据与行号通过插槽送出去 -->
        <slot name="row" :row="row" :index="index" />
      </tr>
    </tbody>
  </table>
</template>
```

使用方用 `#row="slotProps"` 接收，`slotProps` 是一个对象，里面的字段就是子组件传出来的：

```vue [使用方 —— 每一列怎么显示由父组件决定]
<template>
  <DataTable :rows="activities">
    <template #row="{ row, index }">
      <td>{{ index + 1 }}</td>
      <td>{{ row.title }}</td>
      <td>
        <span :class="['tag', row.status]">{{ statusText(row.status) }}</span>
      </td>
      <td>{{ row.signupCount }} / {{ row.capacity }}</td>
    </template>
  </DataTable>
</template>
```

这里的 `#row="{ row, index }"` 用的是对象解构。数据是从子组件“推”到父组件模板里的，
所以叫**作用域插槽**。

::: tip 一句话记住方向
- **普通插槽**：父组件把结构“送进去”。
- **作用域插槽**：子组件把数据“送出来”，父组件接着这份数据画结构。

表格的通用组件几乎全靠作用域插槽做“列自定义”。这也是 Element Plus 的 `<el-table-column>`
背后的原理。
:::

多个插槽时也可以分别传数据：

```vue [子组件：给不同插槽传不同的数据]
<template>
  <div class="list">
    <slot name="head" :total="rows.length" />
    <slot v-for="item in rows" :key="item.id" :item="item" />
    <slot name="foot" :total="rows.length" :page="page" />
  </div>
</template>
```

## 动态插槽名

插槽名可以是一个变量：

```vue [使用方：按条件决定往哪个插槽填]
<template>
  <AppCard>
    <template #[slotName]>
      <span>内容</span>
    </template>
  </AppCard>
</template>
```

`slotName` 是组件里的一个 `ref`，值可以是 `'header'`、`'footer'`。
这种写法在“同一份内容要按不同状态放进不同区域”时有用，但**日常开发用得少**，
了解即可。别为了用而用 —— 能写清楚的静态名就别搞成动态的。

## 插槽与 props 的分工

回到最开始那个问题。判断标准整理成一张表：

| 你要传的东西 | 用哪个 | 例子 |
| --- | --- | --- |
| 一个值（字符串、数字、布尔、对象） | props | `title="活动列表"`、`:total="86"` |
| 一段界面 / 含标签的内容 | 插槽 | 弹窗主体、卡片底部按钮 |
| 子组件有数据、显示方式要外部定 | 作用域插槽 | 表格列、树节点、下拉选项 |
| 一组配置项，值固定 | props | `size="small"`、`type="primary"` |

有个简单口诀：**能写成一个等号的，用 props；需要写一对标签的，用插槽。**

再看 `ConfirmDialog` 改造后的样子：

```vue [src/components/ConfirmDialog.vue]
<script setup>
defineProps({
  title: { type: String, default: '请确认' },
  confirmText: { type: String, default: '确定' },
  loading: { type: Boolean, default: false }
})

defineEmits(['confirm', 'cancel'])
</script>

<template>
  <div class="dialog-mask">
    <div class="dialog">
      <h3>{{ title }}</h3>

      <!-- 主体内容交给使用者决定，不填就走默认 -->
      <div class="dialog-body">
        <slot>这一操作不可撤销，请确认。</slot>
      </div>

      <div class="dialog-actions">
        <button class="btn-plain" @click="$emit('cancel')">取消</button>
        <button class="btn-primary" :disabled="loading" @click="$emit('confirm')">
          {{ loading ? '处理中…' : confirmText }}
        </button>
      </div>
    </div>
  </div>
</template>
```

三个页面各自填自己的内容：

```vue [展示红色警告图标（场次删除）]
<ConfirmDialog title="删除场次" confirm-text="删除" @confirm="remove">
  <p class="danger">
    <WarningIcon />
    删除后已报名的学生将收到通知，且无法恢复。
  </p>
</ConfirmDialog>
```

```vue [展示名额提示（报名通过）]
<ConfirmDialog title="通过报名" confirm-text="通过" @confirm="approve">
  <p>通过后该生占用的名额为 {{ used + 1 }} / {{ capacity }}，超过上限会自动关闭报名入口。</p>
</ConfirmDialog>
```

同一个组件，三种内容，没有多写一个 prop。

## 实战：可配置列的活动表格

把作用域插槽用在一个真实场景上 —— 活动列表的表格，列可以按页面配置。

先写表格主体，它只负责“把行列出来”，不关心列怎么显示：

```vue [src/components/ActivityTable.vue]
<script setup>
defineProps({
  // 每一行是一条活动
  rows: { type: Array, required: true },
  // 加载中，父组件控制
  loading: { type: Boolean, default: false }
})
</script>

<template>
  <table class="activity-table">
    <thead>
      <tr>
        <!-- 表头由父组件决定，它想显示几列就显示几列 -->
        <slot name="head" />
      </tr>
    </thead>
    <tbody>
      <tr v-if="loading">
        <td colspan="9" class="empty">加载中…</td>
      </tr>
      <tr v-else-if="rows.length === 0">
        <td colspan="9" class="empty">还没有活动，先去发布一个</td>
      </tr>
      <template v-else>
        <tr v-for="(row, index) in rows" :key="row.id">
          <slot name="row" :row="row" :index="index" />
        </tr>
      </template>
    </tbody>
  </table>
</template>
```

注意这里留了两个插槽：`#head` 和 `#row`，都把数据往外送。父组件这样用：

```vue [usage: 活动列表页]
<script setup>
import { ref } from 'vue'
import ActivityTable from '@/components/ActivityTable.vue'

const activities = ref([])
const loading = ref(true)

const columns = [
  { key: 'title', label: '活动标题' },
  { key: 'type', label: '类型' },
  { key: 'capacity', label: '名额' },
  { key: 'deadline', label: '报名截止' },
  { key: 'status', label: '状态' }
]

const statusText = {
  draft: '草稿',
  open: '报名中',
  closed: '报名截止',
  ended: '已结束',
  offline: '已下架'
}
</script>

<template>
  <ActivityTable :rows="activities" :loading="loading">
    <template #head>
      <th v-for="col in columns" :key="col.key">{{ col.label }}</th>
      <th>操作</th>
    </template>

    <template #row="{ row, index }">
      <td>{{ index + 1 }}</td>
      <td>{{ row.title }}</td>
      <td>{{ row.type }}</td>
      <td>{{ row.signupCount }} / {{ row.capacity }}</td>
      <td>{{ row.deadline }}</td>
      <td>
        <span :class="['tag', row.status]">{{ statusText[row.status] }}</span>
      </td>
      <td>
        <RouterLink :to="`/activities/${row.id}`">详情</RouterLink>
      </td>
    </template>
  </ActivityTable>
</template>
```

现在换一个页面 —— 报名审核页。它用的还是 `ActivityTable`，但列不一样，
而且“名额”列要突出显示剩余名额：

```vue [usage: 报名审核页 —— 换一套列]
<template>
  <ActivityTable :rows="pending">
    <template #head>
      <th>学生</th>
      <th>学号</th>
      <th>报名时间</th>
      <th>剩余名额</th>
      <th>操作</th>
    </template>

    <template #row="{ row }">
      <td>{{ row.studentName }}</td>
      <td>{{ row.studentNo }}</td>
      <td>{{ row.createdAt }}</td>
      <td>
        <span :class="{ danger: row.remaining <= 3 }">{{ row.remaining }}</span>
      </td>
      <td>
        <button @click="approve(row)">通过</button>
        <button @click="reject(row)">驳回</button>
      </td>
    </template>
  </ActivityTable>
</template>
```

`ActivityTable` 一行代码没改，两个页面各自决定列。这就是作用域插槽的价值：
**把“数据来源”和“呈现方式”拆开，各自演进。**

::: details 为什么不让 ActivityTable 直接接收 columns 配置
你也可以把列定义做成 props，让表格用 `v-for` 渲染单元格。但一旦某一列要显示按钮、
要条件渲染两种样式、要接一个点击事件，配置就会变得复杂：要么在配置里写渲染函数，
要么给配置加一堆 `type: 'button'` 之类的开关。

**插槽的做法是把模板的控制权完全交出去**，支持任何复杂内容，不需要预先设计每一种列
的形态。表格这种“列千变万化”的场景，插槽更合适。
:::

## 小结

- 用 `<slot>` 留位、用组件标签中间的内容填位，这叫默认插槽。
- 多区域用 `<slot name="xxx">`，使用方用 `#xxx` 填；简写 `#` 等价于 `v-slot:`。
- 在 `<slot>` 里写内容就是后备内容，不填时显示。
- 作用域插槽把子组件的数据通过 `:字段名="值"` 送出来，父组件用 `#名字="{ 字段 }"` 接收，
  表格列自定义全靠它。
- 传值用 props，传结构用插槽；子组件出数据、父组件出模板用作用域插槽。
- 动态插槽名 `#[变量]` 可用，但别为了炫技而用。

## 常见坑

::: details 坑 1：把具名插槽和默认插槽混着填，结果顺序乱了
现象：写了 `#header` 和一段没名字的内容，渲染出来位置对不上。

原因：默认插槽的内容必须**不包在 `<template>` 里**，而具名插槽必须包在 `<template #名字>` 里。
一旦你把默认内容也包进了某个 `<template>`，它就不再进默认插槽了。

处理：默认内容直接写在组件标签中间，具名内容用 `<template #名字>` 包起来，两者分开。
:::

::: details 坑 2：在作用域插槽里想访问子组件的数据，写成了父组件的变量
现象：`#row="{ row }"` 里用了 `row`，但父组件刚好也有一个 `row`，结果拿到的是父组件的。

原因：`{ row }` 是解构子组件传出来的对象，它会**遮蔽**外层的同名变量。

处理：给接收的字段换个名字，`#row="{ row: item }"`，或者给父组件的变量换名。别用同名。
:::

::: details 坑 3：以为插槽能拿到子组件的所有数据
现象：只写了 `<slot name="row" :row="row" />`，却想在父组件用 `index`。

原因：插槽只送出你**显式绑定**上去的属性，没绑就没有。

处理：需要什么就在 `<slot>` 上绑什么，`:row="row" :index="index"`。绑多了会让接口变模糊，
只送使用者真正需要的。
:::

::: details 坑 4：`<slot>` 里写了默认内容，但还是空白的
现象：后备内容不生效。

原因：使用方写了一个空的 `<template #header></template>`，这也算“填了”，只是填的是空内容。

处理：要么在使用方删掉这个空的 `<template>`，要么在子组件里用 `v-if` 判断。记住：
**“填了空内容”和“没填”是两回事。**
:::

## 课后练习

::: details 练习 1：把 ConfirmDialog 改成插槽版
把你自己写的二次确认弹窗改成“主体用默认插槽、底部按钮区可用具名插槽覆盖”的结构。
要求：不覆盖底部时，显示默认的取消 / 确定按钮；覆盖时，完全用使用者提供的按钮。

**思路**：底部写成 `<slot name="footer"><button>取消</button><button>确定</button></slot>`。
覆盖时用 `<template #footer>` 传入自己的按钮。想想这样一来“确定按钮的 loading 状态”
该由谁控制 —— 这是设计接口时要做的取舍。
:::

::: details 练习 2：用作用域插槽做活动卡片列表
写一个 `ActivityList.vue`，接收 `activities` 数组，用默认插槽让父组件决定“一条活动怎么显示”。
再写一个页面用它，父组件通过 `#default="{ item }"` 拿到单条活动并渲染卡片。

**思路**：子组件只写 `<div class="list"><slot v-for="item in activities" :key="item.id" :item="item" /></div>`。
注意 `v-for` 和 `<slot>` 一起用时的写法，以及为什么 `:key` 要放在 `<slot>` 上。
:::

::: details 练习 3：给表格加一个“空状态插槽”
在实战的 `ActivityTable` 上，把写死的“还没有活动，先去发布一个”改成槽位，
允许父组件自定义空状态（比如放一个插画和一个“发布活动”按钮）。

**思路**：空分支里写 `<slot name="empty">默认文案</slot>`。想一想：这个插槽需要往外送数据吗？
（提示：如果父组件想知道“总共几条、为什么空”，可能要把 `total` 送出去。）
:::

---

上一节：[单元导学](/unit08/) ·
下一节：[8.2 依赖注入](/unit08/02-provide-inject)
