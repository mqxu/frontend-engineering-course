# 案例 02 · 可排序筛选的数据表格

::: tip 这是什么
**基础档案例，课堂演练内容。** 用校园活动数据做一张带搜索、筛选、排序、分页、
多选的数据表格，不使用任何 UI 组件库。

这个案例的核心是**派生链**：筛选 → 排序 → 分页，每一步都是一个计算属性。
:::

## 需求与派生链设计

需求清单：

| 功能 | 说明 |
| --- | --- |
| 关键词搜索 | 标题或组织者里包含关键词 |
| 状态筛选 | 全部 / 草稿 / 报名中 / 报名截止 / 已结束 |
| 表头排序 | 点表头在三态之间循环：升序 → 降序 → 取消 |
| 分页 | 每页 5 条，显示总条数和当前页 |
| 全选半选 | 表头复选框能全选当前页，部分选中时显示半选态 |
| 四态 | 加载中、出错、空数据、有数据 |

::: warning 先设计派生链，再写代码
这个案例有四个输入（关键词、状态筛选、排序字段、页码）和四层输出。
**顺序画错了，代码会变成一团乱麻。**

```text
原始状态                 派生一              派生二            派生三
────────────────────────────────────────────────────────────────────→
keyword      ┐
statusFilter ┴→ filteredList ──→ sortedList ──→ pagedList ──→ 表格渲染
                                                   │
                                                   └→ pagedIds ──→ 全选半选
sortKey      ┐
sortOrder    ┴───────────────────┘
page ──────────────────────────────────────────────┘
```

**关键点：只有最左边那一列是 `ref`，右边全部是 `computed`。**

这样设计之后，不需要任何一个 `watch` 去“通知下一步”。任何一个输入变了，
Vue 会自己沿着这条链把受影响的部分重算一遍。
:::

## 第一步：数据与表格骨架

```vue [src/views/ActivityTableView.vue]
<script setup>
import { ref } from 'vue'

const activities = ref([
  { id: 1, title: '2026 春季校园歌手大赛', type: '文艺', organizer: '学生会文艺部', deadline: '2026-09-20', capacity: 200, status: 'signing' },
  { id: 2, title: '程序设计竞赛校内选拔', type: '学术', organizer: '计算机学院', deadline: '2026-09-18', capacity: 120, status: 'closed' },
  { id: 3, title: '校园马拉松志愿者招募', type: '志愿', organizer: '青年志愿者协会', deadline: '2026-09-15', capacity: 60, status: 'signing' },
  { id: 4, title: '新生篮球赛', type: '体育', organizer: '体育部', deadline: '2026-09-28', capacity: 96, status: 'draft' },
  { id: 5, title: '开源技术分享会', type: '学术', organizer: '计算机学院', deadline: '2026-09-12', capacity: 150, status: 'finished' },
  { id: 6, title: '摄影作品征集', type: '文艺', organizer: '社团联合会', deadline: '2026-10-08', capacity: 300, status: 'signing' },
  { id: 7, title: '实验室开放日', type: '学术', organizer: '实验中心', deadline: '2026-09-25', capacity: 80, status: 'signing' },
  { id: 8, title: '秋季排球联赛', type: '体育', organizer: '体育部', deadline: '2026-10-01', capacity: 144, status: 'closed' },
  { id: 9, title: '校园辩论赛', type: '学术', organizer: '辩论社', deadline: '2026-09-30', capacity: 64, status: 'draft' },
  { id: 10, title: '手作市集', type: '文艺', organizer: '社团联合会', deadline: '2026-10-12', capacity: 40, status: 'signing' },
  { id: 11, title: '图书馆志愿服务', type: '志愿', organizer: '青年志愿者协会', deadline: '2026-09-22', capacity: 30, status: 'finished' },
  { id: 12, title: '电子竞技友谊赛', type: '体育', organizer: '学生会活动部', deadline: '2026-10-05', capacity: 128, status: 'signing' }
])

const STATUS_TEXT = {
  draft: '草稿',
  signing: '报名中',
  closed: '报名截止',
  finished: '已结束'
}

// 状态本身的排序顺序（不是按文字排，按业务流转顺序排）
const STATUS_RANK = { draft: 0, signing: 1, closed: 2, finished: 3 }

const STATUS_OPTIONS = [
  { value: '', label: '全部状态' },
  { value: 'draft', label: '草稿' },
  { value: 'signing', label: '报名中' },
  { value: 'closed', label: '报名截止' },
  { value: 'finished', label: '已结束' }
]

// 列定义：哪些可排序，直接写在数据里
const COLUMNS = [
  { key: 'title', label: '活动标题', sortable: true },
  { key: 'type', label: '类型', sortable: true },
  { key: 'organizer', label: '组织者', sortable: true },
  { key: 'deadline', label: '报名截止', sortable: true },
  { key: 'capacity', label: '名额', sortable: true },
  { key: 'status', label: '状态', sortable: true }
]
</script>

<template>
  <table class="activity-table">
    <thead>
      <tr>
        <th class="col-check">
          <input type="checkbox" />
        </th>
        <th v-for="col in COLUMNS" :key="col.key">{{ col.label }}</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="activity in activities" :key="activity.id">
        <td><input type="checkbox" /></td>
        <td>{{ activity.title }}</td>
        <td>{{ activity.type }}</td>
        <td>{{ activity.organizer }}</td>
        <td>{{ activity.deadline }}</td>
        <td>{{ activity.capacity }}</td>
        <td>{{ STATUS_TEXT[activity.status] }}</td>
      </tr>
    </tbody>
  </table>
</template>
```

**注意 `:key="activity.id"`。** 表格数据会被筛选、排序、翻页，
用索引做 key 会出现“翻到第二页，行内输入框里还留着第一页的内容”这类问题，
见 [5.4](/unit05/04-list)。

## 第二步：筛选（搜索 + 状态）

```js
const keyword = ref('')
const statusFilter = ref('')

const filteredList = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  const status = statusFilter.value

  return activities.value.filter((activity) => {
    const hitKeyword =
      !kw ||
      activity.title.toLowerCase().includes(kw) ||
      activity.organizer.toLowerCase().includes(kw)

    const hitStatus = !status || activity.status === status

    return hitKeyword && hitStatus
  })
})
```

两个细节：

**一、两个条件用“命中即通过”的写法。** `!kw || ...` 的意思是
“没有关键词，就算命中”。这样两个条件可以自由组合，不用写四层 `if`。

**二、搜索前 `toLowerCase()`。** 用户输入 `vue` 应该能匹配 `Vue`。
输入也 `trim` 一下，避免首尾空格导致搜不到。

::: tip 输入框的即时搜索要不要防抖
数据在本地（不上接口）时不需要 —— 12 条数据的 `filter` 是微秒级的。
**等换成接口请求时再加防抖**，写法见 [5.2 的实战部分](/unit05/02-watch)。

**不要提前优化。** 本地筛选加防抖反而会让输入显得卡顿。
:::

## 第三步：三态排序

排序要做三件事：记录当前排哪个字段、哪个方向、点表头时切换状态。

```js
const sortKey = ref('')        // 当前排序字段，空表示不排序
const sortOrder = ref('')      // 'asc' | 'desc' | ''

function toggleSort(key) {
  // 点了新的一列：从升序开始
  if (sortKey.value !== key) {
    sortKey.value = key
    sortOrder.value = 'asc'
    return
  }
  // 同一列：升序 → 降序
  if (sortOrder.value === 'asc') {
    sortOrder.value = 'desc'
    return
  }
  // 同一列：降序 → 取消排序
  if (sortOrder.value === 'desc') {
    sortKey.value = ''
    sortOrder.value = ''
  }
}

function sortIndicator(key) {
  if (sortKey.value !== key || !sortOrder.value) return '↕'
  return sortOrder.value === 'asc' ? '↑' : '↓'
}

function compareBy(a, b, key) {
  if (key === 'capacity') return a.capacity - b.capacity
  if (key === 'status') return STATUS_RANK[a.status] - STATUS_RANK[b.status]
  return String(a[key]).localeCompare(String(b[key]), 'zh-CN')
}

const sortedList = computed(() => {
  if (!sortKey.value || !sortOrder.value) return filteredList.value

  const dir = sortOrder.value === 'asc' ? 1 : -1
  const key = sortKey.value

  return filteredList.value.toSorted((a, b) => compareBy(a, b, key) * dir)
})
```

四个要注意的地方：

**一、三态循环的顺序要固定。** 换列 → 升序；同一列 → 降序 → 取消。
用户点三次回到“不排序”，符合直觉。

**二、用 `toSorted` 而不是 `sort`。** `sort` 会**就地修改数组**，
而 `filteredList` 是计算属性的结果，直接 `sort` 会改掉它，
导致下一次筛选时数据顺序莫名其妙。`toSorted` 返回新数组，不改原数组。

**三、状态要按业务顺序排，不能按文字排。** 按文字排的结果是
“报名中、已结束、报名截止、草稿”这种没有意义的顺序。
用 `STATUS_RANK` 映射成数字再比较，才是“草稿 → 报名中 → 报名截止 → 已结束”。

**四、数字和字符串要分开处理。** `capacity` 是数字，直接相减；
`deadline` 是 `YYYY-MM-DD` 格式的字符串，按字典序比较**恰好等于**按时间先后比较
（这是这个日期格式的好处）；中文文字用 `localeCompare` 才能按拼音排。

::: warning 中文排序要用 localeCompare
```js
// ✗ 按字符编码排，中文结果是乱的
list.sort((a, b) => a.title > b.title ? 1 : -1)

// ✓ 按拼音排
list.sort((a, b) => a.title.localeCompare(b.title, 'zh-CN'))
```

`localeCompare` 的效率比直接比较低。数据量大（上万条）时，
可以考虑在数据加载阶段预先算好排序用的字段。**但不要凭感觉优化，
先用最直观的写法，遇到卡顿再用工具测。**
:::

表头这样写：

```vue
<template>
  <thead>
    <tr>
      <th class="col-check">
        <input type="checkbox" />
      </th>
      <th
        v-for="col in COLUMNS"
        :key="col.key"
        :class="{ 'is-sortable': col.sortable, 'is-sorted': sortKey === col.key }"
        @click="col.sortable && toggleSort(col.key)"
      >
        {{ col.label }}
        <span v-if="col.sortable" class="sort-indicator">{{ sortIndicator(col.key) }}</span>
      </th>
    </tr>
  </thead>
</template>
```

注意 `@click="col.sortable && toggleSort(col.key)"` 这一句：
不可排序的列点上去什么都不做。**用一个表达式处理，不用写 `if`。**

## 第四步：分页

分页要注意一个容易忽略的问题：**筛选之后，当前页码可能越界。**

比如现在在第 3 页，然后搜索一个只有 2 条结果的关键词 ——
第 3 页已经不存在了，表格会是空的。

常见的错误做法是加一个 `watch`，在筛选条件变化时把页码重置为 1：

```js
// ✗ 能跑，但多了一处需要维护的同步逻辑
watch([keyword, statusFilter, sortKey, sortOrder], () => {
  page.value = 1
})
```

**更好的做法是让“当前页”变成一个派生值**，永远不越界：

```js
const page = ref(1)
const pageSize = ref(5)

const totalPages = computed(() =>
  Math.max(1, Math.ceil(sortedList.value.length / pageSize.value))
)

// 真正用于切片的页码：永远不超过总页数
const currentPage = computed(() => Math.min(page.value, totalPages.value))

const pagedList = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return sortedList.value.slice(start, start + pageSize.value)
})

const filteredCount = computed(() => sortedList.value.length)
const rangeText = computed(() => {
  if (filteredCount.value === 0) return '共 0 条'
  const start = (currentPage.value - 1) * pageSize.value + 1
  const end = Math.min(currentPage.value * pageSize.value, filteredCount.value)
  return `第 ${start} - ${end} 条，共 ${filteredCount.value} 条`
})
```

**这样写，整条派生链里一个 `watch` 都不需要。**
筛选条件变了 → `sortedList` 变了 → `totalPages` 变了 → `currentPage` 被夹到合法范围内 →
`pagedList` 自动变成新结果。**没有“通知”，只有“重算”。**

::: details 为什么“重置页码”用 watch 不好
两个原因：

1. **多一份需要同步的状态。** 以后加一个筛选条件，就要记得把新的变量
   也加进 `watch` 的依赖数组。漏了就是 bug。
2. **会多渲染一次。** `watch` 先触发、把 `page` 改成 1，
   然后再触发一次渲染。而 `computed` 版本的 `currentPage` 是同一个渲染周期里算出来的。

**这不是“watch 不好”，而是“这件事本来就不是副作用”。**
“保证页码在合法范围内”是一个**计算**问题，不是**动作**问题。

**判断标准：如果一段逻辑的产物是一个值，用 `computed`；如果产物是一个动作（发请求、写存储、操作 DOM），用 `watch`。**
:::

分页控制的模板：

```vue
<template>
  <div class="pager">
    <button :disabled="currentPage === 1" @click="page = currentPage - 1">上一页</button>

    <button
      v-for="p in totalPages"
      :key="p"
      :class="{ 'is-active': p === currentPage }"
      @click="page = p"
    >
      {{ p }}
    </button>

    <button :disabled="currentPage === totalPages" @click="page = currentPage + 1">下一页</button>

    <span class="pager__range">{{ rangeText }}</span>
  </div>
</template>
```

::: warning 页数很多时不能把页码全列出来
这里能这么写，是因为只有 12 条数据、最多 3 页。
真实项目里几百页的话，要把中间省略成 `…`，只显示当前页前后几页。
写法和“分页算法”有关，见[单元 11 的列表页标准做法](/unit11/04-list-page)。
:::

## 第五步：全选与半选

全选有几个容易写错的地方：**全选的是哪一页？半选态怎么算？**

```js
const selectedIds = ref([])

// 当前页的所有 id
const pagedIds = computed(() => pagedList.value.map((a) => a.id))

const selectedCount = computed(() => selectedIds.value.length)

// 当前页是不是全部选中
const isAllSelected = computed(
  () => pagedIds.value.length > 0 && pagedIds.value.every((id) => selectedIds.value.includes(id))
)

// 半选：当前页有选中、但不是全部选中
const isIndeterminate = computed(() => {
  const hitCount = pagedIds.value.filter((id) => selectedIds.value.includes(id)).length
  return hitCount > 0 && hitCount < pagedIds.value.length
})

function toggleSelectAll(checked) {
  if (checked) {
    // 并集：保留其他页已选的，加上当前页全部
    selectedIds.value = [...new Set([...selectedIds.value, ...pagedIds.value])]
  } else {
    // 从选中集合里去掉当前页的
    selectedIds.value = selectedIds.value.filter((id) => !pagedIds.value.includes(id))
  }
}

function toggleRow(id, checked) {
  if (checked) {
    selectedIds.value = [...selectedIds.value, id]
  } else {
    selectedIds.value = selectedIds.value.filter((x) => x !== id)
  }
}

function clearSelection() {
  selectedIds.value = []
}
```

模板里的表头复选框：

```vue
<template>
  <th class="col-check">
    <input
      type="checkbox"
      :checked="isAllSelected"
      :indeterminate="isIndeterminate"
      @change="toggleSelectAll($event.target.checked)"
    />
  </th>
</template>
```

**四个设计要点：**

**一、`selectedIds` 存 id，不存整条数据。** 存 id 之后，
即使列表数据重新请求、对象引用全变了，选中状态依然有效。
存对象的话，刷新数据后 `includes` 就找不到了。

**二、全选只作用于当前页。** 这是分页表格的通行做法。
如果要做“跨页全选所有筛选结果”，选择逻辑会复杂很多，
而且用户容易误操作。**默认按当前页全选，符合大多数产品的预期。**

**三、并集用 `Set` 去重。** 用户先勾了第 2 页的两条，回到第 1 页全选，
这时不能有重复 id。`new Set([...])` 一行解决。

**四、半选态用 `:indeterminate`，不是 CSS。**
原生复选框有一个 `indeterminate` 属性表示第三种状态，Vue 可以直接绑定。

::: details 为什么半选要用 `isAllSelected` 和 `isIndeterminate` 两个计算属性
因为它们回答的是两个不同的问题：

- `isAllSelected`：**全部**选了吗？（控制 `checked`）
- `isIndeterminate`：**部分**选了吗？（控制半选态）

写成 `pagedIds.every(...)` 和 `pagedIds.some(...)` 也可以，
但 `some` 在“全选”时也是 `true`，会和 `checked` 冲突。
所以半选必须是“有选中 **且** 没全选”。

**这类“两个状态量表达三种情况”的场景，判断条件一定要互斥。**
:::

## 第六步：把四态补上

表格页也是数据页，要有[四态](/unit05/05-four-states)：

```js
const loading = ref(false)
const error = ref('')

async function loadActivities() {
  loading.value = true
  error.value = ''
  try {
    const res = await fetch('/api/activity/list')
    if (!res.ok) throw new Error(`服务返回 ${res.status}`)
    activities.value = (await res.json()).list ?? []
  } catch (e) {
    error.value = '活动列表加载失败，请检查网络后重试'
    activities.value = []
    console.error(e)     // 技术细节留给控制台
  } finally {
    loading.value = false
  }
}

onMounted(loadActivities)
```

模板里按固定顺序判断：

```vue
<template>
  <section class="activity-page">
    <div v-if="loading" class="state">正在加载…</div>

    <div v-else-if="error" class="state state--error">
      <p>{{ error }}</p>
      <button @click="loadActivities">重试</button>
    </div>

    <!-- 空数据要区分“系统没有”和“筛没了” -->
    <div v-else-if="activities.length === 0" class="state">
      <p>还没有活动</p>
      <RouterLink to="/activities/new">创建活动</RouterLink>
    </div>

    <div v-else-if="filteredList.length === 0" class="state">
      <p>没有符合条件的活动，试试放宽筛选条件。</p>
      <button @click="resetFilters">清除筛选</button>
    </div>

    <template v-else>
      <!-- 工具栏 + 表格 + 分页 -->
    </template>
  </section>
</template>
```

```js
function resetFilters() {
  keyword.value = ''
  statusFilter.value = ''
}
```

**注意两个空状态的位置**：`activities.length === 0`（系统里真没有）
和 `filteredList.length === 0`（筛没了）必须分开判断，引导动作也不同。

## 小结

- 先画派生链再写代码：`keyword` / `statusFilter` / `sortKey` / `page` 是源头，
  其余全是 `computed`。
- 筛选：多个条件用“命中即通过”的写法（`!kw || 匹配`），可以自由组合。
- 排序：三态循环（换列升序 → 同列降序 → 取消）；用 `toSorted` 不动原数组；
  状态要按业务顺序排，中文用 `localeCompare`。
- 分页：**用 `currentPage` 计算属性夹住页码，替代 `watch` 重置页码**；整条链零 `watch`。
- 半选：`isAllSelected`（控制 `checked`）和 `isIndeterminate`（控制半选态）
  两个判断必须互斥。
- 选择状态存 id 不存对象；全选按当前页；用 `Set` 去重。
- 列表页要有四态，空数据要区分“系统没有”和“筛没了”。

## 常见坑

::: details 坑 1：用 `sort` 而不是 `toSorted`，筛选结果顺序被改乱
```js
// ✗ 就地修改了 filteredList 返回的数组
const sortedList = computed(() => filteredList.value.sort(cmp))
```

**现象**：切换筛选条件时，结果顺序莫名其妙和上一次一样；
或者取消排序之后顺序没有恢复。

**原因**：`sort` 修改的是 `filteredList` 内部那个数组，
而它是计算属性缓存的返回值 —— 被就地改掉之后，缓存的内容也变了。

**怎么处理**：用 `toSorted`，或者 `[...filteredList.value].sort(cmp)`。

**判断规则：计算属性的返回值只读，不要在它上面做任何就地修改。**
:::

::: details 坑 2：页码越界后表格空白
```js
// ✗ 直接用 page 切片
const pagedList = computed(() => sortedList.value.slice((page.value - 1) * 5, page.value * 5))
```

**现象**：在第 3 页搜索一个只有 2 条结果的关键词，表格空白，
但底部还显示“第 3 页”。

**原因**：`page` 还是 3，但总页数只有 1。

**怎么处理**：加一个 `currentPage` 计算属性夹住范围，
所有用到页码的地方都用它。

**这个坑的通用形式：用户输入（这里是页码）可能超出数据允许的范围，
要用计算属性把它夹回合法区间。**
:::

::: details 坑 3：全选按钮的勾选状态和实际选中不一致
```js
// ✗ 用单向的“有选中”判断
const isAllSelected = computed(() => pagedIds.value.some((id) => selectedIds.value.includes(id)))
```

**现象**：只勾了一条，表头复选框也变成勾选状态。

**原因**：`some` 只要有一条命中就返回 `true`。

**怎么处理**：全选用 `every`，半选用“一部分（不是全部）”的判断。
**两个条件必须互斥，才不会同时为真。**
:::

::: details 坑 4：`selectedIds` 里留下了已经被删除的活动 id
**现象**：删除了几条活动之后，底部还显示“已选 3 项”，点批量操作时报错“找不到记录”。

**原因**：`selectedIds` 是一个独立的集合，数据变化时它不会自动清理。

**怎么处理**：在数据加载后做一次清理：

```js
function pruneSelection() {
  const validIds = new Set(activities.value.map((a) => a.id))
  selectedIds.value = selectedIds.value.filter((id) => validIds.has(id))
}
```

在 `loadActivities` 成功之后调一次。

**注意**：这是**副作用**（要改另一个状态），所以适合放在数据加载函数里，
不适合做成计算属性 —— 计算属性只读不写。
:::

## 课后练习

::: details 练习 1：加一个“每页条数”选择
加一个下拉框，可选 5 / 10 / 20 条，切换后重新分页。

要求：
1. `pageSize` 是一个 `ref`；
2. 切换每页条数后，页码不能越界（用 `currentPage` 的机制自动处理，不要加 `watch`）；
3. 底部的“第 x - y 条，共 n 条”要跟着变。

**参考思路**：把 `pageSize` 加进 `totalPages` 和 `pagedList` 的依赖里就行。
`currentPage` 会自动夹住范围，不需要额外的同步代码。

**验证方式**：切到第 3 页，然后把每页条数从 5 改成 20，
确认表格正常显示第一页的内容，且底部页码正确。
:::

::: details 练习 2：加一个“多列排序”
把排序从“单列”扩展成“多列”，比如先按状态排、同状态内再按报名截止排。

要求：
1. 按住 Shift 点击表头时，追加一个排序字段；
2. 表头上显示排序的优先级（1、2）；
3. 取消排序时，只取消当前这一列。

**参考思路**：`sortKey` 从一个字符串变成一个数组，`sortOrder` 也变成数组：
`sortKeys = [{ key: 'status', order: 'asc' }, { key: 'deadline', order: 'desc' }]`。
比较函数改成遍历这个数组，第一个不相等的字段决定结果。

**做完之后对比一下**：单列版本的 `toggleSort` 有 15 行，
多列版本会有多少行？**功能复杂度增长时，代码复杂度增长得更快。**
这也是为什么企业项目里表格会用专门的表格库 —— 但你现在知道它内部在做什么了。
:::

::: details 练习 3：把派生链抽成组合式函数
把筛选、排序、分页、选择这套逻辑抽成 `useTableQuery(sourceList)`，
返回所有状态和操作。

**要求**：组件里不再出现任何 `computed`，只有模板和调用。

**参考思路**：这个组合式函数的参数是数据源（一个 ref 数组），
内部维护关键词、筛选、排序、页码，返回 `pagedList`、`totalPages`、
`isAllSelected` 等。

**抽完之后你会发现**：同一个 `useTableQuery` 可以给报名名单、场次列表、
审核记录三个页面复用。**这就是[单元 8 组合式函数](/unit08/04-composables) 的价值。**
:::

---

上一节：[案例 01 · 增删改查清单](/unit05/06-case-crud) ·
下一节：[单元 5 课后练习](/unit05/practice)
