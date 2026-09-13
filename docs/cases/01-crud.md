# 案例 01 · 增删改查清单

## 案例要做什么

校园歌手大赛要安排三个场次：初赛、复赛、决赛。每个场次有名称、场地、起止时间、名额上限。
组织者需要一个页面，能在里面新增场次、当场改几个字、删掉排错的场次，并且能一次勾选多条批量删除。

功能不复杂，但它把 Vue 里最高频的几件事全用上了：**列表渲染、条件渲染、事件处理、表单绑定**。
这个案例的目标不是写出多漂亮的界面，而是把“数据变了页面就变”这条线走顺 —— 后面所有页面都是它的放大版。

| 知识点 | 用在哪里 | 对应章节 |
| --- | --- | --- |
| `v-for` 与 `:key` 的选择 | 渲染场次列表 | [列表渲染与键值](/unit05/04-list) |
| `v-if` / `v-else` / `v-else-if` | 空状态、编辑态与展示态互斥 | [条件渲染](/unit05/03-conditional) |
| `computed` | 全选状态、半选状态、已选条数 | [计算属性与缓存](/unit05/01-computed) |
| `ref` 数组的增删改 | 新增、单条删除、批量删除 | [ref 与 reactive](/unit04/04-reactivity) |
| 事件处理 | 点击、勾选、提交 | [事件处理的完整写法](/unit06/01-events) |
| `v-model` 与修饰符 | 编辑表单的输入绑定 | [表单绑定](/unit06/03-form-binding) |

::: tip 这个案例不需要后端
数据先放在组件里的 `ref` 数组，刷新页面会回到初始状态。真实项目里这些数据来自接口，
换成请求的写法在[案例 04](/cases/04-fetch)里。
:::

## 数据结构与接口设计

**先定数据，再写界面。** 这一步做对了，后面大部分纠结都会消失。

一条场次记录长这样：

```js [场次的数据结构]
/**
 * 场次
 * @typedef {Object} Session
 * @property {string} id        唯一标识，新增时生成
 * @property {string} name      场次名称，如“初赛”
 * @property {string} venue     场地名称
 * @property {string} startAt   开始时间，格式 YYYY-MM-DD HH:mm
 * @property {string} endAt     结束时间，格式 YYYY-MM-DD HH:mm
 * @property {number} capacity  名额上限
 */
```

三个设计决定，先想清楚理由：

| 决定 | 选了什么 | 为什么 |
| --- | --- | --- |
| 时间用什么存 | 固定格式的字符串 `YYYY-MM-DD HH:mm` | 显示时不用转换，先后比较直接比字符串；真实项目里接口传的是时间戳或 ISO 串，取到后统一转一次 |
| `id` 从哪来 | 前端生成 | 这个案例没有后端；接了后端之后由后端返回，前端要做的只是**别再拿数组下标当身份** |
| 编辑时的数据怎么存 | 复制一份新对象 | 直接改原对象的话，用户点“取消”就回不去了 |

业务规则集中在一次校验里，先写下来，别散落在各个 `click` 处理函数里：

- 名称、场地不能为空。
- 结束时间必须晚于开始时间。
- 名额必须是大于 0 的整数。

## 实现步骤

### 步骤 1 · 用 `ref` 存列表，用 `computed` 存“派生出来的状态”

列表本身是数据，勾选状态也是数据，但“是否全选”不是 —— 它能由前两者算出来。**能算出来的东西不要单独存一份**，
否则两份数据迟早不同步。

```js [状态定义]
const sessions = ref([/* 三条初始场次 */])
const checkedIds = ref([])   // 只存被勾选的 id，不存整条记录
const editingId = ref('')    // 当前正在编辑哪一行，空字符串表示没有
const draft = ref(emptyDraft())
const formError = ref('')

const checkedCount = computed(() => checkedIds.value.length)

const isAllChecked = computed(
  () => sessions.value.length > 0 && checkedIds.value.length === sessions.value.length
)

// 全选框有三种外观：全选、一个没选、选了一部分（半选）
const isIndeterminate = computed(() => checkedCount.value > 0 && !isAllChecked.value)
```

注意 `checkedIds` 里存的是 **id 而不是数组下标**。原因是删除一条记录后，后面的下标整体前移，
存下标的勾选状态会“串位” —— 用户删掉第二条，第三条的勾选状态会莫名其妙跑到第四条上。

### 步骤 2 · 列表渲染与空状态：`v-if` 和 `v-else` 是一对

空列表如果什么都不画，用户会以为页面坏了。所以空状态和表格是互斥的两个分支：

```vue [空状态与表格互斥]
<p v-if="sessions.length === 0 && editingId !== NEW_ROW" class="empty">
  还没有场次，点右上角“新增场次”开始安排。
</p>
<table v-else class="grid">
  <!-- 列表 -->
</table>
```

`v-if` 的条件里为什么还要带上 `editingId !== NEW_ROW`？因为要处理一个边界情况：
**列表为空时点“新增场次”，如果还显示空状态，用户就看不到刚弹出的输入行了。**
加了这一个条件，空列表也能进入编辑态；取消之后又自动回到空状态。

### 步骤 3 · 勾选、全选与批量删除

全选框和每一行的复选框都要和 `checkedIds` 保持同步。全选框不能直接 `v-model` 到数组上，
因为它只能表达“选中 / 未选中”两种状态，而第三种状态（选了一部分）要靠 DOM 属性表达：

```vue [全选框]
<input
  type="checkbox"
  :checked="isAllChecked"
  :indeterminate="isIndeterminate"
  @change="toggleAll"
/>
```

```js [toggleAll]
function toggleAll(event) {
  checkedIds.value = event.target.checked ? sessions.value.map((item) => item.id) : []
}
```

行内的复选框就简单了 —— 一组复选框绑定同一个数组，用 `:value` 声明各自的取值：

```vue [行内复选框]
<input v-model="checkedIds" type="checkbox" :value="session.id" />
```

批量删除时要同步清理 `checkedIds`，否则里面会残留已经不存在的 id，导致“全选框看起来没选中，
但已选数量显示 2”这种怪状态：

```js [批量删除]
function removeChecked() {
  const removing = new Set(checkedIds.value)
  sessions.value = sessions.value.filter((item) => !removing.has(item.id))
  checkedIds.value = []
  if (removing.has(editingId.value)) cancelEdit()
}
```

### 步骤 4 · 新增：和编辑共用一套表单

新增行和编辑行长得几乎一样，只有“保存时是 push 还是替换”这一点区别。所以用同一个 `draft` 对象、
同一个 `save()` 函数，用一个特殊值 `NEW_ROW` 标记“这是新增”：

```js [save]
const NEW_ROW = '__new__'

function save() {
  const message = validate(draft.value)
  if (message) {
    formError.value = message
    return
  }
  const payload = { ...draft.value, capacity: Number(draft.value.capacity) }

  if (editingId.value === NEW_ROW) {
    sessions.value.push({ ...payload, id: `s-${Date.now()}` })
  } else {
    const index = sessions.value.findIndex((item) => item.id === editingId.value)
    if (index > -1) sessions.value[index] = { ...payload, id: editingId.value }
  }
  cancelEdit()
}
```

### 步骤 5 · 编辑：行内编辑还是弹窗编辑

这是本案例唯一需要“做取舍”的地方，两种做法各有适用场景：

| 做法 | 优点 | 缺点 | 适合 |
| --- | --- | --- | --- |
| 行内编辑 | 不打断视线，改一两个字最快 | 字段一多，行会变得很宽；表头列宽会被输入框撑变形 | 字段少（不超过 4 个）、以改字为主 |
| 弹窗编辑 | 有足够空间放校验提示和复杂控件；不会被表格挤 | 每次编辑都要开关一次弹窗 | 字段多、要上传附件、要联动选择 |

这个案例只有 5 个字段，选**行内编辑**。实现方式是每行内部再分两个分支：`editingId === session.id`
时渲染输入框，否则渲染文本：

```vue [编辑态切换]
<tr v-for="session in sessions" :key="session.id">
  <template v-if="editingId === session.id">
    <td><input v-model="draft.name" class="input" /></td>
    <!-- 其余输入框 -->
  </template>
  <template v-else>
    <td>{{ session.name }}</td>
    <!-- 其余文本 -->
  </template>
</tr>
```

进入编辑态时，**一定要复制一份，不要直接引用原对象**：

```js [startEdit]
function startEdit(session) {
  editingId.value = session.id
  draft.value = { ...session }   // ✓ 复制一份
  // draft.value = session        // ✗ 取消时改动已经写回原数据，回不去了
  formError.value = ''
}
```

### 步骤 6 · 校验：把规则收在一处

校验函数收在一处，新增和编辑都能用，将来接口端加了同样的规则，前端改一个地方就行：

```js [validate]
function validate(data) {
  if (!data.name.trim()) return '场次名称不能为空'
  if (!data.venue.trim()) return '场地不能为空'
  if (!data.startAt || !data.endAt) return '开始与结束时间都要填'
  // 格式固定为 YYYY-MM-DD HH:mm，逐位比较就是时间先后比较
  if (data.endAt <= data.startAt) return '结束时间必须晚于开始时间'
  if (Number(data.capacity) <= 0) return '名额必须是大于 0 的整数'
  return ''
}
```

## 完整代码

```vue [SessionManager.vue]
<script setup>
import { computed, ref } from 'vue'

const NEW_ROW = '__new__'

// ── 数据 ──────────────────────────────────────────────
const sessions = ref([
  {
    id: 's-1',
    name: '初赛',
    venue: '大学生活动中心 301',
    startAt: '2026-10-12 09:00',
    endAt: '2026-10-12 11:30',
    capacity: 120
  },
  {
    id: 's-2',
    name: '复赛',
    venue: '大学生活动中心 301',
    startAt: '2026-10-19 14:00',
    endAt: '2026-10-19 16:00',
    capacity: 60
  },
  {
    id: 's-3',
    name: '决赛',
    venue: '图书馆报告厅',
    startAt: '2026-10-26 19:00',
    endAt: '2026-10-26 21:00',
    capacity: 200
  }
])

const checkedIds = ref([])
const editingId = ref('')
const draft = ref(emptyDraft())
const formError = ref('')

function emptyDraft() {
  return { name: '', venue: '', startAt: '', endAt: '', capacity: 50 }
}

// ── 派生状态 ─────────────────────────────────────────
const checkedCount = computed(() => checkedIds.value.length)

const isAllChecked = computed(
  () => sessions.value.length > 0 && checkedIds.value.length === sessions.value.length
)

const isIndeterminate = computed(() => checkedCount.value > 0 && !isAllChecked.value)

// ── 勾选 ─────────────────────────────────────────────
function toggleAll(event) {
  checkedIds.value = event.target.checked ? sessions.value.map((item) => item.id) : []
}

// ── 新增与编辑 ───────────────────────────────────────
function startCreate() {
  editingId.value = NEW_ROW
  draft.value = emptyDraft()
  formError.value = ''
}

function startEdit(session) {
  editingId.value = session.id
  draft.value = { ...session } // 复制一份再改，取消时原数据不受影响
  formError.value = ''
}

function cancelEdit() {
  editingId.value = ''
  draft.value = emptyDraft()
  formError.value = ''
}

function validate(data) {
  if (!data.name.trim()) return '场次名称不能为空'
  if (!data.venue.trim()) return '场地不能为空'
  if (!data.startAt || !data.endAt) return '开始与结束时间都要填'
  if (data.endAt <= data.startAt) return '结束时间必须晚于开始时间'
  if (Number(data.capacity) <= 0) return '名额必须是大于 0 的整数'
  return ''
}

function save() {
  const message = validate(draft.value)
  if (message) {
    formError.value = message
    return
  }
  const payload = { ...draft.value, capacity: Number(draft.value.capacity) }

  if (editingId.value === NEW_ROW) {
    sessions.value.push({ ...payload, id: `s-${Date.now()}` })
  } else {
    const index = sessions.value.findIndex((item) => item.id === editingId.value)
    if (index > -1) sessions.value[index] = { ...payload, id: editingId.value }
  }
  cancelEdit()
}

// ── 删除 ─────────────────────────────────────────────
function remove(id) {
  sessions.value = sessions.value.filter((item) => item.id !== id)
  checkedIds.value = checkedIds.value.filter((checkedId) => checkedId !== id)
  if (editingId.value === id) cancelEdit()
}

function removeChecked() {
  const removing = new Set(checkedIds.value)
  sessions.value = sessions.value.filter((item) => !removing.has(item.id))
  checkedIds.value = []
  if (removing.has(editingId.value)) cancelEdit()
}
</script>

<template>
  <section class="session-manager">
    <header class="bar">
      <h2>场次清单</h2>
      <div class="actions">
        <span v-if="checkedCount" class="hint">已选 {{ checkedCount }} 项</span>
        <button class="btn btn-danger" :disabled="checkedCount === 0" @click="removeChecked">
          批量删除
        </button>
        <button class="btn btn-primary" @click="startCreate">新增场次</button>
      </div>
    </header>

    <p v-if="formError" class="error">{{ formError }}</p>

    <p v-if="sessions.length === 0 && editingId !== NEW_ROW" class="empty">
      还没有场次，点右上角“新增场次”开始安排。
    </p>

    <table v-else class="grid">
      <thead>
        <tr>
          <th class="col-check">
            <input
              type="checkbox"
              :checked="isAllChecked"
              :indeterminate="isIndeterminate"
              @change="toggleAll"
            />
          </th>
          <th>名称</th>
          <th>场地</th>
          <th>时间</th>
          <th>名额</th>
          <th class="col-op">操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="editingId === NEW_ROW" class="row-editing">
          <td class="col-check"><input type="checkbox" disabled /></td>
          <td><input v-model="draft.name" class="input" placeholder="场次名称" /></td>
          <td><input v-model="draft.venue" class="input" placeholder="场地名称" /></td>
          <td class="col-time">
            <input v-model="draft.startAt" class="input" placeholder="2026-10-12 09:00" />
            <span class="sep">至</span>
            <input v-model="draft.endAt" class="input" placeholder="2026-10-12 11:30" />
          </td>
          <td>
            <input v-model.number="draft.capacity" class="input input-num" type="number" min="1" />
          </td>
          <td class="col-op">
            <button class="link" @click="save">保存</button>
            <button class="link" @click="cancelEdit">取消</button>
          </td>
        </tr>

        <tr v-for="session in sessions" :key="session.id">
          <template v-if="editingId === session.id">
            <td class="col-check"><input type="checkbox" disabled /></td>
            <td><input v-model="draft.name" class="input" /></td>
            <td><input v-model="draft.venue" class="input" /></td>
            <td class="col-time">
              <input v-model="draft.startAt" class="input" />
              <span class="sep">至</span>
              <input v-model="draft.endAt" class="input" />
            </td>
            <td>
              <input v-model.number="draft.capacity" class="input input-num" type="number" min="1" />
            </td>
            <td class="col-op">
              <button class="link" @click="save">保存</button>
              <button class="link" @click="cancelEdit">取消</button>
            </td>
          </template>

          <template v-else>
            <td class="col-check">
              <input v-model="checkedIds" type="checkbox" :value="session.id" />
            </td>
            <td>{{ session.name }}</td>
            <td>{{ session.venue }}</td>
            <td class="col-time">{{ session.startAt }} 至 {{ session.endAt }}</td>
            <td>{{ session.capacity }}</td>
            <td class="col-op">
              <button class="link" @click="startEdit(session)">编辑</button>
              <button class="link danger-text" @click="remove(session.id)">删除</button>
            </td>
          </template>
        </tr>
      </tbody>
    </table>
  </section>
</template>

<style scoped>
.session-manager {
  font-size: 14px;
}
.bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.bar h2 {
  margin: 0;
  font-size: 18px;
}
.actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.hint {
  color: #6b7280;
}
.btn,
.link {
  cursor: pointer;
  border-radius: 4px;
  border: 1px solid #d0d5dd;
  background: #fff;
  padding: 4px 10px;
}
.btn-primary {
  background: #42b883;
  border-color: #42b883;
  color: #fff;
}
.btn-danger {
  color: #e5484d;
}
.btn:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}
.link {
  border: none;
  color: #2f6feb;
  padding: 2px 4px;
}
.danger-text {
  color: #e5484d;
}
.grid {
  width: 100%;
  border-collapse: collapse;
}
.grid th,
.grid td {
  border-bottom: 1px solid #e5e7eb;
  padding: 8px;
  text-align: left;
}
.col-check {
  width: 40px;
}
.col-op {
  width: 120px;
}
.col-time {
  white-space: nowrap;
}
.sep {
  margin: 0 6px;
  color: #9ca3af;
}
.input {
  width: 100%;
  box-sizing: border-box;
  padding: 4px 6px;
  border: 1px solid #d0d5dd;
  border-radius: 4px;
}
.input-num {
  width: 80px;
}
.row-editing {
  background: #f6fef9;
}
.empty {
  padding: 40px;
  text-align: center;
  color: #9ca3af;
  border: 1px dashed #d0d5dd;
  border-radius: 6px;
}
.error {
  color: #e5484d;
}
</style>
```

在页面里用起来：

```vue [ActivityDetail.vue]
<script setup>
import SessionManager from '@/components/SessionManager.vue'
</script>

<template>
  <main>
    <h1>校园歌手大赛</h1>
    <SessionManager />
  </main>
</template>
```

## 常见坑

::: details 坑 1：用数组下标当 `:key`
**现象**：删除第二条之后，原本勾选第三条的复选框，勾选状态跑到了别的行上；或者编辑第七行时
输入框里的内容是第六行的。

**原因**：`:key="index"` 告诉 Vue“第 0 个、第 1 个……是同一批元素”。删除中间一条后，
下标整体前移，Vue 会复用原来那个位置的 DOM 节点，而节点的状态（勾选、输入框里的值、焦点）
跟着节点走了。

**怎么处理**：键值必须是这条记录**自己**的身份，用 `:key="session.id"`。如果数据里暂时没有 id，
至少在拿到数据后补一个（比如后端返回的记录序号），不要退回去用下标。
:::

::: details 坑 2：编辑时直接改原对象，点“取消”回不去
**现象**：进入编辑态改了几个字，点取消，列表里的数据也变了。

**原因**：`draft.value = session` 是引用赋值，`v-model` 改的是同一个对象。

**怎么处理**：进入编辑态时复制一份 `draft.value = { ...session }`。如果字段里有嵌套对象或数组，
浅拷贝不够，要换成结构化克隆：`structuredClone(session)`（现代浏览器都支持）。
:::

::: details 坑 3：批量删除后勾选列表没清理
**现象**：删完之后，表格已经空了，但“已选 2 项”还挂着，批量删除按钮还是可点的。

**原因**：`checkedIds` 里还留着已经删掉的 id。

**怎么处理**：删除数据的地方，都要顺手同步勾选状态。单条删除按 id 过滤，
批量删除直接清空数组。
:::

::: details 坑 4：把 `indeterminate` 当普通属性写死
**现象**：写了 `<input type="checkbox" indeterminate />`，全选框永远显示成半选。

**原因**：`indeterminate` 是 DOM 属性，不是 HTML 特性，写在标签上不生效，而且它一旦被设为 `true`
就不会自己变回来。

**怎么处理**：写成动态绑定 `:indeterminate="isIndeterminate"`。Vue 会把它当成 DOM 属性来更新。
:::

::: details 坑 5：空列表时点“新增”没有输入框
**现象**：数据清空之后再点新增，页面只有一句“还没有场次”，看不到输入行。

**原因**：空状态和表格写成了二选一，进入编辑态时没有切换条件。

**怎么处理**：在 `v-if` 里补上编辑态判断（`editingId !== NEW_ROW`），让“有数据”“正在新增”
两种情况都渲染表格。
:::

::: details 坑 6：`v-if` 和 `v-for` 写在同一个元素上
**现象**：写了 `<tr v-for="item in list" v-if="item.visible">`，编辑器提示警告。

**原因**：在 Vue 3 里，同一个元素上的 `v-if` 会比 `v-for` 先执行，此时循环变量还不存在，
条件里访问不到 `item`。Vue 会给出警告提醒你。

**怎么处理**：两种情况分开。

- 要按条件过滤列表，用 `computed` 先筛出来再循环：

```js
const visibleList = computed(() => list.value.filter((item) => item.visible))
```

- 要按条件决定整块是否渲染，把 `v-if` 放到外层元素或 `<template>` 上：

```vue
<template v-for="item in list" :key="item.id">
  <tr v-if="item.visible"><!-- …… --></tr>
</template>
```
:::

## 扩展练习

::: details 练习 1：加一个搜索框
在表格上方加一个输入框，输入关键字后只显示名称或场地包含该关键字的场次。

**思路**：不要改动 `sessions` 本身。再加一个 `keyword` 的 `ref`，用 `computed` 算出一个
`visibleSessions`，模板里循环它。注意两点：

1. 现在是“展示态和编辑态共用同一个数组”，过滤之后如果正在编辑的行被滤掉了，编辑态要能自动取消。
2. 搜索词为空时应该显示全部，别写成 `includes('')` —— 虽然结果一样，但语义上分两种分支更清楚。

:::

::: details 练习 2：给表格加排序
点击表头，按名称或名额排序，再点一次切换升降序。

**思路**：排序规则是“派生数据”，用 `computed` 而不是 `watch`。注意名额是数字，
用 `a.capacity - b.capacity`；名称是中文，用 `localeCompare` 并传入区域参数，
直接比大小会按字符编码排，结果看起来是乱的。做完可以对照[案例 02](/cases/02-grid)的多列排序。
:::

::: details 练习 3：改成弹窗编辑
把行内编辑换成弹窗，回到案例里“取舍”那一节的判断标准，说说改完之后哪些地方变简单了、哪些变麻烦了。

**思路**：需要新增一个弹窗组件，用 props 传当前编辑的数据，用 emits 把“保存”事件传回父组件，
具体写法在[组件基础与父子通信](/unit07/02-props)和 [emits](/unit07/03-emits)两节。
重点体会：行内编辑时“复制一份”的技巧在弹窗里同样需要，否则点关闭还是会写回数据。
:::

::: details 练习 4：删除后支持撤销
点删除时先不真的删，页面底部弹一条“已删除 1 项，撤销”，5 秒内点撤销能恢复。

**思路**：把“删除”拆成两步 —— 先从数组里移出并记下它原来的位置，放进一个待确认的变量里；
超时或用户离开页面时才真正丢弃。关键在于**记住原来的位置**，撤销时要插回原位，
否则恢复出来的顺序是乱的。定时器记得在组件卸载时清掉。
:::

---

上一页：[案例总览](/cases/) · 下一页：[案例 02 · 可排序筛选的数据表格](/cases/02-grid)
