# 9.1 路由基础

## 地址栏变了，页面为什么不刷新

先做一个对比。这是传统多页应用的跳转过程：

```text
点击“活动详情”链接
→ 浏览器向服务器请求 /activities/12
→ 服务器返回一份完整的 HTML（含页面框架、样式、脚本）
→ 浏览器丢掉当前页面，重新解析、渲染
→ 页面白一下，然后出现
```

这是单页应用（SPA）的跳转过程：

```text
点击“活动详情”链接
→ 浏览器不发请求，只是地址栏变成 /activities/12
→ 前端代码监听到地址变化
→ 把 <RouterView> 里的内容换成“活动详情组件”
→ 页面不重建，只换了中间一块
```

**关键差别在这里：单页应用里，地址不再由服务器解释，而是由前端代码自己解释。**

浏览器地址栏那个字符串，本身只是一个文本。谁来读它、根据它显示什么，
在单页应用里完全由你决定。这就是**路由**要做的事：**建立“地址 → 组件”的对应关系，
并在地址变化时切换组件。**

::: tip 为什么这件事很重要
没有路由，用户做不到三件事：

1. **分享链接** —— 他没法把“活动 12 的详情页”发给同事。
2. **刷新页面** —— 一刷新回到首页，因为他当前在哪个页面只存在内存里。
3. **前进后退** —— 浏览器历史栈里什么都没有。

路由把这些“浏览器本来就该有”的能力还给你。它不是可选的锦上添花，
而是一个多页面应用的基础设施。
:::

## 安装与基础配置

```bash [安装]
pnpm add vue-router
```

```js [src/router/index.js]
import { createRouter, createWebHistory } from 'vue-router'
import ActivityListView from '@/views/ActivityListView.vue'

const router = createRouter({
  // 用哪种“地址模式”，这一节最后会细讲
  history: createWebHistory(),
  routes: [
    {
      path: '/activities',
      name: 'activity-list',
      component: ActivityListView
    }
  ]
})

export default router
```

挂到应用上：

```js [src/main.js]
import { createApp } from 'vue'
import App from './App.vue'
import router from './router'

const app = createApp(App)
app.use(router)
app.mount('#app')
```

`app.use(router)` 之后，全应用才能用 `<RouterView>`、`<RouterLink>`、`useRoute` 这些能力。

## 路由表的结构

一条路由就是一份配置。字段不多，但每个都有用：

```js [src/router/index.js]
{
  path: '/activities/:id',        // ① 匹配的地址，:id 是动态参数
  name: 'activity-detail',        // ② 路由名，跳转时用它比用路径更稳
  component: () => import('@/views/ActivityDetailView.vue'),  // ③ 渲染哪个组件
  props: true,                    // ④ 把参数作为 props 传给组件（下一节讲）
  meta: {                          // ⑤ 自定义信息，守卫里能读到
    title: '活动详情',
    requiresAuth: true,
    roles: ['organizer', 'reviewer']
  },
  redirect: '/login',             // ⑥ 重定向
  children: []                    // ⑦ 嵌套子路由（下一节讲）
}
```

| 字段 | 作用 | 什么时候一定要写 |
| --- | --- | --- |
| `path` | 匹配规则 | 每条都要 |
| `name` | 路由名 | 建议都写，跳转时用它 |
| `component` | 渲染的组件 | 叶节点路由要；有 `children` 的可以只写 `<RouterView>` 容器 |
| `props` | 参数转 props | 想让组件像普通组件一样收参数时 |
| `meta` | 附加信息 | 需要在守卫里读标题 / 权限时 |
| `redirect` | 重定向 | 访问旧地址要跳新地址时 |
| `children` | 子路由 | 页面里有公共布局时 |
| `alias` | 别名 | 同一页面要用多个地址访问时 |

::: tip `name` 有什么用
用 `router.push({ name: 'activity-detail', params: { id: 12 } })` 跳转，
比 `router.push('/activities/12')` 更安全 —— 以后路径规则改了（比如从 `/activities`
改成 `/activity`），用名字的地方一行都不用改。

**约定：每条路由都给一个 `name`，跳转尽量用名字。** 路径只在路由表里写一次。
:::

## RouterView 与 RouterLink

### RouterView：内容占位

`<RouterView>` 是一个占位符。当前地址匹配到哪个组件，就把它渲染在这里。

```vue [src/App.vue]
<template>
  <RouterView />
</template>
```

嵌套路由里可以有多层 `<RouterView>`，下一节讲。

### RouterLink：导航链接

```vue [src/components/AppMenu.vue]
<template>
  <nav>
    <RouterLink to="/activities">活动管理</RouterLink>
    <RouterLink :to="{ name: 'activity-detail', params: { id: 12 } }">活动 12</RouterLink>
  </nav>
</template>
```

### 它和普通 `<a>` 的区别

| 对比项 | `<a href="/activities">` | `<RouterLink to="/activities">` |
| --- | --- | --- |
| 点击后行为 | 浏览器向服务器发请求，整页刷新 | 前端接管，只切换组件，不刷新 |
| 能否记住当前应用状态 | 不能，整页重建 | 能，其他部分不受影响 |
| active 样式 | 无 | 自动加 `router-link-active` / `router-link-exact-active` |
| 历史记录 | 记录一条 | 记录一条（效果一样） |
| 何时该用 | 跳到**外部站点**、下载文件 | 应用内部跳转 |

```html
<!-- ✓ 应用内部用 RouterLink -->
<RouterLink to="/signup-review">报名审核</RouterLink>

<!-- ✓ 跳外部站点用普通 a -->
<a href="https://vuejs.org" target="_blank" rel="noopener">Vue 官网</a>
```

`RouterLink` 渲染出来其实还是 `<a>` 标签（默认），只是点击事件被前端拦下了。

::: tip active 类的两种
- `router-link-active`：**包含匹配**。地址是 `/activities/12` 时，指向 `/activities` 的链接
  也算 active。适合做“父级菜单高亮”。
- `router-link-exact-active`：**精确匹配**。只有地址完全一致才算。

默认会同时加这两个。做菜单高亮时经常要精确匹配，可以在样式里用后者。
:::

## 编程式导航

用户点链接是“声明式导航”；在代码里主动跳转叫“编程式导航”。
用 `useRouter()` 拿到路由器实例：

```vue [src/views/LoginView.vue]
<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()

async function onSubmit() {
  await login(form)
  // 跳转到活动列表
  router.push('/activities')
}
</script>
```

三个常用方法：

| 方法 | 作用 | 什么时候用 |
| --- | --- | --- |
| `router.push(path)` | 跳转，**新增**一条历史记录 | 用户主动点击、表单提交后跳转 |
| `router.replace(path)` | 跳转，**替换**当前历史记录 | 登录成功后跳首页（不想让用户回退到登录页） |
| `router.back()` | 返回上一页，等价 `router.go(-1)` | “返回”按钮 |

```js [三种跳转的差别]
// 用户点“详情”进活动 12 → push
router.push({ name: 'activity-detail', params: { id: 12 } })
// 历史栈：[列表, 详情12]   按返回 → 回到列表 ✓

// 登录成功后 → replace
router.replace('/activities')
// 历史栈：[登录 → 被替换成 列表]   按返回 → 不会回到登录页 ✓

// 点“返回”按钮 → back
router.back()
```

::: warning 登录成功为什么必须用 `replace`
如果用 `push`，历史栈会变成 `[登录, 列表]`。用户在列表页按浏览器后退，
又回到了登录页 —— 但他已经登录了，这个页面没有意义。更糟的是，
如果登录页有“已登录自动跳走”的逻辑，就会和后退行为打架。

**凡是“跳转后不应该再回到这里”的场景，都用 `replace`**：登录成功、注册成功、
订单提交完成、404 页面里的“回首页”。
:::

::: details `router.go` 的用法
`router.go(n)` 在历史栈里前进或后退 `n` 步：`go(-1)` 是后退一步，
`go(1)` 是前进一步，`go(-2)` 后退两步。`go(0)` 是刷新当前页。

`back()` 就是 `go(-1)` 的别名。**日常用 `back()` 就够了**，`go` 只在需要跨多步时用。
:::

## 两种路由模式

`createRouter` 的 `history` 参数决定地址长什么样，有两种：

```js [history 模式：地址干净]
import { createWebHistory } from 'vue-router'
createRouter({ history: createWebHistory(), routes })
// 地址：https://example.com/activities/12
```

```js [hash 模式：地址带井号]
import { createWebHashHistory } from 'vue-router'
createRouter({ history: createWebHashHistory(), routes })
// 地址：https://example.com/#/activities/12
```

| 对比项 | history 模式 | hash 模式 |
| --- | --- | --- |
| 地址外观 | `example.com/activities/12` | `example.com/#/activities/12` |
| 是否美观 | 好看，像普通网址 | 带 `#`，略显老旧 |
| 刷新会不会 404 | **默认会**，需要服务器配置 | 不会 |
| 服务器要求 | 需要把所有路径都指向 `index.html` | 无特殊要求 |
| 部署到静态托管的难度 | 要配重写规则 | 直接传上去就能用 |

### history 模式刷新为什么 404

这是新手最常撞的一堵墙。原因在于：**服务器根本不知道 `/activities/12` 是什么。**

```text
1. 用户在首页，点了“活动详情”，地址变成 /activities/12
   —— 这是前端改的，服务器完全不知道

2. 用户按了 F5 刷新
   → 浏览器向服务器请求 /activities/12
   → 服务器一看：我这儿没有这个文件，也没有这个目录
   → 返回 404
```

`index.html` 只有一个，服务器只认识它。解决办法是**告诉服务器：
所有找不到的路径，都返回 `index.html`**，剩下的交给前端路由处理。

```nginx [nginx 配置示例]
location / {
  try_files $uri $uri/ /index.html;
}
```

意思是：先看有没有这个文件，再看有没有这个目录，都没有就返回 `index.html`。

::: warning 上线前一定要试一次刷新
开发时不会遇到这个问题 —— `vite dev` 的开发服务器已经帮你做了这个回退。
**所以这个坑通常在部署后才暴露。**

上线后必做的一步：在任意二级页面按 F5，看是不是 404。
[单元 12 的部署章节](/unit12/03-deploy)会给不同平台的配置方法。
:::

::: details 那选哪个模式
课程项目和实际项目都**优先用 history 模式**（地址干净、可分享、对搜索引擎友好），
并把服务器回退配置做好。

如果部署环境完全没法改服务器配置（比如只能传静态文件到某个简单托管，
平台又不提供重写规则），退而求其次用 hash 模式。**它是能用的，
只是地址里那个 `#` 会一直存在。**

一个判断方法：**如果你的应用需要“分享一个能直接打开的链接”，那 history 更合适。**
:::

## 小结

- 单页应用里地址由前端自己解释，路由负责建立“地址 → 组件”的对应关系，
  并带来分享、刷新、前进后退三项能力。
- `createRouter` 配置路由表，`app.use(router)` 装上；`RouterView` 是渲染占位。
- 路由字段：`path`、`name`、`component`、`props`、`meta`、`redirect`、`children`、`alias`。
  建议每条都写 `name`，跳转用名字。
- `RouterLink` 内部拦截点击、不刷新、自动加 active 类；跳外站才用普通 `<a>`。
- 编程式导航：`push` 新增历史、`replace` 替换、`back` 后退；
  登录成功这类“不该回退”的场景用 `replace`。
- history 模式地址干净但刷新会 404，需要服务器把所有路径回退到 `index.html`；
  hash 模式无此问题但地址带 `#`。
- 开发时刷新正常不代表线上正常，部署后必须手动验证一次。

## 常见坑

::: details 坑 1：`useRouter()` 返回 undefined
现象：`const router = useRouter()` 拿到 `undefined`，跳转报错。

原因：忘了 `app.use(router)`，或者 `useRouter` 在组件之外的模块顶层调用。

处理：确认 `main.js` 里装了路由；`useRouter` / `useRoute` **只能在 `setup` 里调用**，
不能在普通 `.js` 文件的顶层调用。要在模块里用，就从组件里传进去，或者用 `router` 实例
（`import router from '@/router'`）。
:::

::: details 坑 2：用 `router.push` 跳转后页面没变化
现象：地址变了，组件没换。

原因：多数是路径没匹配上任何一条路由，或者跳到了同一条路由的同一参数。

处理：检查路由表里的 `path` 拼写（`/activities/:id` 里别漏了冒号），
打开 Vue DevTools 看当前匹配到的是哪条路由。
:::

::: details 坑 3：部署后刷新页面 404
现象：本地好好的，线上刷新就 404。

原因：history 模式需要服务器回退到 `index.html`。

处理：配重写规则（nginx 用 `try_files`，Netlify / Vercel 用各自的重写配置文件），
或者改用 hash 模式。**上线后一定手动在二级页面刷新一次。**
:::

::: details 坑 4：`name` 重名
现象：跳转跳到了别的页面，或者控制台报“重复的路由名”。

原因：两条路由用了同一个 `name`。

处理：命名带上模块前缀，比如 `activity-list`、`activity-detail`、`signup-review`，
避免 `list`、`detail` 这种笼统的名字。
:::

## 课后练习

::: details 练习 1：为管理端设计第一批路由
写出登录页、活动列表、活动详情三条路由，要求：每条都有 `name`，
详情页用动态参数 `:id`，都加 `meta.title`。

**思路**：先写出路由表，再想 `meta` 里除了 `title` 还需要什么
（下一节的 `requiresAuth`）。注意 `name` 用“模块-动作”的命名方式。
:::

::: details 练习 2：对比 push 与 replace
写一个“提交订单 / 保存成功”的小例子，分别用 `push` 和 `replace` 跳转，
在浏览器里点后退，观察差别。

**思路**：打开浏览器开发者工具的历史面板，数一数历史记录条数。
总结出一句话：什么情况下必须用 `replace`。
:::

::: details 练习 3：把一个项目从 hash 改到 history
找一个你用过的 hash 模式项目，改成 history 模式，并说明部署时需要做什么配置。

**思路**：改 `createWebHashHistory` 为 `createWebHistory` 即可。
重点在部署：写出你所用托管平台需要的重写配置（不知道就查平台文档）。
:::

---

上一节：[单元导学](/unit09/) ·
下一节：[9.2 动态参数与嵌套路由](/unit09/02-nested-params)
