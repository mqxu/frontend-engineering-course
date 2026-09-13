# 7.4 组件上的 v-model

## 为什么 `<input>` 上的 `v-model` 到组件上就“不一样”了

在[6.3](/unit06/03-form-binding)里讲过，`v-model` 是语法糖：

```vue [原生元素上的 v-model]
<input v-model="text" />
<!-- 展开后 -->
<input :value="text" @input="text = $event.target.value" />
```

那组件上能不能也这么写？

```vue [父组件]
<ActivitySearchBox v-model="keyword" />
```

可以。但有个关键差别：**组件不是 DOM 元素，它没有 `value` 属性和 `input` 事件。**
Vue 必须约定“用哪个属性、哪个事件来实现双向绑定”。这个约定就是：

> **属性 `modelValue` + 事件 `update:modelValue`**

记住这一对名字，组件上的 `v-model` 就不再是黑箱。

## 本质：一对属性与事件的约定

### 并排对比

```vue [父组件：用 v-model]
<script setup>
import { ref } from 'vue'
import ActivitySearchBox from '@/components/business/ActivitySearchBox.vue'

const keyword = ref('')
</script>

<template>
  <ActivitySearchBox v-model="keyword" />
</template>
```

上面这段和下面这段**完全等价**：

```vue [父组件：手动展开]
<script setup>
import { ref } from 'vue'
import ActivitySearchBox from '@/components/business/ActivitySearchBox.vue'

const keyword = ref('')
</script>

<template>
  <ActivitySearchBox
    :model-value="keyword"
    @update:model-value="keyword = $event"
  />
</template>
```

**`v-model="keyword"` 展开后是一行属性绑定加一行事件监听。**
属性把数据送进去，事件把新值送出来。

### 子组件怎么配合

```vue [src/components/business/ActivitySearchBox.vue]
<script setup>
const props = defineProps({
  // 名字必须是 modelValue
  modelValue: { type: String, default: '' }
})

const emit = defineEmits(['update:modelValue'])

function handleInput(e) {
  // 名字必须是 update:modelValue
  emit('update:modelValue', e.target.value)
}
</script>

<template>
  <input
    :value="modelValue"
    placeholder="搜索活动名称"
    @input="handleInput"
  />
</template>
```

把两侧的对应关系画出来：

```text [v-model 的对应关系]
父组件                          子组件
─────────────────────────────  ──────────────────────────────
v-model="keyword"
  │
  ├─ :model-value="keyword" ──▶  defineProps({ modelValue })
  │                                  │
  │                                  ▼
  │                              :value="modelValue"
  │
  └─ @update:model-value ─────◀──  emit('update:modelValue', v)
        keyword = $event
```

::: warning 为什么不能把 `modelValue` 改成别的名字
约定就是约定。你把属性改名叫 `keyword`，那么父组件的 `v-model` 就找不到 `modelValue`，
双向绑定失效 —— 属性传不进去，事件也没人接。

**如果想用自定义的名字，要用“具名 v-model”**，见下一小节。
:::

### 为什么子组件不能“直接改” `modelValue`

看下面这个错误写法：

```vue [✗ 错误示范]
<script setup>
const props = defineProps({ modelValue: { type: String, default: '' } })

function handleInput(e) {
  // 违反单向数据流，控制台会警告
  props.modelValue = e.target.value
}
</script>
```

即使名字叫 `modelValue`，它仍然是一个 `prop`，
**改它一样会触发“Set operation on ... failed: target is readonly”的警告，而且不生效。**

所以 `v-model` 从来没有打破单向数据流 —— 它只是把“`emit` 一个约定名字的事件”
这件事包装得更短。**数据依然是父组件改的。**

## 多个 v-model

一个组件要双向绑定多个值时，用**具名 v-model**：

```vue [父组件]
<script setup>
import { ref } from 'vue'
import ActivityEditor from '@/components/business/ActivityEditor.vue'

const title = ref('')
const status = ref('draft')
</script>

<template>
  <ActivityEditor v-model:title="title" v-model:status="status" />
</template>
```

展开后：

```vue [父组件：展开写法]
<ActivityEditor
  :title="title"
  @update:title="title = $event"
  :status="status"
  @update:status="status = $event"
/>
```

子组件相应地把属性名和事件名都改成带前缀的形式：

```vue [src/components/business/ActivityEditor.vue]
<script setup>
const props = defineProps({
  title: { type: String, default: '' },
  status: { type: String, default: 'draft' }
})

const emit = defineEmits(['update:title', 'update:status'])
</script>

<template>
  <input
    :value="title"
    @input="emit('update:title', $event.target.value)"
    placeholder="活动标题"
  />

  <select
    :value="status"
    @change="emit('update:status', $event.target.value)"
  >
    <option value="draft">草稿</option>
    <option value="enrolling">报名中</option>
  </select>
</template>
```

::: tip 多个 v-model 与“一个对象”怎么选
有两种设计：

```vue
<!-- 方案 A：多个 v-model -->
<ActivityEditor v-model:title="title" v-model:status="status" />

<!-- 方案 B：一个对象属性 -->
<ActivityEditor :form="form" @update:form="form = $event" />
```

**推荐方案 A。** 理由是方案 B 每次改动都会替换整个对象，
父组件没法知道“改的是 title 还是 status”，也就没法做精细的校验或者按字段发请求。

**方案 B 只在“这一组数据天然就该一起变化”时使用**，比如一次性导入的配置对象。
:::

## 自定义修饰符

原生元素上的 `v-model.trim`、`v-model.number`、`v-model.lazy` 是 Vue 内置的。
**组件上也可以接收自己定义修饰符**。

### 修饰符怎么传到子组件

父组件写：

```vue [父组件]
<ActivitySearchBox v-model.trim="keyword" />
```

子组件里会多收到一个属性 `modelModifiers`：

```js [子组件收到的属性（示意）]
{
  modelValue: '...',
  modelModifiers: { trim: true }
}
```

**修饰符的名字就是 `modelModifiers` 对象里的键。**

如果是具名 v-model，属性名变成“名字 + `Modifiers`”：

| 父组件写法 | 子组件收到的修饰符属性 |
| --- | --- |
| `v-model.trim` | `modelModifiers` |
| `v-model:title.trim` | `titleModifiers` |
| `v-model:status.lazy` | `statusModifiers` |

### 完整实现

```vue [src/components/business/ActivitySearchBox.vue]
<script setup>
const props = defineProps({
  modelValue: { type: String, default: '' },
  // ✓ 对象类型的 default 必须写成函数
  modelModifiers: { type: Object, default: () => ({}) }
})

const emit = defineEmits(['update:modelValue'])

function handleInput(e) {
  let value = e.target.value

  // 父组件写了 .trim，就替它去掉首尾空格
  if (props.modelModifiers.trim) {
    value = value.trim()
  }

  emit('update:modelValue', value)
}
</script>

<template>
  <input :value="modelValue" @input="handleInput" />
</template>
```

父组件照常用：

```vue [父组件]
<ActivitySearchBox v-model.trim="keyword" />
```

::: warning 修饰符是“约定”，不是自动生效的
Vue **不会**自动帮你对组件里的值做 trim。它只负责把 `{ trim: true }` 传进来，
**具体怎么处理要你自己写。**

这一点和原生元素上的 `v-model.trim` 不同 —— 那里是 Vue 内置的 `vModelText` 指令在处理。
:::

## `defineModel`：更省事的写法

Vue 3.4 加了一个编译宏 `defineModel`，把上面那套“声明属性 + 声明事件 + 写 emit”
三步压缩成一步。

### 基本用法

```vue [src/components/business/ActivitySearchBox.vue]
<script setup>
// 一行搞定：声明一个可读可写的双向绑定值
const model = defineModel({ type: String, default: '' })

function handleInput(e) {
  model.value = e.target.value // 赋值时自动 emit('update:modelValue', ...)
}
</script>

<template>
  <input :value="model" @input="handleInput" />
</template>
```

对比一下两种写法的工作量：

| 步骤 | 手动写法 | `defineModel` |
| --- | --- | --- |
| 声明属性 | `defineProps({ modelValue: ... })` | `defineModel({ ... })` |
| 声明事件 | `defineEmits(['update:modelValue'])` | 不用写 |
| 取值 | `props.modelValue` | `model.value` |
| 赋值 | `emit('update:modelValue', v)` | `model.value = v` |

### 具名与修饰符

```vue [src/components/business/ActivityEditor.vue]
<script setup>
// 具名 v-model：对应父组件的 v-model:title
const title = defineModel('title', { type: String, default: '' })

// 带修饰符：拿到的第二个值是修饰符对象
const [status, statusModifiers] = defineModel('status', {
  type: String,
  default: 'draft'
})

function onStatusChange(e) {
  let value = e.target.value
  if (statusModifiers.value.trim) value = value.trim()
  status.value = value
}
</script>
```

父组件照常写 `v-model:title="title"` 与 `v-model:status.trim="status"`。

::: tip `defineModel` 的版本要求
`defineModel` 是 **Vue 3.4 稳定**的。本课程基线是 Vue 3.5.42，可以直接用。

如果在 3.4 之前的项目里用，需要显式打开编译选项（`defineModel: true`），
而且早期版本里它是实验特性。**看项目版本决定用哪种写法。**
:::

::: warning 别把 `defineModel` 用成“万能属性”
`defineModel()` 只能处理**双向绑定**。用它传只读的展示数据是错的 ——
那应该用 `defineProps`。

见过这样的代码：一个组件声明了六个 `defineModel`，其中四个父组件从来不写回值。
**这不是双向绑定，是滥用。** 判断标准见下一小节。
:::

## 什么时候用 v-model，什么时候用属性和事件分开

这是本节最需要想清楚的一个设计决定。

### 决策依据：这个数据是“双向的”还是“只读的”

| 数据的性质 | 用什么 | 例子 |
| --- | --- | --- |
| **双向**：子组件会改它，改完父组件要接受 | `v-model` | 自定义输入框、开关、选择器、分页器的当前页 |
| **只读**：子组件只负责显示 | `props` | 表格的数据源、活动的状态、用户信息 |
| **单向触发**：子组件只是“请求”某个操作，本身不产生新值 | `emits` | 删除某一行、提交表单、取消 |

**一句话判断：父组件需要“收到新值并替换旧值”吗？**

- 需要，而且改动的含义很清楚（就是“这个值变了”）→ 用 `v-model`。
- 不需要（只是通知“发生了一件事”）→ 用 `emits`。

### 一个具体的比较

需求：一个搜索框组件，支持输入关键词、点搜索、点清空。

**方案一：全部用 v-model**

```vue [父组件]
<SearchBox v-model="keyword" v-model:searching="searching" />
```

问题：`searching` 是一个“有没有在搜索”的状态，父组件并不需要一个双向绑定的开关，
它只是想知道“用户点了搜索”。**用 `v-model` 表达“按钮被点了”是不合适的** ——
它是一个瞬时动作，不是一个持续的值。

**方案二：值用 v-model，动作用事件（推荐）**

```vue [父组件]
<SearchBox v-model="keyword" @search="onSearch" @clear="onClear" />
```

子组件的接口：

```js [src/components/business/SearchBox.vue]
const props = defineProps({ modelValue: { type: String, default: '' } })
const emit = defineEmits(['update:modelValue', 'search', 'clear'])
```

**“值”走 `v-model`，“动作”走事件。** 这条分界线在绝大多数场景下都成立。

### 一个反面例子：用 v-model 传整个表单对象

```vue [✗ 不推荐的写法]
<ActivityForm v-model="form" />
```

问题在于：父组件不知道子组件改了 `form` 的哪一部分。
如果父组件想“标题变了就重新查重”，它做不到 —— 它只看到整个对象被替换了。

**改法有两种**：

```vue [✓ 改法一：拆成多个具名 v-model]
<ActivityForm v-model:title="form.title" v-model:capacity="form.capacity" />

<!-- ✓ 改法二：值走 v-model，语义化动作用事件 -->
<ActivityForm :form="form" @field-change="onFieldChange" />
```

**判断标准：一个 `v-model` 背后的数据，能不能用一句话说清它是什么？**

- 能：“关键词”“当前页”“是否下架” → 适合 `v-model`。
- 不能：“表单”“所有配置” → 拆开。

## 小结

- 组件上的 `v-model` 是**属性 `modelValue` 加事件 `update:modelValue`** 的语法糖；
  父组件写一行，等价于 `:model-value` 加 `@update:model-value`。
- 子组件要声明 `modelValue` 属性与 `update:modelValue` 事件，**不能直接改属性**。
- 多个双向值用具名 v-model：`v-model:title` 对应 `:title` 加 `@update:title`。
- 自定义修饰符通过 `modelModifiers`（具名时是 `名字 + Modifiers`）传给子组件，
  **具体处理要自己写**。
- `defineModel` 是 3.4 起的编译宏，把声明属性、声明事件、写 `emit` 三步合成一步；
  具名写 `defineModel('title')`，修饰符用数组解构 `[model, modifiers]`。
- 决策依据：**值是双向的用 `v-model`，值是只读的用 `props`，
  只是通知一个动作用 `emits`**；不要把“按钮被点了”做成 `v-model`。

## 常见坑

::: details 坑 1：子组件没有 emit `update:modelValue`
**现象**：父组件用 `v-model`，子组件里输入框能打字，但父组件的值一直是空的。

**原因**：子组件只写了 `:value="modelValue"`，没有在输入时 `emit`。

**处理**：加上 `emit('update:modelValue', 新值)`，或者去掉 `:value` 直接让输入框自己维护
（但那样父组件的值就不同步了）。

**排查方法**：在父组件里 `watch` 一下那个值，看它变不变。不变就说明 emit 这一环断了。
:::

::: details 坑 2：`modelModifiers` 的默认值写成了对象字面量
**现象**：两个相同组件共用一个修饰符对象，一个组件上写的修饰符出现在另一个上。

**原因**：`default: {}` 让所有实例共享同一个对象。

**处理**：`default: () => ({})`。**所有对象、数组类型的属性默认值都要用函数返回。**
:::

::: details 坑 3：`defineModel` 里改了值但父组件没更新
**现象**：`model.value = 'x'` 之后子组件显示变了，父组件的变量没变。

**原因**：父组件没有用 `v-model` 接收，只写了 `:model-value`，那赋值时没有监听器接住。

**处理**：父组件要么用 `v-model`，要么显式写 `@update:model-value`。
**`defineModel` 只是替你把 emit 写好了，接不接还是父组件的事。**
:::

::: details 坑 4：给只读数据用了 `v-model`
**现象**：一个表格组件声明了 `defineModel('rows')`，但它从来不改 `rows`。

**原因**：把“只读数据”当成了双向绑定。

**处理**：改成 `defineProps`。**`v-model` 只用于子组件会改的数据。**
不用的 `v-model` 会让读代码的人以为“这里可能被改”，增加理解成本。
:::

::: details 坑 5：`v-model` 和 `:model-value` 一起写
**现象**：父组件写 `<Comp v-model="x" :model-value="y" />`，行为混乱。

**原因**：`v-model` 展开后本来就包含 `:model-value`，重复绑定会互相覆盖。

**处理**：二选一。**要不要用 `v-model`，是一个非此即彼的选择。**
:::

## 课后练习

::: details 练习 1：手写一个 `v-model` 组件
不用 `defineModel`，写一个 `CapacityInput.vue`：

- 父组件用 `v-model` 绑定名额数字
- 输入框失焦时把值收成合法数字（小于 1 就变成 1，大于 500 就变成 500）
- 输入过程中不修改用户输入

写出父组件与子组件两边的完整代码，并在注释里标出哪一行对应 `v-model` 的哪一部分。

**参考思路**：想想应该在哪个事件里做“收成合法数字”（提示：不是 `input`）。
收完之后要 `emit` 的还是原来的值吗？

:::

::: details 练习 2：给组件加一个自定义修饰符
给上面的 `CapacityInput` 加一个 `.positive` 修饰符，要求：父组件写了 `.positive`
时，负数一律变成 `1`；没写时不做这个处理。

**参考思路**：修饰符属性名是 `modelModifiers`。注意默认值要写成函数。
想清楚“判断修饰符”的代码写在哪一行，以及用了 `defineModel` 之后怎么拿修饰符。

:::

::: details 练习 3：判断这些接口设计得对不对
逐个判断，说明理由和改法：

```vue
<!-- A：分页器 -->
<Paginator v-model:page="page" :total="total" @page-change="load" />

<!-- B：模态框 -->
<Modal v-model:visible="showModal" title="确认下架" />

<!-- C：表格 -->
<DataTable v-model:rows="rows" :columns="columns" />

<!-- D：搜索栏 -->
<SearchBar v-model="keyword" v-model:focus="focused" @search="onSearch" />
```

**参考思路**：A 里 `v-model:page` 与 `@page-change` 是重复的（想想展开后是什么）；
B 是对的，但可以想一想“点击遮罩关闭”要不要也变成 `v-model`；
C 里 `rows` 是只读数据，不该用 `v-model`；D 里 `focus` 是不是一个“值”，
还是一个瞬时状态。

:::

::: details 练习 4：把 `defineModel` 版本改写成手动版本
把下面这段改写成不用 `defineModel` 的写法，保持行为完全一致。

```vue
<script setup>
const title = defineModel('title', { type: String, default: '' })
const status = defineModel('status', { type: String, default: 'draft' })
</script>
```

**参考思路**：改完之后回答两个问题：代码量增加了多少？可读性有没有变差？
**理解手动写法是必要的**，因为你会在别人的项目里看到大量这种代码；
但在新项目里，`defineModel` 更简洁。
:::

---

上一节：[7.3 父子通信：emits](/unit07/03-emits) ·
下一节：[案例 03 · 树状视图与递归组件](/unit07/05-case-tree)
