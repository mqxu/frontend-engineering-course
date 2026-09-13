# 案例 03 · 树状视图与递归组件

## 场景：场次管理里的“场地分类树”

学校有多个校区，每个校区有若干场馆，每个场馆里有若干具体场地：

```text [场地数据长这样]
主校区
├── 文体中心
│   ├── 篮球馆 A      （可容纳 200 人）
│   ├── 篮球馆 B      （可容纳 200 人）
│   └── 羽毛球馆      （可容纳 80 人）
├── 图书馆报告厅
│   └── 学术报告厅    （可容纳 300 人）
└── 田径场
    └── 标准跑道      （可容纳 1000 人）

北校区
├── 学生活动中心
│   └── 多功能厅      （可容纳 150 人）
└── 体育馆
    └── 排球馆        （可容纳 120 人）
```

安排场次时，组织者要一边看着这棵树，一边选中一个具体场地。需求有六条：

| 编号 | 需求 |
| --- | --- |
| 1 | 树形展示，能展开与收起 |
| 2 | 层级之间有明显的缩进 |
| 3 | 点击**叶子节点**（具体场地）即选中 |
| 4 | 输入关键词搜索，命中的节点要高亮 |
| 5 | 搜索时，命中项的**所有祖先自动展开** |
| 6 | 顶部显示当前选中的完整路径 |

难点在第 4 到第 6 条，以及一个结构性问题：**树的层数是不固定的**，
今天三层（校区 → 场馆 → 场地），明天可能加一层“区域”。写三层嵌套的 `v-for` 就死了。

这一节要用的关键能力是**递归组件**：一个组件在自己的模板里调用自己。

## 递归组件：为什么必须给它一个名字

### 一个组件怎么“调用自己”

在 Vue 里，单文件组件可以**隐式引用自己**：`VenueTreeNode.vue` 的模板里写
`<VenueTreeNode>`，Vue 会把它解析成自己。

也可以**显式命名**，更稳妥：

```vue [src/components/business/VenueTreeNode.vue]
<script setup>
defineOptions({ name: 'VenueTreeNode' })
</script>
```

`defineOptions` 是 Vue 3.3 起可用的编译宏，用来写那些原来要放在 `export default` 里的选项。
这里它承担的作用是**给组件起一个固定的名字**。

::: warning 什么时候必须用 `defineOptions({ name })`
| 情况 | 是否必须显式命名 |
| --- | --- |
| 文件名与要用的标签名一致，且是 `.vue` 单文件组件 | 可以不写（靠文件名推断） |
| 文件名与标签名不一致 | **必须写** |
| 组件被 `keep-alive` 缓存，需要在 Devtools 里看出是谁 | 建议写 |
| 组件要递归引用自己，且构建后文件名不可靠 | **建议写** |

**递归组件一律显式命名。** 这条规矩的理由很简单：递归是最依赖“名字对不对”的场景，
一旦名字推断失败，报错信息是 `Failed to resolve component: VenueTreeNode`，
而你会在模板里反复检查拼写，想半天也想不到是“名字没推断出来”。
:::

::: danger 另一种常见的报错
如果组件没有名字、文件名和标签名又对不上，控制台会打印：

```text [控制台输出]
[Vue warn]: Failed to resolve component: VenueTreeNode
If this is a native custom element, make sure to exclude it from component
resolution via compilerOptions.isCustomElement.
```

看到这个警告，第一反应就是**检查组件名**，而不是检查 import。
递归组件不需要 import 自己 —— 它就在自己里面。
:::

## 状态设计：展开状态放在哪里

先说一个容易做错的设计：

```js [✗ 不要这样设计]
// 直接往接口返回的数据里加字段
treeData.forEach((campus) => {
  campus.expanded = true
  campus.children?.forEach((venue) => {
    venue.expanded = false
  })
})
```

三个问题：

1. **数据来自接口，不该被 UI 状态污染。** 下一次重新拉取数据，展开状态全丢了。
2. **界面状态和业务数据混在一起**，别人读数据时不知道该看哪个字段。
3. **层数不定，代码里要写死遍历几层** —— 又是写三层 `forEach`。

正确的做法是**用一个集合单独记录“哪些节点是展开的”**：

```js [✓ 用一个 Set 记录展开的节点 id]
const userExpanded = ref(new Set())
```

对比一下：

| 方案 | 数据是否被污染 | 查找成本 | 层数变化时 |
| --- | --- | --- | --- |
| 节点上加 `expanded` 字段 | 污染了 | 要看具体节点 | 遍历代码要改 |
| **一个 `Set` 存展开的 id** | 不动原数据 | `Set.has` 是常数级 | 不需要改任何遍历 |

::: tip Vue 3 里 `Set` 是响应式的
`ref(new Set())` 会被 Vue 包装成响应式集合，`add`、`delete`、`clear` 都能触发更新。
**不需要**替换成新 `Set`，也不需要手动调用什么东西。

这一点在 Vue 2 里做不到（Vue 2 的响应式不覆盖 `Set`），所以老项目里常见“用数组存 id”的写法。
Vue 3 不用绕这个弯。
:::

展开状态由**容器组件**持有，通过属性传给每个节点，节点只负责“读”和“报告点击”：

```text [职责划分]
VenueTree（容器）
├── 持有：展开集合、搜索关键词
├── 提供：树数据、选中 id
└── 接收：toggle（要展开哪个）、select（选中哪个）
        ▲                 ▲
        │                 │
        └── VenueTreeNode（递归节点）
            ├── 只读：自己的 node、level、是否展开、是否选中
            └── 只发：toggle(node.id)、select(node)
```

**展开状态不放在节点组件里**，因为节点组件会递归出很多个实例，
状态散落在各处就没法统一控制“全部展开 / 全部收起”。

## 完整实现

三个文件：容器、递归节点、数据。先看容器。

```vue [src/components/business/VenueTree.vue]
<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import VenueTreeNode from './VenueTreeNode.vue'

const props = defineProps({
  // 树的原始数据
  nodes: { type: Array, default: () => [] },
  // 当前选中的节点 id
  selectedId: { type: String, default: '' }
})

const emit = defineEmits(['select'])

const keyword = ref('')
// 用户手动展开的节点 id 集合
const userExpanded = ref(new Set())

/* --------------------------------------------------------------------------
 * 一、搜索：找出命中的节点，以及它们的所有祖先
 * ----------------------------------------------------------------------- */
function matchTree(nodes, kw, ancestors = []) {
  const hits = new Set() // 名字命中的节点
  const expand = new Set() // 需要展开的节点（命中项的祖先 + 有命中子级的节点）

  for (const node of nodes) {
    const childResult = node.children?.length
      ? matchTree(node.children, kw, [...ancestors, node.id])
      : { hits: new Set(), expand: new Set() }

    const selfHit = node.name.toLowerCase().includes(kw)
    const hasHitInside = childResult.hits.size > 0

    if (selfHit) hits.add(node.id)
    childResult.hits.forEach((id) => hits.add(id))
    childResult.expand.forEach((id) => expand.add(id))

    // 自己命中或有子级命中 → 把自己的所有祖先都标记为需要展开
    if (selfHit || hasHitInside) {
      ancestors.forEach((id) => expand.add(id))
    }
    // 有子级命中 → 自己也要展开，否则看不见子级
    if (hasHitInside) {
      expand.add(node.id)
    }
  }

  return { hits, expand }
}

const searchState = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  if (!kw) {
    return { active: false, hits: new Set(), expand: new Set() }
  }
  const { hits, expand } = matchTree(props.nodes, kw)
  return { active: true, hits, expand }
})

/* --------------------------------------------------------------------------
 * 二、按命中的节点剪枝：保留命中项（连同它的子树）与它们的祖先
 * ----------------------------------------------------------------------- */
function pruneTree(nodes, hits) {
  const result = []
  for (const node of nodes) {
    if (hits.has(node.id)) {
      // 命中的节点整棵子树都留着，避免“点进去是空的”
      result.push(node)
      continue
    }
    const children = node.children?.length ? pruneTree(node.children, hits) : []
    if (children.length) {
      result.push({ ...node, children })
    }
  }
  return result
}

const visibleTree = computed(() => {
  if (!searchState.value.active) return props.nodes
  return pruneTree(props.nodes, searchState.value.hits)
})

/* --------------------------------------------------------------------------
 * 三、最终生效的展开集合 = 用户手动展开的 + 搜索时自动展开的
 * ----------------------------------------------------------------------- */
const expandedKeys = computed(() => {
  if (!searchState.value.active) return userExpanded.value
  const merged = new Set(userExpanded.value)
  searchState.value.expand.forEach((id) => merged.add(id))
  return merged
})

function onToggle(id) {
  // 注意：不能直接在 computed 的结果上改，要改用户手动的那一份
  if (userExpanded.value.has(id)) {
    userExpanded.value.delete(id)
  } else {
    userExpanded.value.add(id)
  }
}

function onSelect(node) {
  emit('select', node)
}

/* --------------------------------------------------------------------------
 * 四、选中的完整路径（用于顶部面包屑）
 * ----------------------------------------------------------------------- */
function findPath(nodes, id, path = []) {
  for (const node of nodes) {
    const next = [...path, node]
    if (node.id === id) return next
    if (node.children?.length) {
      const found = findPath(node.children, id, next)
      if (found) return found
    }
  }
  return null
}

const selectedPath = computed(() => findPath(props.nodes, props.selectedId) || [])

/* --------------------------------------------------------------------------
 * 五、初始把第一层展开
 * ----------------------------------------------------------------------- */
function expandRoots() {
  props.nodes.forEach((node) => {
    if (node.children?.length) userExpanded.value.add(node.id)
  })
}

onMounted(expandRoots)
// 数据是异步来的，到货之后再展开一次
watch(() => props.nodes, expandRoots)
</script>

<template>
  <div class="venue-tree">
    <div class="tree-search">
      <input v-model.trim="keyword" placeholder="搜索场地名称" />
      <button v-if="keyword" type="button" @click="keyword = ''">清空</button>
    </div>

    <p class="selected-path">
      <template v-if="selectedPath.length">
        已选场地：{{ selectedPath.map((n) => n.name).join(' / ') }}
      </template>
      <template v-else>尚未选择场地</template>
    </p>

    <p v-if="searchState.active && visibleTree.length === 0" class="empty">
      没有匹配“{{ keyword }}”的场地
    </p>

    <ul v-else class="tree-root">
      <VenueTreeNode
        v-for="node in visibleTree"
        :key="node.id"
        :node="node"
        :level="0"
        :expanded-keys="expandedKeys"
        :selected-id="selectedId"
        :keyword="keyword"
        @toggle="onToggle"
        @select="onSelect"
      />
    </ul>
  </div>
</template>

<style scoped>
.tree-search {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
}

.selected-path {
  font-size: 13px;
  color: #606266;
  margin-bottom: 8px;
}

.tree-root,
.node-children {
  list-style: none;
  margin: 0;
  padding: 0;
}

.empty {
  color: #909399;
  font-size: 13px;
}
</style>
```

递归节点组件：

```vue [src/components/business/VenueTreeNode.vue]
<script setup>
import { computed } from 'vue'

// ✓ 递归组件必须有自己的名字
defineOptions({ name: 'VenueTreeNode' })

const props = defineProps({
  node: { type: Object, required: true },
  // 当前层级，从 0 开始，用于计算缩进
  level: { type: Number, default: 0 },
  // 展开的节点 id 集合（只读，不要在这里改）
  expandedKeys: { type: Set, default: () => new Set() },
  selectedId: { type: String, default: '' },
  keyword: { type: String, default: '' }
})

const emit = defineEmits(['toggle', 'select'])

const hasChildren = computed(() => Boolean(props.node.children?.length))
const isExpanded = computed(() => props.expandedKeys.has(props.node.id))
const isSelected = computed(() => props.selectedId === props.node.id)
const isLeaf = computed(() => !hasChildren.value)

function handleClick() {
  // 叶子节点：选中；有子节点：展开/收起
  if (isLeaf.value) {
    emit('select', props.node)
  } else {
    emit('toggle', props.node.id)
  }
}

// 关键词高亮：把命中的片段切成若干段，命中的段落用 <mark> 包裹
const nameParts = computed(() => {
  const text = props.node.name
  const kw = props.keyword.trim()
  if (!kw) return [{ text, hit: false }]

  const parts = []
  const lowerText = text.toLowerCase()
  const lowerKw = kw.toLowerCase()
  let cursor = 0

  while (cursor < text.length) {
    const found = lowerText.indexOf(lowerKw, cursor)
    if (found === -1) {
      parts.push({ text: text.slice(cursor), hit: false })
      break
    }
    if (found > cursor) {
      parts.push({ text: text.slice(cursor, found), hit: false })
    }
    parts.push({ text: text.slice(found, found + kw.length), hit: true })
    cursor = found + kw.length
  }

  return parts
})
</script>

<template>
  <li class="tree-node">
    <div
      class="node-row"
      :class="{ 'is-selected': isSelected, 'is-leaf': isLeaf }"
      :style="{ paddingLeft: level * 18 + 8 + 'px' }"
      @click="handleClick"
    >
      <!-- 叶子节点不显示箭头，占位保持对齐 -->
      <span class="arrow" :class="{ 'is-open': isExpanded, 'is-invisible': isLeaf }">▶</span>

      <span class="node-name">
        <template v-for="(part, index) in nameParts" :key="index">
          <mark v-if="part.hit" class="hit">{{ part.text }}</mark>
          <template v-else>{{ part.text }}</template>
        </template>
      </span>

      <span v-if="node.capacity" class="node-meta">可容纳 {{ node.capacity }} 人</span>
    </div>

    <!-- ✓ 递归：在自己的模板里使用自己 -->
    <ul v-if="hasChildren && isExpanded" class="node-children">
      <VenueTreeNode
        v-for="child in node.children"
        :key="child.id"
        :node="child"
        :level="level + 1"
        :expanded-keys="expandedKeys"
        :selected-id="selectedId"
        :keyword="keyword"
        @toggle="emit('toggle', $event)"
        @select="emit('select', $event)"
      />
    </ul>
  </li>
</template>

<style scoped>
.node-row {
  display: flex;
  align-items: center;
  gap: 6px;
  height: 34px;
  padding-right: 8px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.node-row:hover {
  background: #f5f7fa;
}

.node-row.is-selected {
  background: #e8f2ff;
  color: #1a6fd4;
  font-weight: 600;
}

.arrow {
  width: 12px;
  font-size: 10px;
  color: #909399;
  transition: transform 0.15s;
}

.arrow.is-open {
  transform: rotate(90deg);
}

.arrow.is-invisible {
  visibility: hidden;
}

.node-meta {
  margin-left: auto;
  font-size: 12px;
  color: #909399;
}

.hit {
  background: #fff3b0;
  color: inherit;
  padding: 0 1px;
}
</style>
```

数据与使用：

```js [src/data/venues.js]
// 场地分类树：三层结构，但组件并不关心有几层
export const venueTree = [
  {
    id: 'c1',
    name: '主校区',
    children: [
      {
        id: 'v1',
        name: '文体中心',
        children: [
          { id: 'f1', name: '篮球馆 A', capacity: 200 },
          { id: 'f2', name: '篮球馆 B', capacity: 200 },
          { id: 'f3', name: '羽毛球馆', capacity: 80 }
        ]
      },
      {
        id: 'v2',
        name: '图书馆报告厅',
        children: [{ id: 'f4', name: '学术报告厅', capacity: 300 }]
      },
      {
        id: 'v3',
        name: '田径场',
        children: [{ id: 'f5', name: '标准跑道', capacity: 1000 }]
      }
    ]
  },
  {
    id: 'c2',
    name: '北校区',
    children: [
      {
        id: 'v4',
        name: '学生活动中心',
        children: [{ id: 'f6', name: '多功能厅', capacity: 150 }]
      },
      {
        id: 'v5',
        name: '体育馆',
        children: [{ id: 'f7', name: '排球馆', capacity: 120 }]
      }
    ]
  }
]
```

```vue [src/views/SessionEditView.vue]
<script setup>
import { ref } from 'vue'
import VenueTree from '@/components/business/VenueTree.vue'
import { venueTree } from '@/data/venues'

const selectedId = ref('')
const selectedVenue = ref(null)

function onSelect(node) {
  selectedId.value = node.id
  selectedVenue.value = node
}
</script>

<template>
  <VenueTree
    :nodes="venueTree"
    :selected-id="selectedId"
    @select="onSelect"
  />

  <p v-if="selectedVenue">当前选择：{{ selectedVenue.name }}</p>
</template>
```

## 三个关键点再拆开讲

### 一、递归的终止条件

递归组件最容易出的问题是**无限递归**。防止它有两个前提：

1. **数据结构本身是有限的树** —— 叶子节点的 `children` 是空数组或不存在。
2. **渲染时有条件** —— 只有 `hasChildren && isExpanded` 才渲染下一层。

```vue
<ul v-if="hasChildren && isExpanded" class="node-children">
```

如果写成无条件渲染子级：

```vue
<!-- ✗ 叶子节点也会渲染一个空的 ul，虽然不报错但会多出无意义的节点 -->
<ul class="node-children">
```

更危险的情况是**数据里有环**（A 的 children 里有 B，B 的 children 里又有 A）。
这时递归不会停，浏览器会卡死。**这类问题要在数据来源处保证**，
组件层面只能靠“数据来自接口，接口保证是树”这个前提。

::: warning 排查递归问题的一个方法
在递归组件的 `setup` 里加一行 `console.log(props.node.id)`。
如果控制台在极短时间内打印了几百条相同或循环的 id，就是数据有环。
**不要试图让组件自己检测环**，成本高、收益低 —— 让数据源头保证。
:::

### 二、缩进怎么算

缩进有两种做法：

| 做法 | 写法 | 评价 |
| --- | --- | --- |
| 用 CSS 嵌套选择器 | `.node-children .node-row { padding-left: 26px }` | 层数一多就要写很多层，且每层间距难统一 |
| **传 `level`，算出行内样式** | `paddingLeft: level * 18 + 8 + 'px'` | ✓ 层数无关，一行搞定 |

用 `level` 的方式，无论树有多少层、什么时候加一层，代码都不用改。

::: tip 为什么用 `paddingLeft` 而不是 `marginLeft`
`paddingLeft` 是元素**内部**的空间，元素的背景色会覆盖这一块。所以选中时的蓝色背景
会从最左侧一直铺到文字前面，看起来是一整行选中。用 `marginLeft` 的话，
选中背景只包住文字部分，视觉上会断掉。

**行选中效果一律用 `paddingLeft`。**
:::

### 三、搜索时自动展开祖先

这是本案例最绕的一段逻辑，核心思路是**先算出两个集合，再各用各的**：

| 集合 | 含义 | 用在哪 |
| --- | --- | --- |
| `hits` | 名字命中的节点 id | 用来**剪枝**，决定展示哪些节点 |
| `expand` | 需要展开的节点 id（命中项的祖先 + 有命中子级的节点） | 用来决定**哪些节点一开始是展开的** |

`matchTree` 是递归函数，返回值里同时带着“这一层子树里有哪些命中项”与“需要展开谁”，
父层拿到子层的返回值之后再补上“我自己要不要展开”。

必须区分“命中项本身”和“命中项的祖先”：

- **命中项本身**要保留下来（连它的子树一起保留，避免点进去是空的）。
- **祖先**只是为了让命中项可见，它们被保留是因为“有子级幸存”，不是为了自己。

::: warning 搜索时用户手动收起会“弹回来”
在搜索状态下，`expandedKeys` 是“用户手动展开的”与“搜索自动展开的”两部分合并。
所以手动收起一个自动展开的节点，下一次重算又会被自动展开。

**这是有意的**：搜索的目的就是让你看到命中项，收起来就看不到了。
如果你希望它能真正收起，就要在搜索时禁用自动展开的合并，
代价是“搜索完发现命中项在折叠的枝干里找不到”，体验更差。
:::

## 小结

- 递归组件在自己的模板里使用自己。**在 `<script setup>` 里靠文件名可以隐式引用，
  但递归场景建议用 `defineOptions({ name })` 显式命名**，避免解析失败。
- 报错 `Failed to resolve component` 时，第一反应是**检查组件名**，不是检查 import。
- 展开状态用**一个 `Set` 存 id**，不要往接口数据里加 `expanded` 字段；
  Vue 3 的 `Set` 是响应式的，`add` / `delete` 都能触发更新。
- 展开状态放在容器组件里，节点组件只读、只上报 `toggle` 与 `select`。
- 缩进用 `level` 算 `paddingLeft`，层数变化不影响代码。
- 搜索要算两个集合：**命中的 id 用于剪枝，祖先的 id 用于自动展开**。
- 递归的两个前提：**数据是有限的树**、**渲染有条件**；数据有环会导致浏览器卡死。

## 常见坑

::: details 坑 1：递归组件没命名，报 `Failed to resolve component`
**现象**：模板里写 `<VenueTreeNode>`，控制台警告组件无法解析，树只渲染第一层。

**原因**：组件名没被推断出来，或者文件名与标签名不一致。

**处理**：在 `defineOptions({ name: 'VenueTreeNode' })` 里显式命名，
并保证模板里的标签名与它完全一致（大小写也要一致）。
:::

::: details 坑 2：展开了但子节点没显示
**现象**：箭头转了，但子节点是空的。

**原因**：三种可能。一是 `isExpanded` 判断的集合不对；
二是子节点数据里字段名不是 `children`；三是传递属性时漏了 `expandedKeys`，
子组件用的是默认的空集合。

**处理**：检查递归调用那一串属性有没有全部传下去。**递归组件漏传属性是很常见的错误**，
因为每一层都要重复写一遍。传的属性超过四个时，考虑用 `v-bind` 打包 ——
或者把它改成[依赖注入](/unit08/02-provide-inject)。
:::

::: details 坑 3：搜索之后点叶子节点选不中
**现象**：搜索出结果，点其中的场地没有反应。

**原因**：剪枝时把原本有子节点的节点变成了“看起来的叶子”，
`isLeaf` 判断基于剪枝后的数据，于是点它就被当成“切换展开”，实际没有子节点可展开。

**处理**：本文的实现里，命中项的**整棵子树都保留**，所以不会出现这个问题。
如果你用了更激进的剪枝（把命中项的子树也剪掉），就必须额外记录“这个节点原本有没有子节点”。
:::

::: details 坑 4：直接改 `expandedKeys` 这个属性
**现象**：节点组件里写了 `props.expandedKeys.add(id)`，控制台没有警告，
但收起功能失效（因为只会加不会删），而且状态绕过了容器组件。

**原因**：`Set` 是对象，改它的内部成员不会触发 props 的只读警告。

**处理**：节点组件只发 `toggle` 事件，改动由容器完成。
**这是“改 props 内部成员”这个坑在集合类型上的版本。**
:::

::: details 坑 5：树数据是异步加载的，初始展开失效
**现象**：第一层没有自动展开。

**原因**：`onMounted` 时 `props.nodes` 还是空数组（数据还没回来）。

**处理**：加一个 `watch(() => props.nodes, expandRoots)`，数据到位后再展开一次。
**只要数据是异步的，“挂载时初始化”这件事就要多想一步。**
:::

## 课后练习

::: details 练习 1：加一个“全部展开 / 全部收起”按钮
需求：顶部两个按钮，一个展开所有有子节点的节点，一个清空展开状态。

**参考思路**：需要一个函数**递归遍历整棵树**，收集所有“有子节点”的节点 id
（这和 `matchTree` 的遍历方式一样，只是判断条件更简单）。
留意按钮在搜索状态下的行为 —— 搜索时改的是 `userExpanded`，
而 `expandedKeys` 是合并结果，所以按钮点了可能“看不出变化”。先想清楚这算不算 bug。

:::

::: details 练习 2：把“选中”扩展成“多选”
需求：场地可以多选，顶部显示“已选 3 个场地”，并提供清空按钮。

**参考思路**：`selectedId` 变成 `selectedIds`（用 `Set`），
事件名从 `select` 改成 `toggle-select`。**先想清楚两个问题**：
选中父节点要不要把子节点全选上？父节点下部分子节点被选中时，父节点显示什么？
这两个问题没有标准答案，**说明你的选择和理由**。

:::

::: details 练习 3：支持键盘操作
需求：Tab 能聚焦到节点上，方向键上下移动焦点，右键展开，回车选中。

**参考思路**：这需要给每个节点行加 `tabindex`，并维护一个“当前聚焦的节点 id”。
方向键的上下移动在这棵树上是**按显示顺序**走的，所以要先算出一个“展开后的平铺列表”。
这个列表可以是一个 `computed`，递归地把可见节点按顺序收集起来。
**这道题的价值在于让你意识到：树形组件做键盘操作的成本比列表高得多。**

:::

::: details 练习 4：为什么不用三个嵌套的 `v-for`
假设树固定三层，用三个嵌套 `v-for` 也能实现。写一小段这样的代码，
然后列三条“相比递归组件，它更差在哪里”。

**参考思路**：三条里至少有一条应该是“层数一变就要改代码”。
另外想想“每层的展开状态怎么管”—— 三个独立的状态变量，会带来多少额外代码。

:::

---

上一节：[7.4 组件上的 v-model](/unit07/04-vmodel) ·
下一节：[案例 09 · 可编辑表格](/unit07/06-case-editable-table)
