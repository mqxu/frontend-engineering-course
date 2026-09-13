# 案例 06 · 模态框与全局通知（进阶档）

## 这个案例做什么

把前面几节学的东西拼成一个**全站都能用的弹窗与提示系统**：

1. 一个用 `Teleport` 送到 `body` 下的模态框，能锁背景滚动、能按 Esc 关闭、
   关闭后焦点回到原来的位置。
2. 一个不依赖 Pinia 的全局状态：模块级的 `ref`。
3. 一个 `useToast` 组合式函数，任何地方调用 `push('报名审核通过')` 就能弹出一条提示，
   能自动消失、能手动关闭、多条堆叠。
4. 用 `TransitionGroup` 做提示进出的补位动画。

::: tip 为什么选这个案例
弹窗和提示是每个管理端项目都要用的东西，也是**最容易写出一堆问题**的东西：
被父容器裁掉、背景还能滚动、按 Tab 焦点跑出去了、关闭后不知道焦点飞哪去了。
这个案例把这些坑一次性讲清楚。
:::

## 第一部分：Teleport 模态框

### 先看不用 Teleport 会怎样

活动列表页的结构大概是这样：

```text
ActivityListView
└── .page-container      overflow: hidden; position: relative
    └── .table-wrap      overflow: auto
        └── ConfirmDialog  ← 弹窗在这里，会被裁剪
```

弹窗写在 `.table-wrap` 里面，超出容器的部分就被切掉了。你加 `z-index: 9999` 也没用 ——
`.table-wrap` 有自己的定位上下文，里面的 `z-index` 只在它内部比较。

**解决办法就是 `Teleport`：把弹窗节点送到 `body` 下。**

### 模态框组件

```vue [src/components/AppModal.vue]
<script setup>
import { ref, watch, nextTick, onUnmounted } from 'vue'

const props = defineProps({
  // 是否显示，用 v-model 双向绑定
  modelValue: { type: Boolean, default: false },
  title: { type: String, default: '' },
  // 点遮罩是否关闭
  closeOnMask: { type: Boolean, default: true },
  // 按 Esc 是否关闭
  closeOnEsc: { type: Boolean, default: true },
  width: { type: String, default: '520px' }
})

const emit = defineEmits(['update:modelValue', 'close'])

const panelRef = ref(null)
// 记住打开之前焦点在哪个元素上，关闭后还给它
let lastActiveElement = null
// 记住页面原来的 overflow，关闭后恢复
let originalOverflow = ''

function close() {
  emit('update:modelValue', false)
  emit('close')
}

/* ---------- 1. 锁背景滚动 ---------- */
function lockScroll() {
  originalOverflow = document.body.style.overflow
  document.body.style.overflow = 'hidden'
}

function unlockScroll() {
  document.body.style.overflow = originalOverflow
}

/* ---------- 2. 焦点陷阱 ---------- */
const FOCUSABLE = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])'
].join(',')

function getFocusable() {
  if (!panelRef.value) return []
  return Array.from(panelRef.value.querySelectorAll(FOCUSABLE))
}

function onKeydown(event) {
  if (event.key === 'Escape' && props.closeOnEsc) {
    event.stopPropagation()
    close()
    return
  }

  // Tab 键在弹窗内部循环，不让焦点跑到背景页面上
  if (event.key === 'Tab') {
    const list = getFocusable()
    if (list.length === 0) {
      event.preventDefault()
      return
    }
    const first = list[0]
    const last = list[list.length - 1]
    const active = document.activeElement

    if (event.shiftKey && active === first) {
      event.preventDefault()
      last.focus()
    } else if (!event.shiftKey && active === last) {
      event.preventDefault()
      first.focus()
    }
  }
}

/* ---------- 3. 打开 / 关闭时的处理 ---------- */
watch(
  () => props.modelValue,
  async (visible) => {
    if (visible) {
      lastActiveElement = document.activeElement
      lockScroll()
      document.addEventListener('keydown', onKeydown)

      // 等 DOM 渲染完再让弹窗内的第一个可聚焦元素获得焦点
      await nextTick()
      const list = getFocusable()
      ;(list[0] ?? panelRef.value)?.focus()
    } else {
      document.removeEventListener('keydown', onKeydown)
      unlockScroll()
      // 焦点还给打开它的那个按钮
      lastActiveElement?.focus?.()
      lastActiveElement = null
    }
  }
)

// 组件被销毁时兜底清理，避免滚动被锁死
onUnmounted(() => {
  document.removeEventListener('keydown', onKeydown)
  unlockScroll()
})

function onMaskClick() {
  if (props.closeOnMask) close()
}
</script>

<template>
  <!-- 关键：传送到 body 下，绕开父容器的裁剪与层叠上下文 -->
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="modelValue" class="modal-mask" @click.self="onMaskClick">
        <div
          ref="panelRef"
          class="modal-panel"
          role="dialog"
          aria-modal="true"
          :style="{ width }"
          tabindex="-1"
        >
          <header class="modal-head">
            <h3>{{ title }}</h3>
            <button class="modal-close" aria-label="关闭" @click="close">×</button>
          </header>

          <div class="modal-body">
            <slot />
          </div>

          <footer v-if="$slots.footer" class="modal-foot">
            <slot name="footer" />
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
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-panel {
  background: #fff;
  border-radius: 10px;
  max-height: 80vh;
  overflow: auto;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.18);
}

/* 进出场动画 */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.25s ease;
}
.modal-enter-active .modal-panel,
.modal-leave-active .modal-panel {
  transition: transform 0.25s ease;
}
.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}
.modal-enter-from .modal-panel,
.modal-leave-to .modal-panel {
  transform: translateY(-16px) scale(0.98);
}
</style>
```

三个细节值得单独说。

**锁背景滚动**：把 `document.body.style.overflow` 临时设成 `hidden`。
保存原值、关闭时恢复，否则下次打开别的页面会一直锁着。
如果页面里同时能开多个弹窗，这种“直接设置”会互相覆盖，需要用一个计数器管理，
但那属于额外复杂度，课程项目里一个弹窗够用。

**焦点陷阱**：按 Tab 时，如果焦点要跳出弹窗（从最后一个元素再按 Tab），就手动把它拉回第一个；
反向也一样。这样键盘用户不会“不小心跑到背景里的按钮上”。

**焦点归还**：打开时记住 `document.activeElement`，关闭时 `focus()` 回去。键盘用户关闭弹窗后，
按 Tab 会从原来那个位置继续，而不是从头开始。

::: warning 别把 v-if 写在 Teleport 上
写成 `<Teleport v-if="modelValue">` 也能用，但 `Transition` 就拿不到“进入 / 离开”的时机了 ——
整个 Teleport 直接创建和销毁，过渡动画会失效。**顺序要记住：`Teleport` 在外、
`Transition` 在内、`v-if` 在最内层的元素上。**
:::

### 用起来

```vue [src/views/ActivityListView.vue]
<script setup>
import { ref } from 'vue'
import AppModal from '@/components/AppModal.vue'

const showConfirm = ref(false)
const current = ref(null)

function askOffline(activity) {
  current.value = activity
  showConfirm.value = true
}

async function confirmOffline() {
  await offlineActivity(current.value.id)
  showConfirm.value = false
}
</script>

<template>
  <button @click="askOffline(item)">下架</button>

  <AppModal v-model="showConfirm" title="下架活动">
    <p>下架“{{ current?.title }}”后，学生将无法再报名。活动记录会保留。</p>

    <template #footer>
      <button class="btn-plain" @click="showConfirm = false">取消</button>
      <button class="btn-danger" @click="confirmOffline">确认下架</button>
    </template>
  </AppModal>
</template>
```

## 第二部分：模块级 ref 就是全局状态

### 问题：任何地方都想弹一个确认框

上面的写法需要一个页面级的 `ref`、一个 `<AppModal>`、一组按钮，每加一个二次确认就要写一遍。
更好的接口是：**任何一个 `.js` 文件里，`await confirm('确定下架吗？')`，
得到用户点的是确定还是取消。**

要跨组件、跨文件共享“当前弹窗要显示什么”，就得有一份全局状态。很多人第一反应是 Pinia，
但这里有一个更轻的办法：**模块级的 `ref`**。

```js [src/composables/confirm.js]
import { ref } from 'vue'

// 模块级状态：整个应用共享同一份
// 写在模块顶层，模块只会被求值一次，所以所有 import 它的地方拿到的是同一个 ref
const visible = ref(false)
const options = ref({ title: '', content: '' })

let resolveFn = null

/**
 * 打开确认框，返回一个 Promise：
 * 用户点确定 → resolve(true)；点取消或关闭 → resolve(false)
 */
export function confirm(content, config = {}) {
  options.value = {
    title: config.title || '请确认',
    content,
    confirmText: config.confirmText || '确定',
    danger: config.danger || false
  }
  visible.value = true

  return new Promise((resolve) => {
    resolveFn = resolve
  })
}

function settle(result) {
  visible.value = false
  resolveFn?.(result)
  resolveFn = null
}

// 供确认框组件调用
export function useConfirmState() {
  return {
    visible,
    options,
    onConfirm: () => settle(true),
    onCancel: () => settle(false)
  }
}
```

配套的组件只需要渲染这份全局状态：

```vue [src/components/GlobalConfirm.vue]
<script setup>
import AppModal from './AppModal.vue'
import { useConfirmState } from '@/composables/confirm'

const { visible, options, onConfirm, onCancel } = useConfirmState()
</script>

<template>
  <AppModal v-model="visible" :title="options.title" :close-on-mask="false" @close="onCancel">
    <p :class="{ danger: options.danger }">{{ options.content }}</p>

    <template #footer>
      <button class="btn-plain" @click="onCancel">取消</button>
      <button class="btn-primary" @click="onConfirm">{{ options.confirmText }}</button>
    </template>
  </AppModal>
</template>
```

在 `App.vue` 里挂一次，全站就能用：

```vue [src/App.vue]
<script setup>
import GlobalConfirm from '@/components/GlobalConfirm.vue'
import ToastContainer from '@/components/ToastContainer.vue'
</script>

<template>
  <RouterView />
  <!-- 全局单例，挂一次，所有页面共用 -->
  <GlobalConfirm />
  <ToastContainer />
</template>
```

调用处就非常干净了：

```js [src/views/ActivityListView.vue]
import { confirm } from '@/composables/confirm'

async function offline(item) {
  const ok = await confirm(`确定下架“${item.title}”吗？`, { danger: true })
  if (!ok) return
  await offlineActivity(item.id)
}
```

### 为什么不用 Pinia

| 维度 | 模块级 ref | Pinia |
| --- | --- | --- |
| 需要的代码量 | 一个文件，几十行 | 一个 store 文件 + 安装配置 |
| 适用场景 | 一个模块自己的状态 | 多处共享、有多个 action、需要调试工具 |
| 用 DevTools 查看 | 看不到 | 有专门的面板 |
| 服务端渲染 | 要小心，模块状态会跨请求共享 | 天然支持每请求隔离 |
| 适合的数据 | 弹窗、通知这类“开关” | 用户信息、权限、列表数据 |

判断依据：**这份状态只服务于某一个功能（弹窗、通知），而且逻辑就写在旁边，用模块级 ref 更直接。
如果是“用户信息”“权限”“全局配置”这种被很多地方依赖、还需要一系列操作的状态，用 Pinia。**

这个案例里的通知和确认框都属于前者，所以用一个模块级 `ref` 就够了。
[单元 10](/unit10/01-when-global) 会讲 Pinia 适用的那些场景。

::: warning 模块级状态的边界
模块级的 `ref` 在**整个页面生命周期**内是同一份。这在单页应用里没问题，
但有两件事要注意：

1. **刷新页面会重置**，需要持久化的数据要自己存本地存储。
2. **在服务端渲染（SSR）里，模块状态会被所有请求共享**，会串数据。本课程不做 SSR，
   知道有这条限制即可。
:::

## 第三部分：useToast 全局通知

### 目标接口

```js
const toast = useToast()

toast.push('报名审核通过')                 // 成功提示，3 秒后自动消失
toast.push('保存失败，请重试', { type: 'error', duration: 0 })  // 错误提示，不自动消失
toast.remove(id)                          // 手动关闭某一条
```

多条同时存在时要堆叠显示。

### 状态模块

```js [src/composables/useToast.js]
import { ref, readonly } from 'vue'

// 模块级状态：所有调用方共享同一个列表
const toasts = ref([])

let seed = 0

/**
 * 推入一条通知
 * @param {string} message 通知内容
 * @param {object} options type 类型、duration 停留时长（0 表示不自动消失）
 * @returns {number} 这条通知的 id，可用于手动关闭
 */
function push(message, options = {}) {
  const { type = 'info', duration = 3000 } = options

  const id = ++seed
  toasts.value.push({ id, message, type })

  if (duration > 0) {
    setTimeout(() => remove(id), duration)
  }

  return id
}

function remove(id) {
  const index = toasts.value.findIndex((t) => t.id === id)
  if (index > -1) toasts.value.splice(index, 1)
}

function clear() {
  toasts.value = []
}

/**
 * 组合式函数接口
 * 注意：状态是共享的，返回的 read 用 readonly 包一层，外部改不了
 */
export function useToast() {
  return {
    toasts: readonly(toasts),
    push,
    success: (msg, opts) => push(msg, { ...opts, type: 'success' }),
    error: (msg, opts) => push(msg, { ...opts, type: 'error', duration: opts?.duration ?? 5000 }),
    warning: (msg, opts) => push(msg, { ...opts, type: 'warning' }),
    remove,
    clear
  }
}
```

几个设计点：

- **`toasts` 在模块顶层**，所有 `useToast()` 拿到的是同一个列表，所以“任何地方 push，
  容器都能显示”。
- **`readonly(toasts)`**：使用方只能读、不能直接改列表，改必须通过 `push` / `remove`。
  和 [8.2 的只读封装](/unit08/02-provide-inject)是同一个思路。
- **`duration: 0` 表示不自动消失**，用于“保存失败”这类需要用户看到并处理的错误。
- **id 用自增的 `seed`**，不用时间戳 —— 同一毫秒推两条会撞 id。

### 通知容器

```vue [src/components/ToastContainer.vue]
<script setup>
import { useToast } from '@/composables/useToast'

const { toasts, remove } = useToast()

const ICONS = {
  success: '✓',
  error: '✕',
  warning: '!',
  info: 'i'
}
</script>

<template>
  <!-- 容器固定在右上角，用 Teleport 送到 body，不受页面布局影响 -->
  <Teleport to="body">
    <TransitionGroup name="toast" tag="div" class="toast-container">
      <div
        v-for="item in toasts"
        :key="item.id"
        :class="['toast', `toast-${item.type}`]"
        role="status"
        @click="remove(item.id)"
      >
        <span class="toast-icon">{{ ICONS[item.type] }}</span>
        <span class="toast-text">{{ item.message }}</span>
        <button class="toast-close" aria-label="关闭" @click.stop="remove(item.id)">×</button>
      </div>
    </TransitionGroup>
  </Teleport>
</template>

<style scoped>
.toast-container {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 2000;
  display: flex;
  flex-direction: column;
  gap: 10px;
  pointer-events: none; /* 容器本身不挡点击 */
}

.toast {
  pointer-events: auto; /* 单条通知可点 */
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 220px;
  max-width: 360px;
  padding: 10px 14px;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.12);
  cursor: pointer;
}

.toast-success { border-left: 4px solid #16a34a; }
.toast-error   { border-left: 4px solid #dc2626; }
.toast-warning { border-left: 4px solid #f59e0b; }
.toast-info    { border-left: 4px solid #2563eb; }

/* 进场：从右侧滑入 */
.toast-enter-from {
  opacity: 0;
  transform: translateX(30px);
}
.toast-leave-to {
  opacity: 0;
  transform: translateX(30px);
}
.toast-enter-active,
.toast-leave-active {
  transition: all 0.25s ease;
}

/* 已有通知在新通知插入 / 移除时平滑上移或下落 */
.toast-move {
  transition: transform 0.25s ease;
}

/* 离场元素脱离文档流，后面的通知立刻补位 */
.toast-leave-active {
  position: absolute;
  right: 0;
  width: 100%;
}
</style>
```

这里 `TransitionGroup` 的用法和 [8.3 的列表动画](/unit08/03-builtin)完全一致，
`key` 用通知的 `id`，`-move` 负责补位。

::: warning 容器上的 `pointer-events: none`
`.toast-container` 是一个铺在右上角的浮层。如果不加 `pointer-events: none`，
它会挡住下面页面的按钮点击 —— 尤其是容器比通知大得多的时候。

做法是“容器不接收点击、单条通知接收点击”，也就是容器 `none`、`.toast` 上再 `auto` 回来。
这是一个很容易漏掉的细节。
:::

### 在业务里用

```js [src/views/SignupReviewView.vue]
import { useToast } from '@/composables/useToast'

const toast = useToast()

async function approve(record) {
  try {
    await approveSignup(record.id)
    toast.success(`${record.studentName} 的报名已通过`)
  } catch (e) {
    // 错误提示不自动消失，让用户看清楚
    toast.error(`审核失败：${e.message}`, { duration: 0 })
  }
}
```

## 第四部分：把三者串起来

一次完整的“批量通过报名”流程，可能同时用到确认框和通知：

```js [src/views/SignupReviewView.vue]
<script setup>
import { ref } from 'vue'
import { confirm } from '@/composables/confirm'
import { useToast } from '@/composables/useToast'

const toast = useToast()
const selected = ref([])

async function batchApprove() {
  const count = selected.value.length

  // 1. 先确认
  const ok = await confirm(`确定将通过选中的 ${count} 条报名吗？`, {
    title: '批量通过',
    confirmText: '通过'
  })
  if (!ok) return

  // 2. 提交
  try {
    const result = await approveMany(selected.value)

    // 3. 通知，部分失败时把失败数量也说清楚
    if (result.failed.length === 0) {
      toast.success(`已通过 ${result.success.length} 条报名`)
    } else {
      toast.warning(`通过 ${result.success.length} 条，${result.failed.length} 条因名额已满未处理`)
    }
    selected.value = []
    await reload()
  } catch (e) {
    toast.error(`操作失败：${e.message}`, { duration: 0 })
  }
}
</script>
```

这三个模块加起来不到 300 行，却覆盖了管理端里绝大部分的“临时性交互”。
**注意它们都是“与视图无关”的**：`confirm` 不知道页面长什么样，`useToast` 也不知道，
它们只提供接口，界面由 `App.vue` 里那两个容器负责。

## 小结

- 模态框用 `Teleport to="body"` 绕开父容器的 `overflow` 裁剪、定位上下文、层叠上下文。
- 锁背景滚动要在打开时保存原 `overflow`、关闭时恢复；组件销毁时兜底清理。
- 焦点陷阱拦 Tab 键，在弹窗内部循环；打开时记住活动元素，关闭后归还焦点。
- `Teleport` 在外、`Transition` 在内、`v-if` 在最内层元素上，动画才不会失效。
- 模块级 `ref` 就是一份天然共享的全局状态，适合弹窗、通知这类单一功能的状态；
  返回时用 `readonly` 保护。
- `useToast` 用模块级数组 + `push` / `remove`，`duration: 0` 表示不自动消失。
- `TransitionGroup` 做通知堆叠动画，`key` 用 id，`-leave-active` 脱离文档流做补位。
- 通知容器要 `pointer-events: none`，单条通知再 `auto` 回来，别挡住页面点击。

## 常见坑

::: details 坑 1：弹窗关了，页面却滚不动了
现象：关闭弹窗后整个页面不能滚动。

原因：打开了 `overflow: hidden` 之后，关闭分支没执行到（比如组件是被 `v-if` 直接销毁的），
或者同时开了两个弹窗，第一个关闭时恢复了、第二个还锁着。

处理：在 `onUnmounted` 里也恢复一次；需要支持多层弹窗时用一个计数器：
打开加一、关闭减一，减到 0 才恢复。
:::

::: details 坑 2：按 Esc 关闭了，但焦点丢了
现象：关闭弹窗后按 Tab，焦点从页面最开头开始。

原因：关闭时没有把焦点还给打开弹窗的那个按钮。

处理：打开时记录 `document.activeElement`，关闭时 `lastActiveElement.focus()`。
注意要判断元素还在不在页面上（`isConnected`），否则可能报错。
:::

::: details 坑 3：通知容器挡住了页面按钮
现象：页面右上角的按钮点不动。

原因：`.toast-container` 是一个大浮层，默认接收指针事件。

处理：容器 `pointer-events: none`，单条通知 `pointer-events: auto`。
:::

::: details 坑 4：`confirm` 返回的 Promise 永远不 resolve
现象：用户关闭弹窗后，`await confirm(...)` 后面的代码不执行。

原因：`resolveFn` 只在点确定 / 取消时调用。如果弹窗被别的方式关掉（比如父组件直接改了
`visible`），没有走到 `settle`。

处理：把 `settle` 挂到弹窗的 `@close` 事件上，保证任何关闭路径都会 resolve。
:::

::: details 坑 5：通知自动消失的定时器在组件销毁后还在跑
现象：控制台警告“在已销毁的组件上更新状态”。

原因：`setTimeout` 没有在组件卸载时清理。

处理：通知的状态在模块级，天然不绑定组件，所以这里没问题。但如果把通知状态写在了组件里，
就必须在 `onUnmounted` 里清掉所有定时器。**这也是把状态放模块级的一个好处。**
:::

## 课后练习

::: details 练习 1：给模态框加“打开时禁止页面滚动”的多层支持
实现一个滚动锁计数器，支持同时打开多个弹窗时，只有全部关闭才恢复滚动。

**思路**：模块级变量 `let count = 0`，`lock()` 时 `count++` 且只在第一次设置 `hidden`，
`unlock()` 时 `count--` 且减到 0 才恢复。
:::

::: details 练习 2：给通知加“悬停暂停自动消失”
鼠标移到某条通知上时，暂停它的倒计时；移开后继续。

**思路**：存储每条通知剩余的时间，`mouseenter` 时清掉定时器并记下剩余毫秒，
`mouseleave` 时用剩余时间重新起一个 `setTimeout`。这是常见交互细节。
:::

::: details 练习 3：用 `provide/inject` 改造 useToast
把 `useToast` 的状态从模块级改成 `provide/inject`，在 `App.vue` 里 provide 一份，
子组件 inject 使用。

**思路**：对比两种写法 —— 注入版本的作用范围是“这棵子树”，模块级版本是“整个应用”。
想清楚什么情况下注入版本更合适（比如同一页面要挂两个互不干扰的通知区域）。
:::

---

上一节：[8.5 自定义指令](/unit08/05-directives) ·
下一节：[案例 08 · 画板与撤销重做](/unit08/07-case-canvas)
