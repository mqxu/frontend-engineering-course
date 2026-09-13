# 8.2 依赖注入

## 一个三层穿透的传值难题

活动编辑页的结构是这样的：

```text
ActivityEditView.vue          页面，持有表单数据 form 与当前用户 user
└── ActivityForm.vue          表单容器，把字段分组
    └── SessionEditor.vue     场次编辑区，每条场次一张卡片
        └── SessionRow.vue    单条场次，有“删除”“上移”按钮
```

现在有个需求：`SessionRow` 里的按钮要根据当前用户角色决定是否可用 ——
只有活动组织者本人能删场次，审核员只能看不能改。`user` 数据在页面顶层。

按第七周学的办法，只能用 props 一路往下传：

```vue [逐层传 props（样板代码）]
<!-- ActivityEditView.vue -->
<ActivityForm :form="form" :user="user" />

<!-- ActivityForm.vue -->
<SessionEditor :sessions="form.sessions" :user="user" />

<!-- SessionEditor.vue -->
<SessionRow :session="session" :user="user" />

<!-- SessionRow.vue -->
<script setup>
const props = defineProps({
  session: Object,
  user: Object  // 终于用上了
})
</script>
```

问题很明显：

1. `ActivityForm` 和 `SessionEditor` **根本不用 `user`**，它们只是“二传手”。
2. 一旦 `SessionRow` 要再拿一个数据（比如“是否只读”），中间两层都要加参数、改代码。
3. 中间层删掉或换成别的组件，这条传递链就断了。

这就是**逐层传参（prop drilling）**的痛点。层级超过两层，就该考虑换一种方式。

依赖注入的思路是：**顶层直接说“我这里有一个 user，谁需要谁自己取”**，不用经过中间层。
提供方叫 `provide`，取用方叫 `inject`。

## provide 与 inject 的基本用法

```vue [src/views/ActivityEditView.vue（顶层提供）]
<script setup>
import { ref, provide } from 'vue'

const user = ref({ id: 3, name: '李老师', role: 'organizer' })

// 提供出去，键名是 user
provide('user', user)
</script>

<template>
  <ActivityForm :form="form" />
</template>
```

```vue [src/components/SessionRow.vue（深层取用）]
<script setup>
import { inject } from 'vue'

// 谁需要谁自己取，中间层完全不用管
const user = inject('user')
</script>

<template>
  <button :disabled="user?.role !== 'organizer'" @click="remove">删除</button>
</template>
```

两个文件之间隔着两层组件，代码里却没有任何传递的痕迹。**这是依赖注入最大的好处：
提供方和使用方直接对上，中间的组件不参与。**

::: tip 就近原则
如果一个组件既提供了某个键，又向下注入同一个键，它取到的是**离自己最近的那个提供值**。
也就是说，某个子树可以再 `provide` 同一个键来覆盖上层 —— 这在做“局部覆盖主题”一类功能时有用。
:::

## 响应性：provide 一个 ref 还是 provide 一个普通值

这是最容易搞错的地方：

```js [对比一：provide 普通值]
import { provide } from 'vue'

const user = { name: '李老师', role: 'organizer' }
provide('user', user)

// 之后把 user.role 改成 'reviewer'
user.role = 'reviewer'
// 深层组件 inject 到的还是原来的对象引用，但对象本身不是响应式的，
// 模板不会重新渲染
```

```js [对比二：provide 一个 ref]
import { ref, provide } from 'vue'

const user = ref({ name: '李老师', role: 'organizer' })
provide('user', user)

// 修改时必须走 .value
user.value.role = 'reviewer'
// 深层组件用到 user.value.role 的地方会重新渲染
```

**结论**：要想深层组件跟着变，提供的必须是一个响应式对象（`ref` 或 `reactive`），
并且提供的是这个对象本身，不是它的快照。

::: warning 为什么 provide 普通值不响应
`provide` 建立的是一个“值的传递”，不是“变量的引用”。你 provide 一个普通对象时，
传递的是那个对象的引用，但对象本身没有响应式能力 —— Vue 无法追踪 `user.role` 的变化。
`ref` 不一样，它自带依赖追踪，`.value` 的变化会通知所有用到它的地方。
:::

也可以 provide 一个计算属性或一个“带方法的对象”：

```js [provide 组合：状态 + 操作]
import { ref, computed, provide } from 'vue'

const user = ref({ role: 'organizer' })
const isOrganizer = computed(() => user.value.role === 'organizer')

provide('auth', {
  user,
  isOrganizer,
  // 提供一个修改方法，而不是让人直接改 user
  setRole(role) {
    user.value.role = role
  }
})
```

这种“把状态和操作一起提供”的方式，是后面写组合式函数时常用的形态。

## 只读封装：别让子组件直接改父级状态

上面那种写法有个隐患：子组件拿到 `user` 这个 ref 之后，可以直接 `user.value.role = 'reviewer'`，
把顶层的状态改了，而且改了之后很难查出是谁改的。

**正确做法是用 `readonly()` 包一层再 provide：**

```js [src/views/ActivityEditView.vue]
<script setup>
import { ref, readonly, provide } from 'vue'

const user = ref({ name: '李老师', role: 'organizer' })

// ✓ 子组件只能读，改不了；想改必须通过我们提供的方法
provide('user', readonly(user))

// 需要修改时，提供明确的方法
function switchRole(role) {
  user.value.role = role
}
provide('switchRole', switchRole)
</script>
```

子组件里尝试直接改会得到一条警告，而且改不动：

```js [深层组件]
const user = inject('user')
user.value.role = 'reviewer'
// 控制台提示：Set operation on key "role" failed: target is readonly.
```

::: tip 这不是“多此一举”
`readonly` 的价值在项目变大之后才看得出来。它把“谁能改这份数据”这件事**在代码层面写清楚了**：
数据的所有权归顶层，其他组件只能读、只能通过约定的方法改。

这和 Pinia 里“状态直接读、用 action 改”是同一个思路。养成习惯：
**provide 出去的状态默认加 `readonly`，除非你确定要让使用方改。**
:::

## 用 Symbol 作为注入键

键名是字符串，就有重名风险。你 provide 一个 `'user'`，用的某个三方组件内部也 provide 一个
`'user'`，虽然就近原则通常能救回来，但对不齐时很难排查。

更稳妥的做法是把键定义成一个 `Symbol`，放在一个单独的文件里：

```js [src/composables/keys.js]
// 全项目共用的注入键，避免字符串重名
export const USER_KEY = Symbol('user')
export const FORM_KEY = Symbol('activity-form')
```

```js [提供方]
import { ref, provide } from 'vue'
import { USER_KEY } from '@/composables/keys'

provide(USER_KEY, ref({ role: 'organizer' }))
```

```js [使用方]
import { inject } from 'vue'
import { USER_KEY } from '@/composables/keys'

const user = inject(USER_KEY)
```

`Symbol` 是唯一的，不可能和别人的键撞上。**符号名（`'user'`）只起调试作用，
方便你在 Vue DevTools 里认出来。**

::: details 小项目也要用 Symbol 吗
如果一个项目里你 provide 的键不超过三五个、且都是自己的组件，用字符串也够。
但只要键一多，或者引入了别人的组件库，Symbol 更省心。**建议直接从 Symbol 开始**，
多写一行 import 而已，省的是将来的排查时间。
:::

## 默认值与“没注入成功”的排查

`inject` 的第二个参数是默认值，第三个参数是配置：

```js [inject 的完整写法]
const user = inject(USER_KEY, null)          // 没找到时返回 null
const theme = inject('theme', 'light')       // 没找到时返回 'light'
```

**排查“inject 拿到 undefined”的三步：**

1. **提供方是不是这个使用方的祖先？** `provide` 只对**后代**生效，兄弟组件、父组件都取不到。
2. **键是不是同一个？** 用字符串键时最常见的就是 `'user'` 和 `'currentUser'` 写岔了；
   用 Symbol 就基本不会。
3. **`provide` 有没有在 `setup` 或 `<script setup>` 顶层执行？** 如果 provide 写在某个
   异步回调或条件分支里，组件初始化时可能根本没执行到。

::: warning 一个反直觉的点
`inject` 拿不到值时**不会报错**（除非你给了默认值以外的错误处理），它只是返回 `undefined`。
所以“模板里显示空白、控制台没报错”，很大概率就是注入没成功。养成习惯：
取用后立刻判断，或者给个默认值兜底。
:::

## 什么时候用 provide/inject，什么时候还是传 props

这是本节最重要的判断。给一条清晰的决策依据：

| 问题 | 用 props | 用 provide/inject |
| --- | --- | --- |
| 这份数据和“组件树层级”有关吗？ | 有关就用 props | 层级很深才用注入 |
| 中间组件关心这份数据吗？ | 关心就用 props | 不关心就用注入 |
| 数据是给“某一个子组件”还是“整棵子树”？ | 某一个子组件用 props | 整棵子树用注入 |
| 数据要能被复用成通用组件吗？ | props 更容易复用 | 注入会形成隐式依赖 |

再翻译成两句人话：

- **只给直接子组件用的数据，老老实实传 props。** 这是最清晰的接口，看组件标签就知道它要什么。
- **一份数据要被整棵子树共享、中间层完全不关心，才用 provide/inject。**
  典型例子：当前登录用户、表单上下文、i18n 语言、主题。

::: danger 别把 provide/inject 当成“全局变量”
注入的依赖是**隐式**的 —— 组件源码里看不到它从哪来，只能靠 `inject` 的名字去猜。
用多了之后，一个组件能在哪儿工作、依赖什么条件，就说不清了。

判断标准：**如果这个数据是“整个应用共享”的，那它属于全局状态，应该用 Pinia（[单元 10](/unit10/02-pinia-basics)）。**
provide/inject 管的是“某棵子树内部的共享”，范围比全局小。
:::

## 实战：活动编辑表单的上下文

把 `provide/inject` 用在一个具体场景上：活动编辑表单。表单数据在页面顶层，
深层有好几个字段组件要读它、还要改它。

先定义键与提供内容：

```js [src/composables/keys.js]
export const ACTIVITY_FORM_KEY = Symbol('activity-form')
```

```vue [src/views/ActivityEditView.vue]
<script setup>
import { reactive, computed, provide, readonly } from 'vue'
import { ACTIVITY_FORM_KEY } from '@/composables/keys'

// 表单数据在这里，所有权只属于这个页面
const form = reactive({
  title: '',
  type: 'lecture',
  capacity: 100,
  deadline: '',
  offline: false,
  sessions: []
})

// 整理成一份上下文：状态只读暴露，改只能走方法
const context = {
  form: readonly(form),

  // 派生数据
  sessionCount: computed(() => form.sessions.length),
  hasConflict: computed(() => detectConflict(form.sessions)),

  // 操作方法
  addSession(session) {
    form.sessions.push({ ...session, id: crypto.randomUUID() })
  },
  removeSession(id) {
    const i = form.sessions.findIndex((s) => s.id === id)
    if (i > -1) form.sessions.splice(i, 1)
  },
  moveSession(id, dir) {
    const i = form.sessions.findIndex((s) => s.id === id)
    const j = i + dir
    if (i < 0 || j < 0 || j >= form.sessions.length) return
    const [item] = form.sessions.splice(i, 1)
    form.sessions.splice(j, 0, item)
  }
}

provide(ACTIVITY_FORM_KEY, context)
</script>

<template>
  <ActivityForm />
</template>
```

注意几个设计取舍：

- `form` 用 `readonly` 包起来提供，字段组件**读得到、改不了**。
- 修改通过 `addSession` / `removeSession` / `moveSession` 这类具名方法进行，谁改的一目了然。
- 派生数据用 `computed` 提供，用到的组件拿到的是响应式的值。

深层组件直接取用，中间层什么都不用做：

```vue [src/components/SessionRow.vue]
<script setup>
import { inject } from 'vue'
import { ACTIVITY_FORM_KEY } from '@/composables/keys'

const { form, removeSession, moveSession, sessionCount } = inject(ACTIVITY_FORM_KEY)

defineProps({
  session: { type: Object, required: true },
  index: { type: Number, required: true }
})
</script>

<template>
  <div class="session-row">
    <span>{{ index + 1 }}. {{ session.venue }}</span>
    <span>{{ session.start }} - {{ session.end }}</span>

    <button :disabled="index === 0" @click="moveSession(session.id, -1)">上移</button>
    <button :disabled="index === sessionCount - 1" @click="moveSession(session.id, 1)">下移</button>
    <button @click="removeSession(session.id)">删除</button>
  </div>
</template>
```

`ActivityForm.vue`（中间层）和 `SessionEditor.vue` 里都不需要出现任何 `form` 相关的 props，
它们的职责回到纯粹的“布局”。

::: details 为什么不直接 provide form，而是拼一个 context 对象
两个好处：

1. **接口更清楚** —— 使用方 inject 一次就拿到了所有需要的东西，不用 inject 五六个键。
2. **可以藏实现** —— 以后把 `sessions` 从数组换成别的结构，只要方法名不变，
   使用方一行都不用改。

这已经非常接近“手写的轻量状态模块”了 —— 下一个知识点会把它正规化成组合式函数。
:::

## 小结

- `provide` 只对后代生效；中间层不再需要当“二传手”。
- 想让深层跟着变，provide 的必须是 `ref` / `reactive` 这类响应式对象，且传对象本身。
- 用 `readonly()` 包一层再 provide，把“谁能改”写清楚；修改走具名方法。
- 注入键优先用 `Symbol`，避免字符串重名；符号名只用于调试。
- `inject` 找不到时返回默认值或 `undefined`，不会报错，排查看“祖先、键名、执行时机”。
- 只给直接子组件的数据传 props；整棵子树共享、中间层不关心的数据才注入。
  全局共享的数据用 Pinia。

## 常见坑

::: details 坑 1：provide 了一个普通对象，子组件改了却不刷新
现象：子组件改了 `inject` 拿到的对象，界面没变化。

原因：提供的是普通对象，没有响应式能力。

处理：provide 时用 `ref`（记得 `inject` 后加 `.value`）或 `reactive`。
想要“只读”就再套一层 `readonly`。
:::

::: details 坑 2：在子组件里 `inject` 另一个兄弟组件的提供值
现象：`inject` 返回 `undefined`。

原因：`provide/inject` 只沿**组件树向下**，兄弟关系之间没有任何通路。

处理：把 provide 提到它们的共同父级，或者改用 Pinia。**先画一下组件树，
确认提供方确实在使用方的祖先链上**，这一步能省很多时间。
:::

::: details 坑 3：在 `onMounted` 里 provide
现象：深层组件 inject 不到。

原因：`onMounted` 触发时子组件已经创建完毕，provide 晚了。

处理：`provide` 必须写在 `setup` 顶层（`<script setup>` 里直接写），
和组件初始化同步执行。
:::

::: details 坑 4：用字符串键，和组件库撞了名
现象：某个深层组件拿到的值不是自己 provide 的。

原因：就近原则可能被三层外的组件库 provide 覆盖，或者键拼错。

处理：换成 `Symbol` 键，集中在一个 `keys.js` 里管理。
:::

## 课后练习

::: details 练习 1：把逐层传参改成注入
找一个你写过的、props 传了三层以上的场景，改成 `provide/inject`。
要求：只读的数据用 `readonly`，修改走具名方法。

**思路**：先列一张表 —— 哪些数据中间层用到（保留 props）、哪些完全不关心（改成注入）。
改完对比两个版本的组件标签，数一数 props 少了几个。
:::

::: details 练习 2：做一套局部主题覆盖
在某个页面 provide 一个 `theme` 对象（比如 `primary` 颜色），深层组件用它来设样式。
再在其中一个子区域里 provide 另一个 `theme` 覆盖它，验证“就近原则”。

**思路**：`inject('theme', { primary: '#1677ff' })` 给默认值。
注意 provide 一个 `reactive` 对象时，覆盖时要把字段合并好，别直接换引用。
:::

::: details 练习 3：给注入写一个兜底提示
写一个 `useInject(key, fallback)` 的小封装，在开发环境下如果取不到值就打印一条
带组件名与键名的警告，生产环境静默返回 `fallback`。

**思路**：用 `import.meta.env.DEV` 判断环境，用 `getCurrentInstance()` 拿组件名。
想想为什么这类“只在开发时提醒”的代码不该在生产包里 —— 体积和性能也是工程化的考虑。
:::

---

上一节：[8.1 插槽](/unit08/01-slots) ·
下一节：[8.3 内置组件](/unit08/03-builtin)
