# 1.2 一个现代前端工程长什么样

## 先看一个真实工程的骨架

不用先配环境，我们先"看看"。下面是官方脚手架 `create-vue` 生成的项目结构（这是 2024 年之后
新建 Vue 3 项目的标准做法）：

```text [项目根目录]
my-project/
├── .vscode/
│   └── extensions.json      推荐安装的编辑器扩展，团队统一用
├── public/                  不需要构建、原样复制到输出目录的文件
│   └── favicon.ico
├── src/                     ★ 你写的代码几乎都在这里
│   ├── assets/              需要经过构建处理的静态资源（图片、样式）
│   │   ├── base.css
│   │   └── logo.svg
│   ├── components/          通用组件，可跨页面复用
│   ├── router/              路由配置
│   │   └── index.js
│   ├── stores/              全局状态
│   │   └── counter.js
│   ├── views/               页面组件，一个路由对应一个
│   ├── App.vue              根组件
│   └── main.js              ★ 应用入口
├── .gitignore               哪些文件不提交到 Git
├── index.html               ★ 浏览器访问的入口页面
├── jsconfig.json            别名与智能提示配置
├── package.json             ★ 项目说明书：依赖、脚本、元信息
├── README.md                给同事看的说明
└── vite.config.js           ★ 构建工具配置
```

先记住三条线：

1. **`index.html` 是起点**，浏览器先加载它。注意它不在 `src` 里，就在根目录。
2. **`src/` 是主体**，90% 的工作在这个目录里完成。
3. **根目录那些配置文件**决定"怎么构建、怎么检查、怎么运行"，一般不常改。

下面逐个拆开看。

## `index.html` 为什么在根目录

很多人第一次看到会觉得奇怪：怎么文件名叫 `index.html` 却没在 `src` 里？

因为 Vite 是**以根目录的 `index.html` 作为入口**来启动整个应用的。打开它会看到很简单的内容：

```html [index.html]
<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" href="/favicon.ico" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>校园活动服务平台</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.js"></script>
  </body>
</html>
```

关键只有两行：

- `<div id="app"></div>` —— 一个空容器，Vue 会把整个应用挂载到这里面。
- `<script type="module" src="/src/main.js">` —— 引入入口脚本，从这里开始加载所有代码。

::: tip 和以前写页面的区别
以前写页面，HTML 里就有内容；现在页面是空的，内容全由 JavaScript 生成。

这不是"退步"，而是把"页面长什么样"的控制权从静态标签交给了程序。
代价是：**如果 JS 报错，用户看到的就是一片空白。** 所以后面每个业务页面都要写"错误态"，
不能只有一个转圈。
:::

## `src/` 里的目录各管什么

### `main.js`：应用入口

```js [src/main.js]
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './assets/main.css'

const app = createApp(App)

app.use(createPinia())  // 装上全局状态
app.use(router)         // 装上路由

app.mount('#app')       // 挂到 index.html 里那个 id="app" 的容器上
```

这个文件的职责是**组装**：把路由、状态管理、全局样式装到应用上，然后挂载。
业务逻辑不要写在这里。

### `App.vue`：根组件

它是所有页面的容器。最简形态只有一行：

```vue [src/App.vue]
<template>
  <RouterView />
</template>
```

`RouterView` 是一个"占位符"—— 当前路由匹配到哪个页面组件，就把它渲染在这里。

### `views/` 与 `components/`：页面与组件

这是新手最容易混的一对。判断标准很简单：

| 目录 | 放什么 | 判断依据 |
| --- | --- | --- |
| `views/` | 页面组件 | **一个路由对应一个**，直接出现在 `router/index.js` 里 |
| `components/` | 通用组件 | 被多个页面引用，或者虽然只用一个页面但内容独立、可以单独讲清楚 |

举例如下：

```text
views/ActivityListView.vue      ← 路由 /activities 对应的页面（在 views/）
components/
├── ActivityStatusTag.vue       ← 活动状态标签，列表页和详情页都要用（在 components/）
├── SearchBar.vue               ← 搜索条，多个列表页复用（在 components/）
└── ConfirmDialog.vue           ← 二次确认弹窗，到处都要用（在 components/）
```

::: warning 不要为了分层而分层
如果一个组件只在一个页面用一次，而且拆出去之后父组件需要传五个属性才能工作，
那还不如就写在页面里。**拆分的目的是减少复杂度，不是增加文件数。**
判断依据会在[单元 7](/unit07/01-sfc)展开讲。
:::

### `assets/` 与 `public/`：两个放资源的地方

这对是最常被问到的：

| 目录 | 处理方式 | 什么时候用 |
| --- | --- | --- |
| `src/assets/` | **经过构建工具处理**：会被压缩、加哈希指纹、可以 import | 项目自己的图片、样式、字体 |
| `public/` | **原样复制**到输出目录，不处理 | 固定路径的文件：`favicon.ico`、`robots.txt`、第三方校验文件 |

```js [引用方式对比]
// 方式一：从 assets 引用，经过构建处理
import logoUrl from '@/assets/logo.svg'
console.log(logoUrl) // 输出 /assets/logo-a3f9c2.svg（带哈希，可长缓存）

// 方式二：从 public 引用，路径写死
const url = '/favicon.ico' // 直接就是根路径，构建后仍然在这个位置
```

**判断规则**：需要构建处理的（会被压缩、要带缓存指纹、要在 JS 里 import 的）放 `assets`；
必须保持固定路径的放 `public`。

### `router/`、`stores/`、`api/`

这三个目录是应用架构的核心，分别在单元 9、10 讲。现在只需要知道：

| 目录 | 职责 | 一句话 |
| --- | --- | --- |
| `router/` | 决定"什么地址显示什么页面" | 地址与页面的映射表 |
| `stores/` | 存"多个页面都要用的数据" | 比如登录用户信息 |
| `api/` | 存"接口调用函数" | 一个业务模块一个文件 |

::: tip 一个常见的坏习惯
在组件里直接写 `axios.get('http://xxx.com/api/activity/list')`。

这样写的后果是：接口地址变了要改十几个文件；测试环境切生产环境要全局搜索替换；
同一个接口在两个页面被写了两次，参数还不一样。

**正确做法**：地址写在 `api/` 里，组件只调用函数。
:::

## 根目录的配置文件

这些文件平时不用改，但必须知道它们是干什么的。**遇到问题时能定位到是哪个文件在起作用。**

| 文件 | 作用 | 什么时候要改 |
| --- | --- | --- |
| `package.json` | 项目说明书：依赖清单、脚本命令、项目元信息 | 加依赖、加脚本命令 |
| `vite.config.js` | 构建配置：别名、代理、打包策略 | 配路径别名、配接口代理 |
| `jsconfig.json` | 告诉编辑器项目结构，让 `@/` 别名有智能提示 | 加别名时同步改 |
| `.gitignore` | 哪些文件不进 Git | 新增了生成物、临时目录 |
| `.env` 系列 | 环境变量 | 配接口地址、应用标题 |
| `README.md` | 给同事看的说明 | 交付前必须写 |

先看两个最重要的。

### `package.json`

```json [package.json]
{
  "name": "campus-activity-admin",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "engines": {
    "node": ">=20.19.0"
  },
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
    "eslint": "^10.10.0",
    "prettier": "^3.9.6",
    "vite": "^8.3.0"
  }
}
```

这里有个新手常犯的错误：**分不清 `dependencies` 和 `devDependencies`。**

| 字段 | 含义 | 放什么 |
| --- | --- | --- |
| `dependencies` | 运行时需要的包 | `vue`、`axios`、`pinia` —— 打包后要进入最终产物的 |
| `devDependencies` | 只在开发时需要的包 | `vite`、`eslint`、`prettier` —— 只在开发机上用，不进产物 |

判断方法：**把 `node_modules` 删掉、线上只部署构建产物，这个包还需要存在吗？**
不需要的，就是 `devDependencies`。

::: danger 装错位置的后果
把 `vite` 装进 `dependencies`，会让它出现在生产依赖树里。
有些云平台会根据 `dependencies` 自动安装依赖，结果线上多装了几百兆的开发工具。

用 `pnpm add <包名>` 装到 `dependencies`，用 `pnpm add -D <包名>` 装到 `devDependencies` ——
**养成用 `-D` 明确区分的习惯。**
:::

### `vite.config.js`

```js [vite.config.js]
import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      // 用 @ 指向 src，避免写 ../../../ 这种相对路径
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    port: 5173,
    open: true
  }
})
```

现在只需要理解两件事：

- `plugins: [vue()]` —— 这个插件让 Vite 能看懂 `.vue` 文件。
- `alias` 里的 `@` —— 让 `@/components/Foo.vue` 等价于 `src/components/Foo.vue`。

具体配置在[单元 2](/unit02/04-vite) 展开。

## 三条脚本命令

`package.json` 的 `scripts` 里定义了命令，用 `pnpm run <名字>` 执行。日常只用到三条：

| 命令 | 实际执行 | 什么时候用 |
| --- | --- | --- |
| `pnpm dev` | `vite` | **开发时一直开着**。启动本地服务器，改代码自动刷新 |
| `pnpm build` | `vite build` | **交付前跑一次**。把源码打包成 `dist/` 目录 |
| `pnpm preview` | `vite preview` | **本地验证构建产物**。用它检查"打包后是不是真的没问题" |

::: warning 一定要用 preview 验证一次
`pnpm dev` 用的是开发模式，很多生产环境的差异它不会暴露：路径大小写、环境变量、
代码压缩后的问题。

**最典型的例子**：开发时图片路径写 `/assets/logo.png` 没问题，打包后变成
`/assets/logo-a3f9c2.png`，如果代码里写死了前者的路径，线上就是 404。
这类问题只能用 `pnpm build && pnpm preview` 才能提前发现。
:::

三条命令都不需要自己写，脚手架已经配好。但要知道**它们背后的实际命令是什么** ——
这样才能在报错时看懂终端里那行命令在干什么。

## 哪些文件不该进 Git

`.gitignore` 决定了哪些文件不提交。脚手架生成的版本已经覆盖了主要情况：

```bash [.gitignore]
# 依赖目录：几十万个文件，绝对不能提交
node_modules/

# 构建产物：每次 build 都能重新生成
dist/
dist-ssr/

# 本地环境变量：每个人机器上可能不同
.env.local
.env.*.local

# 编辑器与系统文件
.DS_Store
.idea/

# 日志
*.log
npm-debug.log*
```

::: danger 把 node_modules 提交上去会发生什么
1. 仓库体积从 1 MB 涨到几百 MB，别人克隆要等很久。
2. 提交记录被几十万行依赖文件淹没，代码评审时找不到真正的改动。
3. **不同操作系统的依赖二进制不同**，你提交的 Windows 版本会让 macOS 的同事报错。

如果已经提交了，需要从 Git 历史里彻底删除（不只是 `git rm`），这一步比较麻烦，**一开始就别提交**。
:::

## 小结

- `index.html` 在根目录，是浏览器加载的起点；`src/` 是写代码的地方。
- `main.js` 负责组装应用，`App.vue` 是根组件，`views/` 放页面，`components/` 放复用组件。
- `assets/` 里的资源经过构建处理，`public/` 里的原样复制 —— 按"是否需要构建"来分。
- `dependencies` 是运行时依赖，`devDependencies` 是开发工具依赖，用 `-D` 明确区分。
- 三条命令：`dev` 开发、`build` 打包、`preview` 验证产物。
- `node_modules`、`dist`、本地环境变量不进 Git。

## 常见坑

::: details 坑 1：把页面写成组件塞进 `components/`
`components/` 不是"所有组件的收纳盒"。如果一个组件直接对应一个路由地址，
它应该放 `views/`。

**判断口诀：路由里出现过的，放 `views/`；被别的组件引用的，放 `components/`。**
:::

::: details 坑 2：在组件里写死接口地址
```js
// ✗ 不要这样写
const res = await axios.get('http://192.168.1.100:8080/api/activity/list')
```

三个问题：地址变了要改多个文件、换环境要全局替换、部署后可能访问不到（因为是内网地址）。

正确做法见[单元 10 的请求层封装](/unit10/04-request-layer)。
:::

::: details 坑 3：改了 `vite.config.js` 但没重启
Vite 的配置文件修改后**需要重启开发服务器**才生效（终端里 `Ctrl + C` 停掉，再 `pnpm dev`）。

有些配置热更新时会自动重载，但别名、插件这类不行。排查"配置明明改了却没生效"时，先重启。
:::

::: details 坑 4：以为 `dist/` 里的文件可以随便改
`dist/` 是构建产物，是压缩混淆过的。改它毫无意义 —— 下次 `build` 就被覆盖了。

**要改的是 `src/` 里的源文件，改完重新构建。** 如果线上有紧急问题，也不应该直接改 `dist`，
而应该走"改源码 → 重新发布"的流程。
:::

## 课后练习

::: details 练习 1：解释目录职责
不看上面的内容，说出下面每个目录的职责，并各举一个具体文件名的例子：

`src/views/`、`src/components/`、`src/assets/`、`public/`、`src/api/`、`src/stores/`

**参考思路**：重点是能举出"符合这个目录定位的具体文件"，而不是背出目录含义。
比如 `src/components/ConfirmDialog.vue`（二次确认弹窗）就比 `src/components/Foo.vue` 好。
:::

::: details 练习 2：判断依赖该放哪里
下面这些包，应该用 `pnpm add` 还是 `pnpm add -D`？逐个说明理由。

1. `element-plus`（UI 组件库）
2. `eslint`（代码检查工具）
3. `axios`（发请求的库）
4. `vitest`（单元测试框架）
5. `@vueuse/core`（组合式函数工具集）
6. `husky`（Git 提交钩子工具）

**参考思路**：判断标准只有一条 —— **代码打包之后，运行时还需要它吗？**
需要就是 `dependencies`，不需要就是 `devDependencies`。注意 `@vueuse/core` 这种很容易判断错：
它是被 import 到业务代码里的，会进入最终产物。
:::

::: details 练习 3：给项目写一份 `README.md`
假设你要把项目交给同学，写一份 `README.md`，让人能在 15 分钟内跑起来。至少包含：

- 项目是做什么的（一句话）
- 需要什么环境（Node 版本）
- 三条命令：怎么装依赖、怎么启动、怎么打包
- 遇到问题找谁

**参考思路**：写完之后**找一个人真的按你写的步骤操作一遍**，记录他在哪一步卡住。
这是[单元 12 交付材料](/unit12/04-delivery)的提前演练，也是课程评分里的硬指标之一。
:::

---

上一节：[1.1 前端是怎么走到工程化的](/unit01/01-why-engineering) ·
下一节：[1.3 学习路线与岗位方向](/unit01/03-learning-path)
