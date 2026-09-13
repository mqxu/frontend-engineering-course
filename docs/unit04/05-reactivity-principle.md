# 4.5 响应式原理初探

## 一个具体的场景

上一节留下的三个问题，其实都能从原理上回答：

- 为什么 `ref` 一定要写 `.value`？
- 为什么 `reactive` 解构之后就“哑”了？
- 为什么 Vue 3 之后，给对象新增属性、改数组下标都能触发更新，而 Vue 2 不行？

这一节的目的是**把机制的轮廓画出来**。不需要你手写一个响应式系统，
但看完之后，遇到奇怪的现象能从原理上推断原因，而不是靠试。

::: tip 先明确这一节的边界
这一节**不要求掌握任何实现代码**。文中出现的伪代码和内部 API
都是为了说明流程，业务代码里不要这么写。

读完只要能做到一件事就够：**给别人讲清楚“数据变了，界面为什么会跟着变”**。
:::

## 原理与写法

### Vue 2 的做法与它的局限

Vue 2 用 `Object.defineProperty` 把对象的每个属性改造成“访问器属性”：

```js
// 简化示意：Vue 2 初始化时对每个属性做的事
function defineReactive(obj, key, value) {
  Object.defineProperty(obj, key, {
    get() {
      dep.depend()        // 有人读这个属性：把它记下来
      return value
    },
    set(newValue) {
      value = newValue
      dep.notify()        // 这个属性变了：通知记下来的人
    }
  })
}
```

思路是对的，但 `Object.defineProperty` 有一个根本性质：**它只能改造“已经存在的属性”。**
由此带来三类问题。

**问题一：新增属性监听不到。**

```js
// Vue 2 里，这样写界面不会更新
this.activity.newField = 'x'
```

因为 `newField` 在初始化时不存在，没有经过 `defineReactive`，
自然没有 `get` / `set` 可以拦截。当时的写法是用 `this.$set`：

```js
// Vue 2 的补救写法
this.$set(this.activity, 'newField', 'x')
this.$delete(this.activity, 'oldField')
```

**问题二：数组的下标和长度监听不到。**

```js
// Vue 2 里，这两种写法都不触发更新
this.list[0] = newItem
this.list.length = 0
```

因为数组的元素不是用 `defineProperty` 一个个改造的（那样下标越多越慢），
所以改下标拦截不到。Vue 2 的办法是**重写数组的七个方法**：

```js
// Vue 2 内部：把 push / pop / shift / unshift / splice / sort / reverse 换成增强版
const methods = ['push', 'pop', 'shift', 'unshift', 'splice', 'sort', 'reverse']
methods.forEach((method) => {
  const original = Array.prototype[method]
  arrayProto[method] = function (...args) {
    const result = original.apply(this, args)
    dep.notify()        // 手动通知一次
    return result
  }
})
```

所以 Vue 2 里 `list.push(x)` 能更新，`list[0] = x` 不能。
**这个不一致对学生来说很难记** —— 同样是“改数组”，一个行一个不行。

**问题三：初始化成本高。**

为了让每个属性都能被拦截，Vue 2 必须在初始化时**递归遍历整个对象**，
把每一层、每一个属性都 `defineProperty` 一遍。
对象大、层级深的时候，启动会明显变慢。

### Vue 3 换成 Proxy 之后

Vue 3 改用 `Proxy`。`Proxy` 是 JavaScript 的原生能力，
可以给一个对象套一层“代理”，并且**拦截对这个对象的几乎所有操作**：

```js
// 简化示意：Proxy 能拦截的操作
const proxy = new Proxy(target, {
  get(target, key) { /* 读属性 */ },
  set(target, key, value) { /* 写属性 */ },
  deleteProperty(target, key) { /* 删属性 */ },
  has(target, key) { /* in 判断 */ },
  ownKeys(target) { /* 遍历键 */ }
  // 一共十来种，这里不一一列
})
```

对比一下就知道它解决了什么：

| 操作 | Vue 2（defineProperty） | Vue 3（Proxy） |
| --- | --- | --- |
| 读、写已有属性 | 能拦截 | 能拦截 |
| **新增属性** | 拦不到，要用 `$set` | 能拦截 |
| **删除属性** | 拦不到，要用 `$delete` | 能拦截 |
| **改数组下标** | 拦不到 | 能拦截 |
| **改数组长度** | 拦不到 | 能拦截 |
| 初始化成本 | 递归遍历所有属性，一次性 | **惰性**：访问到某一层才代理那一层 |

最后一行“惰性”值得单独说。Proxy 代理的是**整个对象**，
不需要在初始化时把每个属性都改造一遍。当代码访问到 `state.activity` 时，
Vue 才去把 `activity` 这个对象也代理起来；再访问到 `activity.title`，
才继续往下。**没被访问到的深层数据，不付出任何代价。**

这也是为什么 Vue 3 可以直接写：

```js
const state = reactive({ activity: {} })

state.activity.title = '2026 校园歌手大赛'   // ✓ 新增属性，界面会更新
delete state.activity.title                  // ✓ 删除属性，界面也会更新
```

而 Vue 2 里这两行都需要特殊 API。

::: tip 一个可以直接观察到的差别
同一个对象，可以用 `Proxy` 检测到新增属性，用 `defineProperty` 检测不到：

```js
// Proxy 版本
const p = new Proxy({}, { set: () => console.log('被写入了') })
p.newKey = 1        // 打印：被写入了

// defineProperty 版本：只能针对已知的键
const o = {}
Object.defineProperty(o, 'known', { set: () => console.log('known 被写入') })
o.known = 1         // 打印：known 被写入
o.newKey = 2        // 什么都不打印
```

**根因就一句话：`defineProperty` 改造的是“属性”，`Proxy` 代理的是“对象”。**
:::

### 依赖收集与触发更新

有了拦截能力，剩下的事情分两步：**记下来**，**通知出去**。

**第一步：记下来（依赖收集）。**

界面上用到了某个数据，渲染时就要去读它。读的那一瞬间，
通过 `get` 拦截器，把“当前正在执行的那个渲染任务”记到这个数据的依赖名单里。

```js
// 简化示意
let activeEffect = null        // 当前正在执行的副作用

function track(target, key) {
  if (!activeEffect) return
  // 取出这个属性对应的依赖集合，把当前副作用加进去
  let deps = depMap.get(target)?.get(key)
  if (!deps) { /* 新建集合并存起来 */ }
  deps.add(activeEffect)
}

function trigger(target, key) {
  // 取出这个属性的所有依赖，逐个重新执行
  const deps = depMap.get(target)?.get(key)
  deps?.forEach((effect) => effect())
}
```

**第二步：通知出去（触发更新）。**

数据被写入时，`set` 拦截器被触发，找出这个数据的依赖名单，
把名单里的每个“副作用”重新执行一遍。渲染函数重跑，界面就更新了。

```
读取数据  →  get 拦截  →  track  →  把当前 effect 记进 dep
写入数据  →  set 拦截  →  trigger →  把 dep 里的 effect 全部重跑
```

**谁在读？谁被通知？** 关键概念是**副作用（effect）**。

### effect 与副作用

“副作用”这个词来自函数式编程，指的是“除了返回值之外，还对外部产生了影响”。
一个普通的加法函数没有副作用：

```js
function add(a, b) {
  return a + b        // 只返回值，不改外部任何东西
}
```

而下面这个函数有副作用，因为它改了外部的东西：

```js
function render() {
  document.querySelector('#app').innerHTML = count.value    // 修改了 DOM
}
```

**在 Vue 里，组件的渲染函数就是一个副作用函数。** 它读取数据、
生成界面，它的执行会对外部（页面）产生影响。

你可以用 `@vue/reactivity` 提供的 `effect` 亲眼看一下这个过程：

```js [理解原理用的实验代码，业务里不要这样写]
import { ref, effect } from '@vue/reactivity'

const count = ref(0)

// effect 会立即执行一次，并把执行过程中读到的响应式数据记为自己的依赖
effect(() => {
  console.log('count 的值是：', count.value)
})
// 打印：count 的值是： 0

count.value = 1
// 打印：count 的值是： 1

count.value = 2
// 打印：count 的值是： 2
```

这里没有任何 DOM，也没有任何模板。`effect` 只做了一件事：
**执行函数，把函数里读到的 `count` 记下来；之后 `count` 一变，就重新执行这个函数。**

Vue 的组件渲染，做的就是同一件事，只是“重新执行”的内容变成了重新生成界面。
把这个实验跑一遍，响应式就从一个抽象概念变成了一个能看见的行为。

::: warning 这只是理解工具
`effect` 属于 `@vue/reactivity` 的内部 API，官方文档不建议在业务代码里直接使用。
写业务时请用 `watch` / `watchEffect`（[单元 5](/unit05/02-watch)），
它们是对 `effect` 的封装，考虑到了清理、停止等实际情况。
:::

### 为什么解构会失去响应性

现在回到上一节的那个坑，用刚讲的机制解释一遍。

```js
const state = reactive({ count: 0 })
const { count } = state
```

`const { count } = state` 做的动作是：**读一次 `state.count`，把读到的值赋给新变量 `count`。**

读的时候确实走了 `get` 拦截器，也做了依赖收集 —— 但收集的是
“**正在执行的那个 effect** 依赖 `state.count`”。解构这个动作本身，
通常发生在 `setup` 里，它不是一个渲染副作用。

真正的问题在后面：`count` 这个变量是一个**普通数字 0**。
之后你写 `count++`，改的是那个局部变量，**根本没有碰到 `state.count`**，
也就没有 `set` 拦截，自然没有 `trigger`。依赖名单上那个渲染任务永远等不到通知。

反过来看 `toRefs` 为什么有用：

```js
const { count } = toRefs(state)
count.value++        // 等价于 state.count++
```

`toRefs` 把每个属性转换成一个 `ref`，这个 ref 的 `get` / `set` 里
做的是“去读写 `state` 上对应的那个属性”。**它没有把值拷出来，
而是保留了一条通往原属性的通路。** 所以 `count.value++` 最终
还是触发了 `state.count` 的 `set`，通知照常发出。

::: details 一句话总结这个坑
**解构取到的是“值”，`toRefs` 取到的是“通路”。**

响应性依附在数据上，不依附在变量名上。你把值拷走了，
就等于把数据从响应式系统里搬了出去。
:::

## 回到开头的那三个问题

| 问题 | 从原理上回答 |
| --- | --- |
| 为什么 `ref` 要 `.value` | `.value` 是访问器属性，`get` / `set` 是拦截点；没有它就没有依赖收集和通知 |
| 为什么解构会丢响应性 | 解构是“读值并拷贝”，拷贝出去的是普通值，改它不经过原对象的 `set` |
| 为什么 Vue 3 能监听新增属性 | `Proxy` 代理整个对象，能拦截 `set` / `deleteProperty`，不依赖“属性已存在” |

**这就是学原理的价值：以前只能靠记忆的规则，现在能推出来。**

以后再遇到“改了数据界面不动”，你不需要去背“哪些操作支持响应式”，
只要问一句：**这次修改有没有经过响应式对象的 `set` 拦截？**
没经过，就是问题所在。

## 小结

- Vue 2 用 `Object.defineProperty` 改造已有属性，拦不到新增属性、删除属性、
  数组下标和长度；补救手段是 `$set` / `$delete` 和重写数组方法。
- Vue 3 用 `Proxy` 代理整个对象，上述操作全都能拦截，而且是惰性代理，
  初始化成本更低。
- 响应式分两步：**读取时收集依赖**（`track`），**写入时触发更新**（`trigger`）。
- 组件的渲染函数就是一个副作用（effect），数据变了它就重跑。
- 解构丢掉响应性，是因为它拷贝了值、切断了通往原属性的通路；
  `toRefs` 保留通路，所以保持响应性。
- 原理不需要背实现，它的用途是**在遇到怪问题时能推断原因**。

## 常见坑

::: details 坑 1：把“响应式”理解成“自动监听所有变化”
响应式监听的是**经过 Vue 代理的那一层**。以下几种情况仍然不会被监听：

```js
const state = reactive({ count: 0 })

// ✗ 通过非响应式引用改原对象
const raw = toRaw(state)      // 拿到原始对象
raw.count = 1                 // 绕过代理，界面不动

// ✗ 换了一个普通对象的引用
let o = { count: 0 }
const s = reactive(o)
o.count = 1                   // 改的是原始对象 o，s 不会更新
```

**怎么处理**：始终通过响应式对象本身去读写，不要留着原始引用去改。
:::

::: details 坑 2：以为 `shallowRef` 和 `ref` 一样
`ref` 是深层响应式：`ref({ a: { b: 1 } })` 里 `b` 变了也会触发更新。
`shallowRef` 是浅层的：**只有 `.value` 被整体替换时才触发**。

```js
import { shallowRef } from 'vue'
const s = shallowRef({ a: 1 })

s.value.a = 2              // ✗ 不触发更新
s.value = { a: 2 }         // ✓ 触发更新
```

**什么时候用**：存第三方库的大对象（比如地图实例、图表实例）时，
用 `shallowRef` 避免 Vue 去遍历代理那堆内部结构。
**日常业务用不到，知道有这回事即可。**
:::

::: details 坑 3：以为 `computed` 也是每次重新算
`computed` 会**缓存**结果，只有依赖变了才重算。这一点和 `effect`
每次都重跑不一样，属于“带缓存的副作用”。

**这正是下一节要讲的内容** —— [5.1 计算属性与缓存](/unit05/01-computed)
里会用 `console.log` 实测给你看。
:::

## 课后练习

::: details 练习 1：跑一遍 effect 实验
在本地新建一个文件，用 `@vue/reactivity` 跑一遍上一节的 `effect` 例子。

1. 观察 `count.value = 1` 之后控制台的输出；
2. 连续两次把 `count.value` 赋成同一个值，看看打印几次；
3. 回答：如果新值和旧值相同，应不应该重新执行 effect？

**参考思路**：第 2 问的答案是“不一定重跑”—— Vue 在 `set` 里会先比较新旧值，
相同就不触发。这个优化叫“值相同不触发”，也是为什么 `watch` 里
新旧值相同时回调不会执行。

**第 3 问没有标准答案**：值没变却重跑，浪费性能；但如果依赖的是对象内部属性，
只比较引用是不够的，这就是 `deep` 选项存在的理由。
:::

::: details 练习 2：用 Vue 2 和 Vue 3 的方式各写一遍
假设有一个活动对象，需要：新增一个 `remark` 属性、删掉旧的 `temp` 属性、
把 `list` 数组的第 0 项换掉。

1. 用 Vue 2 的写法写一遍（提示：`$set`、`$delete`，数组用 `splice`）；
2. 用 Vue 3 的写法写一遍；
3. 对比两者，说明 Vue 3 省掉了什么。

**参考思路**：Vue 2 版本要 `this.$set(obj, 'remark', '')`、
`this.$delete(obj, 'temp')`、`this.list.splice(0, 1, newItem)`。
Vue 3 版本就是三行普通赋值。

**要说明的“省掉了什么”**：省掉了“记住哪些操作需要特殊 API”这个负担。
这正是从 `defineProperty` 换到 `Proxy` 带来的直接好处。
:::

::: details 练习 3：解释现象
有同学写了一段代码，界面不更新。请用“读取 / 写入 / 拦截”这三个词解释原因。

```js
const user = reactive({ profile: { name: '林一鸣' } })
let profile = user.profile
profile.name = '张三'
```

**参考思路**：`let profile = user.profile` 读取了 `user.profile`，
拿到的是**已经被代理过的对象**（注意：这里和数值解构不同，
对象属性拿到的是代理，所以 `profile.name = '张三'` 其实**能**触发更新）。

**这道题的正确结论是：会更新。** 但如果改成
`let name = user.profile.name; name = '张三'`，就不会更新 ——
因为拿到的是字符串，改的是局部变量。

**区别在哪**：对象属性取出的是**引用（代理）**，原始值取出的是**拷贝**。
:::

---

上一节：[4.4 ref 与 reactive](/unit04/04-reactivity) ·
下一节：[单元 4 课后练习](/unit04/practice)
