# 用户端 · 活动浏览参考实现

这一页是用户端**活动列表与详情**的参考实现。

它比管理端的活动管理模块简单得多 —— **学生只能看，不能改**。但有两处比管理端难：移动端的交互细节（下拉刷新、触底加载、安全区），以及详情页那个由状态决定的按钮。

**先读三份文档**：[用户端需求规格](/project/mobile) 的页面清单与界面要求，[接口约定](/project/api) 第十章的学生端接口，[用户端 · 列表页与详情页](/mobile/07-list-detail) 讲的实现要点。

## 一、页面、路由、接口对照

| 页面 | 路由 | 接口 | 在 tabBar |
| --- | --- | --- | --- |
| 活动列表 | `pages/activity/list` | `GET /api/student/activities` | 是 |
| 活动详情 | `pages/activity/detail` | `GET /api/student/activities/{id}` | 否 |

**只有两个接口，都是不需要登录的。** 未登录时详情接口返回的 `mySignupStatus` 是 `null`。

涉及的文件：

| 文件 | 职责 |
| --- | --- |
| `src/api/activity.js` | 两个接口的调用函数 |
| `src/utils/dict.js` | 活动类型与状态的字典 |
| `src/utils/date.js` | 时间格式化与比较 |
| `src/components/activity-card.vue` | 活动卡片 |
| `src/pages/activity/list.vue` | 列表页 |
| `src/pages/activity/detail.vue` | 详情页 |

## 二、接口层

```js [src/api/activity.js]
import { http } from '@/utils/request'

/** 活动列表：params 为 { page, pageSize, keyword, type, status } */
export function fetchActivityList(params) {
  return http.get('/student/activities', params)
}

/** 活动详情：返回含 mySignupStatus 与 sessions */
export function fetchActivityDetail(id) {
  return http.get('/student/activities/' + id)
}
```

**注意路径是 `/student/activities`，不是 `/activities`。** 后者是管理端的接口，用户端的 token 访问不到 —— 这是后端在路由层做的隔离，不是靠参数过滤。

## 三、字典

```js [src/utils/dict.js]
export const ACTIVITY_TYPE = {
  LECTURE:     { label: '讲座', color: '#42b883' },
  COMPETITION: { label: '比赛', color: '#FF9500' },
  PERFORMANCE: { label: '演出', color: '#7B61FF' },
  SPORTS:      { label: '体育', color: '#FA5151' },
  VOLUNTEER:   { label: '志愿服务', color: '#42b883' },
  OTHER:       { label: '其他', color: '#999999' }
}

export const ACTIVITY_STATUS = {
  DRAFT:         { label: '草稿', color: '#999999' },
  SIGNING:       { label: '报名中', color: '#42b883' },
  SIGNUP_CLOSED: { label: '报名截止', color: '#FF9500' },
  FINISHED:      { label: '已结束', color: '#999999' }
}

export function typeOf(code) {
  return ACTIVITY_TYPE[code] || ACTIVITY_TYPE.OTHER
}

export function statusOf(code) {
  return ACTIVITY_STATUS[code] || { label: '未知', color: '#999999' }
}
```

**`DRAFT` 在学生端永远不会出现**（后端不会返回草稿），但字典里留着它 —— 万一接口返回了意料之外的值，页面不会崩，只会显示“草稿”这个标签。**字典的职责是兜底，不是穷举。**

```js [src/utils/date.js]
/** iOS 不认 'yyyy-MM-dd HH:mm:ss'，统一转成斜杠再解析 */
export function parseTime(str) {
  if (!str) return null
  return new Date(String(str).replace(/-/g, '/'))
}

export function formatDateTime(str) {
  const d = parseTime(str)
  if (!d || isNaN(d.getTime())) return '-'
  const p = (n) => String(n).padStart(2, '0')
  return d.getFullYear() + '-' + p(d.getMonth() + 1) + '-' + p(d.getDate()) +
    ' ' + p(d.getHours()) + ':' + p(d.getMinutes())
}

export function formatShort(str) {
  const d = parseTime(str)
  if (!d || isNaN(d.getTime())) return '-'
  const p = (n) => String(n).padStart(2, '0')
  return p(d.getMonth() + 1) + '月' + p(d.getDate()) + '日 ' + p(d.getHours()) + ':' + p(d.getMinutes())
}

export function isPast(str) {
  const d = parseTime(str)
  return d ? d.getTime() < Date.now() : false
}
```

**为什么时间处理要单独一个文件？** 因为 iOS 的坑会在多个地方出现（列表的截止时间、详情的信息行、我的报名的报名时间）。**集中一处改一次，比散在页面里逐个改安全。**

## 四、活动卡片

```vue [src/components/activity-card.vue]
<script setup>
import { computed } from 'vue'
import { typeOf } from '@/utils/dict'
import { formatShort, isPast } from '@/utils/date'

const props = defineProps({
  activity: { type: Object, required: true }
})

const emit = defineEmits(['click'])

const typeInfo = computed(() => typeOf(props.activity.type))
const remaining = computed(() => props.activity.quota - props.activity.approvedCount)
const isFull = computed(() => remaining.value <= 0)
const expired = computed(() => isPast(props.activity.signupDeadline))
const finished = computed(() => props.activity.status === 'FINISHED')

const quotaText = computed(() => {
  if (finished.value) return '活动已结束'
  if (isFull.value) return '名额已满'
  return '还剩 ' + remaining.value + ' 个名额'
})
</script>

<template>
  <view class="card" @tap="emit('click', activity.id)">
    <wd-img
      v-if="activity.coverUrl"
      :src="activity.coverUrl"
      width="100%"
      height="320rpx"
      mode="aspectFill"
      radius="16rpx 16rpx 0 0"
    />

    <view class="card-body">
      <view class="card-head">
        <text class="card-title">{{ activity.title }}</text>
        <wd-tag :color="typeInfo.color" plain>{{ typeInfo.label }}</wd-tag>
      </view>

      <text class="card-organizer">{{ activity.organizerName }}</text>

      <view class="card-foot">
        <text :class="['deadline', { past: expired }]">
          {{ expired ? '已截止' : '截止 ' + formatShort(activity.signupDeadline) }}
        </text>
        <text :class="['quota', { full: isFull || finished }]">{{ quotaText }}</text>
      </view>
    </view>
  </view>
</template>

<style lang="scss" scoped>
.card {
  margin: 0 24rpx 20rpx;
  background: #ffffff;
  border-radius: 16rpx;
  overflow: hidden;
}

.card-body {
  padding: 24rpx;
}

.card-head {
  display: flex;
  align-items: flex-start;
  gap: 16rpx;
}

.card-title {
  flex: 1;
  min-width: 0;
  font-size: 32rpx;
  font-weight: 600;
  color: $text-main;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-organizer {
  display: block;
  margin-top: 8rpx;
  font-size: 24rpx;
  color: $text-sub;
}

.card-foot {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 20rpx;
  font-size: 26rpx;
}

.deadline {
  color: $text-sub;
}

.deadline.past {
  color: #bbbbbb;
}

.quota {
  color: $brand-color;
}

.quota.full {
  color: #fa5151;
  font-weight: 600;
}
</style>
```

**卡片不跳转，只抛事件。** 这一点在[第 5 篇](/mobile/05-components)里讲过：卡片自己跳转就没法在别的场景复用。这里父组件拿到 `id` 决定去哪，将来如果“我的报名”也要用这个卡片展示活动，改父组件就行。

## 五、列表页

### 5.1 页面结构与状态

```vue [src/pages/activity/list.vue]
<script setup>
import { computed, ref } from 'vue'
import { onLoad, onShow, onPullDownRefresh, onReachBottom } from '@dcloudio/uni-app'
import ActivityCard from '@/components/activity-card.vue'
import { fetchActivityList } from '@/api/activity'

const list = ref([])
const loading = ref(false)
const loadError = ref('')
const page = ref(1)
const pageSize = 10
const total = ref(0)
const finished = ref(false)
const loaded = ref(false)
const keyword = ref('')

// 四态：骨架屏 / 错误 / 空 / 有数据
const showSkeleton = computed(() => loading.value && !list.value.length)
const showError = computed(() => !loading.value && loadError.value && !list.value.length)
const showEmpty = computed(() => loaded.value && !loading.value && !list.value.length && !loadError.value)

const loadmoreState = computed(() => {
  if (loading.value && list.value.length) return 'loading'
  if (loadError.value) return 'error'
  if (finished.value && list.value.length) return 'finished'
  return 'loading'
})
</script>

<template>
  <view class="page">
    <view class="search-bar">
      <wd-search
        v-model="keyword"
        placeholder="搜索活动名称"
        hide-cancel
        @search="handleSearch"
        @clear="handleSearch"
      />
    </view>

    <wd-skeleton v-if="showSkeleton" theme="paragraph" :row-col="skeletonRowCol" />

    <view v-else-if="showError" class="state-box">
      <text class="state-text">{{ loadError }}</text>
      <wd-button size="small" plain @click="loadFirstPage">重新加载</wd-button>
    </view>

    <wd-empty v-else-if="showEmpty" tip="暂时没有可报名的活动" />

    <template v-else>
      <view class="list">
        <ActivityCard
          v-for="item in list"
          :key="item.id"
          :activity="item"
          @click="goDetail"
        />
      </view>
      <wd-loadmore :state="loadmoreState" @reload="loadNextPage" />
    </template>

    <wd-toast />
  </view>
</template>
```

**`showSkeleton` / `showError` / `showEmpty` 三个计算属性互斥**，条件判断顺序不能乱。**如果先判断空再判断加载中，加载过程中会闪一下空状态** —— 这个闪烁在慢网下特别明显。

### 5.2 请求逻辑

```js
const skeletonRowCol = [
  { width: '100%', height: '320rpx' },
  { width: '60%', height: '40rpx' },
  { width: '40%', height: '32rpx' }
]

onLoad(() => {
  loadFirstPage()
})

async function loadFirstPage() {
  loading.value = true
  loadError.value = ''
  try {
    const res = await fetchActivityList({ page: 1, pageSize, keyword: keyword.value })
    page.value = 1
    list.value = res.list
    total.value = res.total
    finished.value = res.list.length >= res.total
    loaded.value = true
  } catch (err) {
    loadError.value = err.message || '加载失败'
  } finally {
    loading.value = false
  }
}

async function loadNextPage() {
  if (loading.value || finished.value) return

  const next = page.value + 1        // 先在局部变量里算
  loading.value = true
  loadError.value = ''
  try {
    const res = await fetchActivityList({ page: next, pageSize, keyword: keyword.value })
    page.value = next                // 成功了才写回
    list.value.push(...res.list)
    total.value = res.total
    finished.value = list.value.length >= res.total
  } catch (err) {
    loadError.value = '加载失败，点击重试'
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  finished.value = false
  loadFirstPage()
}

function goDetail(id) {
  uni.navigateTo({ url: '/pages/activity/detail?id=' + id })
}
```

**`page.value = next` 这一行值得盯着看。** 很多人的写法是 `page.value += 1` 然后再发请求，失败了再 `-= 1` 回退 —— **这样也能跑通，但漏掉回退就丢一页数据。** “先算局部变量、成功了才写回”，从结构上就不可能出错。

### 5.3 下拉刷新

```js
onPullDownRefresh(async () => {
  try {
    finished.value = false
    await loadFirstPage()
  } finally {
    uni.stopPullDownRefresh()      // 必须调用，否则加载圈一直转
  }
})
```

别忘了在 `pages.json` 里给这个页面开开关：

```json [src/pages.json]
{
  "path": "pages/activity/list",
  "style": {
    "navigationBarTitleText": "校园活动",
    "enablePullDownRefresh": true,
    "backgroundTextStyle": "dark",
    "onReachBottomDistance": 100
  }
}
```

### 5.4 触底加载

```js
onReachBottom(() => {
  loadNextPage()
})
```

**`onReachBottomDistance` 设成 100**（默认 50）—— 让它提前一点触发，用户滑到底时数据已经在加载了，**手感上更接近“无缝”**。

**注意页面必须是页面滚动，不能用 `scroll-view` 包列表。** 用 `scroll-view` 的话页面本身不滚动，`onReachBottom` 永远不触发，得换成 `@scrolltolower`。

## 六、详情页

### 6.1 页面结构

```vue [src/pages/activity/detail.vue]
<script setup>
import { computed, ref } from 'vue'
import { onLoad, onShow } from '@dcloudio/uni-app'
import { fetchActivityDetail } from '@/api/activity'
import { typeOf } from '@/utils/dict'
import { formatDateTime } from '@/utils/date'
import { ensureLogin } from '@/utils/auth'

const activity = ref(null)
const loading = ref(true)
const notFound = ref(false)
const ready = ref(false)

onLoad((options) => {
  const id = Number(options.id)
  if (!id) {
    uni.showToast({ title: '参数错误', icon: 'none' })
    setTimeout(() => uni.navigateBack(), 800)
    return
  }
  loadDetail(id)
  ready.value = true
})

// 从报名页返回时刷新名额
onShow(() => {
  if (ready.value && activity.value) {
    loadDetail(activity.value.id, true)
  }
})

async function loadDetail(id, silent) {
  if (!silent) loading.value = true
  try {
    activity.value = await fetchActivityDetail(id)
  } catch (err) {
    if (err.code === 2001) {
      notFound.value = true
    }
  } finally {
    loading.value = false
  }
}
</script>
```

**`ready` 这个标记是为了避免首次进入发两次请求。** `onLoad` 里请求一次，紧接着 `onShow` 也会触发 —— 没有这个标记的话，首屏会请求两次。

### 6.2 按钮状态机

**这是这一页最核心的一段代码。**

```js
const buttonState = computed(() => {
  const a = activity.value
  if (!a) return { text: '', disabled: true, action: '' }

  // 第一优先：我报过没有
  if (a.mySignupStatus && a.mySignupStatus !== 'CANCELLED') {
    return { text: '查看我的报名', disabled: false, action: 'mySignup' }
  }

  // 第二优先：活动状态
  if (a.status === 'FINISHED') {
    return { text: '活动已结束', disabled: true, action: '' }
  }
  if (a.status === 'SIGNUP_CLOSED') {
    return { text: '报名已截止', disabled: true, action: '' }
  }

  // 第三优先：名额
  const remaining = a.quota - a.approvedCount
  if (remaining <= 0) {
    return { text: '名额已满', disabled: true, action: '' }
  }

  return { text: '立即报名', disabled: false, action: 'signup' }
})
```

**判断顺序是刻意的**：

| 顺序 | 判断 | 为什么排这个位置 |
| --- | --- | --- |
| 1 | 我报过没有 | **已报名的用户应该能去看结果，而不是被告知“已截止”** |
| 2 | 活动状态 | 结束和截止是两种不同的状态，文案不同 |
| 3 | 名额 | 最后判断，因为前面两种情况更“硬” |

**如果顺序反了会怎样？** 一个已通过审核的学生，在活动报名截止后打开详情页，看到的是“报名已截止” —— 他会以为自己的报名出了问题，然后到处问。**这类问题在测试时几乎不会发现，因为测试的人通常只用一个新账号从零走一遍。**

### 6.3 点击处理

```js
function handleAction() {
  const state = buttonState.value
  if (state.disabled) return

  if (state.action === 'mySignup') {
    uni.switchTab({ url: '/pages/signup/my' })
    return
  }

  if (state.action === 'signup') {
    if (!ensureLogin()) return
    uni.navigateTo({ url: '/pages/signup/form?activityId=' + activity.value.id })
  }
}
```

**注意 `switchTab` 和 `navigateTo` 的区别**：`/pages/signup/my` 在 tabBar 里，必须用 `switchTab`。

### 6.4 活动说明

```vue
<view v-if="activity.description" class="section">
  <text class="section-title">活动说明</text>
  <rich-text class="rich" :nodes="activity.description" />
</view>
```

```css
.rich {
  font-size: 28rpx;
  line-height: 1.7;
  color: $text-main;
}
```

**`rich-text` 支持的标签有限**（`p`、`div`、`span`、`strong`、`img`、`a` 等），**复杂样式和 CSS 类名会丢**。所以要注意两点：

1. 后端返回的 HTML 要用基础标签
2. **图片宽度要由后端在 HTML 里控制**，`rich-text` 里没法用 CSS 约束它 —— 图片超出屏幕宽度是这一块的常见问题

### 6.5 小程序分享

```js
// #ifdef MP-WEIXIN
import { onShareAppMessage, onShareTimeline } from '@dcloudio/uni-app'

onShareAppMessage(() => ({
  title: activity.value ? activity.value.title : '校园活动',
  path: '/pages/activity/detail?id=' + (activity.value ? activity.value.id : '')
}))

onShareTimeline(() => ({
  title: activity.value ? activity.value.title : '校园活动',
  query: 'id=' + (activity.value ? activity.value.id : '')
}))
// #endif
```

**只有写了这两个钩子，小程序右上角菜单里的“转发”才有反应。** 不写的话点了没反应 —— 这是小程序的默认行为，不是 bug。

## 七、关键决策

### 决策一 · 列表不返回活动说明

接口约定里明确写了：列表不返回 `description`，只有详情返回。

**带来的好处是首屏快。** 二十条活动各带一段几百字的说明，响应体可能大好几倍。**代价是详情页必须单独请求一次** —— 而这个请求本来就要发（要拿 `mySignupStatus` 和 `sessions`）。

**如果将来列表要显示“活动简介”**，正确做法是后端加一个 `summary` 字段（截断后的短文本），**而不是把完整的 `description` 塞进列表。**

### 决策二 · 详情页在 `onShow` 刷新

学生从详情页去报名，回来时名额可能已经变了。**详情页选择“每次显示都刷新”**，代价是多一次请求。

**列表页不做同样的事。** 列表数据变化不频繁，让用户自己下拉刷新就够。**两个页面的策略不同是有意的** —— 详情页后面紧跟着一个“有后果的动作”，列表页没有。

### 决策三 · 卡片组件不自己跳转

卡片只抛 `id`，跳转由父组件决定。

**这样做的直接收益**：“我的报名”页要展示活动卡片时，可以复用这个组件，点击后跳到报名记录详情而不是活动详情 —— **不用改卡片，只改父组件的一行。**

### 决策四 · 不用 Pinia

活动列表和详情都是“进页面请求、离开就丢”的数据，**没有跨页共享的需求**，不需要全局状态。

**什么时候该改主意？** 如果要做“离线缓存活动列表”或者“活动数据在多处实时联动”，再考虑引入。**在那之前，`ref` 加请求层就够了。**

## 八、容易出问题的地方

::: details 慢网下先闪一下“没有活动”，然后才出现列表

**现象：** 进页面，先出现“暂时没有可报名的活动”，半秒后列表出来了。

**原因：** 空状态的判断条件里少了 `loaded`。请求还在路上时 `list.length` 是 0，就被判成“空数据”了。

**怎么处理：** 加一个“是否至少完成过一次请求”的标记：

```js
// ✗ 请求中也会命中
const showEmpty = computed(() => !list.value.length)

// ✓ 只在实际拿到结果且为空时才命中
const loaded = ref(false)
const showEmpty = computed(() => loaded.value && !loading.value && !list.value.length)
```

**`loaded` 在请求成功后置为 `true`**（失败时不置），这样失败时会走错误态而不是空态。

:::

::: details 列表滚动到底部，`onReachBottom` 不触发

**现象：** 滑到底部没反应，加载更多不出现。

**原因：** 按概率排四种：

1. **用 `scroll-view` 包住了列表** —— 页面本身不滚动，页面的触底事件自然不触发
2. **内容不足一屏**，滚不动
3. **没配 `onReachBottomDistance`**，触发得太晚
4. **`onReachBottom` 忘了从 `@dcloudio/uni-app` 导入**

**怎么处理：** 先确认是不是第 1 种（最常见）：

```vue
<!-- ✗ scroll-view 会接管滚动，onReachBottom 失效 -->
<scroll-view scroll-y style="height: 100vh">
  <ActivityCard v-for="item in list" :key="item.id" :activity="item" />
</scroll-view>

<!-- ✓ 让页面自己滚 -->
<view class="list">
  <ActivityCard v-for="item in list" :key="item.id" :activity="item" />
</view>
```

**如果用 `scroll-view` 是必须的**（比如固定了列表区域高度、上方有吸顶元素），改用它的 `@scrolltolower` 事件。**但要知道：两种滚动方式不能混用，选一种。**

:::

::: details 图片超出屏幕宽度

**现象：** 活动说明里的图片比屏幕宽，出现横向滚动条。

**原因：** `rich-text` 里的内容**不受页面 CSS 控制** —— 你在外面写 `.rich img { width: 100% }` 是无效的。

**怎么处理：** 三个层次，从治本到绕过：

| 做法 | 说明 |
| --- | --- |
| **后端处理** | 返回 HTML 之前给 `img` 标签加上 `style="max-width:100%"` |
| 前端处理 | 拿到 `description` 后用字符串替换，给 `img` 加样式（脆弱，但能应急） |
| 产品层面 | 活动说明里不鼓励放图，需要图就放在封面或单独字段 |

```js
// 应急的前端处理
const safeHtml = computed(() => {
  if (!activity.value || !activity.value.description) return ''
  return activity.value.description.replace(
    /<img/gi,
    '<img style="max-width:100%;height:auto;"'
  )
})
```

**推荐让后端处理**，因为 HTML 是后端生成的，加样式是它的分内事。

:::

::: details 从报名页返回详情页，名额数字没变

**现象：** 报名成功返回，详情页显示的名额还是旧的。

**原因：** `onShow` 没写刷新逻辑，或者写了但被 `ready` 标记挡住了：

```js
// ✗ ready 在 onLoad 里就置为 true，onShow 判断条件永远成立但时机不对
// 更常见的是忘了给 onShow 加 ready 判断，导致首次进入请求两次
```

**怎么处理：** 按 6.1 的写法，`ready` 在 `onLoad` 末尾置 `true`，`onShow` 里判断 `ready && activity`。**验证办法**：在 `loadDetail` 里打一行日志，进页面时应该只打印一次，从报名页返回时再打印一次。

:::

::: details 详情页从分享链接进入时参数拿不到

**现象：** 别人转发的活动卡片点开，进详情页但显示“参数错误”。

**原因：** 分享的 `path` 里没带 `id`，或者带了但格式不对。

**怎么处理：** 检查 `onShareAppMessage` 返回的 `path`：

```js
onShareAppMessage(() => ({
  title: activity.value ? activity.value.title : '校园活动',
  path: '/pages/activity/detail?id=' + (activity.value ? activity.value.id : '')
}))
```

**`path` 必须以 `/` 开头，且不能带域名。** 写成 `pages/activity/detail?id=1`（不带开头的斜杠）或者带 `https://` 都会失败。

**`onShareTimeline` 的参数名是 `query` 不是 `path`**，这也是容易写混的地方 —— 朋友圈分享用的是 `query`，且不带开头的 `?`。

:::

## 九、验收清单

- [ ] 未登录能浏览列表与详情
- [ ] 列表四态都能看到：骨架屏、错误重试、空数据、有数据
- [ ] 下拉刷新能触发，加载圈正常消失
- [ ] 触底加载能加载完所有数据，出现“没有更多了”
- [ ] 第 2 页失败后重试，拿到的仍是第 2 页数据（不丢页）
- [ ] 活动说明里的图片不超出屏幕宽度
- [ ] 详情页按钮五种状态都验证过（含“已报名”这一条）
- [ ] 从报名页返回，名额数字有更新
- [ ] 小程序端能转发活动，转发出去的链接打开正常
- [ ] iOS 机型上时间显示正常（不是 Invalid Date）
- [ ] H5 端限制最大宽度，大屏下不变形

## 十、可以继续做的事

1. **筛选面板。** 用 `wd-popup` 从底部弹出，按类型、状态筛选，比搜索框更符合手机的操作习惯
2. **活动列表的骨架屏做得更像真实卡片。** 现在是通用的段落骨架，换成卡片形状的会让等待感更短
3. **历史浏览记录。** 存最近看过的几个活动在 storage 里，下次进来自动显示在顶部
4. **分享出去的卡片带封面图。** `onShareAppMessage` 支持 `imageUrl`，配一张活动封面，转发出去更有点击欲
5. **列表的图片懒加载。** `wd-img` 支持 `lazy-load`，长列表加上它会明显省流量

---

上一页：[用户端 · 登录与登录态](/project/impl-mobile-auth) ·
下一页：[用户端 · 报名与我的报名](/project/impl-mobile-signup)
