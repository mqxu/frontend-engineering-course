# 3.2 ESLint 与 Prettier 配置

## 先看懂一条报错

在活动列表页里你写了一个状态判断，保存之后终端里出现这样一段：

```text [终端]
/Users/you/projects/campus-activity-admin/src/views/ActivityListView.vue
  42:11  error    Expected '===' and instead saw '=='      eqeqeq
  58:7   warning  'formatDeadline' is defined but never used  no-unused-vars

✖ 2 problems (1 error, 1 warning)
  1 error and 0 warnings potentially fixable with the --fix option.
```

第一次看到这种输出，多数人的反应是“看不懂，先删掉试试”。其实它的结构非常规整：

| 位置 | 内容 | 含义 |
| --- | --- | --- |
| 第一行 | 文件路径 | 问题在哪个文件 |
| `42:11` | 行号:列号 | 第 42 行第 11 列 |
| `error` | 严重程度 | `error` 会阻止提交，`warning` 不会 |
| `Expected '===' ...` | 问题描述 | 人话描述，告诉你哪里不对 |
| `eqeqeq` | 规则名 | **这是最关键的一列** |
| 最后两行 | 汇总 | 总共几个问题，有几个能自动修 |

**看懂规则名这一列，你就掌握了自查能力。** 把 `eqeqeq` 复制到搜索引擎里，
第一条结果就是这条规则的说明页，里面有正确写法、错误写法、怎么配置。

这一节把 ESLint、Prettier、Stylelint 三件工具配好，并让它们在
**编辑器里**和**提交时**两个位置自动执行。

## ESLint：检查“写得对不对”

ESLint 的配置文件有两个时代：旧的 `.eslintrc.*`、新的 `eslint.config.js`（扁平配置）。

| 形式 | 文件名 | 状态 |
| --- | --- | --- |
| 旧 | `.eslintrc.json` / `.eslintrc.js` | 逐步淘汰，但老项目里很多 |
| 新 | `eslint.config.js` | 当前标准 |

**新项目一律用扁平配置。** 它的好处是配置就是一个数组，每一项要么是“忽略规则”，
要么是“一组规则”，从上到下依次生效，看得见顺序。

```js [eslint.config.js]
import js from '@eslint/js'
import pluginVue from 'eslint-plugin-vue'
import globals from 'globals'

export default [
  // 第一段：哪些目录不检查
  { ignores: ['dist/**', 'node_modules/**', 'public/**'] },

  // 第二段：官方推荐的基础规则
  js.configs.recommended,

  // 第三段：Vue 官方插件的推荐规则
  ...pluginVue.configs['flat/recommended'],

  // 第四段：项目自己的调整
  {
    files: ['**/*.{js,vue}'],
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      // 声明代码里可以直接用的全局变量，避免误报 no-undef
      globals: {
        ...globals.browser,
        ...globals.node
      }
    },
    rules: {
      // 未使用的变量：给警告，不阻止提交
      'no-unused-vars': 'warn',
      // 强制用 ===，不允许 ==
      eqeqeq: ['error', 'always'],
      // 组件名允许单个单词（页面组件经常这样命名）
      'vue/multi-word-component-names': 'off'
    }
  }
]
```

逐段解释。

**第一段：`ignores`**。构建产物、依赖目录、静态资源不检查 ——
检查它们是纯浪费。注意这一项**必须是数组里的第一项**，否则对后面那些配置项不生效。

**第二段：`js.configs.recommended`**。官方推荐规则集，约 60 条，
覆盖的都是“几乎所有人都同意”的规则：`no-undef`（用了没定义的变量）、
`no-unused-vars`（声明了没用）、`no-constant-condition`（恒真的条件）等。

**第三段：Vue 插件的规则集**。`eslint-plugin-vue` 提供四档：

| 档位 | 管什么 | 建议 |
| --- | --- | --- |
| `flat/base` | 只是让 ESLint 能解析 `.vue` 文件 | 单独用没意义 |
| `flat/essential` | 只包含“不遵守就会出错”的规则 | 最低要求 |
| `flat/strongly-recommended` | 加上“强烈建议”的规则 | 推荐 |
| `flat/recommended` | 加上所有推荐规则 | **本课程用这档** |

分档的设计很实用：接手老项目时，先从 `essential` 开始，逐步往上调档，
而不是一上来开最严然后全关掉。

**第四段：项目自己的规则**。`files` 限定适用范围，`rules` 逐条调整等级。

### 规则的三个等级

| 写法 | 含义 | 什么时候用 |
| --- | --- | --- |
| `'off'` 或 `0` | 关闭 | 这条规则不适用于我们的场景 |
| `'warn'` 或 `1` | 警告（黄色） | 希望改，但不阻止提交 |
| `'error'` 或 `2` | 错误（红色） | 必须改，会阻止提交 |

带参数的规则写成数组，第一个元素是等级，后面是参数。
`eqeqeq: ['error', 'always']` 的意思是“等级是 error，并且始终要求用 `===`”。

::: warning 不要一上来把规则设成 error
`no-unused-vars` 设成 `error` 之后，只要有一个没用到的 import，提交就被拦下。
而很多未使用的变量是“正在写但还没写完”的状态。

**建议：先 `warn`，观察两周，之后再考虑升 `error`。**
判断标准是“这条规则报出来的问题，是不是每一次都真的该改”。
:::

### 用 `--fix` 自动修

```bash [终端]
# 检查并自动修复能修的部分
pnpm exec eslint . --fix

# 只看某个目录
pnpm exec eslint src --fix

# 看详细输出，理解每条规则为什么报
pnpm exec eslint src --format stylish
```

**哪些能自动修、哪些不能**，文件末尾的汇总会告诉你：

```text [终端]
✖ 5 problems (3 errors, 2 warnings)
  2 errors and 1 warning potentially fixable with the --fix option.
```

`potentially fixable` 的数量就是能自动修的条数。修不了的那些需要人判断 ——
比如“这个变量未使用，是删掉还是补上使用”。

::: tip 把检查放进 scripts
```json [package.json]
{
  "scripts": {
    "lint": "eslint .",
    "lint:fix": "eslint . --fix",
    "format": "prettier --write ."
  }
}
```

`pnpm lint` 比 `pnpm exec eslint .` 短得多 —— **命令越短，用的人越多。**
:::

## Prettier：只管“长什么样”

Prettier 是一个“有主见的格式化工具”：它几乎不接受配置，你只能选择用或不用。

它和 ESLint 的分工：

| 工具 | 管什么 | 能不能自动修 |
| --- | --- | --- |
| Prettier | 缩进、引号、分号、换行、每行长度 | **全部能** |
| ESLint | 未使用的变量、`==`、漏 `await`、Vue 用法错误 | 一部分能 |

配置只有几行：

```json [.prettierrc.json]
{
  "semi": false,
  "singleQuote": true,
  "printWidth": 100,
  "trailingComma": "none",
  "arrowParens": "always",
  "vueIndentScriptAndStyle": false
}
```

| 配置项 | 取值 | 为什么这么选 |
| --- | --- | --- |
| `semi` | `false` | 不写分号，和主流前端项目一致 |
| `singleQuote` | `true` | 字符串用单引号 |
| `printWidth` | `100` | 一行最多 100 字符，比默认的 80 更适合现代屏幕 |
| `trailingComma` | `none` | 不加尾逗号，避免 diff 里多出无意义的行 |
| `arrowParens` | `always` | 单参数箭头函数也加括号，改动时 diff 更小 |

::: tip 这些取值没有对错，只有“统一”
上面这些配置只是本课程的选择。**关键不是选了哪一个，而是全项目选同一个。**

所以 `prettier` 的配置**必须提交到仓库**，不能只放在自己的编辑器设置里。
:::

还需要一个忽略文件：

```bash [.prettierignore]
node_modules
dist
pnpm-lock.yaml
public
```

`pnpm-lock.yaml` 必须忽略 —— 它由 pnpm 生成，格式化它只会造成大量无意义的改动。

### 冲突怎么消除

历史上有一个常见麻烦：ESLint 里有些规则也能管格式（比如缩进、引号），
和 Prettier 打架 —— 你按 Prettier 格式化完，ESLint 说不行；按 ESLint 改完，
Prettier 又要改回去。

**新版本已经解决了这个问题**：ESLint 从 9 开始把格式类规则从核心里移除了，
所以现在“ESLint 管语义、Prettier 管格式”这个分工是天然的，不需要额外装包去关规则。

需要留意的只有一种情况：如果你的项目额外引入了 `@stylistic/eslint-plugin`
之类的格式规则插件，那就必须把它的规则关掉，否则还是会冲突。

| 方案 | 做法 | 什么时候用 |
| --- | --- | --- |
| 各管一层（推荐） | ESLint 只留语义规则，格式全给 Prettier | 新项目 |
| 用 @stylistic 统一 | 用 `@stylistic` 插件接管格式，不用 Prettier | 团队已有统一偏好时 |

**判断标准：同一个问题不能让两个工具都管。** 谁管格式都行，但不能都管。

## Stylelint：管样式文件

样式也需要检查。常见的两类问题：

```scss [src/assets/activity.scss（✗ 有问题）]
.activity-card {
  color: #ffffff;        // 颜色可以简写
  margin: 0px;           // 单位是多余的
  font-family: 'Arial', sans-serif;
  background: url('./bg.png');  // 路径写法要注意
}
```

配置：

```js [stylelint.config.js]
export default {
  extends: ['stylelint-config-standard', 'stylelint-config-recommended-vue'],
  rules: {
    // 类名用小写加短横线，和项目的命名约定一致
    'selector-class-pattern': '^[a-z][a-z0-9]*(-[a-z0-9]+)*$',
    // 允许使用 :deep() 这类 Vue 特有写法
    'selector-pseudo-class-no-unknown': [
      true,
      { ignorePseudoClasses: ['deep', 'global', 'slotted'] }
    ]
  }
}
```

`stylelint-config-recommended-vue` 的作用是让 Stylelint 能解析 `.vue` 文件里的
`<style>` 块（底层靠 `postcss-html`）。

```json [package.json]
{
  "scripts": {
    "lint:style": "stylelint \"src/**/*.{css,scss,vue}\"",
    "lint:style:fix": "stylelint \"src/**/*.{css,scss,vue}\" --fix"
  }
}
```

::: warning 加 `--allow-empty-input` 避免空匹配报错
当通配符没匹配到文件时，Stylelint 会以非零状态退出，导致流水线莫名其妙失败。

```bash [终端]
pnpm stylelint "src/**/*.{css,scss,vue}" --allow-empty-input
```

这个参数的意思是“没匹配到文件也算通过”。**在提交钩子里必须加**，
因为一次提交可能只改了 `.js` 文件，此时没有样式文件可检查。
:::

## 编辑器联动：让问题在你眼前出现

以上配置解决的是“能检查”。这一步解决的是“**在正确的位置检查**”。

```json [.vscode/settings.json]
{
  "editor.formatOnSave": true,
  "editor.defaultFormatter": "esbenp.prettier-vscode",
  "editor.codeActionsOnSave": {
    "source.fixAll.eslint": "explicit",
    "source.fixAll.stylelint": "explicit"
  },
  "eslint.validate": ["javascript", "vue"],
  "stylelint.validate": ["css", "scss", "vue"]
}
```

同时把需要的扩展列出来，新同学打开项目时编辑器会提示安装：

```json [.vscode/extensions.json]
{
  "recommendations": [
    "Vue.volar",
    "dbaeumer.vscode-eslint",
    "esbenp.prettier-vscode",
    "stylelint.vscode-stylelint",
    "EditorConfig.EditorConfig"
  ]
}
```

配好之后的效果：**你保存文件时，格式被自动整理，能自动修的问题被自动修掉，
修不了的在那一行标出来。**

::: tip 两个 settings.json 都要提交
`.vscode/settings.json` 提交到仓库的意义是：**新同学克隆下来就有同样的体验**，
不用再听别人说“记得开 formatOnSave”。

**注意不要把自己的个人偏好写进去**（比如主题、字体大小、快捷键）——
那些属于你自己的编辑器配置，不属于项目。
:::

## 提交钩子：拦住不合规的提交

编辑器联动靠的是“你会保存文件”。但总有人不保存就提交，或者用的是别的编辑器。
**最后一道防线是提交钩子。**

三个工具配合：

| 工具 | 职责 |
| --- | --- |
| husky | 提供 Git 钩子的挂载点 |
| lint-staged | **只对本次改动的文件**执行检查 |
| commitlint | 检查提交信息的格式 |

### 安装

```bash [终端]
pnpm add -D husky lint-staged @commitlint/cli @commitlint/config-conventional
pnpm exec husky init
```

`husky init` 会做三件事：生成 `.husky/` 目录、写一个示例的 `pre-commit`
钩子、在 `package.json` 里加一条 `prepare` 脚本。

### 配置

```sh [.husky/pre-commit]
pnpm exec lint-staged
```

```sh [.husky/commit-msg]
pnpm exec commitlint --edit "$1"
```

```json [package.json（新增部分）]
{
  "scripts": {
    "prepare": "husky"
  },
  "lint-staged": {
    "*.{js,vue}": ["eslint --fix", "prettier --write"],
    "*.{css,scss,vue}": ["stylelint --fix --allow-empty-input"],
    "*.{json,md,yml}": ["prettier --write"]
  }
}
```

三个地方值得说明。

**`"prepare": "husky"`**：`prepare` 是 npm 生命周期的钩子之一，
在 `pnpm install` 之后自动执行。这样**新同学克隆项目装完依赖，钩子就自动装好了**，
不需要谁去提醒。这就是它可以提交到仓库的原因。

**`lint-staged` 的配置是“按文件类型决定跑什么命令”**：

| 匹配 | 执行的命令 | 为什么要分开 |
| --- | --- | --- |
| `*.{js,vue}` | ESLint 修 + Prettier 格式化 | JS 和 Vue 文件都可能是脚本 |
| `*.{css,scss,vue}` | Stylelint 修 | `.vue` 里可能有 `<style>` |
| `*.{json,md,yml}` | 只格式化 | 这些文件不需要语义检查 |

注意 `.vue` 同时出现在两行里 —— 这是正常的，它会依次执行两组命令。

**`--allow-empty-input`** 在上一节讲过：一次提交可能没有样式文件，
不加这个参数 Stylelint 会因为“没有输入”而失败。

### commitlint：管提交信息

```js [commitlint.config.js]
export default {
  extends: ['@commitlint/config-conventional']
}
```

`config-conventional` 是社区最通用的约定，格式是：

```text
<类型>(<范围>): <描述>

类型（必填）：
  feat     新功能
  fix      修 bug
  docs     文档
  refactor 重构（不改行为）
  chore    杂事（依赖、配置）
  test     测试
  style    只改格式（不影响行为）

范围（可选）：改动影响哪个模块
描述（必填）：一句话说清做了什么，用中文，不加句号
```

几个真实的例子：

```bash
feat(activity): 活动列表支持按状态筛选
fix(activity): 修复报名截止时间在西半球显示成前一天
refactor(api): 把请求层拆成独立模块
chore(deps): 升级 vue 到 3.5.42
```

## 演示：故意提交一次不合规的代码

理论讲完了，直接做一次。**这一步必须自己动手做一遍。**

### 第一步：故意写一个格式错、又有语义问题的文件

```js [src/views/TestView.vue（临时文件，故意写错）]
<script setup>
import { ref } from 'vue'
import dayjs from 'dayjs'

const list=ref([])
function load(status){if(status==0){list.value=[]}}
</script>

<template><div>{{ list }}</div></template>
```

### 第二步：提交，观察被拦下

```bash [终端]
git add src/views/TestView.vue
git commit -m "改了一下"
```

终端输出（内容因配置而异，关键词一致）：

```text [终端]
✔ Preparing lint-staged...
❯ Running tasks for staged files...
  ❯ *.vue — 2 files
    ❯ eslint --fix
      ✖ eslint --fix found some errors. Please fix them and try committing again.

/Users/you/projects/campus-activity-admin/src/views/TestView.vue
  7:15  error  Expected '===' and instead saw '=='  eqeqeq

✖ 1 problem (1 error, 0 warnings)
```

**提交没有成功。** 关键信息是最后那行 `✖ 1 problem` ——
`lint-staged` 检查到了错误，并且因为 ESLint 以非零状态退出，
Git 的提交被中止了。

### 第三步：修掉错误再提交，观察提交信息被拦下

```bash [终端]
# 手动把 == 改成 ===
git add src/views/TestView.vue
git commit -m "改了一下"
```

这次 `pre-commit` 过了，但 `commit-msg` 钩子拦下了：

```text [终端]
⧗   input: 改了一下
✖   subject may not be empty [subject-empty]
✖   type may not be empty [type-empty]

✖   found 2 problems, 0 warnings
ⓘ   Get help: https://github.com/conventional-changelog/commitlint/#what-is-commitlint
```

### 第四步：写一个合规的提交信息

```bash [终端]
git commit -m "feat(activity): 活动列表支持按状态筛选"
```

```text [终端]
[feat/activity-filter 3a1b2c4] feat(activity): 活动列表支持按状态筛选
 1 file changed, 12 insertions(+), 3 deletions(-)
```

提交成功。**这时候你才真正把这一套配置验证完了。**

::: danger 不要用 --no-verify 绕过钩子
`git commit --no-verify` 可以跳过所有钩子。它存在的意义是“紧急情况下的例外”，
不是“日常绕过的开关”。

**如果一个钩子三天两头需要绕过，说明规则配得不合理** ——
应该去调整规则（降级为 `warn`、加忽略），而不是养成绕过的习惯。
:::

## 小结

- ESLint 报错的结构是“文件:行:列 + 等级 + 描述 + **规则名**”，规则名是自查入口。
- 新项目用扁平配置 `eslint.config.js`，是一个数组，`ignores` 必须放第一项。
- 规则等级 `off` / `warn` / `error`；新项目从 `warn` 起步，不要一上来全开 `error`。
- `--fix` 能自动修一部分问题，文件末尾的汇总会告诉你修了几条。
- Prettier 管格式，ESLint 管语义，**同一个问题不能让两个工具都管**。
- Stylelint 管样式文件，提交钩子里要加 `--allow-empty-input`。
- 编辑器联动（保存即格式化）让问题在你眼前出现，`.vscode/` 两个文件都要提交。
- husky + lint-staged 让检查在**提交时**对**改动文件**执行；commitlint 管提交信息。
- 验证配置是否生效的唯一方法：**故意提交一次不合规的代码，看有没有被拦下**。

## 常见坑

::: details 坑 1：钩子完全不生效，提交照样成功
**现象**：配完 husky，提交不合规的代码居然通过了。

**原因**：按可能性排查四件事。

1. `.husky/pre-commit` 文件没有可执行权限。
2. 项目不是 Git 仓库（`git init` 没做，或是在子目录里提交）。
3. `prepare` 脚本没执行过 —— 手动跑一次 `pnpm exec husky init` 或 `pnpm run prepare`。
4. `.husky/` 目录被提交到了仓库，但没有在 `.gitignore` 之外 ——
   确认里面确实有 `pre-commit` 文件。

**处理**：

```bash [终端]
ls -la .husky/          # 看 pre-commit 在不在、有没有执行权限
git rev-parse --is-inside-work-tree   # 确认在 Git 仓库里
pnpm exec husky init    # 重新初始化
```

**验证方式永远是同一句话：做一次不合规的提交试试。**
:::

::: details 坑 2：lint-staged 报 “No staged files match any configured task”
**现象**：改了 `.vue` 文件，提交时提示没有匹配的文件。

**原因**：匹配规则写错了。常见的是把 `*.vue` 写成了 `**.vue`，
或者键名写成了 `vue`（少了 `*.`）。

**处理**：检查 `lint-staged` 的键名格式，必须是 glob：

```json [package.json 片段]
"lint-staged": {
  "*.vue": ["eslint --fix"]
}
```

**另一个原因**：改了文件但没 `git add`。`lint-staged` 只看**已暂存**的文件。
:::

::: details 坑 3：ESLint 和 Prettier 反复改同一样东西
**现象**：保存时 Prettier 格式化，紧接着 ESLint 又改回去，文件不停变动。

**原因**：有格式规则同时被两个工具管。

**处理**：查 ESLint 配置里有没有引入格式类的规则集或插件。
如果有 `@stylistic/eslint-plugin` 之类的包，把它的格式规则关掉。

**判断方法**：关掉 Prettier 单独跑 ESLint，看它是否改动了格式。
如果动了，就是有格式规则在 ESLint 这边。
:::

::: details 坑 4：CI 里 eslint 报了一堆本地没有的错误
**现象**：本地 `pnpm lint` 干净，流水线上失败。

**原因**：三个可能。

1. 本地改完没提交（`dist/` 或新文件没进 Git）。
2. 本地用了全局安装的 ESLint，版本和项目里的不一致。
3. 大小写不一致：本地 macOS 不区分大小写，Linux 区分。

**处理**：一律用 `pnpm exec eslint`（用项目里装的版本），
并且**提交前一定跑一次 `pnpm lint`**。
:::

::: details 坑 5：`eslint .` 检查了 dist 目录，报几千个错误
**现象**：执行 `pnpm lint` 之后终端刷出几千行报错。

**原因**：`ignores` 没配，或者没放在数组第一位。

**处理**：在 `eslint.config.js` 的数组**第一项**写：

```js [eslint.config.js 片段]
export default [
  { ignores: ['dist/**', 'node_modules/**', 'public/**'] },
  // ……其余配置
]
```

顺便检查 `.eslintignore`（旧方案的遗留文件）是否和新配置冲突 ——
扁平配置模式下不再需要 `.eslintignore`，把它删掉。
:::

## 课后练习

::: details 练习 1：读懂五条报错
下面是一条报错的五个字段。逐个说明它的含义，并说出拿到这条报错之后你会怎么做。

```text [终端]
/Users/you/projects/campus-activity-admin/src/components/ActivityCard.vue
  27:5   warning  'props' is defined but never used   no-unused-vars
```

**验收点**：要能答出四件事 —— 问题在哪个文件的第几行、严重程度、
**规则名是什么**、去哪里查这条规则的完整说明。

**进阶**：把这条报错手动制造出来（在组件里声明 `props` 但不用），
然后分别试一次 `no-unused-vars` 设成 `warn`、`error`、`off` 三种情况下的表现差异。
:::

::: details 练习 2：从零配好一套检查
在一个新项目里完成：

1. 装 ESLint、Prettier、Stylelint 及各自需要的配置包。
2. 配好 `eslint.config.js`（含 `ignores`、Vue 规则集、至少 3 条自定义规则）。
3. 配好 `.prettierrc.json` 与 `.prettierignore`。
4. 配好 `stylelint.config.js`。
5. 在 `package.json` 里加 `lint`、`lint:fix`、`format`、`lint:style` 四条脚本。
6. 配好 `.vscode/settings.json` 与 `.vscode/extensions.json`。

**验收标准**

| 检查项 | 要求 |
| --- | --- |
| 检查能跑 | `pnpm lint` 输出正常，不检查 `dist/` |
| 能自动修 | 故意写错格式，`pnpm lint:fix` 能修好 |
| 编辑器生效 | 保存文件时自动格式化，不做任何手动操作 |
| 配置已提交 | `.vscode/` 下两个文件和三个工具配置都进了 Git |

**排查提示**：保存不格式化时，先确认右下角的格式化工具是不是 Prettier
（编辑器里点一下状态栏就能看到）。不是的话，检查 `editor.defaultFormatter` 的值。
:::

::: details 练习 3：配好提交钩子并验证拦截
要求：

1. 装 husky、lint-staged、commitlint 相关包。
2. 配好 `pre-commit` 与 `commit-msg` 两个钩子。
3. 在 `package.json` 里配 `lint-staged`，至少覆盖 `.js`、`.vue`、`.scss` 三类。
4. 手动执行一次 `pnpm exec husky init` 确认钩子已挂载。

**验收标准**（三项都要截图或贴终端输出）

| 场景 | 预期结果 |
| --- | --- |
| 提交一个格式有问题的 `.js` 文件 | 被 `pre-commit` 拦下，终端有 ESLint 报错 |
| 提交信息写“改了一下” | 被 `commit-msg` 拦下，终端有 commitlint 报错 |
| 改成 `feat(activity): ...` 并修好格式 | 提交成功 |

**关键点**：第二个场景要在第一个场景修好之后做 ——
`pre-commit` 在 `commit-msg` 之前执行，pre-commit 不过就看不到 commitlint 的报错。
:::

::: details 练习 4：写三条自己的规则
结合 [3.1 的“三遍规则”练习](/unit03/01-why-lint#课后练习)，
写三条适合本项目的额外 ESLint 规则，并说明理由。

格式：

| 规则名 | 等级 | 理由 | 什么情况下会误报 |
| --- | --- | --- | --- |
| | | | |

**参考思路**：可以从这几个方向找 ——

- 控制台输出：`no-console`（但预览环境可能需要，要配例外）。
- 调试代码：`no-debugger`。
- 组件命名：`vue/component-name-in-template-casing`。
- 属性顺序：`vue/attributes-order`。

**验收点**：“什么情况下会误报”这一栏必须填。答不出来说明这条规则可能不适合现在加。
:::

---

上一节：[3.1 为什么需要代码规范](/unit03/01-why-lint) ·
下一节：[3.3 模块化与目录组织](/unit03/03-modules-structure)
