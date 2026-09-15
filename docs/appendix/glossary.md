# 术语表

收录 80 条以上容易混淆或经常出现的术语。**按四栏写：术语（中英）、一句话解释、常见误解、在本课程哪一节出现。**

读英文文档被术语卡住时，先在这里找一遍，再回去读原文。

## 一、工程化与工具链

| 术语（中英） | 一句话解释 | 常见误解 | 出现位置 |
| --- | --- | --- | --- |
| 工程化 Frontend Engineering | 把"一个人写页面"变成"一套可维护、可协作、可交付的流程" | 以为用了框架就是工程化 | [1.1](/unit01/01-why-engineering) |
| 构建工具 Build Tool | 把源码加工成浏览器能直接运行的产物的工具 | 以为构建工具就是"打包器" | [2.4](/unit02/04-vite) |
| 打包 Bundling | 把分散的模块合并成少量文件，减少请求数 | **以为打包就是压缩**。压缩只是打包过程中的一步，打包的核心是"合并模块、处理依赖关系" | [2.4](/unit02/04-vite) |
| 编译 Compile | 把一种语言写成另一种语言的等价形式 | 以为前端没有编译。把 `.vue` 转成 JS 就是编译 | [2.4](/unit02/04-vite) |
| 转译 Transpile | 把同一门语言的高版本语法转成低版本语法 | **和编译混为一谈**。转译是"同语言换版本"，编译是"换语言" | [2.1](/unit02/01-node) |
| 产物 Build Output | `build` 之后生成的、能直接部署的文件 | 以为 `dist/` 可以手改 | [2.4](/unit02/04-vite) |
| 热更新 HMR | 改代码后只替换改动的那部分，页面不整页刷新且保留状态 | 以为热更新就是"自动刷新页面"。整页刷新会丢表单内容，热更新不会 | [2.4](/unit02/04-vite) |
| 预构建 Pre-bundling | Vite 启动时先把第三方依赖预处理成 ESM，加快开发响应 | 以为预构建是"生产构建的预演"。它只服务于开发服务器 | [2.4](/unit02/04-vite) |
| 脚手架 Scaffold | 一条命令生成项目骨架的工具 | 以为脚手架生成的东西不能改 | [11.2](/unit11/02-scaffold) |
| 环境变量 Environment Variable | 同一份代码在不同环境读到的不同配置值 | 以为随便起个名字就能读到。只有 `VITE_` 开头的才会暴露给浏览器 | [2.5](/unit02/05-env-config) |

## 二、模块与依赖

| 术语（中英） | 一句话解释 | 常见误解 | 出现位置 |
| --- | --- | --- | --- |
| 模块化 Modularity | 把代码拆成职责单一、可单独引用的文件 | 以为"文件多"就是模块化好。关键是职责边界清晰 | [3.3](/unit03/03-modules-structure) |
| ESM | JavaScript 官方的模块标准，用 `import` / `export` | 以为所有浏览器的 `import` 行为都一样（实际由构建工具处理） | [2.3](/unit02/03-package-json) |
| CJS | Node 早期的模块标准，用 `require` / `module.exports` | 以为 CJS 已经不能用了。很多 Node 工具链仍在使用 | [2.3](/unit02/03-package-json) |
| 依赖 Dependency | 项目运行或构建时需要的外部代码包 | 以为依赖越多越好，"能用库就不自己写" | [2.2](/unit02/02-package-manager) |
| 开发依赖 devDependency | 只在开发阶段用的包，不进最终产物 | **以为 `-D` 装的是"不重要的包"**。区分标准是"运行时代码需不需要它" | [2.3](/unit02/03-package-json) |
| 锁文件 Lockfile | 记录每个依赖确切版本的文件，保证任何人装到一样的版本 | 以为锁文件冲突时可以删掉重来。删掉等于放弃版本可复现性 | [2.2](/unit02/02-package-manager) |
| 语义化版本 SemVer | 用主版本.次版本.修订号描述版本，并约定升级含义 | 以为 `^3.5.42` 会锁死在 3.5.42。它允许同主版本内升级 | [2.2](/unit02/02-package-manager) |
| 幽灵依赖 Phantom Dependency | 代码里用了一个自己没声明、靠别人的依赖被"提上来"的包 | 以为"能 import 就说明能一直用"。换个包管理器立刻报错 | [2.2](/unit02/02-package-manager) |
| 扁平化 node_modules | 把依赖尽量提升到顶层，减少重复安装 | 以为它只有好处。它也是幽灵依赖的根源 | [2.2](/unit02/02-package-manager) |
| 路径别名 Path Alias | 用 `@` 之类的短名前缀代替长相对路径 | 以为配了别名就不用管大小写。别名不解决大小写问题 | [2.4](/unit02/04-vite) |

## 三、Vue 核心概念

| 术语（中英） | 一句话解释 | 常见误解 | 出现位置 |
| --- | --- | --- | --- |
| 单文件组件 SFC | 把一个组件的模板、逻辑、样式写在同一个 `.vue` 文件里 | 以为 `.vue` 是浏览器直接支持的文件格式，其实要经过构建处理 | [7.1](/unit07/01-sfc) |
| 模板编译 Template Compilation | Vite 编译期把 `<template>` 转成渲染函数 | 以为模板是运行时解析的字符串 | [4.1](/unit04/01-declarative) |
| 声明式渲染 Declarative Rendering | 描述"界面应该长什么样"，由框架负责更新 DOM | 以为声明式就不用管性能。该用 `key`、该做分割还是要做 | [4.1](/unit04/01-declarative) |
| 虚拟 DOM Virtual DOM | 用 JS 对象描述真实 DOM，对比差异后批量更新 | **以为虚拟 DOM 一定比直接操作 DOM 快**。它的价值在于"让开发者不用手动管更新" | [4.5](/unit04/05-reactivity-principle) |
| 响应式 Reactivity | 数据变化时，用到它的界面和计算自动更新 | 以为只要赋值就会自动更新。解构、丢引用都会切断响应式 | [4.4](/unit04/04-reactivity) |
| 依赖收集 Dependency Tracking | 读取响应式数据时记录"谁用了它"，变化时通知这些使用者 | 以为依赖收集发生在赋值时。它发生在**读取**时 | [4.5](/unit04/05-reactivity-principle) |
| 副作用 Side Effect | 状态变化后要做的、对外部有影响的事情 | 以为发请求、写日志都不算副作用。它们正是`watch` 的目标 | [5.2](/unit05/02-watch) |
| 计算属性 Computed | 由已有状态算出来的值，结果被缓存 | **以为 `computed` 和函数一样每次调用都执行**。依赖不变时它直接返回缓存 | [5.1](/unit05/01-computed) |
| 侦听器 Watcher | 监听状态变化后执行一段逻辑 | 以为 `watch` 能替代 `computed`。`computed` 是算值，`watch` 是做事 | [5.2](/unit05/02-watch) |
| 生命周期 Lifecycle | 组件从创建到销毁经历的一系列阶段 | 以为钩子越多越好。大多数组件只需要 `onMounted` 和 `onBeforeUnmount` | [6.5](/unit06/05-lifecycle) |
| 组合式 API | 用 `ref`、`computed`、函数组织组件逻辑的写法 | 以为组合式 API 就是"写得更高级"。它的核心价值是**逻辑可以复用** | [4.4](/unit04/04-reactivity) |
| 选项式 API | 用 `data`、`methods`、`computed` 分块组织组件逻辑 | 以为新项目不该用。老项目还在用，能看懂是基本要求 | [4.4](/unit04/04-reactivity) |
| 作用域样式 Scoped CSS | 让组件样式只作用于当前组件 | 以为加了 `scoped` 就绝不会影响外部。深度选择器和全局样式仍会穿透 | [7.1](/unit07/01-sfc) |
| 四态 Four States | 加载中、出错、空数据、有数据 —— 数据页面的四种必须状态 | 以为写完"有数据"就够了。漏掉错误态会让用户看到白屏 | [5.5](/unit05/05-four-states) |
| 内存泄漏 Memory Leak | 组件卸载后，定时器/监听器仍持有引用导致资源不释放 | 以为页面切换会自动清理一切。定时器和手动监听必须自己清 | [6.5](/unit06/05-lifecycle) |

## 四、组件通信与复用

| 术语（中英） | 一句话解释 | 常见误解 | 出现位置 |
| --- | --- | --- | --- |
| 属性 Props | 父组件传给子组件的数据，子组件只读 | **以为子组件也能直接改 `props`**。改了会报"target is readonly" | [7.2](/unit07/02-props) |
| 事件 Emits | 子组件通知父组件发生了什么事，可携带数据 | 以为 `emit` 是"改父组件的数据"。它只是通知，改不改由父组件决定 | [7.3](/unit07/03-emits) |
| 插槽 Slot | 父组件往子组件的指定位置填内容 | 以为插槽只是"传 HTML"。它让组件有了可定制的结构 | [8.1](/unit08/01-slots) |
| 作用域插槽 Scoped Slot | 子组件把数据"给回"父组件，让父组件决定怎么渲染 | 以为作用域插槽就是普通插槽加参数。它是**反向的数据传递** | [8.1](/unit08/01-slots) |
| 依赖注入 Dependency Injection | 祖先组件提供数据，任意后代组件都能直接获取 | 以为它能当全局状态用。它只在当前组件树存活期内有效 | [8.2](/unit08/02-provide-inject) |
| 组合式函数 Composable | 用函数封装可复用的有状态逻辑，名字以 `use` 开头 | 以为组合式函数就是普通工具函数。它**内部有响应式状态** | [8.4](/unit08/04-composables) |
| 自定义指令 Custom Directive | 把"操作 DOM"的逻辑封装成 `v-xxx` 指令 | 以为能自定义指令就很厉害。能用组件解决就优先用组件 | [8.5](/unit08/05-directives) |
| 传送门 Teleport | 把组件内容渲染到 DOM 树的另一个位置 | 以为 `Teleport` 会改变组件的父子关系。它只改渲染位置，不改逻辑关系 | [8.3](/unit08/03-builtin) |
| 透传属性 Fallthrough Attributes | 没被声明为 `props` 的属性会自动落到组件根元素上 | 以为所有属性都需要在 `props` 里声明 | [7.2](/unit07/02-props) |
| 递归组件 Recursive Component | 组件在自己的模板里引用自己，用来渲染树形结构 | 以为递归组件不用设结束条件。必须有终止分支，否则栈溢出 | [7.5](/unit07/05-case-tree) |

## 五、路由与应用架构

| 术语（中英） | 一句话解释 | 常见误解 | 出现位置 |
| --- | --- | --- | --- |
| 单页应用 SPA | 只加载一个 HTML，页面切换由 JS 完成，不整页刷新 | **以为单页应用"只有一个页面"**。它是有很多视图，但共用一次加载 | [9.1](/unit09/01-router-basics) |
| 路由 Routing | 地址与页面之间的映射关系 | 以为路由只用来跳转。它还承担参数解析、权限判断 | [9.1](/unit09/01-router-basics) |
| 动态路由参数 Dynamic Params | 路径里的可变部分，如 `/activity/:id` | 以为 `params` 和 `query` 可以互换。前者是路径的一部分，后者是查询串 | [9.2](/unit09/02-nested-params) |
| 嵌套路由 Nested Route | 子页面渲染在父页面的 `<RouterView />` 位置 | 以为配了 `children` 就自动生效。父组件忘了写 `<RouterView />` 就不显示 | [9.2](/unit09/02-nested-params) |
| 路由守卫 Navigation Guard | 在跳转前后执行的检查逻辑 | 以为守卫能"阻止所有非法访问"。它只挡前端，真正的权限还得后端管 | [9.3](/unit09/03-guards) |
| 状态管理 State Management | 把多个页面共享的数据集中存放和管理 | **以为所有状态都该放全局**。表单草稿、弹窗开关都不该放 | [10.1](/unit10/01-when-global) |
| 持久化 Persistence | 把状态写进 `localStorage` 等存储，刷新后能恢复 | 以为持久化就是"把整个 store 存下来"。加载态、错误信息不该存 | [10.3](/unit10/03-persist) |
| 拦截器 Interceptor | 在请求发出前或响应回来后统一执行的处理逻辑 | 以为拦截器越复杂越好。它只该做通用的事，业务逻辑放页面 | [10.4](/unit10/04-request-layer) |
| 幂等 Idempotent | 同一个请求执行多次，对服务器的影响和执行一次相同 | 以为"重复请求"都可以自动重试。创建类接口重试可能造出重复数据 | [10.5](/unit10/05-error-handling) |
| 请求竞态 Race Condition | 先发出的请求后返回，覆盖了后发出请求的结果 | 以为网络快就不会遇到。快速切页时非常容易复现 | [10.6](/unit10/06-case-fetch) |
| 请求去重 Request Deduplication | 避免同一份数据被重复请求或重复追加 | 以为"去重"是后端的事。分页追加时的重复必须前端也防一道 | [10.6](/unit10/06-case-fetch) |

## 六、网络与部署

| 术语（中英） | 一句话解释 | 常见误解 | 出现位置 |
| --- | --- | --- | --- |
| 跨域 CORS | 浏览器的同源策略限制，不同源之间请求需要服务器允许 | **以为跨域是前端 bug**。它是浏览器的安全机制，解决要靠服务端或代理 | [12.1](/unit12/01-integration) |
| 代理 Proxy | 开发服务器把请求转发给后端，绕开浏览器跨域限制 | 以为代理在生产环境也有效。它只服务于开发服务器 | [12.1](/unit12/01-integration) |
| 同源 Same Origin | 协议、域名、端口三者完全相同 | 以为同一个域名就是同源。端口不同也不算 | [12.1](/unit12/01-integration) |
| 代码分割 Code Splitting | 把产物拆成多个文件，按需加载 | 以为拆得越细越好。拆太细会增加请求数和管理成本 | [12.2](/unit12/02-build-optimize) |
| 懒加载 Lazy Loading | 用到某个模块时才去加载它 | 以为懒加载一定更快。首屏不需要的才懒加载，首屏要用的反而更慢 | [12.2](/unit12/02-build-optimize) |
| 树摇 Tree Shaking | 构建时去掉没被用到的代码 | 以为只要用了打包工具就自动生效。它依赖 ESM 的静态结构，CJS 效果差很多 | [12.2](/unit12/02-build-optimize) |
| 异步组件 Async Component | 把组件定义成"用到时才加载" | 以为异步组件适合所有组件。频繁切换的组件异步化反而会闪烁 | [12.2](/unit12/02-build-optimize) |
| 首屏 First Screen | 用户打开页面到看到主要内容的时间 | 以为首屏快慢只跟网速有关。代码体积、请求数量、渲染阻塞都影响 | [12.2](/unit12/02-build-optimize) |
| 白屏 Blank Screen | 页面加载出来却什么都没有 | 以为白屏是"网慢"。多数是 JS 报错或资源 404 | [12.3](/unit12/03-deploy) |
| CSR | 客户端渲染，页面内容由浏览器里的 JS 生成 | 以为 CSR 就是"没有 SEO"。现在的搜索引擎对 CSR 也有一定支持 | [12.2](/unit12/02-build-optimize) |
| SSR | 服务端渲染，服务器直接返回带内容的 HTML | 以为 SSR 一定比 CSR 快。它首屏更快，但服务器压力更大、开发更复杂 | [12.2](/unit12/02-build-optimize) |
| 预渲染 Prerendering | 构建时把特定页面提前生成静态 HTML | 以为预渲染能替代 SSR。它只适合内容相对固定的少数页面 | [12.2](/unit12/02-build-optimize) |
| 水合 Hydration | 服务端渲染的静态 HTML 在浏览器里"接管"为可交互应用 | 以为水合不花钱。它要重新执行一遍 JS，可能造成短暂不可交互 | [12.2](/unit12/02-build-optimize) |
| 环境配置文件 .env | 存放不同环境配置的文件 | 以为改了 `.env` 会立刻生效。开发服务器需要重启 | [2.5](/unit02/05-env-config) |

## 七、质量与协作

| 术语（中英） | 一句话解释 | 常见误解 | 出现位置 |
| --- | --- | --- | --- |
| 代码规范 Lint | 用工具检查代码里的潜在问题与风格问题 | 以为规范是"为了好看"。它拦住的是真实 bug | [3.1](/unit03/01-why-lint) |
| 提交规范 Commit Convention | 约定提交信息的格式，如 `feat: 新增活动列表` | 以为格式只是形式。它是自动生成变更日志的依据 | [3.4](/unit03/04-git-flow) |
| 代码评审 Code Review | 提交前由他人检查改动 | 以为评审是挑错。它是知识传递和质量把关 | [3.4](/unit03/04-git-flow) |
| CI 流水线 CI Pipeline | 每次提交后自动跑检查、构建、测试的流程 | 以为 CI 只在大公司用。一个小项目几百行配置就能跑起来 | [3.5](/unit03/05-ci) |
| 单元测试 Unit Test | 针对最小可测单元验证行为是否符合预期 | **以为测试是为了证明代码没错**。测试是为了在改动后快速发现"改坏了什么" | [12.1](/unit12/01-integration) |
| 快照测试 Snapshot Test | 把输出结果存成基线，之后对比是否变化 | 以为快照变了就是 bug。有时是预期内的改动，要人工确认后更新基线 | [12.1](/unit12/01-integration) |
| 声明式与命令式 | 声明式描述结果，命令式描述步骤 | 以为声明式一定更好。需要精细控制的地方仍要用命令式（如操作 DOM） | [4.1](/unit04/01-declarative) |
| 防抖 Debounce | 事件停止触发一段时间后才执行 | 以为防抖能减少"请求次数"就够了。它也可能让用户觉得"没反应" | [6.1](/unit06/01-events) |
| 事件冒泡 Event Bubbling | 事件从目标元素向上层元素传播 | 以为点了子元素父元素不会响应。默认会，需要 `.stop` 阻止 | [6.1](/unit06/01-events) |
| 上下文丢失 this 指向 | 函数被单独取出后，原来的 `this` 不再生效 | 以为箭头函数能解决所有 `this` 问题。它反而会绑定外层 `this` | [7.3](/unit07/03-emits) |

## 八、常见"看起来像"的概念对照

这几个概念对照最容易被混，单独列出来。

| 一对概念 | 差别一句话 |
| --- | --- |
| 打包 vs 压缩 | 打包是合并模块、处理依赖；压缩只是其中一步，去掉空格和缩短变量名 |
| 编译 vs 转译 | 编译是换语言（`.vue` 转 JS）；转译是同语言降版本（ES2022 转 ES2015） |
| 构建 vs 部署 | 构建是把源码变成产物；部署是把产物放到服务器上让别人能访问 |
| 开发依赖 vs 运行时依赖 | 看"打包后的运行时代码还需不需要它"，需要就是运行时依赖 |
| `ref` vs `reactive` | 都能声明响应式状态；`ref` 通用且解构安全，`reactive` 适合整块对象 |
| `computed` vs `watch` | `computed` 算出一个值并缓存；`watch` 在变化时执行一段逻辑 |
| `computed` vs 普通函数 | `computed` 依赖不变就用缓存；普通函数每次调用都重算 |
| `params` vs `query` | `params` 是路径的一部分（`/activity/12`）；`query` 是问号后面（`?page=2`） |
| `v-if` vs `v-show` | `v-if` 不生成节点；`v-show` 只切 `display`，适合频繁切换 |
| props vs provide/inject | props 是父子逐层传；provide/inject 跳过中间层，但只在子树内存活 |
| 框架 vs 工程化 | 框架解决"怎么写界面"；工程化解决"怎么让项目可维护、可协作、可交付" |
| 全局状态 vs 组件状态 | 判断依据是"被不相邻的多个页面共用吗"，不是"这个数据重不重要" |

::: tip 怎么用这张表
遇到分不清的概念，先在这张对照表里找。
**如果找不到，说明它值得补充** —— 记下来反馈给老师。

判断自己是不是真的分清了，有一个简单方法：
**能各举一个"用了 A 而不是 B"的具体场景，并且说出为什么。**
只能复述定义，说明还没分清。
:::

## 九、跨端与小程序

做[用户端](/mobile/)时会遇到这一组词。它们和后端的“多端”不是一回事，
说的是**同一份前端代码怎么变成不同平台的应用**。

| 术语（中英） | 一句话解释 | 常见误解 | 出现位置 |
| --- | --- | --- | --- |
| 跨端框架 Cross-platform Framework | 用一套代码生成多个平台应用的框架 | 以为“跨端”就是“自适应网页”。跨端产出的是真正的原生或小程序包，不是响应式布局 | [1](/mobile/01-why-uniapp) |
| uni-app | DCloud 出的跨端框架，编译到 H5、微信小程序、App 等多个平台 | 以为它是一个运行时库。它是**编译器**，产物里没有 uni-app 本身 | [1](/mobile/01-why-uniapp) |
| uni-app x | uni-app 的下一代，用 UTS 强类型语言，原生渲染 | 和经典版混为一谈。经典版用 JS/TS 走 WebView 混合渲染，生态完整；uni-app x 主攻 App 与鸿蒙，大量 JS npm 包不可用 | [1](/mobile/01-why-uniapp) |
| UTS | uni-app x 用的强类型语言，语法接近 TypeScript | 以为是 TypeScript 的别名。它是编译到 Kotlin / Swift 的独立语言 | [1](/mobile/01-why-uniapp) |
| 条件编译 Conditional Compilation | 用特殊注释包住一段代码，让它只在某个平台编译进去 | 以为它是运行时判断。它在**编译期**就把别的平台的分支删掉了 | [4](/mobile/04-layout-style) |
| rpx | uni-app 的响应式单位，**750rpx 永远等于屏幕宽度** | 以为 rpx 是 px 的二分之一。它按屏幕宽度等比换算，与设备像素无关 | [4](/mobile/04-layout-style) |
| easycom | uni-app 的组件自动引入机制，按正则匹配组件路径 | 以为改完配置立刻生效。`pages.json` 的改动常常要重新编译 | [5](/mobile/05-components) |
| 页面栈 Page Stack | 当前打开的页面组成的栈，小程序最多 10 层 | 以为可以无限 `navigateTo`。超过 10 层会失败，要用 `redirectTo` 或 `reLaunch` | [3](/mobile/03-pages-router) |
| tabBar | 底部导航栏，只能配 2 到 5 项 | 以为 tabBar 页面可以像普通页面一样 `navigateTo` 过去。它**只能**用 `switchTab`，而且不能带参数 | [3](/mobile/03-pages-router) |
| 小程序 AppID | 小程序的身份标识，写在 `manifest.json` 里 | 以为前端能拿 AppSecret。**AppSecret 只能放在后端**，泄露等于把整个小程序交出去 | [6](/mobile/06-request-auth) |
| code2session | 后端拿 `code` 换 `openid` 的接口 | 以为前端可以直接调。它需要 AppSecret，**必须由后端发起** | [6](/mobile/06-request-auth) |
| Wot UI | 手机端 UI 组件库，npm 包名是 `@wot-ui/ui` | 沿用旧包名 `wot-design-uni`。旧包已停更在 1.x | [5](/mobile/05-components) |

## 十、AI 协作

这一节的术语在 [AI 编程导论](/guide/ai-coding) 之后出现得越来越频繁，不需要会实现，但要知道各自管什么。

| 术语（中英） | 一句话解释 | 常见误解 | 出现位置 |
| --- | --- | --- | --- |
| 编码代理 Coding Agent | 能读文件、改文件、跑命令的 AI 工具，不只是补全 | 以为它和代码补全是同一类。补全帮你打字，代理替你把事做完 | [导论](/guide/ai-coding) |
| 上下文工程 Context Engineering | 决定往对话里放哪些信息，让产出更准 | 以为提示词越长越好。无关信息会稀释重点 | [4](/unit04/ai-collaboration) |
| AGENTS.md | 放在仓库根目录、写明项目约定的 Markdown 文件，供 AI 工具读取 | 以为它是某个工具的专有配置。它是跨工具的通用格式 | [3](/unit03/ai-collaboration) |
| 渐进式披露 Progressive Disclosure | 主文件只放导航性信息，细节按需展开 | 以为把全部内容塞进一个文件更好 | [3](/unit03/ai-collaboration) |
| 规格驱动开发 Spec-Driven Development | 先写清要建什么、为什么建，再让 AI 按规格实现 | 以为要多写一堆文档。需求、规则、接口这几份本身就是规格 | [11](/unit11/ai-collaboration) |
| MCP | 让 AI 连接数据库、接口、内部系统等外部服务的一套协议 | 以为要自己实现。知道它是什么、什么时候需要就够 | [导论](/guide/ai-coding) |
| Agent Skills | 把一套流程与参考资料打包成可复用的能力，AI 按需加载 | 以为要写代码。它就是一个目录加一份 Markdown | [导论](/guide/ai-coding) |
| 幻觉依赖 Hallucinated Dependency | AI 编出来的、仓库里不存在的包名或坐标 | 以为名字符合命名规范就一定是真的 | [2](/unit02/ai-collaboration) |
| 提示注入 Prompt Injection | 把恶意指令藏在 AI 会读到的地方，让它执行不该执行的操作 | 以为只和安全领域有关。2026 年 3 月已出现针对编码代理的真实攻击 | [导论](/guide/ai-coding) |
| 验证缺口 Verification Gap | 多数人知道 AI 代码不能全信，但不到一半的人每次提交前真的检查 | 以为看着跑通了就等于验证过 | [导论](/guide/ai-coding) |
| 代码异味 Code Smell | 不立即报错、但让代码越来越难维护的写法 | 以为只有报错的问题才算问题。有研究显示 AI 代码九成以上的问题属于这一类 | [12](/unit12/ai-collaboration) |

### 两对容易混的

| 一对概念 | 差别一句话 |
| --- | --- |
| AI 补全 vs AI 代理 | 补全只在光标处给建议；代理会读文件、改多个文件、跑命令，自己完成任务 |
| AGENTS.md vs CLAUDE.md | AGENTS.md 是跨工具通用的那个；CLAUDE.md 是 Claude Code 的原生格式，支持的配置项更多 |

---

上一节：[工具链与版本清单](/appendix/tools) ·
下一节：[AI 编程工具速查](/appendix/ai-tools)
