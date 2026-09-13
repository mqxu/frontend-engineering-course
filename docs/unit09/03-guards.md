# 9.3 路由守卫

## 未登录的人，为什么能直接进后台

路由配好了，页面能跳了。但马上有个问题：

登录页只是个页面，它**没有任何强制力**。用户完全可以在地址栏直接输入 `/activities`，
绕过登录直接进入活动列表 —— 因为路由表只写了“这个地址显示哪个组件”，
没写“什么条件下才允许显示”。

再往下想，还有好几类需要拦截的情况：

- 未登录访问受限页面 → 挡回登录页。
- 已登录却访问登录页 → 直接送进首页，别让他重复登录。
- 审核员访问“用户管理” → 告诉他没权限（403），而不是白屏。
- 页面还没保存就离开 → 提示“有未保存的修改，确定离开吗？”。

这些“在跳转前后做判断与拦截”的逻辑，统一叫**导航守卫**。

::: tip 守卫的本质
守卫是一个**在跳转过程中的检查点**。你可以读取“要去哪、从哪来”，
然后决定：放行、拦下、还是改道去别的地方。

它不改变页面长什么样，只决定**这次跳转能不能发生、要不要换成别的目的地**。
:::

## 四种守卫与执行顺序

守卫按作用范围分四类：

| 类型 | 写在哪 | 数量 | 典型用途 |
| --- | --- | --- | --- |
| 全局前置 `beforeEach` | 路由实例上 | 多个，按注册顺序执行 | 登录判断、权限校验 |
| 全局解析 `beforeResolve` | 路由实例上 | 多个 | 等异步数据准备好再放行 |
| 路由独享 `beforeEnter` | 某条路由配置里 | 每条路由一个 | 只针对某条路由的特殊校验 |
| 组件内 `beforeRouteEnter` / `beforeRouteUpdate` / `beforeRouteLeave` | 组件里 | 每个组件 | 离开未保存表单时提示 |

### 完整执行时序

一次从 `/activities` 跳到 `/activities/12` 的完整过程：

```text
① 导航被触发（点击链接 / router.push / 地址栏变化）
        ↓
② 在失活组件里调用 beforeRouteLeave
        ↓
③ 调用全局 beforeEach
        ↓
④ 在重用的组件里调用 beforeRouteUpdate（仅当组件被复用时）
        ↓
⑤ 调用路由独享 beforeEnter（只对进入的路由）
        ↓
⑥ 解析异步路由组件（() => import(...) 在这一步下载）
        ↓
⑦ 在被激活的组件里调用 beforeRouteEnter
        ↓
⑧ 调用全局 beforeResolve
        ↓
⑨ 导航被确认
        ↓
⑩ 调用全局 afterEach
        ↓
⑪ 触发 DOM 更新
        ↓
⑫ 调用 beforeRouteEnter 传给 next 的回调（此时组件实例已创建）
```

记法：**“离开 → 全局前置 → 独享 → 进入 → 全局解析 → 确认 → 全局后置”。**

::: warning 任何一步中断，后面的都不执行
守卫里返回 `false` 或者跳转到别处，导航就**当场中止** ——
后面的守卫、组件加载、`afterEach` 全部不会执行。

所以顺序的意义在于：**想尽早拦下的检查，就写在越靠前的位置。**
登录判断放 `beforeEach`（第 ③ 步），就能在下载页面代码之前把用户挡回去 ——
不用为一个看不了的页面白下载一个 chunk。
:::

## 全局前置守卫 beforeEach

```js [src/router/index.js]
import router from './index'

router.beforeEach((to, from) => {
  // to：即将进入的目标路由对象
  // from：当前正要离开的路由对象
  // 返回值决定这次导航的结果
})
```

### 返回值规则

| 返回什么 | 结果 |
| --- | --- |
| `false` | **中断**这次导航，地址不变 |
| 一个路由地址（字符串 / 对象） | **改道**，跳到那个地址 |
| `undefined` 或 `true` | **放行**，继续后面的流程 |

```js [三种返回的写法]
router.beforeEach((to, from) => {
  // 1. 中断：留在原地
  if (isDoingSomethingImportant()) return false

  // 2. 改道：去别的地方
  if (!isLoggedIn() && to.meta.requiresAuth) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }

  // 3. 放行：不写 return，或 return true
})
```

::: danger 不要“又 return false 又跳转”
```js
// ✗ 这样写，跳转会被 false 取消
if (!isLoggedIn()) {
  router.push('/login')
  return false
}
```

`router.push` 发出的新导航同样要走过守卫，而且和当前这次导航会打架，
容易出现“跳了一次又弹回来”。**改道必须用 return 一个地址的方式**，
让路由器统一处理：

```js
// ✓
if (!isLoggedIn()) {
  return { name: 'login', query: { redirect: to.fullPath } }
}
```
:::

### 在守卫里做登录判断

这是最常见的用法。完整的逻辑要覆盖几个分支：

```js [src/router/guards.js]
import { useAuth } from '@/stores/auth'

export function setupGuards(router) {
  router.beforeEach((to) => {
    const auth = useAuth()

    // 1. 目标路由是否要求登录？
    const requiresAuth = to.meta.requiresAuth !== false   // 默认都要登录

    if (requiresAuth && !auth.isLoggedIn) {
      // 没登录，去登录页，并记住原来要去哪
      return {
        name: 'login',
        query: { redirect: to.fullPath }
      }
    }

    // 2. 已登录还去登录页？直接送去首页
    if (to.name === 'login' && auth.isLoggedIn) {
      return { name: 'activity-list' }
    }

    // 3. 有角色要求时判断角色
    const roles = to.meta.roles
    if (roles && roles.length > 0) {
      const allowed = roles.includes(auth.role)
      if (!allowed) {
        return { name: 'forbidden' }   // 403 页面
      }
    }

    // 4. 其余情况放行
  })
}
```

`to.fullPath` 是**带查询参数的完整路径**，比如 `/activities?page=2`。
用它做 `redirect`，用户登录后能被送回到“原来看的那个筛选结果”，
而不是笼统的 `/activities`。

::: tip `meta.requiresAuth !== false` 这种写法
这样写的含义是“**默认需要登录，只有显式写了 `requiresAuth: false` 的才公开**”。

这比反过来（默认公开、要登录的加 `requiresAuth: true`）更安全：
新加一条路由时如果忘了标，默认是受保护的，不会不小心把页面暴露出去。

**安全判断的默认值，要选“更严格”的那一个。**
:::

## afterEach 适合做什么

`afterEach` 在**导航已经确认之后**执行，不能再改变导航结果（返回什么都没用）。

```js [src/router/guards.js]
router.afterEach((to, from) => {
  // 1. 关闭顶部的加载进度条
  NProgress.done()

  // 2. 设置页面标题
  document.title = to.meta.title ? `${to.meta.title} · 校园活动服务平台` : '校园活动服务平台'

  // 3. 埋点：记录用户访问了哪个页面
  reportPageView(to.fullPath)
})

// 导航开始时打开进度条
router.beforeEach(() => {
  NProgress.start()
})
```

它适合做**“导航已经发生”之后的收尾工作**：关进度条、改标题、上报埋点、记日志。
这些事不影响跳转结果，放在 `afterEach` 最合适。

::: warning 别在 afterEach 里跳转
`afterEach` 里再调 `router.push` 会造成新的导航，容易形成循环。
**改道要在 `beforeEach` 或 `beforeResolve` 里做。**
:::

## beforeResolve 与 beforeEach 的差别

两者都在导航确认之前执行，都能改道或中断。差别在**时机**：

| 对比项 | `beforeEach` | `beforeResolve` |
| --- | --- | --- |
| 执行位置 | 第 ③ 步，很早 | 第 ⑧ 步，很晚 |
| 异步组件是否已加载 | 还没有 | 已经加载完 |
| 组件内钩子是否已跑 | 还没跑 | `beforeRouteEnter` 已跑 |
| 典型用途 | 登录 / 权限校验 | 等所有异步数据就绪再放行 |

**一句话**：`beforeEach` 适合“早在没人知道这个页面长什么样的时候就该判断的”事
（登录、权限）；`beforeResolve` 适合“等一切都准备好了，最后再确认一下”的事
（比如确保全局数据加载完成）。

日常开发里 **90% 的守卫逻辑写在 `beforeEach`**，`beforeResolve` 用得很少。
先把这个比例记住，别为了用而用。

::: details 为什么 beforeResolve 里能拿到的是“已经加载好的组件”
因为第 ⑥ 步已经解析了异步路由组件。这带来一个实际差别：
**在 `beforeResolve` 里中断导航，已经白下载了那个页面的代码；在 `beforeEach` 里中断则不会。**

这也是为什么登录判断要尽量早 —— 让未登录的用户不去下载他看不了的页面。
:::

## 守卫里的异步操作

真实场景里，“是否登录”往往不能只看本地有没有 token，还要**用 token 去请求用户信息**，
确认它还有效。这是一个异步操作。

```js [异步守卫]
router.beforeEach(async (to) => {
  // await 之后，导航会等待这个 Promise resolve 再继续
  const ok = await checkSession()
  if (!ok) return { name: 'login' }
})
```

守卫可以是 `async` 函数，返回一个 Promise，路由器会等它完成。
但这里有一个**必须避开的坑**。

### 死循环的坑

```js [✗ 死循环]
router.beforeEach(async (to) => {
  const user = await fetchCurrentUser()

  // 没拿到用户 → 去登录页
  if (!user) return { name: 'login' }

  // “还没拉过用户信息就再拉一次” —— 这里漏了判断 to.name
  if (!hasLoadedUser()) return to.fullPath   // ✗ 返回当前路径 = 重新触发导航
})
```

问题在于最后那句 `return to.fullPath`：**返回一个地址就等于发起一次新导航**，
新导航又会走一遍守卫，又返回同一个地址…… 无限循环，浏览器卡死。

解决办法：**跳转前先判断“是不是已经在目标页了”。**

```js [✓ 先判断再跳]
router.beforeEach(async (to) => {
  const auth = useAuth()

  // 已经在登录页了，就别再往登录页跳
  if (to.name === 'login') return true

  // 还没加载过用户信息，先加载
  if (!auth.loaded) {
    await auth.loadUser()

    // 加载过程中 token 可能失效了，这里要重新判断
    if (!auth.isLoggedIn) {
      return { name: 'login', query: { redirect: to.fullPath } }
    }
  }
})
```

::: tip 避免死循环的三条经验
1. **跳转前先看 `to`**：目标已经是那个页面，就别再跳。
2. **手动跳转要带“已处理”的标记**：比如加一个 `query: { redirected: '1' }`，
   守卫里看到这个标记就放行。
3. **异步只做一次**：用 `loaded` 标记，避免每次导航都重新请求用户信息。

**任何“守卫里跳转”的逻辑，写完都要亲自在浏览器里试一遍**
（尤其是刷新页面、直接手输地址进入这两种情况），确认不会卡住。
:::

::: details 什么时候用 beforeRouteLeave
组件内的离开守卫，最典型的用途是**拦住未保存的表单**：

```vue [src/views/ActivityEditView.vue]
<script setup>
import { onBeforeRouteLeave } from 'vue-router'

const form = ref({ /* … */ })
const dirty = ref(false)   // 有未保存的修改

onBeforeRouteLeave(() => {
  if (!dirty.value) return true
  return window.confirm('有未保存的修改，确定离开吗？')
})
</script>
```

`window.confirm` 返回 `true` / `false`，正好符合守卫的返回值约定。
用到自定义弹窗时要注意：守卫需要同步返回值，而弹窗是异步的，
要用 `return new Promise(...)` 或 `next` 回调的写法。
:::

## 小结

- 守卫是跳转过程中的检查点，决定“能不能去、要不要改道”，不改变页面内容。
- 四类守卫：全局 `beforeEach` / `beforeResolve`、路由独享 `beforeEnter`、组件内三个。
- 执行顺序：**离开 → 全局前置 → 独享 → 进入 → 全局解析 → 确认 → 全局后置**。
  任何一步返回 `false` 或改道，后面全部不执行。
- `beforeEach` 返回值：`false` 中断、返回地址改道、`undefined` / `true` 放行。
  **改道要用返回值，不要 `router.push` + `return false`。**
- 登录判断写在 `beforeEach`，越早拦下越省事（不用白下载页面代码）。
- `afterEach` 做收尾：关进度条、改标题、埋点，**别在这里跳转**。
- `beforeResolve` 与 `beforeEach` 的差别在时机：前者晚、异步组件已加载；
  日常 90% 的守卫逻辑写在 `beforeEach`。
- 异步守卫要防死循环：跳转前判断 `to`、异步只做一次、手动跳转带标记。

## 常见坑

::: details 坑 1：在守卫里 `router.push` 然后 `return false`
现象：跳转出现两次，或者弹回原页面。

原因：`push` 和本次导航打架。

处理：改成 `return { name: 'login' }`，让路由器统一处理。
:::

::: details 坑 2：守卫里无限循环，页面卡死
现象：浏览器转圈、控制台疯狂输出。

原因：无条件返回一个地址，形成“跳转 → 守卫 → 又跳转”。

处理：跳转前判断 `to.name` / `to.path` 是否已经是目标；异步加载加 `loaded` 标记。
:::

::: details 坑 3：`to.meta` 读不到子路由的配置
现象：子路由明明写了 `meta.requiresAuth`，守卫里却是 `undefined`。

原因：父路由有自己的 `meta`，子路由的 `meta` 不会自动合并到父级。
需要判断的是子路由时，要自己遍历 `to.matched` 检查每一层。

处理：如果所有后台页面都要登录，直接在父布局那条路由上统一标 `meta`，
或者在守卫里遍历：

```js
const requiresAuth = to.matched.some((r) => r.meta.requiresAuth !== false)
```
:::

::: details 坑 4：跳转到登录页时丢了原地址
现象：登录成功后回到了首页，而不是用户本来要去的页面。

原因：守卫里 `return '/login'` 没带 `redirect`。

处理：`return { name: 'login', query: { redirect: to.fullPath } }`，
登录成功后读 `route.query.redirect` 跳过去。**这是 9.4 的链路里的一环。**
:::

::: details 坑 5：页面标题没变
现象：所有页面标题都一样。

原因：标题设置散落在各页面里，或者压根没写。

处理：统一在 `afterEach` 里从 `to.meta.title` 读并设置。集中一处，不会漏。
:::

## 课后练习

::: details 练习 1：画出一次跳转的完整时序
不看上面的内容，画出从 `/activities` 跳到 `/activities/12` 的守卫执行顺序，
并标出“异步组件在第几步加载”。

**思路**：按“离开 → 全局前置 → 独享 → 进入 → 全局解析 → 确认 → 后置”的顺序写，
每一步标上属于哪一类守卫。写完对照本节开头的时序图。
:::

::: details 练习 2：实现未登录拦截与已登录回跳
实现：未登录访问受限页面跳登录页并带上 `redirect`；已登录访问登录页自动跳首页。

**思路**：两个分支都写在 `beforeEach` 里。注意第 2 个分支要先判断 `to.name === 'login'`，
否则会死循环。
:::

::: details 练习 3：加一个 403 分支
给需要特定角色的路由加 `meta.roles`，不是该角色时跳到 403 页面。

**思路**：`to.meta.roles?.includes(auth.role)` 不成立就 `return { name: 'forbidden' }`。
注意 403 页面本身要有权限访问（`meta.requiresAuth: false` 或至少角色不限），
否则会被自己的守卫再拦一次。
:::

---

上一节：[9.2 动态参数与嵌套路由](/unit09/02-nested-params) ·
下一节：[9.4 登录鉴权完整链路](/unit09/04-auth-flow)
