# 数据看板 · 参考实现

数据看板是登录后看到的第一个页面。它的作用不是“把系统里的数字集中展示一遍”，而是**告诉使用者现在该做什么**。

这是看板模块和别的模块最大的不同：列表页有明确的任务（找到那条记录并处理），看板没有 —— 用户打开它，然后呢？如果页面上只是一堆数字，用户看完就走了，这个页面就白做了。所以这一篇的重点不在图表怎么画，而在**信息怎么排**。

## 一、模块范围与页面地图

### 页面 → 路由 → 接口

看板只有一个页面，但它要调三个接口：

| 区块 | 路由 | 接口 | 返回什么 |
| --- | --- | --- | --- |
| 指标卡 | `/dashboard` | `GET /api/dashboard/overview` | 活动总数、按状态分布、报名数、名额使用率等 |
| 待办提醒 | 同上 | `GET /api/dashboard/todos` | 待审核数、48 小时内截止的活动、冲突场次 |
| 近期活动 | 同上 | `GET /api/dashboard/recent-activities?limit=5` | 最近更新的几条活动 |

**权限**：组织者看到的是只统计自己活动的数据，审核员看到全部。**过滤在后端做**，前端不传 `organizerId`。这一点下面第八节单独讲。

### 数据流

```
/dashboard
    │  页面挂载
    ▼
并发发出三个请求（用 Promise.allSettled）
    ├─> GET /api/dashboard/overview ────────> 指标卡区块
    ├─> GET /api/dashboard/todos ───────────> 待办区块
    └─> GET /api/dashboard/recent-activities> 近期活动区块
    │
    ▼
每个区块独立结算：成功就填数据，失败就显示自己的错误提示
其他区块不受影响
```

**“每个区块独立结算”是这一页的核心机制。** 看板是聚合页，任何一个接口挂了，都不应该让整页变成空白。

## 二、信息架构：待办比统计更有价值

先看一个反例。很多同学的第一版看板是这样的：

```
活动总数 36    报名总数 1284    已通过 936    场地数 8
```

四个数字，一排摆开，看起来很整齐。**但它回答了什么问题？** “一共 36 个活动”—— 然后呢？用户接下来要做什么？

**统计是给上级看的，待办是给使用者用的。** 组织者打开后台的真实目的是“我现在有什么活要干”，而不是“系统里一共有多少数据”。看板应该先回答这个问题。

所以三个区块的排序是：

| 顺序 | 区块 | 回答什么问题 | 用户看完做什么 |
| --- | --- | --- | --- |
| 1 | 待办提醒 | 我现在该处理什么 | 点进去处理 |
| 2 | 指标卡 | 整体情况怎么样 | 心里有数 |
| 3 | 近期活动 | 我最近动过哪些活动 | 继续编辑，或查看详情 |

**待办放最上面，是因为它是唯一带“动作”的区块。** 看到“有 47 条报名在等你审核”，用户会点进去；看到“活动总数 36”，用户不会有任何反应。

待办区块的每一项都要能点，点了要跳到对应的列表页并带上筛选条件：

| 待办项 | 点击后去哪 | 带什么参数 |
| --- | --- | --- |
| 待审核报名 47 条 | `/signup` | `status=PENDING` |
| 48 小时内截止的活动 | `/activity/:id` | 直接进那一个活动 |
| 有冲突的场次 | `/session` | 定位到冲突的场次 |

**“能点”这个要求不是随手加的。** 一个显示“47 条待审核”但不给入口的看板，用户还得自己去侧边栏找报名列表、再手动筛“待审核”。**看板的价值就在于省掉这几步。**

如果时间实在不够，砍掉指标卡，也要保住待办区块。**待办是这个页面的存在理由。**

## 三、三个接口并行请求

### 接口封装

```js [src/api/dashboard.js]
import request from './request'

/** 统计概览。组织者只统计自己的活动，过滤在后端做 */
export function getOverview() {
  return request.get('/dashboard/overview')
}

/** 最近更新的活动。按 updatedAt 倒序 */
export function getRecentActivities(limit = 5) {
  return request.get('/dashboard/recent-activities', { params: { limit } })
}

/** 待办：待审核数、即将截止的活动、有冲突的场次 */
export function getTodos() {
  return request.get('/dashboard/todos')
}
```

### 为什么用 `Promise.allSettled` 而不是 `Promise.all`

三个接口互相独立，可以同时发，总耗时约等于最慢的那个。但“并行”的写法有两种，选错了会有很明显的后果。

```js
// ✗ Promise.all：任何一个失败，整段直接进 catch
try {
  const [overview, recent, todos] = await Promise.all([
    getOverview(),
    getRecentActivities(5),
    getTodos()
  ])
  // 三个都成功才会走到这里
} catch (e) {
  // “近期活动”挂了，但概览和待办明明都成功，结果也全丢了
  ElMessage.error('看板加载失败')
}
```

`Promise.all` 的规则是“有一个失败就整体失败”。**它还有一个更隐蔽的问题：失败的 promise 会立刻让整段进入 `catch`，而此时其他两个请求可能已经成功了，返回值却被丢掉。** 用户看到的是整页空白，只有一个“加载失败”。

```js
// ✓ Promise.allSettled：三个请求各自结算，互不影响
const tasks = [
  { key: 'overview', run: () => getOverview() },
  { key: 'recent', run: () => getRecentActivities(5) },
  { key: 'todos', run: () => getTodos() }
]

const results = await Promise.allSettled(tasks.map((t) => t.run()))
```

`allSettled` 返回的每一项要么是 `{ status: 'fulfilled', value }`，要么是 `{ status: 'rejected', reason }`，**而且它自己永远不会 reject**，所以外层不用包 `try / catch`。

| 方法 | 失败时的行为 | 适合的场景 |
| --- | --- | --- |
| `Promise.all` | 一个失败，整体失败，返回值全丢 | 所有请求必须全部成功（一份表单的多个必填部分） |
| `Promise.allSettled` | 各请求独立结算 | 各请求互相独立（看板的多个区块） |

**判断标准是“这几个请求之间有没有依赖”。** 看板的三个区块只是碰巧显示在同一页，它们之间没有任何依赖关系，所以用 `allSettled`。

### 页面里的写法

```js [src/views/dashboard/DashboardView.vue（脚本节选）]
import { reactive, ref, onMounted } from 'vue'
import { getOverview, getRecentActivities, getTodos } from '@/api/dashboard'

const overview = ref(null)
const recentActivities = ref([])
const todos = ref(null)

// 每个区块各自维护加载态和错误，互不干扰
const loading = reactive({ overview: true, recent: true, todos: true })
const errors = reactive({ overview: null, recent: null, todos: null })

const tasks = [
  { key: 'overview', run: () => getOverview() },
  { key: 'recent', run: () => getRecentActivities(5) },
  { key: 'todos', run: () => getTodos() }
]

async function loadAll() {
  // 重试时先把状态复位，否则上一次的错误提示会一直挂着
  tasks.forEach((t) => {
    loading[t.key] = true
    errors[t.key] = null
  })

  const results = await Promise.allSettled(tasks.map((t) => t.run()))

  results.forEach((result, index) => {
    const { key } = tasks[index]
    loading[key] = false
    if (result.status === 'fulfilled') {
      if (key === 'overview') overview.value = result.value
      if (key === 'recent') recentActivities.value = result.value
      if (key === 'todos') todos.value = result.value
    } else {
      errors[key] = result.reason
    }
  })
}

onMounted(loadAll)
```

**三个细节：**

**一、`loading` 和 `errors` 用 `reactive` 对象按区块分开。** 用一个全局的 `loading` 会导致“概览已经加载完，但骨架屏还在转”—— 因为另一个接口没回来。每个区块管自己的状态。

**二、重试时先复位。** 不把 `errors[key]` 清空的话，用户点了重试、这一次成功了，上一次的红色错误提示还挂在页面上。

**三、`reason` 不是 `value`。** `allSettled` 里失败项的字段名是 `reason`，成功项是 `value`。写混了不报错，只是拿到的永远是 `undefined`。

**每个区块的失败提示要独立。** 不要用一个全屏的 `ElMessage.error`，那样用户点一次重试会弹三条。正确做法是在对应区块内部显示一行“加载失败，重试”：

```vue
<div v-if="errors.todos" class="block-error">
  <span>待办加载失败：{{ errors.todos.message }}</span>
  <el-button link type="primary" @click="loadAll">重试</el-button>
</div>
```

## 四、指标卡组件

指标卡是这个页面上重复最多的东西：概览里有四到六个，每个都是“一个标签 + 一个数字 + 一点说明”。**一个组件渲染多个指标，用 `props` 驱动。**

```vue [src/components/MetricCard.vue]
<script setup>
import { formatNumber } from '@/utils/format'

defineProps({
  label: { type: String, required: true },
  value: { type: [Number, String], default: 0 },
  /** 数字后面的单位，比如“个”“人” */
  suffix: { type: String, default: '' },
  /** 数字下面的说明，比如“其中 5 个还是草稿” */
  hint: { type: String, default: '' },
  /** 颜色语气：default / danger / warning / success */
  tone: { type: String, default: 'default' },
  /** 加载中显示骨架，避免布局跳动 */
  loading: { type: Boolean, default: false }
})
</script>

<template>
  <el-card shadow="never" class="metric-card">
    <el-skeleton :loading="loading" animated :rows="2">
      <template #default>
        <p class="metric-label">{{ label }}</p>
        <p class="metric-value" :class="`tone-${tone}`">
          {{ formatNumber(value) }}<span v-if="suffix" class="metric-suffix">{{ suffix }}</span>
        </p>
        <p class="metric-hint">{{ hint || '\u00A0' }}</p>
      </template>
    </el-skeleton>
  </el-card>
</template>

<style scoped>
.metric-label {
  margin: 0 0 8px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.metric-value {
  margin: 0 0 8px;
  font-size: 28px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.metric-suffix {
  margin-left: 4px;
  font-size: 14px;
  font-weight: 400;
  color: var(--el-text-color-secondary);
}

.metric-hint {
  margin: 0;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.tone-danger {
  color: var(--el-color-danger);
}

.tone-warning {
  color: var(--el-color-warning);
}

.tone-success {
  color: var(--el-color-success);
}
</style>
```

用法是把它排成一行，一组指标就是一组 `props`：

```vue [src/views/dashboard/DashboardView.vue（模板节选）]
<el-row :gutter="12">
  <el-col :span="6">
    <MetricCard
      label="活动总数"
      :value="overview?.activityTotal"
      suffix="个"
      :hint="`其中 ${overview?.activityByStatus?.SIGNING ?? 0} 个报名中`"
      :loading="loading.overview"
    />
  </el-col>

  <el-col :span="6">
    <MetricCard
      label="待审核报名"
      :value="todos?.pendingSignupCount"
      suffix="条"
      tone="warning"
      hint="点右侧待办区去处理"
      :loading="loading.todos"
    />
  </el-col>

  <el-col :span="6">
    <MetricCard
      label="已通过报名"
      :value="overview?.approvedTotal"
      suffix="人次"
      :loading="loading.overview"
    />
  </el-col>

  <el-col :span="6">
    <MetricCard
      label="今日占用场地"
      :value="overview?.venueUsageToday"
      suffix="个"
      :hint="`场地总计 ${overview?.venueTotal ?? 0} 个`"
      :loading="loading.overview"
    />
  </el-col>
</el-row>
```

**两个细节：**

- **`font-variant-numeric: tabular-nums`** 让数字用等宽字形。不加的话，`1,284` 和 `936` 位数不同、字宽也不同，加载完数字一变，整个卡片的宽度和排版会轻微抖动。
- **`hint` 为空时补一个不换行空格**（`'\u00A0'`）。空字符串也会占用一行高度，但不写这个兜底，有的浏览器会把这行折叠掉，卡片高度就变了；补一个不占视觉的空格，高度稳定。

**为什么要抽组件。** 四个指标卡，如果每个都手写一遍 `<el-card><p>...</p></el-card>`，样式就有四份，改字号要改四处。抽出来之后，加一个指标就是加一组 `props`，样式只有一份。

## 五、占比可视化：用 SVG 画环形进度

名额使用率适合用环形进度表示。很多同学的第一个念头是“引个 ECharts”。

**不要引。** 这一节说清为什么，以及不引库怎么画。

### 为什么不引 ECharts

| 方案 | 体积（gzip 后） | 这个场景需要的能力 |
| --- | --- | --- |
| ECharts 完整包 | 约 300 KB | 用不到 |
| ECharts 按需引入（只引饼图） | 约 100 KB | 用不到 |
| 一段 SVG | 0 KB（平台自带） | 一个圆环 + 一个百分比数字 |

**为了一个环形图，把首屏体积加回去 100 KB 以上，不划算。** [12.2 构建优化](/unit12/02-build-optimize)里做过一件事：把路由懒加载加上，首屏从 1.4 MB 降到 320 KB。看板是登录后的第一个页面，一定会加载，在这上面加 100 KB 等于把优化的成果吃掉三分之一。

**判断标准是“图表复杂度”。** 需要折线、柱状、堆叠、缩放、图例联动的时候，ECharts 值这个体积；只是画一个“占了多少”的环，SVG 十几行代码就够了。**不要为了一个简单的视觉元素引入一个大库**，这是[12.2](/unit12/02-build-optimize)讲的“重库换轻量替代”的同一个思路。

### SVG 环形进度的实现

原理很简单：画两个同心圆，底层是灰色轨道，上层是彩色进度。彩色圆用 `stroke-dasharray` 把圆周画成虚线，再用 `stroke-dashoffset` 把不需要的部分藏起来。

```vue [src/components/RingProgress.vue]
<script setup>
import { computed } from 'vue'

const props = defineProps({
  /** 比例，0 到 1。传 0.73 表示 73% */
  percent: { type: Number, default: 0 },
  size: { type: Number, default: 120 },
  stroke: { type: Number, default: 12 }
})

// 半径要减去线宽的一半，否则圆环会被画到画布外面
const radius = computed(() => (props.size - props.stroke) / 2)

// 圆的周长，也就是虚线要覆盖的总长度
const circumference = computed(() => 2 * Math.PI * radius.value)

// dashoffset 越大，藏起来的越多。比例越大，藏起来的越少
const dashOffset = computed(() => {
  const ratio = Math.min(Math.max(props.percent, 0), 1)
  return circumference.value * (1 - ratio)
})

// 百分比文字，保留一位小数
const percentText = computed(() => `${(props.percent * 100).toFixed(1)}%`)
</script>

<template>
  <svg :width="size" :height="size" class="ring" role="img">
    <!-- 底层轨道 -->
    <circle
      :cx="size / 2"
      :cy="size / 2"
      :r="radius"
      fill="none"
      stroke="var(--el-fill-color-light)"
      :stroke-width="stroke"
    />
    <!-- 进度：从 12 点方向开始画，所以要旋转 -90 度 -->
    <circle
      :cx="size / 2"
      :cy="size / 2"
      :r="radius"
      fill="none"
      stroke="var(--el-color-primary)"
      :stroke-width="stroke"
      stroke-linecap="round"
      :stroke-dasharray="circumference"
      :stroke-dashoffset="dashOffset"
      :transform="`rotate(-90 ${size / 2} ${size / 2})`"
      class="ring-progress"
    />
    <text
      :x="size / 2"
      :y="size / 2"
      text-anchor="middle"
      dominant-baseline="central"
      class="ring-text"
    >
      {{ percentText }}
    </text>
  </svg>
</template>

<style scoped>
.ring-progress {
  /* 数据变化时平滑过渡。不加的话百分比跳变会显得生硬 */
  transition: stroke-dashoffset 0.6s ease;
}

.ring-text {
  font-size: 20px;
  font-weight: 600;
  fill: var(--el-text-color-primary);
}
</style>
```

**三处关键：**

- **`radius` 要减去线宽的一半。** 不减的话，圆环的中心线落在 `size / 2` 到边缘的距离上，线宽会有一半画到画布外面，看着像被切了一刀。
- **旋转 `-90` 度。** SVG 的圆默认从 3 点方向开始画，进度条是从右边长出来的。旋转到 12 点方向更符合“进度”的直觉。
- **`stroke-dasharray` 和 `stroke-dashoffset` 是一对。** `dasharray` 设成整个周长，等于画一条和周长一样长的实线；`dashoffset` 把它往后推，推出去的部分被裁掉，剩下的就是可见的进度。

如果只是想要一个进度条，不做环形，那就更简单 —— 一个 `div` 加宽度百分比：

```vue
<el-progress :percentage="Math.round((overview?.quotaUsageRate ?? 0) * 100)" :stroke-width="14" />
```

**Element Plus 自带的 `el-progress` 已经能满足进度条，不需要自己写。** 只有环形 + 中心文字这种它做不了的组合，才需要上面的 SVG 组件。

### 使用率要显示分子和分母

不管是环形还是进度条，**旁边都要把原始数字写出来**：

```
名额使用率  73.0%
已通过 936 人次 / 名额合计 1284
```

**一个孤零零的百分比是不可信的。** 用户会想“73% 是怎么来的”，尤其是当它和活动列表里看到的数字对不上时。把 `approvedTotal` 和 `quota` 合计都显示出来，用户自己能核对，信任度就上来了。

这也顺便解决了“算法不一致”这类问题 —— 算法写在接口文档里，算式显示在界面上，两边对得上。

## 六、名额使用率的算法

这一节单独讲，因为它是看板上最容易产生争议的一个数字。

### 两种算法，结果差一倍

“整体名额使用率”有两种算得通的做法，结果差别巨大。举例：看板统计到两个活动。

| 活动 | 名额 `quota` | 已通过 `approvedCount` | 单个活动的使用率 |
| --- | --- | --- | --- |
| 活动 A | 10 | 10 | 100% |
| 活动 B | 1000 | 100 | 10% |

**算法一：求和再除**

```
(10 + 100) / (10 + 1000) = 110 / 1010 ≈ 10.9%
```

**算法二：逐活动算完再平均**

```
(100% + 10%) / 2 = 55%
```

**一个是 10.9%，一个是 55%，差了五倍。** 两个都不是错的，它们回答的是不同的两个问题：

| 算法 | 回答的问题 | 什么时候用它 |
| --- | --- | --- |
| 求和再除 | 整体资源用了多少 | 关心场地、名额这些资源的实际消耗 |
| 逐活动平均 | 活动平均火爆程度 | 关心“典型的活动有多受欢迎” |

### 本项目用求和再除

**理由**：看板服务的对象是组织者和审核员，他们关心的问题是“还有多少名额空着，能不能再安排”，这是一个资源问题，不是热度问题。求和再除算出来的 10.9% 说明“整体还有近九成名额没被占用”，这个结论对决策有用；逐活动平均出来的 55% 什么都说明不了 —— 一个名额 10 人的小活动爆满，不该把 1000 人大活动的数据拉高。

**而且求和再除不容易被小样本带偏。** 只要有一个名额 2 人的活动报满了，逐活动平均就会往 100% 拉一大截，哪怕其他活动都很空。

### 前端不要自己算

`quotaUsageRate` 由后端算好返回，前端只负责格式化显示。三个原因：

1. **前端拿不到算这个数需要的全部数据。** `overview` 里给的是 `approvedTotal` 和 `quotaUsageRate`，没给每个活动的 `quota` 明细。要用算法二的话，前端得把每个活动都拉下来，那是几十个请求。
2. **前后端必须用同一套算法。** 如果前端自己算一个、后端算一个，界面上出现两个不一样的百分比，用户会怀疑整个系统。
3. **这条必须写进接口文档。** [接口约定](/project/api)第九节已经写明了“课程项目用求和再除”，这就是“算法是契约的一部分”的例子 —— 它不像字段名那样显眼，但一旦两边理解不一致，问题很难查。

```js
// ✗ 前端自己算，和后端口径可能不一致
const rate = overview.value.approvedTotal / 1284

// ✓ 用后端给的
const rate = overview.value.quotaUsageRate
```

## 七、空状态与加载骨架

看板上的数字有三种状态：还没加载、加载完了、加载失败。**最容易出问题的是“还没加载”到“加载完”这一步 —— 数字出现时布局会跳。**

### 骨架屏要预留和真实内容一样的高度

```vue
<el-skeleton :loading="loading.overview" animated :rows="2">
  <template #default>
    <!-- 真实内容 -->
  </template>
</el-skeleton>
```

`el-skeleton` 的 `:rows="2"` 要**和真实内容的行数对上**。真实内容是“一行标签 + 一行大数字 + 一行说明”，骨架就给三行。差一行，加载完的高度就变，下面的内容会被顶着一跳。

**更稳的做法是给数值区一个固定的高度：**

```css
.metric-card :deep(.el-skeleton__item) {
  height: 16px;
}

.metric-value {
  min-height: 40px;   /* 字号 28px 加行高，留够空间 */
  line-height: 40px;
  margin: 0;
}
```

`min-height` 而不是 `height`，是因为数字可能出现“—”（加载失败或没有数据），也可能换行，留一点余量比锁死高度安全。

### 三个区块各自有空状态

| 区块 | 没数据时显示什么 | 引导动作 |
| --- | --- | --- |
| 指标卡 | 数字显示 0，不显示“—” | 无 |
| 待办 | “暂时没有要处理的事情” | 无（这是好消息） |
| 近期活动 | “还没有活动” | “去创建一个”按钮 |
| 某区块加载失败 | “加载失败，重试” | 重新加载这个区块 |

**待办的“空”和别的区块的“空”语气不一样。** 待办空了是好事，文案要写得轻松一点（“暂时没有要处理的事情，可以歇会儿”），不要用“暂无数据”这种像出错了一样的文案。**同一句“暂无数据”在四个区块里重复出现，会让用户以为系统坏了。**

## 八、权限差异

| 角色 | 看板看到的数据 | 前端怎么体现 |
| --- | --- | --- |
| 组织者 | 只统计自己的活动 | 标题写“我的活动概览” |
| 审核员 | 统计全部活动 | 标题写“全部活动概览” |

### 过滤在后端做，前端不传 `organizerId`

```js
// ✗ 前端传 organizerId：改一下参数就能看到别人的数据，等于没有权限控制
getOverview({ organizerId: userStore.userInfo.id })
```

**正确做法是后端从 token 里取当前用户身份，自己决定过滤范围。** 前端只管显示，一个参数都不传。

**为什么这条很重要**：看板是聚合数据，前端一过滤（比如“只显示我的活动的数字”）就会出错 —— 因为 `activityTotal`、`approvedTotal` 这些值是后端算好的聚合结果，前端手里没有明细，没法在本地把它拆成“只看我的”。**要么后端给对，要么全靠前端，没有中间选项。** 而看板不能全靠前端，见上面第五节的算法说明。

**前端能做的只有两件事：**

1. **按角色改文案。** 组织者看到大面积的全站数字会以为统计错了，标题写“我的活动概览”能消除这个疑惑。
2. **不要在前端加任何未授权的入口。** 比如“查看全部活动”按钮，组织者点了会 403。**与其给一个点了报错的按钮，不如不给。**

**验收的时候要专门测一次**：用组织者账号打开看板，记下活动总数；打开活动列表，数一下自己的活动数。**两个数字必须相等。** 如果看板显示的是全站总数，就是后端没过滤，这是数据权限漏洞。

## 九、数字格式化

数字的格式统一放在 `utils/format.js`，不要在模板里写 `.toFixed(1)` 这类逻辑。

```js [src/utils/format.js]
/** 大数加千分位：1284 -> 1,284。空值显示一个短横 */
export function formatNumber(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '—'
  return Number(value).toLocaleString('zh-CN')
}

/** 比例转百分比：0.7312 -> 73.1%。digits 控制小数位数 */
export function formatPercent(value, digits = 1) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '—'
  return `${(Number(value) * 100).toFixed(digits)}%`
}
```

| 场景 | 用什么 | 结果 |
| --- | --- | --- |
| 活动总数、报名数 | `formatNumber` | `1,284` |
| 名额使用率 | `formatPercent` | `73.1%` |
| 没有数据 | 两个函数都返回 `—` | `—` |

**两个容易写错的地方：**

**一、`toFixed` 是四舍六入五成双吗？** 不是。JavaScript 的 `toFixed` 用的是浮点数近似处理，`(0.735).toFixed(2)` 在不同引擎上可能得到 `73` 或 `74`。**看板上的百分比不需要精确到这种程度**，保留一位小数就不会碰到这个边界。**不要去纠结 `toFixed` 的舍入规则**，除非你在做财务系统。

**二、`—` 不是 `-`。** 没有数据时显示一个短横，用全角的长横（`—`）在视觉上和负号区分开，用户不会误以为这个数字是负数。

**还有一个相反的坑**：数据库里的 0 是有效数据，不能显示成 `—`。判断空值要用 `=== null || === undefined`，**不要用 `if (!value)`** —— 那样会把 0 也当成空。

```js
// ✗ 0 会被当成空值
if (!value) return '—'

// ✓ 只有 null 和 undefined 才是空
if (value === null || value === undefined) return '—'
```

## 十、关键决策

### 决策一：待办区块放在最上面

**选了什么**：页面从上到下依次是待办、指标卡、近期活动。

**为什么**：看板的用户是来“找活干”的，不是来“看数据”的。待办是唯一带动作的区块，放最上面能让人一进来就看到。**统计放中间是因为它是背景信息，不是任务。**

**代价**：待办为空时，页面顶部会空出一块。这个代价可以接受，而且待办为空本身是好事，可以把空状态做得轻快一点。

### 决策二：三个接口并行，用 `Promise.allSettled`

**选了什么**：概览、待办、近期活动拆成三个接口，页面并发请求，各自处理失败。

**为什么**：拆开之后职责清晰，每个接口可以单独缓存、单独重试；用 `allSettled` 是因为三个区块互不依赖，任何一个挂了其他两个还能显示。接口约定里也讨论过“合成一个接口”的方案，但那个方案会让“近期活动”的一个 bug 拖垮整页。

**代价**：三个请求而不是一个，网络开销略大（在一个校园内网里可以忽略），而且前端要写按区块处理结果的循环。多写十来行代码，换来容错能力。

### 决策三：环形图用 SVG 手写，不引 ECharts

**选了什么**：名额使用率用一个 SVG 圆环加中心文字，进度条直接用 `el-progress`。不引入任何图表库。

**为什么**：这个页面需要的只有“一个环”和“一条进度条”，复杂度极低。为了它引入一个 gzip 后上百 KB 的库，会把[12.2](/unit12/02-build-optimize)里把首屏降到 320 KB 的优化成果吃掉一大块。SVG 是浏览器自带的，零依赖，十几行代码就能画。

**代价**：以后如果看板真的要加折线图或者柱状图，得重新评估、可能要引库。**但到那时候再引，代价也比现在为了一个环就引小。**

### 决策四：使用率用“求和再除”，且算法写进接口文档

**选了什么**：`quotaUsageRate = 所有活动的 approvedCount 之和 / 所有活动的 quota 之和`。后端算，前端显示，算法写进[接口约定](/project/api)。

**为什么**：看板的使用率要回答“整体还有多少资源空着”，这是资源问题，求和再除才反映资源消耗；逐活动平均反映的是热度，会小样本带偏。

**代价**：这个算法对每个活动是“一视同仁”的，一个 10 人的活动和 1000 人的活动在分子分母里的权重不同（按人数加权），可能掩盖“某个小活动爆满”。缓解办法是同时显示活动总数和按状态分布，用户能看到全局构成。

## 十一、常见坑

::: details 数字加载完，页面往下一跳
**现象**：打开看板，先看到一个转圈的骨架，几百毫秒后数字出现，下面的内容整体往下跳了一下。

**原因**：骨架屏的高度和真实内容的高度不一致。骨架是两根细条，真实内容是“标签 + 大数字 + 说明”三行，高度差出了一大截。

**怎么处理**：三件事。

1. `el-skeleton` 的 `:rows` 和真实内容行数对上。
2. 给数字区一个 `min-height`，让骨架和真实内容都落在同一个高度里。
3. `hint` 为空时补一个不换行空格（`'\u00A0'`），否则这一行会被折叠，高度又变了。

**这类“加载完跳一下”的问题在首屏尤其明显**，因为它发生在用户第一次看到页面的时候，是用户对系统的第一印象。**骨架屏的价值就是让布局在加载前后保持稳定**，高度对不上，骨架屏反而更糟 —— 用户会先看到一个大数字的位置，再看到它缩成两个字。
:::

::: details 用 `Promise.all`，一个接口失败整页空白
**现象**：网络正常的时候看板一切正常。某天“近期活动”接口查得慢、超时了，整个看板变成一片空白，只有一个“加载失败”的提示，而概览和待办的数据其实都请求成功了。

**原因**：`Promise.all` 的特性是“一个失败整体失败”，其余成功的结果会被丢掉。用户因此以为“看板坏了”，其实坏的是一个小区块。

**怎么处理**：改成 `Promise.allSettled`，按区块处理结果：

```js
const results = await Promise.allSettled(tasks.map((t) => t.run()))
results.forEach((result, index) => {
  const { key } = tasks[index]
  loading[key] = false
  if (result.status === 'fulfilled') {
    // 把值赋给对应的 ref
  } else {
    errors[key] = result.reason      // 注意是 reason，不是 value
  }
})
```

**还要注意 `loading` 重置的位置。** 出错的那一项也要把 `loading` 置为 `false`，否则那个区块的骨架会一直转下去。**骨架屏永远不消失，比显示一条错误更糟** —— 用户会一直等。
:::

::: details 看板上的使用率和自己算的对不上
**现象**：看板显示名额使用率 55%，但在活动列表里大致一算，感觉只有 10% 左右。两个数字差了好几倍。

**原因**：两端用了不同的算法。看板用了“逐活动平均”，而心里估算的是“求和再除”。两个都算得通，但结果差很多。

**怎么处理**：**先定一个算法，然后写进接口文档，两边都照它来。**

本项目的选择是求和再除：

```
approvedTotal / quotaTotal = 936 / 1284 ≈ 72.9%
```

前端不要自己算，用 `overview.quotaUsageRate`。同时**把分子分母都显示在界面上**（“已通过 936 人次 / 名额合计 1284”），用户能自己核对，就不会怀疑这个百分比。

**这类“同一个指标两种算法”的问题不限于使用率。** “平均报名数”也有两种算法（按活动平均、按组织者平均），“响应时间”也有（平均值、中位数）。**每一个由后端算的指标，都应该在接口文档里写明算法。** 这是接口契约的一部分。
:::

::: details 组织者看到了全站的统计数据
**现象**：用组织者账号登录，看板上的活动总数是 36，但打开活动列表只有自己的 4 个活动。

**原因**：`overview` 接口没有按当前用户过滤，返回的是全站数据。前端也没法补救 —— 因为这是聚合值，前端手里没有明细，没法在本地拆成“只看我的”。

**怎么处理**：**后端从 token 里取用户身份，自己决定过滤范围。** 前端不传 `organizerId`，也不能靠前端过滤。

**这条要在联调时专门验证。** 验证方法：用组织者账号打开看板，记下活动总数；再打开活动列表，看 `total`。**两个数必须相等。** 不相等就是权限漏洞，和[业务规则](/project/rules)第六节里说的“前端权限控制只是体验优化”是同一类问题 —— 只不过这里是数据泄露，比按钮多一点更严重。

**审核员账号也要测对称的一面**：审核员看到的活动总数应该大于等于任意组织者看到的总数，且等于全部活动数。
:::

::: details 百分比显示成了 0.7% 而不是 73%
**现象**：名额使用率显示 0.7%，实际应该是 73%。

**原因**：后端返回的 `quotaUsageRate` 是 `0.73` 这样的小数（比例），前端格式化时没有乘 100，直接接了个百分号。

**怎么处理**：格式化的逻辑统一放进 `formatPercent`，比例进、百分比字符串出：

```js
export function formatPercent(value, digits = 1) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '—'
  return `${(Number(value) * 100).toFixed(digits)}%`
}
```

**这里最需要在接口文档里写清楚的是“`quotaUsageRate` 是 0 到 1 的小数，不是 0 到 100 的数值”。** 光看字段名叫 `Rate` 其实不够 —— 有的后端用 `73` 表示 73%。**约定要写到“小数还是整数”这个程度**，两边才不会理解偏差。如果项目组已经约定用整数，那就约定成整数，但一定要写下来。
:::

::: details 骨架屏一直在转，数字永远出不来
**现象**：看板打开后一直显示骨架，等很久也没有数字，控制台也没有明显的报错。

**原因**：三个可能。

1. 某个请求 `pending` 不返回，`allSettled` 会一直等 —— 因为要等所有 promise 都结算。这时应该给请求配 `timeout`（在 `api/request.js` 的 axios 实例上设）。
2. 处理结果时 `task.key` 和实际赋值的字段名对不上，比如 `tasks` 里写的是 `overview`，赋值时判断的是 `overviewData` —— 两边不一致，`loading` 就置不了 `false`。
3. 出错的那一项忘了把 `loading[key]` 置 `false`，只处理了 `fulfilled` 分支。

**怎么处理**：三件事都检查一遍。

```js
// 请求层给一个超时，避免请求永远 pending
const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 10000
})
```

**用常量而不是字符串字面量做 key，能防住第二类错误**：

```js
const BLOCKS = { OVERVIEW: 'overview', RECENT: 'recent', TODOS: 'todos' }
```

**再强调一次：骨架屏一直转，比显示一条错误更糟。** 显示错误用户知道去点重试，一直转用户只会以为是自己网慢，然后一直等。
:::

## 十二、验收清单

| # | 验收项 | 怎么验证 |
| --- | --- | --- |
| 1 | 待办区块在最上方，且能点击跳转 | 点“待审核 47 条”，跳到 `/signup` 并已按待审核筛选 |
| 2 | 指标卡数字正确 | 看板活动总数等于活动列表的 `total` |
| 3 | 名额使用率显示分子分母 | “已通过 936 人次 / 名额合计 1284”和百分比同时可见 |
| 4 | 使用率算法一致 | 用 `approvedTotal / quotaTotal` 手算，和页面上的百分比一致 |
| 5 | 三个请求并行发出 | 网络面板里三个 `/dashboard/` 请求时间重叠，不是串行 |
| 6 | 单区块失败不影响其他区块 | 把 `recent-activities` 接口改错，概览和待办照常显示，只有近期活动显示失败和重试 |
| 7 | 骨架屏不跳动 | 限速成 Slow 3G，观察数字出现前后页面高度不变 |
| 8 | 待办为空时文案正确 | 造一个没有待办的数据，显示“暂时没有要处理的事情”，不是“暂无数据” |
| 9 | 组织者只看自己的数据 | 组织者账号的看板活动总数等于他活动列表的 `total` |
| 10 | 审核员看全部数据 | 审核员账号的活动总数等于全部活动数 |
| 11 | 大数有千分位 | 报名总数 1284 显示成 `1,284` |
| 12 | 空值显示为长横 | 把某个字段置空，显示 `—`，不是 `0` 也不是 `NaN` |
| 13 | 重试会清掉上一次的错误 | 点重试成功后，错误提示消失 |
| 14 | 看板不引入图表库 | `pnpm build` 后，产物里没有 ECharts 之类的图表库 chunk |

---

上一页：[场次与场地模块](/project/impl-session) · 下一页：返回 [项目总览](/project/)
