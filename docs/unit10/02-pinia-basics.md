# 10.2 Pinia 两种写法

## 从一个登录态模块的需求说起

按 [10.1](/unit10/01-when-global) 的判断，登录用户信息该放进全局状态。
先别急着写，把需求列清楚：

- 要存：token、用户名、角色。
- 要能：登录、退出、刷新用户信息。
- 要能派生：`isLoggedIn`（有没有 token）、`isReviewer`（是不是审核员）。
- 要能在别处读：路由守卫读 `isLoggedIn`，导航栏读 `username`，列表页读写 `role`。

这几条就是 store 要提供的全部能力。下面用两种写法各实现一遍，再比较。

## 写法一：选项式

选项式写法把 store 拆成 `state`、`getters`、`actions` 三块。
熟悉 Vuex 或 Vue 2 的读者会觉得眼熟 —— 它确实是从那套思路延续下来的。

```js [src/stores/auth.js]
import { defineStore } from 'pinia'
import { loginApi, getUserInfoApi } from '@/api/auth'

export const useAuthStore = defineStore('auth', {
  // state 是一个函数，返回初始状态对象
  state: () => ({
    token: '',
    username: '',
    role: '', // 'organizer' 组织者 | 'reviewer' 审核员
    loading: false
  }),

  // getters 相当于 store 的 computed
  getters: {
    isLoggedIn: (state) => Boolean(state.token),
    isReviewer: (state) => state.role === 'reviewer'
  },

  // actions 既可以改 state，也可以发请求
  actions: {
    async login(form) {
      this.loading = true
      try {
        const res = await loginApi(form)
        this.token = res.token
        const info = await getUserInfoApi()
        this.username = info.username
        this.role = info.role
      } finally {
        this.loading = false
      }
    },
    logout() {
      this.token = ''
      this.username = ''
      this.role = ''
    }
  }
})
```

选项式里有两个容易踩的点：

1. **`state` 必须是函数**，返回一个新对象。写成对象字面量会让多个 store 实例共享同一份状态。
2. **在 actions 里用 `this` 访问状态**（`this.token`），不用像 Vuex 那样写 `state.token`。

## 写法二：组合式（setup 写法）

组合式写法把整个 store 写成"一个用 `setup` 语法的函数"：
`ref` 就是 state，`computed` 就是 getters，普通函数就是 actions，最后 `return` 出去。

```js [src/stores/auth.js]
import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { loginApi, getUserInfoApi } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  // 相当于 state
  const token = ref('')
  const username = ref('')
  const role = ref('')
  const loading = ref(false)

  // 相当于 getters
  const isLoggedIn = computed(() => Boolean(token.value))
  const isReviewer = computed(() => role.value === 'reviewer')

  // 相当于 actions
  async function login(form) {
    loading.value = true
    try {
      const res = await loginApi(form)
      token.value = res.token
      const info = await getUserInfoApi()
      username.value = info.username
      role.value = info.role
    } finally {
      loading.value = false
    }
  }

  function logout() {
    token.value = ''
    username.value = ''
    role.value = ''
  }

  // 必须把要暴露出去的东西 return
  return { token, username, role, loading, isLoggedIn, isReviewer, login, logout }
})
```

::: warning `return` 漏了就报错
组合式写法里，**没 `return` 的东西外部拿不到**。
常见现象：`store.username` 是 `undefined`，检查发现 `username` 写了但忘了 `return`。

一个省事的判断：把 `return` 想象成组件的"对外接口"，
你希望别的组件能用到的才写进去。
:::

### 两种写法怎么选

| 对比项 | 选项式 | 组合式（推荐） |
| --- | --- | --- |
| 和组件写法的一致性 | 另一套语法，要单独记 | 与 `<script setup>` 完全一致 |
| 类型推导 | 需要额外处理 | 天然友好 |
| 复用逻辑 | 不方便 | 可以直接用别的组合式函数 |
| 跨模块调用 | 写法稍绕 | 和组件里一样自然 |
| 组织大型 store | 三块分开，要来回跳 | 逻辑相关的写在一起 |

**结论：本课程统一用组合式写法。**

理由不是"组合式更高级"，而是**你已经在组件里用 `ref`、`computed` 了** ——
再学一套 `state` / `getters` / `actions` 的映射规则，纯粹是多一层记忆负担。
组合式写法的 store 读起来和组件一模一样。

::: tip 本课程的 store 约定
- 文件名小写：`stores/auth.js`、`stores/activity.js`。
- 导出的函数名以 `use` 开头、以 `Store` 结尾：`useAuthStore`、`useActivityStore`。
- `defineStore` 的第一个参数（id）与文件名保持一致：`defineStore('auth', ...)`。
- **store 里存状态和业务动作，不写组件的渲染逻辑**。
:::

## 解构状态时怎么保持响应性

这是初学者**最容易踩的坑**，没有之一。

先看现象。你要在导航栏里显示用户名：

```vue [components/TopNav.vue（反例）]
<script setup>
import { useAuthStore } from '@/stores/auth'

// ✗ 直接解构，响应性丢了
const { username, isLoggedIn } = useAuthStore()
</script>

<template>
  <span>{{ username }}</span>
</template>
```

登录成功后，`username` 在 store 里确实变了，但**页面上还是空的**，刷新一下才显示。

原因：`store` 本身是个响应式对象，但 `username` 在 store 里是一个 `ref`。
直接解构拿到的是那个 `ref` 里**当前的值**（一个字符串），
后面的变化和这个字符串没有关系了 —— 解构把"响应式连接"切断了。

正确做法是用 `storeToRefs`：

```vue [components/TopNav.vue]
<script setup>
import { storeToRefs } from 'pinia'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()

// ✓ 用 storeToRefs 解构出的是 ref，响应性保持
const { username, isLoggedIn } = storeToRefs(authStore)
</script>

<template>
  <span>{{ username }}</span>
  <span v-if="isLoggedIn">已登录</span>
</template>
```

::: warning `storeToRefs` 只处理状态，不处理方法
`storeToRefs` 会把 store 里的 `ref`、`computed` 转成 ref，但**函数会被跳过**。

所以常见写法是：**状态用 `storeToRefs` 解构，方法直接 `store.方法名` 调用**：

```js
const authStore = useAuthStore()
const { username, isLoggedIn } = storeToRefs(authStore) // 状态
// 方法不解构，直接调
authStore.logout()
```

如果写成 `const { logout } = authStore` 也能跑，但方法一旦被解构出来单独调用，
`this` 指向会丢（组合式写法里其实没这个问题，但仍建议统一用 `authStore.logout()`，更清楚数据来自哪个 store）。
:::

### 什么时候不需要 `storeToRefs`

如果只是取一个值用一下，**直接用就行**：

```js
const authStore = useAuthStore()
console.log(authStore.token) // ✓ 这样读是响应式的，没问题
```

`storeToRefs` 是**为了配合解构**才存在的。不写解构，就不需要它。

在模板里也不一定需要解构：

```vue [TopNav.vue（另一种写法）]
<script setup>
import { useAuthStore } from '@/stores/auth'
const authStore = useAuthStore()
</script>

<template>
  <!-- ✓ 直接点出来也是响应式的 -->
  <span>{{ authStore.username }}</span>
</template>
```

## getters 与 computed 的差别

组合式写法里，store 的 "getters" 就是普通的 `computed`，**没有语法差别**。
真正需要分清的是**什么时候用 `computed`、什么时候用函数**：

| 写法 | 特点 | 什么时候用 |
| --- | --- | --- |
| `computed(() => ...)` | 有缓存，依赖不变就不重算 | 从状态派生出的值：`isLoggedIn`、`count`、`filteredList` |
| 普通函数 | 每次调用都执行 | 需要传参的计算：`getActivityById(id)`、`canSignup(activity)` |

举例：活动列表要"按状态筛选"，用 `computed`；要"按 id 找某一条"，用函数。

```js [stores/activity.js]
export const useActivityStore = defineStore('activity', () => {
  const list = ref([])

  // ✓ 无参派生 → computed，有缓存
  const total = computed(() => list.value.length)

  // ✓ 带参数的查找 → 普通函数，每次现算
  function getById(id) {
    return list.value.find((item) => item.id === id)
  }

  return { list, total, getById }
})
```

::: warning 把带参数的写成 computed 是错的
`computed(() => list.value.find((i) => i.id === id))` 里的 `id` 从哪来？
computed 不接受调用时传参，硬写只能在外面再套一层函数，反而绕。**带参数就用普通函数。**
:::

## actions 里发请求怎么写

actions 的职责是"改状态"，而改状态往往要先发请求。基本模式是三步：
**置加载态 → 请求 → 成功写数据、失败记错误 → 无论成败收加载态**。

```js [stores/activity.js]
import { ref } from 'vue'
import { defineStore } from 'pinia'
import { getActivityListApi } from '@/api/activity'

export const useActivityStore = defineStore('activity', () => {
  const list = ref([])
  const loading = ref(false)
  const error = ref('')

  async function fetchList(params) {
    loading.value = true
    error.value = ''
    try {
      const res = await getActivityListApi(params)
      list.value = res.list
      return res // 需要分页总数等附加信息时返回出去
    } catch (e) {
      // 错误信息留给页面展示，store 只负责记录
      error.value = e.message || '加载失败'
      throw e // 继续往上抛，页面可以选择再处理
    } finally {
      // ✓ finally 保证无论成功失败都收掉加载态
      loading.value = false
    }
  }

  return { list, loading, error, fetchList }
})
```

这里有两个决定要想清楚：

1. **错误要不要往上抛？** 如果页面需要"失败时弹一个重试按钮"，就要 `throw`；
   如果请求层已经统一提示了，store 里可以不抛，只记状态。
   本课程的做法是**抛出去，让页面决定怎么展示** —— 见 [10.5 错误分层](/unit10/05-error-handling)。
2. **加载态放 store 还是放页面？** 如果只有列表页用这次请求，`loading` 其实该放页面里。
   放进 store 是因为"加载态也要跨组件共享"（比如筛选组件也要知道列表在加载）。

::: tip `finally` 不是可选项
用 `try / catch` 但忘了 `finally`，请求失败时 `loading` 会永远停在 `true`，
页面上转圈转到底。**凡是开加载态，就必须有对应的关闭。**
:::

## 跨模块调用怎么写

活动列表模块要用到登录用户（请求参数里要带角色，或者权限判断），
于是它需要调用 `useAuthStore()`。**写法有讲究**：

```js [stores/activity.js]
import { defineStore } from 'pinia'
import { useAuthStore } from './auth'

export const useActivityStore = defineStore('activity', () => {
  // ✓ 在 store 内部（函数体内）调用，此时 Pinia 已经装好了
  const authStore = useAuthStore()

  function canCreate() {
    return authStore.isReviewer === false
  }

  return { canCreate }
})
```

再看错误的写法：

```js [stores/activity.js（反例）]
import { defineStore } from 'pinia'
import { useAuthStore } from './auth'

// ✗ 在模块顶层调用。此时应用还没 createPinia()，会直接报错
const authStore = useAuthStore()

export const useActivityStore = defineStore('activity', () => {
  // ...
})
```

报错长这样：

```text
getActivePinia() was called but there was no active Pinia. Did you forget to install pinia?
```

**原因**：`import` 是在模块被加载时立即执行的，而模块加载发生在 `createApp` 之前或过程中，
那时候 `app.use(createPinia())` 还没跑，Pinia 没有"当前实例"。
把它写进 `defineStore` 的回调里，调用发生在组件真正使用 store 的时候，
Pinia 早就装好了。

::: details 如果两个 store 互相引用怎么办
`auth` 里要用 `activity`，`activity` 里又要用 `auth`，写成一进一出的循环引用。

做法：**都放在各自的函数内部延迟调用**，不要在任何一边的顶层调用。
真出现循环依赖报错时，可以把其中一个改成"用到的时候才 `useXxxStore()`"：

```js
function doSomething() {
  const authStore = useAuthStore() // 调用时才取，避开加载期的循环
  // ...
}
```
:::

## 实战：活动列表的状态模块

把上面这些拼起来，写一个活动列表模块。需求：

- 存筛选条件（关键词、状态、分页）
- 存列表数据与总条数
- 存加载态与错误信息
- 提供"取列表""改筛选条件并重新取""重置筛选"

```js [src/stores/activity.js]
import { ref, computed, reactive } from 'vue'
import { defineStore } from 'pinia'
import { getActivityListApi } from '@/api/activity'

export const useActivityStore = defineStore('activity', () => {
  // ---- 筛选条件：用一个 reactive 对象装，改起来清晰 ----
  const filters = reactive({
    keyword: '',
    status: '', // '' 全部 | 'draft' 草稿 | 'signing' 报名中 | 'closed' 报名截止 | 'ended' 已结束
    page: 1,
    pageSize: 10
  })

  // ---- 列表数据 ----
  const list = ref([])
  const total = ref(0)
  const loading = ref(false)
  const error = ref('')

  // ---- 派生值 ----
  const isEmpty = computed(() => !loading.value && list.value.length === 0)
  const pageCount = computed(() => Math.ceil(total.value / filters.pageSize))

  // ---- 动作 ----
  async function fetchList() {
    loading.value = true
    error.value = ''
    try {
      // 传副本出去，避免外部改到 filters
      const res = await getActivityListApi({ ...filters })
      list.value = res.list
      total.value = res.total
    } catch (e) {
      error.value = e.message || '活动列表加载失败'
    } finally {
      loading.value = false
    }
  }

  // 改筛选条件后要回到第一页再请求
  function setFilter(key, value) {
    filters[key] = value
    if (key !== 'page') {
      filters.page = 1
    }
    return fetchList()
  }

  function resetFilter() {
    filters.keyword = ''
    filters.status = ''
    filters.page = 1
    return fetchList()
  }

  return {
    filters, list, total, loading, error,
    isEmpty, pageCount,
    fetchList, setFilter, resetFilter
  }
})
```

页面里这样用：

```vue [views/ActivityListView.vue]
<script setup>
import { onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useActivityStore } from '@/stores/activity'

const activityStore = useActivityStore()
// ✓ 状态解构出来保持响应性
const { list, total, loading, error, isEmpty } = storeToRefs(activityStore)

onMounted(() => {
  activityStore.fetchList()
})
</script>

<template>
  <p v-if="loading">加载中…</p>
  <p v-else-if="error">加载失败：{{ error }}</p>
  <p v-else-if="isEmpty">还没有活动</p>
  <ul v-else>
    <li v-for="item in list" :key="item.id">{{ item.title }}</li>
  </ul>
</template>
```

::: tip 这个模块还缺什么
它还缺两样，后面两节补上：
- **持久化**：刷新后筛选条件要还在（[10.3](/unit10/03-persist)）。
- **请求走统一请求层**：`getActivityListApi` 内部应该用封装好的 axios 实例（[10.4](/unit10/04-request-layer)）。
:::

## 小结

- Pinia 两种写法：选项式（`state` / `getters` / `actions`）与组合式（`ref` / `computed` / 函数）。
  本课程统一用组合式。
- 组合式写法里，**没 `return` 的东西外部拿不到**。
- 解构状态一定要用 `storeToRefs`，直接解构会丢响应性；方法不解构。
- 无参派生用 `computed`，带参数的查找用普通函数。
- actions 里发请求用 `try / catch / finally`，`finally` 负责收加载态。
- 跨模块调用必须在函数体内 `useXxxStore()`，不能在模块顶层调用。

## 常见坑

::: details 坑 1：解构后页面不更新
现象：`const { username } = useAuthStore()`，登录后页面不显示用户名，刷新才出现。

原因：直接解构丢响应性。

怎么处理：`const { username } = storeToRefs(useAuthStore())`。
如果只需要读不需要解构，直接 `authStore.username` 也是响应式的。
:::

::: details 坑 2：在模块顶层调用 `useAuthStore()`
现象：控制台报 `getActivePinia() was called but there was no active Pinia`。

原因：模块加载发生在 `createPinia()` 之前。

怎么处理：把调用挪进 `defineStore` 的 setup 函数体内，或挪进具体的函数里。
:::

::: details 坑 3：`state` 写成了对象而不是函数
现象（选项式写法）：两个页面里读到的 store 数据互相串。

原因：`state: { token: '' }` 会让所有使用方共享同一个状态对象。

怎么处理：写成 `state: () => ({ token: '' })`。组合式写法没有这个问题。
:::

::: details 坑 4：忘了 `return`
现象：`store.something` 是 `undefined`，但它明明在 store 文件里定义了。

原因：组合式写法必须显式 `return`。

怎么处理：检查 `return` 那一行。**建议把 `return` 写在文件最后，
和上面的定义一一对照**，避免漏。
:::

::: details 坑 5：改了 store 里的对象状态，页面没反应
现象：`filters.keyword = 'x'` 改了，但 `computed` 没重算。

原因：有可能你改的不是 store 里的那个对象，而是 `storeToRefs` 解构出来的副本
（对 `ref` 解构要用 `.value`，对 `reactive` 是同一个引用）。

怎么处理：改状态时**统一通过 store 的方法改**，不要在组件里直接戳 store 的字段。
这也是"改数据只有一个入口"的好处。
:::

## 课后练习

::: details 练习 1：把选项式改成组合式
把本节开头那段选项式的 `auth` store 改写成组合式写法，功能完全一致。

**参考思路**：逐行对应 ——
`state` 里的每个字段变成 `ref`，`getters` 变成 `computed`，`actions` 变成 `async function`，
最后 `return` 出所有对外的东西。改完跑一遍登录、退出，确认行为没变。
:::

::: details 练习 2：给报名审核模块写一个状态模块
报名记录有字段：学生姓名、学号、活动标题、审核状态（待审核 / 通过 / 拒绝）。
按活动列表模块的做法，写一个 `useSignupStore`：

- 状态：报名列表、总数、筛选条件（活动 ID、审核状态、页码）、加载态、错误信息
- 动作：取列表、通过某条报名、拒绝某条报名、按审核状态筛选
- 派生：待审核条数

**参考思路**：注意"通过/拒绝"是写操作，成功后要**只更新那一条记录的状态**，
而不是重新拉整页列表（除非列表数据依赖后端计算）。
想一想：哪种做法更不容易出错？
:::

::: details 练习 3：找出一处跨模块调用的错误写法
下面这段代码有什么问题？改对，并解释为什么。

```js
import { defineStore } from 'pinia'
import { useAuthStore } from './auth'

const authStore = useAuthStore() // ← 问题在这里

export const useActivityStore = defineStore('activity', () => {
  const canCreate = () => !authStore.isReviewer
  return { canCreate }
})
```

**参考思路**：说清楚"模块加载时机"和"Pinia 安装时机"的先后关系。
改法是把 `useAuthStore()` 挪进 `defineStore` 回调里。
:::

---

上一节：[10.1 什么时候需要全局状态](/unit10/01-when-global) ·
下一节：[10.3 状态持久化](/unit10/03-persist)
