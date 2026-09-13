# 报名审核模块 · 参考实现

报名审核是主线三步里的第二步。学生在前台报名，组织者和审核员在管理端处理这些报名：通过、驳回、撤销。

这一步有一个和别处不一样的特点：**每一个审核动作都会改变活动的名额数据。** 活动管理模块改的是活动自己的字段，场地管理改的是场地自己的字段，只有报名审核会“牵一发而动全身”—— 通过一条报名，活动的 `approvedCount` 加一，报名入口可能在下一刻就关闭。所以这一篇的重点不在列表页怎么写，而在**名额和报名数之间的联动**。

**先自己写一遍再来看这篇。** 直接照抄的结果是答辩时讲不出为什么。

## 一、模块范围与页面地图

### 页面 → 路由 → 接口

| 页面 | 路由 | 主要接口 | 可访问角色 |
| --- | --- | --- | --- |
| 全局报名列表 | `/signup` | `GET /api/signups` | 组织者、审核员 |
| 某活动的报名 | `/activity/:id/signups` | `GET /api/signups?activityId=:id`、`GET /api/activities/:id/signup-stats` | 组织者、审核员 |

| 动作 | 接口 | 副作用 |
| --- | --- | --- |
| 审核通过 | `PATCH /api/signups/:id/approve` | `pendingCount` 减一，`approvedCount` 加一 |
| 审核驳回 | `PATCH /api/signups/:id/reject` | `pendingCount` 减一，写入驳回理由 |
| 撤销审核 | `PATCH /api/signups/:id/cancel` | 若原状态是 `APPROVED`，`approvedCount` 减一（释放名额） |

**注意这里没有“报名详情页”。** 报名的字段很少，用不着单独开一页；审核动作直接做在列表的行操作里。这和活动管理不一样 —— 活动有说明、统计、场次要展示，所以有详情页。**页面要不要拆，看信息量，不看对称性。**

接口的完整定义看[接口约定](/project/api)的第七节，业务规则看[业务规则与状态流转](/project/rules)的第五节。**这两页没读完不要动笔。**

### 数据流

```
组织者点“通过”
      │
      ▼
SignupList.vue  handleApprove(row)
      │  二次确认
      ▼
api/signup.js   approveSignup(row.id)
      │
      ▼
api/request.js  带 token，走 /api 代理
      │
      ▼
后端：开启事务 → 校验状态是 PENDING → 校验名额未满
      → 改报名状态 → 改活动 approvedCount / pendingCount → 提交
      │
      ▼
前端拿到结果 → 重新拉列表 → 用接口返回的数据覆盖本地
```

这张图里只有一处需要记住：**链条的后半段是“重新拉列表”，不是“本地改数字”。** 原因在第七节展开。

## 二、接口封装：`api/signup.js`

接口层只做一件事：把后端约定的路径、方法、参数名翻译成函数。页面里不应该出现 `/signups` 这样的字符串。

```js [src/api/signup.js]
import request from './request'

/**
 * 报名列表。
 * @param {Object} params 支持 activityId / status / keyword / page / pageSize
 * @returns {Promise<{ list: Array, total: number }>}
 */
export function getSignupList(params) {
  return request.get('/signups', { params })
}

/**
 * 某个活动的报名统计。活动详情页顶部和名额提示用这份数据。
 * @returns {Promise<{ quota, approvedCount, pendingCount, rejectedCount, remaining }>}
 */
export function getSignupStats(activityId) {
  return request.get(`/activities/${activityId}/signup-stats`)
}

/** 审核通过。没有请求体，动作全在 URL 里 */
export function approveSignup(id) {
  return request.patch(`/signups/${id}/approve`)
}

/** 审核驳回。reason 必填，长度 5 到 100 字，后端也会校验 */
export function rejectSignup(id, reason) {
  return request.patch(`/signups/${id}/reject`, { rejectReason: reason })
}

/**
 * 撤销审核。
 * 后端会自己判断原来是不是通过状态，通过状态才释放名额。
 * 所以这里不用传“是否已通过”，传了反而多一份不一致的可能。
 */
export function cancelSignup(id, reason) {
  return request.patch(`/signups/${id}/cancel`, { reason })
}
```

三个函数有两点值得说：

**一、三个动作都是 `PATCH`。** 它们只改一条记录的一两个字段，不是替换整个报名对象。用 `PUT` 语义上不对，还会逼着前端把整条报名记录回传一遍 —— 而报名记录里有 `studentName`、`activityTitle` 这类前端不该提交的只读字段。

**二、`cancelSignup` 不接收“原状态”。** 有人会想：撤销时前端明明知道 `row.status`，顺手告诉后端“这条是已通过的，记得释放名额”不是更省事？不能这么做。**名额账目必须由后端一个人记。** 前端传过来的状态可能是上一次刷新时的旧值，如果后端照着它执行，账就错了。

### 让错误带上业务码

[接口约定](/project/api)里的错误码表要求前端按 `code` 分支处理，比如 `2005` 名额已满要单独提示。但请求拦截器里写的是 `Promise.reject(new Error(message))`，`Error` 身上没有 `code`，页面里 `e.code === 2005` 永远不成立。

**所以拦截器 reject 之前要把 `code` 和 `data` 挂到错误对象上：**

```js [src/api/request.js（响应拦截器节选）]
const res = response.data          // { code, message, data }
if (res.code === undefined) return response
if (res.code === 0) return res.data

// 业务失败：统一提示，并拒绝
const err = new Error(res.message || '操作失败')
err.code = res.code                // 页面靠 err.code 区分 2005 / 3002 / 3003
err.data = res.data                // 冲突场次这类附加信息也一并带上
ElMessage.error(err.message)
return Promise.reject(err)
```

**只挂 `code` 不够，`data` 也要带上。** 冲突预检的 `4003` 会在 `data` 里带回冲突的场次信息，丢了它前端就只能提示一句“时段冲突”，用户不知道和谁冲突。这条在[场次与场地模块](/project/impl-session)里会用到。

## 三、报名状态字典

四个状态的颜色和文案统一放在 `utils/dict.js`，页面里一个中文字符都不写。

```js [src/utils/dict.js]
export const SIGNUP_STATUS_OPTIONS = [
  { label: '待审核', value: 'PENDING' },
  { label: '已通过', value: 'APPROVED' },
  { label: '已驳回', value: 'REJECTED' },
  { label: '已取消', value: 'CANCELLED' }
]

export function signupStatusLabel(value) {
  return SIGNUP_STATUS_OPTIONS.find((o) => o.value === value)?.label ?? '未知'
}

/**
 * 标签颜色：
 * 待审核用 warning（需要人处理，醒目但不报警）
 * 已通过用 success
 * 已驳回用 danger
 * 已取消用 info（已经过去的事，不该抢注意力）
 */
export function signupStatusTagType(value) {
  return (
    {
      PENDING: 'warning',
      APPROVED: 'success',
      REJECTED: 'danger',
      CANCELLED: 'info'
    }[value] ?? 'info'
  )
}
```

| 状态 | 值 | 含义 | 标签色 |
| --- | --- | --- | --- |
| 待审核 | `PENDING` | 学生已提交，等处理 | `warning` 橙 |
| 已通过 | `APPROVED` | 审核通过，**占用一个名额** | `success` 绿 |
| 已驳回 | `REJECTED` | 审核不通过，附驳回理由 | `danger` 红 |
| 已取消 | `CANCELLED` | 学生撤销，或组织者撤销审核 | `info` 灰 |

**注意 `REJECTED` 和 `CANCELLED` 都是“不再占用名额”，但语义不同。** 驳回是“你不符合条件”，取消是“这条记录作废了”。前者会带着一条驳回理由展示给学生，后者只是一个终态。展示的时候要区分，不能把两者都显示成灰色标签了事。

字典里还应该有一份“哪些状态允许哪些操作”的规则。它和[业务规则](/project/rules)的第五节一一对应：

```js [src/utils/dict.js（续）]
export function canApprove(status) {
  return status === 'PENDING'
}

export function canReject(status) {
  return status === 'PENDING'
}

/** 待审核可以撤销（撤回），已通过也可以撤销（释放名额）；终态不可撤销 */
export function canCancel(status) {
  return status === 'PENDING' || status === 'APPROVED'
}
```

**把这三个判断写进字典而不是页面里**，是因为它们是业务规则的直接翻译。`REJECTED` 是终态、不能直接改成通过，这条规则后面还可能被别的地方用到（比如看板的待办列表），集中一处才不会前后不一致。

## 四、报名列表页

列表页的骨架和[11.4 列表页标准做法](/unit11/04-list-page)里的模板完全一样：`useTable` 管查询、分页和四态，页面只负责列定义和行操作。这一节只讲报名列表特有的部分。

```vue [src/views/signup/SignupList.vue]
<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getSignupList, approveSignup, rejectSignup, cancelSignup } from '@/api/signup'
import { getActivityDetail } from '@/api/activity'
import { useTable } from '@/composables/useTable'
import {
  SIGNUP_STATUS_OPTIONS,
  signupStatusLabel,
  signupStatusTagType,
  canApprove,
  canReject,
  canCancel
} from '@/utils/dict'
import { formatDateTime } from '@/utils/format'

defineOptions({ name: 'SignupList' })

const route = useRoute()

// 全局入口 /signup 没有 id；活动入口 /activity/:id/signups 有 id
const activityId = computed(() => route.params.id ?? '')

// 活动入口要显示活动标题，全局入口显示固定文案
const activityTitle = ref('')
const pageTitle = computed(() => {
  if (!activityId.value) return '报名审核'
  return activityTitle.value || '活动报名'
})

async function loadActivityTitle() {
  if (!activityId.value) {
    activityTitle.value = ''
    return
  }
  const data = await getActivityDetail(activityId.value)
  activityTitle.value = data.title
}

const {
  query, page, pageSize, total, list, loading, error, isEmpty,
  load, search, reset, handleSizeChange, handlePageChange
} = useTable(
  async (params) => {
    // activityId 固定拼进去，用户改不了，所以不出现在查询表单里
    const data = await getSignupList({
      ...params,
      activityId: activityId.value || undefined
    })
    return { list: data.list, total: data.total }
  },
  {
    query: {
      keyword: '',
      status: ''
    },
    // 关掉 useTable 的自动首请求：下面的 watch 配了 immediate，
    // 首次加载由它触发。两者都开着的话，进页面会发两次请求。
    immediate: false
  }
)

// 两个入口共用同一个组件，Vue Router 默认会复用实例、不重新挂载。
// 所以参数变化要手动重新请求，否则从“全部报名”切到“某活动的报名”看不到数据变化。
watch(activityId, () => {
  loadActivityTitle()
  search()
}, { immediate: true })

// ---- 审核操作 ----

async function handleApprove(row) {
  try {
    await ElMessageBox.confirm(
      `确定通过“${row.studentName}”报名“${row.activityTitle}”吗？通过后会占用该活动的一个名额。`,
      '审核通过确认',
      { type: 'warning', confirmButtonText: '通过', cancelButtonText: '再想想' }
    )
  } catch {
    return // 用户点了取消或关闭
  }

  try {
    await approveSignup(row.id)
    ElMessage.success('已通过')
    load()
  } catch (e) {
    // 2005 = 名额已满。拦截器已经弹过一句后端文案，这里补一条可执行的建议
    if (e.code === 2005) {
      ElMessage.warning('名额已满：可以撤销一条已有的通过记录，或把活动名额调大')
    }
  }
}

async function handleReject(row) {
  let reason
  try {
    const res = await ElMessageBox.prompt(
      `请填写驳回“${row.studentName}”的理由，这条理由会展示给报名的学生。`,
      '驳回报名',
      {
        confirmButtonText: '确认驳回',
        cancelButtonText: '取消',
        inputType: 'textarea',
        inputPlaceholder: '例如：本活动仅面向声乐特长学生，你的报名信息不符合要求',
        // 返回 true 才允许确认；返回字符串则作为错误提示显示在输入框下
        inputValidator: (value) => {
          const text = (value ?? '').trim()
          if (text.length < 5) return '驳回理由至少 5 个字'
          if (text.length > 100) return '驳回理由最多 100 个字'
          return true
        }
      }
    )
    reason = res.value
  } catch {
    return // 用户取消，prompt 会 reject
  }

  await rejectSignup(row.id, reason.trim())
  ElMessage.success('已驳回')
  load()
}

async function handleCancel(row) {
  const willRelease = row.status === 'APPROVED'
  const tip = willRelease
    ? `“${row.studentName}”当前是已通过，撤销后这个名额会被释放，活动恢复可以接受新报名。确定撤销吗？`
    : `确定撤销“${row.studentName}”的这条报名吗？`

  try {
    await ElMessageBox.confirm(tip, '撤销审核', {
      type: 'warning',
      confirmButtonText: '确认撤销',
      cancelButtonText: '取消'
    })
  } catch {
    return
  }

  await cancelSignup(row.id, '审核有误，重新处理')
  ElMessage.success(willRelease ? '已撤销，名额已释放' : '已撤销')
  load()
}
</script>

<template>
  <div class="page">
    <el-card shadow="never" class="filter-card">
      <template #header>
        <span class="page-title">{{ pageTitle }}</span>
      </template>

      <el-form :model="query" inline @submit.prevent="search">
        <el-form-item label="学生">
          <el-input
            v-model="query.keyword"
            placeholder="姓名 / 学号"
            clearable
            style="width: 200px"
            @keyup.enter="search"
          />
        </el-form-item>

        <el-form-item label="状态">
          <el-select v-model="query.status" placeholder="全部" clearable style="width: 140px">
            <el-option
              v-for="opt in SIGNUP_STATUS_OPTIONS"
              :key="opt.value"
              :label="opt.label"
              :value="opt.value"
            />
          </el-select>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="loading" @click="search">查询</el-button>
          <el-button @click="reset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never">
      <div class="table-toolbar">
        <span class="total-hint">共 {{ total }} 条</span>
      </div>

      <el-table v-loading="loading" :data="list" border stripe row-key="id" style="width: 100%">
        <el-table-column prop="studentName" label="学生姓名" width="110" />
        <el-table-column prop="studentNo" label="学号" width="140" class-name="mono" />
        <el-table-column prop="studentClass" label="班级" width="120" />

        <el-table-column prop="activityTitle" label="活动标题" min-width="180" show-overflow-tooltip />

        <el-table-column label="报名时间" width="170">
          <template #default="{ row }">{{ formatDateTime(row.createdAt) }}</template>
        </el-table-column>

        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="signupStatusTagType(row.status)" size="small">
              {{ signupStatusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="审核人" width="110">
          <template #default="{ row }">{{ row.auditorName || '—' }}</template>
        </el-table-column>

        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button v-if="canApprove(row.status)" link type="primary" @click="handleApprove(row)">
              通过
            </el-button>
            <el-button v-if="canReject(row.status)" link type="danger" @click="handleReject(row)">
              驳回
            </el-button>
            <el-button v-if="canCancel(row.status)" link type="info" @click="handleCancel(row)">
              撤销
            </el-button>
            <span v-if="row.status === 'REJECTED' || row.status === 'CANCELLED'" class="muted">
              已结束
            </span>
          </template>
        </el-table-column>

        <template #empty>
          <div v-if="error" class="state-block">
            <p class="state-title">报名数据加载失败</p>
            <p class="state-desc">{{ error.message }}</p>
            <el-button type="primary" @click="load">重新加载</el-button>
          </div>
          <div v-else-if="isEmpty" class="state-block">
            <p class="state-title">这个活动还没有收到报名</p>
            <p class="state-desc">学生报名后会出现在这里，你就可以审核了。</p>
          </div>
        </template>
      </el-table>

      <div class="pagination-wrap">
        <el-pagination
          :current-page="page"
          :page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next, jumper"
          background
          @current-change="handlePageChange"
          @size-change="handleSizeChange"
        />
      </div>
    </el-card>
  </div>
</template>
```

### 查询：三个维度，一个入口

| 查询条件 | 参数 | 说明 |
| --- | --- | --- |
| 活动 | `activityId` | **只在活动入口出现**，不出现在查询表单里，由路由参数固定 |
| 状态 | `status` | 下拉选择，值用英文枚举，显示用中文标签 |
| 学生 | `keyword` | 一个输入框同时按姓名和学号匹配，具体匹配哪些字段由后端决定 |

**为什么活动筛选不做成下拉框？** 在全局入口里，让用户从几十个活动里选一个来筛，体验很差。真正的入口是“从活动详情点进来看这个活动的报名”。所以全局列表不做活动筛选，要看某个活动就从活动详情进去。

### 表格列

| 列 | 字段 | 呈现方式 |
| --- | --- | --- |
| 学生姓名 | `studentName` | 纯文字 |
| 学号 | `studentNo` | 等宽字体，方便核对 |
| 班级 | `studentClass` | 纯文字 |
| 活动标题 | `activityTitle` | 超长省略，悬停显示完整 |
| 报名时间 | `createdAt` | `formatDateTime` 格式化 |
| 状态 | `status` | 彩色标签 |
| 审核人 | `auditorName` | 未审核时显示“—” |
| 操作 | — | 按状态显隐 |

**“学号用等宽字体”这个细节值得做。** 学号是一串数字，审核时经常要逐个核对，等宽字体让数字对齐，眼睛不容易串行。一个 `class-name="mono"` 加一行样式就够了。

### 四态与分页

四态沿用模板：初始、加载中、成功有数据、成功无数据、失败。**报名列表的“无数据”文案和活动列表不同**：

| 入口 | 无数据文案 | 引导动作 |
| --- | --- | --- |
| 全局 | 还没有报名记录 | 无（这不是问题，等等就有） |
| 某活动 | 这个活动还没有收到报名 | 无（同上） |

**这里不要放“立即创建”按钮。** 活动列表的无数据可以引导去创建，报名列表不行 —— 报名是学生产生的，组织者无法在这里造一条。给一个点不动的按钮比不给更糟。

分页参数由 `useTable` 管，`total` 用接口返回的总数。**注意报名列表的数据量可能很大**，一个热门活动上千条报名很正常，所以 `pageSize` 上限就是 50，不要为了“一次看完”去拉全部。

## 五、两个入口的写法差异

`/signup` 和 `/activity/:id/signups` 用的是同一个 `SignupList.vue`，差别只有三处：

| 差异 | 全局入口 | 活动入口 |
| --- | --- | --- |
| 活动筛选 | 无 | 路由参数 `:id` 固定，用户改不了 |
| 页面标题 | “报名审核” | 活动标题（如“2026 春季校园歌手大赛”的报名） |
| 进入方式 | 侧边栏菜单 | 活动详情页的“查看报名”按钮 |

**列表标题为什么要显示活动标题？** 因为从活动详情跳进来之后，用户的任务是“处理这个活动的报名”。如果标题还写着“报名审核”，用户会怀疑自己是不是点错了、看到的到底是不是那一个活动。**把上下文显示出来，用户才敢放心操作。**

### 路由参数变化时组件会复用

这是两个入口共用一个组件时最容易踩的坑。

Vue Router 在同一个路由记录下切换参数，**默认会复用组件实例，不会重新执行 `onMounted`**。也就是说，从 `/activity/1/signups` 跳到 `/activity/2/signups`，`useTable` 里的首次请求不会重跑，页面还停在活动 1 的数据上。

处理办法是监听参数变化：

```js
watch(activityId, () => {
  loadActivityTitle()
  search()
}, { immediate: true })
```

**注意这里用 `search()` 不是 `load()`。** 换了活动相当于换了筛选条件，必须回到第一页，否则用户在第 5 页切活动，很可能看到空列表。

把这个 watch 写成 `immediate: true`，进入页面时的首次请求就由它触发。**同时要把 `useTable` 的 `immediate` 关掉**（传 `immediate: false`），否则两个入口各触发一次，进页面会连着发两次一样的请求。**这类“两个机制都负责首次加载”的重复请求很隐蔽**，因为功能看起来完全正常，只有在网络面板里才看得出来。

## 六、三个审核动作

### 通过：二次确认 + 名额提示

通过是“加一个名额占用”的动作，属于会改变资源状态的操作，所以要有二次确认。确认文案要说清两件事：**改谁**、**改完有什么后果**。

```js
`确定通过“${row.studentName}”报名“${row.activityTitle}”吗？通过后会占用该活动的一个名额。`
```

名额已满时怎么办？**前端不预判，只处理后端返回的错误。** 也就是说，按钮不因为“名额看起来满了”就禁用，而是等后端返回 `2005` 再提示。理由在第七节讲清楚。

提示文案要给下一步，不能只说一句“名额已满”：

| ✗ 不合格的提示 | ✓ 合格的提示 |
| --- | --- |
| 操作失败 | 名额已满：可以撤销一条已有的通过记录，或把活动名额调大 |

### 驳回：`ElMessageBox.prompt` 输入理由

驳回必须填理由，长度 5 到 100 字，这是[业务规则](/project/rules)里的硬要求。用 `ElMessageBox.prompt` 做输入框，`inputValidator` 做前端校验：

```js
inputValidator: (value) => {
  const text = (value ?? '').trim()
  if (text.length < 5) return '驳回理由至少 5 个字'
  if (text.length > 100) return '驳回理由最多 100 个字'
  return true
}
```

`inputValidator` 的返回值有三种含义，用法别搞混：

| 返回值 | 效果 |
| --- | --- |
| `true` | 校验通过，可以确认 |
| `false` | 校验不通过，但**不显示任何提示**（等于让用户自己猜） |
| 字符串 | 校验不通过，字符串作为错误提示显示在输入框下方（推荐） |

**校验通过后还要 `.trim()` 再提交。** 用户可能只敲了几个空格，`'    '.length` 是 4，小于 5 会被拦下；但如果敲 6 个空格，长度校验就通过了，`trim` 之后是空字符串，后端会返回 `3003`。前端这一层 `trim` 能把这种明显无效的输入提前挡掉。

**前端的字数校验只是体验优化。** 用户能改前端代码，也能直接调接口。后端必须再校验一次 `rejectReason` 的长度 —— 和所有校验一样，前端负责早提示，后端负责真约束。

### 撤销：通过的要释放名额

撤销是三个动作里唯一“可能释放名额”的。所以在确认弹窗里必须把这件事说清楚，尤其是当原状态是 `APPROVED` 时：

| 原状态 | 影响 | 确认文案 |
| --- | --- | --- |
| `PENDING` | 只是撤回待审核，名额没动过 | 确定撤销这条报名吗？ |
| `APPROVED` | `approvedCount` 减一，**名额被释放** | 撤销后这个名额会被释放，活动恢复可以接受新报名 |

**“名额被释放”不是一句套话。** 它意味着：如果这个活动之前名额满了、报名入口是关着的，撤销一条通过之后，报名入口会自动恢复可用。这正是[业务规则](/project/rules)里“名额满了不改状态、靠判断”的好处 —— 撤销之后不需要任何额外的动作，入口自己就开了。

**操作后的提示也要跟着状态走：** 撤销待审核提示“已撤销”，撤销已通过提示“已撤销，名额已释放”。用户需要确认名额确实回来了。

## 七、名额与报名数的联动

这一节是报名模块的核心。前面所有代码最后都要落到这一条上。

### 三个数字各自由谁维护

| 数字 | 含义 | 谁改 |
| --- | --- | --- |
| `quota` | 名额上限 | 组织者在活动编辑页改 |
| `approvedCount` | 已通过人数 | **只有后端在审核事务里改** |
| `pendingCount` | 待审核人数 | **只有后端在报名、审核时改** |

**关键规则：只有 `APPROVED` 占用名额。** `PENDING` 不占。所以判断“还能不能通过”看的是 `approvedCount < quota`，和 `pendingCount` 无关。

### 为什么前端算出来的名额一定不准

四个原因，任何一个都足够让前端算错：

**一、前端只拿到了当前页的数据。** 列表接口返回的是第 N 页的 20 条，不是活动的全部报名。想在前端数出“已通过多少”就得把所有页都拉下来，那要几十个请求。

**二、前端拿到的数字是“上次请求那一刻”的快照。** 你页面上的 `approvedCount = 42`，是半分钟前加载的数据。这半分钟里别人可能已经审核了三条。

**三、并发。** 两个人同时点通过，前端各自看到的是同一份旧数据，谁都不知道对方也在操作。下面单独展开。

**四、审核的副作用在服务端。** “通过报名”和“活动名额加一”是同一件事的两半，必须一起成功或一起失败。这件事只有拿着数据库事务的后端做得到。

结论只有一句：**前端只负责显示数字，一个数字都不要自己算、自己加。**

### 并发场景：两个组织者同时点通过

拿一个具体的例子。活动名额 `quota = 100`，当前 `approvedCount = 99`，还剩一个名额。

1. 组织者 A 在电脑上点“通过”，组织者 B 在手机上同时点“通过”，两个请求几乎同时到达后端。
2. 如果后端的逻辑是“先查 `approvedCount`，判断小于 `quota`，然后更新”，两个请求都会读到 `approvedCount = 99`。
3. 两边都判断 99 小于 100，都认为还有名额。
4. 两边都执行“把状态改为通过、`approvedCount` 加一”。

结果 `approvedCount` 变成 101，超卖了一个。

**前端做什么都拦不住它。** 两个请求在前端是各自独立的，A 的浏览器不知道 B 在操作。这就是为什么这件事“必须由后端保证”。

### 后端必须用事务加锁

前端不需要写后端的代码，但**必须知道这必须是后端保证的**，并且能在答辩时讲清楚。后端的做法是把“检查名额”和“写入审核结果”放进同一个数据库事务，并对活动行加锁：

```
BEGIN;
  -- 悲观锁：锁住这个活动的行，其他事务要排队
  SELECT quota, approved_count, pending_count FROM activity
   WHERE id = ? FOR UPDATE;

  -- 在锁的保护下重新检查
  IF approved_count >= quota THEN
    ROLLBACK;  -- 返回 2005 名额已满
  END IF;

  UPDATE signup SET status = 'APPROVED', auditor_id = ?, audited_at = NOW()
   WHERE id = ? AND status = 'PENDING';

  UPDATE activity SET approved_count = approved_count + 1, pending_count = pending_count - 1
   WHERE id = ?;

COMMIT;
```

关键在 `FOR UPDATE` 这一句。加了行锁之后，B 的请求会等 A 的事务提交，拿到的是更新后的 `approved_count = 100`，于是返回 `2005`。**超卖被拦住了。**

也可以用乐观锁（版本号）实现，具体选哪种由后端决定。**前端要知道的是这条界限：这必须是后端保证的。**

::: danger 前端自己做名额校验顶替不了后端
有人觉得“提交前先请求一次名额统计，满了就不让点”，这样能避免超卖。

**不能。** 你在请求统计和真正提交之间有一个时间差，哪怕只有几百毫秒，并发就发生在这个时间差里。而且并发的时间窗口比你想象的大 —— 两个人看到“还剩一个名额”的页面之后，可能过几秒才点按钮。

**前端做校验的唯一价值是提前给用户反馈，止损的价值为 0。**
:::

### 前端该做的三件事

1. **提交后以接口返回的最新数据为准。** 审核成功后调 `load()` 重新拉列表，让后端返回的 `approvedCount` 覆盖本地。**不要写 `row.approvedCount++`。**
2. **名额进度用专门接口拿。** 活动详情顶部显示“42 / 100”要用 `GET /api/activities/:id/signup-stats`，不要用“查列表然后数长度”的方式 —— 那只数了当前页。
3. **把后端的 `2005` 处理掉。** 拦截器提示后端文案，页面里补一句可执行的建议（撤销已有通过，或调大名额）。

```js
// ✗ 本地自增：和其他行的数字对不上，也和活动详情页对不上
async function handleApprove(row) {
  await approveSignup(row.id)
  row.status = 'APPROVED'
  row.approvedCount += 1
}

// ✓ 让后端说了算
async function handleApprove(row) {
  await approveSignup(row.id)
  ElMessage.success('已通过')
  load() // 重新拉，用接口返回的数据覆盖本地
}
```

**“审核后整页刷新”这个选择在第九节还会再讲一次**，因为它和“只刷当前行”是同一组取舍。

## 八、批量审核

待审核多的时候，一条一条点很费时间。批量审核让用户勾选多条一次处理。

先在脚本里准备两个状态，再在表格上加选择列：

```js [src/views/signup/SignupList.vue（脚本补充）]
import { ref } from 'vue'

const tableRef = ref()
const selectedRows = ref([])

function handleSelectionChange(rows) {
  selectedRows.value = rows
}
```

```vue
<el-table
  ref="tableRef"
  :data="list"
  row-key="id"
  @selection-change="handleSelectionChange"
>
  <el-table-column type="selection" width="48" reserve-selection />
  <!-- 其他列 -->
</el-table>
```

**`row-key` 和 `reserve-selection` 缺一不可。** 跨页勾选（第 1 页勾两条，翻到第 2 页再勾两条）要靠这两个属性，没有它们翻页后勾选就丢了 —— 用户以为勾了 4 条，实际只提交了当前页的 2 条。

### `Promise.allSettled` 和 `Promise.all` 的区别

批量审核要逐条调接口，两条路：

```js
// ✗ Promise.all：一条失败，整体进 reject，成功的那几条结果也一起丢了
try {
  await Promise.all(ids.map((id) => approveSignup(id)))
  ElMessage.success('全部通过')
} catch (e) {
  ElMessage.error('批量审核出错') // 不知道有哪几条成功了
}
```

`Promise.all` 的规则是“有一个失败就整体失败”。问题是**前面的请求已经真的执行了**，后端的数据已经被改了，但前端拿不到任何结果，只能笼统报一句“出错”。用户不知道接下来该重试哪些，只能刷新页面自己看。

```js
// ✓ Promise.allSettled：每条独立结算，成功的和失败的都拿得到
const results = await Promise.allSettled(ids.map((id) => approveSignup(id)))

const okCount = results.filter((r) => r.status === 'fulfilled').length
const failures = results.filter((r) => r.status === 'rejected')
```

| 方法 | 什么时候用 |
| --- | --- |
| `Promise.all` | 所有请求必须全部成功，有一个失败整件事就没意义（比如同时提交一份表单的多个必填部分） |
| `Promise.allSettled` | 每个请求互相独立，成功的要保留、失败的单独处理（批量审核、批量删除、看板多个区块） |

**批量操作几乎总是该用 `allSettled`。** 因为它们本来就是一组独立的操作，没有“必须同生共死”的语义。

`allSettled` 返回的每一项长这样：

```js
{ status: 'fulfilled', value: 接口返回的数据 }
{ status: 'rejected',  reason: 错误对象 }   // 注意是 reason 不是 value
```

**取值的时候别写错**：成功取 `value`，失败取 `reason`。

### 部分失败怎么提示

三种情况分开处理，提示的语气和形式都不同：

```js
async function handleBatchApprove() {
  if (selectedRows.value.length === 0) {
    ElMessage.warning('请先勾选要审核的报名')
    return
  }

  const ids = selectedRows.value.map((r) => r.id)
  const results = await Promise.allSettled(ids.map((id) => approveSignup(id)))

  const okCount = results.filter((r) => r.status === 'fulfilled').length
  const failures = results.filter((r) => r.status === 'rejected')

  if (failures.length === 0) {
    ElMessage.success(`已通过 ${okCount} 条`)
  } else if (okCount === 0) {
    ElMessage.error(`全部失败，共 ${failures.length} 条`)
  } else {
    // 部分成功：用常驻弹窗，不要用三秒就消失的 toast
    const reasons = [...new Set(failures.map((f) => f.reason.message))].join('；')
    await ElMessageBox.alert(
      `成功 ${okCount} 条，失败 ${failures.length} 条。失败原因：${reasons}`,
      '批量审核结果',
      { confirmButtonText: '知道了' }
    )
  }

  tableRef.value?.clearSelection()
  load()
}
```

三个细节：

- **部分成功要用 `ElMessageBox.alert` 而不是 `ElMessage`。** toast 三秒就消失，用户还没看清“失败了哪几条”就不见了。常驻弹窗需要用户主动关闭，不会漏掉信息。
- **失败原因要去重。** 十条失败大概率是同一个原因（比如名额已满），列十遍没有意义。`[...new Set(...)]` 就够了。
- **失败后建议刷新列表**，因为失败的常见原因就是“状态已经变了”（别人先审了）或“名额满了”，刷新后用户能看到真实状态。

### 为什么批量接口最好由后端提供

前端逐条发请求能跑通，但只是“能用”。更好的做法是让后端提供一个批量接口，比如 `PATCH /api/signups/batch-approve`，请求体是 `{ ids: [301, 302, 303] }`。

| 做法 | 优点 | 缺点 |
| --- | --- | --- |
| 前端逐条提交（`allSettled`） | 后端不用改，前端自己能实现 | N 条请求就是 N 个事务，部分失败的状态要前端自己拼 |
| 后端批量接口 | 一个事务处理完，返回每条的成败，减轻网络压力 | 要后端配合 |

后端批量接口的关键好处是**事务边界**。逐条提交时，十条请求就是十个独立事务，做到第七条失败了，前六条已经提交，整体处于一个“一半新一半旧”的状态。批量接口可以做到“要么全成功，要么全失败”，也可以明确约定“逐条判断、返回每条的成败”，但**无论哪种，判断逻辑都在服务端一处，不会出现前端以为成功、后端其实失败的情况。**

**这一条要提前和后端商量。** 课程项目里，如果后端排期紧，前端用 `allSettled` 逐条提交是可以接受的；但要在设计文档里写明“批量操作目前是前端逐条提交，事务边界在后端逐条保证，后续可以优化成批量接口”。**知道现在的做法有什么代价，比闷头做完了强。**

## 九、关键决策

### 决策一：驳回理由强制必填

**选了什么**：`rejectReason` 必填，长度 5 到 100 字，前端 `inputValidator` 拦一道，后端再校验一道。

**为什么**：学生收到“你的报名被驳回”但不知道原因，只能来找组织者问。这条规则把沟通成本从“事后一个个解释”前移到“审核的时候填一句”。字数下限 5 个字，是为了防止“不行”“没空”这种没有信息量的理由。

**代价**：审核多了一步，批量驳回没法做（每条理由都得不一样）。这是有意接受的代价 —— 驳回理由的价值高于批量驳回省下的那点时间。

### 决策二：`REJECTED` 做成终态，不能直接改成通过

**选了什么**：被驳回的报名不能一键改成通过。审核错了的正确做法是撤销驳回（变成 `CANCELLED`），让学生重新报名。

**为什么**：驳回时有理由记录。直接改成通过，那条理由就悬在半空、没有意义了，审核记录也会变得前后矛盾。**保持数据的历史一致性，比提供一步操作的便利更重要。** 而且撤销后重新报名会留下两条记录，谁在什么时候处理过一目了然。

**代价**：组织者发现驳错了要多点两下，学生还要再报一次。这个摩擦是刻意的，它让“驳回”这个动作更慎重。

### 决策三：批量操作用前端逐条提交 + `allSettled`，不自造批量语义

**选了什么**：批量审核逐条调 `approveSignup`，用 `Promise.allSettled` 收集结果，部分失败逐个提示。不假装这是一个“原子操作”。

**为什么**：后端暂时没有批量接口，前端用 `allSettled` 能用最小的改动满足需求；而且逐条提交的结果是真实的 —— 哪几条成功、哪几条失败，都能如实告诉用户。假装原子（用 `Promise.all` 然后只报一句成功或失败）反而会误导用户。

**代价**：N 条就是 N 个请求、N 个事务，中途失败会留下“部分成功”的状态。所以要有第九节末尾说的那套部分失败提示，且在设计文档里写明后续可以升级成后端批量接口。

### 决策四：审核后整页刷新，不做“只改当前行”

**选了什么**：审核成功后调 `load()` 重新拉当前页数据，而不是只把 `row.status` 改掉。

**为什么**：一次审核会影响两处显示 —— 当前行的状态、以及活动的名额。名额变化又会牵动其他行（比如名额满了之后，同一活动下面别的行的“通过”操作会失败）。只改当前行的话，页面上的名额数字和真实值就会不一致，用户会按着错误的信息继续操作。**整页刷新多花一个请求，换来的是页面上的数字都可信。**

**代价**：多一次请求，刷新时表格会短暂显示 loading。对后台列表页来说这个代价可以忽略。

### 决策五：两个入口共用一个组件，靠路由参数区分

**选了什么**：`/signup` 和 `/activity/:id/signups` 共用一个 `SignupList.vue`，活动入口把 `activityId` 拼进请求参数并显示活动标题。

**为什么**：两个入口的界面完全一样，差别只有“活动是否固定”和“标题显示什么”。写两份的话，任何一处改动都要改两遍，早晚不一致。

**代价**：组件要处理路由参数变化的重新请求（`watch`），也要处理“没有活动标题时显示什么”。多几行判断代码，换掉一整份重复的列表页，值得。

## 十、常见坑

::: details `ElMessageBox.prompt` 点取消会 reject，代码直接崩
**现象**：点驳回，弹窗出来后点“取消”，控制台报一个未捕获的错误，或者后面的提交逻辑居然跑了。

**原因**：`ElMessageBox` 的 `confirm` 和 `prompt` 在用户取消时都会 **reject**，不是返回 `false`。没包 `try / catch` 的话，reject 会一路抛出去。

注意 `prompt` 的返回结构是 `{ value, action }`，输入值在 `value` 里 —— 和 `confirm` 完全不同，这一点也容易写错。

**怎么处理**：所有 `ElMessageBox` 调用都包 `try / catch`，`catch` 里直接 `return`：

```js
let reason
try {
  const res = await ElMessageBox.prompt('请填写驳回理由', '驳回报名', { /* ... */ })
  reason = res.value
} catch {
  return // 用户取消，什么都不做
}
await rejectSignup(row.id, reason.trim())
```

**不要用 `.catch(() => {})` 挂在后面** —— 那样看起来没有报错，但也不容易看出这里处理了取消，容易被后来的人删掉。
:::

::: details 审核完，列表里已通过的行仍然能点“通过”
**现象**：通过一条报名后，那行的按钮没变，再点一次，后端返回 `3002`（状态不允许此操作）。

**原因**：两个可能。一是操作成功后没有重新加载列表，`row.status` 还是旧值；二是按钮的 `v-if` 直接判断了 `row.status === 'PENDING'`，但用的 `row` 是从列表里来的引用，没有更新。

**怎么处理**：确认操作成功后调了 `load()`。另外，即使前端按钮显隐正确，**也不要假设用户只能点到合法状态** —— 后端必须校验当前状态是不是 `PENDING`，返回 `3002`，前端把这个错误处理好。前端显隐防的是误操作，不是防恶意请求。

**顺便检查 `row-key`**：列表每行的 `row-key="id"` 配上之后，Vue 才能正确复用和更新行节点。
:::

::: details 同一个学生重复报名，列表里有两条一样的
**现象**：列表里同一个学生、同一个活动出现两条记录。

**原因**：这件事前端管不了 —— 学生端可能同时提交了两次，或者网断了重试了一次。前端要做的是**不假设数据唯一**。

**怎么处理**：

- **不要把“学生 id”当作列表的 `row-key`。** 报名记录的唯一键是报名 `id`，不是学生 id。用学生 id 做 key 的话，同一学生报了不同活动会被当成同一行，渲染出错。
- **后端应该在“活动 + 学生”上做唯一约束**，重复报名返回一个明确的错误码。前端把这个错误码的提示展示出来（比如“你已经报名过这个活动了”）。
- 如果确实出现了两条，组织者可以驳回或撤销其中一条。**前端不要自作主张去合并或隐藏。**

这条要在接口约定里和后端确认：**同一学生对同一活动重复报名，后端是拒绝还是允许更新？** 两边理解不一致，前端就不知道该提示什么。
:::

::: details 报名列表里“活动标题”这一列是空的
**现象**：报名列表加载出来了，学生姓名有，活动标题那列全是空白。

**原因**：接口只返回了 `activityId`，没有返回 `activityTitle`。列表里的每一行都得再查一次活动详情才能拿到标题 —— 一页 20 条就是 20 次请求。

**怎么处理**：**这是接口设计问题，要在接口层解决，不是前端逐行补请求。** 报名列表接口要把关联字段带出来（`activityTitle`、`studentName`、`studentNo`、`studentClass`），后端一个联表查询就搞定。

判断标准很简单：**列表页要显示的字段，接口就该直接给。** 如果发现需要“先查列表、再循环查关联”，说明接口该改，而不是前端想办法绕。

同理，`studentName` 也不要前端拿 `studentId` 去查。见[接口约定](/project/api)第七节“注意 `activityTitle` 和 `studentName` 这类冗余字段”。
:::

::: details 在页面上给名额数字加一，和活动详情对不上
**现象**：审核通过一条后，自己把 `row.approvedCount` 加了一，结果这个数字和活动详情页显示的不一致，和看板上的也不一致。

**原因**：名额是共享状态，前端手里的是快照。本地改一下，改的只是自己这一份。

**怎么处理**：删掉所有 `approvedCount += 1` 这样的代码，统一改成重新请求。名额进度要用 `GET /api/activities/:id/signup-stats` 拿，不要自己数列表长度。

**再提醒一次**：前端算的名额一定不准，原因在第七节。**唯一可靠的做法是让后端算、前端显示。**
:::

::: details 从活动 A 的报名列表跳到活动 B，数据没变
**现象**：两个活动都有报名，从活动 A 详情进报名列表，再返回去进活动 B 详情，报名列表里还是活动 A 的数据（或标题还是活动 A 的）。

**原因**：两次是同一个路由记录，只是参数不同，Vue Router 复用了组件实例，`onMounted` 不会再执行，`useTable` 的首次请求也不会重跑。

**怎么处理**：用 `watch` 监听路由参数，参数变化时重新请求：

```js
watch(activityId, () => {
  loadActivityTitle()
  search()
}, { immediate: true })
```

**这类“组件复用导致不刷新”的问题，在“同一个组件被多条路由共用”时一定会遇到。** 遇到“页面数据是上一个路由的”这种现象，第一反应就该是查路由参数的监听。
:::

## 十一、验收清单

| # | 验收项 | 怎么验证 |
| --- | --- | --- |
| 1 | 报名列表能按活动筛选 | 从活动详情点“查看报名”，列表只显示该活动，标题显示活动名 |
| 2 | 全局列表不带活动筛选 | 从侧边栏进 `/signup`，能看到所有活动的报名 |
| 3 | 能按状态筛选 | 选“待审核”，列表只剩待审核的记录 |
| 4 | 能按姓名或学号搜索 | 输入一个学号，能精确查到该学生的报名 |
| 5 | 分页正常 | 翻页、改每页条数，数据正确，`total` 和实际一致 |
| 6 | 四态齐全 | 限速看到 loading；清空筛选看到无数据文案；改错接口地址看到失败和“重新加载” |
| 7 | 能审核通过 | 点通过、二次确认，状态变已通过，审核人显示当前用户 |
| 8 | 驳回必须填理由 | 理由少于 5 字时确定按钮被拦，提示正确 |
| 9 | 驳回后展示理由 | 已驳回的行能看到驳回理由 |
| 10 | 撤销通过会释放名额 | 撤销后活动详情的“已通过”减一，名额恢复 |
| 11 | 名额满了通过被拦 | 造一个名额满的活动，点通过，看到 `2005` 的提示和下一步建议 |
| 12 | 已通过的行不能重复通过 | 已通过的行不显示“通过”按钮；即使手工调接口，后端也返回 `3002` |
| 13 | 已驳回的行不能改成通过 | 被驳回的行只有“已结束”提示，没有审核按钮 |
| 14 | 活动标题不为空 | 报名列表里每行都显示了活动标题，没有空白单元格 |
| 15 | 并发不超卖 | 用两个账号对同一个“只剩一个名额”的活动同时点通过，只有一个成功 |
| 16 | 批量审核部分失败提示清楚 | 勾选多条（其中一条状态已变），提交后能看到“成功 X 条，失败 Y 条”和原因 |

---

上一页：[活动管理模块](/project/impl-activity) · 下一页：[场次与场地模块](/project/impl-session)
