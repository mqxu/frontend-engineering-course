# 工具链与版本清单

这门课会用到的工具，按六层组织。**每层的作用不同，先看层的作用，再看层里的工具。**

| 层次 | 解决的问题 | 这层的工具 |
| --- | --- | --- |
| 运行时 | 代码在哪里跑 | Node.js |
| 包管理 | 依赖怎么装、怎么复现 | pnpm、corepack |
| 构建 | 源码怎么变成能上线的产物 | Vite |
| 语言与语法 | 用什么写页面 | Vue、Vue Router、Pinia、Element Plus、axios、@vueuse/core、sass |
| 质量 | 代码写得对不对、好不好 | ESLint、Prettier、Stylelint、Vitest |
| 协作交付 | 多人怎么配合不出乱子 | Git、husky、lint-staged、commitlint |

**版本基线**（整门课统一，不要自行换版本）：

| 类别 | 版本 |
| --- | --- |
| Node | 24 LTS（Krypton），最低 20.19 |
| pnpm | 12.4.1 |
| Vite | 8.3.0 |
| Vue | 3.5.42 |
| Vue Router | 5.3.1 |
| Pinia | 4.0.3 |
| axios | 1.20.0 |
| Element Plus | 2.14.5 |
| @vueuse/core | 14.4.0 |
| sass | 1.104.1 |
| ESLint | 10.10.0 |
| Prettier | 3.9.6 |
| Stylelint | 17.15.0 |
| Vitest | 5.0.0 |
| husky | 9.1.7 |
| lint-staged | 17.5.1 |
| @commitlint/cli | 21.2.2 |

以上是**管理端**的基线。用户端（uni-app）用的是另一套锁定的版本，
两张表**不能混着看**，见本文末尾的[用户端专用的工具与版本](#用户端专用的工具与版本)。

## 第一层：运行时

运行时的作用是"提供一个能跑 JavaScript 的环境"。
以前只有浏览器能跑 JS，现在 Node.js 让 JS 能在电脑上直接跑，
构建工具、开发服务器、脚本都靠它。

| 名称 | 版本 | 作用 | 什么时候需要它 | 安装命令 |
| --- | --- | --- | --- | --- |
| Node.js | 24 LTS（Krypton） | 在电脑上运行 JavaScript，一切工具的基础 | 第一天就要装，没它什么都跑不了 | 用 fnm：`fnm install 24` |

::: tip 为什么必须用 LTS 而不是 Current
Node 有两个发布线：

- **LTS（长期支持）**：稳定、维护周期长、生态适配好。生产项目用它。
- **Current（最新）**：版本号更大，但可能有未修复的问题，很多库还没适配。

本课程统一用 24 LTS。**看到别人的版本号更大不要跟着升** ——
教学环境稳定比"用最新"重要得多。
:::

## 第二层：包管理

包管理解决"依赖怎么装、怎么保证别人装到一样的版本"。
pnpm 用硬链接共享依赖，装得快、占空间少，而且默认更严格（能减少幽灵依赖）。

| 名称 | 版本 | 作用 | 什么时候需要它 | 安装命令 |
| --- | --- | --- | --- | --- |
| pnpm | 12.4.1 | 安装与管理项目依赖 | 从单元 2 起天天用 | `corepack enable pnpm` |
| corepack | Node 自带 | 启用/切换包管理器版本 | 不想全局装 pnpm 时用它 | 随 Node 一起装好 |

常用命令：

```bash
pnpm install              # 按 package.json 与锁文件安装
pnpm add axios            # 装到 dependencies（运行时要用的）
pnpm add -D vitest        # 装到 devDependencies（只在开发时用的）
pnpm remove lodash        # 卸载
pnpm why vue              # 查某个包为什么被装上、谁依赖了它
pnpm list                 # 看当前装了哪些包
```

::: warning 锁文件必须提交
`pnpm-lock.yaml` 记录了每个依赖的确切版本。
**它要提交到 Git**，别人 `pnpm install` 才能装到完全一样的版本。

删掉锁文件能让"版本冲突"暂时不报错，但下次别人装出来的版本可能不一样 ——
**这是在掩盖问题，不是解决问题。**
:::

## 第三层：构建

构建工具负责把源码（`.vue`、`.scss`、新语法）转成浏览器能直接跑的产物，
并且做优化（压缩、拆分、加缓存指纹）。Vite 用原生 ES 模块提供极快的开发启动，
生产构建则用底层打包能力生成产物。

| 名称 | 版本 | 作用 | 什么时候需要它 | 安装命令 |
| --- | --- | --- | --- | --- |
| Vite | 8.3.0 | 开发服务器 + 生产构建 | 项目初始化的同时就装好 | `pnpm add -D vite` |

三条命令的关系：

```bash
pnpm dev      # 启动开发服务器，带热更新，日常开发一直开着
pnpm build    # 打包出 dist/，交付前跑
pnpm preview  # 本地预览 dist/，验证构建产物
```

::: warning `dev` 没问题不等于构建没问题
大小写、环境变量、资源路径这些问题，`dev` 模式下往往看不出来，
**必须跑 `build && preview` 才能暴露**。
交付前这一步不能省。
:::

## 第四层：语言与语法

这一层是"你真正写业务代码用到的东西"。

| 名称 | 版本 | 作用 | 什么时候需要它 | 安装命令 |
| --- | --- | --- | --- | --- |
| Vue | 3.5.42 | 前端框架，写页面的核心 | 从单元 4 起全程使用 | `pnpm add vue` |
| Vue Router | 5.3.1 | 管理页面之间的跳转与地址 | 有多页面时（单元 9） | `pnpm add vue-router` |
| Pinia | 4.0.3 | 全局状态管理 | 状态要跨页面共享时（单元 10） | `pnpm add pinia` |
| Element Plus | 2.14.5 | UI 组件库，现成的表格/表单/弹窗 | 要快速做出规范界面时（单元 11） | `pnpm add element-plus` |
| axios | 1.20.0 | 发 HTTP 请求 | 前后端联调时（单元 10） | `pnpm add axios` |
| @vueuse/core | 14.4.0 | 现成的组合式函数集 | 需要常见的响应式工具（防抖、可见性等） | `pnpm add @vueuse/core` |
| sass | 1.104.1 | CSS 预处理器，支持嵌套、变量、混入 | 样式复杂、要复用变量时（单元 11） | `pnpm add -D sass` |

::: tip axios 与 @vueuse/core 是运行时依赖还是开发依赖
判断标准只有一条：**打包之后运行时代码还需要它吗？**

- `axios` 被业务代码 `import`，会被打进产物 → `dependencies`。
- `@vueuse/core` 也是 → `dependencies`。
- `sass` 只在构建时把 `.scss` 编译成 CSS，产物里不需要它 → `devDependencies`。

容易判断错的是 `@vueuse/core` —— 它虽然是"工具集"，
但它的代码会进最终产物。
:::

## 第五层：质量

质量层工具**不参与业务逻辑**，它们负责在你写错的时候提醒你。
**它们的报错不是麻烦，是工具在替你干活。**

| 名称 | 版本 | 作用 | 什么时候需要它 | 安装命令 |
| --- | --- | --- | --- | --- |
| ESLint | 10.10.0 | 检查 JS / Vue 代码里的问题 | 项目一建立就配（单元 3） | `pnpm add -D eslint` |
| Prettier | 3.9.6 | 统一代码格式 | 同上 | `pnpm add -D prettier` |
| Stylelint | 17.15.0 | 检查 CSS / SCSS 写法 | 样式变多之后 | `pnpm add -D stylelint` |
| Vitest | 5.0.0 | 单元测试框架 | 需要验证逻辑正确性时（单元 12） | `pnpm add -D vitest` |

| 工具 | 负责什么 | 不负责什么 |
| --- | --- | --- |
| ESLint | 代码**对不对**（未使用变量、潜在 bug、规范） | 不负责排版 |
| Prettier | 代码**长什么样**（换行、引号、缩进） | 不负责逻辑问题 |
| Stylelint | 样式表的写法与规范 | 不检查 JS |

::: warning 别让 ESLint 和 Prettier 打架
两个工具都能管格式时，会出现"ESLint 要求这样、Prettier 要求那样"的循环。
解决办法：**用 `eslint-config-prettier` 关掉 ESLint 里和 Prettier 冲突的规则**，
让 ESLint 只管逻辑、Prettier 只管格式。配置方法见[单元 3.2](/unit03/02-eslint-prettier)。
:::

## 第六层：协作交付

这一层保证"多人写、多台机器"时不出乱子。

| 名称 | 版本 | 作用 | 什么时候需要它 | 安装命令 |
| --- | --- | --- | --- | --- |
| Git | —— | 版本控制，记录每次改动 | 第一次写代码就该用 | 系统安装包或 `brew install git` |
| husky | 9.1.7 | 在 Git 操作前后跑脚本（钩子） | 想在提交前自动检查时（单元 3） | `pnpm add -D husky` |
| lint-staged | 17.5.1 | 只检查本次改动的文件 | 配合 husky 用，避免全量检查太慢 | `pnpm add -D lint-staged` |
| @commitlint/cli | 21.2.2 | 校验提交信息格式 | 团队要统一提交规范时（单元 3） | `pnpm add -D @commitlint/cli` |

一次 `git commit` 会经历这些检查：

```text
git commit
  └─ husky 触发 pre-commit 钩子
       └─ lint-staged 只对本次改动的文件跑 ESLint / Prettier
            ├─ 有问题 → 阻止提交，先修
            └─ 没问题 → 继续
  └─ husky 触发 commit-msg 钩子
       └─ commitlint 检查提交信息是否符合规范（如 feat: 新增活动列表）
```

::: tip 钩子的意义：把检查放在提交前而不是事后
如果没有钩子，问题会在"别人拉代码跑不起来"的时候才暴露，
那时候已经很难定位是谁、哪次改动引入的。

**在提交前挡住，修复成本最低。**
:::

## 版本选择原则

### 为什么教学统一用稳定版

1. **可复现**：所有同学的版本一致，遇到问题时老师能直接复现，
   不会出现"我这能跑你那不能跑"的情况。
2. **文档与生态对得上**：稳定版的文档最全，社区里的答案也最多。
3. **减少无关干扰**：新版本的兼容问题会把你的注意力从"学知识"引到"修环境"上，
   这不是这门课的重点。

### 为什么不要用 Current

- **Current 线可能包含未稳定特性**，遇到问题时你不知道是自己的错还是库的 bug。
- **很多依赖还没适配新版本**，安装时会出现一堆 peer dependency 警告。
- **升上去容易，降回来麻烦** —— 一旦某个包要求新版本，整棵依赖树都可能被牵动。

### 什么时候才升级

- **安全漏洞修复**：有已知漏洞的版本必须升。
- **需要某个新特性**：确认项目真的用得上，而不是"看到就升"。
- **当前版本不再维护**：长期不升级会积累成大问题。

升级的正确姿势：**一次只升一个包，升完跑一遍 `build && preview` 和测试，
确认没问题再升下一个。** 一次升十几个包，出了问题你根本不知道是哪个引起的。

::: warning 版本号里的 `^` 是什么意思
`"vue": "^3.5.42"` 里的 `^` 表示"允许 3.x 范围内的最新版本"。
所以即使你写了 3.5.42，别人 install 时可能装到 3.6.x。

**真正锁死版本的是锁文件（`pnpm-lock.yaml`），不是 `package.json`。**
这也是为什么锁文件必须提交。
:::

## 一次性装齐（新建项目参考）

```bash [新建项目后的依赖安装]
# 运行时依赖
pnpm add vue vue-router pinia axios element-plus @vueuse/core

# 开发依赖
pnpm add -D vite @vitejs/plugin-vue sass
pnpm add -D eslint prettier stylelint vitest
pnpm add -D husky lint-staged @commitlint/cli

# 用脚手架创建项目时，Router / Pinia / ESLint / Vitest 可以勾选自动装
pnpm create vue@latest
```

::: tip 用脚手架，不要手动拼
`create-vue` 会根据你的勾选生成配套的配置，
包括 Router、Pinia、ESLint、Prettier、Vitest。
**手动拼容易漏配置，出了问题很难查。** 见[单元 11 的工程初始化](/unit11/02-scaffold)。
:::

## 用户端专用的工具与版本

用户端（[uni-app 实战](/mobile/)）是**另一个工程**，用的是另一套依赖。
两个工程各自独立安装，互不影响。

| 名称 | 版本 | 作用 | 什么时候需要它 | 安装命令 |
| --- | --- | --- | --- | --- |
| uni-app 编译器 | `3.0.0-5020420260813003` | 把 `.vue` 编译成各平台产物 | 建工程时随模板装好 | 由模板提供，不单独装 |
| `@dcloudio/uni-app` | 同编译器版本 | 提供页面生命周期钩子（`onLoad`、`onShow`、`onPullDownRefresh` 等） | 写页面时从它导入钩子 | 由模板提供 |
| `@dcloudio/vite-plugin-uni` | 同编译器版本 | Vite 的 uni-app 插件，串起编译流程 | 写在 `vite.config.js` 里 | 由模板提供 |
| Vite | 5.2.8 | 开发服务器 + 构建（**模板锁定，不要升到 8**） | 建工程时随模板装好 | 由模板提供 |
| Vue | 3.4.21 | 前端框架（**模板锁定，不要升到 3.5**） | 同上 | 由模板提供 |
| Wot UI（`@wot-ui/ui`） | 2.3.2 | 手机端 UI 组件库，通过 easycom 引入 | 要快速做出规范界面时 | `pnpm add @wot-ui/ui` |
| sass | 1.98 以上 | 编译 `uni.scss` 与组件库的样式 | 装 Wot UI 的同时装上 | `pnpm add -D sass` |
| 微信开发者工具 | 最新稳定版 | 打开 `dev:mp-weixin` 的产物，做真机预览与上传 | 只在做微信小程序时需要 | 官网下载，**不是 npm 包** |

::: warning 两个工程的版本不要混着看
管理端是 Vue 3.5.42 + Vite 8.3.0，用户端是 Vue 3.4.21 + Vite 5.2.8。**这不是写错了。**

uni-app 官方模板把这些版本锁死了，跨端编译器与 Vite 的版本是绑定的，
手动升级会直接编译失败。所以：**两个工程各装各的依赖，不要试图抽一个公共的 `package.json`。**

原因见[用户端总览](/mobile/)里那张“一个必须提前说清的事实”的对照表。
:::

一键装齐：

```bash [用户端工程初始化]
# 1. 用官方模板创建（模板自带 Vite / Vue / uni-app 相关依赖）
npx degit dcloudio/uni-preset-vue#vite activity-mobile

# 2. 进目录装依赖
cd activity-mobile && pnpm install

# 3. 装组件库与 sass
pnpm add @wot-ui/ui
pnpm add -D sass

# 4. 跑起来
pnpm dev:h5          # 在浏览器里跑，最快的验证方式
pnpm dev:mp-weixin   # 编译到小程序，产物在 dist/dev/mp-weixin
```

国内网络下 `degit` 可能连不上 GitHub，用 Gitee 兜底：

```bash [连不上 GitHub 时]
npx degit https://gitee.com/dcloud/uni-preset-vue/repository/archive/vite.zip activity-mobile
```

::: tip 装组件库之前先查包名
`wot-design-uni` 这个包名已经停更，新的包名是 `@wot-ui/ui`。
AI 的训练语料里旧名更多，照着 AI 给的命令装会装到一个 1.x 的旧版本。
核实命令见[用户端 · AI 协作](/mobile/10-ai-collaboration)。
:::

---

上一节：[常见报错与排查](/appendix/errors) ·
下一节：[术语表](/appendix/glossary)
