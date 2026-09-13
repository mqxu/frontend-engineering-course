# 案例 09 · 可编辑表格

## 案例要做什么

场次安排有一个独立页面，用来调整每个场次的场地和时间。数据量不大，通常三到八行，但如果每改一个字段都要弹一个表单，来回点十几下很烦。更合适的做法是**表格里直接改**：点单元格进入编辑，改完按回车或点别处就提交。

要支持这些操作：

| 操作 | 触发方式 |
| --- | --- |
| 进入编辑 | 单击单元格 |
| 提交 | 按 `Enter`，或输入框失去焦点 |
| 取消 | 按 `Esc`，恢复成原来的值 |
| 上下移动 | 按 `Enter` 提交后自动跳到下一行的同一列 |
| 新增一行 | 点“新增场次”，在表格顶部插入一个空行并直接进入编辑 |
| 批量修改 | 勾选多行，统一设置场地或日期 |
| 校验不通过 | 提示原因，并**保留原值**，不做修改 |

业务上要守住的规则有两条：**结束时间必须晚于开始时间；填报的容纳人数不能超过所选场地的实际容量。**

做完之后可以这样自查，每一条都能在浏览器里手动验证：

- 点任意单元格进入编辑，按 `Enter` 提交后光标自动落在下一行的同一列上。
- 在单元格里改了值再按 `Esc`，退出编辑后显示的还是原来的值，没有被提交。
- 把“容纳人数”改成 500，而场地是只能装 60 人的文科楼 102，会看到提示并保留原值。
- 点“新增场次”，新行出现在最上方并且第一列已经在编辑状态；此时正在编辑的行不会串到别的行上。
- 勾选三行点“统一设为 50 人”，其中场地装不下的行不会被改，最后告诉你改了几行、几行没改。
- 在单元格里按回车，页面不会刷新、不会跳转。

这个案例表面看是“表格 + 输入框”，真正有难度的地方在两个细节上，到实现步骤里会单独讲：

1. **`v-for` 的 `key` 用什么。** 用下标当 `key`，一次“在顶部插入新行”就能让编辑态错位到别的行上。
2. **`Esc` 之后 `blur` 还会触发一次。** 处理不好就会“按了取消反而把值提交了”。

::: tip 什么时候该用 UI 组件库的表格
本案例是手写表格，因为要讲清楚“编辑态怎么管、失焦怎么提交、回滚怎么算”这些机制。真实项目里如果只是常规的增删改查，直接用 Element Plus 2.14.5 的表格组件更省时间 —— 它已经内置了单元格编辑、校验、排序和分页。

判断标准是：**这套交互是这个项目的特色，还是行业通用做法？** 通用的就交给组件库，把时间花在业务规则上；只有组件库满足不了的特殊交互（比如前面[案例 08 的画板](/cases/08-canvas)），才值得自己写。**“能讲清楚原理”和“每个项目都从零写”是两回事。**
:::


### 用到的知识点 → 对应章节

| 用到的知识点 | 对应章节 |
| --- | --- |
| `v-for` 列表渲染与 `:key` 的选择 | [5.4 列表渲染与键值](/unit05/04-list) |
| `v-model` 在表单元素上的用法 | [6.3 表单绑定](/unit06/03-form-binding) |
| `v-model.number` 等修饰符 | [6.3 表单绑定](/unit06/03-form-binding) |
| 事件修饰符与按键修饰符 | [6.2 事件与按键修饰符](/unit06/02-modifiers) |
| 表单校验与错误提示 | [6.4 表单校验](/unit06/04-validation) |
| 子组件 props / emits 通信 | [7.2 props](/unit07/02-props) · [7.3 emits](/unit07/03-emits) |
| 组件上的 `v-model` | [7.4 组件上的 v-model](/unit07/04-vmodel) |
| 模板引用与 `nextTick` | [4.4 ref 与 reactive](/unit04/04-reactivity) |
| 复用通知组件提示结果 | [案例 06 · 模态框与全局通知](/cases/06-modal) |

## 数据结构与接口设计

### 行数据

一行就是一条场次记录：

```js [一条场次记录的字段]
{
  id: 3,                    // 唯一且稳定，绝不能用数组下标
  venue: '大学生活动中心 301',
  date: '2026-10-12',
  start: '14:00',
  end: '16:00',
  capacity: 80
}
```

`id` 的“稳定”是硬要求：**只要这一行的 `id` 不变，无论它在数组里排第几，Vue 都认为它是同一行。** 这是后面所有编辑态能定位准确的前提。

### 场地与容量

场地是下拉选项，每个场地有自己的容量上限，校验要用：

```js [src/views/session/venues.js]
export const VENUES = [
  { value: '大学生活动中心 301', label: '大学生活动中心 301', capacity: 200 },
  { value: '大学生活动中心 报告厅', label: '大学生活动中心 报告厅', capacity: 500 },
  { value: '体育馆 主馆', label: '体育馆 主馆', capacity: 800 },
  { value: '文科楼 102', label: '文科楼 102', capacity: 60 },
  { value: '图书馆 报告厅', label: '图书馆 报告厅', capacity: 120 }
]

export function findVenue(name) {
  return VENUES.find((item) => item.value === name)
}
```

### 列配置

列也是一份数据。表格和人一样，**只认配置，不认具体的字段名**，这样加一列只需要改数组。

```js [src/views/session/columns.js]
import { VENUES } from './venues'

export const COLUMNS = [
  {
    key: 'venue',
    title: '场地',
    type: 'select',
    width: 200,
    options: VENUES.map((v) => ({ value: v.value, label: v.label }))
  },
  { key: 'date', title: '日期', type: 'date', width: 150 },
  { key: 'start', title: '开始', type: 'time', width: 110 },
  { key: 'end', title: '结束', type: 'time', width: 110 },
  { key: 'capacity', title: '容纳人数', type: 'number', width: 110 }
]
```

### 编辑态

**整个表格同一时刻只有一个单元格在编辑。** 所以编辑态不需要存在每一行里，它是一份全局的定位信息：

```js [编辑态的形状]
{
  rowId: 3,        // null 表示当前没有单元格在编辑
  field: 'venue'
}
```

为什么不做成“每行一个 `editingField`”？因为那样用户可以同时打开好几个编辑框，两处都改了值、都提交，冲突时谁的算数？**单编辑态是一个有意的约束**，它把问题从“怎么合并多个修改”简化成“现在改哪一个”。

### 校验规则

校验函数统一约定：通过返回 `true`，不通过返回一句提示。

```js [src/views/session/validateRow.js]
import { findVenue } from './venues'

const CAPACITY_LIMIT = 2000

export function validateField(row, field) {
  if (field === 'venue') {
    if (!row.venue) return '请选择场地'
    return true
  }

  if (field === 'date') {
    if (!row.date) return '请选择日期'
    return true
  }

  if (field === 'start' || field === 'end') {
    if (!row.start || !row.end) return '开始和结束时间都要填'
    // 字符串比较在这里成立，因为都是 HH:mm 格式
    if (row.start >= row.end) return '结束时间要晚于开始时间'
    return true
  }

  if (field === 'capacity') {
    const value = Number(row.capacity)
    if (!Number.isInteger(value) || value <= 0) return '容纳人数要填正整数'
    if (value > CAPACITY_LIMIT) return `容纳人数不要超过 ${CAPACITY_LIMIT}`
    const venue = findVenue(row.venue)
    if (venue && value > venue.capacity) {
      return `${venue.label} 最多容纳 ${venue.capacity} 人`
    }
    return true
  }

  return true
}

// 提交整表前跑一遍，返回第一处问题所在的行与提示
export function validateAll(rows) {
  for (const row of rows) {
    for (const field of ['venue', 'date', 'start', 'end', 'capacity']) {
      const result = validateField(row, field)
      if (result !== true) {
        return { rowId: row.id, field, message: result }
      }
    }
  }
  return null
}
```

两条时间都用 `HH:mm` 格式，所以 `'09:00' < '11:00'` 这样的字符串比较是成立的。**如果时间带上了日期，就必须换成 `Date` 对象比较**，字符串比较会出错。

### 接口约定

```js [src/api/session.js]
import request from './request'

// 整表保存：一次性提交所有场次，失败时整批不生效
export function saveSessions(activityId, sessions) {
  return request.put(`/api/activity/${activityId}/sessions`, { sessions })
}

// 单独删除一行
export function deleteSession(sessionId) {
  return request.delete(`/api/session/${sessionId}`)
}
```

::: tip 为什么不每改一格就存一次
可编辑表格有两种保存策略，选哪个取决于数据之间有没有关联：

| 策略 | 怎么存 | 适合的场景 | 代价 |
| --- | --- | --- | --- |
| 逐格保存 | 单元格提交时立刻调接口 | 字段之间互不影响，比如备注、标签 | 请求多，一次误操作无法整体撤销 |
| 整表保存 | 改完点“保存”，一次性提交 | 字段之间有校验关系，比如时段冲突、人数与场地容量 | 用户不点保存就离开会丢改动 |

本案例选整表保存，因为**时段冲突是一条跨行的规则**。如果逐格保存，用户改了第 2 行的开始时间，冲突检测要立刻告诉第 3 行有问题，而第 3 行的数据可能还没提交，前后端状态会对不上。

逐格保存的方案也有它的麻烦：每个请求都要处理失败回滚、都要考虑并发顺序。**数据之间有关联就整表存，没有关联再考虑逐格存**，这是一条很实用的判断。
:::


## 实现步骤

### 第一步：用一份配置渲染整张表

表格的每一列都由 `COLUMNS` 决定，单元格交给一个可编辑单元格组件。**父组件只关心“现在哪一行哪一列在编辑”，渲染细节都在子组件里。**

```vue [src/views/session/SessionTableView.vue（骨架）]
<script setup>
import { reactive, ref } from 'vue'
import EditableCell from './EditableCell.vue'
import { COLUMNS } from './columns'
import { validateField, validateAll } from './validateRow'
import { saveSessions } from '@/api/session'
import { toast } from '@/composables/useToast'

const props = defineProps({
  activityId: { type: [Number, String], required: true },
  initialSessions: { type: Array, default: () => [] }
})

let rowSeed = props.initialSessions.length

const rows = ref(
  props.initialSessions.map((item, index) => ({ ...item, id: item.id ?? index + 1 }))
)

// 单编辑态：整张表只有一个格子在编辑
const editing = reactive({ rowId: null, field: null })

const selectedIds = ref([])

function isEditing(row, column) {
  return editing.rowId === row.id && editing.field === column.key
}

function startEdit(row, column) {
  editing.rowId = row.id
  editing.field = column.key
}

function exitEdit() {
  editing.rowId = null
  editing.field = null
}
</script>

<template>
  <table class="grid">
    <thead>
      <tr>
        <th class="grid__check">
          <input type="checkbox" :checked="allSelected" @change="toggleAll" />
        </th>
        <th v-for="column in COLUMNS" :key="column.key" :style="{ width: `${column.width}px` }">
          {{ column.title }}
        </th>
        <th>操作</th>
      </tr>
    </thead>

    <tbody>
      <tr v-for="row in rows" :key="row.id">
        <td class="grid__check">
          <input
            type="checkbox"
            :checked="selectedIds.includes(row.id)"
            @change="toggleRow(row.id)"
          />
        </td>

        <td
          v-for="column in COLUMNS"
          :key="column.key"
          :class="{ 'is-editing': isEditing(row, column) }"
        >
          <EditableCell
            :model-value="row[column.key]"
            :editing="isEditing(row, column)"
            :type="column.type"
            :options="column.options || []"
            @start-edit="startEdit(row, column)"
            @commit="(value, meta) => commitCell(row, column, value, meta)"
            @cancel="exitEdit"
          />
        </td>

        <td>
          <button type="button" @click="removeRow(row)">删除</button>
        </td>
      </tr>
    </tbody>
  </table>
</template>
```

`v-for="row in rows" :key="row.id"` 这一行是关键。下一节会专门用一个反例说明，把它换成 `:key="index"` 会发生什么。

### 第二步：可编辑单元格组件

单元格组件负责三件事：只读态显示文本、编辑态渲染对应的输入控件、把键盘操作翻译成事件。

```vue [src/views/session/EditableCell.vue]
<script setup>
import { computed, nextTick, ref, watch, useTemplateRef } from 'vue'

const props = defineProps({
  modelValue: { type: [String, Number], default: '' },
  editing: { type: Boolean, default: false },
  type: { type: String, default: 'text' }, // text | number | date | time | select
  options: { type: Array, default: () => [] },
  placeholder: { type: String, default: '' }
})

const emit = defineEmits(['start-edit', 'commit', 'cancel'])

const inputRef = useTemplateRef('input')
const draft = ref(props.modelValue)

// 两个一次性标记：防止同一个编辑过程被提交或取消两次
let committed = false
let cancelled = false

const displayText = computed(() => {
  if (props.type === 'select') {
    const hit = props.options.find((item) => item.value === props.modelValue)
    return hit ? hit.label : ''
  }
  return props.modelValue === '' || props.modelValue === null
    ? ''
    : String(props.modelValue)
})

// 进入编辑态时：清标记、把当前值拷进草稿、聚焦输入框
watch(
  () => props.editing,
  async (editing) => {
    if (!editing) return
    committed = false
    cancelled = false
    draft.value = props.modelValue
    await nextTick()
    inputRef.value?.focus()
    inputRef.value?.select?.()
  }
)

function submit({ moveDown = false } = {}) {
  if (committed || cancelled) return
  committed = true
  emit('commit', draft.value, { moveDown })
}

function cancelEdit() {
  if (committed || cancelled) return
  cancelled = true
  emit('cancel')
}

// 失焦也算提交，但已经被提交或取消过就不再重复
function onBlur() {
  submit()
}

function onKeydown(event) {
  if (event.key === 'Enter') {
    // 阻止回车触发表单提交或换行
    event.preventDefault()
    submit({ moveDown: true })
  } else if (event.key === 'Escape') {
    event.preventDefault()
    cancelEdit()
  }
}

function onCellClick() {
  if (!props.editing) emit('start-edit')
}
</script>

<template>
  <div class="cell" :title="displayText" @click="onCellClick">
    <template v-if="!editing">
      <span v-if="displayText !== ''">{{ displayText }}</span>
      <span v-else class="cell__placeholder">{{ placeholder || '未填写' }}</span>
    </template>

    <template v-else>
      <select
        v-if="type === 'select'"
        ref="input"
        v-model="draft"
        class="cell__control"
        @blur="onBlur"
        @keydown="onKeydown"
      >
        <option value="">请选择</option>
        <option v-for="item in options" :key="item.value" :value="item.value">
          {{ item.label }}
        </option>
      </select>

      <input
        v-else-if="type === 'number'"
        ref="input"
        v-model.number="draft"
        class="cell__control"
        type="number"
        min="1"
        @blur="onBlur"
        @keydown="onKeydown"
      />

      <input
        v-else
        ref="input"
        v-model="draft"
        class="cell__control"
        :type="type"
        @blur="onBlur"
        @keydown="onKeydown"
      />
    </template>
  </div>
</template>

<style scoped>
.cell {
  min-height: 34px;
  padding: 6px 8px;
  cursor: text;
}

.cell:hover {
  background: #f5f7fa;
}

.cell__placeholder {
  color: #c0c4cc;
}

.cell__control {
  width: 100%;
  box-sizing: border-box;
  padding: 4px 6px;
  border: 1px solid #42b883;
  border-radius: 4px;
}
</style>
```

这里有两个容易写错的地方。

**第一，`Enter` 的处理。** 它同时会做两件事：提交，以及通知父组件把编辑态移到下一行。但输入框一旦失焦，`blur` 也会跑到 `onBlur` 里再提交一次。所以 `submit()` 里要先检查 `committed`，第二次直接返回。

**第二，`Esc` 的处理。** 按 `Esc` 后，输入框会被父组件换成只读文本，这个替换过程可能触发一次 `blur`。如果 `blur` 的处理函数不看标记，就会把用户刚取消掉的值又提交上去 —— 表现就是“按 `Esc` 没取消成，反而改了”。加上 `cancelled` 标记后，`onBlur` 里的 `submit()` 会被挡住。

::: tip 为什么标记用普通变量而不是 `ref`
`committed`、`cancelled` 只在一段很短的事件处理流程里被读写，**不需要参与模板渲染**。用普通变量省掉一层响应式代理，也更清楚地表达“这个值只对逻辑有意义”。**只有需要在模板里显示、或者在多次渲染之间保持一致的状态，才需要是响应式的。**
:::

### 第三步：提交与回滚

提交包含“校验”和“落值”两步。**校验不通过时什么也不改**，这就是“回滚原值”最省事的实现方式 —— 值从来没被污染过，自然不需要回滚。

```js [src/views/session/SessionTableView.vue（提交逻辑）]
function commitCell(row, column, value, meta = {}) {
  // 同一个编辑态里的提交只认第一次
  const snapshot = { ...row }

  // 先把草稿写进一个临时对象，用真实数据做校验
  const candidate = { ...row, [column.key]: value }
  const result = validateField(candidate, column.key)

  if (result !== true) {
    // 校验不通过：不改 row，直接退出编辑态，原值原样保留
    toast.error(result)
    exitEdit()
    return
  }

  // 校验通过才真正落值
  Object.assign(row, candidate)
  exitEdit()

  // 回车提交后移动到下一行的同一列
  if (meta.moveDown) {
    focusNextRow(row, column.key)
  }

  // 留个痕迹，方便排查“到底改了哪一行”
  console.debug('updated', snapshot.id, column.key, snapshot[column.key], '→', value)
}

function focusNextRow(row, field) {
  const index = rows.value.findIndex((item) => item.id === row.id)
  const next = rows.value[index + 1]
  if (!next) return
  editing.rowId = next.id
  editing.field = field
}
```

`validateField` 接收的是一个**完整的行对象**，而不是单个值。这样“容纳人数不能超过场地容量”这类**跨字段规则**才能算出来 —— 它要同时看 `capacity` 和 `venue`。这也是为什么校验函数不设计成 `validate(value)` 的原因。

### 第四步：为什么 `key` 必须用 `id`

这是本案例最重要的一个坑，单独拿出来说。假设表格写成这样：

```vue [✗ 用下标当 key]
<tr v-for="(row, index) in rows" :key="index">
```

编辑态也用下标记录：

```js [✗ 配套的错误编辑态]
const editing = reactive({ rowIndex: null, field: null })
```

平时看起来没问题，一旦**在数组顶部插入一行**，问题就出来了：

```js [新增一行时发生的事]
function addRow() {
  rows.value.unshift({ id: ++rowSeed, venue: '', date: '', start: '', end: '', capacity: 0 })
  // 想编辑新插入的这行，也就是下标 0
  editing.rowIndex = 0
  editing.field = 'venue'
}
```

插入之后，原来的第 0 行变成了第 1 行，但 `editing.rowIndex` 是 `0`，指向的是**新插入的那一行** —— 这一次碰巧是对的。真正的麻烦在别的地方：

- 用户在第 2 行（下标 2）的输入框里打字，还没提交，这时列表因为别的原因（比如刷新了数据）在顶部插入了一行。
- 原来的下标 2 变成了下标 3，但 `editing.rowIndex` 还是 `2`。
- **输入框瞬间“跳”到了上一行上**，用户打了一半的字出现在错误的位置。这就是“编辑态串行”。

换成 `id` 之后，定位信息是“第 3 号场次”，无论它在数组里排第几，编辑框都不会跑错：

```vue [✓ 用 id 当 key]
<tr v-for="row in rows" :key="row.id">
```

```js [✓ 编辑态也用 id]
const editing = reactive({ rowId: null, field: null })
```

::: warning 用 `index` 当 `key` 什么时候不算错
如果列表**只读**、或者虽然可编辑但**永远只追加在末尾、从不插入和删除**，用下标当 `key` 确实不会出问题。但这样的前提非常脆弱 —— 只要需求加一句“支持在中间插入”，代码就得推倒重来。

**判断标准很简单：只要列表会增删、会排序、会筛选，就必须用稳定的业务 `id`。** 新数据还没有 `id` 时，也要在创建的那一刻生成一个（可以用 `crypto.randomUUID()`），不要退回下标。这条规则在[5.4 列表渲染](/unit05/04-list)里讲过原理，这里看到的是它在真实界面上的后果。
:::

### 第五步：行内新增一行

新增的关键不是 `push`，而是**新增之后立刻进入编辑态**，让用户能直接开始填。

```js [src/views/session/SessionTableView.vue（新增与删除）]
function addRow() {
  const row = {
    id: crypto.randomUUID(),
    venue: '',
    date: '',
    start: '',
    end: '',
    capacity: 0
  }
  // 插到最前面：新加的通常最需要马上填
  rows.value = [row, ...rows.value]
  // 直接进入第一列的编辑态
  editing.rowId = row.id
  editing.field = COLUMNS[0].key
}

function removeRow(row) {
  const index = rows.value.findIndex((item) => item.id === row.id)
  if (index === -1) return
  rows.value = rows.value.filter((item) => item.id !== row.id)
  selectedIds.value = selectedIds.value.filter((id) => id !== row.id)
  // 删掉的正好是正在编辑的那一行，要把编辑态收掉
  if (editing.rowId === row.id) exitEdit()
}
```

注意最后那句判断：**删除的行可能就是正在编辑的行。** 如果不把 `editing` 清掉，它会指向一个已经不存在的 `id`，界面上没有格子处于编辑态，但状态还留着，下次新增一行时如果 `id` 恰好复用（用自增数字时很容易）就会意外进入编辑。

用 `crypto.randomUUID()` 生成 `id` 也能顺带避开这个问题，因为几乎不会重复。

### 第六步：批量编辑与逐行回滚

勾选多行后统一设置某个字段。批量操作和单格提交的区别在于：**它是先全部写入，再逐行校验，不合格的当场回滚。**

```js [src/views/session/SessionTableView.vue（批量编辑）]
import { computed } from 'vue'

const allSelected = computed(
  () => rows.value.length > 0 && selectedIds.value.length === rows.value.length
)

function toggleAll(event) {
  selectedIds.value = event.target.checked ? rows.value.map((row) => row.id) : []
}

function toggleRow(id) {
  selectedIds.value = selectedIds.value.includes(id)
    ? selectedIds.value.filter((item) => item !== id)
    : [...selectedIds.value, id]
}

/**
 * 批量设置某个字段。逐行校验，不合格的行回滚成原值并计数
 * @returns {{ changed: number, failed: number }}
 */
function batchUpdate(field, value) {
  const targets = rows.value.filter((row) => selectedIds.value.includes(row.id))
  let changed = 0
  let failed = 0

  for (const row of targets) {
    const original = row[field]
    // 先写入，再校验：批量操作必须能看到“改完之后”的状态
    row[field] = value
    const result = validateField(row, field)
    if (result === true) {
      changed += 1
    } else {
      // 回滚这一行，其他行不受影响
      row[field] = original
      failed += 1
    }
  }

  if (changed > 0) toast.success(`已更新 ${changed} 行`)
  if (failed > 0) toast.warning(`${failed} 行不满足规则，已保留原值`)
  return { changed, failed }
}
```

批量操作里有一个单格编辑没有的问题：**`row[field] = value` 是直接改数据的，一旦校验失败，数据已经被污染了。** 所以必须先存一份 `original`，失败时立刻写回去。

如果字段本身是个对象（比如整体替换场次的时间段），`original` 存的会是同一个引用，回滚时写回去也没用。这时要**深拷贝**：

```js [字段是对象时的回滚]
const original = structuredClone(row[field])
// ……
row[field] = original
```

`structuredClone` 是浏览器原生提供的深拷贝方法，比 `JSON.parse(JSON.stringify(x))` 更可靠（能处理 `Date`、`Map`、循环引用等）。

## 完整代码

目录结构：

```text [src/]
src/
├── api/
│   └── session.js
├── composables/
│   └── useToast.js
└── views/
    └── session/
        ├── SessionTableView.vue
        ├── EditableCell.vue
        ├── columns.js
        ├── venues.js
        └── validateRow.js
```

`EditableCell.vue`、`columns.js`、`venues.js`、`validateRow.js`、`api/session.js` 的完整内容就是前面各部分给出的样子，不再重复。

`SessionTableView.vue` 需要把下面几块拼在一起：

1. `<script setup>`：引入组件、数据、校验、接口与通知。
2. 状态：`rows`、`editing`、`selectedIds` 三个，外加派生的 `allSelected`。
3. 编辑相关方法：`isEditing`、`startEdit`、`exitEdit`、`commitCell`、`focusNextRow`。
4. 行相关方法：`addRow`、`removeRow`。
5. 选择与批量：`toggleAll`、`toggleRow`、`batchUpdate`。
6. 整表保存：调用 `validateAll`，有问题的跳到那一行并提示。

整表保存的方法补在这里：

```js [src/views/session/SessionTableView.vue（保存）]
const saving = ref(false)

async function handleSave() {
  if (rows.value.length === 0) {
    toast.warning('至少要保留一个场次')
    return
  }

  const problem = validateAll(rows.value)
  if (problem) {
    // 把编辑态定位到出问题的那一格，用户不用自己找
    editing.rowId = problem.rowId
    editing.field = problem.field
    toast.error(problem.message)
    return
  }

  saving.value = true
  try {
    await saveSessions(props.activityId, rows.value)
    toast.success('场次安排已保存')
  } catch (error) {
    toast.error(error.message, 0)
  } finally {
    saving.value = false
  }
}
```

模板里再加上批量操作条：

```vue [src/views/session/SessionTableView.vue（批量操作条）]
<template>
  <div class="session-table">
    <div class="bulk-bar">
      <span>已选 {{ selectedIds.length }} 行</span>
      <button
        type="button"
        :disabled="selectedIds.length === 0"
        @click="batchUpdate('date', '2026-10-12')"
      >
        统一设为 10 月 12 日
      </button>
      <button
        type="button"
        :disabled="selectedIds.length === 0"
        @click="batchUpdate('capacity', 50)"
      >
        统一设为 50 人
      </button>
      <span class="bulk-bar__spacer" />
      <button type="button" @click="addRow">新增场次</button>
      <button type="button" :disabled="saving" @click="handleSave">保存</button>
    </div>

    <!-- 表格部分同上，省略 -->
  </div>
</template>
```

跑起来之后的效果：点任意单元格进入编辑，按 `Enter` 提交并跳到下一行同一列，按 `Esc` 取消；填了 300 人但场地只能容纳 200 人时会提示并保留原值；勾选几行点“统一设为 50 人”，其中场地装不下的行不会被改，最后告诉你改了几行、几行没改。

## 常见坑

::: details 坑 1：`v-for` 用下标当 `key`，插入一行后编辑框跑错地方
**现象**：在表格顶部新增一行，正在编辑的输入框出现在另一行上；或者用户在第 3 行打字，列表刷新后字跑到了第 2 行。

**原因**：下标 `key` 表达的是“位置”，不是“身份”。插入或删除之后，位置对应的数据变了，但编辑态记录的还是旧位置。

**怎么处理**：`:key` 用稳定的业务 `id`，编辑态也记 `id`。新增的数据如果没有 `id`，就用 `crypto.randomUUID()` 生成一个。**这条规则在“会增删的列表”上没有例外。**
:::

::: details 坑 2：按 `Esc` 之后值反而被提交了
**现象**：明明按的是取消，退出编辑后发现值变了。

**原因**：按 `Esc` 让输入框失去焦点，`blur` 事件随后触发，把草稿又提交了一次。

**怎么处理**：加一个“已经取消过”的标记，`blur` 的处理函数看到标记就直接返回。本案例里是 `cancelled` 变量。**同类问题也会出现在 `Enter` 提交上，所以 `committed` 标记同样不能省。**
:::

::: details 坑 3：`v-model.number` 把空输入变成了空字符串
**现象**：数字列清空后，校验提示“容纳人数要填正整数”，这没问题；但后端收到的字段类型一会儿是 `number`、一会儿是 `string`。

**原因**：`v-model.number` 的规则是“能转成数字就转成数字，转不了就保留原始字符串”。输入框清空时，值是 `''`，它转不成数字，于是保留成空字符串。

**怎么处理**：校验时统一用 `Number(row.capacity)` 转换一次再判断，别直接依赖“值一定是数字”。提交前也可以统一做一次格式整理，把空字符串转成 `null`。**前端状态里混着两种类型，是很多诡异 bug 的来源。**
:::

::: details 坑 4：点击单元格里的下拉框，编辑态马上就没了
**现象**：场地列点开下拉，还没选，编辑框就关闭了。

**原因**：`blur` 和 `click` 的执行顺序是先 `blur` 后 `click`。点击下拉选项时，输入控件先失去焦点，`blur` 触发了提交，编辑态退出，后面的点击落在了一个已经变成文本的单元格上。

**怎么处理**：用 `blur` 提交时，**不要在 `blur` 里立即销毁编辑态**，而是先提交、由父组件决定。原生 `<select>` 的选项弹出属于系统层，一般不会触发 `blur`；真正容易出问题的是自定义下拉组件。这种情况通常改用 `mousedown.prevent` 阻止默认行为，或者延迟一小段时间再处理 `blur`。**能用原生控件就别自己写下拉。**
:::

::: details 坑 5：校验失败的提示刷屏
**现象**：批量改 20 行，19 行不合法，右下角一下子冒出 19 条红色提示。

**原因**：在循环里逐行弹通知，一行一条。

**怎么处理**：循环里只做计数，循环结束后统一报一次：“已更新 1 行，19 行不满足规则，已保留原值”。**用户需要的是结论，不是流水账。** 这也是[案例 06 的通知队列](/cases/06-modal)里“通知要做队列管理”的一个现实理由。
:::

::: details 坑 6：用 `Set` 存选中行，界面不更新
**现象**：`selectedIds` 用 `reactive(new Set())`，勾选后 `selectedIds.size` 变了，但界面上“已选几行”和行高亮都不动。

**原因**：Vue 3 的响应式系统确实支持 `Set` 和 `Map` 的方法，但**前提是通过响应式代理去调用方法**。如果代码里拿的是原始 `Set` 的引用（比如在外面建好再传进来），改动就不会被追踪。

**怎么处理**：存选中项用**数组**最简单也最不容易错，本文就是这么做的。非要用 `Set`，就确保所有增删都走 `reactive` 包装后的对象，而不是原始对象。
:::

::: details 坑 7：回车提交时整个页面刷新了
**现象**：在单元格里按回车，页面重新加载，未保存的修改全丢。

**原因**：表格如果被包在 `<form>` 里，输入框按回车会触发表单的默认提交行为。

**怎么处理**：在 `keydown` 里判断到 `Enter` 时调用 `event.preventDefault()`。如果外面确实有表单，把表单的 `@submit.prevent` 也加上。**两个都加上最稳妥**，因为不同浏览器对“回车提交表单”的行为不完全一致。
:::

## 扩展练习

::: details 练习 1：用 Tab 在单元格之间移动
现在 `Tab` 会把焦点移出表格。改成：`Tab` 提交当前格并进入右边一格，在最后一列按 `Tab` 进入下一行第一列；`Shift + Tab` 反向移动。

**思路**：需要在单元格组件里拦截 `Tab`，`preventDefault()` 之后把“往哪个方向移动”告诉父组件。父组件根据当前列的下标算出目标位置。难点在边界：最后一行的最后一格按 `Tab` 该去哪儿？**想清楚这个边界，比写完整个功能更有价值。**
:::

::: details 练习 2：支持单元格复选和批量粘贴
允许用户从 Excel 里复制一块数据，粘贴到表格的某个区域，自动按行列铺开。

**思路**：监听 `paste` 事件，从 `event.clipboardData.getData('text/plain')` 拿到的是制表符分隔、换行分隔的纯文本，解析成二维数组即可。要注意三件事：粘贴的块可能超出表格范围、粘贴进来的值要逐格校验、粘贴应该算**一步操作**（能整体撤销）。这是“批量编辑”的进阶版本。
:::

::: details 练习 3：让编辑态支持撤销
在表格上方加“撤销”按钮，可以退回上一次修改。

**思路**：可以直接复用[案例 08 的命令栈](/cases/08-canvas)思路：每个 `commitCell` 生成一条 `{ type: 'update', rowId, field, from, to }` 的命令。批量操作生成一条覆盖多行的命令。想一下“撤销之后，如果那一行已经被删除了”该怎么处理 —— 命令里存的是 `rowId`，找不到时跳过还是报错，需要你决定。
:::

::: details 练习 4：给单元格加自定义校验
现在的校验写在 `validateRow.js` 里，只认固定的几个字段。改成允许列配置里带上校验函数：

```js
{
  key: 'capacity',
  title: '容纳人数',
  type: 'number',
  rules: [
    { test: (v) => Number(v) > 0, message: '容纳人数要填正整数' },
    { test: (v, row) => Number(v) <= findVenue(row.venue)?.capacity, message: '超过场地容量' }
  ]
}
```

**思路**：把规则设计成 `(value, row) => boolean` 的形式，第二个参数传整行数据，跨字段规则就能写。改完之后想一个问题：**当列配置来自后端接口时，这种“把函数放在数据里”的做法还行不行？** 如果不行，就要换一套“规则标识 + 参数”的描述方式。
:::

---

上一页：[案例 08 · 画板与撤销重做](/cases/08-canvas) · 下一页：[案例 10 · 登录鉴权](/cases/10-auth)
