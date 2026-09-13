# 3.3 模块化与目录组织

## 一次“改一个功能动了六个目录”的经历

活动状态标签要改一下样式。你打开项目，要找它在哪：

| 你猜的位置 | 实际位置 |
| --- | --- |
| `src/views/activity/ActivityStatusTag.vue` | 不存在 |
| `src/components/ActivityStatusTag.vue` | 不存在 |
| `src/components/common/tag/StatusTag.vue` | 不存在 |

最后是在 `src/components/base/tags/ActivityStatusTag.vue` 找到的。
而在同一个目录里，还躺着 `VenueStatusTag.vue`、`ReviewStatusTag.vue`、
`EnrollStatusTag.vue` —— 四个不同功能的状态标签，因为“都是标签”被放在了一起。

接着你发现事情更麻烦：改完标签样式要顺手改一下活动接口的返回处理，
于是又要去 `src/api/`；改完接口要动状态管理，去 `src/stores/`；
再改类型定义，去 `src/types/`。**一个“改活动状态展示”的需求，动了六个目录。**

这不是因为你笨，而是因为目录按**文件类型**组织 ——
它把“同一件事”的代码拆散到了六处。

## ES Module 的两种导出方式

先说清楚语法，再讲组织方式。

```js [src/shared/utils/format.js]
// 具名导出：导出多个，名字由本文件决定
export function formatDeadline(time) {
  return new Date(time).toLocaleString('zh-CN')
}

export function formatCapacity(enrolled, total) {
  return `${enrolled}/${total}`
}

export const DATE_FORMAT = 'YYYY-MM-DD'
```

```js [src/shared/utils/format.js]
// 默认导出：一个文件只有一个
export default function formatDeadline(time) {
  return new Date(time).toLocaleString('zh-CN')
}
```

引入的写法：

```js [src/views/ActivityListView.vue]
// 具名导出：用 {} 精确引入，名字必须和导出时一致
import { formatDeadline, formatCapacity } from '@/shared/utils/format'

// 具名导出可以重命名
import { formatDeadline as formatTime } from '@/shared/utils/format'

// 把整个模块作为对象引入
import * as formatters from '@/shared/utils/format'

// 默认导出：名字由引入方自己取
import formatDeadline from '@/shared/utils/format'

// 两者混用：默认导出在前，具名导出在后
import formatDeadline, { DATE_FORMAT } from '@/shared/utils/format'
```

| 写法 | 特点 |
| --- | --- |
| `export function foo` | 具名导出，支持按需引入，支持重命名 |
| `export default function foo` | 默认导出，一个文件一个，名字由引入方决定 |
| `import { a, b }` | 具名引入，名字必须对上（除非重命名） |
| `import x from` | 引入默认导出 |
| `import * as ns` | 引入整个模块 |

## 默认导出与具名导出怎么选

这是新人最常纠结的地方。给一张决策表：

| 文件内容 | 推荐方式 | 理由 |
| --- | --- | --- |
| 一个 Vue 组件（`.vue`） | 默认导出（由编译器处理） | 文件名即组件名，引入时可以自由命名 |
| 一组相关工具函数 | **具名导出** | 一个文件多个函数，用到哪个引哪个 |
| 组合式函数（`useXxx`） | 具名导出 | 便于重命名，也便于工具做静态分析 |
| 常量集合 | 具名导出 | 需要哪个引哪个 |
| 只有一个实例的模块（如请求实例） | 默认导出 | 语义就是“这个文件就是它” |
| 类型定义（`.d.ts` 或 JSDoc） | 具名导出 | 类型名要能精确引用 |

两种方式的实际影响：

| 对比项 | 默认导出 | 具名导出 |
| --- | --- | --- |
| 引入时能否自由改名 | 能 | 需要 `as` |
| 编辑器自动补全 | 需要先知道名字 | **输入 `{` 就列出全部** |
| 能否只引入一部分 | 不能（必须整个引入） | 能 |
| 重命名导出项时的安全性 | **低**（引入方不会报错） | 高（引入方立刻报错） |
| 静态分析 / 按需打包 | 较难 | 容易 |

第三、四行是具名导出最重要的优势。第 11 周做综合项目时会遇到这样的场景：
`format.js` 里删掉了 `formatCapacity`，如果全项目都用默认导出，
编辑器不会提醒任何地方；用具名导出的话，所有引用了它的文件立刻标红。

::: warning 一个文件里不要混用两种导出
```js [✗ 不推荐]
export default function a() {}
export function b() {}
export const c = 1
```

能用，但会给引入方带来困惑：到底该用哪种方式引？
**规则：一个文件只选一种风格。** 需要多个导出就用具名，只有一个就默认导出。
:::

## 动态导入与路由懒加载

静态的 `import` 会在**构建时**就被打进产物，无论它用不用得到。

```js [✗ 全部打进主包]
import ActivityListView from '@/features/activity/ActivityListView.vue'
import ReviewListView from '@/features/review/ReviewListView.vue'
import VenueListView from '@/features/venue/VenueListView.vue'
```

三个页面都进主包，用户打开登录页也要下载这三页的代码。正确的做法是用
**动态导入** —— `import()` 是一个函数调用，返回 Promise，构建时会**单独打成一个文件**：

```js [src/app/router/index.js]
const routes = [
  {
    path: '/activities',
    // 访问这个路由时才去下载这个文件
    component: () => import('@/features/activity/ActivityListView.vue')
  },
  {
    path: '/reviews',
    component: () => import('@/features/review/ReviewListView.vue')
  },
  {
    path: '/venues',
    component: () => import('@/features/venue/VenueListView.vue')
  }
]
```

构建输出会变成：

```text [构建输出]
dist/assets/index-Ab3dEf.js                    42.10 kB   ← 登录页 + 公共代码
dist/assets/ActivityListView-Cd4eFg.js         18.32 kB   ← 访问 /activities 时才下
dist/assets/ReviewListView-Hi5jKl.js           15.77 kB   ← 访问 /reviews 时才下
dist/assets/VenueListView-Mn6oPq.js            21.04 kB   ← 访问 /venues 时才下
```

| 对比 | 静态 `import` | 动态 `import()` |
| --- | --- | --- |
| 打包位置 | 全部进主包 | 各自成 chunk |
| 首屏下载量 | 全部页面的代码 | 只有当前页 |
| 写法 | `import X from '...'` | `() => import('...')` |
| 什么时候用 | 首屏就需要的代码 | 路由页面、弹窗、体积大的库 |

**判断标准：这个模块在首屏一定用得到吗？** 用得到就静态引入，用不到就动态引入。

路由懒加载的更多细节在[单元 9](/unit09/02-nested-params) 讲，这里先记住写法和收益。

::: tip 动态导入也能用在非路由场景
比如一个只在点击时打开的数据看板弹窗：

```js [src/features/dashboard/DashboardButton.vue]
async function openDashboard() {
  const { default: DashboardModal } = await import('./DashboardModal.vue')
  showModal(DashboardModal)
}
```

`import()` 返回的模块对象里，默认导出在 `default` 字段上 ——
所以这里用了 `{ default: DashboardModal }` 的写法。**这是最容易写错的一处。**
:::

## 模块解析与路径别名

引入一个模块时，解析器按下面的顺序找：

| 写法 | 解析成什么 |
| --- | --- |
| `import x from 'vue'` | `node_modules/vue` 的入口文件 |
| `import x from '@/utils/a'` | 别名替换成 `src/utils/a`，再补扩展名 |
| `import x from './a.js'` | 相对当前文件的 `a.js` |
| `import x from './a'` | 补扩展名，找 `a.js` / `a.ts` 等 |
| `import x from '../components/Foo.vue'` | 相对路径 |

相对路径的层级一深就会出问题：

```js [✗ 深层相对路径]
// src/features/activity/components/ActivityTable.vue 里
import { formatDeadline } from '../../../../shared/utils/format'
```

数一下：四个 `../`。它的三个缺点：

| 缺点 | 具体表现 |
| --- | --- |
| 数不清层级 | 多写一个少写一个都是“找不到模块” |
| 文件移动后全要改 | 把文件往上挪一层，里面的相对路径全得跟着改 |
| 看不出指向哪里 | `../../../../` 是哪里？只能靠数 |

用别名之后：

```js [✓ 用别名]
import { formatDeadline } from '@/shared/utils/format'
```

别名配置在 [2.5](/unit02/05-env-config#路径别名) 讲过，两处保持一致：
`vite.config.js`（构建时用）和 `jsconfig.json`（编辑器用）。

::: tip 一条实用的约束
**同目录下的文件用相对路径 `./`，跨目录的一律用 `@/`。**

这样做的效果是：`../` 几乎不再出现。约束简单、好记，评审时也好检查 ——
`grep -rn "\.\./" src/` 就能找出所有违反的文件。
:::

## 按功能分目录，不按文件类型分

回到开头那个问题。两种组织方式的差别，用校园活动服务平台的真实场景对比一下。

### 反例：按文件类型分

```text [✗ 按文件类型分目录]
src/
├── components/            ← 所有组件都在这，40 多个文件挤一层
│   ├── ActivityCard.vue
│   ├── ActivityStatusTag.vue
│   ├── EnrollStatusTag.vue
│   ├── ReviewStatusTag.vue
│   ├── VenueStatusTag.vue
│   ├── ActivityFilterBar.vue
│   ├── ReviewTable.vue
│   ├── VenuePicker.vue
│   ├── TimeRangePicker.vue
│   └── ...（还有 30 多个）
├── views/
│   ├── ActivityListView.vue
│   ├── ReviewListView.vue
│   └── VenueListView.vue
├── api/
│   ├── activity.js
│   ├── review.js
│   └── venue.js
├── stores/
│   ├── activity.js
│   ├── review.js
│   └── venue.js
├── utils/
│   ├── format.js
│   └── validate.js
├── types/
└── styles/
```

### 正例：按功能分

```text [✓ 按功能分目录]
src/
├── app/                      应用级：整个应用只有一份的东西
│   ├── main.js
│   ├── App.vue
│   ├── router/
│   │   └── index.js
│   └── styles/
│       └── main.css
├── shared/                   跨功能复用：不止一个功能在用
│   ├── components/
│   │   ├── AppConfirmDialog.vue
│   │   └── AppEmptyState.vue
│   ├── composables/
│   │   └── usePagination.js
│   ├── utils/
│   │   └── format.js
│   └── api/
│       └── request.js
└── features/                 业务功能，一个功能一个目录
    ├── activity/             活动管理
    │   ├── components/
    │   │   ├── ActivityCard.vue
    │   │   ├── ActivityStatusTag.vue
    │   │   └── ActivityFilterBar.vue
    │   ├── composables/
    │   │   └── useActivityFilter.js
    │   ├── api.js
    │   ├── store.js
    │   └── ActivityListView.vue
    ├── review/               报名审核
    │   ├── components/
    │   │   ├── ReviewTable.vue
    │   │   └── ReviewStatusTag.vue
    │   ├── api.js
    │   ├── store.js
    │   └── ReviewListView.vue
    └── venue/                场次与场地
        ├── components/
        │   ├── VenuePicker.vue
        │   └── TimeRangePicker.vue
        ├── api.js
        └── VenueListView.vue
```

### 对比一下实际差别

| 场景 | 按类型分 | 按功能分 |
| --- | --- | --- |
| 找“活动状态标签在哪” | 在 `components/` 的 40 个文件里翻 | 直接进 `features/activity/components/` |
| 改“活动筛选”要动几个目录 | 4 到 6 个 | 1 个 |
| 删掉“场地管理”这个功能 | 要在 6 个目录里逐个找相关文件 | 删掉 `features/venue/` 一个目录 |
| 新人接手 | 看不出模块边界 | 目录结构就是功能清单 |
| 两个人同时开发 | 经常改到同一个目录，容易冲突 | 各改各的功能目录，冲突少 |

最后一行在协作时特别重要。按类型分目录时，所有人都在往同一个
`components/` 里加文件，`git` 冲突概率明显高得多。

::: tip 那 `shared/` 里的东西怎么判断
判断标准是“**有几个功能在用**”：

- 只有一个功能在用 → 放到那个功能的目录里。
- 两个及以上功能在用 → 移到 `shared/`。

**先放功能目录，等第二个功能要用的时候再移出去。** 不要一开始就为了“以后可能复用”
把东西放进 `shared/` —— 结果是 `shared/` 里堆满了只有一个功能用的组件，
比按类型分还乱。
:::

::: warning 不要一上来就搞三层嵌套
按功能分目录的原则是“**一个功能一个目录**”，不是“目录越深越好”。

刚开始做项目时，`features/activity/` 下面平铺几个文件就够了，
不需要再分 `components/`、`composables/`、`api/`。
**等这个功能下的文件超过六七个再分。**
:::

## 命名约定

目录结构定好了，命名也要统一。**同一个东西在三个地方的名字应该能对上。**

| 对象 | 约定 | 例子 |
| --- | --- | --- |
| 目录 | kebab-case | `features/activity-apply/` |
| 组件文件 | PascalCase | `ActivityCard.vue` |
| 页面组件 | PascalCase + 后缀 | `ActivityListView.vue`、`ActivityDetailView.vue` |
| 普通脚本文件 | kebab-case | `format-date.js`、`activity-status.js` |
| 组合式函数 | `use` 前缀 + camelCase | `useActivityList.js`、`usePagination.js` |
| 常量 | UPPER_SNAKE_CASE | `MAX_ENROLL_COUNT`、`ACTIVITY_STATUS` |
| 布尔变量 | `is` / `has` / `can` 前缀 | `isPublished`、`hasConflict`、`canEnroll` |
| 事件名 | kebab-case | `update:modelValue`、`status-change` |

页面组件的后缀值得单独说。三种后缀各自对应一种页面形态：

| 后缀 | 页面形态 | 例子 |
| --- | --- | --- |
| `ListView` | 列表页，带搜索筛选和分页 | `ActivityListView.vue` |
| `DetailView` | 详情页，展示单条数据 | `ActivityDetailView.vue` |
| `FormView` | 新建 / 编辑表单页 | `ActivityFormView.vue` |

**这个约定的价值在于：看到文件名就知道这个页面长什么样**，
不用打开就知道该不该有分页、该不该有提交按钮。

::: danger 大小写不一致会埋很久的雷
`ActivityCard.vue` 和 `activityCard.vue` 在 macOS 上会被当成同一个文件，
在 Linux 上不会。

于是会出现：本地正常，流水线里报 `Failed to resolve import`。
处理办法和 2.4 讲的一样 —— **引入时写的路径要和真实文件名完全一致**。

另外，目录名统一用 kebab-case，不要出现 `features/Activity/` 和
`features/review/` 这种混用。**大小写风格混用是排查成本最高的低级问题之一。**
:::

## 小结

- 具名导出适合一个文件多个导出项，默认导出适合“这个文件就是它”。
- 具名导出的优势：引入时按需、重命名时安全、支持静态分析。
- 动态 `import()` 会单独打成一个 chunk，用于路由懒加载和按需加载的弹窗。
- 解析时优先用别名 `@/`；同目录用 `./`，跨目录用 `@/`，避免 `../`。
- 按功能分目录：`app/`（应用级）、`shared/`（跨功能复用）、`features/xxx/`（业务功能）。
- 判断放 `shared/` 的标准是“有两个以上功能在用”，不是“以后可能复用”。
- 命名约定要能对上：目录 kebab-case、组件 PascalCase、组合式函数 `use` 前缀。
- 大小写不一致是排查成本最高的低级问题，引入路径要与真实文件名完全一致。

## 常见坑

::: details 坑 1：`import()` 拿不到默认导出
**现象**：`const Modal = await import('./Modal.vue')` 之后，`Modal` 用不了。

**原因**：`import()` 返回的是**模块对象**，不是默认导出本身。
默认导出在 `default` 字段上。

**处理**：

```js [✓ 正确写法]
const { default: Modal } = await import('./Modal.vue')
```

**验证方法**：`console.log(await import('./Modal.vue'))` 打印出来看一眼，
结构一目了然。
:::

::: details 坑 2：循环依赖
**现象**：某个模块导出的是 `undefined`，但代码里明明写了 `export`。

**原因**：两个模块互相 import（A 引 B、B 引 A），加载顺序被打乱。

**处理**：这是设计问题，不是配置问题。三个方向 ——

1. 把公共部分抽到第三个文件里，两边都引它。
2. 其中一边改成动态 `import()`。
3. 重新想想模块边界是不是划错了（通常是的）。

**判断方法**：`grep` 一下这两个文件里互相出现的名字。
如果 A 和 B 互相依赖，说明它们可能应该合并，或者中间的公共部分应该独立出去。
:::

::: details 坑 3：`@/` 能用但相对路径也在用
**现象**：同一个文件里既有 `@/shared/utils/format`，也有 `../../utils/format`。

**原因**：没有明确的约束，各人凭习惯写。

**处理**：定一条规则并检查：

```bash [终端]
# 找出所有用了上级相对路径的地方
grep -rn "\.\./" src/
```

**规则：同目录用 `./`，跨目录用 `@/`。** 这条规则简单到能在评审时一眼看出来。
:::

::: details 坑 4：把所有组件都塞进 `shared/`
**现象**：`shared/components/` 里有 30 个组件，其中 25 个只有一个页面在用。

**原因**：一开始就想着“以后可能会复用”。

**处理**：把这些组件移回各自的功能目录。判断标准是**现在有几个地方在用**，
不是“以后会不会复用”。

**收益**：改活动相关的东西时，你只需要在一个目录里找。
:::

::: details 坑 5：一个文件导出十几个东西
**现象**：`utils/index.js` 里有 20 个函数，从日期格式化到权限判断全都有。

**原因**：图方便，什么都往一个文件里塞。

**处理**：按职责拆分。比如拆成 `format.js`（格式化）、
`validate.js`（校验）、`permission.js`（权限）。

**判断方法**：如果一个文件里的函数彼此之间没什么关系，就该拆。
**“文件名描述不了这个文件里的内容”就是拆分的信号。**
:::

::: details 坑 6：路由页面不写懒加载
**现象**：首屏需要下载的 JS 有两三百 KB，其中大部分是用户根本不会访问的页面。

**原因**：路由配置里用了静态 `import`。

**处理**：改成 `component: () => import('...')`，然后重新构建，
对比改动前后的首屏体积。

**这是投入产出比最高的优化之一** —— 改几行代码，首屏体积可能减少一半。
:::

## 课后练习

::: details 练习 1：重组一个按类型分目录的项目
假设你有下面这样一个项目结构，请把它改成按功能分目录。

```text [待重组的项目]
src/
├── components/
│   ├── ActivityCard.vue
│   ├── ActivityStatusTag.vue
│   ├── ReviewTable.vue
│   ├── ReviewStatusTag.vue
│   ├── VenuePicker.vue
│   └── AppConfirmDialog.vue
├── views/
│   ├── ActivityListView.vue
│   ├── ReviewListView.vue
│   └── VenueListView.vue
├── api/
│   ├── activity.js
│   ├── review.js
│   └── venue.js
└── utils/
    └── format.js
```

要求：

1. 画出重组后的目录树。
2. 说明每个文件的归属理由。
3. 指出哪些东西应该放进 `shared/`，为什么。

**验收点**：`AppConfirmDialog.vue` 和 `format.js` 的归属要能说清楚 ——
判断依据是“现在有几个功能在用”，不是“它是通用的”。

**参考思路**：`AppConfirmDialog` 是二次确认弹窗，三个功能都要用，
放 `shared/components/`；`format.js` 里的 `formatDeadline` 如果只有活动功能用，
就放 `features/activity/utils/`。
:::

::: details 练习 2：把路由改成懒加载
在一个有至少三个路由页面的项目里：

1. 记录改动前 `pnpm build` 的主包体积。
2. 把所有路由组件改成 `() => import('...')`。
3. 再构建一次，记录主包体积和新增的 chunk。
4. 用 `pnpm preview` 分别访问每个页面，确认懒加载生效（Network 面板里能看到对应 chunk 被下载）。

**验收标准**

| 项目 | 要求 |
| --- | --- |
| 数据对比 | 改动前后的主包体积有具体数字 |
| 懒加载生效 | 访问某个路由时才下载对应的 chunk |
| 首屏不加载 | 没访问的路由 chunk 不出现在首屏请求里 |

**参考思路**：首屏请求可以在 Network 面板里按 JS 类型筛选后观察。
如果所有 chunk 一开始就全下载了，说明还有地方用了静态 import。
:::

::: details 练习 3：判断该用哪种导出
下面六种场景，分别该用默认导出还是具名导出？说明理由。

1. `src/shared/utils/format.js` —— 里面有三个格式化函数。
2. `src/features/activity/api.js` —— 只有一个导出的请求实例。
3. `src/shared/composables/usePagination.js` —— 一个分页逻辑的组合式函数。
4. `src/features/activity/constants.js` —— 活动状态枚举、类型枚举、名额上限常量。
5. `src/shared/utils/validate.js` —— 学号校验、手机号校验、时段冲突校验。
6. `src/features/review/store.js` —— 一个 Pinia store。

**验收点**：第 4、5 两题的答案要能落到“一个文件多个导出项”这个判断上。
第 6 题要想清楚 Pinia 的 `defineStore` 返回什么、通常怎么导出。
:::

::: details 练习 4：写一份命名约定清单
给本课程的项目写一份命名约定清单，至少包含八类对象。格式：

| 对象 | 约定 | 示例 | 反例 |
| --- | --- | --- | --- |
| | | | |

**参考思路**：从这一节讲过的八类里选，再加上你认为重要的（比如 CSS 类名、
接口函数名、路由路径）。**反例一栏必须填** —— 写反例的过程就是明确边界的过程。

**验收点**：清单要能被拿去做成一条 ESLint 规则，或者至少在评审时能逐条对照检查。
如果某条约定你自己都说不清什么算违反，说明它还不够具体。
:::

---

上一节：[3.2 ESLint 与 Prettier 配置](/unit03/02-eslint-prettier) ·
下一节：[3.4 Git 协作流程](/unit03/04-git-flow)
