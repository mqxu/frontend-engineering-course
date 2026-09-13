# 案例 01 · 增删改查清单

::: tip 这是什么
**基础档案例，课堂演练内容。** 从一个空文件开始，逐步实现一个完整的增删改查清单应用，
最后给出完整代码。

这个案例把 [5.1 计算属性](/unit05/01-computed) 到
[5.5 四态规范](/unit05/05-four-states) 的工具串起来用一遍。
:::

## 需求与最终效果

做一个活动筹备任务清单。功能清单：

| 功能 | 说明 |
| --- | --- |
| 任务列表 | 每条任务有标题、优先级、截止日期、是否完成 |
| 新增 | 输入标题、选优先级、选截止日期，点“添加”或按回车 |
| 切换完成 | 点复选框切换完成状态 |
| 行内编辑 | 点“编辑”就地变成输入框，带“保存”和“取消”；取消要能回滚 |
| 删除 | 点“删除”先二次确认，确认后删除并提供 5 秒撤销窗口 |
| 状态筛选 | 全部 / 未完成 / 已完成 |
| 计数 | 总数、已完成、未完成、完成度百分比 |

**不使用任何 UI 组件库。** 这个案例练的是把逻辑写清楚，不是调组件。

::: warning 先想清楚一件事：哪些是状态，哪些是算出来的
动手之前先分类，这一步比写代码重要。

**原始状态（需要 `ref`）**：任务数组、新增表单的三个字段、当前筛选值、
正在编辑哪一条、正在确认删除哪一条、刚删除的那条（用于撤销）。

**派生数据（用 `computed` 算）**：筛选后的列表、总数、已完成数、
未完成数、完成度。

**判断标准**：能被其他数据算出来的，就不要单独存一份。
比如“已完成数量”，任何时候都能从任务数组算出来，不需要一个 `ref` 去维护它。
:::

## 第一步：数据与静态列表

先把数据和静态列表做出来，不做交互。

```vue [src/views/TaskListView.vue]
<script setup>
import { ref } from 'vue'

const tasks = ref([
  {
    id: 1,
    title: '整理活动报名名单',
    done: false,
    priority: 'high',
    deadline: '2026-09-20'
  },
  {
    id: 2,
    title: '联系场地负责人确认时段',
    done: true,
    priority: 'medium',
    deadline: '2026-09-18'
  },
  {
    id: 3,
    title: '准备审核说明材料',
    done: false,
    priority: 'low',
    deadline: '2026-09-25'
  }
])

const PRIORITY_TEXT = { high: '高', medium: '中', low: '低' }
</script>

<template>
  <ul class="task-list">
    <li v-for="task in tasks" :key="task.id" class="task-item">
      <input type="checkbox" :checked="task.done" />
      <span class="task-item__title" :class="{ 'is-done': task.done }">
        {{ task.title }}
      </span>
      <span class="task-item__priority" :class="`priority--${task.priority}`">
        {{ PRIORITY_TEXT[task.priority] }}
      </span>
      <span class="task-item__deadline">{{ task.deadline }}</span>
    </li>
  </ul>
</template>
```

**注意 `:key="task.id"`。** 这个列表会被增删改序，
必须用业务的唯一标识作为键，理由见 [5.4](/unit05/04-list)。

## 第二步：新增

新增要做三件事：读表单、拼一条新数据、清空表单。

```vue [src/views/TaskListView.vue]
<script setup>
import { ref } from 'vue'

let nextId = 4        // 本地模拟主键，真实项目由后端生成

const tasks = ref([ /* 同上 */ ])

const draftTitle = ref('')
const draftPriority = ref('medium')
const draftDeadline = ref('')

function addTask() {
  const title = draftTitle.value.trim()

  // 校验：标题不能为空，不能全是空格
  if (!title) return

  tasks.value = [
    ...tasks.value,
    {
      id: nextId++,
      title,
      done: false,
      priority: draftPriority.value,
      deadline: draftDeadline.value
    }
  ]

  // 清空表单
  draftTitle.value = ''
  draftPriority.value = 'medium'
  draftDeadline.value = ''
}
</script>

<template>
  <form class="task-form" @submit.prevent="addTask">
    <input v-model="draftTitle" placeholder="要做什么？" />
    <select v-model="draftPriority">
      <option value="high">高</option>
      <option value="medium">中</option>
      <option value="low">低</option>
    </select>
    <input v-model="draftDeadline" type="date" />
    <button type="submit">添加</button>
  </form>
</template>
```

三个写法上的要点：

**一、用 `<form @submit.prevent>` 而不是 `@click`。**
这样按回车也能提交，而且 `type="submit"` 的按钮天生能触发提交，
不用单独绑一次点击事件。`.prevent` 阻止表单默认的刷新行为。

> 这里的 `v-model` 属于[单元 6](/unit06/03-form-binding) 的内容，本案例先用起来。
> 你只需要知道：它同时做了两件事 —— 把数据填进输入框、把用户的输入写回数据。
> 复选框那里本案例故意写了 `:checked` + `@change` 的完整形式，
> 是为了让你看清“读”和“写”分别发生在哪一步。

**二、`trim()` 之后再判断。** 用户输入一个空格也能通过 `if (title)`，
但那是没有意义的数据。**所有用户输入的文本都先 `trim`。**

**三、新增用展开而不是 `push`。**

```js
// ✓ 推荐：生成新数组
tasks.value = [...tasks.value, newTask]

// 也可以：push 在 Vue 3 里同样能触发更新
tasks.value.push(newTask)
```

两种都能跑，推荐展开写法的原因是它和后面要做的“撤销”配合更好 ——
撤销需要一个“改动前的数组快照”，不可变写法天然就有快照。

## 第三步：筛选与计数（派生链）

这里是这个案例最核心的一步：**所有派生数据都用 `computed`。**

```vue [src/views/TaskListView.vue]
<script setup>
import { ref, computed } from 'vue'

const filter = ref('all')          // all / active / done

const FILTER_OPTIONS = [
  { value: 'all', label: '全部' },
  { value: 'active', label: '未完成' },
  { value: 'done', label: '已完成' }
]

// 第一层派生：筛选后的列表
const filteredTasks = computed(() => {
  if (filter.value === 'active') return tasks.value.filter((t) => !t.done)
  if (filter.value === 'done') return tasks.value.filter((t) => t.done)
  return tasks.value
})

// 第二层派生：统计数字
const totalCount = computed(() => tasks.value.length)
const doneCount = computed(() => tasks.value.filter((t) => t.done).length)
const remainingCount = computed(() => totalCount.value - doneCount.value)
const progress = computed(() => {
  if (totalCount.value === 0) return 0
  return Math.round((doneCount.value / totalCount.value) * 100)
})
</script>

<template>
  <div class="task-toolbar">
    <button
      v-for="option in FILTER_OPTIONS"
      :key="option.value"
      :class="{ 'is-active': filter === option.value }"
      @click="filter = option.value"
    >
      {{ option.label }}
    </button>
    <span class="task-toolbar__summary">
      未完成 {{ remainingCount }} / 共 {{ totalCount }} · {{ progress }}%
    </span>
  </div>
</template>
```

**注意派生链的方向：**

```text
tasks（源头）
  ↓
filteredTasks（筛选）
  ↓
列表渲染

tasks（源头）
  ↓
totalCount / doneCount（统计）
  ↓
remainingCount / progress（再派生）
```

**每一层的依赖都是单向的。** `doneCount` 依赖 `tasks`，
`progress` 依赖 `doneCount` 和 `totalCount`，`totalCount` 不依赖任何派生数据。
**没有任何一层回头去改上一层。** 这是派生链能稳定工作的前提。

::: danger 不要这样写
```js
// ✗ 用 watch 维护一份“筛选结果”
const filteredTasks = ref([])
watch([tasks, filter], () => {
  filteredTasks.value = tasks.value.filter(match(filter.value))
}, { immediate: true, deep: true })

// ✗ 用 watch 维护统计数字
const doneCount = ref(0)
watch(tasks, () => {
  doneCount.value = tasks.value.filter((t) => t.done).length
}, { immediate: true, deep: true })
```

两处问题：**多了一份需要手动同步的状态**；`immediate` 忘了写就出 bug；
`deep: true` 让侦听器在数组任何变化时都触发，性能更差。

**凡是能被算出来的，一律用 `computed`。** 这是这个单元最重要的一条纪律。
:::

## 第四步：行内编辑与快照回滚

行内编辑有三个子问题要解决：**管理编辑态、让输入框绑上数据、取消时回滚。**

### 编辑态管理

用一个 `editingId` 表示“当前哪一行在编辑”：

```js
const editingId = ref(null)

function startEdit(task) {
  editingId.value = task.id
}
```

模板里按 `editingId === task.id` 决定这一行显示输入框还是文字：

```vue
<template>
  <li v-for="task in filteredTasks" :key="task.id">
    <!-- 编辑态 -->
    <template v-if="editingId === task.id">
      <input v-model="task.title" />
      <select v-model="task.priority">...</select>
      <input v-model="task.deadline" type="date" />
      <button @click="saveEdit">保存</button>
      <button @click="cancelEdit">取消</button>
    </template>

    <!-- 展示态 -->
    <template v-else>
      <span>{{ task.title }}</span>
      <button @click="startEdit(task)">编辑</button>
    </template>
  </li>
</template>
```

**为什么用 `editingId` 而不是给每个任务加一个 `isEditing` 字段？**
因为“同时只能编辑一行”是这个界面的规则。用 `editingId` 天然满足这个规则；
用 `isEditing` 就要在每个任务上维护，而且可能出现两行同时是 `true`。
**用状态的结构去表达业务规则，比在代码里判断更可靠。**

### 直接绑定原数据

注意 `v-model="task.title"` —— 输入框**直接绑到了任务对象上**。
这样写的好处是模板简单，不需要额外维护一个“草稿对象”。

代价是：**编辑过程中用户输入的每一个字，都已经写进了任务数据里。**
如果这一行还显示优先级、截止日期，你会看到它们实时变化。

### 取消时用快照回滚

既然输入是直接写进原数据的，那“取消”就不能只清掉 `editingId` ——
数据已经被改过了。必须**用编辑前的快照还原**。

```js
const editingId = ref(null)
let snapshot = null      // 编辑开始时的数据快照

function startEdit(task) {
  editingId.value = task.id
  snapshot = { ...task }         // 存一份浅拷贝
}

function saveEdit() {
  // 保存前做一次校验
  const current = tasks.value.find((t) => t.id === editingId.value)
  if (!current || !current.title.trim()) return

  // 输入过程中已经写进数据了，这里只需要补上“去掉首尾空格”
  current.title = current.title.trim()

  finishEdit()
}

function cancelEdit() {
  // 用快照还原
  if (snapshot) {
    tasks.value = tasks.value.map((t) => (t.id === snapshot.id ? { ...snapshot } : t))
  }
  finishEdit()
}

function finishEdit() {
  editingId.value = null
  snapshot = null
}
```

**注意 `snapshot = { ...task }` 是浅拷贝。** 因为每条任务的字段都是
字符串和布尔值这类基本类型，浅拷贝就足够。如果任务里嵌套了对象或数组，
浅拷贝就不够，要用 `structuredClone(task)`。

::: warning 快照要在“进入编辑”的那一刻存，不能晚
```js
// ✗ 错：等取消的时候才存，存到的已经是改过的数据
function cancelEdit(task) {
  const snapshot = { ...task }    // 此时 task 已经被改过了
  // 还原出来还是改过的内容
}
```

**快照的意义就在于“记录改动之前”。** 时间点错了，整套机制就失效了。
:::

::: details 另一种更简单的做法：草稿对象
不直接绑原数据，而是维护一个独立的草稿：

```js
const editingDraft = ref(null)

function startEdit(task) {
  editingId.value = task.id
  editingDraft.value = { title: task.title, priority: task.priority, deadline: task.deadline }
}

function saveEdit() {
  if (!editingDraft.value.title.trim()) return
  tasks.value = tasks.value.map((t) =>
    t.id === editingId.value ? { ...t, ...editingDraft.value } : t
  )
  finishEdit()
}

function cancelEdit() {
  finishEdit()      // 丢掉草稿就行，不用回滚
}
```

**两种做法的取舍：**

| | 直接绑原数据 + 快照 | 独立草稿对象 |
| --- | --- | --- |
| 模板复杂度 | 低（`v-model="task.title"`） | 中（`v-model="editingDraft.title"`） |
| 取消费力 | 需要快照回滚 | 丢掉草稿即可 |
| 中间态是否可见 | 可见（改动实时反映在列表） | 不可见（只有保存后才生效） |
| 适合 | 想要“所见即所得”的编辑 | 不想让改动提前暴露 |

**这个案例用第一种，是为了把“快照回滚”这个手法讲清楚。**
真实项目里两种都常见，选哪种取决于产品要什么效果。
:::

## 第五步：删除的二次确认与撤销窗口

删除是最需要小心处理的操作用户可能点错。两道保护：

1. **二次确认** —— 点“删除”不立刻删，先变成“确认 / 取消”；
2. **撤销窗口** —— 真删了之后，给 5 秒时间可以撤销。

```js
const confirmingId = ref(null)     // 哪一行正在等待确认
const deletedInfo = ref(null)      // { task, index }，用于撤销
let undoTimer = null

function askDelete(task) {
  confirmingId.value = task.id
}

function cancelDelete() {
  confirmingId.value = null
}

function confirmDelete(task) {
  const index = tasks.value.findIndex((t) => t.id === task.id)
  if (index === -1) return

  // 删掉，同时记下它的位置
  tasks.value = tasks.value.filter((t) => t.id !== task.id)
  deletedInfo.value = { task, index }
  confirmingId.value = null

  // 重启撤销倒计时
  if (undoTimer) clearTimeout(undoTimer)
  undoTimer = setTimeout(() => {
    deletedInfo.value = null
  }, 5000)
}

function undoDelete() {
  if (!deletedInfo.value) return
  const { task, index } = deletedInfo.value

  // 用 splice 插回原来的位置（在副本上操作，不动原数组）
  const next = [...tasks.value]
  next.splice(index, 0, task)
  tasks.value = next

  deletedInfo.value = null
  if (undoTimer) clearTimeout(undoTimer)
}

onUnmounted(() => {
  if (undoTimer) clearTimeout(undoTimer)
})
```

模板部分：

```vue
<template>
  <li v-for="task in filteredTasks" :key="task.id">
    <!-- 省略前面的内容 -->

    <!-- 删除：三步走 -->
    <template v-if="confirmingId === task.id">
      <span class="task-item__confirm">确认删除？</span>
      <button @click="confirmDelete(task)">确认</button>
      <button @click="cancelDelete">取消</button>
    </template>
    <button v-else @click="askDelete(task)">删除</button>
  </li>
</template>

<!-- 撤销提示条 -->
<div v-if="deletedInfo" class="undo-bar">
  <span>已删除“{{ deletedInfo.task.title }}”</span>
  <button @click="undoDelete">撤销</button>
</div>
```

**四个设计要点：**

**一、撤销要记位置。** 只存被删的任务，撤销时只能追加到末尾，
用户会发现“撤销后位置变了”。存下 `index`，按原位置插回去。

**二、`splice` 的用法要在副本上。** `const next = [...tasks.value]` 之后
`next.splice(index, 0, task)`，再整体赋值。这样不会就地修改原数组。

**三、倒计时要清理。** 用户在 5 秒内连续删两条，
第一次的定时器会把第二次的撤销提示提前关掉。
所以每次都要先 `clearTimeout`。**这属于“副作用清理”，
就是 [5.2](/unit05/02-watch) 里讲的那个 `onCleanup` 场景的手动版本。**

**四、组件卸载时也要清理。** 用户删完立刻跳走，
定时器还在跑，回调里去改一个已经不存在的组件的状态，控制台会有警告。
`onUnmounted` 里清一次。

::: tip 为什么不用 `confirm()` 弹窗
`window.confirm()` 能用，但两个问题：一是样式改不了，二是它会**阻塞整个页面**
（浏览器主线程停下等用户点）。用页面内的确认状态更好控制，也更符合现代界面习惯。

**但要注意：页内确认不如浏览器原生弹窗“强制”。** 用户可能直接切走。
所以页内确认适合可逆操作（有撤销窗口兜底），不可逆操作还是用原生弹窗或专门的弹窗组件。
:::

## 完整代码

```vue [src/views/TaskListView.vue]
<script setup>
import { ref, computed, onUnmounted } from 'vue'

let nextId = 4

const tasks = ref([
  { id: 1, title: '整理活动报名名单', done: false, priority: 'high', deadline: '2026-09-20' },
  { id: 2, title: '联系场地负责人确认时段', done: true, priority: 'medium', deadline: '2026-09-18' },
  { id: 3, title: '准备审核说明材料', done: false, priority: 'low', deadline: '2026-09-25' }
])

const PRIORITY_TEXT = { high: '高', medium: '中', low: '低' }
const FILTER_OPTIONS = [
  { value: 'all', label: '全部' },
  { value: 'active', label: '未完成' },
  { value: 'done', label: '已完成' }
]

// ---------- 新增表单 ----------
const draftTitle = ref('')
const draftPriority = ref('medium')
const draftDeadline = ref('')

// ---------- 界面状态 ----------
const filter = ref('all')
const editingId = ref(null)
const confirmingId = ref(null)
const deletedInfo = ref(null)
let snapshot = null
let undoTimer = null

// ---------- 派生数据 ----------
const filteredTasks = computed(() => {
  if (filter.value === 'active') return tasks.value.filter((t) => !t.done)
  if (filter.value === 'done') return tasks.value.filter((t) => t.done)
  return tasks.value
})

const totalCount = computed(() => tasks.value.length)
const doneCount = computed(() => tasks.value.filter((t) => t.done).length)
const remainingCount = computed(() => totalCount.value - doneCount.value)
const progress = computed(() =>
  totalCount.value === 0 ? 0 : Math.round((doneCount.value / totalCount.value) * 100)
)

// ---------- 新增 ----------
function addTask() {
  const title = draftTitle.value.trim()
  if (!title) return

  tasks.value = [
    ...tasks.value,
    { id: nextId++, title, done: false, priority: draftPriority.value, deadline: draftDeadline.value }
  ]
  draftTitle.value = ''
  draftPriority.value = 'medium'
  draftDeadline.value = ''
}

// ---------- 切换完成 ----------
function toggleDone(task) {
  tasks.value = tasks.value.map((t) => (t.id === task.id ? { ...t, done: !t.done } : t))
}

// ---------- 行内编辑 ----------
function startEdit(task) {
  editingId.value = task.id
  snapshot = { ...task }
}

function saveEdit() {
  const current = tasks.value.find((t) => t.id === editingId.value)
  if (!current || !current.title.trim()) return
  current.title = current.title.trim()
  finishEdit()
}

function cancelEdit() {
  if (snapshot) {
    tasks.value = tasks.value.map((t) => (t.id === snapshot.id ? { ...snapshot } : t))
  }
  finishEdit()
}

function finishEdit() {
  editingId.value = null
  snapshot = null
}

// ---------- 删除 ----------
function askDelete(task) {
  confirmingId.value = task.id
}

function cancelDelete() {
  confirmingId.value = null
}

function confirmDelete(task) {
  const index = tasks.value.findIndex((t) => t.id === task.id)
  if (index === -1) return

  tasks.value = tasks.value.filter((t) => t.id !== task.id)
  deletedInfo.value = { task, index }
  confirmingId.value = null

  if (undoTimer) clearTimeout(undoTimer)
  undoTimer = setTimeout(() => {
    deletedInfo.value = null
  }, 5000)
}

function undoDelete() {
  if (!deletedInfo.value) return
  const { task, index } = deletedInfo.value

  const next = [...tasks.value]
  next.splice(index, 0, task)
  tasks.value = next

  deletedInfo.value = null
  if (undoTimer) clearTimeout(undoTimer)
}

onUnmounted(() => {
  if (undoTimer) clearTimeout(undoTimer)
})
</script>

<template>
  <section class="task-page">
    <h1>活动筹备任务</h1>

    <form class="task-form" @submit.prevent="addTask">
      <input v-model="draftTitle" placeholder="要做什么？" />
      <select v-model="draftPriority">
        <option value="high">高</option>
        <option value="medium">中</option>
        <option value="low">低</option>
      </select>
      <input v-model="draftDeadline" type="date" />
      <button type="submit">添加</button>
    </form>

    <div class="task-toolbar">
      <button
        v-for="option in FILTER_OPTIONS"
        :key="option.value"
        :class="{ 'is-active': filter === option.value }"
        @click="filter = option.value"
      >
        {{ option.label }}
      </button>
      <span class="task-toolbar__summary">
        未完成 {{ remainingCount }} / 共 {{ totalCount }} · {{ progress }}%
      </span>
    </div>

    <p v-if="filteredTasks.length === 0" class="task-empty">
      <template v-if="totalCount === 0">还没有任务，先添加一条。</template>
      <template v-else>当前筛选条件下没有任务。</template>
    </p>

    <ul v-else class="task-list">
      <li v-for="task in filteredTasks" :key="task.id" class="task-item">
        <template v-if="editingId === task.id">
          <input v-model="task.title" class="task-item__edit-title" />
          <select v-model="task.priority">
            <option value="high">高</option>
            <option value="medium">中</option>
            <option value="low">低</option>
          </select>
          <input v-model="task.deadline" type="date" />
          <button @click="saveEdit">保存</button>
          <button @click="cancelEdit">取消</button>
        </template>

        <template v-else>
          <input type="checkbox" :checked="task.done" @change="toggleDone(task)" />
          <span class="task-item__title" :class="{ 'is-done': task.done }">
            {{ task.title }}
          </span>
          <span class="task-item__priority" :class="`priority--${task.priority}`">
            {{ PRIORITY_TEXT[task.priority] }}
          </span>
          <span class="task-item__deadline">{{ task.deadline || '未设置' }}</span>

          <button @click="startEdit(task)">编辑</button>

          <template v-if="confirmingId === task.id">
            <span class="task-item__confirm">确认删除？</span>
            <button @click="confirmDelete(task)">确认</button>
            <button @click="cancelDelete">取消</button>
          </template>
          <button v-else @click="askDelete(task)">删除</button>
        </template>
      </li>
    </ul>

    <div v-if="deletedInfo" class="undo-bar">
      <span>已删除“{{ deletedInfo.task.title }}”</span>
      <button @click="undoDelete">撤销</button>
    </div>
  </section>
</template>

<style scoped>
.task-item__title.is-done {
  text-decoration: line-through;
  color: #9ca3af;
}

.priority--high {
  color: #b91c1c;
}

.priority--medium {
  color: #b45309;
}

.priority--low {
  color: #4b5563;
}

.undo-bar {
  position: fixed;
  bottom: 24px;
  left: 50%;
  display: flex;
  gap: 12px;
  padding: 12px 20px;
  background: #111827;
  color: #fff;
  border-radius: 6px;
  transform: translateX(-50%);
}
</style>
```

::: details 完整代码里有两处“重复”可以优化
1. **优先级的下拉选项出现了两次**（新增表单和行内编辑各一次）。
   可以抽成一个常量数组，用 `v-for` 渲染：

```js
const PRIORITY_OPTIONS = [
  { value: 'high', label: '高' },
  { value: 'medium', label: '中' },
  { value: 'low', label: '低' }
]
```

2. **`tasks.value = tasks.value.map(...)` 这种“按 id 替换一项”的操作**
   出现了好几次。可以抽成一个函数：

```js
function updateTask(id, patch) {
  tasks.value = tasks.value.map((t) => (t.id === id ? { ...t, ...patch } : t))
}
```

**但在课堂演练阶段，先把逻辑写清楚比“少写几行”更重要。**
等你完全明白了每一步在做什么，再去抽公共部分。
:::

## 小结

- 先分类：哪些是原始状态（`ref`），哪些是派生数据（`computed`）。
- 派生链是单向的：源头 → 筛选 → 渲染；源头 → 统计 → 再派生。不能回头改上一层。
- 新增用 `<form @submit.prevent>`，能同时支持回车和按钮；输入先 `trim`。
- 行内编辑用 `editingId` 管理编辑态，用状态结构表达“同时只能编辑一行”的规则。
- 直接绑原数据时，取消必须靠**编辑前存下的快照**回滚；快照要在进入编辑那一刻存。
- 删除给两道保护：二次确认（页内状态）和撤销窗口（5 秒 + 记下原位置）。
- 定时器要清理：重启用 `clearTimeout`，组件卸载时在 `onUnmounted` 里再清一次。
- 列表的增删改都用不可变写法（展开、`filter`、`map`），这样撤销和快照都容易实现。

## 常见坑

::: details 坑 1：把派生数据也写成了 ref
```js
// ✗ 多了一份需要手动同步的状态
const doneCount = ref(0)
function toggleDone(task) {
  task.done = !task.done
  doneCount.value = tasks.value.filter((t) => t.done).length   // 忘了写这里就出 bug
}
```

**现象**：计数和列表对不上。

**原因**：每次改任务都要记得重新算一遍，漏一处就不一致。

**怎么处理**：`const doneCount = computed(() => tasks.value.filter((t) => t.done).length)`。

**判断依据：这份数据能不能从别处算出来。** 能，就不要单独存。
:::

::: details 坑 2：编辑时改了数据，取消后没还原
```js
function cancelEdit() {
  editingId.value = null      // ✗ 只退出编辑态，数据已经被改过了
}
```

**现象**：编辑时输入了一半，点取消，发现列表里的内容变成了输入到一半的内容。

**原因**：`v-model` 直接绑在任务对象上，输入就已经写进数据了。

**怎么处理**：取消时用快照还原；或者改成“独立草稿对象”的写法。

**这个坑的通用形式是：只要有“实时写入”，就必须准备“回滚”。**
:::

::: details 坑 3：撤销时把任务放到了末尾
```js
// ✗ 位置丢了
tasks.value = [...tasks.value, deletedInfo.value.task]
```

**现象**：删掉第 2 条，撤销后它跑到了最后一条。

**原因**：只存了任务，没存位置。

**怎么处理**：删除前用 `findIndex` 记下位置，撤销时按位置插回。
**这是“撤销”功能和“删除”功能的关键差别** —— 删除只要结果，撤销要过程。
:::

::: details 坑 4：连续删除两次，撤销提示提前消失
```js
// ✗ 每次删除都新建一个定时器，老的不清理
undoTimer = setTimeout(() => { deletedInfo.value = null }, 5000)
```

**现象**：删第一条（提示出现），3 秒后删第二条，2 秒后提示就消失了 ——
第一条的定时器把第二条的提示关掉了。

**原因**：多个定时器同时存在，谁先到时间谁先执行回调，而回调改的是同一个状态。

**怎么处理**：每次启动新定时器前 `clearTimeout(undoTimer)`。
**更根本的做法是用一个“撤销队列”，但这里用清旧定时器就够了。**
:::

## 课后练习

::: details 练习 1：加一个“全部清除已完成”
加一个按钮，一次删掉所有已完成的任务。

要求：
1. 按钮上显示将要删除的数量，为 0 时禁用；
2. 点击后也要二次确认；
3. 删除后能一次性撤销全部。

**参考思路**：撤销信息要从“一条”变成“一个列表 + 它们的原位置”，
所以 `deletedInfo` 的结构要改。这是这个练习的重点 ——
**数据结构要跟着功能变。**

**提示**：记下“删除前的完整数组”是最简单的撤销方式：
`deletedInfo.value = { list: tasks.value, removedCount: n }`。
:::

::: details 练习 2：给编辑加一个“保存失败”的处理
假设保存要发请求（先用 `setTimeout` 模拟 30% 失败率）。

要求：
1. 保存中按钮显示“保存中…”并禁用；
2. 失败时提示“保存失败”，并且**数据回滚到编辑前的状态**；
3. 成功后退出编辑态。

**参考思路**：这正好用上快照 —— 失败时 `cancelEdit()` 的还原逻辑可以复用。
把“回滚”和“退出编辑态”拆成两个函数：
`rollback()` 只回滚，`finishEdit()` 只收尾。

**做完之后想一想**：如果失败时用户已经切到别的行了，回滚会发生什么？
这就是“编辑态管理”要注意的边界情况。
:::

::: details 练习 3：抽出一个组合式函数
把任务清单的逻辑抽成 `useTaskList()`，对外返回状态和操作：

```js
const {
  filteredTasks, totalCount, doneCount, progress,
  filter, draftTitle, addTask, toggleDone,
  editingId, startEdit, saveEdit, cancelEdit,
  askDelete, confirmDelete, undoDelete
} = useTaskList()
```

**参考思路**：把所有 `ref` / `computed` / 函数移到一个函数里，
最后 `return` 出去。组件只负责渲染。

**这一步是[单元 8 组合式函数](/unit08/04-composables) 的提前演练。**
抽完之后你会发现：逻辑和界面分开了，逻辑可以被测试，也可以被别的页面复用。
:::

---

上一节：[5.5 四态页面规范](/unit05/05-four-states) ·
下一节：[案例 02 · 可排序筛选的数据表格](/unit05/07-case-grid)
