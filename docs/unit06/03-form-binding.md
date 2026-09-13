# 6.3 表单绑定

## 一个“勾一个全勾上”的复选框

做活动类型筛选时，有这么一段代码：

```vue [src/components/TypeFilter.vue]
<script setup>
import { ref } from 'vue'

// ✗ 一开始想的是“用户选了哪些类型”，但初始值写成了 null
const selectedTypes = ref(null)
</script>

<template>
  <label><input type="checkbox" v-model="selectedTypes" value="lecture" /> 讲座</label>
  <label><input type="checkbox" v-model="selectedTypes" value="sports" /> 体育</label>
  <label><input type="checkbox" v-model="selectedTypes" value="arts" /> 文艺</label>

  <p>已选：{{ selectedTypes }}</p>
</template>
```

现象是：**勾“讲座”，三个全被勾上了；再点一次“体育”，三个全取消了。**

原因在于第二行那个 `null`。多个复选框共用一个 `v-model` 时，Vue 需要把选中的值**收集到一个数组里**。
如果绑的不是数组，它就按“单个复选框”的规则处理：勾选 → 把值设成 `true`；三个复选框都判断
“我的 `true` 值等于模型值吗”，于是全部点亮。

改成数组初值就好了：

```vue [src/components/TypeFilter.vue]
<script setup>
import { ref } from 'vue'

// ✓ 多个复选框共用 v-model，初始值必须是数组
const selectedTypes = ref([])
</script>
```

这一节把 `v-model` 在不同表单元素上的形态逐个讲清楚，重点就是**取值类型**。

## 一张表记住所有形态

`v-model` 的神奇之处在于：写法几乎一样，但**绑定出来的值类型完全不同**。
先看总表，后面逐个解释。

| 元素 | 写法 | 绑定的值类型 | 举例 |
| --- | --- | --- | --- |
| 单行文本 | `<input type="text" v-model="name">` | `string` | `'校园歌手大赛'` |
| 多行文本 | `<textarea v-model="desc">` | `string` | `'面向全校学生…'` |
| 密码框 | `<input type="password" v-model="pwd">` | `string` | `'••••••'` |
| 单个复选框 | `<input type="checkbox" v-model="agreed">` | `boolean` | `true` / `false` |
| 多个复选框 | `<input type="checkbox" v-model="types" value="lecture">` | 数组 | `['lecture', 'arts']` |
| 单选框 | `<input type="radio" v-model="role" value="reviewer">` | `string` | `'reviewer'` |
| 下拉单选 | `<select v-model="type">` | `string` | `'sports'` |
| 下拉多选 | `<select v-model="types" multiple>` | 数组 | `['lecture', 'sports']` |

::: tip 记表的方法
只看两件事：
1. **能不能同时选多个** —— 能（多复选框、多选下拉、复选框组）就是数组。
2. **单选的是什么内容** —— 单复选框是“勾没勾”这个状态，所以是布尔值；其他的都是选项的值，所以是字符串。
:::

## 逐类展开

### 文本类：单行、多行、密码

这三类最简单，值永远是字符串：

```vue [src/components/ActivityBasicForm.vue]
<script setup>
import { ref } from 'vue'

const title = ref('')
const description = ref('')
const password = ref('')
</script>

<template>
  <label>活动标题</label>
  <input v-model="title" placeholder="不超过 30 个字" />

  <label>活动简介</label>
  <textarea v-model="description" rows="4"></textarea>

  <label>管理密码</label>
  <input type="password" v-model="password" />
</template>
```

::: warning 一个必须记住的差别：`<textarea>` 不用写内容
原生 HTML 里，多行文本框的初始内容写在标签中间：

```html
<!-- ✗ Vue 里不要这么写，会报错或行为异常 -->
<textarea>{{ description }}</textarea>
<textarea v-model="description">这里的内容会被忽略</textarea>
```

Vue 里一律用 `v-model`，**标签内容不要写**。这是模板编译时的一个硬性约定。
:::

### 单个复选框：布尔值

用于“同意条款”“是否下架”这类是非判断：

```vue [src/components/AgreementCheck.vue]
<script setup>
import { ref } from 'vue'

const agreed = ref(false)
</script>

<template>
  <label>
    <input type="checkbox" v-model="agreed" />
    我已阅读并同意《活动报名须知》
  </label>

  <button :disabled="!agreed">提交报名</button>
</template>
```

`:disabled="!agreed"` 这行是表单里最常见的联动：**没勾同意就不让提交。**

如果想让布尔值对应具体的业务值（比如提交时要传 `'Y'` 和 `'N'`），用 `true-value` / `false-value`：

```vue [src/components/PublishedToggle.vue]
<script setup>
import { ref } from 'vue'

const published = ref('N')
</script>

<template>
  <input type="checkbox" v-model="published" true-value="Y" false-value="N" />
  <!-- 勾选后 published 是 'Y'，取消后是 'N' -->
</template>
```

### 多个复选框：数组

用于“选择多个活动类型”。关键是**给每个复选框一个 `value`**，Vue 会把勾上的那些 `value` 收集进数组：

```vue [src/components/TypeFilter.vue]
<script setup>
import { ref } from 'vue'

const allTypes = [
  { value: 'lecture', label: '讲座' },
  { value: 'sports', label: '体育' },
  { value: 'arts', label: '文艺' }
]

// ✓ 数组初值，不能省
const selectedTypes = ref(['lecture'])
</script>

<template>
  <label v-for="item in allTypes" :key="item.value">
    <input type="checkbox" v-model="selectedTypes" :value="item.value" />
    {{ item.label }}
  </label>

  <p>已选 {{ selectedTypes.length }} 个：{{ selectedTypes.join('、') }}</p>
</template>
```

::: danger 不写数组初值会发生什么
把 `ref(['lecture'])` 改成 `ref('lecture')` 或 `ref(null)`，你会看到：

1. **勾任意一个，所有复选框一起变成勾选状态**（共用一个布尔值的结果）。
2. 再勾一个，全部取消。
3. `selectedTypes.length` 之类的写法会出错，因为字符串或 `null` 没有 `length` 的语义。

**判断口诀：多个复选框共用一个 `v-model` 时，初值必须是 `[]`。**
:::

`value` 不必是字符串，用 `:value` 绑定对象也可以，Vue 用“值相等”来匹配：

```vue [src/components/StaffPicker.vue]
<script setup>
import { ref } from 'vue'

const staffList = [
  { id: 1, name: '张三' },
  { id: 2, name: '李四' }
]

// 选中的是完整的对象
const selectedStaff = ref([])
</script>

<template>
  <label v-for="staff in staffList" :key="staff.id">
    <input type="checkbox" v-model="selectedStaff" :value="staff" />
    {{ staff.name }}
  </label>
</template>
```

### 单选框：字符串

一组单选框共用同一个 `v-model`，每个给一个 `value`，被选中的那个 `value` 就是模型值：

```vue [src/components/RolePicker.vue]
<script setup>
import { ref } from 'vue'

const role = ref('organizer')
</script>

<template>
  <label><input type="radio" v-model="role" value="organizer" /> 活动组织者</label>
  <label><input type="radio" v-model="role" value="reviewer" /> 审核员</label>

  <p>当前身份：{{ role }}</p>
</template>
```

::: warning 单选框必须有 `value`
如果一组单选框没写 `value`，Vue 会把 `null` 当作选中值，选中行为会变得不可预测。
**单选框、多复选框的 `value` 不是可有可无的属性，它决定了“选中之后得到什么值”。**
:::

### 下拉框：单选与多选

下拉单选和单选框是一回事，只是长得不一样：

```vue [src/components/ActivityTypeSelect.vue]
<script setup>
import { ref } from 'vue'

const type = ref('')
const visibleTo = ref([])
</script>

<template>
  <!-- 单选下拉：值是 string -->
  <select v-model="type">
    <option value="" disabled>请选择活动类型</option>
    <option value="lecture">讲座</option>
    <option value="sports">体育</option>
  </select>

  <!-- 多选下拉：值是数组，别忘写 multiple -->
  <select v-model="visibleTo" multiple>
    <option value="student">学生</option>
    <option value="teacher">教师</option>
    <option value="staff">行政人员</option>
  </select>
</template>
```

多选下拉在 Mac 上要按住 Command、Windows 上按住 Ctrl 才能多选，用户体验一般。
实际项目里更常用复选框组或标签选择器。**多选下拉的价值在于控件占位小**，
适合“可选值很多、但用户一般只选几个”的场景。

## `v-model` 的本质

理解本质，才能在它“不听话”的时候自己排查。`v-model` 是**语法糖**，
展开之后是一个属性绑定加一个事件监听。

### 文本输入框

```vue [展开前]
<input v-model="title" />
```

```vue [展开后：等价写法]
<input :value="title" @input="title = $event.target.value" />
```

- `:value` 把数据**流向** DOM；
- `@input` 把用户输入**流回**数据。

这就是“双向绑定”这个名字的来源 —— 不是魔法，是两条线。

### 复选框

复选框用的不是 `value` 和 `input`，而是 `checked` 和 `change`：

```vue [展开前]
<input type="checkbox" v-model="agreed" />
```

```vue [展开后：等价写法]
<input type="checkbox" :checked="agreed" @change="agreed = $event.target.checked" />
```

::: tip 为什么要懂这个
遇到这三种情况时，你需要手写展开形态：
1. **需要额外的处理**：比如输入时同时做格式化，`v-model` 不够用。
2. **用在自定义组件上**：组件上的 `v-model` 走的是另一套约定，在[单元 7](/unit07/04-vmodel)讲。
3. **要排查“为什么值没更新”**：知道它监听的是 `input` 还是 `change`，就知道该去哪看。
:::

## 三个表单修饰符

`v-model` 后面可以跟修饰符，改变“值怎么同步”。一共三个。

### `.lazy`：改成失焦时同步

默认是每敲一个字符就同步一次。`.lazy` 把它换成 `change`：

```vue [src/components/SearchBox.vue]
<script setup>
import { ref, watch } from 'vue'

const keyword = ref('')

// 加了 .lazy 之后，输入过程中 keyword 不变，失焦才更新
watch(keyword, (val) => {
  console.log('只有在失焦或回车后才打印：', val)
})
</script>

<template>
  <input v-model.lazy="keyword" />
</template>
```

**适用场景**：输入时不想实时联动。比如一个“按名称查询”的输入框，每敲一个字就发请求太浪费，
用 `.lazy` 让它在用户“确定输入完了”之后再触发。

::: warning `.lazy` 不只是“少触发几次”
它改变的是**数据更新的时机**。如果你在别处依赖这个值做实时预览，加了 `.lazy` 之后预览会“卡住不动”，
直到输入框失焦。**别为了省请求随手加 `.lazy`**，先想清楚有没有别的地方依赖实时值。
:::

### `.number`：转成数字

表单控件的值默认都是字符串。手机号、名额、时长这类数字字段就需要转一下：

```vue [src/components/CapacityInput.vue]
<script setup>
import { ref } from 'vue'

const capacity = ref(0)
</script>

<template>
  <!-- ✓ 输入 50，capacity 就是数字 50，不是字符串 '50' -->
  <input type="number" v-model.number="capacity" />
</template>
```

`type="number"` 本身也会触发自动转换，所以通常不用额外写 `.number`。
真正的用处在 `type="text"` 上：

```vue [src/components/RangeInput.vue]
<script setup>
import { ref } from 'vue'

const minCount = ref(0)
</script>

<template>
  <!-- 用 text 但需要数字：加 .number -->
  <input type="text" v-model.number="minCount" />
</template>
```

::: danger `.number` 的边界：转不了就保留原字符串
`.number` 的内部逻辑大致是“尝试转数字，转不了就返回原值”：

```js [Vue 内部的 looseToNumber 逻辑]
function looseToNumber(val) {
  const n = parseFloat(val)
  return isNaN(n) ? val : n
}
```

由此产生两个必须知道的后果：

| 用户输入 | `v-model.number` 得到的值 | 类型 |
| --- | --- | --- |
| `50` | `50` | number |
| `50.5` | `50.5` | number |
| 空字符串 | `''` | string |
| `abc` | `'abc'` | string |
| `12abc` | `12` | number（`parseFloat` 只读到能读的部分） |

最后一行很危险：用户输入 `12abc`，你拿到的是数字 `12`，**“格式不对”这件事被悄悄吞掉了**。
所以校验不能只看类型，必须校验值本身。这条在[6.4 表单校验](/unit06/04-validation)会具体处理。
:::

### `.trim`：去掉首尾空格

用户在输入框里手滑打出的首尾空格非常常见，尤其是从别处复制粘贴时：

```vue [src/components/TitleInput.vue]
<script setup>
import { ref } from 'vue'

const title = ref('')
</script>

<template>
  <!-- ✓ 输入“  校园歌手大赛  ”，title 是 '校园歌手大赛' -->
  <input v-model.trim="title" />
</template>
```

::: tip 什么时候必须加 `.trim`
- **名称、标题、账号、邮箱**这类用于比较或唯一性判断的字段 —— 首尾空格会造成“看起来一样但判定为不同”。
- **搜索关键词** —— 空格会让搜索结果差很多。

反过来，**简介、驳回理由这类多行文本不要加 `.trim`**，用户可能故意用换行和缩进来排版。
:::

### 修饰符可以连用

```vue [src/components/CountInput.vue]
<template>
  <!-- 先去空格，再转数字 -->
  <input v-model.trim.number="count" />
</template>
```

连用时建议只连两个，超过两个可读性就差了。

## 小结

- 表单绑定的**取值类型分两类**：能多选的（多复选框、多选下拉）是数组，其余是字符串；
  单个复选框是布尔值。
- **多个复选框共用一个 `v-model` 时，初值必须是数组**，否则会“勾一个全勾上”。
- 单选框与多复选框必须写 `value`，它决定选中后拿到的值。
- `v-model` 的本质是 `v-bind` 加 `v-on`：文本框是 `:value` + `@input`，
  复选框是 `:checked` + `@change`。
- `.lazy` 把同步时机从 `input` 改为 `change`；`.number` 尝试转数字；
  `.trim` 去掉首尾空格。
- `.number` 转不了会保留原字符串，`12abc` 会被转成 `12`，**校验不能只看类型**。

## 常见坑

::: details 坑 1：多选下拉忘了写 `multiple`
**现象**：`v-model` 绑了数组，但只能选中一项，数组里永远只有一个值。

**原因**：没写 `multiple` 时 `<select>` 是单选的，只会返回一个字符串。

**处理**：给 `<select>` 加上 `multiple`。加完之后注意键盘操作方式（Mac 用 Command，Windows 用 Ctrl）。
:::

::: details 坑 2：`v-model` 和 `:value` 同时写在一个输入框上
**现象**：输入框里的值改不动，或者改了之后立刻变回去。

**原因**：`:value` 和 `v-model` 都在往 DOM 里写值，两者会互相覆盖。`v-model` 展开后本来就包含 `:value`。

**处理**：二选一。要么用 `v-model`，要么用 `:value` + `@input` 自己管。不要重复绑定。
:::

::: details 坑 3：`<textarea>` 里写了默认内容
**现象**：多行文本框的初始内容不生效，或者模板编译报警告。

**原因**：`<textarea>` 的内容会被 Vue 当作默认插槽处理，和 `v-model` 冲突。

**处理**：把初始值写进 `ref` 的初值里，标签内容留空。
```vue
<textarea v-model="description"></textarea>
```
:::

::: details 坑 4：`.number` 之后 `typeof` 还是字符串
**现象**：`v-model.number="count"`，但 `typeof count.value` 输出 `'string'`。

**原因**：输入框是空的，或者用户输入的内容 `parseFloat` 转不了（比如全是字母），
此时 `.number` 保留原字符串。

**处理**：不要假设 `.number` 一定给出数字。在提交前做一次显式检查：
```js
if (typeof count.value !== 'number') {
  // 提示用户输入有效数字
}
```
或者干脆在 `type="number"` 上做，天然限制用户输入。
:::

::: details 坑 5：多个复选框的 `value` 用了 `:value` 但传了 `undefined`
**现象**：勾选后数组里多出来一个 `undefined`。

**原因**：`:value="item.value"` 里的 `item.value` 不存在（字段名写错，或数据还没加载完）。

**处理**：先确认 `item` 的结构，或者用 `v-if` 保证数据到位后再渲染这组复选框。
渲染前用 `console.log(JSON.stringify(list))` 看一眼，比盯着模板猜快得多。
:::

## 课后练习

::: details 练习 1：给每个字段标出类型
下面是一段跨校区的活动报名表单，先**不要写代码**，把每个 `v-model` 绑定的值类型写出来：

```vue
<input v-model="form.name" />
<textarea v-model="form.remark"></textarea>
<input type="checkbox" v-model="form.agree" />
<input type="checkbox" v-model="form.campuses" value="main" />
<input type="checkbox" v-model="form.campuses" value="north" />
<input type="radio" v-model="form.identity" value="student" />
<select v-model="form.activityId"></select>
<select v-model="form.tags" multiple></select>
<input type="text" v-model.number="form.capacity" />
```

**参考思路**：先判断“能不能多选”，再判断“是状态还是值”。写完之后用
`watch(() => form.value, ...)` 打印一次，看看实际类型和你想的是不是一致。

:::

::: details 练习 2：修好这个筛选面板
```vue [src/components/BugFilter.vue]
<script setup>
import { ref } from 'vue'
const status = ref('')
const types = ref('')
const onlyOpen = ref(null)
</script>
```

要求：状态单选（草稿 / 报名中 / 已结束）、类型多选（讲座 / 体育 / 文艺）、
“只看未满员”是一个开关。指出三处初值问题并改好。

**参考思路**：对照这一节的总表。三处里有两处是“该是数组却是字符串”，
一处是“该是布尔却是 `null`”。改完检查一下联动逻辑符不符合预期。

:::

::: details 练习 3：用展开写法重写一遍
把下面的代码改写成不带 `v-model` 的等价写法，然后说明两种写法的差别。

```vue
<input type="text" v-model.trim="title" />
<input type="checkbox" v-model="agreed" />
```

**参考思路**：文本框用 `:value` + `@input`，在赋值时手动调用 `.trim()`；
复选框用 `:checked` + `@change`。写完之后想一想：**什么时候你不得不这么写？**
（提示：需要同时做格式化或限制输入的时候。）

:::

---

上一节：[6.2 事件与按键修饰符](/unit06/02-modifiers) ·
下一节：[6.4 表单校验](/unit06/04-validation)
