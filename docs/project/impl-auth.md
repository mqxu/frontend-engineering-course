# 登录与鉴权模块参考实现

这一页是登录鉴权模块的**参考实现**，不是教程，是给你对照着写作业用的。

它按同一条线走下来：**关键决策 → 数据流 → 文件与代码 → 容易出问题的地方 → 拓展与验收**。你写自己的版本时卡住了，翻到这里看一眼别人是怎么拆的，然后回去接着写自己的。

**先读三份约定再动手**：[业务规则与状态流转](/project/rules) 里有权限表，[接口约定](/project/api) 里有登录鉴权的三个接口和错误码，[目录结构与命名约定](/project/structure) 决定文件放哪。

## 一、模块范围与页面清单

登录鉴权模块很小，但它决定了后面四个模块能不能开工。先把范围划清楚。

| 页面 | 路由 | 是否免登录 | 作用 |
| --- | --- | --- | --- |
| 登录页 | `/login` | 是 | 输入用户名密码，拿到 token |
| 403 页 | `/403` | 是 | 已登录但角色不够时的提示页 |
| 后台外壳 | `/` 下的布局页 | 否 | 顶栏、侧边菜单、退出按钮 |
| 其余业务页面 | `/activity` 等 | 否 | 登录后才能访问 |

**为什么 403 页要放进免登录白名单？** 因为它是对“已登录但没有权限”这个结果的展示。如果它自己也需要权限，就会出现“点进 403 又被跳去登录”的死循环。

这个模块涉及的文件不多，列出来心里有数：

| 文件 | 职责 |
| --- | --- |
| `src/api/auth.js` | 三个接口的调用函数 |
| `src/api/request.js` | axios 实例、请求拦截器、响应拦截器、401 处理 |
| `src/stores/user.js` | token、用户信息、登录、退出、恢复 |
| `src/router/index.js` | 路由表与全局前置守卫 |
| `src/composables/usePermission.js` | 角色判断，给页面用 |
| `src/views/Login.vue` | 登录页 |
| `src/views/Forbidden.vue` | 403 页 |

## 二、登录数据流

登录看起来只是“填表单、点按钮”，其实中间经过了六个环节。把这条线走通一次，后面很多问题都能自己定位。

```
① 用户填表单，点“登录”
② Login.vue 校验通过，调用 userStore.login(form)
③ store 调 api/auth.js 的 login()，发 POST /api/auth/login
④ 拿到 { token, expiresIn, userInfo }
⑤ token 写进 localStorage，userInfo 写进 Pinia（顺手缓存一份到 localStorage）
⑥ 读 route.query.redirect 决定去哪，用 router.replace 跳转
```

### 2.1 接口层

```js [src/api/auth.js]
import request from './request'

/** 登录：返回 { token, expiresIn, userInfo } */
export function login(data) {
  return request.post('/auth/login', data)
}

/** 用 token 换当前用户信息 */
export function getCurrentUser() {
  return request.get('/auth/me')
}

/** 退出登录 */
export function logout() {
  return request.post('/auth/logout')
}
```

**注意这里没有 `await`，也没有 `res => res.data` 的转换。** 统一响应结构 `{ code, message, data }` 的解包在 `request.js` 的响应拦截器里做掉了，`api` 层拿到的直接就是业务数据。**约定一次，全项目照做**，不要在某个接口里单独再包一层。

### 2.2 登录页

```vue [src/views/Login.vue]
<script setup>
import { ref, reactive } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'

defineOptions({ name: 'LoginPage' })

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const formRef = ref(null)
const loading = ref(false)
const form = reactive({
  username: '',
  password: ''
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少 6 位', trigger: 'blur' }
  ]
}

async function handleSubmit() {
  if (loading.value) return

  try {
    await formRef.value.validate()
  } catch {
    return // 校验失败，validate 会 reject
  }

  loading.value = true
  try {
    await userStore.login(form)
    ElMessage.success('登录成功')

    // redirect 只接受站内路径，避免被拿来跳外部地址
    const redirect = route.query.redirect
    const target = typeof redirect === 'string' && redirect.startsWith('/') ? redirect : '/'
    router.replace(target)
  } catch {
    // 用户名密码错误等业务错误，提示由响应拦截器统一处理
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <el-card class="login-card" shadow="always">
      <h1 class="title">校园活动服务平台</h1>
      <p class="subtitle">管理端登录</p>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        @submit.prevent="handleSubmit"
      >
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" placeholder="organizer" clearable />
        </el-form-item>

        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            show-password
            @keyup.enter="handleSubmit"
          />
        </el-form-item>

        <el-button type="primary" class="submit" :loading="loading" @click="handleSubmit">
          登录
        </el-button>
      </el-form>
    </el-card>
  </div>
</template>

<style scoped lang="scss">
.login-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: var(--el-fill-color-light);
}

.login-card {
  width: 380px;
  padding: 8px;

  .title {
    margin: 0;
    font-size: 20px;
    text-align: center;
  }

  .subtitle {
    margin: 4px 0 24px;
    font-size: 13px;
    color: var(--el-text-color-secondary);
    text-align: center;
  }

  .submit {
    width: 100%;
  }
}
</style>
```

`redirect` 这一段有两个细节值得说清楚。

**第一，为什么要检查 `startsWith('/')`。** `redirect` 来自 URL，是用户能改的。如果写成 `router.replace(route.query.redirect)`，别人把地址栏改成 `/login?redirect=https://evil.example.com`，登录完就会被跳到站外。**这种问题叫开放重定向**，是安全评审会问的点。

**第二，用 `router.replace` 而不是 `router.push`。** 登录成功后如果用户点浏览器“返回”，我们希望他回到登录前的页面，而不是又回到登录页。`replace` 替换掉历史记录里的登录页，正好做到这一点。

### 2.3 一个容易被忽略的边界

如果用户本来就在登录页，`redirect` 会不会是 `/login`？会。比如他手动访问 `/login` 之外的受保护页面被弹回来，redirect 记的是那个页面，不是登录页。但也可能有人手动构造 `/login?redirect=/login`。

登录成功后再跳 `/login`，因为已经登录，守卫会放行到登录页，用户看到自己又回到了登录界面，会以为没登上。

**处理办法：目标等于当前登录页路径时，改跳首页。**

```js
const target = typeof redirect === 'string' && redirect.startsWith('/') ? redirect : '/'
router.replace(target === '/login' ? '/' : target)
```

## 三、Pinia 用户 Store

Store 是这个模块的核心。它管四件事：token、用户信息、登录动作、退出动作。另外还要负责“刷新页面后把状态恢复回来”。

```js [src/stores/user.js]
import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { login as loginApi, getCurrentUser, logout as logoutApi } from '@/api/auth'

const TOKEN_KEY = 'access_token'
const USER_KEY = 'user_info'

export const useUserStore = defineStore('user', () => {
  // token 的初始值从 localStorage 读，保证刷新后还在
  const token = ref(localStorage.getItem(TOKEN_KEY) || '')
  const userInfo = ref(null)

  const isLoggedIn = computed(() => Boolean(token.value))
  const role = computed(() => userInfo.value?.role || '')
  const roleLabel = computed(() => {
    if (role.value === 'ORGANIZER') return '活动组织者'
    if (role.value === 'AUDITOR') return '审核员'
    return '未知角色'
  })

  function setToken(value) {
    token.value = value
    if (value) {
      localStorage.setItem(TOKEN_KEY, value)
    } else {
      localStorage.removeItem(TOKEN_KEY)
    }
  }

  function setUserInfo(info) {
    userInfo.value = info
    if (info) {
      localStorage.setItem(USER_KEY, JSON.stringify(info))
    } else {
      localStorage.removeItem(USER_KEY)
    }
  }

  /** 登录：先存 token，再存用户信息 */
  async function login(form) {
    const data = await loginApi(form)
    setToken(data.token)
    setUserInfo(data.userInfo)
    return data.userInfo
  }

  /** 用 token 换最新的用户信息 */
  async function fetchUserInfo() {
    const info = await getCurrentUser()
    setUserInfo(info)
    return info
  }

  /**
   * 刷新页面后恢复登录态。
   * 返回 true 表示恢复成功，false 表示 token 已失效。
   */
  async function restore() {
    if (!token.value) return false

    // 先用本地缓存快速填上，菜单不会空一下
    const cached = localStorage.getItem(USER_KEY)
    if (cached) {
      try {
        userInfo.value = JSON.parse(cached)
      } catch {
        userInfo.value = null
      }
    }

    try {
      await fetchUserInfo() // 用后端的结果覆盖缓存
      return true
    } catch {
      clear() // token 失效，全部清掉
      return false
    }
  }

  /** 清空本地登录态，不发请求 */
  function clear() {
    setToken('')
    setUserInfo(null)
  }

  /** 退出登录：接口失败也要清本地 */
  async function logout() {
    try {
      await logoutApi()
    } catch {
      // 忽略：后端失败不影响本地清理
    } finally {
      clear()
    }
  }

  return {
    token,
    userInfo,
    isLoggedIn,
    role,
    roleLabel,
    setToken,
    setUserInfo,
    login,
    fetchUserInfo,
    restore,
    clear,
    logout
  }
})
```

### 3.1 为什么 token 存 localStorage，userInfo 却主要放内存

token 必须持久化，否则刷新页面就掉登录，用户没法用。用户信息理论上也能每次用 `/api/auth/me` 拉，但那样每次刷新都要等一个请求才敢渲染菜单。

所以这里的策略是**两级**：

| 数据 | 存哪 | 为什么 |
| --- | --- | --- |
| `token` | `localStorage` | 刷新后必须还在，否则掉登录 |
| `userInfo` | Pinia 内存 + `localStorage` 缓存 | 内存是权威值，缓存只是为了刷新瞬间不闪 |

刷新时先用缓存把菜单画出来，同时发 `/api/auth/me` 拿最新的覆盖。**如果前端缓存和后端不一致（比如管理员改了你的角色），以后端为准。**

### 3.2 `role` 和 `roleLabel` 用 computed 而不是直接存字段

`role` 从 `userInfo` 里派生，不单独存一份。这样只有一处数据源，不会出现“`userInfo` 里是审核员，`role` 变量还是组织者”这种不一致。

`roleLabel` 是给界面显示用的中文名。它只依赖 `role`，所以同样用 computed。**把它放在 store 里而不是散在页面里，是因为顶栏、个人面板、403 页都要显示这个文案。**

## 四、刷新页面恢复登录态

用户按 F5 时会发生什么？

```
刷新 → 内存里的 Vue 应用整个重建 → Pinia 清空
     → 但 localStorage 里的 token 还在
     → 于是 isLoggedIn 为 true，userInfo 却是 null
```

`userInfo` 是 null 的时候，菜单按角色渲染就会全空或者只显示公共项。用户会看到菜单闪一下再出现，严重的甚至以为权限丢了。

恢复流程就是补上“用 token 换用户信息”这一步：

```
从 localStorage 读 token
   ├─ 没有 token → 直接跳登录页
   └─ 有 token
        ├─ 先用缓存渲染（可选，为了不闪）
        ├─ 调 GET /api/auth/me
        │    ├─ 成功 → 覆盖 userInfo，放行
        │    └─ 失败（401）→ clear() 清理 → 跳登录页
```

**放在哪执行？** 两种常见做法：

| 做法 | 怎么做 | 代价 |
| --- | --- | --- |
| 挂载前恢复 | `main.js` 里 `userStore.restore().finally(() => app.mount())` | 首屏要等一个网络请求，慢 |
| 路由守卫里恢复 | 第一次导航时判断 `userInfo` 为空就 `restore()` | 首屏不卡，但守卫里多了异步逻辑 |

**推荐第二种。** 用守卫的写法见下一节，`restore()` 已经在 store 里准备好了。

## 五、路由守卫

守卫要做三件事：放行白名单、拦住未登录、拦住角色不匹配。

### 5.1 路由表带 meta

```js [src/router/index.js]
import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'

const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/Login.vue'),
    meta: { public: true, title: '登录' }
  },
  {
    path: '/403',
    name: 'forbidden',
    component: () => import('@/views/Forbidden.vue'),
    meta: { public: true, title: '无权访问' }
  },
  {
    path: '/',
    component: () => import('@/views/layout/AppLayout.vue'),
    redirect: { name: 'dashboard' },
    children: [
      {
        path: 'dashboard',
        name: 'dashboard',
        component: () => import('@/views/dashboard/DashboardView.vue'),
        meta: { title: '数据看板' }
      },
      {
        path: 'activity',
        name: 'activity-list',
        component: () => import('@/views/activity/ActivityList.vue'),
        meta: { title: '活动管理', roles: ['ORGANIZER', 'AUDITOR'] }
      },
      {
        path: 'venue',
        name: 'venue-list',
        component: () => import('@/views/venue/VenueList.vue'),
        meta: { title: '场地管理', roles: ['AUDITOR'] }
      }
    ]
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('@/views/NotFound.vue'),
    meta: { public: true }
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
})

// 恢复登录态只用执行一次，用这个标记避免每次导航都请求 /auth/me
let restored = false

router.beforeEach(async (to) => {
  const userStore = useUserStore()

  // ① 白名单直接放行
  if (to.meta.public) return true

  // ② 没登录 → 去登录页，并把目标地址记下来
  if (!userStore.isLoggedIn) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }

  // ③ 有 token 但内存里没有用户信息（刷新页面）→ 恢复一次
  if (!userStore.userInfo && !restored) {
    restored = true
    const ok = await userStore.restore()
    if (!ok) {
      return { name: 'login', query: { redirect: to.fullPath } }
    }
  }

  // ④ 角色不匹配 → 403
  const roles = to.meta.roles
  if (roles?.length && !roles.includes(userStore.role)) {
    return { name: 'forbidden' }
  }

  return true
})

router.afterEach((to) => {
  document.title = to.meta.title ? `${to.meta.title} · 校园活动服务平台` : '校园活动服务平台'
})

export default router
```

三个位置要讲清楚。

**`to.meta.public` 这个字段名。** 有的团队叫 `requiresAuth`（true 表示要登录），有的叫 `public`（true 表示免登录）。**两种写法都行，但别混用。** 本项目统一用 `public`：默认所有页面都要登录，免登录的页面显式标记。默认安全比默认开放好。

**`redirect: to.fullPath` 记的是完整路径，不是 `to.path`。** `fullPath` 带 query。用户访问 `/activity?status=DRAFT` 被弹去登录，登录回来应该回到带筛选条件的那个地址。`path` 会把 query 丢掉。

**`restored` 标记。** 如果不加这个标记，每次导航且 `userInfo` 为空时都会请求一次 `/auth/me`。正常情况下恢复成功后 `userInfo` 就不为空了，但如果 `/auth/me` 连续失败，就会变成每次导航都发请求。用标记保证“一次会话只恢复一次”。

### 5.2 403 页

```vue [src/views/Forbidden.vue]
<script setup>
import { useRouter } from 'vue-router'

defineOptions({ name: 'ForbiddenPage' })

const router = useRouter()
</script>

<template>
  <el-result icon="warning" title="403" sub-title="你的角色没有权限访问这个页面">
    <template #extra>
      <el-button type="primary" @click="router.replace('/')">回到首页</el-button>
    </template>
  </el-result>
</template>
```

## 六、请求拦截器与 401 处理

请求拦截器负责带 token，响应拦截器负责解包和处理错误。**这是整个模块最容易出问题的地方。**

```js [src/api/request.js]
import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

// 未授权处理器：由 main.js 在 Pinia 安装后注入
let unauthorizedHandler = null
export function setUnauthorizedHandler(fn) {
  unauthorizedHandler = fn
}

// 防止并发请求同时触发多次跳转
let redirecting = false

const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 10000
})

// ---------- 请求拦截器：带 token ----------
request.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// ---------- 响应拦截器：解包 + 错误处理 ----------
request.interceptors.response.use(
  (response) => {
    const res = response.data

    // 业务码 1001 表示未登录或 token 失效
    if (res.code === 1001) {
      handleUnauthorized()
      return Promise.reject(res)
    }

    if (res.code !== 0) {
      ElMessage.error(res.message || '请求失败')
      return Promise.reject(res) // 业务失败也要 reject
    }

    return res.data // 解包，api 层拿到的就是业务数据
  },
  (error) => {
    const status = error.response?.status

    if (status === 401) {
      handleUnauthorized()
    } else if (status === 403) {
      ElMessage.error('没有权限执行此操作')
    } else {
      ElMessage.error(error.response?.data?.message || '网络异常，请稍后重试')
    }

    return Promise.reject(error)
  }
)

function handleUnauthorized() {
  if (redirecting) return
  redirecting = true

  ElMessage.warning('登录已过期，请重新登录')
  unauthorizedHandler?.() // 清 store 与 localStorage

  const { fullPath } = router.currentRoute.value
  const target = fullPath === '/login' ? '/login' : { name: 'login', query: { redirect: fullPath } }

  router.replace(target).finally(() => {
    redirecting = false
  })
}

export default request
```

### 6.1 `request.js` 顶层不能调 `useUserStore()`

很多人第一版会这么写：

```js
// ✗ 顶层调用，报错
import { useUserStore } from '@/stores/user'

const userStore = useUserStore() // ← 这里会抛错或拿到 undefined
```

**报错的原因是求值时机。**

`request.js` 是被 `stores/user.js` 间接 import 的，而 `useUserStore()` 需要 Pinia 已经通过 `app.use(createPinia())` 安装。模块顶层代码在 import 阶段就执行了，那时候 `main.js` 里的 `app.use(createPinia())` 可能还没跑到。**Pinia 没装上，`useUserStore()` 找不到自己属于哪个 Pinia 实例。**

还有一个更隐蔽的问题：**循环依赖。**

```
request.js  →  stores/user.js  →  api/auth.js  →  request.js
```

`request.js` 顶层 import store，store 又 import `api/auth.js`，`api/auth.js` 又回头 import `request.js`。三个文件绕成一个圈。ES 模块能处理循环引用，但前提是“只在函数里用对方的导出”。**一旦在顶层就调用 `useUserStore()`，就是在模块还没求值完的时候使用它**，拿到的是半成品。

### 6.2 解法一：延迟到拦截器函数内部

把 `useUserStore()` 挪进拦截器回调里，并且用动态 `import()` 断开循环。

```js [src/api/request.js（只贴 401 部分）]
request.interceptors.response.use(null, async (error) => {
  if (error.response?.status === 401) {
    // 动态导入：模块求值阶段不建立静态循环依赖
    const { useUserStore } = await import('@/stores/user')
    const userStore = useUserStore()
    userStore.clear()
    router.replace({ name: 'login' })
  }
  return Promise.reject(error)
})
```

**这个解法能用，但有两个代价**：一是拦截器里出现了异步，错误继续往上传的时机晚了一点；二是 `handleUnauthorized` 里要处理“动态导入还没回来时又来了一个 401”的情况，逻辑容易写乱。

### 6.3 解法二：注入未授权处理器（本项目采用）

就是上面 `request.js` 里的写法。`request.js` **完全不 import store**，只暴露一个 `setUnauthorizedHandler` 让外面注册。

```js [src/main.js]
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { useUserStore } from '@/stores/user'
import { setUnauthorizedHandler } from '@/api/request'
import './assets/main.css'

const app = createApp(App)
app.use(createPinia()) // 先装 Pinia
app.use(router)

// Pinia 装好之后，才调用 useUserStore，并且把清理逻辑注册给请求层
const userStore = useUserStore()
setUnauthorizedHandler(() => userStore.clear())

app.mount('#app')
```

| 对比项 | 解法一 · 动态导入 | 解法二 · 注入处理器 |
| --- | --- | --- |
| 循环依赖 | 用动态导入绕开 | 根本不存在 |
| 拦截器里有没有异步 | 有 | 没有 |
| 谁负责清状态 | 请求层 | 注入进来的那一方 |
| 可测试性 | 差，依赖真实 store | 好，注入一个假函数就能测 |

**解法二把“清理登录态”这件事的调用权和实现权分开了**：请求层只负责在合适的时候喊一声，具体怎么清由 `main.js` 决定。这和“接口层只负责发请求，不负责业务判断”是同一个思路。

### 6.4 两个容易漏的细节

**一、`redirecting` 标记必须加。** 页面一次加载可能同时发三四个请求，如果 token 失效，这几个请求可能同时返回 401。没有标记的话，`ElMessage.warning` 弹三次，`router.replace` 调三次。

**二、`Authorization` 的值是 `Bearer + 一个空格 + token`。** 少那个空格、把 `Bearer` 写成小写、或者 token 存成了带引号的 JSON 字符串，后端都会判成未登录。**这三种错误的现象一模一样**，都是“登录明明成功了，下一个请求就 401”。

## 七、按角色控制菜单与按钮

权限判断要收口到一处，不然会散落在十几个模板里。这里用一个组合式函数。

### 7.1 `usePermission`

```js [src/composables/usePermission.js]
import { computed } from 'vue'
import { useUserStore } from '@/stores/user'

export function usePermission() {
  const userStore = useUserStore()

  const role = computed(() => userStore.role)
  const isOrganizer = computed(() => role.value === 'ORGANIZER')
  const isAuditor = computed(() => role.value === 'AUDITOR')

  /** 当前角色是否属于传入的角色列表 */
  function hasRole(...roles) {
    return roles.includes(role.value)
  }

  return { role, isOrganizer, isAuditor, hasRole }
}
```

菜单的显隐有两种做法，本项目用“路由表驱动”，因为路由表上已经写了 `meta.roles`，不需要再维护一份菜单权限表。

```vue [src/views/layout/AppLayout.vue（菜单部分）]
<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

// 从路由表里取出布局页的子路由，按 meta.roles 过滤
const menuItems = computed(() => {
  const layout = router.options.routes.find((r) => r.path === '/')
  return (layout?.children ?? []).filter((item) => {
    const roles = item.meta?.roles
    if (!roles?.length) return true
    return roles.includes(userStore.role)
  })
})

async function handleLogout() {
  await userStore.logout()
  router.replace({ name: 'login' })
}
</script>
```

**菜单和路由守卫用的是同一份 `meta.roles`。** 这一点很重要：如果菜单按一份规则、守卫按另一份规则，迟早会出现“菜单里看得到、点进去被拦”或者反过来。**一份规则，两个地方用。**

按钮的显隐同理：

```vue
<el-button v-if="hasRole('AUDITOR')" type="primary" @click="goVenue">维护场地</el-button>
```

### 7.2 另一种做法：自定义指令 `v-role`

也有人喜欢把权限写成指令，模板里更短：

```js [src/directives/role.js]
import { useUserStore } from '@/stores/user'

export const vRole = {
  mounted(el, binding) {
    const userStore = useUserStore()
    const roles = Array.isArray(binding.value) ? binding.value : [binding.value]
    if (!roles.includes(userStore.role)) {
      el.parentNode?.removeChild(el)
    }
  }
}
```

在 `main.js` 里注册：

```js [src/main.js（追加一行）]
import { vRole } from '@/directives/role'
app.directive('role', vRole)
```

用法：

```vue
<el-button v-role="['AUDITOR']" type="primary">维护场地</el-button>
```

**它和组合式函数的区别，值得对照着看：**

| 对比项 | `usePermission` + `v-if` | `v-role` 指令 |
| --- | --- | --- |
| 权限变化后能否重新判断 | 能，响应式 | 不能，只在 `mounted` 跑一次 |
| 能不能参与计算（比如算按钮的 `disabled`） | 能 | 不能，只能删元素 |
| 模板可读性 | 一般，要写 `v-if="hasRole(...)"` | 短 |
| 调试 | 好，函数能单独测 | 差，结果不可见 |
| 页面上还有其他逻辑要用角色时 | 直接复用 | 还得再引一次 store |

**推荐组合式函数作为主要手段，指令只在“纯静态、一次性”的按钮上用。** 本项目里，角色在登录后基本不变，两者都能跑；但 `v-role` 那个“只在 `mounted` 跑一次”的局限在“切换账号”场景下会暴露：如果切换账号没有整页刷新，删掉的按钮不会回来。用组合式函数就没有这个问题。

## 八、退出登录

接口约定里写得很清楚：**无论 `/api/auth/logout` 成功还是失败，本地都要清干净。** 所以 `logout` 的动作放在 store 里，用 `finally` 保证清理一定执行（代码见第三节的 `logout`）。

调用处：

```js
async function handleLogout() {
  await userStore.logout() // 内部已保证清理
  router.replace({ name: 'login' })
}
```

**为什么清理要写在前端，而不是“后端删了 token 因此前端清一下就行”？** 因为前端 90% 的登录态存在自己这边（localStorage 的 token 和内存里的 userInfo）。后端删 token 只让旧 token 立刻失效，但前端的 token 还在，不清理的话用户刷新页面还是“登录状态”，只是每个请求都 401。**两边都要清。**

## 九、前端角色控制只是体验优化

这一节是答辩时的必答题，务必读两遍。

**前端藏起来一个按钮，不等于用户不能做这件事。** 用户可以在浏览器控制台里改掉 `v-if`，或者直接用 `curl` 调接口。如果后端没校验，数据就被改了。

对照 [业务规则](/project/rules) 里的权限表：

| 谁做 | 做什么 | 目的是什么 |
| --- | --- | --- |
| 前端 | 菜单按角色显隐 | 让用户少看到用不上的功能 |
| 前端 | 按钮按角色和状态显隐 | 减少误操作 |
| 前端 | 路由守卫拦页面 | 避免用户进到一个必然报错的页面 |
| 后端 | **每个接口校验当前用户有没有权限操作这条数据** | **真正的权限控制** |
| 后端 | 组织者请求别人的活动 id 返回 403 | 防止越权读取和修改 |

**“减少误操作”和“防止越权”是两件事。** 前者是体验问题，后者是安全问题。前端的显隐解决前者，后端校验解决后者。

### 9.1 怎么验证后端有没有真的拦

准备两个账号：一个组织者 `organizer`，一个审核员 `auditor`。按下面的步骤走。

**第一步 · 去掉前端显隐。** 临时把某个按钮的 `v-if` 删掉，或者直接在控制台里把按钮的 `disabled` / `display` 改掉。刷新页面，按钮就点得到了。

**第二步 · 点它，看会发生什么。**

- 后端返回 403 或业务码 1002，界面提示“没有权限执行此操作”→ **权限控制是真的**。
- 操作直接成功了 → **前端那层只是装饰，后端有漏洞**。

**第三步 · 绕开界面直接调接口。** 这比改 `v-if` 更彻底。

```bash
# 用组织者的 token 去改一个不属于他的活动
curl -X PUT http://localhost:8080/api/activities/99 \
  -H "Authorization: Bearer <组织者的 token>" \
  -H "Content-Type: application/json" \
  -d '{"title":"被改的标题"}'
```

如果后端只校验了“已登录”而没校验“这条活动是不是你的”，它会返回成功。**这就是越权修改**，比界面上的问题严重得多。

**第四步 · 把这一步写进设计文档。** “前端的角色控制只用于改善体验，真正的权限由后端在每个接口校验”这句话，加上你的验证截图，是答辩时很好用的一段材料。

::: danger 一句话记住
**前端权限是“让好人不迷路”，后端权限是“让坏人进不来”。** 两件事都要做，但不要以为做了前者就够了。
:::

## 十、常见坑

::: details 坑 1：401 死循环，页面一直转圈
**现象**：登录后访问某个页面，请求一直 401，页面在登录页和业务页之间来回跳，控制台刷出一屏错误。

**原因**：401 的处理逻辑里又调用了一个需要鉴权的接口。比如 `handleUnauthorized` 里为了“记录一下退出原因”调了 `POST /api/logs`，这个请求也带上了已经失效的 token，也返回 401，于是再次触发处理逻辑。

**怎么处理**：

- 401 的处理函数里**只做清状态和跳转，不发任何业务请求**。要上报日志用 `localStorage` 记一笔，等下次登录后再发。
- 加 `redirecting` 标记，确保同一时间只会跳一次。
- 判断目标路由：已经在 `/login` 上就不要再 `router.replace` 到登录页，否则每次 401 都会 push 一条历史记录。

```js
if (router.currentRoute.value.name === 'login') return
```
:::

::: details 坑 2：token 格式不对，登录成功了下一个请求还是 401
**现象**：登录接口返回 200，token 也存进去了，但紧接着 `/auth/me` 就 401。

**原因**：请求头格式错。三种最常见的写法：

```js
// ✗ 少了空格
config.headers.Authorization = `Bearer${token}`

// ✗ 关键字大小写错了（有些后端严格匹配）
config.headers.Authorization = `bearer ${token}`

// ✗ 存进去的时候是 JSON 字符串，带引号
localStorage.setItem('access_token', JSON.stringify(token))
// 发出去变成 Authorization: Bearer "eyJhbGci..."
```

**怎么处理**：打开浏览器开发者工具的 Network 面板，点开任意一个业务请求，看 `Request Headers` 里的 `Authorization` 一行，和后端约定的格式逐字比对。

**正确写法只有一种：**

```js
config.headers.Authorization = `Bearer ${token}`
```

**还有一个连带问题**：`localStorage.getItem` 拿不到返回 `null`，拿不到的时候不能拼出字符串 `"Bearer null"`。所以要先判断 `if (token)`。
:::

::: details 坑 3：并发请求触发多次跳转与多次提示
**现象**：token 过期后，页面上同时发出的 4 个请求都返回 401，屏幕右上角弹出 4 条“登录已过期”。

**原因**：每个 401 都独立走了一遍处理逻辑。

**怎么处理**：加一个模块级的 `redirecting` 标记，第一个 401 进来时置为 true，处理完跳转后再置回 false。中间来的 401 直接返回。

```js
let redirecting = false

function handleUnauthorized() {
  if (redirecting) return
  redirecting = true
  // ...清状态、跳转
  router.replace(target).finally(() => {
    redirecting = false
  })
}
```

**顺带说一个更彻底的做法**：给“跳转”这件事本身做去重，也就是先记一个 `lastRedirectAt` 时间戳，1 秒内重复的跳转请求直接丢弃。但 `redirecting` 标记已经够用了，不要过度设计。
:::

::: details 坑 4：刷新后角色丢失，菜单闪一下
**现象**：F5 刷新后，侧边菜单先显示成空或只显示公共项，大约半秒后才出现完整的角色菜单。

**原因**：`isLoggedIn` 从 `localStorage` 的 token 立刻算出来是 true，但 `userInfo` 在内存里是 null，于是按角色过滤菜单时把带 `roles` 的项全过滤掉了。等 `/auth/me` 回来才有角色。

**怎么处理**：三种，按推荐顺序排。

**一、先读缓存再请求（本节采用）。** store 里持久化了一份 `user_info` 缓存，`restore()` 一进来就用它填 `userInfo`，菜单立刻就是对的，随后 `/auth/me` 回来再做校正。

**二、恢复完成前不渲染布局。** 在布局页用 `v-if="userStore.userInfo"` 包住菜单，恢复期间显示骨架。缺点是整页要多等一会儿。

**三、把角色也存进 localStorage 单独读。** 和做法一本质一样，只是拆成了两个 key。**不推荐**，两份数据分开存容易不一致。

**注意：缓存只是“让界面不闪”，不能拿它当权限依据。** 真正决定能不能操作的是后端的校验结果。
:::

::: details 坑 5：路由守卫里 `await` 让页面白屏一下
**现象**：刷新页面后，地址栏已经是 `/activity`，但页面白了一两秒才出现内容。

**原因**：守卫里的 `restore()` 要发 `/auth/me`，导航被这个请求阻塞住了。这是“在守卫里恢复登录态”这个方案的固有代价。

**怎么处理**：

- `restore()` 先用本地缓存填 `userInfo`，再发请求校正，这样渲染不依赖请求（配合上一条）。
- 只在第一次导航时恢复，用 `restored` 标记，后面就不再请求。
- 如果实在在意这一两秒，把恢复改到 `main.js` 里、在 `app.mount()` 之前做，并配一个全局加载动画。**但那样首屏更慢**，只是把白屏换成了一个转圈，体验不一定更好。

**这一条没有免费的解。** 选择“守卫里恢复”，就是拿首屏的一点点等待，换“菜单不闪、业务页面拿得到角色”。
:::

::: details 坑 6：`redirect` 指回登录页，登录成功后像没登上
**现象**：登录成功，界面又回到了登录页。

**原因**：`route.query.redirect` 的值是 `/login`。常见于用户手动构造地址，或者某次跳转写错了。

**怎么处理**：跳转前判断目标，等于 `/login` 就改跳首页：

```js
const target = redirect && redirect.startsWith('/') ? redirect : '/'
router.replace(target === '/login' ? '/' : target)
```

**顺带把开放重定向也一起防了**：只接受以 `/` 开头的路径，`https://xxx` 一律换成首页。
:::

## 十一、验收清单

做完这个模块，对着下面这张表逐项验证。**每一项都要动手做一遍，不要凭印象打勾。**

| 验收项 | 怎么验证 |
| --- | --- |
| 未登录访问业务页面被拦 | 清空 localStorage，直接访问 `/activity`，看是否跳到 `/login` |
| 跳转带回 `redirect` | 接上一条，看地址栏是否是 `/login?redirect=/activity` |
| 登录后回到原页面 | 在 `/login?redirect=/activity` 登录，看是否进了活动列表而不是首页 |
| 登录后 `redirect` 带 query 也不丢 | 访问 `/activity?status=DRAFT`，登录后地址栏的 query 还在 |
| 开放重定向被拦住 | 访问 `/login?redirect=https://example.com`，登录后进首页而不是站外 |
| 登录成功用 `replace` | 登录后点浏览器“返回”，不应回到登录页 |
| token 正确带上 | Network 面板里看 `Authorization: Bearer xxx`，空格和大小写都对 |
| 刷新页面登录态还在 | 登录后按 F5，仍在原页面，顶栏显示用户名与角色 |
| 刷新后角色菜单正确 | 用审核员账号刷新 `/venue`，场地菜单立刻可见，不闪 |
| token 失效被清理 | 控制台执行 `localStorage.setItem('access_token','bad')`，刷新后回到登录页，localStorage 被清空 |
| 并发 401 只提示一次 | 限速到 Slow 3G，让页面同时发多个请求，token 失效时只弹一条提示 |
| 角色不匹配跳 403 | 用组织者账号访问 `/venue`，看到 403 页 |
| 403 页免登录可达 | 未登录直接访问 `/403`，不被弹去登录页 |
| 菜单与守卫规则一致 | 组织者账号看不到“场地管理”菜单，手动输地址也被 403 拦住 |
| 退出登录清干净 | 点退出，localStorage 里 `access_token` 和 `user_info` 都没了 |
| 退出接口失败也能退出 | 把 `/auth/logout` 地址改错，点退出仍能回到登录页且本地已清 |
| 后端真的会拦 | 去掉某个按钮的 `v-if` 后点击，后端返回 403 或 1002 |

## 十二、可以继续做的事

- **token 提前续期。** 登录响应里的 `expiresIn` 目前没用上。可以在快要过期时用旧 token 换一个新 token，用户就不会在操作到一半时被踢出去。接口约定里暂时没有刷新接口，需要和后端先商量。
- **多标签页同步退出。** 在 A 标签退出登录，B 标签还停在业务页面。可以用 `window.addEventListener('storage', ...)` 监听 `access_token` 被清空，B 标签也跟着跳登录页。
- **把角色判断也收进 domain 层。** `usePermission` 管的是“界面要不要显示”，真正的业务规则（比如“组织者只能编辑自己的草稿”）应该和活动管理模块的规则放在一起，见 [活动管理模块](/project/impl-activity)。
- **登录页记住用户名。** 把用户名存在 localStorage，下次打开自动填上，密码不存。**注意不要做成“记住密码”** —— 明文存密码是安全问题。

---

上一页：[三阶段交付](/project/milestones) · 下一页：[活动管理模块](/project/impl-activity)
