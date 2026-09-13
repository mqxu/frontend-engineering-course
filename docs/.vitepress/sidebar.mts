import type { DefaultTheme } from 'vitepress'

type Item = DefaultTheme.SidebarItem

// ---------------------------------------------------------------------------
// 课程导学
// ---------------------------------------------------------------------------
const guide: Item[] = [
  { text: '课程导读', link: '/guide/' },
  { text: '怎么用这套教程', link: '/guide/how-to-use' },
  { text: '前端学习路线', link: '/guide/learning-path' },
  { text: '开发环境准备', link: '/guide/environment' },
  { text: '12 周课程地图', link: '/guide/roadmap' }
]

// ---------------------------------------------------------------------------
// 各单元的目录条目
// ---------------------------------------------------------------------------
const units: Record<number, { title: string; items: Item[] }> = {
  1: {
    title: '工程化认知与开发环境',
    items: [
      { text: '单元导学', link: '/unit01/' },
      { text: '1.1 前端是怎么走到工程化的', link: '/unit01/01-why-engineering' },
      { text: '1.2 一个现代前端工程长什么样', link: '/unit01/02-modern-project' },
      { text: '1.3 学习路线与岗位方向', link: '/unit01/03-learning-path' },
      { text: '1.4 开发环境搭建与自检', link: '/unit01/04-environment' },
      { text: '课后练习', link: '/unit01/practice' }
    ]
  },
  2: {
    title: 'Node 生态与构建工具',
    items: [
      { text: '单元导学', link: '/unit02/' },
      { text: '2.1 Node.js 与版本管理', link: '/unit02/01-node' },
      { text: '2.2 包管理器与依赖安装', link: '/unit02/02-package-manager' },
      { text: '2.3 package.json 逐字段精讲', link: '/unit02/03-package-json' },
      { text: '2.4 构建工具与 Vite', link: '/unit02/04-vite' },
      { text: '2.5 环境变量与常用配置', link: '/unit02/05-env-config' },
      { text: '课后练习', link: '/unit02/practice' }
    ]
  },
  3: {
    title: '工程规范与 Git 协作',
    items: [
      { text: '单元导学', link: '/unit03/' },
      { text: '3.1 为什么需要代码规范', link: '/unit03/01-why-lint' },
      { text: '3.2 ESLint 与 Prettier 配置', link: '/unit03/02-eslint-prettier' },
      { text: '3.3 模块化与目录组织', link: '/unit03/03-modules-structure' },
      { text: '3.4 Git 协作流程', link: '/unit03/04-git-flow' },
      { text: '3.5 自动构建流水线', link: '/unit03/05-ci' },
      { text: '课后练习', link: '/unit03/practice' }
    ]
  },
  4: {
    title: '模板语法与响应式基础',
    items: [
      { text: '单元导学', link: '/unit04/' },
      { text: '4.1 声明式渲染：从操作 DOM 到描述状态', link: '/unit04/01-declarative' },
      { text: '4.2 模板语法与数据绑定', link: '/unit04/02-template-syntax' },
      { text: '4.3 事件绑定与指令总览', link: '/unit04/03-event-directive' },
      { text: '4.4 ref 与 reactive', link: '/unit04/04-reactivity' },
      { text: '4.5 响应式原理初探', link: '/unit04/05-reactivity-principle' },
      { text: '课后练习', link: '/unit04/practice' }
    ]
  },
  5: {
    title: '计算属性与渲染控制',
    items: [
      { text: '单元导学', link: '/unit05/' },
      { text: '5.1 计算属性与缓存', link: '/unit05/01-computed' },
      { text: '5.2 侦听器', link: '/unit05/02-watch' },
      { text: '5.3 条件渲染', link: '/unit05/03-conditional' },
      { text: '5.4 列表渲染与键值', link: '/unit05/04-list' },
      { text: '5.5 四态页面规范', link: '/unit05/05-four-states' },
      { text: '案例 01 · 增删改查清单', link: '/unit05/06-case-crud' },
      { text: '案例 02 · 可排序筛选的数据表格', link: '/unit05/07-case-grid' },
      { text: '课后练习', link: '/unit05/practice' }
    ]
  },
  6: {
    title: '用户交互与表单绑定',
    items: [
      { text: '单元导学', link: '/unit06/' },
      { text: '6.1 事件处理的完整写法', link: '/unit06/01-events' },
      { text: '6.2 事件与按键修饰符', link: '/unit06/02-modifiers' },
      { text: '6.3 表单绑定', link: '/unit06/03-form-binding' },
      { text: '6.4 表单校验', link: '/unit06/04-validation' },
      { text: '6.5 生命周期与副作用清理', link: '/unit06/05-lifecycle' },
      { text: '案例 05 · Markdown 编辑器', link: '/unit06/06-case-markdown' },
      { text: '课后练习', link: '/unit06/practice' }
    ]
  },
  7: {
    title: '组件基础与父子通信',
    items: [
      { text: '单元导学', link: '/unit07/' },
      { text: '7.1 单文件组件与拆分依据', link: '/unit07/01-sfc' },
      { text: '7.2 父子通信：props', link: '/unit07/02-props' },
      { text: '7.3 父子通信：emits', link: '/unit07/03-emits' },
      { text: '7.4 组件上的 v-model', link: '/unit07/04-vmodel' },
      { text: '案例 03 · 树状视图与递归组件', link: '/unit07/05-case-tree' },
      { text: '案例 09 · 可编辑表格', link: '/unit07/06-case-editable-table' },
      { text: '课后练习', link: '/unit07/practice' }
    ]
  },
  8: {
    title: '组件进阶与逻辑复用',
    items: [
      { text: '单元导学', link: '/unit08/' },
      { text: '8.1 插槽', link: '/unit08/01-slots' },
      { text: '8.2 依赖注入', link: '/unit08/02-provide-inject' },
      { text: '8.3 内置组件', link: '/unit08/03-builtin' },
      { text: '8.4 组合式函数', link: '/unit08/04-composables' },
      { text: '8.5 自定义指令', link: '/unit08/05-directives' },
      { text: '案例 06 · 模态框与全局通知', link: '/unit08/06-case-modal' },
      { text: '案例 08 · 画板与撤销重做', link: '/unit08/07-case-canvas' },
      { text: '课后练习', link: '/unit08/practice' }
    ]
  },
  9: {
    title: '路由与登录鉴权',
    items: [
      { text: '单元导学', link: '/unit09/' },
      { text: '9.1 路由基础', link: '/unit09/01-router-basics' },
      { text: '9.2 动态参数与嵌套路由', link: '/unit09/02-nested-params' },
      { text: '9.3 路由守卫', link: '/unit09/03-guards' },
      { text: '9.4 登录鉴权完整链路', link: '/unit09/04-auth-flow' },
      { text: '案例 10 · 登录与鉴权', link: '/unit09/05-case-auth' },
      { text: '课后练习', link: '/unit09/practice' }
    ]
  },
  10: {
    title: 'Pinia 与数据请求层',
    items: [
      { text: '单元导学', link: '/unit10/' },
      { text: '10.1 什么时候需要全局状态', link: '/unit10/01-when-global' },
      { text: '10.2 Pinia 两种写法', link: '/unit10/02-pinia-basics' },
      { text: '10.3 状态持久化', link: '/unit10/03-persist' },
      { text: '10.4 请求层封装', link: '/unit10/04-request-layer' },
      { text: '10.5 错误分层处理', link: '/unit10/05-error-handling' },
      { text: '案例 04 · 从接口获取数据', link: '/unit10/06-case-fetch' },
      { text: '课后练习', link: '/unit10/practice' }
    ]
  },
  11: {
    title: '项目启动与核心业务',
    items: [
      { text: '单元导学', link: '/unit11/' },
      { text: '11.1 从需求到页面清单', link: '/unit11/01-requirements' },
      { text: '11.2 工程初始化与目录规划', link: '/unit11/02-scaffold' },
      { text: '11.3 布局骨架与嵌套路由', link: '/unit11/03-layout' },
      { text: '11.4 列表页标准做法', link: '/unit11/04-list-page' },
      { text: '11.5 表单页标准做法', link: '/unit11/05-form-page' },
      { text: '课后练习', link: '/unit11/practice' }
    ]
  },
  12: {
    title: '联调优化部署与答辩',
    items: [
      { text: '单元导学', link: '/unit12/' },
      { text: '12.1 前后端联调', link: '/unit12/01-integration' },
      { text: '12.2 构建优化', link: '/unit12/02-build-optimize' },
      { text: '12.3 部署上线', link: '/unit12/03-deploy' },
      { text: '12.4 交付材料与答辩', link: '/unit12/04-delivery' },
      { text: '课后练习', link: '/unit12/practice' }
    ]
  }
}

// 模块 → 单元编号
const MODULES: { text: string; units: number[] }[] = [
  { text: '模块一 · 工程化认知与工具链', units: [1, 2, 3] },
  { text: '模块二 · Vue 3 核心基础', units: [4, 5, 6] },
  { text: '模块三 · 组件化开发', units: [7, 8] },
  { text: '模块四 · 应用架构', units: [9, 10] },
  { text: '模块五 · 综合项目实战', units: [11, 12] }
]

/** 生成侧边栏：所属模块展开，当前单元自动打开，其余收起 */
function unitSidebar(active: number): Item[] {
  const mods: Item[] = MODULES.map((m) => ({
    text: m.text,
    collapsed: false,
    items: m.units.map((n) => ({
      text: '单元 ' + n + ' · ' + units[n].title,
      collapsed: n !== active,
      items: units[n].items
    }))
  }))
  return [{ text: '课程导学', collapsed: true, items: guide }, ...mods]
}

const projectSidebar: Item[] = [
  {
    text: '综合项目 · 校园活动服务平台',
    items: [
      { text: '项目总览', link: '/project/' },
      { text: '需求规格说明', link: '/project/requirements' },
      { text: '业务规则与状态流转', link: '/project/rules' },
      { text: '接口约定', link: '/project/api' },
      { text: '目录结构与命名约定', link: '/project/structure' },
      { text: '三阶段交付', link: '/project/milestones' }
    ]
  },
  {
    text: '参考实现',
    collapsed: false,
    items: [
      { text: '登录与鉴权', link: '/project/impl-auth' },
      { text: '活动管理模块', link: '/project/impl-activity' },
      { text: '报名审核模块', link: '/project/impl-signup' },
      { text: '场次与场地模块', link: '/project/impl-session' },
      { text: '数据看板', link: '/project/impl-dashboard' }
    ]
  }
]

const caseSidebar: Item[] = [
  {
    text: '案例库',
    items: [
      { text: '案例总览', link: '/cases/' },
      { text: '01 · 增删改查清单', link: '/cases/01-crud' },
      { text: '02 · 可排序筛选的数据表格', link: '/cases/02-grid' },
      { text: '03 · 树状视图与递归组件', link: '/cases/03-tree' },
      { text: '04 · 从接口获取数据', link: '/cases/04-fetch' },
      { text: '05 · Markdown 编辑器', link: '/cases/05-markdown' },
      { text: '06 · 模态框与全局通知', link: '/cases/06-modal' },
      { text: '07 · 多步表单', link: '/cases/07-wizard' },
      { text: '08 · 画板与撤销重做', link: '/cases/08-canvas' },
      { text: '09 · 可编辑表格', link: '/cases/09-editable-table' },
      { text: '10 · 登录与鉴权', link: '/cases/10-auth' }
    ]
  }
]

const appendixSidebar: Item[] = [
  {
    text: '附录',
    items: [
      { text: '总览', link: '/appendix/' },
      { text: 'API 速查手册', link: '/appendix/cheatsheet' },
      { text: '常见报错与排查', link: '/appendix/errors' },
      { text: '工具链与版本清单', link: '/appendix/tools' },
      { text: '术语表', link: '/appendix/glossary' }
    ]
  }
]

export const sidebar: DefaultTheme.Sidebar = {
  '/guide/': [{ text: '课程导学', items: guide }],
  '/unit01/': unitSidebar(1),
  '/unit02/': unitSidebar(2),
  '/unit03/': unitSidebar(3),
  '/unit04/': unitSidebar(4),
  '/unit05/': unitSidebar(5),
  '/unit06/': unitSidebar(6),
  '/unit07/': unitSidebar(7),
  '/unit08/': unitSidebar(8),
  '/unit09/': unitSidebar(9),
  '/unit10/': unitSidebar(10),
  '/unit11/': unitSidebar(11),
  '/unit12/': unitSidebar(12),
  '/project/': projectSidebar,
  '/cases/': caseSidebar,
  '/appendix/': appendixSidebar
}
