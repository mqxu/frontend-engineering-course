# 10.4 请求层封装

## 从一个重复了十几遍的请求说起

打开你现在的项目，搜一下 `axios`，大概率会看到这样的代码散落在各个页面里：

```js [views/ActivityListView.vue（反例）]
// 页面一
const res = await axios.get('http://192.168.1.100:8080/api/activity/list', {
  params: { page: 1, pageSize: 10 },
  headers: { Authorization: 'Bearer ' + localStorage.getItem('token') }
})
if (res.data.code === 0) {
  list.value = res.data.data.list
} else {
  ElMessage.error(res.data.message)
}
```

```js [views/ReviewView.vue（反例）]
// 页面二
const res = await axios.get('http://192.168.1.100:8080/api/signup/list', {
  params: { status: 'pending' }
  // ← 这里忘了带 token，接口直接返回 401
})
```

问题一眼可见：

1. **地址写死了**。服务器换了 IP，要全局搜索替换。
2. **每个页面各写一遍 token 注入**。写漏一个就 `401`。
3. **每个页面各写一遍错误判断**。有的判断了 `code`，有的没判断；
   有的弹提示，有的不弹。
4. **同一个接口在两个页面写了两次**，参数还不一样。

这一节要做的事，就是把上面这些**重复的、容易漏的、应该统一的部分**抽到一个地方，
让页面只关心"我要什么数据"。

::: tip 封装之后页面长什么样
```js [views/ActivityListView.vue]
import { getActivityListApi } from '@/api/activity'

const res = await getActivityListApi({ page: 1, pageSize: 10 })
list.value = res.list // ✓ 直接拿到干净的数据
```

没有地址、没有 token、没有 `code` 判断。**这些都下沉到请求层里了。**
:::

## 请求层的目录结构

先看整体长什么样，再逐个文件拆解。

```text [src/]
src/
├── api/
│   ├── request.js          ① axios 实例 + 双拦截器（核心，只写一次）
│   ├── auth.js             ② 登录相关接口
│   ├── activity.js         ③ 活动相关接口
│   └── signup.js           ④ 报名审核相关接口
├── stores/
│   └── auth.js             状态模块，请求层从这里取 token
└── views/
    └── ActivityListView.vue  只 import 函数，不碰 axios
```

分工：

| 文件 | 职责 | 谁改它 |
| --- | --- | --- |
| `request.js` | 统一实例、超时、拦截器 | 架构调整时改一次 |
| `api/activity.js` | 活动模块的接口地址与参数 | 接口变了改这里 |
| 页面组件 | 调函数、处理返回的数据与界面状态 | 天天改 |

## 第一步：创建 axios 实例

不要直接用全局的 `axios`，而是 `axios.create(...)` 造一个属于本项目的实例。
这样配置只写一次，也不会影响项目里其他可能用到的 axios 默认值。

```js [src/api/request.js]
import axios from 'axios'

// 基础地址从环境变量读，不同环境不同值，见“环境变量”一节
const baseURL = import.meta.env.VITE_API_BASE_URL || '/api'

const request = axios.create({
  baseURL,
  timeout: 10000 // 10 秒还没响应就当作超时
})

export default request
```

::: warning 基础地址为什么用环境变量
开发时接口在 `http://localhost:8080`，测试环境在 `http://test.xxx.edu.cn`，
生产环境在 `https://api.xxx.edu.cn`。**同一份代码要在三个环境跑**，
地址不能写死。

用 `import.meta.env.VITE_API_BASE_URL`，在不同 `.env` 文件里给不同值。
配置方法见 [单元 2 的环境变量](/unit02/05-env-config)。

注意：只有以 `VITE_` 开头的变量才会暴露给浏览器代码。
:::

## 第二步：请求拦截器注入凭证

请求发出去之前，统一在这里加上 token。**页面里再也不用管这事。**

```js [src/api/request.js]
import { useAuthStore } from '@/stores/auth'

// 请求拦截器：每个请求发出去之前都会走这里
request.interceptors.request.use(
  (config) => {
    // ✓ 在拦截器函数内部调用 store，此时 Pinia 已装好
    const authStore = useAuthStore()

    if (authStore.token) {
      // 约定：后端用 Authorization 头，格式是 Bearer + 空格 + token
      config.headers.Authorization = `Bearer ${authStore.token}`
    }

    return config // ✓ 一定要把 config 返回，否则请求发不出去
  },
  (error) => {
    // 请求还没发出去就出错了（比如参数拼装异常）
    return Promise.reject(error)
  }
)
```

::: danger 两件绝对不能忘的事
1. **必须 `return config`**。忘了返回，请求会变成 `undefined`，控制台报奇怪错误。
2. **在函数内部 `useAuthStore()`**，不要在文件顶层调用模块（原因见 [10.2](/unit10/02-pinia-basics#跨模块调用怎么写)）。
:::

::: details 为什么不用默认的 `axios` 全局拦截器
`axios.interceptors` 是全局的，会影响项目里所有 axios 请求，
包括某些第三方库内部的请求。用 `axios.create()` 造实例，
拦截器只作用于这个实例，边界清楚。
:::

## 第三步：响应拦截器统一处理

后端返回的结构通常是这样的：

```json [后端统一响应结构]
{
  "code": 200,
  "message": "success",
  "data": { "list": [], "total": 0 }
}
```

`code` 是**业务状态码**，跟 HTTP 状态码是两回事：HTTP 可能是 `200`，
但 `code` 表示业务失败（比如"名额已满"）。

响应拦截器的任务是：**判断业务是否成功，成功就把 `data` 剥出来给页面，
失败就统一提示并拒绝**。

```js [src/api/request.js]
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import router from '@/router'

request.interceptors.response.use(
  (response) => {
    const res = response.data

    // 后端没按约定返回 code 时，直接原样给出去（比如下载文件）
    if (res.code === undefined) {
      return response
    }

    if (res.code === 0) {
      // ✓ 只把 data 剥出去，页面里不用再 res.data.data
      return res.data
    }

    // 业务失败：统一提示，并拒绝，让调用方能感知失败
    ElMessage.error(res.message || '操作失败')
    return Promise.reject(new Error(res.message || '操作失败'))
  },
  (error) => {
    // 这里处理的是"请求本身失败"：网络断了、超时、HTTP 状态非 2xx
    const status = error.response?.status

    if (status === 401) {
      const authStore = useAuthStore()
      authStore.logout()
      // ✓ 用 router 实例跳转，保留单页应用的跳转能力
      router.push({ name: 'login', query: { redirect: router.currentRoute.value.fullPath } })
      return Promise.reject(error)
    }

    // 其他 HTTP 错误统一提示
    ElMessage.error(describeHttpError(error))
    return Promise.reject(error)
  }
)

function describeHttpError(error) {
  if (error.code === 'ECONNABORTED') return '请求超时，请检查网络后重试'
  const status = error.response?.status
  if (status === 403) return '没有权限执行这个操作'
  if (status === 404) return '请求的资源不存在'
  if (status >= 500) return '服务器出错了，请稍后再试'
  if (!error.response) return '网络连接失败，请检查网络'
  return error.message || '请求失败'
}
```

::: tip `return res.data` 带来的最大好处
页面里写 `const res = await getActivityListApi(...)`，
`res` 直接就是 `{ list, total }`，不用再写 `res.data.data.list`。
这层"剥壳"只做一次，所有页面都受益。
:::

::: warning 拦截器里不要弹两次提示
业务失败时，响应拦截器已经弹了一次 `ElMessage.error`。
**如果页面里 `catch` 又弹一次，用户会看到两条一样的提示。**
所以页面里对"已经被提示过的错误"通常只需要处理界面状态（比如显示重试按钮），
不要再弹 toast。这一点在 [10.5](/unit10/05-error-handling) 会展开。
:::

## 第四步：接口地址不写在组件里

按业务模块拆接口文件。每个函数只做三件事：**拼地址、给参数、返回请求**。

```js [src/api/activity.js]
import request from './request'

// 活动列表：GET，参数走 query
export function getActivityListApi(params) {
  return request.get('/activity/list', { params })
}

// 活动详情：GET，路径参数
export function getActivityDetailApi(id) {
  return request.get(`/activity/${id}`)
}

// 新建活动：POST，数据走 body
export function createActivityApi(data) {
  return request.post('/activity', data)
}

// 编辑活动：PUT，路径参数 + body
export function updateActivityApi(id, data) {
  return request.put(`/activity/${id}`, data)
}

// 删除活动：DELETE
export function deleteActivityApi(id) {
  return request.delete(`/activity/${id}`)
}
```

```js [src/api/signup.js]
import request from './request'

// 报名列表：按活动和审核状态筛选
export function getSignupListApi(params) {
  return request.get('/signup/list', { params })
}

// 通过某条报名
export function approveSignupApi(id) {
  return request.post(`/signup/${id}/approve`)
}

// 拒绝某条报名，带上拒绝理由
export function rejectSignupApi(id, reason) {
  return request.post(`/signup/${id}/reject`, { reason })
}
```

```js [src/api/auth.js]
import request from './request'

export function loginApi(data) {
  return request.post('/auth/login', data)
}

export function logoutApi() {
  return request.post('/auth/logout')
}

export function getUserInfoApi() {
  return request.get('/auth/me')
}
```

::: warning 命名约定
- 函数名以 `Api` 结尾，一眼能看出这是接口调用。
- 动词用 `get` / `create` / `update` / `delete`，跟 HTTP 方法对应。
- **接口函数不做业务处理**，不要在里面 `ElMessage`、不要 `try/catch` ——
  那些是页面或 store 的事。它只负责发请求。
:::

## 第五步：四种请求方法的参数怎么传

这是最常搞混的地方。核心区别只有一句话：
**GET / DELETE 的参数放 `params`（拼在地址后面），POST / PUT 的数据放 `data`（放在请求体里）。**

| 方法 | 参数位置 | 写法 | 典型场景 |
| --- | --- | --- | --- |
| GET | query（`params`） | `request.get(url, { params })` | 列表查询、详情 |
| POST | body（`data`） | `request.post(url, data)` | 新建、动作类接口 |
| PUT | body（`data`） | `request.put(url, data)` | 全量更新 |
| DELETE | 无 body，或用 `params` | `request.delete(url, { params })` | 删除 |

```js [参数传法对照]
// GET：参数拼进地址 → /activity/list?page=1&status=signing
request.get('/activity/list', { params: { page: 1, status: 'signing' } })

// POST：参数放进请求体
request.post('/activity', { title: '迎新晚会', quota: 100 })

// PUT：路径带 id，更新内容放请求体
request.put('/activity/12', { title: '迎新晚会（改期）' })

// DELETE：如果后端要求带参数，用 params
request.delete('/activity/12', { params: { hard: true } })
```

::: details 数组参数怎么传
后端可能期望 `status=signing&status=ended`，也可能期望 `status=signing,ended`。
axios 默认会把数组序列化成 `status[]=signing&status[]=ended`，
跟后端约定不一致时要自定义序列化：

```js
paramsSerializer: {
  indexes: null // 变成 status=signing&status=ended，不带方括号
}
```

**先跟后端确认格式，不要凭猜。**
:::

::: details 上传文件怎么写
文件用 `FormData`，并且**让 axios 自己设 `Content-Type`**，不要手写：

```js
export function uploadCoverApi(file) {
  const formData = new FormData()
  formData.append('file', file)
  return request.post('/upload', formData)
  // ✓ 不要手动设 Content-Type: multipart/form-data
  //   手写会丢掉 boundary 参数，后端解析不出文件
}
```
:::

## POST 与 PUT 封装成一个动作型接口

报名审核里有一类接口是"对某条记录做一个动作"：通过、拒绝、撤回。
这类接口 URL 都是 `POST /signup/:id/动作`，可以统一封装：

```js [src/api/signup.js]
/**
 * 对一条报名执行动作
 * @param {number} id 报名 ID
 * @param {'approve' | 'reject' | 'revoke'} action 动作名
 * @param {object} payload 附加数据（比如拒绝理由）
 */
export function actOnSignupApi(id, action, payload = {}) {
  return request.post(`/signup/${id}/${action}`, payload)
}
```

用的时候：`actOnSignupApi(12, 'approve')`。
**注意别把动作名做成任意字符串传进来** —— 那样容易拼出后端不存在的地址。
用注释或常量约束取值范围。

::: danger 不要封装成一个万能的 `request(url, method, data)`
有些教程会教你写一个 `request({ url, method, params })` 的大函数，
然后每个接口调用处都要传 URL。这等于**把地址又写回了页面**，
前面做的封装全白费。

**正确做法：一个接口一个函数，函数名表达业务含义，地址藏在这个函数里。**
:::

## 常见误区：拦截器里用 `window.location.href` 跳登录

`401` 处理时，很多人会这么写：

```js [src/api/request.js（反例）]
if (status === 401) {
  localStorage.removeItem('token')
  // ✗ 整页刷新，应用重新启动
  window.location.href = '/login'
}
```

**为什么不好：**

1. **整页刷新**：整个 Vue 应用被销毁重建，`window.location.href` 会触发浏览器重新加载页面。
   这是个单页应用，这么做等于放弃单页应用的所有好处。
2. **丢失当前路由**：刷新后跳到了 `/login`，但用户本来在 `/activities?page=3` 这个信息没了，
   登录后回不到原来位置。
3. **丢失未提交的数据**：用户正在填一个活动表单，请求超时触发 `401`，整页一刷，
   填的内容全没了。
4. **正在进行的请求全部中断**，可能引发连串报错。

正确做法是用 router 实例：

```js [src/api/request.js]
import router from '@/router'

if (status === 401) {
  const authStore = useAuthStore()
  authStore.logout()
  // ✓ 单页应用内跳转，保留应用状态与路由信息
  router.push({
    name: 'login',
    query: { redirect: router.currentRoute.value.fullPath } // 记住原地址
  })
}
```

::: warning 循环依赖的处理
`request.js` 里 `import router`，而 `router/index.js` 的守卫里又可能 `import` 了 store 或 api，
容易出现循环依赖。

如果启动时报 `Cannot access 'xxx' before initialization`，
把 `import router from '@/router'` 改成**在函数内部动态导入**：

```js
async function toLogin() {
  const { default: router } = await import('@/router')
  router.push({ name: 'login' })
}
```
:::

::: details 401 提示要不要弹
`401` 是"登录失效"，用户看到"登录已过期，请重新登录"是合理的。
但要注意**并发的 401**：页面上同时发了三个请求，三个都返回 `401`，
会弹三条一样的提示。

处理：加一个"正在跳转"的标记，第一个 `401` 跳转后，后面的直接忽略：
```js
let redirecting = false
if (status === 401 && !redirecting) {
  redirecting = true
  // ...跳转
}
```
页面跳转后这个模块会被重新加载，标记自动复位。
:::

## 完整代码汇总

把上面几段合起来，得到最终的 `request.js`：

```js [src/api/request.js]
import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'
import { useAuthStore } from '@/stores/auth'

const baseURL = import.meta.env.VITE_API_BASE_URL || '/api'

const request = axios.create({
  baseURL,
  timeout: 10000
})

// ---- 请求拦截器：注入凭证 ----
request.interceptors.request.use(
  (config) => {
    const authStore = useAuthStore()
    if (authStore.token) {
      config.headers.Authorization = `Bearer ${authStore.token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// ---- 响应拦截器：统一处理业务码与错误 ----
let redirecting = false

request.interceptors.response.use(
  (response) => {
    const res = response.data
    if (res.code === undefined) return response
    if (res.code === 0) return res.data
    ElMessage.error(res.message || '操作失败')
    return Promise.reject(new Error(res.message || '操作失败'))
  },
  (error) => {
    const status = error.response?.status

    if (status === 401) {
      if (!redirecting) {
        redirecting = true
        const authStore = useAuthStore()
        authStore.logout()
        router.push({
          name: 'login',
          query: { redirect: router.currentRoute.value.fullPath }
        })
      }
      return Promise.reject(error)
    }

    if (error.code === 'ECONNABORTED') {
      ElMessage.error('请求超时，请检查网络后重试')
    } else if (status === 403) {
      ElMessage.error('没有权限执行这个操作')
    } else if (status >= 500) {
      ElMessage.error('服务器出错了，请稍后再试')
    } else if (!error.response) {
      ElMessage.error('网络连接失败，请检查网络')
    } else {
      ElMessage.error(error.message || '请求失败')
    }

    return Promise.reject(error)
  }
)

export default request
```

::: tip 请求层的三个衡量标准
1. **改一个接口地址，只需要改 `api/` 下的一个文件。**
2. **页面里搜不到 `axios` 和 `http://`。**
3. **新增一个接口，只需要在 `api/` 里加一个函数。**

三条都满足，说明这层封装到位了。
:::

## 小结

- 用 `axios.create()` 造实例，统一配 `baseURL` 与 `timeout`，`baseURL` 从环境变量读。
- 请求拦截器注入 token；响应拦截器剥出 `data`、判业务码、统一提示错误。
- 拦截器里必须 `return config` / `return response`，否则请求链路断掉。
- 接口按业务模块拆文件（`api/activity.js`、`api/signup.js`），一个接口一个函数。
- GET / DELETE 参数放 `params`，POST / PUT 数据放 `data`。
- `401` 用 router 实例跳转，不要用 `window.location.href`。

## 常见坑

::: details 坑 1：拦截器里忘了 return
现象：请求发出去了但 `await` 拿到的是 `undefined`，页面一直拿不到数据。

原因：请求拦截器里 `config` 没 `return`，或响应拦截器里 `response` 没 `return`。

怎么处理：两个拦截器的成功回调都必须显式返回。检查时直接看有没有 `return`。
:::

::: details 坑 2：`baseURL` 配了 `/api`，接口函数里又写了 `/api/xxx`
现象：请求地址变成 `/api/api/activity/list`，返回 `404`。

原因：路径重复。

怎么处理：约定好 `baseURL` 里带不带 `/api`。
推荐 `baseURL = '/api'`，接口函数里只写 `/activity/list`。
:::

::: details 坑 3：响应拦截器剥了一层，页面里又剥一层
现象：`list.value = res.data.list` 报错说 `res.data` 是 `undefined`。

原因：拦截器已经 `return res.data` 了，页面里又按原始结构写。

怎么处理：**团队统一约定"拦截器剥一层"**，页面里直接用 `res.list`。
写之前看一眼现有接口怎么用的，保持一致。
:::

::: details 坑 4：`401` 无限跳转
现象：登录页本身也发了一个需要鉴权的请求，返回 `401`，又跳登录页，页面看起来无限刷新。

原因：跳转逻辑没排除"已经在登录页"的情况。

怎么处理：跳转前判断 `router.currentRoute.value.name !== 'login'`，
或者用上面那个 `redirecting` 标记。
:::

::: details 坑 5：在 `api/` 文件顶层 `import { useAuthStore }` 并立刻调用
现象：启动报 `getActivePinia() was called but there was no active Pinia`。

原因：`api/*.js` 里如果在模块顶层调用 store 就会踩这个坑。

怎么处理：接口文件里**根本不需要调用 store** —— 注入 token 是拦截器的职责。
:::

::: details 坑 6：超时设置得太短
现象：导出大报表时总是"请求超时"。

原因：全局 `timeout` 设成了 3 秒，长耗时接口撑不住。

怎么处理：给个别接口单独放宽超时：
```js
request.post('/report/export', data, { timeout: 60000 })
```
:::

## 课后练习

::: details 练习 1：迁移现有项目到请求层
把上一个单元的活动列表页改成使用请求层：新建 `api/request.js`、`api/activity.js`，
页面里只保留函数调用。

**参考思路**：迁移时先写 `request.js` 与 `activity.js`，
再逐个页面替换。改完搜一遍 `axios` 与 `http://`，
确保只有 `api/` 目录里出现。**用 `git diff` 看改动范围是很好的验收方式。**
:::

::: details 练习 2：给报名模块补齐接口文件
按业务需求，为报名审核写 `api/signup.js`，至少包含：
取报名列表、通过报名、拒绝报名（带理由）、导出报名名单。

**参考思路**：导出接口返回的是文件流，`responseType` 要设成 `'blob'`，
且**不能被响应拦截器的业务码判断处理**。想一想怎么给这类接口开个例外。
:::

::: details 练习 3：把"整页刷新跳登录"改成路由跳转
找一段用 `window.location.href = '/login'` 的代码，改成 `router.push`，
并补上 `redirect` 参数，让登录后能回到原地址。

**参考思路**：改完之后手动验证两件事 ——
一是登录后确实回到了原来的页面，二是原页面上的列表页回到了同一页码（如果传了 query）。
:::

---

上一节：[10.3 状态持久化](/unit10/03-persist) ·
下一节：[10.5 错误分层处理](/unit10/05-error-handling)
