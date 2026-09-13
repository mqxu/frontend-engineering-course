# 11.4 列表页标准做法

## 后台一半的工作量在列表页

打开任何一个后台系统数一下：活动列表、报名列表、场次列表、场地列表、用户列表……**列表页的数量通常是表单页的两三倍。**

所以列表页必须形成模板。不然你会写五遍几乎一样的代码，而且每遍都漏一两个细节：

- 第一版忘了空状态，数据为空时页面一片白，用户以为坏了。
- 第二版忘了请求失败处理，接口报错时表格卡在加载动画上转个不停。
- 第三版忘了分页参数在查询时重置回第一页，用户在第 5 页改了筛选条件，看到“暂无数据”。

这一节给出一个可以直接抄的列表页模板，然后讲清楚每部分是为什么。

## 一个列表页的完整状态

先把“列表页到底有几个状态”想清楚。很多 bug 都是因为状态漏了：

| 状态 | 什么时候 | 页面显示什么 |
| --- | --- | --- |
| 初始 | 刚进页面，还没发请求 | 表格骨架或加载动画 |
| 加载中 | 请求发出去了 | 表格上盖一层 loading，或骨架屏 |
| 成功有数据 | 拿到非空数组 | 表格 + 分页 |
| 成功无数据 | 拿到空数组 | “暂无数据”文字 + 一个引导按钮 |
| 失败 | 请求报错 | 错误说明 + “重试”按钮 |

**后四种统称“四态”**，在[5.5 四态页面规范](/unit05/05-four-states)里讲过原则。这一节讲具体怎么做。

::: warning “成功无数据”和“失败”不能合并
这是最常见的偷懒：两种情况都显示“暂无数据”。

结果就是后端崩了的时候，用户看到“暂无数据，去创建一个吧”，于是他去点“新增”—— 又报错。**用户会以为是自己操作有问题，而不是网络有问题。**

**这两种状态给用户的下一步动作完全不同**：无数据 → 去创建；失败 → 重试。必须分开。
:::

## 先抽一个组合式函数

列表页的逻辑几乎完全一样：查询条件 → 发请求 → 拿列表和总数 → 分页 → 四态。把这套逻辑抽成 `useTable`：

```js [src/composables/useTable.js]
import { ref, reactive, computed } from 'vue'

/**
 * 列表页通用逻辑
 * @param {Function} fetcher 请求函数，接收 params，返回 { list, total }
 * @param {Object} options.query 查询条件初始值
 * @param {Object} options.immediate 是否立即请求，默认 true
 */
export function useTable(fetcher, options = {}) {
  const { query: initialQuery = {}, immediate = true } = options

  // 查询条件
  const query = reactive({ ...initialQuery })

  // 分页
  const page = ref(1)
  const pageSize = ref(10)
  const total = ref(0)

  // 数据与状态
  const list = ref([])
  const loading = ref(false)
  const error = ref(null)

  // 四态里的“成功无数据”：请求完成、没报错、但列表为空
  const isEmpty = computed(() => !loading.value && !error.value && list.value.length === 0)

  async function load() {
    loading.value = true
    error.value = null
    try {
      const res = await fetcher({
        ...query,
        page: page.value,
        pageSize: pageSize.value
      })
      list.value = res.list ?? []
      total.value = res.total ?? 0
    } catch (e) {
      error.value = e
      list.value = []
      total.value = 0
    } finally {
      loading.value = false
    }
  }

  /** 点“查询”：条件变了，必须回到第一页 */
  function search() {
    page.value = 1
    return load()
  }

  /** 重置查询条件并重新查 */
  function reset() {
    Object.assign(query, initialQuery)
    page.value = 1
    return load()
  }

  /** 每页条数变化：同样要回到第一页 */
  function handleSizeChange(size) {
    pageSize.value = size
    page.value = 1
    return load()
  }

  /** 页码变化：不需要回第一页 */
  function handlePageChange(p) {
    page.value = p
    return load()
  }

  /** 删除后刷新：如果当前页只剩一条，删完应该往前翻一页 */
  function reloadAfterRemove() {
    if (list.value.length === 1 && page.value > 1) {
      page.value -= 1
    }
    return load()
  }

  if (immediate) {
    load()
  }

  return {
    query,
    page,
    pageSize,
    total,
    list,
    loading,
    error,
    isEmpty,
    load,
    search,
    reset,
    handleSizeChange,
    handlePageChange,
    reloadAfterRemove
  }
}
```

::: tip 这段代码里三个容易漏的细节
**一、`search()` 里要把 `page` 重置为 1。** 用户在第三页时把状态筛成“草稿”，如果还在第三页请求，很可能结果为空。**这是列表页最经典的 bug。**

**二、`handleSizeChange` 也要回到第一页。** 从每页 10 条换成 20 条，原来在第 5 页（共 5 页）现在只有 3 页，第 5 页是空的。

**三、`reloadAfterRemove()` 处理删除后的翻页。** 第 3 页只剩一条数据，删掉之后第 3 页就空了，列表显示“暂无数据”—— 但第 2 页还有数据。**应该自动往前翻一页。**

这三个细节不需要记，只要记住一条：**只要查询条件或每页条数变了，`page` 就回到 1；只要数据量变了，要检查当前页是否还有内容。**
:::

## 一个完整的列表页

现在用 `useTable` 写活动列表：

```vue [src/views/activity/ActivityList.vue]
<script setup>
import { reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getActivityList, setActivityOffShelf, deleteActivity } from '@/api/activity'
import { useTable } from '@/composables/useTable'
import { ACTIVITY_STATUS_OPTIONS, activityStatusLabel, activityStatusTagType } from '@/utils/dict'
import { formatDateTime } from '@/utils/format'

defineOptions({ name: 'ActivityList' })

const router = useRouter()

const {
  query, page, pageSize, total, list, loading, error, isEmpty,
  load, search, reset, handleSizeChange, handlePageChange, reloadAfterRemove
} = useTable(
  async (params) => {
    const { data } = await getActivityList(params)
    return { list: data.records, total: data.total }
  },
  {
    query: {
      keyword: '',
      status: '',
      organizerId: ''
    }
  }
)

// ---- 行操作 ----

async function handleToggleOffShelf(row) {
  const next = !row.offShelf
  const actionText = next ? '下架' : '恢复上架'
  try {
    await ElMessageBox.confirm(
      `确定要${actionText}“${row.title}”吗？下架后学生将无法报名。`,
      `${actionText}确认`,
      { type: 'warning', confirmButtonText: '确定', cancelButtonText: '取消' }
    )
  } catch {
    return // 用户点了取消
  }
  await setActivityOffShelf(row.id, next)
  ElMessage.success(`${actionText}成功`)
  load()
}

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
  await reloadAfterRemove()
}

function goDetail(row) {
  router.push({ name: 'activity-detail', params: { id: row.id } })
}

function goCreate() {
  router.push({ name: 'activity-create' })
}

function goEdit(row) {
  router.push({ name: 'activity-edit', params: { id: row.id } })
}
</script>

<template>
  <div class="page">
    <!-- ① 查询区 -->
    <el-card shadow="never" class="filter-card">
      <el-form :model="query" inline @submit.prevent="search">
        <el-form-item label="关键字">
          <el-input
            v-model="query.keyword"
            placeholder="活动标题 / 组织者"
            clearable
            style="width: 200px"
            @keyup.enter="search"
          />
        </el-form-item>

        <el-form-item label="状态">
          <el-select v-model="query.status" placeholder="全部" clearable style="width: 140px">
            <el-option
              v-for="opt in ACTIVITY_STATUS_OPTIONS"
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

    <!-- ② 操作区 + 表格 -->
    <el-card shadow="never" class="table-card">
      <div class="table-toolbar">
        <el-button type="primary" @click="goCreate">
          <el-icon><Plus /></el-icon>新增活动
        </el-button>
        <span class="total-hint">共 {{ total }} 条</span>
      </div>

      <el-table
        v-loading="loading"
        :data="list"
        border
        stripe
        row-key="id"
        style="width: 100%"
      >
        <el-table-column prop="title" label="活动标题" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">
            <el-link type="primary" @click="goDetail(row)">{{ row.title }}</el-link>
          </template>
        </el-table-column>

        <el-table-column prop="type" label="类型" width="110" />

        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="activityStatusTagType(row.status)" size="small">
              {{ activityStatusLabel(row.status) }}
            </el-tag>
            <el-tag v-if="row.offShelf" type="info" size="small" class="ml-4">已下架</el-tag>
          </template>
        </el-table-column>

        <el-table-column label="报名情况" width="150">
          <template #default="{ row }">
            <span :class="{ 'is-full': row.approvedCount >= row.quota }">
              {{ row.approvedCount }} / {{ row.quota }}
            </span>
          </template>
        </el-table-column>

        <el-table-column label="报名截止" width="170">
          <template #default="{ row }">{{ formatDateTime(row.signupDeadline) }}</template>
        </el-table-column>

        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="goDetail(row)">详情</el-button>
            <el-button link type="primary" @click="goEdit(row)">编辑</el-button>
            <el-button link type="warning" @click="handleToggleOffShelf(row)">
              {{ row.offShelf ? '恢复' : '下架' }}
            </el-button>
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>

        <!-- ③ 空状态和错误状态写进 el-table 的 empty 插槽 -->
        <template #empty>
          <!-- 失败 -->
          <div v-if="error" class="state-block">
            <p class="state-title">数据加载失败</p>
            <p class="state-desc">{{ error.message }}</p>
            <el-button type="primary" @click="load">重新加载</el-button>
          </div>

          <!-- 无数据 -->
          <div v-else-if="isEmpty" class="state-block">
            <p class="state-title">还没有活动</p>
            <p class="state-desc">发布第一个活动，学生就能在手机上看到并报名了。</p>
            <el-button type="primary" @click="goCreate">立即创建</el-button>
          </div>
        </template>
      </el-table>

      <!-- ④ 分页 -->
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

<style scoped lang="scss">
.filter-card {
  margin-bottom: 12px;

  :deep(.el-form-item) {
    margin-bottom: 0;
  }
}

.table-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.total-hint {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.is-full {
  color: var(--el-color-danger);
  font-weight: 600;
}

.ml-4 {
  margin-left: 4px;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.state-block {
  padding: 32px 0;
  text-align: center;

  .state-title {
    margin: 0 0 4px;
    font-size: 15px;
    color: var(--el-text-color-primary);
  }

  .state-desc {
    margin: 0 0 16px;
    font-size: 13px;
    color: var(--el-text-color-secondary);
  }
}
</style>
```

## 逐块讲清楚

### 查询区：`v-model` 直接绑 `query`

`query` 是 `reactive` 对象，`v-model="query.keyword"` 直接绑到属性上。**不要为每个查询条件再建一个 `ref`** —— 那会让“重置”逻辑变成五行赋值。

点“查询”按钮时统一调 `search()`，而不是每个条件变化就立刻请求。理由：**筛选项多的时候，用户改一个条件就请求一次，会发出四五次无用请求。**

::: details 那搜索框为什么要支持回车
输入框配 `@keyup.enter="search"`，是给熟悉键盘的用户省一步。**注意不要配 `@input="search"`** —— 那会让用户每敲一个字母就发一次请求。

如果确实想要“边输边搜”，用防抖：

```js
import { useDebounceFn } from '@vueuse/core'

const debouncedSearch = useDebounceFn(search, 400)
```

`useDebounceFn` 的意思是：调用后等 400 毫秒，如果这期间又调用了，就重新计时。**结果是只有用户停手 400 毫秒后才真正发请求。** 防抖的完整用法见[案例 04 · 从接口获取数据](/cases/04-fetch)。
:::

### 表格：`el-table` 的三个属性

```vue
<el-table v-loading="loading" :data="list" border stripe row-key="id">
```

| 属性 | 作用 | 不加的后果 |
| --- | --- | --- |
| `v-loading` | 请求期间盖一层遮罩加转圈 | 用户点了查询没反应，会重复点 |
| `border` | 显示列边框 | 数据多时容易看串行 |
| `stripe` | 斑马纹 | 同上 |
| `row-key` | 行的唯一标识 | 展开行、多选、`reserve-selection` 都会失效 |

**`row-key` 特别重要**：现在列表里没有展开行和多选，看起来没用。但后面一旦加上“批量审核”需要跨页保留勾选，没有 `row-key` 就实现不了。

### 操作列：四个按钮的排布

操作列通常固定在右侧（`fixed="right"`），按钮用 `link` 样式（看起来像文字链接，不占视觉重量）。

**关键点是按钮的显隐要跟业务规则对上。** 对照[活动状态机](/project/rules)：

| 按钮 | 什么时候显示 | 什么时候禁用 |
| --- | --- | --- |
| 详情 | 总是 | — |
| 编辑 | 状态是草稿或报名中 | 已结束的活动不能改 |
| 下架 / 恢复 | 状态不是草稿 | 草稿还没发布，没有什么可下架的 |
| 删除 | 状态是草稿，或已结束 | 报名中的活动删掉会让已报名的学生懵掉 |

```vue
<!-- 更严谨的写法 -->
<template #default="{ row }">
  <el-button link type="primary" @click="goDetail(row)">详情</el-button>

  <el-button
    v-if="canEdit(row)"
    link
    type="primary"
    @click="goEdit(row)"
  >编辑</el-button>

  <el-button
    v-if="row.status !== 'DRAFT'"
    link
    type="warning"
    @click="handleToggleOffShelf(row)"
  >{{ row.offShelf ? '恢复' : '下架' }}</el-button>

  <el-button
    v-if="canDelete(row)"
    link
    type="danger"
    @click="handleDelete(row)"
  >删除</el-button>
</template>
```

```js
function canEdit(row) {
  return row.status === 'DRAFT' || row.status === 'SIGNING'
}

function canDelete(row) {
  return row.status === 'DRAFT' || row.status === 'FINISHED'
}
```

::: warning 前端按钮的显隐不是权限控制
把“删除”按钮藏起来，只是让界面更清爽。**用户完全可以在控制台里改掉 `v-if`，或者直接调接口。**

真正的权限必须后端做：接口收到请求时，先校验这个用户有没有权限删这条活动。

**前端做显隐，是为了减少用户的错误操作；后端做校验，才是为了安全。** 两件事都要做，但不要以为做了前者就够了。
:::

### 空状态和错误状态：写进 `#empty` 插槽

`el-table` 有一个 `#empty` 插槽，当 `:data` 为空数组时显示。**四态里的两种“空”就写在这里。**

为什么不用 `v-if` 在表格外面套一层？因为那样会丢掉表格的列头 —— 用户看不到有哪些列，会觉得页面结构变了。

**保持表格骨架，只换中间的内容区**，视觉上更稳定。

```vue
<template #empty>
  <div v-if="error">
    <!-- 失败：给“重新加载” -->
  </div>
  <div v-else-if="isEmpty">
    <!-- 无数据：给“立即创建” -->
  </div>
</template>
```

`error` 优先判断 —— 出错时 `list` 也是空的，如果不先判断 `error`，会显示成“还没有活动”。**这就是前面说的“两种空不能合并”。**

### 分页：`@current-change` 和 `@size-change` 是两个事件

```vue
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
```

`layout` 里的字符串按顺序决定显示哪些控件：

| 值 | 显示什么 |
| --- | --- |
| `total` | “共 42 条” |
| `sizes` | 每页条数下拉框（配合 `page-sizes`） |
| `prev` / `pager` / `next` | 上一页、页码、下一页 |
| `jumper` | “跳至 N 页”输入框 |

`background` 让页码有底色，选中态更明显。

::: warning `:total` 必须是总数，不是当前页条数
最常见的错误是把接口返回的数组长度当成 `total`：

```js
// ✗ 表格只显示第 1 页的 10 条，分页器也只有 1 页
total.value = res.data.length
```

正确做法是后端返回总条数，前端直接赋值：

```js
// ✓
total.value = res.data.total
```

如果后端不返回总数，就要在后端加（这是一个必须加的接口字段）。**前端自己算不出来 —— 前端只拿到了当前页的数据。**

分页有两种实现，前端分页和后端分页的差别见[案例 02 · 可排序筛选的数据表格](/cases/02-grid)。
:::

## 列表页模板的检查清单

以后每写一个列表页，对着这份清单过一遍：

| 检查项 | 怎么验证 |
| --- | --- |
| 查询条件变化后回到第 1 页 | 翻到第 3 页，改一个筛选条件，点查询，看请求参数里的 `page` 是不是 1 |
| 每页条数变化后回到第 1 页 | 同上 |
| 加载中有反馈 | 网络面板限速成 Slow 3G，看有没有 loading |
| 无数据状态有引导 | 清空筛选条件查一个不存在的关键字，看提示和按钮 |
| 失败状态有重试 | 把接口地址改错，看是否显示错误信息与“重新加载” |
| 删除最后一条会往前翻页 | 翻到最后一页，删光该页数据，看是否自动回退 |
| 危险操作有二次确认 | 点删除，看有没有确认弹窗 |
| 操作成功后刷新列表 | 下架一条，看列表里的状态是否立刻变了 |
| 分页 `total` 是总数 | 对比接口返回的 `total` 和分页器显示的总数 |
| 表格有 `row-key` | 检查属性 |

## 小结

- **列表页占后台工作量的一半以上，必须形成模板。**
- **四态加初始态**：初始、加载中、成功有数据、成功无数据、失败。**“无数据”和“失败”不能合并**，它们要引导用户做不同的事。
- **`useTable` 把分页、查询、四态这套逻辑抽出来**，每个列表页只负责“请求函数”和“列定义”。
- **三个必须记住的翻页规则**：查询条件和每页条数变化时 `page` 回到 1；删除后如果当前页空了要往前翻一页。
- **查询用“点按钮触发”**，不要每个条件变化就请求。要边输边搜就用 `useDebounceFn` 防抖。
- **`v-loading`、`border`、`stripe`、`row-key`** 四个属性是标配，`row-key` 现在看不出作用但以后会需要。
- **操作列按钮的显隐要跟状态机对上**，但前端显隐不是权限控制，后端必须再校验一次。
- **空状态和错误状态写进 `el-table` 的 `#empty` 插槽**，保持表格骨架不塌。
- **`:total` 必须是后端返回的总条数**，不是当前页数组的长度。
- **删除后自动往前翻页**这个小细节，用户不会夸你，但没有它用户会骂你。

## 常见坑

::: details 点查询后表格闪一下空白，然后才显示数据
**现象**：点查询，表格先变成“暂无数据”，再变成有数据，中间闪了一下。

**原因**：请求开始时没有清空旧数据，但 `loading` 和 `error` 的状态组合让 `isEmpty` 短暂为真。

**怎么处理**：两种做法。

**做法一**：请求开始时不清空 `list`，只在 `finally` 里赋值。这样旧数据一直在，`v-loading` 遮罩盖着，不会闪。

**做法二**：把“是否已经请求过”也纳入判断：

```js
const isEmpty = computed(
  () => !loading.value && !error.value && list.value.length === 0 && hasLoaded.value
)
```

**推荐做法一**，简单且没有额外状态。上面 `useTable` 的写法就是做法一 —— 只有 `catch` 里才把 `list` 清空。
:::

::: details 分页器显示了页码，但点下一页数据没变
**现象**：分页器有 5 页，点第 2 页，请求发出去了（网络面板能看到），但表格数据还是第 1 页的。

**原因**：`el-pagination` 用的是 `:current-page`（单向绑定），页面内部维护了自己的状态。点击时它内部状态变了，但你的 `page` ref 没变 —— 除非你绑了 `@current-change`。

**怎么处理**：确认三点：① 绑了 `@current-change`；② 处理函数里更新了 `page.value`；③ 处理函数里调用了 `load()` 重新请求。

如果用的是 `v-model:current-page`（双向绑定），就不需要 `@current-change` 里手动改 `page`，但**仍然需要重新请求**：

```vue
<!-- 双向绑定写法：page 自动更新，但还要手动 load -->
<el-pagination
  v-model:current-page="page"
  v-model:page-size="pageSize"
  :total="total"
  @current-change="load"
  @size-change="search"
/>
```

注意 `@size-change` 绑的是 `search` 而不是 `load` —— 因为每页条数变了要回到第一页，`search` 会重置 `page`。

**两种写法不要混**：既用 `v-model` 又在处理函数里改 `page`，容易出现页码跳动。
:::

::: details 删除失败，但列表还是刷新了
**现象**：点删除，后端返回 500，前端却提示“删除成功”。

**原因**：`await deleteActivity(row.id)` 没有包在 `try` 里，或者请求层拦截器把错误“吞掉”了，让 Promise 变成了成功状态。

**怎么处理**：先检查请求拦截器 —— 有些同学在拦截器里写了 `catch` 并返回 `Promise.resolve()`，这会让所有错误都变成成功。**拦截器只应该处理通用逻辑（带 token、统一提示），不要改变 Promise 的成功 / 失败状态。**

正确的写法：

```js [src/api/request.js]
request.interceptors.response.use(
  (response) => {
    const { code, data, message } = response.data
    if (code !== 0) {
      // 业务错误也要变成失败，不能 resolve
      ElMessage.error(message || '请求失败')
      // 关键：把业务码挂到 Error 上再 reject
      const err = new Error(message || '请求失败')
      err.code = code
      err.data = data
      return Promise.reject(err)
    }
    return data
  },
  (error) => {
    // HTTP 层错误交给调用方或统一处理
    return Promise.reject(error)
  }
)
```

**两处关键：**

**一、`return Promise.reject(...)`。** 不要写 `return Promise.resolve()`，也不要在 `catch` 里不 `throw` —— 那会让失败变成成功。

**二、`err.code = code` 这一行不能省。** 如果直接 `Promise.reject(new Error(message))`，页面里就拿不到业务码了：

```js
try {
  await approveSignup(id)
} catch (e) {
  if (e.code === 2005) {        // ← 没有上面那行的话，这里永远是 undefined
    quotaErrorMessage.value = e.message
  }
}
```

**`new Error()` 只有 `message` 和 `stack`，没有 `code`。** 要按错误码分支处理（名额已满、时段冲突、场地重名都要有不同的提示），就必须在 reject 之前把码挂上去。

**`err.data = data` 也一样重要** —— 冲突检测的错误（`4003`）会在 `data` 里带回冲突的场次信息，不挂上去前端就只拿到一句“时段冲突”，没有信息量。
:::

::: details 表格列很多，横向滚动时操作列跟着滚走了
**现象**：12 列的表格，横着滚到右边，操作按钮找不到了。

**原因**：操作列没加 `fixed="right"`。

**怎么处理**：

```vue
<el-table-column label="操作" width="220" fixed="right">
```

**注意 `fixed` 的列如果也配了 `min-width`，`el-table` 会警告。** 固定列必须给确切的 `width`。

还有一个附带问题：`fixed` 的列在加上 `v-loading` 时，遮罩可能盖不住固定列。如果出现这个现象，把 `v-loading` 移到外层 `el-card` 上，或者用 `element-loading-text` 配全屏 loading。

**最根本的建议是：控制列数。** 12 列的后台表格没人看得过来。把次要信息收进详情页，或者把“报名情况”“报名截止”这种关联信息合并成一列。
:::

::: details 状态筛选用的是中文，但接口要的是英文枚举
**现象**：下拉框显示“报名中”，但接口需要的是 `SIGNING`。

**原因**：直接拿显示文案去请求了。

**怎么处理**：把选项做成 `{ label, value }` 结构，`el-select` 绑 `value`：

```js [src/utils/dict.js]
export const ACTIVITY_STATUS_OPTIONS = [
  { label: '草稿', value: 'DRAFT' },
  { label: '报名中', value: 'SIGNING' },
  { label: '报名截止', value: 'SIGNUP_CLOSED' },
  { label: '已结束', value: 'FINISHED' }
]
```

```js
// 显示文案：从 options 里找 label
export function activityStatusLabel(value) {
  return ACTIVITY_STATUS_OPTIONS.find((o) => o.value === value)?.label ?? '未知'
}

// 标签颜色
export function activityStatusTagType(value) {
  return {
    DRAFT: 'info',
    SIGNING: 'success',
    SIGNUP_CLOSED: 'warning',
    FINISHED: ''
  }[value] ?? 'info'
}
```

**这个 `dict.js` 文件很重要。** 状态文案会出现在列表、详情、表单、看板好几个地方，**统一在一处维护，改文案只改一个文件**。散落在各页面里的魔法字符串是后期维护的灾难。
:::

## 课后练习

::: details 练习 1：把列表页改造成“报名审核列表”
用同一套模板写 `SignupList.vue`，展示报名记录，要求：

- 查询条件：活动标题关键字、审核状态
- 列：学生姓名、学号、活动标题、报名时间、审核状态
- 行操作：通过、驳回（驳回要弹出输入理由的对话框）
- 通过的记录不可再操作

**思路提示**：

- 状态枚举复用 `dict.js`，新增 `SIGNUP_STATUS_OPTIONS`（待审核 / 已通过 / 已驳回 / 已取消）。
- “驳回要输理由”用 `ElMessageBox.prompt`，注意它的返回结构和 `confirm` 不同，输入值在 `{ value }` 里。
- “通过”这个动作有个副作用：会占用活动名额。想一想前端要不要立刻提示余额变化，还是等列表刷新后由后端返回最新的报名数。（提示：必须以后端返回的为准，前端自己算会和后端不一致）
:::

::: details 练习 2：给列表加上 URL 查询参数同步
现在刷新页面，查询条件和页码都会丢失。请把它们同步到 URL 的 query 里。

**思路提示**：

- 进页面时从 `route.query` 读初始值，传给 `useTable` 的 `query` 选项。
- 查询、翻页、改每页条数时，用 `router.replace` 更新 query（用 `replace` 不用 `push`，否则用户点“返回”要按十几次才退得出去）。
- 注意一个坑：`route.query` 里的值都是字符串，`page` 读出来要 `Number()` 转一下。
- **做完之后想一想**：什么情况下值得做这个功能？（提示：需要分享链接给同事、需要浏览器前进后退时，价值就出来了。一般的后台查询不值得，因为用户不会分享一个筛选后的列表 URL）
:::

::: details 练习 3：把四态抽成一个通用组件
现在四态的逻辑写在 `#empty` 插槽里。请抽成 `StateWrapper.vue`，用法：

```vue
<StateWrapper :loading="loading" :error="error" :empty="isEmpty" empty-text="还没有活动">
  <el-table :data="list">……</el-table>
</StateWrapper>
```

**思路提示**：

- 组件内部根据四个 props 决定渲染默认插槽还是状态块。
- “空状态”和“失败状态”的内容要能自定义，用两个具名插槽 `#empty` 和 `#error`，配默认内容兜底。
- 想一想：`el-table` 的 `#empty` 插槽和这个组件能不能同时用？（提示：能，但要决定谁负责显示。最好的分工是：`StateWrapper` 只处理“请求失败”和“加载中”，空状态交给 `el-table` 的 `#empty`，这样列头不会丢）
- **写出你的选择和理由**。这类“抽象到什么程度”的判断，是这一节真正要练的能力。
:::

::: details 练习 4：找出这段代码的四个 bug
```vue
<script setup>
import { ref } from 'vue'
const list = ref([])
const page = ref(1)
const total = ref(0)

async function load() {
  const res = await getActivityList({ page: page.value })
  list.value = res.data.records
  total.value = res.data.records.length
}

function handleSearch() {
  load()
}
</script>

<template>
  <el-table :data="list">
    <el-table-column prop="title" label="标题" />
  </el-table>
  <el-pagination :current-page="page" :total="total" @current-change="load" />
</template>
```

**思路提示**：

想四个方向：① `total` 赋的值对不对？② 查询时 `page` 该不该重置？③ `load` 里有没有处理请求失败和 `loading`？④ `@current-change="load"` 能改到 `page` 吗？（提示：`el-pagination` 触发事件时会传新页码，你的 `load()` 接收到了吗？）

**这四个问题在这节课里都讲过，回去对着找。**
:::

---

上一节：[11.3 布局骨架与嵌套路由](/unit11/03-layout) · 下一节：[11.5 表单页标准做法](/unit11/05-form-page)
