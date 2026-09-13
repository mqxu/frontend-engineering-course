# 4.2 模板语法与数据绑定

## 一个具体的场景

活动管理页要显示一条活动，界面上有几处会变的地方：

- 活动标题（一段文字，会变）；
- 活动状态的标签（“草稿 / 报名中 / 报名截止 / 已结束”，文字和颜色都会变）；
- “下架”按钮（草稿状态下不能点，要置灰）；
- 活动封面图（图片地址来自数据）。

这四处恰好对应模板语法的四类能力：**插值、类名绑定、属性绑定、样式绑定**。

```vue [src/components/ActivityCard.vue]
<script setup>
import { ref } from 'vue'

const activity = ref({
  title: '2026 春季校园歌手大赛',
  status: 'signing',            // draft / signing / closed / finished
  cover: 'https://cdn.example.com/covers/singer.jpg',
  offline: false
})
</script>

<template>
  <article class="activity-card">
    <img :src="activity.cover" :alt="activity.title" />
    <h3>{{ activity.title }}</h3>

    <span class="tag" :class="{ 'tag--signing': activity.status === 'signing' }">
      报名中
    </span>

    <button :disabled="activity.status !== 'draft'">下架</button>
  </article>
</template>
```

这一节讲的就是这些冒号、花括号、引号之间的规则 —— 哪些能写、哪些不能写。

## 原理与写法

### 插值表达式：能放什么，不能放什么

双花括号 `{{ }}` 叫**插值表达式**，作用是“把这里替换成一个值”。
它有两个关键字：**表达式**，和**单行**。

**能放的**：任何能求出一个值的 JavaScript 表达式。

```vue
<template>
  <p>{{ title }}</p>                        <!-- 变量 -->
  <p>{{ count + 1 }}</p>                    <!-- 算术 -->
  <p>{{ isSignedUp ? '已报名' : '报名' }}</p>  <!-- 三元 -->
  <p>{{ name.toUpperCase() }}</p>           <!-- 方法调用 -->
  <p>{{ list.filter(i => i.done).length }}</p> <!-- 链式调用 -->
  <p>{{ `${a} 与 ${b}` }}</p>               <!-- 模板字符串 -->
</template>
```

**不能放的**：

```vue
<template>
  <!-- ✗ 语句：插值只接受表达式，不接受一段要执行的代码 -->
  <p>{{ if (ok) { ... } }}</p>

  <!-- ✗ 条件分支语句：要用三元表达式或 v-if 代替 -->
  <p>{{ if (ok) return 'A' }}</p>

  <!-- ✗ 变量声明：插值里不能定义新变量 -->
  <p>{{ const n = 1; n + 1 }}</p>

  <!-- ✗ 赋值：插值只用来“取一个值”，不用来改数据 -->
  <p>{{ count++ }}</p>

  <!-- ✗ 多个语句 -->
  <p>{{ a(); b() }}</p>
</template>
```

区分“表达式”和“语句”的办法很简单：**问自己“这一小段能不能当成 `const x = ...`
右边那一块”。** 能，就是表达式；不能，就是语句。

```js
const x = count + 1        // ✓ 表达式
const y = ok ? 'A' : 'B'   // ✓ 表达式
const z = if (ok) {}       // ✗ 语法错误，不是表达式
```

### 为什么表达式里不该做复杂运算

表达式里可以写 `list.filter(...).length`，语法上完全合法，但不建议。

```vue
<!-- ✗ 能跑，但不好 -->
<span>{{ list.filter(t => t.done).length }} / {{ list.length }}</span>
```

两个原因：

1. **可读性差。** 模板的职责是描述“界面长什么样”，塞进去一段数据处理逻辑之后，
   读模板的人要停下来分析这段代码。
2. **可能重复计算。** 模板里同样的一段表达式出现三次，Vue 就要算三遍。
   如果它是 `filter` 一个上千条的数组，代价不小。

**正确做法**：抽成[计算属性](/unit05/01-computed)，模板里只留一个名字。

```vue
<!-- ✓ 模板只描述“这里显示什么” -->
<span>{{ doneRatio }}</span>
```

::: tip 一条简单的分界线
模板里允许出现的运算，应该只有三种：

- 取值（`user.name`）；
- 简单判断（`status === 'draft'`、`a ? b : c`）；
- 已经定义好的函数或计算属性的调用。

超过这个范围，就该抽出去。**判断标准：把模板念出来，能不能一句话说清这里显示的是什么。**
:::

### 属性绑定：v-bind 与缩写

插值只能用在**标签中间的文字**上。如果要绑定的东西在**标签的属性位置**，
就得用 `v-bind`。

```vue
<template>
  <!-- ✗ 错：属性位置不认双花括号，浏览器会原样显示这段文字 -->
  <img src="{{ cover }}" />

  <!-- ✓ 对：用 v-bind -->
  <img v-bind:src="cover" />

  <!-- ✓ 更常见的写法：缩写成一个冒号 -->
  <img :src="cover" />
</template>
```

有 `v-bind` 和没 `v-bind`，区别是**引号里是字符串还是表达式**：

```vue
<img src="/covers/a.jpg" />          <!-- 字面量：就是这串固定文字 -->
<img :src="cover" />                 <!-- 表达式：cover 变量或 ref 的值 -->

<img src="cover" />                  <!-- 字面量：真的去请求名叫 cover 的图片 -->
<img :alt="'活动：' + title" />       <!-- 表达式：可以拼字符串 -->
```

常用的简写对应关系：

| 完整写法 | 缩写 | 用在哪 |
| --- | --- | --- |
| `v-bind:src="x"` | `:src="x"` | 任何属性 |
| `v-bind:class="x"` | `:class="x"` | 类名（下一小节详讲） |
| `v-bind:style="x"` | `:style="x"` | 内联样式 |
| `v-on:click="fn"` | `@click="fn"` | 事件（4.3 讲） |

**缩写不是可选项，是团队里的默认写法。** 除了极少数为了可读性刻意写全的地方，
一律用 `:` 和 `@`。

### 布尔属性的特殊性

有些属性是“布尔属性”：只要出现在标签上，就表示 `true`；不出现，就是 `false`。
`disabled`、`checked`、`readonly`、`required` 都属于这一类。

它们特殊在哪？**看字符串的值没用。**

```vue
<template>
  <!-- ✗ 危险：只要这个属性出现了，按钮就是禁用的 -->
  <!-- 哪怕 disabled 的值是 false，浏览器也只看到“有 disabled 这个属性” -->
  <button disabled="false">提交</button>

  <!-- ✓ 对：用 v-bind 绑定布尔值 -->
  <button :disabled="isSubmitting">提交</button>
</template>
```

`<button disabled="false">` 确实会被禁用 —— 这是 HTML 的规定，不是 Vue 的行为。
动态控制时必须用 `:` 绑定布尔值（或用 `:disabled="condition"`）。

同理还有 `:checked`、`:readonly` 等。常见的判断写法：

```vue
<template>
  <!-- 报名截止后不能再改 -->
  <button :disabled="activity.status === 'closed'">编辑</button>

  <!-- 名额满了就不能报名 -->
  <button :disabled="signedCount >= capacity">报名</button>
</template>
```

::: warning `null` / `undefined` 与布尔属性的配合
Vue 对布尔属性做了特殊处理：绑定值是 `null` 或 `undefined` 时，属性会被**移除**。

```vue
<button :disabled="undefined">A</button>  <!-- 渲染结果：<button>A</button> -->
<button :disabled="''">B</button>         <!-- 渲染结果：<button disabled>B</button> -->
```

也就是说，空字符串会**加上** `disabled`。用布尔值判断时不要用 `''` 表示“禁用”，
那样容易出现反直觉的结果。
:::

### 类名绑定：三种形态

类名绑定是模板里用得最频繁的绑定，因为它承担了“根据状态显示不同样子”的职责。
`class` 和 `:class` 可以同时写，Vue 会把结果合并：

```vue
<span class="tag" :class="dynamicClass">报名中</span>
```

`:class` 的值有三种形态，按“条件复杂度”选用。

**形态一：字符串** —— 类名固定，只是来源是变量。

```vue
<span :class="'tag--' + activity.status">报名中</span>
<!-- 等价于 class="tag--signing" -->
```

**形态二：对象** —— 按条件决定某个类名要不要加。这是最常用的一种。

```vue
<span
  class="tag"
  :class="{
    'tag--draft': activity.status === 'draft',
    'tag--signing': activity.status === 'signing',
    'tag--closed': activity.status === 'closed',
    'tag--finished': activity.status === 'finished'
  }"
>
  {{ statusText }}
</span>
```

对象的写法是 `类名: 条件`。条件是 `true` 就加上这个类名，是 `false` 就不加。
**注意类名要加引号** —— 因为 `tag--signing` 里有减号，不加引号 JavaScript 会当成减法。

**形态三：数组** —— 需要叠加一组类名时用。

```vue
<!-- 固定类名 + 条件类名混用 -->
<span class="tag" :class="['tag--' + activity.status, { 'tag--offline': activity.offline }]">
  {{ statusText }}
</span>
```

数组里可以混着写字符串和对象，Vue 会依次处理。

三种形态的选择：

| 形态 | 什么时候用 | 例子 |
| --- | --- | --- |
| 字符串 | 类名由一个值算出来 | `'tag--' + status` |
| 对象 | 若干个类名各自看条件 | 状态标签四种颜色 |
| 数组 | 要同时叠加多个来源的类名 | 固定样式 + 状态 + 禁用态 |

::: details 一个常见疑问：`:class` 和 `class` 会不会互相覆盖
不会。Vue 会把 `:class` 的结果和静态 `class` 合并成一个。

```vue
<span class="tag tag--base" :class="{ 'tag--signing': true }">
<!-- 渲染成：<span class="tag tag--base tag--signing"> -->
```

如果两边有同名类名，去重后只保留一个。**放心用，这是一个安全的设计。**
:::

### 内联样式绑定

样式绑定和类名绑定类似，也有对象和数组两种形态。区别是：**类名绑定写“名字”，
样式绑定写“具体的值”。**

```vue
<template>
  <!-- 对象形式：CSS 属性名用小驼峰，或加引号的短横线 -->
  <p :style="{ color: textColor, fontSize: size + 'px' }">名额已满</p>
  <p :style="{ 'font-size': size + 'px' }">也可以用短横线，但要加引号</p>

  <!-- 数组形式：叠加多组样式 -->
  <p :style="[baseStyle, themeStyle]">叠加样式</p>
</template>
```

什么时候用类名、什么时候用内联样式？

| 情况 | 用哪个 | 理由 |
| --- | --- | --- |
| 样式是预设的几种之一（四种状态色） | 类名绑定 | 样式写在 CSS 里，能复用、能被样式检查工具管 |
| 值来自用户的实时输入（主题色选择器） | 内联样式 | 值不可穷举，没法预先写类名 |
| 需要透传一个 CSS 变量 | 内联样式 | 见下 |

**内联样式的值不能直接写 CSS 变量吗？** 可以，但要作为对象的键写：

```vue
<template>
  <!-- 定义一个 CSS 变量，供组件内的样式引用 -->
  <div class="card" :style="{ '--theme-color': themeColor }">
    <button class="card__btn">主按钮</button>
  </div>
</template>

<style scoped>
.card__btn {
  /* 引用外部传入的主题色，没传入时用默认值 */
  background: var(--theme-color, #2f6fed);
}
</style>
```

这个用法在“换主题色”这种需求里很常见：**父组件只传一个颜色值，
组件内部所有用到这个颜色的地方，都从 CSS 变量取。** 它比在模板里给每个元素
都算一遍样式要清爽得多。

## 实战：活动状态标签

现在把上面的东西合起来，做项目里那个 `ActivityStatusTag` 组件。
需求是四种状态四种颜色：

| 状态值 | 显示文字 | 颜色 |
| --- | --- | --- |
| `draft` | 草稿 | 灰色 |
| `signing` | 报名中 | 绿色 |
| `closed` | 报名截止 | 橙色 |
| `finished` | 已结束 | 蓝色 |

```vue [src/components/ActivityStatusTag.vue]
<script setup>
import { computed } from 'vue'

const props = defineProps({
  status: {
    type: String,
    required: true,
    // 限制取值范围，写错时控制台会警告
    validator: (v) => ['draft', 'signing', 'closed', 'finished'].includes(v)
  }
})

// 状态到文字的映射
const STATUS_TEXT = {
  draft: '草稿',
  signing: '报名中',
  closed: '报名截止',
  finished: '已结束'
}

const statusText = computed(() => STATUS_TEXT[props.status] ?? '未知')
</script>

<template>
  <span class="status-tag" :class="`status-tag--${status}`">{{ statusText }}</span>
</template>

<style scoped>
.status-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  line-height: 18px;
}

.status-tag--draft {
  color: #6b7280;
  background: #f3f4f6;
}

.status-tag--signing {
  color: #047857;
  background: #d1fae5;
}

.status-tag--closed {
  color: #b45309;
  background: #fef3c7;
}

.status-tag--finished {
  color: #1d4ed8;
  background: #dbeafe;
}
</style>
```

这份实现里有几个值得注意的点：

- **文字用映射表，不用 `v-if` 链。** `STATUS_TEXT[status]` 一行就够，
  加一种状态只改表，不改模板。
- **类名用字符串形态。** 因为四种状态刚好对应 `status-tag--draft` 这样的类名，
  一个模板字符串就够了，不需要写成对象。
- **颜色的具体值写在 CSS 里，不在模板里。** 这样样式可以被样式检查工具覆盖，
  也方便以后统一改配色。

::: tip 类比名绑定更彻底的做法
如果状态标签的颜色以后要支持“换皮肤”，可以把颜色也变成 CSS 变量：

```vue
<span class="status-tag" :class="`status-tag--${status}`" :style="{ '--tag-color': colorMap[status] }">
```

然后 CSS 里统一写 `color: var(--tag-color)`。加一层变量，样式就完全由数据驱动了。
:::

## 小结

- 插值 `{{ }}` 里只能放**表达式**，不能放语句、`if`、变量声明、赋值。
- 模板里避免复杂运算，超过“取值 + 简单判断”就抽成计算属性。
- 属性位置用 `:` 绑定（`v-bind` 的缩写）；有 `:` 是表达式，没 `:` 是字符串字面量。
- 布尔属性不能靠字符串值判断，必须绑定布尔值；`null` / `undefined` 会移除属性，
  但空字符串会**加上**布尔属性。
- 类名绑定三种形态：字符串（一个值算出类名）、对象（多个条件各自判断）、数组（叠加多个来源）。
- 内联样式用对象或数组；需要传递颜色这类不可枚举的值时，用 CSS 变量配合。
- 状态与文字、颜色的对应关系，优先用映射表，不要写成一长串 `v-if`。

## 常见坑

::: details 坑 1：类名里有减号却忘了加引号
```vue
<!-- ✗ 错 -->
<span :class="{ status-active: isActive }">...</span>

<!-- ✓ 对 -->
<span :class="{ 'status-active': isActive }">...</span>
```

**现象**：报 `status is not defined` 之类的错误，或者类名没加上。

**原因**：`status-active` 没加引号时，JavaScript 把它当成 `status - active` 这个减法表达式，
于是去找 `status` 和 `active` 两个变量。

**怎么处理**：凡是有减号的类名（BEM 命名里几乎全都是），一律加引号。
:::

::: details 坑 2：把 `:disabled` 写成了 `disabled`
```vue
<!-- ✗ 错：按钮永远禁用，或者永远启用 -->
<button disabled="isSubmitting">提交</button>

<!-- ✓ 对 -->
<button :disabled="isSubmitting">提交</button>
```

**现象**：明明数据变了，按钮的可点状态不变。

**原因**：漏了冒号，`isSubmitting` 被当成字符串 `"isSubmitting"`，
而字符串不是空值，布尔属性就始终存在。

**怎么处理**：凡是“会根据状态变化”的属性，检查有没有冒号。
:::

::: details 坑 3：在 `:style` 里写了 `!important`
```vue
<!-- ✗ 不会生效 -->
<p :style="{ color: 'red !important' }">...</p>
```

**现象**：样式没生效，控制台可能有警告。

**原因**：`:style` 是通过元素的 `style` 属性设置的，而 `!important` 在行内样式里
需要单独设置优先级，字符串里的 `!important` 不被识别。

**怎么处理**：改成类名绑定，把 `!important` 写进 CSS；或者调整样式的选择器优先级。
**更根本的做法**：不要用 `!important` 解决问题，它会让后续样式难以覆盖。
:::

::: details 坑 4：以为 `v-bind` 可以对任意 HTML 属性生效
`:src`、`:disabled`、`:class`、`:style` 这些能用，是因为 Vue 会把绑定结果设置到元素上。
但有些“看起来是属性、其实是特性”的东西（比如 `<input>` 的 `value` 在表单里），
行为要看具体场景。

**怎么处理**：表单相关的一律用[单元 6 的 `v-model`](/unit06/03-form-binding)，
不要用 `:value` 硬绑。`:value` 绑了之后用户输入不会同步回数据，容易出问题。
:::

## 课后练习

::: details 练习 1：把一长串判断改成映射表
下面这段模板能跑，但维护困难。请改写成更易扩展的形式，并说明改动量。

```vue
<span v-if="status === 'draft'">草稿</span>
<span v-else-if="status === 'signing'">报名中</span>
<span v-else-if="status === 'closed'">报名截止</span>
<span v-else-if="status === 'finished'">已结束</span>
<span v-else>未知</span>
```

**参考思路**：先建一个 `STATUS_TEXT` 映射表，模板里只留一句 `{{ STATUS_TEXT[status] ?? '未知' }}`。
然后回答：如果现在要加一个“已下架”状态，两个版本各要改几行？
**加状态不改模板，是映射表的价值所在。**
:::

::: details 练习 2：四种状态四种颜色，用对象形式写
不参考上面的代码，自己写一个“报名审核状态标签”，三种状态：
待审核（黄色）、已通过（绿色）、已驳回（红色）。

要求：
1. 用**对象形式**的类名绑定实现（不是字符串形态）；
2. 文字用映射表算出来；
3. 额外加一个 `size` 属性，支持 `small` 和 `default` 两档，用数组形态叠加类名。

**参考思路**：类名对象写成 `{ 'tag--pending': status === 'pending', ... }` 这样的形式；
`size` 用数组形态拼进去。做完了和上面 `ActivityStatusTag` 的字符串形态对比一下，
想想什么情况下对象形态更合适。
:::

::: details 练习 3：给卡片加主题色
做一个活动卡片，卡片顶部有一块强调色区域，颜色由外部传入。

要求：
1. 通过 `:style` 定义一个 CSS 变量；
2. 卡片内部至少有三处用到这个颜色（边框、标题、按钮）；
3. 这三处都从 CSS 变量取，不要在模板里重复算样式。

**参考思路**：关键是把“一个颜色值”变成“一个可以被多处引用的变量”。
如果发现自己在模板里给三个元素分别写 `:style="{ color: themeColor }"`，
就说明还没用上 CSS 变量。
:::

---

上一节：[4.1 声明式渲染：从操作 DOM 到描述状态](/unit04/01-declarative) ·
下一节：[4.3 事件绑定与指令总览](/unit04/03-event-directive)
