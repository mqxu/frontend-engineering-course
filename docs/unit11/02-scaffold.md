# 11.2 工程初始化与目录规划

## 从一条命令到能跑的空壳

上一节你拿到了三份清单。现在要让清单里的路由真的能访问 —— 也就是说，得先把工程建起来。

学生的常见做法是回到单元 2 那条命令：

```bash
npm create vite@latest activity-admin -- --template vue
```

跑完，装依赖，`npm run dev`，浏览器打开 `localhost:5173`，看到一个 Vite 的示例页面。然后开始删：

删掉 `HelloWorld.vue`，删掉 `style.css` 里那一大堆示例样式，删掉 `App.vue` 里的示例内容……删到一半发现 `main.js` 里 import 了一个已经不存在的文件，白屏。再改。再删。

**这个过程本身不是问题 —— 问题是删完之后，你不知道该往哪里放什么。**

所以这一节的重点不是 `create vite` 这条命令，是**目录怎么定、配置文件怎么配**。命令五分钟就敲完了，目录一旦定歪，后面每加一个模块都会更乱。

## 第一步：建工程并装齐依赖

```bash
# 1. 建工程（用 pnpm，包管理器已在单元 2 装好）
pnpm create vite activity-admin --template vue

cd activity-admin

# 2. 装基础依赖
pnpm install

# 3. 装运行时依赖
pnpm add vue-router pinia axios element-plus @element-plus/icons-vue @vueuse/core

# 4. 装开发依赖
pnpm add -D sass unplugin-auto-import unplugin-vue-components
```

::: tip 为什么单独装这几个
| 依赖 | 为什么需要 |
| --- | --- |
| `vue-router` | 三个路由以上就该用路由，这个项目有十几个页面 |
| `pinia` | 登录用户信息、全局通知这些状态要跨页面共享 |
| `axios` | 请求层封装（单元 10 讲过），比 `fetch` 多了拦截器和超时 |
| `element-plus` | 后台项目的表格、表单、弹窗、日期选择器都是高频组件，自己写不现实 |
| `@vueuse/core` | 用它的 `useDebounceFn`、`useLocalStorage`、`useEventListener`，省掉一批手写工具函数 |
| `sass` | 用嵌套语法写布局样式，可读性比纯 CSS 好 |
| `unplugin-auto-import` / `unplugin-vue-components` | Element Plus 按需引入，不用每页手写 import |

版本统一按课程的基线来：**Vue 3.5.42 / Vite 8.3.0 / Vue Router 5.3.1 / Pinia 4.0.3 / axios 1.20.0 / Element Plus 2.14.5**，完整清单见[工具链与版本清单](/appendix/tools)。

**不要在这时候去装 ESLint、Prettier、husky。** 那些是单元 3 的内容，工程跑起来之后再补，顺序反了会在配 lint 报错时分不清是自己写错了还是工具没配对。
:::

## 第二步：定目录 —— 一次定好，后面不改

`create vite` 生成的 `src` 里只有 `App.vue`、`main.js`、`style.css`。你要把它扩成一个能装十几个页面的结构：

```
src/
├── api/                    # 接口层：每个模块一个文件
│   ├── request.js          # axios 实例 + 拦截器
│   ├── activity.js
│   ├── signup.js
│   ├── session.js
│   └── auth.js
├── assets/                 # 会被构建处理的静态资源
│   └── styles/
│       ├── variables.scss  # 颜色、间距变量
│       └── index.scss      # 全局样式
├── components/             # 全局通用组件（跨模块复用）
│   ├── AppTable.vue
│   ├── AppPagination.vue
│   ├── StateWrapper.vue    # 四态包装组件
│   └── StatusTag.vue       # 状态标签
├── composables/            # 组合式函数
│   ├── useTable.js         # 列表页通用逻辑
│   ├── useForm.js
│   └── usePermission.js
├── layouts/                # 布局组件
│   └── AdminLayout.vue
├── router/
│   ├── index.js
│   └── routes.js           # 路由表单独一个文件
├── stores/                 # Pinia
│   ├── user.js
│   └── notify.js
├── utils/
│   ├── format.js           # 时间、状态文案格式化
│   └── validate.js         # 自定义校验规则
├── views/                  # 页面，按模块分子目录
│   ├── login/
│   │   └── LoginView.vue
│   ├── dashboard/
│   │   └── DashboardView.vue
│   ├── activity/
│   │   ├── ActivityList.vue
│   │   ├── ActivityDetail.vue
│   │   ├── ActivityForm.vue
│   │   └── components/     # 只属于这个模块的组件
│   │       └── ActivityStatusTag.vue
│   ├── signup/
│   ├── session/
│   └── venue/
├── App.vue
└── main.js
```

这个结构里，有三条规则必须记住。

### 规则一：`views` 和 `components` 的分界是“复用范围”

| 目录 | 放什么 | 判断标准 |
| --- | --- | --- |
| `src/components/` | 通用组件 | **两个以上模块会用** |
| `src/views/xxx/components/` | 模块私有组件 | **只有这个模块会用** |
| `src/views/xxx/` 下的 `XxxList.vue` 等 | 页面组件 | 直接挂到路由上 |

具体到这个项目：

- `StatusTag.vue` 放 `src/components/` —— 活动状态、报名状态、场次状态都要用，只是状态字典不同，做成 props 传入。
- `ActivityFormSteps.vue`（如果做了分步表单）放 `src/views/activity/components/` —— 只有活动表单会用。

**判断错了后果不严重，搬一次就好。** 但反过来，养成“先想复用范围再决定放哪”的习惯，能避免 `src/components` 最后变成几十个文件的杂物间。

### 规则二：`api` 按模块分文件，不要一个文件写到底

```js [src/api/activity.js]
import request from './request'

export function getActivityList(params) {
  return request.get('/activities', { params })
}

export function getActivityDetail(id) {
  return request.get(`/activities/${id}`)
}

export function createActivity(data) {
  return request.post('/activities', data)
}

export function updateActivity(id, data) {
  return request.put(`/activities/${id}`, data)
}

export function setActivityOffShelf(id, offShelf) {
  return request.patch(`/activities/${id}/offshelf`, { offShelf })
}
```

**接口函数只做一件事：拼路径、传参数、返回 Promise。** 不要在这里做数据处理、不要在这里弹提示、不要在这里判断状态码 —— 那些是拦截器和调用方的事。

这样写的好处是：后端改了路径，你只改这一个文件；想知道项目调了哪些接口，翻 `api/` 目录就够了。

### 规则三：`views` 按业务模块分，不按类型分

不要这样：

```
views/
├── list/
│   ├── ActivityList.vue
│   ├── SignupList.vue
│   └── VenueList.vue
└── form/
    ├── ActivityForm.vue
    └── VenueForm.vue
```

看起来整齐，但一改“活动”功能，你要在 `list/` 和 `form/` 两个目录之间来回跳。而且 `list/` 到第十五章会挤满文件。

按模块分，一个模块的所有东西在一起：

```
views/activity/
├── ActivityList.vue
├── ActivityDetail.vue
├── ActivityForm.vue
└── components/
```

**改需求时只在一个目录里工作。** 这才是目录结构要解决的问题。

## 第三步：配别名与按需引入

`../../../components/AppTable.vue` 这种路径，数层级会数错，移动文件会失效。配一个别名：

```js [vite.config.js]
import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'

export default defineConfig({
  plugins: [
    vue(),
    // 自动引入 Vue、Vue Router、Pinia 的 API，不用每页手写 import
    AutoImport({
      imports: ['vue', 'vue-router', 'pinia'],
      resolvers: [ElementPlusResolver()],
      dts: 'src/auto-imports.d.ts'
    }),
    // 自动引入 Element Plus 组件与项目内 components 目录下的组件
    Components({
      dirs: ['src/components'],
      resolvers: [ElementPlusResolver()],
      dts: 'src/components.d.ts'
    })
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    port: 5173,
    open: true
  }
})
```

配完之后：

```js
// ✓ 别名 + 自动引入
import { getActivityList } from '@/api/activity'

const list = ref([])                    // ref 自动引入，不用 import
const router = useRouter()              // useRouter 自动引入
const listRef = ref(null)               // ElTable 在模板里直接用 <el-table>，不用 import
```

::: warning `dirs: ['src/components']` 这一行有个副作用
配了它之后，`src/components/` 下的组件**不需要 import 就能在模板里用**。听起来方便，但有个坑：

**组件名冲突时不会有任何提示。** 你在 `views/activity/` 下建了一个 `AppTable.vue`，模板里写 `<AppTable />`，实际渲染的是 `src/components/AppTable.vue` —— 你改的那个文件根本不生效，能排查半天。

**建议**：`dirs` 只配 `src/components`，模块私有组件放 `views/xxx/components/`（不在扫描范围内），需要时老老实实 import。**这样至少能保证“哪里写错了，一眼能看出来”。**
:::

接着配路径别名让编辑器也能识别：

```json [jsconfig.json]
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    }
  },
  "exclude": ["node_modules", "dist"]
}
```

VSCode 装上项目根目录的 `jsconfig.json` 之后，写 `@/` 会有路径提示，`Ctrl + 点击`也能跳转。

## 第四步：环境变量

开发时接口地址是 `http://localhost:8080`，上线后是真实域名。这类“随环境变化的值”放环境变量：

```bash [.env.development]
VITE_API_BASE_URL=/api
VITE_APP_TITLE=校园活动服务平台
```

```bash [.env.production]
VITE_API_BASE_URL=https://api.campus-activity.example.com
VITE_APP_TITLE=校园活动服务平台
```

**规则一：只有 `VITE_` 开头的变量才会暴露给前端代码。** 这是 Vite 的保护机制 —— 不加前缀的变量只能给配置文件用，前端代码读不到。

```js
// ✓ 能读到
console.log(import.meta.env.VITE_API_BASE_URL)

// ✗ 读不到，是 undefined
console.log(import.meta.env.DB_PASSWORD)
```

**规则二：环境变量里的值都是字符串。** `VITE_PORT=5173` 读到的是 `"5173"`，要当数字用必须转：

```js
// ✗ 字符串比较，可能出错
if (import.meta.env.VITE_PORT === 5173) { }

// ✓
if (Number(import.meta.env.VITE_PORT) === 5173) { }
```

**规则三：`VITE_` 开头的变量会被打包进产物，任何人都能看到。** 所以密钥、token、密码**绝对不能**放这里。前端没有秘密 —— 这一点在[9.4 登录鉴权完整链路](/unit09/04-auth-flow)里讲过，这里再强调一次。

开发环境的 `/api` 前缀要配代理转发到后端：

```js [vite.config.js]
export default defineConfig({
  // ...上面的配置
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true
        // 不需要 rewrite，后端接口本身就以 /api 开头
      }
    }
  }
})
```

::: details 为什么开发环境用代理，不直接写后端地址
**直接写 `http://localhost:8080`** 会遇到跨域：你的页面在 `5173`，接口在 `8080`，浏览器判定为跨域，请求被拦。要么让后端配 CORS，要么前端绕过去。

**用代理**：页面请求 `/api/activities`（同源，不带端口差异），Vite 开发服务器收到后转发给 `localhost:8080`。浏览器全程以为在跟 `5173` 说话，没有跨域问题。

**关键点**：代理只在开发服务器生效。打完包部署出去，代理就不存在了，所以生产环境的 `VITE_API_BASE_URL` 必须是后端真实地址（或者由 Nginx 做转发）。**这就是为什么接口地址要放环境变量，而不是写死在代码里。**
:::

## 第五步：`main.js` 与 `App.vue`

现在把装好的东西挂上去：

```js [src/main.js]
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import 'element-plus/dist/index.css'

import App from './App.vue'
import router from './router'
import '@/assets/styles/index.scss'

const app = createApp(App)

app.use(createPinia())
app.use(router)
// 中文语言包：日期选择器、分页器这些内置组件的文案才会是中文
app.use(ElementPlus, { locale: zhCn })

app.mount('#app')
```

```vue [src/App.vue]
<template>
  <RouterView />
</template>
```

**`App.vue` 里只放一个 `<RouterView />`。** 布局、侧边栏、顶栏都不在这里写 —— 它们是 `AdminLayout.vue` 的事，而 `AdminLayout` 是路由表里的一个组件，只包住需要登录的后台页面。登录页不该有侧边栏，就是这个设计的直接结果。

::: details 为什么 Element Plus 用了完整引入，又装了按需引入插件
两处不冲突，但**这个项目里最好只选一种**。

**完整引入**（上面的写法 `import ElementPlus from 'element-plus'` + `import 'element-plus/dist/index.css'`）：

- 好处：写起来最简单，不会出现“组件样式没加载”的怪问题。
- 代价：产物里包含了全部组件和全部样式，打包后大约多出几百 KB。

**按需引入**（只配 `unplugin-vue-components`，不写那两行 import）：

- 好处：只有用到的组件进产物，首屏体积明显小。
- 代价：偶尔会遇到“JS 进来了但 CSS 没进来”的样式错乱，需要手动 `import 'element-plus/theme-chalk/el-message.css'` 之类补上。

**课程项目的建议**：开发阶段用完整引入，**能跑通优先**；到[12.2 构建优化](/unit12/02-build-optimize)时再切换成按需引入，然后对比两次的产物体积 —— 这个对比本身就是一个很有说服力的实验数据，答辩时用得上。
:::

## 第六步：验证骨架

到这一步，工程应该能跑起来了：

```bash
pnpm dev
```

打开 `http://localhost:5173`，看到的就是 `App.vue` 里的空 `<RouterView />` —— 一片空白，控制台可能有“No match found for location with path "/"”的警告。

**这是对的。** 因为你还没写路由表（下一节 11.3 的内容）。**这个空白页面是本节的合格标志**：说明工程建起来了、依赖装齐了、样式加载了、别名能解析了。

如果白屏且控制台报错，按下面的顺序排查：

| 报错信息 | 原因 | 怎么改 |
| --- | --- | --- |
| `Failed to resolve import "@/..."` | 别名没配或 `jsconfig.json` 没生效 | 检查 `vite.config.js` 的 `resolve.alias`，重启开发服务器 |
| `Cannot find module 'element-plus'` | 依赖没装成 | `pnpm install` 重跑，检查 `package.json` 里有没有 |
| `[plugin:vite:css] ...` | sass 语法错误 | 检查 `.scss` 文件的括号与嵌套 |
| 页面全白且无报错 | `index.html` 里 `#app` 被改了 | 确认 `<div id="app"></div>` 还在 |
| `EADDRINUSE` | 5173 端口被占 | 关掉上一个 `pnpm dev`，或改 `server.port` |

## 目录规划的检查清单

建完之后对着这份清单过一遍，**每一项都应该是“是”**：

| 检查项 | 是 / 否 |
| --- | --- |
| 打开 `src/`，能在三秒内说出每个目录装什么 | |
| `views/` 下按业务模块分了子目录，不是按 list / form 分 | |
| `api/` 下每个业务模块一个文件 | |
| `vite.config.js` 里配了 `@` 别名 | |
| 代码里搜 `../../`，找不到任何三级以上的相对路径 | |
| `.env.development` 里的变量都以 `VITE_` 开头 | |
| 没有任何密钥、token 写进 `VITE_` 变量 | |
| `App.vue` 里只有一个 `<RouterView />` | |
| `git status` 里没有 `node_modules` 和 `dist` | |

最后一项需要 `.gitignore`：

```bash [.gitignore]
node_modules
dist
dist-ssr
*.local
.DS_Store
.vscode/*
!.vscode/extensions.json

# 自动生成的类型声明文件，各人本地重新生成即可
src/auto-imports.d.ts
src/components.d.ts
```

::: warning 两个 `.d.ts` 文件为什么要忽略
`auto-imports.d.ts` 和 `components.d.ts` 是插件自动生成的，内容依赖你本地装了什么组件、什么版本。**团队协作时它们每个人的都不一样**，提交上去会导致无意义的冲突。

但注意：**忽略之后，新克隆项目的人第一次打开编辑器会有大量“找不到 ref”的报错。** 解决办法是在 README 里写明：克隆后先跑一次 `pnpm dev`，插件会自动生成这两个文件。

这种情况在真实项目里很常见 —— **凡是自动生成的东西都不该提交，但要在文档里说清怎么生成。**
:::

## 小结

- **建工程只要五分钟，定目录要想清楚。** 目录定歪的代价是每加一个模块都更乱。
- **三条目录规则**：`components` 与 `views/xxx/components` 按复用范围分；`api` 按模块分文件；`views` 按业务模块分。
- **接口函数只做拼路径和传参。** 数据处理、提示、状态判断都放到别处。
- **别名 `@` 是必需品**，配上 `jsconfig.json` 让编辑器也能识别。
- **环境变量三规则**：只有 `VITE_` 前缀暴露给前端；值都是字符串；`VITE_` 变量会进产物，不能放密钥。
- **开发环境用代理解决跨域**，生产环境要另配地址，所以接口地址必须放环境变量。
- **`App.vue` 只放 `<RouterView />`**，布局是路由表里组件的事。
- **自动生成的文件不提交，但要在 README 里说清怎么生成。**

## 常见坑

::: details 装完依赖，`pnpm dev` 报“找不到 vite 命令”
**现象**：`pnpm install` 显示成功，紧接着 `pnpm dev` 报 `vite: command not found`。

**原因**：多半是 `pnpm install` 中途被中断（网络波动），`node_modules` 装了一半。

**怎么处理**：删掉 `node_modules` 重装。

```bash
rm -rf node_modules
pnpm install
```

如果反复失败，先清缓存再装：`pnpm store prune && pnpm install`。**不要在失败状态下反复 `pnpm add` 试图修好**，只会让依赖树更乱。
:::

::: details 别名配了，编辑器还是标红
**现象**：`import x from '@/api/activity'` 运行正常，但编辑器里有一条红色波浪线，`Ctrl + 点击`跳不过去。

**原因**：Vite 的 `resolve.alias` 只影响构建（运行时），编辑器的提示来自 `jsconfig.json` 或 `tsconfig.json`。

**怎么处理**：确认项目根目录有 `jsconfig.json`，并且 `paths` 里配了 `"@/*": ["src/*"]`。改完之后**重启 VSCode**（不是重启开发服务器）才生效。
:::

::: details Element Plus 组件出来了，但样式全乱
**现象**：`<el-button>` 渲染出来了，但看不出是按钮的样子。

**原因**：用了按需引入但漏了样式，或者完整引入时漏了 `import 'element-plus/dist/index.css'`。

**怎么处理**：两种模式不要混用。**混用是最难排查的** —— 按需插件引入了组件的 JS，样式由 `unplugin-vue-components` 的 resolver 处理，你再手动 import 一遍全量 CSS，可能出现样式覆盖顺序不一致。

课程项目统一用**完整引入**到 12.2 再切按需，切换时把 `main.js` 里那两行 import 删干净。
:::

::: details 环境变量改了不生效
**现象**：`.env.development` 里把接口地址改了，代码里读到的还是旧值。

**原因**：Vite 在启动时读取环境变量并注入，**运行期间不会重新读取**。

**怎么处理**：改完 `.env*` 文件必须重启 `pnpm dev`。另外确认文件名正确 —— 是 `.env.development` 不是 `.env.dev`，Vite 只认 `development` / `production` 这两种。
:::

::: details 提交后发现仓库里有 node_modules
**现象**：第一次 `git push` 跑了很久，发现推上去几万个文件。

**原因**：`.gitignore` 写晚了，或者在 `git init` 之前就已经有 `node_modules`。

**怎么处理**：从 Git 索引里移除但保留本地文件：

```bash
# 先从索引里移除
git rm -r --cached node_modules
git rm -r --cached dist

# 然后提交 .gitignore
git add .gitignore
git commit -m "chore: 补上 .gitignore"
```

**注意 `--cached` 不能漏**，漏了会把本地文件也删掉，只能重新装依赖。
:::

## 课后练习

::: details 练习 1：把目录结构图补全，并说明每个目录的职责
照着这一节的目录树，为你的项目写一份 `STRUCTURE.md`，逐个目录写明三件事：放什么、不放什么、什么情况下该新建文件。

**思路提示**：

- “不放什么”比“放什么”更有用。比如 `api/` 不放工具函数，`utils/` 不放组件。
- 最后再写一段“这个结构在什么情况下会不够用”—— 比如模块超过 15 个、或者需要拆成微前端时该怎么调整。这一段能看出你是不是真的想过，还是在抄目录树。
:::

::: details 练习 2：给“报名审核”模块规划目录
用同一套规则，写出“报名审核”模块需要哪些文件和目录，每个文件放什么。

**思路提示**：

- 报名审核模块要操作报名记录，也要读活动信息。想清楚：报名列表里要显示活动标题，这个数据是列表接口直接返回，还是前端再查一次活动详情？
- 如果接口直接返回，前端就不用碰 `api/activity.js`；如果前端再查，就要处理好“一页 20 条报名，要查 20 次活动详情”的问题（提示：应该用批量接口，或者让后端直接带出来）。
- 把这个判断写进你的文档里。
:::

::: details 练习 3：亲手验证一次跨域
把 `vite.config.js` 里的 `proxy` 配置注释掉，把 `VITE_API_BASE_URL` 改成后端的真实地址（`http://localhost:8080`），然后请求一次接口，看控制台报什么错。

**思路提示**：

- 报错信息里会有 `CORS`、`Access-Control-Allow-Origin` 这两个关键词，把它记下来。
- 然后再把配置改回来，确认请求恢复正常。
- **这个实验的意义是**：以后遇到跨域，你能一眼认出来，而不是去搜索“为什么请求失败”。
- 如果本地没有后端服务，可以用 `json-server` 起一个假接口，或者直接用一个公开的测试接口做实验。
:::

---

上一节：[11.1 从需求到页面清单](/unit11/01-requirements) · 下一节：[11.3 布局骨架与嵌套路由](/unit11/03-layout)
