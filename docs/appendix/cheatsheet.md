# API 速查手册

这份手册按主题分区，每区都是"表格 + 最小示例"。**每个知识点都给一行"什么时候用"，
不要只背语法。**

- 表里出现 `// ✓` 的是推荐写法，`// ✗` 的是常见错误写法。
- 代码全部基于 Vue 3.5 + Vue Router 5 + Pinia 4 的写法。
- 最后一节 [用户端（uni-app）速查](#用户端-uni-app-速查) 是另一套 API，**不要和前面的混着用**。
- 记不住某个东西时，用浏览器搜索：`Ctrl + F`（Windows）/ `Cmd + F`（macOS）。

## 模板语法

| 写法 | 作用 | 什么时候用 |
| --- | --- | --- |
| `{{ 表达式 }}` | 插值，把数据显示到页面上 | 显示文本、数字；不能放语句（`if`、`for`） |
| `v-bind:attr` / `:attr` | 绑定属性 | 绑定 `src`、`href`、`disabled`、组件 props |
| `v-on:event` / `@event` | 绑定事件 | 点击、输入、提交等交互 |
| `v-if` / `v-else-if` / `v-else` | 条件渲染，不满足就**不生成**节点 | 状态互斥、权限控制 |
| `v-show` | 条件显示，靠 `display: none` 切换 | 频繁切换的显示/隐藏（比如弹窗） |
| `v-for` | 列表渲染 | 渲染数组/对象；**必须配 `:key`** |
| `v-model` | 双向绑定 | 表单输入、组件上的双向绑定 |
| `v-html` | 渲染 HTML 字符串 | 富文本展示；**内容不可信时禁用** |
| `v-slot` / `#slot` | 具名插槽 | 组件内容分发 |

```vue [模板语法最小示例]
<script setup>
import { ref } from 'vue'
const keyword = ref('')
const list = ref([{ id: 1, title: '迎新晚会' }])
const disabled = ref(false)
</script>

<template>
  <!-- 插值 -->
  <p>{{ list.length }} 个活动</p>

  <!-- v-bind：简写 : -->
  <button :disabled="disabled">提交</button>

  <!-- v-on：简写 @；.prevent 阻止默认行为 -->
  <form @submit.prevent="onSubmit">
    <!-- v-model 双向绑定 -->
    <input v-model.trim="keyword" placeholder="搜索活动" />
  </form>

  <!-- v-if 与 v-show 的区别：一个不生成节点，一个只是隐藏 -->
  <p v-if="list.length === 0">还没有活动</p>
  <p v-show="disabled">按钮已禁用</p>

  <!-- v-for 一定要用业务 id 作 key -->
  <ul>
    <li v-for="item in list" :key="item.id">{{ item.title }}</li>
  </ul>
</template>
```

### 修饰符速查

| 修饰符 | 用在哪 | 作用 | 什么时候用 |
| --- | --- | --- | --- |
| `.prevent` | `@submit` / `@click` | 阻止默认行为 | 表单提交不想刷新页面 |
| `.stop` | `@click` | 阻止事件冒泡 | 卡片里的按钮不想触发卡片点击 |
| `.once` | `@click` | 只触发一次 | 只允许点一次的按钮 |
| `.self` | `@click` | 只有点自己才触发 | 弹窗遮罩点击关闭，点内容不关 |
| `.trim` | `v-model` | 自动去首尾空格 | 账号、学号、关键词输入 |
| `.number` | `v-model` | 转成数字 | 名额、页码这类数字输入 |
| `.lazy` | `v-model` | 失焦时才同步 | 输入框实时校验太重时 |
| `.enter` / `.esc` | `@keyup` | 指定按键 | 回车提交、Esc 关闭 |
| `.sync` | —— | Vue 2 的写法 | **Vue 3 已移除，用 `v-model:xxx`** |

::: warning 常用组合
- 搜索框：`v-model.trim` + `@keyup.enter`
- 表单：`@submit.prevent`
- 数字输入：`v-model.number`
- 弹窗遮罩：`@click.self="close"`
:::

## 响应式

| API | 类别 | 写法 | 什么时候用 |
| --- | --- | --- | --- |
| `ref` | 声明状态 | `const n = ref(0)`，用 `n.value` | **首选**。任何类型都能装，解构/传递不丢响应性 |
| `reactive` | 声明状态 | `const form = reactive({ a: 1 })` | 一整块相关的对象状态，不想到处写 `.value` |
| `computed` | 派生值 | `const t = computed(() => a.value + b.value)` | 由已有状态算出来的值；**有缓存** |
| `watch` | 副作用 | `watch(src, (nv, ov) => {})` | 状态变化后要做事（发请求、写存储），能拿到新旧值 |
| `watchEffect` | 副作用 | `watchEffect(() => {})` | 只关心"用到的状态变了就执行"，自动收集依赖 |
| `toRef` | 保持响应性 | `toRef(props, 'title')` | 从响应式对象里取一个属性单独传递 |
| `toRefs` | 保持响应性 | `const { a } = toRefs(obj)` | 解构 `reactive` 对象时保持响应性 |
| `storeToRefs` | 保持响应性 | `const { token } = storeToRefs(store)` | 解构 Pinia store 的状态（方法不解构） |
| `shallowRef` | 性能 | `const list = shallowRef([])` | 大数组/大对象，整体替换才更新 |

```js [响应式最小示例]
import { ref, reactive, computed, watch, watchEffect, toRefs } from 'vue'

// ref：最常用，用 .value 读写
const keyword = ref('')
keyword.value = '篮球'

// reactive：整块对象状态
const filters = reactive({ status: '', page: 1 })

// computed：有缓存，依赖不变不重算
const pageCount = computed(() => Math.ceil(37 / filters.pageSize))

// watch：拿到新旧值，适合"变化后做某事"
watch(keyword, (newVal, oldVal) => {
  console.log(`从 ${oldVal} 改成 ${newVal}`)
})

// watchEffect：自动收集依赖，立即执行一次
watchEffect(() => {
  console.log('当前筛选状态：', filters.status)
})

// toRefs：解构 reactive 时保持响应性
const { status, page } = toRefs(filters)
```

::: danger 三个最常见的响应式错误
1. **解构 `reactive` 丢响应性** → 用 `toRefs`。
2. **解构 `ref` 忘了 `.value`**（在 `script` 里）→ 模板里会自动解包，JS 里不会。
3. **解构 Pinia store 丢响应性** → 用 `storeToRefs`。
:::

```js [去抖搜索的典型写法]
import { ref, watch } from 'vue'

const keyword = ref('')
let timer = null

watch(keyword, (val) => {
  clearTimeout(timer)
  // ✓ 输入停止 300ms 后再发请求，避免每敲一个字发一次
  timer = setTimeout(() => {
    if (val.trim()) search(val)
  }, 300)
})
```

## 组件

| 宏 / API | 作用 | 什么时候用 |
| --- | --- | --- |
| `defineProps` | 声明接收的属性 | 父组件传值进来 |
| `defineEmits` | 声明要触发的事件 | 子组件通知父组件 |
| `defineModel` | 声明 `v-model` 双向绑定 | 组件支持 `v-model` |
| `defineOptions` | 声明组件选项（如 `name`） | 需要给组件命名（缓存、递归、调试用） |
| `defineSlots` | 声明插槽（类型提示用） | 需要明确插槽结构时 |
| `useTemplateRef` | 获取模板 ref | 要操作子组件实例或 DOM（聚焦、滚动） |
| `useSlots` / `useAttrs` | 在 JS 里访问插槽 / 透传属性 | 需要把插槽或属性转发给内部组件 |

```vue [组件宏最小示例]
<script setup>
// 父传子：声明时给默认值
const props = defineProps({
  title: { type: String, required: true },
  editable: { type: Boolean, default: false }
})

// 子传父：声明事件名
const emit = defineEmits(['submit', 'cancel'])

// v-model：可读可写的双向绑定
const keyword = defineModel('keyword', { type: String, default: '' })

// 组件命名：递归组件、KeepAlive 缓存、调试都靠它
defineOptions({ name: 'ActivityCard' })

// 模板 ref：拿 DOM 或子组件实例
const inputRef = useTemplateRef('input')
function focusTitle() {
  inputRef.value?.focus()
}

function handleSubmit() {
  // 触发事件，把数据带给父组件
  emit('submit', { keyword: keyword.value })
}
</script>

<template>
  <div class="activity-card">
    <h3>{{ props.title }}</h3>
    <input ref="input" v-model="keyword" />
    <!-- 默认插槽 -->
    <slot :count="0">默认内容</slot>
    <button v-if="props.editable" @click="handleSubmit">提交</button>
  </div>
</template>
```

```vue [插槽的两种用法]
<!-- 默认插槽：父组件写内容 -->
<ActivityCard title="迎新晚会">
  这里的内容会出现在 ActivityCard 的 <slot> 位置
</ActivityCard>

<!-- 具名插槽 + 作用域插槽：子组件把数据"给回"父组件 -->
<ActivityCard title="迎新晚会">
  <template #footer="{ count }">
    已报名 {{ count }} 人
  </template>
</ActivityCard>
```

::: tip 组件拆分与命名
- 一个路由对应一个页面 → 放 `src/views/`。
- 被多个页面复用 → 放 `src/components/`。
- 组件名用大驼峰：`ActivityCard.vue`，模板里写 `<ActivityCard />`。
- `defineProps` / `defineEmits` **不需要 import**，是编译器宏。
:::

## 生命周期

| 钩子 | 执行时机 | 什么时候用 |
| --- | --- | --- |
| `onBeforeMount` | 挂载前 | 很少用 |
| `onMounted` | 挂载完成后 | **最常用**：首次取数据、操作 DOM、起定时器 |
| `onBeforeUpdate` | 数据更新、DOM 还没更新前 | 很少用 |
| `onUpdated` | DOM 更新完成后 | 需要读更新后的 DOM 时 |
| `onBeforeUnmount` | 卸载前 | 清理定时器、事件监听、请求 |
| `onUnmounted` | 卸载完成后 | 释放资源、断开连接 |
| `onActivated` | 被 `KeepAlive` 缓存的组件再次激活 | 缓存页面回到前台时刷新 |
| `onDeactivated` | 组件被缓存而停用 | 停掉轮询 |

```vue [生命周期最小示例]
<script setup>
import { onMounted, onBeforeUnmount } from 'vue'

let timer = null

onMounted(() => {
  // ✓ 起定时器
  timer = setInterval(refresh, 30000)
})

onBeforeUnmount(() => {
  // ✓ 必须清理，否则组件卸载后定时器还在跑
  clearInterval(timer)
})
</script>
```

::: warning 清理不只是定时器
要清理的东西：`setInterval` / `setTimeout`、`addEventListener`、
`AbortController`、WebSocket 连接、`ResizeObserver`。
**凡是"挂载时建立的"，卸载时都要清掉。**
:::

## 路由

| API | 作用 | 什么时候用 |
| --- | --- | --- |
| `useRouter()` | 拿到 router 实例 | 做跳转：`router.push` / `replace` / `back` |
| `useRoute()` | 拿到当前路由信息 | 读参数：`route.params` / `query` / `meta` |
| `<RouterView />` | 渲染匹配到的组件 | 页面容器、嵌套路由的子出口 |
| `<RouterLink to="...">` | 声明式跳转 | 导航链接（可被搜索引擎识别，能新窗口打开） |
| `router.push(loc)` | 编程式跳转，留历史记录 | 用户点按钮后跳转 |
| `router.replace(loc)` | 跳转，不留历史 | 登录成功后跳转（不想让用户"返回"回登录页） |
| `router.back()` | 返回上一页 | 取消、关闭 |
| `beforeEach` | 全局前置守卫 | 登录鉴权、权限判断 |

```js [路由守卫签名]
import { createRouter, createWebHistory } from 'vue-router'

router.beforeEach((to, from) => {
  // to：即将进入的路由；from：来自的路由
  // 返回值决定行为：
  //   true / undefined → 放行
  //   false → 中断
  //   '/login' 或 { name: 'login' } → 重定向到指定地址
  const authStore = useAuthStore() // ✓ 守卫内部调用
  if (to.meta.requiresAuth && !authStore.isLoggedIn) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
})
```

```vue [读取参数]
<script setup>
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

// 动态参数 /activity/:id → route.params.id
const id = route.params.id

// query /activity?page=2 → route.query.page（注意是字符串）
const page = Number(route.query.page) || 1

// 跳转时带 query
router.push({ name: 'activity-detail', params: { id: '12' }, query: { from: 'list' } })
</script>
```

::: warning `route.query` 里的值永远是字符串
`?page=2` 读出来是 `"2"`，不是 `2`。做数字比较或计算前记得转换：
`Number(route.query.page)`。布尔值同理，`?draft=true` 读出来是字符串 `"true"`。
:::

## 请求

| API / 配置 | 作用 | 什么时候用 |
| --- | --- | --- |
| `axios.create({ baseURL, timeout })` | 创建独立实例 | **项目里统一用一个实例** |
| `request.interceptors.request.use` | 请求拦截器 | 注入 token、加公共参数 |
| `request.interceptors.response.use` | 响应拦截器 | 剥数据、判业务码、统一错误提示 |
| `request.get(url, { params })` | GET 请求 | 查询类接口；参数拼在地址后 |
| `request.post(url, data)` | POST 请求 | 新建、动作类接口；数据放请求体 |
| `request.put(url, data)` | PUT 请求 | 全量更新 |
| `request.delete(url)` | DELETE 请求 | 删除 |
| `{ signal }` | 取消请求 | 竞态防护、离开页面取消 |
| `{ timeout: 60000 }` | 单独设超时 | 导出、上传这类长耗时接口 |
| `{ responseType: 'blob' }` | 拿文件流 | 下载文件 |

```js [请求层最小骨架]
import axios from 'axios'

const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 10000
})

// 请求拦截器：注入凭证
request.interceptors.request.use((config) => {
  const authStore = useAuthStore() // ✓ 函数内部调用
  if (authStore.token) {
    config.headers.Authorization = `Bearer ${authStore.token}`
  }
  return config // ✓ 必须返回
})

// 响应拦截器：统一处理
request.interceptors.response.use(
  (response) => {
    const res = response.data
    if (res.code === 0) return res.data // ✓ 剥一层，页面直接用
    return Promise.reject(new Error(res.message))
  },
  (error) => {
    if (axios.isCancel(error)) return Promise.reject(error) // 取消不提示
    // ...按状态码提示、401 跳登录
    return Promise.reject(error)
  }
)

export default request
```

| 参数传法 | 正确写法 | 常见错误 |
| --- | --- | --- |
| GET 的查询参数 | `get(url, { params: { page: 1 } })` | `get(url, { page: 1 })` |
| POST 的请求体 | `post(url, { title: 'x' })` | `post(url, { data: {...} })`（多套了一层） |
| DELETE 带参数 | `delete(url, { params: { hard: true } })` | `delete(url, { hard: true })` |
| 上传文件 | 用 `FormData`，不手写 `Content-Type` | 手写 `multipart/form-data`（丢 boundary） |

## 常用工具

### 数组方法

| 方法 | 作用 | 什么时候用 |
| --- | --- | --- |
| `map` | 每个元素映射成新值 | 列表数据转成组件需要的结构 |
| `filter` | 按条件筛选 | 前端筛选、搜索 |
| `reduce` | 归约成一个值 | 求和、分组、计数 |
| `find` | 找第一个匹配的元素 | 按 id 找活动 |
| `findIndex` | 找第一个匹配的索引 | 找到后做替换/删除 |
| `some` | 有没有满足条件的 | 校验"至少选一个" |
| `every` | 是不是全都满足 | 校验"全部填了" |
| `includes` | 数组里有没有这个值 | 判断权限、判断是否已选 |
| `sort` | **原地**排序，会改原数组 | 慎用，会改数据源 |
| `toSorted` | 排序，**返回新数组** | 推荐用这个，不改原数组 |
| `slice` | 截取一段，返回新数组 | 分页截取、复制数组 |
| `flat` | 拍平嵌套数组 | 处理树形结构 |
| `at(-1)` | 取最后一个元素 | 替代 `arr[arr.length - 1]` |

```js [数组方法最小示例]
const activities = [
  { id: 1, title: '迎新晚会', quota: 100, signupCount: 60, status: 'signing' },
  { id: 2, title: '篮球赛', quota: 50, signupCount: 50, status: 'closed' }
]

activities.map((a) => a.title) // ['迎新晚会', '篮球赛']
activities.filter((a) => a.status === 'signing') // [{ id: 1, ... }]
activities.find((a) => a.id === 2) // { id: 2, ... }
activities.some((a) => a.signupCount >= a.quota) // true
activities.every((a) => a.quota > 0) // true
activities.reduce((sum, a) => sum + a.signupCount, 0) // 110

// ✓ 不改原数组的排序
const sorted = activities.toSorted((a, b) => b.signupCount - a.signupCount)

// 按状态分组
const grouped = activities.reduce((acc, a) => {
  ;(acc[a.status] ??= []).push(a)
  return acc
}, {})
```

::: warning `sort` 会改原数组
`list.sort(...)` 会直接改 `list`，在 Vue 里可能引发意料之外的更新。
**用 `toSorted` 返回新数组**，或者先 `[...list].sort(...)` 复制再排。
:::

### 对象方法

| API | 作用 | 什么时候用 |
| --- | --- | --- |
| `Object.keys(obj)` | 取所有键 | 遍历对象、统计 |
| `Object.values(obj)` | 取所有值 | 求和、查找 |
| `Object.entries(obj)` | 取 `[键, 值]` 数组 | 遍历对象并同时用键和值 |
| `Object.fromEntries(pairs)` | 从键值对数组建对象 | 把 Map 或数组转对象 |
| `Object.assign(target, src)` | 合并（改 target） | 慎用；用展开替代 |
| `{ ...a, ...b }` | 合并，返回新对象 | 给对象加/改字段 |
| `'key' in obj` | 有没有这个键 | 判断字段存在 |
| `obj?.a?.b` | 可选链 | 读可能不存在的嵌套字段 |

```js [对象方法最小示例]
const activity = { id: 1, title: '迎新晚会', quota: 100 }

Object.keys(activity) // ['id', 'title', 'quota']
Object.entries(activity) // [['id', 1], ['title', '迎新晚会'], ...]

// ✓ 不可变更新：改一个字段用展开复制
const updated = { ...activity, quota: 200 }

// ✓ 可选链防止报错
const city = activity.location?.city // undefined，不会报错
```

### 日期处理

| 做法 | 写法 | 什么时候用 |
| --- | --- | --- |
| 当前时间戳 | `Date.now()` | 记录、比较 |
| 转成 Date | `new Date(ts)` | 格式化、取值 |
| 格式化 | `` `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}` `` | 显示日期 |
| 补零 | `String(n).padStart(2, '0')` | 月份/日期/时间补零 |
| 转 ISO 字符串 | `d.toISOString()` | 传给后端 |
| 日期差 | `(a - b) / 86400000` | 计算相隔天数 |

```js [日期最小示例]
const pad = (n) => String(n).padStart(2, '0')

function formatDate(ts) {
  const d = new Date(ts)
  // ✓ 补零，避免出现 2026-9-3 这种不整齐的格式
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

formatDate(Date.now()) // '2026-09-13 18:30'
```

::: warning 月份从 0 开始
`getMonth()` 返回 `0` 到 `11`，表示 1 月到 12 月。**显示时要 `+ 1`**，
这是最容易错的一个地方。
:::

### 字符串

| 方法 | 作用 | 什么时候用 |
| --- | --- | --- |
| `trim()` | 去首尾空格 | 提交表单前清洗 |
| `includes(s)` | 包不包含子串 | 前端搜索 |
| `startsWith` / `endsWith` | 前缀 / 后缀判断 | 判断文件类型 |
| `split(sep)` | 切成数组 | 处理逗号分隔字符串 |
| `slice(start, end)` | 截取 | 截断长文本 |
| `padStart(len, ch)` | 前面补字符 | 时间补零、编号补位 |
| `replace` / `replaceAll` | 替换 | 文本处理 |
| `toLowerCase` / `toUpperCase` | 大小写转换 | 搜索时忽略大小写 |

```js [字符串最小示例]
const raw = '  活动名称：迎新晚会  '

raw.trim() // '活动名称：迎新晚会'
raw.trim().includes('迎新') // true

const csv = '1,2,3'
csv.split(',') // ['1', '2', '3']

// 截断长标题
function truncate(text, max = 12) {
  return text.length > max ? `${text.slice(0, max)}…` : text
}

// ✓ 搜索时忽略大小写
const matched = 'Basketball'.toLowerCase().includes('basket'.toLowerCase())
```

### 数字与全局

| API | 作用 | 什么时候用 |
| --- | --- | --- |
| `Number(x)` | 转数字 | 转换 query 参数 |
| `parseInt(x, 10)` | 转整数 | 取整 |
| `x.toFixed(2)` | 保留两位小数 | 显示金额、比例 |
| `Math.ceil` / `floor` / `round` | 上取整 / 下取整 / 四舍五入 | 算总页数用 `ceil` |
| `Number.isNaN(x)` | 是不是 NaN | 校验转换结果 |
| `structuredClone(obj)` | 深拷贝 | 复制复杂对象（比 JSON 拷贝强） |
| `JSON.stringify` / `parse` | 序列化 / 反序列化 | 存 `localStorage`、传数据 |

```js
// ✓ 算总页数的标准写法
const pageCount = Math.ceil(total / pageSize)

// ✓ 深拷贝：支持 Date、Map，比 JSON 方案好
const copy = structuredClone(activity)
```

## 用户端（uni-app）速查

这一节是[用户端专栏](/mobile/)的速查。**这里的 API 在管理端用不上，管理端的写法在这里也大多不能用。**

### 页面生命周期

从 `@dcloudio/uni-app` 导入，写在 `<script setup>` 里。

| 钩子 | 什么时候触发 | 典型用途 |
| --- | --- | --- |
| `onLoad(options)` | 页面加载一次，`options` 是 URL 查询参数 | 拿 `id`、发首次请求 |
| `onShow()` | 每次页面显示（含从后台返回） | 刷新名额、刷新列表 |
| `onReady()` | 首次渲染完成 | 需要拿 DOM 或节点信息时 |
| `onHide()` | 页面隐藏 | 暂停定时器 |
| `onUnload()` | 页面销毁 | 清理定时器、取消请求 |
| `onPullDownRefresh()` | 下拉刷新，需 `pages.json` 开 `enablePullDownRefresh` | 重置到第一页重新拉 |
| `onReachBottom()` | 滚动到底部（默认距底 50 px 触发） | 加载下一页 |
| `onShareAppMessage()` | 用户点右上角转发 | 小程序分享 |

```vue
<script setup>
import { onLoad, onShow, onPullDownRefresh, onReachBottom } from '@dcloudio/uni-app'
import { ref } from 'vue'

const id = ref('')

onLoad((options) => {
  // ✓ URL 参数只能传字符串，中文要 encodeURIComponent
  id.value = options.id
  loadDetail()
})

onPullDownRefresh(async () => {
  try {
    await loadList()
  } finally {
    // ✓ 必须调用，否则下拉动画不会收回去
    uni.stopPullDownRefresh()
  }
})
</script>
```

### 页面跳转

| API | 作用 | 注意 |
| --- | --- | --- |
| `uni.navigateTo({ url })` | 打开新页面，保留当前页 | 页面栈最多 10 层 |
| `uni.redirectTo({ url })` | 关闭当前页，打开新页 | 登录成功后用它，避免返回登录页 |
| `uni.switchTab({ url })` | 切到 tabBar 页面 | **只能跳 tabBar 页，且不能带参数** |
| `uni.reLaunch({ url })` | 关闭所有页面再打开 | 退出登录时用 |
| `uni.navigateBack({ delta: 1 })` | 返回上 N 层 | `delta` 默认 1 |

```js
// ✓ 参数只能拼在 url 上，中文要编码
uni.navigateTo({ url: `/pages/activity/detail?id=${id}` })
uni.navigateTo({ url: `/pages/activity/list?keyword=${encodeURIComponent(keyword)}` })

// ✗ 这样传参收不到
uni.navigateTo({ url: '/pages/activity/detail', params: { id } })
```

### 常用 uni API

| API | 作用 | 管理端的对应物 |
| --- | --- | --- |
| `uni.request({ url, method, data, header })` | 发 HTTP 请求 | `axios` |
| `uni.getStorageSync(k)` / `setStorageSync(k, v)` | 读写本地存储（同步） | `localStorage` |
| `uni.removeStorageSync(k)` | 删一个键 | `localStorage.removeItem` |
| `uni.showToast({ title, icon })` | 轻提示，`icon` 取 `none` 时是纯文字 | `ElMessage` |
| `uni.showModal({ title, content, success })` | 带确认的弹窗，返回 `confirm` | `ElMessageBox.confirm` |
| `uni.showLoading()` / `hideLoading()` | 全屏加载 | `v-loading` |
| `uni.setNavigationBarTitle({ title })` | 改导航栏标题 | 路由 meta 里的标题 |
| `uni.stopPullDownRefresh()` | 结束下拉刷新 | 无 |
| `uni.login({ provider })` | 拿微信临时 `code` | 无 |
| `uni.getSystemInfoSync()` | 拿设备信息 | `window.innerWidth` |

### pages.json 必备片段

```json [src/pages.json]
{
  "easycom": {
    "autoscan": true,
    "custom": {
      "^wd-(.*)": "@wot-ui/ui/components/wd-$1/wd-$1.vue"
    }
  },
  "pages": [
    { "path": "pages/activity/list", "style": { "navigationBarTitleText": "活动", "enablePullDownRefresh": true } },
    { "path": "pages/activity/detail", "style": { "navigationBarTitleText": "活动详情" } },
    { "path": "pages/signup/form", "style": { "navigationBarTitleText": "报名" } },
    { "path": "pages/my-signup/list", "style": { "navigationBarTitleText": "我的报名" } },
    { "path": "pages/mine/index", "style": { "navigationBarTitleText": "我的" } }
  ],
  "tabBar": {
    "list": [
      { "pagePath": "pages/activity/list", "text": "活动" },
      { "pagePath": "pages/my-signup/list", "text": "我的报名" },
      { "pagePath": "pages/mine/index", "text": "我的" }
    ]
  }
}
```

| 要点 | 说明 |
| --- | --- |
| `pages` 第一项 | 就是启动页 |
| 新加页面 | **必须**在这里加一条，否则跳转失败 |
| `enablePullDownRefresh` | 默认 `false`，不开的话 `onPullDownRefresh` 不触发 |
| `tabBar.list` | 只能 2 到 5 项，页面必须同时在 `pages` 里 |
| 改完配置 | 常常要重启开发服务器才生效 |

### 条件编译

按平台保留不同代码。**注释符号跟位置有关，写错就不生效。**

| 位置 | 写法 |
| --- | --- |
| JS | `// #ifdef H5` … `// #endif` |
| 模板 | `<!-- #ifdef H5 -->` … `<!-- #endif -->` |
| 样式 | `/* #ifdef H5 */` … `/* #endif */` |
| JSON | 用 `#ifdef` 注释（`pages.json` / `manifest.json` 支持） |

```js
// #ifdef H5
// 只有 H5 平台会编译这段
window.location.reload()
// #endif

// #ifdef MP-WEIXIN
// 只有微信小程序会编译这段
uni.showShareMenu({ withShareTicket: true })
// #endif
```

常用平台标识：`H5`、`MP-WEIXIN`、`MP-ALIPAY`、`APP-PLUS`。
`#ifndef` 是“不包含该平台”。

### 单位与样式

| 规则 | 说明 |
| --- | --- |
| `750rpx` 永远等于屏幕宽度 | 设计稿标注多少 px，就写多少 rpx，**不要除以 2** |
| 什么时候用 px | 一条 1 px 的细线、阴影、`border-radius` 的极小值 |
| 全局样式写在哪 | `App.vue` 的 `<style>`，页面背景色设在 `page` 选择器上 |
| 安全区 | `padding-bottom: calc(20rpx + env(safe-area-inset-bottom))` |
| 页面根节点 | 用 `<view>`，不要用 `<div>`（H5 能跑，小程序不行） |
| 文本节点 | 用 `<text>`，短文本可以省，长文本建议加 |

### Wot UI 常用组件与两个 API 差异

| 组件 | 用途 |
| --- | --- |
| `wd-button` / `wd-cell` / `wd-cell-group` | 按钮、列表项、分组 |
| `wd-input` / `wd-textarea` / `wd-search` | 输入、多行输入、搜索框 |
| `wd-form` / `wd-form-item` | 表单与字段 |
| `wd-tag` / `wd-divider` / `wd-empty` / `wd-skeleton` | 标签、分割线、空态、骨架屏 |
| `wd-loadmore` / `wd-segmented` / `wd-popup` | 加载更多、分段筛选、弹层 |
| `wd-toast` / `wd-dialog` | **必须写进页面模板**，否则不渲染 |

两处最容易按别的库的习惯写错的：

| 项 | ✗ 别的库的写法 | ✓ Wot UI 的写法 |
| --- | --- | --- |
| 校验规则 | `:rules="rules"` | `:schema="schema"`（配 `zodAdapter` 或自定义） |
| 字段标签 | `label="联系方式"` | `title="联系方式"` |
| 字段名 | `v-model` 绑一个字符串 | `prop="contact"` |

```vue
<script setup>
import { ref } from 'vue'
import { useToast } from '@wot-ui/ui'

const form = ref(null)
const toast = useToast()

async function submit() {
  // ✓ validate() 返回 { valid, errors }，不抛异常
  const { valid } = await form.value.validate()
  if (!valid) return
  // ...提交逻辑
}
</script>

<template>
  <wd-form ref="form" :model="model" :schema="schema">
    <wd-form-item title="联系方式" prop="contact">
      <wd-input v-model="model.contact" />
    </wd-form-item>
  </wd-form>
  <wd-toast />
</template>
```

---

上一节：[附录总览](/appendix/) ·
下一节：[常见报错与排查](/appendix/errors)
