# 案例 04 · 从接口获取数据

这是本单元的课堂演练案例，难度**进阶档**。做完它，你会有一个能直接拿去用的"列表页取数据"模板。

## 准备一个能用的接口

没有后端也能做。起一个本地 mock 服务，返回活动列表数据。

```bash [安装并启动 mock 服务]
# 在项目根目录
pnpm add -D vite-plugin-mock
```

在 `vite.config.js` 里加上插件配置，然后新建 mock 文件：

```js [mock/activity.js]
// 造 37 条活动数据，方便测试分页与"加载更多"
const activities = Array.from({ length: 37 }, (_, i) => ({
  id: i + 1,
  title: `校园活动 ${i + 1}`,
  type: i % 3 === 0 ? '文艺' : i % 3 === 1 ? '体育' : '学术',
  status: ['draft', 'signing', 'closed', 'ended'][i % 4],
  quota: 50 + i * 10,
  signupCount: i * 3,
  createdAt: `2026-09-${String((i % 28) + 1).padStart(2, '0')}`
}))

export default [
  {
    url: '/api/activity/list',
    method: 'get',
    response: ({ query }) => {
      const page = Number(query.page) || 1
      const pageSize = Number(query.pageSize) || 10
      const status = query.status || ''
      const keyword = query.keyword || ''

      let filtered = activities
      if (status) {
        filtered = filtered.filter((a) => a.status === status)
      }
      if (keyword) {
        filtered = filtered.filter((a) => a.title.includes(keyword))
      }

      const start = (page - 1) * pageSize
      return {
        code: 200,
        message: 'success',
        data: {
          list: filtered.slice(start, start + pageSize),
          total: filtered.length
        }
      }
    }
  }
]
```

::: tip 为什么 mock 也要返回 `{ code, message, data }`
因为真实后端就是按这个结构返回的。
**mock 的目的是让前端代码"不用改一行就能接后端"**，
如果 mock 返回的结构跟真实接口不一样，切换时又要改一遍代码，mock 就白做了。

如果你要验证错误处理，可以给 mock 加一个特殊参数让它返回失败：
```js
if (query.fail === '1') {
  return { code: 5000, message: '服务器开小差了', data: null }
}
```
:::

## 第一步：把请求封装成组合式函数

与其在每个页面里重复写"加载态、错误、请求、取消"，
不如像 [单元 8 的组合式函数](/unit08/04-composables) 那样，抽成一个 `useRequest`。

```js [src/composables/useRequest.js]
import { ref, shallowRef } from 'vue'

/**
 * 把一次异步请求包成"状态 + 执行函数 + 取消"三件套
 * @param {Function} service 返回 Promise 的请求函数
 * @param {object} options 配置
 */
export function useRequest(service, options = {}) {
  const { manual = false, initialData = null } = options

  const data = shallowRef(initialData) // 数据可能是大数组，用 shallowRef 省性能
  const loading = ref(false)
  const error = ref('')

  // 保存当前的取消函数，供 cancel 使用
  let abort = null

  async function run(...args) {
    // 每次执行前，先取消上一次还没回来的请求
    abort?.()

    const controller = new AbortController()
    abort = () => controller.abort()

    loading.value = true
    error.value = ''
    try {
      // 把 signal 传下去，请求层透传给 axios
      const res = await service(...args, controller.signal)
      data.value = res
      return res
    } catch (e) {
      // 主动取消的不算错误
      if (controller.signal.aborted) return
      error.value = e.message || '请求失败'
      throw e
    } finally {
      if (!controller.signal.aborted) {
        loading.value = false
      }
    }
  }

  function cancel() {
    abort?.()
  }

  // 不要求手动触发时，立刻执行一次
  if (!manual) {
    run()
  }

  return { data, loading, error, run, cancel }
}
```

接口函数要能接收 `signal` 参数：

```js [src/api/activity.js]
import request from './request'

export function getActivityListApi(params, signal) {
  return request.get('/activity/list', { params, signal })
}
```

::: warning `shallowRef` 而不是 `ref`
`ref` 会深度遍历对象做响应式代理，一个 37 条的数组还好，
但真实项目里列表可能有几千条，深度代理会明显拖慢速度。
**列表数据用 `shallowRef`**，替换整个数组时才触发更新 —— 这正是我们需要的。
:::

## 第二步：四态模板

任何"从接口取数据"的页面，都必须处理四种状态：
**加载中、出错、空数据、有数据**。这就是[单元 5 的四态规范](/unit05/05-four-states)。

```vue [views/ActivityListView.vue]
<script setup>
import { computed } from 'vue'
import { getActivityListApi } from '@/api/activity'
import { useRequest } from '@/composables/useRequest'

const { data, loading, error, run } = useRequest(
  (signal) => getActivityListApi({ page: 1, pageSize: 10 }, signal)
)

// ✓ 派生值用 computed
const list = computed(() => data.value?.list ?? [])
const isEmpty = computed(() => !loading.value && !error.value && list.value.length === 0)
</script>

<template>
  <div class="activity-list">
    <!-- ① 加载中 -->
    <div v-if="loading" class="state state--loading">正在加载活动…</div>

    <!-- ② 出错：给出重试入口 -->
    <div v-else-if="error" class="state state--error">
      <p>{{ error }}</p>
      <button @click="run()">重新加载</button>
    </div>

    <!-- ③ 空数据 -->
    <div v-else-if="isEmpty" class="state state--empty">
      <p>还没有活动</p>
      <button @click="run()">刷新看看</button>
    </div>

    <!-- ④ 有数据 -->
    <ul v-else class="activity-list__items">
      <li v-for="item in list" :key="item.id">
        <h3>{{ item.title }}</h3>
        <span>{{ item.type }} · 名额 {{ item.signupCount }} / {{ item.quota }}</span>
      </li>
    </ul>
  </div>
</template>
```

::: tip 四态的判断顺序不能乱
顺序是 `loading` → `error` → `empty` → `list`。
常见的错误是把顺序写反：
- `loading` 放最后，加载时页面闪一下"没有活动"（因为 `list` 还是空的）。
- `error` 放在 `loading` 后面但 `empty` 前面……其实 `error` 必须比 `empty` 早，
  否则出错时 `list` 为空，会显示成"没有活动"，把故障说成了"确实没数据"。

**"没有数据"和"数据没取到"对用户是两件完全不同的事。**
:::

## 第三步：处理请求竞态

这是本案例最重要的部分，也是真实项目里最常见的 bug。

### 现象

用户点第一页，请求发出（假设服务器慢，要 3 秒）。
还没回来，用户手快点了第二页，第二个请求发出（1 秒就回来了）。
于是：

- 时间点 1 秒：第二页数据显示出来。
- 时间点 3 秒：第一页的数据**后到**，把页面覆盖回了第一页内容。

**用户明明点了第二页，看到的却是第一页的数据。** 这就是请求竞态
（race condition）：先发出的请求后返回，覆盖了后发出的请求的结果。

### 方案一：序号标记（"最新的才算数"）

每次请求前记一个自增序号，回来时检查自己是不是最新那个：

```js [src/composables/useRequest.js（序号方案）]
import { ref, shallowRef } from 'vue'

export function useRequest(service, options = {}) {
  const { manual = false } = options
  const data = shallowRef(null)
  const loading = ref(false)
  const error = ref('')

  let seq = 0 // 请求序号

  async function run(...args) {
    const mySeq = ++seq // ✓ 每次请求领一个号
    loading.value = true
    error.value = ''
    try {
      const res = await service(...args)
      // ✓ 回来时检查：我还是最新那个吗？不是就丢弃结果
      if (mySeq !== seq) return
      data.value = res
      return res
    } catch (e) {
      if (mySeq !== seq) return // 过期的错误也不处理
      error.value = e.message || '请求失败'
      throw e
    } finally {
      if (mySeq === seq) {
        loading.value = false
      }
    }
  }

  return { data, loading, error, run }
}
```

**优点**：简单，不需要接口函数配合，几行代码就够。
**缺点**：请求还是发出去了，只是结果被丢弃。服务器带宽和用户流量照常消耗。

### 方案二：`AbortController` 取消

下一次请求开始时，直接把上一次的请求取消掉：

```js [src/composables/useRequest.js（取消方案）]
import { ref, shallowRef } from 'vue'

export function useRequest(service, options = {}) {
  const { manual = false } = options
  const data = shallowRef(null)
  const loading = ref(false)
  const error = ref('')

  let abort = null

  async function run(...args) {
    abort?.() // ✓ 取消上一次还没回来的请求

    const controller = new AbortController()
    abort = () => controller.abort()

    loading.value = true
    error.value = ''
    try {
      const res = await service(...args, controller.signal)
      data.value = res
      return res
    } catch (e) {
      if (controller.signal.aborted) return // 取消不算错误
      error.value = e.message || '请求失败'
      throw e
    } finally {
      if (!controller.signal.aborted) {
        loading.value = false
      }
    }
  }

  return { data, loading, error, run }
}
```

对应的接口函数要把 `signal` 传给 axios：

```js [src/api/activity.js]
export function getActivityListApi(params, signal) {
  // ✓ axios 支持 signal，取消后抛出的错误 code 是 ERR_CANCELED
  return request.get('/activity/list', { params, signal })
}
```

**优点**：真正取消，省流量、省服务器资源；还能顺带支持"用户离开页面取消请求"。
**缺点**：接口函数必须把 `signal` 透传下去，多一层约定。

### 两种方案对比

| 对比项 | 序号标记 | `AbortController` |
| --- | --- | --- |
| 实现复杂度 | 低，改几行 | 中，接口函数要透传 `signal` |
| 是否真正取消请求 | 否，只是丢弃结果 | 是 |
| 省流量 | 否 | 是 |
| 依赖接口改造 | 不需要 | 需要 |
| 能否用于"离开页面取消" | 不能 | 能 |
| 判断"是不是错误" | 靠序号比对 | 靠 `signal.aborted` |

::: tip 什么时候用哪个
- **请求很轻（几十 KB）**：序号标记足够，实现简单。
- **请求很重（大列表、导出文件）**：用 `AbortController`，真的省资源。
- **页面离开要释放资源**：必须用 `AbortController`。

本案例**两种都实现一遍**，你会清楚感受到差别。
:::

::: danger 用 `AbortController` 时要记得改拦截器
请求取消后 axios 抛出的是取消错误，如果不处理，
[10.5](/unit10/05-error-handling) 里的拦截器会把它当成网络错误弹 toast。
**拦截器里加一句 `if (axios.isCancel(error)) return Promise.reject(error)`，
并且不要提示。**
:::

## 第四步：加载更多与去重

列表数据多了要分页追加。这里有两个坑：**追加时重复**、**重复点击时穿插**。

```js [src/views/ActivityListView.vue（加载更多逻辑）]
import { ref, computed } from 'vue'
import { getActivityListApi } from '@/api/activity'

const list = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 10
const loading = ref(false)

const hasMore = computed(() => list.value.length < total.value)

async function loadPage(targetPage) {
  loading.value = true
  try {
    const res = await getActivityListApi({ page: targetPage, pageSize })
    // ✓ 按 id 去重：即使后端重复返回，也不会出现两条一样的
    const existingIds = new Set(list.value.map((item) => item.id))
    const fresh = res.list.filter((item) => !existingIds.has(item.id))
    list.value = targetPage === 1 ? res.list : [...list.value, ...fresh]
    total.value = res.total
    page.value = targetPage
  } finally {
    loading.value = false
  }
}

function loadMore() {
  // ✓ 正在加载时忽略重复点击
  if (loading.value || !hasMore.value) return
  loadPage(page.value + 1)
}
```

```vue [template 部分]
<template>
  <ul>
    <li v-for="item in list" :key="item.id">{{ item.title }}</li>
  </ul>

  <p v-if="hasMore" class="load-more">
    <button :disabled="loading" @click="loadMore">
      {{ loading ? '加载中…' : '加载更多' }}
    </button>
  </p>
  <p v-else class="no-more">已经到底了</p>
</template>
```

要点：

- **去重用 `Set` 按 id**。后端分页有"翻页时数据变动导致重复"的可能，
  前端去重是最后一道防线。
- **`loading` 期间禁用按钮**，否则连点会发出好几个请求。
- **`hasMore` 由 `list.length < total` 推出**，不要用"返回条数是否等于 pageSize"判断 ——
  最后一批恰好满页时会漏掉结束条件。

::: tip 追加和替换的区别
- **切页 / 换筛选条件 → 替换**（`list.value = res.list`）。
- **加载更多 → 追加**（`list.value = [...list.value, ...res.list]`）。

追加时要注意**用新数组替换**，不要 `list.value.push(...)` 一大批，
否则响应式更新可能触发多次。
:::

## 第五步：手动刷新与自动刷新

**手动刷新**就是给用户一个按钮：

```vue
<button :disabled="loading" @click="loadPage(1)">刷新</button>
```

**自动刷新**有两种常见需求：

```js [组合式：轮询刷新]
import { onMounted, onUnmounted } from 'vue'

// 每 30 秒刷新一次（比如报名审核页想看到最新报名）
let timer = null

onMounted(() => {
  timer = setInterval(() => {
    // ✓ 只在没有正在进行的请求时才刷新，避免请求堆积
    if (!loading.value) loadPage(1)
  }, 30000)
})

onUnmounted(() => {
  // ✓ 组件卸载必须清掉定时器，否则内存泄漏
  clearInterval(timer)
})
```

**回到页面时刷新**（用户切到别的标签页再切回来）：

```js
import { useDocumentVisibility } from '@vueuse/core'

const visibility = useDocumentVisibility()

watch(visibility, (state) => {
  // 从后台切回前台时刷新一次
  if (state === 'visible') loadPage(1)
})
```

::: warning 自动刷新要克制
轮询太频繁会白白消耗服务器资源。三条经验：
1. **间隔不短于 30 秒**，绝大多数列表页不需要更频繁。
2. **页面不可见时停止轮询**（`document.visibilityState`）。
3. **有正在进行的请求时跳过这次轮询**，避免请求堆积。

更好的做法是"提交后刷新"或"离开页面前刷新"，
而不是无脑轮询 —— **先想清楚为什么需要自动刷新**。
:::

## 第六步：失败后的重试入口

错误态必须给用户一个动作，不能只显示一句话。

```vue [错误态]
<div v-else-if="error" class="state state--error">
  <p>{{ error }}</p>
  <!-- ✓ 重试入口：重新执行同一次请求 -->
  <button @click="retry">重新加载</button>
</div>
```

```js
// 记住最后一次的参数，重试时原样再发一遍
const lastParams = ref({ page: 1, pageSize: 10 })

function retry() {
  loadPage(lastParams.value.page)
}
```

如果错误是"可重试"的（网络超时、`5xx`），也可以自动重试一次再交给用户：

```js
import { withRetry } from '@/api/retry'

const res = await withRetry(() => getActivityListApi(params))
```

**不可重试的错误（`403`、`404`）不要给重试按钮**，点了也没用，只会让用户困惑。

## 完整代码

把上面几步合起来，得到一个可以复用的列表页模板。

```vue [views/ActivityListView.vue]
<script setup>
import { ref, computed } from 'vue'
import { getActivityListApi } from '@/api/activity'

// ---- 状态 ----
const list = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 10
const loading = ref(false)
const error = ref('')

// 当前在跑的请求的取消函数
let abort = null

// ---- 派生 ----
const isEmpty = computed(() => !loading.value && !error.value && list.value.length === 0)
const hasMore = computed(() => list.value.length < total.value)

// ---- 请求 ----
async function loadPage(targetPage = 1, { append = false } = {}) {
  // 取消上一次未完成的请求，避免竞态
  abort?.()
  const controller = new AbortController()
  abort = () => controller.abort()

  loading.value = true
  error.value = ''
  try {
    const res = await getActivityListApi(
      { page: targetPage, pageSize },
      controller.signal
    )

    if (append) {
      // 追加时按 id 去重
      const ids = new Set(list.value.map((i) => i.id))
      const fresh = res.list.filter((i) => !ids.has(i.id))
      list.value = [...list.value, ...fresh]
    } else {
      list.value = res.list
    }
    total.value = res.total
    page.value = targetPage
  } catch (e) {
    // 主动取消不算错误
    if (controller.signal.aborted) return
    error.value = e.message || '活动列表加载失败'
  } finally {
    if (!controller.signal.aborted) {
      loading.value = false
    }
  }
}

function loadMore() {
  if (loading.value || !hasMore.value) return
  loadPage(page.value + 1, { append: true })
}

function refresh() {
  loadPage(1)
}

// 首次进入加载
loadPage(1)
</script>

<template>
  <div class="activity-list">
    <header class="activity-list__bar">
      <h2>活动列表</h2>
      <button :disabled="loading" @click="refresh">刷新</button>
    </header>

    <!-- 出错 -->
    <div v-if="error" class="state state--error">
      <p>{{ error }}</p>
      <button @click="refresh">重新加载</button>
    </div>

    <!-- 加载中（首次加载，还没有数据） -->
    <div v-else-if="loading && list.length === 0" class="state state--loading">
      正在加载活动…
    </div>

    <!-- 空数据 -->
    <div v-else-if="isEmpty" class="state state--empty">
      <p>还没有活动</p>
      <button @click="refresh">刷新看看</button>
    </div>

    <!-- 有数据 -->
    <template v-else>
      <ul class="activity-list__items">
        <li v-for="item in list" :key="item.id">
          <h3>{{ item.title }}</h3>
          <span>{{ item.type }} · 名额 {{ item.signupCount }} / {{ item.quota }}</span>
        </li>
      </ul>

      <p v-if="hasMore" class="load-more">
        <button :disabled="loading" @click="loadMore">
          {{ loading ? '加载中…' : '加载更多' }}
        </button>
      </p>
      <p v-else class="no-more">已经到底了</p>
    </template>
  </div>
</template>
```

::: tip 验证竞态防护是否生效
mock 服务里给接口加一个"延迟"参数：

```js
const delay = Number(query.delay) || 0
await new Promise((r) => setTimeout(r, delay))
```

然后手动测试：第一次请求带 `delay=3000`，紧接着第二次带 `delay=300`。
**如果第二次的数据能正常显示、不会被第一次覆盖，竞态防护就生效了。**
把这个操作过程录下来，作为练习的验证证据。
:::

## 小结

- 没有后端就用 mock 服务，**mock 的返回结构必须与真实接口一致**。
- 列表数据用 `shallowRef`，避免大数组被深度代理。
- 四态顺序：加载中 → 出错 → 空数据 → 有数据，顺序错了会误报"没有数据"。
- 请求竞态用序号标记或 `AbortController`；前者简单，后者能真正省资源。
- 加载更多要按 id 去重、加载期间禁用按钮；`hasMore` 由 `list.length < total` 判断。
- 自动刷新要克制，页面不可见时暂停，有请求在跑时跳过。
- 出错必须给重试入口，不可重试的错误不给按钮。

## 常见坑

::: details 坑 1：切页太快显示上一页的数据
现象：快速点第 1、2、3 页，最后显示的可能是第 1 页的内容。

原因：请求竞态，先发的后到。

怎么处理：用本节两种方案之一。**验收时用带不同延迟的 mock 接口复现一次，确认修好了。**
:::

::: details 坑 2：`loading` 卡在 `true`
现象：请求取消后，加载态没复位，按钮一直禁用。

原因：`finally` 里没判断 `signal.aborted`，取消时 `loading` 被设成 `false` 又被谁改回去了；
或者有两个请求同时跑，先结束的那个把 `loading` 关了，后面的结果又打开。

怎么处理：`finally` 里加 `if (!controller.signal.aborted)` 判断，
并保证同一时刻只有一个请求在跑（每次 `run` 先取消上一次）。
:::

::: details 坑 3：`v-for` 的 `key` 用了索引
现象：加载更多后，列表项内容"串位"了，或者勾选状态跑到了别的项上。

原因：`key` 用了 `index`，追加数据后同一位置的元素换成了别的数据。

怎么处理：**用业务 id 作 `key`**：`:key="item.id"`。这在[单元 5 的列表渲染](/unit05/04-list)
讲过，列表追加场景下尤其重要。
:::

::: details 坑 4：去重时用 `title` 而不是 `id`
现象：两个活动标题一样（比如都是"新生篮球赛"），其中一个被去重掉了。

原因：用非唯一字段判断重复。

怎么处理：用 **id** 这类唯一标识。如果后端不保证 id 唯一，那是后端的问题，要在接口约定里写清楚。
:::

::: details 坑 5：轮询定时器没清理
现象：切走页面后控制台还在报请求错误，或者内存占用越来越高。

原因：`onUnmounted` 里忘了 `clearInterval`。

怎么处理：定时器、事件监听器、`AbortController` 都要在卸载时清理，
这是[单元 6 生命周期](/unit06/05-lifecycle)的固定套路。
:::

::: details 坑 6：mock 服务在生产构建里也被打进去了
现象：打包产物里包含了 mock 数据。

原因：mock 插件没限制环境。**mock 只应该在开发环境启用。**

怎么处理：在 `vite.config.js` 里根据 `mode` 判断，只在 `serve` 时加 mock 插件。
:::

## 课后练习

::: details 练习 1：把两种竞态方案都实现一遍
用带延迟的 mock 接口，分别用序号标记与 `AbortController` 实现竞态防护，
记录两种方案在"快速切页"时的表现差异。

**参考思路**：重点观察网络面板 —— 序列号方案里旧请求仍然完整走完，
只是结果被丢弃；取消方案里旧请求会显示为 `canceled`。
**把这个差异写进你的实验记录。**
:::

::: details 练习 2：给列表加上筛选与分页
在活动列表页加上"按状态筛选"和"按关键词搜索"，要求：
筛选条件变化时回到第一页、重新请求、清空之前加载更多的数据。

**参考思路**：筛选条件变化时调用 `loadPage(1)`（替换而不是追加），
并且**先取消正在进行的请求**。想一想：如果不取消，会出什么问题？
:::

::: details 练习 3：把 `useRequest` 用到另一个页面上
把报名审核列表页也改成用 `useRequest` + 四态模板。

**参考思路**：真正的验收标准是**页面组件里没有出现 `axios`、没有手写 `loading/error` 的 try/catch**。
如果重复代码还很多，想想 `useRequest` 还能抽走哪些东西。
:::

---

上一节：[10.5 错误分层处理](/unit10/05-error-handling) ·
下一节：[单元 10 课后练习](/unit10/practice)
