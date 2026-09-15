# 7. 列表页与详情页

## 一个具体的场面

活动列表页在浏览器里跑通了：数据出来了，卡片也好看。然后你把它装到手机上试，冒出四个问题。

1. **下拉到底不能再加载** —— 桌面上数据少的时候看不出问题，手机上一屏只能放三张卡片
2. **想下拉刷新，没有那个圈** —— 以为写了 `onPullDownRefresh` 就行
3. **从详情页返回，名单还是旧的** —— 别人刚抢走最后一个名额，用户看到的还是“还剩 1 个”
4. **点进详情页，按钮永远显示“立即报名”** —— 名额满了、已经报过了、活动结束了，按钮都没变

**这一节做移动端最重要的两个页面，重点全在这四处。**

## 一、列表页的整体结构

列表页要做的事比桌面端多，先看结构：

```vue [src/pages/activity/list.vue]
<template>
  <view class="page">
    <!-- 搜索框，吸顶 -->
    <view class="search-bar">
      <wd-search v-model="keyword" placeholder="搜索活动名称" @search="handleSearch" @clear="handleSearch" />
    </view>

    <!-- 第一屏加载中：骨架屏 -->
    <wd-skeleton v-if="showSkeleton" theme="paragraph" :row-col="skeletonRowCol" />

    <!-- 出错：给重试入口 -->
    <view v-else-if="errorMsg" class="state-box">
      <text class="state-text">{{ errorMsg }}</text>
      <wd-button size="small" plain @click="loadFirstPage">重新加载</wd-button>
    </view>

    <!-- 空数据 -->
    <wd-empty v-else-if="!list.length" tip="暂时没有可报名的活动" />

    <!-- 有数据 -->
    <template v-else>
      <view class="list">
        <ActivityCard
          v-for="item in list"
          :key="item.id"
          :activity="item"
          @click="goDetail"
        />
      </view>

      <!-- 触底状态提示 -->
      <wd-loadmore :state="loadmoreState" @reload="loadNextPage" />
    </template>

    <wd-toast />
  </view>
</template>
```

**这就是四态在移动端的落法**：加载中用骨架屏、出错给重试按钮、空数据给提示、有数据显示列表。**和单元 5 讲的四态是一个东西，只是每个状态的呈现方式换成了手机上的样子。**

骨架屏和空状态具体长什么样：

```js
import { computed, ref } from 'vue'
import { onLoad, onPullDownRefresh, onReachBottom } from '@dcloudio/uni-app'
import ActivityCard from '@/components/activity-card.vue'
import { fetchActivityList } from '@/api/activity'

const list = ref([])
const loading = ref(false)
const loadError = ref('')
const page = ref(1)
const pageSize = 10
const total = ref(0)
const finished = ref(false)
const loaded = ref(false)      // 是否至少完成过一次请求

// 四种状态互斥，用一个 computed 表达比到处写 if 清楚
const showSkeleton = computed(() => loading.value && !list.value.length)
const errorMsg = ref('')
</script>
```

**注意 `loaded` 这个标记。** 没有它的话，“还没开始请求”和“请求完了但是空的”都是 `list.length === 0`，页面会在加载前闪一下“暂时没有活动” —— 很难看，而且会让人误以为真的没数据。

## 二、下拉刷新

三件事缺一不可。

**第一件：在 `pages.json` 里开启。**

```json [src/pages.json]
{
  "path": "pages/activity/list",
  "style": {
    "navigationBarTitleText": "校园活动",
    "enablePullDownRefresh": true,
    "backgroundTextStyle": "dark"
  }
}
```

**第二件：页面里写钩子。**

**第三件：请求结束后调 `uni.stopPullDownRefresh()`。**

```js
onPullDownRefresh(async () => {
  page.value = 1
  finished.value = false
  await loadList(true)
  // 必须调用，否则那个圈一直转着不消失
  uni.stopPullDownRefresh()
})
```

::: warning 忘了 stopPullDownRefresh 的后果
下拉的那个加载圈会一直转，**用户以为页面卡死了**。而且再下拉也不会有反应。

**保险的做法是把它放在 `finally` 里**，或者像上面这样放在所有请求之后 —— **重点是无论请求成功还是失败都要调到**：

```js
onPullDownRefresh(async () => {
  try {
    page.value = 1
    await loadList(true)
  } finally {
    uni.stopPullDownRefresh()
  }
})
```
:::

## 三、触底加载

分页逻辑和管理端一样（`page` 加 `pageSize`，返回 `{ list, total }`），差别在触发方式：**手机上不用页码按钮，滚动到底部自动加载。**

```js
onReachBottom(() => {
  if (finished.value || loading.value) return
  loadNextPage()
})

async function loadNextPage() {
  page.value += 1
  try {
    const res = await fetchActivityList({ page: page.value, pageSize, keyword: keyword.value })
    if (page.value === 1) {
      list.value = res.list
    } else {
      list.value = list.value.concat(res.list)
    }
    total.value = res.total
    finished.value = list.value.length >= res.total
  } catch (err) {
    page.value -= 1        // 失败要把页码退回去，否则下次会跳过这一页
    loadError.value = '加载更多失败'
  }
}
```

两个细节：

**一、失败时把页码退回去。** 不退的话，这次加载的第 2 页失败了，下次加载的是第 3 页，**第 2 页的数据永远丢了。** 这个 bug 在弱网下很常见，测试时不容易发现。

**二、`finished` 的判断。** 用 `list.length >= total` 或者看后端返回的 `list.length < pageSize`，两种都行，**选一种并在全项目统一。**

### 触底状态用 loadmore 提示

```js
const loadmoreState = computed(() => {
  if (loading.value && list.value.length) return 'loading'
  if (loadError.value) return 'error'
  if (finished.value && list.value.length) return 'finished'
  return 'loading'
})
```

页面上四种状态分别显示“加载中”“加载失败，点击重试”“没有更多了”。**别小看这个提示** —— 没有它，用户滑到底会以为卡住了，继续往上滑。

## 四、详情页

### 拿参数、请求数据、处理异常

```js
import { onLoad, onShow } from '@dcloudio/uni-app'

const activity = ref(null)
const notFound = ref(false)

onLoad((options) => {
  const id = Number(options.id)
  if (!id) {
    // 参数非法直接退回，不要让页面停在半死不活的状态
    uni.showToast({ title: '活动参数错误', icon: 'none' })
    setTimeout(() => uni.navigateBack(), 800)
    return
  }
  loadDetail(id)
})

async function loadDetail(id) {
  try {
    activity.value = await fetchActivityDetail(id)
  } catch (err) {
    if (err.code === 2001) {
      notFound.value = true          // 活动不存在，显示专门的提示页
    }
  }
}
```

### 回到这个页面时刷新名额

```js
// 从报名页返回时，名额可能已经变了
onShow(() => {
  if (activity.value) {
    loadDetail(activity.value.id)
  }
})
```

**这一段是必需的吗？** 看场景。别人可能在你去报名的这一分钟里抢走了名额，回来还显示“还剩 3 个”就是错的。**但对于浏览性质强的页面，每次 `onShow` 都请求一次太浪费。**

一个折中的判断：

| 页面 | 要不要在 onShow 刷新 |
| --- | --- |
| 活动列表 | 不要，用户可以自己下拉 |
| 活动详情 | 要（名额是实时变化的，且用户下一步就要报名） |
| 我的报名 | 要（刚提交完，用户期望看到新记录） |

### 按钮的状态机

**这是详情页最容易写漏的地方。** 一个按钮要表达五种情况：

| 活动状态 | 我的报名情况 | 按钮文字 | 是否可点 |
| --- | --- | --- | --- |
| `SIGNING` | 没报过，名额未满 | 立即报名 | 是 |
| `SIGNING` | 没报过，名额已满 | 名额已满 | 否 |
| `SIGNING` 或 `SIGNUP_CLOSED` | 已报过 | 查看我的报名 | 是（跳转） |
| `SIGNUP_CLOSED` | 没报过 | 报名已截止 | 否 |
| `FINISHED` | 任意 | 活动已结束 | 否 |

写成计算属性，别在模板里堆 `v-if`：

```js
const buttonState = computed(() => {
  const a = activity.value
  if (!a) return { text: '', disabled: true }

  if (a.mySignupStatus && a.mySignupStatus !== 'CANCELLED') {
    return { text: '查看我的报名', disabled: false, action: 'goMySignup' }
  }
  if (a.status === 'FINISHED') {
    return { text: '活动已结束', disabled: true }
  }
  if (a.status === 'SIGNUP_CLOSED') {
    return { text: '报名已截止', disabled: true }
  }
  if (a.quota - a.approvedCount <= 0) {
    return { text: '名额已满', disabled: true }
  }
  return { text: '立即报名', disabled: false, action: 'goSignup' }
})
```

**判断顺序有讲究**：**先判断“我报过没有”，再判断活动状态。** 反过来的话，一个已经报名的用户会看到“报名已截止”，然后不知道自己去哪儿看结果 —— 这是常见的体验问题。

### 活动说明用 rich-text

管理端用 `v-html` 渲染富文本，uni-app 里没有 `v-html`：

```vue
<!-- ✗ v-html 在小程序端无效 -->
<view v-html="activity.description"></view>

<!-- ✓ 用 rich-text -->
<rich-text :nodes="activity.description"></rich-text>
```

`rich-text` 支持的标签和样式是有限的（`p`、`div`、`span`、`img`、`a` 等基础标签），**复杂样式会丢。** 所以后端返回的活动说明最好是简单 HTML。

## 五、分享（小程序端）

小程序有个桌面端没有的能力：**用户可以把活动卡片转发给同学或微信群。** 这是学生端很自然的传播方式。

```js
// #ifdef MP-WEIXIN
import { onShareAppMessage, onShareTimeline } from '@dcloudio/uni-app'

onShareAppMessage(() => {
  return {
    title: activity.value ? activity.value.title : '校园活动',
    path: '/pages/activity/detail?id=' + (activity.value ? activity.value.id : '')
  }
})
// #endif
```

**加了这段，小程序右上角菜单里才会出现“转发”。** 不加就没有 —— 这是小程序的默认行为。

`#ifdef MP-WEIXIN` 是必要的，**H5 端没有 `onShareAppMessage` 这个钩子**，写在外面虽然不一定报错，但属于无效代码。

## 小结

- 列表页的四态和单元 5 讲的是一回事，**呈现方式换成骨架屏、空状态、重试按钮**
- 下拉刷新三件事：`pages.json` 开 `enablePullDownRefresh`、写 `onPullDownRefresh`、**一定要调 `uni.stopPullDownRefresh()`**
- 触底加载用 `onReachBottom`，**失败时要把页码退回去**，否则会漏掉一页数据
- 详情页在 `onLoad` 拿 `id` 请求，**`onShow` 里按需刷新名额**
- 报名按钮是**状态机**，五种情况；**判断顺序是“先看报没报过，再看活动状态”**
- 富文本用 `<rich-text>`，**`v-html` 在小程序端无效**
- 小程序分享要显式写 `onShareAppMessage`，**并用条件编译圈住**

## 常见坑

::: details `onReachBottom` 完全不触发

**现象：** 滑动到底部，什么都没发生，控制台没有输出。

**原因：** 四种可能，按概率排序：

1. **页面没有滚动** —— `onReachBottom` 是页面的滚动事件，如果滚动被 `scroll-view` 组件接走了，页面的滚动就不存在了
2. **没配 `onReachBottomDistance`** —— 有些布局下需要显式配这个距离
3. **内容高度不足** —— 只有三条数据，撑不满屏幕，滚不动自然触发不了
4. **函数写在了 `<script setup>` 外面**，或者忘了 import

**怎么处理：** 先确认用的是页面滚动而不是 `scroll-view`：

```vue
<!-- ✗ 用 scroll-view 就不能用 onReachBottom -->
<scroll-view scroll-y style="height: 100vh">
  <view v-for="item in list" :key="item.id">{{ item.title }}</view>
</scroll-view>
```

如果确实需要 `scroll-view`（比如固定了列表区域高度），**触底事件要换成 `scroll-view` 的 `@scrolltolower`**：

```vue
<scroll-view scroll-y style="height: calc(100vh - 100rpx)" @scrolltolower="loadNextPage">
  <!-- 列表 -->
</scroll-view>
```

**开发时不容易发现这个问题，因为测试数据通常少。** 造 30 条假数据放到列表里，滚一遍就知道触发没触发。

:::

::: details 加载更多时列表闪一下，滚动位置跳回顶部

**现象：** 滚到底部触发加载，新数据追加进来了，但页面跳回了顶部。

**原因：** 往列表里 push 数据时，如果 **`key` 用的是数组下标**，Vue 会复用错节点；或者**整个列表被重新赋值**（`list.value = newArray`）导致重新渲染。

**怎么处理：**

```js
// ✗ 用下标做 key：追加数据时前面的节点会被复用错
<ActivityCard v-for="(item, index) in list" :key="index" />

// ✓ 用业务主键
<ActivityCard v-for="item in list" :key="item.id" />

// ✗ 重新赋值整个数组，触发全量重渲染
list.value = list.value.concat(res.list)

// ✓ 用 push 追加（vue 的响应式数组方法，会原地修改并触发更新）
```

**这和管理端的 `key` 问题是同一件事**，只是手机上体现得更明显（节点多、屏幕小，复用错了一眼能看出来）。

:::

::: details `uni.showToast` 的提示文字被截断了

**现象：** 想提示“名额已满，请报名其他活动”，实际只显示了前几个字或者干脆不显示。

**原因：** `uni.showToast` 显示的是**一行短提示**，超长会被截断。它本来就不是用来显示长文本的。

**怎么处理：** 按用途选对应的组件：

| 用途 | 用什么 |
| --- | --- |
| 一句短提示（成功、失败、加载中） | `uni.showToast` 或 `wd-toast` |
| 多行文本、需要用户确认 | `wd-dialog` |
| 较长的说明、有标题和内容 | `uni.showModal` 或 `wd-message-box` |
| 页面内的固定错误显示 | 页面里自己放一块提示区域 |

**一般超过 15 个字就该换组件了。** 报名失败这类需要说明原因的，用 `wd-dialog` 更合适 —— 用户能停下来读完，而不是一闪而过。

:::

::: details 从报名页返回详情页，名额还是旧的

**现象：** 报名成功返回，名额显示没变，甚至还能再点一次“立即报名”。

**原因：** 详情页没有在 `onShow` 里重新请求。

**怎么处理：** 加 `onShow` 重新拉数据。**但注意别写成每次 `onShow` 都请求两次**：

```js
// ✗ onLoad 和 onShow 都请求，首次进入会发两次
onLoad((o) => loadDetail(o.id))
onShow(() => loadDetail(activity.value && activity.value.id))

// ✓ onLoad 请求一次，onShow 只在"从别的页回来"时请求
const ready = ref(false)
onLoad((o) => {
  loadDetail(Number(o.id))
  ready.value = true
})
onShow(() => {
  // 首次进入时 ready 还是 false，跳过
  if (ready.value && activity.value) {
    loadDetail(activity.value.id)
  }
})
```

**更省事的办法是让详情页也做“下拉刷新”**，用户在需要的时候自己刷新。**两种都行，但要说清这个页面用的是哪种策略**，别让后面接手的人猜。

:::

## 课后练习

**做完整的活动列表页与详情页，用假数据先把交互跑通。**

| 任务 | 要求 |
| --- | --- |
| 假数据 | 造 30 条活动，模拟分页（每页 10 条），请求加 500 毫秒延时 |
| 下拉刷新 | 能触发，成功后加载圈消失 |
| 触底加载 | 三次加载完 30 条，出现“没有更多了” |
| 加载失败 | 加一个开关，让第 2 页请求失败一次，验证页码回退 |
| 四态 | 能分别看到骨架屏、空状态、错误重试、正常列表 |
| 详情页 | 收 `id` 显示详情，底部固定报名栏 |
| 按钮状态 | 五种情况都能手动切换验证 |
| 分享 | 小程序端能转发（真机验证） |

::: details 验收标准与参考思路

**验收标准：**

| 项 | 要求 |
| --- | --- |
| 下拉 | 松开后加载圈出现，请求结束后消失（**不能一直转**） |
| 触底 | 滚到底自动加载，滚动位置不跳回顶部 |
| 页码回退 | 让第 2 页失败一次，重新触发加载后拿到的仍是第 2 页数据，第 2 页数据不丢 |
| 空状态 | 把假数据清空，显示空状态提示，**不闪烁** |
| 按钮 | 手动切换活动状态与报名状态，五种文案都正确 |
| 返回刷新 | 从报名页返回，名额数字有变化 |

**不合格的写法：**

```js
// ✗ 三个问题：没有 stopPullDownRefresh、key 用下标、失败不退页码
onPullDownRefresh(() => {
  page.value = 1
  loadList()
})

<ActivityCard v-for="(item, index) in list" :key="index" />

async function loadNextPage() {
  page.value += 1
  const res = await fetchActivityList({ page: page.value, pageSize })
  list.value = list.value.concat(res.list)
}
```

这三个问题单看都是小毛病，叠在一起就是：下拉圈不消失、加载后滚动位置乱跳、弱网下一整页数据消失。

**合格的写法：**

```js
onPullDownRefresh(async () => {
  try {
    page.value = 1
    finished.value = false
    await loadList()
  } finally {
    uni.stopPullDownRefresh()     // 放在 finally，成功失败都执行
  }
})

async function loadNextPage() {
  if (loading.value || finished.value) return
  const next = page.value + 1
  try {
    loading.value = true
    const res = await fetchActivityList({ page: next, pageSize })
    page.value = next              // 只有成功了才更新页码
    list.value.push(...res.list)   // push 而不是重新赋值
    finished.value = list.value.length >= res.total
  } catch (err) {
    loadError.value = '加载失败，点击重试'
  } finally {
    loading.value = false
  }
}
```

**关键差别在 `page.value = next` 这一行** —— **先在局部变量里算，成功了才写回 `page`**。这比“先加再回退”更不容易出错。

**参考思路：**

两个地方值得注意：

**一是造测试数据的技巧。** 用 `setTimeout` 模拟网络延时，**顺便模拟两种异常**：第 2 页返回失败、总数为 0。**这两种情况在真实开发里一定会遇到，但真连后端时反而不好造。**

**二是按钮状态机的判断顺序。** 建议把五种情况写在纸上，逐个手动切换验证 —— **不要只测“正常报名”那一条路径**。答辩时老师最可能问的就是“如果用户已经报过名了，这个按钮是什么状态”。

:::

---

上一节：[请求封装与登录态](/mobile/06-request-auth) ·
下一节：[报名表单与我的报名](/mobile/08-signup-form)
