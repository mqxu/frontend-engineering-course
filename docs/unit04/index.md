<UnitMeta
  unit="单元 4"
  title="模板语法与响应式基础"
  module="模块二 · Vue 3 核心基础"
  hours="4 学时"
  week="第 4 周"
  :goals="[
    '能用模板语法完成数据展示与属性绑定',
    '能准确区分 v-bind 与 v-on 的用途并写出正确缩写',
    '能正确使用响应式 API 声明状态',
    '能独立排查“改了数据界面不动”这类问题'
  ]"
  :outcomes="['个人名片页（含交互）']"
/>

## 为什么从这一周开始，写代码的方式变了

前三周我们做的事情，都是“把工具装好、把规范定好、把项目跑起来”。到这一周，
终于要开始写真正的界面了。

先看一段很常见的学生代码。这是用原生 JavaScript 写的一个“切换活动报名状态”的功能：

```js [原生 DOM 写法]
const btn = document.querySelector('#toggle-btn')
const label = document.querySelector('#status-label')
let isSignedUp = false

btn.addEventListener('click', () => {
  isSignedUp = !isSignedUp
  if (isSignedUp) {
    label.textContent = '已报名'
    label.classList.remove('status--idle')
    label.classList.add('status--done')
  } else {
    label.textContent = '未报名'
    label.classList.remove('status--done')
    label.classList.add('status--idle')
  }
})
```

这段代码能跑，也没写错。但它有两个问题：

1. **状态和界面是两套东西。** `isSignedUp` 变了之后，必须记得去改 `label` 的文字和类名。
   哪天加一个“报名时间”的显示，就要在每一处 `if / else` 里都补上。
2. **你必须知道界面长什么样。** `document.querySelector` 要拿到某个具体元素，
   意味着写逻辑的时候，脑子里得同时装着 HTML 结构。

Vue 把这两件事换了位置。同一个功能，用 Vue 写：

```vue [Vue 写法]
<script setup>
import { ref } from 'vue'

const isSignedUp = ref(false)
</script>

<template>
  <button @click="isSignedUp = !isSignedUp">
    {{ isSignedUp ? '退订' : '报名' }}
  </button>
  <span :class="isSignedUp ? 'status--done' : 'status--idle'">
    {{ isSignedUp ? '已报名' : '未报名' }}
  </span>
</template>
```

差别不是“少写了几行”。差别在于：**你只描述了“数据是什么”和“界面应该长什么样”，
没有写一句“怎么把数据搬到界面上”。** 这个“搬运”的活，Vue 替你干了。

这个单元要讲清楚的，就是这套写法的规则：模板里能写什么、不能写什么，状态怎么声明，
以及最关键的 —— 为什么你改了数据，界面就会自己变。

::: tip 一句话概括这个单元的作用
**学会用“描述”代替“操作”。** 这是 Vue 与原生 DOM 最根本的分界，
也是后面所有组件、路由、状态管理的基础。
:::

## 本单元的知识地图

| 小节 | 讲什么 | 解决什么问题 |
| --- | --- | --- |
| [4.1 声明式渲染：从操作 DOM 到描述状态](/unit04/01-declarative) | 用同一个需求对比命令式与声明式两种写法 | 为什么值得换一种写法 |
| [4.2 模板语法与数据绑定](/unit04/02-template-syntax) | 插值的边界、属性绑定、类名与样式绑定 | 模板里能写什么 |
| [4.3 事件绑定与指令总览](/unit04/03-event-directive) | 事件写法、事件对象、动态参数、指令地图 | 用户操作怎么接进来 |
| [4.4 ref 与 reactive](/unit04/04-reactivity) | 两个响应式 API 的用法、取舍与自动解包规则 | 状态怎么声明才有效 |
| [4.5 响应式原理初探](/unit04/05-reactivity-principle) | Object.defineProperty 的局限、Proxy 的好处、依赖收集 | 出问题时能推断原因 |
| [AI 协作 · 别让它写 Vue 2 的写法](/unit04/ai-collaboration) | Vue 2 残留写法、解构丢响应性、`.value` 在脚本与模板的差别 | 它见过太多旧代码，要靠你守住 Vue 3 |

五节是递进的：4.1 讲**为什么**，4.2 和 4.3 讲**模板怎么写**，
4.4 讲**数据怎么声明**，4.5 讲**这套机制背后的道理**。

## 这次课的 4 学时怎么用

| 环节 | 时长 | 做什么 |
| --- | --- | --- |
| 检查预习 | 0.3 学时 | 抽问：用原生 JS 改一个元素的内容，要写哪几步？ |
| 讲解 | 1.4 学时 | 重点讲 4.1 的两种写法对比、4.2 的绑定、4.4 的 ref |
| 现场任务 | 1.7 学时 | 跟着 4.1 到 4.4 的代码逐段敲一遍；动手做个人名片页 |
| 复盘 | 0.6 学时 | 挑几份名片页，现场排查“改了数据界面不动”的问题 |

::: warning 这次课最容易卡住的地方
不是模板语法，是**响应式没生效**。典型表现是：代码写得完全正确，
但点按钮界面就是不动。九成以上的原因是下面三种之一：

- 忘了写 `.value`；
- 直接改了对象的某个属性，但改的是解构出来的副本；
- 用新对象整体替换了 `reactive` 声明的对象，把引用换掉了。

这三种会在 [4.4](/unit04/04-reactivity) 里专门花时间讲。
**遇到界面不动时，先按这三个方向查，不要急着怀疑 Vue。**
:::

## 开始之前：需要哪些 JavaScript 基础

这个单元开始，JavaScript 基础不够会明显吃力。请对照下表自查，
任何一项不熟都建议边学边补：

| 基础点 | 在 Vue 里的用法 | 不熟的后果 |
| --- | --- | --- |
| 箭头函数 | `const fn = () => {}`、事件处理函数 | 看不懂缩写写法 |
| 数组方法 | `map`、`filter`、`find`、`reduce` | 列表渲染、派生数据写不出来 |
| 解构赋值 | `const { name, age } = user` | 看不懂组件的属性接收 |
| 模板字符串 | `` `${a} 和 ${b}` `` | 拼字符串时容易出错 |
| 三元表达式 | `a ? b : c` | 模板里的条件显示写不出来 |
| 展开运算符 | `[...list, newItem]` | 列表的不可变更新不会写 |

其中**数组方法**是最要紧的。单元 5 会大量用 `filter`、`map`、`sort`
做筛选、排序、分页，这些都属于 JavaScript 基础，不属于 Vue。
基础不牢的话，会误以为是 Vue 难。

::: tip 一个判断标准
如果你能不看资料写出“从一个学生数组里筛出所有通过审核的，再按学号排序”，
说明基础够用了。写不出来的话，先补这一块，不要硬上。
:::

## 这个单元的产出

按课程要求，这次课交一件东西：**个人名片页（含交互）**。

它不是把文字排上去就完事的静态页面，必须包含下面这些内容：

| 要求 | 说明 |
| --- | --- |
| 头像 | 用属性绑定把图片地址绑到 `src` 上，不要写死 |
| 姓名与角色标签 | 角色用对象形式的类名绑定，不同角色不同颜色 |
| 在岗 / 请假状态 | 点击按钮切换，标签的文字与颜色都要跟着变 |
| 主题色切换 | 点击按钮改变整张卡片的主题色，颜色值来自状态 |
| 至少一处列表渲染 | 比如“技能标签”“参与过的活动”，用 `v-for` 渲染数组 |

完整要求和验收标准在[单元 4 练习](/unit04/practice)。

::: details 一份合格的实现大概长什么样
核心思路是**把页面上所有会变的东西都变成状态**：

```js
const name = ref('林一鸣')
const role = ref('organizer')          // organizer / auditor / student
const isOnDuty = ref(true)
const themeColor = ref('#2f6fed')
const skills = ref(['需求梳理', '活动执行', '数据复盘'])
```

界面上所有会变的地方，都从这几个状态算出来 —— 而不是手动去改 DOM。
判断一份实现好不好，就看一句话：**改一个状态，界面是不是自己就对了。**
如果还要手动去 `querySelector` 改元素，说明还没切换到 Vue 的写法。
:::

## 读完之后

这个单元的代码都很短，但每一行都值得自己敲一遍。
尤其是 [4.1](/unit04/01-declarative) 里的两种写法对比，
建议你真的把两版代码都写出来跑一次 —— 只有自己写过命令式的版本，
才会明白声明式省掉的是什么。

读完这个单元，进入[单元 5：计算属性、侦听器与渲染控制](/unit05/)，
那里开始处理真实业务里的筛选、排序、分页。

如果模板语法里有没看懂的细节，可以顺带看：

- [API 速查手册](/appendix/cheatsheet) —— 常用 API 的用法速查
- [常见报错与排查](/appendix/errors) —— 响应式失效类报错的排查入口
