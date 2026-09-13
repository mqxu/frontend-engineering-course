# 案例 06 · 模态框与全局通知

## 案例要做什么

在活动列表页，每一行右侧有一个“下架”按钮，点它会弹出确认框。这个确认框要满足下面这些要求：

1. 半透明遮罩盖住整页，**背后的页面不能再滚动**，而且滚动条消失时页面不能左右抖一下。
2. 按 `Esc` 或点遮罩空白处可以关掉，点对话框内部不关。
3. 打开时焦点落在“确认下架”上，关闭后焦点回到刚才那个“下架”按钮，键盘用户不会“丢失位置”。
4. 出现和消失各有一段淡入加轻微上移的动画。
5. 点“确认下架”之后，右下角冒出一条绿色的“活动已下架”，三秒后自己消失；接口失败就冒一条红色的，要手动点掉。
6. 如果三条通知几乎同时来，它们要**上下堆叠**，不能互相盖住。

需求本身不大，但它把组件进阶里最容易写错的几个点一次碰全了：组件要怎么挂到 `body` 上、全局事件监听什么时候加什么时候撤、页面滚动怎么锁、焦点该落在哪、动画怎么进场出场、一堆消息怎么排队。**把这一篇的代码写对，等于把这几类问题都过一次手。**

### 用到的知识点 → 对应章节

| 用到的知识点 | 对应章节 |
| --- | --- |
| `<Teleport>` 把节点传送到 `body` | [8.3 内置组件](/unit08/03-builtin) |
| `<Transition>` 与 `<TransitionGroup>` 动画 | [8.3 内置组件](/unit08/03-builtin) |
| `provide` / `inject` 共享通知队列 | [8.2 依赖注入](/unit08/02-provide-inject) |
| 组合式函数抽取可复用逻辑 | [8.4 组合式函数](/unit08/04-composables) |
| 事件修饰符 `.self` | [6.2 事件与按键修饰符](/unit06/02-modifiers) |
| 按键修饰符与 `keydown` 里的 `key` 判断 | [6.2 事件与按键修饰符](/unit06/02-modifiers) |
| `watch` 与 `nextTick` | [5.2 侦听器](/unit05/02-watch) |
| `ref` 与模板引用 | [4.4 ref 与 reactive](/unit04/04-reactivity) |
| 自定义指令 `v-focus`（可选的另一种做法） | [8.5 自定义指令](/unit08/05-directives) |

做完之后，你可以用下面这几条自己验收，每一条都能在浏览器里手动试出来：

- 打开模态框，用鼠标滚轮滚滚看，背后页面的表格纹丝不动，而且页面没有横向跳动。
- 按 Tab 键，焦点在模态框内部的几个按钮之间走，不会跑到背后的列表上。
- 按 `Esc` 关闭，再按 Tab，焦点回到刚才那个“下架”按钮上。
- 快速连点三次不同行的“下架”，模态框里显示的是**最后一次**点的那个活动标题。
- 打开 DevTools 的 Elements 面板，看到模态框的 DOM 节点直接挂在 `<body>` 下，而不是嵌套在列表容器里。
- 连续触发三条通知，三条上下排开、互不遮挡，各自到时间后单独消失。

## 数据结构与接口设计

先定数据，再写界面。这个案例有两份数据：一份描述“当前这个模态框”，一份描述“当前堆着的通知”。

### 模态框的状态

模态框只有一个实例被复用在多个业务上，所以它是**受控组件**：打开关闭由外部传 `visible`，删除、确认这类动作通过事件抛出去。

```js [src/components/AppModal.vue 的 props 与事件设计]
// props
{
  visible: Boolean,        // 由外部控制，必须用 v-model:visible 传
  title: String,
  confirmText: String,     // 默认“确定”
  cancelText: String,      // 默认“取消”
  confirmLoading: Boolean, // 请求进行中：按钮转圈并禁用
  closeOnMask: Boolean,    // 默认 true，允许点遮罩关闭
  closeOnEsc: Boolean      // 默认 true，允许按 Esc 关闭
}

// 事件
'update:visible' // 关闭时通知外部改 visible
'confirm'        // 点了确认按钮
'cancel'         // 点了取消、×、遮罩或按了 Esc
```

为什么不把 `visible` 直接放在模态框内部管理？因为**打开和关闭的时机往往是业务决定的**（比如“接口失败时不关，成功后自动关”）。状态放在页面里，模态框只管渲染和回报动作，职责最清楚。

### 通知的数据结构

```js [src/composables/useToast.js 里的一条通知]
{
  id: 1,                      // 自增主键，同时也是 TransitionGroup 的 :key
  type: 'success',            // success | error | warning | info
  message: '活动已下架',
  duration: 3000              // 毫秒；传 0 表示不自动消失
}
```

队列用一个 `reactive` 的数组承载，模块级单例，整个应用共用一份。这样任何组件只要 `import { toast }` 就能弹消息，不必挂在组件树上。

这里有一个容易被忽略的点：**通知的 `id` 必须由队列自己生成，不能由调用方传入。** 如果调用方各写各的 `id`（有人用时间戳、有人用活动 ID），很快就会出现两条通知 `id` 相同，`TransitionGroup` 的动画当场错乱。把生成权收在 `push` 内部，用自增计数器，是最省心的做法。

### 三个设计决定

把上面的数据结构落成代码之前，有三个选择先定下来，后面写起来会顺很多：

| 决定 | 选哪个 | 理由 |
| --- | --- | --- |
| 模态框的开关状态放哪 | 放在调用它的页面里，组件用 `visible` 受控 | 开关时机由业务决定，组件不猜 |
| 一动一静的样式怎么分 | 结构、动画、主题色都放组件自己的 `<style scoped>` | Teleport 之后外部选择器选不中，样式留在组件里最稳 |
| 通知队列放哪 | 独立模块，模块级单例 | “到处都要弹”的东西不适合绑在组件树上 |

这三个决定背后是同一条标准：**谁最清楚这件事，就把决定权放在谁那里。** 页面最清楚什么时候该弹、该关；组件最清楚自己长什么样、怎么动；队列最清楚当前有几条通知、哪条该消失。

### 接口约定

下架是**独立标记**，不改活动的 `status` 字段（草稿、报名中、报名截止、已结束这套状态照样走）。接口设计如下：

```js [src/api/activity.js]
import request from './request'

// 下架：只是把活动从学生端隐藏，报名记录全部保留
export function offlineActivity(id) {
  return request.post(`/api/activity/${id}/offline`)
}

// 恢复上架
export function restoreActivity(id) {
  return request.post(`/api/activity/${id}/restore`)
}
```

```js [src/api/request.js（最小可用的请求层，完整版见单元 10）]
import axios from 'axios'
import { toast } from '@/composables/useToast'

const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 10000
})

request.interceptors.response.use(
  (res) => res.data.data,
  (err) => {
    // 统一把后端消息翻译成一句人能看懂的话
    const msg = err.response?.data?.message || '网络异常，请稍后重试'
    // 这里返回 reject 的对象里带上 message，调用方 catch 时直接可用
    return Promise.reject(new Error(msg))
  }
)

export default request
```

## 实现步骤

### 第一步：用 Teleport 把模态框挂到 body 上

模态框最常见的坑是**被父元素的样式剪掉**。比如页面里有个容器写了 `overflow: hidden` 或者 `transform: translateZ(0)`，模态框写在它里面，就会出现“遮罩只盖住半个屏幕”或者“滚动容器一滚，模态框跟着跑”。

`<Teleport>` 的做法是：**代码写在组件里，DOM 渲染到别处**。

```vue [src/components/AppModal.vue]
<script setup>
const props = defineProps({
  visible: { type: Boolean, default: false },
  title: { type: String, default: '' },
  confirmText: { type: String, default: '确定' },
  cancelText: { type: String, default: '取消' },
  confirmLoading: { type: Boolean, default: false }
})

const emit = defineEmits(['update:visible', 'confirm', 'cancel'])

function close() {
  emit('update:visible', false)
  emit('cancel')
}
</script>

<template>
  <!-- 渲染位置被传送到 body，但样式作用域、响应式都还挂在这个组件上 -->
  <Teleport to="body">
    <div v-if="visible" class="modal-mask" @click.self="close">
      <div class="modal" role="dialog" aria-modal="true" tabindex="-1">
        <header class="modal__header">
          <h3>{{ title }}</h3>
          <button class="modal__close" type="button" @click="close">×</button>
        </header>

        <div class="modal__body">
          <slot>确定要执行这个操作吗？</slot>
        </div>

        <footer class="modal__footer">
          <button type="button" @click="close">{{ cancelText }}</button>
          <button type="button" :disabled="confirmLoading" @click="emit('confirm')">
            {{ confirmLoading ? '处理中…' : confirmText }}
          </button>
        </footer>
      </div>
    </div>
  </Teleport>
</template>
```

有两个地方值得留意。

**第一，`@click.self` 不能换成 `@click.stop` 写在外层。** `.self` 的意思是“只有事件目标就是遮罩本身时才执行”，点对话框内部时目标不是遮罩，函数不执行。而 `.stop` 写在外层拦的是“继续往外冒泡”，处理函数照样会被调用 —— 点内容还是会关。这个区分在[6.2](/unit06/02-modifiers)里详细讲过。

**第二，`<style scoped>` 对 Teleport 的内容仍然生效。** Vue 编译时给元素打上的 `data-v-xxx` 属性会跟着元素一起被搬运，所以不必担心样式丢失。真正会出问题的是**样式写在父组件、且靠父子选择器选中**的那种，这部分后面在“常见坑”里说。

### 第二步：ESC 关闭与滚动锁定

`Esc` 要监听在 `document` 上，不能挂在对话框上 —— 用户点了一下页面空白处之后，焦点可能已经不在对话框里了，挂在自己身上会失灵。既然是全局监听，就必须**在关闭时或组件卸载时撤掉**，否则关闭十次就加了十个监听。

```vue [src/components/AppModal.vue（只展示新增部分）]
<script setup>
import { watch, onBeforeUnmount } from 'vue'
import { useScrollLock } from '@/composables/useScrollLock'

const props = defineProps({
  visible: { type: Boolean, default: false },
  closeOnEsc: { type: Boolean, default: true }
  // ……其余同上
})

function onKeydown(event) {
  if (event.key !== 'Escape') return
  // 阻止事件继续传到更外层的处理器，避免“按一次 Esc 关掉两层”
  event.stopPropagation()
  close()
}

// 打开时才开始监听，关闭立刻撤掉
watch(
  () => props.visible,
  (visible) => {
    if (visible && props.closeOnEsc) {
      document.addEventListener('keydown', onKeydown)
    } else {
      document.removeEventListener('keydown', onKeydown)
    }
  }
)

// 兜底：组件被卸载时也要撤
onBeforeUnmount(() => document.removeEventListener('keydown', onKeydown))

// 打开时锁定页面滚动
useScrollLock(() => props.visible)
</script>
```

滚动锁定看起来简单，直接 `document.body.style.overflow = 'hidden'` 就行了。但这么做会带来两个副作用：

1. **滚动条消失，页面宽度变大，整个页面往右跳一下。** 尤其是内容居中的布局，跳动非常明显。
2. **多个模态框嵌套时，内层关闭会把外层的锁定也一起解掉。**

所以真正的实现要多算一步“滚动条宽度”，并用计数处理嵌套：

```js [src/composables/useScrollLock.js]
import { watch } from 'vue'

// 模块级变量：一份锁，全应用共用
let lockCount = 0
let savedOverflow = ''
let savedPaddingRight = ''

function applyLock() {
  // 滚动条宽度 = 视口宽度 - 文档可用宽度（页面没有滚动条时结果是 0）
  const scrollBarWidth = window.innerWidth - document.documentElement.clientWidth

  savedOverflow = document.body.style.overflow
  savedPaddingRight = document.body.style.paddingRight

  document.body.style.overflow = 'hidden'

  // 补偿被滚动条占掉的那点宽度，页面就不会因为滚动条消失而抖动
  if (scrollBarWidth > 0) {
    const base = Number.parseFloat(getComputedStyle(document.body).paddingRight) || 0
    document.body.style.paddingRight = `${base + scrollBarWidth}px`
  }
}

function releaseLock() {
  document.body.style.overflow = savedOverflow
  document.body.style.paddingRight = savedPaddingRight
}

/**
 * @param {import('vue').Ref<boolean> | (() => boolean)} isLocked
 */
export function useScrollLock(isLocked) {
  watch(
    isLocked,
    (locked) => {
      if (locked) {
        // 只有第一个锁才真正动 DOM
        if (lockCount === 0) applyLock()
        lockCount += 1
      } else {
        lockCount = Math.max(0, lockCount - 1)
        // 全部解锁后才恢复
        if (lockCount === 0) releaseLock()
      }
    },
    { immediate: true }
  )
}
```

::: tip 用 `scrollbar-gutter` 会更省事吗
CSS 的 `scrollbar-gutter: stable` 可以让容器一直给滚动条留位置，就不必用 JS 算宽度了。但它对移动端和部分旧版浏览器的支持还不一致，而且项目里已经有滚动容器用了 `overflow: auto` 的话，全局设置不一定接管得了。**作为课程实现，JS 补偿是最稳的做法**；知道有 `scrollbar-gutter` 这个东西就行。
:::

### 第三步：焦点管理

键盘用户和读屏用户完全依赖焦点。模态框打开后焦点如果还留在背后的页面上，按 Tab 会跑到遮罩底下的按钮上去，体验是崩的。要做三件事：

1. 打开瞬间记住“之前焦点在哪”。
2. 把焦点移进对话框。
3. 关闭时把焦点还回去。

```vue [src/components/AppModal.vue（新增焦点管理）]
<script setup>
import { ref, watch, nextTick, useTemplateRef } from 'vue'

const dialogRef = useTemplateRef('dialog')
// 打开之前焦点的元素，关闭时要还给它
let lastActiveElement = null

watch(
  () => props.visible,
  async (visible) => {
    if (visible) {
      lastActiveElement = document.activeElement
      // 等 DOM 渲染出来再聚焦，v-if 刚打开时元素还不存在
      await nextTick()
      const target =
        dialogRef.value?.querySelector('[data-autofocus]') ?? dialogRef.value
      target?.focus()
    } else {
      // 那个元素可能已经被列表刷新移除了，先判断还挂在文档上
      if (lastActiveElement?.isConnected) lastActiveElement.focus()
      lastActiveElement = null
    }
  }
)
</script>

<template>
  <Teleport to="body">
    <div v-if="visible" class="modal-mask" @click.self="close">
      <!-- 对话框本身可聚焦，作为兜底的焦点落点 -->
      <div ref="dialog" class="modal" role="dialog" aria-modal="true" tabindex="-1">
        <header class="modal__header">
          <h3>{{ title }}</h3>
          <button class="modal__close" type="button" @click="close">×</button>
        </header>

        <div class="modal__body">
          <slot>确定要执行这个操作吗？</slot>
        </div>

        <footer class="modal__footer">
          <button type="button" @click="close">{{ cancelText }}</button>
          <!-- 打开后自动聚焦到这里 -->
          <button
            type="button"
            data-autofocus
            :disabled="confirmLoading"
            @click="emit('confirm')"
          >
            {{ confirmLoading ? '处理中…' : confirmText }}
          </button>
        </footer>
      </div>
    </div>
  </Teleport>
</template>
```

`useTemplateRef('dialog')` 是 Vue 3.5 新增的写法，等价于“声明一个和 `ref` 属性同名的模板引用”。如果项目还在 3.4，写成 `const dialogRef = ref(null)` 一样能跑。

::: warning `document.activeElement` 在打开瞬间可能不是按钮
如果“下架”按钮在点击后触发了列表重新渲染，`document.activeElement` 可能已经变成 `body`（旧按钮被移除）。这时关闭后焦点还原就等于没还原。

更稳的做法不是记 `activeElement`，而是**把触发元素的引用传进来**：

```js
// 页面里
const triggerEl = ref(null)
// <button ref="triggerEl" @click="open">
// 关闭后：triggerEl.value?.focus()
```

本案例为了通用性用了 `activeElement` 方案，并在还原前判断 `isConnected`。你在项目里可以按实际情况二选一。
:::

### 第四步：进出场动画

`<Transition>` 配合 `v-if` 就能做动画，样式类名由 `name` 决定。默认名字是 `v-`，改名成 `modal` 之后类名就变成 `modal-enter-from` 这一套。

```vue [src/components/AppModal.vue（模板部分）]
<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="visible" class="modal-mask" @click.self="close">
        <div ref="dialog" class="modal" role="dialog" aria-modal="true" tabindex="-1">
          <!-- 内容同上，省略 -->
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.modal-mask {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgb(0 0 0 / 45%);
  z-index: 1000;
}

.modal {
  width: min(480px, calc(100vw - 32px));
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 12px 32px rgb(0 0 0 / 18%);
  padding: 20px;
}

/* 进入前、离开后：整层透明，对话框略微上移并缩小 */
.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-from .modal,
.modal-leave-to .modal {
  transform: translateY(-12px) scale(0.96);
}

/* 过渡进行中：把 transition 属性挂上 */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.2s ease;
}

.modal-enter-active .modal,
.modal-leave-active .modal {
  transition: transform 0.2s ease;
}
</style>
```

四个阶段的含义固定死了，记住一条就够：**`-from` 是起点，`-to` 是终点，`-active` 表示“这段时间内过渡属性生效”。**

| 类名 | 什么时候加 | 什么时候移除 |
| --- | --- | --- |
| `modal-enter-from` | 进入前的一帧 | 进入开始的下一帧 |
| `modal-enter-active` | 进入开始 | 进入结束 |
| `modal-enter-to` | 进入开始后的下一帧 | 进入结束 |
| `modal-leave-from` | 离开前的一帧 | 离开开始的下一帧 |
| `modal-leave-active` | 离开开始 | 离开结束 |
| `modal-leave-to` | 离开开始后的下一帧 | 离开结束 |

::: details 动画期间元素还占着 DOM 吗
进入动画时元素已经在 DOM 里了；离开动画时元素**还没被移除**，等动画结束才删。所以离开动画播到一半时，遮罩仍然挡着页面 —— 这就是为什么滚动锁要等动画结束（组件更新）时才解，而不是在 `emit('update:visible', false)` 的那一刻解。

如果希望离开动画期间遮罩不再拦截点击，可以加 `.modal-leave-active { pointer-events: none; }`。
:::

### 第五步：通知队列

通知的难点不在“怎么显示一条”，而在“怎么管住同时来的好几条”。做法是**把队列抽成一个模块级单例**，组件只负责渲染。

```js [src/composables/useToast.js]
import { reactive, readonly } from 'vue'

// 自增 id：保证 TransitionGroup 的 :key 不重复
let seed = 0
const DEFAULT_DURATION = 3000

const state = reactive({
  items: []
})

function push(type, message, duration = DEFAULT_DURATION) {
  const id = ++seed
  state.items.push({ id, type, message, duration })

  // duration 为 0 表示“不自动消失”，交给用户手动点掉
  if (duration > 0) {
    window.setTimeout(() => remove(id), duration)
  }
  return id
}

function remove(id) {
  const index = state.items.findIndex((item) => item.id === id)
  if (index > -1) state.items.splice(index, 1)
}

export const toast = {
  success: (message, duration) => push('success', message, duration),
  error: (message, duration) => push('error', message, duration),
  warning: (message, duration) => push('warning', message, duration),
  info: (message, duration) => push('info', message, duration),
  remove
}

// 组件里拿到的永远是只读视图，想加想删都只能走上面那组方法
export function useToastList() {
  return readonly(state)
}
```

这里有两个细节值得说：

- **返回 `readonly(state)` 而不是 `state`。** 组件如果直接 `state.items.push(...)`，等于绕过了计时器管理，会出现“一条通知永远不会消失”。只暴露只读视图，能把“谁能改队列”这件事写清楚，和 [8.2](/unit08/02-provide-inject)里讲 `readonly` 的道理一样。
- **用 `window.setTimeout` 而不是直接 `setTimeout`。** 在浏览器里两者一样，但显式写 `window.` 能让读代码的人立刻知道这是个浏览器计时器，也方便静态检查工具识别。

渲染队列的组件挂在根节点上，全局只需要一个：

```vue [src/components/ToastHost.vue]
<script setup>
import { toast, useToastList } from '@/composables/useToast'

const state = useToastList()
</script>

<template>
  <Teleport to="body">
    <div class="toast-host">
      <TransitionGroup name="toast">
        <div
          v-for="item in state.items"
          :key="item.id"
          class="toast"
          :class="`toast--${item.type}`"
          role="status"
          aria-live="polite"
        >
          <span class="toast__message">{{ item.message }}</span>
          <button
            class="toast__close"
            type="button"
            aria-label="关闭提示"
            @click="toast.remove(item.id)"
          >
            ×
          </button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<style scoped>
.toast-host {
  position: fixed;
  right: 24px;
  bottom: 24px;
  display: flex;
  flex-direction: column; /* 新的在下，旧的往上推 */
  gap: 8px;
  z-index: 1100;
  /* 容器本身不挡点击，只让每条通知挡 */
  pointer-events: none;
}

.toast {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 220px;
  max-width: 360px;
  padding: 10px 14px;
  border-radius: 6px;
  background: #fff;
  box-shadow: 0 6px 20px rgb(0 0 0 / 15%);
  pointer-events: auto;
}

.toast--success {
  border-left: 4px solid #42b883;
}
.toast--error {
  border-left: 4px solid #f56c6c;
}
.toast--warning {
  border-left: 4px solid #e6a23c;
}
.toast--info {
  border-left: 4px solid #909399;
}

.toast__message {
  flex: 1;
  font-size: 14px;
}

/* 进出场：从右侧滑入 */
.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateX(24px);
}

.toast-enter-active,
.toast-leave-active {
  transition: all 0.24s ease;
}

/* 离开时把高度也收掉，后面的通知才会补位而不是瞬间跳过去 */
.toast-leave-active {
  position: absolute;
  width: 100%;
}
</style>
```

`<TransitionGroup>` 比 `<Transition>` 多管两件事：**它会给列表里每一项单独做进出场动画，并且在项被移除后自动重排位置**。所以 `:key` 必须稳定唯一 —— 用数组下标当 `key` 的话，删掉第一项时下标会整体前移，动画就会错乱。

::: details 也可以用 provide / inject 来分发给子树
把队列放到模块里，优点是“任何地方都能 import 到”，缺点是整个应用只有一份，做不了“某个区域单独一套通知”。

如果想把它限制在某棵子树里（比如后台管理页用的是自己的通知样式），可以换成注入：

```js [src/composables/toast-key.js]
export const TOAST_KEY = Symbol('toast')
```

```vue [src/layouts/AdminLayout.vue（提供方）]
<script setup>
import { ref, provide } from 'vue'
import { TOAST_KEY } from '@/composables/toast-key'

const items = ref([])

function push(type, message, duration = 3000) {
  const id = Date.now() + Math.random()
  items.value.push({ id, type, message })
  if (duration > 0) window.setTimeout(() => remove(id), duration)
}

function remove(id) {
  items.value = items.value.filter((item) => item.id !== id)
}

provide(TOAST_KEY, { items, push, remove })
</script>
```

```js [深层组件（使用方）]
import { inject } from 'vue'
import { TOAST_KEY } from '@/composables/toast-key'

const { push } = inject(TOAST_KEY)
push('success', '审核通过')
```

注入版本更“局部”，但每个需要它的组件都得确保自己在提供方的子树里，否则 `inject` 会拿到 `undefined`。**做全局通知这种“到处都要用”的功能，模块函数版本更省事；做“局部一套主题”的时候，注入版本更合适。** 判断标准和[8.2 的决策表](/unit08/02-provide-inject)是一致的。
:::

### 第六步：把业务串起来

把模态框和通知都装好之后，页面代码会变得很短 —— 它只负责“什么时候打开、确认后调什么接口、结果怎么反馈”。

先让通知宿主全局只挂一个：

```vue [src/App.vue]
<script setup>
import ToastHost from '@/components/ToastHost.vue'
</script>

<template>
  <RouterView />
  <ToastHost />
</template>
```

再写下架确认的逻辑：

```vue [src/views/ActivityListView.vue]
<script setup>
import { ref } from 'vue'
import AppModal from '@/components/AppModal.vue'
import { offlineActivity } from '@/api/activity'
import { toast } from '@/composables/useToast'

const activities = ref([
  { id: 1, title: '校园歌手大赛', status: 'open', offline: false },
  { id: 2, title: '前端技术分享会', status: 'closed', offline: false }
])

const modalVisible = ref(false)
const submitting = ref(false)
const currentActivity = ref(null)

function askOffline(activity) {
  currentActivity.value = activity
  modalVisible.value = true
}

async function handleConfirm() {
  if (!currentActivity.value) return
  submitting.value = true
  try {
    await offlineActivity(currentActivity.value.id)
    currentActivity.value.offline = true
    modalVisible.value = false
    toast.success('活动已下架')
  } catch (error) {
    // 失败时不关闭模态框，让用户能重试
    toast.error(error.message, 0)
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="activity-list">
    <table>
      <thead>
        <tr>
          <th>活动标题</th>
          <th>状态</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="activity in activities" :key="activity.id">
          <td>{{ activity.title }}</td>
          <td>{{ activity.offline ? '已下架' : '上架中' }}</td>
          <td>
            <button
              type="button"
              :disabled="activity.offline"
              @click="askOffline(activity)"
            >
              下架
            </button>
          </td>
        </tr>
      </tbody>
    </table>

    <!-- 受控模态框：v-model:visible 双向绑定 -->
    <AppModal
      v-model:visible="modalVisible"
      title="确认下架"
      confirm-text="确认下架"
      :confirm-loading="submitting"
      @confirm="handleConfirm"
    >
      下架后学生端将不再展示“{{ currentActivity?.title }}”，
      已通过审核的报名记录会保留。确定要下架吗？
    </AppModal>
  </div>
</template>
```

注意失败提示传了 `0`，意思是**这条错误不自动消失**。成功的绿条三秒就走，失败的必须让用户看到，这是通知设计里一条很实用的原则。

## 完整代码

把上面的片段拼成能直接跑的文件。目录结构：

```text [src/]
src/
├── api/
│   ├── activity.js
│   └── request.js
├── components/
│   ├── AppModal.vue
│   └── ToastHost.vue
├── composables/
│   ├── useScrollLock.js
│   └── useToast.js
├── views/
│   └── ActivityListView.vue
└── App.vue
```

```vue [src/components/AppModal.vue]
<script setup>
import { watch, nextTick, onBeforeUnmount, useTemplateRef } from 'vue'
import { useScrollLock } from '@/composables/useScrollLock'

const props = defineProps({
  visible: { type: Boolean, default: false },
  title: { type: String, default: '' },
  confirmText: { type: String, default: '确定' },
  cancelText: { type: String, default: '取消' },
  confirmLoading: { type: Boolean, default: false },
  closeOnMask: { type: Boolean, default: true },
  closeOnEsc: { type: Boolean, default: true }
})

const emit = defineEmits(['update:visible', 'confirm', 'cancel'])

const dialogRef = useTemplateRef('dialog')
let lastActiveElement = null

function close() {
  emit('update:visible', false)
  emit('cancel')
}

function onMaskClick() {
  if (props.closeOnMask) close()
}

function onKeydown(event) {
  if (!props.closeOnEsc || event.key !== 'Escape') return
  event.stopPropagation()
  close()
}

watch(
  () => props.visible,
  async (visible) => {
    if (visible) {
      lastActiveElement = document.activeElement
      document.addEventListener('keydown', onKeydown)
      await nextTick()
      const target =
        dialogRef.value?.querySelector('[data-autofocus]') ?? dialogRef.value
      target?.focus()
    } else {
      document.removeEventListener('keydown', onKeydown)
      if (lastActiveElement?.isConnected) lastActiveElement.focus()
      lastActiveElement = null
    }
  }
)

onBeforeUnmount(() => document.removeEventListener('keydown', onKeydown))

useScrollLock(() => props.visible)
</script>

<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="visible" class="modal-mask" @click.self="onMaskClick">
        <div
          ref="dialog"
          class="modal"
          role="dialog"
          aria-modal="true"
          tabindex="-1"
        >
          <header class="modal__header">
            <h3>{{ title }}</h3>
            <button class="modal__close" type="button" @click="close">×</button>
          </header>

          <div class="modal__body">
            <slot>确定要执行这个操作吗？</slot>
          </div>

          <footer class="modal__footer">
            <button type="button" @click="close">{{ cancelText }}</button>
            <button
              type="button"
              data-autofocus
              :disabled="confirmLoading"
              @click="emit('confirm')"
            >
              {{ confirmLoading ? '处理中…' : confirmText }}
            </button>
          </footer>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.modal-mask {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgb(0 0 0 / 45%);
  z-index: 1000;
}

.modal {
  width: min(480px, calc(100vw - 32px));
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 12px 32px rgb(0 0 0 / 18%);
  padding: 20px;
}

.modal__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.modal__close {
  border: none;
  background: transparent;
  font-size: 20px;
  line-height: 1;
  cursor: pointer;
}

.modal__footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 20px;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-from .modal,
.modal-leave-to .modal {
  transform: translateY(-12px) scale(0.96);
}

.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.2s ease;
}

.modal-enter-active .modal,
.modal-leave-active .modal {
  transition: transform 0.2s ease;
}
</style>
```

剩余的 `useScrollLock.js`、`useToast.js`、`ToastHost.vue`、`App.vue`、`ActivityListView.vue` 与实现步骤里给出的完全一致，这里不再重复。

## 常见坑

::: details 坑 1：直接把 `overflow: hidden` 加在 body 上，页面还是能滚
**现象**：模态框打开后，鼠标滚轮照样能让背后的页面滚动。

**原因**：项目里通常有一个 `.app-main { overflow: auto; height: 100vh; }` 之类的**滚动容器**，真正在滚的是它，不是 `body`。锁住 `body` 对它没有影响。

**怎么处理**：先确认到底是谁在滚。打开 DevTools，选中页面主体，看它的 `overflow` 和高度。锁定时把那个容器也一起锁，或者干脆让页面整体由 `body` 滚动（布局改成 `min-height: 100vh`，不要写死高度加 `overflow: auto`）。
:::

::: details 坑 2：滚动条消失导致页面横向跳一下
**现象**：打开模态框的瞬间，居中的内容往右挪了几像素，关闭后又挪回来。

**原因**：`overflow: hidden` 之后滚动条没了，可用宽度多出十几像素，居中布局跟着重新计算。

**怎么处理**：按本文的 `useScrollLock` 那样，用 `window.innerWidth - document.documentElement.clientWidth` 算出滚动条宽度，补给 `padding-right`。注意是**加到已有的 `padding-right` 上**，不是直接覆盖 —— 页面本身有内边距时直接覆盖会让内容贴边。
:::

::: details 坑 3：按下 `Esc`，两层模态框一起关了
**现象**：模态框里再开一个确认框，按一次 `Esc` 两个都关。

**原因**：两个实例都在 `document` 上监听了 `keydown`，事件同时到达两个监听器。

**怎么处理**：本案例里加了 `event.stopPropagation()`，但它只能拦住冒泡到更外层元素的监听器，**拦不住同一个元素上的其他监听器**。嵌套模态框要靠“只让最上层响应”来解，做法是维护一个打开栈，只有栈顶的实例处理 `Esc`。作为练习留在下面。
:::

::: details 坑 4：关闭后焦点丢了，Tab 又跑回页面顶部
**现象**：关闭模态框后按 Tab，焦点从头开始走一遍。

**原因**：关闭时没有把焦点还给触发它的按钮，浏览器把焦点留在了刚被移除的对话框上，于是回退到 `body`。

**怎么处理**：打开时记录触发元素，关闭时 `focus()` 回去。注意判断元素是否还在文档里（`isConnected`），列表刷新后旧按钮可能已经被删了。
:::

::: details 坑 5：通知的 `:key` 用了下标，删除时动画错乱
**现象**：同时来了三条通知，删掉中间一条，剩下的两条动画闪一下。

**原因**：用 `index` 当 `key`，删除后后面每一项的 `index` 都变了，Vue 认为“这些都不是原来的元素”，于是重新创建。这正是[5.4 列表渲染](/unit05/04-list)里强调过的问题。

**怎么处理**：用自增的 `id` 当 `key`。本案例里的 `seed` 就是干这个的。
:::

::: details 坑 6：点对话框里的输入框，模态框被关掉了
**现象**：在模态框里输入文字，点一下文本框，框没了。

**原因**：遮罩上的处理函数没有用 `.self`，事件从输入框冒泡到遮罩，函数被触发。

**怎么处理**：遮罩用 `@click.self`。不要用 `.stop` 写在外层，那个方向是反的，具体原因见[6.2](/unit06/02-modifiers)。
:::

::: details 坑 7：Teleport 之后父组件的样式选不中了
**现象**：在父组件里写 `.dialog-wrapper .modal { ... }`，模态框样式不生效。

**原因**：`<Teleport>` 只搬运 DOM 节点，**不改变组件树的父子关系**。所以元素已经被移出父组件渲染的 DOM 子树，父组件基于“DOM 祖先”写的选择器自然选不中。

**怎么处理**：样式写在模态框组件自己的 `<style scoped>` 里。需要外部微调时，用 `:deep()` 或者定义一个 CSS 变量，别指望靠 DOM 层级去选。
:::

::: details 坑 8：计时器没清，组件卸载后还在改状态
**现象**：控制台偶尔报“Cannot read properties of null”或者通知已经关了又自己冒出来。

**原因**：`setTimeout` 里的回调持有组件作用域的变量，卸载后仍然会执行。

**怎么处理**：本案例的通知队列在模块级，天然不会随组件卸载消失，但要保证 `remove` 是幂等的（找不到就什么都不做）。如果计时器写在组件里，一定要在 `onBeforeUnmount` 里 `clearTimeout`。
:::

## 扩展练习

::: details 练习 1：做一个“打开栈”，只让最上层模态框响应 Esc
给 `AppModal` 加一个模块级的打开栈：打开时 `push` 自己，关闭时移除，`Esc` 处理函数先判断自己是不是栈顶，不是就直接返回。写完验证“两层模态框按一次 `Esc` 只关最上面那层”。

**思路**：栈里存什么？存组件实例、存一个递增的层号都行。关键是要处理“不是通过 `Esc` 关闭”的情况（比如点了取消按钮），也要把栈里的记录清掉，否则栈会越长越高。
:::

::: details 练习 2：给 Toast 加鼠标悬停暂停
鼠标移进某条通知时，它的倒计时暂停；移出去再继续。这样用户不会“刚要看清楚就消失了”。

**思路**：把每条通知的 `setTimeout` 句柄存下来，悬停时 `clearTimeout` 并记录已经过去的时间，移除时用剩余时间重新 `setTimeout`。注意本案例里计时器写在 `push` 里，抽成独立函数会更清楚。想更稳的话可以用 `requestAnimationFrame` 或者给每条通知记 `createdAt` 和 `remain`。
:::

::: details 练习 3：把模态框的确认按钮换成“需要输入文字才能确认”
有些危险操作（比如删除整个活动）要求用户输入活动标题才能确认。给 `AppModal` 加一个可选的 `confirmText` 校验：传了 `requireInput` 时，`AppModal` 内部渲染一个输入框，只有输入内容与 `expectedText` 完全一致，确认按钮才可点。

**思路**：这会让 `AppModal` 从“通用壳”变得有点重。想清楚它是应该加更多 props，还是干脆拆一个 `DangerConfirmModal` 组件专门管这件事。**功能能加，但组件职责别混**，这是练习的重点。
:::

::: details 练习 4：让通知支持带操作按钮
给通知加上可选的“撤销”按钮，点击后执行一个回调并立刻移除这条通知。用在下架成功之后“撤销下架”的场景上。

**思路**：`push` 的参数从位置参数改成对象更合适：`toast.success({ message, duration, action: { text: '撤销', onClick } })`。想一下 `onClick` 执行后要不要重新计时、如果用户没点，超时后这条通知的“撤销权”是不是就失效了 —— **这类问题的答案取决于业务，而不是取决于代码好不好写。**
:::

---

上一页：[案例 05 · Markdown 编辑器](/cases/05-markdown) · 下一页：[案例 07 · 多步表单](/cases/07-wizard)
