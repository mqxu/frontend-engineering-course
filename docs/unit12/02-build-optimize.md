# 12.2 构建优化

## 先看一个真实的数字

功能都调通了，跑一次打包：

```bash
pnpm build
```

终端输出：

```
dist/index.html                     0.85 kB
dist/assets/index-a1b2c3d4.css      1.24 kB
dist/assets/element-plus-e5f6g7h8.js  1,082.36 kB
dist/assets/vue-i9j0k1l2.js         234.51 kB
dist/assets/index-m3n4o5p6.js       186.72 kB

✓ built in 12.34s

(!) Some chunks are larger than 500 kB after minification.
Consider using dynamic import() to code-split the application.
```

**1 MB 的 Element Plus。** 用户的浏览器要下载这 1 MB 才能看到第一个像素。用 4G 网络大概要 3 秒，用校园网慢一点要 8 秒。

这一节要做的事：**把首屏需要下载的体积降下来，同时让用户更快看到内容。**

## 优化前的准备：先测，再改

优化的第一步不是改代码，是**建立基线**。不知道改之前是多少，改完也说不清有没有用。

### 测三件事

| 指标 | 怎么测 | 关注什么 |
| --- | --- | --- |
| 产物体积 | `pnpm build` 的终端输出，或者 `du -sh dist` | 总量和最大的几个文件 |
| 首屏实际加载量 | 构建后 `pnpm preview`，开发者工具 Network 面板，勾上 Disable cache，硬刷新 | 首屏加载了多少 KB、几个请求 |
| 首屏时间 | Network 面板底部的时间，或者 Lighthouse 的 FCP / LCP | 用户多久看到内容 |

**“产物体积”和“首屏加载量”是两回事。** `dist` 总共 1.5 MB，但首屏可能只加载 900 KB —— 剩下的靠路由懒加载，用户点到那个页面才下载。

**优化的目标是首屏加载量，不是 dist 总量。** 有些同学把 dist 从 1.5 MB 压到 1.2 MB，但首屏一点没变，因为压下去的都是懒加载的 chunk。

### 用一个可视化工具看产物

终端输出不够直观。装一个分析插件：

```bash
pnpm add -D rollup-plugin-visualizer
```

```js [vite.config.js]
import { visualizer } from 'rollup-plugin-visualizer'

export default defineConfig({
  plugins: [
    vue(),
    // ...其他插件
    visualizer({
      open: true,               // 构建完自动打开浏览器
      filename: 'dist/stats.html',
      gzipSize: true,           // 显示 gzip 后的体积
      brotliSize: true
    })
  ]
})
```

跑 `pnpm build`，浏览器会自动打开一张方块图。**方块面积代表体积，一眼能看出谁最大。**

这个图会告诉你几件事：

- Element Plus 占了多少（通常是最大的那一块）
- 有没有重复打包的依赖（同一个库出现两次，通常是版本冲突）
- 有没有把巨大的库打进首屏（比如整个 `lodash`、整个 `moment`）

::: tip gzip 后的体积才是用户实际下载的量
严格来说，`stats.html` 里显示的“体积”有三种：

| 列 | 含义 |
| --- | --- |
| Stat | 原始字节数 |
| Parsed | 源文件大小 |
| Gzip / Brotli | 压缩后的大小 |

**用户实际下载的是 Gzip 或 Brotli 后的量**（服务器开启压缩的前提下）。JavaScript 和 CSS 的文本压缩率通常在 70% 左右 —— 1 MB 的 JS 压缩后大概 300 KB。

所以看到“Element Plus 1 MB”不要慌，先看 Gzip 那一列。**但压不压缩都要优化** —— 300 KB 也不小。
:::

## 优化一：路由懒加载

这是投入产出比最高的一项，**改动最小，效果最明显**。

```js [src/router/routes.js]
// ✗ 全部静态导入：所有页面都进首屏的包
import ActivityList from '@/views/activity/ActivityList.vue'
import SignupList from '@/views/signup/SignupList.vue'
import SessionList from '@/views/session/SessionList.vue'
// ...十几个页面

// ✓ 路由懒加载：进到那个路由才下载
const routes = [
  {
    path: '/',
    component: () => import('@/layouts/AdminLayout.vue'),
    children: [
      {
        path: 'activity',
        component: () => import('@/views/activity/ActivityList.vue')
      }
    ]
  }
]
```

**原理**：`() => import('...')` 是一个动态导入。Vite（更准确地说，底层的 Rollup）看到它，会把那个模块**单独打成一个 chunk**，只有在真正导航到那个路由时才去请求这个文件。

**改动成本**：几乎为零。把所有路由的 `component` 从静态 import 改成箭头函数返回 `import()`。**这件事应该在写路由表的时候就做，不要等到优化阶段。**

来看效果。一个十五个页面的后台项目：

| 方案 | 首屏 JS | 首次访问 | 进入活动列表 |
| --- | --- | --- | --- |
| 全部静态导入 | 约 1.4 MB | 下载 1.4 MB | 无需额外下载 |
| 路由懒加载 | 约 320 KB | 下载 320 KB | 额外下载约 24 KB |

**首屏从 1.4 MB 降到 320 KB。** 代价是第一次进某个模块多一次请求，但那个请求只有几十 KB，比 1 MB 快得多。

::: details 懒加载之后，打包体积反而变大的情况
有时候把懒加载加上，发现 `dist` 总大小变大了几百 KB。

**原因**：公共代码被重复打包了。每个懒加载的 chunk 里都包含了一份它用到的公共模块。

**解决办法**：用 `manualChunks` 把公共依赖抽出来（下面会讲）。**这是懒加载的必要配套，不是可选项。**

另一种情况是 Vite 的预加载指令（`<link rel="modulepreload">`）会自动加上，让浏览器提前下载。**这是好事** —— 它让懒加载的体验接近静态导入，因为浏览器在空闲时会预取。

控制它的开关：

```js
// vite.config.js
export default defineConfig({
  build: {
    modulePreload: {
      polyfill: false,        // 现代浏览器不需要 polyfill
      resolveDependencies: (filename, deps) => deps
    }
  }
})
```
:::

## 优化二：Element Plus 按需引入

回顾 [11.2](/unit11/02-scaffold) 里用的是完整引入：

```js
// main.js
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'     // ← 全部组件的样式
```

**这两个 import 把整个组件库都装进了首屏。** 改成按需引入：

```js [src/main.js]
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import '@/assets/styles/index.scss'
// ⚠️ 删掉 ElementPlus 和它的全量 CSS

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
```

样式交给 `vite.config.js` 里已配好的 `unplugin-vue-components` + `ElementPlusResolver`：

```js [vite.config.js]
Components({
  dts: 'src/components.d.ts',
  resolvers: [ElementPlusResolver()]
}),
AutoImport({
  imports: ['vue', 'vue-router', 'pinia'],
  resolvers: [ElementPlusResolver()],
  dts: 'src/auto-imports.d.ts'
})
```

**模板里继续直接写 `<el-table>`，不用手写 import。** 插件在编译时扫描模板，只把用到的组件引入进来。

效果：

| 方案 | Element Plus 部分（gzip 后） |
| --- | --- |
| 完整引入 | 约 330 KB |
| 按需引入（只用到十几个组件） | 约 90 KB |

::: warning 按需引入会踩的三个坑
**坑一：`ElMessage`、`ElMessageBox` 这类“服务式”组件不会被自动引入。**

它们不是在模板里用的，是 `import { ElMessage } from 'element-plus'` 在脚本里调的。`unplugin-vue-components` 只处理模板，管不到脚本。

`unplugin-auto-import` 的 resolver 会处理它们，但要确认 `AutoImport` 里配了 `ElementPlusResolver()`。

**坑二：函数式组件的样式可能没进来。**

`ElMessage`、`ElLoading`、`ElNotification` 这些的样式是独立的 CSS 文件。如果发现提示框出来了但没样式，手动加一行：

```js [src/main.js]
import 'element-plus/theme-chalk/el-message.css'
import 'element-plus/theme-chalk/el-message-box.css'
import 'element-plus/theme-chalk/el-loading.css'
```

**坑三：`el-icon` 里的图标组件不能自动引入。**

`@element-plus/icons-vue` 的图标是独立包，要单独处理：

```js [vite.config.js]
Components({
  resolvers: [
    ElementPlusResolver(),
    // 图标也要配
    IconsResolver({ prefix: 'Icon' })
  ]
})
```

**或者更简单**：手动把用到的图标引入并全局注册：

```js
// 只引入用到的那几个，不要 import * as Icons
import { Plus, Search, Refresh, Delete, Edit } from '@element-plus/icons-vue'

const icons = { Plus, Search, Refresh, Delete, Edit }
Object.entries(icons).forEach(([name, comp]) => app.component(name, comp))
```

**千万不要 `import * as Icons from '@element-plus/icons-vue'` 然后循环注册全部图标** —— 那会把 2000 多个图标全打进产物，比完整引入组件库还大。
:::

## 优化三：分包（manualChunks）

不做分包的时候，所有 `node_modules` 里的依赖会被打进同一个 vendor chunk。问题是：**你改了一行业务代码，整个 vendor 的哈希也变了，用户要重新下载全部依赖。**

分包的目标是**让不常变的东西单独成块**。

```js [vite.config.js]
export default defineConfig({
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          // Vue 全家桶：版本升级前不会变
          'vue-vendor': ['vue', 'vue-router', 'pinia'],
          // Element Plus：独立成块，它最大
          'element-plus': ['element-plus', '@element-plus/icons-vue'],
          // 其他工具库
          'utils-vendor': ['axios', '@vueuse/core']
        }
      }
    }
  }
})
```

分包之后的效果：

| chunk | 什么时候变 |
| --- | --- |
| `vue-vendor` | Vue 版本升级时 |
| `element-plus` | 组件库升级时 |
| `utils-vendor` | 工具库升级时 |
| `index` | **每次改业务代码都变，但它很小** |

**用户第二次访问时，只有 `index` 需要重新下载。** 这就是分包的价值 —— 它不减少首次加载量，而是减少**后续访问**的加载量。

::: details 分包分得太细反而更慢
把每个依赖都拆成一个 chunk，会产生几十个小文件。HTTP/1.1 下每个文件都要一次请求，请求数太多会拖慢加载。

**合理的 chunk 数量是 3 到 6 个。**

**分包策略：**

| 策略 | 怎么做 | 适用 |
| --- | --- | --- |
| 按依赖分组 | 手动配 `manualChunks` 对象 | 依赖稳定、结构清晰的项目 |
| 按大小 | 用函数判断，超过阈值的单独成块 | 依赖多、不好手动分组 |
| 不手动分 | 让 Rollup 自动处理 | 小项目 |

按大小自动分：

```js
manualChunks(id) {
  if (!id.includes('node_modules')) return
  // 大库单独成块
  if (id.includes('element-plus')) return 'element-plus'
  if (id.includes('echarts')) return 'echarts'
  // 其余的合成一个
  return 'vendor'
}
```

**注意 `manualChunks` 用对象和用函数不能同时存在。** 二选一。

**还有一个坑**：`manualChunks` 里引用的包名必须和 `package.json` 里的一致。如果你写了 `'vue'` 但实际装的是 `@vue/runtime-dom` 的传递依赖，可能不生效。**验证方法：打包后看 `dist/assets/` 下有没有你预期的文件名。**
:::

## 优化四：开启 gzip / brotli 压缩

前三项是“少传”，这一项是“压小”。

压缩有两种做法：

| 做法 | 在哪压 | 什么时候压 |
| --- | --- | --- |
| 构建时预压缩 | 本地打包时生成 `.gz` 文件 | 构建时 |
| 服务端实时压缩 | Nginx 收到请求时压缩 | 每次请求 |

**推荐服务端实时压缩** —— 不用管理额外的文件，配置几行就行。Nginx 的配置见 [12.3 部署上线](/unit12/03-deploy)。

**如果部署到静态托管平台**（Vercel / Netlify / Cloudflare Pages），它们默认就开了 gzip 或 brotli，不用管。

**如果只能传静态文件**（比如某些学校的服务器不允许改 Nginx 配置），就用构建时预压缩：

```bash
pnpm add -D vite-plugin-compression
```

```js [vite.config.js]
import compression from 'vite-plugin-compression'

export default defineConfig({
  plugins: [
    vue(),
    // 同时生成 .gz 和 .br
    compression({ algorithm: 'gzip', threshold: 10240 }),     // 超过 10 KB 才压
    compression({ algorithm: 'brotliCompress', ext: '.br', threshold: 10240 })
  ]
})
```

打包后 `dist/assets/` 下会同时有 `index-xxx.js` 和 `index-xxx.js.gz`。**需要服务器配置“优先返回 .gz 文件”**，否则生成了也没人用。

::: warning 预压缩有个常见误解
有同学以为生成了 `.gz` 文件，用户下载的就是压缩版了。**不是。** 服务器必须配置 `gzip_static on;`（Nginx）才会优先发送 `.gz` 文件。

**没有对应配置的话，`.gz` 文件只是白占磁盘空间。**

**判断方法**：部署后打开 Network 面板，看响应头里有没有 `Content-Encoding: gzip`。没有就说明压缩没生效。
:::

## 优化五：图片与静态资源

图片经常是被忽略的大头。三种处理：

**一、小图转成 base64 内联。**

Vite 默认把小于 4 KB 的资源内联成 base64。**好处是少一次请求，代价是体积增大约 33%**（base64 编码的开销）。

```js
build: {
  assetsInlineLimit: 4096   // 默认值，小于 4 KB 内联
}
```

**不要把 `assetsInlineLimit` 调大。** 内联 20 KB 的图片会让 JS 体积涨 27 KB，还得跟首屏一起下载 —— 不划算。

**二、大图压缩，并用现代格式。**

| 格式 | 相对 PNG | 相对 JPG |
| --- | --- | --- |
| WebP | 小 25% - 35% | 小 25% - 35% |
| AVIF | 小 50% 左右 | 小 40% 左右 |

**转换工具**：`squoosh.app`（在线，不用装东西）、`sharp`（Node 库）。

**三、加上尺寸和加载属性。**

```vue
<img
  src="@/assets/banner.webp"
  alt="2026 春季校园歌手大赛"
  width="800"
  height="320"
  loading="lazy"
/>
```

| 属性 | 作用 |
| --- | --- |
| `width` / `height` | 预留位置，避免图片加载完后页面跳动（这叫 CLS，累积布局偏移） |
| `loading="lazy"` | 图片进入视口才加载，首屏之外的图片不占带宽 |
| `alt` | 图片加载失败时的替代文字，也是无障碍要求 |

**注意：首屏第一屏的图片不要加 `loading="lazy"`** —— 它本来就该立刻加载，加了反而延迟。

## 优化六：去掉不必要的东西

有些体积是“写代码时不小心带进来的”。

| 问题 | 怎么发现 | 怎么改 |
| --- | --- | --- |
| 整个库只用了几个函数 | 分析图里某个库方块很大 | 按需引入，或换成更小的替代品 |
| 引入了两套日期库 | 分析图里同时有 `moment` 和 `dayjs` | 统一成一个 |
| 图标全部打包 | 分析图里 `@element-plus/icons-vue` 很大 | 只引入用到的 |
| 生产环境带了开发警告 | 产物里有 `Warning:` 字样 | 正常，Vue 的生产构建会自动去掉 |
| 打了 `console.log` | 产物里搜到 `console.log` | 构建时移除 |

移除 `console.log`：

```js [vite.config.js]
export default defineConfig({
  esbuild: {
    drop: ['console', 'debugger']   // 生产构建时移除
  }
})
```

**注意这会在所有环境生效。** 想只在生产移除：

```js
export default defineConfig(({ mode }) => ({
  esbuild: {
    drop: mode === 'production' ? ['console', 'debugger'] : []
  }
}))
```

::: details 几个常见库的轻量替代
| 重库 | 轻量替代 | 体积对比（gzip 后） |
| --- | --- | --- |
| `moment` | `dayjs` | 约 72 KB → 约 3 KB |
| `lodash` | `lodash-es`（按需引入）或 `radash` | 约 25 KB → 按需几百字节 |
| `axios` | `ofetch` / 原生 `fetch` | 约 13 KB → 接近 0 |
| `echarts` | 按需引入图表类型 | 约 350 KB → 约 80 KB |

**但这些替换不是必须的。** 如果项目里 `moment` 只用了两次格式化，花两小时换成 `dayjs` 的意义不大。**优先级排序：路由懒加载 → 按需引入 → 分包 → 压缩 → 图片 → 换库。**

**先做前四项，通常能解决 80% 的问题。**
:::

## 优化完再测一遍

改完之后重新打包，把数据填进这张表：

| 指标 | 优化前 | 优化后 | 变化 |
| --- | --- | --- | --- |
| dist 总大小 | | | |
| 最大单个 JS 文件 | | | |
| 首屏加载量（Network 里的 transferred） | | | |
| 首屏请求数 | | | |
| FCP（首次内容绘制） | | | |
| LCP（最大内容绘制） | | | |

**这张表要留着，答辩时用得上。** 它的价值在于“有对比”—— 说“我做了优化”没人有感觉，说“首屏从 1.4 MB 降到 320 KB，用校园网实测从 4.2 秒降到 1.1 秒”，就有了。

::: warning 测的时候要公平
两次测量必须在相同条件下：

- 都用**生产构建**（`pnpm build` + `pnpm preview`，不是 `pnpm dev`）
- 都**勾上 Disable cache**
- 都在**同一个网络限速**下（建议用 Slow 4G 模拟真实移动网络）
- 都**取三次的平均值**，不要只测一次

**开发服务器和构建产物的表现差别非常大。** 开发环境下 Vite 按需编译模块，请求数是几十上百个；构建后是几个文件。**在 `pnpm dev` 下测性能是没有意义的。**
:::

## 小结

- **优化前先测基线。** 不知道改之前是多少，改完也说不清有没有用。
- **“dist 体积”和“首屏加载量”是两回事。** 优化目标是首屏加载量。
- **优化的优先级**：路由懒加载 → Element Plus 按需引入 → 分包 → gzip / brotli → 图片 → 换掉重库。**前四项解决 80% 的问题。**
- **路由懒加载改动最小、效果最大**，`component: () => import('...')` 就行。它应该一开始就写上，不是优化阶段才补。
- **懒加载必须配合分包**，否则公共代码会重复打包进每个 chunk。
- **按需引入的三个坑**：服务式组件（`ElMessage` 等）、函数式组件的样式、图标组件。都要单独处理。
- **分包不减少首次加载量，它减少后续访问量。** 用户改业务代码后只需要重新下载很小的 `index` chunk。
- **chunk 数量 3 到 6 个比较合理**，分太细反而更慢。
- **压缩优先用服务端实时压缩**，预压缩需要服务器配置 `gzip_static` 才生效。
- **图片的三件事**：转 WebP、控制内联阈值、加 `width` / `height` 与 `loading="lazy"`。
- **测性能要用生产构建 + Disable cache + 固定限速 + 取平均**，在 `pnpm dev` 下测没有意义。
- **优化结果要有前后对比数据。** 答辩时这是最有力的证据。

## 常见坑

::: details 本地 `pnpm dev` 一切正常，`pnpm preview` 白屏
**现象**：打包成功后 `pnpm preview` 打开是一片白，控制台报错。

**原因**：有三种，按概率排序。

**一、资源路径错误。** 部署到子路径（比如 `https://school.edu.cn/activity-admin/`）时，默认的 `base: '/'` 会让资源请求到错误的地址。

**怎么处理**：改 `base`：

```js [vite.config.js]
export default defineConfig({
  base: '/activity-admin/'    // 注意前后都有斜杠
})
```

**二、路由的 history 模式没有回退。** `pnpm preview` 会处理，但某些情况下不完整。

**三、代码里用了只在开发环境存在的变量。** 比如 `import.meta.env.DEV` 判断时用错了分支。

**怎么处理**：看控制台的第一个报错。**白屏的时候 99% 会在控制台有报错**，先看它，不要盲目改配置。
:::

::: details 按需引入之后，弹窗组件没有样式
**现象**：`ElMessage` 弹出来了，但是没有背景色和图标，看起来像一段裸文字。

**原因**：`ElMessage` 是函数式组件，`unplugin-vue-components` 扫描不到它的样式依赖，需要手动引入。

**怎么处理**：

```js [src/main.js]
import 'element-plus/theme-chalk/el-message.css'
import 'element-plus/theme-chalk/el-message-box.css'
import 'element-plus/theme-chalk/el-loading.css'
import 'element-plus/theme-chalk/el-notification.css'
```

**这四个覆盖了绝大部分函数式组件的样式：** 消息提示、确认框、加载遮罩、通知。用了哪个就引哪个。

**更省事的做法**：先查一下 `node_modules/element-plus/theme-chalk/` 目录，看有哪些 `.css` 文件，按需要的引。
:::

::: details 图标全部被打进产物，体积反而变大
**现象**：做了按需引入，体积反而从 1 MB 涨到 1.5 MB。

**原因**：写了这种代码：

```js
// ✗ 这一行就把两千多个图标全打进来了
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}
```

**怎么处理**：只引入用到的图标：

```js
import { Plus, Search, Refresh, Delete, Edit, Fold, Expand } from '@element-plus/icons-vue'

const icons = { Plus, Search, Refresh, Delete, Edit, Fold, Expand }
Object.entries(icons).forEach(([name, comp]) => app.component(name, comp))
```

**或者用 `IconsResolver`** 配到 `Components` 插件里（见上）。

**验证方法**：在分析图里找 `@element-plus/icons-vue`，看它的体积。**如果超过 100 KB，就是全量引入了。**
:::

::: details `manualChunks` 配了但没生效
**现象**：配了 `manualChunks`，`dist/assets/` 里还是只有一个大的 vendor 文件。

**原因**：有三种。

**一、对象和函数混用了。** `manualChunks` 只能是对象或函数，不能两个都写。

**二、包名写错了。** 写了 `'vue'`，但实际在 `node_modules` 里的路径是 `@vue/runtime-core`。

**怎么处理**：用函数版本，按路径匹配，更可靠：

```js
manualChunks(id) {
  if (!id.includes('node_modules')) return
  if (id.includes('element-plus')) return 'element-plus'
  if (id.includes('@vue') || id.includes('/vue/') || id.includes('pinia') || id.includes('vue-router')) {
    return 'vue-vendor'
  }
  return 'vendor'
}
```

**三、用了 `rollupOptions.output.manualChunks` 但项目跑的是 Vite 的默认配置。** 确认配置写在 `build.rollupOptions.output` 里，不是 `build.rollupOptions` 下。

**验证方法**：`pnpm build` 之后 `ls dist/assets/`，看有没有 `element-plus-xxxx.js` 这样的文件名。
:::

::: details 首屏还是很慢，但产物已经很小了
**现象**：产物压到 300 KB，Network 里 transferred 也只有 300 KB，但首屏还是要等三四秒。

**原因**：问题可能不在体积，在别的地方。

| 原因 | 怎么确认 | 怎么改 |
| --- | --- | --- |
| 服务器响应慢（TTFB 高） | Network 里看 Timing → Waiting (TTFB) | 换服务器，或加 CDN |
| 接口慢，首屏在等数据 | Network 里看接口请求耗时 | 接口加索引、加缓存 |
| 大量串行请求 | Waterfall 图里请求是一条一条排的 | 改成并行（`Promise.all`） |
| 字体加载阻塞 | 页面文字先是空白，然后突然出现 | 用 `font-display: swap`，或换成系统字体 |
| 首屏发了很多次接口 | 每个组件各自请求 | 合并接口，或者父组件一次请求后分发给子组件 |

**看图的方法**：Network 面板切到 Waterfall 视图。**如果请求是一个接一个的阶梯状，就是串行。** 串行是首屏慢最常见的原因之一。

```js
// ✗ 串行：两个请求总耗时是两者之和
const activities = await getActivityList()
const stats = await getStats()

// ✓ 并行：总耗时等于较慢的那个
const [activities, stats] = await Promise.all([getActivityList(), getStats()])
```
:::

::: details 打了包但代码里的 `console.log` 还在
**现象**：配了 `esbuild.drop: ['console']`，但产物里还能搜到日志。

**原因**：`esbuild.drop` 只处理通过 esbuild 转换的代码。如果是被 `@vitejs/plugin-vue` 处理的 `.vue` 文件里的 `<script>`，走的是不同的转换流程。

**怎么处理**：用 `build.minify` 配 terser，并配置 `drop_console`：

```bash
pnpm add -D terser
```

```js [vite.config.js]
export default defineConfig({
  build: {
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true,
        drop_debugger: true
      }
    }
  }
})
```

**代价**：terser 比 esbuild 慢很多（大项目可能慢好几倍），压缩效果好一点点。

**建议**：只在确实需要去掉日志时用 terser。**更好的办法是不在代码里留 `console.log`** —— 交代码之前自己搜一遍清掉，比配置构建工具可靠。
:::

## 课后练习

::: details 练习 1：给项目做一次完整优化并记录数据
按这一节的优先级顺序，逐项优化你的项目，每做一项就测一次数据。

**思路提示**：

- 建议顺序：路由懒加载 → 检查有没有全量引入的图标 → 分包 → 压缩 → 图片。
- 每做一项就 `pnpm build` + `pnpm preview`，填一次表。
- **不要把所有优化一起做完再测。** 那样你不知道每一项的贡献是多少。逐项做、逐项测，最后能画出一条下降曲线 —— 这个曲线在答辩时非常有说服力。
- 如果某一项没有效果，也记下来。“试了 X 但没有效果”和“做了 X 效果好”一样有价值。

**测试表格模板**：

| 步骤 | dist 总大小 | 首屏 transferred | 首屏请求数 |
| --- | --- | --- | --- |
| 基线 | | | |
| + 路由懒加载 | | | |
| + 图标按需 | | | |
| + 分包 | | | |
| + 压缩 | | | |
| + 图片优化 | | | |
:::

::: details 练习 2：分析一次真实的产物报告
跑一次 `rollup-plugin-visualizer`，对着图回答五个问题：

1. 最大的三个方块分别是什么？各占多少？
2. 有没有哪个库只用了一两个函数，却被打包了几百 KB？
3. 有没有重复出现的模块（同一个库的多个版本）？
4. 首屏 chunk 和懒加载 chunk 各占多少？
5. 如果只能做一项优化，你会选哪个？为什么？

**思路提示**：

- 第 3 题找重复模块的方法：在 `stats.html` 里搜库名，看是不是出现在两个不同的父节点下。常见的是 `vue` 出现两个版本，通常是某个依赖锁了旧版本。
- 用 `pnpm why <包名>` 可以查是谁引入了它。
- 第 5 题的答案应该是“改完之后首屏体积下降最多的那一项”。**用数据说话，不要凭感觉。**
:::

::: details 练习 3：把首屏的接口请求从串行改成并行
找出首屏加载时发出的接口请求，看有没有可以并行的。

**思路提示**：

- 在 Network 面板看 Waterfall 的排布。**一条一条错开的阶梯 = 串行。**
- 常见的串行来源：一个接口的返回值是下一个接口的参数（这种不能并行）；或者在 `onMounted` 里 `await` 了第一个再 `await` 第二个（这些无关的话可以并行）。
- 用 `Promise.all` 并行时注意错误处理 —— 一个失败会导致整体 reject：

```js
const results = await Promise.allSettled([getActivityList(), getStats()])
const [listRes, statsRes] = results
if (listRes.status === 'rejected') {
  // 列表加载失败，但统计还有数据
}
```

- **写一段结论**：并行之后首屏的接口等待时间从多少降到了多少。
:::

::: details 练习 4：给项目加一个体积守门
在 CI 或本地加一道检查：产物超过阈值就报错。

**思路提示**：

- 最简单的做法是写一个 Node 脚本，构建完读 `dist` 目录，算出总大小，超过阈值就 `process.exit(1)`。

```js [scripts/check-size.mjs]
import { readdirSync, statSync } from 'node:fs'
import { join } from 'node:path'

const LIMIT_KB = 500
const dir = 'dist/assets'
const total = readdirSync(dir)
  .map((f) => statSync(join(dir, f)).size)
  .reduce((a, b) => a + b, 0)

const kb = Math.round(total / 1024)
console.log(`产物体积：${kb} KB（上限 ${LIMIT_KB} KB）`)
if (kb > LIMIT_KB) {
  console.error('产物体积超出上限，请检查是否引入了不该引入的依赖')
  process.exit(1)
}
```

```json [package.json]
{
  "scripts": {
    "build": "vite build",
    "build:check": "vite build && node scripts/check-size.mjs"
  }
}
```

- **这道题的意义**：有了守门，别人（或者三个月后的你）不小心引入一个巨大的库时，会立刻发现，而不是等到上线后才知道。
- 想一想：阈值定多少合适？（提示：先测当前值，上限设在当前值的 110% 到 120%。**定得太松没意义，定得太紧每次构建都失败**）
:::

---

上一节：[12.1 前后端联调](/unit12/01-integration) · 下一节：[12.3 部署上线](/unit12/03-deploy)
