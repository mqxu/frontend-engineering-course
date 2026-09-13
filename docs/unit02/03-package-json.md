# 2.3 package.json 逐字段精讲

## 一次“改了一行就炸”的构建

活动列表页需要格式化时间，你听说 Vue 2 的项目用 `moment` 很常见，于是顺手打开了
`package.json`。看着依赖列表里那个 `"vue": "3.5.42"`，你想：“版本号写死了不灵活，
项目里又只用了几行 Vue 的语法，降个大版本应该没问题吧？”于是改成：

```diff [package.json]
- "vue": "3.5.42"
+ "vue": "^2.0.0"
```

然后：

```bash [终端]
pnpm install
pnpm dev
```

安装一路顺利，启动却直接报错：

```text [浏览器控制台]
Uncaught SyntaxError: The requested module '/node_modules/.vite/deps/vue.js'
does not provide an export named 'createApp'
```

`main.js` 里那行 `import { createApp } from 'vue'` 拿不到 `createApp`。
因为 **Vue 2 根本没有 `createApp` 这个导出** —— 它是 Vue 3 才有的 API。

问题出在哪？`package.json` 里的版本范围**不是注释，是命令**。
你写 `^2.0.0`，pnpm 就老老实实装了 2.x 的最新版；`^2.0.0` 在语法上完全合法，
工具不会提醒你“这个范围和你代码里的写法不匹配”。

这一节把 `package.json` 的每个关键字段讲透，重点讲清**版本范围到底是什么意思**。
这是排查“依赖版本问题”的基础，也是第 3 周建仓库时必须读懂的文件。

## 逐个字段看

先看一份完整的、本课程项目要用的 `package.json`：

```json [package.json]
{
  "name": "campus-activity-admin",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "engines": {
    "node": ">=20.19.0",
    "pnpm": ">=12.0.0"
  },
  "packageManager": "pnpm@12.4.1",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "axios": "^1.20.0",
    "element-plus": "^2.14.5",
    "pinia": "^4.0.3",
    "vue": "^3.5.42",
    "vue-router": "^5.3.1"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^6.0.0",
    "vite": "^8.3.0"
  }
}
```

下面按“容易搞混的程度”从低到高讲。

### `name` 与 `version`

`name` 是包名。发布到 npm 上要有唯一性，本地项目只要求小写、用短横线连接。
`version` 只在发布包时有意义，**本地项目写 `0.1.0` 就行** —— 它不会影响构建。

::: tip 不要用中文和空格
`"name": "校园活动平台"` 会导致安装时报 `Invalid package name`。
统一用 kebab-case：`campus-activity-admin`。
:::

### `private`

```json [package.json]
{ "private": true }
```

设成 `true` 表示“这个包不允许被发布到 npm”。**所有业务项目都应该加上它**，原因有两个：

1. 防止误操作。手滑敲了 `npm publish`，没有这个字段就把内部代码公开了。
2. 告诉工具“这不是要发布的库”，一些检查会相应放宽。

### `type`

决定 `.js` 文件按哪种模块规范解析：

| 取值 | `.js` 文件被当作 | 写法 |
| --- | --- | --- |
| 不写（默认 `commonjs`） | CommonJS | `const vue = require('vue')` |
| `"module"` | ES Module | `import { createApp } from 'vue'` |

现代前端项目统一写 `"module"`。**这个字段漏写会有一个很典型的现象**：
某天你新建一个 `vite.config.js` 用来读环境变量，编辑器提示
`require is not defined in ES module scope`，或者反过来提示不能用 `import`。

用 `create-vue` 生成的项目已经写好了，自己在根目录加 `.js` 脚本时要注意这个前提。

### `engines` 与 `packageManager`

这一对在 [2.1](/unit02/01-node) 讲过：`engines` 是“要求的版本范围”，
`packageManager` 是“指定用哪个包管理器的哪个版本”。

两者的区别值得再强调一次：

| 字段 | 作用对象 | 不满足时的表现 |
| --- | --- | --- |
| `engines` | Node / pnpm 的版本 | 警告；开了 `engine-strict` 才报错 |
| `packageManager` | 具体哪个包管理器 | Corepack 直接拒绝用别的工具装 |

### `scripts`

键是命令名，值是要执行的 shell 命令。约定俗成的三条：

| 命令 | 干什么 | 什么时候跑 |
| --- | --- | --- |
| `dev` | 启动开发服务器 | 开发时一直开着 |
| `build` | 构建生产产物 | 交付前、流水线里 |
| `preview` | 本地预览构建产物 | 每次 `build` 之后 |

两个实用技巧：

```json [package.json]
{
  "scripts": {
    "dev": "vite --port 5174",
    "lint": "eslint .",
    "check": "pnpm lint && pnpm build"
  }
}
```

- 自定义脚本可以组合已有脚本：`pnpm check` 会依次执行 `lint` 和 `build`，
  任意一步失败就停下来。
- 想临时加参数，用 `pnpm dev -- --port 5175`（`--` 后面的参数透传给底层命令）。

::: warning scripts 里的命令不需要写路径
`"dev": "vite"` 里的 `vite` 不是系统命令，而是
`node_modules/.bin/vite`。pnpm 执行脚本时会自动把 `node_modules/.bin`
加到 `PATH` 前面，所以直接写命令名就行。

这也解释了一个常见困惑：**为什么在项目外敲 `vite` 报 `command not found`，
`pnpm dev` 却能用**。
:::

### `dependencies` 与 `devDependencies`

| 字段 | 含义 | 判断标准 |
| --- | --- | --- |
| `dependencies` | 运行时需要的包 | 会被 import 进业务代码，**进入构建产物** |
| `devDependencies` | 只在开发阶段需要的包 | 构建产物里不需要它 |

判断方法只有一句：**把 `node_modules` 删掉、只部署构建产物，这个包还需要存在吗？**

几个容易判断错的例子：

| 包 | 放哪 | 理由 |
| --- | --- | --- |
| `vue` | `dependencies` | 代码里 import 了，会被打包进产物 |
| `axios` | `dependencies` | 同上 |
| `@vueuse/core` | `dependencies` | 组合式函数，被业务代码 import |
| `element-plus` | `dependencies` | UI 组件，代码里用了 |
| `vite` | `devDependencies` | 只在构建时运行 |
| `eslint` | `devDependencies` | 只在检查时运行 |
| `sass` | `devDependencies` | 样式在构建时被编译成 CSS |
| `vitest` | `devDependencies` | 只在跑测试时运行 |
| `husky` | `devDependencies` | 只在提交时运行 |

`sass` 是最容易搞错的一个：它是**构建时的编译器**，产物里只有编译好的 CSS，
没有 `sass` 本身，所以放 `devDependencies`。

### `peerDependencies`

这个字段初学者最少见，但它解释了很多“安装时的一堆警告”。

`peerDependencies` 的意思是：**“我的插件需要宿主环境提供某个包，但我不自己装它。”**
举一个真实例子：`@vitejs/plugin-vue` 是 Vite 的插件，它必须和 `vite` 配合工作，
但它不会把 `vite` 装进自己的依赖里：

```json [node_modules/@vitejs/plugin-vue/package.json（节选）]
{
  "peerDependencies": {
    "vite": "^5.0.0 || ^6.0.0 || ^7.0.0 || ^8.0.0",
    "vue": "^3.2.25"
  }
}
```

你项目里装了 `vite@8.3.0`，落在它接受的范围里，一切正常。
如果你把 `vite` 降到 4.x，pnpm 会给出警告：

```text [警告输出]
 WARN  Issues with peer dependencies found
└─┬ @vitejs/plugin-vue 6.0.0
  └── ✕ unmet peer vite@^5.0.0 || ^6.0.0 || ^7.0.0 || ^8.0.0: found 4.5.0
```

看到 `unmet peer` 就要注意了：插件和宿主版本不匹配，运行起来大概率出问题。
**处理方式是统一版本，不是去关掉警告。**

## 语义化版本：三个数字各管什么

版本号 `MAJOR.MINOR.PATCH`（主版本.次版本.修订号）的约定：

```text
3 . 5 . 42
│   │   └── PATCH：修 bug，不改接口 —— 可以放心升
│   └────── MINOR：加功能，保持兼容 —— 一般可以升
└────────── MAJOR：有破坏性改动 —— 升之前必须查文档
```

范围符号就是基于这个约定，表达“我能接受升到哪一步”：

| 写法 | 含义 | `1.2.3` 能升到 | 不能升到 |
| --- | --- | --- | --- |
| `1.2.3` | 精确版本 | 就是 1.2.3 | 任何别的版本 |
| `~1.2.3` | 允许修订号变 | `1.2.9` | `1.3.0` |
| `^1.2.3` | 允许次版本与修订号变 | `1.9.9` | `2.0.0` |
| `>=1.2.3` | 至少 1.2.3 | `5.0.0` 也行 | 低于 1.2.3 |
| `*` 或 `latest` | 任意版本 | 任何 | 无 |
| `1.x` | 主版本固定为 1 | `1.9.9` | `2.0.0` |

### 用 Vue 的实际版本对照一遍

| 你写的范围 | 安装时可能拿到的版本 | 会不会拿到 Vue 2 |
| --- | --- | --- |
| `"vue": "3.5.42"` | 3.5.42 | 不会 |
| `"vue": "~3.5.42"` | 3.5.42 到 3.5.x | 不会 |
| `"vue": "^3.5.42"` | 3.5.42 到 3.x 的最新 | 不会 |
| `"vue": "^2.0.0"` | 2.0.0 到 2.x 的最新（2.7.16） | **会** |
| `"vue": "*"` | 最新的任何版本 | 不会（但拿到什么不好说） |
| `"vue": ">=2.0.0"` | 2.x 到 3.x 的最新 | **可能会** |

**回到开头那个报错**：你写 `^2.0.0`，pnpm 装的是 2.7.16。
代码里用的是 `createApp`，Vue 2 里不存在，于是构建直接失败。
`^2.0.0` 和 `^3.5.42` 都是合法的范围，工具没法替你判断哪个对 ——
**范围表达的是你的意图，意图错了工具救不了。**

### 有一类版本范围要特别小心：0.x

主版本是 0 表示“还在开发中，接口随时会变”，所以语义化版本对 `^0.x` 有特殊规定：

| 范围 | 实际含义 |
| --- | --- |
| `^0.2.3` | `>=0.2.3 <0.3.0`（只允许修订号变） |
| `^0.0.3` | `>=0.0.3 <0.0.4`（等同于精确版本） |
| `^1.2.3` | `>=1.2.3 <2.0.0` |

**判断口诀：主版本为 0 时，`^` 的行为退化成 `~`，甚至变成精确版本。**
这类包升级时只能靠自己看变更说明，不能依赖范围符号。

::: tip 不要手改版本范围
想升降版本，用命令：

```bash [终端]
pnpm add vue@^3.5.42        # 改 dependencies 里的 vue
pnpm add -D vite@^8.3.0     # 改 devDependencies 里的 vite
```

命令会做三件事：查这个范围能不能解析出版本、写字段、更新锁文件。
手写只会做第一件的一半 —— 而且写错了要等 `pnpm install` 或运行时才发现。
:::

## 把两个文件连起来看

回顾一下 2.2 讲过的一对关系，这次从“字段”角度再看一遍：

| 文件 | 记的是 | 谁写 | 版本形态 |
| --- | --- | --- | --- |
| `package.json` | 你的**意图**（`^3.5.42`） | 你，用 `pnpm add` | 范围 |
| `pnpm-lock.yaml` | 实际装出来的**结果**（`3.5.42`） | pnpm | 精确 |

锁文件必须提交，理由是：**如果没有它，`^3.5.42` 这个范围在不同时间会解析出不同结果。**
今天装到 3.5.42，下个月新版本发布后装到 3.5.48。两个人跑的不是同一份代码，
却都认为自己“没改过依赖”。

::: danger 排查版本问题时，先看锁文件里实际装了什么
“我明明写的是 Vue 3，怎么会报 Vue 2 的错”这种问题，答案通常在两个地方：

```bash [终端]
# 看 package.json 里写的范围
pnpm why vue
# 看实际装出来的版本
node -p "require('./node_modules/vue/package.json').version"
```

**永远以锁文件和实际安装的版本为准，不要凭 `package.json` 里的印象判断。**
:::

## 小结

- `package.json` 里的版本范围是命令，不是注释；写错了工具不会替你判断。
- `private` 防止误发布，`type: "module"` 让 `.js` 按 ES Module 解析，业务项目都要写。
- `dependencies` 是运行时依赖，`devDependencies` 是开发工具依赖；`sass` 属于后者。
- `peerDependencies` 由宿主环境提供，看到 `unmet peer` 要统一版本，不要关警告。
- 语义化版本 `MAJOR.MINOR.PATCH` 对应“破坏性改动 / 加功能 / 修 bug”。
- `^1.2.3` 升到 `<2.0.0`，`~1.2.3` 升到 `<1.3.0`，精确版本不升；`^0.x` 行为更严格。
- 排查版本问题以**锁文件和实际安装版本**为准。

## 常见坑

::: details 坑 1：改了 package.json 但没跑 pnpm install
**现象**：手动在 `package.json` 里加了一行依赖，代码里 import 报
`Failed to resolve import`。

**原因**：改 `package.json` 只是改了“意图”，`node_modules` 和锁文件还没有跟着变。

**处理**：执行 `pnpm install`。**记住这条链：改 `package.json` → `pnpm install` →
`node_modules` 与锁文件同步更新。** 缺一步都不生效。
:::

::: details 坑 2：把 devDependencies 里的东西 import 进了业务代码
**现象**：本地一切正常，构建时报 `Rollup failed to resolve import`。

**原因**：某个包装在 `devDependencies` 里，但被业务代码 import 了。
开发服务器对它宽容，构建时会严格按依赖关系去找。

**处理**：把它移到 `dependencies`：

```bash [终端]
pnpm remove -D some-package
pnpm add some-package
```

**预防方法**：装包时先想清楚“构建产物里要不要它”，不要一律 `-D`。
:::

::: details 坑 3：用 `*` 或 `latest` 当版本
**现象**：某天同事拉代码后整个项目跑不起来，谁也没改代码。

**原因**：`package.json` 里写了 `"axios": "*"`，刚好那天发布了不兼容的大版本，
重新安装就装到了新版本。

**处理**：改成 `^` 开头的范围，并且把锁文件提交上。

**为什么 `*` 更危险**：`^` 至少保证主版本不变，`*` 连主版本都不管。
**范围越宽，未来的不确定性越大。**
:::

::: details 坑 4：以为 `~` 比 `^` 的“权限更大”
**现象**：想让依赖只升修订号，写了 `^`，结果升到了次版本，出了兼容问题。

**原因**：记反了。`^` 比 `~` 宽松。

**记忆方法**：符号的形状代表“锁住几位”。
`~` 只松开最后一位（修订号），`^` 松开后两位（次版本 + 修订号）。
**想更保守就用 `~`，或用精确版本。**
:::

::: details 坑 5：删掉 package.json 里的依赖，代码却没删 import
**现象**：`pnpm remove dayjs` 之后，构建报 `Failed to resolve import "dayjs"`。

**原因**：依赖删了，但 `src/utils/format.js` 里那行 `import` 还在。

**处理**：删依赖之前先搜一遍代码，确认没有引用：

```bash [终端]
# 搜一搜这个包在哪里被用了
grep -rn "from 'dayjs'" src/
```

**顺序很重要**：先删代码里的引用，再删依赖。反过来会出现“装回去还是跑不了”的假象。
:::

## 课后练习

::: details 练习 1：把每个字段讲给同学听
不看这一节的内容，用自己的话回答下面八个问题。答不上来的回去查：

1. `private: true` 不写会有什么风险？
2. `type: "module"` 影响的是什么？
3. `pnpm add -D sass` 装到哪个字段？为什么？
4. `peerDependencies` 和 `dependencies` 的区别是什么？
5. `^1.2.3` 能不能升到 `1.3.0`？能升到 `2.0.0` 吗？
6. `~1.2.3` 能升到 `1.3.0` 吗？
7. `^0.2.3` 能升到 `0.3.0` 吗？
8. `pnpm-lock.yaml` 里记的是范围还是精确版本？

**验收点**：第 5、6、7 三题要能说出**范围的上边界数字**，而不是只答“能”或“不能”。
:::

::: details 练习 2：复现一次“改范围改炸”
按本节开头的场景，在一个测试项目里实际操作一遍：

1. 初始项目用 Vue 3，跑通 `pnpm dev`。
2. 把 `"vue": "^3.5.42"` 改成 `"vue": "^2.0.0"`。
3. `pnpm install`，启动，把报错完整记录下来。
4. 用 `pnpm why vue` 和读 `node_modules/vue/package.json` 找出实际装的版本。
5. 改回 `^3.5.42`，删掉 `node_modules` 重装，确认恢复。
6. 在报告里写清“为什么会装到 2.x”。

**验收点**：报告里要能指出**三个证据**：`package.json` 里写的范围、
锁文件里记的版本、`node_modules/vue/package.json` 里的版本。

**这一步必须在练习项目里做**：不要拿正在做的课程作业直接改。
改坏一次是学习，改坏作业是事故。

:::

::: details 练习 3：为校园活动服务平台补全 package.json
现在给综合项目写一份 `package.json`。要求：

1. 运行时依赖包含：`vue`、`vue-router`、`pinia`、`axios`、`element-plus`。
2. 开发依赖包含：`vite`、`@vitejs/plugin-vue`、`sass`、`eslint`、`prettier`。
3. 三条脚本：`dev`、`build`、`preview`，再加一条 `check` 依次跑检查和构建。
4. `engines` 要求 Node `>=20.19.0`，`packageManager` 指定 pnpm。
5. `private: true`，`type: "module"`。

**参考思路**：不要照抄上面的示例数值，**逐个用 `pnpm add` / `pnpm add -D` 装一遍**，
观察每个包最后落在哪个字段、版本范围被写成了什么。

**验收点**：`pnpm install` 之后 `pnpm check` 能跑通（检查暂时没有的话，
先让 `check` 里只有 `build`）。
:::

::: details 练习 4：写一份 peerDependencies 说明
找三个你项目里用到的、带 `peerDependencies` 的包（提示：插件类、UI 库的适配包、
测试框架的插件通常都有）。对每一个说明：

1. 它要求宿主提供哪个包、什么范围？
2. 你项目里实际装的是什么版本？
3. 版本对得上吗？如果对不上会有什么现象？

**参考思路**：用 `pnpm why <包名>` 看解析结果，或者直接打开
`node_modules/<包名>/package.json` 看 `peerDependencies`。

**这项检查很实用**：升级依赖时提前发现 `peer` 不匹配，比等到运行时报错省时间。
:::

---

上一节：[2.2 包管理器与依赖安装](/unit02/02-package-manager) ·
下一节：[2.4 构建工具与 Vite](/unit02/04-vite)
