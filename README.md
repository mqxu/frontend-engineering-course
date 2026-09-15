# 前端工程化开发 · 教程

《前端工程化开发》课程的配套教程。48 学时，12 周，12 个单元，共 152 篇文档。
技术主线是 Vue 3，项目主线是“校园活动服务平台”，从工程地基写到项目上线 ——
管理端是 Vue 3 + Vite 的 Web 后台，用户端是 uni-app 的 H5 / 微信小程序。

在线地址：<https://mqxu.github.io/frontend-engineering-course/>

## 本地运行

```bash
npm install
npm run dev
```

开发服务器默认在 `http://localhost:5173/frontend-engineering-course/`。路径里的
`/frontend-engineering-course/` 对应 `config.mts` 中的 `base`，不能省略。

| 命令 | 作用 |
| --- | --- |
| `npm run dev` | 启动开发服务器 |
| `npm run build` | 打包到 `docs/.vitepress/dist/` |
| `npm run preview` | 本地预览打包结果 |

Node 版本要求 20.19 以上，推荐 24 LTS。

## 目录结构

```
.
├── docs/
│   ├── .vitepress/
│   │   ├── config.mts          站点配置，含导航、搜索、base、markdown 设置
│   │   ├── sidebar.mts         侧边栏配置，改导航只改这一个文件
│   │   └── theme/              主题入口、样式与自定义组件
│   │       └── components/
│   │           ├── UnitMeta.vue    单元导学卡
│   │           ├── Demo.vue        可运行示例容器
│   │           └── demos/          示例组件，文件名即组件名
│   ├── public/
│   │   ├── logo.svg
│   │   └── download/           离线版 HTML，首页下载入口指向这里
│   ├── index.md                首页
│   ├── guide/                  课程导学（6 篇，含 AI 编程导论）
│   ├── unit01/ ... unit12/     12 个单元（共 101 篇，每单元含一节 AI 协作）
│   ├── project/                综合项目规格与参考实现，两端共 16 篇
│   ├── mobile/                 用户端专栏（11 篇，uni-app 跨端）
│   ├── cases/                  案例库（11 篇）
│   └── appendix/               附录（6 篇）
├── tools/
│   ├── check.py                内容静态校验，查语法、排版与内部链接
│   ├── fix-wording.py          批量替换行业空词
│   └── build-html.py           Markdown 转单文件 HTML
├── deploy.sh                   构建并推送到 gh-pages 分支
├── WRITING.md                  内容写作规范
└── package.json
```

## 内容组织

| 模块 | 单元 | 主题 |
| --- | --- | --- |
| 模块一 · 工程化认知与工具链 | 1 - 3 | 工程化认知与开发环境、Node 生态与构建工具、工程规范与 Git 协作 |
| 模块二 · Vue 3 核心基础 | 4 - 6 | 模板语法与响应式基础、计算属性与渲染控制、用户交互与表单绑定 |
| 模块三 · 组件化开发 | 7 - 8 | 组件基础与父子通信、组件进阶与逻辑复用 |
| 模块四 · 应用架构 | 9 - 10 | 路由与登录鉴权、Pinia 与数据请求层 |
| 模块五 · 综合项目实战 | 11 - 12 | 项目启动与核心业务、联调优化部署与答辩 |

综合项目的载体是校园活动服务平台的管理端，业务主线为活动发布、报名审核、场次安排，
涉及活动组织者与审核员两个角色，划分为登录鉴权、活动管理、报名审核、场次与场地、
数据看板五个模块。`docs/project/` 下是这个项目的需求规格、业务规则、接口约定，
以及五个模块的参考实现。

项目还有第二个端。学生不会为了报名去开电脑，所以另有一个用手机报名的用户端，
用 uni-app 写，一套代码编译到 H5 与微信小程序，5 个页面，和管理端共用一套后端接口。
用户端**不占用 12 周的课时**，是管理端跑通之后的延伸内容，单独放在 `docs/mobile/`，
共 11 篇，从“为什么是 uni-app”讲到打包发布。它的规格写在 `docs/project/mobile.md`，
三个模块的参考实现在 `docs/project/impl-mobile-*.md`。

每个单元的结构固定为：单元导学、正文若干节、课后练习。正文各节依次讲具体场景、
原理与写法、小结、常见坑，练习只给思路和验收标准，不给完整代码。
用户端专栏不按单元编号，每篇单独成文，篇末用“上一节 / 下一节”串起来。

## AI 协作主线

教程里有一条并行的 AI 协作主线，不额外占课时。内容分布在四处：

| 位置 | 内容 |
| --- | --- |
| `docs/guide/ai-coding.md` | AI 编程导论：工具现状、风险数据、本课程的三条约定 |
| `docs/unitNN/ai-collaboration.md` | 12 个单元各一节：哪些活能交给 AI、提示词怎么写、AI 容易错什么、怎么验收 |
| `docs/project/ai-collaboration.md` | 项目级规范：AGENTS.md 模板、从规格到实现的流程、AI 参与声明、合并前评审清单 |
| `docs/appendix/ai-tools.md` | 工具速查、提示词句式库、AI 代码审查清单、版本核实命令 |

正文里引用的数据以 `docs/guide/ai-coding.md` 为准，新增内容不要从别处引入数字。
AI 协作节的写法见 `WRITING.md` 的“AI 协作小节的固定结构”一节。

## 编写内容

写作规范见 `WRITING.md`，改内容前先读一遍。核心要求是中文语境用全角标点、
中西文之间加空格、不使用直角引号、代码块标注语言并尽量标出文件名。

新增一篇文档的流程：

1. 在对应目录新建 `.md`，文件名用 kebab-case。
2. 在 `docs/.vitepress/sidebar.mts` 的对应条目里加上链接（单元、`projectSidebar` 或 `mobileSidebar`）。
3. 小节末尾的“上一节 / 下一节”指向真实存在的文件。
4. 跑 `python3 tools/check.py` 到零问题。
5. 跑 `npm run build`，确认没有渲染错误。

`tools/check.py` 只做静态检查，覆盖代码块围栏配对、容器标记配对、自定义组件标签
闭合、中文排版规则和内部链接。它查不出模板层面的问题，所以第 5 步不能省。

```bash
python3 tools/check.py              # 语法与排版
python3 tools/check.py --links      # 额外检查内部链接
python3 tools/check.py --all        # 输出全部问题，默认每类只显示 12 条
python3 tools/check.py --only=排版  # 只看某一类
```

## 离线版

首页提供整本教程的单文件 HTML 下载，双击就能打开，不需要联网。文件由
`tools/build-html.py` 生成：

```bash
python3 tools/build-html.py -o "docs/public/download/前端工程化开发-完整教程.html"
```

脚本依赖 `markdown-it-py`，另需 `mdit-py-plugins` 与 `linkify-it-py`：

```bash
pip install markdown-it-py mdit-py-plugins linkify-it-py
```

正文改动后要重新生成一次，再跑 `npm run build`，否则站点上的离线版是旧的。

## 发布

```bash
./deploy.sh
```

脚本本地构建，把 `docs/.vitepress/dist` 的内容推到 `gh-pages` 分支，GitHub Pages
从该分支发布，通常一分钟左右生效。`main` 分支存源码，推送它不会触发发布，所以
内容改动需要分两步：

```bash
git add -A && git commit -m "docs: 更新单元 5" && git push
./deploy.sh
```

站点发布在仓库子路径下，`config.mts` 里的 `base` 与仓库名一致，改了仓库名要同步改
`base`，否则页面能打开但样式和跳转失效。绑定自定义域名时用环境变量覆盖即可：

```bash
DOCS_BASE=/ npm run build
```

`.github/workflows/deploy.yml` 里留了一份 GitHub Actions 的构建流程，只支持手动
触发，默认不参与发布。

## 提交规范

提交信息用 Conventional Commits 格式：

```
<type>(<scope>): <subject>
```

常用的 type 有 `feat`、`fix`、`docs`、`style`、`refactor`、`chore`，scope 可以省略。

## 注意事项

- 行内代码里的 `{{ }}` 由 `config.mts` 中的 `v-pre` 规则处理，不会被 Vue 当作插值。
  裸写在正文里的 `{{ }}` 仍会执行，需要避免。
- 给链接加 `{}` 属性（例如 `{download}`）之后，VitePress 不再补 `base` 前缀，
  这类链接要写成相对路径。
- 代码块的语言标记要选 Shiki 认识的语言，`gitignore` 不在支持列表里，写 `.gitignore`
  文件内容时用 `bash`。
- 用户端专栏里引用组件库时，代码示例的导入路径写 `@wot-ui/ui`（npm 安装），
  不要抄官方文档里的 `@/uni_modules/wot-ui`（那是 uni_modules 安装的路径）。
- 两个端的版本基线不同，正文里给出的版本号要标清是哪一个端的，不能混用。

## 版本基线

教程正文里的版本号按下面这套写，不要凭记忆改：

| 类别 | 版本 |
| --- | --- |
| Node | 24 LTS（Krypton），最低 20.19 |
| 包管理 | pnpm 12.4.1 |
| 构建 | Vite 8.3.0 |
| 框架 | Vue 3.5.42 |
| 路由 | Vue Router 5.3.1 |
| 状态 | Pinia 4.0.3 |
| 请求 | axios 1.20.0 |
| UI 库 | Element Plus 2.14.5 |
| 规范 | ESLint 10.10.0 / Prettier 3.9.6 / Stylelint 17.15.0 |
| 钩子 | husky 9.1.7 / lint-staged 17.5.1 / @commitlint/cli 21.2.2 |
| 测试 | Vitest 5.0.0 |
| 工具集 | @vueuse/core 14.4.0 |
| 样式 | sass 1.104.1 |

npm 包的版本用 registry 查：

```bash
curl -s https://registry.npmjs.org/vue/latest | head -c 200
curl -s https://registry.npmjs.org/@vue%2Fuse%2Fcore/latest | head -c 200
```

用户端用的是另一套被官方模板锁定的版本，**两张表不能混着看**：

| 类别 | 版本 |
| --- | --- |
| 跨端框架 | uni-app（经典版） |
| uni-app 编译器 | 3.0.0-5020420260813003 |
| 构建 | Vite 5.2.8（模板锁定，不要升到 8） |
| 框架 | Vue 3.4.21（模板锁定，不要升到 3.5） |
| 路由 | 不用 vue-router，用 `pages.json` + `uni.navigateTo` 等 API |
| 状态 | 不引入 Pinia，用 `uni.storage` + 工具函数 |
| UI 库 | Wot UI，npm 包名是 `@wot-ui/ui` 2.3.2 |
| 请求 | `uni.request` 自封装 |

写这两张表之前要核实的地方，各给一条命令：

```bash
# 管理端
curl -s https://registry.npmjs.org/vue/latest | head -c 200

# 用户端组件库：新包名是 @wot-ui/ui，旧的 wot-design-uni 已停更在 1.14.0
curl -s https://registry.npmjs.org/@wot-ui%2Fui/latest | head -c 200
curl -s https://registry.npmjs.org/wot-design-uni/latest | head -c 200
```

站点自身用 VitePress 1.6.4。VuePress 2 至今仍是 RC 状态，npm 上 `vuepress@latest`
还指向 1.9.x，教材不适合建在 RC 版本上。

## 许可证

课程内部教学材料。
