# 写作规范（本课程教程）

这份文档是《前端工程化开发》教程内容的统一写作规范。**写任何一节之前先读完它。**

## 一、这是什么

一套 VitePress 教程站点，配套《前端工程化开发》48 学时课程（12 周 × 4 学时，12 个单元）。

- 读者：职业本科软件工程技术专业大二 / 大三学生，有 HTML、CSS、JavaScript 基础。
- 定位：**可以独立自学的实操教程**，同时作为课堂实训的操作手册。
- 目标：读者读完能动手做出来，而不是"看懂了"。

## 二、先读样板

动笔前必须读这三个文件，**风格、结构、详略程度全部照此**：

| 文件 | 学什么 |
| --- | --- |
| `docs/unit01/index.md` | 单元导学的写法（UnitMeta 组件、知识地图、四学时分配、产出要求） |
| `docs/unit01/02-modern-project.md` | 知识点小节的写法（问题引入 → 原理 → 代码 → 坑 → 练习） |
| `docs/unit01/practice.md` | 单元练习的写法（必做 / 选做分开，验收标准用表格） |

单元里的案例页可参考 `docs/unit01/01-why-engineering.md` 的“反例 + 表格对比”手法。

## 三、每节的固定结构

知识点小节按这个骨架写，不要跳步：

```
# 编号 标题

## 一个具体的场景 / 问题        ← 用一个真实场景引入，不要直接讲概念
## 原理与写法                   ← 分 2-4 个小标题讲清，配可运行的代码
## 小结                         ← 3-6 条要点，用列表
## 常见坑                       ← 用 ::: details 折叠，每条"现象 → 原因 → 怎么处理"
## 课后练习                     ← 用 ::: details 折叠，给思路不给完整答案

---

上一节：[xxx](链接) · 下一节：[xxx](链接)
```

**篇幅**：每节 3500 - 6000 字（含代码）。案例页可以更长。

## 四、语言规范（硬要求）

1. **中文语境用全角标点**：，。；：！？（）“ ”
2. **西文语境用半角标点**：, . ; : ! ? ( ) " "
3. **中西文之间加空格**：写“Vue 3 框架”“Node 版本是 24”，不写“Vue3框架”“Node版本是24”
4. **不用直角引号**（U+300C、U+300D、U+300E、U+300F 四个字符），统一用全角引号 “ ”；西文用半角 " "
5. **不用行业黑话**：禁止“闭环”“落地”“赋能”“对齐”“抓手”“打通”“颗粒度”。
   用直白表达：“完成”“实现”“实际应用”“对应”“统一”
6. **不用营销腔**：不写“极致”“赋能”“一站式”“颠覆”“重磅”
7. **人称**：直接对读者说话用“你”，讲团队时用“我们”，不要用“笔者”“本人”
8. **结论要具体**：不写“性能更好”，写“首屏从 2.1 秒降到 0.8 秒”

## 五、代码示例规范

**代码块必须标语言，重要文件要标文件名**：

````md
```js [src/main.js]
import { createApp } from 'vue'
```
````

其他要求：

- 代码要能跑。不确定的 API 先查官方文档，不要凭记忆写。
- 错误示范用 `// ✗` 标注，正确示范用 `// ✓` 标注，并且成对出现讲清差别。
- 长代码给出关键部分，不重要的一律省略，用注释标 `// 省略`。
- 代码里的中文注释要符合规范（全角标点、中西文空格）。

## 六、VitePress 语法

**自定义容器**（必须用这些，不要自造）：

```md
::: tip 提示
:::

::: warning 常见坑
:::

::: danger 别这么做
:::

::: details 展开看更多
:::
```

**可运行示例**（只在关键处用，每个单元 1-3 个）：

```md
<Demo title="示例标题" desc="一句话说明">
  <DemoXxx />

  <template #code>

```vue
（这里是源码）
```

  </template>
</Demo>
```

可运行的示例组件放在 `docs/.vitepress/theme/components/demos/`，文件名即组件名
（`DemoCounter.vue` 在 md 里写 `<DemoCounter />`）。**代理不要新建 demo 组件文件**，
如需可运行示例，用文字说明并链接到已有示例。

**单元导学页开头**必须用 UnitMeta 组件：

```md
<UnitMeta
  unit="单元 4"
  title="模板语法与响应式基础"
  module="模块二 · Vue 3 核心基础"
  hours="4 学时"
  week="第 4 周"
  :goals="['目标一', '目标二']"
  :outcomes="['产出物一', '产出物二']"
/>
```

**两个踩过的坑**（2026-09 部署到 GitHub Pages 时发现，已在 `config.mts` 里处理）：

1. **行内代码里的 `{{ }}` 会被当成 Vue 插值真的去执行。**
   VitePress 把 Markdown 当 Vue 模板编译。围栏代码块本来安全，但行内代码不是：
   写 `` `{{ doneCount() }}` `` 会让构建直接失败并报
   `TypeError: _ctx.doneCount is not a function`；写 `` `{{ }}` ``（空插值）
   会报 `Cannot read properties of undefined`。**这类错误只在 `vitepress build`
   时才暴露，`dev` 下看不出来**，写合规就交付的话线上页面是坏的。
   现在 `config.mts` 给所有行内 `<code>` 加了 `v-pre`，正文里可以照常写。
   边界要注意：**受保护的只有行内代码和围栏代码块**，裸写在正文里的 `{{ }}` 仍会被执行。

2. **带 `{}` 属性的链接不会被补上 base 前缀。**
   `[下载](/download/x.html){download}` 会原样输出 `href="/download/x.html"`，
   少了 `/frontend-engineering-course/` 这一段，线上直接 404。
   要么去掉属性写纯绝对链接，要么写成相对路径（浏览器按当前页面解析）。
   首页那个离线版下载链接就是因此写成 `./download/…` 的，别改成绝对路径。

## 七、项目背景（全课程贯穿）

综合项目是 **校园活动服务平台 · 管理端**。教程里的业务例子尽量用它，形成一条主线。

| 维度 | 内容 |
| --- | --- |
| 主线 | 活动发布 → 报名审核 → 场次安排 |
| 角色 | 活动组织者、审核员 |
| 模块 | 登录鉴权、活动管理、报名审核、场次与场地、数据看板 |
| 活动状态 | 草稿 → 报名中 → 报名截止 → 已结束；下架是独立标记 |
| 关键规则 | 名额上限（通过审核人数达上限则报名入口关闭）、时段冲突（同场地时段不能重叠，边界相接不算冲突） |
| 数据形态 | 活动有标题、类型、组织者、报名截止时间、名额、状态；报名记录有学生、学号、审核状态 |

举例时优先用这些实体。不要编造与项目无关的业务（如电商、博客、天气）。

## 八、技术版本基线（不要凭记忆写别的版本号）

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

Vue 3.5 起 `defineProps` 支持响应式解构；`useTemplateRef`、`defineOptions`、`defineSlots` 都是 3.5 可用特性。
写这些特性时按官方文档的用法写，不确定就换成稳妥的老写法。

## 九、写完之后必须校验

```bash
cd /Users/moqi/Desktop/前端工程化开发/output/course-site
/Users/moqi/.workbuddy/binaries/python/versions/3.13.12/bin/python3 tools/check.py
```

**必须零问题。** 最常见的两类问题：

1. 直角引号（U+300C / U+300D）—— 换成 “ ”
2. 中文与西文直接相邻 —— 中间加空格

其他有用的参数：

```bash
# 输出某一类的全部问题（默认每类只显示 12 条）
/Users/moqi/.workbuddy/binaries/python/versions/3.13.12/bin/python3 tools/check.py --only=排版

# 输出全部问题
/Users/moqi/.workbuddy/binaries/python/versions/3.13.12/bin/python3 tools/check.py --all
```

链接检查（内容写完后跑一次）：

```bash
/Users/moqi/.workbuddy/binaries/python/versions/3.13.12/bin/python3 tools/check.py --links
```

批量清理用词：

```bash
# 清理行业黑话用词（闭环 / 落地 / 赋能 / 对齐 / 抓手）
/Users/moqi/.workbuddy/binaries/python/versions/3.13.12/bin/python3 tools/fix-wording.py
```

## 十、边界

- **只写分给你的文件**，不要改 `docs/.vitepress/` 下的配置、`sidebar.mts`、别人的页面。
- 不要在 Markdown 正文里写裸的 `<script setup>`，要写成 `` `<script setup>` `` 或放在代码块里。
- 内部链接用绝对路径，不带 `.md` 后缀，例如 `/unit04/04-reactivity`。
- 每节的“上一节 / 下一节”链接要指向真实存在的文件（按 sidebar.mts 里的清单）。
