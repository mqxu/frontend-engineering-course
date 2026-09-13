# 4.1 声明式渲染：从操作 DOM 到描述状态

## 一个具体的场景

需求是这样的：**渲染一个待办列表，每一项有一个复选框，点一下切换“完成 / 未完成”，同时该项的文字加删除线。**

需求很普通，但它是前端最典型的一类交互。“切换状态”这四个字里，
藏着一个问题：状态改了之后，界面怎么跟着改？

先看用原生 JavaScript 怎么写。

```html [todo.html]
<!DOCTYPE html>
<html lang="zh-CN">
  <body>
    <ul id="list"></ul>
    <p id="summary"></p>

    <script>
      // 数据：一条待办有 id、文字、是否完成
      let todos = [
        { id: 1, text: '整理活动报名名单', done: false },
        { id: 2, text: '联系场地负责人', done: true },
        { id: 3, text: '准备审核说明材料', done: false }
      ]

      const listEl = document.querySelector('#list')
      const summaryEl = document.querySelector('#summary')

      // 渲染：把数据变成 DOM
      function render() {
        listEl.innerHTML = ''
        todos.forEach((todo) => {
          const li = document.createElement('li')

          const checkbox = document.createElement('input')
          checkbox.type = 'checkbox'
          checkbox.checked = todo.done
          // 关键：点击时要先找到这条数据，再改它，再重新渲染
          checkbox.addEventListener('change', () => toggle(todo.id))

          const span = document.createElement('span')
          span.textContent = todo.text
          // 关键：样式也得手动改
          if (todo.done) span.style.textDecoration = 'line-through'

          li.appendChild(checkbox)
          li.appendChild(span)
          listEl.appendChild(li)
        })

        const doneCount = todos.filter((t) => t.done).length
        summaryEl.textContent = '已完成 ' + doneCount + ' / ' + todos.length
      }

      // 改数据：要自己找到那一条
      function toggle(id) {
        const index = todos.findIndex((t) => t.id === id)
        if (index === -1) return
        todos[index].done = !todos[index].done
        render() // 改完必须手动重新渲染
      }

      render()
    </script>
  </body>
</html>
```

数一下：**五十多行**。而且这里面有几个地方是“不得不写”的。

现在看 Vue 的版本。

```vue [src/components/TodoList.vue]
<script setup>
import { ref } from 'vue'

const todos = ref([
  { id: 1, text: '整理活动报名名单', done: false },
  { id: 2, text: '联系场地负责人', done: true },
  { id: 3, text: '准备审核说明材料', done: false }
])

const doneCount = () => todos.value.filter((t) => t.done).length
</script>

<template>
  <ul>
    <li v-for="todo in todos" :key="todo.id">
      <input type="checkbox" v-model="todo.done" />
      <span :style="{ textDecoration: todo.done ? 'line-through' : 'none' }">
        {{ todo.text }}
      </span>
    </li>
  </ul>
  <p>已完成 {{ doneCount() }} / {{ todos.length }}</p>
</template>
```

**十四行**，而且真正描述“界面长什么样”的只有 `<template>` 里那几行。

省掉的到底是什么？不是“循环”那点代码，而是下面这些活：

- 不用 `document.createElement`、`appendChild` 去拼 DOM；
- 不用在点击时 `findIndex` 找那条数据；
- 不用在改完数据后手动调 `render()`；
- 不用手动判断要不要加删除线。

这四件事有一个共同点：**它们都在回答“怎么把数据的变化搬到界面上”。
Vue 把这部分接管了。**

## 原理与写法

### 命令式：一步一步告诉程序怎么做

上面那份原生写法，叫**命令式（imperative）**。命令式的特点是：
**你既要描述结果，也要描述到达结果的每一步。**

“把第二条设为完成”这件事，在命令式里要拆成：

1. 找到 `todos` 里 `id` 等于 2 的那一项（`findIndex`）；
2. 把它的 `done` 取反；
3. 清空列表容器（`innerHTML = ''`）；
4. 按新数据重新生成所有 `<li>`；
5. 对每一项判断 `done`，决定要不要加删除线；
6. 更新底部统计文字。

第 3 到第 6 步，全部和“切一条待办”这个业务毫无关系，
它们只是在“把数据搬运到界面”。搬运本身没有业务价值，但不做界面就不对。

### 声明式：只描述结果

Vue 的写法叫**声明式（declarative）**。声明式的特点是：
**你只描述“数据是什么”和“界面应该长什么样”，中间过程交给框架。**

看 Vue 版本里的关键三句：

| 写法 | 你描述的东西 |
| --- | --- |
| `v-for="todo in todos"` | 列表有几项，取决于 `todos` 数组有几项 |
| `:style="{ textDecoration: todo.done ? ... }"` | 这一项的样式，取决于 `todo.done` |
| `{{ doneCount() }}` | 这里的数字，取决于 `todos` 里已完成的数量 |

你没有写“怎么改”，只写了“是什么样”。**当依赖的数据变了，
框架知道要重新生成对应的界面片段。**

### 逐条对比

把两种写法放到同一张表里，差别就清楚了：

| 对比项 | 命令式（原生 DOM） | 声明式（Vue） |
| --- | --- | --- |
| 谁负责找元素 | 你，用 `querySelector` / `createElement` | 框架，你不用找 |
| 谁负责改界面 | 你，改完数据后手动 `render()` | 框架，数据一变就自己更新 |
| 数据存在几份 | 两份：JS 里的 `todos`、DOM 里的文字与勾选态 | 一份：只有 `todos`，DOM 是它的投影 |
| 加一个“显示优先级”需求 | 在 `render()` 里加一个元素，改样式的地方也要加 | 在模板里加一句 `{{ todo.priority }}` |
| 加一个筛选器 | 改 `render()`，还要改 `toggle` 里的查找逻辑 | 加一个筛选后的数组，模板里换成它 |

最后两行最值得琢磨。

**“数据有几份”这件事，是这两种写法的分水岭。** 命令式里，
“第二条已完成”这个事实，同时存在于两个地方：JS 数组里、DOM 上那个勾选框里。
它们可能对不上 —— 比如某次改数据时忘了调 `render()`，或者 `render()` 漏了某个分支。
一旦对不上，你就得去排查“到底是数据错了还是界面错了”。

声明式里只有一份数据。DOM 是数据算出来的结果，
**不存在“数据和界面对不上”这种状态** —— 因为它俩没有分别维护，
界面永远是数据当下的样子。

### 再加一个需求，看看各自要动哪里

对比表里的最后两行值得亲手验证一遍。给待办列表加第三个需求：
**只显示未完成的待办，并且底部统计只算显示出来的。**

先看命令式版本要改的地方：

```js
// 1. 新增一个状态
let onlyUndone = false

// 2. 改渲染逻辑：循环里先判断要不要跳过这一条
function render() {
  listEl.innerHTML = ''
  const visible = onlyUndone ? todos.filter((t) => !t.done) : todos
  visible.forEach((todo) => {
    // ... 原来的生成逻辑不变
  })

  // 3. 统计也要跟着改成“只算可见的”
  const doneCount = visible.filter((t) => t.done).length
  summaryEl.textContent = '已完成 ' + doneCount + ' / ' + visible.length
}

// 4. 还得加一个切换开关的按钮和它的监听
document.querySelector('#toggle-filter').addEventListener('click', () => {
  onlyUndone = !onlyUndone
  render()          // 改完别忘了重新渲染
  updateFilterButton()   // 按钮的高亮也要手动同步
})
```

**四处改动，而且第 4 处的“按钮高亮”是最容易漏的** —— 数据筛了、
列表对了、统计对了，但按钮看起来还是“未开启”的样子。
这类“状态和界面不同步”的问题，是命令式写法里的常客。

再看 Vue 版本：

```vue
<script setup>
import { ref, computed } from 'vue'

const onlyUndone = ref(false)

const visibleTodos = computed(() =>
  onlyUndone.value ? todos.value.filter((t) => !t.done) : todos.value
)

const doneCount = computed(() => visibleTodos.value.filter((t) => t.done).length)
</script>

<template>
  <button :class="{ 'is-active': onlyUndone }" @click="onlyUndone = !onlyUndone">
    {{ onlyUndone ? '显示全部' : '只看未完成' }}
  </button>

  <li v-for="todo in visibleTodos" :key="todo.id">
    <!-- ... -->
  </li>
  <p>已完成 {{ doneCount }} / {{ visibleTodos.length }}</p>
</template>
```

**改动集中在两处**：加一个状态 `onlyUndone`，加一个计算属性 `visibleTodos`。
模板里替换一下数据源，按钮和统计都从 `visibleTodos` 派生。

**按钮的高亮状态不需要单独处理** —— `:class="{ 'is-active': onlyUndone }"`
就是它的定义。这就是“只有一份数据”的实际好处：
**新加的需求只要接进这条派生链，所有依赖它的地方自动跟上。**


::: tip 一个可以随身带的判断句
写 Vue 的时候，心里要默念这句话：

**我不是在“操作界面”，我是在“描述界面应该是什么样”。**

一旦你开始想 `querySelector`、想 `innerHTML`，就说明思路跑偏了。
:::

### 那 ref 是什么

上面 Vue 版本里出现了 `ref`，它是 Vue 用来声明**响应式状态**的。

```js
const todos = ref([ /* ... */ ])
```

你可以先把 `ref` 理解成一个“盒子”：真正的数据放在盒子的 `.value` 里。

```js
console.log(todos.value)        // 取出数组
todos.value = [ /* 新数组 */ ]   // 换掉整个数组
```

为什么非得套一层盒子？因为**普通变量变了，Vue 是不知道的**。
只有经过 `ref` 包装的数据，Vue 才能在它变化时收到通知，
然后去更新用到它的界面。

这也是为什么模板里可以直接写 `todos`、不用写 `todos.value`：
模板对这个“盒子”做了**自动解包**。这部分规则会在
[4.4 ref 与 reactive](/unit04/04-reactivity) 里详细讲，现在先记住用法。

::: warning 这里正是新手最容易出错的地方
在 `<script setup>` 里操作 `ref` 数据，一定要写 `.value`；
在 `<template>` 里用，不写 `.value`。

```js
// ✗ 错：这是把数组换成了一个普通数组变量，Vue 收不到通知
todos = newTodos

// ✓ 对：改的是盒子里的内容
todos.value = newTodos
```

“改了数据界面不动”的第一大原因，就是这里漏了 `.value`。
:::

## 那还需要命令式吗

需要。**声明式不是“永远不碰 DOM”，而是“只在必须碰的时候，从一个明确的出口碰”。**

有四类场景，你确实必须直接操作 DOM：

| 场景 | 为什么必须碰 DOM | 做法 |
| --- | --- | --- |
| 集成第三方库（图表、地图、富文本编辑器） | 这些库要你给它一个容器元素，它自己管理容器内部 | 用模板引用拿到元素，交给库 |
| 测量元素尺寸（`offsetWidth`、`scrollHeight`） | 尺寸只有浏览器排版完才知道，不在数据里 | 用模板引用读，放到生命周期钩子里 |
| 控制焦点、选区、滚动位置 | 这些属于浏览器的运行时状态，不是数据 | 用模板引用调 `focus()`、`scrollIntoView()` |
| Canvas / WebGL 绘制 | 画面靠绘图指令逐帧画出来 | 用模板引用拿 canvas，自己写绘制逻辑 |

**注意这四类的共同点：它们操作的是“浏览器 API 的运行时状态”，
不是“页面上显示的内容”。** 显示什么、显示几条、什么颜色，仍然由数据决定；
`focus()`、`scrollTop`、图表实例这些东西，数据描述不了。

Vue 为这四类场景留了一个受控的出口：**模板引用**。用法是先声明一个 ref，
再把它绑到元素的 `ref` 属性上，元素挂载后就能通过 `.value` 拿到真实元素。

```vue
<script setup>
import { ref, onMounted } from 'vue'

const inputEl = ref(null)      // 注意：这个 ref 用来存元素，不是存数据

onMounted(() => {
  // 元素已经渲染完成，可以安全操作
  inputEl.value?.focus()
})
</script>

<template>
  <input ref="inputEl" placeholder="搜索活动" />
</template>
```

**这个出口和 `document.querySelector` 的关键区别是“作用范围可控”** ——
它只指向当前组件模板里的那个元素，不会误抓到别的页面上的同名元素，
也不会因为列表里多了一项而抓错。

::: tip 一条实用的判断标准
想操作 DOM 之前，先问一句：**我想改的这件事，用数据能不能描述？**

- “这个按钮要变成禁用” → 能描述 → 用状态 + `:disabled`
- “列表要筛掉已完成” → 能描述 → 用数据源
- “输入框要获得焦点” → 描述不了 → 用模板引用
- “这个 div 现在有多高” → 描述不了 → 用模板引用

**能描述就不要碰 DOM。** 这四类之外的场景，几乎都能用状态解决。
:::

## 小结

- 命令式要写“到达结果的每一步”，声明式只写“结果是什么”。
- Vue 里你描述两件事：**数据是什么**、**界面应该长什么样**；中间的更新过程由框架负责。
- 命令式里数据存在两份（JS 与 DOM），容易对不上；声明式里只有一份，DOM 是数据的投射。
- 加需求时，命令式要改多处（渲染、查找、样式），声明式通常只改模板里的一两处。
- `ref` 是声明响应式状态的方式，脚本里读写要 `.value`，模板里不用。
- 判断自己有没有写出“Vue 味”的标准：**有没有手动去拿 DOM 元素。**

## 常见坑

::: details 坑 1：在 Vue 里继续用 querySelector
```js
// ✗ 不要这样写
import { ref, onMounted } from 'vue'
const listEl = ref(null)
onMounted(() => {
  document.querySelector('#list').innerHTML = '...'
})
```

**现象**：代码能跑，但数据一变界面不更新，或者更新之后又被覆盖回去。

**原因**：你绕过了 Vue 的渲染过程，直接改了 DOM。Vue 下次更新时
会按自己的数据重新渲染，把你手动改的内容冲掉。

**怎么处理**：改成用模板描述。确实需要拿元素引用时（比如聚焦输入框），
用[模板引用](/unit08/03-builtin)，不要用 `querySelector`。
:::

::: details 坑 2：以为“少写代码”是目的
有人看到十四行和五十行的对比，得出“Vue 就是省代码”的结论。
省代码只是结果，不是目的。

真正的目的是**消除“数据和界面不一致”的可能**。命令式写法里，
只要有一处忘了同步，界面就会和数据对不上；声明式写法里这种错误根本写不出来。

**判断一份代码好不好，看的不是行数，是有没有两套状态在各自维护。**
:::

::: details 坑 3：把 `ref` 当成普通变量重新赋值
```js
const count = ref(0)

// ✗ 错：丢掉了 ref 盒子，count 变成了普通数字
count = 1

// ✓ 对
count.value = 1
```

**现象**：`count = 1` 这行甚至会直接报错（`Assignment to constant variable`），
因为 `const` 声明的变量不能重新赋值。

**原因**：`count` 始终是那个盒子，你不能换掉盒子，只能换盒子里的东西。

**怎么处理**：一律用 `.value`。命名上也可以提醒自己 ——
把变量名想成“盒子”，`.value` 才是“里面的值”。
:::

::: details 坑 4：在模板里写复杂逻辑
```vue
<!-- ✗ 模板里塞了太多运算 -->
<span>{{ todos.filter(t => t.done).length }} / {{ todos.length }}</span>
```

能跑，但两个问题：一是模板变难读，二是这种运算在每次重渲染时都会重跑一遍。

**怎么处理**：抽成[计算属性](/unit05/01-computed)，模板里只留一个名字。
上面 Vue 版本里的 `doneCount` 就是过渡写法，单元 5 会把它改成计算属性。
:::

::: details 坑 5：把“不需要操作 DOM”理解成“不能操作 DOM”
有同学听完这一节，遇到“输入框自动聚焦”这种需求也硬要用数据表达，
于是写出这样的代码：

```vue
<!-- ✗ 数据描述不了“焦点”，这条路走不通 -->
<input :autofocus="shouldFocus" />
```

`:autofocus` 是浏览器的**初始**属性，只在元素第一次插入页面时生效。
之后把 `shouldFocus` 改成 `false` 再改成 `true`，输入框不会再次获得焦点。

**现象**：首次能用，之后再触发就没反应。

**原因**：焦点是浏览器的运行时状态，不是元素属性，数据描述不了它。

**怎么处理**：用模板引用 + `onMounted`（或 `nextTick`）调用 `focus()`。

```vue
<script setup>
import { ref, nextTick } from 'vue'

const inputEl = ref(null)
const isEditing = ref(false)

async function startEdit() {
  isEditing.value = true
  await nextTick()          // 等 DOM 渲染出来
  inputEl.value?.focus()    // 再操作
}
</script>

<template>
  <input v-if="isEditing" ref="inputEl" />
</template>
```

**记住结论：显示什么用数据，浏览器状态用模板引用。不要试图用数据去控制焦点、
滚动位置、元素尺寸这类东西。**
:::

## 课后练习

::: details 练习 1：写两个版本，量一量差距
需求：渲染一个活动报名列表，每一项显示“学生姓名 + 学号 + 审核状态”，
点一下在“待审核 / 已通过”之间切换。

1. 先用原生 JavaScript 写一版，统计行数。
2. 再用 Vue 写一版，统计行数。
3. 回答：如果你现在要加一个“只显示待审核”的开关，两个版本各自要改哪些地方？

**参考思路**：第 3 问是重点。原生版本要改 `render()` 的渲染逻辑、
还要处理切换后该项是否该从列表里消失；Vue 版本通常只是换一个数据源。
把两边的改动点都写出来，你会对“加需求的成本”有具体的感受。
:::

::: details 练习 2：找出“第二份状态”
下面这段原生代码里，同一个事实被存了几份？

```js
let activeFilter = 'all'
const listEl = document.querySelector('#list')
document.querySelector('#filter-btn').addEventListener('click', () => {
  activeFilter = 'pending'
  listEl.classList.add('is-filtered')
  listEl.dataset.filter = 'pending'
})
```

**参考思路**：“当前筛选是待审核”这个事实，同时存在三个地方：
变量 `activeFilter`、`listEl` 的类名、`listEl` 的 `data-filter`。
任何一处忘了同步，就会出现“看着是筛选了、数据却没筛”的问题。

**结论**：凡是能被其他状态算出来的东西，就不要单独存一份。
:::

::: details 练习 3：把命令式翻译成声明式
下面这段代码用原生 DOM 做了一件事，请用 Vue 的写法重写，
要求不再出现任何 `querySelector` 和 `classList`。

```js
function updateBadge(count) {
  const badge = document.querySelector('.badge')
  if (count > 0) {
    badge.textContent = count
    badge.classList.remove('hidden')
  } else {
    badge.classList.add('hidden')
  }
}
```

**参考思路**：先想清楚“有几份数据”。这里只有一份：`count`。
“要不要显示”“显示什么文字”都是它算出来的。
Vue 版本大概是：`<span v-if="count > 0" class="badge">{{ count }}</span>`。
注意 `v-if` 要到[单元 5](/unit05/03-conditional) 才正式讲，这里可以先照抄感受一下。
:::

---

上一节：[单元导学](/unit04/) ·
下一节：[4.2 模板语法与数据绑定](/unit04/02-template-syntax)
