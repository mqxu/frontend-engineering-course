# 6.2 事件与按键修饰符

## 一个“关不掉的弹窗”

审核员在列表页点“驳回”，弹出一个填写驳回理由的对话框。代码是这样的：

```vue [src/components/RejectDialog.vue]
<script setup>
const emit = defineEmits(['close'])

function close() {
  emit('close')
}
</script>

<template>
  <!-- 遮罩层：点空白处关闭 -->
  <div class="mask" @click="close">
    <div class="dialog">
      <h3>驳回理由</h3>
      <textarea placeholder="请输入驳回理由"></textarea>
      <button @click="close">确认驳回</button>
    </div>
  </div>
</template>
```

上线后收到反馈：**在文本框里点一下，弹窗就关了，理由根本没法填。**

原因很简单：点击 textarea 时，事件先触发在最内层的元素上，然后沿着 DOM 树一层层往外“冒泡”，
冒到 `.mask` 上时，`@click="close"` 被执行了。你不是点遮罩关的，是冒泡冒上去的。

修法有三种，分别对应三个不同的修饰符。这一节就把这套方法讲清楚。

## 冒泡是怎么回事

要理解修饰符，先要理解事件的传播路径。看这张图：

```text [点击弹窗里的 textarea 时，事件经过了谁]
用户点击 <textarea>
      │
      ▼
┌─────────────────────────────────────────────┐
│ ③ <textarea>        ← event.target（真正被点到的元素） │
│      @click 监听器在冒泡阶段被调用                    │
└─────────────────────────────────────────────┘
      │ ① 捕获阶段：从外往内（document → ... → textarea）
      ▼
┌─────────────────────────────────────────────┐
│ ② <div class="dialog">                       │
└─────────────────────────────────────────────┘
      │ 冒泡阶段：从内往外
      ▼
┌─────────────────────────────────────────────┐
│ <div class="mask">  @click="close"           │
│      ← 冒到这里，close 被调用，弹窗关闭             │
└─────────────────────────────────────────────┘
      │
      ▼
   <body> → <html> → document
```

一次点击在 DOM 里走两个阶段：

1. **捕获阶段**：事件从最外层节点往里传，直到目标元素。
2. **冒泡阶段**：事件从目标元素往外传，一路传到 `document`。

默认情况下，你在元素上写的 `@click` 绑定在**冒泡阶段**。所以里层元素的点击会“连累”外层元素。

::: tip 两个要分清的概念
- **`event.target`**：真正被点到的那个元素，可能是最里层的 textarea。
- **`event.currentTarget`**：当前正在处理这个事件的元素，也就是“你的监听器挂在谁身上”。

`.self` 修饰符就是拿这两个值做比较。这个区别后面会反复用到。
:::

## 六个事件修饰符：每个拦掉的是什么

Vue 提供了六个事件修饰符，**它们拦截的东西完全不同**，混用就会出现“明明加了修饰符却没效果”。

| 修饰符 | 底层做的事 | 拦掉的是什么 | 什么时候必须用 |
| --- | --- | --- | --- |
| `.stop` | `event.stopPropagation()` | 事件**继续向上冒泡** | 内层点击不想触发外层监听 |
| `.prevent` | `event.preventDefault()` | 浏览器的**默认行为** | 表单提交不跳转、链接不跳转 |
| `.self` | 判断 `target === currentTarget` | **不阻止冒泡**，只是让处理函数“只在点到自己时”执行 | 点遮罩才关弹窗，点弹窗内容不关 |
| `.once` | 触发一次后移除监听 | **后续所有触发** | 只能点一次的“领取”“初始化”按钮 |
| `.capture` | 绑定到捕获阶段 | 不是拦截，是**改变触发时机** | 需要在外层先于内层拿到事件 |
| `.passive` | 给浏览器一个“不会 preventDefault”的承诺 | 不是拦截，是**放弃阻止默认行为的能力** | 滚动、触摸这类高频事件 |

### `.stop` 与 `.self` 的差别

这两个最容易被当成“差不多”，其实方向完全相反。

```vue [src/components/RejectDialog.vue]
<script setup>
const emit = defineEmits(['close'])
</script>

<template>
  <div class="mask" @click.self="emit('close')">
    <div class="dialog">
      <textarea placeholder="请输入驳回理由"></textarea>
      <button @click="emit('close')">确认驳回</button>
    </div>
  </div>
</template>
```

这里用了 `.self`：点到 `.mask` 本身（空白区域）才关；点到内部的 textarea 或 dialog 时不关，
因为 `target` 是 textarea，不等于 `currentTarget`（`.mask`）。

对比一下 `.stop` 的用法：

```vue [src/components/RejectDialog.vue（另一种修法）]
<template>
  <div class="mask" @click="emit('close')">
    <!-- ✓ 在内层把冒泡掐断，事件根本传不到 .mask -->
    <div class="dialog" @click.stop>
      <textarea placeholder="请输入驳回理由"></textarea>
      <button @click="emit('close')">确认驳回</button>
    </div>
  </div>
</template>
```

两种修法都对，但**语义不同**：

- `.self` 说的是“只有点我自己时才执行”；
- `.stop` 说的是“别往外传”。

::: warning `.stop` 要写在“内层”，不是写在外层
有同学看到上面第二种写法，会想“那我在 `.mask` 上加 `.stop` 不就行了”：

```vue [✗ 错误示范]
<div class="mask" @click.stop="emit('close')">
```

加了 `.stop` 之后，事件传到 `.mask` 就停了 —— 但**处理函数还是执行了**。
你点 textarea 时，事件冒泡到 `.mask`，`emit('close')` 照样被调用，弹窗照样关。
`.stop` 拦的是“继续往上”，不是“执行到我自己”。**要拦外层的监听，必须在内层加 `.stop`。**
:::

### `.capture` 与 `.passive`

`.capture` 很少用，但要知道它改了时机：

```vue [src/components/TrackPanel.vue]
<template>
  <!-- 捕获阶段执行：即使点到的是内层的按钮，外层也会最先收到 -->
  <div class="panel" @click.capture="track('panel')">
    <button @click="track('button')">点击</button>
  </div>
</template>
```

点按钮时的执行顺序变成：外层 `track('panel')` → 内层 `track('button')`，**与冒泡顺序相反**。
统计埋点、需要在业务处理前拦截的场景会用到。

`.passive` 解决的是性能问题。滚动事件如果处理函数里有可能调用 `preventDefault()`，
浏览器就必须等函数跑完才能决定滚不滚，页面会卡。加上 `.passive` 等于告诉浏览器“我保证不阻止默认行为，
你先滚”：

```vue [src/components/LongList.vue]
<template>
  <!-- ✓ 高频滚动事件加 passive，滚动更跟手 -->
  <div class="list" @scroll.passive="onScroll">……</div>
</template>
```

::: danger `.passive` 和 `.prevent` 不能一起用
```vue [✗ 错误示范]
<div @scroll.passive.prevent="onScroll">
```

`.passive` 的承诺是“不会调用 preventDefault”，`.prevent` 又要去调用它。两者矛盾，
浏览器会忽略 `.prevent`，还可能在控制台给出警告。**要阻止默认行为就别加 `.passive`。**
:::

### 修饰符的链式顺序是有讲究的

修饰符可以连写：`@click.self.stop`、`@click.once.prevent`。但**顺序会改变结果**。

Vue 的实现方式是：把修饰符按你写的顺序组成一个数组，然后一个一个“守卫”，
遇到第一个不通过的直接 `return`，后面的守卫和真正的处理函数都不会执行。大致是这样的逻辑：

```js [Vue 内部 withModifiers 的简化实现]
const modifierGuards = {
  stop: (e) => e.stopPropagation(),
  prevent: (e) => e.preventDefault(),
  self: (e) => e.target !== e.currentTarget,
  ctrl: (e) => !e.ctrlKey,
  // ……
}

function withModifiers(fn, modifiers) {
  return (event, ...args) => {
    // 按书写顺序逐个检查，任一个返回真值就中断
    for (let i = 0; i < modifiers.length; i++) {
      const guard = modifierGuards[modifiers[i]]
      if (guard && guard(event)) return
    }
    return fn(event, ...args)
  }
}
```

有了这段代码，顺序差异就很好解释了：

| 写法 | 点内层元素时的行为 |
| --- | --- |
| `@click.self.stop` | 先判断 `self`，不是点自己 → **直接中断**，`stopPropagation` 不会执行，事件照常冒泡 |
| `@click.stop.self` | 先执行 `stopPropagation`，**所有点击**都停止冒泡，再判断 `self` 决定要不要执行函数 |

::: tip 记不住顺序怎么办
**把“判断类”的修饰符写在前面，把“动作类”的写在后面。** 判断类指 `.self`、`.ctrl` 这类
“决定要不要执行”的；动作类指 `.stop`、`.prevent` 这类“一定会执行”的。

如果实在分不清，就**避免连写**：把逻辑拆成两个小函数，或者用 `if` 明确写出来。
链式修饰符写超过两个，可读性就开始下降了。
:::

## 按键修饰符

### 内置按键别名

在输入框上监听“按了什么键”，Vue 提供了一组常用别名：

| 修饰符 | 对应按键 |
| --- | --- |
| `.enter` | 回车 |
| `.tab` | Tab |
| `.esc` | Esc |
| `.space` | 空格 |
| `.delete` | Delete 与 Backspace（两者都算） |
| `.up` / `.down` / `.left` / `.right` | 方向键 |

常用场景是“回车提交、Esc 清空”：

```vue [src/components/QuickSearch.vue]
<script setup>
import { ref } from 'vue'

const keyword = ref('')

function search() {
  console.log('搜索', keyword.value)
}

function reset() {
  keyword.value = ''
}
</script>

<template>
  <!-- 回车触发搜索；Esc 清空输入 -->
  <input v-model="keyword" @keydown.enter="search" @keydown.esc="reset" />
</template>
```

::: tip 用 `keydown` 还是 `keyup`
- **`keydown`**：按下就触发，响应用户更快，但**长按会连续触发**。
- **`keyup`**：松开才触发，长按不会重复，但体感稍慢一点点。

表单里的一次性动作（提交、清空）用哪个都行；需要长按连续的场景（比如按住方向键移动选中项）
用 `keydown`，但要自己处理重复触发。**提交类操作建议用 `keydown`，避免用户长按回车发出多次请求。**
:::

### 自定义按键

不是每个键都有别名。`KeyboardEvent.key` 的任意合法值都可以直接当修饰符用，
**写法是把原值转成 kebab-case（小写、单词间用连字符）**：

```vue [src/components/ShortcutPanel.vue]
<template>
  <!-- PageDown 键：KeyboardEvent.key 是 'PageDown'，修饰符写 page-down -->
  <button @keyup.page-down="nextPage">下一页</button>

  <!-- 功能键 F1 -->
  <button @keyup.f1="showHelp">帮助</button>
</template>
```

::: warning Vue 3 里没有 `config.keyCodes`
网上很多老教程写着 `app.config.keyCodes.f1 = 112`，那是 Vue 2 的写法，
**Vue 3 已经移除**。Vue 3 直接用 `KeyboardEvent.key` 的值，不需要注册键码。
:::

### 系统修饰键

`.ctrl`、`.alt`、`.shift`、`.meta`（Mac 上是 Command 键，Windows 上是 Win 键）用来做组合键：

```vue [src/components/ToolbarPanel.vue]
<script setup>
function save() {
  console.log('保存')
}
function saveAs() {
  console.log('另存为')
}
</script>

<template>
  <!-- Ctrl + 点击：多选 -->
  <li @click.ctrl="toggleMultiSelect">报名记录</li>

  <!-- Ctrl + S：保存 -->
  <div @keydown.ctrl.s.prevent="save" tabindex="0">编辑区</div>

  <!-- Ctrl + Shift + S：另存为，两个系统键都要按住 -->
  <div @keydown.ctrl.shift.s.prevent="saveAs" tabindex="0">编辑区</div>
</template>
```

关于系统修饰键有两个容易踩的点。

**第一，单独用系统修饰键时，它只在“按键本身就是这个修饰键”时触发。**
`@keyup.ctrl` 只在松开 Ctrl 键时触发，不会因为你按了 Ctrl + A 就触发。

**第二，`.exact` 用来控制“精确组合”。**

```vue [src/components/ToolbarPanel.vue]
<template>
  <!-- 按住 Ctrl 点击就触发，此时如果同时还按着 Shift 也会触发 -->
  <button @click.ctrl="onCtrlClick">多选</button>

  <!-- ✓ 加了 .exact：必须只按 Ctrl，多按了 Alt 或 Shift 都不触发 -->
  <button @click.ctrl.exact="onCtrlOnlyClick">仅 Ctrl 多选</button>

  <!-- ✓ 不加任何系统键，才触发 -->
  <button @click.exact="onPlainClick">普通点击</button>
</template>
```

::: tip 什么时候需要 `.exact`
做键盘快捷键时。比如“Ctrl + S 保存”，如果用户习惯性地按了 Ctrl + Shift + S，
你不希望它被当成保存。这时用 `.exact` 把组合限定死，或者在处理函数里读
`event.shiftKey` 自己判断。**做快捷键的场合，`.exact` 基本都要加。**
:::

## 小结

- 事件默认在**冒泡阶段**触发，里层元素的点击会一路传到外层，这是“点弹窗内容却关了弹窗”的原因。
- `.stop` 拦的是冒泡，写在**内层**；`.prevent` 拦的是浏览器默认行为；`.self` 不拦冒泡，
  只是让函数只在点到元素本身时执行。
- `.once` 只触发一次，`.capture` 改到捕获阶段，`.passive` 放弃阻止默认行为、换滚动性能。
- `.passive` 不能和 `.prevent` 一起用。
- 修饰符按**书写顺序**逐个守卫，任一个不通过就中断，所以 `.self.stop` 与 `.stop.self` 行为不同。
- 按键用内置别名（`.enter`、`.esc`、`.tab` 等）或 `KeyboardEvent.key` 的 kebab-case 写法；
  系统修饰键组合用 `.ctrl`、`.alt`、`.shift`、`.meta`，快捷键场景加 `.exact`。

## 常见坑

::: details 坑 1：在外层写 `.stop` 想阻止内层点击
**现象**：以为加了 `.stop` 就不会误触发，结果还是关掉了弹窗。

**原因**：`.stop` 阻止的是“事件继续往外传”，不是“事件传到我自己时不执行”。
处理函数挂在冒泡路径上，冒到它就会执行。

**处理**：要在内层阻止事件传到外层，就把 `.stop` 写在内层元素上；
如果本意是“只有点我自己才执行”，用 `.self`。

:::

::: details 坑 2：把 `.prevent` 加在按钮上，表单还是跳转了
**现象**：`<button @click.prevent="submit">` 写了 `.prevent`，点提交页面还是刷新了。

**原因**：默认行为（提交表单）是在 `<form>` 的 `submit` 事件上触发的，
你在按钮的 `click` 上 `preventDefault`，拦住的是点击的默认行为，不一定能拦住表单提交。

**处理**：把 `.prevent` 写在表单上：`<form @submit.prevent="submit">`。
按钮只需要 `type="submit"`。

:::

::: details 坑 3：`@click.once` 加在列表项上，只有第一项能点
**现象**：列表渲染出来十个项目，只有第一个点击有效。

**原因**：`.once` 是加在**监听器**上的。列表项共用了同一段模板，
每个渲染出来的元素各有一个监听器，理论上每个都能点一次。但如果 `.once` 用在了
父级的委托监听上，就只有第一次有效。

**处理**：确认真实需求是“每个项目各能点一次”还是“整个列表只能点一次”。
前者把 `.once` 放在单项上并确保 `v-for` 有正确的 `:key`；后者放在父级容器上。

:::

::: details 坑 4：`.passive` 加上之后 `.prevent` 悄悄失效了
**现象**：`@touchmove.passive.prevent` 写了，手机上页面还是跟着滑动。

**原因**：`.passive` 向浏览器承诺不会阻止默认行为，`.prevent` 的调用会被忽略。

**处理**：二选一。要阻止滚动就别用 `.passive`；要滚动流畅就别用 `.prevent`。

:::

::: details 坑 5：系统修饰键在 Mac 上不生效
**现象**：`@click.ctrl` 在 Windows 上能用，同事的 Mac 上按 Command 没反应。

**原因**：Mac 的 Command 键对应的是 `metaKey`，不是 `ctrlKey`。

**处理**：跨平台快捷键用 `.meta` 覆盖 Mac，或者两个都写：
`@keydown.ctrl.s.prevent` 与 `@keydown.meta.s.prevent` 各来一份。
**在代码里给 Mac 用户留一条注释**，不然下一个人还会踩。

:::

## 课后练习

::: details 练习 1：修好这个“点内容也关闭”的面板
```vue
<template>
  <div class="panel-mask" @click="close">
    <div class="panel-body">
      <input placeholder="审核意见" />
      <button @click="close">关闭</button>
    </div>
  </div>
</template>
```

用 `.self` 和 `.stop` 各写一版，然后回答：两版在“点击面板空白处”时的行为一样吗？

**参考思路**：`.self` 版本点空白处会关；`.stop` 版本要看 `.stop` 写在哪一层。
把两次的手动验证结果对照着写下来，比只看代码印象深得多。

:::

::: details 练习 2：实现一组快捷键
给审核页面加三个快捷键：

1. `Ctrl + Enter`：提交当前审核
2. `Ctrl + Shift + Z`：撤回上一次审核结论
3. `Esc`：关闭当前弹窗

要求：`Ctrl + Enter` 不能因为用户多按了 Shift 就失效，`Ctrl + Shift + Z` 不能在
只按 Ctrl 时触发。

**参考思路**：先想清楚每个组合“允许多按哪些键、不允许多按哪些键”，
再决定 `.exact` 放在哪里。注意 Mac 上要额外处理 `.meta`。

:::

::: details 练习 3：解释一个现象
有一段代码：

```vue
<div class="outer" @click="outer">
  <div class="inner" @click.self.stop="inner">
    <button @click="btn">按钮</button>
  </div>
</div>
```

点击按钮时，`outer` 会不会执行？为什么？把 `.self` 和 `.stop` 换个位置再回答一次。

**参考思路**：按“守卫按顺序执行、遇到不通过就中断”这条规则，一步步推。
点按钮时 `target` 是按钮，`currentTarget` 是 `.inner`，先判断哪个修饰符是关键。

:::

---

上一节：[6.1 事件处理的完整写法](/unit06/01-events) ·
下一节：[6.3 表单绑定](/unit06/03-form-binding)
