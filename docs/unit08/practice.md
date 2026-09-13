# 单元 8 课后练习

本单元的练习围绕“让组件更通用、让逻辑更值钱”展开。**三道必做题，一道选做题。**

各节末尾还有针对单点的小练习，这一页是单元级的产出。

## 必做题

### 练习 1 · 抽一个 useFetch 组合式函数

参考 [8.4 的 useRequest](/unit08/04-composables)，实现 `useFetch(url, options)`，
并在活动列表页替换掉原来那段复制粘贴的请求代码。

**要求**：

1. 放在 `src/composables/useFetch.js`，用 `use` 前缀，一个函数一个文件。
2. 返回**对象**，至少包含 `data`、`loading`、`error`、`refresh`。
3. 挂载时自动请求一次（可用 `immediate` 关闭）。
4. 用 `AbortController` 处理竞态，并在组件卸载时取消未完成的请求。
5. 收到非 2xx 响应时要把 `error` 设上，而不是静默失败。

**接口示意**

```js [src/composables/useFetch.js]
export function useFetch(url, options = {}) {
  // 实现你的版本
  // return { data, loading, error, refresh, cancel }
}
```

```vue [src/views/ActivityListView.vue]
<script setup>
import { useFetch } from '@/composables/useFetch'

const { data: activities, loading, error, refresh } = useFetch('/api/activities')
</script>

<template>
  <p v-if="loading">加载中…</p>
  <p v-else-if="error">加载失败：{{ error.message }}</p>
  <ul v-else>
    <li v-for="a in activities" :key="a.id">{{ a.title }}</li>
  </ul>
</template>
```

**验收标准**

| 项目 | 要求 |
| --- | --- |
| 命名与位置 | `use` 前缀，放在 `src/composables/`，文件名与函数名一致 |
| 不留残留状态 | 组件卸载后不再更新 `data` / `loading` / `error`，控制台无警告 |
| 竞态处理 | 快速切换筛选条件时，界面显示的是最后一次请求的结果 |
| 与业务解耦 | 函数内部不出现“活动”“报名”这类业务词，URL 完全来自参数 |
| 错误可见 | 接口 500 或断网时，`error` 有值且页面显示出来 |

::: warning 不合格的写法
```js
// ✗ 把业务逻辑写进了组合式函数
export function useActivityList() {
  const data = ref([])
  async function load() {
    data.value = await axios.get('http://10.0.0.8:8080/api/activities')  // ✗ 地址写死
  }
  return { data, load }
}
```

地址写死、名字带业务：这个函数只能在活动列表页用，等于没抽。
**判断标准是“能不能原样复制到另一个项目里”。**
:::

### 练习 2 · 用插槽实现可复用卡片组件

实现一个 `BaseCard.vue`，接收插槽三个区域：头部、默认内容、底部。

**要求**：

1. 头部、底部都有**后备内容** —— 不填时显示默认样式，不报错、不留空白。
2. 底部操作区支持“没有操作时不显示整块区域”。
3. 支持一个 `#header-extra` 之类的扩展区域，用来放右上角的小按钮（比如“更多”菜单），
   不填时不占位。
4. 至少在两个页面用上：活动详情（展示活动信息）与报名审核（展示审核卡片）。

**接口示意**

```vue [src/components/BaseCard.vue]
<template>
  <section class="base-card">
    <header class="base-card-head">
      <slot name="header"><span>未命名卡片</span></slot>
      <!-- 扩展区：仅在传入时渲染 -->
      <div v-if="$slots['header-extra']" class="base-card-extra">
        <slot name="header-extra" />
      </div>
    </header>

    <div class="base-card-body">
      <slot />
    </div>

    <footer v-if="$slots.footer" class="base-card-foot">
      <slot name="footer" />
    </footer>
  </section>
</template>
```

**验收标准**

| 项目 | 要求 |
| --- | --- |
| 三个区域 | 头部、默认、底部都能独立填入，互不干扰 |
| 后备内容 | 不传 `#header` 时显示默认标题，不出现空白的头部 |
| 条件渲染 | 不传 `#footer` 时底部整块不渲染，不是渲染一个空框 |
| 复用 | 至少两个页面的用法不同，且组件本身一行没改 |
| 命名 | 插槽名用短横线（`header-extra`），语义清楚 |

::: details 提示：`$slots` 怎么用
在模板里 `$slots.footer` 为真表示使用方传了 `#footer`。
也可以写成 `v-if="$slots.footer || $slots.header"` 来统一控制渲染。

注意：**“传了空的 `<template #footer></template>`”也算传了**，
`$slots.footer` 会是真。如果想让空内容也隐藏，需要额外判断，但通常不必这么严格。
:::

### 练习 3 · 用 KeepAlive 保留列表状态

实现“活动列表 → 详情 → 返回”时，列表的**搜索条件与页码**还在。

**要求**：

1. 在 `App.vue` 的 `<RouterView>` 外用 `KeepAlive`，只缓存列表页。
2. 列表页用 `defineOptions({ name: 'ActivityList' })` 补上组件名，让 `include` 能匹配。
3. 用 `onActivated` / `onDeactivated` 打印日志，验证“缓存生效”而不是“意外重建”。
4. 再加一个“刷新”按钮，手动调用接口刷新，验证缓存与刷新能共存。

**接口示意**

```vue [src/App.vue]
<script setup>
import { RouterView } from 'vue-router'
</script>

<template>
  <RouterView v-slot="{ Component }">
    <KeepAlive include="ActivityList">
      <component :is="Component" />
    </KeepAlive>
  </RouterView>
</template>
```

```vue [src/views/ActivityListView.vue]
<script setup>
import { ref, onMounted, onActivated, onDeactivated } from 'vue'

defineOptions({ name: 'ActivityList' })

const keyword = ref('')
const page = ref(1)

onMounted(() => console.log('列表页 mounted（只应出现一次）'))
onActivated(() => console.log('列表页 activated（每次回来都出现）'))
onDeactivated(() => console.log('列表页 deactivated（切走时出现）'))
</script>
```

**验收标准**

| 项目 | 要求 |
| --- | --- |
| 状态保留 | 输入关键词、翻到第 3 页，进详情再返回，条件与页码都还在 |
| 缓存范围 | 详情页**没有**被缓存，每次进入都重新请求 |
| 日志证据 | 控制台里 `mounted` 只出现一次，`activated` 每次返回都出现 |
| 清理正确 | 列表页里的定时器 / 监听在 `onDeactivated` 里处理，不是只在 `onUnmounted` |

::: danger 容易漏的一点
`KeepAlive` 缓存的组件**不会触发 `onUnmounted`**。如果你在列表页里起了定时器、
绑了全局监听，只写在 `onUnmounted` 里清理，那切走之后它还在跑。

**缓存组件的清理要放在 `onDeactivated` 里**（需要恢复时在 `onActivated` 里重新建立）。
:::

## 选做题

### 练习 4 · v-permission 按钮级权限

写一个 `v-permission` 指令，配合角色数据控制按钮显示。

**要求**：

1. 指令写在 `src/directives/permission.js`，支持传单个权限码或数组。
2. 数组时“命中任意一个”即放行。
3. 在活动管理页用它控制“审核通过”“驳回”“删除活动”三个按钮。
4. 在文档里用一段注释写清楚：**这只是体验优化，真正的权限校验必须在后端。**

**接口示意**

```vue [控制按钮显示]
<template>
  <!-- 只有拥有 signup:review 权限才显示 -->
  <button v-permission="'signup:review'" @click="approve">审核通过</button>

  <!-- 命中任意一个权限即显示 -->
  <button v-permission="['activity:edit', 'activity:delete']" @click="remove">删除活动</button>
</template>
```

**参考思路**：参考 [8.5 的实战三](/unit08/05-directives#实战三v-permission)。
权限数据可以先用一个模块级的 `ref` 模拟：

```js [src/composables/useAuth.js（模拟版）]
import { ref } from 'vue'

const currentUser = ref({
  name: '李老师',
  role: 'reviewer',
  permissions: ['signup:review']
})

export function useAuth() {
  return { currentUser }
}
```

**验收标准**

| 项目 | 要求 |
| --- | --- |
| 单值与数组 | `v-permission="'a'"` 和 `v-permission="['a', 'b']"` 都能用 |
| 判定正确 | 无权限时元素不出现在 DOM 里（用开发者工具确认） |
| 命名 | 注册名是 `permission`，模板里写 `v-permission` |
| 边界说明 | 代码注释里写明前端权限不是安全边界，后端必须独立校验 |

## 自检标准

本单元做完后逐条自查：

- [ ] 能在同一个组件里同时用三种插槽，并说清 props 与插槽的分工
- [ ] 写的作用域插槽能让父组件决定子组件数据的显示方式
- [ ] 用过 `provide/inject`，且对提供出去的状态加了 `readonly`
- [ ] 能说清 `Transition` 六个 class 各在什么时机生效
- [ ] 给列表做过 `TransitionGroup` 动画，并知道为什么必须给 `key`
- [ ] 用 `KeepAlive` 缓存过页面，并在 `onActivated` 里处理过刷新
- [ ] 说得清弹窗为什么必须 `Teleport` 到 `body`（三堵墙）
- [ ] 抽过至少两个组合式函数，返回值是对象
- [ ] 写过一个自定义指令，并在 `unmounted` 里做过清理
- [ ] 知道前端权限控制不能替代后端校验

全部打勾，这个单元过关。

## 常见问题

::: details 组合式函数和普通工具函数到底怎么分
看里面有没有**响应式状态或生命周期钩子**。

- 有 `ref` / `computed` / `watch` / `onMounted` → 组合式函数，放 `src/composables/`，`use` 开头。
- 只是纯计算（格式化日期、校验手机号、计算时段是否重叠）→ 工具函数，
  放 `src/utils/`，普通命名。

分不清时的默认做法：先当工具函数写，等它真的需要响应式状态了再改名字、换目录。
:::

::: details 为什么不直接用 @vueuse/core
项目里**应该用**。`@vueuse/core` 14.4.0 里有 `useMouse`、`useLocalStorage`、
`useFetch` 等大量成熟实现，比手写的更稳。

这个单元要求自己写，是为了让你理解里面发生了什么 —— 知道 `AbortController` 怎么取消请求、
清理逻辑写在哪、`shallowRef` 和 `ref` 差在哪。**先会手写，再用库，遇到问题才知道从哪查。**
:::

::: details KeepAlive 缓存了之后数据不更新怎么办
两个办法：

1. 在 `onActivated` 里重新请求，拿到最新数据。
2. 用一个“过期时间”标记：记录上次请求的时间，回来时超过一定时长才重新请求。

**不要**为了“每次都是新的”就干脆不用 `KeepAlive` —— 那就把“保留搜索条件”这个体验一起丢了。
先想清楚哪些数据要保、哪些要刷新，再写代码。
:::

::: details 案例 08 太难了，可以跳过吗
案例 08 是加分任务，不完成不影响这个单元过关。但建议至少把第二部分（坐标换算与
设备像素比）和第三部分（撤销重做的双栈）读懂 —— 这两块是通用的：

- dpr 换算在处理任何 canvas、地图、图表时都会遇到。
- 撤销重做的双栈设计是所有“可撤销编辑器”的通用模式，
  从画板到富文本编辑器都用同一套思路。

读懂思路比写全代码更重要。
:::

---

上一节：[案例 08 · 画板与撤销重做](/unit08/07-case-canvas) ·
下一单元：[单元 9 · 路由 Vue Router 与登录鉴权](/unit09/)
