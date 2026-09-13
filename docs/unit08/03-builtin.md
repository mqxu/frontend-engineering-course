# 8.3 内置组件

## 这些需求你是不是都自己造过

打开第七周的活动管理页面，数一数下面这些需求：

- 点“发布活动”弹出抽屉，希望它不是“啪”地出现，而是从右侧滑进来。
- 审核通过后，列表里那条记录渐隐消失，剩下的记录平滑地补上来。
- 活动列表 → 详情 → 返回，列表的搜索条件和页码没了，又要重新填一遍。
- 模态框被父容器的 `overflow: hidden` 裁掉了，只露出半截。
- 活动详情页体积很大，第一次打开白屏了两秒。

这五件事，Vue 都有**内置组件**直接解决：`Transition`、`TransitionGroup`、`KeepAlive`、
`Teleport`、`Suspense`。它们不用安装，模板里写上就能用。

这一节逐个讲，每个给一个最小可运行的例子。**重点是搞清每个解决什么问题、什么时候该用。**

## Transition：单元素的进出场动画

最简单的用法，用 `<Transition>` 包住一个会显示 / 隐藏的元素：

```vue [src/components/PublishDrawer.vue]
<script setup>
import { ref } from 'vue'

const visible = ref(false)
</script>

<template>
  <button @click="visible = !visible">发布活动</button>

  <Transition name="slide">
    <div v-if="visible" class="drawer">
      <h3>发布活动</h3>
      <p>填写活动信息…</p>
    </div>
  </Transition>
</template>

<style scoped>
/* 进场：从右侧滑入 */
.slide-enter-from {
  transform: translateX(100%);
  opacity: 0;
}
.slide-enter-active {
  transition: all 0.3s ease;
}
.slide-enter-to {
  transform: translateX(0);
  opacity: 1;
}

/* 离场：滑回右侧 */
.slide-leave-from {
  transform: translateX(0);
  opacity: 1;
}
.slide-leave-active {
  transition: all 0.3s ease;
}
.slide-leave-to {
  transform: translateX(100%);
  opacity: 0;
}
</style>
```

`name="slide"` 决定了六个 class 的前缀。默认前缀是 `v-`（不写 `name` 时）。

### 六个 class 的作用时机

这是 `Transition` 的核心，必须记清楚：

| class | 什么时候加 | 什么时候移除 | 通常写什么 |
| --- | --- | --- | --- |
| `slide-enter-from` | 进场**开始前** | 进场第 1 帧后 | 起始状态（透明度 0、位移） |
| `slide-enter-active` | 进场**全程** | 进场结束后 | `transition` 时长与缓动 |
| `slide-enter-to` | 进场第 1 帧后 | 进场结束后 | 结束状态 |
| `slide-leave-from` | 离场**开始前** | 离场第 1 帧后 | 起始状态 |
| `slide-leave-active` | 离场**全程** | 离场结束后 | `transition` 时长与缓动 |
| `slide-leave-to` | 离场第 1 帧后 | 离场结束后 | 结束状态 |

记忆方法：`from` 是起点、`to` 是终点、`active` 是“这段时间用什么过渡”。
`enter` 是出现，`leave` 是消失。

大多数情况只需要写 `-enter-from`、`-enter-active`、`-leave-to`、`-leave-active` 四个 ——
`-enter-to` 和 `-leave-from` 的样式通常就是元素的默认样式。

::: tip `appear`：首次渲染也要动画
默认情况下，元素**首次渲染**时不播动画。加上 `appear` 属性，初次出现也走一遍进场：

```html
<Transition name="fade" appear>
  <div v-if="visible">内容</div>
</Transition>
```
:::

### mode：两个元素之间的切换

`Transition` 里如果有两个元素互相切换（比如登录表单的“账号登录 / 扫码登录”），
默认行为是**同时进行** —— 新元素进场的同时旧元素在离场，两个会重叠、跳动。

```html
<!-- ✗ 默认：两个元素同时存在，会挤在一起 -->
<Transition name="fade">
  <div v-if="tab === 'account'">账号登录</div>
  <div v-else>扫码登录</div>
</Transition>
```

用 `mode` 让它们排队：

```html
<!-- ✓ out-in：先出后进，位置不会重叠 -->
<Transition name="fade" mode="out-in">
  <div v-if="tab === 'account'">账号登录</div>
  <div v-else>扫码登录</div>
</Transition>
```

`mode` 有两个值：

- `out-in`：旧元素离场**完成后**，新元素才进场。最常用。
- `in-out`：新元素先进场，完成后旧元素再离场。用得少，因为会“叠”一下。

::: warning `Transition` 只能包一个根元素
```html
<!-- ✗ 会报警告，同时只有一个子节点能被动画 -->
<Transition name="fade">
  <div>标题</div>
  <div>正文</div>
</Transition>
```

如果里面是 `v-if` / `v-else` 两个分支，同一时刻只会渲染一个，这是允许的；
但若是**两个同时存在**的兄弟元素，就不行。列表动画要用下面的 `TransitionGroup`。
:::

## TransitionGroup：列表动画

活动列表里点“下架”，希望那一行淡出，后面的行平滑补位。这时元素是**一组**，
元素数量会变，用 `TransitionGroup`：

```vue [src/components/ActivityList.vue]
<script setup>
import { ref } from 'vue'

const activities = ref([
  { id: 1, title: '春季运动会' },
  { id: 2, title: '编程马拉松' },
  { id: 3, title: '摄影展' }
])

function offline(id) {
  activities.value = activities.value.filter((a) => a.id !== id)
}
</script>

<template>
  <TransitionGroup name="list" tag="ul" class="activity-list">
    <li v-for="item in activities" :key="item.id" @click="offline(item.id)">
      {{ item.title }}
    </li>
  </TransitionGroup>
</template>

<style scoped>
.list-move,
.list-enter-active,
.list-leave-active {
  transition: all 0.3s ease;
}

/* 补位：剩下的元素移动到新位置时的中间态 */
.list-move {
  transition: transform 0.3s ease;
}

/* 离场元素脱离文档流，其他元素才能立刻补位 */
.list-leave-active {
  position: absolute;
  width: 100%;
}

.list-enter-from,
.list-leave-to {
  opacity: 0;
  transform: translateX(30px);
}
</style>
```

注意几个点：

- `tag="ul"` 指定 `TransitionGroup` 渲染成什么标签，不写则渲染成 `<span>`。
- **`:key` 是必须的。** 没有 `key`，Vue 无法识别“哪个是新增的、哪个还在”，
  动画和补位都无从谈起。
- `-move` 这个 class 是 `TransitionGroup` 独有的，用来做“补位移动”动画。
- `-leave-active` 上要加 `position: absolute`，让离场的元素脱离布局，其他元素才能马上补位。

::: details 为什么必须给 key
`TransitionGroup` 判断“某一项是新增、移除还是移动”，靠的是虚拟节点上的 `key`。
没有 `key` 时，列表更新只能按位置逐项比对，删掉中间一项时，Vue 会认为“最后一项变了内容”，
于是播的是“内容变化”而不是“最后一项被删除”，动画就乱了。

**一句话：列表里凡是会增删移动的，`key` 都要写，而且要写稳定的唯一标识（一般用 `id`，别用 `index`）。**
:::

## KeepAlive：组件缓存

活动列表有搜索框和页码。点进详情再返回，条件全清了 —— 因为列表页组件被销毁重建了。

`KeepAlive` 把组件**缓存**起来，不销毁：

```vue [src/App.vue]
<template>
  <RouterView v-slot="{ Component }">
    <KeepAlive>
      <component :is="Component" />
    </KeepAlive>
  </RouterView>
</template>
```

这样来回切换时，列表页的组件实例被保留，`ref` 里的搜索条件、页码都还在。

### include / exclude / max

缓存不能无限制，也不该什么都缓存。三个属性控制范围：

```html
<!-- 只缓存组件名为 ActivityList 和 SessionList 的 -->
<KeepAlive include="ActivityList,SessionList">
  <component :is="Component" />
</KeepAlive>

<!-- 用数组形式也一样，还支持正则 -->
<KeepAlive :include="[/^Activity/, 'SessionList']">
  <component :is="Component" />
</KeepAlive>

<!-- 除了编辑页，其他都缓存 -->
<KeepAlive exclude="ActivityEdit">
  <component :is="Component" />
</KeepAlive>

<!-- 最多缓存 10 个，超过就淘汰最久未用的 -->
<KeepAlive :max="10">
  <component :is="Component" />
</KeepAlive>
```

::: warning include 匹配的是“组件名”，不是路由名
这里填的 `ActivityList` 必须是**组件的 `name`**。用 `<script setup>` 写的组件默认没有 `name`，
需要用 `defineOptions` 补上：

```vue [src/views/ActivityListView.vue]
<script setup>
defineOptions({ name: 'ActivityList' })
</script>
```

很多人写了 `include` 却不生效，就是卡在这里 —— 组件根本没有名字，自然匹配不上。
:::

::: tip 缓存了之后，怎么知道“又回到这个页面了”
`KeepAlive` 缓存的组件**不会重新走 `onMounted`**。想在“每次回到这个页面”时刷新数据，
要用 `onActivated`：

```js [src/views/ActivityListView.vue]
import { onActivated, onMounted } from 'vue'

onMounted(() => {
  console.log('只在第一次进入时执行一次')
})

onActivated(() => {
  console.log('每次（从缓存）激活时都会执行')
})
```

对应的还有 `onDeactivated`，在被切走时触发。**注意 `onUnmounted` 在这种组件里不会触发**，
清理副作用要放在 `onDeactivated` 里。
:::

### 什么时候该缓存

| 场景 | 是否缓存 |
| --- | --- |
| 带搜索、筛选、分页的列表页 | 缓存，返回时保留条件 |
| 详情页 | 不缓存，每次都要拿最新数据 |
| 标签页之间切换 | 缓存，切换不丢状态 |
| 表单页 | 不缓存，离开就该丢弃草稿（除非有草稿保存） |
| 数据看板大屏 | 按需，数据实时性要求高就不缓存 |

判断依据：**回来后希望看到“上次那个状态”，就缓存；希望看到“最新的”，就不缓存。**

## Teleport：把内容送到别处

模态框经常被父容器的样式裁剪，露不全。原因通常是三堵墙：

```text
父容器 overflow: hidden   →  超出部分被裁掉
父容器 position: relative  →  子元素的定位以它为参照
父容器设置了 transform      →  形成了一个新的层叠上下文
```

任何一条都可能让 `z-index: 9999` 也不管用 —— 因为 `z-index` 只在同一个层叠上下文里比较，
被 `transform` 关进去之后，跟外面的元素根本不在同一个层级里比。

`Teleport` 的解决办法很直接：**把这个节点渲染到页面上另一个位置去**，通常是 `body` 下。

```vue [src/components/ConfirmDialog.vue]
<template>
  <Teleport to="body">
    <div v-if="visible" class="dialog-mask">
      <div class="dialog">…</div>
    </div>
  </Teleport>
</template>
```

`to` 接受任何 CSS 选择器，`to="body"` 就是送到 `body` 下。这样模态框不在那个
`overflow: hidden` 的容器里了，三堵墙一次全部绕开。

::: tip 别忘了 v-if 写在 Teleport 里面
如果你希望“关闭时 `body` 下不残留这个节点”，把 `v-if` 写在 `<Teleport>` **内部的元素上**：

```html
<Teleport to="body">
  <div v-if="visible">…</div>
</Teleport>
```

如果把 `v-if` 写在 `<Teleport>` 标签上（`<Teleport v-if="visible">`），也能工作，
但每次开关都会重建整个 Teleport 而不是只切换内容，元素上的过渡动画会更难做。
配合 `Transition` 时，**顺序是 `Teleport` 在外、`Transition` 在内、`v-if` 在最内层元素上**。
:::

```html
<!-- 推荐的三层顺序 -->
<Teleport to="body">
  <Transition name="dialog">
    <div v-if="visible" class="dialog-mask">…</div>
  </Transition>
</Teleport>
```

::: details 还有 `disabled` 属性
`<Teleport disabled>` 会临时“关掉传送”，内容渲染在原位。常见于响应式布局：
桌面端用弹窗（传送到 `body`），移动端改成内嵌面板（不传送）。
:::

## Suspense 与异步组件

活动详情页体积大，第一次打开白屏。可以把它做成**异步组件**，用到时才加载：

```js [src/router/index.js]
import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/activities/:id',
      // 用到这个路由时才去下载对应 chunk
      component: () => import('@/views/ActivityDetailView.vue')
    }
  ]
})
```

`defineAsyncComponent` 则用于**组件级的异步加载**，可以在等待时显示占位：

```vue [src/components/HeavyChart.vue 的加载方]
<script setup>
import { defineAsyncComponent } from 'vue'

const HeavyChart = defineAsyncComponent({
  loader: () => import('@/components/HeavyChart.vue'),
  // 加载中显示的组件
  loadingComponent: LoadingSpinner,
  // 失败时显示的组件
  errorComponent: LoadFailed,
  // 等待多久才显示 loading，避免闪一下
  delay: 200,
  // 超时时间
  timeout: 10000
})
</script>

<template>
  <HeavyChart :data="chartData" />
</template>
```

如果不想自己写加载态和错误态，用 `<Suspense>` 包一层，它能自动接管：

```vue [src/views/DashboardView.vue]
<script setup>
import { defineAsyncComponent } from 'vue'

const ActivityStats = defineAsyncComponent(() => import('@/components/ActivityStats.vue'))
</script>

<template>
  <Suspense>
    <!-- 默认插槽：加载完成后显示的内容 -->
    <ActivityStats />

    <template #fallback>
      <!-- 加载过程中显示的骨架 -->
      <div class="skeleton">数据加载中…</div>
    </template>
  </Suspense>
</template>
```

`<Suspense>` 还有一层能力：**等异步 `setup` 完成**。一个组件的 `<script setup>`
里如果写了顶层 `await`，它就成了异步组件，`<Suspense>` 会等它 resolve 后再渲染：

```vue [src/views/ActivityDetailView.vue]
<script setup>
// 顶层 await：这个组件必须在 <Suspense> 里使用
const detail = await fetchActivityDetail(route.params.id)
</script>
```

::: warning Suspense 目前仍是实验性功能
`<Suspense>` 在 Vue 3.5 里仍标记为实验性，API 可能变化，而且真正的错误处理要靠
`onErrorCaptured` 或 `errorComponent` 补齐。

**实际项目里的稳妥选择**：路由懒加载（`() => import(...)`）必备，配合每个页面自己
写加载态、错误态、空态（[单元 5 的四态规范](/unit05/05-four-states)）。
`<Suspense>` 用在明确的场景（外层统一管理多个异步子组件的加载态），别为了用它而用。
:::

### 路由懒加载与它的关系

| 做法 | 粒度 | 触发时机 | 写在哪 |
| --- | --- | --- | --- |
| `() => import(...)` | 一个路由一个 chunk | 访问该路由时 | 路由表 |
| `defineAsyncComponent` | 一个组件一个 chunk | 该组件第一次渲染 | 组件里 |
| 直接 `import` | 打进主包 | 应用启动时 | 任何地方 |

三者的共同点：**都是为了减小首屏要下载的代码量**。路由懒加载是项目里最常用、收益最直接的做法，
构建后你能在 `dist/assets/` 下看到一个个独立的 `js` 文件，每个对应一个路由页面。
具体怎么验证，[单元 12 的构建优化](/unit12/02-build-optimize)会展开。

## 小结

- `Transition` 做单元素进出场，六个 class 分 `enter` / `leave` 两组，`from` 起点、`to` 终点、
  `active` 过渡；两元素切换用 `mode="out-in"`。
- `TransitionGroup` 做列表动画，**必须给 `key`**，`-move` 做补位，`-leave-active` 要脱离文档流。
- `KeepAlive` 缓存组件实例，`include` 匹配的是组件 `name`（`<script setup>` 要用 `defineOptions`
  补），缓存组件用 `onActivated` 而不是 `onMounted`。
- `Teleport` 把节点送到别处，弹窗送到 `body` 是为了绕开 `overflow` 裁剪、定位上下文、
  层叠上下文三堵墙。
- 异步组件用 `defineAsyncComponent`；路由懒加载 `() => import(...)` 是最常用的做法；
  `<Suspense>` 是实验性的，稳妥方案是每个页面自己写四态。

## 常见坑

::: details 坑 1：Transition 里的元素没有变化，动画不触发
现象：`v-if` 一直是 `true`，动画不播。

原因：`Transition` 只在**元素插入或移除**时触发。只是切换 `class` 或内容不会触发。

处理：确认触发动画的是 `v-if` / `v-show` 的真假变化，或者配合 `<component :is>` 切换组件。
用 `v-show` 也可以（内部走的是 `display` 切换 + 同样的 class）。
:::

::: details 坑 2：列表动画里用 index 当 key，删除时全乱
现象：删掉第一项，后面每一项都播了一次动画。

原因：`key` 用了 `index`，删除后所有元素的 `index` 都变了，Vue 认为每一行都“换人了”。

处理：用稳定唯一标识，比如 `item.id`。
:::

::: details 坑 3：KeepAlive 的 include 不生效
现象：写了 `include="ActivityList"` 但组件还是被销毁。

原因：`<script setup>` 组件默认没有 `name`，匹配不上。

处理：加 `defineOptions({ name: 'ActivityList' })`，名字要和 `include` 里写的完全一致。
:::

::: details 坑 4：Teleport 之后样式丢了
现象：弹窗送到 `body` 下，`scoped` 样式不生效或乱掉。

原因：`scoped` 样式靠给元素加自定义属性实现，传送后元素还在同一个组件的渲染树里，
属性仍在，但如果样式写在**父组件**的 `scoped` 里，就不会应用到传送出去的元素上。

处理：把样式写在弹窗组件自己的 `<style scoped>` 里，别写在调用方的父组件里。
:::

::: details 坑 5：顶层 await 用了，但组件没包 Suspense
现象：控制台报错，或者组件不渲染。

原因：顶层 `await` 的组件是异步组件，必须有 `<Suspense>` 作为父级。

处理：要么包 `<Suspense>`，要么把数据获取放到 `onMounted` 里用普通 `loading` 状态管理。
**课程项目里更推荐后者**，逻辑更直白，也便于处理错误。
:::

## 课后练习

::: details 练习 1：给抽屉加进出场动画
做一个右侧滑入的“发布活动”抽屉，要求：进场从右侧滑入、离场滑回、遮罩层同时淡入淡出。

**思路**：抽屉和遮罩分别用 `<Transition>`，或用一个包裹层统一做。注意 `transform` 会影响
`position: fixed` 的定位参照 —— 这也是为什么弹窗要 `Teleport` 到 `body`。
:::

::: details 练习 2：报名列表的增删动画
做一个报名列表，支持“通过”和“驳回”。通过时该行移到“已通过”区域的末尾，
驳回时该行淡出。用 `TransitionGroup` 实现补位动画。

**思路**：两个区域各用一个 `TransitionGroup`，`key` 用报名记录的 `id`。
想一想：为什么“移动”这一步要交给数据变化而不是手动操作 DOM。
:::

::: details 练习 3：给列表页加 KeepAlive 并验证
给活动列表页按上 `KeepAlive`，在搜索框里输入关键词、翻到第 3 页，点进详情再返回，
验证条件还在。再加一个“刷新”按钮，用 `onActivated` 恢复时按需重新请求。

**思路**：给列表页加 `defineOptions({ name: 'ActivityList' })`，
在 `App.vue` 的 `<RouterView>` 外用 `<KeepAlive include="ActivityList">`。
观察 `onMounted` 与 `onActivated` 各打印几次。
:::

---

上一节：[8.2 依赖注入](/unit08/02-provide-inject) ·
下一节：[8.4 组合式函数](/unit08/04-composables)
