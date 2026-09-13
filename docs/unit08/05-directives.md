# 8.5 自定义指令

## 有些事，组合式函数做不了

组合式函数能复用逻辑，但它有一个前提：**你得能在组件里拿到那个 DOM 元素**。
而有些需求，本质就是“给某个元素做一件事”，逻辑和元素是绑在一起的：

- 打开活动编辑弹窗时，标题输入框要**自动获得焦点**。
- 搜索按钮要**防抖**，点太快只发一次请求。
- 没有“报名审核”权限的账号，那个审核按钮**根本不该出现在页面上**。

这些用组合式函数也能做，但要写一堆模板 ref、`onMounted`、手动绑定：

```vue [只做“自动聚焦”，代码已经不少]
<script setup>
import { ref, onMounted, nextTick } from 'vue'

const inputRef = ref(null)

onMounted(async () => {
  await nextTick()
  inputRef.value?.focus()
})
</script>

<template>
  <input ref="inputRef" />
</template>
```

如果页面里有好几个输入框都要自动聚焦，这段代码要复制好几遍。
**自定义指令**就是为了这种“和元素绑定的通用行为”准备的 —— 写一次，注册好，
之后在标签上写一个 `v-xxx` 就行。

```vue [用自定义指令之后]
<template>
  <input v-focus />
</template>
```

## 指令的钩子函数

一个自定义指令就是一个对象，里面有几个钩子函数，在元素的不同生命周期触发。
最常用的三个：

| 钩子 | 触发时机 | 典型用途 |
| --- | --- | --- |
| `mounted` | 元素被插入到 DOM 后 | 初始化为元素做什么（聚焦、绑定监听） |
| `updated` | 所在组件的 `vnode` 更新后 | 值变了要重新处理（重新校验、更新样式） |
| `unmounted` | 元素从 DOM 移除后 | 清理（移除监听、销毁实例） |

完整还有 `created`、`beforeMount`、`beforeUpdate`、`beforeUnmount`，但日常够用的
就是上面三个。

```js [src/directives/focus.js]
export const vFocus = {
  mounted(el) {
    // el 就是这个指令所在的 DOM 元素
    el.focus()
  }
}
```

::: tip 钩子的简写
如果一个指令只需要 `mounted` 和 `updated`，而且两者做的事一样，可以直接写成一个函数：

```js
export const vColor = (el, binding) => {
  el.style.color = binding.value
}
```

它等价于同时写了 `mounted` 和 `updated` 两个钩子。
:::

## 指令参数 binding

钩子的第二个参数是 `binding`，它包含了指令使用时的所有信息：

```html
<div v-demo:color.strong="'red'"></div>
```

```js
{
  value: 'red',        // 等号后面的值
  arg: 'color',        // 冒号后面的参数
  modifiers: { strong: true },  // 点号后面的修饰符
  oldValue: undefined, // 上一次的值（只在 updated 里有）
  instance: null,      // 使用这个指令的组件实例
}
```

对应关系：

| 写法里的部分 | binding 字段 | 例子 |
| --- | --- | --- |
| `v-demo="值"` | `value` | `'red'` |
| `v-demo:参数="值"` | `arg` | `'color'` |
| `v-demo.修饰符="值"` | `modifiers` | `{ strong: true }` |

值可以动态绑定，用 `v-demo="someRef"`，这样 `value` 会跟着变，`updated` 里能拿到新值。

## 实战一：v-focus

最简单也最常用的一个。做成一个能接受参数、支持“条件聚焦”的版本：

```js [src/directives/focus.js]
/**
 * v-focus —— 元素挂载后自动聚焦
 * 用法：
 *   <input v-focus />
 *   <input v-focus="shouldFocus" />
 */
export const vFocus = {
  mounted(el, binding) {
    // 没传值，或者传了真值，就聚焦
    const shouldFocus = binding.value === undefined ? true : binding.value
    if (shouldFocus) {
      el.focus()
    }
  },

  updated(el, binding) {
    // 值从 false 变成 true 时，补一次聚焦
    if (!binding.oldValue && binding.value) {
      el.focus()
    }
  }
}
```

用在活动编辑弹窗里：

```vue [src/components/ActivityForm.vue]
<template>
  <form>
    <!-- 弹窗一打开，标题输入框自动聚焦 -->
    <input v-focus v-model="form.title" placeholder="活动标题" />
    <input v-model="form.deadline" placeholder="报名截止时间" />

    <!-- 校验失败后 hasTitleError 变成 true，焦点被拉回标题框 -->
    <input v-if="hasTitleError" v-focus="hasTitleError" v-model="form.title" placeholder="标题不能为空" />
  </form>
</template>
```

::: warning 为什么是 `mounted` 而不是 `created`
`created` 钩子触发时元素还没插入 DOM，此时 `el.focus()` 不会有任何效果。

要等元素真的在页面上，才能聚焦、才能测量尺寸、才能绑定需要真实 DOM 的行为。
**凡是“操作元素本身”的，都放在 `mounted` 或之后。**
:::

## 实战二：v-debounce

给按钮加防抖。这个例子重点讲**怎么在 `unmounted` 里清理监听**。

```js [src/directives/debounce.js]
/**
 * v-debounce —— 给按钮的点击加防抖
 * 用法：
 *   <button v-debounce="search">搜索</button>
 *   <button v-debounce:500="search">搜索，防抖 500ms</button>
 */
export const vDebounce = {
  mounted(el, binding) {
    // 从指令参数拿延迟时间，默认 300ms
    const delay = Number(binding.arg) || 300

    // 保存定时器，放在 el 上，unmounted 时才能拿到并清掉
    let timer = null

    const handler = (event) => {
      // 防抖期间也要阻止默认行为，避免重复提交表单
      event.preventDefault()
      if (timer) clearTimeout(timer)
      timer = setTimeout(() => {
        binding.value(event)
        timer = null
      }, delay)
    }

    // 把监听函数存到元素上，卸载时按同一个引用移除
    el.__debounceHandler = handler
    el.addEventListener('click', handler)
  },

  unmounted(el) {
    // 关键：用同一个函数引用移除监听，否则监听还在，元素却被销毁了
    if (el.__debounceHandler) {
      el.removeEventListener('click', el.__debounceHandler)
      delete el.__debounceHandler
    }
  }
}
```

使用：

```vue [src/views/ActivityListView.vue]
<template>
  <input v-model="keyword" placeholder="搜索活动" />

  <!-- 点得再快，也只会在停下来 500ms 后执行一次 -->
  <button v-debounce:500="search">搜索</button>

  <button v-debounce="reset">重置</button>
</template>
```

::: warning 移除监听必须用同一个函数引用
`addEventListener` 和 `removeEventListener` 是靠“函数引用相同”来配对的。
下面这种写法**移除不掉**：

```js
// ✗ 两个匿名函数，引用不同，移除无效
el.addEventListener('click', () => doSomething())
el.removeEventListener('click', () => doSomething())
```

正确做法是把函数存下来（挂在 `el.__xxx` 上），两边用同一个引用。
`el.__xxx` 这种自定义属性是常见做法，加下划线前缀避免和原生属性撞名。
:::

::: details 防抖和节流的区别
- **防抖（debounce）**：连续触发时，只在**停下来之后**执行一次。
  典型场景：搜索框输入完再请求、按钮防重复点击。
- **节流（throttle）**：连续触发时，**每隔一段时间**执行一次。
  典型场景：滚动监听、拖拽时更新位置。

判断方法：**“停下来才算数”用防抖，“持续动作里按频率更新”用节流。**
案例 08 画板里的指针移动用的是节流，不然每一像素都要重画。
:::

## 实战三：v-permission

按钮级权限。没有对应权限时，把元素从 DOM 里移除。

```js [src/directives/permission.js]
/**
 * v-permission —— 按钮级权限控制
 * 用法：
 *   <button v-permission="'signup:review'">审核</button>
 *   <button v-permission="['activity:edit', 'activity:delete']">编辑</button>
 */
export const vPermission = {
  mounted(el, binding) {
    const required = binding.value
    const codes = Array.isArray(required) ? required : [required]
    const userPermissions = binding.instance?.$permissions ?? []

    // 只要有一个权限命中就放行
    const allowed = codes.some((code) => userPermissions.includes(code))

    if (!allowed) {
      // 直接把元素从父节点上摘掉
      el.parentNode?.removeChild(el)
      // 或者只隐藏：el.style.display = 'none'
    }
  }
}
```

::: danger 这只提升体验，真正的权限校验必须在后端
把按钮从页面上移除，**只是不让用户看到、点不到**。用户完全可以：

- 打开浏览器控制台，手动调用那个接口；
- 直接拿 token 去发请求。

**后端接口必须独立校验“当前用户有没有这个权限”，并且以它为准。**
前端做的事是“别让用户做无用功、别显示点了会报错的按钮”，不是安全防护。

课程项目答辩时，如果只有前端权限判断而后端不校验，这一项会被直接扣分。
:::

两种处理方式的取舍：

| 做法 | 效果 | 什么时候用 |
| --- | --- | --- |
| `removeChild` 移除元素 | 元素彻底不在 DOM 里 | 按钮完全不该存在 |
| `style.display = 'none'` 隐藏 | 元素还在，占位也没了 | 需要保留结构、或权限会动态变化 |

::: details 权限数据从哪来
指令里通过 `binding.instance.$permissions` 拿，需要你在应用启动时把它挂到全局属性上：

```js [src/main.js]
import { useAuthStore } from '@/stores/auth'

const app = createApp(App)
// 用 getter 保证每次取的是最新值
Object.defineProperty(app.config.globalProperties, '$permissions', {
  get: () => useAuthStore().permissions.value
})
```

但这已经是“全局状态”的范畴了，[单元 10](/unit10/01-when-global) 会用 Pinia 把它讲清楚。
现在只需要知道：**指令本身不产生数据，它只是判断 + 操作 DOM。**
:::

## 注册方式：局部与全局

**局部注册**：写在组件里，只有这个组件能用。

```vue [src/views/ActivityListView.vue]
<script setup>
import { vFocus } from '@/directives/focus'

// 局部注册的命名规则：v 开头 + 驼峰名字
// vFocus 在模板里用 v-focus
</script>

<template>
  <input v-focus />
</template>
```

**全局注册**：在 `main.js` 里注册，全项目都能用。

```js [src/main.js]
import { createApp } from 'vue'
import App from './App.vue'
import { vFocus } from '@/directives/focus'
import { vDebounce } from '@/directives/debounce'
import { vPermission } from '@/directives/permission'

const app = createApp(App)

// 第一个参数是“指令名”，不带 v- 前缀
app.directive('focus', vFocus)
app.directive('debounce', vDebounce)
app.directive('permission', vPermission)

app.mount('#app')
```

| 方式 | 作用范围 | 什么时候用 |
| --- | --- | --- |
| 局部 | 只有当前组件 | 只在一个页面用的、实验性的指令 |
| 全局 | 整个应用 | 通用能力（聚焦、权限），多处会用 |

::: danger 指令命名的坑
**注册时的名字不带 `v-` 前缀，使用时的名字带。**

```js
// ✗ 注册名写成了 v-focus
app.directive('v-focus', vFocus)
// 模板里写 v-focus 会报错：找不到指令 focus
```

```js
// ✓ 注册名是 focus
app.directive('focus', vFocus)
```

另外，**注册名里不要带大写字母**。`v-myDirective` 这种写法在 HTML 模板里会被浏览器
转成小写，导致匹配不上。多单词用短横线：`v-my-directive`，
或者用驼峰注册：`app.directive('myDirective', ...)`，模板里写 `v-my-directive`。
**项目里统一用短横线风格最省心。**
:::

::: details 指令 vs 组件，怎么选
| 问题 | 用指令 | 用组件 |
| --- | --- | --- |
| 需要产出自己的界面结构吗？ | 不需要，只是增强已有元素 | 需要，独立的一块界面 |
| 行为能靠 props / 事件表达吗？ | 能就用组件 | 优先组件 |
| 是不是“给元素做一件事”？ | 是，就用指令 | 不是 |

实在拿不准时的默认选择是**组件**：组件更显式、更好调试、更容易复用逻辑。
指令是“当组件表达不了时”的补充手段，不是首选。

典型能用指令的场景：聚焦、防抖、权限移除、拖拽、点击外部关闭。
这些都和“元素本身”强相关，用组件反而绕。
:::

## 小结

- 自定义指令解决“和元素绑定的通用行为”，写一次、注册后到处用。
- 三个常用钩子：`mounted`（初始化）、`updated`（值变化）、`unmounted`（清理）。
- `binding` 里有 `value`（等号的值）、`arg`（冒号参数）、`modifiers`（点号修饰符）。
- `v-focus` 在 `mounted` 里调用 `el.focus()`；`v-debounce` 要把监听函数存下来，
  在 `unmounted` 里用**同一个引用**移除。
- `v-permission` 移除元素只提升体验，**真正的权限校验必须由后端完成**。
- 注册名不带 `v-`、不带大写，多单词用短横线；全局注册在 `main.js`，局部注册在组件内。
- 能用组件表达的就别用指令，指令是补充手段。

## 常见坑

::: details 坑 1：注册名写成了 `v-focus`
现象：模板里用了 `v-focus`，控制台报“找不到指令 focus”。

原因：注册时的名字不该带 `v-` 前缀。

处理：`app.directive('focus', vFocus)`，模板里写 `v-focus`。
:::

::: details 坑 2：在 `created` 里操作 DOM
现象：`el.focus()` 没反应，或者 `el.offsetWidth` 是 0。

原因：`created` 时元素还没进 DOM。

处理：把 DOM 相关操作放到 `mounted` 里。需要等样式生效再测量时，
用 `nextTick` 或 `requestAnimationFrame` 再取。
:::

::: details 坑 3：`removeEventListener` 移除不掉
现象：组件销毁后，事件还在触发。

原因：`addEventListener` 和 `removeEventListener` 传的是两个不同的函数（通常是两个匿名
箭头函数）。

处理：把处理函数存成变量或挂在 `el.__xxx` 上，两边传同一个引用。
:::

::: details 坑 4：以为 `v-permission` 能防住接口
现象：以为前端藏了按钮就安全了。

原因：前端代码对用户完全可见，接口能被直接调用。

处理：后端每个涉及权限的接口都要校验当前用户。前端指令只负责体验。
:::

::: details 坑 5：指令动态改权限后没更新
现象：用户退出登录换了角色，按钮还在。

原因：指令默认只在 `mounted` 时判断一次。

处理：要么在 `updated` 里重新判断，要么用 `v-if` + 响应式的权限判断代替指令
（组件里改判断更容易追踪）。**权限频繁变化时，`v-if` 比指令更好维护。**
:::

## 课后练习

::: details 练习 1：实现 v-focus 并用在三个地方
写一个 `v-focus`，支持两种用法：不传值默认聚焦、传布尔值按条件聚焦。
用在活动编辑弹窗、报名表单、搜索框三处。

**思路**：参考实战一的写法。思考 `updated` 里为什么要判断 `!binding.oldValue && binding.value`。
:::

::: details 练习 2：实现 v-debounce 并验证清理
实现 `v-debounce:延迟`，在按钮上加日志验证“连点五次只执行一次”。
然后给按钮套上 `v-if` 切换显示，验证组件卸载后监听被清掉。

**思路**：`unmounted` 里移除监听。验证方法：在 `unmounted` 里打日志，
再用浏览器性能面板或反复 `addEventListener` 计数来确认没泄漏。
:::

::: details 练习 3：配合角色数据用 v-permission
假设角色数据是 `{ role: 'reviewer', permissions: ['signup:review'] }`，
用 `v-permission` 控制“审核通过”“驳回”“删除活动”三个按钮的显示。

**思路**：先想清楚这三个按钮各需要什么权限码，再把权限挂到全局属性上供指令读取。
写完后回答一个问题：**如果用户手动调接口，后端该怎么挡住？**（这一问是为了强化
“前端权限不是安全边界”这个认知。）
:::

---

上一节：[8.4 组合式函数](/unit08/04-composables) ·
下一节：[案例 06 · 模态框与全局通知](/unit08/06-case-modal)
