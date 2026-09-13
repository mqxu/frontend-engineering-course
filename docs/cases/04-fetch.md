# 案例 04 · 从接口获取数据

## 案例要做什么

审核员的报名记录页面要接真实接口了。看起来只是把本地数组换成一次请求，但真正写起来会遇到一串问题：

- 请求发出去了还没回来，页面显示什么？
- 请求失败了，用户怎么知道、怎么重试？
- 请求成功但一条数据都没有，和“加载中”长得一样吗？
- 用户在搜索框里快速输字，每输一个字都发一次请求吗？
- 快速点页码，第 2 页的请求比第 3 页慢，回来之后把第 3 页的数据覆盖了怎么办？

前三个问题对应**四态页面**，后两个分别对应**防抖**和**竞态**。这些不是“高级技巧”，
是任何一个接接口的页面都必须处理的事 —— 漏掉哪一个，用户都会遇到。

| 知识点 | 用在哪里 | 对应章节 |
| --- | --- | --- |
| 生命周期与副作用清理 | 组件挂载时请求、卸载时取消 | [生命周期与副作用清理](/unit06/05-lifecycle) |
| 四态页面规范 | 加载中 / 成功 / 失败 / 空数据 | [四态页面规范](/unit05/05-four-states) |
| `watch` 触发请求 | 关键字、页码变化时重新取数 | [侦听器](/unit05/02-watch) |
| 组合式函数 | 把取数逻辑抽成可复用的函数 | [组合式函数](/unit08/04-composables) |
| 请求层封装 | axios 实例、拦截器、重试 | [请求层封装](/unit10/04-request-layer) |
| 错误分层处理 | 哪类错误给用户看、哪类只记日志 | [错误分层处理](/unit10/05-error-handling) |

::: warning 本案例的重点不是 axios
`axios.get()` 这一行谁都会写。**本案例 80 分的内容在“怎么处理还没回来、回来失败、回来是空”这三种情况。**
如果你只记住了一行请求代码，这个案例就等于没做。
:::

## 数据结构与接口设计

### 先把接口约定写下来

接口是前后端的合同。合同没写清就开始写代码，返工是必然的。

```text [GET /api/signups 的请求与响应]
请求参数：
  keyword   string  可选，按姓名或学号模糊匹配
  page      number  从 1 开始，默认 1
  pageSize  number  每页条数，默认 8

响应体：
{
  "code": 0,
  "message": "ok",
  "data": {
    "list": [
      {
        "id": "r-01",
        "studentName": "林小满",
        "studentNo": "2023010112",
        "activityTitle": "校园歌手大赛",
        "status": "approved",
        "submittedAt": "2026-09-02 10:12"
      }
    ],
    "total": 128
  }
}
```

三个约定要提前定死，否则后面每个页面都要各写一套：

| 约定 | 取值 | 为什么重要 |
| --- | --- | --- |
| 业务状态码 | `code` 为 `0` 表示成功 | 让拦截器能统一判断成败，业务代码不用每次都写 `if (res.code === 0)` |
| 列表结构 | 永远 `{ list, total }` | 分页组件只认这两个字段，换接口不用改组件 |
| 时间格式 | `YYYY-MM-DD HH:mm` | 前端直接显示；要计算时间差时再转 `Date` |

### 四态，不是三态

很多人写“三态”：加载中、成功、失败。实际还要补一个：

| 状态 | 界面表现 | 漏掉的后果 |
| --- | --- | --- |
| 加载中 `loading` | 转圈或骨架屏 | 用户以为卡住了，反复点按钮 |
| 成功 `success` | 数据列表 | —— |
| 失败 `error` | 错误说明 + 重试按钮 | 用户不知道发生了什么，只能刷新整页 |
| 空数据 `empty` | “没有符合条件的记录” | 表格一片空白，用户以为页面坏了、或者以为自己搜错了 |

还要注意一个更细的点：**首次进入页面时，状态不应该直接是 `success`**。
否则请求还没发出，页面会先闪一下“暂无数据”。所以加一个初始状态 `idle`：

```js [状态定义]
const status = ref('idle')   // idle | loading | success | error
```

渲染时 `idle` 和 `loading` 一起处理，都不显示列表。

## 实现步骤

### 步骤 1 · 封装 axios 实例与拦截器

不要在组件里直接调 `axios.get('http://…')`。原因在[单元 10](/unit10/04-request-layer)里讲过，
这里给出完整写法：

```js [src/api/http.js]
import axios from 'axios'

const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE ?? '/api',
  timeout: 10000
})

// 请求拦截器：统一带上登录凭证
http.interceptors.request.use((config) => {
  const token = localStorage.getItem('campus_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

const RETRY_LIMIT = 2

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

// 哪些错误值得重试：网络不通、超时、服务端 5xx
function shouldRetry(error) {
  if (axios.isCancel(error)) return false // 主动取消的不重试
  if (!error.response) return true
  return error.response.status >= 500
}

http.interceptors.response.use(
  (response) => {
    // 约定：后端统一返回 { code, message, data }
    const body = response.data
    if (body && typeof body.code === 'number' && body.code !== 0) {
      const error = new Error(body.message || '接口返回失败')
      error.code = body.code
      return Promise.reject(error)
    }
    // 解一层壳，业务代码直接拿到 data
    return body?.data ?? body
  },
  async (error) => {
    const config = error.config
    const retried = config?.__retryCount ?? 0

    if (config && shouldRetry(error) && retried < RETRY_LIMIT) {
      config.__retryCount = retried + 1
      // 指数退避：第一次等 300 毫秒，第二次等 600 毫秒
      await delay(300 * 2 ** (retried))
      return http(config)
    }
    return Promise.reject(error)
  }
)

export default http
```

三个设计点说明：

| 设计 | 作用 |
| --- | --- |
| 响应拦截器里 `return body.data` | 业务代码写 `const data = await http.get(...)`，不用每次剥两层壳 |
| 业务码不为 0 时 `reject` | 让“业务失败”和“网络失败”走同一个 `catch` 分支 |
| `shouldRetry` 排除取消和 4xx | 重试 404 或参数错误毫无意义，只会把错误放大成请求风暴 |

### 步骤 2 · 接口函数单独放一层

```js [src/api/signup.js]
import http from './http'
import { mockFetchSignups } from './mock'

// 本地还没有后端时打开 mock；联调时改成 false，组件一行都不用动
const USE_MOCK = true

export function fetchSignups({ keyword = '', page = 1, pageSize = 8, signal } = {}) {
  if (USE_MOCK) {
    return mockFetchSignups({ keyword, page, pageSize, signal })
  }
  return http.get('/signups', { params: { keyword, page, pageSize }, signal })
}
```

**`signal` 一定要往下透传。** 这是本案例后面取消请求的前提 —— 忘了传，`abort()` 就是个空动作。

没有后端时，用本地数据假装一个接口。关键是**接口形状要和服务端一模一样**：

```js [src/api/mock.js]
import { CanceledError } from 'axios'

const ALL = [
  { id: 'r-01', studentName: '林小满', studentNo: '2023010112', activityTitle: '校园歌手大赛', status: 'approved', submittedAt: '2026-09-02 10:12' },
  { id: 'r-02', studentName: '陈亦航', studentNo: '2023010233', activityTitle: '校园歌手大赛', status: 'pending', submittedAt: '2026-09-03 09:40' },
  { id: 'r-03', studentName: '周敏', studentNo: '2022020118', activityTitle: '程序设计竞赛', status: 'approved', submittedAt: '2026-09-03 11:05' },
  { id: 'r-04', studentName: '赵一鸣', studentNo: '2023030145', activityTitle: '志愿服务周', status: 'rejected', submittedAt: '2026-09-04 08:20' },
  { id: 'r-05', studentName: '孙静', studentNo: '2023010176', activityTitle: '程序设计竞赛', status: 'pending', submittedAt: '2026-09-04 15:55' },
  { id: 'r-06', studentName: '吴忧', studentNo: '2024040102', activityTitle: '志愿服务周', status: 'approved', submittedAt: '2026-09-05 10:30' },
  { id: 'r-07', studentName: '郑可', studentNo: '2022020301', activityTitle: '校园歌手大赛', status: 'pending', submittedAt: '2026-09-05 13:47' },
  { id: 'r-08', studentName: '冯子涵', studentNo: '2023030233', activityTitle: '运动会方阵', status: 'approved', submittedAt: '2026-09-06 09:05' },
  { id: 'r-09', studentName: '黄诗雨', studentNo: '2024040256', activityTitle: '运动会方阵', status: 'rejected', submittedAt: '2026-09-06 16:12' },
  { id: 'r-10', studentName: '徐嘉禾', studentNo: '2023010409', activityTitle: '程序设计竞赛', status: 'approved', submittedAt: '2026-09-07 08:58' },
  { id: 'r-11', studentName: '何欣', studentNo: '2022020402', activityTitle: '志愿服务周', status: 'pending', submittedAt: '2026-09-07 14:33' },
  { id: 'r-12', studentName: '罗一诺', studentNo: '2024040333', activityTitle: '校园歌手大赛', status: 'approved', submittedAt: '2026-09-08 11:20' }
]

/** 模拟网络延迟；被取消时抛出和 axios 一致的错误 */
function delay(ms, signal) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(resolve, ms)
    signal?.addEventListener('abort', () => {
      clearTimeout(timer)
      reject(new CanceledError('请求已取消'))
    })
  })
}

export async function mockFetchSignups({ keyword = '', page = 1, pageSize = 8, signal } = {}) {
  // 耗时故意取随机值，方便观察竞态：有的请求快、有的慢
  await delay(400 + Math.round(Math.random() * 800), signal)

  const text = keyword.trim()
  const filtered = text
    ? ALL.filter((item) => item.studentName.includes(text) || item.studentNo.includes(text))
    : ALL

  const start = (page - 1) * pageSize
  return {
    list: filtered.slice(start, start + pageSize),
    total: filtered.length
  }
}
```

### 步骤 3 · 竞态：先用错误写法把它复现出来

**竞态**指的是：多个请求同时在飞，返回顺序和发出顺序不一致，导致旧数据覆盖新数据。

```js
// ✗ 没有取消，也没有序号
async function load() {
  status.value = 'loading'
  const result = await fetchSignups({ page: page.value })
  list.value = result.list
  status.value = 'success'
}
```

这段代码在快速翻页时会发生什么：

| 时刻 | 发生了什么 | 页面显示 |
| --- | --- | --- |
| T1 | 点第 2 页，请求 A 发出（恰好耗时 1100 毫秒） | 加载中 |
| T2 | 点第 3 页，请求 B 发出（恰好耗时 200 毫秒） | 加载中 |
| T3 | B 返回，列表显示第 3 页数据 | 第 3 页 ✓ |
| T4 | A 返回，列表被覆盖成第 2 页数据 | 第 2 页 ✗ |

用户看到的现象是“我点了第 3 页，页面却显示第 2 页”。**这类 bug 在本地开发很难稳定复现，
上线后一到弱网环境就频繁出现。** mock 里把耗时设成随机值，就是为了让它稳定复现。

### 步骤 4 · 用 `AbortController` 取消过期请求

正确做法是：**发新请求之前，把上一次还没完成的请求取消掉。**

```js [取消上一次请求]
let controller = null
let requestSeq = 0

async function load() {
  // 取消上一次未完成的请求
  controller?.abort()
  controller = new AbortController()
  const signal = controller.signal
  const seq = ++requestSeq

  status.value = 'loading'
  errorMessage.value = ''
  try {
    const result = await fetchSignups({
      keyword: keyword.value.trim(),
      page: page.value,
      pageSize,
      signal
    })
    if (seq !== requestSeq) return // 已经有更新的请求发出，丢弃这次结果
    list.value = result.list
    total.value = result.total
    status.value = 'success'
  } catch (error) {
    if (signal.aborted || error.code === 'ERR_CANCELED') return // 主动取消，不是错误
    if (seq !== requestSeq) return
    errorMessage.value = error.message || '加载失败'
    status.value = 'error'
  }
}
```

这里做了**两层防护**，缺一不可：

| 防护 | 解决的问题 | 什么时候失效 |
| --- | --- | --- |
| `AbortController` | 让过期请求根本不会返回结果 | 请求已经到达、只是响应慢时，取消可能来不及 |
| 请求序号 `seq` | 即使过期请求返回了，也不采纳它的结果 | 单独用也能防竞态，但白跑了一次网络请求 |

::: tip 什么时候需要第二层
`abort()` 之后，浏览器会尽量中止请求，但**如果响应已经在路上，`await` 依然可能拿到结果**。
所以真正稳妥的写法是“取消 + 序号”一起用。序号那几行成本极低，建议养成习惯。
:::

**组件卸载时还要收尾。**

组件被销毁后，请求可能还在飞。它回来时去改一个已经不存在的组件的状态，
会造成内存泄漏和无意义的报错。所以卸载时要收尾：

```js [卸载清理]
onBeforeUnmount(() => {
  clearTimeout(debounceTimer)
  controller?.abort()
})
```

### 步骤 5 · 防抖：别让用户每敲一个字就发一次请求

搜索框每输入一个字符都触发一次请求，既浪费又容易乱序。**防抖**的思路是：
输入停下来一段时间（比如 300 毫秒）之后才真正发请求。

```js [防抖搜索]
let debounceTimer = 0

watch(keyword, () => {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    page.value = 1 // 换关键字要回到第一页
    load()
  }, 300)
})
```

两个必须注意的点：

- **每次都要 `clearTimeout`**。否则前一次输入排的定时器还会执行，等于没防抖。
- **组件卸载时要清掉定时器**，不然它可能在组件销毁后触发一次请求。

工具集 `@vueuse/core` 里有现成的 `useDebounceFn`，项目里可以直接用；
但先自己写一遍，你才知道它在解决什么：

```js [用 @vueuse/core 的写法]
import { useDebounceFn } from '@vueuse/core'

const reload = useDebounceFn(() => {
  page.value = 1
  load()
}, 300)

watch(keyword, reload)
```

### 步骤 6 · 超时与重试放在拦截器里，不要散在组件里

如果把重试写在组件里，每个页面都要写一遍，而且规则会越来越不一致。
放在拦截器里，所有请求自动生效：

| 错误类型 | 处理 |
| --- | --- |
| 网络不通、超时 | 重试，最多 2 次，间隔指数增长 |
| 服务端 5xx | 重试 |
| 401 | 清除本地登录态，跳到登录页（见[案例 10](/cases/10-auth)） |
| 其他 4xx | 不重试，把 `message` 交给页面显示 |
| 用户主动取消 | 不重试，也不当成错误 |

`timeout: 10000` 表示 10 秒没响应就算失败。**超时是必须设的** ——
不设的话，一个卡住的请求会让页面永远停在“加载中”。

## 完整代码

```vue [SignupList.vue]
<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { fetchSignups } from '@/api/signup'

const STATUS_TEXT = {
  pending: '待审核',
  approved: '已通过',
  rejected: '已驳回'
}

const keyword = ref('')
const page = ref(1)
const pageSize = 8

const status = ref('idle') // idle | loading | success | error
const list = ref([])
const total = ref(0)
const errorMessage = ref('')

let controller = null
let requestSeq = 0
let debounceTimer = 0

async function load() {
  // 取消上一次未完成的请求
  controller?.abort()
  controller = new AbortController()
  const signal = controller.signal
  const seq = ++requestSeq

  status.value = 'loading'
  errorMessage.value = ''

  try {
    const result = await fetchSignups({
      keyword: keyword.value.trim(),
      page: page.value,
      pageSize,
      signal
    })
    if (seq !== requestSeq) return
    list.value = result.list
    total.value = result.total
    status.value = 'success'
  } catch (error) {
    if (signal.aborted || error.code === 'ERR_CANCELED') return
    if (seq !== requestSeq) return
    errorMessage.value = error.message || '加载失败'
    status.value = 'error'
  }
}

// 空数据是“成功但没有内容”，单独判断，避免和加载中混淆
const isEmpty = computed(() => status.value === 'success' && list.value.length === 0)
const isBusy = computed(() => status.value === 'idle' || status.value === 'loading')
const pageCount = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))

watch(keyword, () => {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    page.value = 1
    load()
  }, 300)
})

watch(page, load)

onMounted(load)

onBeforeUnmount(() => {
  clearTimeout(debounceTimer)
  controller?.abort()
})
</script>

<template>
  <section class="signup-list">
    <header class="toolbar">
      <input v-model="keyword" class="search" placeholder="搜索姓名或学号" />
      <button class="refresh" :disabled="isBusy" @click="load">刷新</button>
    </header>

    <div v-if="isBusy" class="state">正在加载……</div>

    <div v-else-if="status === 'error'" class="state state-error">
      <p>{{ errorMessage }}</p>
      <button @click="load">重试</button>
    </div>

    <p v-else-if="isEmpty" class="state">没有符合条件的报名记录。</p>

    <template v-else>
      <table class="grid">
        <thead>
          <tr>
            <th>学生</th>
            <th>学号</th>
            <th>活动</th>
            <th>状态</th>
            <th>提交时间</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in list" :key="row.id">
            <td>{{ row.studentName }}</td>
            <td>{{ row.studentNo }}</td>
            <td>{{ row.activityTitle }}</td>
            <td>{{ STATUS_TEXT[row.status] ?? row.status }}</td>
            <td>{{ row.submittedAt }}</td>
          </tr>
        </tbody>
      </table>

      <div class="pager">
        <button :disabled="page <= 1" @click="page -= 1">上一页</button>
        <span>第 {{ page }} / {{ pageCount }} 页，共 {{ total }} 条</span>
        <button :disabled="page >= pageCount" @click="page += 1">下一页</button>
      </div>
    </template>
  </section>
</template>

<style scoped>
.signup-list {
  font-size: 14px;
}
.toolbar {
  display: flex;
  gap: 10px;
  margin-bottom: 12px;
}
.search {
  width: 240px;
  padding: 6px 8px;
  border: 1px solid #d0d5dd;
  border-radius: 4px;
}
.refresh {
  padding: 6px 12px;
  border: 1px solid #d0d5dd;
  border-radius: 4px;
  background: #fff;
  cursor: pointer;
}
.refresh:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}
.state {
  padding: 40px;
  text-align: center;
  color: #6b7280;
  border: 1px dashed #d0d5dd;
  border-radius: 6px;
}
.state-error {
  color: #e5484d;
  border-color: #f5c6c8;
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

## 常见坑

::: details 坑 1：只写了三态，空数据时表格一片空白
**现象**：搜索一个不存在的学生，页面什么都没有，用户以为功能坏了。

**原因**：只判断了加载中和失败，成功之后直接渲染表格，而表格的行数为 0。

**怎么处理**：把“空数据”当成一个独立分支，用 `computed` 判断
`status === 'success' && list.length === 0`。文案要说清是“没有符合条件的记录”，
而不是“没有数据” —— 让用户知道是筛选条件的问题。
:::

::: details 坑 2：组件卸载后请求才回来
**现象**：控制台出现警告，或者切到别的页面后仍然弹出错误提示。

**原因**：组件已经销毁，请求才返回，回调里还在改状态。

**怎么处理**：`onBeforeUnmount` 里取消请求、清掉定时器。另外在 `catch` 里判断
`signal.aborted`，直接把取消当成“正常结束”。
:::

::: details 坑 3：把“用户主动取消”当成失败弹提示
**现象**：快速翻页时，页面突然闪一下“请求失败”。

**原因**：取消请求会让 `await` 抛错，`catch` 里没区分就当成失败处理了。

**怎么处理**：判断 `axios.isCancel(error)` 或 `error.code === 'ERR_CANCELED'`，
命中就直接 `return`。**取消是正常流程，不是异常。**
:::

::: details 坑 4：竞态下加载状态闪烁
**现象**：快速翻页时，页面会在“加载中”和列表之间来回闪。

**原因**：旧请求的 `finally` 把新请求刚设上的 `loading` 关掉了。

**怎么处理**：`loading` 的写入也要受序号保护 —— 只有“当前最新请求”才有权改状态。
本案例的写法是 `if (seq !== requestSeq) return` 放在赋值之前，所有状态写入都在这个判断后面。
:::

::: details 坑 5：防抖定时器没清，卸载后还发一次请求
**现象**：在搜索框输了一半就切走页面，控制台里还能看到一次请求。

**原因**：定时器排在事件循环里，组件销毁不会自动取消它。

**怎么处理**：把 `debounceTimer` 存成组件作用域的变量，`onBeforeUnmount` 里 `clearTimeout`。
如果用 `useDebounceFn`，也建议在卸载时主动取消一次。
:::

::: details 坑 6：4xx 也重试，把错误放大
**现象**：参数写错时，一条请求变成三条，服务端日志里三倍错误。

**原因**：重试条件写成了“只要失败就重试”。

**怎么处理**：只对**可能自行恢复**的错误重试：网络不通、超时、5xx。4xx 是请求本身有问题，
重试一百次结果都一样。
:::

::: details 坑 7：拦截器返回值不统一
**现象**：有的接口拿到的是 `{ code, message, data }`，有的拿到的是 `data`，
组件里到处写 `res.data ?? res`。

**原因**：一部分请求走了拦截器，一部分没走；或者拦截器的成功分支和失败分支返回值形态不一致。

**怎么处理**：**约定拦截器只返回业务数据本身**，所有请求都走同一个实例。返回结构统一后，
接口函数的返回值类型就是确定的，组件里不用做兼容判断。
:::

::: details 坑 8：忘了把 `signal` 传给 axios
**现象**：`controller.abort()` 调了，但请求还在飞，竞态照样出现。

**原因**：`fetchSignups({ signal })` 接收了参数，但内部 `http.get` 没把它传下去。

**怎么处理**：写接口函数时检查一遍参数透传。这类问题不会报错，只会让取消静默失效，
**所以要用“快速翻页看是否出现旧数据”的方式验证一次。**
:::

## 扩展练习

::: details 练习 1：加载时保留旧数据（骨架屏）
现在是每次请求都把列表清空显示“加载中”。改成：首次加载显示骨架屏，刷新时保留旧数据加一个半透明遮罩。

**思路**：需要把“有没有数据”和“是不是在加载”两个判断分开。条件是
`list.length === 0 && isBusy` 时显示骨架屏，`list.length > 0 && isBusy` 时显示旧数据加遮罩。
注意在竞态下，遮罩的显隐同样要受序号保护。
:::

::: details 练习 2：把分页与筛选同步到地址栏
刷新页面后，页码、关键字、每页条数都要恢复。

**思路**：用路由 query 作为唯一数据源：进入页面时从 `route.query` 初始化本地状态，
状态变化时用 `router.replace` 写回去。用 `router.replace` 而不是 `push`，
否则用户点五次翻页要按五次返回才能退出页面。路由用法见[路由基础](/unit09/01-router-basics)。
:::

::: details 练习 3：加一个“取消”按钮
搜索框旁边加一个按钮，点了之后中止当前请求，页面回到上一次成功的数据。

**思路**：要额外保存一份“上一次成功的结果”。取消之后不能把页面变成错误态，
而要回到 `success` 并显示旧数据，同时给用户一个“已取消”的轻提示。
这个练习的重点是**分清“用户取消”和“请求失败”是两件事**。
:::

::: details 练习 4：列表和统计并行请求
页面要同时显示报名总数、待审核数和一个状态分布图，一共三个接口。

**思路**：用 `Promise.all` 并行发起，总耗时取决于最慢的那个接口，而不是三个相加。
但要注意：**其中任意一个失败，`Promise.all` 会整体失败**。如果希望“统计失败不影响列表显示”，
就用 `Promise.allSettled`，然后分别判断每个接口的成功与失败，
并给失败的那部分单独显示重试入口。

:::

---

上一页：[案例 03 · 树状视图与递归组件](/cases/03-tree) · 下一页：[案例 05 · Markdown 编辑器](/cases/05-markdown)
