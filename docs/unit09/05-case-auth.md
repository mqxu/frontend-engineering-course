# 案例 10 · 登录与鉴权（挑战档）

## 这个案例做什么

把 9.1 到 9.4 的知识组装成一套**能用的登录鉴权**：

| 部分 | 要求 |
| --- | --- |
| 登录页 | 表单校验、提交中状态、错误提示 |
| 状态模块 | 存 token 与用户信息，刷新后能恢复 |
| 路由守卫 | 未登录访问受限页面被挡回登录页，带上原地址 |
| 两级权限 | 菜单级（看不到入口）+ 按钮级（看不到按钮），角色数据控制 |
| 退出登录 | 清干净并回到登录页 |
| 刷新保持 | 刷新页面不掉登录态，也不闪 |
| 401 自动跳转 | 凭证失效时自动回登录页 |

::: tip 这是本单元唯一一次“把零件装成机器”
9.1 讲路由表，9.2 讲参数与嵌套，9.3 讲守卫，9.4 讲链路。
这个案例把它们拼起来，做出课程要求的**带鉴权的页面骨架**。

代码会比较多，但每一段都能在 9.4 里找到对应的解释。这个案例的重点不是“再抄一遍代码”，
而是**把三个最容易做错的地方讲透** —— 它们在下面的三个 `::: danger` 块里。
:::

## 项目结构

```text [src/]
├── api/
│   ├── auth.js            登录、取当前用户、退出
│   └── request.js         axios 实例 + 拦截器（401 在这里处理）
├── layouts/
│   └── AdminLayout.vue    菜单 + 顶部栏 + 子级出口
├── router/
│   ├── index.js           路由实例与路由表
│   ├── routes.js          路由表（菜单也从这里推导）
│   └── guards.js          守卫
├── stores/
│   └── auth.js            token 与用户信息
├── utils/
│   └── token.js           token 读写
└── views/
    ├── LoginView.vue
    ├── ForbiddenView.vue  403
    └── NotFoundView.vue   404
```

## 第一部分：状态模块

```js [src/stores/auth.js]
import { ref, computed } from 'vue'
import { getToken, setToken, clearToken } from '@/utils/token'
import { loginApi, fetchCurrentUserApi, logoutApi } from '@/api/auth'

const token = ref(getToken())
const user = ref(null)
// ready：登录态是否已经确定（已登录或已确认未登录）
const ready = ref(false)

const isLoggedIn = computed(() => Boolean(token.value && user.value))
const role = computed(() => user.value?.role ?? null)
const permissions = computed(() => user.value?.permissions ?? [])

async function login(credentials) {
  const { token: newToken, user: userInfo } = await loginApi(credentials)
  token.value = newToken
  setToken(newToken)
  user.value = userInfo
  ready.value = true
}

async function restore() {
  const saved = getToken()

  if (!saved) {
    user.value = null
    ready.value = true
    return
  }

  try {
    token.value = saved
    user.value = await fetchCurrentUserApi()
  } catch {
    resetState()
  } finally {
    ready.value = true
  }
}

async function logout() {
  try {
    // 让服务端也失效这个 token（失败也不影响前端退出）
    await logoutApi()
  } catch {
    // 忽略：网络问题不该阻止用户退出
  }
  resetState()
}

function resetState() {
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

::: tip 这段代码和 9.4 的差别
只有两处：`login` 直接用了登录接口返回的 `user`（少一次请求），
`logout` 多调了一次服务端注销接口。

**其余代码一模一样 —— 说明 9.4 讲的就是能直接用的实现。**
:::

## 第二部分：路由表与菜单从同一份数据推导

### 路由表

```js [src/router/routes.js]
export const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
    meta: { title: '登录', public: true }
  },
  {
    path: '/',
    component: () => import('@/layouts/AdminLayout.vue'),
    redirect: '/activities',
    children: [
      {
        path: 'activities',
        name: 'activity-list',
        component: () => import('@/views/ActivityListView.vue'),
        meta: { title: '活动管理', icon: 'calendar', menu: true }
      },
      {
        path: 'activities/new',
        name: 'activity-create',
        component: () => import('@/views/ActivityEditView.vue'),
        meta: { title: '发布活动', menu: false }   // 不进菜单
      },
      {
        path: 'activities/:id/edit',
        name: 'activity-edit',
        component: () => import('@/views/ActivityEditView.vue'),
        meta: { title: '编辑活动', menu: false },
        props: true
      },
      {
        path: 'signup-review',
        name: 'signup-review',
        component: () => import('@/views/SignupReviewView.vue'),
        meta: { title: '报名审核', icon: 'check', menu: true }
      },
      {
        path: 'sessions',
        name: 'session-list',
        component: () => import('@/views/SessionListView.vue'),
        meta: { title: '场次与场地', icon: 'clock', menu: true }
      },
      {
        path: 'dashboard',
        name: 'dashboard',
        component: () => import('@/views/DashboardView.vue'),
        meta: { title: '数据看板', icon: 'chart', menu: true, roles: ['admin', 'reviewer'] }
      }
    ]
  },
  {
    path: '/403',
    name: 'forbidden',
    component: () => import('@/views/ForbiddenView.vue'),
    meta: { title: '没有权限', public: true }
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('@/views/NotFoundView.vue'),
    meta: { title: '页面不存在', public: true }
  }
]
```

三个约定：

- `meta.public: true` 表示不需要登录（登录页、403、404）。
- `meta.menu: true` 表示这条路由要出现在菜单里。**不写就默认不进菜单**，
  避免“编辑活动”这种带参数的页面出现在菜单上。
- `meta.roles` 声明这条路由需要的角色，不写表示所有登录用户都能看。

### 菜单从路由表推导

这是**第一个容易做错的地方**。

很多人的做法是：菜单写一份列表，路由写一份路由表。两份数据各自维护。
过一段时间就会出现：

```text
菜单里看不到“数据看板”
→ 但手输 /dashboard 还能进去
→ 因为菜单里删了，路由里的权限判断忘了改
```

还有反过来的情况：路由里加了 `roles`，菜单里忘了同步，于是“看得到、点进去 403”，
用户莫名其妙。

**正确做法：菜单和路由用同一份数据。** 菜单是“路由表里 `meta.menu` 为真、
且当前用户有权限的那些”，用 `computed` 推导出来：

```js [src/composables/useMenu.js]
import { computed } from 'vue'
import { routes } from '@/router/routes'
import { useAuth } from '@/stores/auth'

export function useMenu() {
  const auth = useAuth()

  return computed(() => {
    // 找到布局那条路由（有 children 的）
    const layout = routes.find((r) => r.children?.length)
    if (!layout) return []

    return layout.children
      // ① 只要声明了要进菜单的
      .filter((r) => r.meta?.menu)
      // ② 角色不匹配的直接过滤掉 —— 这是菜单级权限
      .filter((r) => {
        const roles = r.meta?.roles
        if (!roles || roles.length === 0) return true
        return roles.includes(auth.role.value)
      })
      // ③ 整理成菜单需要的样子
      .map((r) => ({
        name: r.name,
        title: r.meta.title,
        icon: r.meta.icon
      }))
  })
}
```

菜单组件只是把它渲染出来：

```vue [src/components/AppMenu.vue]
<script setup>
import { useMenu } from '@/composables/useMenu'

const menu = useMenu()
</script>

<template>
  <nav class="app-menu">
    <RouterLink v-for="item in menu" :key="item.name" :to="{ name: item.name }" class="menu-item">
      <AppIcon :name="item.icon" />
      <span>{{ item.title }}</span>
    </RouterLink>
  </nav>
</template>
```

::: danger 容易做错的地方一：菜单与路由的权限判断不一致
**菜单权限是“看得见 / 看不见”，路由守卫是“进得去 / 进不去”。这是两道不同的门。**

只做菜单过滤不做守卫拦截，等于把门装在墙上 —— 用户手输地址照样进。
只做守卫不做菜单过滤，用户会看到一堆点进去就 403 的入口。

**判断：一份数据，两处使用。** 菜单从路由表的 `meta` 推导，
守卫也读同一份 `meta`。这样它们永远一致 —— 想改权限只改一处。
:::

## 第三部分：守卫

```js [src/router/guards.js]
import { useAuth } from '@/stores/auth'
import { useToast } from '@/composables/useToast'

export function setupGuards(router) {
  router.beforeEach(async (to) => {
    const auth = useAuth()

    // ① 恢复登录态，只做一次
    if (!auth.ready.value) {
      await auth.restore()
    }

    const isPublic = to.meta.public === true

    // ② 公开页面直接放行；已登录还去登录页则送回首页
    if (isPublic) {
      if (to.name === 'login' && auth.isLoggedIn.value) {
        return { name: 'activity-list' }
      }
      return true
    }

    // ③ 需要登录但没登录 → 去登录页并记住原地址
    if (!auth.isLoggedIn.value) {
      return { name: 'login', query: { redirect: to.fullPath } }
    }

    // ④ 角色不匹配 → 403
    const roles = to.meta.roles
    if (roles && roles.length > 0 && !roles.includes(auth.role.value)) {
      return { name: 'forbidden' }
    }

    // ⑤ 放行
  })

  router.afterEach((to) => {
    // 页面标题
    const base = '校园活动服务平台'
    document.title = to.meta.title ? `${to.meta.title} · ${base}` : base
  })
}

/** 单独导出，供拦截器在 401 时使用 */
export function redirectToLogin(router) {
  const current = router.currentRoute.value
  if (current.name === 'login') return
  router.replace({ name: 'login', query: { redirect: current.fullPath } })
}
```

::: danger 容易做错的地方二：刷新时的时序问题
用户刷新 `/dashboard` 会发生什么？内存里的 `user` 空了，只剩 `localStorage` 里的 token。

如果恢复逻辑写在 `App.vue` 的 `onMounted` 里：页面会先渲染，
此时 `auth.isLoggedIn` 是 `false` —— **要么闪一下登录页，要么闪一下 403**，
等用户信息回来才跳回 `/dashboard`。

**正确做法是上面这段代码的第 ① 步：在 `beforeEach` 里 `await auth.restore()`。**
路由的首次导航是异步的，`RouterView` 在导航确认前什么都不渲染，
所以页面根本没有机会渲染错误的状态。

`ready` 标记保证这段异步只执行一次，后续的每次导航都能直接读到已经恢复好的状态。

**验证方法**：在 `/dashboard` 页面按 F5，观察有没有“闪一下”。没有闪，就对了。
:::

## 第四部分：登录页

```vue [src/views/LoginView.vue]
<script setup>
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuth } from '@/stores/auth'
import { useToast } from '@/composables/useToast'

const route = useRoute()
const router = useRouter()
const auth = useAuth()
const toast = useToast()

const form = ref({ username: '', password: '' })
const submitting = ref(false)
const errorMsg = ref('')
const touched = ref(false)

const usernameError = computed(() => {
  if (!touched.value) return ''
  if (!form.value.username) return '请输入账号'
  if (form.value.username.length < 3) return '账号至少 3 个字符'
  return ''
})

const passwordError = computed(() => {
  if (!touched.value) return ''
  if (!form.value.password) return '请输入密码'
  if (form.value.password.length < 6) return '密码至少 6 位'
  return ''
})

const canSubmit = computed(
  () => form.value.username && form.value.password.length >= 6 && !submitting.value
)

/** 只接受站内路径，防开放重定向 */
function safeRedirect(value, fallback = '/activities') {
  if (typeof value !== 'string') return fallback
  if (!value.startsWith('/') || value.startsWith('//')) return fallback
  return value
}

async function onSubmit() {
  touched.value = true
  errorMsg.value = ''
  if (usernameError.value || passwordError.value) return

  submitting.value = true
  try {
    await auth.login(form.value)
    toast.success('登录成功')
    // replace：不让用户后退回到登录页
    await router.replace(safeRedirect(route.query.redirect))
  } catch (e) {
    errorMsg.value = e.response?.data?.message || '账号或密码不正确'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <form class="login-card" @submit.prevent="onSubmit">
      <h1>校园活动服务平台</h1>
      <p class="subtitle">管理端 · 活动组织者与审核员使用</p>

      <label class="field">
        <span>账号</span>
        <input
          v-model.trim="form.username"
          :class="{ invalid: usernameError }"
          autocomplete="username"
          placeholder="请输入账号"
          @blur="touched = true"
        />
        <em v-if="usernameError" class="error">{{ usernameError }}</em>
      </label>

      <label class="field">
        <span>密码</span>
        <input
          v-model="form.password"
          type="password"
          :class="{ invalid: passwordError }"
          autocomplete="current-password"
          placeholder="请输入密码"
          @blur="touched = true"
        />
        <em v-if="passwordError" class="error">{{ passwordError }}</em>
      </label>

      <p v-if="errorMsg" class="form-error">{{ errorMsg }}</p>

      <button type="submit" :disabled="!canSubmit">
        {{ submitting ? '登录中…' : '登录' }}
      </button>
    </form>
  </div>
</template>
```

三个细节：

- **校验时机**：`@blur` 之后才显示错误。一进页面就报“请输入账号”很烦人。
- **提交中状态**：按钮禁用 + 文案变“登录中…”，防止重复提交。
- **错误来源分两层**：前端校验的错误显示在字段下方，接口返回的错误显示在表单底部。

## 第五部分：两级权限

### 菜单级：看不到入口

就是上面的 `useMenu`，它按 `meta.roles` 过滤。审核员看不到“数据看板”这个菜单项。

### 按钮级：看不到按钮

用 8.5 的 `v-permission` 指令：

```js [src/directives/permission.js]
export const vPermission = {
  mounted(el, binding) {
    const required = Array.isArray(binding.value) ? binding.value : [binding.value]
    const granted = binding.instance?.$permissions ?? []

    if (!required.some((code) => granted.includes(code))) {
      el.parentNode?.removeChild(el)
    }
  }
}
```

权限数据从状态模块挂到全局属性上：

```js [src/main.js]
import { createApp } from 'vue'
import { useAuth } from '@/stores/auth'
import { vPermission } from '@/directives/permission'
import App from './App.vue'
import router from './router'
import { setupGuards } from './router/guards'

const app = createApp(App)

app.directive('permission', vPermission)

// 让指令能读到当前用户的权限码
Object.defineProperty(app.config.globalProperties, '$permissions', {
  get: () => useAuth().permissions.value
})

setupGuards(router)

app.use(router)
app.mount('#app')
```

路由实例本身接收路由表：

```js [src/router/index.js]
import { createRouter, createWebHistory } from 'vue-router'
import { routes } from './routes'

const router = createRouter({
  history: createWebHistory(),
  routes,
  // 切换路由时滚动到顶部，返回时恢复位置
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) return savedPosition
    return { top: 0 }
  }
})

export default router
```

用起来：

```vue [src/views/SignupReviewView.vue]
<template>
  <div class="review-actions">
    <button v-permission="'signup:review'" @click="approve">通过</button>
    <button v-permission="'signup:review'" @click="reject">驳回</button>
    <button v-permission="'activity:delete'" class="danger" @click="remove">删除活动</button>
  </div>
</template>
```

::: danger 容易做错的地方三：按钮级权限只是体验优化
把按钮从 DOM 里移除，**拦得住鼠标，拦不住接口**。

用户只要打开开发者工具，手工发一个 `POST /api/signups/12/approve`，
请求就发出去了。前端代码对用户是完全透明的，**任何前端判断都能被绕过**。

所以真正的权限校验**必须在后端做**：服务端拿到 token，
查出这个用户的角色和权限，再判断这个操作允不允许。

**前端做按钮级权限的目的只有一个：别显示点了会报错的按钮，减少用户的无效操作。**
它是体验优化，不是安全措施。

答辩时这一点会被问到。如果你的项目只有前端权限判断、后端接口谁都能调，
这一项分数会很低。**哪怕项目里后端是模拟的，也要把这句话写在文档里。**
:::

### 角色与权限码的设计

角色是“身份”，权限码是“能做什么”。一个角色对应一组权限码：

| 角色 | 权限码 | 能做什么 |
| --- | --- | --- |
| `organizer` 活动组织者 | `activity:create`、`activity:edit`、`session:manage` | 发布、编辑活动，管理场次 |
| `reviewer` 审核员 | `signup:review`、`dashboard:view` | 审核报名、看数据看板 |
| `admin` 管理员 | 全部 | 都能做 |

::: details 为什么不直接用角色判断
“角色判断”写起来是 `auth.role === 'organizer'`，简单直接。但活动一多，
会发现“某个特殊的审核员也要能删活动”，于是到处改成 `role === 'organizer' || role === 'reviewer'`，
改到最后没人说得清谁有什么权限。

**权限码把“谁能做什么”从代码里拿出来，变成一份数据。** 要调整时改数据或改后端配置即可，
前端只是照着权限码显示 / 隐藏按钮。这是更耐用的设计。
:::

## 第六部分：401 处理与退出登录

### 401 自动跳转

```js [src/api/request.js]
import axios from 'axios'
import router from '@/router'
import { useAuth } from '@/stores/auth'
import { getToken } from '@/utils/token'
import { redirectToLogin } from '@/router/guards'

const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 10000
})

request.interceptors.request.use((config) => {
  const token = getToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// 多个请求同时 401 时，只跳一次
let redirecting = false

request.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.response?.status === 401) {
      const auth = useAuth()
      auth.logout()

      if (!redirecting) {
        redirecting = true
        redirectToLogin(router)
        // 一秒后复位，允许下一次 401 触发跳转
        setTimeout(() => {
          redirecting = false
        }, 1000)
      }
    }
    return Promise.reject(error)
  }
)

export default request
```

### 退出登录

```vue [src/components/UserDropdown.vue]
<script setup>
import { useRouter } from 'vue-router'
import { useAuth } from '@/stores/auth'
import { confirm } from '@/composables/confirm'

const router = useRouter()
const auth = useAuth()

async function onLogout() {
  const ok = await confirm('确定退出登录吗？', { title: '退出登录' })
  if (!ok) return

  await auth.logout()
  // replace：不让用户后退回到已登录的页面
  await router.replace({ name: 'login' })
}
</script>

<template>
  <div class="user-dropdown">
    <span>{{ auth.user.value?.name }}</span>
    <button @click="onLogout">退出登录</button>
  </div>
</template>
```

全流程验证清单：

| 场景 | 期望结果 |
| --- | --- |
| 未登录访问 `/activities` | 跳登录页，地址是 `/login?redirect=/activities` |
| 登录成功 | 回到 `/activities`，后退不回登录页 |
| 未登录访问 `/dashboard` | 登录后回到 `/dashboard`，不是首页 |
| 已登录访问 `/login` | 自动跳 `/activities` |
| 普通用户在受限页面刷新 | 不闪登录页，稳定显示目标页 |
| 审核员访问 `/dashboard` | 正常进入；访问无权限页面 → 403 |
| 审核员看菜单 | 菜单里没有无权限的入口 |
| token 失效后再操作 | 自动回登录页，带 `redirect` |
| 点退出登录 | 回登录页，再访问受限页面被拦 |

## 小结

- 状态模块管三样：token、user、`ready`；`isLoggedIn` / `role` / `permissions` 从它们派生。
- **菜单与路由从同一份路由表推导**，权限只维护一处，两道门永远一致。
- 恢复登录态写在 `beforeEach` 并 `await`，用 `ready` 保证只做一次，页面才不会闪。
- 登录成功读 `redirect` 跳回原地址并用 `replace`；`redirect` 必须校验是站内路径。
- 两级权限：菜单按 `meta.roles` 过滤（看不到入口），按钮按权限码过滤（看不到按钮）。
- **按钮级权限只是体验优化，真正的校验必须在后端。**
- 401 在拦截器里统一处理，多请求并发时加防抖；退出登录要清干净并用 `replace`。

## 常见坑

::: details 坑 1：菜单藏了入口，地址栏还能进
原因：只做了菜单过滤，没做守卫拦截。

处理：守卫读同一份 `meta.roles`。**两道门都要装，而且用同一把锁。**
:::

::: details 坑 2：刷新时闪一下登录页
原因：恢复逻辑在渲染之后。

处理：`beforeEach` 里 `await auth.restore()`。验证方法是直接 F5 看有没有闪。
:::

::: details 坑 3：`redirect` 带了完整域名
现象：登录后跳到外部站点。

原因：直接用了地址栏的值。

处理：`safeRedirect` 只接受以单个 `/` 开头的路径。
:::

::: details 坑 4：退出登录后，列表页的缓存还在
原因：只清了 token。

处理：退出时清掉用户维度的所有缓存；给这类 key 统一加前缀，按前缀清理。
:::

::: details 坑 5：多个请求同时 401，跳转好几次
原因：每个失败的请求都触发了一次跳转。

处理：加 `redirecting` 防抖标记。
:::

## 课后练习

::: details 练习 1：跑通验证清单
按上面的清单逐项验证，把每一项的实际结果记录下来。有不符合的，定位并修复。

**思路**：先在 `/dashboard` 这类受限页面按 F5，观察有没有闪烁；再手工改
`localStorage` 里的 token 为一个无效值，验证 401 链路。
:::

::: details 练习 2：给菜单加二级结构
把活动管理做成一个可展开的分组，里面放活动列表、场次与场地。

**思路**：在 `meta` 里加一个 `group` 字段，`useMenu` 把同一组的项归到一起。
想清楚：**分组本身要不要权限？**（要 —— 组里所有项都没权限时，整组也不该显示。）
:::

::: details 练习 3：加一个“上次访问页面”记忆
用户登录后，如果没有 `redirect`，优先回到他上次访问的页面。

**思路**：在 `afterEach` 里把 `to.fullPath` 写进 `sessionStorage`（注意排除登录页、
403、404）。登录成功后：有 `redirect` 用 `redirect`，没有就用记忆值，都没有才回首页。
:::

---

上一节：[9.4 登录鉴权完整链路](/unit09/04-auth-flow) ·
下一节：[单元 9 课后练习](/unit09/practice)
