# 用户端 · 报名与我的报名参考实现

这是用户端参考实现的最后一页：**报名表单页与我的报名列表。**

这两页是学生侧的重点 —— 前面所有的浏览都是为了走到这一步。**真正会被老师提问的异常情况，大半也出在这里。**

**先读三份文档**：[用户端需求规格](/project/mobile) 的状态表与验收方式，[接口约定](/project/api) 第十章的三个接口，[用户端 · 报名表单与我的报名](/mobile/08-signup-form) 讲的实现要点。

## 一、页面、路由、接口对照

| 页面 | 路由 | 接口 | 需要登录 |
| --- | --- | --- | --- |
| 报名表单 | `pages/signup/form` | `POST /api/student/signups` | 是 |
| 我的报名 | `pages/signup/my` | `GET /api/student/signups/mine` | 是 |
| | | `PUT /api/student/signups/{id}/cancel` | 是 |

表单页还要用活动详情接口（`GET /api/student/activities/{id}`）来做提交前的自检 —— **自检需要活动的最新状态与名额。**

涉及的文件：

| 文件 | 职责 |
| --- | --- |
| `src/api/signup.js` | 报名、我的报名、取消 |
| `src/utils/dict.js` | 报名状态字典（含颜色与文案） |
| `src/utils/date.js` | 时间格式化 |
| `src/pages/signup/form.vue` | 报名表单 |
| `src/pages/signup/my.vue` | 我的报名 |

## 二、接口层

```js [src/api/signup.js]
import { http } from '@/utils/request'

/** 提交报名：data 为 { activityId, studentNo, studentClass, remark } */
export function createSignup(data) {
  return http.post('/student/signups', data)
}

/** 我的报名：params 为 { page, pageSize, status } */
export function fetchMySignups(params) {
  return http.get('/student/signups/mine', params)
}

/** 取消报名 */
export function cancelSignup(id) {
  return http.put('/student/signups/' + id + '/cancel')
}
```

**注意报名时不需要传姓名。** 后端从登录用户的信息里取 —— 让学生自己填姓名等于允许他随便写，审核环节就没有意义了。

## 三、报名状态字典

```js [src/utils/dict.js]
export const SIGNUP_STATUS = {
  PENDING:   { label: '待审核', color: '#FF9500' },
  APPROVED:  { label: '已通过', color: '#42b883' },
  REJECTED:  { label: '已驳回', color: '#FA5151' },
  CANCELLED: { label: '已取消', color: '#999999' }
}

export function signupStatusOf(code) {
  return SIGNUP_STATUS[code] || { label: '未知', color: '#999999' }
}

/** 能取消的状态 */
export const CANCELABLE_STATUS = ['PENDING', 'APPROVED']
```

**把“能取消的状态”也放进字典文件。** 这个判断会在两三个地方用到（列表里显示按钮、点击时校验、可能还有详情页），**集中一处才不会改漏。**

## 四、报名表单页

### 4.1 数据流

```
① 详情页点“立即报名”
② ensureLogin() 通过 → navigateTo 带 activityId
③ onLoad 拿 activityId，请求活动详情做自检
④ 自检通过 → 用 userInfo 预填表单
⑤ 用户确认信息，点提交
⑥ validate() 通过 → POST /api/student/signups
⑦ 成功 → 弹窗告知后续 → switchTab 到“我的报名”
   失败 → 按错误码给不同的提示与后续动作
```

**第 ③ 步容易被跳过。** 有人觉得“详情页已经判断过一次了，这里不用再查” —— 但用户可能在详情页停留了几分钟，期间名额被抢完、或者报名刚截止。**自检要用最新数据。**

### 4.2 页面实现

```vue [src/pages/signup/form.vue]
<script setup>
import { reactive, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { z } from 'zod'
import { zodAdapter, useToast } from '@wot-ui/ui'
import { fetchActivityDetail } from '@/api/activity'
import { createSignup } from '@/api/signup'
import { getUserInfo } from '@/utils/auth'
import { formatDateTime, isPast } from '@/utils/date'

const toast = useToast()
const form = ref(null)
const activity = ref(null)
const loading = ref(true)
const submitting = ref(false)

const model = reactive({
  studentName: '',
  studentNo: '',
  studentClass: '',
  remark: ''
})

const schema = zodAdapter(
  z.object({
    studentName: z.string().min(1, '请填写姓名').max(20, '姓名不超过 20 个字'),
    studentNo: z.string().regex(/^\d{10}$/, '学号是 10 位数字'),
    studentClass: z.string().max(30, '班级不超过 30 个字').optional(),
    remark: z.string().max(200, '备注不超过 200 个字').optional()
  })
)

onLoad(async (options) => {
  const activityId = Number(options.activityId)
  if (!activityId) {
    uni.showToast({ title: '参数错误', icon: 'none' })
    setTimeout(() => uni.navigateBack(), 800)
    return
  }
  await checkBeforeFill(activityId)
})

/** 提交前的自检：三种情况不该让用户填表 */
async function checkBeforeFill(activityId) {
  try {
    const data = await fetchActivityDetail(activityId)
    activity.value = data

    if (data.mySignupStatus && data.mySignupStatus !== 'CANCELLED') {
      return blockWith('你已经报过名了', '去“我的报名”看看审核结果吧', 'mySignup')
    }
    if (data.status === 'FINISHED') {
      return blockWith('活动已经结束', '可以看看其他活动', 'back')
    }
    if (data.status !== 'SIGNING') {
      return blockWith('报名已关闭', '这个活动已经过了报名时间', 'back')
    }
    if (isPast(data.signupDeadline)) {
      return blockWith('报名已截止', '已过报名截止时间', 'back')
    }
    if (data.quota - data.approvedCount <= 0) {
      return blockWith('名额已满', '可以看看其他活动', 'back')
    }

    prefill()
  } catch (err) {
    uni.showToast({ title: err.message || '加载失败', icon: 'none' })
    setTimeout(() => uni.navigateBack(), 1000)
  } finally {
    loading.value = false
  }
}

function blockWith(title, content, then) {
  uni.showModal({
    title,
    content,
    showCancel: false,
    success: () => {
      if (then === 'mySignup') {
        uni.switchTab({ url: '/pages/signup/my' })
      } else {
        uni.navigateBack()
      }
    }
  })
}

function prefill() {
  const info = getUserInfo()
  if (!info) return
  model.studentName = info.realName || ''
  model.studentNo = info.studentNo || ''
  model.studentClass = info.studentClass || ''
}
</script>
```

**`blockWith` 这个函数值得注意。** 五种拦截情况的处理结构完全一样（弹窗 + 后续动作），**抽成一个函数比写五遍好**，但要保证每种情况的文案不同 —— **文案相同的话，用户不知道到底哪里出了问题。**

### 4.3 提交与错误码

```js
const ERROR_ACTIONS = {
  2005: { msg: '名额刚好被抢完了，可以看看其他活动', then: 'refresh' },
  2006: { msg: '已经过了报名截止时间', then: 'back' },
  3004: { msg: '你已经报过这个活动了', then: 'mySignup' },
  2007: { msg: '这个活动当前不能报名', then: 'back' }
}

async function handleSubmit() {
  if (submitting.value) return

  const { valid } = await form.value.validate()
  if (!valid) return

  submitting.value = true
  try {
    await createSignup({
      activityId: activity.value.id,
      studentNo: model.studentNo,
      studentClass: model.studentClass,
      remark: model.remark
    })

    uni.showModal({
      title: '报名已提交',
      content: '组织者会尽快审核，可以在“我的报名”里查看结果',
      showCancel: false,
      confirmText: '去看看',
      success: () => uni.switchTab({ url: '/pages/signup/my' })
    })
  } catch (err) {
    handleError(err)
  } finally {
    submitting.value = false
  }
}

function handleError(err) {
  const hit = ERROR_ACTIONS[err.code]
  if (!hit) {
    // 没约定的错误，用请求层的默认提示就够了
    return
  }
  uni.showToast({ title: hit.msg, icon: 'none' })

  if (hit.then === 'mySignup') {
    setTimeout(() => uni.switchTab({ url: '/pages/signup/my' }), 1200)
  } else if (hit.then === 'back') {
    setTimeout(() => uni.navigateBack(), 1200)
  }
  // then === 'refresh' 时什么都不做 —— 用户应该留在当前页，
  // 但要注意：名额满了之后这一页已经没意义了，所以下面补一句回详情
}
```

::: warning 名额已满之后，用户应该留在哪
拿到 `2005` 时，用户已经填完表了，但名额没了。**留在表单页等于让他对着一个提交不了的页面发呆。**

更合理的处理是：**提示之后把用户送回详情页**，让他看到真实的名额数，再决定要不要看别的活动。

```js
if (err.code === 2005) {
  uni.showToast({ title: '名额刚好被抢完了', icon: 'none' })
  setTimeout(() => uni.navigateBack(), 1200)   // 回详情页
}
```

**回详情页而不是回列表**，用户的思路是连续的：我在看这个活动 → 想报名 → 没抢上 → 那我看看这个活动的情况（或者点“相关活动”）。**直接甩回列表会打断这个思路。**
:::

### 4.4 表单模板

```vue
<template>
  <view class="page">
    <view v-if="activity" class="activity-brief">
      <text class="brief-title">{{ activity.title }}</text>
      <view class="brief-meta">
        <text>截止 {{ formatDateTime(activity.signupDeadline) }}</text>
        <text class="brief-quota">还剩 {{ activity.quota - activity.approvedCount }} 个名额</text>
      </view>
    </view>

    <wd-form ref="form" :model="model" :schema="schema">
      <wd-cell-group border>
        <!-- 姓名预填且不可改 -->
        <wd-form-item title="姓名" prop="studentName">
          <wd-input v-model="model.studentName" disabled placeholder="来自你的账号信息" />
        </wd-form-item>

        <wd-form-item title="学号" prop="studentNo">
          <wd-input v-model="model.studentNo" type="number" maxlength="10" placeholder="10 位学号" clearable />
        </wd-form-item>

        <wd-form-item title="班级" prop="studentClass">
          <wd-input v-model="model.studentClass" placeholder="例如：软件 2301" clearable />
        </wd-form-item>

        <wd-form-item title="备注" prop="remark">
          <wd-textarea
            v-model="model.remark"
            placeholder="有什么想说的可以写在这里（选填）"
            :maxlength="200"
            show-word-limit
            clearable
          />
        </wd-form-item>
      </wd-cell-group>
    </wd-form>

    <view class="tips">
      <text>提交后由组织者审核，结果会在“我的报名”里更新</text>
    </view>

    <view class="footer-bar">
      <wd-button
        type="primary"
        size="large"
        block
        :loading="submitting"
        :disabled="submitting"
        @click="handleSubmit"
      >
        {{ submitting ? '提交中…' : '提交报名' }}
      </wd-button>
    </view>

    <wd-toast />
  </view>
</template>
```

**姓名那一项是 `disabled` 的。** 它显示用户账号里的姓名，但不可改 —— **这一条是刻意的设计**：报名记录里的姓名必须可追溯，让学生随便填就失去了审核的意义。要改姓名得去“我的”那一页改资料，那里可以留下修改记录。

**顶部显示活动标题与剩余名额。** 用户从详情页跳过来，需要确认“我报的是这个活动”，而不是凭记忆。

## 五、我的报名页

### 5.1 结构

```vue [src/pages/signup/my.vue]
<script setup>
import { computed, ref } from 'vue'
import { onLoad, onPullDownRefresh, onReachBottom } from '@dcloudio/uni-app'
import { useDialog, useToast } from '@wot-ui/ui'
import { fetchMySignups, cancelSignup } from '@/api/signup'
import { signupStatusOf, CANCELABLE_STATUS } from '@/utils/dict'
import { formatDateTime } from '@/utils/date'
import { isLoggedIn } from '@/utils/auth'

const dialog = useDialog()
const toast = useToast()

const FILTERS = [
  { label: '全部', value: '' },
  { label: '待审核', value: 'PENDING' },
  { label: '已通过', value: 'APPROVED' },
  { label: '已驳回', value: 'REJECTED' }
]

const currentStatus = ref('')
const list = ref([])
const loading = ref(false)
const loadError = ref('')
const page = ref(1)
const pageSize = 10
const finished = ref(false)
const loaded = ref(false)

const showSkeleton = computed(() => loading.value && !list.value.length)
const showEmpty = computed(() => loaded.value && !loading.value && !list.value.length && !loadError.value)
const loadmoreState = computed(() => {
  if (loading.value && list.value.length) return 'loading'
  if (loadError.value) return 'error'
  if (finished.value && list.value.length) return 'finished'
  return 'loading'
})

function canCancel(item) {
  if (!CANCELABLE_STATUS.includes(item.status)) return false
  if (item.activityStatus === 'FINISHED') return false
  return true
}
</script>
```

### 5.2 列表项

```vue
<template>
  <view class="page">
    <view class="filter-bar">
      <wd-segmented v-model="currentStatus" :options="FILTERS" @change="handleFilterChange" />
    </view>

    <wd-skeleton v-if="showSkeleton" theme="paragraph" :row-col="skeletonRowCol" />

    <view v-else-if="loadError && !list.length" class="state-box">
      <text class="state-text">{{ loadError }}</text>
      <wd-button size="small" plain @click="loadFirstPage">重新加载</wd-button>
    </view>

    <wd-empty v-else-if="showEmpty" tip="还没有报名记录">
      <template #bottom>
        <wd-button size="small" plain @click="goActivityList">去看看活动</wd-button>
      </template>
    </wd-empty>

    <template v-else>
      <view class="list">
        <view
          v-for="item in list"
          :key="item.id"
          class="record"
          @tap="goActivityDetail(item.activityId)"
        >
          <view class="record-head">
            <text class="record-title">{{ item.activityTitle }}</text>
            <wd-tag :color="signupStatusOf(item.status).color" plain>
              {{ signupStatusOf(item.status).label }}
            </wd-tag>
          </view>

          <view class="record-rows">
            <view class="row">
              <text class="row-label">报名时间</text>
              <text class="row-value">{{ formatDateTime(item.createdAt) }}</text>
            </view>

            <!-- 已通过的要显示时间地点 -->
            <view v-if="item.status === 'APPROVED'" class="row">
              <text class="row-label">活动时间</text>
              <text class="row-value">{{ item.activityStartTime ? formatDateTime(item.activityStartTime) : '待安排' }}</text>
            </view>
            <view v-if="item.status === 'APPROVED'" class="row">
              <text class="row-label">活动地点</text>
              <text class="row-value">{{ item.venueName || '待安排' }}</text>
            </view>

            <view v-if="item.remark" class="row">
              <text class="row-label">我的备注</text>
              <text class="row-value">{{ item.remark }}</text>
            </view>
          </view>

          <!-- 驳回理由单独高亮：这是学生最想看的信息 -->
          <view v-if="item.status === 'REJECTED' && item.rejectReason" class="reject-box">
            <text class="reject-title">驳回原因</text>
            <text class="reject-text">{{ item.rejectReason }}</text>
            <text class="reject-hint">修改材料后可以重新报名</text>
          </view>

          <view v-if="item.status === 'APPROVED' && item.auditorName" class="audit-info">
            <text>由 {{ item.auditorName }} 于 {{ formatDateTime(item.auditedAt) }} 审核通过</text>
          </view>

          <view v-if="canCancel(item)" class="record-actions">
            <wd-button size="small" plain @click.stop="handleCancel(item)">取消报名</wd-button>
          </view>
        </view>
      </view>

      <wd-loadmore :state="loadmoreState" @reload="loadNextPage" />
    </template>

    <wd-toast />
    <wd-dialog />
  </view>
</template>
```

**三处值得说明的设计：**

| 设计 | 为什么 |
| --- | --- |
| 驳回理由单独一块高亮 | 学生点进来最想看的就是这个，藏在详情页里等于让人白跑一趟 |
| 已通过时显示活动时间与地点 | “过了之后什么时候去哪”是第二个最想知道的问题 |
| **“取消报名”用 `@click.stop`** | 不加的话点击会冒泡到整行，同时触发跳转 |

**需求规格里写了一条：`CANCELLED` 的记录不删除，仍显示为灰色标签。** 这样学生不会以为自己从没报过而重复提交。

### 5.3 请求与取消

```js
onLoad(() => {
  if (!isLoggedIn()) {
    uni.showToast({ title: '请先登录', icon: 'none' })
    setTimeout(() => uni.redirectTo({ url: '/pages/login/index' }), 600)
    return
  }
  loadFirstPage()
})

onPullDownRefresh(async () => {
  try {
    finished.value = false
    await loadFirstPage()
  } finally {
    uni.stopPullDownRefresh()
  }
})

onReachBottom(() => loadNextPage())

async function loadFirstPage() {
  loading.value = true
  loadError.value = ''
  try {
    const res = await fetchMySignups({
      page: 1,
      pageSize,
      status: currentStatus.value || undefined
    })
    page.value = 1
    list.value = res.list
    finished.value = res.list.length >= res.total
    loaded.value = true
  } catch (err) {
    loadError.value = err.message || '加载失败'
  } finally {
    loading.value = false
  }
}

function handleFilterChange() {
  list.value = []
  finished.value = false
  loaded.value = false
  loadFirstPage()
}

async function handleCancel(item) {
  const ok = await dialog.confirm({
    title: '确认取消报名',
    msg: '取消后名额会被释放，需要时可以重新报名',
    confirmButtonText: '确认取消',
    cancelButtonText: '再想想'
  })
  if (!ok) return

  try {
    await cancelSignup(item.id)
    toast.success('已取消报名')
    item.status = 'CANCELLED'        // 就地更新，不用整页重发请求
  } catch (err) {
    if (err.code === 3002) {
      toast.error('当前状态不允许取消')
      list.value = []
      loadFirstPage()                 // 本地数据过期了，拉一次新的
    }
  }
}
```

**切换筛选时要注意清空列表。** 上面的 `handleFilterChange` 里 `list.value = []` 是必需的 —— 不清的话，新筛选条件的数据会追加在旧数据后面。

**取消成功后就地改 `item.status`。** 不重新请求的理由很实在：用户刚看到一条明确的结果，重新拉一次列表会让滚动位置和加载状态都变化，**体验上反而更差**。状态冲突（`3002`）时才重新拉，因为那说明本地数据确实旧了。

## 六、关键决策

### 决策一 · 姓名不可改

报名表单里的姓名显示为禁用状态，取自账号信息。

**代价**：学生如果在教务系统改了名字，需要先改资料再报名。**收益**：报名记录的姓名可追溯，审核有意义。**这个取舍在校园场景里收益明显更大。**

### 决策二 · 报名的自检放在表单页而不是只在详情页

详情页判断过一次，表单页的 `onLoad` 再判断一次。

**听起来是重复劳动，实际上是必要的**：用户可能从详情页停留几分钟后才点报名，这期间名额可能被抢完。**重复检查的成本是一次请求，漏检的成本是用户填完表才被拒。**

### 决策三 · 取消报名就地更新而不是重拉

理由上面讲过。**关键判据是“这次改动的结果是否可预测”** —— 取消失败的原因如果是“状态不允许”，那说明本地状态不对，必须重拉；成功的话结果就是 `CANCELLED`，不需要问后端。

### 决策四 · 筛选用分段器而不是 tabs

四个筛选项用 `wd-segmented` 比 tabs 更省空间，且**在手机上手指够得着**（`wd-tabs` 通常更高，占掉一屏的十分之一）。

**代价**：分段器一屏只能放 4 个左右的选项。**如果筛选项要增加到六七个，就得换成 `wd-tabs` 或者底部弹层的筛选面板。**

## 七、容易出问题的地方

::: details 点“取消报名”，同时跳到了活动详情

**现象：** 点取消按钮，确认框弹出后页面也跳转了。

**原因：** 取消按钮在整行可点击的容器里，**事件冒泡到外层的 `@tap`**。

**怎么处理：**

```vue
<view class="record" @tap="goActivityDetail(item.activityId)">
  <!-- ✗ 冒泡，会跳转 -->
  <wd-button @click="handleCancel(item)">取消报名</wd-button>

  <!-- ✓ 阻止冒泡 -->
  <wd-button @click.stop="handleCancel(item)">取消报名</wd-button>
</view>
```

**同类问题会出现在**：列表里的收藏按钮、卡片上的分享按钮、表格里的操作列。**规律是“可点击的容器里有可点击的元素”。**

:::

::: details 切了筛选条件，列表里混着上一个条件的数据

**现象：** 从“全部”切到“待审核”，列表里既有待审核也有已通过的记录。

**原因：** 切换时没有清空 `list` 和 `page`，新数据追加在了旧数据后面；或者 `finished` 没重置，导致触底加载不触发。

**怎么处理：** 切换筛选时把这几个状态一起重置：

```js
function handleFilterChange() {
  list.value = []
  page.value = 1
  finished.value = false
  loaded.value = false
  loadFirstPage()
}
```

**四个状态一起清**，漏一个就会有奇怪的表现：漏 `page` 会导致第二次筛选取的是第 2 页；漏 `finished` 会导致列表不再加载更多。

:::

::: details iOS 上“活动时间”显示成 Invalid Date

**现象：** 安卓和开发者工具里正常，iPhone 上显示 `Invalid Date`。

**原因：** 后端返回 `2026-04-10 14:00:00`（带空格），**iOS 的 JavaScript 引擎不接受这种格式。**

**怎么处理：** 走统一的工具函数（`src/utils/date.js` 里的 `formatDateTime`），它内部做了 `replace(/-/g, '/')`。

**检查办法**：搜一下项目里有没有直接用 `new Date(` 的地方：

```bash
grep -rn "new Date(" src/ | grep -v "utils/date"
```

**除了 `date.js` 之外的都应该清掉。**

:::

::: details 取消报名后，详情页的名额没变

**现象：** 取消了一条已通过的报名，回活动详情页，名额还是取消之前的。

**原因：** 详情页的数据是它自己请求的，取消操作发生在“我的报名”页，两个页面各管各的。

**怎么处理：** 详情页在 `onShow` 里刷新（[活动浏览参考实现](/project/impl-mobile-browse) 的 6.1 已经这么做了）。**如果详情页没写 `onShow` 刷新，这条就会挂。**

**验证办法**：报名一条 → 去详情页看名额 → 回“我的报名”取消 → 再回详情页，看名额有没有加回去。

:::

::: details 提交时提示“已经报过名了”，但列表里没有

**现象：** 提交报名返回 `3004`，去“我的报名”看却是空的。

**原因：** 三种可能：

1. **筛选条件不是“全部”** —— 当前选着“待审核”，而那条记录已经被驳回了
2. **后端有脏数据** —— 存在一条 `CANCELLED` 之外的记录但列表接口过滤掉了
3. **报名记录被别的方式修改了**（比如管理端删除过）

**怎么处理：** 前端能做的只有一件事：**收到 `3004` 时把筛选重置为“全部”再跳过去**，至少不会让用户对着一个空列表发懵。

```js
if (err.code === 3004) {
  uni.showToast({ title: '你已经报过这个活动了', icon: 'none' })
  setTimeout(() => {
    currentStatus.value = ''        // 重置筛选
    uni.switchTab({ url: '/pages/signup/my' })
  }, 1200)
}
```

**剩下的是后端的事** —— 如果确实是脏数据，要在后端查“有没有效报名”的判断逻辑里找原因。

:::

## 八、验收清单

- [ ] 未登录进“我的报名”，提示并跳登录页
- [ ] 五种自检都生效：已报过、已结束、非报名中、已截止、名额已满
- [ ] 姓名预填且不可改；学号、班级可从账号信息预填
- [ ] 学号校验：不足 10 位、含非数字都会拦下
- [ ] 提交中按钮转圈且不可重复点
- [ ] 提交成功弹窗说明后续，点“去看看”跳到我的报名
- [ ] `2005` / `2006` / `3004` 三个错误码的提示与后续动作都正确
- [ ] 我的报名四种筛选都正确，切换时不残留上一种的数据
- [ ] `REJECTED` 的记录在列表里就能看到驳回理由
- [ ] 只有 `PENDING` 和 `APPROVED` 显示取消按钮
- [ ] 取消报名有二次确认，成功后状态就地变为“已取消”
- [ ] 取消后回详情页，名额数量增加
- [ ] H5 与微信小程序端都跑一遍

## 九、可以继续做的事

1. **报名的草稿保存。** 用户填了一半被打断（接电话、切走了），回来能继续填
2. **驳回后的重新报名入口。** 在驳回理由下面直接给一个“重新报名”按钮，带上原来的信息
3. **报名记录详情页。** 现在列表点击跳的是活动详情，可以单独做一个报名记录详情，把审核轨迹也展示出来
4. **我的报名页加下拉刷新**（如果还没加）。学生等审核结果时会反复下拉，这个动作是刚需
5. **提交前的姓名修改入口。** 姓名不可改是对的，但要给一个“去修改资料”的跳转，别让用户卡住

---

上一页：[用户端 · 活动浏览参考实现](/project/impl-mobile-browse) ·
返回：[用户端需求规格](/project/mobile)
