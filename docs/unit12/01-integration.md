# 12.1 前后端联调

## 联调是把两个“各自能跑”的东西接起来

在单元 11 里，你用的是 mock 数据 —— 自己写的假数据，字段名自己定，返回结构自己定。

现在后端同学写好接口了。你以为把 `baseURL` 一改就完事了，结果是：

```
POST /api/auth/login  →  200
{ code: 200, data: { token: "eyJ..." }, message: "success" }
```

你的请求层拦截器写的是：

```js
if (code !== 0) { /* 当成失败处理 */ }
```

于是登录成功，前端判定为失败。你去找后端，后端说“我返回的是 200 啊，标准 HTTP 状态码”。

**这就是联调。** 两边各自的代码都没错，但约定不一样。联调要解决的就是这类问题。

## 联调的完整流程

不要一上来就调最复杂的接口。按这个顺序走：

| 阶段 | 做什么 | 目的 |
| --- | --- | --- |
| 第一步：对约定 | 和后端一起过一遍接口文档，确认统一响应结构、分页字段名、时间格式 | 把能提前发现的问题提前发现 |
| 第二步：用工具先试 | 用 Postman / Apifox 直接调接口，不经过前端 | 确认接口本身是通的 |
| 第三步：调最简接口 | 前端接上登录接口 | 验证请求层、拦截器、跨域 |
| 第四步：调列表接口 | 接活动列表 | 验证分页参数、响应结构 |
| 第五步：调写接口 | 新增、编辑、下架 | 验证参数格式、错误码 |
| 第六步：串完整链路 | 登录 → 列表 → 新增 → 审核 | 验证 token 携带、状态同步 |

**第二步不能跳过。** 很多同学直接用前端调接口，一报错就分不清是前端传错了还是后端返回错了。**先用工具确认接口本身没问题，把范围缩小一半。**

::: tip 用 curl 也能替代 Postman
不想装工具的话，命令行就够：

```bash
curl -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d @login.json
```

其中 `login.json` 里放请求体，内容是 `{ "username": "organizer", "password": "..." }`。

**把凭据放进文件而不是写在命令行里**，是因为命令行参数会留在 shell 的历史记录里。这个习惯在操作真实账号时很重要。

**带 token 的请求**：

```bash
curl http://localhost:8080/api/activities?page=1&pageSize=10 \
  -H "Authorization: Bearer <登录返回的 token>"
```

**好处是命令可以直接贴进联调记录里**，别人能复制执行。Postman 的截图做不到这一点。
:::

## 第一件要定下来的事：统一响应结构

前后端必须约定一个统一的外层结构。这个项目用的约定是：

```json
{
  "code": 0,
  "message": "success",
  "data": { }
}
```

| 字段 | 含义 |
| --- | --- |
| `code` | 业务状态码。`0` 表示成功，非 `0` 表示业务失败 |
| `message` | 给用户看的提示文案 |
| `data` | 真正的业务数据 |

**为什么要有 `code`，不直接用 HTTP 状态码？**

因为 HTTP 状态码不够用。比如“用户名或密码错误”和“账号被禁用”，HTTP 都返回 401。前端要区分这两种情况（提示文案不同），就需要业务码：

```json
{ "code": 1001, "message": "用户名或密码错误", "data": null }
{ "code": 1002, "message": "账号已被禁用，请联系管理员", "data": null }
```

::: warning 要和后端确认清楚的三件事
**一、成功码是 `0` 还是 `200`。** 两种约定都很常见。**不要猜，去问。** 猜错的后果是登录成功却被判定为失败 —— 这个 bug 你要花半小时才能想明白。

**二、业务失败用 HTTP 200 还是 4xx。** 有些后端所有错误都返回 HTTP 200，靠 `code` 区分；有些后端业务错误也返回 4xx。**这两种情况的拦截器写法完全不同。**

```js
// 情况 A：业务失败也返回 HTTP 200
request.interceptors.response.use((response) => {
  const { code, data, message } = response.data
  if (code !== 0) {
    const err = new Error(message)
    err.code = code          // 别漏：页面要按 code 分支处理
    err.data = data
    return Promise.reject(err)
  }
  return data
})

// 情况 B：业务失败返回 4xx，会直接进入 error 回调
request.interceptors.response.use(
  (response) => response.data.data,
  (error) => {
    const body = error.response?.data
    error.code = body?.code          // 同样把业务码带出来
    error.data = body?.data
    error.message = body?.message ?? error.message
    return Promise.reject(error)
  }
)
```

**两种情况都要做同一件事：把业务码带到 reject 出来的错误对象上。** 漏了它，页面里 `e.code === 2005` 这类判断永远不成立 —— 而且不报错，只是静静失效，很难查。

**三、分页的字段名。** 是 `list` 还是 `records`？是 `total` 还是 `totalCount`？是 `page` / `pageSize` 还是 `pageNum` / `pageSize`？

**这三件事定下来写进[接口约定](/project/api)，后面所有人照这个来。**
:::

## 第二件要定下来的事：字段名与类型

翻开你的表单代码，看提交的字段名：

```js
const payload = {
  title: form.title,
  type: form.type,
  quota: form.quota,
  signupDeadline: form.signupDeadline    // 驼峰
}
```

后端的接口文档写的是：

```
signup_deadline  (datetime, 必填)
```

**一个驼峰，一个下划线。** 提交上去，后端说“缺少必填参数 signup_deadline”。

有三种处理方式，各有取舍：

| 方式 | 前端改动 | 后端改动 | 适用情况 |
| --- | --- | --- | --- |
| 后端改成驼峰 | 无 | 改字段名 | 后端项目刚开始，改动成本低 |
| 前端改成下划线 | 改表单字段名 | 无 | 后端已经对接了别的客户端 |
| 前端在 api 层做转换 | 加两个转换函数 | 无 | 两边都不想改，字段又比较多 |

**课程项目推荐第一种：让后端用驼峰。** 因为 JavaScript 生态普遍用驼峰，前端代码里到处都是 `signup_deadline` 会很难看，而且 `el-form` 的 `prop` 也得跟着改。

**但这不是绝对的。** 如果后端是已经上线的老系统，改字段名的代价远大于前端做转换。**判断标准是“哪边改动成本低”，不是“哪边更规范”。**

如果确实要前端转换，放在 `api` 层，不要散在组件里：

```js [src/api/activity.js]
// 后端 → 前端
function toModel(raw) {
  return {
    id: raw.id,
    title: raw.title,
    type: raw.type,
    quota: raw.quota,
    approvedCount: raw.approved_count,
    signupDeadline: raw.signup_deadline,
    offShelf: raw.off_shelf
  }
}

// 前端 → 后端
function toPayload(model) {
  return {
    title: model.title,
    type: model.type,
    quota: model.quota,
    signup_deadline: model.signupDeadline
  }
}

export async function getActivityDetail(id) {
  const { data } = await request.get(`/activities/${id}`)
  return toModel(data)
}

export async function createActivity(form) {
  return request.post('/activities', toPayload(form))
}
```

::: details 时间的三种格式，一定要问清楚
同一个接口文档里，时间可能出现三种写法：

| 写法 | 例子 | 什么时候用 |
| --- | --- | --- |
| 字符串 | `"2026-03-20 14:30:00"` | 最常见的约定 |
| 时间戳（毫秒） | `1774167000000` | 有些后端习惯返回数字 |
| ISO 8601 | `"2026-03-20T06:30:00.000Z"` | Java 的 `LocalDateTime` 序列化默认可能这样 |

**前端要问的问题是**：“时间是字符串还是时间戳？”

字符串的话还要问：“带不带时区？是 `yyyy-MM-dd HH:mm:ss` 吗？”

时间戳的话要注意：**JavaScript 的 `Date` 用毫秒，有些后端用秒。** 秒级时间戳直接 `new Date(1774167000)` 会得到一个 1970 年的日期。

处理方式：在 `utils/format.js` 里统一收口，别在每个页面各写一遍：

```js [src/utils/format.js]
/** 兼容字符串、毫秒时间戳、秒级时间戳 */
export function toDate(value) {
  if (value == null || value === '') return null
  if (typeof value === 'number') {
    // 小于 10 位数的按秒处理
    return new Date(String(value).length <= 10 ? value * 1000 : value)
  }
  // iOS Safari 对 "2026-03-20 14:30:00" 这种格式解析会失败，要换成斜杠
  return new Date(String(value).replace(/-/g, '/'))
}

export function formatDateTime(value) {
  const d = toDate(value)
  if (!d || Number.isNaN(d.getTime())) return '—'
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}
```

**`new Date("2026-03-20 14:30:00")` 在 Chrome 上能用，在 iOS Safari 上会得到 `Invalid Date`。** 换成斜杠就都能用了 —— 这是一个真实的、很多人在真机上才发现的问题。
:::

## 第三件要定下来的事：跨域

跨域不是前端的 bug，也不是后端的 bug，是浏览器的安全策略。

报错长这样：

```
Access to XMLHttpRequest at 'http://localhost:8080/api/activities'
from origin 'http://localhost:5173' has been blocked by CORS policy:
No 'Access-Control-Allow-Origin' header is present on the requested resource.
```

**关键信息是 `origin 'http://localhost:5173'`** —— 意思是“这个来源的页面去请求了另一个来源”。

三种解决方案：

| 方案 | 前端改 | 后端改 | 说明 |
| --- | --- | --- | --- |
| 开发环境用代理 | 配 `server.proxy` | 无 | 本地开发推荐 |
| 后端开启 CORS | 无 | 加跨域配置 | 生产环境的常规做法 |
| Nginx 反向代理 | 无 | 无 | 部署后统一走同域 |

**同一时刻只需要一种。** 有些同学在开发环境同时配了代理和后端 CORS，出问题时分不清是哪个生效了。

开发环境用代理：

```js [vite.config.js]
export default defineConfig({
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true
      }
    }
  }
})
```

::: warning 代理配置里最常见的两个错
**一、`/api` 被重写了两次。** 如果后端的接口路径本身就是 `/api/activities`，就不要再 `rewrite`：

```js
// ✗ 后端接口是 /api/activities，被改成了 /activities
proxy: {
  '/api': {
    target: 'http://localhost:8080',
    rewrite: (path) => path.replace(/^\/api/, '')
  }
}
```

去掉 `rewrite` 就对了。**判断方法**：前端请求 `/api/activities`，目标地址是 `target + 请求路径`。看拼出来的完整地址对不对，就知道要不要 rewrite。

**二、改了 `vite.config.js` 没重启。** Vite 的配置文件改动**必须重启开发服务器**才生效。这个坑每个人都踩过一次，改完没反应先重启。
:::

::: details 为什么用代理就没有跨域了
跨域的判断主体是**浏览器**。浏览器检查的是“当前页面的地址”和“请求的地址”是否同源（协议 + 域名 + 端口都相同）。

**不用代理时**：页面在 `http://localhost:5173`，请求 `http://localhost:8080` —— 端口不同，跨域。浏览器拦截。

**用代理时**：页面在 `http://localhost:5173`，请求 `/api/activities` —— 这是相对路径，实际请求的是 `http://localhost:5173/api/activities`，同源。浏览器放行。

**然后** Vite 开发服务器（服务端，不是浏览器）收到这个请求，把它转发给 `localhost:8080`，拿回结果再返回给浏览器。**服务端之间的请求没有跨域限制**，因为跨域是浏览器的策略，不是网络的限制。

所以“代理”本质上是：**让浏览器以为在跟同源的服务器说话，实际的跨域请求由开发服务器替你做了。**

这也解释了为什么代理只在开发环境有效 —— 打包之后没有 Vite 开发服务器了，得靠 Nginx 做同样的事。见 [12.3 部署上线](/unit12/03-deploy)。
:::

## token 与 401：最容易出 bug 的地方

请求要带 token，token 失效要跳登录页。这个逻辑看着简单，但有四个坑。

```js [src/api/request.js]
import axios from 'axios'
import { ElMessage } from 'element-plus'

const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 10000
})

// 请求拦截器：带上 token
request.interceptors.request.use((config) => {
  // ⚠️ 不能在文件顶层 import store 然后在这里用
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截器：统一处理业务码与 401
request.interceptors.response.use(
  (response) => {
    const { code, data, message } = response.data
    if (code !== 0) {
      ElMessage.error(message || '请求失败')
      const err = new Error(message || '请求失败')
      err.code = code          // 把业务码挂到 Error 上
      err.data = data          // 冲突错误（4003）的详细信息在 data 里
      return Promise.reject(err)
    }
    return data
  },
  (error) => {
    const status = error.response?.status

    if (status === 401) {
      // 清理登录态并跳回登录页
      localStorage.removeItem('access_token')
      // 用 location 而不是 router，避免在拦截器里依赖 router 实例
      if (!location.pathname.startsWith('/login')) {
        location.href = `/login?redirect=${encodeURIComponent(location.pathname)}`
      }
      return Promise.reject(error)
    }

    const message = error.response?.data?.message ?? '网络异常，请稍后重试'
    ElMessage.error(message)
    // HTTP 层错误也把业务码挂上去（后端在 4xx 里也返回 code 时）
    error.code = error.response?.data?.code
    error.data = error.response?.data?.data
    return Promise.reject(error)
  }
)

export default request
```

::: tip `err.code = code` 这两行是这一节最容易被漏掉的代码
`new Error(message)` 创建出来的对象上只有 `message` 和 `stack`，**没有 `code`**。

漏了这两行的后果是：页面里所有按错误码分支的逻辑全部失效。

```js
try {
  await approveSignup(id)
} catch (e) {
  if (e.code === 2005) {          // 永远是 undefined，这个分支永远不进
    quotaError.value = e.message
  } else {
    ElMessage.error(e.message)    // 所有错误都走到这里，提示变得没有针对性
  }
}
```

**判断方法**：在 `catch` 里打一行 `console.log(e.code)`。打出 `undefined` 就是漏了。

同样重要的是 `err.data = data`。**冲突检测（`4003`）的详细信息——和哪个活动、哪个时段的场次冲突——都在 `data` 里。** 不挂上去，前端就只能提示一句“时段冲突”，用户不知道该改哪里。
:::

### 坑一：在文件顶层 import store

```js
// ✗ 可能在 Pinia 初始化之前就执行了
import { useUserStore } from '@/stores/user'
const userStore = useUserStore()      // 这里会报 "getActivePinia() was called but there was no active Pinia"
```

`useUserStore()` 必须在 Pinia 被 `app.use(createPinia())` 安装之后才能调用。而 `request.js` 可能在 `main.js` 里被更早地 import 到。

**两种解决办法：**

**办法一**：直接在拦截器里读 `localStorage`（上面代码用的就是这个）。最简单，没有时序问题。

**办法二**：在拦截器内部（调用时才执行）拿 store：

```js
request.interceptors.request.use((config) => {
  const userStore = useUserStore()      // 调用时才执行，此时 Pinia 已安装
  if (userStore.token) {
    config.headers.Authorization = `Bearer ${userStore.token}`
  }
  return config
})
```

**注意必须在拦截器的回调函数内部调用 `useUserStore()`**，不能在外面。

### 坑二：token 拼接格式不对

`Authorization: Bearer <token>` 里的 `Bearer` 和空格都不能少。

有些后端约定的是 `Authorization: <token>`（没有 Bearer），有些用自定义头 `token: <token>`。**去问，不要猜。**

猜错的后果是：后端一直返回 401，你以为 token 过期了，其实格式不对。**排查方法：看 Network 里的请求头，再和接口文档逐字对比。**

### 坑三：401 的死循环

如果登录接口本身返回 401（用户名密码错误），而拦截器又跳转登录页 —— 会不断刷新页面。

上面代码里的 `if (!location.pathname.startsWith('/login'))` 就是防这个。**这个判断不能省。**

另一种情况：跳转时带了 `redirect` 参数，登录页又去请求一个 401 的接口，又跳转。**所以要确认登录页上的接口都是免鉴权的。**

### 坑四：登录后 token 存在哪

| 位置 | 有效期 | 安全性 | 适用 |
| --- | --- | --- | --- |
| `localStorage` | 一直有效，除非手动清 | 任何脚本都能读 | 常规选择 |
| `sessionStorage` | 关闭标签页就清 | 同上 | 公共机房、需要更短会话 |
| 内存（Pinia） | 刷新就丢 | 最高，脚本也拿不到持久副本 | 高安全要求 + 配合 refresh token |
| Cookie（httpOnly） | 由后端设 | 脚本读不到，防 XSS | 最安全的做法，但需要后端配合 |

**课程项目用 `localStorage`。** 但要清楚它的风险：**`localStorage` 里的 token 能被任何注入的脚本读走（XSS 攻击）。**

前端能做的缓解措施：

- 不要把用户输入直接塞进 `v-html`（这是 XSS 最主要的入口）。
- 后端返回的富文本内容，渲染前要过滤。
- token 设置较短的过期时间，配合 refresh token 续期。

**这些措施只是缓解。** 真正安全的做法是 httpOnly Cookie，但要处理 CSRF，成本更高。**记住这条原则：前端没有任何秘密，安全必须靠后端。**

## 联调排错的方法

报错了，怎么快速定位？按这个顺序看。

### 第一步：看 Network 面板

这是所有排查的起点。打开开发者工具 → Network → 找到那条请求，看四件事：

| 看什么 | 能判断出什么 |
| --- | --- |
| Status Code | 是 4xx（参数 / 权限问题）、5xx（后端异常）还是 CORS 错误（没有状态码） |
| Request URL | 路径对不对，有没有拼错、少了前缀 |
| Request Payload | 参数名字和格式对不对（这一步能发现 90% 的“参数错误”） |
| Response | 后端返回了什么错误信息 |

**CORS 错误的特征是 Status 显示 `(failed)` 或 `CORS error`，而不是一个数字。** 看到这个直接去查跨域配置。

### 第二步：对照接口文档逐字比对

把 Request Payload 和接口文档并排看：

| 检查项 | 常见错误 |
| --- | --- |
| 路径 | `/api/activity` vs `/api/activities`（单复数） |
| 方法 | `PUT` 写成了 `PATCH` |
| 参数名 | `pageSize` vs `page_size` |
| 参数类型 | 数字传成了字符串 `"10"` |
| 缺参数 | 忘了传必填的组织者 id |
| 多参数 | 把整个表单对象传了，里面含后端不认识的字段 |

**逐字比对听起来笨，但它是定位最快的办法。** 大部分联调问题在这一步就能解决。

### 第三步：用同样的参数在 Postman / curl 里复现

如果前端传的参数和文档一致，但接口还是报错，那就用命令行复现：

```bash
curl -X POST http://localhost:8080/api/activities \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <登录返回的 token>" \
  -d '{"title":"测试活动","type":"LECTURE","quota":50,"signup_deadline":"2026-04-01 18:00:00"}'
```

**如果命令行也报错** → 后端的问题，把这条命令发给后端同学。
**如果命令行成功，前端失败** → 前端的问题，对比两次请求的差别（用浏览器的“Copy as cURL”功能把前端的请求也导出来对比）。

**这一步的价值是把“我觉得是后端的问题”变成“这是复现命令，你看一下”。** 沟通效率差别很大。

### 第四步：记进联调问题记录表

解决了就记下来。为什么要记：

- 同样的错误会出现第二次（尤其是 token 相关的问题）。
- 答辩时这是很好的素材 —— 它证明你真的调过，而不是纸上谈兵。
- 万一问题反复出现，记录里有排查路径，不用从头开始。

## 联调检查清单

| 检查项 | 怎么验证 |
| --- | --- |
| 接口用工具能调通 | 用 curl 或 Postman 调一遍登录、列表、新增 |
| 统一响应结构已确认 | 拦截器里的成功码和实际返回的一致 |
| 分页字段名已确认 | 列表页能显示正确的总数 |
| 时间字段格式已确认 | 列表里的时间显示正常，不是 `Invalid Date` |
| 字段名驼峰 / 下划线已统一 | 新增活动能成功提交，后端不报“缺少参数” |
| 开发环境跨域已解决 | 请求没有 CORS 报错 |
| token 能正确携带 | Network 里看请求头有 `Authorization: Bearer ...` |
| 刷新页面登录态不丢 | 登录后刷新，还停留在原页面 |
| token 失效能跳登录页 | 手动把 `localStorage` 里的 token 改成乱码，然后请求一次，看是否跳登录页 |
| 401 不会死循环 | 上面那步操作后，页面稳定停在登录页，不反复刷新 |
| 业务错误有提示 | 用一个不存在的活动 id 请求详情，看有没有错误提示 |
| 网络异常有提示 | 关掉后端服务，请求一次，看有没有“网络异常”提示 |
| 联调问题记录表有内容 | 至少 3 条 |

## 小结

- **联调是把两个“各自能跑”的东西接起来**，问题出在约定不一致，不是谁写错了。
- **按六步走**：对约定 → 工具先试 → 调最简接口 → 调列表 → 调写接口 → 串完整链路。**工具先试这一步不能跳。**
- **三件事必须先定下来**：统一响应结构（成功码、错误返回方式）、分页字段名、时间格式。
- **业务失败用 HTTP 200 还是 4xx**，决定了拦截器怎么写，必须先问清。
- **字段名不一致有三种解法**，按“哪边改动成本低”选，不要只看哪个更规范。
- **跨域是浏览器的策略**，开发用 Vite 代理，生产用 Nginx 或后端 CORS，同一时刻只需一种。
- **`new Date("2026-03-20 14:30:00")` 在 iOS Safari 上会得到 `Invalid Date`**，换成斜杠就通用。
- **不要在 `request.js` 顶层调 `useUserStore()`**，会有 Pinia 初始化时序问题。在拦截器回调内部调用，或者直接读 `localStorage`。
- **401 处理要防死循环**，跳转前判断当前是不是已经在登录页。
- **`localStorage` 存 token 有 XSS 风险**，安全必须靠后端。
- **排查四步**：看 Network → 对照文档逐字比对 → 用命令行复现 → 记录。
- **记录表比“功能都实现了”这句话有价值。** 它证明你真的调通过。

## 常见坑

::: details 请求发了，但 Network 里看不到
**现象**：点查询按钮没反应，Network 面板里一条请求都没有。

**原因**：请求根本没发出去。三种可能：

**一、`await` 漏了但代码里有报错。** 在请求之前就有异常，函数提前中断了。

**二、请求被浏览器缓存拦下了。** 状态显示 `(disk cache)`，看不到新请求。勾上 Network 面板的“Disable cache”。

**三、代码里的请求函数根本没被调用。** 比如 `@click="handleSearch"` 写成了 `@click="handleSearch()"` —— 后者会在渲染时立刻执行一次并返回 `undefined`。

```vue
<!-- ✗ 渲染时就执行了 -->
<el-button @click="search()">查询</el-button>

<!-- ✓ 点击时才执行 -->
<el-button @click="search">查询</el-button>
```

**注意带参数时两种写法都合法，语义不同：**

```vue
<!-- 传事件对象 -->
<el-button @click="search">查询</el-button>
<!-- 传自定义参数 -->
<el-button @click="search('draft')">查询草稿</el-button>
```
:::

::: details 列表能显示，但总数是 0
**现象**：表格里有 10 条数据，分页器显示“共 0 条”，页码只有 1 页。

**原因**：`total` 取错字段了。

```js
// ✗ 后端返回的是 { records: [...], total: 42 }
total.value = data.list.length

// ✓
total.value = data.total
```

**还可能的原因**：后端返回的字段名是 `totalCount`、`count`、`totalElements`（Spring Data 的分页默认字段），前端取的是 `total`。

**怎么处理**：在 Network → Response 里看真实的返回结构，按实际字段名取。**如果用了 `toModel` 转换层，在这一层统一改成前端习惯的名字**：

```js
function toPage(raw) {
  return {
    list: raw.records ?? raw.list ?? [],
    total: raw.total ?? raw.totalCount ?? raw.totalElements ?? 0
  }
}
```

**这一段看着啰嗦，但能让前端不依赖后端的具体命名。** 后端换了分页实现，前端只改这一处。
:::

::: details 新增成功了，但列表里看不到刚创建的那条
**现象**：提交后提示成功，跳回列表，但列表里没有刚新增的活动。

**原因**：有三种，从简单到复杂。

**一、跳回列表后没有重新请求。** 列表数据是缓存的（`KeepAlive`）或者 `onMounted` 没重新执行。

**怎么处理**：跳转时通知列表刷新。最简单的方式是让列表页监听路由变化：

```js
// ActivityList.vue
const route = useRoute()
watch(() => route.fullPath, () => {
  if (route.name === 'activity-list') load()
})
```

**更简单的办法**：跳转时带一个标记，列表页看到就刷新：

```js
router.push({ name: 'activity-list', query: { refresh: Date.now() } })
```

**二、筛选条件把它过滤掉了。** 新增的活动是“草稿”状态，但列表当前的筛选条件是“报名中”。

**怎么处理**：新增成功后跳转时把筛选条件重置，或者提示用户“刚创建的活动在草稿状态”。

**三、排序问题。** 列表默认按创建时间倒序，如果后端按正序返回，刚创建的在最后一页。

**怎么处理**：确认排序规则，或者让后端默认按创建时间倒序。
:::

::: details 401 之后一直刷新页面
**现象**：token 过期了，页面疯狂刷新，停不下来。

**原因**：响应拦截器里 `location.href = '/login'`，登录页上又有接口在请求，那个接口也返回 401，又跳转。

**怎么处理**：三层防护。

**第一层**：跳转前判断当前路径：

```js
if (!location.pathname.startsWith('/login')) {
  location.href = '/login'
}
```

**第二层**：确认登录页上的请求都是免鉴权的。登录接口本身不该需要 token，所以它返回的 401 应该在业务层处理（“密码错误”），而不是走“token 失效”这条分支。

区分方法：**看请求有没有带 token**。

```js
if (status === 401 && error.config?.headers?.Authorization) {
  // 带了 token 还 401，说明 token 失效了
} else if (status === 401) {
  // 没带 token 的 401，是登录失败，交给调用方处理
}
```

**第三层**：加一个“正在跳转”的标记，防止并发请求触发多次跳转。

```js
let redirecting = false
// ...
if (!redirecting) {
  redirecting = true
  location.href = '/login'
}
```

**并发请求的场景很常见**：进一个页面同时发了三个接口，token 都过期了，三个 401 一起触发跳转。
:::

::: details Postman 能调通，浏览器报 CORS
**现象**：同样的接口，Postman 正常，浏览器报跨域。

**原因**：**Postman 不做跨域检查**（它不是浏览器，没有同源策略）。所以“Postman 能通”只能说明接口本身没问题，不能说明跨域配置正确。

**怎么处理**：跨域必须用真实浏览器验证。配好代理或后端 CORS 之后，在浏览器里再测一次。

**额外提醒**：如果请求带自定义头（比如 `Authorization`），会触发浏览器的 **预检请求**（`OPTIONS` 方法）。后端必须正确响应 `OPTIONS` 请求，返回允许的方法和头：

```
Access-Control-Allow-Origin: http://localhost:5173
Access-Control-Allow-Methods: GET, POST, PUT, PATCH, DELETE, OPTIONS
Access-Control-Allow-Headers: Content-Type, Authorization
```

**如果 Network 里看到一条 OPTIONS 请求失败**，就是这个原因。这种问题在 Postman 里永远发现不了。
:::

::: details 表单提交的是字符串 "false"，后端需要布尔值
**现象**：下架操作的接口返回参数类型错误。

**原因**：从某个地方（`localStorage`、URL query、表单控件）拿到的值都是字符串。

**怎么处理**：提交前显式转换。

```js
// ✗
await setActivityOffShelf(id, form.offShelf)

// ✓
await setActivityOffShelf(id, form.offShelf === true || form.offShelf === 'true')
```

**注意不要用 `Boolean('false')`** —— 它的结果是 `true`（非空字符串都是真值）。这是一个经典的坑。

**更靠谱的写法**：在后端接口约定里明确“布尔字段用 `0/1` 还是 `true/false`”，然后用一个工具函数统一转换：

```js
// utils/format.js
export function toBool(value) {
  return value === true || value === 1 || value === '1' || value === 'true'
}
```
:::

## 课后练习

::: details 练习 1：完成一次完整的联调并写记录表
把前端接到后端（同学写的或公开的测试接口都行），跑通“登录 → 活动列表 → 新增活动 → 下架活动”这条链路，写一份联调记录表。

**思路提示**：

- 记录表建议的列：编号、时间、现象、排查过程、定位、处理、是否复现。**“排查过程”这一列最重要**，它记录了你试过什么、排除了什么。
- 如果实在没有可用的后端，用 `json-server` 起一个。写一个 `db.json`，里面放活动数据，就能得到一套 REST 接口：

```bash
npx json-server --watch db.json --port 8080
```

```json [db.json]
{
  "activities": [
    { "id": 1, "title": "校园歌手大赛", "type": "COMPETITION", "quota": 100, "status": "SIGNING" },
    { "id": 2, "title": "程序设计竞赛", "type": "COMPETITION", "quota": 60, "status": "DRAFT" }
  ]
}
```

**注意 `json-server` 返回的分页结构和你的接口约定不同**（它返回的是 `X-Total-Count` 响应头），所以这正好是一个练“字段名对不上怎么处理”的机会 —— 在 `toModel` 里适配它。
:::

::: details 练习 2：给请求层加上统一的重试与超时
现在的请求失败就是失败。请加上：

- 超时时间 10 秒，超时给出明确提示
- 网络类错误（非 4xx）自动重试一次
- 重试时不要重试 POST 请求

**思路提示**：

- axios 的超时错误特征是 `error.code === 'ECONNABORTED'`。
- 判断“是不是网络类错误”：没有 `error.response` 就说明请求根本没到服务器（网络断了、超时了、被拦截了），这类可以重试；有 `error.response` 说明服务器明确拒绝了（4xx / 5xx），重试没有意义（除非是 502 / 503）。
- **为什么 POST 不重试**：POST 通常用于创建数据，重试可能导致创建两条。这是“幂等性”问题 —— GET、PUT、DELETE 是幂等的（执行多次结果相同），POST 不是。

```js
const IDEMPOTENT_METHODS = ['get', 'head', 'options', 'put', 'delete']

function canRetry(error) {
  const method = (error.config?.method ?? '').toLowerCase()
  if (!IDEMPOTENT_METHODS.includes(method)) return false
  // 没有 response → 请求没到服务器
  if (!error.response) return true
  // 502 / 503 可以重试
  return [502, 503].includes(error.response.status)
}
```

**这道题的重点不是写重试，是想清楚“什么情况下重试是安全的”。** 把结论写进你的项目文档。
:::

::: details 练习 3：把接口约定写成一份可执行的文档
整理出一份 `docs/api.md`，包含：

- 统一响应结构说明
- 错误码表（至少 8 个）
- 每个接口的完整定义（路径、方法、请求参数、响应示例、错误情况）

**思路提示**：

- 请求参数要写清类型和是否必填，不要只写参数名。
- 响应示例要用真实的 JSON，不要用 `{ ... }` 省略。
- 错误码表要覆盖：参数校验失败、未登录、无权限、资源不存在、状态不允许（比如给已结束的活动排场次）、唯一约束冲突（比如场地名称重复）、名额已满、时段冲突。
- **状态不允许和时段冲突这两个错误码特别重要** —— 它们对应的是业务规则，前端要能识别并给出针对性提示，而不是一律提示“操作失败”。
- 写完自己检查：**照着这份文档，一个没参与项目的人能不能独立调通所有接口？**
:::

::: details 练习 4：模拟一次 401 并验证你的处理
手动制造 token 失效，验证你的前端能不能稳定处理。

**思路提示**：

操作步骤：

1. 正常登录，确认能访问活动列表。
2. 打开开发者工具 → Application → Local Storage，把 `access_token` 的值改成 `abc123`（一个非法 token）。
3. 在应用里点一次“查询”。
4. 观察：有没有跳转到登录页？跳转后有没有稳定停住，还是反复刷新？
5. 登录页上的接口有没有报错？地址栏的 `redirect` 参数对不对？重新登录后有没有回到原来的页面？

**如果第 4 步出现反复刷新**，回去看这一节“401 的四条防护”。

**再加一个测试**：同时发三个请求（进一个会发多个请求的页面），三个都返回 401，看会不会触发三次跳转。用 `console.count('redirect')` 数一下。
:::

---

上一节：[单元导学](/unit12/) · 下一节：[12.2 构建优化](/unit12/02-build-optimize)
