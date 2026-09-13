# 案例 09 · 可编辑表格

## 场景：审核员要批量改报名记录

活动报名截止后，审核员需要核对并修正一批报名记录。用弹窗逐条编辑太慢，
所以他们希望**在表格里直接改**：

| 编号 | 需求 |
| --- | --- |
| 1 | 点击可编辑的单元格，就地进入编辑态 |
| 2 | 回车确认、Esc 取消、点别处（失焦）保存 |
| 3 | 方向键在单元格之间移动 |
| 4 | 整行保存，且**只提交改过的行** |
| 5 | 批量选择若干行，做批量操作（批量通过） |
| 6 | 撤销上一次修改 |
| 7 | 支持从 Excel 复制多行，粘贴进表格 |

这个案例比树状视图更“散”，因为它涉及**输入、键盘、剪贴板**多种交互。
但它的核心只有一件事：**用什么样的数据形状来表达“正在编辑”和“已选中”这两种界面状态。**

::: warning 两个最容易做错的地方
1. **给每行加一个 `isEditing` 字段** —— 看起来直观，实际会带来一堆麻烦。
2. **编辑态的进入与退出时机** —— 失焦保存与“点到别的单元格”会打架，
   回车确认之后失焦还会再触发一次。

这两点在下面会单独讲，它们是本案例真正的难点。
:::

## 数据结构与列配置

```js [src/views/SignupBatchEditView.vue（数据部分）]
import { ref, computed } from 'vue'

// 可编辑的列由配置决定，表格组件不写死任何业务字段
const columns = [
  { key: 'studentName', title: '姓名', width: 110, editable: false },
  { key: 'studentId', title: '学号', width: 150, editable: false },
  { key: 'phone', title: '联系电话', width: 150, editable: true },
  // 下拉类型的单元格
  { key: 'group', title: '分组', width: 120, editable: true, type: 'select', options: ['A 组', 'B 组', 'C 组'] },
  { key: 'remark', title: '备注', width: 200, editable: true },
  { key: 'status', title: '审核状态', width: 110, editable: false }
]

const rows = ref([
  { id: 1001, studentName: '林小雨', studentId: '20230101', phone: '13800000001', group: 'A 组', remark: '需素食餐', status: 'pending' },
  { id: 1002, studentName: '陈志远', studentId: '20230102', phone: '13800000002', group: 'B 组', remark: '', status: 'pending' },
  { id: 1003, studentName: '黄思琪', studentId: '20230103', phone: '13800000003', group: 'A 组', remark: '有带队老师', status: 'approved' }
])
```

关键在于：**哪些列可编辑、用什么控件编辑，全部写在列的配置里。**
表格组件只负责“按配置渲染”，它不认识 `phone` 或 `group` 这些业务字段。

## 编辑态：用一个值表达

### 不要给每行加 `isEditing` 字段

```js [✗ 不推荐]
rows.value.forEach((row) => {
  row.isEditing = false
})
// 点某个单元格时
row.isEditing = true
row.editingKey = 'phone'
```

问题有四个：

| 问题 | 说明 |
| --- | --- |
| 污染数据 | 接口返回的数据里被塞了界面状态，提交时还要记得删掉 |
| 表达不了“哪一格” | 一行有多个可编辑列，`isEditing` 说不清是哪一个 |
| 维护“同时只编辑一格”很麻烦 | 每次进入编辑都要遍历所有行，把所有 `isEditing` 置回 `false` |
| 撤销、重载后容易残留 | 数据被替换了，状态可能还留着 |

### 正确做法：一个对象说清“谁在编辑”

```js [✓ 推荐]
// 当前正在编辑的单元格：{ rowId, key }，没有就是 null
const editing = ref(null)

// 当前键盘聚焦的单元格（编辑态之外的概念）
const activeCell = ref(null)

function isEditing(row, col) {
  return editing.value?.rowId === row.id && editing.value?.key === col.key
}

function startEdit(row, col) {
  if (!col.editable) return
  activeCell.value = { rowId: row.id, key: col.key }
  editing.value = { rowId: row.id, key: col.key }
}
```

这个设计的三个好处：

1. **天然的“同时只有一个单元格在编辑”** —— 因为 `editing` 只有一个值，赋值就切换了，
   不需要遍历重置。
2. **数据完全不被动** —— 表格里拿到的行还是接口返回的原样数据。
3. **状态可序列化** —— 调试时打印 `editing.value` 就知道现在在编辑哪一格。

::: tip 同一个思路在别处的应用
“用一个值表达唯一状态”这个思路很通用：

| 场景 | 用单值 | 不要用 |
| --- | --- | --- |
| 表格编辑态 | `editing = { rowId, key }` | 每行一个 `isEditing` |
| 当前展开的菜单 | `openMenuId = 'file'` | 每个菜单一个 `opened` |
| 当前选中的标签页 | `activeTab = 'basic'` | 每个标签页一个 `selected` |

**判断标准：这个状态“同时只能有一个”吗？** 是的话，用一个值就够了。
唯一状态用单值表达，天然不会出现“两个同时为真”的非法状态。
:::

### 批量选中：一个 `Set` 存 id

批量选择是“可以有多个”的状态，用集合：

```js
// 选中的行 id 集合
const selectedIds = ref(new Set())

function toggleSelect(id) {
  if (selectedIds.value.has(id)) {
    selectedIds.value.delete(id)
  } else {
    selectedIds.value.add(id)
  }
}

// 表头的全选框用 computed 算状态
const allSelected = computed(
  () => rows.value.length > 0 && rows.value.every((row) => selectedIds.value.has(row.id))
)

function toggleSelectAll() {
  if (allSelected.value) {
    selectedIds.value = new Set()
  } else {
    selectedIds.value = new Set(rows.value.map((row) => row.id))
  }
}
```

**注意“唯一状态用单值、多选状态用集合”这条分界线。** 两者都避免了“往业务数据里加标记字段”。

## 单元格组件与三个出口

把单元格拆成 `EditableCell.vue`，好处是**自动聚焦的逻辑只写一次**，
而且表格的模板会干净很多。

```vue [src/components/business/EditableCell.vue]
<script setup>
import { ref, nextTick, onMounted, useTemplateRef } from 'vue'

const props = defineProps({
  value: { type: [String, Number], default: '' },
  type: { type: String, default: 'text' }, // text | select
  options: { type: Array, default: () => [] }
})

const emit = defineEmits(['commit', 'cancel', 'move-vertical'])

const draft = ref(props.value)
const inputEl = useTemplateRef('inputRef')

// 去重标志：回车确认之后失焦还会再触发一次，必须保证只提交一次
let finished = false

onMounted(() => {
  // 挂载后自动聚焦并全选，用户可以直接覆盖输入
  nextTick(() => {
    const el = inputEl.value
    if (!el) return
    el.focus()
    if (typeof el.select === 'function') el.select()
  })
})

function commit() {
  if (finished) return
  finished = true
  emit('commit', draft.value)
}

function cancel() {
  if (finished) return
  finished = true
  emit('cancel')
}

function onKeydown(e) {
  if (e.key === 'Enter') {
    e.preventDefault()
    commit()
    // 回车之后顺势往下走一格（和表格软件的习惯一致）
    emit('move-vertical', 1)
  } else if (e.key === 'Escape') {
    e.preventDefault()
    cancel()
  } else if (e.key === 'ArrowDown') {
    e.preventDefault()
    commit()
    emit('move-vertical', 1)
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    commit()
    emit('move-vertical', -1)
  }
  // 左右方向键保留给光标移动，不做单元格移动
}
</script>

<template>
  <select
    v-if="type === 'select'"
    ref="inputRef"
    v-model="draft"
    class="cell-input"
    @change="commit"
    @blur="commit"
    @keydown="onKeydown"
  >
    <option v-for="option in options" :key="option" :value="option">{{ option }}</option>
  </select>

  <input
    v-else
    ref="inputRef"
    v-model="draft"
    class="cell-input"
    @blur="commit"
    @keydown="onKeydown"
  />
</template>

<style scoped>
.cell-input {
  width: 100%;
  height: 28px;
  padding: 0 6px;
  border: 1px solid #1a6fd4;
  border-radius: 3px;
  outline: none;
  font-size: 14px;
}
</style>
```

### 三个出口分别做了什么

| 出口 | 触发条件 | 行为 |
| --- | --- | --- |
| **回车** | 在输入框里按 Enter | 提交草稿，并往下移动一格 |
| **Esc** | 在输入框里按 Esc | 丢弃草稿，退出编辑态 |
| **失焦** | 点到表格其他地方、切到别的窗口 | 提交草稿，退出编辑态 |

### 失焦保存与“点到别处”的冲突

这是本案例最容易出 bug 的地方。设想用户正在编辑第一行的“电话”列，然后**直接点第四行的“备注”列**。
浏览器的事件顺序是：

```text [事件顺序]
1. 第一个输入框触发 blur        → 保存第一行的电话
2. 第四个单元格触发 click       → 进入编辑态
```

顺序上是对的，所以**不会丢数据**。但如果不处理，会有两个副作用：

- 如果表格的 `click` 写在 `td` 上，而 `blur` 的保存导致 `rows` 重新渲染，
  有时会让 `click` 落空。稳妥做法是把点击处理写在 `td` 上而不是内部元素上。
- 用户想“取消”，但点了别处 → 变成了保存。这是**有意**的设计：
  点了别的地方说明他认可当前内容。想取消就用 Esc。

::: warning 回车之后失焦会再触发一次
按 Enter 时 `commit()` 执行了，紧接着输入框被移除（`v-if` 变化）会触发 `blur`，
`commit()` 又会被调用一次。**如果不做去重，会出现两次提交、两次入历史栈。**

所以 `EditableCell` 里必须有一个 `finished` 标志。这个坑在
“一个操作有多个触发路径”时普遍存在 —— 比如[6.4 里的重复提交防护](/unit06/04-validation)，
思路是一样的。
:::

### 编辑态的进入与退出时机

把规则列清楚，避免写出“点不进去”或“退不出来”的表格：

| 时机 | 动作 | 说明 |
| --- | --- | --- |
| 单击**可编辑**单元格 | 进入编辑态 | 不可编辑的列只更新 `activeCell` |
| 单击**不可编辑**单元格 | 退出当前编辑（提交） | 因为它不会接管编辑态 |
| 双击 | 不做处理 | 单击已经进了，双击会先编辑再退出，体验差 |
| Esc | 取消并退出 | 草稿丢弃 |
| 回车 / 上下方向键 | 提交并移动 | 移动目标必须也是可编辑列，否则停在原地 |
| 表格数据被重新加载 | 清空编辑态与选中态 | 否则 `rowId` 可能已经不存在了 |

最后一条常被漏掉。数据重新加载后，`editing` 里存的 `rowId` 可能已经不在新数据里，
这时表格看起来“卡在编辑态”。**加载新数据时应该一并重置界面状态。**

```js
function reload() {
  rows.value = await fetchSignupList(activityId)
  // ✓ 数据换了，界面状态一起重置
  editing.value = null
  activeCell.value = null
  selectedIds.value = new Set()
  resetSnapshot()
}
```

## 键盘方向键移动

`activeCell` 记录当前聚焦的单元格。表格外层监听方向键：

```js [键盘移动]
// 从 colIndex 出发，往 direction 方向找最近的可编辑列
function findEditableColumn(fromIndex, direction) {
  let index = fromIndex + direction
  while (index >= 0 && index < columns.length) {
    if (columns[index].editable) return index
    index += direction
  }
  return fromIndex
}

function onTableKeydown(e) {
  // 编辑态下的按键由单元格自己处理
  if (editing.value || !activeCell.value) return

  const rowIndex = rows.value.findIndex((row) => row.id === activeCell.value.rowId)
  const colIndex = columns.findIndex((col) => col.key === activeCell.value.key)
  if (rowIndex < 0 || colIndex < 0) return

  let nextRow = rowIndex
  let nextCol = colIndex

  switch (e.key) {
    case 'ArrowDown':
      nextRow = Math.min(rowIndex + 1, rows.value.length - 1)
      break
    case 'ArrowUp':
      nextRow = Math.max(rowIndex - 1, 0)
      break
    case 'ArrowRight':
      nextCol = findEditableColumn(colIndex, 1)
      break
    case 'ArrowLeft':
      nextCol = findEditableColumn(colIndex, -1)
      break
    case 'Enter':
      if (columns[colIndex].editable) {
        e.preventDefault()
        startEdit(rows.value[rowIndex], columns[colIndex])
      }
      return
    default:
      return
  }

  e.preventDefault()
  activeCell.value = { rowId: rows.value[nextRow].id, key: columns[nextCol].key }
}
```

::: tip 为什么左右键不移动单元格
在电子表格里，左右键既移动单元格又移动光标，靠双击区分。但在网页里，
用户在输入框里按左右键的期望是**移动光标**（改一个字的位置）。

所以这里做了一个取舍：

- **上下键**：移动单元格（提交当前编辑）。
- **左右键**：编辑态下移动光标；非编辑态下移动聚焦的单元格。

**做键盘交互时，一定要先想“用户在这个位置最想要什么”，而不是照搬表格软件。**
:::

## 脏检查与整行保存

### 保留一份原始快照

“只提交改过的行”需要知道每行改之前长什么样。做法是**加载数据时存一份浅拷贝**：

```js [原始快照]
// rowId → 原始行的副本
const originalMap = ref(new Map())

const EDITABLE_KEYS = columns.filter((col) => col.editable).map((col) => col.key)

function resetSnapshot() {
  originalMap.value = new Map(rows.value.map((row) => [row.id, { ...row }]))
}
```

### 算出差集

```js [脏行计算]
const dirtyIds = computed(() => {
  const ids = new Set()
  for (const row of rows.value) {
    const original = originalMap.value.get(row.id)
    if (!original) continue
    const changed = EDITABLE_KEYS.some((key) => original[key] !== row[key])
    if (changed) ids.add(row.id)
  }
  return ids
})

const dirtyRows = computed(() => rows.value.filter((row) => dirtyIds.value.has(row.id)))
const dirtyCount = computed(() => dirtyRows.value.length)
```

::: warning 为什么只比较可编辑字段
如果不筛选字段，那么**任何**字段变了都会算成“脏”。但有些字段是别的操作改的
（比如“审核状态”是批量操作改的，走的是另一个接口），把它算进来会导致
“明明只点了批量通过，却把整行也提交了一遍”。

**脏检查的范围要和提交的范围一致。** 这里提交的是可编辑字段，
那脏检查也只比这几个字段。
:::

### 提交

```js [只提交改过的行]
const saving = ref(false)

async function saveDirty() {
  if (saving.value) return
  if (dirtyRows.value.length === 0) {
    message.info('没有需要保存的修改')
    return
  }

  saving.value = true
  try {
    await batchUpdateSignup(activityId.value, dirtyRows.value.map(toPayload))
    message.success(`已保存 ${dirtyRows.value.length} 条记录`)
    // ✓ 保存成功后刷新快照，否则“脏”状态一直挂着
    resetSnapshot()
  } catch (e) {
    message.error(e.message || '保存失败')
  } finally {
    saving.value = false
  }
}

function toPayload(row) {
  const payload = { id: row.id }
  EDITABLE_KEYS.forEach((key) => {
    payload[key] = row[key]
  })
  return payload
}
```

注意 `resetSnapshot()` 的位置：**在请求成功之后**。如果放在 `finally` 里，
请求失败时也刷新了快照，用户就丢失了“哪些行还没保存成功”的信息。

## 批量选择与批量操作

选中行之后，表头会出现一个批量操作条：

```vue [批量操作条]
<div v-if="selectedIds.size > 0" class="batch-bar">
  <span>已选 {{ selectedIds.size }} 条</span>
  <button type="button" @click="batchApprove">批量通过</button>
  <button type="button" @click="selectedIds = new Set()">取消选择</button>
</div>
```

```js [批量通过]
async function batchApprove() {
  const ids = [...selectedIds.value]
  pushHistory() // 批量操作也要能撤销
  try {
    await approveSignupBatch(ids)
    rows.value.forEach((row) => {
      if (ids.includes(row.id)) row.status = 'approved'
    })
    message.success(`已通过 ${ids.length} 条`)
    selectedIds.value = new Set()
    resetSnapshot()
  } catch (e) {
    message.error(e.message || '批量操作失败')
  }
}
```

::: tip 一个必须想清楚的问题：批量操作改了可编辑字段怎么办
如果批量操作修改的字段正好在 `EDITABLE_KEYS` 里（比如“批量设置分组”），
那么执行完之后**这些行会立刻变成“脏”的**，因为快照里还是旧值。

两种处理方式：

1. **改完立刻刷新快照**（上面的做法）：认为“批量操作已经落库了，不算待保存的修改”。
2. **不刷新快照**：认为“批量操作是本地预览，要等点保存才提交”。

**两种都对，取决于你的接口设计。** 但必须**明确选一种**，否则会出现
“批量设置分组后，点保存又把分组提交了一遍”或者“以为已经保存了，其实没有”。
:::

## 撤销上一次修改

用**整表快照**实现最简单：

```js [撤销栈]
const history = ref([])
const MAX_HISTORY = 20

function pushHistory() {
  // 深一层拷贝：只拷行对象，值都是基础类型，浅拷贝够用
  history.value.push(rows.value.map((row) => ({ ...row })))
  if (history.value.length > MAX_HISTORY) {
    history.value.shift()
  }
}

function undo() {
  const last = history.value.pop()
  if (!last) {
    message.info('没有可撤销的操作')
    return
  }
  rows.value = last
  editing.value = null
  activeCell.value = null
}
```

::: tip 整表快照 vs 记录差异
| 方案 | 实现成本 | 内存 | 撤销粒度 |
| --- | --- | --- | --- |
| **整表快照** | 低，十行代码 | 每步一份全表数据 | 只能逐步回退 |
| 记录每个操作 | 高，要为每种操作写反向操作 | 只存差异 | 可以实现“跳到某一步” |

本案例的表格最多几十行，**整表快照完全够用**。
真正需要“记录差异”的是画板、富文本编辑器这类数据量大的场景 ——
[案例 08 画板的撤销重做](/unit08/07-case-canvas)会讲那种做法。

**先选实现成本低的方案，等它真的不够用再换。**
:::

注意 `pushHistory()` 的调用时机：**在修改之前**。
所以每个改动入口（提交单元格、批量操作、粘贴）都要在改之前调一次。

## 粘贴多行数据（TSV 解析）

从 Excel 或在线表格里复制一片区域，粘到网页里，得到的是 **TSV 文本**：
列之间用制表符（`\t`）分隔，行之间用换行符分隔。

```text [从 Excel 复制的三行两列]
13800000004	张三
13800000005	李四
13800000006	王五
```

把它解析成二维数组：

```js [TSV 解析]
function parseTsv(text) {
  return text
    .replace(/\r\n/g, '\n') // Windows 换行统一成 \n
    .replace(/\r/g, '\n') // 老 Mac 换行
    .replace(/\n$/, '') // 去掉末尾多出来的空行
    .split('\n')
    .map((line) => line.split('\t'))
}
```

粘贴时，以**当前编辑的单元格**为左上角锚点，把数据铺开：

```js [粘贴处理]
function onPaste(e) {
  const text = e.clipboardData?.getData('text/plain') ?? ''

  // 单值的粘贴交给浏览器默认行为，不要拦
  if (!text.includes('\t') && !text.includes('\n')) return

  const anchor = editing.value || activeCell.value
  if (!anchor) return

  const startRow = rows.value.findIndex((row) => row.id === anchor.rowId)
  const startCol = columns.findIndex((col) => col.key === anchor.key)
  if (startRow < 0 || startCol < 0) return

  e.preventDefault()
  pushHistory() // 粘贴是一次可撤销的批量修改

  const matrix = parseTsv(text)

  matrix.forEach((cells, rowOffset) => {
    const row = rows.value[startRow + rowOffset]
    if (!row) return // 超出行数范围，直接忽略
    cells.forEach((cellText, colOffset) => {
      const col = columns[startCol + colOffset]
      if (!col || !col.editable) return // 跳过不可编辑的列
      row[col.key] = cellText.trim()
    })
  })

  editing.value = null
}
```

::: warning 粘贴必须处理的三件事
1. **单值粘贴不要拦。** 用户只是粘一个手机号，应该走默认行为，
   否则光标位置、撤销栈都会乱。
2. **越界要停。** 粘的列数、行数可能超过表格范围，多的部分直接丢掉，
   **不要动态往表格里加行** —— 那会让“粘贴”变成“导入”，是完全不同的功能。
3. **算一次撤销。** 粘贴了 10 行 3 列，撤销一次应该全部回退，
   而不是要按 30 次撤销。
:::

## 完整的表格组件

把上面各部分合起来：

```vue [src/components/business/EditableTable.vue]
<script setup>
import { ref, computed } from 'vue'
import EditableCell from './EditableCell.vue'

const props = defineProps({
  columns: { type: Array, required: true },
  rows: { type: Array, default: () => [] },
  rowKey: { type: String, default: 'id' }
})

const emit = defineEmits(['change'])

const editing = ref(null)
const activeCell = ref(null)
const selectedIds = ref(new Set())
const history = ref([])
const MAX_HISTORY = 20

const editableColumns = computed(() => props.columns.filter((col) => col.editable))
const editableKeys = computed(() => editableColumns.value.map((col) => col.key))

/* ---------------- 编辑态 ---------------- */
function isEditing(row, col) {
  return editing.value?.rowId === row.id && editing.value?.key === col.key
}

function isActive(row, col) {
  return activeCell.value?.rowId === row.id && activeCell.value?.key === col.key
}

function startEdit(row, col) {
  activeCell.value = { rowId: row.id, key: col.key }
  if (col.editable) {
    editing.value = { rowId: row.id, key: col.key }
  } else {
    editing.value = null
  }
}

function commitEdit(value) {
  const cell = editing.value
  if (!cell) return
  const row = props.rows.find((item) => item[props.rowKey] === cell.rowId)
  if (!row) return
  if (row[cell.key] !== value) {
    pushHistory()
    row[cell.key] = value
    emit('change', { row, key: cell.key, value })
  }
  editing.value = null
}

function cancelEdit() {
  editing.value = null
}

function moveVertical(direction) {
  const cell = editing.value || activeCell.value
  if (!cell) return
  const rowIndex = props.rows.findIndex((row) => row[props.rowKey] === cell.rowId)
  const next = rowIndex + direction
  if (next < 0 || next >= props.rows.length) {
    editing.value = null
    return
  }
  const row = props.rows[next]
  activeCell.value = { rowId: row[props.rowKey], key: cell.key }
  editing.value = editableKeys.value.includes(cell.key)
    ? { rowId: row[props.rowKey], key: cell.key }
    : null
}

/* ---------------- 键盘移动 ---------------- */
function findEditableColumn(fromIndex, direction) {
  let index = fromIndex + direction
  while (index >= 0 && index < props.columns.length) {
    if (props.columns[index].editable) return index
    index += direction
  }
  return fromIndex
}

function onTableKeydown(e) {
  if (editing.value || !activeCell.value) return

  const rowIndex = props.rows.findIndex((row) => row[props.rowKey] === activeCell.value.rowId)
  const colIndex = props.columns.findIndex((col) => col.key === activeCell.value.key)
  if (rowIndex < 0 || colIndex < 0) return

  let nextRow = rowIndex
  let nextCol = colIndex

  switch (e.key) {
    case 'ArrowDown':
      nextRow = Math.min(rowIndex + 1, props.rows.length - 1)
      break
    case 'ArrowUp':
      nextRow = Math.max(rowIndex - 1, 0)
      break
    case 'ArrowRight':
      nextCol = findEditableColumn(colIndex, 1)
      break
    case 'ArrowLeft':
      nextCol = findEditableColumn(colIndex, -1)
      break
    case 'Enter':
      if (props.columns[colIndex].editable) {
        e.preventDefault()
        startEdit(props.rows[rowIndex], props.columns[colIndex])
      }
      return
    default:
      return
  }

  e.preventDefault()
  activeCell.value = {
    rowId: props.rows[nextRow][props.rowKey],
    key: props.columns[nextCol].key
  }
}

/* ---------------- 选中 ---------------- */
function toggleSelect(id) {
  if (selectedIds.value.has(id)) selectedIds.value.delete(id)
  else selectedIds.value.add(id)
}

const allSelected = computed(
  () =>
    props.rows.length > 0 &&
    props.rows.every((row) => selectedIds.value.has(row[props.rowKey]))
)

function toggleSelectAll() {
  selectedIds.value = allSelected.value
    ? new Set()
    : new Set(props.rows.map((row) => row[props.rowKey]))
}

/* ---------------- 撤销 ---------------- */
function pushHistory() {
  history.value.push(props.rows.map((row) => ({ ...row })))
  if (history.value.length > MAX_HISTORY) history.value.shift()
}

function undo() {
  const last = history.value.pop()
  if (!last) return false
  props.rows.splice(0, props.rows.length, ...last)
  editing.value = null
  activeCell.value = null
  return true
}

const canUndo = computed(() => history.value.length > 0)

/* ---------------- 粘贴 ---------------- */
function parseTsv(text) {
  return text
    .replace(/\r\n/g, '\n')
    .replace(/\r/g, '\n')
    .replace(/\n$/, '')
    .split('\n')
    .map((line) => line.split('\t'))
}

function onPaste(e) {
  const text = e.clipboardData?.getData('text/plain') ?? ''
  if (!text.includes('\t') && !text.includes('\n')) return

  const anchor = editing.value || activeCell.value
  if (!anchor) return

  const startRow = props.rows.findIndex((row) => row[props.rowKey] === anchor.rowId)
  const startCol = props.columns.findIndex((col) => col.key === anchor.key)
  if (startRow < 0 || startCol < 0) return

  e.preventDefault()
  pushHistory()

  parseTsv(text).forEach((cells, rowOffset) => {
    const row = props.rows[startRow + rowOffset]
    if (!row) return
    cells.forEach((cellText, colOffset) => {
      const col = props.columns[startCol + colOffset]
      if (!col || !col.editable) return
      row[col.key] = cellText.trim()
    })
  })

  editing.value = null
}

defineExpose({ undo, canUndo, pushHistory, selectedIds, editing })
</script>

<template>
  <div class="editable-table" tabindex="0" @keydown="onTableKeydown" @paste="onPaste">
    <table>
      <thead>
        <tr>
          <th class="col-check">
            <input type="checkbox" :checked="allSelected" @change="toggleSelectAll" />
          </th>
          <th
            v-for="col in columns"
            :key="col.key"
            :style="{ width: col.width + 'px' }"
          >
            {{ col.title }}
          </th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="row[rowKey]">
          <td class="col-check">
            <input
              type="checkbox"
              :checked="selectedIds.has(row[rowKey])"
              @change="toggleSelect(row[rowKey])"
            />
          </td>
          <td
            v-for="col in columns"
            :key="col.key"
            :class="{ 'is-active': isActive(row, col), 'is-editable': col.editable }"
            @click="startEdit(row, col)"
          >
            <EditableCell
              v-if="isEditing(row, col)"
              :value="row[col.key]"
              :type="col.type || 'text'"
              :options="col.options || []"
              @commit="commitEdit"
              @cancel="cancelEdit"
              @move-vertical="moveVertical"
            />
            <span v-else>{{ row[col.key] }}</span>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
```

::: warning 上面这一段里有一处需要注意的写法
`undo` 里用了 `props.rows.splice(...)` —— 这是在**修改父组件传进来的数组**，
严格来说违反了单向数据流。

这里之所以这么做，是因为这个组件被设计成“**就地编辑表格**”：
它的定位就是一个操作父组件数据的编辑器，而不是一个纯展示组件。
**这是一个有意的例外，必须写清楚**：

- 如果是“纯展示表格”，不应该这么做，应该把改动通过事件抛出去。
- 如果是“就地编辑表格”，可以让父组件把响应式数组直接传进来，由表格改它 ——
  但要**在组件注释里写明这一点**，否则下一个人会以为这是漏改的 bug。

更规范的做法是让父组件传入 `v-model:rows`，或者在表格里维护副本、
通过事件同步回去。**两种做法各有代价，选一种并说清楚。**
:::

在页面里使用：

```vue [src/views/SignupBatchEditView.vue]
<script setup>
import { ref } from 'vue'
import EditableTable from '@/components/business/EditableTable.vue'
import { saveSignupBatch } from '@/api/signup'
import { message } from '@/utils/message'

const columns = [/* 见前面的配置 */]
const rows = ref([/* 见前面的数据 */])

const tableRef = ref(null)

async function handleSave() {
  const changed = rows.value.filter((row) => row.status === 'pending')
  await saveSignupBatch(changed)
  message.success('已保存')
}

function handleUndo() {
  if (!tableRef.value?.undo()) {
    message.info('没有可撤销的操作')
  }
}
</script>

<template>
  <div class="toolbar">
    <button type="button" :disabled="!tableRef?.canUndo" @click="handleUndo">撤销</button>
    <button type="button" @click="handleSave">保存修改</button>
  </div>

  <EditableTable ref="tableRef" :columns="columns" :rows="rows" />
</template>
```

## 小结

- 编辑态用**一个对象**表达（`{ rowId, key }`），不要给每行加 `isEditing` 字段；
  唯一状态用单值，多选状态用 `Set`。
- 单元格的三个出口：**回车提交并下移、Esc 取消、失焦提交**；
  必须用 `finished` 标志去重，防止回车之后的 `blur` 再提交一次。
- 编辑态的进入与退出规则要列清楚；**数据重新加载时要重置界面状态**。
- 上下键移动单元格，左右键保留给光标；**键盘交互要按用户预期设计，不照搬表格软件**。
- 脏检查靠**原始快照**比对，范围要和提交范围一致（只比可编辑字段）；
  **快照在请求成功后才刷新**。
- 撤销用**整表快照栈**，实现成本低；每个改动入口都要在改之前存一次快照。
- 粘贴要解析 TSV，**单值不拦、越界丢弃、算一次撤销**。
- 就地编辑表格会修改属性传入的数组，这是**有意的例外**，必须在注释里写明。

## 常见坑

::: details 坑 1：回车确认后提交了两次
**现象**：改一个单元格，点了回车，接口收到了两次同样的请求（或者撤销要按两次）。

**原因**：回车触发 `commit`，紧接着输入框被移除触发 `blur`，`commit` 又执行一次。

**处理**：用一个 `finished` 标志，提交或取消之后就不再响应后续触发。
**任何“一个操作有多个触发路径”的地方都要做这个去重。**
:::

::: details 坑 2：点别的单元格，数据没保存
**现象**：编辑完直接点另一个单元格，前一个格子的修改丢了。

**原因**：`blur` 的处理函数没写，或者写在了错误的元素上（比如写在 `td` 上，
而 `blur` 只在输入框上触发）。

**处理**：`blur` 一定要绑在**输入框本身**上。同时确认点击另一个单元格时
事件顺序是 `blur` → `click`（正常情况就是这样）。
:::

::: details 坑 3：脏检查把不该算的行也算上了
**现象**：只点了一次“批量通过”，保存时却把整行数据都提交了。

**原因**：脏检查比较的是整行所有字段，而批量操作改了 `status`。

**处理**：脏检查只比较**提交范围内**的字段。先明确“保存接口会提交哪些字段”，
脏检查就比对哪些字段。
:::

::: details 坑 4：粘贴把表格撑大了
**现象**：从 Excel 粘了 50 行，表格自动变成了 50 行。

**原因**：粘贴处理里做了“超出行数就新增行”。

**处理**：**越界的部分直接丢弃**，并在界面上提示“只粘贴了前 N 行”。
“粘贴”和“导入”是两个功能，不要混在一起。
:::

::: details 坑 5：重新加载数据后编辑态卡住
**现象**：保存成功后重新拉取列表，表格里还残留着一个输入框，或者点击没反应。

**原因**：`editing` 里存的 `rowId` 在新数据里已经不存在了，或者 `activeCell` 指向了被删掉的行。

**处理**：任何重新加载数据的动作，都要顺手清空 `editing`、`activeCell`、`selectedIds`。
**把这三行写进一个 `resetUiState()` 函数**，每次加载都调一次。
:::

::: details 坑 6：`tabindex` 没写，键盘事件收不到
**现象**：表格外层写了 `@keydown`，但按方向键没反应。

**原因**：普通 `<div>` 不能获得焦点，也就收不到键盘事件。

**处理**：给容器加 `tabindex="0"`。如果希望点击单元格后键盘事件也能生效，
要注意焦点可能在输入框上 —— 这时 `editing` 不为空，按键由单元格处理，这是预期行为。
:::

## 课后练习

::: details 练习 1：加一个“复制选中行到剪贴板”
需求：选中若干行后，点“复制”，把选中行（只含可编辑列）以 TSV 格式写入剪贴板。

**参考思路**：用 `navigator.clipboard.writeText(text)`，两个字符串用 `\t` 连、
多行用 `\n` 连。**注意列的顺序要和粘贴解析时一致**，否则复制出来再粘回去会错位。
写完可以自己测一次“复制 → 粘贴到 Excel → 再从 Excel 复制回来”，一测就知道对不对。

:::

::: details 练习 2：给“分组”这一列加校验
需求：分组只允许 `A 组`、`B 组`、`C 组` 三个值，粘贴进来的其他值一律丢弃并统计丢弃数量。

**参考思路**：校验放在 `commitEdit` 和粘贴处理里。注意区分“用户手动输入非法值”
和“粘贴了大批数据”。前者适合弹提示让用户改，后者适合静默丢弃并汇总提示
（弹 20 次提示没人受得了）。

:::

::: details 练习 3：把撤销改成“按单元格撤销”
需求：撤销一次只回退**最后一个被修改的单元格**，而不是整行或整表。

**参考思路**：需要把历史栈从“整表快照”改成“操作记录”，每条记录包含
`{ rowId, key, before, after }`。撤销时用 `before` 写回。
想一想：如果两次修改在同一个单元格上，记录会怎么累积？这算不算问题？

:::

::: details 练习 4：讨论“就地编辑”这个设计
回答三个问题：

1. 为什么本案例的表格可以直接改 `props.rows`，而[7.2](/unit07/02-props)说不能改属性？
2. 如果要把它改成“严格单向数据流”，接口要怎么改？
3. 两种做法各自的代价是什么？

**参考思路**：第 1 问的关键是“组件的定位”——
它是纯展示组件还是编辑器。第 2 问可以想想 `v-model:rows` 或者
“内部维护副本 + 事件同步”。第 3 问要落到具体的代码复杂度上。

:::

---

上一节：[案例 03 · 树状视图与递归组件](/unit07/05-case-tree) ·
下一节：[单元 7 课后练习](/unit07/practice)
