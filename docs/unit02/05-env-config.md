# 2.5 环境变量与常用配置

## 一个不得不改代码才能换环境的下午

活动列表页终于联调通了。你把接口地址写在了 `src/api/activity.js` 里：

```js [src/api/activity.js]
import axios from 'axios'

const request = axios.create({
  baseURL: 'http://192.168.1.100:8080'  // ✗ 写死的地址
})
```

下午换了教室，后端同学的 IP 变成 `192.168.1.117`，你改了。第二天要把演示版本发给老师，
老师在你电脑上跑没问题，因为连的是内网地址 —— 他那边访问不到。

这时你意识到问题不在这一行代码，而在于：**同一个项目，在不同环境下应该连不同的地址。**

那能不能像后端那样读系统环境变量？不能。前端产物是**静态文件**，
浏览器里没有“环境变量”这个概念。所以前端的环境变量必须在**构建时**就被替换成具体的值，
写进产物里。

这一节讲怎么把这件事做对。

## `.env` 文件族

Vite 会从项目根目录读取 `.env` 开头的文件，把里面的键值对注入到代码里。
文件不是随便起的，按模式（mode）区分：

| 文件 | 什么时候加载 | 要不要提交到 Git |
| --- | --- | --- |
| `.env` | 所有模式都会加载 | 提交（放通用默认值） |
| `.env.local` | 所有模式，但会被 Git 忽略 | **不提交**（放个人机器相关的值） |
| `.env.development` | `pnpm dev` 时加载 | 提交 |
| `.env.production` | `pnpm build` 时加载 | 提交（注意不要放密钥） |
| `.env.development.local` | `pnpm dev` 时加载，优先级最高 | **不提交** |
| `.env.production.local` | `pnpm build` 时加载，优先级最高 | **不提交** |

一份典型的三文件配置：

```ini [.env]
# 所有模式共用的值
VITE_APP_TITLE=校园活动服务平台
```

```ini [.env.development]
# 开发时走本地代理，避免跨域
VITE_API_BASE=/api
VITE_PROXY_TARGET=http://localhost:8080
```

```ini [.env.production]
# 生产环境直连后端域名
VITE_API_BASE=https://api.campus.example.com
```

### 加载优先级

同一个键在多个文件里出现时，谁的优先级高：

```text
.env  <  .env.local  <  .env.[mode]  <  .env.[mode].local
（低）                                            （高）
```

规则记成一句话：**越具体的文件优先级越高**。`.env.development.local`
是针对“我本机开发”这个最具体的场景，所以它说了算。

::: warning 优先级顺序最容易被搞反
常见误解是“基础文件里的值会覆盖具体的”。正好相反。

实际用法是：**`.env` 放全项目一致的默认值，`.env.development` 放开发环境要改的部分，
`.env.development.local` 放只有你自己机器需要的部分（比如后端 IP）。**

这样团队的默认配置在仓库里，个人的差异在本地，互不干扰。
:::

别忘了把本地文件加进忽略：

```bash [.gitignore]
# 本地环境变量：每个人机器上可能不同
.env.local
.env.*.local
```

## `VITE_` 前缀：不是可选项

Vite 只把**以 `VITE_` 开头**的变量注入到客户端代码里。这条规则看起来麻烦，实际上是保护。

先看一个错误的做法：

```ini [.env.development（✗ 危险）]
# ✗ 不要这样写：没有 VITE_ 前缀确实不会注入，但如果加上前缀就危险了
VITE_MAP_SECRET_KEY=xxxxxxxxxxxxxxxx
```

再看一个更危险的：

```ini [.env.production（✗ 危险）]
VITE_PAYMENT_SECRET=sk_live_xxxxxxxx
```

构建之后，产物里会有这样的代码：

```js [dist/assets/index-xxxx.js]
// 你在代码里写了 import.meta.env.VITE_PAYMENT_SECRET
// 构建后就变成了这个
const key = 'sk_live_xxxxxxxx'
```

**任何带 `VITE_` 前缀的值都会被打进产物，而产物是公开的。**
用户打开开发者工具搜一下字符串就能找到。所以：

| 内容 | 能不能放 `.env` 并加 `VITE_` 前缀 |
| --- | --- |
| 接口基础路径 | 可以 |
| 应用标题、版本号 | 可以 |
| 功能开关 | 可以 |
| 第三方地图的公开 key（有域名白名单限制） | 可以，但要确认白名单生效 |
| 支付密钥、数据库密码、管理员令牌 | **绝对不行** |
| 任何“泄露了会造成损失”的东西 | **绝对不行** |

::: danger 没有 VITE_ 前缀的变量，客户端读不到
反过来说：不带前缀的变量**不会**注入客户端，你在业务代码里
`import.meta.env.SOME_VAR` 会得到 `undefined`。

这个设计是好事：`.env` 文件里可以放一些只给 `vite.config.js` 用的变量
（比如上面那个 `VITE_PROXY_TARGET` 其实也可以写成不带前缀的，
只在配置里用 `loadEnv` 读）。

**结论：判断标准是“这个值能不能出现在用户能下载到的文件里”。**
答案是否，就不要加 `VITE_` 前缀，并且只能通过后端接口间接使用。
:::

## 在代码里怎么读

客户端代码里用 `import.meta.env`：

```js [src/api/request.js]
import axios from 'axios'

const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE,
  timeout: 10000
})
```

`import.meta.env` 里除了你定义的变量，还有一些内置的：

| 变量 | 含义 | 开发态 | 生产态 |
| --- | --- | --- | --- |
| `MODE` | 当前模式字符串 | `development` | `production` |
| `BASE_URL` | 应用部署的基础路径 | `/` | `/`（除非配了 `base`） |
| `DEV` | 是否开发态 | `true` | `false` |
| `PROD` | 是否生产态 | `false` | `true` |
| `SSR` | 是否服务端渲染 | `false` | `false` |

`MODE` 值得留意：它默认由命令决定（`dev` 对应 `development`，`build` 对应
`production`），但可以改：

```bash [终端]
# 用 production 模式跑开发服务器，读 .env.production 的值
pnpm dev --mode production

# 用 staging 模式构建，会去读 .env.staging
pnpm build --mode staging
```

第三条命令很有用：**测试环境不需要改代码，只要多一个 `.env.staging` 文件。**
这就是“同一份代码部署到多套环境”的实现方式。

::: tip 别用 DEV / PROD 判断业务逻辑
有一种常见错误：用 `import.meta.env.DEV` 判断“要不要显示调试按钮”。

它能用，但不好。因为 `PROD` 的判定依据是“是否在构建”，而不是“你连的是哪个后端”。
如果某天你要构建一个给测试同学用的版本（`--mode staging`），
`PROD` 依然是 `true`，调试按钮就没了。

**正确做法：加一个自己的变量，比如 `VITE_ENABLE_DEBUG=true`，按需配置。**
:::

## 常用配置实战

下面是一份完整的 `vite.config.js`，把这一节和后面几周会用到的配置放在一起。

```js [vite.config.js]
import { fileURLToPath, URL } from 'node:url'
import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig(({ mode }) => {
  // loadEnv 的第三个参数传 '' 表示“加载所有变量”，不加前缀限制
  const env = loadEnv(mode, process.cwd(), '')

  return {
    plugins: [vue()],

    resolve: {
      alias: {
        // 用 @ 指向 src，避免写 ../../../ 这种相对路径
        '@': fileURLToPath(new URL('./src', import.meta.url))
      }
    },

    server: {
      port: 5173,
      open: true,
      proxy: {
        // 以 /api 开头的请求转发到后端
        '/api': {
          target: env.VITE_PROXY_TARGET || 'http://localhost:8080',
          changeOrigin: true,
          // 去掉路径里的 /api 前缀，后端接口本身没有这个前缀
          rewrite: (path) => path.replace(/^\/api/, '')
        }
      }
    },

    build: {
      outDir: 'dist',
      // 小于 4 KB 的资源直接内联成 base64，减少请求数
      assetsInlineLimit: 4096,
      rollupOptions: {
        output: {
          // 手动分包：把体积大的库拆出去，不和业务代码混在一个文件里
          manualChunks: {
            'vue-vendor': ['vue', 'vue-router', 'pinia'],
            'element-plus': ['element-plus']
          }
        }
      }
    }
  }
})
```

逐块说明。

### 路径别名

```js [vite.config.js 片段]
resolve: {
  alias: {
    '@': fileURLToPath(new URL('./src', import.meta.url))
  }
}
```

配好之后，`import ActivityCard from '@/components/ActivityCard.vue'` 等价于
`import ActivityCard from './components/ActivityCard.vue'`（假设当前文件也在 `src` 下）。

为什么用 `fileURLToPath(new URL(...))` 而不是直接写 `'./src'`？因为配置文件是
ES Module，没有 `__dirname` 这个变量。这种写法在任何工作目录下执行都能算出绝对路径。

::: warning 编辑器里没有智能提示，是因为没配 jsconfig.json
Vite 只管构建，编辑器要靠另一个文件才知道别名：

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

**两处都要配，且必须一致。** 只配 Vite，编辑器里 `@/` 会标红波浪线；
只配编辑器，构建时找不到模块。
:::

### 开发代理解决跨域

跨域问题的根源是浏览器的**同源策略**：页面在 `http://localhost:5173`，
接口在 `http://localhost:8080`，端口不同就是跨域。浏览器会拦住响应。

代理的思路是**让请求看起来是同源的**：

```text [代理的工作过程]
浏览器  →  http://localhost:5173/api/activity/list   （同源，不跨域）
              ↓ Vite 开发服务器在中间转发
Vite    →  http://localhost:8080/activity/list        （服务器之间没有同源策略）
```

请求先到 Vite 开发服务器，由它转给后端。浏览器只看到自己发给了 `5173`，
于是不再拦。

关键配置只有三行：

| 配置项 | 作用 |
| --- | --- |
| `target` | 转发到哪个地址 |
| `changeOrigin: true` | 把请求头里的 `Host` 改成目标地址，后端才能正确识别 |
| `rewrite` | 改写路径，把 `/api` 前缀去掉 |

::: danger 代理只在开发态生效
`server.proxy` 只在 `pnpm dev` 时起作用。**`pnpm build` 的产物里没有代理，
`pnpm preview` 也没有。**

这意味着一件很重要的事：**用了代理之后，生产环境需要后端或运维在服务器上配同样的转发规则**，
或者让接口本身支持跨域（后端加 `Access-Control-Allow-Origin`）。

所以联调阶段就要和后端确认：**生产环境的接口地址是什么、走不走转发。**
不要等到部署那天才发现前端发出去的请求 404。
:::

### 构建输出与资源内联

| 配置项 | 作用 | 什么时候改 |
| --- | --- | --- |
| `outDir` | 产物目录，默认 `dist` | 需要和别的流程区分时改 |
| `assetsInlineLimit` | 小于这个字节数的资源内联成 base64 | 小图标多、请求数偏高时调大 |
| `emptyOutDir` | 构建前清空产物目录 | 默认在 `dist` 时会自动清空，改过 `outDir` 才需要注意 |

内联的取舍：

| 做法 | 好处 | 代价 |
| --- | --- | --- |
| 内联（base64） | 少一个请求 | 体积会变大（base64 比原文件大约 33%），且不能单独缓存 |
| 不内联（写文件） | 可单独缓存、体积小 | 多一个请求 |

一般把界线设在 4 KB 左右：小图标内联，稍大的图片走文件。

### 代码分包

默认情况下，Vite 会把所有代码打成一个文件。问题是：**`element-plus` 有几百 KB，
一个月都不改一次；而你的业务代码每天改好几遍。** 混在一起的结果是，你改一行代码，
用户就要重新下载整个包含 UI 库的大文件。

分包把不常变的部分拆出去：

```js [vite.config.js 片段]
manualChunks: {
  'vue-vendor': ['vue', 'vue-router', 'pinia'],
  'element-plus': ['element-plus']
}
```

构建输出会变成：

```text [分包后的构建输出]
dist/assets/index-Ab3dEf.js           42.10 kB │ gzip:  14.32 kB   ← 你的业务代码
dist/assets/vue-vendor-Cd4eFg.js     118.45 kB │ gzip:  45.61 kB   ← 不常变，可长期缓存
dist/assets/element-plus-Hi5jKl.js   312.78 kB │ gzip:  98.23 kB   ← 不常变，可长期缓存
```

文件名里的哈希是**根据内容算的**：内容不变，哈希就不变，浏览器直接用缓存。
于是“改业务代码”只会让用户重新下载那 42 KB，而不是 470 KB。

::: tip 分包不是越细越好
拆成 20 个 chunk 会让请求数变多，反而变慢。合理的做法是：

- **按“变更频率”拆**：框架层、UI 库层、业务代码层，三层足够。
- **顺手拆出体积大的单个库**：比如图表库、富文本编辑器，它们通常几百 KB 且不常变。

**判断依据是构建输出的体积表**，不是凭感觉。所以每次 `build` 之后都要看一眼那段输出。
:::

## 三条命令分别在什么时候用

| 命令 | 执行的模式 | 读哪些 `.env` | 什么时候用 |
| --- | --- | --- | --- |
| `pnpm dev` | development | `.env` + `.env.development` + `.local` | 开发时一直开着 |
| `pnpm build` | production | `.env` + `.env.production` + `.local` | 交付前、流水线里 |
| `pnpm preview` | 读已有产物 | 不读 | 每次 `build` 之后 |

### 为什么必须用 preview 验证产物

因为**开发态和生产态的环境变量取值不一样**。

举一个会出事的例子：

```ini [.env.development]
VITE_API_BASE=/api
```

```ini [.env.production]
VITE_API_BASE=https://api.campus.example.com
```

开发时请求发到 `/api/activity/list`，被代理转发到后端，一切正常。
构建后请求发到 `https://api.campus.example.com/activity/list` ——
如果这个域名没配好、或者后端接口路径里本来就有 `/api`，线上就是 404。

这类问题**只跑 `pnpm dev` 是发现不了的**。必须：

```bash [终端]
pnpm build
pnpm preview
```

然后在预览页面里点一遍主要功能，看请求真的发出去了、真的拿到了数据。

::: warning 一个实用的自检动作
预览页面打开后，执行一次：

```js [浏览器控制台]
console.log(import.meta.env.MODE, import.meta.env.PROD, import.meta.env.VITE_API_BASE)
```

在 `dev` 下应该打印 `development false /api`，
在 `preview` 下应该打印 `production true https://...`。

**两次输出不一样，才说明环境变量真的在起作用。** 两次一样，就说明配置没生效 ——
回去检查文件名的模式后缀对不对（`development` 不能写成 `dev`）。
:::

## 小结

- 前端的环境变量在**构建时**被替换进产物，浏览器里没有系统环境变量。
- 加载优先级：`.env` < `.env.local` < `.env.[mode]` < `.env.[mode].local`，越具体越高。
- 只有 `VITE_` 开头的变量注入客户端；**任何密钥都不能加这个前缀**。
- 客户端用 `import.meta.env` 读取，内置变量有 `MODE`、`BASE_URL`、`DEV`、`PROD`、`SSR`。
- 别名要在 `vite.config.js` 和 `jsconfig.json` 里配两处，且保持一致。
- 开发代理只在 dev 生效，生产环境要后端或运维配合。
- 分包按“变更频率”拆三层：框架、UI 库、业务代码。
- 每次 `build` 之后必须 `preview` 验证，因为环境变量取值和开发态不同。

## 常见坑

::: details 坑 1：环境变量读出来是 undefined
**现象**：`.env` 里明明写了，`import.meta.env.VITE_XXX` 却是 `undefined`。

**原因**：按可能性从高到低依次查。

1. 变量名没加 `VITE_` 前缀。
2. 改了 `.env` 但没重启开发服务器（环境变量只在启动时读一次）。
3. 文件名模式写错了，比如写成了 `.env.dev` 而不是 `.env.development`。
4. 变量名拼错了，比如 `.env` 里是 `VITE_API_BASE`，代码里写 `VITE_API_BASEURL`。

**处理**：先重启（第 2 条最常见），再逐个核对名字。核对时把两边贴在一起比：

```bash [终端]
grep VITE_ .env.development
```

**验证配置是否生效的最快方式**：在页面里 `console.log(import.meta.env)`
把整个对象打出来，看有没有你要的键。
:::

::: details 坑 2：改了 .env 不重启
**现象**：改了值，页面上还是老的。

**原因**：环境变量在开发服务器启动时被读入并写进了编译结果，运行中修改不会生效。

**处理**：`Ctrl + C` 停掉再 `pnpm dev`。

**为什么会这样**：还记得上一节讲的“开发态不打包”吗？虽然代码是按需编译的，
但 `import.meta.env` 的替换发生在**编译每一个模块时**，
已经编译过的模块不会因为 `.env` 变了就重新编译。
:::

::: details 坑 3：把代理配在生产环境里等它生效
**现象**：部署之后所有请求 404，本地一切正常。

**原因**：`server.proxy` 只属于开发服务器，产物里没有任何代理逻辑。

**处理**：三条路，按推荐顺序：

1. 生产环境由运维在 Nginx 上配同样的转发规则（最常见）。
2. 后端直接开启 CORS，前端用完整域名请求。
3. 前端和接口同域部署（前端放在后端服务的静态资源目录里）。

**这件事必须在联调阶段确认**，写进交接文档。第 12 周部署时会再讲一次。
:::

::: details 坑 4：别名在编辑器里标红，构建却正常
**现象**：`import Foo from '@/components/Foo.vue'` 下面有红色波浪线，
但 `pnpm dev` 能跑。

**原因**：编辑器读的是 `jsconfig.json`（或 `tsconfig.json`），不读 `vite.config.js`。

**处理**：在 `jsconfig.json` 里补上 `paths` 配置。**两个地方必须一致。**

**后果提醒**：标红本身不影响运行，但会掩盖真正的错误 ——
以后你写错路径时，编辑器同样不会提示，你以为没问题。
:::

::: details 坑 5：分包之后本地预览报 chunk 加载失败
**现象**：`pnpm build && pnpm preview` 之后，控制台报
`Failed to fetch dynamically imported module` 或某个 chunk 404。

**原因**：可能是构建产物目录被压缩后路径变了，或者 `preview` 启动时读的是旧的 `dist`。

**处理**：先确认构建是最新的（重新跑一次 `pnpm build`），再 `pnpm preview`。
如果只有部署到服务器才出现，检查服务器的 `base` 路径配置 ——
部署在子路径（比如 `https://example.com/admin/`）时要把 `base` 设成 `/admin/`。

**一句话**：本地预览正常但线上报 chunk 404，九成是 `base` 没配。
:::

## 课后练习

::: details 练习 1：为项目设计一套环境变量
给校园活动服务平台设计三个文件：`.env`、`.env.development`、`.env.production`。

要求：

1. 定义一个应用标题、一个接口基础路径。
2. 开发态用代理，生产态用完整域名。
3. 写一个**故意不能加 `VITE_` 前缀**的变量，并在注释里说明为什么。

**验收点**：

- 打开浏览器控制台执行 `console.log(import.meta.env)`，
  在 `dev` 和 `preview` 两种模式下输出的值不同。
- 报告里要能解释清楚“为什么有些变量客户端读不到”。

**参考思路**：不能加前缀的例子可以写一个“管理后台的演示口令”
或者“内部报表导出密钥”，说明它一旦进入产物就等于公开。
:::

::: details 练习 2：补齐别名与代理配置
在一个已有项目上完成两处配置：

1. 配上 `@` 别名，并同步配置 `jsconfig.json`。
2. 配一个 `/api` 代理，目标地址从环境变量 `VITE_PROXY_TARGET` 读，
   默认值是 `http://localhost:8080`，并去掉 `/api` 前缀。

**验收点**：

| 检查项 | 验收标准 |
| --- | --- |
| 别名 | 把某个组件的引入改成 `@/...` 形式，构建通过 |
| 编辑器 | `@/` 不标红波浪线 |
| 代理 | 在页面里请求 `/api/activity/list`，Network 面板显示状态 200 |
| 前缀重写 | 后端收到的路径不带 `/api` |

**排查提示**：代理不生效时，先确认改完 `vite.config.js` **重启了服务器**。
第二步看 Network 面板里请求的完整 URL 是什么 —— 是发到了 `5173` 还是 `8080`。
:::

::: details 练习 3：做一次产物构成分析
构建一次，把 `dist/` 里的文件按体积从大到小列出来，回答：

1. 体积最大的三个文件分别是什么？属于哪一类（框架 / UI 库 / 业务代码）？
2. 加上 `manualChunks` 之后，分包结果有什么变化？
3. 有没有哪个 chunk 体积明显偏大、值得进一步拆？

**做法**：

```bash [终端]
pnpm build
du -sh dist/assets/* | sort -h
```

**参考思路**：`element-plus` 通常是最大的一个。如果用的是按需引入，
它应该比全量引入小很多 —— 如果没变小，说明按需引入没配对。

**这份分析就是本单元产出之一“可复用的 vite.config.js”的验证材料。**
:::

::: details 练习 4：用 preview 抓一次环境变量配错
任务：故意制造一次“开发态正常、生产态出错”，然后用 `preview` 抓出来。

思路：

1. 把 `.env.production` 里的 `VITE_API_BASE` 改成一个不存在的地址。
2. `pnpm build && pnpm preview`，在预览页面里触发一次请求。
3. 观察 Network 面板里的请求地址，确认它用的是生产态的值。

**验收点**：报告里要能写出**两次请求地址的对比**：

| 模式 | 实际请求地址 |
| --- | --- |
| dev | |
| preview | |

**为什么要做这一步**：这就是“为什么必须用 preview 验证”的具体证据。
做过一次之后，你就不会再有“本地跑通就算完成”的想法了。
:::

---

上一节：[2.4 构建工具与 Vite](/unit02/04-vite) ·
下一节：[单元 2 课后练习](/unit02/practice)
