# 4.3 事件绑定与指令总览

## 一个具体的场景

活动列表里每一项后面都有操作按钮：编辑、下架、查看报名。“编辑”要把当前活动的
数据带进表单，“下架”要先弹出确认框。

用原生写法，你得给每个按钮绑定监听：

```js
document.querySelectorAll('.btn-edit').forEach((btn) => {
  btn.addEventListener('click', () => {
    const id = btn.dataset.id
    openEditor(id)
  })
})
```

问题在于：**如果列表是动态渲染的，新加进来的按钮不在 `querySelectorAll` 的结果里**，
得重新绑一次。列表一变就要重绑，这是原生写法里最常见的一类 bug。

Vue 的写法是在模板里直接写绑定的意图：

```vue
<template>
  <button @click="openEditor(activity.id)">编辑</button>
  <button @click="confirmOffline(activity.id)">下架</button>
</template>
```

**按钮是渲染出来的，绑定就跟着渲染出来。** 不存在“漏绑”这种问题。
这一节把事件绑定的各种写法讲清楚，最后给一张指令总表。

## 原理与写法

### 两种写法：内联表达式与方法引用

事件绑定用 `v-on` 指令，缩写是 `@`。它的值有两种风格。

**风格一：内联表达式** —— 直接在引号里写一小段代码。

```vue
<script setup>
import { ref } from 'vue'
const count = ref(0)
const isOpen = ref(false)
</script>

<template>
  <!-- 简单的“改一个值”，适合内联 -->
  <button @click="count++">加一</button>
  <button @click="isOpen = !isOpen">切换</button>

  <!-- 带参数调用，适合内联 -->
  <button @click="openEditor(activity.id)">编辑</button>
</template>
```

**风格二：方法引用** —— 引号里只写一个函数名，不加括号。

```vue
<script setup>
function handleSubmit() {
  // 这里能用事件对象、能拿到组件里的其他状态
  console.log('提交')
}
</script>

<template>
  <!-- 写法 A：方法引用，函数会在事件触发时被调用 -->
  <button @click="handleSubmit">提交</button>

  <!-- 写法 B：内联调用，效果等价，但多了一层包装 -->
  <button @click="handleSubmit()">提交</button>
</template>
```

`@click="handleSubmit"` 和 `@click="handleSubmit()"` 效果一样，
但有一个重要区别：**加了括号才能传参。**

```vue
<script setup>
function selectActivity(id) {
  console.log('选中活动', id)
}
</script>

<template>
  <!-- ✗ 错：函数没被调用，id 也没传进去 -->
  <li @click="selectActivity">...</li>

  <!-- ✓ 对：加括号，把 id 传进去 -->
  <li @click="selectActivity(activity.id)">...</li>

  <!-- ✓ 对：如果不需要额外参数，方法引用更简洁 -->
  <li @click="selectActivity">...</li>
</template>
```

怎么选？按这个标准：

| 情况 | 推荐写法 |
| --- | --- |
| 只是改一个值（`count++`、`isOpen = !isOpen`） | 内联表达式 |
| 要传业务参数（`edit(item.id)`） | 内联调用 |
| 逻辑超过两行，或要复用 | 方法引用（函数写在 `<script setup>` 里） |

::: warning 一个反直觉的点
`@click="selectActivity"` 在**不需要参数**时是对的，而且更简洁。
但如果你写的是 `@click="selectActivity"` 却以为参数会自己传进去，就错了 ——
事件触发时调用 `selectActivity()` 时不带任何参数，`id` 是 `undefined`。

**报错现象**：函数进来了，但参数是 `undefined`，于是接口请求报 400。

**怎么处理**：只要函数需要业务参数，就必须加括号显式传。
:::

### 事件对象怎么拿

浏览器的事件回调会收到一个 `event` 对象，里面有点击坐标、目标元素等信息。
Vue 里拿它有两条规则。

**规则一：不传参时，事件对象自动注入。** 你只写函数名，Vue 会把事件对象作为第一个参数传进去。

```vue
<script setup>
function handleClick(event) {
  console.log(event.target)     // 被点击的那个元素
  console.log(event.clientX)    // 点击位置
}
</script>

<template>
  <button @click="handleClick">点我</button>
</template>
```

**规则二：要传参时，事件对象不会自动来，得用 `$event` 显式传给函数。**

```vue
<script setup>
// 第一个参数是业务参数，第二个才是事件对象
function handleItemClick(id, event) {
  console.log(id, event)
}
</script>

<template>
  <!-- ✗ 错：event 是 undefined -->
  <li @click="handleItemClick(item.id)">...</li>

  <!-- ✓ 对：用 $event 显式传入 -->
  <li @click="handleItemClick(item.id, $event)">...</li>
</template>
```

`$event` 是一个特殊变量，Vue 在事件处理里提供，指向原生的事件对象。
**内联表达式里也能直接用**：

```vue
<template>
  <!-- 内联里直接用 $event：阻止冒泡 -->
  <button @click="isOpen = false; $event.stopPropagation()">关闭</button>
</template>
```

::: details 为什么不传参时会自动注入、传参时不会
因为 Vue 把 `@click="handleClick"` 编译成“把 `handleClick` 本身作为监听器”，
浏览器调用监听器时天然会传事件对象。

而 `@click="handleItemClick(item.id)"` 编译成的是**一个内联函数**：
`() => handleItemClick(item.id)`。这个包装函数没有接收、也没有转发事件对象，
所以 `handleItemClick` 拿不到它。

**记住这一句就够：内联调用时，事件对象必须自己用 `$event` 传。**
:::

### 动态参数与指令缩写

有些场景下，绑定的属性名本身是变量。这时候用**动态参数**，写法是给参数加方括号。

```vue
<script setup>
import { ref } from 'vue'
const attrName = ref('title')
const eventName = ref('click')
</script>

<template>
  <!-- 绑定哪个属性，由 attrName 决定 -->
  <div :[attrName]="'2026 校园歌手大赛'">悬停看看</div>

  <!-- 绑定哪个事件，由 eventName 决定 -->
  <button @[eventName]="doSomething">按钮</button>
</template>
```

动态参数适合“同一个组件在不同场景绑不同东西”的封装场景，
日常业务里用得不多。**更需要注意的是它的三个限制**：

```vue
<template>
  <!-- ✗ 动态参数里的表达式有限制 -->
  <div :['data-' + name]="value">A</div>   <!-- 字符串拼接不合法 -->
  <div :[`data-${name}`]="value">B</div>   <!-- 模板字符串也不合法 -->
  <div :[name.toUpperCase()]="value">C</div> <!-- 方法调用不合法 -->

  <!-- ✓ 只接受一个简单的表达式 -->
  <div :[name]="value">D</div>
  <div :[name === 'a' ? 'x' : 'y']="value">E</div> <!-- 三元是合法的 -->
</template>
```

另外，动态参数的值应当是**小写**的。浏览器会把 HTML 属性的名字转成小写，
写 `:[someAttr]` 时，如果 `someAttr` 的值里有大写字母，可能匹配不上。
属性名一律用小写加连字符（`data-index` 这种），就不用担心。

指令缩写再统一列一次：

| 完整 | 缩写 | 记忆 |
| --- | --- | --- |
| `v-bind:xxx` | `:xxx` | 冒号在左边 = “绑定一个值” |
| `v-on:xxx` | `@xxx` | 艾特 = “当某个事件发生时” |

### 常用修饰符

修饰符是加在指令后面的小后缀，用来处理那些“每次都要写”的琐事。
事件修饰符直接接在事件名后面：

```vue
<template>
  <!-- 阻止事件冒泡，不用写 event.stopPropagation() -->
  <button @click.stop="select(item)">选中</button>

  <!-- 阻止默认行为，比如表单提交后刷新页面 -->
  <form @submit.prevent="onSubmit">...</form>

  <!-- 只在事件目标是元素本身时触发，点内部的文字不触发 -->
  <div @click.self="close">...</div>

  <!-- 只触发一次 -->
  <button @click.once="submitOnce">提交</button>

  <!-- 滚动时先不阻止默认行为，交给浏览器优化 -->
  <div @scroll.passive="onScroll">...</div>

  <!-- 按键修饰符：只在按回车时触发 -->
  <input @keyup.enter="search" />

  <!-- 修饰符可以链式叠加 -->
  <a @click.stop.prevent="goDetail">详情</a>
</template>
```

常用修饰符速查：

| 修饰符 | 作用 | 典型场景 |
| --- | --- | --- |
| `.stop` | 阻止冒泡（`stopPropagation`） | 列表项里点按钮不影响整行 |
| `.prevent` | 阻止默认行为（`preventDefault`） | 表单提交、链接跳转 |
| `.self` | 只处理目标元素自身的事件 | 点遮罩关闭弹窗，点内容不关 |
| `.once` | 只触发一次 | 提交按钮防重复 |
| `.capture` | 在捕获阶段处理 | 少见 |
| `.passive` | 不做阻止默认行为的检查 | 滚动、触摸事件 |
| `.enter` / `.esc` / `.tab` | 只在某个按键时触发 | 搜索框回车 |
| `.left` / `.right` / `.middle` | 鼠标按键 | 右键菜单 |

表单相关的修饰符（`.lazy`、`.number`、`.trim`）配合 `v-model` 使用，
在[单元 6](/unit06/02-modifiers) 展开。

::: tip 修饰符的顺序有讲究
`@click.prevent.self` 和 `@click.self.prevent` 不是一回事。前者先阻止默认行为，
再判断是不是元素自身；后者反过来。

**实际写的时候**：同类修饰符按“需要的行为顺序”写，不要凭感觉堆。
不确定时，拆成函数里两行代码，可读性反而更好。
:::

### 指令地图

Vue 的指令不多，而且就集中在几个单元里讲。下面这张表把整门课会出现的指令列全，
**建议截图存下来** —— 后面每次看到不认识的指令，回来查一下就知道在哪一节。

| 指令 | 作用 | 讲在哪 |
| --- | --- | --- |
| `v-bind` / `:` | 绑定属性、类名、样式 | 单元 4 · 4.2 |
| `v-on` / `@` | 绑定事件 | 单元 4 · 4.3（本节） |
| `v-html` / `v-text` | 插入内容 | 单元 4 · 4.3 |
| `v-once` | 只渲染一次，之后不再更新 | 单元 4 · 4.3 |
| `v-if` / `v-else-if` / `v-else` | 条件渲染（会创建和销毁） | 单元 5 · 5.3 |
| `v-show` | 条件显示（只切换 `display`） | 单元 5 · 5.3 |
| `v-for` | 列表渲染 | 单元 5 · 5.4 |
| `v-model` | 表单双向绑定 | 单元 6 · 6.3 |
| `v-model` 的 `.lazy` / `.number` / `.trim` | 表单绑定修饰符 | 单元 6 · 6.2 |
| 自定义指令（如 `v-focus`） | 直接操作 DOM 的复用逻辑 | 单元 8 · 8.5 |
| `v-memo` | 手动跳过一部分更新 | 附录 · API 速查 |
| `v-cloak` | 编译完成前隐藏模板 | 附录 · 常见报错 |
| `v-pre` | 跳过编译，原样输出 | 附录 · API 速查 |

这张表的用法是这样的：左边一列是你在代码里看到的东西，右边告诉你去哪一节查。
**它不是用来背的，是用来定位的。**

::: details `v-html` 和 `v-text` 为什么现在讲
它们和插值 `{{ }}` 是一组，所以放在这个单元。

```vue
<script setup>
import { ref } from 'vue'
const plain = ref('<strong>活动说明</strong>')
</script>

<template>
  <p>{{ plain }}</p>        <!-- 原样显示：<strong>活动说明</strong> -->
  <p v-text="plain"></p>    <!-- 同上，但会覆盖元素内已有内容 -->
  <p v-html="plain"></p>    <!-- 解析成 HTML：活动说明（加粗） -->
</template>
```

**`v-html` 在项目里要慎用。** 活动描述如果来自用户输入，直接 `v-html`
会有跨站脚本风险。项目里的做法是：活动描述先用 Markdown 存储，
渲染时用经过配置的 Markdown 渲染器转换，不用 `v-html`。详见
[单元 6 的 Markdown 案例](/unit06/06-case-markdown)。
:::

## 小结

- 事件用 `@`（`v-on` 缩写）绑定；内联表达式适合改一个值，方法引用适合有逻辑的处理。
- 只要函数需要业务参数，就必须写括号；不需要参数时，写函数名即可。
- 不传参时事件对象自动注入；传参时要用 `$event` 显式传入。
- 动态参数写 `:[name]`，值只能是一个简单表达式，不要拼接或调用方法。
- 修饰符把常见操作变成后缀：`.stop`、`.prevent`、`.self`、`.once`、`.passive`、按键修饰符。
- 指令总数不多，记住“哪个指令讲在哪一节”比背语法更有用。
- `v-html` 有安全风险，涉及用户输入时不要用。

## 常见坑

::: details 坑 1：在 `@click` 里写多行语句
```vue
<!-- ✗ 难读，且容易出错 -->
<button @click="if (ok) { save(); close() }">保存</button>
```

**现象**：语法错误。内联表达式里不能写 `if` 语句。

**原因**：`@click` 的值要么是一个表达式，要么是一个函数调用，不是一段代码块。

**怎么处理**：抽成函数。

```vue
<button @click="handleSave">保存</button>
```

判断标准：内联表达式里出现分号、`if`、`return` 就该抽函数了。
（`a = 1; b = 2` 这种没有 `if` 的多语句语法上合法，但同样建议抽出去。）
:::

::: details 坑 2：传了参却拿不到事件对象
```vue
<!-- ✗ 可能报错：undefined -->
<button @click="handleDelete(item.id)">删除</button>
<!-- 函数里写 function handleDelete(id, event) {} → event 是 undefined -->
```

**现象**：函数第二个参数是 `undefined`，想调用 `event.preventDefault()` 时报错。

**原因**：内联调用时 Vue 不会自动转发事件对象。

**怎么处理**：显式写 `$event`：

```vue
<button @click="handleDelete(item.id, $event)">删除</button>
```

**如果只是想阻止冒泡**，其实不用事件对象，直接加修饰符 `@click.stop` 更省事。
:::

::: details 坑 3：`@click="handleDelete()"` 在渲染时就执行了
这个坑和上一个相反，但更隐蔽。

```vue
<!-- ✗ 如果漏了 @ 写成 : -->
<button :click="handleDelete(item.id)">删除</button>

<!-- ✓ 对 -->
<button @click="handleDelete(item.id)">删除</button>
```

**现象**：页面一渲染，所有项都触发了删除；或者点击没反应。

**原因**：`:click` 是绑定一个名叫 `click` 的 HTML 属性，不是绑定事件。
浏览器不认识它，但 `handleDelete(item.id)` 这段表达式**在渲染时就被求值了**。

**怎么处理**：事件一律用 `@`。看到“页面一打开就发请求 / 就弹窗”的问题，
先检查是不是把 `@` 写成了 `:`。
:::

::: details 坑 4：用了 `.passive` 又想 `preventDefault`
```vue
<!-- ✗ 无效，控制台会警告 -->
<div @scroll.passive="onScroll">...</div>

<!-- onScroll 里调用 event.preventDefault() 不起作用 -->
```

**现象**：阻止默认行为无效，控制台提示 `Unable to preventDefault inside passive event listener`。

**原因**：`.passive` 的含义就是“我保证不阻止默认行为”，浏览器据此做了优化。

**怎么处理**：需要阻止默认行为就不要加 `.passive`；两个都要时，
说明场景设计有问题，重新想一下交互。
:::

## 课后练习

::: details 练习 1：改写事件绑定
下面是一段列表渲染，请补全事件绑定，满足三条要求：

```vue
<template>
  <ul>
    <li v-for="item in list" :key="item.id">
      {{ item.name }}
      <!-- 1. 点击整行，选中这一项，并把 id 传进 select -->
      <span>选中</span>
      <!-- 2. 点击“删除”按钮，删这一项，但不要触发整行的选中 -->
      <button>删除</button>
    </li>
  </ul>
</template>
```

**参考思路**：第 1 条用 `@click="select(item.id)"`；第 2 条的关键是
**阻止冒泡**，用 `@click.stop="remove(item.id)"`，而不是 `@click.stop="remove(item.id, $event)"`
再在函数里处理。**能用修饰符解决的，不要写进函数。**
:::

::: details 练习 2：判断该用哪种写法
下面五种场景，各该用内联表达式、方法引用，还是内联调用？

1. 点击按钮，把 `isOpen` 取反；
2. 表单提交时做五件事，包括校验、发请求、跳转；
3. 点击列表项，把该行的 `id` 传进处理函数；
4. 输入框按回车触发搜索，搜索逻辑有十几行；
5. 点击遮罩，关闭弹窗，但点弹窗内容不关。

**参考思路**：1 用内联；2 用方法引用；3 用内联调用；4 用方法引用 + `.enter` 修饰符；
5 用 `@click.self` 加方法引用。第 5 题是重点，`.self` 比手写
`if (event.target === event.currentTarget)` 清爽得多。
:::

::: details 练习 3：画一张自己的指令地图
不看上面的表格，凭印象写出你能记住的指令和它们的用途，然后和表格对照，
把漏掉的补上。

**参考思路**：这个练习的价值在于暴露“你以为记住、其实没记住”的部分。
补完之后，把这张表贴在你的项目笔记里 —— 后面每学一个新指令就回来添一行。
到单元 8 结束，这张表会是完整的。
:::

---

上一节：[4.2 模板语法与数据绑定](/unit04/02-template-syntax) ·
下一节：[4.4 ref 与 reactive](/unit04/04-reactivity)
