# 8. 报名表单与我的报名

## 一个具体的场面

报名功能做完了，测试也通过了。上线第一天，班群里出现这些话：

- “我点了报名，提示成功，然后呢？”
- “我报了两个活动，在哪儿看我自己的报名？”
- “我被拒了，也没说为什么啊”

**三句话指向三个问题**：提交后没有下一步引导、缺少“我的报名”入口、审核结果没展示。

这一节把报名这条链路走完 —— 从填表到看结果，包括被驳回之后怎么办。

## 一、提交前先自检

用户在详情页点了“立即报名”，进到表单页。**在填表之前，有些情况应该先挡住。**

| 检查项 | 怎么知道 | 处理 |
| --- | --- | --- |
| 活动还在报名期吗 | 详情页已经判断过一次，表单页 `onLoad` 再拿一次 | 过期就直接提示并返回 |
| 名额还有吗 | 详情接口的 `quota` 减 `approvedCount` | 满了就提示，按钮置灰 |
| 我是不是已经报过了 | 详情接口返回的 `mySignupStatus` | 直接跳到“我的报名” |

```js
onLoad(async (options) => {
  const activityId = Number(options.activityId)
  if (!activityId) {
    uni.showToast({ title: '参数错误', icon: 'none' })
    setTimeout(() => uni.navigateBack(), 800)
    return
  }

  activity.value = await fetchActivityDetail(activityId)

  // 三种不该让用户填表的情况
  if (activity.value.mySignupStatus && activity.value.mySignupStatus !== 'CANCELLED') {
    uni.showModal({
      title: '你已经报过名了',
      content: '去“我的报名”看看审核结果吧',
      showCancel: false,
      success: () => uni.switchTab({ url: '/pages/signup/my' })
    })
    return
  }

  if (activity.value.status !== 'SIGNING') {
    uni.showModal({
      title: '报名已关闭',
      content: activity.value.status === 'FINISHED' ? '活动已经结束了' : '这个活动已经过了报名时间',
      showCancel: false,
      success: () => uni.navigateBack()
    })
    return
  }

  if (activity.value.quota - activity.value.approvedCount <= 0) {
    uni.showModal({
      title: '名额已满',
      content: '可以看看其他活动',
      showCancel: false,
      success: () => uni.navigateBack()
    })
    return
  }

  // 预填个人信息，别让用户每次重新输
  const profile = uni.getStorageSync('userInfo')
  if (profile) {
    model.studentName = profile.realName || ''
    model.studentNo = profile.studentNo || ''
    model.studentClass = profile.studentClass || ''
  }
})
```

**最后那段预填是体验上的关键。** 报名表单每次填四个字段，第三次之后用户就不耐烦了。登录时后端返回的 `userInfo` 里如果有姓名和学号，直接填上，用户只需要确认。

::: tip 前端自检是为了体验，不是为了防止出错
上面这几个判断**能被绕过** —— 抓包直接发请求就行。真正的把关在后端：后端会重新检查活动状态、名额、重复报名，**这些检查一个都不能省。**

**前端做这些判断的价值在于：让用户在填表之前就知道不行，而不是填完点提交才被拒。** 这是体验优化，不是安全措施 —— 和单元 9 的结论一致。
:::

## 二、提交：把每个错误码对应到一句人话

后端返回的错误码是有分工的，**用户端要把它们翻译成用户能理解的话**：

```js
async function handleSubmit() {
  if (submitting.value) return

  const { valid } = await form.value.validate()
  if (!valid) return

  submitting.value = true
  try {
    await createSignup({
      activityId: activity.value.id,
      studentName: model.studentName,
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
    // 每个码对应一句具体的话和一个后续动作
    const map = {
      2005: { msg: '名额刚好被抢完了', then: 'back' },
      2006: { msg: '已经过了报名截止时间', then: 'back' },
      3002: { msg: '你已经报过这个活动了', then: 'mySignup' },
      1003: { msg: err.message, then: 'stay' },
    }
    const hit = map[err.code] || { msg: err.message || '提交失败，请稍后重试', then: 'stay' }

    uni.showToast({ title: hit.msg, icon: 'none' })

    if (hit.then === 'back') {
      setTimeout(() => uni.navigateBack(), 1200)
    } else if (hit.then === 'mySignup') {
      setTimeout(() => uni.switchTab({ url: '/pages/signup/my' }), 1200)
    }
  } finally {
    submitting.value = false
  }
}
```

**这张映射表是这一节最重要的东西。** 没有它，用户看到的是后端给的原始文案（可能是“操作失败”），也不知道接下来该干什么。

顺带说清一个设计：**成功之后用 `showModal` 而不是 `showToast`。** 因为提交报名是个有后果的动作，用户需要知道“接下来会发生什么”，而且要有一个明确的“去看看”按钮。**一闪而过的提示承载不了这些。**

## 三、我的报名：状态字典放一处

“我的报名”列表的每一行都要显示状态。状态值的颜色、文案、能不能取消，都跟状态相关 —— **这些信息集中放在一个文件里，不要散在页面里。**

```js [src/utils/dict.js]
// 报名状态
export const SIGNUP_STATUS = {
  PENDING:   { label: '待审核', color: '#FF9500' },
  APPROVED:  { label: '已通过', color: '#42b883' },
  REJECTED:  { label: '已驳回', color: '#FA5151' },
  CANCELLED: { label: '已取消', color: '#999999' }
}

// 活动状态
export const ACTIVITY_STATUS = {
  DRAFT:         { label: '草稿', color: '#999999' },
  SIGNING:       { label: '报名中', color: '#42b883' },
  SIGNUP_CLOSED: { label: '报名截止', color: '#FF9500' },
  FINISHED:      { label: '已结束', color: '#999999' }
}

// 活动类型
export const ACTIVITY_TYPE = {
  LECTURE:     { label: '讲座', color: '#42b883' },
  COMPETITION: { label: '比赛', color: '#FF9500' },
  PERFORMANCE: { label: '演出', color: '#7B61FF' },
  SPORTS:      { label: '体育', color: '#FA5151' },
  VOLUNTEER:   { label: '志愿服务', color: '#42b883' },
  OTHER:       { label: '其他', color: '#999999' }
}

export function signupStatusOf(code) {
  return SIGNUP_STATUS[code] || { label: '未知', color: '#999999' }
}

export function activityTypeOf(code) {
  return ACTIVITY_TYPE[code] || ACTIVITY_TYPE.OTHER
}
```

**为什么要单独一个文件？**

管理端的 `dict.js` 讲过一次理由，这里再补一条用户端特有的：**同一个状态在多个地方出现。** “已通过”这个状态会出现在：我的报名列表的标签上、详情页的按钮文案里、报名成功后的提示里。**散在三个文件里改，必然会改漏一个。**

## 四、状态筛选

“我的报名”默认要按状态筛。用分段器（`wd-segmented`）比 tabs 更省空间：

```vue
<template>
  <view class="page">
    <view class="filter-bar">
      <wd-segmented v-model="currentStatus" :options="filterOptions" />
    </view>

    <wd-skeleton v-if="showSkeleton" theme="paragraph" :row-col="skeletonRowCol" />

    <wd-empty v-else-if="!list.length" tip="还没有报名记录" />

    <template v-else>
      <view class="list">
        <view v-for="item in list" :key="item.id" class="record" @tap="goDetail(item.activityId)">
          <view class="record-head">
            <text class="record-title">{{ item.activityTitle }}</text>
            <wd-tag :color="signupStatusOf(item.status).color" plain>
              {{ signupStatusOf(item.status).label }}
            </wd-tag>
          </view>

          <view class="record-meta">
            <text>报名时间：{{ item.createdAt }}</text>
          </view>

          <!-- 驳回理由要显眼，用户最关心这个 -->
          <view v-if="item.status === 'REJECTED' && item.rejectReason" class="reject-box">
            <text class="reject-label">驳回原因</text>
            <text class="reject-text">{{ item.rejectReason }}</text>
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

两个细节：

**一、`@click.stop`。** 取消按钮在整行可点击的区域里，不阻止冒泡的话，点取消会同时触发跳转详情。**这是移动端列表里很常见的一个 bug。**

**二、驳回理由单独一块高亮显示。** 用户点进“我的报名”，**最想知道的就是“为什么被拒了”**。把这个信息藏在详情页里，用户会来回找。

## 五、取消报名

取消不是随时都能做，要按状态判断：

```js
function canCancel(item) {
  // 只有待审核和已通过可以取消，已驳回、已取消不用取消
  if (item.status !== 'PENDING' && item.status !== 'APPROVED') return false
  // 活动结束后不能取消
  if (item.activityStatus === 'FINISHED') return false
  return true
}

async function handleCancel(item) {
  const ok = await dialog.confirm({
    title: '确认取消报名',
    msg: '取消后名额会被释放，如果需要请重新报名',
    confirmButtonText: '确认取消',
    cancelButtonText: '再想想'
  })
  if (!ok) return

  try {
    await cancelSignup(item.id)
    toast.success('已取消报名')
    // 就地更新这一条的状态，不用整页重新请求
    item.status = 'CANCELLED'
  } catch (err) {
    if (err.code === 3002) {
      toast.error('当前状态不允许取消')
      loadList()          // 状态不对说明本地数据旧了，刷新一次
    }
  }
}
```

**注意这里做了两种处理**：成功后就地改这一条的状态（快，不用重新拉列表）；状态冲突时重新拉整个列表（说明本地数据过期了）。

**二次确认是必须的。** 取消报名会释放名额，对用户来说是个有损失的动作 —— 可能是排了半小时队才抢到的名额。

## 六、把三件事连起来

做完这一节，报名这条链路是完整的：

```
活动列表 → 活动详情 → 报名表单 → 提交成功 → 我的报名（看结果）
    ↑                                              ↓
    └──────────── 被驳回，重新报其他活动 ←──────────┘
```

**注意最后那条回边。** 被驳回的学生要能顺畅地回去找别的活动 —— 所以在驳回理由下面给一个“看看其他活动”的入口，或者至少确保 `switchTab` 回活动列表是通的。

## 小结

- 进表单前先自检三件事：**报名期、名额、是否重复报名**；自检是体验优化，**真正的把关在后端**
- 提交前把 `userInfo` 里的姓名学号预填上，**别让用户每次重填**
- **每个业务错误码对应一句人话**加一个后续动作，别把后端的原始文案直接抛给用户
- 成功时用 `showModal` 而不是 `showToast` —— 用户需要知道“接下来会发生什么”
- 状态字典集中在一个文件里，**同一个状态会在多个地方出现**
- 驳回理由要在列表里就显示出来，**那是用户点进来最想看的**
- 取消报名要二次确认，**成功后可以就地改状态**，状态冲突时重新拉列表

## 常见坑

::: details iOS 上时间显示成 Invalid Date 或者空白

**现象：** 安卓和微信开发者工具里正常，iPhone 上 `new Date('2026-03-01 10:00:00')` 得到 `Invalid Date`，页面上显示空白或 NaN。

**原因：** 后端返回的时间格式是 `yyyy-MM-dd HH:mm:ss`（中间是空格）。**iOS 的 JavaScript 引擎不接受这种格式**，只认 `2026-03-01T10:00:00` 或者 `2026/03/01 10:00:00`。安卓的引擎更宽松，所以问题只在 iOS 上出现。

**怎么处理：** 写一个统一的格式化函数，**把空格换成斜杠再解析**：

```js [src/utils/date.js]
export function parseTime(str) {
  if (!str) return null
  // iOS 不认 '2026-03-01 10:00:00'，换成斜杠
  return new Date(String(str).replace(/-/g, '/'))
}

export function formatDate(str) {
  const d = parseTime(str)
  if (!d) return '-'
  const pad = (n) => String(n).padStart(2, '0')
  return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate())
}

// 判断是否已过截止时间
export function isExpired(str) {
  const d = parseTime(str)
  return d ? d.getTime() < Date.now() : false
}
```

**所有时间比较和显示都走这个文件**，别在页面里直接 `new Date(字符串)`。这个坑和管理端的时区问题是两类，**不要混为一谈** —— 这里的问题纯粹是格式解析。

:::

::: details 提交成功了，用户还是重复点，报了两次名

**现象：** 用户以为没提交成功，连点两下，后端出现两条报名记录，或者第二次报错说“已经报过名”。

**原因：** 三种可能：

1. **没有 `submitting` 防重复**，请求还没回来按钮就可以再点
2. **有 `submitting` 但没传给按钮的 `:loading`**，按钮看起来还能点
3. **请求成功了但用户没看到反馈**（提示一闪而过），以为失败又点了一次

**怎么处理：** 三个都要做：

```vue
<wd-button
  type="primary"
  block
  :loading="submitting"
  :disabled="submitting"
  @click="handleSubmit"
>
  {{ submitting ? '提交中…' : '提交报名' }}
</wd-button>
```

```js
async function handleSubmit() {
  if (submitting.value) return    // 双保险，防止极快的连点
  // …
}
```

**第三条最容易被忽略**：成功反馈要足够明显（用 `showModal` 而不是一闪的 toast），用户看到了才不会重复点。

**还有一个兜底思路**：后端对“同一用户同一活动”做唯一约束，重复提交时返回 `3002`。**前端防重复是体验，后端防重复才是保证。**

:::

::: details 取消报名成功了，但名额数字没变

**现象：** 用户取消报名后回详情页，名额还是取消之前的数字。

**原因：** 详情页的数据是缓存的那一份，取消操作发生在“我的报名”页，两个页面各管各的数据。

**怎么处理：** 三种办法，按场景选：

| 办法 | 适合 |
| --- | --- |
| 详情页在 `onShow` 重新请求 | 详情页是数据的主人，最直接 |
| 取消成功后弹提示，让用户自己下拉刷新 | 数据实时性要求不高 |
| 把活动详情放进全局 store，两处共享 | 多处都需要同一份实时数据 |

**本项目用第一种**（详情页 `onShow` 刷新）。**第三种要谨慎**：把详情塞进 store 听起来方便，但要处理“什么时候该失效”的问题，容易引入更麻烦的 bug。

:::

::: details 列表点“取消报名”，同时跳到了详情页

**现象：** 点取消按钮，确认框弹出来了，关掉之后页面跳到了活动详情。

**原因：** 取消按钮在整行可点击的区域里，**事件冒泡到外层，触发了行的 `@tap`**。

**怎么处理：** 在按钮上加 `.stop`：

```vue
<view class="record" @tap="goDetail(item.activityId)">
  <!-- ✗ 冒泡到外层，会跳转 -->
  <wd-button @click="handleCancel(item)">取消报名</wd-button>

  <!-- ✓ 阻止冒泡 -->
  <wd-button @click.stop="handleCancel(item)">取消报名</wd-button>
</view>
```

**同类问题还会出现在**：卡片里的收藏按钮、列表里的下拉菜单、表格里的操作列。**凡是“可点击的行里有可点击的元素”，都要记得处理冒泡。**

:::

## 课后练习

**把报名链路做完整，重点验证被驳回这个分支。**

| 任务 | 要求 |
| --- | --- |
| 表单页 | 三个自检：报名期、名额、重复报名；预填 userInfo |
| 提交 | 用假接口，可切换返回成功或指定的错误码 |
| 错误码 | `2005` / `2006` / `3002` 分别有对应的提示与后续动作 |
| 我的报名 | 状态筛选、四态、触底加载 |
| 驳回理由 | 在列表里高亮显示，不是藏在详情里 |
| 取消报名 | 二次确认、状态限制、成功后就地更新 |
| 时间处理 | 所有时间显示与比较走统一的工具函数 |
| 不许做的 | 不要在页面里直接 `new Date(后端字符串)` |

::: details 验收标准与参考思路

**验收标准：**

| 项 | 要求 |
| --- | --- |
| 自检 | 把活动状态改成 `FINISHED`，进表单页直接被拦下 |
| 预填 | 登录后进表单，姓名和学号已经填好 |
| 错误码 | 分别触发三个码，提示文案不同，后续动作也不同 |
| 取消 | `REJECTED` 状态的记录上看不到取消按钮 |
| 时间 | 在微信开发者工具里选 iOS 机型模拟，时间正常显示 |
| 驳回 | 驳回的记录在列表里就能看到原因 |

**不合格的写法：**

```js
// ✗ 把后端的原始文案直接抛给用户
catch (err) {
  uni.showToast({ title: err.message, icon: 'none' })
}

// ✗ 时间直接在页面里转换
<text>{{ new Date(item.createdAt).toLocaleDateString() }}</text>
```

第一处的问题：后端返回“操作失败”或“名额已满”这种通用文案时，用户不知道该干什么。**错误码存在的意义就是让前端能给出更有用的提示。**

第二处的问题：iOS 上直接崩掉，而且**安卓上看着正常会让你以为写对了**。

**合格的写法：**

```js
// 统一的错误映射，在 api 层或页面层都行，但要有一处
const SIGNUP_ERROR = {
  2005: { msg: '名额刚好被抢完了', action: 'refresh' },
  2006: { msg: '已过报名截止时间', action: 'back' },
  3002: { msg: '你已经报过这个活动了', action: 'mySignup' }
}

function handleSignupError(err) {
  const hit = SIGNUP_ERROR[err.code]
  if (!hit) {
    uni.showToast({ title: err.message || '提交失败', icon: 'none' })
    return
  }
  uni.showToast({ title: hit.msg, icon: 'none' })
  if (hit.action === 'back') setTimeout(() => uni.navigateBack(), 1200)
  if (hit.action === 'mySignup') setTimeout(() => uni.switchTab({ url: '/pages/signup/my' }), 1200)
  if (hit.action === 'refresh') refreshDetail()
}
```

**参考思路：**

两个地方值得多想：

**一是“被驳回”这个分支的完整处理。** 用户被拒了，他会：看到理由 → 想报别的活动 → 回活动列表。**这条路径要能顺畅走通**，而且驳回理由要具体（“材料不全”这种等于没说，好的理由会写清“请补充班级信息后重新报名”）。

**二是复习一下单元 8 的 AI 协作里讲过的“状态放错位置”。** “我的报名”和“活动详情”都需要知道自己报没报过，如果你把报名状态抽成一个组合式函数，**注意 `ref` 要定义在函数内部**，定义在模块作用域会导致两个页面互相干扰。这个坑在用户端一样会踩。

:::

---

上一节：[列表页与详情页](/mobile/07-list-detail) ·
下一节：[打包与发布](/mobile/09-publish)
