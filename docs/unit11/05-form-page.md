# 11.5 表单页标准做法

## 表单是 bug 最集中的地方

一个后台系统里，列表页出 bug 顶多是显示不对，**表单页出 bug 会写进数据库。**

看一下这个项目里“新增活动”需要考虑多少事：

- 标题必填，长度 2 到 50
- 报名截止时间必填，且必须晚于当前时间
- 名额必填，必须是正整数，不能超过场地容量
- 类型必填，从固定几个里选
- 编辑模式下，前三个字段能不能改？（提示：活动已经有人报名了，就不能改名额到比已报名人数还少）
- 提交中要禁止重复点击，否则会创建两条一样的数据
- 用户填了一半切走，要不要提醒？

**这些事一件不做，就会变成一个线上问题。** 所以这一节的重点不是“怎么写表单”，而是“怎么不漏”。

## 新增和编辑共用一个组件

上一节 11.1 说过：新增和编辑字段完全相同，用一个组件，靠路由参数区分。

```vue [src/views/activity/ActivityForm.vue]
<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter, onBeforeRouteLeave } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getActivityDetail, createActivity, updateActivity } from '@/api/activity'
import { ACTIVITY_TYPE_OPTIONS } from '@/utils/dict'

defineOptions({ name: 'ActivityForm' })

const route = useRoute()
const router = useRouter()

// ① 判断模式
const activityId = computed(() => route.params.id)
const isEdit = computed(() => Boolean(activityId.value))

// ② 表单数据
const formRef = ref(null)
const form = reactive({
  title: '',
  type: '',
  quota: 50,
  signupDeadline: '',
  description: ''
})

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
          callback(new Error('名额必须是大于 0 的整数'))
        } else if (isEdit.value && value < originalApprovedCount.value) {
          // 编辑时不能把名额改到比已通过人数还少
          callback(new Error(`已有 ${originalApprovedCount.value} 人通过审核，名额不能小于这个数`))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ],
  signupDeadline: [
    { required: true, message: '请选择报名截止时间', trigger: 'change' },
    {
      validator: (rule, value, callback) => {
        if (!value) return callback()
        if (new Date(value).getTime() <= Date.now()) {
          callback(new Error('报名截止时间必须晚于当前时间'))
        } else {
          callback()
        }
      },
      trigger: 'change'
    }
  ]
}

// ④ 编辑模式下已通过的人数，用于上面的校验
const originalApprovedCount = ref(0)

// ⑤ 提交状态
const submitting = ref(false)
// ⑥ 是否已加载完初始数据，用于“离开提醒”的判断基准
const dirty = ref(false)

onMounted(async () => {
  if (!isEdit.value) return
  const { data } = await getActivityDetail(activityId.value)
  Object.assign(form, {
    title: data.title,
    type: data.type,
    quota: data.quota,
    signupDeadline: data.signupDeadline,
    description: data.description
  })
  originalApprovedCount.value = data.approvedCount ?? 0
})

// ⑦ 提交
async function handleSubmit(publish = false) {
  try {
    await formRef.value.validate()
  } catch {
    return // 校验失败，validate 会 reject
  }

  submitting.value = true
  try {
    const payload = { ...form, publish }
    if (isEdit.value) {
      await updateActivity(activityId.value, payload)
      ElMessage.success('保存成功')
    } else {
      await createActivity(payload)
      ElMessage.success(publish ? '创建并发布成功' : '草稿已保存')
    }
    dirty.value = false
    router.push({ name: 'activity-list' })
  } catch (e) {
    // 错误提示由请求层拦截器统一处理，这里只负责不跳转
  } finally {
    submitting.value = false
  }
}

function handleCancel() {
  router.back()
}

// ⑧ 离开提醒
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
</script>

<template>
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
        <el-input v-model="form.title" placeholder="例如：2026 春季校园歌手大赛" maxlength="50" show-word-limit />
      </el-form-item>

      <el-form-item label="活动类型" prop="type">
        <el-select v-model="form.type" placeholder="请选择" style="width: 240px">
          <el-option
            v-for="opt in ACTIVITY_TYPE_OPTIONS"
            :key="opt.value"
            :label="opt.label"
            :value="opt.value"
          />
        </el-select>
      </el-form-item>

      <el-form-item label="名额" prop="quota">
        <el-input-number v-model="form.quota" :min="1" :max="2000" :step="10" />
        <span class="field-hint">通过审核的人数达到此上限后，报名入口自动关闭</span>
      </el-form-item>

      <el-form-item label="报名截止" prop="signupDeadline">
        <el-date-picker
          v-model="form.signupDeadline"
          type="datetime"
          placeholder="选择日期时间"
          value-format="YYYY-MM-DD HH:mm:ss"
          :disabled-date="(d) => d.getTime() < Date.now() - 86400000"
          style="width: 240px"
        />
      </el-form-item>

      <el-form-item label="活动说明" prop="description">
        <el-input
          v-model="form.description"
          type="textarea"
          :rows="4"
          maxlength="500"
          show-word-limit
          placeholder="面向哪些同学、需要准备什么、注意事项等"
        />
      </el-form-item>

      <el-form-item>
        <el-button type="primary" :loading="submitting" @click="handleSubmit(false)">
          {{ isEdit ? '保存' : '存为草稿' }}
        </el-button>
        <el-button v-if="!isEdit" :loading="submitting" @click="handleSubmit(true)">
          保存并发布
        </el-button>
        <el-button @click="handleCancel">取消</el-button>
      </el-form-item>
    </el-form>
  </el-card>
</template>

<style scoped lang="scss">
.field-hint {
  margin-left: 12px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
</style>
```

## 逐块讲清楚

### 校验规则的三种类型

Element Plus 的 `rules` 底层用的是一套声明式校验，规则有三种写法：

**第一种：单条规则用对象**

```js
title: [
  { required: true, message: '请输入活动标题', trigger: 'blur' },
  { min: 2, max: 50, message: '标题长度在 2 到 50 个字符之间', trigger: 'blur' }
]
```

字段可以配多条规则，**校验时按顺序执行，任何一条失败就停下来**。

**第二种：规则用 `validator` 函数**

需要跨字段、或者需要请求后端才能判断的校验，用 `validator`：

```js
{
  validator: (rule, value, callback) => {
    if (new Date(value).getTime() <= Date.now()) {
      callback(new Error('报名截止时间必须晚于当前时间'))   // 传 Error 表示失败
    } else {
      callback()                                        // 不传参数表示通过
    }
  },
  trigger: 'change'
}
```

**关键点：`callback()` 不带参数是通过，`callback(new Error('...'))` 是失败。** 忘了调用 `callback` 会让校验永远挂着，表现为“点提交没反应”。

**第三种：规则可以返回 Promise**

```js
{
  validator: async (rule, value) => {
    if (!value) return
    const { data } = await checkTitleExists(value)
    if (data.exists) throw new Error('这个标题已经被占用了')
  },
  trigger: 'blur'
}
```

这种写法更简洁 —— 不抛错就是通过。**注意这种校验会发请求，`trigger` 用 `blur` 不要用 `change`**，否则用户每敲一个字就查一次。

### `trigger` 该用 `blur` 还是 `change`

| 控件 | 用哪个 | 为什么 |
| --- | --- | --- |
| `el-input` | `blur` | 边输边报错很烦，等用户离开输入框再提示 |
| `el-select` | `change` | 选项是点选的，选完就该校验 |
| `el-date-picker` | `change` | 同上 |
| `el-input-number` | `blur` 或 `change` | 用 `change` 更及时，因为它的改动很明确 |

**校验失败时自动滚到第一个出错的字段**，这个行为 `el-form` 自带，不用配。

### 提交：三个必须做的事

```js
async function handleSubmit(publish = false) {
  try {
    await formRef.value.validate()
  } catch {
    return   // ← 这就是“表单校验失败”的分支
  }
  // ...
}
```

**第一件：`validate()` 失败会 reject，必须包 `try`。** 不包的话，用户填错一个字段，控制台会出现一条未捕获的 Promise 错误，而且后面的代码照样往下跑（如果 `await` 写漏了），把脏数据提交上去。

**第二件：`submitting` 要在 `finally` 里恢复。**

```js
submitting.value = true
try { /* 提交 */ } finally {
  submitting.value = false   // ← 无论成功失败都要恢复
}
```

漏了 `finally` 会出现两种情况：提交成功跳走了（没影响），或者提交失败 —— **按钮永远卡在 loading 状态，用户只能刷新页面**。

**第三件：`submitting` 要防重复提交。** 上面模板里按钮绑了 `:loading="submitting"`。`el-button` 在 `loading` 时会自动禁用点击。**这是防重复提交最简单有效的办法。**

但要注意一个坑：**用户可能用回车键提交**。如果表单上绑了 `@submit.prevent="handleSubmit"`，回车会绕过按钮的 loading 状态。这时候要在函数开头加一道判断：

```js
async function handleSubmit(publish = false) {
  if (submitting.value) return   // ← 兜底
  // ...
}
```

### 日期：显示格式和数据格式分开

```vue
<el-date-picker
  v-model="form.signupDeadline"
  type="datetime"
  value-format="YYYY-MM-DD HH:mm:ss"
  :disabled-date="(d) => d.getTime() < Date.now() - 86400000"
/>
```

这里有三个配置值得说：

**`value-format`** —— `el-date-picker` 默认绑定的值是 `Date` 对象。**`Date` 对象在 `JSON.stringify` 时会变成 ISO 格式（`2026-03-20T06:30:00.000Z`），和很多后端约定的 `yyyy-MM-dd HH:mm:ss` 不一样。** 配 `value-format` 让它直接绑定字符串，省掉一层转换。

**`disabled-date`** —— 把过去的日期置灰，用户选不了。注意它的粒度是“天”，所以 `Date.now() - 86400000`（一天）的意思是“昨天之前都禁用”。**当天仍然可以选，因为当天里还有未来的时间点。** 真正的“必须晚于当前时间”由后面的 `validator` 兜住。

**两个校验都要。** `disabled-date` 是“让用户选不到”，`validator` 是“防止绕过”。**只做前端的可达性限制是不够的** —— 用户可以手动输入日期（`el-date-picker` 支持键盘输入）。

::: warning `value-format` 和 `format` 不是一回事
- `format`：**输入框里显示的格式**，比如 `YYYY年MM月DD日 HH时mm分`
- `value-format`：**绑定值的格式**，比如 `YYYY-MM-DD HH:mm:ss`

只配 `format` 不配 `value-format`，绑定值还是 `Date` 对象。**很多同学以为配了 `format` 就够了，结果提交上去的日期格式后端不认。**
:::

### 编辑模式下的字段限制

编辑一个“报名中”的活动时，有些字段不能随便改：

| 字段 | 草稿状态 | 报名中状态 | 原因 |
| --- | --- | --- | --- |
| 标题 | 可改 | 可改 | 改了不影响已有报名 |
| 类型 | 可改 | 可改 | 同上 |
| 名额 | 可改 | **只能调大** | 已经有人通过审核了，调小到比已通过人数还少，数据就不一致了 |
| 报名截止时间 | 可改 | **只能往后退** | 提前截止会让已报名的学生觉得被坑了 |

这个限制在 `validator` 里实现（前一节代码里的 `quota` 规则就是这个）。**更好的做法是用 `:disabled` 让用户改不了**，但要注意：**完全禁用会让用户不知道原因**，所以在旁边加一句提示。

```vue
<el-form-item label="名额" prop="quota">
  <el-input-number v-model="form.quota" :min="1" :max="2000" />
  <span v-if="isEdit && originalApprovedCount > 0" class="field-hint">
    已有 {{ originalApprovedCount }} 人通过审核，名额不能小于这个数
  </span>
</el-form-item>
```

## 两个按钮 vs 一个按钮

新增活动的页面上，有“存为草稿”和“保存并发布”两个按钮。这也是一种设计选择。

| 方案 | 好处 | 代价 |
| --- | --- | --- |
| 两个按钮 | 用户少点几次（不用先进列表再点发布） | 需要后端支持 `publish` 参数 |
| 一个“保存”按钮 | 后端接口简单 | 用户要走“保存 → 回列表 → 找这条 → 点发布”四步 |
| 一个“保存”，再配一个“状态”下拉 | 灵活，可以一次切到任何状态 | 状态机暴露给用户，容易选错 |

**推荐两个按钮。** 常用的动作（保存草稿、直接发布）一键完成，是后台系统该有的效率。

**但要注意**：如果后端只提供了 `POST /api/activities`（创建），没有 `publish` 参数，那前端要发两次请求 —— 先创建，拿到 id，再调发布接口：

```js
async function handleSubmit(publish = false) {
  await formRef.value.validate()

  submitting.value = true
  try {
    const { data } = await createActivity(form)
    if (publish) {
      await publishActivity(data.id)   // 第二次请求
    }
    // ...
  } finally {
    submitting.value = false
  }
}
```

**两次请求的问题是它们不是原子的** —— 第二次失败时，活动已经创建了，处于草稿状态。用户看到“发布失败”，但列表里已经有这条活动了。

**这种情况应该在后端合并成一个事务接口。** 前端能做的是把提示写清楚：“草稿已保存，发布失败，请在列表中重试发布”。**不要假装什么都没发生。**

## 离开提醒

用户填了半个小时的报名规则，不小心点到菜单，全没了。这个体验很差。

```js
onBeforeRouteLeave(async () => {
  if (!dirty.value || submitting.value) return true
  try {
    await ElMessageBox.confirm('表单还没保存，确定要离开吗？', '提示', { type: 'warning' })
    return true    // 用户确认离开
  } catch {
    return false   // 用户选择留下，导航被取消
  }
})
```

三个要点：

**一、`dirty` 要有意义。** 上面的写法是在 `el-form` 上绑 `@change="dirty = true"`。但 `change` 只在值真的变化时触发，所以**用户点进某个输入框又出来，不会触发**。这正是想要的。

**二、提交成功跳转时要跳过询问。** 上面代码在 `router.push` 之前设了 `dirty.value = false`。**顺序不能颠倒** —— 先设 false，再 push。

**三、`submitting` 时直接放行。** 提交中不询问，否则会出现“点提交 → 跳转 → 弹出离开确认”的怪事。

::: details 为什么还要处理“关闭浏览器”的情况
`onBeforeRouteLeave` 只在**站内路由跳转**时生效。用户直接关闭标签页、或者按 F5 刷新，它拦不住。

要拦这两种情况，得用浏览器的原生事件：

```js
import { onMounted, onUnmounted } from 'vue'

function handleBeforeUnload(e) {
  if (!dirty.value) return
  e.preventDefault()
  e.returnValue = ''   // 现代浏览器只看有没有设这个值，文案由浏览器决定
}

onMounted(() => window.addEventListener('beforeunload', handleBeforeUnload))
onUnmounted(() => window.removeEventListener('beforeunload', handleBeforeUnload))
```

**注意：浏览器不允许自定义这段提示的文字。** 你只能触发它，显示什么由 Chrome / Edge / Safari 自己决定。这是浏览器的安全限制，防止页面用假提示骗用户。

**还有一个细节**：`beforeunload` 在提交成功跳转时也会触发，所以还需要在 `dirty.value = false` 之后它才不拦。上面的写法已经满足了。

**最后提醒**：不要滥用。用户点“取消”时也弹一个“确定要离开吗”，会让人烦躁。**只在真的可能有数据丢失时才拦。**
:::

## 表单页模板的检查清单

| 检查项 | 怎么验证 |
| --- | --- |
| 新增和编辑共用一个组件 | 检查 `views/activity/` 下只有一个 `ActivityForm.vue` |
| 编辑模式会先拉详情回填 | 从列表点编辑，字段有值；直接访问 `/activity/create`，字段是空的 |
| 必填项有提示 | 什么都不填点提交，看每个必填项下面有没有红字 |
| 数字字段不能输文字 | 在名额里粘一段文字，看是否被拦 |
| 日期不能选过去 | 打开日期选择器，看过去的日期是否置灰 |
| 提交时按钮 loading | 点提交，看按钮是否变 loading 且不可重复点 |
| 提交失败后按钮恢复 | 把接口地址改错，提交失败后看按钮是否恢复可点 |
| 提交成功有提示并跳转 | 看是否提示并回到列表页 |
| 提交成功后列表有新数据 | 回到列表页，看列表是否包含刚创建的活动 |
| 编辑时名额不能小于已通过人数 | 造一条已有 5 人通过的活动，把名额改成 3，看是否报错 |
| 离开未保存的表单有提醒 | 填一个字段，点侧边栏菜单，看有没有确认弹窗 |
| 离开提醒在提交成功时不出现 | 提交成功跳转时不应弹提示 |

## 小结

- **表单页出 bug 会写进数据库**，所以要比列表页更小心。
- **新增和编辑共用一个组件**，靠 `route.params.id` 判断模式。区别只有“要不要拉详情回填”和“调 POST 还是 PUT”两处。
- **校验规则三种写法**：声明式对象、`validator` 函数、`validator` 返回 Promise。忘记调用 `callback` 会让校验永远挂着。
- **`trigger` 选择**：输入框用 `blur`，选择类控件用 `change`。
- **`validate()` 失败会 reject**，必须包 `try`。
- **`submitting` 必须在 `finally` 里恢复**，否则失败后按钮永久卡在 loading。
- **`submitting` 要防重复提交**，用 `:loading` 加函数开头的兜底判断（防回车键提交）。
- **日期的 `format` 和 `value-format` 是两件事**，只配 `format` 绑定值还是 `Date` 对象。
- **`disabled-date` 和 `validator` 都要做** —— 前者让用户选不到，后者防止绕过。
- **编辑模式下要按业务规则限制字段**，限制不了的要给用户说明原因。
- **离开提醒只在站内跳转生效**，关闭标签页要用 `beforeunload`，且不能自定义文案。
- **两次请求不是原子的**，能合并到后端一个接口就合并；不能的话，提示要说清楚发生了什么。

## 常见坑

::: details 点提交什么反应都没有
**现象**：填完表单点提交，页面没反应，控制台也没有明显报错。

**原因**：有三种可能，按概率排序。

**一、校验没通过但错误提示看不见。** 表单字段多、页面长，报错的字段在上面一屏之外。`el-form` 会自动滚动到第一个错误字段，但如果你的表单在 `el-dialog` 里，滚动可能失效。

**二、`validator` 里忘了调用 `callback`。**

```js
// ✗ 校验永远挂着
validator: (rule, value, callback) => {
  if (value > 10) {
    callback(new Error('不能大于 10'))
  }
  // 通过时没有 callback()，Promise 永远不 resolve
}
```

**三、`validate()` 没有 `await`。** 不 await 的话，校验是异步的，后面的提交代码立刻执行，而校验结果被丢掉了。

```js
// ✗
formRef.value.validate()
await createActivity(form)

// ✓
await formRef.value.validate()
await createActivity(form)
```

**怎么处理**：先在 `validate()` 后面加一行 `console.log('校验通过')`，看有没有打出来。没打出来就是校验失败，把校验规则逐条检查。
:::

::: details 提交成功了，但创建了两条一样的数据
**现象**：用户手机上网络慢，点了两次提交，列表里出现两条一样的数据。

**原因**：按钮的 loading 状态没配，或者用户用了回车提交。

**怎么处理**：三层防护一起上。

**第一层**：按钮绑 `:loading="submitting"`。

**第二层**：函数开头加判断。

```js
if (submitting.value) return
```

**第三层**：**最重要的一层在后端。** 后端应该用“幂等键”或唯一约束来防止重复创建。前端的防护是体验优化，网络层的重复请求前端拦不住。

**这就是为什么说“前端的所有校验都要在后端再做一遍”。** 前端拦的是“用户手快”，后端拦的是“真的重复了”。
:::

::: details 编辑时改了 id，保存到了错误的活动
**现象**：从活动 42 的编辑页返回列表，再进活动 43 的编辑页，保存时改的是 42。

**原因**：`ActivityForm.vue` 被复用，组件没有重新创建，而 `onMounted` 只执行一次。

**怎么处理**：上一节 11.3 里已经处理了 —— 布局里给 `<component :is="Component" :key="route.path" />` 加了 `:key`。路径变化时组件重建，`onMounted` 重新执行。

**另一种情况**：如果在同一个页面内切换 id（比如页面上有个“下一条”按钮），`route.path` 也会变，组件重建。这是对的行为。

**如果你不想让组件重建**（想保留一些状态），就要用 `watch` 监听 id 变化：

```js
watch(activityId, async (id) => {
  if (!id) return
  const { data } = await getActivityDetail(id)
  Object.assign(form, data)
}, { immediate: true })
```

**注意 `immediate: true`**，它让 `watch` 在初始化时也执行一次，替代 `onMounted` 里的逻辑。**这两种写法选一种，不要两个都写，否则会请求两次。**
:::

::: details 表单数据模型里的字段和接口返回的字段名对不上
**现象**：编辑模式下拉到的详情数据回填不了，字段全是空的。

**原因**：接口返回的字段名和表单的字段名不一致。比如接口返回 `signupDeadLine`（大写 L），前端写的是 `signupDeadline`。

**怎么处理**：有两处地方容易出错。

**第一次核对**：从接口文档抄字段名时抄错了。**抄完之后对着接口文档逐字比对一遍**，这个动作花两分钟，能省掉半小时调试。

**第二层防护**：在编辑页的回填代码里打出日志：

```js
onMounted(async () => {
  const { data } = await getActivityDetail(activityId.value)
  console.log('详情原始数据', data)   // ← 调试完删掉
  Object.assign(form, data)
})
```

**第三层防护**：如果后端字段名确实和前端不一样（比如后端用下划线风格 `signup_deadline`），就要在 `api` 层做一次转换，**不要把转换逻辑散在组件里**。

```js [src/api/activity.js]
/** 后端字段 → 前端字段 */
function toModel(raw) {
  return {
    id: raw.id,
    title: raw.title,
    type: raw.type,
    quota: raw.quota,
    signupDeadline: raw.signup_deadline,
    description: raw.description
  }
}

/** 前端字段 → 后端字段 */
function toPayload(model) {
  return {
    title: model.title,
    type: model.type,
    quota: model.quota,
    signup_deadline: model.signupDeadline,
    description: model.description
  }
}
```

调用处：

```js
export async function getActivityDetail(id) {
  const { data } = await request.get(`/activities/${id}`)
  return toModel(data)
}

export async function createActivity(form) {
  return request.post('/activities', toPayload(form))
}
```

**这样做的好处是转换逻辑只有一处，改了字段名只改这两个函数。** 代价是多了一层映射代码，小项目可能觉得啰嗦。**判断标准：字段名风格差得多、或者字段数量超过 10 个，就值得加这层。**
:::

::: details `el-input-number` 允许输入小数
**现象**：名额输入框里输入了 `2.5`，提交后数据库里是 2.5。

**原因**：`el-input-number` 默认允许小数。

**怎么处理**：配 `:precision="0"` 或者 `:step-strictly="true"`。

```vue
<el-input-number v-model="form.quota" :min="1" :max="2000" :precision="0" />
```

**但注意 `:precision="0"` 只影响 UI。** 用户仍然可能通过其他方式传入小数（比如后端接口直接调用）。所以：

- `quota` 规则里加 `Number.isInteger(value)` 判断（上面代码里已经有）。
- 后端用 `int` 类型接收，或者自己校验。

**三者缺一不可。** 前端 UI 限制 → 前端校验 → 后端校验，层层往后兜。
:::

::: details 表单校验通过了，但提交后后端说参数不对
**现象**：前端校验全过，提交后返回 400，说缺少必填参数。

**原因**：通常是三类。

**一、字段名不匹配。** 见上一条。

**二、多传了后端不认识的字段。** 比如表单对象里带了 `approvedCount`、`createdAt` 这些只读字段。**后端如果配了严格模式会直接报错。**

**怎么处理**：提交时只挑要传的字段：

```js
const payload = {
  title: form.title,
  type: form.type,
  quota: form.quota,
  signupDeadline: form.signupDeadline,
  description: form.description
}
```

**不要直接 `...form`**，除非表单对象的字段和接口字段完全一致。

**三、格式不对。** 日期传了 `Date` 对象、布尔传了 `"false"` 字符串、数字传了 `"50"` 字符串。

**怎么处理**：提交前打日志看实际发出去的请求体。Chrome 开发者工具 → Network → 找到请求 → Payload 标签页，**这是排查参数问题最快的办法**。
:::

## 课后练习

::: details 练习 1：把“新增场地”表单写出来
场地只有一个实体，字段更少：名称、容量、位置、备注。写一个 `VenueForm.vue`。

**思路提示**：

- 场地名称要唯一。前端的做法是先查一遍（`GET /api/venues?keyword=xxx` 看有没有同名的），但**这不是可靠的** —— 两个人同时创建同名场地，都查不到，都提交成功。真正的唯一约束必须靠后端数据库的唯一索引。
- 前端的查重是“体验优化”：让用户尽早知道。要把它写成 `validator` 返回 Promise 的形式（见这一节的第三种校验写法）。
- 容量用 `el-input-number`，加 `:precision="0"`。
- **做完之后想一想**：如果后端没有提供查重接口，你还做这个校验吗？（提示：不做。宁可让后端返回唯一约束冲突的错误，也不要自己造一个不可靠的检查）
:::

::: details 练习 2：给活动表单加上“分步”
活动表单的字段如果继续增加（比如加上报名资格、联系方式、附件），一屏放不下，就该分步了。

**思路提示**：

- 分步表单的完整实现见[案例 07 · 多步表单](/cases/07-wizard)。
- 核心是“每一步的字段抽出来单独校验”：`formRef.value.validateField(['title', 'type'])` —— `validateField` 接收字段名数组，只校验这几个。
- 注意每步的字段数组要和 `el-form-item` 的 `prop` 对上。
- **做完之后回答一个问题**：分步表单真的比一屏长表单好用吗？（提示：分步适合有很多字段、且字段之间有逻辑分组的情况。字段少于 10 个时分步反而增加操作成本，因为用户看不到全貌）
:::

::: details 练习 3：给表单加草稿自动保存
用户填到一半切走了，回来还能接着填。

**思路提示**：

- 用 `useLocalStorage` 把 `form` 存到本地，加一个防抖（每 2 秒最多存一次）。
- 键名里带上用户 id 和活动 id，否则不同人、不同活动的草稿会互相覆盖：

```js
const draftKey = computed(() =>
  `activity-draft:${userStore.userId}:${activityId.value ?? 'new'}`
)
```

- 进页面时：有草稿就问用户“发现上次未提交的内容，是否恢复？”，**不要自动恢复** —— 用户可能故意放弃了那份草稿。
- 提交成功或用户点了取消后，要清掉本地草稿。
- **做完之后想一想**：草稿里如果包含了敏感信息（比如学生手机号），存 `localStorage` 合适吗？（提示：`localStorage` 没有加密，同一台电脑的其他人都能读到。敏感数据不该存本地）
:::

::: details 练习 4：找出这段提交代码的三个问题
```js
const submitting = ref(false)

async function handleSubmit() {
  submitting.value = true
  await formRef.value.validate()
  await createActivity(form)
  submitting.value = false
  ElMessage.success('创建成功')
  router.push('/activity')
}
```

**思路提示**：

想三个方向：① `validate()` 失败了会怎样？（提示：会 reject，后面的代码全部中断，`submitting` 永远停在 true）② 提交失败了会怎样？③ 用户连点两次会发生什么？

**改完之后对照这一节“提交：三个必须做的事”检查。**
:::

---

上一节：[11.4 列表页标准做法](/unit11/04-list-page) · 下一节：[课后练习](/unit11/practice)
