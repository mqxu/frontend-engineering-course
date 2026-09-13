# 目录结构与命名约定

这一页规定**文件放哪、怎么命名**。

看起来很琐碎，但它是“工程质量”这个评分维度里最直接能看出来的一项。**打开一个项目，看目录结构和文件命名，基本能判断出作者是随手写还是有组织地写。**

## 一、完整的目录结构

```
activity-admin/
├── .env.development          # 开发环境变量（提交）
├── .env.production           # 生产环境变量（提交）
├── .env.example              # 环境变量示例（提交，供别人参考）
├── .gitignore
├── README.md                 # 项目说明（提交，必须完整）
├── index.html                # 入口 HTML，在根目录
├── jsconfig.json             # 让编辑器识别 @ 别名
├── package.json
├── pnpm-lock.yaml            # 锁文件（必须提交）
├── vite.config.js
├── docs/                     # 项目文档
│   ├── design.md             # 设计文档
│   ├── api.md                # 接口文档
│   ├── deploy.md             # 部署文档
│   ├── dev-notes.md          # 开发记录
│   └── optimization.md       # 优化记录
├── public/                   # 原样复制到产物的静态资源
│   └── favicon.ico
├── scripts/
│   ├── deploy.sh             # 部署脚本
│   └── check-size.mjs        # 产物体积检查
└── src/
    ├── api/                  # 接口层，按业务模块分文件
    │   ├── request.js        # axios 实例 + 拦截器
    │   ├── auth.js
    │   ├── activity.js
    │   ├── signup.js
    │   ├── session.js
    │   ├── venue.js
    │   └── dashboard.js
    ├── assets/               # 会被构建处理的静态资源
    │   ├── images/
    │   └── styles/
    │       ├── variables.scss
    │       ├── reset.scss
    │       └── index.scss
    ├── components/           # 跨模块复用的组件
    │   ├── AppPageHeader.vue
    │   ├── AppStateWrapper.vue
    │   ├── AppStatusTag.vue
    │   └── AppEmpty.vue
    ├── composables/          # 组合式函数
    │   ├── useTable.js
    │   ├── useFormPage.js
    │   └── useConflictCheck.js
    ├── domain/               # 业务规则（纯函数，集中维护）
    │   └── activity-rules.js
    ├── layouts/              # 布局组件
    │   ├── AdminLayout.vue
    │   └── components/
    │       ├── AppSidebar.vue
    │       └── AppBreadcrumb.vue
    ├── router/
    │   ├── index.js          # 创建路由实例 + 守卫
    │   └── routes.js         # 路由表
    ├── stores/               # Pinia
    │   ├── user.js
    │   └── notify.js
    ├── utils/                # 工具函数
    │   ├── dict.js           # 枚举与文案
    │   ├── format.js         # 格式化
    │   └── validate.js       # 自定义校验器
    ├── views/                # 页面，按业务模块分子目录
    │   ├── login/
    │   │   └── LoginView.vue
    │   ├── dashboard/
    │   │   ├── DashboardView.vue
    │   │   └── components/
    │   │       ├── MetricCard.vue
    │   │       └── UsageRing.vue
    │   ├── activity/
    │   │   ├── ActivityList.vue
    │   │   ├── ActivityDetail.vue
    │   │   ├── ActivityForm.vue
    │   │   └── components/
    │   │       └── ActivityQuotaCell.vue
    │   ├── signup/
    │   │   ├── SignupList.vue
    │   │   └── components/
    │   │       └── SignupAuditDialog.vue
    │   ├── venue/
    │   │   ├── VenueList.vue
    │   │   └── VenueForm.vue
    │   ├── session/
    │   │   ├── SessionList.vue
    │   │   ├── SessionForm.vue
    │   │   └── components/
    │   │       └── VenueTimeline.vue
    │   └── error/
    │       ├── ForbiddenView.vue
    │       └── NotFoundView.vue
    ├── App.vue
    └── main.js
```

## 二、六条分目录的规则

### 规则一：`views` 按业务模块分，不按类型分

**不要这样：**

```
views/
├── list/          # 所有列表页放一起
│   ├── ActivityList.vue
│   ├── SignupList.vue
│   └── VenueList.vue
└── form/          # 所有表单页放一起
    ├── ActivityForm.vue
    └── VenueForm.vue
```

看起来整齐，但改“活动”这个功能时，要在 `list/` 和 `form/` 之间来回跳。而且模块一多，`list/` 会挤满几十个文件。

**要这样：**

```
views/activity/    # 活动的所有东西在一起
├── ActivityList.vue
├── ActivityDetail.vue
├── ActivityForm.vue
└── components/
```

**改需求时只在一个目录里工作。** 这才是目录结构要解决的问题。

### 规则二：`components` 和 `views/xxx/components` 按复用范围分

| 目录 | 放什么 | 判断标准 |
| --- | --- | --- |
| `src/components/` | 跨模块复用的组件 | **两个以上模块会用** |
| `src/views/xxx/components/` | 模块私有组件 | **只有这个模块会用** |

具体到这个项目：

| 组件 | 放在哪 | 为什么 |
| --- | --- | --- |
| `AppStatusTag.vue` | `src/components/` | 活动状态、报名状态、场次状态都要用，靠 props 传不同的字典 |
| `AppStateWrapper.vue` | `src/components/` | 每个列表页都要处理加载中与失败 |
| `UsageRing.vue` | `views/dashboard/components/` | 只有看板用环形进度 |
| `VenueTimeline.vue` | `views/session/components/` | 只有场次安排用时间轴 |

**判断错了不要紧，搬一次就好。** 养成“先想复用范围再决定放哪”的习惯，能避免 `src/components` 最后变成几十个文件的杂物间。

### 规则三：`api` 按模块分文件，一个文件对应一个业务实体

```js [src/api/activity.js]
import request from './request'

/** 后端字段 → 前端字段 */
function toModel(raw) {
  return {
    id: raw.id,
    title: raw.title,
    type: raw.type,
    quota: raw.quota,
    approvedCount: raw.approved_count,
    pendingCount: raw.pending_count,
    signupDeadline: raw.signup_deadline,
    status: raw.status,
    offShelf: raw.off_shelf,
    description: raw.description,
    createdAt: raw.created_at,
    updatedAt: raw.updated_at
  }
}

export async function getActivityList(params) {
  const { data } = await request.get('/activities', { params })
  return { list: (data.list ?? []).map(toModel), total: data.total ?? 0 }
}

export async function getActivityDetail(id) {
  const { data } = await request.get(`/activities/${id}`)
  return toModel(data)
}

export function createActivity(form) {
  return request.post('/activities', form)
}

export function updateActivity(id, form) {
  return request.put(`/activities/${id}`, form)
}

export function publishActivity(id) {
  return request.patch(`/activities/${id}/status`, { status: 'SIGNING' })
}

export function setActivityOffShelf(id, offShelf) {
  return request.patch(`/activities/${id}/offshelf`, { offShelf })
}

export function deleteActivity(id) {
  return request.delete(`/activities/${id}`)
}
```

**三条规则：**

**一、接口函数只做“拼路径、传参数、返回 Promise”。** 不在这里弹提示、不在这里判断状态码。那些是拦截器和调用方的事。

**二、需要字段名转换的，转换放在这个文件里。** 不要散到组件中。转换函数用 `toModel`（后端 → 前端）和 `toPayload`（前端 → 后端）两个名字，团队里形成默契。

**三、列表接口在这里就把 `list` / `total` 拆出来。** 这样页面里不用再记“后端返回的是 `records` 还是 `list`”。

### 规则四：`domain` 放业务规则，`utils` 放通用工具

这两个目录容易混。判断标准：

| 目录 | 内容特征 | 例子 |
| --- | --- | --- |
| `domain/` | **跟业务有关**，换个项目就用不上了 | `canSignup()`、`canDelete()`、`isTimeConflict()` |
| `utils/` | **跟业务无关**，换个项目照样能用 | `formatDateTime()`、`toBool()`、`debounce()` |

```js [src/domain/activity-rules.js]
import { ACTIVITY_STATUS } from '@/utils/dict'

/** 学生能不能报名 */
export function canSignup(activity) {
  if (activity.status !== ACTIVITY_STATUS.SIGNING) {
    return { ok: false, reason: '活动当前不接受报名' }
  }
  if (activity.offShelf) {
    return { ok: false, reason: '活动已下架' }
  }
  if (new Date(activity.signupDeadline).getTime() <= Date.now()) {
    return { ok: false, reason: '报名已截止' }
  }
  if (activity.approvedCount >= activity.quota) {
    return { ok: false, reason: '名额已满' }
  }
  return { ok: true }
}

/** 能不能编辑 */
export function canEdit(activity) {
  return activity.status !== ACTIVITY_STATUS.FINISHED
}

/** 能不能删除 */
export function canDelete(activity) {
  return activity.status === ACTIVITY_STATUS.DRAFT
}

/** 能不能下架 */
export function canOffShelf(activity) {
  return activity.status !== ACTIVITY_STATUS.DRAFT
    && activity.status !== ACTIVITY_STATUS.FINISHED
}

/** 判断两个时段是否冲突。边界相接不算冲突。 */
export function isTimeConflict(aStart, aEnd, bStart, bEnd) {
  const a1 = new Date(aStart).getTime()
  const a2 = new Date(aEnd).getTime()
  const b1 = new Date(bStart).getTime()
  const b2 = new Date(bEnd).getTime()
  if (a2 <= b1) return false
  if (b2 <= a1) return false
  return true
}
```

**为什么单独搞一个 `domain` 目录**：这些规则在列表页、详情页、表单页、看板里都要用。散在页面里的话，改一条规则要搜遍全项目，而且很容易出现“列表页判断对了、详情页判断错了”的不一致。

**规则集中之后还能单独测试**：

```js
// domain/activity-rules.test.js
import { describe, it, expect } from 'vitest'
import { isTimeConflict, canDelete } from './activity-rules'

describe('isTimeConflict', () => {
  it('边界相接不算冲突', () => {
    expect(isTimeConflict('2026-04-10 14:00:00', '2026-04-10 17:00:00',
                          '2026-04-10 17:00:00', '2026-04-10 20:00:00')).toBe(false)
  })

  it('部分重叠算冲突', () => {
    expect(isTimeConflict('2026-04-10 14:00:00', '2026-04-10 17:00:00',
                          '2026-04-10 15:00:00', '2026-04-10 18:00:00')).toBe(true)
  })

  it('完全相同算冲突', () => {
    expect(isTimeConflict('2026-04-10 14:00:00', '2026-04-10 17:00:00',
                          '2026-04-10 14:00:00', '2026-04-10 17:00:00')).toBe(true)
  })
})
```

**这类有边界条件的纯函数最适合写测试。** 用文字描述“边界相接不算冲突”可能有人理解错，但一条断言就是精确的。

### 规则五：`composables` 放跨页面复用的逻辑

这个项目里值得抽的只有三个：

| 组合式函数 | 解决什么 | 用在哪 |
| --- | --- | --- |
| `useTable.js` | 列表页的查询、分页、四态 | 所有列表页 |
| `useFormPage.js` | 新增 / 编辑共用的表单逻辑 | 所有表单页 |
| `useConflictCheck.js` | 时段冲突预检 | 场次表单 |

**不要为了抽而抽。** 如果一段逻辑只在一个页面用，就留在页面里。

**判断标准**：第二个页面要用同一段逻辑时，再抽。**提前抽象出来的东西，往往抽象错了。**

### 规则六：`layouts` 里只放布局，不放业务

`AdminLayout.vue` 里应该有：侧边栏、顶栏、面包屑、内容区。

`AdminLayout.vue` 里不应该有：活动列表的查询逻辑、用户权限判断的具体规则。

**判断方法**：把 `AdminLayout` 换成一个完全不同的布局（比如顶部导航式），如果里面的业务逻辑要重新写一遍，说明放错了。

## 三、命名约定

### 文件与目录

| 类型 | 规范 | 例子 |
| --- | --- | --- |
| 目录 | kebab-case（小写 + 连字符） | `views/activity/`、`views/error/` |
| Vue 组件 | PascalCase | `ActivityList.vue`、`AppSidebar.vue` |
| JS 文件 | kebab-case | `activity-rules.js`、`request.js` |
| 组合式函数 | camelCase，以 `use` 开头 | `useTable.js`、`useConflictCheck.js` |
| 文档 | kebab-case 或小写单词 | `dev-notes.md`、`design.md` |
| 样式 | kebab-case | `variables.scss` |

**“组件用 PascalCase、其他用 kebab-case”这条规则的用处**：在文件列表里一眼能区分出“这是个 Vue 组件”还是“这是个普通 JS 文件”。

### 组件命名

| 前缀 | 用途 | 例子 |
| --- | --- | --- |
| `App` | 全局通用组件 | `AppStatusTag.vue`、`AppStateWrapper.vue` |
| `Admin` | 布局相关 | `AdminLayout.vue` |
| 业务名词 | 具体业务的组件 | `ActivityQuotaCell.vue`、`VenueTimeline.vue` |

**`App` 前缀的作用**：在模板里看到 `<AppStatusTag>`，立刻知道它是全局通用组件，不是某个模块的私有组件。

**视图组件的后缀**：

| 后缀 | 用途 | 例子 |
| --- | --- | --- |
| `List` | 列表页 | `ActivityList.vue` |
| `Detail` | 详情页 | `ActivityDetail.vue` |
| `Form` | 新增 / 编辑表单页 | `ActivityForm.vue` |
| `View` | 其他独立页面 | `LoginView.vue`、`NotFoundView.vue` |
| `Dialog` | 弹窗组件 | `SignupAuditDialog.vue` |

**`Form` 后缀同时用于新增和编辑**，这是刻意的 —— 它提醒你“这是一个共用的表单组件”，不要再去建一个 `ActivityCreate.vue`。

### 变量与函数

| 类型 | 规范 | 例子 |
| --- | --- | --- |
| 变量 | camelCase | `activityList`、`signupDeadline` |
| 常量 | 大写下划线 | `ACTIVITY_STATUS`、`PAGE_SIZE_OPTIONS` |
| 布尔变量 | 以 `is` / `has` / `can` / `should` 开头 | `isEdit`、`hasPermission`、`canDelete` |
| 事件处理函数 | 以 `handle` 开头 | `handleSearch`、`handleSubmit` |
| 数据请求函数 | 以 `get` / `fetch` 开头 | `getActivityList` |
| 组合式函数 | 以 `use` 开头 | `useTable` |
| 纯函数（判断类） | 以 `is` / `can` / `has` 开头 | `isTimeConflict`、`canSignup` |

**布尔变量加前缀的价值**：看到一个 `editable` 你不知道它是布尔还是函数，看到 `canEdit` 就知道是布尔。**这种不确定会在读代码时消耗注意力。**

### 事件与 props

| 场景 | 规范 | 例子 |
| --- | --- | --- |
| props 定义 | camelCase | `defineProps({ activityId: Number })` |
| 模板里传 props | kebab-case | `<ActivityCard :activity-id="row.id" />` |
| 自定义事件 | kebab-case | `emit('update:modelValue')`、`emit('audit-pass')` |
| 事件处理函数 | camelCase | `@audit-pass="handleAuditPass"` |

**“模板里用 kebab-case、定义时用 camelCase”是 Vue 的约定。** 严格来说模板里两种写法都能用，但统一用 kebab-case，和原生 HTML 属性风格一致。

### CSS 类名

统一用 **BEM 风格**（块-元素-修饰符）：

```vue
<template>
  <div class="activity-card">
    <h3 class="activity-card__title">{{ title }}</h3>
    <span class="activity-card__quota activity-card__quota--full">已满</span>
  </div>
</template>

<style scoped lang="scss">
.activity-card {
  &__title { }
  &__quota {
    &--full { color: var(--el-color-danger); }
  }
}
</style>
```

三条规则：

- 块名用业务名，不要用 `box`、`wrap`、`inner` 这种无语义的名字
- 元素用双下划线连接
- 修饰符用双连字符连接

**配合 `<style scoped>` 之后，命名冲突的风险已经很低了。** BEM 的价值在于**可读性** —— 看到 `activity-card__quota--full` 就知道它属于哪个块、是什么状态。

**不要用 `!important`。** 需要覆盖 Element Plus 的样式时，用 `:deep()`：

```scss
.activity-card {
  :deep(.el-card__body) {
    padding: 12px;
  }
}
```

## 四、提交进仓库和不提交的

**必须提交：**

| 文件 | 为什么 |
| --- | --- |
| `package.json` / `pnpm-lock.yaml` | 锁文件保证所有人装到同样的版本 |
| `.env.development` / `.env.production` | 值里没有密钥，是环境相关的地址 |
| `.env.example` | 供别人参考要配哪些变量 |
| `jsconfig.json` | 别名提示，团队一致 |
| `docs/` | 项目文档是交付物 |
| `README.md` | 别人看仓库的第一份材料 |

**不要提交：**

```bash [.gitignore]
# 依赖
node_modules

# 构建产物
dist
dist-ssr

# 编辑器与系统
.DS_Store
.idea
.vscode/*
!.vscode/extensions.json

# 自动生成
src/auto-imports.d.ts
src/components.d.ts

# 本地配置与日志
*.local
.env.local
.env.*.local
*.log
npm-debug.log*
pnpm-debug.log*

# 测试覆盖率
coverage
```

**两个 `.d.ts` 文件为什么要忽略**：它们是插件自动生成的，内容依赖你本地装了什么组件、什么版本。团队协作时每个人的都不一样，提交上去会产生无意义的冲突。

**但忽略之后，新克隆的人第一次打开编辑器会有大量“找不到 ref”的报错。** 所以要在 README 里写明：

> 第一次启动会自动生成 `src/auto-imports.d.ts` 和 `src/components.d.ts`，在此之前编辑器可能报“找不到 ref”，启动一次即可消除。

**这就是“自动生成的文件不提交，但要在文档里说清怎么生成”这条原则。** 只做前一半会给别人添麻烦。

## 五、检查清单

建工程时对着这份清单过一遍。**每一项都应该能回答“是”：**

| 检查项 | 怎么验证 |
| --- | --- |
| 打开 `src/`，三秒内能说出每个目录装什么 | 遮住目录名，只看文件列表猜 |
| `views/` 按业务模块分，不是按 list / form 分 | 看目录名是不是业务名词 |
| `api/` 每个业务模块一个文件 | 文件数和模块数对得上 |
| 业务规则集中在 `domain/` | 页面里搜 `status ===` 应该在少数几处 |
| 组件同时有 PascalCase 文件和 kebab-case 文件吗 | 不应该，组件统一 PascalCase |
| 布尔变量有 `is` / `can` / `has` 前缀 | 搜 `const .* = true` |
| 代码里搜不到三级以上的相对路径 | `grep -rn "\.\./\.\./\.\." src/` 应为 0 |
| 危险操作有二次确认 | 点删除、下架，看有没有弹窗 |
| `.gitignore` 覆盖了该忽略的 | `git status` 里没有 `node_modules` / `dist` |
| `.env.example` 存在 | 检查文件是否存在 |
| README 写清了自动生成文件的问题 | 读一遍“本地运行”那一段 |

## 小结

- **目录结构是“工程质量”这个维度里最直接能看出来的东西。**
- **六条规则**：`views` 按业务模块分、组件按复用范围分、`api` 按模块分文件、`domain` 与 `utils` 分开、`composables` 第二个页面要用时才抽、`layouts` 不放业务。
- **接口函数只做拼路径和传参**，字段名转换放在同一个文件里。
- **`domain` 放业务规则，`utils` 放通用工具。** 判断标准是“换个项目还用不用得上”。
- **业务规则集中之后可以单独测试**，`isTimeConflict` 这类有边界条件的纯函数最适合。
- **不要提前抽象。** 第二个页面要用同一段逻辑时再抽。
- **命名约定**：组件 PascalCase，其他 kebab-case；布尔加 `is` / `can` / `has` 前缀；事件处理函数加 `handle` 前缀。
- **CSS 用 BEM**，配合 `scoped`。不用 `!important`，覆盖第三方样式用 `:deep()`。
- **自动生成的文件不提交，但要在 README 里说清怎么生成。** 只做前一半会给别人添麻烦。
- **判断一个目录结构好不好：改一个需求时，你要在几个目录之间跳？** 越少越好。

---

上一页：[接口约定](/project/api) · 下一页：[三阶段交付](/project/milestones)
