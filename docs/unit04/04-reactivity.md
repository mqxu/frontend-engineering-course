# 4.4 ref 与 reactive

## 一个具体的场景

上一节的名片页里，有同学这样写：

```vue
<script setup>
let isOnDuty = true

function toggleDuty() {
  isOnDuty = !isOnDuty
  console.log('现在是：', isOnDuty)   // 控制台确实变了
}
</script>

<template>
  <button @click="toggleDuty">{{ isOnDuty ? '在岗' : '请假' }}</button>
</template>
```

点击按钮，控制台打印的值每次都正确切换，**但按钮上的文字一动不动。**

这个现象非常典型，也非常容易误判成“Vue 有 bug”。原因其实很简单：
`isOnDuty` 是一个普通的 `let` 变量。**它变了，但 Vue 根本不知道它变了。**

要让 Vue 知道，得用响应式的方式声明它：

```vue
<script setup>
import { ref } from 'vue'

const isOnDuty = ref(true)

function toggleDuty() {
  isOnDuty.value = !isOnDuty.value
}
</script>

<template>
  <button @click="toggleDuty">{{ isOnDuty ? '在岗' : '请假' }}</button>
</template>
```

区别只有三点：`import { ref }`、`ref(true)`、读写加 `.value`。
这一节把这两个 API（`ref` 和 `reactive`）讲透。

## 原理与写法

### 响应式要解决的问题：数据变了，界面怎么知道

回忆 [4.1](/unit04/01-declarative) 的结论：声明式里只有一份数据，界面是数据的投射。
那就有个必须回答的问题：**数据变的那一刻，怎么触发界面更新？**

最笨的办法是“一直重渲染”：每隔一小段时间检查一遍所有数据有没有变。
这显然不行，代价太大。

Vue 的做法是**在读取时记录、在写入时通知**：

1. 渲染界面的时候，模板会去读数据（读 `isOnDuty.value`）；
2. 读的那一刻，Vue 记下“这个界面片段依赖这个数据”；
3. 之后数据被写（`isOnDuty.value = false`），Vue 收到通知，就去更新第 2 步记下的那些界面片段。

这个机制要能成立，**前提是 Vue 能“看住”数据** —— 知道它什么时候被读、什么时候被写。
普通的 `let` 变量做不到：读写就是直接读内存，没有任何拦截的机会。

所以需要一层包装。`ref` 和 `reactive` 就是两种包装方式。

### ref：把值装进一个盒子

```js
import { ref } from 'vue'

const count = ref(0)              // 数字
const title = ref('校园歌手大赛')   // 字符串
const list = ref([1, 2, 3])       // 数组
const user = ref({ name: '林一鸣' }) // 对象
```

`ref` 几乎能装任何类型。它返回的不是原始值，而是一个对象，通常叫它“ref 对象”。
真正的值放在 `.value` 上：

```js
console.log(count)         // RefImpl { value: 0 }
console.log(count.value)   // 0

count.value = 1            // 改值：界面会更新
count = 5                  // ✗ 报错：不能换掉盒子本身
```

**为什么非得有 `.value`？** 因为 Vue 拦截的是“对 `.value` 的读写”。
`.value` 是一个访问器属性，读它的时候 Vue 能记下依赖，写它的时候 Vue 能收到通知。
如果不经过 `.value`，就没有拦截点。

```js
// 伪代码：ref 内部大概是这样
class Ref {
  get value() {
    track(this)        // 记录：有东西在读我
    return this._raw
  }
  set value(newVal) {
    this._raw = newVal
    trigger(this)      // 通知：我变了，用我的东西都去更新
  }
}
```

具体原理在 [4.5](/unit04/05-reactivity-principle) 展开，这里先建立印象：
**`.value` 是拦截点，不是累赘。**

**模板里为什么可以不写 `.value`？** 因为 Vue 在编译模板时，发现你引用的是顶层
的 ref，会自动帮你补上 `.value`。这叫**自动解包**。

```vue
<script setup>
import { ref } from 'vue'
const count = ref(0)
</script>

<template>
  <!-- 这里写 count，等价于 count.value -->
  <p>{{ count }}</p>
  <button @click="count++">加一</button>
</template>
```

注意 `@click="count++"` 也能跑 —— 编译后它等价于 `count.value++`。

::: tip 口诀
**脚本里要 `.value`，模板里不要 `.value`。**

这条规则有一个前提：**那个 ref 在模板里是“顶层”的**。什么算顶层，
后面“自动解包的边界”会讲清楚。绝大多数情况下，你在 `<script setup>` 里
用 `const` 声明的 ref，在模板里都是顶层。
:::

### reactive：一个被代理的对象

```js
import { reactive } from 'vue'

const activityForm = reactive({
  title: '',
  type: 'lecture',
  capacity: 100,
  deadline: ''
})

activityForm.title = '2026 校园歌手大赛'   // 直接改属性，界面会更新
activityForm.capacity = 200                // 数组、对象里的东西同理
```

`reactive` 只能接收**对象类型**（对象、数组、`Map`、`Set`），返回一个被代理的对象。
读写它的属性时，Vue 能拦截到，所以**不用写 `.value`**，直接改属性就行。

它适合什么场景？**一组相关联、要一起用的数据。** 比如一个表单的所有字段、
一个列表页的查询条件。用 `reactive` 之后，模板里写 `form.title`、
`form.capacity`，不用到处 `.value`，读起来干净一些。

但它有**三个必须知道的坑**。

**坑一：不能整体替换。** `reactive` 返回的是一个代理对象，
如果你用一个新对象把它整个替换掉，就丢掉了代理：

```js
let state = reactive({ count: 0 })

// ✗ 错：state 变成普通对象，响应式没了
state = reactive({ count: 1 })   // 这行其实能跑，但后面引用它的人拿到的是新对象

// ✗ 更常见的一种错
state = { count: 1 }             // 直接把代理换成了普通对象
```

正确做法是**改属性，不换对象**：

```js
// ✓ 对
Object.assign(state, { count: 1 })
// 或者逐个改
state.count = 1
```

**坑二：解构会丢响应性。**

```js
const state = reactive({ count: 0, name: '林一鸣' })

// ✗ 错：解构出来的是普通的值，和 state 断了关系
const { count } = state
count++              // 界面不会变，state.count 也没变
console.log(state.count)  // 0
```

解构是“取出当下的值”，取出来的 `count` 是一个普通数字，
它和 `state.count` 再也没有联系。想让解构出来的东西保持响应性，要用 `toRefs`：

```js
import { toRefs } from 'vue'

const state = reactive({ count: 0, name: '林一鸣' })

// ✓ 对：toRefs 把每个属性转成 ref
const { count, name } = toRefs(state)
count.value++        // state.count 也变成 1，界面更新

// 也可以在模板里直接解构使用
```

**坑三：只对对象有效。**

```js
// ✗ 错：传原始值会报错，或返回的值不具响应性
const count = reactive(0)
const title = reactive('活动')
```

原始类型（数字、字符串、布尔值）没有属性可以拦截，`reactive` 无能为力。
这类状态必须用 `ref`。

::: warning reactive 为什么会有这三个坑
因为它的机制是“代理一个对象”。对象被换掉了、属性被拿出来了、
或者根本没有对象，代理就无从下手。

**记住一句话：`reactive` 的响应性依附在“那个对象”上，而不是依附在“变量名”上。**
:::

### ref 与 reactive 怎么选

既然 `reactive` 有这么多限制，为什么不干脆都用 `ref`？官方文档的建议就是**优先用 `ref`**。
下面这张表说明理由：

| 对比项 | `ref` | `reactive` |
| --- | --- | --- |
| 能装的类型 | 任意类型（含数字、字符串、布尔） | 只能是对象类型 |
| 整体替换 | 支持（`x.value = 新值`） | 不支持，会丢响应性 |
| 解构 | 解构后仍是 ref，响应性在 | 解构后丢响应性，需要 `toRefs` |
| 模板里是否要 `.value` | 不要（自动解包） | 不要 |
| 脚本里是否要 `.value` | 要 | 不要 |
| 传参给函数 | 传 ref 本身，响应性保留 | 传出去的是代理对象，通常也没问题 |
| 心智负担 | 一致：一个盒子 | 分散：要记住那三个坑 |

选用的经验：

- **默认用 `ref`。** 数字、字符串、布尔值只能用 `ref`；对象、数组用 `ref` 也没有问题。
- **只在两种情况考虑 `reactive`**：一是表单这类“一组属性始终一起用”的数据；
  二是在 `composables` 里封装一组状态，希望调用方写 `state.xxx` 而不是 `state.xxx.value`。
- **不要在一个组件里混着用。** 一会儿 `.value` 一会儿不写，
  最容易出现“忘了写 `.value`”的低级错误。

::: details 一个对象的属性多的时候，用 reactive 真的更好吗
看这段对比：

```js
// 方案 A：ref
const form = ref({ title: '', type: '', capacity: 100 })
form.value.title = '...'

// 方案 B：reactive
const form = reactive({ title: '', type: '', capacity: 100 })
form.title = '...'
```

方案 B 模板里写 `form.title` 更干净，脚本里也少一层 `.value`。
但代价是：**当你想重置表单时，不能用 `form = {}`**，只能
`Object.keys(form).forEach((k) => { form[k] = '' })` 或者把初始值存好再 `Object.assign`。

**结论**：属性多且有“整体重置”需求的表单，方案 A 反而更省心。
这也是官方推荐 `ref` 的原因 —— 它的一致性好，不用为个别场景记特殊规则。
:::

### 自动解包的规则与边界

模板里的自动解包**只作用于顶层的 ref**。什么叫顶层？就是模板能直接访问到的那个变量。

```vue
<script setup>
import { ref } from 'vue'

const count = ref(0)                      // 顶层 ref：解包
const user = ref({ name: '林一鸣' })       // 顶层 ref：解包
const list = ref([1, 2, 3])               // 顶层 ref：解包
const nested = { inner: ref('x') }        // 嵌套在普通对象里：不解包
const refList = ref([ref('a'), ref('b')]) // 数组里的 ref：不解包
</script>

<template>
  <p>{{ count }}</p>          <!-- ✓ 解包，显示 0 -->
  <p>{{ user.name }}</p>      <!-- ✓ 解包后取属性，显示 林一鸣 -->
  <p>{{ list[0] }}</p>        <!-- ✓ 解包后取下标，显示 1 -->

  <!-- ✗ 不解包：nested 是普通对象，inner 是 ref 对象 -->
  <p>{{ nested.inner }}</p>   <!-- 显示 RefImpl { value: 'x' } 这种东西 -->

  <!-- ✗ 不解包：数组元素是 ref，不会自动取值 -->
  <p>{{ refList[0] }}</p>
</template>
```

同样的规则也适用于“函数参数”：**ref 传进函数时不会自动解包。**

```js
const count = ref(0)

// ✗ 错：value 是 ref 对象，不是数字
function double(value) {
  return value * 2
}
console.log(double(count))   // NaN（ref 对象乘 2）

// ✓ 对：在调用处取 .value
console.log(double(count.value))

// ✓ 也可以：让函数自己处理 ref
function doubleRef(r) {
  return r.value * 2
}
```

**为什么会这样？** 自动解包是**模板编译**阶段的行为，不是运行时行为。
`<script setup>` 里的 JavaScript 代码不经过模板编译，自然没有这层处理。

::: warning 唯一容易踩的坑
```js
const list = ref([])
list.value.push(item)   // ✓ 对：先解包再 push
list.push(item)         // ✗ 错：list 是 ref 对象，没有 push 方法
```

写 `list.push` 时 JavaScript 会报 `list.push is not a function`，
这个报错本身很好懂。真正麻烦的是 `reactive` 里嵌套的数组：
`reactive` 会把嵌套对象也代理好，所以 `state.list.push(x)` 是正常的，
不需要额外处理。**别把两套规则记混了。**
:::

## 排查实例：我改了数据，界面不动

现在把最常见的三种原因列出来，遇到问题按这个顺序查。

**原因一：忘了 `.value`。**

```js
const count = ref(0)

count = 1           // ✗ 报错：Assignment to constant variable
count.value = 1     // ✓
```

前一种写法会直接报错，比较好发现。难发现的是这种：

```js
const list = ref([])
list.push({ id: 1 })   // ✗ 报错，但报的是 list.push is not a function
```

看到 `xxx is not a function`，先去想“这个 `xxx` 是不是 ref”。

**原因二：改的是副本。**

```js
const form = reactive({ title: 'A', type: 'lecture' })

// ✗ 错：解构出来的是普通值
let { title } = form
title = 'B'              // form.title 还是 'A'，界面不动

// ✓ 对：直接改属性
form.title = 'B'
```

另一种副本的形式是**传参**：

```js
// ✗ 错：函数参数是值的拷贝
function rename(title) {
  title = 'B'     // 只改了局部变量
}
rename(form.title)

// ✓ 对：把对象本身传进去
function rename(form) {
  form.title = 'B'
}
rename(form)
```

**原因三：整体替换了 `reactive` 对象。**

```js
let state = reactive({ list: [], page: 1 })

// ✗ 错：把代理对象换掉了
state = { list: [], page: 1 }

// ✓ 对：改属性
state.page = 2
state.list = newList       // 属性可以整体换，对象本身不行
```

注意最后一行：**替换属性是允许的，替换对象本身不允许。**
`state.list = newList` 会被代理拦截到，能触发更新；
`state = {...}` 则把变量指向了另一个普通对象。

::: tip 遇到“界面不动”时的三步排查
1. **这个数据是响应式的吗？** 看它是不是用 `ref` / `reactive` 声明的。
   是普通的 `let`，那就不用往下看了。
2. **改的方式对吗？** `ref` 看有没有 `.value`；`reactive` 看是不是整体替换或解构赋值了。
3. **还有别的可能吗？** 前面两条都排除了，再看是不是同一个数据被复制了一份
   （比如 `const copy = { ...form }` 之后改 `copy`）。

三步查完基本都能定位。**不要一上来就怀疑 Vue** —— 这套机制已经非常稳定，
出问题的几乎总是这三处。
:::

## 小结

- 普通变量变了，Vue 不知道；只有 `ref` / `reactive` 声明的数据才有响应性。
- `ref` 能装任意类型，真正的值在 `.value` 上；`.value` 是 Vue 的拦截点。
- 脚本里读写 `ref` 要 `.value`，模板里不用 —— 模板编译时会自动解包。
- `reactive` 只接受对象类型，直接改属性即可；但**不能整体替换、解构会丢响应性、不能用于原始值**。
- 需要解构 `reactive` 时用 `toRefs`；需要重置时用 `Object.assign`，不要重新赋值。
- 自动解包只在模板顶层和 `.value` 位置生效；嵌套在普通对象里的 ref、
  数组元素里的 ref、函数参数里的 ref 都不会解包。
- 默认优先用 `ref`，一个组件里不要混着用两种。

## 常见坑

::: details 坑 1：用 `const` 声明 reactive 后想整体重置
```js
const form = reactive({ title: '', capacity: 100 })
form = reactive({ title: '', capacity: 100 })   // ✗ 报错：常量不能重新赋值
```

**现象**：报 `Assignment to constant variable`。

**原因**：`const` 不能重新赋值，而且就算用 `let`，整体替换也会丢响应性。

**怎么处理**：把初始值提出来，用 `Object.assign` 覆盖：

```js
const initialForm = { title: '', capacity: 100 }
const form = reactive({ ...initialForm })

function resetForm() {
  Object.assign(form, initialForm)   // ✓ 保持同一个代理对象
}
```
:::

::: details 坑 2：解构 `defineProps` 之后属性不更新
```vue
<script setup>
const props = defineProps({ status: String })
const { status } = props   // ✗ 在 Vue 3.5 之前会丢响应性
</script>
```

**现象**：父组件改了 `status`，子组件里的 `status` 还是旧值。

**原因**：`props` 是一个响应式对象，直接解构出来的是当下的值。

**怎么处理**：三种都行 ——

```vue
<script setup>
const props = defineProps({ status: String })
// 方案一：不把 props 解构，用 props.status
// 方案二：用 toRefs
// 方案三：Vue 3.5 起可以直接解构（编译宏会处理）
</script>
```

**注意区分**：`defineProps` 的解构在 Vue 3.5 起是支持响应性的，
这是编译宏的特殊处理；而普通 `reactive()` 对象的解构**不支持**。
两者不要混淆。详见[单元 7 的 props](/unit07/02-props)。
:::

::: details 坑 3：ref 放进普通对象后忘了 .value
```js
const filter = {
  keyword: ref(''),
  status: ref('all')
}

// ✗ 错：filter.keyword 是 ref 对象，不是字符串
if (filter.keyword === '') { /* 永远不成立 */ }

// ✓ 对
if (filter.keyword.value === '') { }
```

**现象**：判断永远不成立，或者接口参数传成了 `[object Object]`。

**原因**：`ref` 只有放在模板顶层或直接 `.value` 才解包，
放进普通对象的属性里不会解包。

**怎么处理**：用 `reactive` 声明这组数据；如果确实要用 `ref`，
在用的时候写清 `.value`。**这类问题最隐蔽的地方在于不报错，只是逻辑不对。**
:::

::: details 坑 4：以为 `ref` 里的对象改属性不用 `.value`
```js
const user = ref({ name: '林一鸣', role: 'organizer' })

// ✗ 错
user.name = '张三'

// ✓ 对
user.value.name = '张三'
```

**现象**：不报错，但数据没变、界面不动。（在非严格模式下甚至可能静默失败。）

**原因**：`user` 是 ref 对象，它本身没有 `name` 属性 ——
你是在给 ref 对象新增了一个无意义的属性。

**怎么处理**：先 `.value` 拿到里面的对象，再改属性。
**读的时候也要 `.value`**：`user.value.name`，不是 `user.name`。
:::

## 课后练习

::: details 练习 1：找出下面代码里所有的错
```vue
<script setup>
import { reactive } from 'vue'

let form = reactive({ title: '', tags: [] })

function addTag(tag) {
  form.tags = [...form.tags, tag]
}

function reset() {
  form = reactive({ title: '', tags: [] })
}

function readTitle() {
  const { title } = form
  return title
}
</script>

<template>
  <p>{{ form.title }}</p>
  <p>{{ form.tags.length }}</p>
</template>
```

**参考思路**：`addTag` 和模板都是对的；`reset` 里整体替换了对象，
应该改成 `Object.assign(form, { title: '', tags: [] })`；
`readTitle` 里解构不会丢响应性（因为只是读取返回），但如果返回后还期望它跟着变，
就要用 `toRefs`。**重点是区分“读一下就走”和“要跟着更新”两种场景。**
:::

::: details 练习 2：给下面对话判断对错
> 同学 A：`reactive` 更方便，我以后全用它。
> 同学 B：`ref` 要写 `.value` 太麻烦，为什么不统一省掉。

1. A 的说法有什么问题？
2. B 的疑问，`.value` 为什么不能省？

**参考思路**：A 的问题是 `reactive` 不能装原始类型，而界面上大量状态是数字、
字符串、布尔值，这些只能靠 `ref`。B 的答案在“拦截点”那一节：
`.value` 是访问器属性，读写它 Vue 才能记依赖、发通知；
省掉它就没有拦截的地方，响应式无从谈起。
:::

::: details 练习 3：修一个“改了但不动”的 bug
下面这段代码点击按钮后，界面上的 `page` 不变。找出原因并改对。

```vue
<script setup>
import { reactive } from 'vue'

const query = reactive({ keyword: '', page: 1 })

function nextPage() {
  const { page } = query
  page = page + 1
}
</script>

<template>
  <p>第 {{ query.page }} 页</p>
  <button @click="nextPage">下一页</button>
</template>
```

**参考思路**：`const { page } = query` 解构出来的是普通数字，
`page = page + 1` 只改了局部变量。改成 `query.page += 1`。

**再想一步**：如果确实需要解构（比如要传给别的函数），该怎么写？
答案是 `toRefs`。
:::

---

上一节：[4.3 事件绑定与指令总览](/unit04/03-event-directive) ·
下一节：[4.5 响应式原理初探](/unit04/05-reactivity-principle)
