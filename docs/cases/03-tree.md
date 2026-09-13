# 案例 03 · 树状视图与递归组件

## 案例要做什么

校园活动服务平台里，一个活动由某个组织者发起。组织者下面分部门，部门下面有学生。
审核员要能展开组织者看部门、展开部门看学生，还能勾选若干学生 —— 比如“把文艺部的人都加到这场演出的参演名单里”。

这个需求有两个难点：

1. **层级深度不固定**。今天是“组织者 → 部门 → 学生”，明天可能加一层“学院 → 组织者 → 部门 → 学生”。
   写死三层 `<div>` 的代码改起来很痛苦。
2. **父子状态要联动**。勾了“文艺部”，下面所有学生都要被勾上；反过来，只勾了文艺部里一半学生，
   文艺部自己应该是“半选”状态。

第一个难点用**递归组件**解决，第二个难点用**一次自底向上的遍历**解决。这两件事想清楚了，树就不难写。

| 知识点 | 用在哪里 | 对应章节 |
| --- | --- | --- |
| 递归组件（`name` / `defineOptions`） | 节点组件渲染自己的子节点 | [单文件组件与拆分依据](/unit07/01-sfc) |
| `props` 传数据 | 把节点数据传进递归组件 | [父子通信：props](/unit07/02-props) |
| 依赖注入 | 深层节点共享展开、勾选状态 | [依赖注入](/unit08/02-provide-inject) |
| 数组与 `Map` | 扁平数组转树、状态缓存 | [列表渲染与键值](/unit05/04-list) |
| 条件渲染 | 折叠时不渲染子树 | [条件渲染](/unit05/03-conditional) |

::: tip 这个案例是本单元里“最像真实组件库”的一个
前两个案例都是单文件组件，这一个必须拆成两个文件。**拆分的理由不是“文件太长”，
而是“节点组件要递归自己”** —— 而组件不能在自己的模板里内联定义自己。
:::

## 数据结构与接口设计

### 接口为什么返回扁平数组

一个直觉反应是让接口直接返回嵌套结构：

```json
[
  {
    "id": "org-1",
    "name": "校学生会",
    "children": [
      { "id": "dept-1", "name": "文艺部", "children": [] }
    ]
  }
]
```

但真实接口几乎都返回**扁平数组**：

```json
[
  { "id": "org-1", "parentId": null, "name": "校学生会" },
  { "id": "dept-1", "parentId": "org-1", "name": "文艺部" }
]
```

原因很实际：

| 原因 | 说明 |
| --- | --- |
| 便于局部更新 | 改一个部门的名称，扁平结构里改一条记录就行；嵌套结构要递归找 |
| 便于分页与增量加载 | 每层单独请求，返回的都是一段扁平数据 |
| 避免重复 | 一个节点挂在两条路径下时，嵌套结构要存两份 |
| 后端实现简单 | 数据库里本来就是一张带 `parentId` 的表 |

所以前端必须会做一件事：**把扁平数组转成树。** 这一步做不好，后面递归组件就没得写。

### 节点长什么样

```js [节点的数据结构]
/**
 * 组织架构节点
 * @typedef {Object} OrgNode
 * @property {string} id          唯一标识
 * @property {string|null} parentId 父节点 id，根节点为 null
 * @property {string} type        organizer | department | student
 * @property {string} name        名称
 * @property {string} [studentNo] 学号，只有 type 为 student 时有
 * @property {OrgNode[]} [children] 子节点，转换后才有
 */
```

### 两棵“状态树”要分开想

初学者最容易把三件事混在一起。先把它们分开：

| 状态 | 存什么 | 为什么这样存 |
| --- | --- | --- |
| 展开集合 `expanded` | 展开的节点 id | 只跟“用户当前看到什么”有关，与数据无关 |
| 勾选集合 `checkedLeaves` | 被勾选的**叶子** id | 只存叶子，父节点的状态算出来就行，避免两份数据打架 |
| 当前选中节点 `selectedId` | 一个 id | 单选，用于高亮和信息面板 |

**只存叶子节点的勾选状态**，是本案例最重要的一个设计决定。如果父子都往集合里塞，
就会出现“父节点被勾了但子节点没勾”“取消一个子节点后父节点状态没更新”这类问题。
父节点的状态永远由子节点推出来，只有一处真相。

## 实现步骤

### 步骤 1 · 两趟线性扫描把扁平数组转成树

不用递归，也不要在循环里 `find` 父节点（那会变成 O(n²)）。做法是**先建一张 id 到节点的索引表，
再扫一遍挂到父节点上**：

```js [src/utils/tree.js]
/**
 * 把扁平数组转成树。两趟线性扫描，整体复杂度 O(n)。
 */
export function buildTree(list, { idKey = 'id', parentKey = 'parentId' } = {}) {
  const map = new Map()

  // 第一趟：为每条记录建一个带 children 的副本
  for (const item of list) {
    map.set(item[idKey], { ...item, children: [] })
  }

  const roots = []
  // 第二趟：把每个节点挂到父节点下
  for (const item of list) {
    const node = map.get(item[idKey])
    const parentId = item[parentKey]

    if (parentId === null || parentId === undefined) {
      roots.push(node)
      continue
    }

    const parent = map.get(parentId)
    if (parent) {
      parent.children.push(node)
    } else {
      // parentId 指向一个不存在的节点：兜底当成根，否则这条数据会凭空消失
      roots.push(node)
    }
  }

  return roots
}
```

两趟扫描，复杂度是 O(n)。对比一下常见写法：

```js
// ✗ 每个节点都去数组里找一次父节点，复杂度 O(n²)
for (const item of list) {
  const parent = list.find((candidate) => candidate.id === item.parentId)
  parent.children.push(item)
}
```

数据量小的时候两种写法看不出差别，等到几百个节点时就会卡。**建索引是这类问题的通用解法。**

### 步骤 2 · 递归组件：让组件引用自己

树形结构的渲染天然是递归的：一个节点要渲染的，是它自己加它的所有子节点。
所以节点组件必须在自己的模板里引用自己：

```vue [OrgTreeNode.vue 的骨架]
<script setup>
import { computed, inject } from 'vue'

// 显式声明组件名，递归引用才稳
defineOptions({ name: 'OrgTreeNode' })

const props = defineProps({
  node: { type: Object, required: true },
  depth: { type: Number, default: 0 }
})
</script>

<template>
  <li>
    <!-- 当前节点的内容 -->
    <ul v-if="node.children.length && expanded">
      <OrgTreeNode
        v-for="child in node.children"
        :key="child.id"
        :node="child"
        :depth="depth + 1"
      />
    </ul>
  </li>
</template>
```

三个要点：

| 要点 | 说明 |
| --- | --- |
| `defineOptions({ name: 'OrgTreeNode' })` | 给组件起名字。在 `<script setup>` 里也能靠文件名推断，但改个文件名就失效，显式声明更稳 |
| 递归的终止条件 | `node.children.length` 为 0 时不再渲染 `<ul>`，递归自然停住 |
| `:key="child.id"` | 树形结构里键值必须是节点自己的 id，用下标会出现折叠状态串位 |

### 步骤 3 · 展开与折叠：状态提到共同的祖先

展开状态不能放在节点组件里。原因是：**折叠一个节点之后，它下面的子节点组件会被销毁，
放在子组件里的状态就丢了**，重新展开时又变回默认值。

所以展开集合放在树的根组件里，用依赖注入传给每一层：

```js [展开与折叠]
// 默认展开所有根节点
const expanded = ref(new Set(props.nodes.map((node) => node.id)))

function toggleExpand(id) {
  // 用一个新 Set 替换旧值，触发更新最直接
  const next = new Set(expanded.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  expanded.value = next
}
```

::: warning 为什么每次都新建一个 Set
Vue 3 的响应式系统**能**追踪 `Set` 的 `add` / `delete`，所以直接改也能触发更新。
但“新值替换旧值”这个写法不依赖细节，无论换成数组还是对象都成立，也更方便以后加撤销功能。
**养成“改集合就换一个新的”习惯。**
:::

### 步骤 4 · 半选：一次自底向上的遍历

这是本案例最值得花时间的一步。要解决的问题是：

- 一个部门的**全部**学生都勾了 → 部门勾选。
- 一个部门**部分**学生勾了 → 部门半选（`indeterminate`）。
- 一个学生都没勾 → 部门未勾选。

千万不要在模板里对每个节点调一次递归统计 —— 那样每个节点都要遍历自己的整棵子树，
整体变成 O(n²)。正确做法是**一次遍历同时算出所有节点的状态，存进一张 Map**：

```js [状态表]
const checkedLeaves = ref(new Set())

const stateMap = computed(() => {
  const map = new Map()

  // 返回值是本节点的状态，供父节点汇总
  function walk(node) {
    // 叶子节点：状态完全由勾选集合决定
    if (node.children.length === 0) {
      const state = checkedLeaves.value.has(node.id) ? 'checked' : 'unchecked'
      map.set(node.id, state)
      return state
    }

    let allChecked = true
    let anyChecked = false

    for (const child of node.children) {
      const childState = walk(child)
      if (childState === 'checked') {
        anyChecked = true
      } else {
        allChecked = false
        if (childState === 'indeterminate') anyChecked = true
      }
    }

    const state = allChecked ? 'checked' : anyChecked ? 'indeterminate' : 'unchecked'
    map.set(node.id, state)
    return state
  }

  for (const root of props.nodes) walk(root)
  return map
})
```

这段代码的结构值得记住：**递归函数一边遍历一边把结果写进 `Map`，同时把状态返回给上一层。**
每个节点只被访问一次，整体 O(n)。模板里只做一次查表：

```vue [节点里读状态]
<input
  type="checkbox"
  :checked="state === 'checked'"
  :indeterminate="state === 'indeterminate'"
  @change="tree.toggleCheck(node)"
/>
```

### 步骤 5 · 勾选与状态传递

勾选一个部门，等于勾选它下面所有学生。所以要有一个“收集所有叶子”的函数：

```js [collectLeaves 与 toggleCheck]
function collectLeaves(node, out = []) {
  if (node.children.length === 0) out.push(node)
  else node.children.forEach((child) => collectLeaves(child, out))
  return out
}

function toggleCheck(node) {
  const next = new Set(checkedLeaves.value)
  // 当前状态是“已勾选”就取消，否则全选
  const target = stateMap.value.get(node.id) === 'checked' ? 'unchecked' : 'checked'

  for (const leaf of collectLeaves(node)) {
    if (target === 'checked') next.add(leaf.id)
    else next.delete(leaf.id)
  }

  checkedLeaves.value = next
}
```

**共享状态用依赖注入传下去，不要逐层透传。**

节点组件在很深的层级，逐层透传 props 和 emits 会非常啰嗦：
每加一个状态，每一层都要改一遍。用依赖注入一次传下去：

```js [根组件里注入]
provide('orgTree', {
  expanded,
  stateMap,
  selectedId,
  toggleExpand,
  toggleCheck,
  select
})
```

```js [节点组件里取出]
const tree = inject('orgTree')

const expanded = computed(() => tree.expanded.value.has(props.node.id))
const state = computed(() => tree.stateMap.value.get(props.node.id) ?? 'unchecked')
const isSelected = computed(() => tree.selectedId.value === props.node.id)
```

注意 `provide` 传的是一个**装着 ref 的普通对象**，节点组件里仍然要用 `.value`。
这样引用本身是稳定的，值变了所有用到它的组件都会更新。

### 步骤 6 · 递归遍历的性能注意点

树的代码写起来简洁，但很容易写出 O(n²)。四条规则：

| 规则 | 反例 | 正例 |
| --- | --- | --- |
| 状态一次算完存表 | 模板里调 `countLeaves(node)` | `stateMap` 里一次遍历 |
| 折叠时不渲染子树 | 渲染出来再用 CSS 隐藏 | `v-if="expanded"` |
| 键值用 id | `:key="index"` | `:key="node.id"` |
| 集合查找用 `Set` / `Map` | `expanded.value.includes(id)` | `expanded.value.has(id)` |

## 完整代码

```js [src/utils/tree.js]
/**
 * 把扁平数组转成树。两趟线性扫描，整体复杂度 O(n)。
 */
export function buildTree(list, { idKey = 'id', parentKey = 'parentId' } = {}) {
  const map = new Map()

  for (const item of list) {
    map.set(item[idKey], { ...item, children: [] })
  }

  const roots = []
  for (const item of list) {
    const node = map.get(item[idKey])
    const parentId = item[parentKey]

    if (parentId === null || parentId === undefined) {
      roots.push(node)
      continue
    }

    const parent = map.get(parentId)
    if (parent) parent.children.push(node)
    else roots.push(node)
  }

  return roots
}
```

```js [src/data/orgs.js]
export const flatOrgs = [
  { id: 'org-1', parentId: null, type: 'organizer', name: '校学生会' },
  { id: 'dept-1', parentId: 'org-1', type: 'department', name: '文艺部' },
  { id: 'dept-2', parentId: 'org-1', type: 'department', name: '体育部' },
  { id: 'stu-1', parentId: 'dept-1', type: 'student', name: '林小满', studentNo: '2023010112' },
  { id: 'stu-2', parentId: 'dept-1', type: 'student', name: '陈亦航', studentNo: '2023010233' },
  { id: 'stu-3', parentId: 'dept-1', type: 'student', name: '周敏', studentNo: '2022020118' },
  { id: 'stu-4', parentId: 'dept-2', type: 'student', name: '赵一鸣', studentNo: '2023030145' },
  { id: 'stu-5', parentId: 'dept-2', type: 'student', name: '孙静', studentNo: '2023010176' },

  { id: 'org-2', parentId: null, type: 'organizer', name: '青年志愿者协会' },
  { id: 'dept-3', parentId: 'org-2', type: 'department', name: '校内服务部' },
  { id: 'dept-4', parentId: 'org-2', type: 'department', name: '社区服务部' },
  { id: 'stu-6', parentId: 'dept-3', type: 'student', name: '吴忧', studentNo: '2024040102' },
  { id: 'stu-7', parentId: 'dept-4', type: 'student', name: '郑可', studentNo: '2022020301' },
  { id: 'stu-8', parentId: 'dept-4', type: 'student', name: '冯子涵', studentNo: '2023030233' }
]
```

```vue [OrgTreeNode.vue]
<script setup>
import { computed, inject } from 'vue'

// 递归组件要引用自己，显式声明 name 最稳妥
defineOptions({ name: 'OrgTreeNode' })

const props = defineProps({
  node: { type: Object, required: true },
  depth: { type: Number, default: 0 }
})

const tree = inject('orgTree')

const TYPE_TEXT = {
  organizer: '组织者',
  department: '部门',
  student: '学生'
}

const expanded = computed(() => tree.expanded.value.has(props.node.id))
const state = computed(() => tree.stateMap.value.get(props.node.id) ?? 'unchecked')
const isSelected = computed(() => tree.selectedId.value === props.node.id)
</script>

<template>
  <li class="node">
    <div class="row" :class="{ selected: isSelected }" :style="{ paddingLeft: `${depth * 18 + 8}px` }">
      <button
        class="toggle"
        :class="{ invisible: node.children.length === 0 }"
        type="button"
        :aria-label="expanded ? '折叠' : '展开'"
        @click="tree.toggleExpand(node.id)"
      >
        {{ expanded ? '▾' : '▸' }}
      </button>

      <input
        type="checkbox"
        :checked="state === 'checked'"
        :indeterminate="state === 'indeterminate'"
        @change="tree.toggleCheck(node)"
      />

      <span class="name" @click="tree.select(node)">{{ node.name }}</span>
      <span class="type">{{ TYPE_TEXT[node.type] ?? node.type }}</span>
      <span v-if="node.studentNo" class="meta">{{ node.studentNo }}</span>
    </div>

    <ul v-if="node.children.length && expanded" class="children">
      <OrgTreeNode
        v-for="child in node.children"
        :key="child.id"
        :node="child"
        :depth="depth + 1"
      />
    </ul>
  </li>
</template>

<style scoped>
.node {
  list-style: none;
}
.row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-top: 6px;
  padding-bottom: 6px;
  border-radius: 4px;
}
.row:hover {
  background: #f9fafb;
}
.row.selected {
  background: #ecfdf3;
}
.toggle {
  width: 18px;
  border: none;
  background: none;
  cursor: pointer;
  color: #6b7280;
}
.toggle.invisible {
  visibility: hidden;
}
.name {
  cursor: pointer;
}
.type {
  font-size: 12px;
  color: #9ca3af;
  border: 1px solid #e5e7eb;
  border-radius: 3px;
  padding: 0 4px;
}
.meta {
  font-size: 12px;
  color: #9ca3af;
}
.children {
  margin: 0;
  padding: 0;
}
</style>
```

```vue [OrgTree.vue]
<script setup>
import { computed, provide, ref } from 'vue'
import OrgTreeNode from './OrgTreeNode.vue'

const props = defineProps({
  nodes: { type: Array, required: true }
})

const selectedId = ref('')
const expanded = ref(new Set(props.nodes.map((node) => node.id)))
const checkedLeaves = ref(new Set())

function toggleExpand(id) {
  const next = new Set(expanded.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  expanded.value = next
}

function select(node) {
  selectedId.value = node.id
}

function collectLeaves(node, out = []) {
  if (node.children.length === 0) out.push(node)
  else node.children.forEach((child) => collectLeaves(child, out))
  return out
}

// 一次自底向上的遍历，算出每个节点的状态，避免在模板里重复递归
const stateMap = computed(() => {
  const map = new Map()

  function walk(node) {
    if (node.children.length === 0) {
      const state = checkedLeaves.value.has(node.id) ? 'checked' : 'unchecked'
      map.set(node.id, state)
      return state
    }

    let allChecked = true
    let anyChecked = false

    for (const child of node.children) {
      const childState = walk(child)
      if (childState === 'checked') {
        anyChecked = true
      } else {
        allChecked = false
        if (childState === 'indeterminate') anyChecked = true
      }
    }

    const state = allChecked ? 'checked' : anyChecked ? 'indeterminate' : 'unchecked'
    map.set(node.id, state)
    return state
  }

  for (const root of props.nodes) walk(root)
  return map
})

function toggleCheck(node) {
  const next = new Set(checkedLeaves.value)
  const target = stateMap.value.get(node.id) === 'checked' ? 'unchecked' : 'checked'

  for (const leaf of collectLeaves(node)) {
    if (target === 'checked') next.add(leaf.id)
    else next.delete(leaf.id)
  }

  checkedLeaves.value = next
}

const checkedCount = computed(() => checkedLeaves.value.size)

provide('orgTree', {
  expanded,
  stateMap,
  selectedId,
  toggleExpand,
  toggleCheck,
  select
})
</script>

<template>
  <section class="org-tree">
    <header class="head">
      <h2>组织架构</h2>
      <span class="count">已选 {{ checkedCount }} 名学生</span>
    </header>

    <p v-if="nodes.length === 0" class="empty">暂无组织数据。</p>

    <ul v-else class="tree">
      <OrgTreeNode v-for="node in nodes" :key="node.id" :node="node" />
    </ul>
  </section>
</template>

<style scoped>
.org-tree {
  font-size: 14px;
}
.head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 8px;
}
.head h2 {
  margin: 0;
  font-size: 16px;
}
.count {
  color: #6b7280;
}
.tree {
  margin: 0;
  padding: 0;
}
.empty {
  padding: 24px;
  text-align: center;
  color: #9ca3af;
}
</style>
```

用法：

```vue [OrgPanel.vue]
<script setup>
import { computed } from 'vue'
import OrgTree from '@/components/OrgTree.vue'
import { flatOrgs } from '@/data/orgs'
import { buildTree } from '@/utils/tree'

const tree = computed(() => buildTree(flatOrgs))
</script>

<template>
  <OrgTree :nodes="tree" />
</template>
```

## 常见坑

::: details 坑 1：递归组件报 “Failed to resolve component”
**现象**：写了 `<OrgTreeNode>` 在它自己的模板里，控制台警告组件无法解析，页面不显示子节点。

**原因**：在 `<script setup>` 里，组件名默认靠**文件名**推断。如果文件叫
`OrgTreeNode.vue` 但组件名有拼写差异，或者你把它重命名成了 `TreeNode.vue`，
自引用就找不到了。

**怎么处理**：显式声明 `defineOptions({ name: 'OrgTreeNode' })`，模板里用这个名字。
改文件名不影响。
:::

::: details 坑 2：把展开状态放在节点组件里
**现象**：折叠一个部门再展开，它下面原本展开的学生全收起来了。

**原因**：折叠时 `v-if` 为假，子节点组件被销毁，放在子组件里的展开状态跟着丢了。

**怎么处理**：展开集合放在树的根组件，用依赖注入传下去。**凡是“关掉再打开还要记得”的状态，
都不能放在会被销毁的组件里。**
:::

::: details 坑 3：在模板里算状态，复杂度变成 O(n²)
**现象**：节点几百个之后，勾选一个部门要卡一下。

**原因**：模板里写 `countLeaves(node)` 或 `allChecked(node)`，每个节点都要遍历自己的整棵子树。

**怎么处理**：一次遍历把结果写进 `Map`，模板只查表。这是本案例步骤 4 的核心。
:::

::: details 坑 4：`buildTree` 直接改原始数据
**现象**：调用两次 `buildTree` 之后，`children` 数组里出现重复节点。

**原因**：`parent.children.push(node)` 中的 `node` 如果就是原始数组里的对象，
第一次转换给每个节点加了 `children`，第二次转换又往上堆。

**怎么处理**：第一趟就用 `{ ...item, children: [] }` 建副本。**转换函数不应该有副作用。**
:::

::: details 坑 5：数据不全，节点凭空消失
**现象**：14 条数据，树上只显示了 12 个，另外 2 个怎么都找不到。

**原因**：这两条记录的 `parentId` 指向一个不存在的节点。它们既不是根（`parentId` 不为 `null`），
也没被挂到任何父节点下，就这样丢了。

**怎么处理**：找不到父节点时当成根节点兜底，同时打日志或上报，方便发现数据问题。
**“静默丢弃”是最难排查的一类 bug。**
:::

::: details 坑 6：数据里有环
**现象**：页面卡死，控制台报 “Maximum call stack size exceeded”。

**原因**：A 的 `parentId` 指向 B，B 的 `parentId` 又指向 A。`buildTree` 之后形成环，
递归遍历永远走不到叶子。

**怎么处理**：转换时用一个 `visited` 集合记录路径，遇到重复就切断并报警。**接口数据要当成不可信输入**，
尤其是人工维护的组织架构。
:::

::: details 坑 7：用非响应式的 `Set` 存状态
**现象**：`const expanded = new Set()`（没有 `ref` 也没有 `reactive`）之后，
点展开按钮，变量里确实加进去了，但页面不动。

**原因**：普通 `Set` 不是响应式的，Vue 不知道它变了。

**怎么处理**：用 `ref(new Set())`，并且在修改后**替换成一个新 Set**。这样无论响应式系统怎么实现，
更新都不会丢。
:::

## 扩展练习

::: details 练习 1：懒加载子节点
先只请求组织者，展开某个组织者时再请求它的部门，展开部门时再请求学生。

**思路**：给节点加一个 `loaded` 标记。`toggleExpand` 里判断“要展开但还没加载过”就去请求，
请求回来把 `children` 填上。要注意三件事：

1. 加载中要有转圈，否则用户会以为点了没反应。
2. 加载失败要能把状态回退，否则这个节点永远打不开。
3. 同一个节点被连点两次展开，不要发两个请求。

:::

::: details 练习 2：加上搜索定位
输入学生姓名，自动展开从根到该学生的路径，并高亮这个学生。

**思路**：先用一次遍历找出目标节点的**祖先链**（可以在遍历时用 `Map` 记下每个节点的
`parentId`），再把这些祖先 id 合并进 `expanded`。重点是想清楚：搜索命中的节点可能有多个，
是全部展开还是只展开第一个？

:::

::: details 练习 3：改成活动分类树
把“组织架构”换成“活动分类”（学术讲座 → 理工类 → 计算机），勾选后筛选活动列表。

**思路**：树的结构完全一样，只需要换数据源和字段名 —— **这正是把树抽成通用组件的价值**。
要额外处理的是“勾选结果怎么给到父组件”：让 `OrgTree` 用 emits 把选中的叶子 id 数组传出去。
这里可以体会到，`provide` / `inject` 适合“往下传”，往上回传还是得靠 emits。
:::

::: details 练习 4：做一个可拖拽的目录树
支持把节点拖到另一个节点下，改变层级。

**思路**：用原生 `draggable` 属性加 `dragstart` / `dragover` / `drop` 三个事件就够起步。
真正的难点不是拖拽本身，而是**拖放的目标位置校验**：

- 不能把父节点拖进自己的子孙（会形成环）。
- 拖到“学生”节点下要拒绝（学生不能有下级）。
- 拖完之后要同步修改数据里的 `parentId`，并重新构建树。

不妨先把校验规则列成一张表，再写代码。

:::

---

上一页：[案例 02 · 可排序筛选的数据表格](/cases/02-grid) · 下一页：[案例 04 · 从接口获取数据](/cases/04-fetch)
