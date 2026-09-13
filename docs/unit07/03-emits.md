# 7.3 父子通信：emits

## 一个“点了没反应”的提交按钮

审核页拆出了 `ReviewForm.vue`，负责填写审核意见并提交。子组件里这么写：

```vue [src/components/business/ReviewForm.vue（有问题）]
<script setup>
function submit() {
  // 把审核结果抛给父组件
  emit('submitReview', { result: 'approved', comment: '材料齐全' })
}
</script>
```

父组件这么听：

```vue [src/views/SignupReviewView.vue（有问题）]
<template>
  <!-- ✗ 监听不到 -->
  <ReviewForm @submit-review="onReviewSubmit" />
</template>
```

点按钮，什么也没发生。父组件的 `onReviewSubmit` 一次都没执行，控制台也没有任何报错。

`emit('submitReview')` 与 `@submit-review` 对不上 —— 这就是本节要讲清楚的第一件事。

## 声明与触发

### `defineEmits` 声明

在 `<script setup>` 里用 `defineEmits` 声明这个组件会发出哪些事件：

```vue [src/components/business/ReviewForm.vue]
<script setup>
// ✓ 先声明，再触发
const emit = defineEmits(['submit-review', 'cancel'])
</script>
```

声明有两个作用：

1. **告诉使用方**这个组件会发什么事件（组件接口的一半）。
2. **告诉 Vue 这些是自定义事件**，不是要透传到根元素上的原生属性。

然后用 `emit` 触发：

```vue [src/components/business/ReviewForm.vue]
<script setup>
const emit = defineEmits(['submit-review', 'cancel'])

function handleSubmit() {
  emit('submit-review', { result: 'approved', comment: '材料齐全' })
}

function handleCancel() {
  emit('cancel')
}
</script>
```

### 不声明会怎样

`defineEmits` 是可以不写的。不写时，`emit` 依然能用（在模板里可以用 `$emit`），
但会带来两个问题：

| 问题 | 表现 |
| --- | --- |
| 使用方看不出有哪些事件 | 只能读子组件源码去找 `emit(` 调用 |
| 没有校验 | 事件名写错了，也没有任何提示 |

::: tip 一个能帮你排查问题的警告
如果声明了 `defineEmits(['submit-review'])`，但代码里调用了 `emit('submmit-review')`
（拼错了一个字母），Vue 在开发环境会给出警告，大意是：

```text [控制台输出]
[Vue warn] Component emitted event "submmit-review" but it is neither declared in
the emits option nor as an "onSubmmitReview" prop.
```

**这是排查“事件发不出去”的第一条线索。** 看到这个警告就去核对名字。
:::

## 事件名怎么写：一个必须搞清的规则

### 规则只有一条：名字要一模一样

`emit` 里的字符串和模板里 `@` 后面的名字，**必须完全对应**。

| 子组件里写 | 父组件里要写 | 能不能听到 |
| --- | --- | --- |
| `emit('submit-review')` | `@submit-review` | ✓ 能 |
| `emit('submit-review')` | `@submitReview` | ✓ 能 |
| `emit('submitReview')` | `@submitReview` | ✓ 能 |
| `emit('submitReview')` | `@submit-review` | ✗ **听不到** |

第一行到第三行能通，第四行通不了。原因是 Vue 在匹配时会做一次“从连字符转驼峰”的尝试，
但**不会做反向的“从驼峰转连字符”**。

::: danger 结论：事件名统一用 kebab-case
```js [✓ 推荐]
emit('submit-review')
emit('status-change', newStatus)
emit('row-select', row)
```

```js [✗ 不推荐]
emit('submitReview')
```

原因不只是“上面那张表”的第三条能通。更关键的是**HTML 属性名不区分大小写**：
一旦组件被用在 DOM 模板里（比如直接写在 `index.html` 里），
`@submitReview` 会被浏览器统一转成小写的 `@submitreview`，
此时子组件的 `emit('submitReview')` 就再也匹配不上了。

**用 kebab-case，就不用去想“这里行不行”。**
:::

### 为什么 `emit('update:modelValue')` 对应 `@update:modelValue`

有同学会问：既然要把驼峰转成连字符，那 `update:modelValue` 里的 `modelValue`
为什么不写成 `model-value`？

答案是：**这一条不属于上面那套规则。** `update:modelValue` 是一个固定约定，
它的两个部分各有含义：

| 部分 | 含义 |
| --- | --- |
| `update` | 事件类型前缀，表示“要更新某个值” |
| `:` | 分隔符 |
| `modelValue` | 要更新的那个属性的名字 |

它对应的是组件属性 `modelValue`。所以：

```vue [子组件]
<script setup>
const props = defineProps({ modelValue: { type: String, default: '' } })
const emit = defineEmits(['update:modelValue'])

function onInput(e) {
  // ✓ 名字必须是 update: + 属性名
  emit('update:modelValue', e.target.value)
}
</script>
```

```vue [父组件]
<template>
  <!-- 两种写法完全等价 -->
  <MyInput @update:model-value="text = $event" />
  <MyInput v-model="text" />
</template>
```

`v-model` 就是 `@update:modelValue` 加 `:modelValue` 的简写。这套机制在
[7.4](/unit07/04-vmodel)里展开。

::: warning 别把 `update:modelValue` 写成 `update:model-value`
`modelValue` 是**属性的名字**，要用驼峰写。写成 `model-value` 之后，
Vue 会去找 `modelValue` 这个属性去匹配，结果对不上。

**记住：`:` 前面是“干什么”，`:` 后面是“改哪个属性”，属性名用驼峰。**
:::

## 事件带参数

事件可以带任意多个参数：

```vue [src/components/business/SignupTable.vue]
<script setup>
const emit = defineEmits(['row-select', 'sort-change', 'batch-approve'])

// 一个参数
function selectRow(row) {
  emit('row-select', row)
}

// 两个参数
function changeSort(key, order) {
  emit('sort-change', key, order)
}

// 带一个对象（推荐）
function batchApprove(ids) {
  emit('batch-approve', { ids, operator: 'current-user' })
}
</script>
```

父组件里收：

```vue [src/views/SignupReviewView.vue]
<script setup>
function onSortChange(key, order) {
  // ✓ 多个参数按顺序接收
  console.log('按', key, order, '排序')
}

function onBatchApprove(payload) {
  // ✓ 一个对象参数，取出时一目了然
  batchApprove(payload.ids, payload.operator)
}
</script>

<template>
  <SignupTable @sort-change="onSortChange" @batch-approve="onBatchApprove" />
</template>
```

::: tip 参数超过一个就打包成对象
和[6.1 里事件处理函数](/unit06/01-events)的建议一样：**参数超过一个，
打包成一个对象传。**

对比一下：

```js
// 一般：接收方要数参数位置
emit('sort-change', key, order)

// 更好：接收方一眼看出每个值是什么
emit('sort-change', { key, order })
```

多参数的形式还有一个隐患：将来想在中间插入一个参数，所有监听处都要改。
对象形式加字段不影响已有代码。
:::

## 事件的校验

`defineEmits` 也可以用对象形式，给每个事件配一个校验函数：

```vue [src/components/business/SignupTable.vue]
<script setup>
const emit = defineEmits({
  // 不校验，写 null 或直接省略
  'row-select': null,

  // 校验：必须有 ids 且不能是空数组
  'batch-approve': (payload) => {
    if (!payload || !Array.isArray(payload.ids) || payload.ids.length === 0) {
      console.warn('[SignupTable] batch-approve 需要传入非空的 ids 数组')
      return false
    }
    return true
  }
})
</script>
```

校验函数返回 `false` 时，Vue 在开发环境会打印警告，**但事件依然会发出**。
校验的价值是**在开发阶段帮你发现用错了接口**，不是拦截。

::: warning 校验函数只在开发环境生效
生产构建时校验代码会被去掉，不影响运行性能。所以可以放心地写详细一点 ——
它是给你自己用的。
:::

## 完整的父子通信流程

把 props 和 emits 合起来看，一条完整的数据链路是这样的：

```text [子组件提交表单 → 父组件发请求]
┌─────────────────────────────────────────────────────────┐
│ 父组件 SignupReviewView                                   │
│                                                          │
│  const formData = ref({...})     ← 数据在这里              │
│  async function onReviewSubmit(payload) {                │
│    await submitReview(payload)   ← 请求在这里发             │
│  }                                                       │
└───────────────┬─────────────────────────▲───────────────┘
                │ props 往下传              │ emit 往上抛
                │ :signup="current"        │ @submit-review
                ▼                          │
┌─────────────────────────────────────────────────────────┐
│ 子组件 ReviewForm                                         │
│                                                          │
│  props.signup        ← 只读，用来显示                      │
│  emit('submit-review', payload)  ← 只负责收集与通知         │
└─────────────────────────────────────────────────────────┘
```

**职责划分**：子组件负责“收集用户的输入并校验”，父组件负责“持有数据和发请求”。

```vue [src/components/business/ReviewForm.vue]
<script setup>
import { ref } from 'vue'

const props = defineProps({
  signup: { type: Object, required: true }
})

const emit = defineEmits(['submit-review', 'cancel'])

const result = ref('approved')
const comment = ref('')
const error = ref('')

function handleSubmit() {
  // 子组件只做与“输入”有关的校验
  if (result.value === 'rejected' && comment.value.trim() === '') {
    error.value = '驳回时必须填写理由'
    return
  }
  error.value = ''

  // 通知父组件：数据收集好了，请你处理
  emit('submit-review', {
    signupId: props.signup.id,
    result: result.value,
    comment: comment.value.trim()
  })
}
</script>

<template>
  <form @submit.prevent="handleSubmit">
    <p>报名学生：{{ signup.studentName }}（{{ signup.studentId }}）</p>

    <label>
      <input type="radio" v-model="result" value="approved" />
      通过
    </label>
    <label>
      <input type="radio" v-model="result" value="rejected" />
      驳回
    </label>

    <textarea v-model="comment" placeholder="审核意见"></textarea>
    <p v-if="error" class="field-error">{{ error }}</p>

    <button type="submit">提交审核</button>
    <button type="button" @click="emit('cancel')">取消</button>
  </form>
</template>
```

父组件：

```vue [src/views/SignupReviewView.vue]
<script setup>
import { ref } from 'vue'
import ReviewForm from '@/components/business/ReviewForm.vue'
import { submitReview } from '@/api/signup'
import { message } from '@/utils/message' // 假设的全局提示

const current = ref(null)
const submitting = ref(false)

async function onReviewSubmit(payload) {
  // ✓ 发请求是父组件的事
  if (submitting.value) return
  submitting.value = true
  try {
    await submitReview(payload)
    message.success('审核完成')
    current.value = null
  } catch (e) {
    message.error(e.message || '审核失败')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <ReviewForm
    v-if="current"
    :signup="current"
    @submit-review="onReviewSubmit"
    @cancel="current = null"
  />
</template>
```

::: tip 为什么不把请求写在子组件里
子组件不知道“审核成功后要关掉表单、要刷新列表”。这些是**页面的编排逻辑**，
属于父组件的职责。

子组件如果自己去发请求，它就必须知道接口地址、成功提示、失败处理、
以及之后要通知谁 —— 它就不再是一个“可复用组件”，而是“只能在这个页面用的专用组件”。

**判断标准：这段逻辑换个页面还用得上吗？** 用得上留在子组件，用不上交给父组件。
:::

## 排查：事件发了但监听没反应

这是本单元最花时间的一类问题。给一套排查顺序。

| 步骤 | 检查什么 | 怎么看 |
| --- | --- | --- |
| 1 | 子组件的 `emit` 有没有被执行 | 在 `emit` 前一行加 `console.log` |
| 2 | 事件名拼写 | 对照 `defineEmits` 的声明，逐字符核对 |
| 3 | 事件名的大小写形式 | 统一改成 kebab-case |
| 4 | 有没有“未声明事件”的警告 | 看控制台 `[Vue warn]` |
| 5 | 父组件的监听器是不是挂上了 | Devtools 里看组件的 `onXxx` 属性 |
| 6 | 监听器的函数本身有没有报错 | 看执行时有没有异常 |

### 第 5 步怎么看

打开 Vue Devtools，选中父组件，看它的属性列表里有没有 `onSubmitReview` 这样的项
（`@submit-review` 在内部对应的属性名是 `onSubmitReview`）。

- **有** → 监听器挂上了，问题在子组件那边（事件没发出来，或名字不对）。
- **没有** → 问题在父组件这边（模板写错、组件没渲染、写在了错误的标签上）。

新版 Vue Devtools 的**时间线（Timeline）**面板里有 Events 图层，
能直接看到每个事件的触发时刻和携带的参数。**这是排查事件问题最快的工具**，
比到处加 `console.log` 有效率得多。

::: warning 监听器名写错时控制台不会报错
`@submmit-review`（多了一个 m）不会触发任何警告，因为在 Vue 看来，
这只是父组件声明了一个**没人用的属性**，完全合法。

**不报错不等于写对了。** 这类问题的排查必须靠“核对名字 + 看 Devtools”。
:::

### 一个容易被忽略的“假故障”

```vue [✗ 监听器挂在了错误的地方]
<template>
  <div @submit-review="onSubmit">
    <ReviewForm />
  </div>
</template>
```

事件是从 `ReviewForm` 发出的，监听器挂在它的父级 `div` 上 —— **子组件的事件不会冒泡到父组件**。
组件事件只在“发出它的那个组件”和“使用它的那个组件的模板”之间传递，不经过 DOM 树。

**处理**：监听器必须写在组件标签上。

## 小结

- 用 `defineEmits(['a', 'b'])` 声明事件，再用返回的 `emit` 触发。
- **`emit` 的名字与模板里 `@` 后面的名字必须对应**；`emit('submitReview')` 用
  `@submit-review` 是听不到的。**统一用 kebab-case。**
- `update:modelValue` 是固定约定，`:` 后面是被更新的**属性名**，用驼峰写。
- 事件参数超过一个就打包成对象传递。
- 对象形式的 `defineEmits` 可以给事件加校验函数，只在开发环境生效。
- 职责划分：**子组件收集输入并做输入相关校验，父组件持有数据并发请求。**
- 排查“事件没反应”的顺序：看 `emit` 有没有执行、核对名字、看未声明事件的警告、
  在 Devtools 里查 `onXxx` 属性、检查监听器有没有挂在错误的标签上。
- **监听器名写错不会报错**，必须靠核对与 Devtools。

## 常见坑

::: details 坑 1：驼峰事件名配连字符监听
**现象**：`emit('submitReview')` 配 `@submit-review`，点按钮没反应，也没有警告。

**原因**：Vue 会把连字符形式转成驼峰去匹配，但不会把驼峰转成连字符。

**处理**：两边统一用 kebab-case：`emit('submit-review')` 配 `@submit-review`。
:::

::: details 坑 2：`emit` 拼写错误
**现象**：`emit('submmit-review')`，父组件监听的是 `@submit-review`，没反应。

**原因**：名字对不上。

**处理**：声明了 `defineEmits` 之后，Vue 会对“发出未声明事件”给出警告。
**看到 `[Vue warn] Component emitted event ... but it is neither declared` 就去核对拼写。**
:::

::: details 坑 3：在子组件里用了 `this.$emit`
**现象**：`<script setup>` 里写 `this.$emit('cancel')`，报 `this is undefined`。

**原因**：`<script setup>` 里没有组件实例的 `this`。

**处理**：用 `defineEmits` 的返回值：
```js
const emit = defineEmits(['cancel'])
emit('cancel')
```
模板里如果需要，可以用 `$emit('cancel')`，但更推荐统一走声明好的 `emit`。
:::

::: details 坑 4：事件名带了 `on` 前缀
**现象**：`emit('onSubmit')`，父组件写 `@on-submit`，听不到。

**原因**：`on` 前缀是 Vue 内部把事件转成属性名时加的，**写事件名时不要带**。

**处理**：事件名就是 `submit`，父组件监听 `@submit`（或 `@submit-x` 这种业务化的名字）。
**事件名用“发生了什么”，不要用“监听到之后要干嘛”。**
:::

::: details 坑 5：v-model 和 `update:modelValue` 同时写
**现象**：父组件既写 `v-model="text"` 又写 `@update:model-value="text = $event"`，
行为变得奇怪。

**原因**：两者是同一个东西，重复绑定会让赋值发生两次。

**处理**：二选一。要双向绑定用 `v-model`，要自己控制赋值时机就写 `:model-value` + `@update:model-value`。
:::

## 课后练习

::: details 练习 1：把事件名改对
下面四组写法，哪些能正常工作？不能的请改对。

```vue
<!-- A -->
<Child @status-change="onChange" />
<!-- 子组件： --> emit('statusChange', s)

<!-- B -->
<Child @row-select="onSelect" />
<!-- 子组件： --> emit('rowSelect', row)

<!-- C -->
<Child @update:model-value="v = $event" />
<!-- 子组件： --> emit('update:modelValue', v)

<!-- D -->
<Child @cancel="onCancel" />
<!-- 子组件： --> emit('onCancel')
```

**参考思路**：A 与 B 的问题一样 —— 驼峰 emit 配连字符监听。
C 想想“kebab 与驼峰哪种形式能互相匹配”。D 想想 `on` 前缀该不该写。
**四组里有三组需要改。**

:::

::: details 练习 2：给搜索栏组件设计事件
设计 `ActivitySearchBar.vue` 的接口，它的功能是：输入关键词、选择活动状态、
点搜索、点重置。

要求写出：

1. `defineProps` 的属性表（哪些是外部传进来的）
2. `defineEmits` 的事件表（每个事件带什么参数）
3. 每一条“为什么放在属性里 / 为什么用事件抛出去”的理由

**参考思路**：先想“哪些数据是父组件必须知道的”。
输入到一半的关键词要不要抛出去？点了搜索才抛，还是每敲一个字都抛？
**这个决定会影响接口设计，先想清楚再写。** 如果每敲一个字就抛，
父组件要负责防抖；如果只在点搜索时抛，防抖就可以留在子组件里。

:::

::: details 练习 3：写一个“确认对话框”组件
需求：一个二次确认弹窗，父组件这样用：

```vue
<ConfirmDialog
  v-if="showConfirm"
  title="确认下架该活动？"
  content="下架后学生将无法查看报名入口。"
  @confirm="doOffline"
  @cancel="showConfirm = false"
/>
```

要求：

1. 写出完整的 `defineProps` 与 `defineEmits`。
2. `confirm` 事件要不要带参数？如果父组件需要知道“用户有没有勾选‘同时通知已报名学生’”呢？
3. 用对象形式的 `defineEmits` 给某个事件加一个校验函数。

**参考思路**：第 2 问涉及一个设计选择 —— 是把勾选状态放在父组件里（属性传下来），
还是放在子组件里（通过事件参数抛上去）。两种都可以，**说明你的理由**。

:::

---

上一节：[7.2 父子通信：props](/unit07/02-props) ·
下一节：[7.4 组件上的 v-model](/unit07/04-vmodel)
