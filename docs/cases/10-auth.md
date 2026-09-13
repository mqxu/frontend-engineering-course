# 案例 10 · 登录鉴权

## 案例要做什么

前九个案例做的页面，都是打开就能看的。这个案例给整套管理端装上门：**没登录的人看不到任何业务页面，登录了的人只能看到自己该看的东西。**

平台有两个角色：

| 角色 | 能做什么 |
| --- | --- |
| 活动组织者（`organizer`） | 发布活动、安排场次与场地、查看自己活动的报名情况 |
| 审核员（`reviewer`） | 审核报名记录、驳回并填写理由、查看全部活动，但不能修改活动内容 |

要接起来的链路有八段，从打开页面一直到退出登录：

1. 打开任意业务页面，发现没登录，**跳去登录页**，并且记住原本想去哪。
2. 登录成功后拿到 token，**存起来**，再跳回原来那个页面。
3. 之后每个请求都自动带上 token，不用每个接口手写一遍。
4. 刷新页面，**登录状态不能丢**，也不能闪一下登录页。
5. 服务端说 token 过期（返回 401），**自动登出**并跳回登录页，而不是卡在一个报错的页面上。
6. 菜单按角色显示，组织者看不到“报名审核”，审核员看不到“场次与场地”。
7. 页面里的按钮也按角色控制，审核员看不到“编辑活动”。
8. 点“退出登录”，**本地状态和存储都清干净**，再跳回登录页。

做完之后可以这样自查，每一条都能在浏览器里手动验证：

- 清空浏览器数据后直接访问 `/activities`，会跳到登录页，地址栏带着 `?redirect=/activities`。
- 用组织者账号登录，登录后自动回到 `/activities`，顶栏显示姓名和角色。
- 按 F5 刷新，页面直接是业务页，不会闪一下登录页。
- 点“退出登录”，回到登录页；按浏览器后退键，回不到业务页（守卫会再拦一次）。
- 用审核员账号登录，菜单里没有“活动管理”，页面上也没有“新建活动”按钮。
- 打开 DevTools 的 Application 面板，能看到 token 存在 `sessionStorage` 里；勾选“记住我”再登录，token 会跑到 `localStorage` 里。
- 在 Application 面板里手动把 token 改成一个乱码，刷新页面，会停在登录页而不是报错的业务页。

### 用到的知识点 → 对应章节

| 用到的知识点 | 对应章节 |
| --- | --- |
| Pinia 的定义与使用 | [10.2 Pinia 两种写法](/unit10/02-pinia-basics) |
| 什么时候该用全局状态 | [10.1 什么时候需要全局状态](/unit10/01-when-global) |
| 请求层封装与拦截器 | [10.4 请求层封装](/unit10/04-request-layer) |
| 错误分层处理 | [10.5 错误分层处理](/unit10/05-error-handling) |
| 路由基础与命名路由 | [9.1 路由基础](/unit09/01-router-basics) |
| 路由守卫 `beforeEach` | [9.3 路由守卫](/unit09/03-guards) |
| 登录鉴权完整链路 | [9.4 登录鉴权完整链路](/unit09/04-auth-flow) |
| 自定义指令 | [8.5 自定义指令](/unit08/05-directives) |
| 应用启动与插件安装 | [2.4 构建工具与 Vite](/unit02/04-vite) |

::: danger 先说清楚一件事
**前端做角色控制，只是“体验”，不是“安全”。**

用户可以按 F12 改 DOM 把隐藏的按钮显示出来，也可以用 Postman 直接调接口 —— 页面里所有 `v-if` 和指令都拦不住这两件事。所以：**每一个接口都必须在服务端校验“你是谁、你能不能做这件事”**，前端控制的作用只是让界面别显示用户用不了的东西。

把这句话记住，后面所有代码的理解都会顺。看到“前端隐藏了按钮”，永远不要在脑子里翻译成“用户做不了这件事”。
:::

## 数据结构与接口设计

### 用户对象

登录接口返回的东西很少，够用就行：

```js [登录成功后拿到的数据]
{
  token: 'eyJhbGciOiJIUzI1NiIs...',
  user: {
    id: 12,
    name: '李思远',
    account: 'lisy',
    role: 'organizer',        // organizer | reviewer
    orgName: '计算机学院学生会',
    avatar: ''
  }
}
```

**token 和用户信息分开存。** token 存进浏览器存储，用户信息只放在 Pinia 里、刷新后用接口重新拉。原因在下一步细讲。

### 存储的取舍：localStorage 还是 sessionStorage

这是登录功能第一个要做的决定，两个选项的差别不只是“会不会过期”：

| 存储 | 生命周期 | 适合的场景 | 风险 |
| --- | --- | --- | --- |
| `localStorage` | 一直保留，除非用户清除或代码删除 | 勾选了“记住我” | 同一台电脑上的下一个人打开就是登录态 |
| `sessionStorage` | 关闭标签页就失效 | 没勾“记住我”，公共场所用 | 关标签页就要重新登录 |
| `httpOnly` Cookie | 由服务端设置 | 安全性要求高的系统 | 需要后端配合，还要处理跨站请求伪造 |

`localStorage` 和 `sessionStorage` 有一个共同的弱点：**JavaScript 能读到它们，所以一旦页面被注入恶意脚本（XSS），token 就会被偷走。** `httpOnly` Cookie 恰好能防住这一点（脚本读不到），但它需要后端在响应头里设置，还要额外处理 CSRF 防护。

本案例的做法是：**“记住我”勾选时用 `localStorage`，没勾选用 `sessionStorage`。** 这是教学项目里的合理折中，但你必须在报告或答辩里说清它的风险 —— **存储方案是安全决策，不是随手写一行代码。**

### token 存在哪、用户信息存在哪

| 数据 | 存哪 | 为什么 |
| --- | --- | --- |
| token | `localStorage` 或 `sessionStorage` | 刷新页面后还要用，只能落在浏览器存储里 |
| 用户信息（姓名、角色） | 只放 Pinia | 可能过期、可能被后台改动，刷新后重新拉最可靠 |
| “角色”这类派生值 | Pinia 里的 `computed` | 不要存两份，否则改一处忘一处 |

**千万不要把用户信息和 token 一起塞进 `localStorage` 就当缓存用。** 角色改动后，旧缓存会让用户在界面上继续看到不该看到的菜单，直到手动清理浏览器数据。用户信息只有一个来源：**服务端接口**。

### Pinia Store 的形状

```js [src/stores/user.js 对外暴露的内容]
{
  token,        // ref，当前 token
  profile,      // ref，用户信息对象或 null
  isLoggedIn,   // computed，是否已登录
  role,         // computed，'organizer' | 'reviewer' | ''
  displayName,  // computed，用于顶栏显示
  login,        // 登录
  restore,      // 用本地 token 拉一次用户信息
  logout,       // 退出
  clear         // 只清状态，不发请求
}
```

### 路由的 meta 约定

路由表里用 `meta` 描述“这条路由需要什么条件”，守卫统一按这份描述判断。

```js [src/router/index.js 里的 meta 写法]
{ path: '/activities', meta: { requiresAuth: true, roles: ['organizer'] } }
{ path: '/reviews', meta: { requiresAuth: true, roles: ['reviewer'] } }
{ path: '/dashboard', meta: { requiresAuth: true } }   // 两种角色都能看
{ path: '/login', meta: { requiresAuth: false } }
```

`roles` 不写表示“登录即可访问”。**把权限规则写在路由表里，而不是散落在各个页面的 `onMounted` 里**，这样一眼就能看清整个系统的权限分布。

### 接口约定

```js [src/api/auth.js]
import request from './request'

// 登录：成功返回 { token, user }
export function loginApi(payload) {
  return request.post('/api/auth/login', payload)
}

// 用当前 token 换取用户信息
export function fetchProfileApi() {
  return request.get('/api/auth/profile')
}

// 退出：通知服务端把 token 作废
export function logoutApi() {
  return request.post('/api/auth/logout')
}
```

## 实现步骤

### 第一步：token 的读写封装

token 的读写要集中在一个文件里，因为**取的时候要按优先级查两处，清的时候要两处都清**。散落各处早晚会漏。

```js [src/utils/token.js]
const TOKEN_KEY = 'campus-admin-token'

export function getToken() {
  // 先查长效存储，再查会话存储：勾了“记住我”的会存在前面那个
  return localStorage.getItem(TOKEN_KEY) || sessionStorage.getItem(TOKEN_KEY) || ''
}

export function setToken(token, remember = false) {
  // 先把两处都清掉，避免旧值残留在另一个存储里
  removeToken()
  const storage = remember ? localStorage : sessionStorage
  storage.setItem(TOKEN_KEY, token)
}

export function removeToken() {
  localStorage.removeItem(TOKEN_KEY)
  sessionStorage.removeItem(TOKEN_KEY)
}
```

::: warning 别忘了 `removeToken` 里的第二行
只清 `localStorage` 是个很典型的疏忽：用户先勾了“记住我”登录，退出，再取消勾选登录一次，看起来正常；但下次打开浏览器仍然是登录态 —— 因为第一次的 `localStorage` 值从来没被清掉。

**“写的时候只写一处，清的时候两处都清”**，这条规则在处理多种存储介质时几乎总是对的。
:::

::: warning token 里不要放敏感信息
很多项目用的是 JWT。要记住一件事：**JWT 的载荷部分是 Base64 编码的，不是加密的。** 随便找个在线工具粘贴进去就能看到里面的内容。

所以：

- 不要把手机号、身份证号、家庭住址这类信息塞进 token。
- **不要在 token 里放“这个用户是管理员”这类可以决定权限的字段然后前端自己解析** —— 前端解析出来的角色是用户随手就能改的，角色必须以服务端每次请求返回的结果为准。
- token 的有效期要短。有效期越长，泄露之后的影响越大。这也是“自动续期”这类机制存在的意义。

**判断标准：这段内容如果被一个陌生人看到，会不会造成损失？会就不要放。**
:::


### 第二步：用户 Store

Store 只做三件事：维护状态、发请求、更新状态。**它不碰路由，也不碰界面** —— 这是它能被路由、被请求层、被组件同时安全使用的前提。

```js [src/stores/user.js]
import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { loginApi, fetchProfileApi, logoutApi } from '@/api/auth'
import { getToken, setToken, removeToken } from '@/utils/token'

export const useUserStore = defineStore('user', () => {
  // 初始值直接读本地存储：刷新后第一帧就已经是“已登录”状态
  const token = ref(getToken())
  const profile = ref(null)

  const isLoggedIn = computed(() => Boolean(token.value))
  const role = computed(() => profile.value?.role ?? '')
  const displayName = computed(() => profile.value?.name ?? '')

  /**
   * @param {{ account: string, password: string }} payload
   * @param {boolean} remember 是否写入 localStorage
   */
  async function login(payload, remember = false) {
    const data = await loginApi(payload)
    token.value = data.token
    profile.value = data.user
    setToken(data.token, remember)
    return data
  }

  // 用本地 token 换取用户信息。token 失效时清掉本地状态
  async function restore() {
    if (!token.value) return
    try {
      profile.value = await fetchProfileApi()
    } catch {
      // 这里不要弹提示、不要跳路由：启动阶段由调用方决定怎么处理
      clear()
    }
  }

  async function logout() {
    try {
      // 通知服务端作废 token。失败也要继续清本地，不能卡在登录态
      await logoutApi()
    } catch {
      // 故意留空：退出登录不允许失败
    }
    clear()
  }

  function clear() {
    token.value = ''
    profile.value = null
    removeToken()
  }

  return {
    token,
    profile,
    isLoggedIn,
    role,
    displayName,
    login,
    restore,
    logout,
    clear
  }
})
```

`token` 的初始值写成 `ref(getToken())` 而不是 `ref('')`，可以省掉一次“先渲染成未登录、再变成已登录”的闪烁。**能用初始化就确定的初始值，就不要留到之后再去赋。**

::: tip Store 不要 import 路由
如果 `stores/user.js` 里写 `import router from '@/router'`，就会出现循环依赖：路由文件要用 Store 做守卫，Store 又要用路由做跳转，两边互相等对方先加载完。

**正确做法：Store 只管状态，跳转交给调用方。** 登录成功后由登录页跳转，401 之后由注册好的回调跳转。这也是为什么本案例里有一个单独的 `auth-events.js`。
:::

### 第三步：请求层带 token 与 401 处理

请求拦截器负责两件事：每个请求自动带上 `Authorization` 头；响应是 401 时通知外面“该登出了”。

```js [src/api/request.js]
import axios from 'axios'
import { getToken } from '@/utils/token'
import { emitUnauthorized } from './auth-events'

const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 10000
})

request.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    // Bearer 是约定俗成的格式，具体前缀以接口文档为准
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

request.interceptors.response.use(
  (response) => response.data.data,
  (error) => {
    const status = error.response?.status

    // 401：token 缺失、过期或无效。交给外部统一处理
    if (status === 401) {
      emitUnauthorized()
      return Promise.reject(new Error('登录已过期，请重新登录'))
    }

    const message = error.response?.data?.message || '网络异常，请稍后重试'
    return Promise.reject(new Error(message))
  }
)

export default request
```

```js [src/api/auth-events.js]
// 一个极小的发布订阅：请求层只负责“报告发生了什么”，不关心谁来处理
let unauthorizedHandler = null

export function onUnauthorized(handler) {
  unauthorizedHandler = handler
}

export function emitUnauthorized() {
  unauthorizedHandler?.()
}
```

为什么不直接在 `request.js` 里 `import router`？因为会形成循环依赖链：`request.js` → `router` → 页面组件 → `api` → `request.js`。模块之间的循环引用在不同打包顺序下表现不一样，有时报错、有时静默失效，非常难查。

用这个十来行的 `auth-events.js` 把两边解开：**请求层只管发信号，谁需要谁来订阅。** 这个模式在工程里很常见，名字叫“事件总线”或者“回调注册”，本质就是不要让底层模块依赖上层模块。

::: tip 401 和 403 不是一回事
HTTP 状态码里有两个很容易混的：

| 状态码 | 含义 | 前端该怎么反应 |
| --- | --- | --- |
| 401 Unauthorized | **你是谁，我不知道。** token 缺失、过期、无效 | 清登录态，跳回登录页 |
| 403 Forbidden | **我知道你是谁，但你不能做这件事。** 已登录，角色或数据权限不够 | 提示“没有权限”，**不要登出** |

本案例的拦截器只对 401 做登出。如果顺手把 403 也当成 401 处理，就会出现这样的事：审核员点了某个组织者才能用的操作，结果整个人被踢出登录 —— 这是很严重的体验事故。

**判断方法：先问“这次失败和身份有关还是和权限有关”，再决定要不要清登录态。** 后端设计接口时也应该严格区分这两个码。
:::


::: details 401 也有可能出现在“正在登录”的时候
如果账号密码错误，登录接口返回 401，这个拦截器一样会触发 `emitUnauthorized()`，把用户“登出”一次 —— 虽然此时他本来就还没登录。

这看起来无害，但如果处理函数里写了“跳转到登录页”，就会出现一个尴尬的场面：用户在登录页输错密码，页面刷新了一下，输入的内容没了。

**处理办法是在处理函数里判断当前路由**：已经在登录页就什么都不做。下面的 `main.js` 就是这么写的。
:::

### 第四步：路由守卫

守卫的判断逻辑只有三条，写在 `beforeEach` 里：

```js [src/router/index.js]
import { createRouter, createWebHistory } from 'vue-router'
import { pinia } from '@/stores'
import { useUserStore } from '@/stores/user'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { requiresAuth: false }
    },
    {
      path: '/',
      component: () => import('@/layouts/AdminLayout.vue'),
      meta: { requiresAuth: true },
      children: [
        {
          path: 'dashboard',
          name: 'dashboard',
          component: () => import('@/views/DashboardView.vue')
        },
        {
          path: 'activities',
          name: 'activities',
          component: () => import('@/views/ActivityListView.vue'),
          meta: { requiresAuth: true, roles: ['organizer'] }
        },
        {
          path: 'reviews',
          name: 'reviews',
          component: () => import('@/views/ReviewListView.vue'),
          meta: { requiresAuth: true, roles: ['reviewer'] }
        },
        {
          path: 'forbidden',
          name: 'forbidden',
          component: () => import('@/views/ForbiddenView.vue')
        }
      ]
    }
  ]
})

router.beforeEach((to) => {
  const userStore = useUserStore(pinia)

  // 1. 需要登录但没登录：记住原本要去哪，登录后能跳回来
  if (to.meta.requiresAuth !== false && !userStore.isLoggedIn) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }

  // 2. 已经登录了还去登录页：直接送到首页，不用再登一次
  if (to.name === 'login' && userStore.isLoggedIn) {
    return { name: 'dashboard' }
  }

  // 3. 角色不匹配：送到无权限页，不是登录页
  const allowedRoles = to.meta.roles
  if (allowedRoles && allowedRoles.length > 0 && !allowedRoles.includes(userStore.role)) {
    return { name: 'forbidden' }
  }

  return true
})

export default router
```

有三处细节值得说明。

**`to.meta.requiresAuth !== false` 而不是 `to.meta.requiresAuth === true`。** 两者含义不同：前者是“默认需要登录，除非明确写了不需要”，后者是“默认公开，必须明确写需要”。安全相关的默认值应该选前者 —— **忘记写 `meta` 的后果是“多要求一次登录”，而不是“把页面暴露出去”。**

**第二段判断不能省。** 已登录用户访问 `/login`，如果不重定向，他会看到一个登录表单，填完又登录一次，结果覆盖掉当前会话。这种“多余的操作入口”应该在路由层就堵住。

**角色不匹配跳的是 `/forbidden` 而不是 `/login`。** 用户明明登录了，你把他扔回登录页，他会以为登录失效了，反复重新登录。**给一个“你没有权限”的页面，比让他怀疑人生好得多。**

### 第五步：刷新页面恢复登录态

刷新之后 Pinia 是全新的，`profile` 是 `null`，但 `token` 还在。所以启动时必须**先用 token 拉一次用户信息，再挂载应用**。

```js [src/main.js]
import { createApp } from 'vue'
import App from './App.vue'
import { pinia } from './stores'
import router from './router'
import { useUserStore } from './stores/user'
import { onUnauthorized } from './api/auth-events'
import { permission } from './directives/permission'
import './assets/main.css'

async function bootstrap() {
  const app = createApp(App)
  app.use(pinia)
  app.directive('permission', permission)

  const userStore = useUserStore(pinia)

  // 注册 401 的统一处理：清状态 + 跳登录页
  onUnauthorized(async () => {
    userStore.clear()
    const current = router.currentRoute.value
    // 已经在登录页就不要再跳了，否则输入内容会被清掉
    if (current.name === 'login') return
    await router.replace({
      name: 'login',
      query: { redirect: current.fullPath }
    })
  })

  // 关键：先恢复登录态，再挂载
  await userStore.restore()

  app.use(router)
  await router.isReady()
  app.mount('#app')
}

bootstrap()
```

```js [src/stores/index.js]
import { createPinia } from 'pinia'

// 单独导出 pinia 实例：在组件之外（守卫、指令、启动脚本）也能拿到同一个实例
export const pinia = createPinia()
```

为什么要把 `pinia` 单独导出？因为 `useUserStore()` 在组件外面调用时，必须显式传 pinia 实例。守卫里、自定义指令里、启动脚本里都不在组件的 `setup` 上下文中，不传实例就可能拿到 `undefined` 或者另外一个实例。

::: warning 不要在 `setup` 里发起恢复请求
一个常见的写法是在 `App.vue` 的 `onMounted` 里调 `userStore.restore()`，然后 `main.js` 直接 `app.mount()`。这样会有一个问题：**挂载和恢复是并行的，守卫可能先跑，看到 `isLoggedIn` 是 `false`，于是把用户踢到登录页**，然后恢复请求回来了，用户又被弹回业务页 —— 表现就是“刷新页面时闪一下登录页”。

正确做法就是本文这样：**`await restore()` 之后再 `mount`。** 页面会多等一个请求的时间（通常几十毫秒），但登录态是确定的。**宁可多等一会儿，也不要让界面先给出一个错误的判断。**
:::

### 第六步：按角色控制界面

菜单用 `computed` 过滤，这是最干净的做法：

```js [src/layouts/AdminLayout.vue（菜单）]
<script setup>
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const { role, displayName } = storeToRefs(userStore)

const MENUS = [
  { name: 'dashboard', title: '数据看板', roles: ['organizer', 'reviewer'] },
  { name: 'activities', title: '活动管理', roles: ['organizer'] },
  { name: 'reviews', title: '报名审核', roles: ['reviewer'] },
  { name: 'sessions', title: '场次与场地', roles: ['organizer'] }
]

// 只渲染当前角色能进的那几项
const visibleMenus = computed(() =>
  MENUS.filter((menu) => menu.roles.includes(role.value))
)

async function handleLogout() {
  await userStore.logout()
  // 退出后回登录页。不要带 redirect，不然登录完又跳回刚才那个页面
  router.replace({ name: 'login' })
}
</script>

<template>
  <aside class="layout">
    <nav>
      <RouterLink v-for="menu in visibleMenus" :key="menu.name" :to="{ name: menu.name }">
        {{ menu.title }}
      </RouterLink>
    </nav>

    <footer>
      <span>{{ displayName }}（{{ role === 'organizer' ? '活动组织者' : '审核员' }}）</span>
      <button type="button" @click="handleLogout">退出登录</button>
    </footer>
  </aside>
</template>
```

页面里的按钮控制有两种做法，各有各的适用场景。

**做法一：`v-if` 直接判断。** 显式、一眼能看懂、天然响应式。

```vue [src/views/ActivityListView.vue]
<script setup>
import { storeToRefs } from 'pinia'
import { useUserStore } from '@/stores/user'

const { role } = storeToRefs(useUserStore())
</script>

<template>
  <div class="page-actions">
    <!-- ✓ 只有活动组织者能新建活动 -->
    <button v-if="role === 'organizer'" type="button" @click="goCreate">新建活动</button>
    <button v-if="role === 'organizer'" type="button" @click="batchOffline">批量下架</button>
  </div>
</template>
```

**做法二：自定义指令。** 把判断抽出来，页面里只写“需要什么角色”，适合按钮很多、判断条件重复的场景。

```js [src/directives/permission.js]
import { useUserStore } from '@/stores/user'
import { pinia } from '@/stores'

function check(el, binding) {
  const userStore = useUserStore(pinia)
  // 允许写字符串，也允许写数组
  const allow = Array.isArray(binding.value) ? binding.value : [binding.value]
  const allowed = allow.includes(userStore.role)

  // 用 display 控制而不是删掉节点：权限变化时还能恢复
  el.style.display = allowed ? '' : 'none'
}

export const permission = {
  mounted: check,
  // 指令的 updated 必须写：角色变化后要重新判断
  updated: check
}
```

```vue [src/views/ActivityListView.vue（指令写法）]
<template>
  <div class="page-actions">
    <button v-permission="'organizer'" type="button" @click="goCreate">新建活动</button>
    <button v-permission="['organizer', 'reviewer']" type="button" @click="exportList">
      导出名单
    </button>
  </div>
</template>
```

两种做法的对比：

| 维度 | `v-if` | 自定义指令 |
| --- | --- | --- |
| 可读性 | 好，判断就在模板里 | 需要知道指令做了什么 |
| 复用 | 每个按钮写一遍 | 一行搞定 |
| 响应性 | 天然支持 | 必须实现 `updated` 钩子 |
| 隐藏方式 | 不渲染节点 | 仍在 DOM 里，只是 `display: none` |
| 调试 | 直观 | 需要翻指令定义 |

::: warning 自定义指令最容易漏的是 `updated`
只写 `mounted` 的指令，在首次渲染时判断一次就完事了。如果用户在不刷新页面的情况下切换了角色（比如测试环境有个“切换身份”按钮），按钮的显示不会更新，因为 `mounted` 不会再执行。

**判断型的指令，`mounted` 和 `updated` 两个钩子都要写，而且应该调同一个 `check` 函数。** 这是很容易漏掉的一条。
:::

**选哪个？** 一个页面里只有两三个按钮用 `v-if`，一眼就能读懂谁在控制什么；同一个判断在十几个地方重复出现，才值得抽成指令。**不要为了“看起来高级”就把所有权限判断都塞进指令** —— 指令是隐式的，读模板的人看不到它的逻辑。

## 完整代码

目录结构：

```text [src/]
src/
├── api/
│   ├── auth.js
│   ├── auth-events.js
│   └── request.js
├── directives/
│   └── permission.js
├── layouts/
│   └── AdminLayout.vue
├── router/
│   └── index.js
├── stores/
│   ├── index.js
│   └── user.js
├── utils/
│   └── token.js
├── views/
│   ├── LoginView.vue
│   ├── DashboardView.vue
│   ├── ForbiddenView.vue
│   └── ActivityListView.vue
├── App.vue
└── main.js
```

登录页：

```vue [src/views/LoginView.vue]
<script setup>
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { toast } from '@/composables/useToast'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const form = reactive({
  account: '',
  password: '',
  remember: false
})
const submitting = ref(false)

async function handleSubmit() {
  if (!form.account.trim() || !form.password) {
    toast.warning('请输入账号和密码')
    return
  }

  submitting.value = true
  try {
    await userStore.login(
      { account: form.account.trim(), password: form.password },
      form.remember
    )
    toast.success('登录成功')

    // 回到被拦下来之前想去的页面；没有就回首页
    const redirect = route.query.redirect
    await router.replace(typeof redirect === 'string' ? redirect : { name: 'dashboard' })
  } catch (error) {
    toast.error(error.message)
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="login">
    <form class="login__card" @submit.prevent="handleSubmit">
      <h1>校园活动服务平台 · 管理端</h1>

      <label>
        <span>账号</span>
        <input v-model.trim="form.account" autocomplete="username" />
      </label>

      <label>
        <span>密码</span>
        <input v-model="form.password" type="password" autocomplete="current-password" />
      </label>

      <label class="login__remember">
        <input v-model="form.remember" type="checkbox" />
        <span>记住我（在这台电脑上保持登录）</span>
      </label>

      <button type="submit" :disabled="submitting">
        {{ submitting ? '登录中…' : '登录' }}
      </button>
    </form>
  </div>
</template>
```

`App.vue` 保持最简，只放出口：

```vue [src/App.vue]
<template>
  <RouterView />
  <ToastHost />
</template>
```

其余文件（`api/*`、`utils/token.js`、`stores/*`、`router/index.js`、`directives/permission.js`、`main.js`、`AdminLayout.vue`）的完整内容就是上面实现步骤里给出的版本，不再重复。

跑起来之后的效果：直接访问 `/activities` 会被送到登录页，地址栏带着 `?redirect=/activities`；登录成功后自动回到活动列表；顶栏显示“李思远（活动组织者）”，菜单里没有“报名审核”；用审核员账号登录，看到的菜单只有“数据看板”和“报名审核”，页面里也没有“新建活动”按钮；故意把 token 改坏再刷新，会先恢复失败、然后停在登录页；点退出登录，本地存储清空，回到登录页。

## 常见坑

::: details 坑 1：刷新页面时闪一下登录页
**现象**：登录状态下按 F5，先看到登录页，半秒后才跳到业务页。

**原因**：应用先挂载了，Pinia 里的 `profile` 还是 `null`，守卫看到“未登录”就跳了；等 `restore()` 的请求回来，又把用户送回业务页。

**怎么处理**：`await userStore.restore()` 之后再 `app.mount()`。如果请求慢，宁可显示一个全局的加载态，也不要先挂载再纠正。**界面给出的第一个判断必须是正确的。**
:::

::: details 坑 2：401 处理里出现死循环
**现象**：token 过期后页面疯狂跳转，控制台里 401 一个接一个。

**原因**：401 处理器跳转到登录页，而登录页本身的某个请求（比如获取验证码）也返回 401，又触发一次跳转，循环往复。

**怎么处理**：两件事。一是在处理器里判断“已经在登录页就什么都不做”；二是加一个 `redirecting` 标记，正在跳转中的请求直接忽略。**处理全局异常时，第一件要想的事是“这个处理本身会不会再触发自己”。**
:::

::: details 坑 3：登录成功后跳转用了 `location.href`
**现象**：登录成功，页面刷新了一下，登录态要重新恢复一次，慢。

**原因**：`window.location.href = '/dashboard'` 是整页跳转，会重新加载 HTML、重新执行所有 JS。

**怎么处理**：用 `router.replace()`。它只切换组件，不刷新页面。**只有在真的需要“彻底重来一次”的场合（比如切换账号后清缓存）才用整页跳转。** 本案例里退出登录也用 `router.replace`，因为 Store 和存储都已经清干净了。
:::

::: details 坑 4：`redirect` 参数没用上，登录后总是回首页
**现象**：用户想访问“报名审核”，被拦到登录页；登录成功后回到了数据看板，还得再点一次菜单。

**怎么处理**：守卫里把 `to.fullPath` 写进 `query.redirect`，登录成功后读出来跳回去。注意 `route.query.redirect` 的类型可能是字符串、可能是数组，**取用前要判断类型**，别直接塞进 `router.replace()`。

另外还有一个小坑：`redirect` 的值是用户可控的，虽然只用在内站跳转，也应该只接受以 `/` 开头的路径，避免被构造成外部地址。**任何来自 URL 的参数都当作不可信输入。**
:::

::: details 坑 5：退出登录后上个账号的数据还在页面上
**现象**：A 退出登录，B 登录进来，首页上还留着 A 的操作记录。

**原因**：业务数据存在别的 Store 里，退出时只清了用户 Store。

**怎么处理**：退出登录要清的是**所有用户相关的状态**，不是一个 Store。可以在用户 Store 里维护一个“重置清单”，或者干脆在退出后调用 `location.reload()` 让应用重新启动一次 —— 简单粗暴但有效。**如果选后者，要接受多一次完整加载。**
:::

::: details 坑 6：自定义指令只在首次渲染时生效
**现象**：切换角色之后，原本隐藏的按钮还是隐藏着，或者原本显示的按钮还在。

**原因**：指令只写了 `mounted`，首次绑定之后就不再执行了。

**怎么处理**：`mounted` 和 `updated` 都绑定同一个 `check` 函数。另外要注意，指令里用 `display` 隐藏的元素**仍然在 DOM 里**，用户能看到它的结构 —— 如果需要隐藏的内容本身敏感，就应该用 `v-if` 不渲染，或者根本不下发这份数据。**隐藏元素不等于保护数据。**
:::

::: details 坑 7：以为前端藏了按钮就安全了
**现象**：审核员看不到“新建活动”按钮，但用接口调试工具直接调创建接口，居然成功了。

**原因**：前端只是没显示入口，服务端没有校验角色。

**怎么处理**：这是**必须由后端兜底**的。前端控制的意义是“不让用户看到用不了的东西”，服务端的校验才是“不让用户做不该做的事”。做这个案例的时候，一定要把这句话写进你的答辩材料 —— **能说清楚这条边界，比多写一个按钮重要得多。**
:::

::: details 坑 8：把用户信息缓存进 `localStorage`
**现象**：管理员把某个账号从组织者改成了审核员，用户刷新页面后菜单还是旧的。

**原因**：角色是从本地缓存里读的，没有重新拉接口。

**怎么处理**：用户信息只从接口取，不要本地缓存。如果确实要缓存以减少请求，也必须设置一个很短的过期时间，并且**在角色相关的判断之前强制刷新一次**。本案例的做法最简单也最可靠：token 存本地，用户信息每次启动重新拉。
:::

## 扩展练习

::: details 练习 1：加一个“切换身份”的调试入口
在开发环境给顶栏加一个按钮，可以在组织者和审核员之间切换，方便测试两套菜单和按钮。生产环境必须看不到。

**思路**：用 `import.meta.env.DEV` 判断是否渲染。切换的动作是改 Store 里的 `role`，但要注意 **`role` 是 `computed`，没法直接赋值**，需要先把它变成可写的（内部维护一个 `roleOverride`）。这个练习的重点不是功能，而是让你亲手验证一次“前端改角色真的能改掉界面”，从而真正理解“前端控制只是体验”。
:::

::: details 练习 2：菜单和路由都从一份配置生成
现在菜单是一份数组、路由是另一份配置，加一个页面要改两个地方，很容易漏。把它们合并成一份“带 meta 的路由配置”，菜单直接从路由表里筛。

**思路**：给路由的 `meta` 加上 `menu: { title, icon, order }`，然后写一个 `buildMenus(routes, role)` 递归过滤。难点在于**过滤时要跳过没有 `menu` 的路由**（比如登录页、无权限页），并且要处理好嵌套路由的父子关系。做出来之后，加页面只需要在一个地方写配置。
:::

::: details 练习 3：实现一个简易的 token 自动续期
需求：token 有效期 30 分钟，用户操作期间不能突然被踢出去。做法是在每次请求前判断 token 是否快到 30 分钟，如果剩余不到 2 分钟就先调一次刷新接口换新 token，再发原请求。

**思路**：关键是**并发控制**：页面同时发出 5 个请求，不能让它们各自去刷新一次。用一个 `refreshPromise` 变量存住“正在进行的刷新”，其他请求 `await` 同一个 Promise。想清楚“刷新接口本身返回 401 时怎么办” —— 那就是真的过期了，应该走登出流程。这个练习的难点全在并发上，不在接口上。
:::

::: details 练习 4：给权限指令加上“没权限时替换成提示”
现在 `v-permission` 是直接 `display: none`。改成另一种行为：`v-permission:disable` 时不隐藏，而是把按钮置灰并加上 `title="当前角色没有此权限"`。

**思路**：用 `binding.arg` 区分这两种模式。置灰要同时设置 `disabled` 属性和样式，并且要注意 `<button>` 和 `<a>` 的禁用方式不一样。写完之后想一个问题：**置灰的按钮真的不能点吗？** 答案和坑 7 是同一个 —— 前端做的任何事都拦不住手动调接口。
:::

---

上一页：[案例 09 · 可编辑表格](/cases/09-editable-table) · 下一页：[案例总览](/cases/)
