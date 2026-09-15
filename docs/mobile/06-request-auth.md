# 6. 请求封装与登录态

## 一个具体的场面

列表页要请求活动数据，你写下第一版：

```js
uni.request({
  url: 'http://localhost:8080/api/activities',
  method: 'GET',
  header: { Authorization: 'Bearer ' + uni.getStorageSync('token') },
  success: (res) => {
    if (res.data.code === 0) {
      list.value = res.data.data.list
    } else {
      uni.showToast({ title: res.data.message, icon: 'none' })
    }
  },
  fail: () => {
    uni.showToast({ title: '网络错误', icon: 'none' })
  }
})
```

能跑。但等你写到第五个页面，这段代码已经复制了五遍，而且：

- 接口地址写了两遍（`localhost:8080` 那串），上线前得一个个改
- **token 是手动加的**，有一个页面忘了加，接口返回 401，你还得排查半天
- 业务码的判断、错误提示、网络异常处理，五份各自的写法略有不同
- **业务码丢了** —— 后端返回“名额已满”（`code: 2005`），到页面层只剩一句文案，没法按码做不同处理

这一节把这些收进一个文件里。

## 一、为什么必须封装

先看清 `uni.request` 和管理端 `axios` 的差别：

| | axios（管理端） | `uni.request`（用户端） |
| --- | --- | --- |
| 返回 | Promise | 没有 Promise，只有回调 |
| 拦截器 | `interceptors.request/response` | **没有** |
| 请求头统一处理 | 在拦截器里写一次 | 每次自己传 |
| 取消请求 | `AbortController` | 返回值上有 `abort()` 方法 |
| 在浏览器外能不能用 | 不能 | 能（这是它存在的理由） |

**没有拦截器是关键差别。** 管理端你在拦截器里写一次 `Authorization` 头，所有请求自动带上；`uni.request` 没有这个机制，**只能在封装层自己造一个。**

## 二、请求层：一个文件解决五件事

新建 `src/utils/request.js`：

```js [src/utils/request.js]
// 基础路径：开发环境走 vite 代理，生产环境走 Nginx 转发
const BASE_URL = '/api'

// 未授权处理器，由外部注入（避免请求层直接依赖 store）
let unauthorizedHandler = null

export function setUnauthorizedHandler(fn) {
  unauthorizedHandler = fn
}

/**
 * 统一请求方法
 * @param {object} options
 * @param {string} options.url        接口路径，不含 /api 前缀，如 /activities
 * @param {string} [options.method]   GET / POST / PUT / DELETE，默认 GET
 * @param {object} [options.data]     参数
 * @param {object} [options.header]   额外请求头
 * @param {boolean} [options.silent]  为 true 时不自动弹错误提示，默认 false
 */
export function request(options) {
  const { url, method = 'GET', data, header = {}, silent = false } = options

  const token = uni.getStorageSync('token')

  return new Promise((resolve, reject) => {
    uni.request({
      url: BASE_URL + url,
      method,
      data,
      header: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: 'Bearer ' + token } : {}),
        ...header
      },
      success: (res) => {
        // HTTP 层失败：没有响应体可读
        if (res.statusCode < 200 || res.statusCode >= 300) {
          const err = new Error('网络异常（' + res.statusCode + '）')
          err.code = res.statusCode
          if (!silent) {
            uni.showToast({ title: err.message, icon: 'none' })
          }
          reject(err)
          return
        }

        const body = res.data

        // 业务成功：直接把 data 交给调用方
        if (body.code === 0) {
          resolve(body.data)
          return
        }

        // 业务失败：把业务码和数据挂到错误对象上，别丢
        const err = new Error(body.message || '请求失败')
        err.code = body.code
        err.data = body.data

        if (body.code === 1001) {
          // 未登录或 token 失效
          if (unauthorizedHandler) unauthorizedHandler()
        } else if (!silent) {
          uni.showToast({ title: err.message, icon: 'none' })
        }

        reject(err)
      },
      fail: (e) => {
        const err = new Error('网络连接失败，请检查网络')
        err.cause = e
        if (!silent) {
          uni.showToast({ title: err.message, icon: 'none' })
        }
        reject(err)
      }
    })
  })
}

// 语义化的快捷方法
export const http = {
  get: (url, params, options) => request({ url, method: 'GET', data: params, ...options }),
  post: (url, data, options) => request({ url, method: 'POST', data, ...options }),
  put: (url, data, options) => request({ url, method: 'PUT', data, ...options }),
  del: (url, data, options) => request({ url, method: 'DELETE', data, ...options })
}
```

这一段里有五个设计，每个都能对应到前面学过的东西：

| 设计 | 解决什么问题 | 管理端对应物 |
| --- | --- | --- |
| 返回 Promise | 调用方能 `await`，能 `try/catch` | axios 天生就是 |
| `Authorization` 自动加 | 不用每个请求手动传 | 请求拦截器 |
| `code === 0` 判断收在一处 | 页面层不用重复写业务码判断 | 响应拦截器 |
| **`err.code = body.code`** | 业务码不丢，上层能按码分支 | 响应拦截器里 `reject` 带码 |
| `silent` 开关 | 有些错误要自己处理，不想弹两次 | 拦截器里的可配置项 |

**第四个是最容易漏的。** 管理端的 AI 协作节里提过这个坑，这里是它在真实代码里的样子：

```js
// ✗ 把业务码丢了：上层只知道“失败了”，不知道是哪种失败
reject(new Error(body.message))

// ✓ 把码挂回错误对象
const err = new Error(body.message)
err.code = body.code
err.data = body.data
reject(err)
```

有了码，页面层才能做这种判断：

```js
try {
  await http.post('/signups', payload)
  toast.success('报名已提交')
} catch (err) {
  if (err.code === 2005) {
    toast.error('名额刚好被抢完了')
    refreshDetail()        // 刷新名额显示
  } else if (err.code === 2006) {
    toast.error('已过报名截止时间')
    uni.navigateBack()
  } else {
    toast.error(err.message)
  }
}
```

**只拿到一句文案的写法做不到上面这些分支。**

## 三、api 层：按模块分文件

请求层管通用逻辑，具体接口写在 api 层。和管理端的组织方式保持一致：

```js [src/api/activity.js]
import { http } from '@/utils/request'

// 活动列表（只返回已发布、未下架的活动）
export function fetchActivityList(params) {
  return http.get('/activities', params)
}

// 活动详情
export function fetchActivityDetail(id) {
  return http.get('/activities/' + id)
}
```

```js [src/api/signup.js]
import { http } from '@/utils/request'

// 提交报名
export function createSignup(data) {
  return http.post('/signups', data)
}

// 我的报名列表
export function fetchMySignups(params) {
  return http.get('/signups/mine', params)
}

// 取消报名
export function cancelSignup(id) {
  return http.put('/signups/' + id + '/cancel')
}
```

```js [src/api/auth.js]
import { http } from '@/utils/request'

export function loginByPassword(data) {
  return http.post('/auth/login', data)
}

// 小程序登录：把 uni.login 拿到的 code 换成 token
export function loginByWeixin(code) {
  return http.post('/auth/weixin', { code })
}

export function fetchProfile() {
  return http.get('/auth/profile')
}

export function logout() {
  return http.post('/auth/logout')
}
```

**路径里不带 `/api`** —— 请求层会补上。这样将来换部署路径只需要改一个地方。

## 四、登录：两条路

用户端支持两种登录方式，对应两个平台。

### 路一：账号密码（H5 和调试时用）

```js
const res = await loginByPassword({ username, password })
// res 形如 { token, userInfo }
uni.setStorageSync('token', res.token)
uni.setStorageSync('userInfo', res.userInfo)
```

这条路管理端已经走过一遍，接口也是同一个。

### 路二：微信小程序一键登录

```js
// #ifdef MP-WEIXIN
async function loginByWeixinFlow() {
  // 第一步：拿 code。这一步不需要后端参与
  const { code } = await new Promise((resolve, reject) => {
    uni.login({
      provider: 'weixin',
      success: resolve,
      fail: reject
    })
  })

  // 第二步：把 code 交给后端，后端去换 openid 并签发 token
  const res = await loginByWeixin(code)
  uni.setStorageSync('token', res.token)
  uni.setStorageSync('userInfo', res.userInfo)
}
// #endif
```

::: danger 这个 code 不是身份凭证，也不能自己换 token
微信登录的完整链路是：

```
小程序 uni.login() → 拿到 code（临时、一次性、几分钟过期）
        ↓ 发给自己的后端
后端拿着 code + AppSecret 调微信接口 → 换到 openid / session_key
        ↓
后端签发自己的 token 返回给小程序
```

**两个必须记住的点：**

**一、`AppSecret` 只能放在后端。** 它是小程序的最高权限凭证，写进前端代码等于公开。**没有任何商量余地。**

**二、拿到 code 不等于登录成功。** code 只是“这个用户授权了小程序”的凭据，需要后端去换 openid 才知道是谁。**前端不能自己拼请求去调微信的接口**（也要用 AppSecret）。

**这一条对应单元 9 的结论：前端的判断不是安全边界。** 前端能拿到 code，但**能不能登录、登录成谁，由后端定**。
:::

## 五、token 存哪、怎么用

```js
// 存
uni.setStorageSync('token', token)

// 读（请求层里已经自动做了）
const token = uni.getStorageSync('token')

// 清
uni.removeStorageSync('token')
uni.removeStorageSync('userInfo')
```

`uni.setStorageSync` 在各平台对应的底层实现不同：小程序里是 `wx.setStorageSync`（有独立存储空间），H5 里是 `localStorage`。

::: warning 前端存 token 都不是绝对安全
三种存法的实际风险：

| 存法 | 风险 |
| --- | --- |
| H5 的 `localStorage` | 页面有 XSS 就能被读走 |
| 小程序的 storage | 相对隔离，但**小程序包被反编译后能看到结构** |
| 内存（不持久化） | 刷新就丢，用户每次都要重登 |

**没有一种能让你“放心”。** 正确的做法是接受它，然后在服务端补上防护：token 设短有效期、关键操作二次校验、异常登录检测。

**前端这一侧要做的是别帮倒忙**：不要 `console.log` 打印 token、不要拼进 URL、不要写进代码里。这几条和管理端的要求一样。
:::

## 六、没有全局路由守卫，那在哪判断登录

管理端用 `router.beforeEach` 统一拦。**uni-app 没有这个东西**，页面参数和跳转都不经过一个全局函数。

三种做法，从简单到复杂：

### 做法一：需要登录时才判断（本项目采用）

不登录也能浏览活动，只有点“报名”时才要求登录。写一个函数：

```js [src/utils/auth.js]
export function isLoggedIn() {
  return !!uni.getStorageSync('token')
}

/**
 * 确保已登录。未登录则跳登录页，返回 false
 */
export function ensureLogin() {
  if (isLoggedIn()) return true
  uni.showToast({ title: '请先登录', icon: 'none' })
  setTimeout(() => {
    uni.navigateTo({ url: '/pages/login/index' })
  }, 600)
  return false
}
```

用的时候：

```js
function handleSignup() {
  if (!ensureLogin()) return
  uni.navigateTo({ url: '/pages/signup/form?activityId=' + activity.value.id })
}
```

**这种做法最直白，也最好调试。** 缺点是每个需要登录的入口都要写一行 —— 而用户端只有“报名”“我的报名”“我的”三处，写三行不算负担。

### 做法二：拦截跳转

```js
uni.addInterceptor('navigateTo', {
  invoke(args) {
    if (args.url.includes('/pages/signup/form') && !isLoggedIn()) {
      uni.navigateTo({ url: '/pages/login/index' })
      return false        // 返回 false 阻止本次跳转
    }
  }
})
```

规矩集中在一处，但**要维护一份“哪些页面需要登录”的名单**，漏一个就是漏洞。

### 做法三：在每个页面的 `onLoad` 里判断

```js
onLoad(() => {
  if (!isLoggedIn()) {
    uni.redirectTo({ url: '/pages/login/index' })
    return
  }
  loadData()
})
```

适合整个页面都必须登录的情况（比如“我的报名”）。**注意用 `redirectTo` 而不是 `navigateTo`** —— 否则用户登录完返回，又会回到这个页面再被拦一次，卡在循环里。

**本项目三种混用**：“我的报名”页用做法三（整页需要登录），报名按钮用做法一，不做全局拦截。

## 七、把 401 处理接上

请求层留了一个钩子 `setUnauthorizedHandler`，要在应用启动时接上：

```js [src/main.js]
import { createSSRApp } from 'vue'
import App from './App.vue'
import { setUnauthorizedHandler } from '@/utils/request'

export function createApp() {
  const app = createSSRApp(App)

  setUnauthorizedHandler(() => {
    uni.removeStorageSync('token')
    uni.removeStorageSync('userInfo')
    uni.showToast({ title: '登录已过期，请重新登录', icon: 'none' })
    setTimeout(() => {
      uni.navigateTo({ url: '/pages/login/index' })
    }, 600)
  })

  return { app }
}
```

**为什么要用注入的方式，而不是在请求层直接 `import` 用户状态？** 因为 `main.js` 执行时应用还没挂载完，**在顶层 import 一个 Pinia store 会报“还没安装 Pinia”** —— 这个坑管理端也踩过（`request.js` 顶层不能调 `useUserStore()`），解法是同一个思路：**把依赖注入进来，不要在模块顶层做需要运行时环境的事。**

## 小结

- `uni.request` 是回调式的，**没有拦截器**，所以要在封装层自己造一套
- 请求层要解决五件事：Promise 化、自动加 token、统一判业务码、**把业务码挂回错误对象**、可关闭的自动提示
- api 层按模块分文件，**路径里不带 `/api`**，基础路径只在请求层定义一处
- 微信登录是“前端拿 code，后端换 token”，**`AppSecret` 绝不能出现在前端**
- **uni-app 没有全局路由守卫**，登录判断放在需要的地方，或用 `uni.addInterceptor`
- 401 用注入的方式接（`setUnauthorizedHandler`），**请求层不要在模块顶层 import store**

## 常见坑

::: details 请求发出去了，后端收到的是空参数

**现象：** `POST` 请求后端说参数为空，抓包看请求体是 `username=xxx&password=yyy` 这种表单格式。

**原因：** `uni.request` 会根据 `Content-Type` 决定怎么序列化 `data`。**没有显式设置 `Content-Type: application/json` 时，默认按表单格式发。**

**怎么处理：** 请求层的 `header` 里写死 `'Content-Type': 'application/json'`（上面的封装里已经这么做了）。**注意：如果不小心写成小写的 `content-type`，某些平台的实现会认不出来** —— HTTP 头本身大小写不敏感，但实现可能有差异，**统一用首字母大写的规范写法最保险。**

:::

::: details H5 端请求正常，小程序端报“不在合法域名列表中”

**现象：** 微信开发者工具里发请求失败，提示 `request:fail url not in domain list`。

**原因：** 微信小程序要求所有网络请求的域名必须在微信公众平台的白名单里。开发时用的 `localhost` 当然不在白名单里。

**怎么处理：** 开发阶段在开发者工具里关掉检查：**详情 → 本地设置 → 勾上“不校验合法域名、web-view（业务域名）、TLS 版本以及 HTTPS 证书”**。

也可以写在 `manifest.json` 里，让这个设置跟着项目走：

```json [src/manifest.json]
{
  "mp-weixin": {
    "setting": {
      "urlCheck": false
    }
  }
}
```

::: danger 上线前必须改回来
`urlCheck: false` 只是开发期的便利。**提交审核前要做两件事**：把它改成 `true`，并去微信公众平台把正式域名加进 `request` 合法域名列表（要求 HTTPS，不能带端口，不能是 IP）。

**忘了改的后果是：开发时一切正常，提交审核后所有接口都请求不到。**
:::

:::

::: details 用了 `async/await`，但错误提示弹了两次

**现象：** 一个接口出错，页面弹出两个一模一样的错误提示。

**原因：** 请求层在 `silent` 为 `false` 时自动弹了一次；页面层的 `catch` 里又弹了一次。

**怎么处理：** 明确分工。两种做法选一种，**别混着用**：

| 做法 | 请求层 | 页面层 |
| --- | --- | --- |
| A · 请求层统一提示（本项目默认） | 自动弹 | `catch` 里只处理需要特殊分支的情况 |
| B · 页面层统一提示 | 调用时传 `silent: true` | 每个 `catch` 里自己弹 |

简单页面用 A，逻辑复杂的用 B。**关键是团队内统一，不然同一个人隔两周写出两种风格。**

```js
// 做法 A：页面层只需要处理特殊码
catch (err) {
  if (err.code === 2005) refreshDetail()
  // 其他错误请求层已经提示过了，这里什么都不做
}

// 做法 B：页面层全权负责
const data = await http.get('/activities', params, { silent: true })
```

:::

::: details 401 之后跳到登录页，登录完返回却回到登录页

**现象：** token 过期，跳登录页；登录成功后返回，又立刻被跳到登录页。

**原因：** 登录页自己也被判断逻辑拦住了。或者跳登录用的 `navigateTo`，登录成功后 `navigateBack` 回到了那个已经失败的页面，页面又发了一次请求，又 401。

**怎么处理：**

1. **登录页要排除在拦截之外**（如果用做法二，名单里不要包含登录页）
2. **跳登录用 `navigateTo`，登录成功后用 `navigateBack` 回到原页并让原页重新请求**；或者跳登录前先记下当前页路径，登录后用 `redirectTo` 回去
3. **最简单可靠的做法：登录成功后用 `reLaunch` 回首页**，让用户重新走一遍流程。牺牲一点体验，换掉一整类难查的问题

:::

## 课后练习

**把请求层和登录链路搭起来，并用两个错误码验证分支处理。**

| 任务 | 要求 |
| --- | --- |
| 请求层 | 实现 `request` 与 `http.get/post/put/del` |
| 业务码 | 业务失败时，错误对象上要有 `code` 和 `data` |
| 提示 | 默认自动弹 Toast；传 `silent: true` 时不弹 |
| 401 | 收到 `code === 1001` 时清 token 并跳登录页 |
| api 层 | 至少写 `activity.js` 与 `signup.js` 两个文件 |
| 分支验证 | 在页面上做两个按钮：一个故意触发 `2005`（名额已满），一个触发 `2006`（已过截止时间），分别显示不同的提示 |
| 不许做的 | 不要在页面里直接用 `uni.request` |

::: details 验收标准与参考思路

**验收标准：**

| 项 | 要求 |
| --- | --- |
| 不重复提示 | 触发一个普通错误，只弹一次 Toast |
| 业务码可用 | `catch` 里能读到 `err.code`，不是 `undefined` |
| silent 生效 | 传 `silent: true` 时页面上不弹提示，但 `catch` 能拿到错误 |
| 401 链路 | 手动把 storage 里的 token 改成一个乱码，发请求后自动跳到登录页 |
| 无重复代码 | 页面里没有出现 `http://localhost:8080` 这串地址 |

**不合格的写法：**

```js
// ✗ 业务码丢了，上层只知道失败了
if (body.code !== 0) {
  uni.showToast({ title: body.message, icon: 'none' })
  reject(new Error(body.message))
}
```

上层 `catch` 到的 `err.message` 是一句文案，`err.code` 是 `undefined`。**“名额刚好被抢完”和“网络抖动”在代码里长得一模一样，没法区别对待。**

**另一个常见的不合格写法：**

```js
// ✗ 每个页面自己拼地址和 token
uni.request({
  url: 'http://localhost:8080/api/activities',
  header: { Authorization: 'Bearer ' + uni.getStorageSync('token') }
})
```

上线换域名时要全局搜索替换；某个页面忘了加 token 就是一个难查的 bug。

**合格的写法：**

```js
// 页面层：只管业务分支
async function handleSignup() {
  try {
    await createSignup({ activityId: activity.value.id, ...form })
    toast.success('报名已提交')
    uni.switchTab({ url: '/pages/signup/my' })
  } catch (err) {
    switch (err.code) {
      case 2005:
        toast.error('名额刚好被抢完了')
        await refreshDetail()          // 刷新名额，让用户看到真实情况
        break
      case 2006:
        toast.error('已过报名截止时间')
        uni.navigateBack()
        break
      case 3002:
        toast.error('你已报过名了')
        uni.switchTab({ url: '/pages/signup/my' })
        break
      default:
        toast.error(err.message)       // 其他情况用后端文案
    }
  }
}
```

**参考思路：**

两个地方值得多想一步：

**一是 401 之后要不要把用户正在做的事保住。** 用户填完报名表单，点提交，结果 token 过期跳走了 —— 回来表单是空的，体验很差。**改进办法是在跳登录前把表单数据暂存**，登录回来后恢复。

**二是 `silent` 什么时候用。** 判断标准是“这个错误要不要按不同情况分别处理”。需要的话传 `silent: true` 自己处理；只是弹个提示就完事的，让请求层统一弹。**别养成每个请求都传 `silent` 的习惯** —— 那等于放弃了统一提示的好处。

:::

---

上一节：[组件与组件库](/mobile/05-components) ·
下一节：[列表页与详情页](/mobile/07-list-detail)
