# 场次与场地模块 · 参考实现

主线三步的最后一步是安排场次：通过审核的学生，要知道什么时间、在哪个场地参加活动。

这一步的技术难点集中在一件事上：**判断两个时段会不会撞车。** 判定规则本身只有四行代码，但边界条件不少 —— 边界相接算不算冲突、编辑时要不要排除自己、取消的场次还占不占时段。这几条漏掉任何一条，都会让组织者遇到“明明取消了还说冲突”“改个字都改不了”这类让人困惑的问题。

这一篇按“场地 → 场次 → 冲突检测”的顺序讲。场地是基础数据，场次依赖场地，冲突检测是场次保存时的校验。

## 一、模块范围与页面地图

### 页面 → 路由 → 接口

| 页面 | 路由 | 主要接口 | 可访问角色 |
| --- | --- | --- | --- |
| 场地列表 | `/venue` | `GET /api/venues` | 审核员 |
| 场次列表 | `/session` | `GET /api/sessions` | 组织者、审核员 |

| 动作 | 接口 | 说明 |
| --- | --- | --- |
| 新增场地 | `POST /api/venues` | 名称唯一，重名返回 `4002` |
| 编辑场地 | `PUT /api/venues/:id` | 同上 |
| 启用 / 停用场地 | `PATCH /api/venues/:id/enabled` | **接口约定里没有，需要和后端补一条** |
| 新增场次 | `POST /api/sessions` | 时段冲突返回 `4003` |
| 编辑场次 | `PUT /api/sessions/:id` | 同上，且要排除自己 |
| 取消场次 | `PATCH /api/sessions/:id/cancel` | **接口约定里没有，需要和后端补一条** |
| 冲突预检 | `POST /api/sessions/check-conflict` | 返回冲突详情 |

**注意最后两行的“接口约定里没有”。** [接口约定](/project/api)的第八节列了场地的增改、场次的增改和冲突预检，但没列“停用场地”和“取消场次”。这两件事在[需求规格说明](/project/requirements)里是明确要求的（D3 和 D7）。**发现文档缺了接口，正确做法是停下来和后端补一条约定，而不是随便找个接口凑合。** 推荐用 `PATCH` 单字段接口，因为它只改一个字段，语义上比 `PUT` 一个完整对象准确。

### 数据流

```
场地：审核员维护基础数据
      /venue ──> api/venue.js ──> /api/venues
                                    │
场次：组织者挑空闲时段              │ venueId 引用
      /session ──> api/session.js ──> /api/sessions
                       │
                       ├─ 保存前：POST /api/sessions/check-conflict（预检，给反馈）
                       └─ 保存时：POST /api/sessions（后端再查一次，定正确性）
```

两个接口的关系是这一篇的主线：**预检是为了体验，保存时的校验是为了正确性，两者都要有，但职责不能混。**

## 二、场地管理

### 接口封装

```js [src/api/venue.js]
import request from './request'

/** 场地列表。支持 keyword（按名称模糊查）和分页 */
export function getVenueList(params) {
  return request.get('/venues', { params })
}

/** 场地详情。编辑时回填表单用 */
export function getVenueDetail(id) {
  return request.get(`/venues/${id}`)
}

export function createVenue(data) {
  return request.post('/venues', data)
}

export function updateVenue(id, data) {
  return request.put(`/venues/${id}`, data)
}

/** 启用 / 停用。用 PATCH 只改一个字段，语义比 PUT 整个对象准确 */
export function setVenueEnabled(id, enabled) {
  return request.patch(`/venues/${id}/enabled`, { enabled })
}
```

### 场地列表

场地数量通常不多（一间学校几十个），可以一次性列出来，但为了和其他列表页一致，仍然用 `useTable` 走标准模板。

```vue [src/views/venue/VenueList.vue]
<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getVenueList, setVenueEnabled } from '@/api/venue'
import { useTable } from '@/composables/useTable'

defineOptions({ name: 'VenueList' })

const router = useRouter()

const {
  query, page, pageSize, total, list, loading, error, isEmpty,
  load, search, reset, handleSizeChange, handlePageChange
} = useTable(
  async (params) => {
    const data = await getVenueList(params)
    return { list: data.list, total: data.total }
  },
  { query: { keyword: '' } }
)

async function handleToggleEnabled(row) {
  const next = !row.enabled
  const action = next ? '启用' : '停用'
  try {
    await ElMessageBox.confirm(
      next
        ? `确定启用“${row.name}”吗？启用后它就能被安排场次了。`
        : `确定停用“${row.name}”吗？停用后新增场次时选不到它，但已有的场次不受影响。`,
      `${action}场地`,
      { type: 'warning', confirmButtonText: `确定${action}` }
    )
  } catch {
    return
  }
  await setVenueEnabled(row.id, next)
  ElMessage.success(`已${action}`)
  load()
}
</script>

<template>
  <el-card shadow="never">
    <div class="table-toolbar">
      <el-input
        v-model="query.keyword"
        placeholder="场地名称"
        clearable
        style="width: 200px"
        @keyup.enter="search"
      />
      <el-button type="primary" :loading="loading" @click="search">查询</el-button>
      <el-button @click="reset">重置</el-button>
      <el-button type="primary" @click="router.push({ name: 'venue-create' })">
        新增场地
      </el-button>
    </div>

    <el-table v-loading="loading" :data="list" border stripe row-key="id">
      <el-table-column prop="name" label="场地名称" min-width="180" show-overflow-tooltip />
      <el-table-column prop="capacity" label="容量" width="90" align="right" />
      <el-table-column prop="location" label="位置" min-width="140" show-overflow-tooltip />
      <el-table-column prop="remark" label="备注" min-width="180" show-overflow-tooltip />

      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.enabled ? 'success' : 'info'" size="small">
            {{ row.enabled ? '已启用' : '已停用' }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button
            link
            type="primary"
            @click="router.push({ name: 'venue-edit', params: { id: row.id } })"
          >编辑</el-button>
          <el-button
            link
            :type="row.enabled ? 'warning' : 'success'"
            @click="handleToggleEnabled(row)"
          >{{ row.enabled ? '停用' : '启用' }}</el-button>
        </template>
      </el-table-column>

      <template #empty>
        <div v-if="error" class="state-block">
          <p class="state-title">场地数据加载失败</p>
          <p class="state-desc">{{ error.message }}</p>
          <el-button type="primary" @click="load">重新加载</el-button>
        </div>
        <div v-else-if="isEmpty" class="state-block">
          <p class="state-title">还没有登记场地</p>
          <p class="state-desc">先把可用的场地录进来，安排场次时才选得到。</p>
          <el-button type="primary" @click="router.push({ name: 'venue-create' })">新增场地</el-button>
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
</template>
```

停用场地的确认文案里有一句不能省：**“停用后新增场次时选不到它，但已有的场次不受影响”**。组织者最怕的就是“我一停用，之前排的场次是不是没了”。把答案写在确认框里，他就敢点。

### 场地表单

```vue [src/views/venue/VenueForm.vue]
<script setup>
import { computed, reactive, ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { createVenue, updateVenue, getVenueDetail, getVenueList } from '@/api/venue'

defineOptions({ name: 'VenueForm' })

const route = useRoute()
const router = useRouter()
const formRef = ref()
const submitting = ref(false)

const venueId = computed(() => route.params.id)
const isEdit = computed(() => Boolean(venueId.value))
const nameError = ref('')

const form = reactive({
  id: null,
  name: '',
  capacity: 100,
  location: '',
  remark: ''
})

const rules = {
  name: [
    { required: true, message: '请输入场地名称', trigger: 'blur' },
    { min: 2, max: 50, message: '场地名称长度 2 到 50 个字', trigger: 'blur' }
  ],
  capacity: [
    { required: true, message: '请输入容量', trigger: 'blur' },
    { type: 'number', min: 1, max: 100000, message: '容量必须是正整数', trigger: 'blur' }
  ]
}

/**
 * 失焦时查一次重名。只在“前端能快速判断”的情况下给即时反馈，
 * 真正的唯一性由后端数据库的唯一索引保证 —— 见下面的说明。
 */
async function checkNameDuplicate() {
  const name = form.name.trim()
  nameError.value = ''
  if (!name || name.length < 2) return

  const data = await getVenueList({ keyword: name, page: 1, pageSize: 20 })
  const duplicated = data.list.some((v) => v.name === name && v.id !== form.id)
  if (duplicated) {
    nameError.value = '这个名称已经有人用了，换一个吧'
  }
}

onMounted(async () => {
  if (!isEdit.value) return
  // 用详情接口回填，不要把列表接口的第一条拿来用
  const data = await getVenueDetail(venueId.value)
  Object.assign(form, {
    id: data.id,
    name: data.name,
    capacity: data.capacity,
    location: data.location ?? '',
    remark: data.remark ?? ''
  })
})

async function handleSubmit() {
  await formRef.value.validate()
  if (nameError.value) return

  submitting.value = true
  try {
    const payload = { ...form }
    delete payload.id
    if (isEdit.value) {
      await updateVenue(venueId.value, payload)
    } else {
      await createVenue(payload)
    }
    ElMessage.success(isEdit.value ? '保存成功' : '新增成功')
    router.push({ name: 'venue-list' })
  } catch (e) {
    // 4002 = 场地名称已存在。表单字段级错误显示在字段下，不弹全局提示
    if (e.code === 4002) {
      nameError.value = e.message
    }
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <el-card shadow="never">
    <el-form ref="formRef" :model="form" :rules="rules" label-width="90px" style="max-width: 560px">
      <el-form-item label="场地名称" prop="name" :error="nameError">
        <el-input
          v-model="form.name"
          placeholder="例如：大学生活动中心 报告厅"
          @blur="checkNameDuplicate"
          @input="nameError = ''"
        />
      </el-form-item>

      <el-form-item label="容量" prop="capacity">
        <el-input-number v-model="form.capacity" :min="1" :max="100000" />
      </el-form-item>

      <el-form-item label="位置">
        <el-input v-model="form.location" placeholder="例如：活动中心 3 楼" />
      </el-form-item>

      <el-form-item label="备注">
        <el-input v-model="form.remark" type="textarea" :rows="3" maxlength="200" show-word-limit />
      </el-form-item>

      <el-form-item>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">保存</el-button>
        <el-button @click="router.back()">取消</el-button>
      </el-form-item>
    </el-form>
  </el-card>
</template>
```

### 场地名称唯一性：前端查重和后端唯一索引是两件事

这是这一节最值得讲清楚的一点，也是答辩时经常被问到的地方。

场地名称是全局唯一的。前端在输入框失焦时查一遍有没有重名，看起来像是在“校验唯一性”。但它**不是**并发安全的：

1. 审核员 A 和审核员 B 同时新增场地，两个人都输入了“大学生活动中心 报告厅”。
2. A 失焦时查了一遍，还没有这个名称，没问题。
3. B 几乎同时失焦查了一遍，也还没有 —— 因为 A 还没提交。
4. 两个人先后点保存，两条同名场地就都进了数据库。

**前端查重的窗口期有多长，取决于用户手速。** 只要两个人离得足够近，就一定能撞上。

后端也不能只靠“先查有没有，没有再插入”。因为两个请求可能同时查到“没有”，然后同时插入。**唯一性必须由数据库的唯一索引（或者等价的加锁机制）来保证**：数据库在写入时做原子检查，第二个请求会直接失败。

所以三件事的分工是：

| 位置 | 做什么 | 作用是 |
| --- | --- | --- |
| 前端失焦查重 | 输入完立刻查一次 | **体验优化**，让用户在提交前就知道重名 |
| 后端提交校验 | 收到请求检查一次 | 给出一致的 `4002` 错误码 |
| 数据库唯一索引 | 写入时原子检查 | **真正的约束**，并发下也拦得住 |

**前端的查重可以不做，但后端的唯一索引不能不做。** 前端的价值只是“早点告诉用户”，没有它最坏也只是提交后才被拦下；没有数据库的唯一索引，数据就真错了。

前端要处理的错误码是 `4002`，而且它是**表单字段级错误**，要显示在名称输入框下面，不要弹全局提示：

```js
if (e.code === 4002) {
  nameError.value = e.message   // 绑到 el-form-item 的 :error 上
}
```

## 三、场次管理

### 接口封装

```js [src/api/session.js]
import request from './request'

/**
 * 场次列表。
 * @param {Object} params activityId / startDate / endDate / page / pageSize
 * 日期范围是闭区间，包含首尾两天（见接口约定）
 */
export function getSessionList(params) {
  return request.get('/sessions', { params })
}

export function createSession(data) {
  return request.post('/sessions', data)
}

export function updateSession(id, data) {
  return request.put(`/sessions/${id}`, data)
}

/**
 * 冲突预检。
 * 注意这个接口“有冲突”时也返回 code: 0，
 * 冲突信息在 data.conflicts 里 —— 检测动作本身成功了。
 */
export function checkConflict(payload) {
  return request.post('/sessions/check-conflict', payload)
}

/** 取消场次。接口约定里未列出，需和后端确认 */
export function cancelSession(id) {
  return request.patch(`/sessions/${id}/cancel`)
}
```

### 场次列表

场次列表比报名列表复杂一点：它有两个筛选维度（活动、日期范围），还有一件“冲突检测”的外围工作。

```vue [src/views/session/SessionList.vue]
<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getSessionList, cancelSession } from '@/api/session'
import { getActivityList } from '@/api/activity'
import { useTable } from '@/composables/useTable'
import { formatDateTime } from '@/utils/format'

defineOptions({ name: 'SessionList' })

const router = useRouter()

// 日期范围选择器绑一个 [start, end] 数组，拆成两个参数发给后端
const dateRange = ref([])

const {
  query, page, pageSize, total, list, loading, error, isEmpty,
  load, search, reset, handleSizeChange, handlePageChange
} = useTable(
  async (params) => {
    const [startDate, endDate] = dateRange.value ?? []
    const data = await getSessionList({
      ...params,
      startDate: startDate || undefined,
      endDate: endDate || undefined
    })
    return { list: data.list, total: data.total }
  },
  { query: { activityId: '', keyword: '' } }
)

// 活动下拉选项。真实的项目里可以做成远程搜索，场次数量少时一次拉够用
const activityOptions = ref([])
async function loadActivityOptions() {
  const data = await getActivityList({ page: 1, pageSize: 100 })
  activityOptions.value = data.list
}

async function handleCancel(row) {
  try {
    await ElMessageBox.confirm(
      `确定取消“${row.activityTitle}”在 ${formatDateTime(row.startTime)} 的场次吗？取消后这个时段会被释放，可以安排别的场次。`,
      '取消场次',
      { type: 'warning', confirmButtonText: '确认取消' }
    )
  } catch {
    return
  }
  await cancelSession(row.id)
  ElMessage.success('已取消，该时段已释放')
  load()
}
</script>

<template>
  <el-card shadow="never">
    <el-form inline @submit.prevent="search">
      <el-form-item label="活动">
        <el-select
          v-model="query.activityId"
          placeholder="全部活动"
          clearable
          filterable
          style="width: 240px"
          @visible-change="(v) => v && loadActivityOptions()"
        >
          <el-option
            v-for="a in activityOptions"
            :key="a.id"
            :label="a.title"
            :value="a.id"
          />
        </el-select>
      </el-form-item>

      <el-form-item label="日期范围">
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          value-format="YYYY-MM-DD"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
        />
      </el-form-item>

      <el-form-item>
        <el-button type="primary" :loading="loading" @click="search">查询</el-button>
        <el-button @click="reset">重置</el-button>
      </el-form-item>
    </el-form>

    <div class="table-toolbar">
      <el-button type="primary" @click="router.push({ name: 'session-create' })">新增场次</el-button>
      <span class="total-hint">共 {{ total }} 条</span>
    </div>

    <el-table v-loading="loading" :data="list" border stripe row-key="id">
      <el-table-column prop="activityTitle" label="活动" min-width="180" show-overflow-tooltip />
      <el-table-column prop="venueName" label="场地" min-width="160" show-overflow-tooltip />

      <el-table-column label="开始时间" width="170">
        <template #default="{ row }">{{ formatDateTime(row.startTime) }}</template>
      </el-table-column>
      <el-table-column label="结束时间" width="170">
        <template #default="{ row }">{{ formatDateTime(row.endTime) }}</template>
      </el-table-column>

      <el-table-column prop="remark" label="备注" min-width="120" show-overflow-tooltip />

      <el-table-column label="状态" width="110">
        <template #default="{ row }">
          <el-tag :type="row.status === 'CANCELLED' ? 'info' : 'success'" size="small">
            {{ row.statusName }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{ row }">
          <el-button
            v-if="row.status !== 'CANCELLED'"
            link
            type="primary"
            @click="router.push({ name: 'session-edit', params: { id: row.id } })"
          >编辑</el-button>
          <el-button
            v-if="row.status !== 'CANCELLED'"
            link
            type="warning"
            @click="handleCancel(row)"
          >取消</el-button>
          <span v-else class="muted">已取消</span>
        </template>
      </el-table-column>

      <template #empty>
        <div v-if="error" class="state-block">
          <p class="state-title">场次数据加载失败</p>
          <p class="state-desc">{{ error.message }}</p>
          <el-button type="primary" @click="load">重新加载</el-button>
        </div>
        <div v-else-if="isEmpty" class="state-block">
          <p class="state-title">这段时间还没有安排场次</p>
          <p class="state-desc">换个日期范围看看，或者直接新增一个场次。</p>
          <el-button type="primary" @click="router.push({ name: 'session-create' })">新增场次</el-button>
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
</template>
```

**日期范围是闭区间，包含首尾两天。** 用户选“4 月 1 日到 4 月 30 日”，意思是 4 月 1 日 00:00:00 到 4 月 30 日 23:59:59。这条必须在[接口约定](/project/api)里写死，否则“含不含最后一天”两边理解不一致，会少显示一天的数据 —— 这种问题很难被发现。

## 四、冲突检测

这一节是模块的核心。前面所有代码都是铺垫。

### 判定函数 `isTimeConflict`

```js [src/utils/session.js]
/**
 * 把后端的时间字符串转成 Date。
 * "2026-04-10 14:00:00" 里的空格在部分浏览器（老版本 Safari）解析不出来，
 * 换成 ISO 的 "2026-04-10T14:00:00" 更稳。
 */
export function parseTime(text) {
  if (!text) return null
  return new Date(String(text).replace(' ', 'T'))
}

/**
 * 判断两个时段是否冲突。
 * 边界相接不算冲突：14:00-17:00 和 17:00-20:00 是合法的。
 */
export function isTimeConflict(aStart, aEnd, bStart, bEnd) {
  const a1 = parseTime(aStart).getTime()
  const a2 = parseTime(aEnd).getTime()
  const b1 = parseTime(bStart).getTime()
  const b2 = parseTime(bEnd).getTime()

  // 不冲突的两种情况：a 在 b 开始前就结束，或 b 在 a 开始前就结束
  if (a2 <= b1) return false
  if (b2 <= a1) return false
  return true
}
```

判定逻辑可以写成一句：

```js
const conflict = a1 < b2 && b1 < a2
```

但**上面那种“先列不冲突的情况再返回冲突”的写法更好读，也更容易检查边界。** 具体的判断过程：

| 已有场次 | 新场次 | 冲突吗 | 走到的分支 |
| --- | --- | --- | --- |
| 14:00 - 17:00 | 15:00 - 18:00 | 冲突 | 两个 `return false` 都不满足 |
| 14:00 - 17:00 | 17:00 - 20:00 | 不冲突 | `a2 = 17:00 <= b1 = 17:00` |
| 14:00 - 17:00 | 13:00 - 14:00 | 不冲突 | `b2 = 14:00 <= a1 = 14:00` |
| 14:00 - 17:00 | 14:00 - 17:00 | 冲突 | 都相等，两个分支都不满足 |
| 14:00 - 17:00 | 13:00 - 15:00 | 冲突 | 第二个分支不满足，第一个也不满足 |

### 为什么必须是 `<=` 而不是 `<`

**这一个等号就是“边界相接不算冲突”这条规则的实现。**

如果把 `a2 <= b1` 改成 `a2 < b1`，那么当已有场次是 14:00 - 17:00、新场次是 17:00 - 20:00 时：`a2 = 17:00 < b1 = 17:00` 是 `false`，第二个分支 `b2 = 20:00 < a1 = 14:00` 也是 `false`，函数走到最后 `return true` —— **两个首尾相接、完全合法的场次被判成了冲突。**

为什么会有人写 `<`？因为直觉上“重叠”就是“有交集的区间”，而严格的不等式 `a1 < b2 && b1 < a2` 在数学上表达的是开区间的相交。但场次是**半开区间** `[start, end)`：17:00 这一瞬间属于后一场，不属于前一场。用半开区间的视角看，`a2 <= b1` 才是“不重叠”的正确条件。

```
前一场： [14:00 ─────────── 17:00)
后一场：                      [17:00 ─────────── 20:00)
                              ↑ 这一个瞬间只属于后一场
```

**这条规则也是验收清单里要单独强调的一项（需求里第 17 条）。** 区分“做完”和“做对”的地方，就在这个等号上。

### 编辑时要排除自己

一个场次本来就是 14:00 - 17:00，组织者想把开始时间改成 15:00。查重的时候会查到“这个场地在这个时段有一个场次”—— 那个场次就是它自己。如果不排除自己，它会报告冲突，这个场次就永远改不了。

```ts
async function checkConflict(session: Session, excludeId?: number) {
  const existing = await getSessionsByVenue(session.venueId, session.startTime, session.endTime)
  return existing.filter((s) => {
    if (s.id === excludeId) return false          // 编辑时排除自己
    if (s.status === 'CANCELLED') return false    // 已取消的场次不占时段
    return isTimeConflict(
      session.startTime, session.endTime,
      s.startTime, s.endTime
    )
  })
}
```

**两个排除条件都不能少：**

- `excludeId`：编辑场景。新增时传 `null`，后端据此知道不用排除任何场次。
- 已取消的场次不占时段：一个场次被取消了，那个时段就该空出来。

“已取消的场次不占时段”这一条很容易漏。漏了的后果是：组织者取消了一个场次想重新安排，结果系统说冲突。他会很困惑 —— **我明明取消了，它凭什么占着时间？** 这类“行为不符合用户直觉”的问题，用户不会觉得是系统有 bug，而是觉得自己没操作对。

### 前端预检与后端校验，两者都要有

前端预检调的是 `POST /api/sessions/check-conflict`。这个接口有个特点：**检测出冲突时返回的是 `code: 0`，不是错误码。** 冲突信息在 `data.conflicts` 里。

```js
// 预检：检测动作成功，结果是“有冲突”
const { conflict, conflicts } = await checkConflict(payload)
```

因为“检测”这个动作本身成功了，检测出冲突是一个正常结果，不是错误。这和“真的提交一个冲突的场次”不一样 —— 那是提交动作失败了，返回错误码 `4003`。

**区分标准：失败的是“动作”还是“结果”。** 结果“有 / 无”的是查询，用成功响应；结果“行 / 不行”的是提交，用错误码。

两者的分工：

| | 前端预检 | 后端提交校验 |
| --- | --- | --- |
| 什么时候跑 | 用户选完场地和时间，提交之前 | 收到 `POST /api/sessions` 时 |
| 为了什么 | 让用户立刻知道结果，不用等提交 | 保证正确性 |
| 拦得住并发吗 | **拦不住** | 能 |
| 能不能省 | 能省，体验差一点 | **不能省** |

**前端预检拦不住的场景**：两个人同时给同一个场地排重叠的时段；别人刚创建的场次，你的页面还没刷新。前端的预检是拿“页面已经加载的数据”比，别人刚提交的它根本不知道。

**所以后端必须再检测一次。** 前端预检是为了体验，后端检测是为了正确性 —— 这和[报名模块](/project/impl-signup)里的名额问题是同一类问题：**并发场景下，前端的任何检查都不作数。**

::: details 如果时间紧张，能不能只做后端检测
能。把检测完全交给后端，前端只负责把后端返回的 `4003` 展示出来。

**好处**：逻辑只有一份，不会出现“前端说不冲突、后端说冲突”这种前后不一致。
**代价**：用户要点了保存才知道冲突，得多改几次。

**推荐的做法是两边都做。** 前端预检覆盖常规情况（即时反馈），后端校验覆盖并发情况（兜底）。课程项目里如果时间不够，只做后端检测完全可以接受 —— 这不是扣分项，但要在设计文档里写明理由。
:::

### 冲突提示要具体

**只说一句“时段冲突”等于没说。** 用户不知道和哪个活动、哪段时间冲突，只能瞎猜着改时间。所以 `4003` 和预检的 `conflicts` 都要带上冲突场次的信息，提示也要把它们写进去。

```js
function showConflictMessage(conflicts) {
  const lines = conflicts.map((c) => {
    const start = formatDateTime(c.startTime)
    const end = formatDateTime(c.endTime)
    return `与“${c.activityTitle}”在 ${start} 到 ${end} 的场次冲突`
  })
  return `${lines.join('；')}。请调整时间或更换场地。`
}
```

效果是这样的：

> 与“程序设计竞赛”在 2026-04-10 15:00 到 18:00 的场次冲突。请调整时间或更换场地。

**这句话里有三样东西：哪个活动、哪段时间、下一步怎么办。** 前两样是从接口返回的 `conflicts` 里取的，第三样是文案固定给的。少了任何一样，用户都得多问一次。

**这要求后端在 `4003` 的响应里带回冲突场次的信息。** 这一条要提前和后端说，否则他只会返回一句“时段冲突”，前端拿不到任何细节。见[接口约定](/project/api)第三节的规则二。

## 五、时间选择

### `value-format` 和 `format` 是两个东西

`el-date-picker` 有两个配置时间的属性，名字很像，作用完全不同：

| 属性 | 控制什么 | 影响 |
| --- | --- | --- |
| `format` | **显示**格式 | 用户在输入框里看到的样子 |
| `value-format` | **绑定值**格式 | `v-model` 拿到的东西是什么类型 |

```vue
<el-date-picker
  v-model="form.startTime"
  type="datetime"
  format="YYYY-MM-DD HH:mm"
  value-format="YYYY-MM-DD HH:mm:ss"
  placeholder="选择开始时间"
/>
```

**只配 `format` 不配 `value-format`，`v-model` 拿到的是一个 `Date` 对象。** 直接把这个对象放进请求体，axios 会用 `JSON.stringify` 把它序列化成 ISO 字符串 `2026-04-10T14:00:00.000Z`，和后端约定的 `2026-04-10 14:00:00` 完全不是一个样子。后端接到的就是一串它不认识的字符。

**配上 `value-format` 之后，`v-model` 直接拿到格式化好的字符串**，可以直接提交，不用手动转换。

**还要注意大小写的区别。** [接口约定](/project/api)里时间格式写的是 `yyyy-MM-dd HH:mm:ss`，那是 Java 的写法；Element Plus 用的是 Day.js 的记号，同样的格式要写成 `YYYY-MM-DD HH:mm:ss`。**一个字母都不能错**：`mm` 是分钟，`MM` 是月份，写错了时间会变成乱码。

```js
// ✗ Java 风格，Day.js 不认
value-format="yyyy-MM-dd HH:mm:ss"

// ✓ Day.js 风格
value-format="YYYY-MM-DD HH:mm:ss"
```

### `disabled-date` 禁用不该选的日期

已经结束的活动不能再排场次，过去的日期也不能选。`disabled-date` 接收一个函数，参数是日期，返回 `true` 表示禁用：

```js
function disabledDate(date) {
  // 今天之前不能选
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  return date.getTime() < today.getTime()
}
```

```vue
<el-date-picker
  v-model="form.startTime"
  type="datetime"
  value-format="YYYY-MM-DD HH:mm:ss"
  :disabled-date="disabledDate"
/>
```

**`disabled-date` 只禁用日期，不禁用时间。** 用户还是可以选今天的 09:00（现在已经 15:00）。要连过去的时间一起拦，得在 `disabled-hours` 或者提交校验里做。**课程项目里做一个提交校验就够了** —— 前端禁用日期是体验，真正的约束仍然在后端。

### 开始时间必须早于结束时间的双向校验

`el-form` 的规则支持自定义校验函数。这里的关键是**双向**：改了开始时间要重新校验结束时间，改了结束时间也要重新校验开始时间，否则改完一个字段，另一个字段还挂着上次的错误。

```js [src/views/session/SessionForm.vue（校验节选）]
import { parseTime } from '@/utils/session'

function validateEndTime(rule, value, callback) {
  if (!value) {
    callback(new Error('请选择结束时间'))
  } else if (parseTime(value).getTime() <= parseTime(form.startTime).getTime()) {
    callback(new Error('结束时间必须晚于开始时间'))
  } else {
    callback()
  }
}

const rules = {
  startTime: [
    { required: true, message: '请选择开始时间', trigger: 'change' },
    {
      validator: (rule, value, callback) => {
        // 开始时间变了，结束时间的合法性可能跟着变，顺手重校验一次
        if (form.endTime) {
          formRef.value?.validateField('endTime')
        }
        callback()
      },
      trigger: 'change'
    }
  ],
  endTime: [
    { required: true, message: '请选择结束时间', trigger: 'change' },
    { validator: validateEndTime, trigger: 'change' }
  ]
}
```

**注意 `<=` 而不是 `<`。** 开始时间和结束时间相等（一个时长为零的场次）也是不合法的，这里和冲突检测的边界规则不一样 —— 冲突检测要放过相接的边界，而单条场次内部的时长必须大于零。**同一个模块里两个地方用了不同的边界符号，各自都对**，这一点要想清楚，别抄串了。

## 六、时段可视化

冲突的提示是“事后”的 —— 用户填完时间才发现撞了。**更好的做法是“事前”的**：把当天各场地的占用情况画成一条时间轴，用户一眼就能看出哪个场地、哪个时段是空的，直接挑空闲的地方填。

这不是必须做的功能，但做出来体验提升很明显，而且实现不难。

### 思路

一天的可安排时段固定成一个区间，比如 08:00 到 22:00，一共 840 分钟。每个场次占用的时段，可以换算成这条时间轴上的一个横向色条：

```
场地           08:00      12:00      16:00      20:00   22:00
报告厅         [────初赛────]
               [────────决赛──────]
多功能厅                   [──讲座──]
```

关键是两个计算：**色条从哪开始**（`left`）和**色条多宽**（`width`），都用百分比表示，这样容器宽度变了也不用改代码。

```js [src/views/session/timeline.js]
import { parseTime } from '@/utils/session'

const DAY_START = 8 * 60        // 08:00，单位分钟
const DAY_END = 22 * 60         // 22:00
const DAY_SPAN = DAY_END - DAY_START

/** 把时间换算成“一天中的第几分钟” */
function toMinutes(time) {
  const d = parseTime(time)
  return d.getHours() * 60 + d.getMinutes()
}

/**
 * 算出色条的 left 和 width（百分比）。
 * left 以 DAY_START 为起点，超出范围的会被裁到两端。
 */
export function toBarStyle(session) {
  const start = Math.max(toMinutes(session.startTime), DAY_START)
  const end = Math.min(toMinutes(session.endTime), DAY_END)
  return {
    left: `${((start - DAY_START) / DAY_SPAN) * 100}%`,
    width: `${((end - start) / DAY_SPAN) * 100}%`
  }
}
```

### 渲染

按场地分组，每个场地一行，行内放一条轨道（`position: relative`），场次是绝对定位的色条：

```vue [src/views/session/SessionTimeline.vue]
<script setup>
import { computed } from 'vue'
import { toBarStyle } from './timeline'

const props = defineProps({
  /** 场次列表，每条含 venueId、venueName、startTime、endTime、activityTitle、status */
  sessions: { type: Array, default: () => [] },
  /** 场地列表，用来保证没有场次的场地也显示一行 */
  venues: { type: Array, default: () => [] }
})

// 按场地分组。没有场次的场地也要占一行，否则用户会以为这个场地不存在
const rows = computed(() => {
  return props.venues.map((venue) => ({
    venueId: venue.id,
    venueName: venue.name,
    bars: props.sessions
      .filter((s) => s.venueId === venue.id && s.status !== 'CANCELLED')
      .map((s) => ({ ...s, style: toBarStyle(s) }))
  }))
})

// 时间轴上的刻度，每小时一个
const ticks = computed(() =>
  Array.from({ length: 15 }, (_, i) => 8 + i)
)
</script>

<template>
  <div class="timeline">
    <div class="timeline-header">
      <span class="venue-label" />
      <div class="track">
        <span v-for="h in ticks" :key="h" class="tick">{{ h }}:00</span>
      </div>
    </div>

    <div v-for="row in rows" :key="row.venueId" class="timeline-row">
      <span class="venue-label" :title="row.venueName">{{ row.venueName }}</span>
      <div class="track">
        <!-- 未占用的底纹，让空闲时段一眼可见 -->
        <div class="track-bg" />
        <div
          v-for="bar in row.bars"
          :key="bar.id"
          class="bar"
          :style="bar.style"
          :title="`${bar.activityTitle} ${bar.startTime} - ${bar.endTime}`"
        >
          {{ bar.activityTitle }}
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.timeline-row {
  display: flex;
  align-items: center;
  height: 32px;
}

.venue-label {
  flex: 0 0 120px;
  overflow: hidden;
  font-size: 13px;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.track {
  position: relative;
  flex: 1;
  height: 24px;
}

.track-bg {
  position: absolute;
  inset: 0;
  background: var(--el-fill-color-light);
  border-radius: 4px;
}

.bar {
  position: absolute;
  top: 0;
  overflow: hidden;
  height: 24px;
  padding: 0 6px;
  color: #fff;
  font-size: 12px;
  line-height: 24px;
  white-space: nowrap;
  background: var(--el-color-primary);
  border-radius: 4px;
}
</style>
```

**这个组件的价值和前面几节不一样。** 它不是“把数据展示出来”，而是**帮用户做出选择** —— 挑一个空的时段。这也是[数据看板](/project/impl-dashboard)里“待办比统计更有价值”的同一个思路：界面的价值在于帮用户做决定，不只是把数字摆出来。

**这个功能是选做的。** 时间紧就先不做，先保证冲突检测正确。可视化的前提是冲突数据已经准了，本末不能倒置。

## 七、关键决策

### 决策一：冲突检测前端预检和后端校验都做

**选了什么**：前端在用户选完场地和时间后调 `check-conflict` 做预检，后端在真正保存时再查一次，两个都保留。

**为什么**：两者的职责不一样。前端预检让用户在填表过程中就知道结果，不用等提交；后端校验是唯一的正确性保证，因为它能看到“别人刚提交的场次”。少了前端预检，体验差；少了后端校验，并发下会排出冲突的场次。

**代价**：检测逻辑写了两份，有前后不一致的风险。缓解办法是让两边的判定规则都以[业务规则](/project/rules)第四节的 `isTimeConflict` 为准，前端不用自己发挥。

### 决策二：场地用 `enabled` 停用，不用删除

**选了什么**：场地提供“停用 / 启用”，不提供删除。停用的场地不出现在新增场次的下拉选项里，但历史场次仍然能显示它的名字。

**为什么**：场次记录里存的是 `venueId`。删掉场地之后，历史场次就查不到场地名了 —— 用户看到的是一条“场地：未知”的记录，不知道这个活动当初在哪办的。**停用既解决了“这个场地不再可用”，又保住了历史数据。**

**代价**：场地列表里会积累一些不再使用的记录。用“已停用”标签区分，用户可以按状态筛，不影响使用。

### 决策三：时间统一用字符串传递，不用时间戳

**选了什么**：`el-date-picker` 配 `value-format="YYYY-MM-DD HH:mm:ss"`，`v-model` 直接拿字符串，请求体和响应体里的时间都是这个格式。

**为什么**：接口约定里的时间格式就是字符串。用时间戳要来回转换，转换代码本身就是 bug 的来源；字符串还有个好处是接口调试时肉眼就能看懂，抓包一眼就知道时间对不对。

**代价**：字符串比较时间大小要靠 `new Date()` 解析，而各家浏览器对 `2026-04-10 14:00:00` 这种带空格的格式解析行为不完全一致，所以要包一层 `parseTime` 做兼容。多写一个函数，换掉所有的手动转换，值得。

### 决策四：冲突信息由后端返回详情，不是只返回一个布尔值

**选了什么**：`check-conflict` 返回 `conflicts` 数组，每项带活动标题、开始时间、结束时间；`4003` 错误也带同样的信息。

**为什么**：只返回“有冲突”的话，用户不知道和谁冲突、冲突在哪段时间，只能一个个试。**提示里必须包含“发生了什么”和“怎么办”** —— 给不出冲突的对象，这句提示就没有信息量。

**代价**：后端要多查一次关联数据（冲突场次对应的活动标题）再返回。一次联表查询的成本，换来提示质量，值得。

### 决策五：一次只排一个场次，不做“批量排场次”

**选了什么**：新增场次一次提交一条，冲突就停下让用户改。

**为什么**：批量提交多个场次时，只要有一个冲突，整批就失败了 —— 用户不知道是哪一条的问题，要一条条排查。而且“哪些场次算同一个批次”本身没有清晰的定义。**一条一条来，每条都能给出明确的反馈，用户心里有底。**

**代价**：排五个场次要操作五次。课程项目里这个量级可以接受；如果以后真的需要批量，正确做法是后端提供批量接口，逐条返回结果，而不是前端用 `Promise.all` 硬凑。

## 八、常见坑

::: details 时段边界相接被误判为冲突
**现象**：已有场次 14:00 - 17:00，新增 17:00 - 20:00 提示冲突，但这两个时段明明首尾相接、不重叠。

**原因**：判定函数里写成了 `<` 而不是 `<=`。

```js
// ✗ 17:00 < 17:00 是 false，走到最后 return true，误判冲突
if (aEnd < bStart) return false

// ✓
if (aEnd <= bStart) return false
```

**为什么是这个等号**：场次是半开区间 `[start, end)`，17:00 这个瞬间属于后一场，不属于前一场。用 `<` 相当于按闭区间处理，相接的一瞬间就被算成了重叠。

**怎么处理**：改判定函数，然后补一条断言测试。这类边界 bug 光看代码看不出来，一定要写用例：

```js
// 边界相接不冲突
expect(isTimeConflict('2026-04-10 14:00:00', '2026-04-10 17:00:00',
                      '2026-04-10 17:00:00', '2026-04-10 20:00:00')).toBe(false)
// 完全包含冲突
expect(isTimeConflict('2026-04-10 14:00:00', '2026-04-10 17:00:00',
                      '2026-04-10 14:00:00', '2026-04-10 17:00:00')).toBe(true)
```
:::

::: details 编辑场次时自己和自己冲突，改不了
**现象**：把一个 14:00 - 17:00 的场次改成 15:00 - 17:00，保存时报冲突，提示的冲突场次正是它自己。

**原因**：查重时把这个场地在这个时段的所有场次都查了出来，其中包含正在编辑的这一条。

**怎么处理**：查重时排除自己。新增时传 `sessionId: null`，编辑时传当前场次的 id：

```js
const { conflict, conflicts } = await checkConflict({
  sessionId: form.id ?? null,   // 编辑时有值，新增时为 null
  venueId: form.venueId,
  startTime: form.startTime,
  endTime: form.endTime
})
```

**后端也要排除**，不能只靠前端过滤。后端拿到 `sessionId` 之后，在查询条件里加上“id 不等于这个值”。**这个参数记得在接口约定里写清楚**，否则后端不知道前端会传，就不会处理。
:::

::: details 取消的场次仍然占着时段
**现象**：取消了一个场次，想重新安排，系统说这个时段冲突。

**原因**：判定冲突时没有过滤 `status === 'CANCELLED'` 的场次，被取消的那条还参与比较。

**怎么处理**：查重和可视化时都跳过已取消的场次：

```js
if (s.status === 'CANCELLED') return false
```

**在时段可视化里也要过滤**，否则时间轴上还会画着一条已经取消的色条，用户以为那个时段被占着。

**这条规则要写进[业务规则](/project/rules)**，因为它同时影响“能不能保存”和“界面上显示什么”，只改一处不够。
:::

::: details 用了 `format` 没配 `value-format`，提交的是 Date 对象
**现象**：时间选择器显示得好好的，提交时后端报参数格式错误，抓包看到请求体里是 `2026-04-10T06:00:00.000Z`。

**原因**：`format` 只控制显示，`value-format` 才控制 `v-model` 拿到的类型。没配 `value-format` 时，绑定值是 `Date` 对象，`JSON.stringify` 把它转成了 ISO 字符串（还带了时区），和后端约定的 `2026-04-10 14:00:00` 不是一回事。

**怎么处理**：

```vue
<el-date-picker
  v-model="form.startTime"
  type="datetime"
  format="YYYY-MM-DD HH:mm"
  value-format="YYYY-MM-DD HH:mm:ss"
/>
```

**记住大小写的坑**：`YYYY` 是年、`MM` 是月、`mm` 是分。`YYYY-MM-DD HH:mm:ss` 里的 `mm` 写成 `MM`，时间会变成月份，而且不会报错，只会默默算错。
:::

::: details 停用场地后，历史场次显示不出场地名
**现象**：停用了一个场地，编辑历史场次时，场地下拉框里找不到这个场地，回填不上去，看着像是数据丢了。

**原因**：新增场次的下拉只加载了 `enabled = true` 的场地，但编辑一条历史场次时，它引用的场地可能已经被停用。选项列表里没有它，`el-select` 就显示成空白。

**怎么处理**：编辑时把当前场次引用的场地**补进选项列表**，即使它是停用的：

```js
// 编辑回填时，如果当前场地不在选项里，手动补一条
if (form.venueId && !venueOptions.value.some((v) => v.id === form.venueId)) {
  venueOptions.value.push({
    id: form.venueId,
    name: currentSession.venueName,   // 列表接口返回的场地名
    enabled: false
  })
}
```

**根本原因是“选项列表”和“已存数据”的来源不同。** 选项列表是“能选的”，已存数据是“已经选的”，后者可能不在前者里。**任何“编辑时回填下拉框”的场景都要考虑这一点**，不只是场地这一个字段。

顺带说：**这又是“不要用删除代替停用”的一个理由。** 场地真被删了的话，连 `venueName` 都查不出来，补选项都没得补。
:::

::: details 老版本 Safari 里 `new Date('2026-04-10 14:00:00')` 是 Invalid Date
**现象**：Chrome 里冲突检测一切正常，iOS 或 Safari 上所有场次都显示成“无冲突”，或者时间显示成 `NaN:NaN`。

**原因**：带空格的日期时间字符串不是标准的 ISO 格式，老版本 Safari 解析不了，返回 `Invalid Date`。`Invalid Date.getTime()` 是 `NaN`，`NaN` 参与的所有比较都是 `false`，于是判定函数一路返回“不冲突”。

**怎么处理**：包一层 `parseTime`，把空格换成 `T`：

```js
export function parseTime(text) {
  if (!text) return null
  return new Date(String(text).replace(' ', 'T'))
}
```

**注意这个 bug 很隐蔽**：出错的方式不是报错，而是“全部判定为不冲突”。如果项目里所有时间都经过 `parseTime`，就不会有这个问题。**只要项目里出现多处 `new Date(时间字符串)`，早晚会漏一处。**
:::

## 九、验收清单

| # | 验收项 | 怎么验证 |
| --- | --- | --- |
| 1 | 场地列表显示名称、容量、位置、启用状态 | 打开 `/venue`，四列都在，状态标签正确 |
| 2 | 能新增场地 | 填表保存，列表里看到它 |
| 3 | 场地名称唯一 | 用已存在的名称新增，名称输入框下提示重复，`4002` 不弹全局提示 |
| 4 | 能编辑场地 | 改名保存，列表里的名字跟着变 |
| 5 | 停用场地不影响历史场次 | 停用一个有场次的场地，历史场次仍显示场地名 |
| 6 | 停用的场地不出现在新增场次的下拉里 | 新增场次，下拉里找不到已停用的场地 |
| 7 | 场次列表能按活动筛 | 选一个活动，列表只剩它的场次 |
| 8 | 场次列表能按日期范围筛 | 选 4 月 1 日到 4 月 30 日，边界两天的场次都在 |
| 9 | 能新增场次 | 选活动、场地、时间，保存成功 |
| 10 | 结束时间必须晚于开始时间 | 选结束时间早于或等于开始时间，被拦下 |
| 11 | 同场地重叠时段被拦 | 给同一场地排 15:00 - 18:00（已有 14:00 - 17:00），提示冲突 |
| 12 | 冲突提示包含活动名和时段 | 提示里能看到冲突活动的标题和起止时间 |
| 13 | **边界相接不算冲突** | 已有 14:00 - 17:00，新增 17:00 - 20:00，保存成功 |
| 14 | 编辑场次能改时间 | 把 14:00 改成 15:00，不报自己和自己冲突 |
| 15 | 取消场次后时段被释放 | 取消一个场次，再排同一场地同一时段，保存成功 |
| 16 | 已取消的场次不画在时间轴上 | 取消后，时段可视化里对应的色条消失 |
| 17 | 不同场地同时段不冲突 | 两个场地在同一时间各排一个场次，都保存成功 |
| 18 | 时间格式符合约定 | 抓包看请求体，是 `2026-04-10 14:00:00`，不是 ISO 字符串 |

---

上一页：[报名审核模块](/project/impl-signup) · 下一页：[数据看板](/project/impl-dashboard)
