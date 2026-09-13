# 案例 08 · 画板与撤销重做

## 案例要做什么

场次安排页要加一个“场地布置草图”功能。组织者在画布上随手画出舞台、签到台、物资区的位置，标好方向，然后把这张图随场次一起保存。审核员看场次详情时，能直接看到这张布置图。

功能不多，但要求挺细：

1. **在高清屏上不能糊。** 笔记本和手机的屏幕像素密度不一样，同一段代码在普通屏上清楚、在 `devicePixelRatio` 为 2 的屏幕上就发虚。
2. **鼠标和触摸都要能用。** 组织者可能在手机上手绘。而且手指画的时候页面不能跟着上下滚。
3. **有颜色和粗细可选，还有橡皮擦。** 橡皮擦要真的把笔迹擦掉，不是盖一层白色 —— 否则导出成透明底图片时会露馅。
4. **能撤销和重做。** 只要 `Ctrl + Z`（Mac 上是 `Cmd + Z`）就能退回上一笔，`Shift + Ctrl + Z` 恢复。
5. **能清空。** 清空这种破坏性操作要二次确认，这里直接复用[案例 06 的模态框](/cases/06-modal)。
6. **能导出 PNG 并上传。** 带着场次 ID 存到后端。

撤销重做是这个案例的核心。教科书上常见的做法是“每画一笔存一张 `ImageData` 快照”，简单但**内存代价极大**：一张 1000 × 700 的画布，一个快照就是 2.8 MB，存 50 步就是 140 MB，页面会直接卡死。我们改用**命令栈**：每一步只记录“发生了什么”，重放即可还原。

做完之后可以这样自查，每一条都能在浏览器里手动验证：

- 在高清屏上画一条细线，放大到 200% 仍然边缘平滑，没有明显的像素方块。
- 在手机上用手指画，页面不会跟着滚动；手指画出画布边界再回来，线还是连续的。
- 画三笔，按两次 `Ctrl + Z` 退回第一笔的状态，再按两次 `Shift + Ctrl + Z` 完全恢复。
- 撤销一步后重新画一笔，此时“重做”按钮变灰 —— 原来的重做链已经断了。
- 选橡皮擦擦掉一段线，导出的 PNG 放在深色背景上看，被擦的地方是透明白底而不是白块。
- 把浏览器窗口拉大，已经画的内容不会消失，笔画按新的尺寸重新渲染。

### 用到的知识点 → 对应章节

| 用到的知识点 | 对应章节 |
| --- | --- |
| 模板引用拿到 DOM 元素 | [4.4 ref 与 reactive](/unit04/04-reactivity) |
| `watch` 侦听变化触发重绘 | [5.2 侦听器](/unit05/02-watch) |
| 生命周期与副作用清理 | [6.5 生命周期与副作用清理](/unit06/05-lifecycle) |
| 用 `computed` 派生“能不能撤销” | [5.1 计算属性与缓存](/unit05/01-computed) |
| `defineExpose` 暴露组件方法 | [7.2 props](/unit07/02-props) |
| 组合式函数封装历史栈 | [8.4 组合式函数](/unit08/04-composables) |
| 复用模态框做二次确认 | [案例 06 · 模态框与全局通知](/cases/06-modal) |
| 上传文件到接口 | [10.4 请求层封装](/unit10/04-request-layer) |

## 数据结构与接口设计

### 笔画：一次按下到抬起之间画的线

```js [一笔的结构]
{
  id: 12,                         // 自增，用于重绘定位和重做校验
  tool: 'pen',                    // pen | eraser
  color: '#1f2329',               // 画笔颜色，橡皮擦时忽略
  width: 4,                       // 线宽，单位是 CSS 像素
  points: [                       // 采样点，坐标是 CSS 像素
    { x: 120.5, y: 88 },
    { x: 123, y: 91 },
    // ……
  ]
}
```

**为什么要存点而不是存 `Path2D`？** 因为 `Path2D` 没法序列化，不能存进 `localStorage`，也不方便做“简化点集”这类优化。存点则是纯数据，可存可传可比较，重放的时候重新连成线就行。

::: tip 点要不要做抽稀
一次手绘会采到成百上千个点，其中很多是几乎重合的。如果发现画布上笔画多了之后变卡，可以在 `pointermove` 里加一句最小距离判断：**新点与上一个点距离小于 1.5 像素就丢弃**。这样点的数量能少一半以上，视觉上看不出差别。本案例为了代码清楚没有加，留到扩展练习里。
:::

### 命令：历史栈里存的东西

历史栈不存笔画本身，存的是**可以正向执行、反向撤销的操作**。

```js [两种命令]
// 画了一笔
{ type: 'add', stroke: { /* 上面那个结构的对象 */ } }

// 清空了画布
{ type: 'clear', removed: [ /* 被清掉的全部笔画，用来支持撤销 */ ] }
```

- `add` 的正向是“加一笔”，反向是“移除这一笔”。
- `clear` 比较特殊：它的正向是“全部清掉”，反向是“把清掉的那些还原回来”。所以执行 `clear` 的时候必须**顺手把当前所有笔画记进 `removed`**，否则撤销就无从还原。

这个设计的好处是：**每一步操作的数据量等于它实际改动的量。** 画一笔只占一个笔画的内存，清空操作只在撤销时占用一份数组引用（不是深拷贝），50 步历史加起来通常不到 1 MB。

### 为什么不存位图快照

另一种常见的撤销实现是“每画完一笔，把整张画布存成 `ImageData`，撤销时盖回去”。写法很短，但代价很大，算一下就清楚了：

| 画布尺寸 | 单张快照大小 | 存 50 步 |
| --- | --- | --- |
| 800 × 480 | 约 1.5 MB | 约 75 MB |
| 1200 × 720 | 约 3.5 MB | 约 175 MB |
| 1920 × 1080 | 约 8.3 MB | 约 415 MB |

快照大小按 `宽 × 高 × 4 字节` 算，因为每个像素要存 RGBA 四个通道。上面这张表说明的是：**只要画布稍微大一点，位图快照方案就会把内存吃光。**

命令栈方案的数据量完全由“画了多少”决定。一个笔画几百个点，每个点两个数字，撑死几十 KB，画满一屏也才几百 KB。而且它还有一个额外的好处：**画布尺寸变化时可以重新渲染**。位图快照在窗口变大之后重新拉伸会糊，矢量笔画重放一遍仍然清晰。

代价是**实现更复杂**：要保证每个命令都能正确地“正向执行 + 反向撤销”，还要处理清空这类一次改动多条数据的操作。下面第一步写的 `useDrawingHistory` 就是在处理这些复杂度。

### 历史栈的状态

```js [src/composables/useDrawingHistory.js 的内部状态]
strokes    // 当前画布上的笔画（按顺序）
undoStack  // 可撤销的命令，栈顶是最新的一步
redoStack  // 可重做的命令
version    // 内容版本号，每次变化自增，组件 watch 它来重绘
MAX_HISTORY = 50   // 栈深上限
```

有三条规则必须写死，否则历史会错乱：

1. **执行新操作时清空 `redoStack`。** 撤销两步之后又画了一笔，原来的“重做链”就断了 —— 这是所有编辑器的通用行为。
2. **`undoStack` 超过上限时丢掉最早的一条。** 丢掉之后不是“不能撤销”，而是“不能撤销到那么早”，画面保持不变，这是可以接受的。
3. **`redoStack` 不设上限。** 它最多和 `undoStack` 一样长，不需要额外控制。

### 坐标系与高清适配

画布有两套尺寸，这是最容易搞混的地方：

| 尺寸 | 含义 | 怎么设置 |
| --- | --- | --- |
| CSS 尺寸 | 元素在页面上占的位置，比如 `800 × 480` | 由 CSS 或父容器决定 |
| 位图尺寸 | 画布实际有多少像素，比如 `1600 × 960` | 设置 `canvas.width / height` |

如果两者写成一样，在 `devicePixelRatio` 为 2 的屏幕上，浏览器会把 800 个像素拉伸到 1600 个物理像素上显示，笔迹就发虚。正确做法是**位图尺寸乘以 `devicePixelRatio`，再用 `ctx.setTransform()` 把绘制坐标系放大回去**。

```js [建立坐标系（核心三行）]
const dpr = window.devicePixelRatio || 1
canvas.width = Math.round(cssWidth * dpr)
canvas.height = Math.round(cssHeight * dpr)
ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
```

做完这三行，**之后所有绘制都按 CSS 像素写坐标**，不用在每次 `lineTo` 的时候自己乘 `dpr`。鼠标事件拿到的是 `event.clientX`，也是 CSS 像素，两边天然一致。

### 接口约定

```js [src/api/session.js]
import request from './request'

// 上传场次布置图：用 FormData 传二进制，比 base64 小三分之一左右
export function uploadSessionSketch(sessionId, blob) {
  const formData = new FormData()
  formData.append('file', blob, `session-${sessionId}.png`)
  return request.post(`/api/session/${sessionId}/sketch`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

// 读取已有的布置图地址
export function fetchSessionSketch(sessionId) {
  return request.get(`/api/session/${sessionId}/sketch`)
}
```

## 实现步骤

### 第一步：把历史栈抽成组合式函数

历史栈的逻辑和界面无关，抽成组合式函数最合适。**它只负责“有哪些笔画、能不能撤销、撤销后长什么样”，一行绘制代码都不要有。**

```js [src/composables/useDrawingHistory.js]
import { ref, shallowRef, computed } from 'vue'

const MAX_HISTORY = 50
let strokeSeed = 0

export function useDrawingHistory() {
  // shallowRef 够用：我们只整体替换数组，不会原地改它的下标
  const strokes = shallowRef([])
  const undoStack = shallowRef([])
  const redoStack = shallowRef([])
  // 内容版本号：每次内容变化自增。组件 watch 它，而不是 deep watch 笔画数组
  const version = ref(0)

  const canUndo = computed(() => undoStack.value.length > 0)
  const canRedo = computed(() => redoStack.value.length > 0)

  function touch() {
    version.value += 1
  }

  function nextStrokeId() {
    strokeSeed += 1
    return strokeSeed
  }

  // 正向执行
  function applyCommand(command) {
    if (command.type === 'add') {
      strokes.value = [...strokes.value, command.stroke]
    } else if (command.type === 'clear') {
      // 关键：把当前内容存进命令里，撤销时才有东西可还原
      command.removed = strokes.value
      strokes.value = []
    }
  }

  // 反向撤销
  function revertCommand(command) {
    if (command.type === 'add') {
      strokes.value = strokes.value.filter((s) => s.id !== command.stroke.id)
    } else if (command.type === 'clear') {
      strokes.value = command.removed ?? []
    }
  }

  function commit(command) {
    applyCommand(command)

    const next = [...undoStack.value, command]
    // 超过上限就丢掉最早的一条：不影响画面，只是撤不到那么早
    undoStack.value =
      next.length > MAX_HISTORY ? next.slice(next.length - MAX_HISTORY) : next

    // 新的操作让重做链失效
    redoStack.value = []
    touch()
  }

  function addStroke(stroke) {
    commit({ type: 'add', stroke })
  }

  function clearAll() {
    if (strokes.value.length === 0) return
    commit({ type: 'clear' })
  }

  function undo() {
    if (undoStack.value.length === 0) return false
    const stack = [...undoStack.value]
    const command = stack.pop()
    undoStack.value = stack
    revertCommand(command)
    redoStack.value = [...redoStack.value, command]
    touch()
    return true
  }

  function redo() {
    if (redoStack.value.length === 0) return false
    const stack = [...redoStack.value]
    const command = stack.pop()
    redoStack.value = stack
    applyCommand(command)
    undoStack.value = [...undoStack.value, command]
    touch()
    return true
  }

  return {
    strokes,
    version,
    canUndo,
    canRedo,
    nextStrokeId,
    addStroke,
    clearAll,
    undo,
    redo
  }
}
```

`shallowRef` 而不是 `ref` 是一个小优化：`strokes` 数组里每个笔画对象都可能有几百个点，用 `ref` 会让 Vue 递归地把每个点都变成响应式代理，白白多出几万个 Proxy。**我们只需要“数组被替换”这一个层级的响应性**，`shallowRef` 正好。用 `version` 做重绘信号也是同一个思路 —— 比 `deep: true` 侦听整个数组便宜得多。

::: tip 为什么撤销和重做都要“先复制再操作”
你可能注意到 `undo()` 里写的是：

```js
const stack = [...undoStack.value]
const command = stack.pop()
undoStack.value = stack
```

而不是直接 `undoStack.value.pop()`。原因是 `shallowRef` 只在**整个值被替换**时才触发更新。如果直接对数组 `pop()`，`undoStack.value` 的引用没变，`canUndo` 这个 `computed` 就收不到通知，按钮的禁用状态不会跟着变。

用 `ref` 会深一层代理数组，`pop()` 能触发；但 `ref` 会把每个笔画对象都代理，代价太大。**用 `shallowRef` 就必须养成“替换而不是修改”的习惯**，这两种写法的取舍在[4.5 响应式原理](/unit04/05-reactivity-principle)里有更细的解释。
:::


### 第二步：让画布在高清屏上不糊

```vue [src/components/canvas/CanvasBoard.vue（画布建立部分）]
<script setup>
import { onMounted, onBeforeUnmount, watch, useTemplateRef } from 'vue'
import { useDrawingHistory } from '@/composables/useDrawingHistory'

const canvasRef = useTemplateRef('canvas')
const history = useDrawingHistory()

let ctx = null
let cssWidth = 0
let cssHeight = 0
let resizeObserver = null

function setupCanvas() {
  const canvas = canvasRef.value
  if (!canvas) return

  const rect = canvas.getBoundingClientRect()
  const dpr = window.devicePixelRatio || 1

  cssWidth = rect.width
  cssHeight = rect.height

  // 注意：设置 width / height 会清空画布并重置变换矩阵，所以顺序不能颠倒
  canvas.width = Math.round(cssWidth * dpr)
  canvas.height = Math.round(cssHeight * dpr)

  ctx = canvas.getContext('2d')
  // 把坐标系放大 dpr 倍：之后一律按 CSS 像素写坐标
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  ctx.lineCap = 'round'
  ctx.lineJoin = 'round'

  // 尺寸变了画布内容会被清空，必须重绘
  redraw()
}

function redraw() {
  if (!ctx) return
  ctx.clearRect(0, 0, cssWidth, cssHeight)
  for (const stroke of history.strokes.value) {
    paintStroke(stroke)
  }
}

// 内容变化就重绘。watch 版本号比 deep watch 数组便宜
watch(() => history.version.value, redraw)

onMounted(() => {
  setupCanvas()
  // 父容器尺寸变化时（比如侧边栏折叠）重新建立坐标系
  resizeObserver = new ResizeObserver(() => setupCanvas())
  resizeObserver.observe(canvasRef.value)
})

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  resizeObserver = null
})
</script>
```

`lineCap` 和 `lineJoin` 设成 `round` 是为了让折线看起来像手绘的圆头笔，否则每个转折点都会有硬角，快速画出来的线像锯齿。

### 第三步：鼠标与触摸统一用 Pointer Events

鼠标事件、触摸事件各写一套是过去的做法。现在浏览器都支持 **Pointer Events**，一套 `pointerdown / pointermove / pointerup` 同时覆盖鼠标、手指、触控笔。省事，而且不会出现“手机上能画、电脑上画不了”这种漏写。

坐标换算只需要减掉元素在视口里的偏移：

```js [src/components/canvas/CanvasBoard.vue（事件部分）]
<script setup>
import { ref } from 'vue'

const props = defineProps({
  color: { type: String, default: '#1f2329' },
  width: { type: Number, default: 4 },
  tool: { type: String, default: 'pen' } // pen | eraser
})

const drawing = ref(false)
let currentStroke = null

// 把视口坐标换算成画布内部的 CSS 像素坐标
function pointFromEvent(event) {
  const rect = canvasRef.value.getBoundingClientRect()
  return {
    x: event.clientX - rect.left,
    y: event.clientY - rect.top
  }
}

function onPointerDown(event) {
  // 只响应鼠标左键，避免右键菜单、中键滚动时误画
  if (event.pointerType === 'mouse' && event.button !== 0) return

  // 捕获指针：手指滑出画布范围时也能继续收到 pointermove
  canvasRef.value.setPointerCapture(event.pointerId)

  drawing.value = true
  const point = pointFromEvent(event)
  currentStroke = {
    id: history.nextStrokeId(),
    tool: props.tool,
    color: props.color,
    // 橡皮擦按画笔的 3 倍宽，手感更接近“擦除面积”
    width: props.tool === 'eraser' ? props.width * 3 : props.width,
    points: [point]
  }
  // 先画一个点，单击也能留下痕迹
  paintStroke(currentStroke)
}

function onPointerMove(event) {
  if (!drawing.value || !currentStroke) return
  const point = pointFromEvent(event)
  const last = currentStroke.points[currentStroke.points.length - 1]
  currentStroke.points.push(point)
  paintSegment(last, point, currentStroke)
}

function finishStroke(event) {
  if (!drawing.value || !currentStroke) return
  drawing.value = false
  canvasRef.value.releasePointerCapture?.(event.pointerId)

  // 只提交有内容的笔画；单击留下的是一个只有一个点的笔画
  history.addStroke(currentStroke)
  currentStroke = null
}
</script>

<template>
  <canvas
    ref="canvas"
    class="board"
    @pointerdown="onPointerDown"
    @pointermove="onPointerMove"
    @pointerup="finishStroke"
    @pointercancel="finishStroke"
    @pointerleave="finishStroke"
  />
</template>

<style scoped>
.board {
  display: block;
  width: 100%;
  height: 480px;
  background: #fff;
  border: 1px solid #dcdfe6;
  border-radius: 6px;
  /* 关键：告诉浏览器这个元素自己处理手势，别拿去做滚动 */
  touch-action: none;
  cursor: crosshair;
}
</style>
```

`touch-action: none` 是移动端能画画的前提。缺了它，手指在画布上一划，浏览器会认为你在滚动页面，`pointermove` 直接被取消，表现就是“画两下就断线”。

### 第四步：画笔与橡皮擦

画笔和橡皮擦的区别只有一个：**用什么方式改像素**。

```js [src/components/canvas/CanvasBoard.vue（绘制函数）]
function paintStroke(stroke) {
  if (stroke.points.length === 1) {
    paintDot(stroke.points[0], stroke)
    return
  }
  ctx.save()
  applyStyle(stroke)
  ctx.beginPath()
  ctx.moveTo(stroke.points[0].x, stroke.points[0].y)
  for (let i = 1; i < stroke.points.length; i++) {
    ctx.lineTo(stroke.points[i].x, stroke.points[i].y)
  }
  ctx.stroke()
  ctx.restore()
}

// 一笔只落下一个点：画个实心圆，否则 lineTo 到自身画不出来
function paintDot(point, stroke) {
  ctx.save()
  applyStyle(stroke)
  ctx.beginPath()
  ctx.arc(point.x, point.y, stroke.width / 2, 0, Math.PI * 2)
  ctx.fillStyle = ctx.strokeStyle
  ctx.fill()
  ctx.restore()
}

// 实时绘制：把新采到的点与上一个点连成一小段
function paintSegment(from, to, stroke) {
  ctx.save()
  applyStyle(stroke)
  ctx.beginPath()
  ctx.moveTo(from.x, from.y)
  ctx.lineTo(to.x, to.y)
  ctx.stroke()
  ctx.restore()
}

function applyStyle(stroke) {
  ctx.lineWidth = stroke.width
  if (stroke.tool === 'eraser') {
    // destination-out：新画的形状会“挖掉”下面已有的像素
    ctx.globalCompositeOperation = 'destination-out'
    ctx.strokeStyle = 'rgba(0, 0, 0, 1)'
  } else {
    ctx.globalCompositeOperation = 'source-over'
    ctx.strokeStyle = stroke.color
  }
}
```

`globalCompositeOperation = 'destination-out'` 是橡皮擦的关键。它做的事是：**在新图形覆盖到的地方，把下面已有的内容擦成透明**。和“用白色再画一遍”相比，它的好处是擦出来的区域真的是空的 —— 画布底色换成浅灰、或者导出成透明背景 PNG 时都不会露馅。

::: warning `ctx.save()` / `ctx.restore()` 不能省
`globalCompositeOperation` 是画布上下文的一个状态，改完不还原，会把后面所有绘制都变成“擦除模式”。`save()` 在进入时记下当前状态，`restore()` 退出时还原，是防这类“状态污染”的标准做法。**每一段独立的绘制都包一层，就不会出错。**
:::

### 第五步：快捷键与工具栏

快捷键要同时照顾 Mac 和 Windows，判断方式是**读 `event.metaKey` 与 `event.ctrlKey`**，而不是去猜用户的系统。

```js [src/components/canvas/CanvasBoard.vue（快捷键）]
function onKeydown(event) {
  // Cmd（Mac）或 Ctrl（Windows / Linux）
  const withModifier = event.metaKey || event.ctrlKey
  if (!withModifier) return

  // 用 event.code 而不是 event.key：
  // 按 Shift 时 event.key 会变成大写 'Z'，而 code 始终是 'KeyZ'
  if (event.code !== 'KeyZ') return

  // 光标在输入框里时不要抢快捷键（浏览器自带的撤销更合适）
  const target = event.target
  if (target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement) {
    return
  }

  event.preventDefault()
  if (event.shiftKey) {
    history.redo()
  } else {
    history.undo()
  }
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
```

::: tip 为什么用 `event.code` 而不是 `event.key`
- 按 `Shift + Z` 时，`event.key` 是 `'Z'`；不按 Shift 时是 `'z'`。用 `key` 判断就得写两遍，还得考虑大小写锁定。
- `event.code` 表示“键盘上哪个物理键被按下”，`Z` 键永远是 `'KeyZ'`，和修饰键、输入法都无关。

做快捷键时优先用 `code`；只有在需要区分键盘布局（比如区分 `Z` 和 `Y` 在不同国家的键盘位置）时才用 `key`。**注意中文输入法处于激活状态时，`keydown` 里的 `event.key` 可能是 `'Process'`，而 `code` 不受影响** —— 这也是用 `code` 更稳的原因之一。
:::

工具栏放在父组件里，通过模板引用调用画布暴露出来的方法：

```vue [src/views/session/SketchPanel.vue]
<script setup>
import { reactive, useTemplateRef, ref } from 'vue'
import CanvasBoard from '@/components/canvas/CanvasBoard.vue'
import AppModal from '@/components/AppModal.vue'
import { uploadSessionSketch } from '@/api/session'
import { toast } from '@/composables/useToast'

const props = defineProps({
  sessionId: { type: [Number, String], required: true }
})

const boardRef = useTemplateRef('board')

const color = ref('#1f2329')
const width = ref(4)
const tool = ref('pen')

// 画布通过 change 事件回报自己的状态，父组件不需要窥探它的内部
const boardState = reactive({ canUndo: false, canRedo: false, empty: true })

const COLORS = ['#1f2329', '#f56c6c', '#409eff', '#67c23a', '#e6a23c']
const WIDTHS = [
  { label: '细', value: 2 },
  { label: '中', value: 4 },
  { label: '粗', value: 8 }
]

const clearVisible = ref(false)

function requestClear() {
  // 空画布不需要确认，直接放过
  if (boardState.empty) return
  clearVisible.value = true
}

function confirmClear() {
  boardRef.value?.clear()
  clearVisible.value = false
  toast.info('已清空，可以用 Ctrl + Z 撤销')
}

async function handleSave() {
  if (boardState.empty) {
    toast.warning('还没有画任何内容')
    return
  }
  try {
    const blob = await boardRef.value.exportPng()
    await uploadSessionSketch(props.sessionId, blob)
    toast.success('布置图已保存')
  } catch (error) {
    toast.error(error.message, 0)
  }
}
</script>

<template>
  <div class="sketch-panel">
    <div class="toolbar">
      <button
        type="button"
        :class="{ 'is-active': tool === 'pen' }"
        @click="tool = 'pen'"
      >
        画笔
      </button>
      <button
        type="button"
        :class="{ 'is-active': tool === 'eraser' }"
        @click="tool = 'eraser'"
      >
        橡皮擦
      </button>

      <span class="toolbar__divider" />

      <button
        v-for="item in COLORS"
        :key="item"
        type="button"
        class="color-dot"
        :class="{ 'is-active': color === item && tool === 'pen' }"
        :style="{ background: item }"
        :aria-label="`使用颜色 ${item}`"
        @click="((color = item), (tool = 'pen'))"
      />

      <span class="toolbar__divider" />

      <button
        v-for="item in WIDTHS"
        :key="item.value"
        type="button"
        :class="{ 'is-active': width === item.value }"
        @click="width = item.value"
      >
        {{ item.label }}
      </button>

      <span class="toolbar__divider" />

      <button type="button" :disabled="!boardState.canUndo" @click="boardRef.undo()">
        撤销
      </button>
      <button type="button" :disabled="!boardState.canRedo" @click="boardRef.redo()">
        重做
      </button>
      <button type="button" @click="requestClear">清空</button>

      <span class="toolbar__spacer" />

      <button type="button" @click="handleSave">保存布置图</button>
    </div>

    <CanvasBoard
      ref="board"
      :color="color"
      :width="width"
      :tool="tool"
      @change="Object.assign(boardState, $event)"
    />

    <AppModal
      v-model:visible="clearVisible"
      title="确认清空"
      confirm-text="清空"
      @confirm="confirmClear"
    >
      清空后画布上的内容都会消失，你还可以用撤销恢复最近 50 步内的内容。
    </AppModal>
  </div>
</template>
```

画布那边把能力暴露出去，同时在内容变化时通知父组件：

```js [src/components/canvas/CanvasBoard.vue（对外接口）]
const emit = defineEmits(['change'])

watch(
  () => history.version.value,
  () => {
    emit('change', {
      canUndo: history.canUndo.value,
      canRedo: history.canRedo.value,
      empty: history.strokes.value.length === 0
    })
  }
)

function clear() {
  history.clearAll()
}

function exportPng() {
  const canvas = canvasRef.value
  // 导出一张带白色底的图：透明底在某些看图软件里会显示成黑块
  const output = document.createElement('canvas')
  output.width = canvas.width
  output.height = canvas.height
  const outputCtx = output.getContext('2d')
  outputCtx.fillStyle = '#ffffff'
  outputCtx.fillRect(0, 0, output.width, output.height)
  outputCtx.drawImage(canvas, 0, 0)

  return new Promise((resolve, reject) => {
    output.toBlob((blob) => {
      if (blob) resolve(blob)
      else reject(new Error('导出图片失败'))
    }, 'image/png')
  })
}

defineExpose({ undo: history.undo, redo: history.redo, clear, exportPng })
```

::: tip 为什么不在父组件里直接拿 canvas 元素
父组件调用 `boardRef.value.clear()` 而不是自己去操作 DOM，有两个好处：

1. **历史栈不出组件。** 撤销、重做、清空都要改历史栈，如果父组件直接改 `strokes`，就会绕过 `commit`，历史链立刻错乱。
2. **画布的实现可以换。** 以后把 `<canvas>` 换成 WebGL 或者引第三方绘图库，父组件的代码一行都不用改。

这就是 `defineExpose` 的用途：**给组件开一组明确的对外方法，而不是把内部状态摊开给外面看。** 和组件设计里的“最小接口”是同一条原则。
:::

## 完整代码

目录结构：

```text [src/]
src/
├── api/
│   └── session.js
├── components/
│   ├── canvas/
│   │   └── CanvasBoard.vue
│   └── AppModal.vue
├── composables/
│   ├── useDrawingHistory.js
│   └── useToast.js
└── views/
    └── session/
        └── SketchPanel.vue
```

`useDrawingHistory.js`、`CanvasBoard.vue`、`SketchPanel.vue` 的完整内容就是上面各部分拼起来的样子，其中 `CanvasBoard.vue` 需要把下面几块按顺序组合：

1. `<script setup>` 顶部：引入依赖、`useTemplateRef`、`useDrawingHistory`、props 与 emits。
2. 画布建立：`setupCanvas`、`redraw`、`ResizeObserver`、`onMounted` / `onBeforeUnmount`。
3. 事件处理：`pointFromEvent`、`onPointerDown`、`onPointerMove`、`finishStroke`、`onKeydown`。
4. 绘制函数：`paintStroke`、`paintDot`、`paintSegment`、`applyStyle`。
5. 对外接口：`clear`、`exportPng`、`defineExpose`。
6. 模板：一个 `<canvas>` 加六类事件监听。
7. 样式：`touch-action: none`、固定高度、白色底、描边。

跑起来之后的效果：在画布上按住鼠标或手指就能画；选橡皮擦可以擦；`Ctrl + Z` 一步步退回，`Shift + Ctrl + Z` 恢复；点清空会弹确认框；点保存会把 PNG 传到后端。

## 常见坑

::: details 坑 1：画布在 Mac 上看得很清楚，在普通显示器上就正常？
**现象**：同一份代码，在高清屏上写出来的线明显更细腻，普通屏上反而“正常”。反过来也成立 —— 有些同学的画布在自己电脑上挺好，别人电脑上发虚。

**原因**：`devicePixelRatio` 因设备而异。高清屏是 2 或 3，普通屏是 1。代码如果没做适配，在 `dpr` 大于 1 的屏幕上，`canvas.width` 小于实际需要的物理像素数，浏览器把图像拉伸显示，就发虚。

**怎么处理**：按本文的三行代码，位图尺寸乘以 `dpr`，再用 `setTransform` 把绘制坐标系放大回来。**并且在 `ResizeObserver` 里重做一遍**，因为屏幕缩放、窗口拖到外接显示器都会改变 `dpr`。
:::

::: details 坑 2：设置了 `canvas.width`，画的内容全没了
**现象**：窗口一调整大小，之前画的都没了。

**原因**：给 `canvas.width` 或 `canvas.height` 赋值会**清空整个画布**，并重置变换矩阵。这是规范规定的行为，不是 bug。

**怎么处理**：重设尺寸之后立刻调用一次 `redraw()` 重放全部笔画。由于历史栈里存的是矢量笔画，重放的成本很低，这也是“存点不存快照”的另一个好处。
:::

::: details 坑 3：笔迹位置偏了一段距离
**现象**：鼠标画在左上角，线条出现在右下角。

**原因**：`event.clientX` 是相对整个视口的，而你直接把它当成了画布内的坐标。如果画布不在页面左上角，或者页面有滚动、有侧边栏，偏差就出来了。

**怎么处理**：一律用 `getBoundingClientRect()` 换算：

```js
const rect = canvas.getBoundingClientRect()
const x = event.clientX - rect.left
const y = event.clientY - rect.top
```

注意 `rect` 要**在事件处理里实时取**，不能在 `onMounted` 里取一次存起来 —— 页面滚动或布局变化后它就过期了。
:::

::: details 坑 4：移动端画两下就断线
**现象**：手机上开始画还有线，手指一动页面跟着滚，线就断了。

**原因**：浏览器把手势判断为“滚动页面”，主动取消了 `pointermove`。

**怎么处理**：给画布加 `touch-action: none`，让浏览器把这个元素上的触摸手势全部交给页面自己处理。同时用 `setPointerCapture` 捕获指针，手指滑出画布边界时也不断线。
:::

::: details 坑 5：橡皮擦用白色画，导出透明底时露馅
**现象**：画布上看不出问题，导出的 PNG 放到深色背景上，擦过的地方出现白块。

**原因**：用白色画笔“擦”，只是把白色像素盖在了上面，并没有真的把内容删掉。

**怎么处理**：用 `globalCompositeOperation = 'destination-out'`，它会把被覆盖的像素真正挖成透明。导出前再补一层白色底，让图片在任何背景上都能正常显示。
:::

::: details 坑 6：撤销两步后又画一笔，重做还能用，结果错乱
**现象**：撤销两步，画一笔，再点重做，画面上出现了顺序不对的笔画。

**原因**：执行新操作时没有清空 `redoStack`，那些“被撤销的步骤”还留着，重做时它们被重新应用到了新的分支上。

**怎么处理**：`commit()` 里第一件事就是把 `redoStack` 清空。这是所有编辑器的通用规则，写历史栈时务必记住这一条。
:::

::: details 坑 7：画布越用越卡，内存一直涨
**现象**：连续画几分钟之后，画布明显掉帧，任务管理器里的内存一直往上涨。

**原因**：很可能是每步都存了 `ImageData` 或 `toDataURL` 快照。一张普通画布的快照就是几兆。

**怎么处理**：改用命令栈，只存笔画数据。同时给历史栈设上限，本案例是 50 步。如果笔画本身太密导致点数过多，就在采集时做抽稀（相邻点距离小于一个阈值就丢弃）。
:::

::: details 坑 8：`Ctrl + Z` 把浏览器的撤销也触发了
**现象**：在画布上按 `Ctrl + Z`，画布退了一步，页面里某个输入框的内容也退了一步。

**原因**：只调用了 `history.undo()`，没有 `event.preventDefault()`，浏览器继续执行了它的默认行为。

**怎么处理**：确认要接管这个快捷键时，先 `event.preventDefault()`。同时要排除“光标在输入框里”的情况 —— 那时用户想撤销的是输入，应该把快捷键让给浏览器。**快捷键不是抢得越多越好，边界要清楚。**
:::

## 扩展练习

::: details 练习 1：给笔迹加抽稀与平滑
现在的线是折线拼接的，快速画大弧线时能看出棱角。做两件事：

1. 在 `pointermove` 里加最小距离判断，新点与上一个点距离小于 1.5 像素就丢弃。
2. 重绘时把折线换成平滑曲线。

**思路**：平滑曲线的常用做法是**用相邻两点的中点作为曲线的端点，把原始点作为控制点**，调用 `quadraticCurveTo`。这样曲线会穿过那些中点，视觉上很顺。抽稀要注意**一笔的最后一个点必须保留**，否则笔画的尾部会短一截。
:::

::: details 练习 2：加矩形和圆形工具
工具栏增加“矩形”“圆形”两个按钮：按下后拖动可以拉出一个矩形或椭圆，松开时确定大小。要支持撤销。

**思路**：这两种图形不适合“逐点绘制”，更适合“按下时记起点，移动时先清掉预览再画一次，松开时提交”。注意**预览不能进历史栈**，否则每动一下都会多一步撤销记录。可以在 `strokes` 之外单独放一个 `previewStroke`，`redraw()` 时最后画它。
:::

::: details 练习 3：把画布内容存进 localStorage
刷新页面后还能恢复之前的草图，并且要求“恢复之后还能继续撤销”。

**思路**：存两组数据：`strokes` 和当前可撤销的命令列表。但**命令里引用的笔画对象必须一起存**，否则撤销时会拿到空对象。更简单的做法是只存 `strokes`，恢复时把它们当作“初始状态”，历史栈清空 —— 也就是说刷新之后不能撤销到刷新前。想清楚哪种更符合需求，这是这类功能的常见取舍。
:::

::: details 练习 4：支持导入一张背景图
让组织者上传场地平面图，画布上把它铺在底层，然后在上面标注。注意背景图不能挡住笔迹，也不能被橡皮擦擦掉。

**思路**：背景图单独用**另一个 `<canvas>` 或 `<img>` 放在绘图画布下面**，而不是画到同一张画布上。这样橡皮擦的 `destination-out` 不会擦到它，撤销重做也不用管它。如果一定要画在同一张画布上，就必须在每次 `redraw()` 时先铺背景、再重放笔画，并且橡皮擦的擦除范围要限制在标注层 —— **分层永远比在一层里做条件判断简单。**
:::

---

上一页：[案例 07 · 多步表单](/cases/07-wizard) · 下一页：[案例 09 · 可编辑表格](/cases/09-editable-table)
