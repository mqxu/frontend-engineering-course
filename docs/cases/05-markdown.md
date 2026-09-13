# 案例 05 · Markdown 编辑器

## 案例要做什么

组织者发布活动时，要写一段“活动详情”。这段内容有标题、有列表、有加粗重点，用纯文本框写很不方便，
用富文本编辑器又太重 —— 而且富文本存出来的是 HTML，脏标签多。

所以做一个 **Markdown 编辑器**：左边写 Markdown 源文，右边实时看到渲染结果；上方一排按钮，
点一下就插入对应的语法，不用自己敲星号；写完能导出成一份独立的 HTML 文件。

这个案例的两个技术含量点：**一是在光标位置插入文本**（要会算 `selectionStart` 和 `selectionEnd`），
**二是把自定义组件接到 `v-model` 上**（父组件只看到 `v-model`，不关心内部怎么实现）。

| 知识点 | 用在哪里 | 对应章节 |
| --- | --- | --- |
| `v-model` 自定义组件 | 编辑器整体对外只暴露一个 `v-model` | [组件上的 v-model](/unit07/04-vmodel) |
| `defineModel` | 在 `<script setup>` 里声明 `v-model` | [组件上的 v-model](/unit07/04-vmodel) |
| 表单绑定 | 左侧输入框与父组件状态同步 | [表单绑定](/unit06/03-form-binding) |
| 事件处理 | 工具栏按钮、输入事件 | [事件处理的完整写法](/unit06/01-events) |
| `nextTick` | 改完内容后再设置光标位置 | [生命周期与副作用清理](/unit06/05-lifecycle) |
| `watch` 与清理 | 输入防抖、卸载时清定时器 | [侦听器](/unit05/02-watch) |

::: warning 一个必须先说清的取舍
本案例的解析器是**为了讲清原理而手写的**，只支持常用语法。生产项目请用
`markdown-it`（成熟、可选插件多、边界处理完善）配合 `DOMPurify` 做净化。
手写这一遍的价值在于：你会知道 `v-html` 为什么危险、解析为什么要先转义。
:::

## 数据结构与接口设计

### 组件对外只有一个值

编辑器的数据形态非常简单：**一个字符串**。所有功能都围绕它。

```js [组件接口]
// 父组件这样用
// <MarkdownEditor v-model="form.description" />

// 子组件内部的“值”就是一个字符串
const value = defineModel({ type: String, default: '' })
```

`defineModel` 是 Vue 3.4 之后稳定下来的写法，它把过去要写的 `props.modelValue` +
`emits('update:modelValue')` 两件事合成一行。本课程基线是 Vue 3.5.42，可以放心使用。

### 工具栏的配置也当成数据

六个按钮如果每个都写一段 `<button @click="...">`，模板会又长又重复。把它们描述成数组：

```js [工具栏配置]
const tools = [
  { label: 'B', title: '加粗', run: () => wrapSelection('**') },
  { label: 'I', title: '斜体', run: () => wrapSelection('*') },
  { label: '‹›', title: '行内代码', run: () => wrapSelection('`') },
  { label: 'H2', title: '二级标题', run: () => prefixLine('## ') },
  { label: '•', title: '无序列表', run: () => prefixLine('- ') },
  { label: '❝', title: '引用', run: () => prefixLine('> ') }
]
```

按钮分成两类，这是本案例的结构主线：

| 类型 | 例子 | 操作对象 | 需要什么光标信息 |
| --- | --- | --- | --- |
| 包裹式 | 加粗、斜体、行内代码 | 选中的一段文字 | 选区起点 `selectionStart`、终点 `selectionEnd` |
| 行首式 | 标题、列表、引用 | 光标所在的**整行** | 行首位置、行尾位置 |

### 支持的 Markdown 语法范围

先划清边界，免得写着写着失控。本案例的解析器支持：

| 语法 | 写法 | 输出 |
| --- | --- | --- |
| 标题 | `#` 到 `######` 开头 | `<h1>` 到 `<h6>` |
| 无序列表 | `- ` 或 `* ` 开头 | `<ul><li>` |
| 有序列表 | `1. ` 开头 | `<ol><li>` |
| 引用 | `> ` 开头 | `<blockquote>` |
| 代码块 | 三个反引号包裹 | `<pre><code>` |
| 行内代码 | 一对反引号 | `<code>` |
| 加粗 / 斜体 | 双星号 / 单星号 | `<strong>` / `<em>` |
| 链接 | `[文字](https://…)` | `<a>` |

**不支持**表格、任务列表、脚注、嵌套列表。这些用 `markdown-it` 都能拿到，
但自己写一遍不划算 —— 知道边界在哪，比硬撑一个“什么都支持”的半成品更有价值。

## 实现步骤

### 步骤 1 · 用 `defineModel` 把组件接到 `v-model`

```js [定义组件的值]
const value = defineModel({ type: String, default: '' })
```

就这么一行，父组件写 `<MarkdownEditor v-model="form.description" />` 就能双向绑定。
`value` 在模板里当普通 ref 用，在 `<script setup>` 里要用 `value.value` 读写。

::: tip 三个等价写法，记住现在这种
过去常见两种写法：`props.modelValue` + `emit('update:modelValue', …)`，或者用
`v-model:value` 换名字。`defineModel` 把第一种收敛成一行，**新项目直接用 `defineModel`。**
:::

### 步骤 2 · 左右分栏与预览：为什么必须“先转义”

右侧预览要用 `v-html` 把渲染结果插进 DOM。这是整个案例里最危险的一行：

```vue
<div class="pane preview" v-html="renderedHtml"></div>
```

如果直接把用户输入交给 `v-html`，用户在内容里写一段 `<img src=x onerror="…">` 就能执行脚本。
所以解析的第一步是**把源文里所有 HTML 特殊字符转义掉**：

```js [escapeHtml]
function escapeHtml(text) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}
```

转义之后，用户输入的 `<` 变成 `&lt;`，不可能再变成标签。之后解析器拼出来的
`<strong>`、`<h2>` 这些标签是我们自己写的字符串，只有它们能成为真正的 HTML。

::: danger 这个顺序不能颠倒
“先转义、再拼标签”和“先拼标签、再转义”完全是两回事。
如果先拼再转义，你自己写的 `<strong>` 也会被转义成文本，页面显示成一堆标签；
如果先转义再允许用户输入进白名单，那需要一套完整的净化规则。

**结论：转义全部输入，只拼接自己生成的标签。** 这是最小、最容易验证正确的做法。
:::

### 步骤 3 · 简易 Markdown 解析器

解析分两层：**逐行判断块级语法**，行内再替换行内语法。块级用一个循环加状态变量搞定：

```js [块级解析的骨架]
const lines = escapeHtml(source).split('\n')
const out = []
let listTag = ''   // 当前打开的是 ul 还是 ol
let inCode = false // 是否在代码块里

for (const line of lines) {
  // 1. 代码块围栏：进入或离开代码块
  // 2. 代码块内部：原样输出，不做任何替换
  // 3. 标题：/^(#{1,6})\s+(.*)$/
  // 4. 引用：/^>\s?(.*)$/
  // 5. 无序列表：/^\s*[-*]\s+(.*)$/
  // 6. 有序列表：/^\s*\d+\.\s+(.*)$/
  // 7. 空行：关闭列表
  // 8. 其它：当成段落
}
```

有两个容易写错的地方：

**第一个：列表要收尾。** 循环结束时如果列表还开着，要补一个闭合标签，
否则 HTML 结构不完整，浏览器会自己猜，渲染结果可能和预期差很远。

**第二个：行内替换有顺序。** 代码要最先处理，因为代码里的星号不该被当成加粗：

```js [renderInline]
function renderInline(text) {
  return text
    // 行内代码最先，保护代码里的星号
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\*([^*]+)\*/g, '<em>$1</em>')
    .replace(
      /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
      '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>'
    )
}
```

链接只允许 `http` 和 `https` 开头，是为了挡住 `javascript:` 这种协议 ——
它在浏览器里点一下就能执行脚本，是 `v-html` 场景里的经典攻击方式。

### 步骤 4 · 包裹式语法：在选区两端插字符

用户在文本框里选中“校园歌手大赛”，点“加粗”，期望得到 `**校园歌手大赛**`，
并且光标仍然选中中间那几个字，方便继续操作。

```js [wrapSelection]
function wrapSelection(prefix, suffix = prefix, placeholder = '内容') {
  const el = editor.value
  if (!el) return

  const start = el.selectionStart
  const end = el.selectionEnd
  // 没选中任何东西时用占位文字，插入后用户可以直接改写
  const selected = value.value.slice(start, end) || placeholder

  value.value = value.value.slice(0, start) + prefix + selected + suffix + value.value.slice(end)

  // 等 DOM 更新完再重设选区，否则位置会被 v-model 的重渲染覆盖
  nextTick(() => {
    el.focus()
    el.setSelectionRange(start + prefix.length, start + prefix.length + selected.length)
  })
}
```

三个细节：

| 细节 | 为什么 |
| --- | --- |
| `nextTick` | `value.value` 改完，DOM 还没更新。立刻设选区会被覆盖 |
| `start + prefix.length` | 选区起点要跳过插入的前缀，否则一选中就连星号一起选上 |
| `selected \|\| placeholder` | 没选中文字时插入“内容”两个占位字，比插入一对空星号好操作 |

**工具栏（二）：行首式语法，整行加前缀，再点一次取消。**

标题、列表、引用都是“给整行加一个前缀”。用户点了“H2”，就是把光标所在行变成 `## 正文`。
如果这一行已经是 `## ` 开头，再点一次应该去掉 —— 这样按钮变成了开关。

```js [prefixLine]
function prefixLine(marker) {
  const el = editor.value
  if (!el) return

  const start = el.selectionStart
  const lineStart = value.value.lastIndexOf('\n', start - 1) + 1
  const endIndex = value.value.indexOf('\n', start)
  const lineEnd = endIndex === -1 ? value.value.length : endIndex
  const line = value.value.slice(lineStart, lineEnd)

  // 已经有同样的前缀就去掉，相当于再点一次切换回来
  const nextLine = line.startsWith(marker) ? line.slice(marker.length) : marker + line
  value.value = value.value.slice(0, lineStart) + nextLine + value.value.slice(lineEnd)

  // 光标按行的长度变化量平移
  const shift = nextLine.length - line.length
  const caret = Math.max(lineStart, start + shift)

  nextTick(() => {
    el.focus()
    el.setSelectionRange(caret, caret)
  })
}
```

`lastIndexOf('\n', start - 1)` 这个写法值得记一下：它从光标位置往前找换行符，
加 1 就是行首。**如果找不到，`lastIndexOf` 返回 -1，加 1 正好是 0**，也就是第一行 ——
不需要额外判断“是不是第一行”。

### 步骤 5 · 输入防抖：别每敲一个字就重新解析

解析整篇文档是 O(n) 的操作。文档写长了以后，每敲一个字都重新渲染右侧预览，
输入会明显发涩。做法是延迟 150 毫秒再更新预览：

```js [预览的防抖]
const debouncedSource = ref(value.value)
let timer = 0

watch(value, (next) => {
  clearTimeout(timer)
  timer = setTimeout(() => {
    debouncedSource.value = next
  }, 150)
})

const renderedHtml = computed(() => renderMarkdown(debouncedSource.value))

onBeforeUnmount(() => clearTimeout(timer))
```

注意用了两个变量：`value` 是编辑器里的实时内容（必须实时，否则打字会丢字符），
`debouncedSource` 是给预览用的延迟内容。**不要把 `value` 本身做成防抖的** ——
那样输入框会变得一卡一卡的。

### 步骤 6 · 导出成独立的 HTML 文件

导出的目标是“双击就能在浏览器里打开”的单文件。用 `Blob` 打包内容，
用 `URL.createObjectURL` 生成临时地址，再用一个隐藏的 `<a>` 触发下载：

```js [exportHtml]
function exportHtml() {
  // 省略文件头样式
  const html = `<!DOCTYPE html><html>…${renderedHtml.value}…</html>`
  const blob = new Blob([html], { type: 'text/html;charset=utf-8' })
  const url = URL.createObjectURL(blob)

  const link = document.createElement('a')
  link.href = url
  link.download = 'activity-detail.html'
  link.click()

  // 用完立刻释放，否则这块内存要等到页面关闭才回收
  URL.revokeObjectURL(url)
}
```

`URL.revokeObjectURL(url)` 这一句不能省。每次导出都会生成一个新的内存地址，
不释放就是内存泄漏。

## 完整代码

```js [src/utils/markdown.js]
/**
 * 只支持常用语法的 Markdown 渲染器，用于讲清原理。
 * 生产项目建议用 markdown-it 加 DOMPurify。
 */

function escapeHtml(text) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function renderInline(text) {
  return text
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\*([^*]+)\*/g, '<em>$1</em>')
    .replace(
      /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
      '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>'
    )
}

export function renderMarkdown(source) {
  // 先整体转义，后面拼接的标签都是自己生成的，才可能成为真正的 HTML
  const lines = escapeHtml(source).split('\n')
  const out = []
  let listTag = ''
  let inCode = false

  const closeList = () => {
    if (listTag) {
      out.push(`</${listTag}>`)
      listTag = ''
    }
  }

  for (const line of lines) {
    if (/^\s*```/.test(line)) {
      closeList()
      out.push(inCode ? '</code></pre>' : '<pre><code>')
      inCode = !inCode
      continue
    }

    if (inCode) {
      out.push(line)
      continue
    }

    const heading = line.match(/^(#{1,6})\s+(.*)$/)
    if (heading) {
      closeList()
      const level = heading[1].length
      out.push(`<h${level}>${renderInline(heading[2])}</h${level}>`)
      continue
    }

    const quote = line.match(/^>\s?(.*)$/)
    if (quote) {
      closeList()
      out.push(`<blockquote>${renderInline(quote[1])}</blockquote>`)
      continue
    }

    const unordered = line.match(/^\s*[-*]\s+(.*)$/)
    if (unordered) {
      if (listTag !== 'ul') {
        closeList()
        out.push('<ul>')
        listTag = 'ul'
      }
      out.push(`<li>${renderInline(unordered[1])}</li>`)
      continue
    }

    const ordered = line.match(/^\s*\d+\.\s+(.*)$/)
    if (ordered) {
      if (listTag !== 'ol') {
        closeList()
        out.push('<ol>')
        listTag = 'ol'
      }
      out.push(`<li>${renderInline(ordered[1])}</li>`)
      continue
    }

    if (line.trim() === '') {
      closeList()
      continue
    }

    closeList()
    out.push(`<p>${renderInline(line)}</p>`)
  }

  // 收尾：列表和代码块都可能还开着
  closeList()
  if (inCode) out.push('</code></pre>')

  return out.join('\n')
}
```

```vue [MarkdownEditor.vue]
<script setup>
import { computed, nextTick, onBeforeUnmount, ref, useTemplateRef, watch } from 'vue'
import { renderMarkdown } from '@/utils/markdown'

const value = defineModel({ type: String, default: '' })

const editor = useTemplateRef('editor')

// 预览用延迟后的内容，输入框用实时内容
const debouncedSource = ref(value.value)
let timer = 0

watch(value, (next) => {
  clearTimeout(timer)
  timer = setTimeout(() => {
    debouncedSource.value = next
  }, 150)
})

const renderedHtml = computed(() => renderMarkdown(debouncedSource.value))

// ── 包裹式语法 ───────────────────────────────────────
function wrapSelection(prefix, suffix = prefix, placeholder = '内容') {
  const el = editor.value
  if (!el) return

  const start = el.selectionStart
  const end = el.selectionEnd
  const selected = value.value.slice(start, end) || placeholder

  value.value = value.value.slice(0, start) + prefix + selected + suffix + value.value.slice(end)

  nextTick(() => {
    el.focus()
    el.setSelectionRange(start + prefix.length, start + prefix.length + selected.length)
  })
}

// ── 行首式语法 ───────────────────────────────────────
function prefixLine(marker) {
  const el = editor.value
  if (!el) return

  const start = el.selectionStart
  const lineStart = value.value.lastIndexOf('\n', start - 1) + 1
  const endIndex = value.value.indexOf('\n', start)
  const lineEnd = endIndex === -1 ? value.value.length : endIndex
  const line = value.value.slice(lineStart, lineEnd)

  const nextLine = line.startsWith(marker) ? line.slice(marker.length) : marker + line
  value.value = value.value.slice(0, lineStart) + nextLine + value.value.slice(lineEnd)

  const shift = nextLine.length - line.length
  const caret = Math.max(lineStart, start + shift)

  nextTick(() => {
    el.focus()
    el.setSelectionRange(caret, caret)
  })
}

const tools = [
  { label: 'B', title: '加粗', run: () => wrapSelection('**') },
  { label: 'I', title: '斜体', run: () => wrapSelection('*') },
  { label: '‹›', title: '行内代码', run: () => wrapSelection('`') },
  { label: 'H2', title: '二级标题', run: () => prefixLine('## ') },
  { label: '•', title: '无序列表', run: () => prefixLine('- ') },
  { label: '❝', title: '引用', run: () => prefixLine('> ') }
]

// ── 导出 ────────────────────────────────────────────
const EXPORT_STYLE = [
  'body{max-width:720px;margin:40px auto;padding:0 16px;font-family:system-ui,sans-serif;line-height:1.75;color:#1f2328}',
  'pre{background:#f6f8fa;padding:12px;border-radius:6px;overflow:auto}',
  'code{background:#f6f8fa;padding:1px 4px;border-radius:3px}',
  'blockquote{margin:0;padding-left:12px;border-left:3px solid #d0d5dd;color:#6b7280}'
].join('')

function exportHtml() {
  // 导出文档的标题用固定文字，避免把用户输入拼进文件头
  const html = [
    '<!DOCTYPE html>',
    '<html lang="zh-CN">',
    '<head>',
    '<meta charset="UTF-8" />',
    '<title>活动详情</title>',
    `<style>${EXPORT_STYLE}</style>`,
    '</head>',
    '<body>',
    renderedHtml.value,
    '</body>',
    '</html>'
  ].join('\n')

  const blob = new Blob([html], { type: 'text/html;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'activity-detail.html'
  link.click()
  URL.revokeObjectURL(url)
}

onBeforeUnmount(() => clearTimeout(timer))
</script>

<template>
  <section class="md-editor">
    <div class="toolbar">
      <button
        v-for="tool in tools"
        :key="tool.title"
        type="button"
        :title="tool.title"
        @mousedown.prevent
        @click="tool.run"
      >
        {{ tool.label }}
      </button>
      <span class="spacer"></span>
      <button type="button" @mousedown.prevent @click="exportHtml">导出 HTML</button>
    </div>

    <div class="panes">
      <textarea
        ref="editor"
        v-model="value"
        class="pane input"
        placeholder="在这里写活动详情，支持标题、加粗、列表、引用、行内代码"
      ></textarea>
      <div class="pane preview" v-html="renderedHtml"></div>
    </div>

    <footer class="foot">{{ value.length }} 字</footer>
  </section>
</template>

<style scoped>
.md-editor {
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  overflow: hidden;
  font-size: 14px;
}
.toolbar {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 8px;
  background: #f9fafb;
  border-bottom: 1px solid #e5e7eb;
}
.toolbar button {
  min-width: 30px;
  padding: 4px 8px;
  border: 1px solid #d0d5dd;
  border-radius: 4px;
  background: #fff;
  cursor: pointer;
}
.spacer {
  flex: 1;
}
.panes {
  display: grid;
  grid-template-columns: 1fr 1fr;
}
.pane {
  min-height: 320px;
  padding: 12px;
}
.input {
  border: none;
  border-right: 1px solid #e5e7eb;
  resize: none;
  outline: none;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}
.preview {
  overflow: auto;
}
.preview :deep(h1),
.preview :deep(h2) {
  margin: 12px 0 8px;
}
.preview :deep(blockquote) {
  margin: 0;
  padding-left: 12px;
  border-left: 3px solid #d0d5dd;
  color: #6b7280;
}
.preview :deep(pre) {
  background: #f6f8fa;
  padding: 10px;
  border-radius: 4px;
  overflow: auto;
}
.preview :deep(code) {
  background: #f6f8fa;
  padding: 1px 4px;
  border-radius: 3px;
}
.foot {
  padding: 6px 10px;
  border-top: 1px solid #e5e7eb;
  color: #9ca3af;
  text-align: right;
}
</style>
```

在活动表单里使用：

```vue [ActivityForm.vue]
<script setup>
import { ref } from 'vue'
import MarkdownEditor from '@/components/MarkdownEditor.vue'

const form = ref({
  title: '校园歌手大赛',
  description: '## 活动简介\n\n面向全校学生，**无需报名费**。\n\n- 初赛：10 月 12 日\n- 决赛：10 月 26 日'
})
</script>

<template>
  <form class="activity-form">
    <label class="field">
      活动标题
      <input v-model="form.title" class="input" />
    </label>

    <p class="label">活动详情</p>
    <MarkdownEditor v-model="form.description" />
  </form>
</template>
```

### 换成 `markdown-it` 的方式

手写解析器只覆盖了常用语法。要支持表格、任务列表、嵌套列表，换成成熟库就行：

```bash
pnpm add markdown-it dompurify
```

```js [接入 markdown-it]
import MarkdownIt from 'markdown-it'
import DOMPurify from 'dompurify'

const md = new MarkdownIt({ html: false, linkify: true, breaks: true })

const renderedHtml = computed(() => {
  // html: false 已经禁掉了原始 HTML，DOMPurify 再做一层净化兜底
  return DOMPurify.sanitize(md.render(debouncedSource.value))
})
```

两个参数说明：`html: false` 表示**不允许源文里的原始 HTML 通过**，
这是最关键的一道防线；`linkify: true` 会把纯文本里的网址自动变成链接。
即使如此，仍然建议保留 `DOMPurify` —— 库的默认行为会随版本变化，多一层防护成本很低。

## 常见坑

::: details 坑 1：`v-html` 直接渲染用户输入，被脚本注入
**现象**：在活动详情里输入一段带 `onerror` 的图片标签，预览时触发了脚本，或者弹出了 alert。

**原因**：`v-html` 会把字符串当成真正的 HTML 插入。用户的输入里可以包含任意标签和属性，
包括能执行脚本的那些。

**怎么处理**：**输入全部转义，只拼接自己生成的标签。** 链接还要限制协议为 `http` / `https`。
如果一定要允许用户写 HTML（比如富文本编辑器），就必须用 `DOMPurify` 之类的库做白名单净化，
不要试图自己写正则过滤 —— 那是一定会被绕过的。
:::

::: details 坑 2：点工具栏按钮后光标跳到了开头
**现象**：选中一段文字，点“加粗”，结果星号插在了文档最前面，而不是选区两端。

**原因**：`mousedown` 会让 `<textarea>` 失去焦点，某些浏览器下 `selectionStart` 被重置为 0。

**怎么处理**：在工具栏按钮上写 `@mousedown.prevent`，阻止默认的焦点转移行为。
这样点击过程中文本框一直是焦点状态，`selectionStart` 保持正确。
:::

::: details 坑 3：设置选区位置不生效
**现象**：`setSelectionRange` 明明调了，光标还是停在末尾。

**原因**：`v-model` 改了值之后，Vue 要等下一个 DOM 更新周期才把新内容写进文本框。
在同一个同步流程里设置选区，位置会被随后的重渲染覆盖。

**怎么处理**：**把设置选区的代码放进 `nextTick` 回调。** 顺序是“改值 → 等 DOM 更新 → 选中”。
:::

::: details 坑 4：代码块里的星号被当成加粗
**现象**：写 `**变量**` 这样的示例代码放在代码块里，预览里却真变成了加粗文字。

**原因**：行内替换的正则无视代码块边界，对整行都做了替换。

**怎么处理**：解析要分段 —— 块级循环里判断“当前是否在代码块内”，
在代码块内**原样输出、不做任何行内替换**。行内替换本身也要让代码最先处理，
把代码里的内容先保护起来。
:::

::: details 坑 5：中文输入法打字时预览乱跳
**现象**：用拼音输入法打中文，还没选词，预览就开始跟着变化，甚至把拼音字母渲染出来。

**原因**：输入法在“组合中”（composition）阶段会不断触发 `input` 事件，
这些中间态并不代表用户最终输入的内容。

**怎么处理**：监听 `compositionstart` 和 `compositionend`，在组合期间不更新预览：

```js
let composing = false

function onCompositionStart() {
  composing = true
}

function onCompositionEnd() {
  composing = false
  debouncedSource.value = value.value
}
```

配合已有的防抖，输入法场景基本就没有问题了。
:::

::: details 坑 6：防抖定时器没清理，组件卸载后还在跑
**现象**：切走页面之后，控制台里还能看到预览相关的计算。

**原因**：`setTimeout` 排在事件循环里，组件卸载不会自动取消。

**怎么处理**：把定时器 id 存在组件作用域，`onBeforeUnmount` 里 `clearTimeout`。
另外把 `debouncedSource` 初值设成 `value.value`，否则组件挂载时预览是空的。
:::

::: details 坑 7：导出的文件里内容不全
**现象**：刚打完字马上点导出，导出的 HTML 里少了最后几个字。

**原因**：预览用的是防抖后的内容 `debouncedSource`，而导出直接用了 `renderedHtml`，
它比实际输入慢 150 毫秒。

**怎么处理**：导出时**不要用防抖后的值**，用实时内容重新渲染一次：
`renderMarkdown(value.value)`。这类问题的根源是“同一份数据有两个更新时机”，
凡是需要“当前完整值”的地方，都不该读防抖后的副本。
:::

## 扩展练习

::: details 练习 1：预览区跟随滚动
编辑区滚动到某一行，预览区自动滚到对应位置。

**思路**：右侧的渲染结果没有“行号”信息，所以最实用的近似做法是**按比例映射**：
用 `编辑区 scrollTop / (scrollHeight - clientHeight)` 得到滚动百分比，
乘到预览区的可滚动高度上。难点在于两侧内容高度比例不是线性的，
所以要用 `requestAnimationFrame` 节流，并且要加一个“用户正在手动滚动预览区时暂停同步”的开关，
否则两边会互相抢滚动位置。
:::

::: details 练习 2：加字数统计与预计阅读时间
底部显示“共 328 字，预计阅读 2 分钟”。

**思路**：中文按字符数算，英文按单词数算，两者要分开统计再相加。
阅读速度可以取每分钟 300 字作为粗略估计。**注意这是派生数据，用 `computed`**，
不要用 `watch` 去同步一个 `wordCount` 的 ref。
:::

::: details 练习 3：加一个“编辑 / 预览 / 分栏”切换
三个按钮，分别显示只编辑、只预览、左右分栏。

**思路**：用一个 `mode` ref 存当前模式，容器上绑定对应的 class 控制网格列数。
要注意的是：**切到“只预览”时，编辑区的 DOM 被隐藏而不是被销毁**，
否则光标位置和滚动位置都会丢。用 CSS 隐藏，或者用 `v-show` 而不是 `v-if`。
:::

::: details 练习 4：给代码块加语法高亮
代码块里的 JS 要显示成带颜色的。

**思路**：在 `renderMarkdown` 输出前，对代码块内容调用 `highlight.js` 或 `prismjs` 的处理函数，
并保留语言标识（三个反引号后面的单词，比如 `js`）。两个注意点：

1. 高亮库输出的也是 HTML，要和当前“先转义”的策略配合好 —— 通常做法是让高亮库处理
   未转义的原文，再把它生成的标签当成可信内容拼进去。
2. 高亮会显著增加渲染耗时，**必须放在防抖之后**，不要放进输入事件里。

:::

---

上一页：[案例 04 · 从接口获取数据](/cases/04-fetch) · 下一页：[案例 06 · 模态框与全局通知](/cases/06-modal)
