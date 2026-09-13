# 9.4 登录鉴权完整链路

## 把“登录”这件事从头到尾走一遍

9.3 讲了怎么用守卫拦住未登录用户。但“拦住”只是一条线，整件事其实有五个环节：

1. 用户填账号密码，点登录 —— 成功后，**凭证写在哪里**？
2. 用户按 F5 刷新 —— **怎么知道他还是登录状态**？
3. 凭证过期了，接口返回 401 —— **怎么处理**？
4. 被挡去登录页的用户登录成功后 —— **怎么回到他本来要去的页面**？
5. 用户点退出登录 —— **要清掉哪些东西**？

这五件事必须一起考虑，少一个都会出问题：

- 只做 1 不做 2，一刷新就退登，用户每次都要重新登录。
- 只做 1 不做 3，token 过期后页面显示一堆“加载失败”，用户不知道要重新登录。
- 只做 1 不做 4，用户想看活动 12，被挡去登录，登录完却被扔回首页，还得再点一次。
- 不做 5，退出后 token 还在本地，随便谁打开浏览器都能进后台。

这一节按顺序把五个环节讲清楚，最后把整条链路的时序画出来。

::: tip 这一节是本单元的核心
前面的路由表、动态参数、守卫都是零件。**这一节是把零件装成一台能用的机器。**

学完它，你就做出了课程要求的“带鉴权的页面骨架”。案例 10 会把它完整实现一遍。
:::

## 整条链路的时序

先看全景，再逐段看代码。

```text
【第一次打开应用】
  用户访问 /activities
    ↓
  main.js：创建 app、装上路由、mount
    ↓
  路由开始处理首次导航，进入 beforeEach
    ↓
  ┌─ 本地有 token 吗？
  │   没有 → 目标需要登录吗？
  │         需要 → 跳 /login?redirect=/activities
  │         不需要 → 放行
  │
  └─ 有 token → 用户信息加载过了吗？
      （用 ready 标记判断）
       没有 → 用 token 请求“当前用户信息”
              ├─ 成功 → 写入用户信息，ready = true，放行
              └─ 失败（401 / 过期）→ 清掉 token，跳 /login
       已经加载过 → 直接放行
    ↓
  导航确认，渲染目标页面
    ↓
  进入页面，正常请求业务接口
    ↓
  ┌─ 某个接口返回 401（token 过期）
  │    → 清掉 token 与用户信息
  │    → 跳 /login?redirect=当前地址
  └─ 其他错误 → 交给页面显示错误态

【登录】
  用户在 /login 填表单
    ↓
  提交：POST /api/login
    ├─ 失败 → 显示错误提示，停留在登录页
    └─ 成功 → 拿到 token
        → 存 token
        → 请求“当前用户信息”（或直接用返回的用户数据）
        → 写入用户信息，ready = true
        → 读 route.query.redirect，有就跳过去，没有就跳首页
        → 用 replace 而不是 push（不让用户后退回登录页）

【刷新页面】
  与“第一次打开应用”完全一样 —— 因为内存里的状态没了，只有 token 还在。
  这正是为什么登录恢复逻辑必须写在守卫里，而不是写在某个组件的 onMounted 里。

【退出登录】
  用户点退出
    ↓
  调退出接口（可选，让服务端失效 token）
    ↓
  清掉 token、用户信息、ready 标记
    ↓
  跳登录页，用 replace
```

这张图请对照下面的代码看两遍。**五个环节是连续的，不是五个独立的小功能。**

## 环节一：登录成功后把凭证写在哪里

服务端返回的 `token` 是后续请求的“身份证明”。存哪里有三种选择：

| 存储位置 | 到期行为 | 能否被 JS 读取 | 是否随请求自动带上 | 特点 |
| --- | --- | --- | --- | --- |
| `localStorage` | 手动清除，关浏览器还在 | 能 | 否，要手动加请求头 | 跨标签页共享；最常用 |
| `sessionStorage` | 关标签页就没了 | 能 | 否 | 每个标签页一份，适合“关掉即退登” |
| Cookie（`HttpOnly`） | 可设过期时间 | **不能**（更安全） | 是 | 最安全，但需要服务端设置，且要防 CSRF |

::: warning 前端拿到的 localStorage 里的 token，理论上不安全
`localStorage` 里的内容，页面上任何一个脚本都能读。如果页面被注入了恶意脚本（XSS），
token 就会被偷走。

**更安全的是服务端把 token 写进 `HttpOnly` Cookie** —— 这种 Cookie 浏览器会自动带上，
但 JavaScript 读不到，XSS 偷不走。代价是要处理跨站请求伪造（CSRF）。

课程项目用 `localStorage` 是**教学上的简化**：它简单、直观、便于调试。
但你要知道这个取舍，答辩时能说清“生产环境更推荐 HttpOnly Cookie”就够好。
:::

课程项目的做法：

```js [src/utils/token.js]
// token 的读写集中在一个文件里，将来换成别的存储方式只改这里
const KEY = 'campus-admin-token'

export function getToken() {
  return localStorage.getItem(KEY)
}

export function setToken(token) {
  localStorage.setItem(KEY, token)
}

export function clearToken() {
  localStorage.removeItem(KEY)
}
```

**为什么单独抽一个文件？** 因为将来如果要从 `localStorage` 换成 `Cookie`，
只需要改这一个文件，不用全局搜索替换。

::: tip 用 sessionStorage 还是 localStorage
判断依据：**“关掉浏览器再打开，还要不要保持登录？”**

- 校园管理端的老师，希望下次打开还在登录状态 → `localStorage`。
- 考试系统、公共电脑上的后台，希望关掉就退登 → `sessionStorage`。

课程项目用 `localStorage`。
:::

## 环节二：刷新页面后恢复登录态

### 为什么这是最容易做错的一步

刷新页面后，**内存里的所有状态都没了**，只剩 `localStorage` 里的 token。所以：

- 我们知道“有一个 token”，但**不知道它还有效吗**，也**不知道这个用户是谁、有什么权限**。
- 用户信息必须**用 token 去请求**才知道，这是一个**异步操作**。

于是就有了那个著名的问题：**页面是先渲染，还是先等校验结果？**

```text
如果先渲染再校验：
  用户刷新 /activities
  → 页面立刻渲染，此时 isLoggedIn = false
  → 界面闪一下“未登录” / 被踢到登录页
  → 200 毫秒后用户信息回来了，isLoggedIn = true
  → 又跳回 /activities
  结果：用户看到页面闪来闪去，体验很差。
```

```text
如果先校验再渲染：
  用户刷新 /activities
  → 导航被守卫挡住，什么都不渲染
  → 请求用户信息（期间显示空白或骨架）
  → 校验通过 → 渲染目标页面
  结果：干净的“等一下，然后出内容”。
```

### 解决办法：ready 标记 + 在守卫里恢复

核心是两件事：

1. 状态模块里加一个 `ready` 标记，表示“登录态是否已经确定”。
2. **在守卫里等待恢复完成**，因为守卫会阻塞导航 —— 导航没确认，页面就不会渲染。

```js [src/stores/auth.js]
import { ref, computed } from 'vue'
import { getToken, setToken, clearToken } from '@/utils/token'
import { loginApi, fetchCurrentUserApi } from '@/api/auth'

// 模块级状态：整个应用共享这一份
const token = ref(getToken())
const user = ref(null)
// ready 表示“登录态已经确定”：要么确认已登录，要么确认未登录
const ready = ref(false)

const isLoggedIn = computed(() => Boolean(token.value && user.value))
const role = computed(() => user.value?.role ?? null)
const permissions = computed(() => user.value?.permissions ?? [])

/** 登录：写 token 与用户信息 */
async function login(credentials) {
  const { token: newToken, user: userInfo } = await loginApi(credentials)
  token.value = newToken
  setToken(newToken)
  user.value = userInfo
  ready.value = true
}

/**
 * 恢复登录态：刷新页面后调用
 * 有 token 就去换用户信息；没有或已失效就清干净
 */
async function restore() {
  const saved = getToken()

  if (!saved) {
    // 没有 token，直接确定“未登录”
    user.value = null
    ready.value = true
    return
  }

  try {
    token.value = saved
    user.value = await fetchCurrentUserApi()
  } catch {
    // token 过期或无效，清干净
    logout()
  } finally {
    ready.value = true
  }
}

function logout() {
  token.value = null
  user.value = null
  clearToken()
  ready.value = true
}

export function useAuth() {
  return {
    token,
    user,
    ready,
    isLoggedIn,
    role,
    permissions,
    login,
    restore,
    logout
  }
}
```

守卫里等它：

```js [src/router/guards.js]
import { useAuth } from '@/stores/auth'

export function setupGuards(router) {
  router.beforeEach(async (to) => {
    const auth = useAuth()

    // ① 登录态还没确定，先恢复（只做一次）
    if (!auth.ready.value) {
      await auth.restore()
    }

    // ② 已经在登录页了，不再拦截，避免死循环
    if (to.name === 'login') {
      return auth.isLoggedIn.value ? { name: 'activity-list' } : true
    }

    // ③ 需要登录但没登录
    if (to.meta.requiresAuth !== false && !auth.isLoggedIn.value) {
      return { name: 'login', query: { redirect: to.fullPath } }
    }

    // ④ 角色不匹配 → 403
    const roles = to.meta.roles
    if (roles && !roles.includes(auth.role.value)) {
      return { name: 'forbidden' }
    }
  })
}
```

::: tip 为什么写在守卫里，而不是 App.vue 的 onMounted
`App.vue` 的 `onMounted` 触发时，**页面已经开始渲染了**。此时 `ready` 还是 `false`，
你会看到“未登录”的状态闪一下。

而**路由的首次导航同样是异步的**：`RouterView` 在导航被确认之前什么都不渲染。
把恢复逻辑放进 `beforeEach` 并 `await`，导航就会等它 —— 页面根本没机会渲染错误的状态。

这叫“**把异步的前置条件放在渲染之前**”。是处理这类问题时值得记住的一招。
:::

::: warning 恢复失败也可能因为网络问题
上面 `restore()` 里，`catch` 分支把请求失败统一当成“token 失效”处理了。
如果失败原因只是**网络断了**，用户会被莫名退登。

更严谨的写法要区分状态码：401 / 403 才退登，网络错误则保留 token、
让用户重试或进入离线状态。课程项目可以先按简单版做，
但**要知道这里有个取舍**，答辩时能说出来。
:::

## 环节三：401 之后怎么处理

token 有过期时间。用户挂着页面两小时不动，再点按钮时接口会返回 401。
这时不能让他对着一堆“加载失败”发呆 —— 要**清掉登录态并跳到登录页**。

这件事应该**在一个地方统一处理**，而不是每个页面各自判断。
如果用的是 axios，就放在响应拦截器里：

```js [src/api/request.js]
import axios from 'axios'
import router from '@/router'
import { useAuth } from '@/stores/auth'
import { getToken } from '@/utils/token'

const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 10000
})

// 请求拦截器：每次请求自动带上 token
request.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截器：统一处理 401
request.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const status = error.response?.status

    if (status === 401) {
      const auth = useAuth()
      auth.logout()

      // 带上当前地址，登录完能回来
      const current = router.currentRoute.value
      router.replace({
        name: 'login',
        query: { redirect: current.fullPath }
      })
    }

    return Promise.reject(error)
  }
)

export default request
```

这个文件是[单元 10 的请求层封装](/unit10/04-request-layer)的内容，这里先知道
**401 要统一处理**即可。

::: warning 别在拦截器里同时用 router 和守卫跳转
拦截器里的 `router.replace` 会触发一次新导航，顺带走过守卫 —— 这是正常的，
守卫会看到“要去登录页”并放行。

但要注意：**如果多个请求同时返回 401，会触发多次跳转。** 加一个防抖标记：

```js
let redirecting = false

if (status === 401 && !redirecting) {
  redirecting = true
  // …跳转
  // 跳转完成后（或延时后）把标记复位
  setTimeout(() => { redirecting = false }, 1000)
}
```
:::

## 环节四：登录后回到原来要访问的页面

用户在 `/activities/12` 被挡去登录，登录成功后应该回到 `/activities/12`，
而不是被扔到首页。这就是 `redirect` 参数的作用。

**去登录页时带上**（9.3 的守卫里已经写了）：

```js
return { name: 'login', query: { redirect: to.fullPath } }
```

**登录成功后读出来并用**：

```vue [src/views/LoginView.vue]
<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuth } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuth()

const form = ref({ username: '', password: '' })
const submitting = ref(false)
const errorMsg = ref('')

async function onSubmit() {
  submitting.value = true
  errorMsg.value = ''

  try {
    await auth.login(form.value)

    // 读 redirect，没有就回默认首页
    const redirect = route.query.redirect
    const target = typeof redirect === 'string' ? redirect : '/activities'

    // 用 replace：不让用户后退回到登录页
    await router.replace(target)
  } catch (e) {
    errorMsg.value = e.response?.data?.message || '登录失败，请检查账号密码'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <form class="login-form" @submit.prevent="onSubmit">
    <h1>校园活动服务平台 · 管理端</h1>

    <label>
      账号
      <input v-model.trim="form.username" autocomplete="username" />
    </label>

    <label>
      密码
      <input v-model="form.password" type="password" autocomplete="current-password" />
    </label>

    <p v-if="errorMsg" class="error">{{ errorMsg }}</p>

    <button type="submit" :disabled="submitting">
      {{ submitting ? '登录中…' : '登录' }}
    </button>
  </form>
</template>
```

::: warning redirect 要校验，不能直接用
`route.query.redirect` 来自地址栏，是**用户可控的输入**。如果直接 `router.replace(redirect)`，
有人构造一个 `?redirect=https://evil.com`，登录后就会被跳到外部站点 —— 这是开放重定向漏洞。

处理：**只接受站内路径**（以 `/` 开头、不以 `//` 开头），否则用默认地址：

```js
function safeRedirect(value, fallback = '/activities') {
  if (typeof value !== 'string') return fallback
  // 必须是以单个 / 开头的站内路径，排除 //evil.com 这种协议相对地址
  if (!value.startsWith('/') || value.startsWith('//')) return fallback
  return value
}
```

**凡是“地址里的值直接拿去跳转”，都要做这个校验。**
:::

## 环节五：退出登录要清哪些东西

退出登录不是只删一个 token。至少有四样：

```js [src/stores/auth.js（logout 完整版）]
function logout() {
  // 1. 内存里的凭证与用户信息
  token.value = null
  user.value = null

  // 2. 本地存储里的 token
  clearToken()

  // 3. ready 标记复位，下次守卫会重新走一遍恢复逻辑
  ready.value = true   // 这里保持 true，因为“已经确定是未登录”

  // 4. 其他和用户相关的缓存
  //    比如列表页的草稿、缓存的数据、表格的列设置
  clearUserCache()
}
```

| 要清的东西 | 为什么 |
| --- | --- |
| 内存里的 token 与用户信息 | 页面上的判断立刻生效 |
| `localStorage` 里的 token | 刷新后不会被恢复 |
| 其他用户相关的本地缓存 | 换一个账号登录时不应看到上一个人的草稿 |
| 请求层的默认请求头（如果缓存了 token） | 否则下一个请求还带着旧 token |

::: danger 退出登录不等于“用户找不到了”
前端退出只是清掉**浏览器这边的凭证**。服务端那边，那个 token 在过期之前
**理论上仍然有效** —— 如果它被别的脚本复制走了，还能继续用。

所以生产环境里，退出登录应该**同时调用服务端的“注销接口”**，
让服务端把这个 token 加进黑名单或直接失效。

课程项目里可以先只做前端清理，但**答辩时要能说清这个差别**。
:::

如果切换账号时不清理，会出现一个很尴尬的 bug：A 用户退出，B 用户登录，
B 看到了 A 留在本地存储里的活动草稿。**这类问题排查起来很费时间，不如一开始就清干净。**

## 小结

- 登录链路有五个环节：写凭证、恢复登录态、处理 401、登录后回原页面、退出清理，
  它们必须一起设计。
- token 存 `localStorage`（跨标签页、关浏览器还在）、`sessionStorage`（关标签页就退）、
  或 `HttpOnly` Cookie（最安全，JS 读不到，需服务端设置）。课程项目用第一种。
- **刷新后的时序问题是核心**：用户信息要异步请求，必须用 `ready` 标记 + 在守卫里
  `await` 恢复，让导航阻塞到登录态确定，页面才不会闪。
- 401 在响应拦截器里统一处理：清登录态 + 跳登录页 + 带 `redirect`；
  多个请求同时 401 要加防抖。
- 登录成功后读 `redirect` 跳回原地址，并用 `replace`；**`redirect` 必须校验是站内路径**。
- 退出要清：内存状态、本地 token、用户相关缓存、请求层缓存的请求头；
  生产环境还要调服务端注销接口。

## 常见坑

::: details 坑 1：刷新后页面闪一下再跳转
现象：刷新受限页面，先看到“未登录”或登录页，然后才稳定。

原因：恢复逻辑写在了组件挂载之后。

处理：把 `restore()` 放进 `beforeEach` 并 `await`；用 `ready` 标记保证只执行一次。
:::

::: details 坑 2：登录后一直跳回登录页，循环
现象：登录成功，但马上又被踢回登录页。

原因：可能是 `isLoggedIn` 的判断依赖了还没写入的 `user`，或者守卫里无条件跳转。

处理：登录时**先把 token 和 user 都写好再跳转**；守卫里跳转前判断 `to.name`。
:::

::: details 坑 3：401 之后停在原页面
现象：接口报 401，页面显示“加载失败”，用户不知道要重新登录。

原因：没有统一的 401 处理。

处理：在请求拦截器里统一处理，跳登录页并带 `redirect`。
:::

::: details 坑 4：`redirect` 被用来跳外站
现象：`?redirect=https://evil.com` 登录后被跳到外部站点。

原因：直接信任了地址栏的值。

处理：只接受以单个 `/` 开头的站内路径，其余一律用默认地址。
:::

::: details 坑 5：切换账号后还能看到上一个账号的草稿
现象：B 登录后看到 A 的未保存内容。

原因：退出时只清了 token，没清用户相关的本地缓存。

处理：退出时清所有带用户维度的缓存（可以给这些 key 统一加前缀，退出时按前缀清理）。
:::

## 课后练习

::: details 练习 1：实现带 ready 标记的恢复逻辑
写一个 `useAuth`，包含 `login`、`restore`、`logout`，以及 `ready` / `isLoggedIn` / `role`。
在守卫里调用 `restore`，验证刷新页面时不闪登录页。

**思路**：先不写 UI，只写模块和守卫，用 `console.log` 观察 `ready` 的变化顺序。
确认“导航被阻塞”这个行为真的发生了。
:::

::: details 练习 2：接上 401 处理
实现请求拦截器：请求带上 token，响应 401 时清登录态并跳登录页带 `redirect`。
用一个会返回 401 的假接口测试。

**思路**：注意多请求同时 401 的防抖。测试方法：页面上同时发三个请求，看是不是只跳一次。
:::

::: details 练习 3：校验 redirect
实现 `safeRedirect`，用 `/activities`、`//evil.com`、`https://evil.com`、
`/activities/12?tab=signup`、`undefined` 五个输入测试。

**思路**：只有以单个 `/` 开头的才算站内路径。写完想想还有没有别的绕过方式
（提示：`/\evil.com` 在某些浏览器里的行为）。
:::

---

上一节：[9.3 路由守卫](/unit09/03-guards) ·
下一节：[案例 10 · 登录与鉴权](/unit09/05-case-auth)
