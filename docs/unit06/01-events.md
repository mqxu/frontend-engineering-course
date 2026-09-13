# 6.1 事件处理的完整写法

## 一个“点了没反应”的按钮

审核页面有这样一个需求：审核员点“通过”，弹一个确认框，确认后调用接口。有同学写成这样：

```vue [src/components/ReviewPanel.vue]
<script setup>
function approve() {
  // 想在这里拿到点击事件对象，读一下 event 里的东西
  console.log(event.type) // ✗ event 未定义，直接报错
}
</script>

<template>
  <button @click="approve">通过</button>
</template>
```

他一脸疑惑：“老师，不是说事件处理函数能拿到 `event` 吗？我 `console.log(event)` 就报 `event is not defined`。”

问题出在**他写的不是事件对象，而是一个普通函数**。普通函数里的 `event` 是全局变量，
浏览器里可能是 `window.event`，在模块化的代码里根本不存在。

正确的写法有三种，用哪一种取决于你要不要传参数、要不要用事件对象。这一节把这三种写法讲清楚。

## 三种写法与它们的差别

### 写法一：内联表达式

```vue [src/components/CounterCard.vue]
<script setup>
import { ref } from 'vue'
const count = ref(0)
</script>

<template>
  <!-- ✓ 简单逻辑直接写在模板里 -->
  <button @click="count++">报名人数 +1（当前 {{ count }}）</button>
</template>
```

内联表达式适合**一行能讲完的逻辑**：自增、取反、赋一个固定值。优点是就近、直观。

它的边界也很清楚：**超过一行就该抽成函数**。下面这种写法要避免：

```vue [不推荐的写法]
<button @click="count++; if (count > 10) { alert('名额已满') }">加入</button>
```

一行里塞判断，模板会越来越难读，而且这类逻辑测试不了。

### 写法二：方法引用

```vue [src/components/ReviewPanel.vue]
<script setup>
function approve() {
  // 只要逻辑，不要事件对象
  console.log('通过审核')
}
</script>

<template>
  <!-- ✓ 写方法名，不写括号 -->
  <button @click="approve">通过</button>
</template>
```

这是最常用的写法。**注意写的是 `approve` 而不是 `approve()`。**

如果你写了括号，就变成了“在模板渲染时立刻执行一次，把返回值当作处理函数”，
结果往往是页面一加载就触发了逻辑，点击反而没反应。

::: tip 事件对象会自动注入
用方法引用时，Vue 会把这个事件的事件对象**作为第一个参数**传进来。所以下面这样写是合法的：

```vue [src/components/ReviewPanel.vue]
<script setup>
function approve(e) {
  console.log(e.type) // 'click'
  console.log(e.target) // 被点到的那个元素
}
</script>
```

**只要你不主动传参，事件对象就自动给你。** 反过来，一旦你主动传了参数，它就不给了 ——
这就是下面要讲的第三种写法。
:::

### 写法三：内联调用 + `$event`

需求变了：审核时要带上这条报名的编号。

```vue [src/components/ReviewPanel.vue]
<script setup>
function approve(id, e) {
  console.log('审核', id, '触发元素', e.target.tagName)
}
</script>

<template>
  <!-- ✓ 主动传参时，用 $event 把事件对象手动传进去 -->
  <button @click="approve(record.id, $event)">通过</button>
</template>
```

`$event` 是 Vue 在模板里提供的一个特殊变量，指代这次事件的事件对象。

它有一个容易被忽略的细节：**`$event` 只在模板的内联处理里可用**。
如果你的处理函数被包在箭头函数里，可以直接用形参：

```vue [src/components/ReviewPanel.vue]
<script setup>
function approve(id, e) {
  console.log('审核', id)
}
</script>

<template>
  <!-- ✓ 箭头函数包一层，事件对象作为箭头函数的参数 -->
  <button @click="(e) => approve(record.id, e)">通过</button>
</template>
```

::: warning 传多个参数时不要写成这样
```vue [✗ 错误示范]
<button @click="approve(record.id, 'admin', $event, extra)">通过</button>
```

一个处理函数里塞四个参数，说明这个函数承担的职责太多。正确做法是**把数据组织成一个对象再传**：

```vue [✓ 正确示范]
<script setup>
function approve(payload) {
  // payload: { id, operator, source }
}
</script>

<template>
  <button @click="approve({ id: record.id, operator: currentUser, source: 'list' })">
    通过
  </button>
</template>
```

**给函数传参数，超过两个就应该考虑改成对象。** 这样调用处一看就知道每个值是什么，
将来加字段也不用改所有调用点。
:::

## 常见事件类型与它们的触发时机

同一个“用户操作”在浏览器里可能触发好几个事件，选错了就会出现“提示不刷新”“校验不生效”这类问题。
先记一张表：

| 事件 | 触发时机 | 典型用途 |
| --- | --- | --- |
| `click` | 鼠标点击（或回车/空格触发按钮） | 按钮操作 |
| `input` | **每次值改变**，包括粘贴、输入法上屏后 | 实时搜索、即时校验 |
| `change` | 值**确认改变并提交**：文本框失焦时、`select` / 复选框选中后立即 | 下拉框选择、复选框勾选 |
| `submit` | 表单提交时 | 整表提交 |
| `keydown` | 按下按键的那一刻 | 快捷键、回车提交 |
| `keyup` | 松开按键时 | 与 `keydown` 配合避免长按重复触发 |
| `blur` | 元素失去焦点 | 失焦校验 |
| `focus` | 元素获得焦点 | 高亮提示 |
| `scroll` | 元素或页面滚动 | 滚动加载、回到顶部按钮 |

### `input` 与 `change` 的区别

这是新手最容易混的一对。用一句话区分：

> **`input` 管“值变了”，`change` 管“值定下来了”。**

在文本框里，你每敲一个字符就触发一次 `input`；而 `change` 只在**内容确实变了、且元素失去焦点**时才触发。

看个例子就清楚了。假设要做一个“活动标题长度提示”：

```vue [src/components/ActivityTitleInput.vue]
<script setup>
import { ref, computed } from 'vue'

const title = ref('')
const tip = computed(() => `已输入 ${title.value.length} 个字`)
</script>

<template>
  <label>活动标题</label>
  <!-- ✓ 用 input：用户每打一个字，提示立刻更新（v-model 内部就是监听 input） -->
  <input v-model="title" />

  <!-- ✓ 也可以不用 v-model，直接监听 input 手动赋值，效果一样 -->
  <input :value="title" @input="title = $event.target.value" />

  <p>{{ tip }}</p>
</template>
```

如果把上面的 `input` 换成 `change`，现象是：**用户打字时提示一直是“已输入 0 个字”，
直到点到别的地方才突然跳成正确数字。** 用户会觉得这个页面坏了。

那 `change` 用在什么地方？

```vue [src/components/ActivityTypeSelect.vue]
<script setup>
import { ref } from 'vue'

const type = ref('')
function onTypeChange(e) {
  // 选择确定之后再做一次重操作，比如按类型拉取不同的表单字段
  console.log('类型切换为', e.target.value)
}
</script>

<template>
  <!-- ✓ 下拉框用 change：选中的那一刻值就定下来了 -->
  <select v-model="type" @change="onTypeChange">
    <option value="">请选择活动类型</option>
    <option value="lecture">讲座</option>
    <option value="sports">体育</option>
    <option value="arts">文艺</option>
  </select>
</template>
```

::: tip 一个更常见的场景：失焦时才校验
即时校验对用户干扰大 —— 才打了两个字符就红字提示“手机号格式不正确”。
更好的做法是**失焦时校验**：

```vue [src/components/PhoneInput.vue]
<script setup>
import { ref } from 'vue'

const phone = ref('')
const error = ref('')

function validateOnBlur() {
  error.value = /^1[3-9]\d{9}$/.test(phone.value) ? '' : '请输入 11 位手机号'
}
</script>

<template>
  <input v-model="phone" @blur="validateOnBlur" />
  <p v-if="error" class="error">{{ error }}</p>
</template>
```

这里用 `blur` 而不是 `change`，是因为 `blur` 的语义就是“用户离开这个输入框”，
它比“值变了”更符合“该检查一下了”这个时机。
:::

## 表单提交为什么必须阻止默认行为

这是 `submit` 事件的特殊之处。先看一个纯粹的原生 HTML 行为：

```html [原生 HTML 的表单]
<!-- 什么都不写的情况下：点提交按钮，浏览器会带着所有字段跳转到新页面 -->
<form action="/api/signup" method="post">
  <input name="name" />
  <button type="submit">提交</button>
</form>
```

**表单的默认行为是“提交并跳转”**：浏览器会把字段拼进请求里，加载 `action` 指向的页面。
在单页应用里这是灾难 —— 整个 Vue 应用会被卸载重载，用户看到页面闪一下回到初始状态。

所以只要写 `@submit`，几乎总要阻止默认行为：

```vue [src/components/SignupForm.vue]
<script setup>
import { ref } from 'vue'

const name = ref('')

function onSubmit() {
  // 这里发请求，而不是让浏览器跳转
  console.log('提交', name.value)
}
</script>

<template>
  <!-- ✓ .prevent 修饰符，等价于在函数里 e.preventDefault() -->
  <form @submit.prevent="onSubmit">
    <input v-model="name" />
    <button type="submit">提交</button>
  </form>
</template>
```

关于按钮还有一个常见困惑：**为什么我按了回车，表单也提交了？**

因为浏览器有内置规则：表单里存在 `type="submit"` 的按钮时，在**单个文本输入框**里按回车
会触发一次 `submit`。这不是你写的，是浏览器替你做的。理解了这一点，你就知道为什么
“回车提交”的需求只需要给 `<form>` 加 `@submit.prevent`，而不需要单独监听 `keydown`。

::: warning 回车提交的两种做法，优先用 `submit`
| 做法 | 写法 | 评价 |
| --- | --- | --- |
| 监听表单提交 | `@submit.prevent="onSubmit"` | ✓ 推荐，浏览器原生支持，输入框聚焦时回车也生效 |
| 监听输入框按键 | `@keydown.enter="onSubmit"` | 只在输入框聚焦时生效，多输入框时要写多处 |

后者不是错，但**当表单里有多个输入框时，你需要给每个都加一遍**，容易漏。
优先用 `submit`，只有“在某个特定输入框里回车做别的事”时才用 `keydown`。
:::

## 小结

- 三种写法各有用途：**内联表达式**写一行能讲完的逻辑，**方法引用**最常用且事件对象自动注入，
  **内联调用 + `$event`** 用于同时要参数和事件对象。
- 主动传参之后，事件对象不会自动给，必须用 `$event` 手动传，或用箭头函数包一层。
- 处理函数参数超过两个，改成传一个对象。
- `input` 管“值变了”、`change` 管“值定下来了”；实时提示用 `input`，选择确认用 `change`，
  离开输入框时校验用 `blur`。
- 表单的默认行为是提交并跳转，`@submit` 上几乎总要加 `.prevent`。
- 回车提交优先走 `@submit`，不要给每个输入框加 `keydown.enter`。

## 常见坑

::: details 坑 1：写成了 `@click="handleClick()"`
**现象**：页面一加载就执行了一次 `handleClick`，之后点击按钮反而没反应。

**原因**：加括号是在渲染时求值，Vue 拿到的是 `handleClick()` 的返回值（通常是 `undefined`），
于是点击时没有可执行的函数。

**处理**：
- 不需要传参 → 写 `@click="handleClick"`。
- 需要传参 → 写 `@click="handleClick(id)"`，这时事件对象要用 `$event` 手动传。

:::

::: details 坑 2：`$event` 写成了 `event`
**现象**：`$event.target` 报 `Cannot read properties of undefined`。

**原因**：模板里的 `$event` 是 Vue 注入的特殊变量，写成 `event` 它会去组件作用域里找，
找不到就是 `undefined`。

**处理**：内联处理里统一用 `$event`；如果用了箭头函数，写形参名即可
（`@click="(e) => handle(id, e)"`）。

:::

::: details 坑 3：用 `change` 做实时搜索，用户以为卡住了
**现象**：输入框里打字，搜索建议不出现；点到别处才刷出来。

**原因**：`change` 要等失焦才触发，用户的每次敲击都没被处理。

**处理**：实时输入场景一律用 `input`。如果请求太频繁，加防抖，而不是把事件换成 `change`。
防抖的写法见[单元 8 的组合式函数](/unit08/04-composables)。

:::

::: details 坑 4：给 `<button>` 忘了写 `type="submit"`，回车不提交
**现象**：点按钮能提交，但在输入框里按回车没反应。

**原因**：`<button>` 的默认 `type` 在表单里是 `submit`，但如果你显式写了 `type="button"`
（比如这个按钮是“取消”），它就不会触发提交。

**处理**：把“提交”按钮写成 `type="submit"`，“取消”按钮写成 `type="button"`。
**不要两个都不写默认值**，否则点“取消”也会提交。

:::

::: details 坑 5：中英文输入法组合期的事件
**现象**：用中文输入法打“活动”，第一段拼音还没选字，`input` 事件已经触发了好几次，
实时搜索框里出现了拼音串。

**原因**：输入法在组合过程中会持续触发 `input`，这叫组合事件（composition）。

**处理**：需要避开组合期的场景，监听 `compositionstart` 与 `compositionend`，
只在 `compositionend` 之后处理。多数表单不用管这件事，只有实时搜索这类
“每次输入都做重操作”的场景才需要。

:::

## 课后练习

::: details 练习 1：三种写法各改一次
把下面这段代码改成三种写法，并说明每种写法的事件对象从哪里来。

```vue
<template>
  <button @click="submit">提交</button>
</template>
```

**参考思路**：第一种保留方法引用，函数加一个形参接事件对象；
第二种改成内联调用并带上报名编号，用 `$event` 传事件对象；
第三种用箭头函数包一层。改完对比一下，哪种写法下事件对象是自动给的。

:::

::: details 练习 2：给“活动标题”加实时字数提示
要求：输入框打字时实时显示“已输入 N 个字 / 最多 30 个字”，超过 30 个字时提示变红，
并且**不要在用户用输入法打字的中途就提示超限**。

**参考思路**：用一个 `ref` 存标题，一个 `computed` 算长度和是否超限。
关于输入法，先想想“组合期”是什么时候开始、什么时候结束，再决定在哪个事件里更新提示。

:::

::: details 练习 3：找出提交表单的三个问题
下面这段代码有三处问题，找出来并修好。

```vue [src/components/BugForm.vue]
<script setup>
import { ref } from 'vue'
const keyword = ref('')

function search() {
  console.log(keyword.value, event.type)
}
</script>

<template>
  <form @submit="search">
    <input v-model="keyword" @change="search" />
    <button @click="search()">搜索</button>
  </form>
</template>
```

**参考思路**：先看 `event` 从哪来，再看表单提交有没有处理默认行为，
最后看按钮的类型与点击处理会不会重复触发。三处都在这一节里讲过。

:::

---

上一节：[单元 6 导学](/unit06/) ·
下一节：[6.2 事件与按键修饰符](/unit06/02-modifiers)
