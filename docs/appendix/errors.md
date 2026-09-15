# 常见报错与排查

这份附录按"现象 → 原因 → 解决 → 怎么预防"四栏组织。
**先找现象对得上的那一条，再看原因 —— 直接抄解决命令能解决一次，看懂原因能解决一类。**

排查的通用顺序：

1. **看清报错原文**。不要只看到"报错了"，把完整的那几行读一遍，通常会直接指出文件和行号。
2. **定位层次**：是环境、依赖、构建还是代码运行时报的错？不同层次的排查入口不同。
3. **用最小改动验证**：先注释掉刚写的代码，看报错还在不在，快速缩小范围。
4. **记下来**。同一类报错第二次遇到时，你会感谢第一次记笔记的自己。

## 环境类

::: details 现象：终端输入 `node` 报 `command not found`
**原因**：Node 没装，或者装了但没配到系统环境变量 `PATH` 里。
刚装完没重启终端是最常见的情况。

**解决**：
```bash
# 1. 确认是否真的装了
node -v
# 2. 如果提示找不到，看它是不是装到了别处
which node        # macOS / Linux
where node        # Windows
# 3. 重开一个终端窗口，或让配置生效
source ~/.zshrc   # macOS / zsh
```

用 fnm 或 nvm 管理版本时，检查这两行是否写进了 shell 配置：
```bash
eval "$(fnm env --use-on-cd)"
```

**怎么预防**：装完 Node 后**新开一个终端**再验证；把安装命令写进
[单元 1.4 的环境自检报告](/unit01/04-environment)，别人按你的步骤能复现。
:::

::: details 现象：Windows 上跑 `pnpm` 报 "因为在此系统上禁止运行脚本"
**原因**：PowerShell 的执行策略默认是 `Restricted`，不允许运行 `.ps1` 脚本。
pnpm 这类用脚本实现的命令会被拦下。

**解决**：
```powershell
# 查看当前策略
Get-ExecutionPolicy
# 改成只对当前用户放开本地脚本（推荐，不需要管理员）
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```
或者改用 CMD、Git Bash，它们不受 PowerShell 策略限制。

**怎么预防**：在环境自检报告里注明你用的是哪个终端，以及执行策略是什么。
换电脑或重装系统后先用 `Get-ExecutionPolicy` 确认一遍。
:::

::: details 现象：安装依赖时报 `Unsupported engine`，或运行时报语法错误
**原因**：Node 版本太低，装不上或跑不动新语法。
本课程基线是 Node 24 LTS，最低支持 20.19。

**解决**：
```bash
node -v
# 低于 20.19 就升级。用 fnm 管理版本：
fnm install 24
fnm use 24
node -v
```
项目里还可以用 `engines` 字段声明要求：
```json [package.json]
{ "engines": { "node": ">=20.19.0" } }
```

**怎么预防**：团队统一用同一个版本管理器（推荐 fnm），
并在项目根目录放 `.nvmrc` 或 `.node-version` 文件，写死版本号，别人 `fnm use` 一下就对上了。
:::

::: details 现象：全局安装包时报 `EACCES: permission denied`
**原因**：全局目录属于管理员，当前用户没有写权限。
用 `sudo npm install -g` 是错误做法 —— 会把权限问题越搞越乱。

**解决**：
```bash
# 不要用 sudo。正确做法：改全局目录到用户目录下
npm config set prefix ~/.npm-global
export PATH=~/.npm-global/bin:$PATH   # 写进 ~/.zshrc
# 或者在项目内只用 pnpm 装本地依赖，不用全局
```

**怎么预防**：**全局只装版本管理器，其余依赖一律装到项目里**。
项目依赖跟着代码走，换机器 `pnpm install` 就能复现，不需要全局安装。
:::

::: details 现象：`pnpm: command not found`，但 `npm` 能用
**原因**：pnpm 没装，或者装到了没进 `PATH` 的目录。

**解决**：
```bash
# 用 corepack（Node 自带）启用 pnpm，最省事
corepack enable pnpm
pnpm -v       # 期望 12.4.1 附近
```
装不了 corepack 时用 npm 全局装：
```bash
npm install -g pnpm@12
```

**怎么预防**：`corepack` 是 Node 自带的包管理器开关，
**优先用它**，避免"每台机器全局装一堆东西"。
:::

## 依赖类

::: details 现象：`Cannot find module 'xxx'` 或 `Module not found`
**原因**：三种可能 ——
① 这个包根本没装；② 装了但没在 `package.json` 里（幽灵依赖）；
③ 导入路径写错了。

**解决**：
```bash
# 1. 看这个包在不在依赖里
grep "包名" package.json
# 2. 不在就装；在但报错就重装
pnpm add 包名
rm -rf node_modules && pnpm install
# 3. 是本地文件的话，检查路径和大小写
ls src/components/ActivityCard.vue
```

**怎么预防**：导入本地文件时用 `@/` 别名，减少相对路径层级；
新增依赖一律用 `pnpm add`，别手动改 `package.json` 后忘记 `install`。
:::

::: details 现象：`EEXIST: file already exists`，或创建项目时目录非空
**原因**：目标目录已经存在同名文件，工具不敢覆盖。
常见于用脚手架创建项目时，当前目录里已经有 `package.json`。

**解决**：
```bash
# 换一个空目录，或先确认目录里有什么
ls -a
# 确认没有重要文件后清空，或换个名字创建
pnpm create vue@latest my-project
```

**怎么预防**：创建项目前 `ls` 看一眼当前目录。
**不要随便删别人的目录** —— 先确认那些文件是不是别人的工作成果。
:::

::: details 现象：`ERR_PNPM_OUTDATED_LOCKFILE`，或 CI 上报锁文件不一致
**原因**：`pnpm-lock.yaml` 和 `package.json` 对不上。
常见于手动改了 `package.json` 没跑 `install`，或者多人协作时锁文件冲突没解干净。

**解决**：
```bash
# 本地：重新生成锁文件
pnpm install
# CI 上：用 frozen 模式检查，它会明确告诉你哪里不一致
pnpm install --frozen-lockfile
```

**怎么预防**：**锁文件必须提交到 Git**，并且每次改依赖后一起提交。
评审时看到 `package.json` 变了但 `pnpm-lock.yaml` 没变，就要问一句为什么。
:::

::: details 现象：`pnpm install` 卡在某个包上不动
**原因**：网络问题（默认源在国外），或者某个包体积大、解析慢。

**解决**：
```bash
# 1. 换国内镜像源
pnpm config set registry https://registry.npmmirror.com
# 2. 清缓存重来
pnpm store prune
rm -rf node_modules && pnpm install
# 3. 看是不是卡在某个具体包上
pnpm install --reporter=append-only
```

**怎么预防**：项目根目录放 `.npmrc`，把源写进文件里，团队共享：
```ini [.npmrc]
registry=https://registry.npmmirror.com
```
:::

::: details 现象：代码里能 import 一个没在 `package.json` 里的包（幽灵依赖）
**原因**：扁平化的 `node_modules` 让某个包的间接依赖被提升到了顶层，
你的代码能直接访问到它，但它并不是你的直接依赖。

**解决**：**不要这么用**。把真正用到的包显式装进来：
```bash
pnpm add 那个包
```
然后从 `package.json` 里检查一遍，确保所有 `import` 的第三方包都声明了。

**怎么预防**：用 pnpm 的严格模式（默认行为）能减少这类问题；
定期搜一遍 `import` 的包名，跟 `package.json` 对照。
:::

::: details 现象：`peer dependencies` 警告，或版本冲突导致运行报错
**原因**：两个包依赖同一个包的不同大版本，装了两份，运行时可能行为不一致。

**解决**：
```bash
# 看是谁依赖了不同版本
pnpm why 包名
# 按提示升级其中一个包，或加 overrides 强制统一（谨慎）
```

**怎么预防**：升级依赖时看升级日志；不要一次同时升级多个大版本。
`pnpm why` 是排查版本冲突的第一入口。
:::

## Vite 与构建类

::: details 现象：`Failed to resolve import "@/xxx"` —— 找不到别名路径
**原因**：`vite.config.js` 里没配 `@` 别名，或 `jsconfig.json` 没同步，
导致编辑器和构建工具对路径的理解不一致。

**解决**：
```js [vite.config.js]
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  }
})
```
改完必须**重启开发服务器**（配置文件不热更新）。

**怎么预防**：新建项目时就用 `create-vue` 生成的基础配置，
别自己从零拼。别名改动后同步改 `jsconfig.json`。
:::

::: details 现象：`Port 5173 is in use`
**原因**：上一次的开发服务器没关干净，或者有别的程序占了这个端口。

**解决**：
```bash
# macOS / Linux：找到占用进程并结束
lsof -ti:5173 | xargs kill -9
# Windows
netstat -ano | findstr :5173
taskkill /PID <进程号> /F
```
或者让 Vite 自动换端口：
```js [vite.config.js]
export default defineConfig({ server: { port: 5173, strictPort: false } })
```

**怎么预防**：终端里用 `Ctrl + C` 正常停止服务器；
`strictPort: false` 让它在端口被占时自动顺延，不会直接启动失败。
:::

::: details 现象：开发时正常，构建后某个文件 404；或 macOS 正常、Linux 报错
**原因**：**路径大小写不一致**。macOS 的文件系统默认不区分大小写，
Linux 区分。`import ActivityCard from './activitycard.vue'` 在 macOS 能跑，Linux 就找不到。

**解决**：
```bash
# 找出实际文件名，核对大小写
ls src/components/
# 逐个修正 import 路径，改成与文件名完全一致
```

**怎么预防**：文件名和 import 路径都用统一约定（组件用大驼峰），
并且**交付前必须跑一次 `pnpm build && pnpm preview`** ——
构建环境对大小写更严格。
:::

::: details 现象：`import.meta.env.VITE_XXX` 读到 `undefined`
**原因**：三种可能 ——
① 变量名没以 `VITE_` 开头；② 改完 `.env` 没重启服务器；③ 变量定义在了错误的 `.env` 文件里。

**解决**：
```bash
# 1. 看变量名
grep VITE_ .env*
# 2. 只用 VITE_ 开头的会暴露给浏览器
# 3. 重启开发服务器（环境变量不热更新）
```
```js
console.log(import.meta.env.VITE_API_BASE_URL) // 确认能读到
```

**怎么预防**：在 `src/` 里加一个 `env.d.ts` 声明变量类型，
写错名字时编辑器会提示；`.env` 改动后形成"改完重启"的习惯。
:::

::: details 现象：构建成功但页面全白，控制台报错
**原因**：常见三类 ——
① 用了 `window` / `document` 但代码在构建期也跑了；
② 打包后资源路径不对（部署到了子目录）；
③ 某个依赖在构建时被错误处理。

**解决**：
```bash
# 先本地预览构建产物，复现问题
pnpm build && pnpm preview
# 打开浏览器控制台，看第一条报错（第一条最关键）
```
如果部署在子目录下，构建时指定基础路径：
```js [vite.config.js]
export default defineConfig({ base: '/admin/' })
```

**怎么预防**：**每次交付前都跑 `build && preview`**，
不要只在 `dev` 模式下验证。白屏问题在 `dev` 下常常看不到。
:::

::: details 现象：构建时内存溢出，或提示 chunk 过大
**原因**：依赖太多、单个 chunk 太大，或者 `import()` 用得不够细。

**解决**：
```bash
# 加大 Node 内存（临时绕过）
NODE_OPTIONS=--max-old-space-size=4096 pnpm build
```
更好的做法是把大依赖拆开：
```js
// ✓ 按需引入：只引一个组件，不要整包引
import { ElButton } from 'element-plus'
```

**怎么预防**：用 `pnpm build --report` 或构建分析插件看产物构成；
大路由用动态 `import()` 做代码分割，见[单元 12 的构建优化](/unit12/02-build-optimize)。
:::

## Vue 运行类

::: details 现象：`Property "xxx" was accessed during render but is not defined`
**原因**：模板里用了一个组件里没定义的变量。常见于拼错名字、
或者用 `setup` 写法时忘了 `return`（选项式）。

**解决**：
```vue
<script setup>
const activities = ref([]) // ✓ 定义了才能用
</script>

<template>
  <!-- ✗ 拼错了：activites -->
  <li v-for="item in activities" :key="item.id">{{ item.title }}</li>
</template>
```

**怎么预防**：用编辑器插件（Vue - Official）会实时提示模板里未定义的变量。
写模板时对照 `script` 里的名字逐个核对。
:::

::: details 现象：`Set operation on key "xxx" failed: target is readonly`（改 prop）
**原因**：子组件直接改了 `props` 传进来的值。`props` 是只读的。

**解决**：
```vue [子组件]
<script setup>
const props = defineProps({ modelValue: String })
const emit = defineEmits(['update:modelValue'])

// ✗ props.modelValue = 'x'
// ✓ 通知父组件改
function update(val) {
  emit('update:modelValue', val)
}
</script>
```
用 `defineModel` 更省事：
```js
const title = defineModel('title') // 可读可写，自动 emit
```

**怎么预防**：记住"数据谁拥有谁修改"。子组件要改父组件的数据，一律走事件；
双向绑定用 `v-model` / `defineModel`。
:::

::: details 现象：列表更新后内容串位，或勾选状态跑到了别的项上
**原因**：`v-for` 的 `key` 用了索引（`index`），列表增删后同一索引对应的元素变了。

**解决**：
```vue
<!-- ✗ -->
<li v-for="(item, index) in list" :key="index">

<!-- ✓ 用业务 id -->
<li v-for="item in list" :key="item.id">
```

**怎么预防**：`v-for` 一律用唯一业务 id 作 `key`，
除非列表是纯静态且永不增删。
:::

::: details 现象：`Failed to resolve component: xxx` 或页面不显示组件
**原因**：组件没 import（`<script setup>` 里不会自动注册所有组件），
或者注册的名字和用法对不上。

**解决**：
```vue
<script setup>
// ✓ 显式导入，模板里就能直接用
import ActivityCard from '@/components/ActivityCard.vue'
</script>

<template>
  <ActivityCard title="迎新晚会" />
</template>
```

**怎么预防**：全项目统一用"显式 import + 大驼峰"的写法，
不要依赖自动全局注册。全局注册只在 UI 组件库这类场景用。
:::

::: details 现象：`Cannot read properties of null (reading 'value')`
**原因**：模板 ref 还没挂载就去读了，或者 `ref.value` 是 `null`。

**解决**：
```vue
<script setup>
import { onMounted, useTemplateRef } from 'vue'
const inputRef = useTemplateRef('input')

onMounted(() => {
  // ✓ 挂载后才能拿到
  inputRef.value?.focus()
})
</script>

<template>
  <input ref="input" />
</template>
```

**怎么预防**：操作 DOM / 子组件实例一律放在 `onMounted` 之后；
读取时用可选链 `?.` 兜底。
:::

## 路由类

::: details 现象：刷新页面返回 404（开发正常，部署后报错）
**原因**：单页应用只有 `index.html` 一个入口。
用户刷新 `/activities` 时，服务器真的去找名为 `activities` 的文件，找不到就 404。

**解决**：把服务器配置成"找不到文件时返回 `index.html`"。
Nginx 示例：
```nginx
location / {
  try_files $uri $uri/ /index.html;
}
```
静态托管平台（Vercel、Netlify）用对应的重写规则文件。

**怎么预防**：**部署前先本地 `pnpm build && pnpm preview` 验证**；
把这条重写规则写进部署文档。见[单元 12 的部署一节](/unit12/03-deploy)。
:::

::: details 现象：嵌套路由配了但子页面不显示
**原因**：父路由组件里忘了写 `<RouterView />`。
子路由的内容要渲染在父组件的这个占位符里。

**解决**：
```vue [layouts/AdminLayout.vue]
<template>
  <div class="layout">
    <TopNav />
    <aside><SideNav /></aside>
    <main>
      <!-- ✓ 子路由渲染在这里 -->
      <RouterView />
    </main>
  </div>
</template>
```

**怎么预防**：只要配了 `children`，父组件就必须有 `<RouterView />`。
画路由表时顺手在父组件里放上占位符。
:::

::: details 现象：页面不停重定向，或浏览器报"too many redirects"
**原因**：路由守卫对自己的目标路径也做了拦截。
典型：守卫把未登录用户跳到 `/login`，而 `/login` 也被标了 `requiresAuth`。

**解决**：
```js [router/index.js]
router.beforeEach((to) => {
  const authStore = useAuthStore()
  // ✓ 先放行白名单页面，避免守卫自己拦自己
  if (to.meta.public) return true
  if (to.meta.requiresAuth && !authStore.isLoggedIn) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
})
```
登录页、注册页、错误页都要标成 `public: true`。

**怎么预防**：加守卫时先列出"不需要登录就能访问"的页面清单；
守卫里永远先判断白名单。
:::

::: details 现象：`route.query.page` 拿到的 `2` 不能做加法
**原因**：`query` 里的值**永远是字符串**。`'2' + 1` 得到 `'21'`，不是 `3`。

**解决**：
```js
// ✓ 显式转换
const page = Number(route.query.page) || 1
// 布尔值也一样
const includeEnded = route.query.includeEnded === 'true'
```

**怎么预防**：从 `params` / `query` 取值时立刻转换并给默认值，
不要在后续逻辑里反复转换。
:::

::: details 现象：跳转到详情页后 `route.params.id` 是 `undefined`
**原因**：路由路径里没有声明动态参数，或者跳转时传的是 `query` 而不是 `params`。

**解决**：
```js [router/index.js]
{ path: '/activity/:id', name: 'activity-detail', component: ActivityDetailView }
```
```js
// ✓ 用 params 传路径参数，地址形如 /activity/12
router.push({ name: 'activity-detail', params: { id: 12 } })
```

**怎么预防**：用 `name` 跳转而不是拼路径字符串 ——
路由路径改了不会影响跳转代码。
:::

## 请求类

::: details 现象：浏览器控制台报 CORS / 跨域错误
**原因**：浏览器的同源策略。前端在 `localhost:5173`，后端在 `localhost:8080`，
端口不同就算跨域，浏览器会拦截响应。

**解决**：
```js [vite.config.js]
export default defineConfig({
  server: {
    proxy: {
      // ✓ 把 /api 转发给后端，浏览器看来是同源请求
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      }
    }
  }
})
```
注意 **代理只在开发环境有效**。生产环境要么后端允许跨域，要么前后端同域部署。

**怎么预防**：接口地址始终用 `/api` 这类相对路径，
跨域问题交给代理和部署配置解决，**前端代码里不要出现具体的后端域名**。
:::

::: details 现象：登录过期后页面无限跳转登录页
**原因**：`401` 处理时，登录页本身也发了需要鉴权的请求，
被拦截器又跳一次登录页，形成循环。

**解决**：
```js [src/api/request.js]
let redirecting = false

if (status === 401 && !redirecting) {
  redirecting = true
  authStore.logout()
  router.push({ name: 'login' })
}
```

**怎么预防**：跳转前判断当前是不是已经在登录页，
或者用上面的标记，保证**同一轮故障只跳一次**。
:::

::: details 现象：同一个接口在短时间内被调用了好几次
**原因**：常见三类 ——
① 按钮没禁用，用户连点；② `watch` 监听了一个在 `computed` 里也会被读取的对象，来回触发；
③ 组件被重复挂载。

**解决**：
```js
// ① 请求期间禁用按钮
const submitting = ref(false)
async function submit() {
  if (submitting.value) return // ✓ 守卫
  submitting.value = true
  try { await submitApi() } finally { submitting.value = false }
}
```
```vue
<button :disabled="submitting">{{ submitting ? '提交中…' : '提交' }}</button>
```

**怎么预防**：所有会改数据的操作都要有"进行中"状态；
调试时打开网络面板，按时间看请求，确认真实发送次数。
:::

::: details 现象：接口明明返回了数据，页面拿到的却是 `undefined`
**原因**：响应拦截器已经剥了一层（`return res.data`），
页面里又按原始结构读了一次，比如 `res.data.list`。

**解决**：
```js
// 拦截器里：return res.data
// 页面里：直接用
const res = await getActivityListApi(params)
list.value = res.list // ✓ 不要再写 res.data
```

**怎么预防**：团队约定"拦截器剥一层"，
新接口先看一个已有接口的用法，保持一致。
:::

::: details 现象：请求超时 `timeout of 10000ms exceeded`
**原因**：全局超时设得太短，或后端接口确实慢。

**解决**：
```js
// 给个别长耗时接口单独放宽
export function exportSignupsApi(params) {
  return request.get('/signup/export', { params, timeout: 60000, responseType: 'blob' })
}
```

**怎么预防**：区分"普通接口"和"长耗时接口"，
普通的 10 秒、导出上传的单独设置，并在错误提示里说明是超时而不是失败。
:::

::: details 现象：请求取消了，但页面弹了一条错误提示
**原因**：竞态防护用 `AbortController.abort()` 取消请求，
axios 抛出的取消错误被拦截器当成了网络错误。

**解决**：
```js
request.interceptors.response.use(null, (error) => {
  // ✓ 取消不算错误
  if (axios.isCancel(error)) return Promise.reject(error)
  // ...其他错误处理
})
```

**怎么预防**：拦截器处理错误时，第一件事就是判断是不是取消；
页面里的 `catch` 也要检查 `signal.aborted`。
:::

::: details 现象：文件上传后后端说解析不到文件
**原因**：手动设置了 `Content-Type: multipart/form-data`，
丢掉了浏览器自动生成的 `boundary` 参数，后端无法解析。

**解决**：
```js
// ✓ 用 FormData，不要手写 Content-Type
export function uploadCoverApi(file) {
  const formData = new FormData()
  formData.append('file', file)
  return request.post('/upload', formData)
}
```

**怎么预防**：上传一律用 `FormData`，
让 axios 自己决定请求头。**"看起来更明确"的手写配置往往是错的。**
:::

## 跨端类

这一节的报错只在[用户端（uni-app）](/mobile/)里出现。**共同点是：同一段代码在管理端能跑，在这里不行。**

::: details 现象：页面里写了 wd-button，什么也不显示，控制台提示找不到组件
**原因**：easycom 的路径写成了 `uni_modules` 的路径，但你是用 npm 装的。
官方文档的示例按 `uni_modules` 安装写（路径是 `@/uni_modules/wot-ui`），npm 装的包名是 `@wot-ui/ui`。

**解决**：

```json [src/pages.json]
{
  "easycom": {
    "autoscan": true,
    "custom": {
      "^wd-(.*)": "@wot-ui/ui/components/wd-$1/wd-$1.vue"
    }
  }
}
```

改完**重启一次开发服务器**。`pages.json` 的改动不一定触发重新编译。

**怎么预防**：照文档抄配置之前，先确认文档假设的安装方式与你实际用的方式是不是同一种。
:::

::: details 现象：从 wot-design-uni 装的组件，样式偏旧，某些属性不生效
**原因**：这个包名已经停更，最后停在 1.14.0。新的包名是 `@wot-ui/ui`。

**解决**：

```bash
# 分别查两个包的最新版本
curl -s https://registry.npmjs.org/@wot-ui%2Fui/latest | head -c 200
curl -s https://registry.npmjs.org/wot-design-uni/latest | head -c 200

pnpm remove wot-design-uni
pnpm add @wot-ui/ui
```

**怎么预防**：AI 给出安装命令时，**先查包名再装**。训练语料里旧名更多，它会很自信地给你旧包名。
:::

::: details 现象：页面一打开就报 window is not defined / document is not defined
**原因**：小程序里没有浏览器那套 API。`window`、`document`、`localStorage`、`navigator` 全都不存在。

**解决**：换成 uni-app 提供的等价 API。

| 浏览器写法 | 用户端写法 |
| --- | --- |
| `localStorage.setItem(k, v)` | `uni.setStorageSync(k, v)` |
| `window.location.href = url` | `uni.navigateTo({ url })` |
| `document.title = x` | `pages.json` 里配 `navigationBarTitleText` |
| `setTimeout` | 能用，但要在 `onUnload` 里清掉 |

**怎么预防**：写用户端代码时，看到这几个词就停下来想一想。**管理端的工具函数不能直接复制过来。**
:::

::: details 现象：点进新加的页面，提示页面不存在，跳转失败
**原因**：加了 `.vue` 文件，但没往 `pages.json` 的 `pages` 数组里注册。
uni-app 的路由表是配置式的，**不是按文件目录自动生成的**。

**解决**：

```json [src/pages.json]
{
  "pages": [
    { "path": "pages/activity/list", "style": { "navigationBarTitleText": "活动" } },
    { "path": "pages/activity/detail", "style": { "navigationBarTitleText": "活动详情" } }
  ]
}
```

**怎么预防**：把“新建页面 = 建文件 + 加 `pages.json`”当成一个动作，**不要只做前半截**。
让 AI 加页面时，明确要求它同时改 `pages.json`。
:::

::: details 现象：navigateTo 跳转失败，控制台提示页面栈超限
**原因**：微信小程序的页面栈上限是 10 层。连续 `navigateTo` 会一直往栈里压。

**解决**：按场景换 API。

| 场景 | 用什么 |
| --- | --- |
| 从列表进详情，要能返回 | `navigateTo` |
| 登录成功后进主页，不要返回登录页 | `redirectTo` |
| 切到底部 tabBar 的页面 | `switchTab`（**不能带参数**） |
| 退出登录，清空页面栈 | `reLaunch` |
| 返回上一页 | `navigateBack` |

**怎么预防**：设计跳转时先想清“要不要留返回路径”，不要一律用 `navigateTo`。
:::

::: details 现象：表单写了 rules 和 label，既不校验，标签也不显示
**原因**：Wot UI 的表单 API 和后台常用的 Element Plus 不一样：
校验规则用 **`schema`** 而不是 `rules`，标签属性是 **`title`** 而不是 `label`，字段名用 `prop` 绑定。

**解决**：

```vue
<wd-form ref="form" :model="model" :schema="schema">
  <wd-form-item title="联系方式" prop="contact">
    <wd-input v-model="model.contact" />
  </wd-form-item>
</wd-form>
```

**怎么预防**：换组件库时先读一遍表单的 props 表，**不要按上一个库的习惯猜**。
:::

::: details 现象：调用了 useToast().success()，页面上什么都没出现
**原因**：uni-app 不支持全局挂载组件，`<wd-toast />` 必须显式写进页面模板里。

**解决**：

```vue
<template>
  <view class="page">
    <!-- 页面内容 -->
  </view>
  <!-- ✓ 这两个必须写在模板里，否则不渲染 -->
  <wd-toast />
  <wd-dialog />
</template>
```

**怎么预防**：在页面骨架里就先把这两个写进去，用到的时候不用回头找。
:::

---

上一节：[API 速查手册](/appendix/cheatsheet) ·
下一节：[工具链与版本清单](/appendix/tools)
