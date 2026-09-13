# 单元 9 课后练习

本单元的练习围绕“把多页面应用组织起来并加上鉴权”展开。**三道必做题，一道选做题。**

从这一单元开始，练习都要写进同一个项目仓库 —— 校园活动服务平台管理端。

## 必做题

### 练习 1 · 设计管理端的完整路由表

设计校园活动服务平台管理端的完整路由表，覆盖下面这些页面：

| 页面 | 地址建议 | 说明 |
| --- | --- | --- |
| 登录页 | `/login` | 不需要登录 |
| 后台布局 | `/` | 菜单 + 顶部栏 + 子级出口 |
| 活动列表 | `/activities` | 进菜单 |
| 活动详情 | `/activities/:id` | 不进菜单，`props: true` |
| 活动编辑 | `/activities/:id/edit` | 不进菜单，`props: true`，支持新建时用 `/activities/new` |
| 报名审核 | `/signup-review` | 进菜单 |
| 场次管理 | `/sessions` | 进菜单 |
| 数据看板 | `/dashboard` | 进菜单，限定角色 |
| 403 | `/403` | 不需要权限校验 |
| 404 | 兜底 | 放最后一条 |

**要求**：

1. 所有页面组件都用 `() => import(...)` 懒加载。
2. 每条路由都有 `name`，命名统一（模块-动作）。
3. 需要登录的页面标 `requiresAuth`（或按 9.4 的约定，默认都要登录，
   只有公开页面标 `public: true`）。
4. 数据看板标 `meta.roles`，限定 `admin` 与 `reviewer`。
5. 哪些页面进菜单用 `meta.menu` 标出来，不要靠“猜”。

**路由表结构示意**

```js [src/router/routes.js]
export const routes = [
  // 登录页、403、404 …（公开页面）
  {
    path: '/',
    component: () => import('@/layouts/AdminLayout.vue'),
    redirect: '/activities',
    children: [
      // 活动列表、活动详情、活动编辑、报名审核、场次管理、数据看板
    ]
  },
  // 404 兜底，放最后
  { path: '/:pathMatch(.*)*', name: 'not-found', component: () => import('@/views/NotFoundView.vue') }
]
```

**验收标准**

| 项目 | 要求 |
| --- | --- |
| 完整性 | 十个页面全部覆盖，含 403 与 404 |
| 嵌套正确 | 后台页面都在布局的 `children` 里，子路由 `path` 不以 `/` 开头 |
| 懒加载 | 每个页面都是 `() => import(...)`；构建后 `dist/assets/` 有多个 chunk |
| 命名 | 每条路由有 `name`，风格统一，无重名 |
| 元信息 | `meta` 里有 `title`，权限相关的页面有 `roles` 或 `requiresAuth` |
| 顺序 | 404 兜底在最后一条 |

::: details 提示：嵌套与 404 的关系
404 路由如果放进布局的 `children` 里，404 页面也会带上菜单和顶部栏。
两种都可以，取决于你想让 404 长什么样：

- **放在布局外**：404 是一个独立的干净页面，适合“整个地址都不对”的情况。
- **放在布局内**：用户还能看到菜单，方便他直接点回别的页面。

课程项目推荐**放在布局外**，逻辑更简单。想清楚你的选择并写进注释。
:::

### 练习 2 · 实现“登录后回到原地址”

实现完整流程：未登录访问受限页面 → 跳登录页 → 登录成功后回到原来要访问的页面。

**要求**：

1. 守卫里跳登录页时带上 `redirect`，值是 `to.fullPath`（含查询参数）。
2. 登录成功后读 `redirect` 并跳过去。
3. `redirect` 必须校验：只接受站内路径，其余用默认地址。
4. 用 `replace` 而不是 `push`，验证后退不会回到登录页。

**验收标准**

| 项目 | 要求 |
| --- | --- |
| 基本回跳 | 访问 `/activities/12?tab=signup`，登录后精确回到这个地址 |
| 带查询参数 | `redirect` 里的 `?page=2` 等参数不丢 |
| 安全性 | `?redirect=https://evil.com` 登录后**不**跳外站 |
| 无 redirect | 直接访问 `/login` 登录后进默认首页 |
| 后退行为 | 登录成功后按浏览器后退，不会回到登录页 |

::: warning 一个容易忽略的测试
在登录页手动把地址改成 `/login?redirect=//evil.com` 登录一次。
`//` 开头的是**协议相对地址**，某些浏览器的处理方式和 `https://` 一样，
会跳到外站。你的 `safeRedirect` 必须同时排除这种。
:::

### 练习 3 · 页面标题随路由变化

给路由加 `meta.title`，让浏览器标签页的标题随页面变化。

**要求**：

1. 在 `afterEach` 里统一设置标题，不要在各个页面里各写一遍。
2. 标题格式统一，比如 `活动管理 · 校园活动服务平台`。
3. 活动详情页的标题带上活动名（需要拿到数据后再更新）。

**接口示意**

```js [src/router/guards.js]
router.afterEach((to) => {
  const base = '校园活动服务平台'
  document.title = to.meta.title ? `${to.meta.title} · ${base}` : base
})
```

```js [详情页拿到数据后更新标题]
// 组件里数据回来后，再覆盖一次
watch(activity, (val) => {
  if (val) document.title = `${val.title} · 校园活动服务平台`
})
```

**验收标准**

| 项目 | 要求 |
| --- | --- |
| 集中设置 | 基础标题在 `afterEach` 里统一设置，页面里不重复写 |
| 格式统一 | 所有页面标题格式一致 |
| 动态标题 | 活动详情页标题里含活动名，不是写死的“活动详情” |
| 兜底 | 没写 `meta.title` 的页面显示默认标题，不是 `undefined` |

::: tip 为什么值得单独做这一件小事
这是一个很典型的“**一次性投入、长期受益**”的工程习惯。

如果每个页面各写一遍 `document.title = ...`，一定会有人忘。
集中在 `afterEach` 里做，新加页面只要在路由表里补一个 `meta.title`，标题自动就对。
**这类“有统一入口的地方，就别让人重复劳动”，是工程化思维的一部分。**
:::

## 选做题

### 练习 4 · 面包屑导航

从当前路由的 `matched` 数组推导面包屑。

**目标效果**

```text
活动管理 / 活动详情 / 编辑
```

**要求**：

1. 用 `route.matched` 拿到当前地址匹配到的**所有层级**的路由记录。
2. 每一级显示 `meta.title`，最后一级不可点击。
3. 中间层级可点击，跳转到对应的路由。
4. 没有 `meta.title` 的层级跳过（比如布局那条只有一个 `/` 的记录）。

**接口示意**

```vue [src/components/Breadcrumb.vue]
<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const items = computed(() =>
  route.matched
    .filter((r) => r.meta?.title)   // 跳过没有标题的层级
    .map((r) => ({
      name: r.name,
      title: r.meta.title,
      // 最后一级不可点击
      clickable: r.name !== route.name
    }))
)
</script>

<template>
  <nav class="breadcrumb">
    <template v-for="(item, i) in items" :key="i">
      <RouterLink v-if="item.clickable" :to="{ name: item.name }">{{ item.title }}</RouterLink>
      <span v-else>{{ item.title }}</span>
      <span v-if="i < items.length - 1" class="sep">/</span>
    </template>
  </nav>
</template>
```

**验收标准**

| 项目 | 要求 |
| --- | --- |
| 层级正确 | `/activities/12/edit` 显示三级，不是只显示当前页 |
| 可点击 | 中间层级能点，最后一级是纯文本 |
| 缺标题的层级 | 被跳过，不会显示空白项 |
| 首页兜底 | 直接进 `/activities` 时显示一级，不报错 |

::: details 提示：为什么用 matched 而不是自己拼
`route.matched` 是路由器算好的“当前地址经过了哪几层路由记录”，
**它就是面包屑的天然数据源**。

自己按 `/` 切分地址拼出来，会遇到动态参数（`/activities/12` 里 12 该显示成什么？）
和嵌套层级的问题，反而更麻烦。**用框架已经算好的结果，比自己重新推一遍可靠。**
:::

## 自检标准

本单元做完后逐条自查：

- [ ] 能说清单页应用为什么需要路由，以及它带来的三项能力
- [ ] 能区分类比动态参数与查询参数，说出各自的适用场景
- [ ] 能画出一次导航的守卫完整执行顺序
- [ ] 能说出 `push` 与 `replace` 的差别，并知道登录成功该用哪个
- [ ] 知道 history 模式刷新 404 的原因和解决办法
- [ ] 做到了路由懒加载，并在构建产物里看到了多个 chunk
- [ ] 实现了登录态恢复，且刷新时不闪
- [ ] 实现的权限判断菜单与路由一致，来自同一份数据
- [ ] 知道按钮级权限不能替代后端校验，能说清为什么
- [ ] 退出登录清干净了所有用户相关的状态

全部打勾，这个单元过关。

## 常见问题

::: details 路由表和菜单为什么要放在同一个文件里
不一定要同一个文件，但**必须是同一份数据**。

可以拆成两个文件：`routes.js` 定义路由表，`useMenu.js` 从路由表推导菜单。
关键是不能“路由写一份、菜单再手写一份” —— 两份数据一定会不同步。

判断方法：**改动权限规则时，需要改几个文件？** 一个就对了，两个就说明有重复。
:::

::: details 刷新闪一下登录页，但我已经把 restore 放进守卫了
按顺序排查：

1. `restore` 是不是真的在 `beforeEach` 的**同步执行路径**上被 `await` 了？
   如果写在了 `setTimeout` 或某个回调里，就不会阻塞导航。
2. `ready` 的判断是不是写反了？（`if (!auth.ready.value) await auth.restore()`）
3. 页面里有没有别的地方也依赖 `isLoggedIn` 提前渲染了？（比如布局里的用户信息区域）

先在守卫里 `console.log('restore start / end')`，看日志和页面渲染的先后顺序。
:::

::: details 登录接口返回的用户信息不够，怎么办
两种做法：

1. 登录接口只返回 token，登录成功后再调一次获取当前用户信息的接口。逻辑更清楚，
   用户信息只有一处来源。
2. 登录接口直接返回完整的用户信息，省一次请求。

课程项目推荐**第一种**：`restore` 和 `login` 都走同一个“获取当前用户信息”的接口，
用户信息的处理逻辑只有一处。
:::

::: details 为什么用模块级 ref 而不是 Pinia
`src/stores/auth.js` 用的是模块级 `ref`，和 [单元 8 的全局状态做法](/unit08/06-case-modal)一致。

好处是不依赖额外库、代码少、启动快。缺点是看不到 DevTools 的专门面板、
多个模块互相依赖时不如 Pinia 清楚。

**单元 10 会换成 Pinia**，到时候你会看到两种写法的对照。
先用简单的方式跑通，再理解更完整的方案，顺序更自然。
:::

---

上一节：[案例 10 · 登录与鉴权](/unit09/05-case-auth) ·
下一单元：[单元 10 · Pinia 与数据请求层](/unit10/)
