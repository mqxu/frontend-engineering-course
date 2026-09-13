# 案例 08 · 画板与撤销重做（挑战档）

## 这个案例做什么

给校园活动服务平台加一个**场地平面示意图**功能。组织者发布活动时要说明场地怎么布置
（哪里是签到台、哪里是展览区），与其让用户手动画图上传，不如在页面里给一块画板：
用鼠标或手指拖动画出区域，画错了能撤销，还能撤销后再重做，最后导出成图片。

技术上有四件事要解决：

1. 用指针事件画出线条或圆点。
2. 把鼠标坐标正确换算到画布坐标系（要考虑设备像素比）。
3. 撤销 / 重做的双栈设计 —— **重点讲“什么时候要清空重做栈”**。
4. 导出成 PNG 或 SVG。

这个案例是加分任务，涉及直接操作 DOM 和命令式 API，是自定义指令和组合式函数的综合练习。

::: tip 先想清楚一件事：画布上的内容存什么
新手最容易犯的错是“画一笔就画在画布上，之后不做记录”。这样撤销时无从下手 ——
像素画上去就擦不干净了。

**正确做法是：把每一笔存成一个数据对象，画布只是这份数据的“渲染结果”。**
每次数据变了，就整体重画一遍。撤销 / 重做改的是数据，不是画布。
这个思路和 Vue 的“用状态描述界面”完全一致。
:::

## 第一部分：数据模型与坐标换算

### 一笔的形状

```js [src/composables/useDrawing.js（数据部分）]
// 一种笔：画笔（自由线条）、矩形（区域）、圆点（标记点）
// 每一种都只需要存“起点”和“若干点 / 终点”

let seed = 0
function createStroke(type, point, style) {
  return {
    id: ++seed,
    type,              // 'pen' | 'rect' | 'dot'
    points: [point],   // pen 用 points，rect 用 points[0] 与 points[1]
    style              // 颜色、线宽等
  }
}
```

一次完整的绘制过程是：

```text
pointerdown  → 新建一笔，记下起点，开始“绘制中”
pointermove  → 把当前点追加进去（pen）或更新终点（rect），实时重画
pointerup    → 这一笔结束，把它推进历史记录
```

### 坐标换算：设备像素比这一关

画布的显示尺寸（CSS 尺寸）和它内部的实际像素尺寸是两回事。
如果不处理，在 2 倍屏（Retina）上画出来的线会发虚模糊。

```js [尺寸初始化的正确写法]
function resize() {
  const canvas = canvasRef.value
  const rect = canvas.getBoundingClientRect()
  const dpr = window.devicePixelRatio || 1

  // 1. 把画布的“像素尺寸”设成 CSS 尺寸的 dpr 倍，这样才有足够清晰度
  canvas.width = Math.round(rect.width * dpr)
  canvas.height = Math.round(rect.height * dpr)

  // 2. 把绘图坐标系整体放大 dpr 倍
  //    之后我们就能一直用 CSS 像素坐标来画，不用每处乘 dpr
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)

  redraw()
}
```

::: warning 两个尺寸别搞混
| 名称 | 怎么设置 | 作用 |
| --- | --- | --- |
| CSS 尺寸 | 样式里的 `width` / `height` | 用户看到的物理大小 |
| 像素尺寸 | `canvas.width` / `canvas.height` | 画布内部有多少个像素可以画 |

不设 `canvas.width` 时它默认是 300×150，打开就是一片糊。
设了像素尺寸但不配 `ctx.scale`，坐标就对不上，画出来的位置会偏移。

**处理办法：像素尺寸 = CSS 尺寸 × dpr，然后用 `setTransform` 把坐标系放大回来。**
这样后面所有逻辑都用 CSS 像素坐标，简单又不出错。
:::

把屏幕坐标转成画布坐标：

```js [坐标换算]
function toCanvasPoint(event) {
  const rect = canvasRef.value.getBoundingClientRect()
  return {
    // 减去画布在页面中的位置，得到相对画布的坐标
    x: event.clientX - rect.left,
    y: event.clientY - rect.top
  }
}
```

因为我们已经用 `setTransform` 处理了 dpr，这里**不需要再乘 dpr**。
如果不用 `setTransform`，就要写成 `(event.clientX - rect.left) * dpr`，两处容易写岔。

## 第二部分：指针事件与指针捕获

鼠标、触摸、触控笔在浏览器里都能用 **Pointer Events** 统一处理，
所以只监听一套事件就够了：

```text
pointerdown  → 按下
pointermove  → 移动
pointerup    → 抬起
pointercancel → 被系统打断（如来电、手势）
```

### 指针捕获：为什么必须用

不用指针捕获时有个经典问题：**鼠标按住不放、快速拖出画布再松开，
`pointerup` 事件不会在画布上触发**（因为松手时指针已经不在画布上了），
于是这一笔永远停在“绘制中”，下一次进入画布会接着上一条线画。

`setPointerCapture` 解决的正是这件事：**把后续所有指针事件都定向到画布上，不管指针在哪。**

```js [pointerdown 里立即捕获]
function onPointerDown(event) {
  const point = toCanvasPoint(event)

  // 捕获指针：从这一刻起，这个 pointerId 的 move / up 都会发到 canvas 上
  canvasRef.value.setPointerCapture(event.pointerId)

  // 鼠标左键之外的按键不画
  if (event.pointerType === 'mouse' && event.button !== 0) return

  drawing.value = createStroke(currentTool.value, point, currentStyle.value)
  redraw()
}

function onPointerUp(event) {
  canvasRef.value.releasePointerCapture(event.pointerId)
  if (drawing.value) {
    commit(drawing.value)   // 把这一笔记入历史
    drawing.value = null
  }
}
```

::: details 指针捕获与 `pointercancel`
移动端手势、来电、切后台都可能发出 `pointercancel`，此时这一笔应该**丢弃**而不是提交。
所以 `pointercancel` 的处理和 `pointerup` 不同：不 commit，直接清掉 `drawing`：

```js
function onPointerCancel() {
  drawing.value = null
  redraw()
}
```
:::

## 第三部分：撤销与重做的双栈设计

这是本案例的核心，也是**最容易漏掉一条规则**的地方。

### 快照式历史记录

思路是每次“一笔完成”或“清空画布”时，把**操作前的完整状态**存进撤销栈：

```js [历史记录结构]
undoStack: [state0, state1, state2]   // 越靠后越新
redoStack: []
current:   state3                      // 当前状态
```

| 操作 | 做法 |
| --- | --- |
| 提交一次修改 | 把当前状态推进 `undoStack`，把新状态设为 `current`，**清空 `redoStack`** |
| 撤销 | 把 `current` 推进 `redoStack`，`undoStack` 弹出上一个设为 `current` |
| 重做 | 把 `current` 推进 `undoStack`，`redoStack` 弹出下一个设为 `current` |

```js [src/composables/useDrawing.js（历史部分）]
const strokes = ref([])
const undoStack = []
const redoStack = []

// 用于触发按钮的禁用状态
const canUndo = ref(false)
const canRedo = ref(false)

function syncFlags() {
  canUndo.value = undoStack.length > 0
  canRedo.value = redoStack.length > 0
}

/** 提交一次修改：把操作前的状态压入撤销栈 */
function commit(nextStrokes) {
  undoStack.push(strokes.value)
  strokes.value = nextStrokes

  // ★★★ 关键规则：产生新操作时，重做栈必须清空 ★★★
  redoStack.length = 0

  syncFlags()
}

function undo() {
  if (undoStack.length === 0) return
  redoStack.push(strokes.value)
  strokes.value = undoStack.pop()
  syncFlags()
}

function redo() {
  if (redoStack.length === 0) return
  undoStack.push(strokes.value)
  strokes.value = redoStack.pop()
  syncFlags()
}
```

### 为什么“产生新操作时要清空重做栈”

这是本节最需要记住的一条。看一个具体场景：

1. 画了三笔：A、B、C。此时 `undoStack = [空, A, A+B]`，`current = A+B+C`。
2. 撤销一次 —— 回到 `A+B`。此时 `redoStack = [A+B+C]`。
3. 现在**画一笔 D**。

问题来了：`A+B+C` 这条重做记录还该不该留着？

**不该。** 因为用户此刻走的是一条新分支（`A+B+D`），而 `A+B+C` 属于原来那条已经放弃的分支。
如果保留它，用户点重做会得到 `A+B+C`，把刚画的 D 覆盖掉 —— 用户会觉得“重做把我的图吞了”。

```text
分支视角：

画 A、B、C 后：  ──A──B──C
撤销一次：       ──A──B        （redo 里存着 C）
再画 D：
  ✗ 如果不清 redo：──A──B──D  但 redo 还指向 C，点重做会跳到 C，D 没了
  ✓ 清空 redo 后：──A──B──D  重做按钮变灰，符合“新分支没有未来”的直觉
```

::: danger 这条规则对应到界面上的表现
**撤销一次之后，只要用户又做了任何新操作，重做按钮就应该立刻变灰。**

如果你发现项目里出现过“重做按钮还能点，点了之后刚才画的东西消失了”，
基本就是这里漏了清空 `redoStack`。把 `redoStack.length = 0` 写进 `commit` 里，
**每一个“新操作”都走 `commit`**，就不会漏。
:::

::: tip 为什么用快照而不是“逆操作”
另一种实现是给每种操作写一个“反向操作”（画了一笔就记“删掉这一笔”）。
快照式简单得多：每次存整个数组的引用，代码量小、不会写错。

代价是内存：每步存一份数组。对画板这种规模（几百笔、每笔几十个点）完全够用。
如果数据量很大（比如几千笔），可以改成只存“新增的那一笔”，
或者用 `structuredClone` 前的引用共享 —— 但那是优化的范畴，**先让它正确，再让它快**。
:::

### 清空画布

清空也要能被撤销，所以要走 `commit`：

```js [清空]
function clear() {
  if (strokes.value.length === 0) return
  commit([])   // 走 commit，才能撤销回来
}
```

如果写成 `strokes.value = []` 而不走 `commit`，用户点清空后按撤销没反应，
是一个很典型的漏改。

## 第四部分：渲染循环

数据变了就整体重画。这个函数负责把 `strokes` 画到画布上：

```js [src/composables/useDrawing.js（渲染）]
function redraw(ctx, canvas, width, height) {
  // 先清空整块画布
  ctx.clearRect(0, 0, width, height)
  drawGrid(ctx, width, height)   // 背景网格，可省略

  // 依次画出每一笔
  for (const stroke of strokes.value) {
    drawStroke(ctx, stroke)
  }

  // 正在绘制中的那一笔也要画出来（实时预览）
  if (drawing.value) {
    drawStroke(ctx, drawing.value)
  }
}

function drawStroke(ctx, stroke) {
  const { type, points, style } = stroke
  if (points.length === 0) return

  ctx.strokeStyle = style.color
  ctx.fillStyle = style.color
  ctx.lineWidth = style.width
  ctx.lineCap = 'round'
  ctx.lineJoin = 'round'

  if (type === 'dot') {
    // 圆点标记
    const p = points[0]
    ctx.beginPath()
    ctx.arc(p.x, p.y, style.width, 0, Math.PI * 2)
    ctx.fill()
    return
  }

  if (type === 'rect') {
    // 矩形区域：起点到当前点
    const [start, end] = [points[0], points[points.length - 1]]
    if (!end) return
    ctx.strokeRect(start.x, start.y, end.x - start.x, end.y - start.y)
    return
  }

  // 自由线条：把所有点连起来
  ctx.beginPath()
  ctx.moveTo(points[0].x, points[0].y)
  for (let i = 1; i < points.length; i++) {
    ctx.lineTo(points[i].x, points[i].y)
  }
  ctx.stroke()
}
```

`pointermove` 里做两件事：更新当前笔画、请求重画。

```js [pointermove 用 requestAnimationFrame 节流]
let rafId = null

function scheduleRedraw() {
  if (rafId) return
  rafId = requestAnimationFrame(() => {
    rafId = null
    redraw()
  })
}

function onPointerMove(event) {
  if (!drawing.value) return
  const point = toCanvasPoint(event)

  if (drawing.value.type === 'pen') {
    drawing.value.points.push(point)
  } else {
    // 矩形只需要保留起点和当前点
    drawing.value.points[1] = point
  }
  scheduleRedraw()
}
```

::: warning 别在 pointermove 里直接重画
`pointermove` 一秒能触发上百次，每次都 `clearRect` + 重画全部笔画，会明显卡顿。

用 `requestAnimationFrame` 把重画压到每帧最多一次（约每秒 60 次）：
**“事件频繁触发、但渲染只需要跟上屏幕刷新率”的场合，这是标准做法。**
指针移动事件通常不会比屏幕刷新还快，所以这里用 rAF 就够了。
:::

## 第五部分：导出图片与 SVG

### 导出 PNG

```js [导出 PNG]
function exportPng(filename = '场地示意图.png') {
  // toDataURL 得到的是 base64 图片数据
  const url = canvasRef.value.toDataURL('image/png')

  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
}
```

::: details 导出时白底
画布默认是透明的，导出 PNG 打开可能是黑底或透明。
如果希望有白底，导出前先临时画一层白色矩形：

```js
function exportPngWithBackground() {
  const canvas = canvasRef.value
  const ctx = canvas.getContext('2d')

  // 用一个离屏画布，避免污染当前画布
  const off = document.createElement('canvas')
  off.width = canvas.width
  off.height = canvas.height
  const offCtx = off.getContext('2d')

  offCtx.fillStyle = '#fff'
  offCtx.fillRect(0, 0, off.width, off.height)
  offCtx.drawImage(canvas, 0, 0)

  const url = off.toDataURL('image/png')
  // …下载
}
```
:::

### 导出 SVG

SVG 的好处是**无损放大、体积小、还能二次编辑**。因为我们的笔画本来就是矢量数据
（点、线、矩形），直接拼成 SVG 字符串就行：

```js [导出 SVG]
function exportSvg(width, height) {
  const parts = []

  parts.push(`<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}">`)
  parts.push(`<rect width="100%" height="100%" fill="#fff"/>`)

  for (const stroke of strokes.value) {
    const { type, points, style } = stroke
    if (points.length === 0) continue

    if (type === 'dot') {
      const p = points[0]
      parts.push(`<circle cx="${p.x}" cy="${p.y}" r="${style.width}" fill="${style.color}"/>`)
    } else if (type === 'rect') {
      const [s, e] = [points[0], points[points.length - 1]]
      if (!e) continue
      parts.push(
        `<rect x="${s.x}" y="${s.y}" width="${e.x - s.x}" height="${e.y - s.y}" ` +
          `fill="none" stroke="${style.color}" stroke-width="${style.width}"/>`
      )
    } else {
      const d = points.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x} ${p.y}`).join(' ')
      parts.push(
        `<path d="${d}" fill="none" stroke="${style.color}" ` +
          `stroke-width="${style.width}" stroke-linecap="round" stroke-linejoin="round"/>`
      )
    }
  }

  parts.push('</svg>')

  const blob = new Blob([parts.join('\n')], { type: 'image/svg+xml' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = '场地示意图.svg'
  a.click()
  URL.revokeObjectURL(url)   // 用完释放，避免内存泄漏
}
```

::: tip 为什么 SVG 更好存
PNG 是**结果**，SVG 是**过程**。本项目里笔画本身就是矢量数据，导出 SVG 等于把数据换个格式写出，
不需要任何转换。用户下次导入 SVG 就能继续编辑。

**凡是你手里已经有结构化的矢量数据，优先导出 SVG**：放大不糊、文件更小。
只有涉及图像、渐变、滤镜这些光栅内容时，才必须用 PNG。
:::

## 完整组件

把上面的部分拼起来：

```vue [src/components/ActivityCanvas.vue]
<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useDrawing } from '@/composables/useDrawing'

const canvasRef = ref(null)
const {
  strokes, currentTool, currentStyle,
  canUndo, canRedo,
  startStroke, extendStroke, endStroke, cancelStroke,
  undo, redo, clear,
  exportPng, exportSvg,
  bindCanvas
} = useDrawing(canvasRef)

let ctx = null
let resizeObserver = null

onMounted(() => {
  const canvas = canvasRef.value
  ctx = canvas.getContext('2d')
  bindCanvas(ctx)

  // 监听尺寸变化，尺寸变了要重新设置像素尺寸
  resizeObserver = new ResizeObserver(() => {
    resize()
  })
  resizeObserver.observe(canvas)

  resize()
})

onUnmounted(() => {
  resizeObserver?.disconnect()
})

function resize() {
  const canvas = canvasRef.value
  const rect = canvas.getBoundingClientRect()
  const dpr = window.devicePixelRatio || 1

  canvas.width = Math.round(rect.width * dpr)
  canvas.height = Math.round(rect.height * dpr)
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)

  ctx.clearRect(0, 0, rect.width, rect.height)
  // redraw 会用到最新的宽高
  bindCanvas(ctx, rect.width, rect.height)
}

// 键盘快捷键：Ctrl / Cmd + Z 撤销，加 Shift 重做
function onKeydown(e) {
  const mod = e.ctrlKey || e.metaKey
  if (!mod || e.key.toLowerCase() !== 'z') return
  e.preventDefault()
  e.shiftKey ? redo() : undo()
}

onMounted(() => document.addEventListener('keydown', onKeydown))
onUnmounted(() => document.removeEventListener('keydown', onKeydown))
</script>

<template>
  <div class="canvas-board">
    <div class="toolbar">
      <button :class="{ active: currentTool === 'pen' }" @click="currentTool = 'pen'">画笔</button>
      <button :class="{ active: currentTool === 'rect' }" @click="currentTool = 'rect'">区域</button>
      <button :class="{ active: currentTool === 'dot' }" @click="currentTool = 'dot'">标记点</button>

      <input v-model="currentStyle.color" type="color" aria-label="颜色" />
      <input v-model.number="currentStyle.width" type="range" min="1" max="20" aria-label="线宽" />

      <button :disabled="!canUndo" @click="undo">撤销</button>
      <button :disabled="!canRedo" @click="redo">重做</button>
      <button @click="clear">清空</button>
      <button @click="exportPng()">导出 PNG</button>
      <button @click="exportSvg()">导出 SVG</button>
    </div>

    <canvas
      ref="canvasRef"
      class="canvas"
      @pointerdown="startStroke"
      @pointermove="extendStroke"
      @pointerup="endStroke"
      @pointercancel="cancelStroke"
    />
  </div>
</template>

<style scoped>
.canvas {
  width: 100%;
  height: 480px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  /* 关键：禁用浏览器默认的触摸滚动 / 缩放手势，否则画线和页面滚动会打架 */
  touch-action: none;
  cursor: crosshair;
  display: block;
}

.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 10px;
}

.toolbar button.active {
  outline: 2px solid #2563eb;
}
</style>
```

::: warning `touch-action: none` 不能漏
在触屏设备上，手指在画布上滑动时，浏览器默认会把它当成**页面滚动**，
于是 `pointermove` 会被取消，画出来的线断断续续。

`touch-action: none` 告诉浏览器“这块区域的手势由我自己处理”。
**这是移动端画板必须加的一行。**
:::

## 小结

- **数据驱动渲染**：每一笔存成数据对象，画布只是数据的渲染结果；撤销改的是数据。
- 画布有两个尺寸：CSS 尺寸（显示）与像素尺寸（`canvas.width`），
  用“像素尺寸 = CSS 尺寸 × dpr + `setTransform` 放大坐标系”处理清晰度。
- 指针事件统一鼠标与触摸；`setPointerCapture` 保证拖出画布松手也能收到 `pointerup`。
- `touch-action: none` 防止触摸滑动被当成页面滚动。
- 撤销 / 重做用双栈：`commit` 把旧状态压入撤销栈并**清空重做栈**；
  撤销把当前压入重做栈，重做把当前压入撤销栈。
- **产生新操作必须清空重做栈**，否则会出现“重做吞掉刚画的图”。
- 清空画布也要走 `commit`，否则不可撤销。
- 频繁的 `pointermove` 用 `requestAnimationFrame` 节流，每帧最多重画一次。
- 有矢量数据时优先导出 SVG（无损、小、可再编辑），需要固定效果时导出 PNG。

## 常见坑

::: details 坑 1：画出来的线发虚、位置偏移
现象：在 2 倍屏上线条模糊，或者画的点和鼠标位置对不上。

原因：没有处理 `devicePixelRatio`，或者处理了一半（设了像素尺寸但没缩放坐标系）。

处理：`canvas.width = rect.width * dpr`，并且 `ctx.setTransform(dpr, 0, 0, dpr, 0, 0)`。
之后所有坐标都用 CSS 像素，别再乘 dpr。
:::

::: details 坑 2：拖出画布松手，这一笔画不完
现象：线条一直连着，鼠标移回画布会继续画。

原因：没有用 `setPointerCapture`，`pointerup` 发到了别的元素上。

处理：`pointerdown` 里立刻 `setPointerCapture(event.pointerId)`，
`pointerup` 里 `releasePointerCapture`。注意 `pointercancel` 要单独处理，丢弃这一笔。
:::

::: details 坑 3：撤销一次后再画，重做按钮还能点，点了内容被吞
现象：就是你，重做栈没清。

原因：`commit` 里漏了 `redoStack.length = 0`。

处理：把清空重做栈写进 `commit` 内部，让“新操作必走 commit”成为唯一入口。
:::

::: details 坑 4：清空之后撤销不回来
现象：点清空，按撤销无反应。

原因：清空直接改了 `strokes.value`，没走 `commit`。

处理：`clear()` 写成 `commit([])`。
:::

::: details 坑 5：移动端画不了，页面在滚
现象：手指滑动时页面滚动，画布上没有线。

原因：浏览器默认把触摸手势当成滚动。

处理：画布加 `touch-action: none`。
:::

::: details 坑 6：导出 SVG 后图片显示不全
现象：SVG 打开只有一部分图形。

原因：SVG 的 `width` / `height` 用了画布像素尺寸（含 dpr 放大），
但坐标是 CSS 尺寸，两者差了一个 dpr。

处理：导出时用 CSS 尺寸作为 SVG 的 `width` / `height`，
或者把坐标乘上 dpr。**保持坐标系一致**即可。
:::

## 课后练习

::: details 练习 1：加一个“橡皮擦”
增加 `eraser` 工具，擦掉经过的笔画。

**思路**：不要用 `clearRect` 擦像素（那样画布就变了，撤销也没法处理）。
正确做法是判断哪些笔画被“擦”到了，把它们从 `strokes` 里删掉，然后走 `commit`。
判断方式可以用“点到线段的距离小于阈值”。
:::

::: details 练习 2：把历史记录改成有上限
给撤销栈设一个最大长度（比如 50 步），超过就丢弃最老的记录。

**思路**：`commit` 里 `if (undoStack.length > 50) undoStack.shift()`。
想一想：为什么要有上限？（内存）为什么按钮禁用状态要跟着改？
:::

::: details 练习 3：把画板做成自定义指令
把“初始化画布尺寸、绑定指针事件、清理监听”这部分做成 `v-canvas` 指令。

**思路**：`mounted` 里初始化并绑定，`unmounted` 里解绑并断开 `ResizeObserver`。
思考：指令适合这种场景吗？还是组合式函数更合适？把你的判断理由写下来。
:::

---

上一节：[案例 06 · 模态框与全局通知](/unit08/06-case-modal) ·
下一节：[单元 8 课后练习](/unit08/practice)
