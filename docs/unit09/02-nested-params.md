# 9.2 动态参数与嵌套路由

## 两种“会变的地址”

管理端里有两类地址是会变的：

```text
/activities/12             ← 12 是活动 id，换一个 id 就是另一份活动
/activities?page=2&keyword=运动会   ← 页码和关键词是筛选条件
```

前者是**动态路由参数**（`params`），后者是**查询参数**（`query`）。
两者长得很像，都是“地址里带信息”，但用途完全不同。选错了会让代码别扭。

判断依据只有一条：

| 这个信息是…… | 用哪种 | 例子 |
| --- | --- | --- |
| **资源的唯一标识** —— 换掉它就是另一个东西 | 动态参数 `/:id` | `/activities/12` 里的 `12` |
| **列表的筛选条件** —— 换掉它还是同一类内容 | 查询参数 `?key=value` | `?page=2`、`?keyword=运动会` |

再翻译成两句话：

- **“我要看哪一个”用动态参数。** `/activities/12` 和 `/activities/13` 是两份不同的活动，
  路径本身就体现了“这是第 12 号资源”。
- **“我怎么看这一堆”用查询参数。** `/activities` 永远是活动列表，
  `?page=2` 只是它的第 2 页。

::: tip 一个实际的判断方法
问自己：**“这个地址能不能单独分享给别人，让他看到同样的东西？”**

- `/activities/12` 分享出去，对方看到活动 12 的详情 —— 合理，用动态参数。
- `/activities?page=2` 分享出去，对方看到列表第 2 页 —— 也合理。

再问：**“把它删掉，这个地址还成立吗？”**

- 去掉 `12`，`/activities` 仍然是有效地址（列表）→ 说明 `12` 是标识，用动态参数。
- 去掉 `?page=2`，`/activities` 也成立（默认第 1 页）→ 说明 `page` 是筛选，用查询参数。

两种都“还成立”，区别在于**语义**：一个是“哪一个”，一个是“怎么看”。
:::

## 动态路由参数

```js [src/router/index.js]
{
  path: '/activities/:id',
  name: 'activity-detail',
  component: () => import('@/views/ActivityDetailView.vue')
}
```

`:id` 是占位符，能匹配任意一段。`/activities/12`、`/activities/abc` 都能匹配，
`route.params.id` 分别是 `'12'` 和 `'abc'`。

多个参数就写多个：

```js [场次详情：活动 id + 场次 id]
{
  path: '/activities/:id/sessions/:sessionId',
  name: 'session-detail',
  component: () => import('@/views/SessionDetailView.vue')
}
```

### 读取参数：useRoute

```vue [src/views/ActivityDetailView.vue]
<script setup>
import { useRoute } from 'vue-router'

const route = useRoute()

// 动态参数在 route.params 里
console.log(route.params.id)   // '12'（注意是字符串）
</script>
```

`useRoute()` 返回的是**当前路由对象**，它是一个响应式对象。
地址变了，`route.params` 会跟着变。

::: warning 参数都是字符串
`route.params.id` 永远是字符串 `'12'`，不是数字 `12`。要比较或计算时手动转：

```js
const id = Number(route.params.id)   // ✓
// route.params.id === 12            // ✗ 永远为 false，'12' !== 12
```

查询参数更是如此，**所有 query 值都是字符串**，见下面。
:::

### 用 props 接收参数

`useRoute` 能用，但组件和路由强耦合了 —— 这个组件只能在路由环境里跑。
更好的做法是打开 `props: true`，让参数变成普通的 props：

```js [src/router/index.js]
{
  path: '/activities/:id',
  name: 'activity-detail',
  component: () => import('@/views/ActivityDetailView.vue'),
  props: true   // 把 route.params 作为 props 传给组件
}
```

```vue [src/views/ActivityDetailView.vue]
<script setup>
// 和普通组件一模一样，不依赖 useRoute
const props = defineProps({
  id: { type: String, required: true }
})
</script>
```

好处很直接：**组件不知道自己在路由里**，可以单独测试、单独预览，
也可以在别的页面里直接 `<ActivityDetail id="12" />` 用。

需要类型转换或改名时，用函数形式：

```js [props 用函数形式自己组装]
{
  path: '/activities/:id',
  component: () => import('@/views/ActivityDetailView.vue'),
  props: (route) => ({
    activityId: Number(route.params.id),   // 转成数字
    tab: route.query.tab || 'info'         // query 也给一个
  })
}
```

## 查询参数

```text
/activities?page=2&keyword=运动会&status=open
```

```vue [src/views/ActivityListView.vue]
<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

// 读取：注意全部是字符串
const page = computed(() => Number(route.query.page) || 1)
const keyword = computed(() => route.query.keyword || '')
const status = computed(() => route.query.status || 'all')

// 修改：改 query 时建议整份替换，避免残留旧参数
function changePage(next) {
  router.push({
    query: { ...route.query, page: next }
  })
}

function reset() {
  router.push({ query: {} })   // 清空所有查询参数
}
</script>
```

::: warning query 里的值可能是数组
同名参数出现多次时，`route.query.tag` 会是一个数组，不是字符串：

```text
/activities?tag=体育&tag=文艺
→ route.query.tag 是 ['体育', '文艺']
```

不处理的话，`tag.length` 之类会出错。稳妥的写法是先统一成数组：

```js
const tags = computed(() => {
  const raw = route.query.tag
  if (raw === undefined) return []
  return Array.isArray(raw) ? raw : [raw]
})
```

**所有从 `query` 里取的值，都要假设它可能是 `undefined`、可能是字符串、可能是数组。**
:::

## 嵌套路由与子级出口

管理端有一个共同的需求：**除了登录页，所有页面都有“左侧菜单 + 顶部栏”这套框架。**

如果每个页面组件都自己写一遍菜单，复制几十遍不说，改一处要改十几处。
用嵌套路由把“框架”和“内容”分开：

```text
App.vue
└── RouterView                    ← 第一层出口
    ├── LoginView                 /login，没有框架
    └── AdminLayout               / 布局组件（菜单 + 顶部栏 + 第二层出口）
        └── RouterView            ← 第二层出口，内容渲染在这里
            ├── ActivityListView     /activities
            ├── ActivityDetailView   /activities/:id
            └── SignupReviewView     /signup-review
```

路由表这样写：

```js [src/router/index.js]
const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue')
  },
  {
    path: '/',
    component: () => import('@/layouts/AdminLayout.vue'),
    redirect: '/activities',
    children: [
      {
        path: 'activities',                  // 注意：子路由 path 不带 /
        name: 'activity-list',
        component: () => import('@/views/ActivityListView.vue')
      },
      {
        path: 'activities/:id',
        name: 'activity-detail',
        component: () => import('@/views/ActivityDetailView.vue'),
        props: true
      },
      {
        path: 'signup-review',
        name: 'signup-review',
        component: () => import('@/views/SignupReviewView.vue')
      }
    ]
  }
]
```

布局组件里放第二个 `<RouterView>`：

```vue [src/layouts/AdminLayout.vue]
<template>
  <div class="admin-layout">
    <aside class="menu">
      <AppMenu />
    </aside>

    <div class="main">
      <header class="topbar">
        <Breadcrumb />
        <UserDropdown />
      </header>

      <section class="content">
        <!-- 子页面渲染在这里 -->
        <RouterView />
      </section>
    </div>
  </div>
</template>
```

::: warning 子路由的 path 不要以 `/` 开头
```js
children: [
  { path: 'activities' }      // ✓ 拼接后是 /activities
  { path: '/activities' }     // ✗ 会被当成绝对路径，变成顶级路由
]
```

子路由的 `path` 是**相对父路径**的。父路径是 `/` 时，
`'activities'` 拼出来是 `/activities`。写成了 `'/activities'`，
Vue Router 会把它当作绝对路径，父布局就套不上了。
:::

::: tip 什么时候用嵌套路由
判断依据：**这几个页面之间有没有“公共的、不需要重新渲染的外壳”？**

- 管理端所有后台页共享菜单和顶部栏 → 用嵌套路由，切换时外壳不重建。
- 登录页不需要这套外壳 → 放在嵌套之外。
- 页面之间没有任何共同外壳 → 不用嵌套，各写各的。

好处不只是少写代码：**外壳不重建，菜单的展开状态、滚动位置都能保留。**
:::

## 重定向与别名

**重定向**：访问 A 地址时自动跳到 B。

```js [三种 redirect 写法]
// 1. 字符串
{ path: '/', redirect: '/activities' }

// 2. 用路由名
{ path: '/home', redirect: { name: 'activity-list' } }

// 3. 函数，可以按条件决定
{
  path: '/old-activity/:id',
  redirect: (to) => ({ name: 'activity-detail', params: { id: to.params.id } })
}
```

**别名**：同一份内容能用多个地址访问，地址栏显示的是你输入的那个。

```js [alias]
{
  path: '/activities',
  alias: ['/activity-list', '/list'],
  component: () => import('@/views/ActivityListView.vue')
}
```

| 对比 | 重定向 | 别名 |
| --- | --- | --- |
| 地址栏 | 变成新地址 | 保持你输入的地址 |
| 历史记录 | 新地址进历史 | 输入的地址进历史 |
| 用途 | 旧地址迁移、默认页跳转 | 一个页面支持多种写法 |

**日常更常用重定向** —— 比如 `/` 跳到默认首页、旧地址兼容。

## 404：处理没匹配上的地址

总会有地址匹配不上（用户手输错、旧链接失效）。加一条“兜底路由”：

```js [src/router/index.js]
// 放在路由表最后
{
  path: '/:pathMatch(.*)*',
  name: 'not-found',
  component: () => import('@/views/NotFoundView.vue'),
  meta: { title: '页面不存在' }
}
```

`/:pathMatch(.*)*` 是 Vue Router 4 及以后的通配写法，意思是“匹配任意多层路径”。
它能匹配 `/abc`、`/abc/def`、`/a/b/c/d` 等所有没被前面规则接走的地址。

::: warning 顺序很重要
**兜底路由必须放在路由表最后。** Vue Router 按顺序匹配，
放在前面会把后面所有正常路由都吃掉。
:::

```vue [src/views/NotFoundView.vue]
<template>
  <div class="not-found">
    <h1>404</h1>
    <p>这个地址不存在，可能活动已经被下架了。</p>
    <RouterLink to="/activities">回到活动列表</RouterLink>
  </div>
</template>
```

## 路由懒加载与代码分割

十几个页面如果全部在路由表顶部 `import`，它们会被打包进同一个文件。
首屏要下载全部代码 —— 用户只想看登录页，却下了整个应用。

懒加载改成“用到才下载”：

```js [✗ 全部打进主包]
import ActivityListView from '@/views/ActivityListView.vue'
import ActivityDetailView from '@/views/ActivityDetailView.vue'
// …十几个页面，首屏全下载

const routes = [
  { path: '/activities', component: ActivityListView }
]
```

```js [✓ 每个页面一个独立文件]
const routes = [
  {
    path: '/activities',
    component: () => import('@/views/ActivityListView.vue')
  },
  {
    path: '/activities/:id',
    component: () => import('@/views/ActivityDetailView.vue')
  }
]
```

`() => import(...)` 是一个函数，只有路由被访问时才执行，此时浏览器才去下载对应的代码块。

### 构建后能看到独立的 chunk

跑一次构建：

```bash [构建]
pnpm build
```

`dist/assets/` 里会出现多个 `js` 文件，每个页面一个：

```text [dist/assets/ 片段]
index-a1b2c3.js                 ← 主包（框架 + 公共代码）
ActivityListView-d4e5f6.js      ← 活动列表页，独立
ActivityDetailView-g7h8i9.js    ← 活动详情页，独立
SignupReviewView-j0k1l2.js      ← 报名审核页，独立
```

打开登录页时，浏览器只会下载 `index-*.js` 和登录页那个 chunk；
点进活动列表，才下载 `ActivityListView-*.js`。**首屏体积明显变小。**

::: tip 怎么验证懒加载真的生效
1. `pnpm build`，看 `dist/assets/` 里是不是有多个 js 文件。
2. `pnpm preview` 打开页面，在开发者工具的 Network 面板里，点不同菜单，
   观察有没有新的 js 文件被下载。

如果只有一个巨大的 js，说明懒加载没生效 —— 检查是不是在别处又把页面 `import` 进来了
（比如在某个 `.js` 文件顶部统一导出所有页面）。
:::

::: details 懒加载让首屏变快，但也有代价
每个 chunk 首次访问时要下载，会有几十毫秒的等待。所以：

- **首屏必看的页面**（登录页、首页）可以**不做**懒加载，直接打进主包。
- **其他页面**全部懒加载。
- 页面里很大的组件（图表库、富文本编辑器）也可以单独再拆一层懒加载。

这属于构建优化的内容，[单元 12](/unit12/02-build-optimize)会展开。
:::

## 小结

- “我要看哪一个”用动态参数 `/:id`；“我怎么看这一堆”用查询参数 `?key=value`。
- `route.params` 和 `route.query` 里**所有值都是字符串**，要数字就手动 `Number()`；
  query 的值还可能是数组，处理前先统一。
- `props: true` 把参数变成普通 props，组件不必依赖 `useRoute`，更好测试和复用。
- 嵌套路由把公共外壳和内容分开，子路由 `path` **不以 `/` 开头**；
  布局组件里放第二层 `<RouterView>`。
- `redirect` 会改变地址栏，`alias` 不会；404 兜底用 `/:pathMatch(.*)*`，**放最后一条**。
- 懒加载 `() => import(...)` 让每个页面成为独立 chunk，构建后在 `dist/assets/` 能看到，
  首屏只下载当前页面需要的代码。

## 常见坑

::: details 坑 1：把 id 当成数字比较
现象：`if (route.params.id === 12)` 永远不成立。

原因：`params` 里的值都是字符串。

处理：`Number(route.params.id)`，或者用 `==` 比较（不推荐），
最好是用 `props` 函数形式在路由表里就转换好。
:::

::: details 坑 2：子路由 path 以 `/` 开头，布局没了
现象：子页面的菜单和顶部栏消失了。

原因：`'/activities'` 被当成绝对路径，成了顶级路由，父布局不再包裹它。

处理：子路由 `path` 去掉开头的 `/`。
:::

::: details 坑 3：切换页码时 query 参数互相污染
现象：从第 2 页改关键词，结果还剩着上一页的 `status=closed`。

原因：直接 `router.push({ query: { keyword } })` 会整份替换 `query`，
但如果手动拼了一份不完整的，就会丢参数或留旧参数。

处理：改某一个参数时用 `{ query: { ...route.query, page: next } }` 合并；
要清空就传 `{ query: {} }`。**想清楚是“保留其他条件”还是“重置”。**
:::

::: details 坑 4：404 路由放前面，所有页面都 404
现象：加完兜底路由后，正常页面打不开了。

原因：通配规则写在前面，先匹配上了。

处理：兜底路由永远放路由表**最后一条**。
:::

::: details 坑 5：懒加载没生效
现象：构建后只有一个大 js 文件。

原因：页面组件在别的地方也被静态 `import` 了（比如一个统一的页面导出文件）。

处理：全局搜 `import ... from '@/views/`，确保页面组件只在路由表里用 `() => import(...)` 引入。
:::

## 课后练习

::: details 练习 1：设计活动模块的嵌套路由
写出 `/activities`、`/activities/:id`、`/activities/:id/edit` 三条路由，
让它们都在后台布局内，详情页用 props 接收 id。

**思路**：先在纸上画出组件树（布局 → 列表 / 详情 / 编辑），
再对照写出路由表。注意 `:id` 与 `:id/edit` 的匹配顺序。
:::

::: details 练习 2：把列表的筛选条件同步到地址
让活动列表页的页码、关键词、状态三个筛选条件都写进 `query`，
刷新页面后条件还在。

**思路**：筛选条件的变化 → `router.push({ query })`；
组件里用 `computed` 从 `route.query` 读回值。这样“地址就是状态”，
分享链接、刷新、前进后退全部自动生效。
:::

::: details 练习 3：加上 404 与懒加载
给管理端加上 404 兜底路由，并把所有页面改成懒加载，
构建一次看 `dist/assets/` 里是不是有多个 chunk。

**思路**：404 路由放最后。构建后数一数 js 文件个数，
再用 `pnpm preview` 打开页面，在 Network 面板确认按需下载。
:::

---

上一节：[9.1 路由基础](/unit09/01-router-basics) ·
下一节：[9.3 路由守卫](/unit09/03-guards)
