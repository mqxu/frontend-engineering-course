# 案例 07 · 多步表单

## 案例要做什么

活动组织者要发布一个活动，需要填的东西不少：标题、类型、组织者、简介、报名截止时间、场次安排、名额上限、是否需要审核、报名规则。**把十几个字段塞进一个页面，用户会填到一半就想放弃。** 所以拆成四步：

| 步骤 | 内容 | 这一步要校验什么 |
| --- | --- | --- |
| 1 基本信息 | 标题、类型、组织者、简介 | 标题长度、类型必选、组织者必选 |
| 2 时间地点 | 报名截止时间、若干场次（场地 + 日期 + 起止时间） | 至少一个场次、时间完整、同场地时段不重叠、截止时间早于最早场次 |
| 3 名额与规则 | 名额上限、是否需要审核、报名规则说明 | 名额是正整数且有上限、需要审核时必须写规则 |
| 4 确认提交 | 把前三步汇总成一张表，逐条确认 | 全量校验，不通过就跳回第一个出错的步骤 |

除了这四步本身，这个案例还要处理三件多步表单绕不开的事：

1. **数据跨步保留。** 从第 3 步退回第 1 步改标题，前面填的场次不能丢。
2. **步骤状态机。** 上一步、下一步、跳到已通过的某一步，每个动作都有明确的前置条件。
3. **离开前提醒。** 填了一半点侧边栏跑去别的页面，得拦一下。

### 用到的知识点 → 对应章节

| 用到的知识点 | 对应章节 |
| --- | --- |
| 用一个 `reactive` 对象承载整份表单数据 | [4.4 ref 与 reactive](/unit04/04-reactivity) |
| 用 `computed` 做派生状态（能不能下一步、进度） | [5.1 计算属性与缓存](/unit05/01-computed) |
| 用 `watch` 追踪“有没有改动过” | [5.2 侦听器](/unit05/02-watch) |
| `v-model` 表单绑定与修饰符 | [6.3 表单绑定](/unit06/03-form-binding) |
| 表单校验的写法 | [6.4 表单校验](/unit06/04-validation) |
| 父子通信 props / emits | [7.2 props](/unit07/02-props) · [7.3 emits](/unit07/03-emits) |
| 把组合式函数抽出来复用 | [8.4 组合式函数](/unit08/04-composables) |
| 路由守卫与离开确认 | [9.3 路由守卫](/unit09/03-guards) |

## 数据结构与接口设计

### 表单数据

**整份表单只有一个 `reactive` 对象。** 这是“跨步保留”能轻松做到的根本原因：四步对应的是这个对象的不同字段，切步骤只是换一个组件渲染，数据本身从来没动过。

```js [src/views/activity/useActivityForm.js]
import { reactive } from 'vue'

export function createActivityForm() {
  return reactive({
    // ---- 第 1 步：基本信息 ----
    title: '',
    type: '', // lecture | sports | art | volunteer
    organizer: '',
    summary: '',

    // ---- 第 2 步：时间地点 ----
    deadline: '', // datetime-local 的值，形如 2026-10-01T18:00
    sessions: [
      // { id, venue, date, start, end }
    ],

    // ---- 第 3 步：名额与规则 ----
    capacity: 100,
    needAudit: true,
    ruleText: ''
  })
}
```

为什么不用四个 `ref` 分别存四步的数据？因为拆开之后，第 2 步的校验要用到第 1 步的 `title`（用来拼提示语）、第 4 步的汇总要用到前两步的所有字段，你会被迫在这些 `ref` 之间来回传。**一个对象，一份数据，是表单最省事的心智模型。**

### 步骤定义与校验钩子

步骤不是写死在模板里的，而是**一份配置数据**。这样步骤增删、顺序调整、校验规则修改，都只动这一个数组。

```js [src/views/activity/useActivitySteps.js]
export const STEP_KEYS = ['basic', 'schedule', 'quota', 'confirm']

export const stepMeta = [
  { key: 'basic', title: '基本信息', desc: '活动叫什么、谁来办' },
  { key: 'schedule', title: '时间地点', desc: '什么时候、在哪儿办' },
  { key: 'quota', title: '名额与规则', desc: '收多少人、怎么报名' },
  { key: 'confirm', title: '确认提交', desc: '核对一遍再提交' }
]
```

```js [src/views/activity/validators.js]
// 校验函数统一约定：通过返回 true，不通过返回一句中文提示
let seed = 0
export function createSession() {
  return { id: ++seed, venue: '', date: '', start: '', end: '' }
}

export function validateBasic(form) {
  const title = form.title.trim()
  if (!title) return '请填写活动标题'
  if (title.length < 4) return '标题至少 4 个字'
  if (title.length > 40) return '标题不要超过 40 个字'
  if (!form.type) return '请选择活动类型'
  if (!form.organizer) return '请选择组织者'
  return true
}

// 两个场次是否冲突：同一天、同一场地、时间段有交集
// 边界相接不算冲突：一个 09:00-11:00，另一个 11:00-13:00，是合法的
export function isConflict(a, b) {
  if (a.date !== b.date || a.venue !== b.venue) return false
  return a.start < b.end && b.start < a.end
}

export function validateSchedule(form) {
  if (form.deadline === '') return '请选择报名截止时间'
  if (form.sessions.length === 0) return '至少添加一个场次'

  for (const session of form.sessions) {
    if (!session.venue) return '每个场次都要选场地'
    if (!session.date) return '每个场次都要选日期'
    if (!session.start || !session.end) return '每个场次都要填开始和结束时间'
    if (session.start >= session.end) return '场次的结束时间要晚于开始时间'
  }

  // 两两比较，找出第一处冲突就返回
  for (let i = 0; i < form.sessions.length; i++) {
    for (let j = i + 1; j < form.sessions.length; j++) {
      if (isConflict(form.sessions[i], form.sessions[j])) {
        const s = form.sessions[j]
        return `${s.date} 在 ${s.venue} 的时段与其他场次重叠了`
      }
    }
  }

  const earliest = form.sessions
    .map((s) => new Date(`${s.date}T${s.start}`))
    .sort((a, b) => a - b)[0]
  if (new Date(form.deadline) >= earliest) {
    return '报名截止时间要早于最早场次的开始时间'
  }
  return true
}

export function validateQuota(form) {
  if (!Number.isInteger(form.capacity) || form.capacity <= 0) {
    return '名额要填一个正整数'
  }
  if (form.capacity > 2000) return '单个活动名额不要超过 2000'
  if (form.needAudit && form.ruleText.trim().length < 10) {
    return '勾选了需要审核，报名规则说明至少要写 10 个字'
  }
  return true
}
```

### 校验函数为什么单独放一个文件

注意上面三个校验函数的形态：**它们都是纯函数，参数是 `form`，返回值是 `true` 或一句提示。** 这是一个刻意做的选择，好处有三个：

第一，**校验和界面解耦。** 校验逻辑不写在 `.vue` 里，样式怎么改、布局怎么调，都碰不到它。想在提交前统一跑一遍、想在单元测试里单独测它，都很直接。

第二，**同一份规则可以被多个地方复用。** 第 2 步的时段冲突检测，在 `StepSchedule.vue` 里被用来做实时红框提示，在提交前又被 `validateAll` 用来做全量校验 —— 两处调的是同一个 `isConflict`。如果规则分散在两个文件里各写一遍，早晚会出现“一个地方提示冲突、另一个地方放行”的情况。

第三，**提示语是数据，不是逻辑。** 校验函数返回的字符串可以直接扔到页面上，不需要维护一张“错误码 → 文案”的映射表。对中小型表单来说，这样最省事。

::: warning 校验函数不要碰组件状态
`validateSchedule(form)` 只依赖传入的 `form`，不读 `ref`、不读全局变量、不调接口。一旦它开始依赖外部状态，你就没法在别处复用它了，也没法预测它什么时候会返回什么。**“同样的输入永远得到同样的输出”，是这类函数最值钱的性质。**
:::

### 接口约定

```js [src/api/activity.js]
import request from './request'

// 创建活动：成功后返回新建活动的 id
export function createActivity(payload) {
  return request.post('/api/activity', payload)
}

// 场地下拉列表
export function fetchVenues() {
  return request.get('/api/venue/list')
}
```

提交给后端的结构里，**不带前端的临时字段**（比如场次的 `id`），由写接口的同事按约定来处理。这一点在下一步的“格式转换”里会具体写。

## 实现步骤

### 第一步：定义步骤状态机

多步表单的核心是一个很小的状态机：一个下标表示当前在哪一步，一个布尔数组记录每一步是否已经通过校验。**“能不能往下走”这件事必须由校验结果决定，不能只靠点击。**

```js [src/composables/useWizard.js]
import { ref, computed } from 'vue'

/**
 * @param {Array<{ key: string, title: string, validate?: () => true | string }>} steps
 * @param {{ onChange?: (index: number) => void }} [options]
 */
export function useWizard(steps, options = {}) {
  const current = ref(0)
  // 每一步是否已经通过过校验
  const passed = ref(steps.map(() => false))
  // 当前步骤的校验提示，空字符串表示没有错误
  const message = ref('')

  const step = computed(() => steps[current.value])
  const isFirst = computed(() => current.value === 0)
  const isLast = computed(() => current.value === steps.length - 1)
  const progress = computed(() =>
    Math.round((current.value / (steps.length - 1)) * 100)
  )

  function validateCurrent() {
    const validate = steps[current.value]?.validate
    if (!validate) return true
    const result = validate()
    message.value = result === true ? '' : result
    return result === true
  }

  function goNext() {
    // 校验不通过就停在本步，把提示留在 message 里
    if (!validateCurrent()) return false
    passed.value[current.value] = true
    if (!isLast.value) current.value += 1
    message.value = ''
    options.onChange?.(current.value)
    return true
  }

  function goPrev() {
    message.value = ''
    if (!isFirst.value) current.value -= 1
    options.onChange?.(current.value)
  }

  // 往回跳随时可以；往前跳要求“路上每一步都已经通过”
  function canJumpTo(index) {
    if (index <= current.value) return true
    return passed.value.slice(0, index).every(Boolean)
  }

  function goTo(index) {
    if (index < 0 || index >= steps.length) return
    if (!canJumpTo(index)) return
    message.value = ''
    current.value = index
    options.onChange?.(index)
  }

  // 提交前跑一遍全部校验，遇到第一个不合格的就跳过去并显示提示
  function validateAll() {
    for (let i = 0; i < steps.length; i++) {
      const validate = steps[i].validate
      if (!validate) continue
      const result = validate()
      if (result !== true) {
        current.value = i
        message.value = result
        return false
      }
      passed.value[i] = true
    }
    message.value = ''
    return true
  }

  return {
    current,
    step,
    isFirst,
    isLast,
    progress,
    message,
    passed,
    goNext,
    goPrev,
    goTo,
    canJumpTo,
    validateCurrent,
    validateAll
  }
}
```

几个设计点解释一下：

- **`passed` 记录的是“曾经通过过”，不是“现在合法”。** 用户在第 2 步通过校验后回到第 1 步把标题清空，第 2 步的 `passed` 仍是 `true`。真正提交前 `validateAll` 会重跑所有校验，所以不会带着错误数据提交。平时跳步允许宽松一点，提交时严格，这是体验和正确性的折中。
- **`progress` 用 `current / (steps.length - 1)`**，所以第 1 步是 0%，最后一步是 100%。进度条的含义是“当前位置在整条路上的比例”，而不是“完成了百分之几的任务”。
- **`onChange` 回调**给页面留了一个钩子，滚动到顶部、上报埋点、记住上次的位置都可以挂在这里。

::: details 为什么不把校验直接写在组件里
一个常见的写法是让每个步骤组件自己判断“我这一步合不合法”，然后 `emit('valid', true)` 回来。这样做能跑，但会带来两个问题：一是“下一步”按钮被点的那一刻，父组件其实不知道当前步到底合不合法，得等子组件回报，时序容易乱；二是提交前的全量校验没法做，因为校验逻辑在四个已经卸载的组件里。

把校验抽成一组接收 `form` 的纯函数，放一个文件里，父组件就能**在任何时刻、任何顺序下主动调用它们**。步骤组件只管展示提示语和收集输入，不承担判断责任。这也是为什么 `useWizard` 的构造参数里，每一步带的是一个 `validate` 函数而不是一个布尔值。
:::

### 第二步：进度指示器组件

指示器只做三件事：显示每一步、标记当前和已完成、处理点击跳转。**它不判断“能不能跳”，判断逻辑通过 `canJumpTo` 传进来** —— 组件不应该知道状态机的内部规则。

```vue [src/views/activity/StepIndicator.vue]
<script setup>
defineProps({
  steps: { type: Array, required: true },
  current: { type: Number, required: true },
  passed: { type: Array, required: true },
  canJumpTo: { type: Function, required: true }
})

const emit = defineEmits(['jump'])
</script>

<template>
  <ol class="stepper">
    <li
      v-for="(item, index) in steps"
      :key="item.key"
      class="stepper__item"
      :class="{
        'is-active': index === current,
        'is-done': passed[index],
        'is-disabled': !canJumpTo(index)
      }"
    >
      <button type="button" :disabled="!canJumpTo(index)" @click="emit('jump', index)">
        <span class="stepper__index">
          <template v-if="passed[index] && index !== current">✓</template>
          <template v-else>{{ index + 1 }}</template>
        </span>
        <span class="stepper__text">
          <span class="stepper__title">{{ item.title }}</span>
          <span class="stepper__desc">{{ item.desc }}</span>
        </span>
      </button>
    </li>
  </ol>
</template>

<style scoped>
.stepper {
  display: flex;
  gap: 8px;
  margin: 0 0 24px;
  padding: 0;
  list-style: none;
}

.stepper__item button {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 10px 14px;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  background: #fff;
  cursor: pointer;
  text-align: left;
}

.stepper__item.is-active button {
  border-color: #42b883;
  background: #f0faf6;
}

.stepper__item.is-done button {
  border-color: #b3e19d;
}

.stepper__item.is-disabled button {
  cursor: not-allowed;
  opacity: 0.55;
}

.stepper__index {
  display: grid;
  place-items: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #f0f2f5;
  font-size: 13px;
}

.stepper__title {
  display: block;
  font-size: 14px;
}

.stepper__desc {
  display: block;
  color: #909399;
  font-size: 12px;
}
</style>
```

### 第三步：四个子步骤组件

四个步骤都是“只负责渲染和改数据”的哑组件，数据由父组件通过 props 传进来。因为传的是一个 `reactive` 对象，子组件改它的字段会**直接反映到父组件**，不需要 `emit` 一层层往回传。

```vue [src/views/activity/StepBasic.vue]
<script setup>
defineProps({
  form: { type: Object, required: true }
})

const TYPE_OPTIONS = [
  { value: 'lecture', label: '讲座报告' },
  { value: 'sports', label: '体育竞技' },
  { value: 'art', label: '文艺演出' },
  { value: 'volunteer', label: '志愿服务' }
]

const ORGANIZERS = [
  { value: 'cs-college', label: '计算机学院学生会' },
  { value: 'art-center', label: '大学生艺术中心' },
  { value: 'youth-league', label: '校团委' }
]
</script>

<template>
  <div class="step-basic">
    <label class="field">
      <span class="field__label">活动标题</span>
      <input v-model.trim="form.title" maxlength="40" placeholder="不超过 40 个字" />
    </label>

    <label class="field">
      <span class="field__label">活动类型</span>
      <select v-model="form.type">
        <option value="">请选择</option>
        <option v-for="item in TYPE_OPTIONS" :key="item.value" :value="item.value">
          {{ item.label }}
        </option>
      </select>
    </label>

    <label class="field">
      <span class="field__label">主办组织</span>
      <select v-model="form.organizer">
        <option value="">请选择</option>
        <option v-for="item in ORGANIZERS" :key="item.value" :value="item.value">
          {{ item.label }}
        </option>
      </select>
    </label>

    <label class="field">
      <span class="field__label">活动简介</span>
      <textarea v-model="form.summary" rows="3" maxlength="200" />
    </label>
  </div>
</template>
```

第 2 步稍微复杂一点，因为它要增删场次、还要实时提示冲突：

```vue [src/views/activity/StepSchedule.vue]
<script setup>
import { computed, onMounted, ref } from 'vue'
import { createSession, isConflict } from './validators'
import { fetchVenues } from '@/api/activity'

const props = defineProps({
  form: { type: Object, required: true }
})

const venues = ref([])

onMounted(async () => {
  venues.value = await fetchVenues()
})

function addSession() {
  props.form.sessions.push(createSession())
}

function removeSession(index) {
  props.form.sessions.splice(index, 1)
}

// 标出哪些场次当前是冲突的，做即时提示
const conflictIds = computed(() => {
  const ids = new Set()
  const list = props.form.sessions
  for (let i = 0; i < list.length; i++) {
    for (let j = i + 1; j < list.length; j++) {
      if (isConflict(list[i], list[j])) {
        ids.add(list[i].id)
        ids.add(list[j].id)
      }
    }
  }
  return ids
})
</script>

<template>
  <div class="step-schedule">
    <label class="field">
      <span class="field__label">报名截止时间</span>
      <input v-model="form.deadline" type="datetime-local" />
    </label>

    <div class="field">
      <span class="field__label">场次安排</span>

      <div
        v-for="(session, index) in form.sessions"
        :key="session.id"
        class="session"
        :class="{ 'is-conflict': conflictIds.has(session.id) }"
      >
        <select v-model="session.venue">
          <option value="">选择场地</option>
          <option v-for="venue in venues" :key="venue.id" :value="venue.name">
            {{ venue.name }}（容纳 {{ venue.capacity }} 人）
          </option>
        </select>

        <input v-model="session.date" type="date" />
        <input v-model="session.start" type="time" />
        <input v-model="session.end" type="time" />

        <button type="button" @click="removeSession(index)">删除</button>
      </div>

      <button type="button" @click="addSession">添加场次</button>

      <p v-if="conflictIds.size > 0" class="hint hint--error">
        有场次的时间段重叠了，同一个场地同一时段只能排一场。
      </p>
    </div>
  </div>
</template>
```

注意这里用了 `:key="session.id"`，**不是 `index`**。场次可以增删，用下标当 `key` 会让 Vue 在删除时错位复用 DOM，输入框里已经填的值会跑到错误的行上。这个坑在[5.4 列表渲染](/unit05/04-list)里专门讲过，表格类界面里几乎必踩一次。

第 3 步和第 4 步：

```vue [src/views/activity/StepQuota.vue]
<script setup>
defineProps({
  form: { type: Object, required: true }
})
</script>

<template>
  <div class="step-quota">
    <label class="field">
      <span class="field__label">名额上限</span>
      <input v-model.number="form.capacity" type="number" min="1" max="2000" />
      <span class="field__tip">通过审核的报名人数达到上限后，报名入口自动关闭。</span>
    </label>

    <label class="field field--row">
      <input v-model="form.needAudit" type="checkbox" />
      <span>报名需要审核</span>
    </label>

    <label class="field">
      <span class="field__label">报名规则说明</span>
      <textarea
        v-model="form.ruleText"
        rows="4"
        placeholder="说明报名条件、材料要求、审核标准等"
      />
    </label>
  </div>
</template>
```

```vue [src/views/activity/StepConfirm.vue]
<script setup>
defineProps({
  form: { type: Object, required: true },
  typeLabel: { type: Function, required: true },
  organizerLabel: { type: Function, required: true }
})

const emit = defineEmits(['edit'])
</script>

<template>
  <div class="step-confirm">
    <section class="summary">
      <header>
        <h4>基本信息</h4>
        <button type="button" @click="emit('edit', 0)">修改</button>
      </header>
      <dl>
        <dt>活动标题</dt>
        <dd>{{ form.title }}</dd>
        <dt>活动类型</dt>
        <dd>{{ typeLabel(form.type) }}</dd>
        <dt>主办组织</dt>
        <dd>{{ organizerLabel(form.organizer) }}</dd>
        <dt>活动简介</dt>
        <dd>{{ form.summary || '未填写' }}</dd>
      </dl>
    </section>

    <section class="summary">
      <header>
        <h4>时间地点</h4>
        <button type="button" @click="emit('edit', 1)">修改</button>
      </header>
      <dl>
        <dt>报名截止</dt>
        <dd>{{ form.deadline.replace('T', ' ') }}</dd>
      </dl>
      <table>
        <thead>
          <tr>
            <th>场地</th>
            <th>日期</th>
            <th>时间</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="session in form.sessions" :key="session.id">
            <td>{{ session.venue }}</td>
            <td>{{ session.date }}</td>
            <td>{{ session.start }} - {{ session.end }}</td>
          </tr>
        </tbody>
      </table>
    </section>

    <section class="summary">
      <header>
        <h4>名额与规则</h4>
        <button type="button" @click="emit('edit', 2)">修改</button>
      </header>
      <dl>
        <dt>名额上限</dt>
        <dd>{{ form.capacity }} 人</dd>
        <dt>报名审核</dt>
        <dd>{{ form.needAudit ? '需要审核' : '报名即通过' }}</dd>
        <dt>报名规则</dt>
        <dd>{{ form.ruleText || '未填写' }}</dd>
      </dl>
    </section>
  </div>
</template>
```

### 第四步：把父页面拼起来

父页面负责三件事：创建表单、把校验函数绑到步骤定义上、处理提交。

```vue [src/views/activity/ActivityCreateView.vue]
<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useWizard } from '@/composables/useWizard'
import { createActivityForm } from './useActivityForm'
import { stepMeta } from './useActivitySteps'
import { validateBasic, validateSchedule, validateQuota } from './validators'
import { createActivity } from '@/api/activity'
import { toast } from '@/composables/useToast'
import StepIndicator from './StepIndicator.vue'
import StepBasic from './StepBasic.vue'
import StepSchedule from './StepSchedule.vue'
import StepQuota from './StepQuota.vue'
import StepConfirm from './StepConfirm.vue'

const router = useRouter()
const form = createActivityForm()

const TYPE_LABELS = {
  lecture: '讲座报告',
  sports: '体育竞技',
  art: '文艺演出',
  volunteer: '志愿服务'
}

const ORGANIZER_LABELS = {
  'cs-college': '计算机学院学生会',
  'art-center': '大学生艺术中心',
  'youth-league': '校团委'
}

// 把校验函数绑到步骤定义上，状态机不关心校验内容是什么
const steps = computed(() => [
  { ...stepMeta[0], validate: () => validateBasic(form) },
  { ...stepMeta[1], validate: () => validateSchedule(form) },
  { ...stepMeta[2], validate: () => validateQuota(form) },
  { ...stepMeta[3] } // 最后一步没有额外校验
])

const wizard = useWizard(steps.value)
const submitting = ref(false)

function typeLabel(value) {
  return TYPE_LABELS[value] || '未选择'
}

function organizerLabel(value) {
  return ORGANIZER_LABELS[value] || '未选择'
}

// 提交前把前端结构翻译成后端约定的结构，去掉临时字段
function toPayload(source) {
  return {
    title: source.title.trim(),
    type: source.type,
    organizer: source.organizer,
    summary: source.summary,
    deadline: source.deadline,
    capacity: source.capacity,
    needAudit: source.needAudit,
    ruleText: source.ruleText,
    sessions: source.sessions.map((s) => ({
      venue: s.venue,
      date: s.date,
      start: s.start,
      end: s.end
    }))
  }
}

async function handleSubmit() {
  if (!wizard.validateAll()) return
  submitting.value = true
  try {
    await createActivity(toPayload(form))
    toast.success('活动已创建，等待审核')
    await router.push('/activities')
  } catch (error) {
    toast.error(error.message, 0)
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="create-view">
    <StepIndicator
      :steps="steps"
      :current="wizard.current.value"
      :passed="wizard.passed.value"
      :can-jump-to="wizard.canJumpTo"
      @jump="wizard.goTo"
    />

    <p v-if="wizard.message.value" class="step-error">{{ wizard.message.value }}</p>

    <StepBasic v-if="wizard.current.value === 0" :form="form" />
    <StepSchedule v-else-if="wizard.current.value === 1" :form="form" />
    <StepQuota v-else-if="wizard.current.value === 2" :form="form" />
    <StepConfirm
      v-else
      :form="form"
      :type-label="typeLabel"
      :organizer-label="organizerLabel"
      @edit="wizard.goTo"
    />

    <footer class="actions">
      <button
        type="button"
        :disabled="wizard.isFirst.value"
        @click="wizard.goPrev"
      >
        上一步
      </button>

      <button
        v-if="!wizard.isLast.value"
        type="button"
        @click="wizard.goNext"
      >
        下一步
      </button>

      <button
        v-else
        type="button"
        :disabled="submitting"
        @click="handleSubmit"
      >
        {{ submitting ? '提交中…' : '提交' }}
      </button>
    </footer>
  </div>
</template>
```

注意 `wizard.current.value` 这种写法。`useWizard` 返回的 `current` 是一个 `ref`，在模板里本该自动解包，但它是从**普通函数返回值里解构出来的**，模板只会对顶层 `setup` 返回的 `ref` 自动解包，嵌套在对象里的不会。稳妥的做法是用 `storeToRefs` 的思路显式写 `.value`，或者把 `current`、`message` 单独解构出来。这里为了把状态机完整暴露成一个对象，统一写 `.value`。

::: tip 想让模板清爽一点
可以在父组件里再包一层：

```js
const { current, message, isFirst, isLast, passed } = useWizard(steps.value)
```

这样在模板里直接写 `current`、`message` 就行 —— 顶层解构出来的 `ref` 会被模板自动解包。**但要注意别把 `goNext` 这类方法也解构丢了引用之外的语义**，方法本来就没绑定 `this`，解构出来照样能用。
:::

### 第五步：离开前提醒

用户填到一半跑去别的页面，得拦一下。这里要拦两种“离开”：

- **站内路由跳转**（点侧边栏、点返回按钮）—— 思路是用路由守卫。
- **关闭标签页 / 刷新 / 在地址栏敲别的网址** —— 路由守卫管不到，要用 `beforeunload`。

```js [src/views/activity/useUnsavedGuard.js]
import { ref, watch, onMounted, onBeforeUnmount } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'

export function useUnsavedGuard(source, isSubmitted) {
  // 有没有改动过。初始 false，任何一次数据变化都置为 true
  const dirty = ref(false)
  // 提交成功时把 dirty 关掉，避免提交完跳走还弹提醒
  const saving = ref(false)

  watch(
    source,
    () => {
      if (!saving.value) dirty.value = true
    },
    { deep: true }
  )

  function shouldWarn() {
    return dirty.value && !isSubmitted.value
  }

  // 站内跳转：返回 false 会取消这次导航
  onBeforeRouteLeave(() => {
    if (!shouldWarn()) return true
    return window.confirm('活动还没提交，确定要离开吗？离开后已填写的内容会丢失。')
  })

  // 关标签页/刷新：现代浏览器不支持自定义文案，只弹系统提示
  function handleBeforeUnload(event) {
    if (!shouldWarn()) return
    event.preventDefault()
    // 按规范需要给 returnValue 赋值，浏览器才会弹确认框
    event.returnValue = ''
  }

  onMounted(() => window.addEventListener('beforeunload', handleBeforeUnload))
  onBeforeUnmount(() => window.removeEventListener('beforeunload', handleBeforeUnload))

  return { dirty, saving, shouldWarn }
}
```

父页面接上：

```js [src/views/activity/ActivityCreateView.vue（新增部分）]
<script setup>
import { ref } from 'vue'
import { useUnsavedGuard } from './useUnsavedGuard'

// ……前面的代码

const submitted = ref(false)
const guard = useUnsavedGuard(form, submitted)

async function handleSubmit() {
  if (!wizard.validateAll()) return
  submitting.value = true
  guard.saving.value = true // 提交过程中不触发 dirty
  try {
    await createActivity(toPayload(form))
    submitted.value = true // 先标记已提交，再跳转
    toast.success('活动已创建，等待审核')
    await router.push('/activities')
  } catch (error) {
    toast.error(error.message, 0)
  } finally {
    guard.saving.value = false
    submitting.value = false
  }
}
</script>
```

顺序很关键：**先 `submitted.value = true`，再 `router.push`。** 如果反过来，`onBeforeRouteLeave` 会在 `submitted` 还是 `false` 的时候被触发，用户就会在提交成功后收到一条“内容会丢失”的提醒。

::: warning 提交按钮要能防住连点
用户手快连点两下“提交”，就会发出两个创建请求，后端收到两条一模一样的数据。这在活动发布这种场景里非常麻烦，因为活动是**不能重复创建**的。

本案例用了两个手段叠在一起：按钮上 `:disabled="submitting"` 挡住第二次点击，`submitting` 在 `try` 之前就置为 `true`。这两步必须都在**第一个 `await` 之前完成**，否则两个请求还是会几乎同时发出去。

后端也应该做幂等（比如带一个客户端生成的 `requestId`，重复的直接返回第一次的结果）。**前端防连点是体验，后端幂等才是保证。** 这条判断在后端接口设计里同样适用。
:::


`beforeunload` 有一个容易误解的地方：**浏览器早就禁用了自定义文案**，你写什么用户都不会看到，只会看到“确定要离开此网站吗”这类系统提示。所以 `event.returnValue = ''` 就够了，别在文案上纠结。

::: tip 三种“离开”要分清
用户离开正在编辑的页面，其实有三种路径，处理方式各不相同：

| 离开方式 | 谁来管 | 能做到什么 |
| --- | --- | --- |
| 站内路由跳转 | `onBeforeRouteLeave` | 可以弹自定义文案，甚至可以“保存草稿再走” |
| 关标签页 / 刷新 / 改地址栏 | `beforeunload` | 只能弹系统确认框，无法自定义文案 |
| 浏览器后退到站外 | `beforeunload` | 同上 |

`onBeforeRouteLeave` 拦截不到后两种，所以两个都要写。**只写路由守卫，用户一按 F5 内容照样丢**，这是新手最常漏的一环。
:::


## 完整代码

目录结构：

```text [src/]
src/
├── api/
│   └── activity.js
├── composables/
│   └── useWizard.js
├── views/
│   └── activity/
│       ├── ActivityCreateView.vue
│       ├── StepIndicator.vue
│       ├── StepBasic.vue
│       ├── StepSchedule.vue
│       ├── StepQuota.vue
│       ├── StepConfirm.vue
│       ├── useActivityForm.js
│       ├── useActivitySteps.js
│       ├── useUnsavedGuard.js
│       └── validators.js
└── router/
    └── index.js
```

路由配置里给编辑页加一条，离开守卫才能生效：

```js [src/router/index.js]
import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/activities',
      name: 'activity-list',
      component: () => import('@/views/ActivityListView.vue')
    },
    {
      path: '/activities/create',
      name: 'activity-create',
      component: () => import('@/views/activity/ActivityCreateView.vue'),
      meta: { title: '发布活动' }
    }
  ]
})

export default router
```

`useWizard.js`、`validators.js`、`StepIndicator.vue`、四个步骤组件与上面实现步骤里给出的完全一致，这里不再重复。最终跑起来的效果是：四步依次填写，任何一步没通过校验就停在本步并显示提示，通过后可以回头改任意一步，最后一步汇总确认，提交前会再全量校验一次。

## 常见坑

::: details 坑 1：把四步的数据拆成四个 ref，跨步就丢
**现象**：从第 2 步退回第 1 步改一下标题，第 2 步填的场次全没了。

**原因**：每一步各写了一个 `reactive`，切换步骤时用了 `v-if`，被切走的那个组件卸载，它内部的状态跟着销毁。

**怎么处理**：**整份表单只有一个 `reactive` 对象，放在父页面顶层。** 子组件通过 props 拿到它的引用去改字段。只要父组件还在，数据就在。
:::

::: details 坑 2：`v-if` 切步骤，表单的 DOM 值丢了
**现象**：第 1 步用原生 `<input>` 没绑 `v-model`，退回上一步再前进，内容清空了。

**原因**：`v-if` 会销毁并重建 DOM，元素上的值当然也没了。`v-model` 之所以不受影响，是因为值存在 JS 状态里，DOM 只是它的投影。

**怎么处理**：所有输入框都必须 `v-model` 到那份共享数据上。**不要依赖 DOM 保存状态**，这是[4.1 声明式渲染](/unit04/01-declarative)的核心思想。如果确实想让 DOM 一直存在（比如避免重复加载下拉数据），把 `v-if` 换成 `v-show`，但要接受四个步骤同时在 DOM 里。
:::

::: details 坑 3：子组件直接改 props 的对象，控制台没报错但感觉“不对劲”
**现象**：`defineProps({ form: Object })` 之后，子组件里 `form.title = 'xxx'`，能改，也不报错。

**原因**：Vue 对 props 的只读限制是**浅层的**。它拦的是“给 `form` 这个 prop 重新赋值”，不拦“改 `form` 里面的属性”。传进去的是一个对象引用，改内部字段当然有效。

**怎么处理**：这在这种“共享表单对象”的场景里是**故意这么用的**，可以接受，但要在团队里约定清楚：**表单对象的所有权在父页面，子组件只允许改字段，不允许整体替换。** 如果需要更严格，就把校验和提交都收到父组件，子组件只 `emit` 字段变化 —— 代价是代码量会翻倍，一般的活动表单不值得。
:::

::: details 坑 4：`useWizard(steps.value)` 传了个快照，步骤变了不生效
**现象**：`steps` 是 `computed`，改了什么之后进度条不更新。

**原因**：`computed` 的 `.value` 拿出来是一个快照，而且 `useWizard` 内部只在初始化时读了一次。

**怎么处理**：步骤定义是**静态配置**时，传快照完全没问题，本案例就是静态的。如果步骤本身会变化（比如根据活动类型显示不同的第 3 步），要么把 `steps` 改成 ref 传进去、在内部用 `steps.value`，要么干脆让 `computed` 依赖稳定的配置。**别把会变的东西当不会变的用。**
:::

::: details 坑 5：`onBeforeRouteLeave` 在组件卸载后还留着
**现象**：已经离开编辑页了，在别的页面点击链接还会弹“内容会丢失”。

**原因**：一般不会出现，因为 `onBeforeRouteLeave` 是绑定到当前路由组件的，组件卸载时守卫自动注销。真正的问题通常是把守卫写在了**不成对**的地方，比如在 `watch` 回调里重复注册。

**怎么处理**：`onBeforeRouteLeave` 只在 `setup` 顶层调用一次。如果确实要在别处注册，用 `onBeforeRouteLeave` 返回的注销函数手动清理。**写守卫前先确认它到底注册在哪个组件上。**
:::

::: details 坑 6：`beforeunload` 里写了自定义文案，用户看不到
**现象**：`event.returnValue = '活动还没提交'`，浏览器弹的是系统默认提示。

**原因**：出于安全考虑，浏览器禁止网页在关闭确认框里显示自定义文字，你的文案会被忽略。

**怎么处理**：接受现实，`event.returnValue = ''` 就行。想要具体提示，就在页面里显眼地放一个“未提交”状态条，别指望离开时那个弹窗。
:::

::: details 坑 7：步骤校验只在前端做，后端仍然可能拒绝
**现象**：四步全绿、点提交却返回 400。

**原因**：前端的校验是为了**早提示、少往返**，不是安全边界。名额上限、时段冲突这些规则，后端一定要再校验一次 —— 用户完全可以绕过页面直接发请求。

**怎么处理**：前端校验规则要和后端接口约定一致（同一个规则在两个地方都要写）。后端返回的错误要能定位到具体字段，这样才好在页面上标出来。**前端校验是体验，后端校验是底线。**
:::

## 扩展练习

::: details 练习 1：给表单加本地草稿
每 5 秒把 `form` 存进 `localStorage`，页面重新打开时如果有草稿就提示“发现未提交的草稿，是否恢复”。

**思路**：`watch` + `debounce` 再写入，别每次按键都写。注意两点：`localStorage` 只能存字符串，用 `JSON.stringify` / `JSON.parse`；恢复之前要校验草稿的结构（用户可能升级了版本，旧草稿字段对不上），做法是给草稿加一个 `version` 字段，版本不符就直接丢弃。
:::

::: details 练习 2：把校验规则改成声明式
现在校验函数里是一串 `if`。试试用一张字段规则表来驱动校验：

```js
const basicRules = {
  title: [
    { required: true, message: '请填写活动标题' },
    { min: 4, message: '标题至少 4 个字' },
    { max: 40, message: '标题不要超过 40 个字' }
  ]
}
```

**思路**：写一个 `runRules(form, rules)` 返回第一条不通过的提示。难点不在实现，在于想清楚“跨字段的规则”（比如截止时间要早于最早场次）怎么塞进这套模型 —— 有些规则天生不是单个字段能表达的，可能需要单独的 `validateCrossField`。**能识别出哪些规则不适合抽象，比抽象本身更重要。**
:::

::: details 练习 3：支持“编辑已有活动”
现在是新建流程。需求改成“也能编辑一个已经存在的活动”，要求：进入时先把已有数据加载进表单，标题显示“编辑活动”，提交时调更新接口。

**思路**：路由上用动态参数 `/activities/:id/edit`（见[9.2 动态参数](/unit09/02-nested-params)），`id` 不存在就是新建。真正的难点是**草稿和未保存提醒的行为要区分**：新建时随便离开都要提醒，编辑时“没改过就不用提醒”。这正是本案例里 `dirty` 存在的意义 —— 它按“有没有改动”判断，而不是按“填了没有”。
:::

::: details 练习 4：把四个步骤改成可访问的键盘流程
给指示器加上键盘支持：左右方向键在步骤之间移动焦点，`Enter` 才真正跳转；当前步骤用 `aria-current="step"` 标记。

**思路**：`<ol>` 加 `role="tablist"` 那套是另一条路，用原生按钮加 `aria-current` 更简单。要点是**焦点和选中状态分开管理**：方向键只移动焦点，`Enter` 才改 `current`，否则用户只是想在步骤间浏览一下，却把表单切走了会很不舒服。
:::

---

上一页：[案例 06 · 模态框与全局通知](/cases/06-modal) · 下一页：[案例 08 · 画板与撤销重做](/cases/08-canvas)
