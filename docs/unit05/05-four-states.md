# 5.5 四态页面规范

## 一个具体的场景

先看一个学生写的活动列表页：

```vue
<script setup>
import { ref, onMounted } from 'vue'

const list = ref([])

onMounted(async () => {
  const res = await fetch('/api/activity/list')
  list.value = (await res.json()).list
})
</script>

<template>
  <ul>
    <li v-for="item in list" :key="item.id">{{ item.title }}</li>
  </ul>
  <p v-if="list.length === 0">暂无数据</p>
</template>
```

这个页面在“网速正常、接口正常、有数据”的情况下没问题。
但把它放到真实环境里，会出三种状况：

1. **网速慢**：打开页面，先看到“暂无数据”，一两秒后才刷出列表 ——
   用户以为真的没数据；
2. **接口报错**：页面什么都没有，只说“暂无数据”，用户不知道是网断了还是真没数据，
   也没有重试的地方；
3. **筛选后无结果**：显示“暂无数据”，用户不知道是因为筛选条件太严，
   只能自己去猜。

这三类问题都归结到一件事：**页面只处理了“有数据”一种状态。**

一个能用的数据页面必须处理四种状态，这就是**四态**。

| 状态 | 触发条件 | 用户看到什么 |
| --- | --- | --- |
| 加载中 | 请求已发出、还没回来 | 骨架屏或“加载中”提示 |
| 出错 | 请求失败 | 错误说明 + 重试按钮 |
| 空数据 | 请求成功，但没有数据 | 说明为什么空 + 下一步动作 |
| 有数据 | 请求成功，有数据 | 正常内容 |

## 原理与写法

### 顺序为什么不能颠倒

四态的判断顺序是**固定的**：

```text
1. 加载中？（loading === true）
2. 出错了？（error 有值）
3. 空数据？（list.length === 0）
4. 有数据
```

**这个顺序不能改。** 把“空数据”提到前面会发生什么？

```vue
<!-- ✗ 错：先判断空数据 -->
<template>
  <p v-if="list.length === 0">暂无数据</p>
  <div v-else-if="loading">加载中…</div>
  <div v-else-if="error">出错了</div>
  <ul v-else>...</ul>
</template>
```

**现象**：页面一打开，`list` 是空数组，`list.length === 0` 成立，
所以先显示“暂无数据”；请求回来后（假如有数据），才切到列表。
中间那一下就是**闪一下空状态**。

网速慢的时候，这个“闪一下”可能持续好几秒。用户的感受就是
“这里明明有活动，为什么先说没有”。

把顺序调回来，`loading` 先命中，加载期间只显示加载态，
**不会出现“先空后有”的闪烁。**

同理，`error` 必须在 `empty` 前面。请求失败时 `list` 也是空的，
如果先判断 `empty`，用户看到的是“暂无数据”，而真实原因是请求失败了。
**错误被伪装成了空数据，排查起来会绕很多弯。**

::: tip 一句话记住顺序
**先问“正在干什么”，再问“有没有问题”，最后才问“有没有内容”。**

- 正在干什么 → loading
- 有没有问题 → error
- 有没有内容 → empty / data

**先判断“结果”再判断“过程”，就会出现闪烁和误报。**
:::

::: details 为什么很多人会写反
因为“空数据”的判断条件（`list.length === 0`）看起来最直观，
而且它和列表渲染在同一个数据上。写完 `v-for` 之后顺手加一个
“如果没有数据就显示暂无数据”，很自然就写在了前面。

**记住一个信号**：只要页面上出现“先闪一下空状态”，
第一个要检查的就是判断顺序。
:::

### 可复用的四态结构

下面这个结构可以直接抄到任何列表页里：

```vue [src/views/ActivityListView.vue]
<script setup>
import { ref, onMounted } from 'vue'

const loading = ref(false)
const error = ref('')
const list = ref([])

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await fetch('/api/activity/list')
    if (!res.ok) throw new Error(`请求失败：${res.status}`)
    const data = await res.json()
    list.value = data.list ?? []
  } catch (e) {
    error.value = e.message || '加载失败，请稍后重试'
    list.value = []          // 出错时清空，避免显示上一次的数据造成误解
  } finally {
    loading.value = false    // 无论成功失败都要关掉 loading
  }
}

onMounted(load)
</script>

<template>
  <section class="activity-list">
    <!-- 第一态：加载中 -->
    <div v-if="loading" class="state state--loading">
      <span class="spinner"></span>
      <p>正在加载活动列表…</p>
    </div>

    <!-- 第二态：出错 -->
    <div v-else-if="error" class="state state--error">
      <p class="state__title">加载失败</p>
      <p class="state__desc">{{ error }}</p>
      <button @click="load">重新加载</button>
    </div>

    <!-- 第三态：空数据 -->
    <div v-else-if="list.length === 0" class="state state--empty">
      <p class="state__title">还没有活动</p>
      <p class="state__desc">创建一场活动，它就会出现在这里。</p>
      <RouterLink class="state__action" to="/activities/new">创建活动</RouterLink>
    </div>

    <!-- 第四态：有数据 -->
    <ul v-else class="activity-list__items">
      <li v-for="activity in list" :key="activity.id" class="activity-item">
        <h3>{{ activity.title }}</h3>
        <p>截止：{{ activity.deadline }}</p>
      </li>
    </ul>
  </section>
</template>
```

这段代码里有四个值得注意的地方。

**第一，`error` 和 `list` 在请求开始时就要重置。** 否则上一次的错误信息
或数据会残留，导致状态判断出错。

**第二，`finally` 里关 `loading`。** 如果用 `try` 里关，
请求失败时 `loading` 永远是 `true`，页面就卡在加载态了。
**这是四态里最常见的 bug。**

**第三，出错时清空 `list`。** 如果一个页面出错后又显示了旧数据，
用户会以为是新数据。清空更安全。

**第四，`<RouterLink>` 出现在空状态里，是“引导”而不是“提示”。** 见下一节。

::: warning 请求要包在 try / catch 里
上面用的是 `fetch`，它在**网络错误**和**非 2xx 状态码**下的行为不同：

- 断网、域名解析失败 → `fetch` 抛出异常，被 `catch` 捕获；
- 服务器返回 404、500 → `fetch` **不抛异常**，要通过 `res.ok` 自己判断。

所以 `if (!res.ok) throw new Error(...)` 这一句不能省。
用 axios 时不需要，因为 axios 默认会把非 2xx 当成错误抛出来。
详见[单元 10 的请求层封装](/unit10/04-request-layer)。
:::

### 空状态要给出下一步动作

“暂无数据”四个字是最没用的空状态。用户看到之后不知道：

- 是我操作错了，还是系统就没有数据？
- 我该做什么才能让它有数据？
- 是不是我筛选条件太严了？

好的空状态包含三部分：**说明情况、解释原因、给出动作。**

```vue
<template>
  <div class="state state--empty">
    <p class="state__title">没有符合条件的活动</p>
    <p class="state__desc">
      当前筛选条件是“报名中”，且关键词为“歌手”。
      可以试试放宽条件。
    </p>
    <button @click="resetFilter">清除筛选条件</button>
  </div>
</template>
```

**注意**：不同的“空”要对应不同的引导。

| 空的原因 | 说明怎么写 | 动作是什么 |
| --- | --- | --- |
| 系统里确实一条都没有 | 还没有活动 | 创建活动（跳转到新建页） |
| 筛选后没有结果 | 没有符合条件的活动，并复述当前条件 | 清除筛选条件 |
| 搜索无结果 | 没有找到包含“xxx”的活动 | 清空关键词 |
| 没有权限看到数据 | 你没有查看该活动的权限 | 联系组织者 / 返回列表 |
| 分页越界（删到最后一页空了） | 当前页没有数据 | 回到上一页 |

::: tip 一个好用的检查方法
把空状态截图发给一个不了解这个页面的同学，问他：“**现在你打算做什么？**”

如果他答不上来，说明空状态缺少引导。**“暂无数据”就属于答不上来的那类。**
:::

### 错误态要给重试入口

错误态的底线是**让用户有办法继续**。用户能做的通常有三种：

1. **重试** —— 网络抖动导致的失败，重试一次就好了；
2. **返回上一页** —— 如果是权限问题或页面不存在，重试没用；
3. **联系管理员** —— 前面两种都没用时的兜底。

```vue
<template>
  <div class="state state--error">
    <p class="state__title">活动列表加载失败</p>
    <p class="state__desc">{{ error }}</p>
    <div class="state__actions">
      <button @click="load">重试</button>
      <button @click="goBack">返回</button>
    </div>
  </div>
</template>
```

错误信息要**对用户有意义**。下面这两种写法差别很大：

```js
// ✗ 没用的错误信息
error.value = 'Error: Network Error'

// ✓ 有用的
error.value = '网络连接失败，请检查网络后重试'
```

**技术细节写进控制台，用户看的话要写人能看懂的。** 具体怎么分层处理错误，
在[单元 10](/unit10/05-error-handling) 展开。

::: details 三类错误可以给不同的动作
| 错误类型 | 判断依据 | 建议动作 |
| --- | --- | --- |
| 网络错误 | 请求没到达服务器 | 重试 |
| 401 未登录 | 状态码 401 | 跳登录页 |
| 403 无权限 | 状态码 403 | 返回列表，不提供重试 |
| 404 不存在 | 状态码 404 | 返回列表 |
| 500 服务端错误 | 状态码 5xx | 重试，并提示“如持续失败请联系管理员” |

**关键点**：401 / 403 / 404 这类错误，重试按钮是**误导** —— 重试一百次结果一样。
这时候要给“返回”而不是“重试”。
:::

### 加载态的两个细节

**细节一：骨架屏比转圈更好。**

转圈只告诉用户“在等”，骨架屏还能告诉用户“等来的是什么形状”。
对于列表页，骨架屏可以用固定几行灰色占位：

```vue
<template>
  <ul v-if="loading" class="skeleton">
    <li v-for="n in 5" :key="n" class="skeleton__row">
      <span class="skeleton__block"></span>
    </li>
  </ul>
</template>
```

**细节二：区分“首次加载”和“刷新”。**

带筛选条件的列表页，切换筛选时如果整页变成骨架屏，界面会“跳”一下。
更好的做法是：**首次加载显示骨架屏；之后切换条件时保留列表，
在列表上方加一条细的加载提示。**

```js
const loading = ref(false)
const isFirstLoad = ref(true)

async function load() {
  loading.value = true
  try {
    // ...
  } finally {
    loading.value = false
    isFirstLoad.value = false
  }
}
```

```vue
<template>
  <!-- 首次加载：整页骨架屏 -->
  <SkeletonList v-if="isFirstLoad && loading" />

  <template v-else>
    <!-- 非首次加载：顶部一条细提示 -->
    <div v-if="loading" class="refresh-tip">刷新中…</div>
    <!-- 后面还是四态的判断 -->
  </template>
</template>
```

**这一条属于“体验优化”，初学阶段做到“不闪、不卡”就够了。**
先把四态写对，再考虑这类细节。

## 完整示例：校园活动列表页

把上面的东西合起来，做一个完整的列表页。

```vue [src/views/ActivityListView.vue]
<script setup>
import { ref, computed, onMounted } from 'vue'

const loading = ref(false)
const error = ref('')
const activities = ref([])
const keyword = ref('')

async function loadActivities() {
  loading.value = true
  error.value = ''

  try {
    const res = await fetch('/api/activity/list')
    if (!res.ok) throw new Error(`服务返回 ${res.status}`)
    const data = await res.json()
    activities.value = data.list ?? []
  } catch (e) {
    error.value = e.message === 'Failed to fetch'
      ? '网络连接失败，请检查网络后重试'
      : '加载失败，请稍后重试'
    activities.value = []
  } finally {
    loading.value = false
  }
}

// 筛选结果：空状态要能区分“真没有”和“筛没了”
const filteredList = computed(() => {
  const kw = keyword.value.trim()
  if (!kw) return activities.value
  return activities.value.filter((a) => a.title.includes(kw))
})

const isEmpty = computed(() => activities.value.length === 0)
const isFilteredEmpty = computed(() => !isEmpty.value && filteredList.value.length === 0)

function resetKeyword() {
  keyword.value = ''
}

onMounted(loadActivities)
</script>

<template>
  <section class="activity-page">
    <header class="activity-page__header">
      <h1>活动列表</h1>
      <input v-model="keyword" placeholder="搜索活动标题" />
    </header>

    <!-- 1. 加载中 -->
    <div v-if="loading" class="state state--loading">
      <span class="spinner"></span>
      <p>正在加载活动列表…</p>
    </div>

    <!-- 2. 出错 -->
    <div v-else-if="error" class="state state--error">
      <p class="state__title">活动列表加载失败</p>
      <p class="state__desc">{{ error }}</p>
      <div class="state__actions">
        <button @click="loadActivities">重试</button>
        <RouterLink to="/">返回首页</RouterLink>
      </div>
    </div>

    <!-- 3a. 空数据：系统里确实没有 -->
    <div v-else-if="isEmpty" class="state state--empty">
      <p class="state__title">还没有活动</p>
      <p class="state__desc">创建一场活动之后，它会出现在这里。</p>
      <RouterLink class="state__action" to="/activities/new">创建活动</RouterLink>
    </div>

    <!-- 3b. 空数据：筛选之后没有 -->
    <div v-else-if="isFilteredEmpty" class="state state--empty">
      <p class="state__title">没有符合条件的活动</p>
      <p class="state__desc">当前关键词是“{{ keyword }}”，试试换个词。</p>
      <button @click="resetKeyword">清空关键词</button>
    </div>

    <!-- 4. 有数据 -->
    <ul v-else class="activity-list">
      <li v-for="activity in filteredList" :key="activity.id" class="activity-item">
        <h3 class="activity-item__title">{{ activity.title }}</h3>
        <p class="activity-item__meta">
          报名截止：{{ activity.deadline }} · 名额 {{ activity.capacity }}
        </p>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.state {
  padding: 48px 16px;
  text-align: center;
  color: #6b7280;
}

.state__title {
  font-size: 16px;
  color: #111827;
}

.state--error .state__title {
  color: #b91c1c;
}

.state__actions {
  display: flex;
  gap: 12px;
  justify-content: center;
}
</style>
```

这份实现里有几个**有意为之**的设计：

- **`isEmpty` 和 `isFilteredEmpty` 是两个计算属性**，因为这个页面的“空”
  有两种含义，引导动作完全不同；
- **`error` 里存的是给用户看的文字**，不是原始的 `Error` 对象；
- **加载态和错误态里没有 `v-for`**，只有 `v-else` 那支才有 ——
  这正是四态互斥的含义。

::: tip 这段结构可以复用到任何列表页
把 `activities` 换成 `signups`、`sessions`、`auditRecords`，
四态的外壳完全不用改。

**建议把它记成一个模板**，以后写新的数据页面直接套。
课程后面的[单元 11 列表页标准做法](/unit11/04-list-page)会把它进一步规范化。
:::

## 小结

- 数据页面必须处理四种状态：加载中、出错、空数据、有数据。
- 判断顺序固定：**loading → error → empty → data**；写反会出现“闪一下空状态”或“把错误伪装成空”。
- 请求要包 `try / catch / finally`，`loading` 在 `finally` 里关；
  出错时清空列表，避免显示旧数据。
- `fetch` 不会因为 404 / 500 抛异常，要自己判断 `res.ok`。
- 空状态要给引导：说明情况、解释原因、给出动作；不同的“空”对应不同引导。
- 错误态要给重试入口，但 401 / 403 / 404 这类错误应该给“返回”而不是“重试”。
- 加载态：首次加载用骨架屏，之后切换条件时保留列表加一条刷新提示。

## 常见坑

::: details 坑 1：`loading` 只写在成功分支里
```js
// ✗ 错：请求失败时 loading 永远是 true
async function load() {
  loading.value = true
  const res = await fetch('/api/list')
  list.value = (await res.json()).list
  loading.value = false
}
```

**现象**：接口一报错，页面永远停在“加载中”。

**原因**：`fetch` 抛异常之后，后面的 `loading.value = false` 不会执行。

**怎么处理**：放在 `finally` 里。**这是四态实现里最高频的 bug，
写完一定要故意把接口改错一次，看会不会卡住。**
:::

::: details 坑 2：用 `v-show` 写四态
```vue
<!-- ✗ 条件会重复且互相矛盾 -->
<div v-show="loading">加载中…</div>
<div v-show="!loading && error">出错</div>
<div v-show="!loading && !error && list.length === 0">空</div>
<ul v-show="!loading && !error && list.length > 0">...</ul>
```

**现象**：能跑，但加一种状态就要改每一行，而且很容易漏条件导致两个状态同时显示。

**原因**：`v-show` 之间没有“互斥”关系，每个元素各自判断。

**怎么处理**：用 `v-if` / `v-else-if` / `v-else`，天然互斥。
:::

::: details 坑 3：只在“筛选后为空”时显示空状态，忘了区分
```vue
<!-- ✗ 用户看到“还没有活动”，以为是系统没有数据 -->
<div v-if="filteredList.length === 0">
  <p>还没有活动</p>
  <RouterLink to="/activities/new">创建活动</RouterLink>
</div>
```

**现象**：用户明明有 30 场活动，只是搜“歌手”没搜到，
页面却引导他去“创建活动”。点进去之后会很困惑。

**原因**：没有区分“数据源为空”和“筛选结果为空”。

**怎么处理**：两个 `computed` 分开判断，引导动作也不同。
**这个坑的通用形式是：一个界面状态可能由多种原因造成，要分开表达。**
:::

::: details 坑 4：错误信息直接把 `Error` 对象渲染出来
```vue
<!-- ✗ 用户看不懂 -->
<p>{{ error }}</p>   <!-- 渲染出 "TypeError: Cannot read properties of undefined" -->
```

**现象**：页面上出现技术术语，用户无法理解，也无法据此做任何事。

**原因**：直接把异常信息展示给用户。

**怎么处理**：在 `catch` 里转换成用户能懂的话，
原始错误用 `console.error` 输出到控制台供开发排查。

**判断标准：用户看完这句话，知道下一步做什么吗？** 不知道，就重写。
:::

## 课后练习

::: details 练习 1：找出这段代码的四个问题
```vue
<script setup>
import { ref, onMounted } from 'vue'
const list = ref([])
const loading = ref(true)

onMounted(async () => {
  const res = await fetch('/api/activity/signups')
  list.value = (await res.json()).list
  loading.value = false
})
</script>

<template>
  <p v-if="list.length === 0">暂无数据</p>
  <div v-else-if="loading">加载中…</div>
  <ul v-else>
    <li v-for="item in list">{{ item.name }}</li>
  </ul>
</template>
```

**参考思路**：四个问题是 ——

1. 判断顺序错了，`list.length === 0` 排在 `loading` 前面，会闪空状态；
2. 没有错误态，请求失败时页面停在加载中或显示空；
3. 没有 `try / catch / finally`，失败时 `loading` 不会关；
4. `v-for` 没有 `key`。

**如果只找出两个，说明还需要再读一遍这一节。**
:::

::: details 练习 2：给一个页面补齐四态
选一个你之前写过的数据页面（或者用[单元 4 的名片页](/unit04/practice)里的列表），
给它补齐四态：

1. 写清楚每种状态的触发条件；
2. 空状态区分“系统没数据”和“筛选后没数据”；
3. 错误态给两个动作：重试、返回；
4. 加载态用骨架屏。

**验收标准**：把网络改成“慢速 3G”，刷新页面，**不能出现闪一下空状态**；
把接口地址故意改错一次，**不能让页面卡在加载中**。

**这两个动作是四态是否写对的最低标准。**
:::

::: details 练习 3：设计三种空状态
假设你在做一个“报名审核”页面，会出现下面三种空：

1. 这个活动还没有人报名；
2. 筛选“待审核”之后没有记录；
3. 你负责的活动还没有任何报名。

为每种空写一段文案（说明 + 原因 + 动作），然后拿给同学看，
问他们“看完之后知道该做什么吗”。

**参考思路**：第 1 种的引导可能是“去活动详情页分享报名入口”，
第 2 种是“切换到全部”，第 3 种是“去创建活动”。

**重点在于：三种空的动作都不一样。** 如果你的三条文案动作相同，
说明还没有真的区分它们。
:::

---

上一节：[5.4 列表渲染与键值](/unit05/04-list) ·
下一节：[案例 01 · 增删改查清单](/unit05/06-case-crud)
