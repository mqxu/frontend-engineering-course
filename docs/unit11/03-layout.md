# 11.3 布局骨架与嵌套路由

## 每个页面都要写一遍头部，这件事本身说明结构错了

上一节末尾，工程跑起来是一片空白。现在开始加页面。

假设你按最直觉的方式做：先写 `ActivityList.vue`，在它最上面加上侧边栏和顶栏：

```vue
<!-- ✗ 错误做法 -->
<template>
  <div class="app">
    <aside class="sidebar">……一堆菜单项……</aside>
    <div class="main">
      <header class="header">校园活动服务平台</header>
      <div class="content">
        <!-- 这里才是活动列表的真正内容 -->
      </div>
    </div>
  </div>
</template>
```

写完 `ActivityList.vue`，接着写 `SignupList.vue` —— 侧边栏和顶栏的代码要再抄一遍。

抄到第三个页面的时候你会发现三个问题：

1. **菜单项改动要改五处。** 加一个“数据看板”菜单，五个页面全要改。
2. **滚动条位置不对。** 侧边栏应该固定不动，只有内容区滚动。但每个页面各写一套布局，很容易做成整页滚动。
3. **菜单高亮状态没法统一。** 在活动列表页时，侧边栏的“活动管理”应该高亮。五个页面各写一套 `active` 判断逻辑，改一次漏三个。

**这三个问题的根源是同一个：把"布局"和"页面"写在了一起。**

正确的做法是：**布局是一个组件，页面是另一个组件，页面被布局包住。** 而“包住”这件事，Vue Router 的**嵌套路由**天生就是干这个的。

## 嵌套路由：让布局只写一次

回顾[9.2 动态参数与嵌套路由](/unit09/02-nested-params)讲过的基础，这里直接用：

```js [src/router/routes.js]
export const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/login/LoginView.vue'),
    meta: { title: '登录', public: true }
  },
  {
    path: '/',
    component: () => import('@/layouts/AdminLayout.vue'),
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'dashboard',
        component: () => import('@/views/dashboard/DashboardView.vue'),
        meta: { title: '数据看板', icon: 'DataLine' }
      },
      {
        path: 'activity',
        meta: { title: '活动管理', icon: 'Tickets' },
        children: [
          {
            path: '',
            name: 'activity-list',
            component: () => import('@/views/activity/ActivityList.vue'),
            meta: { title: '活动列表' }
          },
          {
            path: 'create',
            name: 'activity-create',
            component: () => import('@/views/activity/ActivityForm.vue'),
            meta: { title: '新增活动', activeMenu: '/activity' }
          },
          {
            path: ':id',
            name: 'activity-detail',
            component: () => import('@/views/activity/ActivityDetail.vue'),
            meta: { title: '活动详情', activeMenu: '/activity' }
          },
          {
            path: ':id/edit',
            name: 'activity-edit',
            component: () => import('@/views/activity/ActivityForm.vue'),
            meta: { title: '编辑活动', activeMenu: '/activity' }
          }
        ]
      }
    ]
  }
]
```

三个要点。

### 要点一：只有 `AdminLayout` 那一层是布局

`/login` 不在 `AdminLayout` 的 `children` 里，所以**登录页不会有侧边栏** —— 这是嵌套路由最直观的好处。如果登录页也要写 `<RouterView />`，那说明路由表分层分错了。

### 要点二：`meta` 里放展示信息，不放业务数据

`meta` 适合放的东西：

| 字段 | 用途 |
| --- | --- |
| `title` | 侧边栏文字、面包屑、浏览器标题栏 |
| `icon` | 侧边栏图标名 |
| `public` | 是否免登录（路由守卫用） |
| `activeMenu` | 这一页该让哪个菜单项高亮 |
| `roles` | 哪些角色能进（路由守卫用） |

`meta` **不适合**放的东西：接口地址、当前页面 id、列表数据。这些要么是页面自己的事，要么从 `route.params` 拿。**`meta` 是静态的配置，不是数据的容器。**

### 要点三：`meta` 会在子路由上继承

Vue Router 4 起，`route.meta` 会把**所有匹配到的路由的 meta 合并**：

```vue
<!-- 访问 /activity/42/edit 时 -->
<script setup>
const route = useRoute()
console.log(route.meta)
// { title: '编辑活动', activeMenu: '/activity', icon: 'Tickets' }
//                       ↑ 来自自己      ↑ 来自父级 activity
</script>
```

注意 `title` 只有自己的值 —— 子路由的 meta 会覆盖父路由的同名字段。这正是我们想要的：父级给“菜单图标”，子级给“页面标题”。

::: warning 继承是浅合并，不是深合并
如果父级 `meta` 里有一个对象，子级再写一个对象，子级会**整个替换**父级，不是合并字段。

```js
// 父级
meta: { breadcrumb: { show: true, prefix: '活动' } }
// 子级
meta: { breadcrumb: { show: false } }
// 结果：{ breadcrumb: { show: false } }  ← prefix 丢了
```

**所以 `meta` 里尽量只放扁平的值**（字符串、布尔、数组），需要嵌套结构时在组件里自己合成。
:::

## 布局组件：三块结构

```vue [src/layouts/AdminLayout.vue]
<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import AppSidebar from './components/AppSidebar.vue'
import AppBreadcrumb from './components/AppBreadcrumb.vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const collapsed = ref(false)

const pageTitle = computed(() => route.meta.title ?? '校园活动服务平台')

function handleLogout() {
  userStore.logout()
  router.push('/login')
}
</script>

<template>
  <div class="admin-layout">
    <!-- ① 侧边栏：固定宽度，不随内容滚动 -->
    <aside class="sidebar" :class="{ 'is-collapsed': collapsed }">
      <div class="brand">
        <img src="@/assets/logo.svg" alt="" class="brand-logo" />
        <span v-show="!collapsed" class="brand-text">校园活动服务平台</span>
      </div>
      <AppSidebar :collapsed="collapsed" />
    </aside>

    <!-- ② 右侧主区：顶栏固定，内容区自己滚 -->
    <div class="main">
      <header class="topbar">
        <el-button text @click="collapsed = !collapsed">
          <el-icon><Fold v-if="!collapsed" /><Expand v-else /></el-icon>
        </el-button>

        <AppBreadcrumb />

        <div class="topbar-right">
          <span class="user-name">{{ userStore.displayName }}</span>
          <el-tag size="small">{{ userStore.roleLabel }}</el-tag>
          <el-button text @click="handleLogout">退出登录</el-button>
        </div>
      </header>

      <main class="content">
        <RouterView v-slot="{ Component }">
          <KeepAlive :include="['ActivityList']">
            <component :is="Component" :key="route.path" />
          </KeepAlive>
        </RouterView>
      </main>
    </div>
  </div>
</template>

<style scoped lang="scss">
.admin-layout {
  display: flex;
  height: 100vh;      /* 撑满视口，而不是被内容撑高 */
  overflow: hidden;   /* 关键：外层不滚动 */
}

.sidebar {
  flex: 0 0 220px;
  display: flex;
  flex-direction: column;
  background: #1f2937;
  transition: flex-basis 0.2s;

  &.is-collapsed {
    flex-basis: 64px;
  }
}

.brand {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 56px;
  padding: 0 16px;
  color: #fff;
  white-space: nowrap;
}

.main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;       /* 关键：不加这行，内部宽表格会把布局撑破 */
}

.topbar {
  display: flex;
  align-items: center;
  gap: 12px;
  height: 56px;
  padding: 0 16px;
  border-bottom: 1px solid var(--el-border-color-light);
  background: #fff;
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
}

.content {
  flex: 1;
  overflow: auto;     /* 只有内容区滚动 */
  padding: 16px;
  background: #f5f7fa;
}
</style>
```

::: tip 三行 CSS 撑起整个后台布局
`height: 100vh` + `overflow: hidden` + 内容区 `overflow: auto`。

这三行做到的效果是：**侧边栏和顶栏固定不动，只有内容区滚动。** 这是后台系统的基本体验要求 —— 表格很长时，菜单和表头一直在视野里。

如果漏掉 `overflow: hidden`，整个页面会滚动，侧边栏跟着滚上去，看起来很奇怪。

另外 `.main` 上的 `min-width: 0` 容易被漏。flex 子项默认 `min-width: auto`，遇到内部有宽内容（比如一个 12 列的表格）时，会把父容器撑得超出视口。**加这一行，宽内容就会在内容区内部滚动，而不是撑破布局。**
:::

## 侧边栏菜单：跟着路由自动高亮

菜单最容易写错的地方是“当前在哪个页面”。如果每个菜单项都手写 `:class="{ active: route.path === '/activity' }"`，会遇到两个问题：

1. `/activity/42/edit` 时，`route.path` 不等于 `/activity`，菜单不高亮。
2. `/activity/create` 时同样不高亮。

所以高亮的判断依据不是 `route.path`，而是 **`route.meta.activeMenu`**（如果没有，就回退到匹配到的最长路径）。

```vue [src/layouts/components/AppSidebar.vue]
<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { routes } from '@/router/routes'

defineProps({
  collapsed: { type: Boolean, default: false }
})

const route = useRoute()

// 把路由表里 level 1 的 children 转成菜单数据
const menus = computed(() =>
  (routes.find((r) => r.path === '/')?.children ?? [])
    .filter((r) => !r.meta?.hidden)
    .map((r) => ({
      path: '/' + r.path,
      title: r.meta?.title ?? '',
      icon: r.meta?.icon,
      // 有 children 的做成子菜单；只有一层 path 为 '' 的，直接指向它
      children: r.children?.map((c) => ({
        path: c.path ? `/${r.path}/${c.path}` : `/${r.path}`,
        title: c.meta?.title ?? '',
        hidden: c.meta?.hidden
      }))
    }))
)

// 当前应该高亮的菜单项
const activeMenu = computed(() => route.meta.activeMenu ?? route.path)
</script>

<template>
  <el-menu
    :default-active="activeMenu"
    :collapse="collapsed"
    :collapse-transition="false"
    router
    background-color="#1f2937"
    text-color="#cbd5e1"
    active-text-color="#42b883"
  >
    <template v-for="menu in menus" :key="menu.path">
      <!-- 有子菜单 -->
      <el-sub-menu v-if="menu.children?.length" :index="menu.path">
        <template #title>
          <el-icon v-if="menu.icon"><component :is="menu.icon" /></el-icon>
          <span>{{ menu.title }}</span>
        </template>
        <el-menu-item
          v-for="child in menu.children.filter((c) => !c.hidden)"
          :key="child.path"
          :index="child.path"
        >
          {{ child.title }}
        </el-menu-item>
      </el-sub-menu>

      <!-- 没有子菜单，直接是菜单项 -->
      <el-menu-item v-else :index="menu.path">
        <el-icon v-if="menu.icon"><component :is="menu.icon" /></el-icon>
        <template #title>{{ menu.title }}</template>
      </el-menu-item>
    </template>
  </el-menu>
</template>
```

三个关键点：

**一、`:default-active="activeMenu"`** —— 属性名叫 `default`，但它其实支持响应式更新。当 `activeMenu` 变化时，高亮会跟着变。**不要被 `default` 这个词误导成"只在初始化时生效"。**

**二、`router` 属性** —— 加上之后，`el-menu-item` 的 `index` 会被当成路由路径，点击自动 `router.push`，不用自己监听 `@select`。

**三、`:collapse-transition="false"`** —— 折叠动画会和 `flex-basis` 的 transition 打架，出现抖动。关掉它。

::: details 为什么 `hidden` 的菜单项要过滤两次
上面代码里，`menus` 里过滤了一次 `hidden`，渲染子菜单时又 `filter` 了一次。

第一层过滤是给**一级菜单**用的（比如整个“系统设置”模块不想显示）。
第二层过滤是给**二级菜单**用的（“编辑活动”这种页面不该出现在菜单里）。

**为什么要有 `meta.hidden`？** 因为 `ActivityForm.vue` 同时用于新增和编辑，它不是独立功能，只是活动列表的延伸。它必须在路由表里（否则访问不了），但不该在菜单里（否则菜单会有“新增活动”“编辑活动”两个莫名其妙的项）。

这类“有路由但不进菜单”的页面，就是靠 `meta.hidden` 标记的。
:::

## 面包屑：从路由表自动生成

面包屑不该手写。它的信息在路由表里已经有了（`meta.title` 和 `matched` 数组），直接算出来：

```vue [src/layouts/components/AppBreadcrumb.vue]
<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const items = computed(() =>
  route.matched
    // 只保留有 title 的层，且过滤掉“有 children 但没有自己的页面”的中间层
    .filter((r) => r.meta?.title)
    .map((r, index) => ({
      title: r.meta.title,
      // 中间层没有自己的组件时，不生成可点链接
      to: r.components?.default ? { path: r.path } : null,
      isLast: index === route.matched.filter((x) => x.meta?.title).length - 1
    }))
)
</script>

<template>
  <el-breadcrumb separator="/">
    <el-breadcrumb-item
      v-for="item in items"
      :key="item.title"
      :to="item.isLast ? undefined : item.to"
    >
      {{ item.title }}
    </el-breadcrumb-item>
  </el-breadcrumb>
</template>
```

`route.matched` 是**当前路由从根到叶的完整匹配链**。访问 `/activity/42/edit` 时它是：

```
[
  { path: '/',                      meta: {} },                       ← 只是布局，无 title，被过滤
  { path: '/activity',              meta: { title: '活动管理' } },
  { path: '/activity/:id/edit',     meta: { title: '编辑活动' } }
]
```

过滤出有 `title` 的两层，面包屑就是“活动管理 / 编辑活动”。

::: warning `path: '/activity'` 这一层没有自己的页面组件
注意 `/activity` 这层只是一个“容器路由”，它没有 `component`，只有 `children`。所以面包屑里“活动管理”**不应该可点** —— 点进去没有任何页面。

上面代码用 `r.components?.default` 判断：有组件才生成链接。没有组件的中间层渲染成纯文字。

另一种做法是给 `/activity` 层加一个 `redirect: '/activity'`（指向自己的默认子路由），这样它就能点了。两种都行，**关键是别让用户点到一个空白页**。
:::

::: details 面包屑里显示 id 而不是标题，怎么处理
访问 `/activity/42/edit`，面包屑显示“活动管理 / 编辑活动”—— 看不出在编辑哪个活动。

想在中间插一个活动标题，有三种做法：

**做法一：路由 `meta.title` 用函数。** Vue Router 的 `meta.title` 可以是函数，接收 `route` 返回字符串。

```js
meta: { title: (route) => `编辑活动 #${route.params.id}` }
```

代价是它拿不到接口返回的真实标题，只能显示 id 或“编辑活动”。

**做法二：详情页通过 `provide` 往上送标题。** 页面拿到数据后调用一个由布局提供的函数：

```vue
<!-- AdminLayout.vue 里 -->
<script setup>
const extraTitle = ref('')
provide('setBreadcrumbExtra', (t) => (extraTitle.value = t))
</script>

<!-- ActivityForm.vue 里 -->
<script setup>
const setExtra = inject('setBreadcrumbExtra')
watch(activity, (v) => setExtra?.(v?.title ?? ''))
</script>
```

**做法三：干脆不显示 id。** 面包屑只到“编辑活动”为止，用户能通过页面顶部的标题或表单内容知道在编辑哪个活动。

**课程项目用做法三。** 面包屑的职责是告诉用户“我在系统的哪个位置”，不是复述数据。**把一个不该它承担的信息塞进来，会让组件多出一堆跨层通信。**
:::

## 路由守卫与登录页

布局搭好了，但现在的路由表格所有页面都能直接访问。补上守卫：

```js [src/router/index.js]
import { createRouter, createWebHistory } from 'vue-router'
import { routes } from './routes'
import { useUserStore } from '@/stores/user'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
  scrollBehavior: () => ({ top: 0 })
})

router.beforeEach((to) => {
  const userStore = useUserStore()

  // 免登录页面直接放行
  if (to.meta.public) return true

  // 未登录，跳登录页并记住原目标
  if (!userStore.token) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }

  // 已登录但角色不匹配
  if (to.meta.roles && !to.meta.roles.includes(userStore.role)) {
    return { path: '/403' }
  }

  return true
})

router.afterEach((to) => {
  document.title = to.meta.title
    ? `${to.meta.title} · 校园活动服务平台`
    : '校园活动服务平台'
})

export default router
```

`afterEach` 里改 `document.title`，这样浏览器标签页显示的是“活动列表 · 校园活动服务平台”。**这一行代码几乎不花成本，但用户感受差别很大** —— 开了十个标签页时，靠标题就能找到想要的那个。

完整的登录鉴权链路（登录 → 存 token → 拦截器 → 401 处理 → 退出清理）在
[9.4 登录鉴权完整链路](/unit09/04-auth-flow)和[案例 10 · 登录与鉴权](/cases/10-auth)里。

## 骨架完成的验收标准

跑起来之后，对照这份清单逐项确认：

| 检查项 | 怎么验证 |
| --- | --- |
| 登录页没有侧边栏 | 访问 `/login`，看不到菜单 |
| 后台页面有侧边栏 | 访问 `/dashboard`，左侧有菜单、顶部有面包屑 |
| 菜单能跳转 | 点“活动管理 → 活动列表”，地址栏变成 `/activity` |
| 菜单自动高亮 | 直接访问 `/activity/create`，侧边栏的“活动管理”仍需高亮 |
| 面包屑跟着变 | 从活动列表进编辑页，面包屑从“活动管理”变成“活动管理 / 编辑活动” |
| 未登录会被拦 | 清掉 token 后访问 `/activity`，跳回 `/login` 且地址栏带 `?redirect=` |
| 只有内容区滚动 | 把一个页面内容撑长，侧边栏和顶栏应固定不动 |
| 标题栏跟着变 | 切换页面，浏览器标签页文字跟着变 |

**这八项全过，布局骨架就算合格了。** 内容区现在还是空白的，下一节开始填。

## 小结

- **布局是一个组件，页面是另一个组件，页面被布局包住。** 这是嵌套路由要解决的问题。
- **登录页放在布局外面**，所以它天然没有侧边栏 —— 这是分层正确的直接结果。
- **`meta` 只放静态展示信息**（title、icon、public、roles），不放接口地址和业务数据。
- **meta 会从父路由继承，但子路由同名会覆盖；对象字段是浅合并**，所以尽量只放扁平值。
- **后台布局靠三行 CSS**：`height: 100vh` + `overflow: hidden` + 内容区 `overflow: auto`。
- **`min-width: 0` 不能漏**，否则宽表格会撑破布局。
- **菜单高亮看 `meta.activeMenu`**，不是 `route.path`，否则详情页和编辑页都不会高亮。
- **有路由但不进菜单的页面用 `meta.hidden` 标记**。
- **面包屑从 `route.matched` 生成**，没有组件的中间层不生成可点链接。
- **`afterEach` 里改 `document.title`**，一行代码换来很大的体验提升。

## 常见坑

::: details 页面内容撑长后，整页滚动而侧边栏跟着滚
**现象**：表格有 50 条数据，滚动时侧边栏一起滚上去了，菜单看不到。

**原因**：漏了 `.admin-layout { height: 100vh; overflow: hidden }`，或者内容区没写 `overflow: auto`。

**怎么处理**：三个值要同时写。少任何一个都会出问题：

| 漏掉哪个 | 现象 |
| --- | --- |
| `height: 100vh` | 容器高度等于内容高度，永远不会滚动 |
| `overflow: hidden` | 外层滚动条出现，侧边栏跟着滚 |
| 内容区 `overflow: auto` | 内容溢出被裁掉，看不到后面的数据 |
:::

::: details 宽表格把整个布局撑出横向滚动条
**现象**：活动列表有 12 列，屏幕不够宽时整个页面出现横向滚动条，顶栏和侧边栏被推走。

**原因**：`.main` 是 flex 子项，默认 `min-width: auto`，不会小于内部内容的宽度。

**怎么处理**：给 `.main` 加 `min-width: 0`。

```scss
.main {
  flex: 1;
  min-width: 0;   /* 关键 */
  display: flex;
  flex-direction: column;
}
```

**这是一个纯 CSS 的坑，但现象看起来像布局组件写错了**，容易往组件代码里找原因。记住这个组合：flex 子项 + 内部宽内容 = 需要 `min-width: 0`。
:::

::: details 从 `/activity/42/edit` 刷新后菜单不高亮
**现象**：从列表页点进编辑页，菜单高亮正常；一刷新，高亮就没了。

**原因**：`el-menu` 的 `default-active` 绑的是 `route.path`，而 `/activity/42/edit` 在菜单里不存在，匹配不上。刷新时组件重新挂载，重新算一次匹配，就走了这条错逻辑。

**怎么处理**：绑 `route.meta.activeMenu ?? route.path`，并且在编辑页的路由 `meta` 里写上 `activeMenu: '/activity'`。

**注意**：`el-menu` 的 `default-active` 支持响应式，但在某些 Element Plus 版本里，如果 `default-active` 的值一开始就是空字符串，后续再变可能不生效。稳妥做法是给它一个初始的兜底值：

```js
const activeMenu = computed(() => route.meta.activeMenu ?? route.path ?? '/dashboard')
```
:::

::: details 路由改了，菜单没跟着变
**现象**：在 `routes.js` 里加了一个新页面，侧边栏没出现。

**原因**：侧边栏的菜单数据是从 `routes` 里算出来的，但 `menus` 是 `computed`。如果 `routes` 是普通数组，`computed` 不会重新算 —— 不过正常情况下 `routes` 在应用启动后不会变，所以这个问题一般是别的原因。

**实际更常见的原因**：新加的路由放在了一个 `meta.hidden` 的父路由下面，或者父路由不是 `path: '/'` 那个。

**怎么处理**：检查三件事：① 新路由是不是 `/` 的 `children`（或者它的后代）；② 自己和父级都没有 `meta.hidden`；③ 有 `children` 的那一层，自己的 `meta.title` 会显示为子菜单标题，别漏写。

**如果确实需要菜单动态变化**（比如按角色显示不同菜单），把 `routes` 换成 `ref` 或者从 store 里读，`computed` 就会跟着重算。角色控制菜单的写法见[案例 10](/cases/10-auth)。
:::

::: details 编辑页和新增页共用一个组件，切换时数据没清空
**现象**：先打开 `/activity/create` 填了几个字段，再进 `/activity/42/edit`，发现新增页面填的内容还在。

**原因**：两个路由用的是同一个组件，Vue 复用了组件实例，不会重新创建。

**怎么处理**：上面布局里已经处理了 —— 给 `<component :is="Component" :key="route.path" />` 加了 `:key="route.path"`。

**`:key` 加了之后，组件会跟着路径变化重建，`onMounted` 会重新执行。** 代价是失去了状态复用（但这里本来就是两个不同的页面，不该复用）。

**另一种情况**：如果是同一个路由只是参数变了（比如从 `/activity/42/edit` 跳到 `/activity/43/edit`），`:key="route.path"` 也会变，同样会重建。这是想要的行为。
:::

::: details `KeepAlive :include` 写了但没生效
**现象**：想让活动列表页保留查询条件和翻页状态，配了 `<KeepAlive :include="['ActivityList']">`，但切回来发现状态还是没了。

**原因**：`include` 匹配的是**组件的 `name` 选项**，不是文件名，也不是路由名。用 `<script setup>` 写的组件默认没有 `name`。

**怎么处理**：显式声明组件名：

```vue [src/views/activity/ActivityList.vue]
<script setup>
defineOptions({ name: 'ActivityList' })
</script>
```

**`defineOptions` 是 Vue 3.3 起可用的宏**，当前基线 Vue 3.5.42 完全支持。

**另外要注意**：`KeepAlive` 只保留组件状态，**不会阻止路由离开时的数据加载逻辑**。如果你在 `onMounted` 里拉列表，被缓存后切回来不会重新拉 —— 这通常正是想要的（保留翻页位置），但用户点了“新增”再返回时希望看到新数据，就会觉得数据没更新。这种情况要在“新增成功”后主动刷新列表，或者用 `onActivated` 钩子在恢复时重新拉一次。
:::

## 课后练习

::: details 练习 1：给侧边栏加上折叠状态的记忆
现在的折叠状态存在 `ref` 里，刷新就恢复成展开。请改成刷新后仍然保持上次的状态。

**思路提示**：

- 用 `@vueuse/core` 的 `useLocalStorage`，它和 `ref` 用法一致，但会自动同步到 `localStorage`：

```js
import { useLocalStorage } from '@vueuse/core'
const collapsed = useLocalStorage('admin-sidebar-collapsed', false)
```

- 想一想：`localStorage` 里存布尔值，读出来还是布尔值吗？（提示：`useLocalStorage` 会做序列化，比手写 `JSON.parse` 省事）
- 再进一步：屏幕宽度小于 768 时自动折叠。用 `useMediaQuery` 试试。
:::

::: details 练习 2：让面包屑显示活动的真实标题
按这一节“面包屑里显示 id 而不是标题”那条 `details` 里的做法二，实现“编辑活动时面包屑显示活动标题”。

**思路提示**：

- 需要一个从页面往布局送数据的方式，`provide` / `inject` 是最短的路径。
- 注意组件卸载时要把标题清掉，否则从编辑页回到列表页，面包屑上会残留上一个活动的标题。在 `onUnmounted` 里调用清空。
- 想一想：如果直接用 Pinia 存这个标题，会有什么问题？（提示：这是一个“只跟当前页面相关、页面一走就该失效”的数据，放进全局 store 会出现残留和多个页面互相覆盖）
- **做完之后回答一个问题**：这个功能值不值得付出这些复杂度？把答案写进你的项目文档。
:::

::: details 练习 3：加一个 403 页面和一个 404 页面
现在角色不匹配会跳到 `/403`，但这个路由还不存在。

**思路提示**：

- 404 用通配路由捕获：`{ path: '/:pathMatch(.*)*', name: 'not-found', component: ... }`，**必须放在路由表最后**。
- 403 页面给两个按钮：“返回首页”和“退出登录换个账号”。
- 想一想：403 和 404 该不该放在 `AdminLayout` 里面？（提示：404 有两种情况 —— 已登录用户访问了不存在的后台路径，应该带侧边栏；未登录用户乱输网址，带侧边栏很奇怪。这个判断没有唯一答案，说清理由就行）
- 把 403 的 `meta` 写成 `{ title: '无权限', public: true }`，否则会出现“跳 403 → 403 被守卫拦住 → 再跳 403”的死循环。
:::

::: details 练习 4：把菜单数据抽成独立文件
现在菜单是从 `routes.js` 算出来的。请改成从 `src/config/menu.js` 独立维护。

**思路提示**：

- 抽出来之后，路由表可以随便拆分成多个文件（`routes/activity.js`、`routes/signup.js`），菜单结构不受影响。
- 代价是两边要手工保持同步 —— 加了路由忘了加菜单，页面就进不去。
- **写一段结论**：这个项目里，从路由表算菜单 vs 独立维护菜单，你选哪个？理由是什么？这个判断在模块数量不同的时候会变吗？
:::

---

上一节：[11.2 工程初始化与目录规划](/unit11/02-scaffold) · 下一节：[11.4 列表页标准做法](/unit11/04-list-page)
