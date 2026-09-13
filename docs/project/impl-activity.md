# 活动管理模块参考实现

活动管理是整个项目的主干。报名审核、场次安排、数据看板都建立在“有一条活动”之上，所以这个模块要最先做完、做扎实。

这一页按 **页面与接口对照 → 接口层 → 字典 → 列表页 → 表单页 → 详情页 → 状态操作 → 关键决策 → 常见坑 → 验收** 的顺序讲。所有业务判断都以 [业务规则与状态流转](/project/rules) 为准，所有请求参数以 [接口约定](/project/api) 为准。

## 一、模块范围

活动管理是四个页面，但新增与编辑共用一个组件，所以实际是三个 `.vue` 文件。

| 页面 | 路由 | 主要职责 | 关键依赖 |
| --- | --- | --- | --- |
| 活动列表 | `/activity` | 查询、分页、行操作入口 | `useTable`、`dict` |
| 活动详情 | `/activity/:id` | 信息展示、报名统计、状态操作 | 详情接口的权限布尔值 |
| 新增活动 | `/activity/create` | 填表、存草稿、保存并发布 | 表单校验、字典 |
| 编辑活动 | `/activity/:id/edit` | 回填、按状态限制字段、提交 | 状态相关的字段限制 |

**新增和编辑用同一个 `ActivityForm.vue`。** 理由是字段完全相同，区别只有三处：要不要拉详情回填、`POST` 还是 `PUT`、按钮文案。为了这三处维护两个几乎一样的文件，改一个字段要改两遍，不划算。

## 二、页面、路由、接口对照

先把三条线对起来，写代码时不容易迷路。

| 页面 | 路由 name | 调用的接口 |
| --- | --- | --- |
| 活动列表 | `activity-list` | `GET /api/activities` |
| 活动详情 | `activity-detail` | `GET /api/activities/:id`、`GET /api/activities/:id/signup-stats` |
| 新增活动 | `activity-create` | `POST /api/activities` |
| 编辑活动 | `activity-edit` | `GET /api/activities/:id`、`PUT /api/activities/:id` |
| 列表 / 详情行操作 | — | `PATCH /api/activities/:id/status`、`PATCH /api/activities/:id/offshelf`、`DELETE /api/activities/:id` |

路由表可以直接用：

```js [src/router/modules/activity.js]
export default {
  path: 'activity',
  name: 'activity',
  redirect: { name: 'activity-list' },
  children: [
    {
      path: '',
      name: 'activity-list',
      component: () => import('@/views/activity/ActivityList.vue'),
      meta: { title: '活动管理', roles: ['ORGANIZER', 'AUDITOR'] }
    },
    {
      // 注意：create 必须写在 :id 前面
      path: 'create',
      name: 'activity-create',
      component: () => import('@/views/activity/ActivityForm.vue'),
      meta: { title: '新增活动', roles: ['ORGANIZER'] }
    },
    {
      path: ':id',
      name: 'activity-detail',
      component: () => import('@/views/activity/ActivityDetail.vue'),
      meta: { title: '活动详情', roles: ['ORGANIZER', 'AUDITOR'] }
    },
    {
      path: ':id/edit',
      name: 'activity-edit',
      component: () => import('@/views/activity/ActivityForm.vue'),
      meta: { title: '编辑活动', roles: ['ORGANIZER'] }
    }
  ]
}
```

::: warning `create` 写在 `:id` 后面会怎样
Vue Router 匹配路由是从上往下找**第一个匹配的**。`create` 如果不排在 `:id` 前面，访问 `/activity/create` 会先命中 `:id`，于是 `route.params.id` 变成字符串 `"create"`，详情页拿着 `"create"` 去请求 `GET /api/activities/create`，后端报 404。

**现象是“点新增活动进了详情页，还提示活动不存在”。** 这类问题的特点是路由能跳转、组件也渲染了，只是数据不对，比较难一眼看出是顺序问题。

顺序规则记一条就够：**静态路径永远写在动态参数前面。**
:::

## 三、接口层 `api/activity.js`

接口层只做三件事：拼参数、发请求、把后端字段转成前端字段。

```js [src/api/activity.js]
import request from './request'

/** 后端字段 → 前端字段 */
function toModel(raw) {
  if (!raw) return null
  return {
    id: raw.id,
    title: raw.title,
    type: raw.type,
    typeName: raw.typeName,
    organizerId: raw.organizerId,
    organizerName: raw.organizerName,
    quota: raw.quota,
    approvedCount: raw.approvedCount,
    pendingCount: raw.pendingCount,
    signupDeadline: raw.signupDeadline,
    status: raw.status,
    statusName: raw.statusName,
    offShelf: raw.offShelf,
    description: raw.description,
    createdAt: raw.createdAt,
    updatedAt: raw.updatedAt
  }
}

/** 前端表单 → 后端请求体 */
function toPayload(form) {
  return {
    title: form.title,
    type: form.type,
    quota: form.quota,
    signupDeadline: form.signupDeadline,
    description: form.description
  }
}

/** 列表：返回 { list, total }，total 是总条数 */
export async function getActivityList(params) {
  const data = await request.get('/activities', { params })
  return {
    list: (data.list ?? []).map(toModel),
    total: data.total ?? 0
  }
}

/** 详情 */
export async function getActivityDetail(id) {
  return toModel(await request.get(`/activities/${id}`))
}

/** 新增，可带 publish 一次创建并发布 */
export function createActivity(form, publish = false) {
  return request.post('/activities', { ...toPayload(form), publish })
}

/** 编辑 */
export function updateActivity(id, form) {
  return request.put(`/activities/${id}`, toPayload(form))
}

/** 发布：只有 DRAFT → SIGNING 是允许的 */
export function publishActivity(id) {
  return request.patch(`/activities/${id}/status`, { status: 'SIGNING' })
}

/** 下架 / 恢复上架 */
export function setActivityOffShelf(id, offShelf) {
  return request.patch(`/activities/${id}/offshelf`, { offShelf })
}

/** 删除：只有 DRAFT 能删 */
export function deleteActivity(id) {
  return request.delete(`/activities/${id}`)
}

/** 某活动的报名统计 */
export function getSignupStats(id) {
  return request.get(`/activities/${id}/signup-stats`)
}
```

### 3.1 `toModel` / `toPayload` 什么时候需要

这一层不是必须的。**判断标准有两条：**

| 情况 | 要不要转换层 |
| --- | --- |
| 后端返回的字段名和前端一模一样 | 不需要，直接返回 |
| 后端用下划线风格（`signup_deadline`）、前端用驼峰 | 需要 |
| 字段超过 10 个、以后还可能改名 | 需要 |
| 只想挑一部分字段传给后端（表单里有只读字段） | 需要 `toPayload` |

本项目的接口约定里字段名本来就是驼峰，所以 `toModel` 看起来只是“把字段抄一遍”。**但我仍然建议保留它**，理由有三个：

**一、把“后端返回什么”和“页面用什么”隔开。** 详情接口会额外返回 `canEdit`、`canDelete` 这些字段，列表接口不返回。有了 `toModel`，多出来的字段不会漏进页面，`ActivityList.vue` 里不会出现 `row.rejectReason` 这种看着像能用、其实永远是 undefined 的字段。

**二、`toPayload` 挡住了只读字段。** 表单对象里如果混了 `approvedCount`、`createdAt`，直接 `...form` 提交上去，后端严格模式会报错。`toPayload` 只挑该传的五个字段，多传的问题从根上没有了。

**三、改字段名只改一处。** 后端哪天把 `signupDeadline` 改名，只要改 `toModel` 和 `toPayload` 两个函数，页面一行都不用动。

**代价是多了一层映射代码。** 字段少、名字又一致的时候确实显得啰嗦。**如果你们的接口字段和前端完全一致，去掉 `toModel` 只保留 `toPayload` 也完全可以。**

### 3.2 分页参数怎么传

```js
// useTable 会把 query、page、pageSize 合成一个对象传进来
const { list, total } = await getActivityList({ keyword, status, offShelf, page, pageSize })
```

axios 的 `params` 会把它们拼到 URL 上。**注意布尔值 `offShelf`。** 从 URL query 或 `el-switch` 拿到的是字符串 `'true'` / `'false'`，而 `Boolean('false')` 是 `true`。接口约定里明确要求传真正的 `true` / `false`，所以传之前要转一次：

```js [src/utils/format.js]
export function toBool(value) {
  return value === true || value === 1 || value === '1' || value === 'true'
}
```

## 四、字典 `utils/dict.js`

状态和类型是“一个值对应一段文案和一个颜色”的映射。这类东西必须集中维护。

```js [src/utils/dict.js]
/** 活动状态：值与中文文案 */
export const ACTIVITY_STATUS_OPTIONS = [
  { label: '草稿', value: 'DRAFT' },
  { label: '报名中', value: 'SIGNING' },
  { label: '报名截止', value: 'SIGNUP_CLOSED' },
  { label: '已结束', value: 'FINISHED' }
]

/** 活动类型 */
export const ACTIVITY_TYPE_OPTIONS = [
  { label: '比赛竞赛', value: 'COMPETITION' },
  { label: '文艺演出', value: 'PERFORMANCE' },
  { label: '讲座沙龙', value: 'LECTURE' },
  { label: '志愿服务', value: 'VOLUNTEER' },
  { label: '体育活动', value: 'SPORTS' }
]

const STATUS_LABEL_MAP = Object.fromEntries(
  ACTIVITY_STATUS_OPTIONS.map((o) => [o.value, o.label])
)
const TYPE_LABEL_MAP = Object.fromEntries(
  ACTIVITY_TYPE_OPTIONS.map((o) => [o.value, o.label])
)

/** 状态值 → 中文文案 */
export function activityStatusLabel(value) {
  return STATUS_LABEL_MAP[value] ?? '未知'
}

/** 类型值 → 中文文案 */
export function activityTypeLabel(value) {
  return TYPE_LABEL_MAP[value] ?? '未知'
}

/** 状态值 → el-tag 的颜色类型 */
const STATUS_TAG_TYPE = {
  DRAFT: 'info',
  SIGNING: 'success',
  SIGNUP_CLOSED: 'warning',
  FINISHED: ''
}

export function activityStatusTagType(value) {
  return STATUS_TAG_TYPE[value] ?? 'info'
}

/** 报名状态（报名审核模块会用） */
export const SIGNUP_STATUS_OPTIONS = [
  { label: '待审核', value: 'PENDING' },
  { label: '已通过', value: 'APPROVED' },
  { label: '已驳回', value: 'REJECTED' },
  { label: '已取消', value: 'CANCELLED' }
]
```

### 为什么字典要集中在一处

“报名中”这三个字会出现在：列表的状态列、详情的状态标签、看板的图例、表单编辑时的提示、取消操作的确认文案。**如果每个地方各写一遍，产品要把“报名中”改成“进行中”，你得搜遍全项目。**

集中之后，改一处就全变了。再加两个实际好处：

- **下拉框和展示用的是同一份数据。** `el-select` 绑 `ACTIVITY_STATUS_OPTIONS` 的 `value`，列表用 `activityStatusLabel` 显示，永远不会出现“下拉里叫报名中、列表里叫进行中”。
- **`label` 函数一定要有兜底。** 后端哪天加了一个新状态 `PENDING_REVIEW`，没兜底的话界面显示 `undefined`，加兜底至少显示“未知”，问题一眼可见。

**一个容易犯的错：** 直接拿显示文案去请求接口。`el-select` 的 `:value` 必须绑枚举值 `'SIGNING'`，不是文案 `'报名中'`。所以选项要做成 `{ label, value }` 结构。

## 五、列表页

列表页的标准骨架在 [11.4 列表页标准做法](/unit11/04-list-page) 里讲过，这里只讲活动列表特有的部分：查询条件、列设计、按钮显隐。

### 5.1 查询条件

按接口约定，列表支持三个筛选条件加两个分页参数：

| 条件 | 控件 | 传参 |
| --- | --- | --- |
| 关键字 | `el-input` | `keyword`，按标题模糊搜 |
| 状态 | `el-select` | `status`，取字典的枚举值 |
| 是否只看已下架 | `el-switch` 或 `el-checkbox` | `offShelf`，布尔 |

```js
const { query, page, pageSize, total, list, loading, error, isEmpty,
  load, search, reset, handleSizeChange, handlePageChange, reloadAfterRemove
} = useTable(
  async (params) => {
    // 直接返回 { list, total }，转换已经在 api 层做完了
    return getActivityList(params)
  },
  {
    query: { keyword: '', status: '', offShelf: false }
  }
)
```

**`offShelf` 默认给 `false` 而不是空字符串。** 因为接口约定的类型是布尔。给 `''` 的话，传出去是空串，后端可能当成“未定义”也可能报类型错误。**查询条件的初始值类型要和接口约定对上**，这是联调时很常见的一类小问题。

### 5.2 表格列

```vue [src/views/activity/ActivityList.vue（表格部分）]
<el-table v-loading="loading" :data="list" border stripe row-key="id" style="width: 100%">
  <el-table-column prop="title" label="活动标题" min-width="200" show-overflow-tooltip>
    <template #default="{ row }">
      <el-link type="primary" @click="goDetail(row)">{{ row.title }}</el-link>
    </template>
  </el-table-column>

  <el-table-column label="类型" width="110">
    <template #default="{ row }">{{ activityTypeLabel(row.type) }}</template>
  </el-table-column>

  <el-table-column label="状态" width="130">
    <template #default="{ row }">
      <el-tag :type="activityStatusTagType(row.status)" size="small">
        {{ activityStatusLabel(row.status) }}
      </el-tag>
      <el-tag v-if="row.offShelf" type="info" size="small" class="ml-4">已下架</el-tag>
    </template>
  </el-table-column>

  <el-table-column label="报名情况" width="140">
    <template #default="{ row }">
      <span :class="{ 'is-full': row.approvedCount >= row.quota }">
        {{ row.approvedCount }} / {{ row.quota }}
      </span>
      <span v-if="row.pendingCount > 0" class="pending">（待审 {{ row.pendingCount }}）</span>
    </template>
  </el-table-column>

  <el-table-column label="报名截止" width="170">
    <template #default="{ row }">{{ row.signupDeadline }}</template>
  </el-table-column>

  <el-table-column label="组织者" width="110">
    <template #default="{ row }">{{ row.organizerName }}</template>
  </el-table-column>

  <el-table-column label="操作" width="240" fixed="right">
    <template #default="{ row }">
      <el-button link type="primary" @click="goDetail(row)">详情</el-button>
      <el-button v-if="canEditRow(row)" link type="primary" @click="goEdit(row)">编辑</el-button>
      <el-button v-if="canOffShelfRow(row)" link type="warning" @click="handleToggleOffShelf(row)">
        {{ row.offShelf ? '恢复' : '下架' }}
      </el-button>
      <el-button v-if="canDeleteRow(row)" link type="danger" @click="handleDelete(row)">删除</el-button>
    </template>
  </el-table-column>

  <template #empty>
    <div v-if="error" class="state-block">
      <p class="state-title">数据加载失败</p>
      <p class="state-desc">{{ error.message }}</p>
      <el-button type="primary" @click="load">重新加载</el-button>
    </div>
    <div v-else-if="isEmpty" class="state-block">
      <p class="state-title">还没有活动</p>
      <p class="state-desc">发布第一个活动，学生就能看到并报名了。</p>
      <el-button type="primary" @click="goCreate">立即创建</el-button>
    </div>
  </template>
</el-table>
```

**列的设计上有两个取舍。**

**一是把“报名情况”做成一列。** `approvedCount / quota` 让人一眼看出还剩多少名额，超了或满了标红。待审核数量用括号补在后面，不单独占一列。**列数超过 7 列，横向滚动就很难看**，次要信息要么合并要么挪到详情页。

**二是组织者单独一列。** 审核员能看所有人的活动，组织者名必须显示。组织者自己看的时候这一列是冗余的，但没什么坏处。

### 5.3 操作按钮的显隐

按 [业务规则](/project/rules) 里的权限表，编辑、删除、下架三个按钮各有自己的条件：

| 按钮 | 谁能看到 | 什么状态能看到 |
| --- | --- | --- |
| 详情 | 组织者、审核员 | 总是 |
| 编辑 | 组织者（仅自己的活动） | 不是 `FINISHED` |
| 下架 / 恢复 | 组织者（自己的）、审核员（全部） | 不是 `DRAFT` 也不是 `FINISHED` |
| 删除 | 组织者（仅自己的活动） | 只有 `DRAFT` |

**这些规则从哪来？** 接口约定里说，详情接口会返回 `canEdit`、`canDelete`、`canOffShelf` 三个布尔值，推荐前端直接用后端返回的。但列表接口的单条对象里没有这三个字段。

于是有两种做法：

| 做法 | 怎么做 | 好处 | 代价 |
| --- | --- | --- | --- |
| 列表也返回三个布尔值 | 让后端在列表里也带上 | 规则只有后端一份，永不不一致 | 每个列表接口都要加字段 |
| 前端用 `domain` 模块算 | 规则集中写在一个文件里 | 不用改后端 | 规则写了两遍 |

本项目的做法是**优先用后端返回的，没有就用前端规则兜底**：

```js [src/domain/activity-rules.js]
/** 活动相关的业务规则。页面只调用，不自己写条件。 */

export function canEdit(activity, user) {
  if (!activity || !user) return false
  if (activity.status === 'FINISHED') return false
  if (user.role === 'AUDITOR') return false
  return activity.organizerId === user.id
}

export function canDelete(activity, user) {
  if (!activity || !user) return false
  if (activity.status !== 'DRAFT') return false
  if (user.role === 'AUDITOR') return false
  return activity.organizerId === user.id
}

export function canOffShelf(activity, user) {
  if (!activity || !user) return false
  if (activity.status === 'DRAFT' || activity.status === 'FINISHED') return false
  if (user.role === 'AUDITOR') return true
  return activity.organizerId === user.id
}
```

页面里包一层薄的判断函数：

```js
import { useUserStore } from '@/stores/user'
import { canEdit, canDelete, canOffShelf } from '@/domain/activity-rules'

const userStore = useUserStore()

// 后端给了就用后端的，没给就前端算
function canEditRow(row) {
  return row.canEdit ?? canEdit(row, userStore.userInfo)
}
function canDeleteRow(row) {
  return row.canDelete ?? canDelete(row, userStore.userInfo)
}
function canOffShelfRow(row) {
  return row.canOffShelf ?? canOffShelf(row, userStore.userInfo)
}
```

**为什么不干脆只写前端规则？** 因为这会让 [业务规则](/project/rules) 里的规则出现在两个地方。规则改一次，前端要改一处，后端要改一处，迟早不一致。**“后端是权威，前端能拿就用、拿不到再用本地规则兜底”是两者之间比较稳的配合方式。**

**还有一点必须记住：这三个布尔值只决定按钮显不显示，不决定后端放不放行。** 见 [登录与鉴权模块](/project/impl-auth) 里的讨论。

### 5.4 分页与四态

分页用 `useTable` 里现成的 `handlePageChange` 和 `handleSizeChange`，不要自己再写一套。四态中“失败”和“无数据”分开写在 `#empty` 插槽里。

**三个翻页细节在 `useTable` 里已经处理了**，这里只重复一遍现象：

- 改了筛选条件不回第 1 页 → 显示空列表
- 删掉当前页最后一条不往前翻 → 明明前面还有数据，却显示“暂无数据”
- 每页条数从 10 改成 20 不回第 1 页 → 原来的第 5 页现在只有 3 页，第 5 页是空的

## 六、表单页

新增和编辑共用 `ActivityForm.vue`，靠 `route.params.id` 判断模式。

```js [src/views/activity/ActivityForm.vue]
<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter, onBeforeRouteLeave } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getActivityDetail, createActivity, updateActivity } from '@/api/activity'
import { ACTIVITY_TYPE_OPTIONS } from '@/utils/dict'

defineOptions({ name: 'ActivityForm' })

const route = useRoute()
const router = useRouter()

// ① 模式判断
const activityId = computed(() => route.params.id)
const isEdit = computed(() => Boolean(activityId.value))

const formRef = ref(null)
const form = reactive({
  title: '',
  type: '',
  quota: 50,
  signupDeadline: '',
  description: ''
})

// ② 编辑时的原始数据，用来做“只能调大 / 只能往后推”的校验
const original = ref(null) // 完整的原始活动对象
const originalApprovedCount = computed(() => original.value?.approvedCount ?? 0)

const submitting = ref(false)
const dirty = ref(false)

// ③ 校验规则
const rules = {
  title: [
    { required: true, message: '请输入活动标题', trigger: 'blur' },
    { min: 2, max: 50, message: '标题长度在 2 到 50 个字符之间', trigger: 'blur' }
  ],
  type: [{ required: true, message: '请选择活动类型', trigger: 'change' }],
  quota: [
    { required: true, message: '请输入名额', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (!Number.isInteger(value) || value <= 0) {
          return callback(new Error('名额必须是大于 0 的整数'))
        }
        // 编辑时名额不能小于已通过人数（见业务规则）
        if (isEdit.value && value < originalApprovedCount.value) {
          return callback(
            new Error(`已有 ${originalApprovedCount.value} 人通过审核，名额不能小于这个数`)
          )
        }
        // 报名中状态名额只能调大
        if (
          isEdit.value &&
          original.value?.status === 'SIGNING' &&
          value < original.value.quota
        ) {
          return callback(new Error(`报名中的活动名额只能调大，当前是 ${original.value.quota}`))
        }
        callback()
      },
      trigger: 'change'
    }
  ],
  signupDeadline: [
    { required: true, message: '请选择报名截止时间', trigger: 'change' },
    {
      validator: (rule, value, callback) => {
        if (!value) return callback()
        if (new Date(value.replace(/-/g, '/')).getTime() <= Date.now()) {
          return callback(new Error('报名截止时间必须晚于当前时间'))
        }
        // 报名中状态截止时间只能往后推
        if (
          isEdit.value &&
          original.value?.status === 'SIGNING' &&
          value < original.value.signupDeadline
        ) {
          return callback(new Error(`报名中的活动截止时间只能往后推，当前是 ${original.value.signupDeadline}`))
        }
        callback()
      },
      trigger: 'change'
    }
  ]
}

// ④ 编辑模式拉详情回填
onMounted(async () => {
  if (!isEdit.value) return
  const data = await getActivityDetail(activityId.value)
  original.value = data
  Object.assign(form, {
    title: data.title,
    type: data.type,
    quota: data.quota,
    signupDeadline: data.signupDeadline,
    description: data.description
  })
})

// ⑤ 提交
async function handleSubmit(publish = false) {
  if (submitting.value) return
  try {
    await formRef.value.validate()
  } catch {
    return
  }

  submitting.value = true
  try {
    if (isEdit.value) {
      await updateActivity(activityId.value, form)
      ElMessage.success('保存成功')
    } else {
      await createActivity(form, publish)
      ElMessage.success(publish ? '创建并发布成功' : '草稿已保存')
    }
    dirty.value = false
    router.push({ name: 'activity-list' })
  } catch {
    // 错误提示由响应拦截器统一处理，这里只负责不跳转
  } finally {
    submitting.value = false
  }
}

// ⑥ 离开提醒
onBeforeRouteLeave(async () => {
  if (!dirty.value || submitting.value) return true
  try {
    await ElMessageBox.confirm('表单还没保存，确定要离开吗？', '提示', {
      type: 'warning',
      confirmButtonText: '离开',
      cancelButtonText: '继续编辑'
    })
    return true
  } catch {
    return false
  }
})

function handleBeforeUnload(e) {
  if (!dirty.value) return
  e.preventDefault()
  e.returnValue = ''
}
onMounted(() => window.addEventListener('beforeunload', handleBeforeUnload))
onUnmounted(() => window.removeEventListener('beforeunload', handleBeforeUnload))
</script>
```

模板部分只贴关键片段：

```vue [ActivityForm.vue（模板片段）]
<el-card shadow="never" v-loading="submitting">
  <template #header>
    <span>{{ isEdit ? '编辑活动' : '新增活动' }}</span>
  </template>

  <el-form
    ref="formRef"
    :model="form"
    :rules="rules"
    label-width="110px"
    @change="dirty = true"
  >
    <el-form-item label="活动标题" prop="title">
      <el-input v-model="form.title" maxlength="50" show-word-limit
        placeholder="例如：2026 春季校园歌手大赛" />
    </el-form-item>

    <el-form-item label="活动类型" prop="type">
      <el-select v-model="form.type" placeholder="请选择" style="width: 240px">
        <el-option v-for="opt in ACTIVITY_TYPE_OPTIONS" :key="opt.value"
          :label="opt.label" :value="opt.value" />
      </el-select>
    </el-form-item>

    <el-form-item label="名额" prop="quota">
      <el-input-number v-model="form.quota" :min="1" :max="2000" :precision="0" />
      <span class="field-hint">
        通过审核的人数达到此上限后，报名入口自动关闭
      </span>
    </el-form-item>

    <el-form-item label="报名截止" prop="signupDeadline">
      <el-date-picker
        v-model="form.signupDeadline"
        type="datetime"
        value-format="YYYY-MM-DD HH:mm:ss"
        style="width: 240px"
      />
    </el-form-item>

    <el-form-item label="活动说明" prop="description">
      <el-input v-model="form.description" type="textarea" :rows="4"
        maxlength="500" show-word-limit />
    </el-form-item>

    <el-form-item>
      <el-button type="primary" :loading="submitting" @click="handleSubmit(false)">
        {{ isEdit ? '保存' : '存为草稿' }}
      </el-button>
      <el-button v-if="!isEdit" :loading="submitting" @click="handleSubmit(true)">
        保存并发布
      </el-button>
      <el-button @click="router.back()">取消</el-button>
    </el-form-item>
  </el-form>
</el-card>
```

### 6.1 编辑时两条额外的限制

[业务规则](/project/rules) 里写得很明确，编辑“报名中”的活动时：

| 字段 | 限制 | 为什么 |
| --- | --- | --- |
| 名额 | 只能调大 | 已经有人通过审核，改到比这个数小，数据就不一致了 |
| 报名截止时间 | 只能往后推 | 提前截止会让已经看到倒计时的学生觉得被坑了 |

这两条都放在 `validator` 里。**为什么不干脆用 `disabled` 锁住？** 因为“只能调大”不是“不能改”—— 用户还是要把 100 改到 150。锁住输入框就做不到这件事了。

**更好的做法是“不禁用，但把下限锁死”**：给 `el-input-number` 的 `:min` 动态赋值：

```vue
<el-input-number
  v-model="form.quota"
  :min="isEdit ? Math.max(originalApprovedCount, original?.status === 'SIGNING' ? original.quota : 1) : 1"
  :max="2000"
  :precision="0"
/>
```

这样用户根本改不到非法的值，`validator` 仍然保留作为兜底。**“控制可达性 + 校验兜底”两层一起上，比只做一层稳。**

### 6.2 `submitting` 与防重复提交

三件事一件都不能少：

1. **按钮绑 `:loading="submitting"`。** `el-button` 在 loading 时会自动禁用点击。
2. **函数开头 `if (submitting.value) return`。** 防的是回车键提交绕开按钮的 loading。
3. **`submitting` 在 `finally` 里恢复。** 漏了的话，提交失败后按钮永远卡在 loading，用户只能刷新。

**第三层在后端。** 前端这三招拦的是“用户手快”，网络层的重复请求前端拦不住。后端该用幂等键或唯一约束。**前端的所有校验都要在后端再做一遍**，这句话在表单上同样成立。

### 6.3 离开提醒

用户填了十分钟，不小心点了侧边菜单，全没了。这个体验很差。

- **站内跳转**用 `onBeforeRouteLeave`，返回 `false` 取消导航。
- **关闭标签页 / 刷新**用 `beforeunload`。
- **提交成功时不能弹。** 所以 `router.push` 之前先 `dirty.value = false`，顺序不能反。
- **提交中直接放行。** `submitting` 为 true 时 `return true`，否则会出现“点提交 → 跳转 → 弹出离开确认”的怪事。

`beforeunload` 有个限制要知道：**浏览器不允许自定义提示文字**，`e.returnValue = ''` 只能触发它，显示什么由浏览器决定。这是浏览器的安全限制，改不了。

## 七、详情页

详情页要显示四类内容：基本信息、报名统计、当前状态下的可用操作、跳去报名列表的入口。

```js [src/views/activity/ActivityDetail.vue（脚本片段）]
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getActivityDetail, getSignupStats } from '@/api/activity'
import { activityStatusLabel, activityStatusTagType, activityTypeLabel } from '@/utils/dict'

const route = useRoute()
const router = useRouter()

const activity = ref(null)
const stats = ref(null)
const loading = ref(true)

// 权限布尔值优先用后端返回的
const canEdit = computed(() => activity.value?.canEdit ?? false)
const canDelete = computed(() => activity.value?.canDelete ?? false)
const canOffShelf = computed(() => activity.value?.canOffShelf ?? false)
// 只有 DRAFT 能发布
const canPublish = computed(() => activity.value?.status === 'DRAFT')

onMounted(async () => {
  const id = route.params.id
  try {
    // 两个请求互不依赖，并行发
    const [detail, signupStats] = await Promise.all([getActivityDetail(id), getSignupStats(id)])
    activity.value = detail
    stats.value = signupStats
  } finally {
    loading.value = false
  }
})

function goSignupList() {
  router.push({ name: 'signup-list', query: { activityId: route.params.id } })
}
```

模板里要有几个关键点：

```vue
<template>
  <el-card v-loading="loading" shadow="never">
    <template #header>
      <div class="detail-header">
        <span class="title">{{ activity?.title }}</span>
        <el-tag :type="activityStatusTagType(activity?.status)">
          {{ activityStatusLabel(activity?.status) }}
        </el-tag>
        <el-tag v-if="activity?.offShelf" type="info">已下架</el-tag>

        <div class="actions">
          <el-button v-if="canPublish" type="primary" @click="handlePublish">发布</el-button>
          <el-button v-if="canEdit" @click="goEdit">编辑</el-button>
          <el-button v-if="canOffShelf" @click="handleToggleOffShelf">
            {{ activity.offShelf ? '恢复上架' : '下架' }}
          </el-button>
          <el-button v-if="canDelete" type="danger" @click="handleDelete">删除</el-button>
        </div>
      </div>
    </template>

    <el-descriptions :column="2" border>
      <el-descriptions-item label="活动类型">{{ activityTypeLabel(activity?.type) }}</el-descriptions-item>
      <el-descriptions-item label="组织者">{{ activity?.organizerName }}</el-descriptions-item>
      <el-descriptions-item label="名额">{{ activity?.quota }}</el-descriptions-item>
      <el-descriptions-item label="报名截止">{{ activity?.signupDeadline }}</el-descriptions-item>
      <el-descriptions-item label="活动说明" :span="2">{{ activity?.description || '—' }}</el-descriptions-item>
    </el-descriptions>

    <h3 class="section-title">报名统计</h3>
    <div class="stat-row">
      <el-statistic title="已通过" :value="stats?.approvedCount ?? 0" />
      <el-statistic title="待审核" :value="stats?.pendingCount ?? 0" />
      <el-statistic title="已驳回" :value="stats?.rejectedCount ?? 0" />
      <el-statistic title="剩余名额" :value="stats?.remaining ?? 0" />
      <el-button type="primary" link @click="goSignupList">查看报名列表</el-button>
    </div>
  </el-card>
</template>
```

**统计数字一律来自 `GET /api/activities/:id/signup-stats`，不要用详情里带的数字自己减。** 接口约定里说得很清楚，`remaining` 由后端算。前端做减法看起来一样，但当规则变化（比如“待审核也预占名额”）时就会不一致。

**详情页的按钮用后端返回的 `canEdit` / `canDelete` / `canOffShelf`，不自己算。** 详情接口本来就返回这三个字段，直接用最省事，也避免了列表页和详情页显示不一致。

## 八、状态操作的交互

三个状态操作各有各的确认文案和刷新策略。

### 8.1 发布

```js
async function handlePublish() {
  try {
    await ElMessageBox.confirm(
      `确定要发布“${activity.value.title}”吗？发布后学生可以开始报名。`,
      '发布确认',
      { type: 'warning', confirmButtonText: '发布', cancelButtonText: '再想想' }
    )
  } catch {
    return // 用户取消，confirm 会 reject
  }
  await publishActivity(activity.value.id)
  ElMessage.success('发布成功')
  await loadDetail() // 重新拉，状态和按钮一起变
}
```

**发布前提醒一件事：** 接口约定里说，发布时会校验报名截止时间是否还在未来。如果活动创建了三个月、截止时间早就过了，发布接口会返回错误码 `2004`。前端可以不做额外判断，让后端返回；但更好的做法是在列表页就把这种活动标出来提醒组织者。**这不是必须的，是加分项。**

### 8.2 下架 / 恢复上架

```js
async function handleToggleOffShelf() {
  const next = !activity.value.offShelf
  const actionText = next ? '下架' : '恢复上架'
  try {
    await ElMessageBox.confirm(
      next
        ? `确定要下架“${activity.value.title}”吗？下架后不再接受新报名，已通过审核的学生不受影响。`
        : `确定要恢复上架“${activity.value.title}”吗？恢复后学生可以继续报名。`,
      `${actionText}确认`,
      { type: 'warning', confirmButtonText: '确定', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  await setActivityOffShelf(activity.value.id, next)
  ElMessage.success(`${actionText}成功`)
  await loadDetail()
}
```

**下架的确认文案里必须写清“已通过的学生不受影响”。** 这是组织者最常问的问题，写在确认框里能省掉一部分咨询。见 [业务规则](/project/rules)。

**下架和状态是两回事。** 下架只改 `offShelf`，`status` 不动。一个下架的报名中活动，过了截止时间后 `status` 照样会变成 `SIGNUP_CLOSED`，`offShelf` 仍是 true。**代码里不要把下架做成一个状态值。**

### 8.3 删除

```js
async function handleDelete() {
  try {
    await ElMessageBox.confirm(
      `确定要删除“${activity.value.title}”吗？删除后不可恢复。`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', confirmButtonClass: 'el-button--danger' }
    )
  } catch {
    return
  }
  await deleteActivity(activity.value.id)
  ElMessage.success('删除成功')
  router.push({ name: 'activity-list' })
}
```

**删除成功后直接回列表页**，不要留在详情页刷新 —— 详情数据已经不存在了，刷新只会得到一个 404。

列表页里删除要处理“删完当前页空了”的情况：

```js
async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(
      `确定要删除“${row.title}”吗？删除后不可恢复。`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', confirmButtonClass: 'el-button--danger' }
    )
  } catch {
    return
  }
  await deleteActivity(row.id)
  ElMessage.success('删除成功')
  await reloadAfterRemove() // 当前页只剩一条时会自动往前翻
}
```

### 8.4 三个操作的刷新策略

| 操作 | 成功后做什么 | 为什么 |
| --- | --- | --- |
| 发布 | 刷新当前数据 | 状态从 `DRAFT` 变 `SIGNING`，按钮显隐跟着变 |
| 下架 / 恢复 | 刷新当前数据 | `offShelf` 变了，列表里的“已下架”标签要更新 |
| 删除 | 列表页原地刷新，详情页回列表 | 数据没了，留在详情页没有意义 |

**统一用“重新请求”而不是“改本地数据”。** 本地改看起来快，但状态变化会带着一串副作用（比如下架后某些按钮该消失），自己维护很容易漏。**一次请求换一份准确的数据，值。**

## 九、关键决策

这一节是答辩时的重点。每条都按“选了什么 / 为什么 / 代价是什么”写。

### 决策一 · 新增与编辑共用一个组件

**选了什么：** `ActivityForm.vue` 一个文件同时承担新增和编辑，靠 `route.params.id` 区分。

**为什么：** 字段完全相同，表单校验规则也几乎相同。分成两个文件的话，加一个字段要改两处，改一条校验规则也要改两处，而且很容易改漏。共用一个组件后差异被压缩到三处：回填、接口方法、按钮文案。

**代价是什么：** 组件内部多了 `isEdit` 判断，`onMounted` 里要分支，读代码时需要在两个模式之间切换。另外如果以后编辑页和新增页的字段真的开始分化（比如编辑时禁止改类型、新增时可以），分支会越来越多，那时候就该拆开了。**判断标准：分支超过五处就拆。**

### 决策二 · 字典集中在一个 `dict.js`

**选了什么：** 所有状态、类型、标签颜色的映射都放 `src/utils/dict.js`，页面只调用函数。

**为什么：** “报名中”这四个字会出现在五六个地方。散着写的话，改文案要全项目搜索替换，漏一处就出现两种叫法。集中之后改一个地方全变，而且下拉框的选项和列表的展示用的是同一份数据，不会出现“下拉里叫报名中、列表里叫进行中”。

**代价是什么：** 多了一个文件，页面里要 `import`。另外字典函数必须写兜底（`?? '未知'`），不然后端加了新枚举值界面会显示 `undefined`。**兜底是必须的，不是可选的。**

### 决策三 · 操作按钮的显隐放前端，但规则来源以后端返回为准

**选了什么：** 优先用后端返回的 `canEdit` / `canDelete` / `canOffShelf`；列表接口没返回时，用 `src/domain/activity-rules.js` 里的函数兜底。

**为什么：** 这些规则的条件不少（状态、下架、角色、是不是自己的活动），前端自己算一定会和后端算得不完全一样。让后端算、前端用，规则就只有一份。但列表接口目前没返回，全等后端改也不现实，所以留一个前端规则模块兜底。

**代价是什么：** 规则在前端还是写了一份，存在两边不一致的风险。**处理办法是每加一条规则，先想清楚“后端有没有对应校验”，有的话前端这份只是显示逻辑，改的时候两边一起改。** 更根本的解决办法是让后端在所有列表接口里也返回这三个字段，前端规则模块就可以删掉了。

### 决策四 · 状态的中文文案前端维护，不用后端返回的 `statusName`

**选了什么：** 接口会返回 `statusName`，但页面显示统一走 `activityStatusLabel(row.status)`。

**为什么：** 接口约定里提示过：同一个状态在不同页面可能有不同文案（列表用“报名中”、看板用“进行中”）。如果文案全由后端返回，前端就没法按页面调整。文案是展示问题，交给展示层决定更合适。

**代价是什么：** 前端和后端各维护一份文案，可能不一致。**处理办法是约定清楚：`statusName` 只作为排查问题时的参考，界面显示一律用前端的字典函数。** 如果团队更希望文案统一由后端管，那就反过来 —— 用 `row.statusName`，前端字典只保留颜色映射，删掉 label 函数。**两种都行，关键是全项目统一，不要一半一半。**

### 决策五 · 列表页抽 `useTable`，详情和表单不抽

**选了什么：** 列表页的逻辑（查询、分页、四态）抽成 `useTable`；详情页和表单页的逻辑各自写在组件里。

**为什么：** 列表页有五个页面、逻辑几乎一样，抽出来收益大。详情页每个模块的字段和操作都不同，抽出来只会变成一堆参数；表单页同理。**“三个以上地方重复”才值得抽。**

**代价是什么：** `useTable` 有一定的理解成本，新同学第一次看列表页会不知道 `search` 和 `load` 的区别。**所以要在 `useTable` 里写好注释**（见 [11.4](/unit11/04-list-page) 的代码）。

## 十、常见坑

::: details 坑 1：换了筛选条件，列表显示“暂无数据”
**现象**：在第 3 页把状态筛成“草稿”，表格变空，但去掉筛选条件又有数据。

**原因**：查询时没有把 `page` 重置回 1，还是拿第 3 页去请求，而筛选后的结果只有 1 页。

**怎么处理**：查询走 `search()` 而不是 `load()`，`useTable` 里 `search` 已经把 `page` 置为 1。**每页条数变化也必须回第 1 页**，所以 `@size-change` 绑的是 `search`。

```js
function search() {
  page.value = 1
  return load()
}
```

**自查办法**：翻到第 3 页改条件点查询，打开 Network 面板看请求参数里的 `page` 是不是 1。
:::

::: details 坑 2：删了当前页最后一条，列表空了但前面还有数据
**现象**：翻到最后一页，把这一页的数据全删掉，列表显示“暂无数据”，但点上一页又有内容。

**原因**：删除后直接 `load()`，请求的还是原来那一页，那一页已经没有数据了。

**怎么处理**：用 `reloadAfterRemove()` —— 当前页只剩一条且不是第 1 页时，先把 `page` 减 1 再请求。

```js
function reloadAfterRemove() {
  if (list.value.length === 1 && page.value > 1) {
    page.value -= 1
  }
  return load()
}
```

**这个细节用户不会夸你，但没有它用户会骂你。**
:::

::: details 坑 3：新增成功后回列表，看不到刚新增的数据
**现象**：新增保存成功，跳回列表，列表里没有那条新活动。

**原因**：两种可能。一是列表用了缓存或 `keep-alive`，跳回来时没重新请求；二是排序按 `createdAt` 倒序，新数据应该在最前面，但当前在第 3 页，看不到。

**怎么处理**：

- 列表页的 `onMounted`（或 `onActivated`）里重新 `load()`，不要依赖上一次的数据。
- 如果第 1 页也看不到，检查是不是 `keep-alive` 缓存了组件、`onMounted` 没再执行 —— 这种情况要在 `onActivated` 里刷新。
- 顺带确认新增接口真的写进了库（看返回的 `id` 有没有值）。

**最稳的做法是“新增成功后回列表并重新请求”**，不要用“把新数据 push 到本地列表”这种乐观更新，除非你很确定排序和分页都对得上。
:::

::: details 坑 4：从活动 42 的编辑页到 43 的编辑页，保存改的是 42
**现象**：编辑完 42 返回列表，再点编辑 43，`onMounted` 没重新执行，表单里还是 42 的数据。

**原因**：新增和编辑用的是同一个组件，两个路由指向同一个组件时，Vue Router 会复用组件实例，`onMounted` 只执行一次。

**怎么处理**：在布局页给动态组件加 `:key`，路径变化就重建组件：

```vue [src/views/layout/AppLayout.vue]
<router-view v-slot="{ Component }">
  <component :is="Component" :key="route.path" />
</router-view>
```

**另一种思路是 `watch` 路由参数**，但那样要自己处理“清空旧数据”和“重新请求”，容易漏。`:key` 是最省事的做法。

**注意 `:key` 的取值要用 `route.path` 而不是 `route.name`** —— 编辑页切换 id 时 name 不变，path 变了。
:::

::: details 坑 5：用 `ElMessageBox.confirm` 时，点取消会抛错
**现象**：点删除弹出确认框，点“取消”，控制台出现一条未捕获的错误。

**原因**：`ElMessageBox.confirm` 返回的是 Promise，**用户点取消时会 reject**（reject 的值是字符串 `'cancel'`）。不处理就会变成未捕获错误，而且后面的代码如果没被中断，还会继续执行删除。

**怎么处理**：用 `try / catch` 包起来，`catch` 里直接 `return`。

```js
try {
  await ElMessageBox.confirm('确定要删除吗？', '删除确认', { type: 'warning' })
} catch {
  return // ← 用户取消，什么都不做
}
// 只有走到这里才是确认了
await deleteActivity(row.id)
```

**关键在 `return`。** 只写 `catch {}` 不 `return` 的话，代码会往下走，取消反而变成了确认。**这类 bug 的现象是“点了取消数据还是被删了”，很吓人。**
:::

::: details 坑 6：`el-input-number` 允许输入小数
**现象**：名额输入框里能输 `2.5`，提交后数据库里就是 2.5。

**原因**：`el-input-number` 默认允许小数。

**怎么处理**：三层一起上。

```vue
<el-input-number v-model="form.quota" :min="1" :max="2000" :precision="0" />
```

- UI 层 `:precision="0"` 让用户输不进小数；
- `validator` 里加 `Number.isInteger(value)` 判断；
- 后端用整型接收或自己校验。

**只做第一层是不够的**，用户可以通过其他方式传小数。**前端 UI 限制 → 前端校验 → 后端校验，一层一层往后兜。**
:::

::: details 坑 7：日期比较字符串，跨时区或格式不一致时出错
**现象**：`signupDeadline` 校验有时对有时错，改了时区或者后端返回格式变一下就不准了。

**原因**：直接比较日期字符串，或者用 `new Date('2026-04-01 18:00:00')`。**带空格的日期字符串在部分浏览器里解析结果不确定**，Safari 历史上会把它当成非法日期返回 `Invalid Date`。

**怎么处理**：统一转成时间戳再比，并且把空格换成斜杠，或者用 `Date.parse` 前先归一化：

```js
function toTimestamp(str) {
  if (!str) return NaN
  return new Date(String(str).replace(/-/g, '/')).getTime()
}

// 比较
if (toTimestamp(form.signupDeadline) <= Date.now()) {
  // 报错
}
```

**字符串比较只在“格式完全一致”时才可靠。** `'2026-04-01 18:00:00' < '2026-04-02 09:00:00'` 恰好是对的，因为格式统一、位数相同；但一旦后端返回 `2026-4-1 18:00:00` 就不对了。**不要依赖这个巧合，转时间戳。**
:::

::: details 坑 8：表单校验通过了，提交却报参数错误
**现象**：前端校验全过，提交返回 400，说缺少必填字段或字段类型不对。

**原因**：通常是三类 —— 字段名不匹配（`signupDeadLine` 和 `signupDeadline`）、多传了只读字段（`approvedCount`、`createdAt`）、类型不对（数字传成字符串 `"50"`、布尔传成 `"false"`）。

**怎么处理**：

- 提交前只挑该传的字段（`toPayload` 已经做了）；
- 用 Network 面板看实际的 `Payload`，这是排查参数问题最快的办法；
- 布尔值用 `toBool()` 转，数字用 `Number()` 转。

**抄接口文档里的字段名时逐字比对一遍**，花两分钟能省掉半小时调试。
:::

## 十一、验收清单

| 验收项 | 怎么验证 |
| --- | --- |
| 列表能查到数据 | 进 `/activity`，表格有数据，分页器显示的总数和接口返回的 `total` 一致 |
| 关键字搜索生效 | 输入一个存在的标题片段，点查询，结果都包含这个片段 |
| 状态筛选生效 | 选“草稿”，列表里全是草稿状态 |
| 只看已下架生效 | 打开开关，列表里全部带“已下架”标签 |
| 查询后回到第 1 页 | 翻到第 2 页再点查询，看请求参数里 `page` 是 1 |
| 每页条数变化回第 1 页 | 从 10 改成 20，看 `page` 是 1 |
| 删除最后一条会往前翻 | 删光最后一页的数据，看是否自动回退到上一页 |
| 无数据有引导按钮 | 搜一个不存在的关键字，看提示和“立即创建”按钮 |
| 失败态有重试 | 把接口地址改错，看是否显示错误和“重新加载” |
| 新增路由不被 `:id` 抢走 | 点“新增活动”，地址是 `/activity/create`，进的是表单页 |
| 新增存草稿 | 只填必填项，点“存为草稿”，列表里出现一条草稿 |
| 创建并发布 | 点“保存并发布”，列表里这条的状态是“报名中” |
| 新增的校验生效 | 标题只填 1 个字、名额填 0，看两条错误提示 |
| 编辑能回填 | 从列表点编辑，字段都有值 |
| 编辑名额不能小于已通过人数 | 造一条已有 5 人通过的活动，名额改成 3，看是否报错 |
| 报名中名额只能调大 | 把报名中活动的名额从 100 改成 80，看是否报错 |
| 报名中截止时间只能往后推 | 把截止时间改成更早的，看是否报错 |
| 提交防重复 | 快速双击提交按钮，看是否只创建了一条 |
| 提交失败按钮恢复 | 把接口地址改错，提交失败后按钮能再点 |
| 离开未保存表单有提醒 | 改一个字段，点侧边菜单，看有没有确认框 |
| 提交成功不弹离开提醒 | 提交成功跳转时不应弹提示 |
| 切换编辑 id 数据不残留 | 编辑 42 后返回，再编辑 43，表单里是 43 的数据 |
| 发布操作生效 | 草稿活动点发布，状态变成“报名中”，按钮变成“下架” |
| 下架后已报名不受影响 | 下架一个报名中的活动，看已通过人数没变，只是不能再报 |
| 恢复上架生效 | 点恢复，`offShelf` 变回 false |
| 删除只有草稿能删 | 报名中的活动看不到删除按钮，用 curl 直接调接口返回 2002 |
| 删除有二次确认 | 点删除，有确认框，点取消不执行 |
| 取消确认不误删 | 点删除后点“取消”，看数据是否还在（这条专门测 `catch` 里的 `return`） |
| 详情统计来自统计接口 | 详情的已通过 / 待审核数字和报名列表里筛出来的条数对得上 |
| 详情能跳报名列表 | 点“查看报名列表”，地址带 `activityId` |

## 十二、可以继续做的事

- **列表筛选同步到 URL。** 刷新页面后筛选条件和页码丢失。把 `query`、`page` 同步到 `route.query`，用 `router.replace` 更新，用户就能分享一个筛选后的链接。**注意 `route.query` 里的值都是字符串，`page` 读出来要 `Number()` 转一下。**
- **批量下架。** 给表格加 `type="selection"` 和 `row-key`，选中多条后一次下架。**需要后端提供批量接口**，前端循环调单个接口会在中途失败时留下不一致。
- **把 `domain/activity-rules.js` 加上单元测试。** 规则函数是纯函数，用 Vitest 写几个用例断言 `canDelete`、`canOffShelf` 的返回值，改规则时先跑测试。这也是答辩时能讲的一个点。
- **列表加入“即将截止”提醒。** 报名截止在 48 小时内的活动，在标题后面加一个红色小标签。数据可以从看板的待办接口拿，也可以在列表接口里返回一个 `endingSoon` 布尔值。
- **详情页加操作日志。** 谁在什么时候发布 / 下架了这条活动。需要后端新增接口，能显著提升“数据可追溯”这一项的可信度。

---

上一页：[登录与鉴权模块](/project/impl-auth) · 下一页：[报名审核模块](/project/impl-signup)
