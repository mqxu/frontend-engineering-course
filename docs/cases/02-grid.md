# 案例 02 · 可排序筛选的数据表格

## 案例要做什么

审核员打开报名记录页面，看到的是几百条报名：谁报的、报的什么活动、什么时间提交的、审核状态是什么。
他需要三件事：**按某一列排序**（比如按提交时间倒序看最新报名）、**按关键字缩小范围**（比如只看某个学生）、
**分页**（一次只看一屏，别刷出一整页滚动条）。

这三件事有一个共同点：**它们都不改变原始数据，只改变“当前看到哪一批”。** 所以本案例的核心不是表格样式，
而是**数据派生的顺序**：原始数据 → 筛选 → 排序 → 分页，一步一层，每层都用 `computed`。

| 知识点 | 用在哪里 | 对应章节 |
| --- | --- | --- |
| `computed` 与缓存 | 筛选、排序、分页三层派生 | [计算属性与缓存](/unit05/01-computed) |
| `computed` 链式派生 | 后一层依赖前一层，不重复计算 | [计算属性与缓存](/unit05/01-computed) |
| `v-for` 与 `:key` | 表头、表体都由配置数组渲染 | [列表渲染与键值](/unit05/04-list) |
| 数组的 `filter` / `sort` / `slice` | 三层派生各自的实现 | [列表渲染与键值](/unit05/04-list) |
| `watch` 的正确用途 | 页码越界修正、筛选后回到第一页 | [侦听器](/unit05/02-watch) |
| 表单绑定 | 搜索框、页码 | [表单绑定](/unit06/03-form-binding) |

::: warning 本案例的一个关键判断
“筛选后的结果”“排序后的结果”“当前页的数据”**都是算出来的，不是存出来的**。
如果你写了 `const filteredList = ref([])` 再用 `watch` 去同步它，说明派生方向反了 ——
这种写法在项目里是 bug 高发区，本案例最后会讲为什么。
:::

## 数据结构与接口设计

一条报名记录：

```js [报名记录的数据结构]
/**
 * 报名记录
 * @typedef {Object} SignupRecord
 * @property {string} id             唯一标识
 * @property {string} studentName    学生姓名
 * @property {string} studentNo      学号
 * @property {string} activityTitle  报名活动的标题
 * @property {string} status         pending | approved | rejected
 * @property {string} submittedAt    提交时间，格式 YYYY-MM-DD HH:mm
 * @property {number} score          初审评分，用于演示数字排序
 */
```

列配置也当成数据来设计。**表格渲染要靠这份配置，不要每一列都手写一个 `<th>`**：

```js [列配置]
const columns = [
  { key: 'studentName', label: '学生', sortable: true },
  { key: 'studentNo', label: '学号', sortable: true },
  { key: 'activityTitle', label: '活动', sortable: false },
  { key: 'status', label: '状态', sortable: true, format: (value) => STATUS_TEXT[value] ?? value },
  { key: 'submittedAt', label: '提交时间', sortable: true }
]
```

这样设计的好处很实际：将来要加一列“报名渠道”，只改这份数组；要做“某几列可排序”，也只改
`sortable` 这个开关，模板不用动。

排序规则用数组表示，**数组顺序就是优先级** —— 这是一切多列排序的基础：

```js [排序规则]
// 数组第一项是主排序，第二项是主排序打平时才生效的次排序
const sortRules = ref([{ key: 'submittedAt', order: 'desc' }])
```

筛选参数与分页参数分开存，因为它们的更新时机不同：

| 状态 | 类型 | 谁改它 |
| --- | --- | --- |
| `keyword` | `ref('')` | 用户在搜索框输入 |
| `page` | `ref(1)` | 用户翻页；筛选变化时要重置 |
| `sortRules` | `ref([...])` | 用户点击表头 |

## 实现步骤

### 步骤 1 · 三层派生：筛选 → 排序 → 分页

`computed` 的优势在这里体现得最清楚：**后一层依赖前一层，任何一层变化，后面的会自动重算，
而且只有真正用到的层才会算。**

```js [三层派生]
// 第一层：筛选
const filtered = computed(() => {
  const text = keyword.value.trim().toLowerCase()
  if (!text) return props.records
  return props.records.filter(
    (row) => row.studentName.toLowerCase().includes(text) || row.studentNo.includes(text)
  )
})

// 第二层：排序（依赖 filtered）
const sorted = computed(() => { /* …… */ })

// 第三层：分页（依赖 sorted）
const pagedRows = computed(() => {
  const start = (page.value - 1) * props.pageSize
  return sorted.value.slice(start, start + props.pageSize)
})
```

**注意第一层里 `if (!text) return props.records` 这一句。** 搜索词为空时直接返回原数组，
不是偷懒 —— 它避免了每次重算都复制一遍几百条数据。别写成 `includes('')`，
那样虽然结果一样，但会白白跑一次遍历。

### 步骤 2 · 筛选：中文和大小写都要照顾到

搜索框里的关键字可能是英文大小写混输，所以比较前统一转小写。姓名是中文，`toLowerCase` 不影响它。

```js [筛选]
const text = keyword.value.trim().toLowerCase()
return props.records.filter(
  (row) => row.studentName.toLowerCase().includes(text) || row.studentNo.includes(text)
)
```

这里有两个容易漏的点：

- `trim()`：用户复制粘贴时末尾常常带空格，不处理就会“明明有这个学生却搜不到”。
- 多字段：搜索通常要覆盖姓名和学号两个字段，用 `||` 连接。

### 步骤 3 · 单列排序：先写一个能比较任意字段的函数

排序的核心是比较函数。难点在于**字段类型不统一**：分数是数字，姓名是中文，时间是字符串。
先把它统一到一个函数里，排序逻辑本身就很短了：

```js [compareValue]
function compareValue(a, b) {
  if (a === b) return 0
  // 空值排在最前面，否则 null 会参与字符串比较，出现奇怪的顺序
  if (a === null || a === undefined) return -1
  if (b === null || b === undefined) return 1
  if (typeof a === 'number' && typeof b === 'number') return a - b
  return String(a).localeCompare(String(b), 'zh-Hans-CN', { numeric: true })
}
```

三个细节值得记住：

| 写法 | 作用 |
| --- | --- |
| `a - b` | 数字比较。写成 `a > b` 也行，但返回布尔值，排序引擎不接受 |
| `localeCompare(..., 'zh-Hans-CN')` | 中文按拼音顺序排，默认按字符编码排出来是乱的 |
| `{ numeric: true }` | 让 `学号 2` 排在 `学号 10` 前面，否则字符串比较会把 `10` 排到 `2` 前面 |

### 步骤 4 · 多列排序：三种点击行为

点击表头时，用户想要的行为有三种，用**是否按住 Shift**和**当前这一列的排序状态**区分：

| 操作 | 期望结果 |
| --- | --- |
| 点一个没排序的列 | 把它设为主排序，升序，**清掉其他规则** |
| 按住 Shift 点一个没排序的列 | 追加为**次排序**，之前的规则保留 |
| 反复点同一列 | 升序 → 降序 → 取消这一列的排序 |

```js [toggleSort]
function toggleSort(key, event) {
  const rules = sortRules.value
  const index = rules.findIndex((rule) => rule.key === key)

  if (index === -1) {
    const next = { key, order: 'asc' }
    // 按住 Shift 追加为次排序，否则替换掉所有规则
    sortRules.value = event.shiftKey ? [...rules, next] : [next]
    return
  }

  const current = rules[index]
  if (current.order === 'asc') {
    sortRules.value = rules.map((rule, i) => (i === index ? { ...rule, order: 'desc' } : rule))
  } else {
    // 第三次点击：取消这一列的排序
    sortRules.value = rules.filter((_, i) => i !== index)
  }
}
```

模板里给有排序规则的列标上序号和箭头，用户才知道“现在是按哪几列排、谁优先”：

```js [sortMark]
function sortMark(key) {
  const index = sortRules.value.findIndex((rule) => rule.key === key)
  if (index === -1) return ''
  const rule = sortRules.value[index]
  const arrow = rule.order === 'asc' ? '↑' : '↓'
  // 多列排序时才需要标出优先级序号
  return sortRules.value.length > 1 ? `${index + 1}${arrow}` : arrow
}
```

多列排序的实现在 `computed` 里：**按规则数组的顺序依次比较，第一个不相等的规则决定顺序。**

```js [多列排序]
const sorted = computed(() => {
  if (sortRules.value.length === 0) return filtered.value
  const list = [...filtered.value] // 复制一份再排
  list.sort((a, b) => {
    for (const rule of sortRules.value) {
      const result = compareValue(a[rule.key], b[rule.key])
      if (result !== 0) return rule.order === 'asc' ? result : -result
    }
    // 所有规则都打平，用 id 兜底，顺序才是稳定可预期的
    return String(a.id).localeCompare(String(b.id))
  })
  return list
})
```

第一行 `[...filtered.value]` 不能省。`Array.prototype.sort` 会**原地修改数组**，
直接 `filtered.value.sort(...)` 改的是上一层 `computed` 返回的数组，属于“在派生层里改数据”，
后面会出问题。

### 步骤 5 · 分页：切片、页码与边界修正

数据量不大时，一次取全量、在前端切页最简单：

```js [客户端分页]
const pageCount = computed(() => Math.max(1, Math.ceil(sorted.value.length / props.pageSize)))

const pagedRows = computed(() => {
  const start = (page.value - 1) * props.pageSize
  return sorted.value.slice(start, start + props.pageSize)
})
```

`Math.max(1, ...)` 是为了兜住“结果为空”的情况 —— 没有数据时也应该显示“第 1 / 1 页”，
而不是“第 1 / 0 页”。

翻页按钮的禁用条件直接写边界：

```vue [翻页按钮]
<button :disabled="page <= 1" @click="page -= 1">上一页</button>
<span>第 {{ page }} / {{ pageCount }} 页</span>
<button :disabled="page >= pageCount" @click="page += 1">下一页</button>
```

**页码越界只能靠 `watch` 修正。这是 `watch` 该出场的少数场景之一。**

前面反复强调“用 `computed` 而不是 `watch` 做派生”。但有一类情况必须用 `watch`：
**用户在状态 A 下手动改了一个值，现在状态 B 变了，这个值需要被修正。** 页码就是典型：

- 本来就 3 条结果，只有 1 页，用户在第 1 页 —— 没问题。
- 用户翻到第 5 页，然后在搜索框输入关键字，结果只剩 8 条（1 页）——
  此时 `page` 还是 5，`slice` 切出来是空数组，表格一片空白。

```js [页码修正]
// pageCount 变小后，把越界的页码拉回最后一页
watch(pageCount, (count) => {
  if (page.value > count) page.value = count
})

// 筛选条件变了，回到第一页（否则用户搜完停在原来的页码上，像是没搜到东西）
watch(keyword, () => {
  page.value = 1
})
```

区分标准很简单：

| 场景 | 用什么 |
| --- | --- |
| “看到的数据”由其他数据算出来 | `computed` |
| 用户操作产生的状态需要被修正 | `watch` |

### 步骤 7 · 假服务端分页：先把接口形状定下来

客户端分页有个前提：数据全在手上。真实项目里报名记录可能有几万条，必须让后端分页。
但**现在还没有后端**，怎么办？答案是把接口形状先定下来，用本地数据假装一个后端。

```js [src/composables/useServerPage.js]
import { ref, watch } from 'vue'

/**
 * 按“服务端分页”的接口形状取数。
 * 现在 fetcher 用本地数据假装后端，将来换成真实接口时，使用它的组件一行都不用改。
 */
export function useServerPage(fetcher, query, pageSize = 8) {
  const rows = ref([])
  const total = ref(0)
  const page = ref(1)
  const loading = ref(false)
  const errorMessage = ref('')

  async function load(signal) {
    loading.value = true
    errorMessage.value = ''
    try {
      const result = await fetcher({ ...query.value, page: page.value, pageSize, signal })
      rows.value = result.list
      total.value = result.total
    } catch (error) {
      if (error?.code === 'ERR_CANCELED') return
      errorMessage.value = error.message || '加载失败'
    } finally {
      loading.value = false
    }
  }

  watch([query, page], () => load(), { deep: true, immediate: true })

  return { rows, total, page, loading, errorMessage, reload: load }
}
```

两种分页的取舍，**先判断数据量，再选方案**：

| 方案 | 什么时候用 | 代价 |
| --- | --- | --- |
| 客户端分页 | 总量在几千条以内，一次拉全量 | 首屏数据体积大；排序筛选规则必须都在前端维护 |
| 服务端分页 | 总量大、或数据实时性要求高 | 每次翻页一次网络请求；筛选和排序规则必须一起传给后端 |

::: tip 为什么值得先用“假服务端”
接口形状（`{ list, total }` + `page` / `pageSize` 参数）定下来之后，组件里就没有“本地 slice”
这种临时写法了。等到真接口就位，只需要把 `fetcher` 换掉，组件、分页器、筛选逻辑全都不用动。
**这不是多写代码，是把返工提前避免掉。**
:::

## 完整代码

```js [src/data/signup-records.js]
export const signupRecords = [
  { id: 'r-01', studentName: '林小满', studentNo: '2023010112', activityTitle: '校园歌手大赛', status: 'approved', submittedAt: '2026-09-02 10:12', score: 88 },
  { id: 'r-02', studentName: '陈亦航', studentNo: '2023010233', activityTitle: '校园歌手大赛', status: 'pending', submittedAt: '2026-09-03 09:40', score: 76 },
  { id: 'r-03', studentName: '周敏', studentNo: '2022020118', activityTitle: '程序设计竞赛', status: 'approved', submittedAt: '2026-09-03 11:05', score: 92 },
  { id: 'r-04', studentName: '赵一鸣', studentNo: '2023030145', activityTitle: '志愿服务周', status: 'rejected', submittedAt: '2026-09-04 08:20', score: 55 },
  { id: 'r-05', studentName: '孙静', studentNo: '2023010176', activityTitle: '程序设计竞赛', status: 'pending', submittedAt: '2026-09-04 15:55', score: 81 },
  { id: 'r-06', studentName: '吴忧', studentNo: '2024040102', activityTitle: '志愿服务周', status: 'approved', submittedAt: '2026-09-05 10:30', score: 69 },
  { id: 'r-07', studentName: '郑可', studentNo: '2022020301', activityTitle: '校园歌手大赛', status: 'pending', submittedAt: '2026-09-05 13:47', score: 90 },
  { id: 'r-08', studentName: '冯子涵', studentNo: '2023030233', activityTitle: '运动会方阵', status: 'approved', submittedAt: '2026-09-06 09:05', score: 74 },
  { id: 'r-09', studentName: '黄诗雨', studentNo: '2024040256', activityTitle: '运动会方阵', status: 'rejected', submittedAt: '2026-09-06 16:12', score: 48 },
  { id: 'r-10', studentName: '徐嘉禾', studentNo: '2023010409', activityTitle: '程序设计竞赛', status: 'approved', submittedAt: '2026-09-07 08:58', score: 95 },
  { id: 'r-11', studentName: '何欣', studentNo: '2022020402', activityTitle: '志愿服务周', status: 'pending', submittedAt: '2026-09-07 14:33', score: 83 },
  { id: 'r-12', studentName: '罗一诺', studentNo: '2024040333', activityTitle: '校园歌手大赛', status: 'approved', submittedAt: '2026-09-08 11:20', score: 79 }
]
```

```vue [SignupGrid.vue]
<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({
  records: { type: Array, default: () => [] },
  pageSize: { type: Number, default: 8 }
})

const STATUS_TEXT = {
  pending: '待审核',
  approved: '已通过',
  rejected: '已驳回'
}

const columns = [
  { key: 'studentName', label: '学生', sortable: true },
  { key: 'studentNo', label: '学号', sortable: true },
  { key: 'activityTitle', label: '活动', sortable: false },
  { key: 'status', label: '状态', sortable: true, format: (value) => STATUS_TEXT[value] ?? value },
  { key: 'submittedAt', label: '提交时间', sortable: true }
]

const keyword = ref('')
const page = ref(1)
const sortRules = ref([{ key: 'submittedAt', order: 'desc' }])

// ── 第一层：筛选 ─────────────────────────────────────
const filtered = computed(() => {
  const text = keyword.value.trim().toLowerCase()
  if (!text) return props.records
  return props.records.filter(
    (row) => row.studentName.toLowerCase().includes(text) || row.studentNo.includes(text)
  )
})

function compareValue(a, b) {
  if (a === b) return 0
  if (a === null || a === undefined) return -1
  if (b === null || b === undefined) return 1
  if (typeof a === 'number' && typeof b === 'number') return a - b
  return String(a).localeCompare(String(b), 'zh-Hans-CN', { numeric: true })
}

// ── 第二层：排序 ─────────────────────────────────────
const sorted = computed(() => {
  if (sortRules.value.length === 0) return filtered.value
  const list = [...filtered.value]
  list.sort((a, b) => {
    for (const rule of sortRules.value) {
      const result = compareValue(a[rule.key], b[rule.key])
      if (result !== 0) return rule.order === 'asc' ? result : -result
    }
    return String(a.id).localeCompare(String(b.id))
  })
  return list
})

// ── 第三层：分页 ─────────────────────────────────────
const pageCount = computed(() => Math.max(1, Math.ceil(sorted.value.length / props.pageSize)))

const pagedRows = computed(() => {
  const start = (page.value - 1) * props.pageSize
  return sorted.value.slice(start, start + props.pageSize)
})

const sortSummary = computed(() =>
  sortRules.value
    .map((rule, index) => {
      const column = columns.find((item) => item.key === rule.key)
      const order = rule.order === 'asc' ? '升序' : '降序'
      return `${index + 1}. ${column?.label ?? rule.key}（${order}）`
    })
    .join('，')
)

watch(pageCount, (count) => {
  if (page.value > count) page.value = count
})

watch(keyword, () => {
  page.value = 1
})

// ── 交互 ────────────────────────────────────────────
function toggleSort(key, event) {
  const rules = sortRules.value
  const index = rules.findIndex((rule) => rule.key === key)

  if (index === -1) {
    const next = { key, order: 'asc' }
    sortRules.value = event.shiftKey ? [...rules, next] : [next]
    return
  }

  const current = rules[index]
  if (current.order === 'asc') {
    sortRules.value = rules.map((rule, i) => (i === index ? { ...rule, order: 'desc' } : rule))
  } else {
    sortRules.value = rules.filter((_, i) => i !== index)
  }
}

function sortMark(key) {
  const index = sortRules.value.findIndex((rule) => rule.key === key)
  if (index === -1) return ''
  const rule = sortRules.value[index]
  const arrow = rule.order === 'asc' ? '↑' : '↓'
  return sortRules.value.length > 1 ? `${index + 1}${arrow}` : arrow
}

function cellText(row, column) {
  const value = row[column.key]
  return column.format ? column.format(value) : value
}
</script>

<template>
  <section class="grid-wrap">
    <div class="toolbar">
      <input v-model="keyword" class="search" placeholder="搜索姓名或学号" />
      <span class="summary">{{ sorted.length }} 条 · {{ sortSummary || '未排序' }}</span>
    </div>

    <table class="grid">
      <thead>
        <tr>
          <th
            v-for="column in columns"
            :key="column.key"
            :class="{ sortable: column.sortable }"
            @click="column.sortable && toggleSort(column.key, $event)"
          >
            {{ column.label }}
            <span v-if="column.sortable" class="mark">{{ sortMark(column.key) }}</span>
          </th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="pagedRows.length === 0">
          <td :colspan="columns.length" class="empty">没有符合条件的报名记录。</td>
        </tr>
        <tr v-for="row in pagedRows" :key="row.id">
          <td v-for="column in columns" :key="column.key">{{ cellText(row, column) }}</td>
        </tr>
      </tbody>
    </table>

    <div class="pager">
      <button :disabled="page <= 1" @click="page -= 1">上一页</button>
      <span>第 {{ page }} / {{ pageCount }} 页</span>
      <button :disabled="page >= pageCount" @click="page += 1">下一页</button>
    </div>
  </section>
</template>

<style scoped>
.grid-wrap {
  font-size: 14px;
}
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}
.search {
  width: 240px;
  padding: 6px 8px;
  border: 1px solid #d0d5dd;
  border-radius: 4px;
}
.summary {
  color: #6b7280;
}
.grid {
  width: 100%;
  border-collapse: collapse;
}
.grid th,
.grid td {
  padding: 8px;
  border-bottom: 1px solid #e5e7eb;
  text-align: left;
}
.grid th.sortable {
  cursor: pointer;
  user-select: none;
}
.grid th.sortable:hover {
  background: #f9fafb;
}
.mark {
  margin-left: 4px;
  color: #42b883;
}
.empty {
  padding: 32px;
  text-align: center;
  color: #9ca3af;
}
.pager {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 12px;
}
.pager button {
  padding: 4px 10px;
  border: 1px solid #d0d5dd;
  border-radius: 4px;
  background: #fff;
  cursor: pointer;
}
.pager button:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}
</style>
```

```vue [SignupPage.vue]
<script setup>
import SignupGrid from '@/components/SignupGrid.vue'
import { signupRecords } from '@/data/signup-records'

const records = signupRecords
</script>

<template>
  <main>
    <h1>报名记录</h1>
    <SignupGrid :records="records" :page-size="8" />
  </main>
</template>
```

## 常见坑

::: details 坑 1：在 `computed` 里原地排序，把源数据改了
**现象**：点了一次排序，之后再点别的列，顺序怎么都对不回来；严重时筛选结果也跟着乱。

**原因**：`Array.prototype.sort` 是原地排序。写 `filtered.value.sort(...)`，改的是上一层
`computed` 返回的那个数组，等于在派生层里动了数据。

**怎么处理**：排序前先复制：`const list = [...filtered.value]`。表格、列表这类“展示用”的排序，
永远不要在源数组上做。
:::

::: details 坑 2：数字被当字符串排
**现象**：按学号排序，`2023010112` 排到了 `2022020118` 后面，看起来毫无规律；或者
`9` 排在了 `10` 后面。

**原因**：`localeCompare` 默认按字符逐位比较，`'9'` 大于 `'1'`，所以 `'9' > '10'`。
如果字段是纯数字却存成了字符串，就会这样。

**怎么处理**：数字字段用 `a - b`；确实是字符串但要按数值比（学号、版本号），
传 `{ numeric: true }`。
:::

::: details 坑 3：中文排序结果是乱的
**现象**：按姓名排序，顺序既不是拼音也不是笔画，像是随机的。

**原因**：没传区域参数时，`localeCompare` 用的是运行环境的默认区域，对中文按 Unicode 码位排，
结果自然不是人习惯的顺序。

**怎么处理**：传 `'zh-Hans-CN'`。如果要严格按拼音，还需要 `{ sensitivity: 'accent' }` 之类的参数，
具体看项目要求，不要凭感觉调。
:::

::: details 坑 4：筛选之后页码越界，表格变空
**现象**：翻到第 5 页，输入搜索词，结果一条都不显示，但“没有符合条件的记录”也没出现。

**原因**：结果只剩 1 页，`page` 还是 5，`slice` 切出来是空数组。

**怎么处理**：用 `watch` 监听总页数，越界时拉回最后一页；同时筛选条件变化时回到第一页。
这是 `watch` 的正当用途 —— 修正用户状态，不是维护派生数据。
:::

::: details 坑 5：用 `watch` 维护派生数据
**现象**：写了 `const sortedList = ref([])`，再 `watch(records, () => { sortedList.value = [...records.value].sort() })`。
一开始能跑，加了筛选之后三个 `watch` 互相触发，改一个筛选条件页面刷新两次。

**原因**：把“算出来的东西”存成了独立状态，变成需要人工同步的两份数据。

**怎么处理**：改成 `computed`。链路是 `records → filtered → sorted → pagedRows`，
任何一环变化后面自动重算，不需要手动同步。判断口诀：**能由别的数据算出来的，一律 `computed`。**
:::

::: details 坑 6：多列排序的优先级搞反
**现象**：先点“状态”再按住 Shift 点“提交时间”，结果先按时间排，状态被打平了。

**原因**：比较时从数组末项开始遍历，或者插入规则时用了 `unshift`，导致后加的规则变成了主排序。

**怎么处理**：**保持“数组顺序 = 优先级”，比较时从前往后遍历，第一个不相等的结果直接返回。**
界面上把序号标出来，用户一眼就能看出当前优先级。
:::

::: details 坑 7：用 `reverse()` 实现降序，相等元素顺序被翻过来
**现象**：升序时两个分数相同的学生顺序是 A、B，切到降序变成 B、A，再切回升序变不回去。

**原因**：先升序排序再整体 `reverse()`，把打平元素的相对顺序也一起翻转了。

**怎么处理**：不要用 `reverse()`，用**取反比较结果**的方式：

```js
if (result !== 0) return rule.order === 'asc' ? result : -result
```

再补一条 `id` 兜底规则。这样不论升降序，打平的元素顺序都一致 —— 这正是“排序稳定”的含义。
:::

## 扩展练习

::: details 练习 1：列的显示与隐藏
在工具栏加一组复选框，勾选哪些列就显示哪些列。

**思路**：给列配置加一个 `visible` 字段（或者单独维护一个 `visibleKeys` 数组），
模板里的 `<th>` 和 `<td>` 都按“可见列”循环。注意两件事：

1. `<td :colspan="columns.length">` 那个空状态单元格要跟着变，用可见列的数量。
2. 隐藏一列时，如果它正在参与排序，排序规则要不要一起清掉？这需要你先定规则，再实现。

:::

::: details 练习 2：把当前结果导出成 CSV
导出的必须是**当前筛选和排序之后的结果**，不是原始数据。

**思路**：用 `sorted.value` 作为数据源，按 `columns` 拼 CSV 文本，再用 `Blob` 加
`URL.createObjectURL` 触发下载（和[案例 05](/cases/05-markdown)导出 HTML 是同一套做法，
可以对照）。两个容易忽略的点：

- 单元格里的逗号和换行要转义，否则表格会错列。
- 姓名字段里如果有逗号，必须用双引号包起来。

:::

::: details 练习 3：把排序规则同步到地址栏
刷新页面之后，排序和筛选条件要还在。

**思路**：排序规则和关键字变化时，用 `router.replace` 把状态写进 query；组件初始化时从
`route.query` 读回来。关键是**只写一次代码**：用一个 `watch` 把两者绑起来，别在每个点击处理函数里各写一遍。
路由的用法见[路由基础](/unit09/01-router-basics)。
:::

::: details 练习 4：换成真服务端分页
用[案例 04](/cases/04-fetch)里的请求层，把 `SignupGrid` 改成用 `useServerPage` 取数。

**思路**：改造分三步 ——

1. 把 `fetcher` 从本地 `slice` 换成真实的 `fetchSignups` 请求函数，参数里带上 `keyword`、
   `sortKey`、`sortOrder`、`page`、`pageSize`。
2. 前端不再需要 `filtered` 和 `sorted` 两层 `computed`，只保留 `pagedRows` 的替代品
   （接口返回的 `list`）。但要补上 `loading` 和错误态。
3. 快速切换页码会产生竞态，必须加请求取消。这一条在[案例 04](/cases/04-fetch)里有完整演示，
   不做的话会遇到“点第 3 页显示第 2 页数据”。

:::

---

上一页：[案例 01 · 增删改查清单](/cases/01-crud) · 下一页：[案例 03 · 树状视图与递归组件](/cases/03-tree)
