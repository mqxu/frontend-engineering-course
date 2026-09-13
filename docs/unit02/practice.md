# 单元 2 课后练习

本单元的练习围绕一个**故意做坏的工程**展开。你需要把它修到能正常开发、能正常构建，
并且把每次排查都记录下来。

**四道必做题，一道选做题。** 必做题之间是递进的：先修好（练习 1），
再补配置（练习 2），然后验证配置真的生效（练习 3），最后看产物（练习 4）。

::: tip 开始之前
四道题都在同一个项目里做。建议放在 `~/projects/campus-activity-admin`，
后面几周会一直用这个目录。

**不要一边做一边看答案。** 这道题的训练目标是“排查”，不是“抄配置” ——
照着答案改一遍，你什么也没学到。
:::

## 必做题

### 练习 1 · 修好一份“问题工程”

下面是一个从别处拿来的项目。它能装、能跑，但每一处都有问题。

```text [问题工程的文件结构]
campus-activity-admin/
├── src/
│   ├── api/
│   │   └── activity.js
│   ├── utils/
│   │   └── format.js
│   ├── views/
│   │   └── ActivityListView.vue
│   ├── App.vue
│   └── main.js
├── index.html
├── package.json
└── vite.config.js
```

```json [package.json（问题版）]
{
  "name": "campus-activity-admin",
  "version": "1.0.0",
  "scripts": {
    "dev": "vite dev --port 5173",
    "build": "vite",
    "start": "vite preview"
  },
  "dependencies": {
    "vue": "^2.0.0",
    "vue-router": "^5.3.1",
    "pinia": "^4.0.3",
    "axios": "^1.20.0",
    "element-plus": "^2.14.5",
    "@vitejs/plugin-vue": "^6.0.0",
    "vite": "^8.3.0",
    "sass": "^1.104.1"
  },
  "devDependencies": {
    "eslint": "latest"
  }
}
```

```js [src/main.js]
import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import App from './App.vue'
import './assets/main.css'

createApp(App).use(ElementPlus).mount('#app')
```

```js [src/utils/format.js]
import dayjs from 'dayjs'

// 把报名截止时间格式化成“2026-09-13 18:00”这种形式
export function formatDeadline(time) {
  return dayjs(time).format('YYYY-MM-DD HH:mm')
}
```

```js [vite.config.js（问题版）]
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()]
})
```

#### 你要做的事

**第一步：把问题找出来，先不修。** 按下面的清单逐项核对，
把每个问题写成“现象 → 影响 → 属于哪一层”三栏。

| 排查方向 | 要核对什么 |
| --- | --- |
| 依赖声明 | `package.json` 里声明的包，和代码里 import 的包对得上吗 |
| 版本范围 | 每个范围装出来的版本，和代码里的写法匹配吗 |
| 依赖字段 | 每个包在 `dependencies` 还是 `devDependencies`？理由是什么 |
| 脚本命令 | 每条脚本实际执行什么？哪条是错的 |
| 缺失字段 | 一个规范项目的 `package.json` 还应该有哪些字段 |
| 配置完整度 | `vite.config.js` 缺了什么（别名、代理） |

**第二步：逐个修，一次只改一处。** 每改一处，跑一次 `pnpm install` 或 `pnpm dev`，
记录结果。**不要一次改完再跑** —— 那样你不知道是哪一处起了作用。

**第三步：把过程写进依赖排查单。**

#### 问题清单（核对用）

::: details 想不出来的时候，展开看提示（只有问题描述，不给答案）
一共 8 处问题，分布如下：

1. `vue` 的版本范围写的是 `^2.0.0` —— 会装出 Vue 2。
2. `vue-router` 的版本范围与 Vue 的版本不匹配。
3. `dev` 脚本里写了一个 Vite 不认识的子命令。
4. `build` 脚本执行的根本不是构建命令。
5. 三条脚本里缺了一条必需的（`dev` / `build` / `preview` 三缺一）。
6. 有三个包放错了字段 —— 它们只在开发时用得到。
7. 代码里用了一个包，但 `package.json` 里没有声明（幽灵依赖）。
8. 缺少若干规范项目应有的字段：`private`、`type`、`engines`、`packageManager`。
   另外 `.npmrc` 里应该开严格模式。
:::

::: details 修好之后应该是什么样（参考答案，做完再看）
```json [package.json（修复版）]
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
    "dayjs": "^1.11.13",
    "element-plus": "^2.14.5",
    "pinia": "^4.0.3",
    "vue": "^3.5.42",
    "vue-router": "^5.3.1"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^6.0.0",
    "eslint": "^10.10.0",
    "sass": "^1.104.1",
    "vite": "^8.3.0"
  }
}
```

```ini [.npmrc]
engine-strict=true
```

注意几处关键差别：

- `vue` 从 `^2.0.0` 改成 `^3.5.42`，`vue-router` 的 `^5.3.1` 与 Vue 3 匹配。
- `vite`、`@vitejs/plugin-vue`、`sass` 从 `dependencies` 移到 `devDependencies`。
- 补上 `dayjs`，并用 `pnpm add dayjs` 装而不是手写 —— 这样版本范围由工具决定。
- `eslint` 从 `latest` 换成 `^10.10.0`，范围可控。
- 脚本三条归一：`vite` / `vite build` / `vite preview`。
:::

#### 验收标准

| 项目 | 要求 |
| --- | --- |
| 问题清单 | 8 处问题全部找出，每条写出“现象 → 影响 → 所属层” |
| 修复完整 | `pnpm install` 无警告、无 `unmet peer` |
| 可复现 | `rm -rf node_modules && pnpm install && pnpm dev` 能正常启动 |
| 依赖正确 | 删掉 `node_modules` 重装后依然能跑，没有幽灵依赖 |
| 过程记录 | 8 处问题各有记录，不是最后一并补写 |

::: warning 不要用“装到能跑”当验收标准
“能跑”只是最低要求。一个 `dependencies` 和 `devDependencies` 乱放的工程也能跑，
但它会让云平台的构建变慢、让依赖冲突难以排查。

**验收看的是上面那张表，不是“跑起来了”。**
:::

### 练习 2 · 为工程补齐别名与代理配置

在练习 1 修好的项目上继续。

#### 要求

1. 配 `@` 指向 `src`，并把项目里所有相对路径的 import 改成 `@/` 形式。
2. 同步配置 `jsconfig.json`，让编辑器能识别别名。
3. 配一个 `/api` 开发代理，目标地址从环境变量读取，并去掉 `/api` 前缀。
4. 代理配置里要有一份合理的默认值，环境变量没配时也能用。

```js [src/api/activity.js（要靠别名改写）]
import axios from 'axios'
import { formatDeadline } from '../utils/format'  // ✗ 改成 @/utils/format
```

#### 验收标准

| 检查项 | 验收标准 |
| --- | --- |
| 别名生效 | 构建通过，且 `grep -rn "\.\./" src/` 找不到跨目录的相对路径 |
| 编辑器识别 | `@/` 不标红波浪线，有路径提示 |
| 两处一致 | `vite.config.js` 与 `jsconfig.json` 里的别名规则相同 |
| 代理生效 | 页面里请求 `/api/activity/list`，Network 面板状态 200 |
| 前缀重写 | 后端收到的路径不带 `/api`（用后端日志或抓包确认） |
| 可配置 | 改 `VITE_PROXY_TARGET` 后重启，代理目标跟着变 |

::: details 参考思路
**别名部分**：

```js [vite.config.js 片段]
resolve: {
  alias: {
    '@': fileURLToPath(new URL('./src', import.meta.url))
  }
}
```

```json [jsconfig.json]
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": { "@/*": ["src/*"] }
  },
  "exclude": ["node_modules", "dist"]
}
```

**代理部分**：

```js [vite.config.js 片段]
server: {
  proxy: {
    '/api': {
      target: env.VITE_PROXY_TARGET || 'http://localhost:8080',
      changeOrigin: true,
      rewrite: (path) => path.replace(/^\/api/, '')
    }
  }
}
```

**最容易漏的两处**：一是忘记在配置里用 `loadEnv` 读环境变量，
直接写 `process.env.VITE_PROXY_TARGET` 会拿到 `undefined`；
二是改了配置没重启服务器，以为配置没生效。
:::

### 练习 3 · 在开发态与生产态验证环境变量

#### 要求

准备三个环境变量文件，然后**在两种模式下各验证一次取值**。

```ini [.env]
VITE_APP_TITLE=校园活动服务平台
```

```ini [.env.development]
VITE_API_BASE=/api
VITE_PROXY_TARGET=http://localhost:8080
```

```ini [.env.production]
VITE_API_BASE=https://api.campus.example.com
```

验证方式：在 `App.vue` 里临时加一段输出，用 `pnpm dev` 和
`pnpm build && pnpm preview` 各看一次。

```js [src/App.vue（验证用，验完删掉）]
console.log('MODE:', import.meta.env.MODE)
console.log('PROD:', import.meta.env.PROD)
console.log('API:', import.meta.env.VITE_API_BASE)
console.log('TITLE:', import.meta.env.VITE_APP_TITLE)
```

#### 验收标准

| 检查项 | 要求 |
| --- | --- |
| 表格完整 | 四个变量在两种模式下的取值全部填出 |
| 取值正确 | dev 下 `MODE` 是 `development`、`PROD` 是 `false`；preview 下相反 |
| 有差异 | 至少有一个变量的取值在两种模式下不同，并说明为什么 |
| 优先级验证 | 在 `.env.development.local` 里覆盖一个值，确认它赢过 `.env.development` |
| 安全性检查 | 报告里说明为什么有的变量不能加 `VITE_` 前缀 |

#### 结果记录表

| 变量 | `pnpm dev` | `pnpm preview` | 是否需要 `VITE_` 前缀 |
| --- | --- | --- | --- |
| `MODE` | | | 内置，不用自己定义 |
| `PROD` | | | 内置 |
| `VITE_API_BASE` | | | |
| `VITE_APP_TITLE` | | | |

::: details 参考思路
关键动作有两个：

1. **`preview` 之前必须先 `build`**。`preview` 不会重新构建，
   它只是把 `dist/` 挂到一个本地服务器上。
2. **改了 `.env` 要重启**。环境变量在启动时读入，运行中改不生效。

`MODE` 和 `PROD` 的关系容易搞混：

- `MODE` 默认跟命令走，`dev` → `development`，`build` → `production`，
  但可以用 `--mode staging` 改。
- `PROD` 只看“是不是在构建”，用 `--mode staging` 构建时它**仍然是 `true`**。

所以**不要用 `PROD` 判断“连的是哪个环境”**，要自己定义变量。

优先级验证那一步：在 `.env.development.local` 里写
`VITE_APP_TITLE=我的本地标题`，重启后看输出 —— 应该是本地标题。
这个文件不要提交到 Git。
:::

### 练习 4 · 完成一次构建并分析产物构成

#### 要求

1. 在**不加** `manualChunks` 的情况下构建一次，记录产物构成。
2. 加上 `manualChunks` 再构建一次，记录变化。
3. 对两次结果做对比分析，回答下面四个问题：

| 问题 | 回答要点 |
| --- | --- |
| 体积最大的文件是哪个？属于框架、UI 库还是业务代码？ | 给出文件名和体积 |
| 加上分包之后，业务代码那个文件变小了多少？ | 给出具体数字 |
| 有哪些文件带哈希？哈希的作用是什么？ | 结合“内容不变则哈希不变”回答 |
| 如果还要继续优化，下一步该动哪里？ | 给出一个具体方向 |

#### 做法

```bash [终端]
# 第一次：不分包
pnpm build
du -sh dist/assets/* | sort -h

# 配上 manualChunks 之后再构建一次
pnpm build
du -sh dist/assets/* | sort -h
```

#### 验收标准

| 项目 | 要求 |
| --- | --- |
| 数据真实 | 两份体积数据来自实际构建输出，不是估计 |
| 对比清晰 | 用同一张表并列两次结果 |
| 结论具体 | 写“业务代码从 470 KB 降到 42 KB”，不写“变小了很多” |
| 有后续动作 | 指出下一步优化方向，并说明预期效果 |

::: details 参考思路
分包配置：

```js [vite.config.js 片段]
build: {
  rollupOptions: {
    output: {
      manualChunks: {
        'vue-vendor': ['vue', 'vue-router', 'pinia'],
        'element-plus': ['element-plus']
      }
    }
  }
}
```

分包前后大致会长这样（数字以你的实际构建结果为准）：

| 文件 | 分包前 | 分包后 |
| --- | --- | --- |
| `index-xxxx.js`（业务代码 + 全部依赖） | 约 470 KB | 约 42 KB |
| `vue-vendor-xxxx.js` | 无 | 约 118 KB |
| `element-plus-xxxx.js` | 无 | 约 313 KB |

**分包的意义不在“总体积变小”**（总体积几乎不变），而在于
**改业务代码时用户不用重新下载 UI 库**。这一点要在结论里说清楚。

下一步优化方向可以是：

- `element-plus` 改成按需引入，它能从 313 KB 降到几十 KB。
- 用 `du` 找出重复打包的库 —— 有些包可能同时进了两个 chunk。
- 检查有没有把只在开发时用的代码带进了产物。
:::

## 选做题

### 练习 5 · 写一份“依赖排查单”模板

把你这次排查用到的记录格式整理成一份**可复用的模板**，交给同学用。

要求：

1. 模板要能直接复制使用（Markdown 表格或文件骨架）。
2. 包含五层排查顺序，并且每一层写清“怎么查”。
3. 附上至少三条真实案例（来自练习 1）。
4. 加一个“下次遇到同类问题，第一步查什么”的收尾栏。

```md [依赖排查单.template.md（参考骨架）]
# 依赖排查单

## 一、基本信息
- 项目 / 分支：
- 时间：
- 执行的命令：

## 二、现象
（报错原文，完整粘贴）

## 三、按顺序排查

| 顺序 | 查什么 | 怎么查 | 结果 |
| --- | --- | --- | --- |
| 1 | 网络与镜像 | `pnpm config get registry` | |
| 2 | Node 与 pnpm 版本 | `node -v`、`pnpm -v` | |
| 3 | 文件权限 | 看报错里有没有 EACCES / EPERM | |
| 4 | 缓存 | `pnpm store prune` 后重装 | |
| 5 | 锁文件 | 看有没有冲突标记 | |

## 四、结论
- 最终原因：
- 属于第几层：
- 下次第一步查什么：
```

**为什么值得做**：这门课后面还会遇到大量安装与构建问题，而**排查顺序比排查技巧更重要**。
有一个固定顺序，就不会在“重装试试”上浪费半小时。

## 自检标准

做完之后，逐条自查：

- [ ] 8 处问题全部找出，每处都能说出属于哪一层
- [ ] `rm -rf node_modules && pnpm install` 后项目依然能跑
- [ ] 别名在构建和编辑器里都生效
- [ ] 代理在 Network 面板里能看到 200 的响应
- [ ] 环境变量在 dev 与 preview 下的取值不同，且能解释原因
- [ ] 能说清哪些变量不能加 `VITE_` 前缀
- [ ] 有两次构建的产物体积数据，并做出了对比
- [ ] 依赖排查单里至少有三条真实案例

全部打勾，这个单元过关。

## 常见问题

::: details 我的项目里没有后端，代理怎么验证
两个办法：

1. 用任意一个在线的接口测试地址当 `target`，请求一个公开接口，
   看 Network 面板里的响应。
2. 起一个最简单的本地服务（比如用 `pnpm dlx serve` 提供静态文件），
   把它当后端，验证请求有没有被转发过去。

**验收看的是“请求被转发到了 target 地址”，不是“拿到了真实业务数据”。**
:::

::: details 练习 1 的问题，我一个都没找出来怎么办
按这个顺序重看：

1. 先看 [2.3 的字段表](/unit02/03-package-json)，对着问题版 `package.json` 逐项核对。
2. 再看 [2.2 的常用命令](/unit02/02-package-manager#常用命令)，
   想想这 8 个问题里有几个能靠 `pnpm why` 发现。
3. 最后看 [2.1](/unit02/01-node)，想想为什么“缺少 `engines`”也算一个规范性问题。

**一个都不找到很正常**，说明这正是你需要的练习。找完之后记得把过程写完整 ——
问题清单本身不是产出，**排查过程才是**。
:::

::: details 产物分析里的数字和参考思路差很多
正常。差异可能来自三个方面：

- 依赖版本不同（`element-plus` 不同版本的体积差别不小）。
- 是否用了按需引入。
- 是否只写了一个页面 —— 业务代码越多，业务 chunk 越大。

**关键不是数字对得上，而是你能解释“为什么这个文件最大”。**
:::

::: details 我用的不是 pnpm，能过吗
不行。本课程统一 pnpm，原因是它的严格结构能拦住幽灵依赖，
而这一点正好是练习 1 的核心考点。

如果一定要用 npm，请在报告里额外说明：**你用 `npm ls` 是怎么发现幽灵依赖的**。
（答案通常是发现不了 —— 这恰好说明 pnpm 的价值。）
:::

---

上一节：[2.5 环境变量与常用配置](/unit02/05-env-config) ·
下一单元：[单元 3 · 工程规范、质量保障与 Git 协作](/unit03/)
