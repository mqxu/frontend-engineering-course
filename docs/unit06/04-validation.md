# 6.4 表单校验

## 从一团 if 说起

活动发布表单有八个字段。第一版代码是这样写的：

```vue [src/components/ActivityForm.vue（第一版）]
<script setup>
import { ref } from 'vue'

const form = ref({ title: '', capacity: '', deadline: '', contact: '' })
const message = ref('')

function submit() {
  // ✗ 一个函数里塞了所有判断，而且只提示第一条
  if (!form.value.title) {
    message.value = '标题不能为空'
    return
  }
  if (form.value.title.length > 30) {
    message.value = '标题太长了'
    return
  }
  if (!form.value.capacity) {
    message.value = '名额不能为空'
    return
  }
  if (Number(form.value.capacity) <= 0) {
    message.value = '名额必须大于 0'
    return
  }
  if (!/^1[3-9]\d{9}$/.test(form.value.contact)) {
    message.value = '手机号格式不对'
    return
  }
  // ……还有四条
}
</script>
```

这段代码能跑，但问题很明显：

1. **错误提示只有一个位置**，用户必须“改一个、提交一次、再改一个”，来回好几轮。
2. **规则和界面混在一起**，想复用“手机号格式”这条规则，只能复制粘贴。
3. **加一条规则就得改这个函数**，越改越长。
4. **只在提交时检查**，用户填完最后一项才知道第一项错了。

这一节要解决的就是怎么把校验写“散”——散成一组可以单独测试、可以复用、能按字段组装的规则。

## 两种校验时机

先说什么时候校验，这决定了整个交互的体感。

| 时机 | 做法 | 优点 | 缺点 | 适用 |
| --- | --- | --- | --- | --- |
| **即时校验** | 每次 `input` 或 `blur` 就校验该字段 | 反馈快，用户边填边知道对不对 | 打字过程中频繁报错，干扰大 | 格式类字段：手机号、邮箱、日期 |
| **提交校验** | 只在点提交时校验全部字段 | 用户填写过程不受打扰 | 一次性冒出一堆错误，改起来要来回找 | 字段多、规则复杂的长表单 |
| **混合（推荐）** | 首次**提交时**全量校验；之后该字段**改动就校验** | 第一次不打扰，出错后改到哪提示到哪 | 需要记录“这个字段有没有被碰过” | 绝大多数业务表单 |

混合方式的关键是给每个字段一个“是否已被触碰过”的状态：

```js [src/composables/useFormValidation.js]
import { ref, computed } from 'vue'

export function useFormValidation(form, rules) {
  const errors = ref({}) // 字段 → 错误信息
  const touched = ref({}) // 字段 → 是否已被用户碰过

  // 校验单个字段，返回是否通过
  function validateField(field) {
    const fieldRules = rules[field] || []
    for (const rule of fieldRules) {
      const msg = rule(form.value[field])
      if (msg) {
        errors.value[field] = msg
        return false
      }
    }
    errors.value[field] = ''
    return true
  }

  // 全量校验：把所有字段标记为已触碰，一次性给出全部错误
  function validateAll() {
    let passed = true
    for (const field of Object.keys(rules)) {
      touched.value[field] = true
      if (!validateField(field)) passed = false
    }
    return passed
  }

  const hasError = computed(() => Object.values(errors.value).some(Boolean))

  return { errors, touched, validateField, validateAll, hasError }
}
```

在组件里这样用：

```vue [src/components/ActivityForm.vue]
<script setup>
import { ref } from 'vue'
import { useFormValidation } from '@/composables/useFormValidation'
import { required, maxLength, mobile, range } from '@/utils/validators'

const form = ref({
  title: '',
  capacity: '',
  contact: ''
})

const rules = {
  title: [required('活动标题'), maxLength(30, '活动标题')],
  capacity: [required('名额'), range(1, 500, '名额')],
  contact: [required('联系电话'), mobile()]
}

const { errors, touched, validateField, validateAll } = useFormValidation(form, rules)

// 用户改动时，只有“已经碰过”的字段才实时提示
function onFieldInput(field) {
  if (touched.value[field]) validateField(field)
}

// 用户离开字段时，先校验一次，之后再改动就实时提示
function onFieldBlur(field) {
  touched.value[field] = true
  validateField(field)
}
</script>

<template>
  <form @submit.prevent="submit">
    <label>活动标题</label>
    <input
      v-model="form.title"
      @input="onFieldInput('title')"
      @blur="onFieldBlur('title')"
    />
    <p v-if="errors.title" class="field-error">{{ errors.title }}</p>

    <label>名额</label>
    <input
      v-model.trim="form.capacity"
      @input="onFieldInput('capacity')"
      @blur="onFieldBlur('capacity')"
    />
    <p v-if="errors.capacity" class="field-error">{{ errors.capacity }}</p>

    <label>联系电话</label>
    <input
      v-model.trim="form.contact"
      @input="onFieldInput('contact')"
      @blur="onFieldBlur('contact')"
    />
    <p v-if="errors.contact" class="field-error">{{ errors.contact }}</p>

    <button type="submit">提交</button>
  </form>
</template>
```

效果是：用户第一次进来时安安静静；一旦某字段失焦校验失败，红字出现；
之后用户修改这个字段，提示会**跟着输入实时更新**，改对了就立刻消失。

::: warning 不要用 `input` 做“首次校验”
如果用 `@input="validateField('contact')"` 从一开始就校验手机号，用户才输入“1”就会看到
“请输入 11 位手机号”。**这类“还没填完就报错”的体验是表单被嫌弃的头号原因。**
判断标准很简单：**用户还没离开这个字段，就不要说他错。**
:::

## 错误信息怎么组织

这是一个设计决定，先想清楚再写代码。三种常见形态：

| 组织方式 | 数据结构 | 适合什么 | 不适合什么 |
| --- | --- | --- | --- |
| 每字段一条 | `{ title: '标题不能为空' }` | **绝大多数表单**，界面上每个字段下显示一条就够 | 需要同时展示多条候选提示 |
| 每字段一数组 | `{ title: ['不能为空', '不能超过 30 字'] }` | 密码强度这类需要**同时**给出多条提示的字段 | 简单表单，数组让取值变麻烦 |
| 表单级错误列表 | `{ _form: ['名额已满', '报名已截止'] }` | **接口返回的业务错误**，不属于某个字段 | 字段级校验 |

**决策依据：界面上要显示几条？**

- 每个字段下方只显示**一条**最关键的提示 → 用每字段一条（最省事，推荐从它开始）。
- 某个字段要同时显示好几条（类似密码要求的清单，勾掉一条少一条）→ 那个字段单独用数组，
  其他字段仍用字符串。
- 错误来自接口而且不对应具体字段（“该活动已下架”“名额已满”）→ 放表单级。

::: tip 一个折中的做法
先用“每字段一条”，但**留一个 `formError` 给表单级错误**。这样 90% 的场景够用，
剩下的 10% 也有地方放，不用重构：

```js
const errors = ref({}) // 字段级：{ title: '...' }
const formError = ref('') // 表单级：'当前活动已截止报名'
```
:::

## 规则怎么写：一组纯函数

校验规则的最优形态是**纯函数**：输入一个值，输出一条错误信息（或空字符串）。
不依赖组件、不依赖响应式、不依赖页面。

```js [src/utils/validators.js]
// 每条规则都是 (value) => errorMessage 的形式
// 返回 '' 表示通过，返回非空字符串表示不通过

export const required = (label) => (value) => {
  if (value === null || value === undefined || String(value).trim() === '') {
    return `${label}不能为空`
  }
  return ''
}

export const maxLength = (len, label) => (value) => {
  if (value && String(value).length > len) {
    return `${label}不能超过 ${len} 个字`
  }
  return ''
}

export const minLength = (len, label) => (value) => {
  if (value && String(value).length < len) {
    return `${label}至少 ${len} 个字`
  }
  return ''
}

// 正则类规则：为空时不报错，交给 required 处理
export const pattern = (re, message) => (value) => {
  if (!value) return ''
  return re.test(String(value)) ? '' : message
}

export const mobile = () =>
  pattern(/^1[3-9]\d{9}$/, '请输入 11 位手机号')

export const studentId = () =>
  pattern(/^\d{8,12}$/, '学号应为 8 到 12 位数字')

export const range = (min, max, label) => (value) => {
  if (value === '' || value === null || value === undefined) return ''
  const n = Number(value)
  if (Number.isNaN(n)) return `${label}必须是数字`
  if (n < min || n > max) return `${label}应在 ${min} 到 ${max} 之间`
  return ''
}

// 自定义规则：截止时间不能早于今天
export const notBeforeToday = (label) => (value) => {
  if (!value) return ''
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  if (new Date(value) < today) {
    return `${label}不能早于今天`
  }
  return ''
}
```

::: tip 为什么“为空就不校验格式”
注意 `pattern` 的第一行 `if (!value) return ''`。

如果不写这一行，空值会同时触发两条错误：“不能为空”和“格式不正确”。
而用户看到的应该是**最基础的那条**：你还没填。

**规则顺序上也配合这一点**：`required` 永远放在数组第一位。
:::

有了这组函数，规则表就变得非常直白：

```js [src/views/activity/rules.js]
import {
  required,
  maxLength,
  mobile,
  studentId,
  range,
  notBeforeToday
} from '@/utils/validators'

export const activityRules = {
  title: [required('活动标题'), maxLength(30, '活动标题')],
  type: [required('活动类型')],
  capacity: [required('名额'), range(1, 500, '名额')],
  deadline: [required('报名截止时间'), notBeforeToday('报名截止时间')],
  contact: [required('联系电话'), mobile()]
}

export const signupRules = {
  studentName: [required('姓名'), maxLength(20, '姓名')],
  studentId: [required('学号'), studentId()],
  phone: [required('手机号'), mobile()]
}
```

这张表就是**表单的说明书**。别人接手你的页面，看这张表就知道有哪些约束，不用去组件里翻 `if`。

::: tip 这组函数能直接写单元测试
因为它们是纯函数，所以不启动浏览器就能测：

```js [tests/validators.spec.js]
import { describe, it, expect } from 'vitest'
import { required, mobile, range } from '@/utils/validators'

describe('校验规则', () => {
  it('必填：空字符串不通过', () => {
    expect(required('标题')('')).toBe('标题不能为空')
  })
  it('手机号：13800000000 通过', () => {
    expect(mobile()('13800000000')).toBe('')
  })
  it('范围：超过上限给出提示', () => {
    expect(range(1, 500, '名额')('600')).toBe('名额应在 1 到 500 之间')
  })
})
```

单元测试在[单元 3](/unit03/)里讲过配置，这里只是顺带用一次。
:::

## 异步校验

有些规则必须问服务端，比如“活动标题是否已存在”“这个时段场地是否冲突”。这类校验有两个坑。

### 坑一：结果回来晚了，覆盖了新结果

用户在标题框里打字，每敲一次发一次请求。如果第一次请求比第二次慢，就会出现
“已经改成别的标题了，却提示重复”—— 旧结果盖住了新结果。

处理方式是**给每次请求编号，只认最新一次的结果**：

```js [src/composables/useTitleUnique.js]
import { ref } from 'vue'
import { checkActivityTitle } from '@/api/activity'

export function useTitleUnique() {
  const checking = ref(false)
  const error = ref('')
  let requestSeq = 0 // 请求序号

  async function check(title) {
    if (!title) {
      error.value = ''
      return
    }
    const current = ++requestSeq // 本次请求的序号
    checking.value = true
    try {
      const res = await checkActivityTitle(title)
      // 关键：如果又发起了新请求，本次结果作废
      if (current !== requestSeq) return
      error.value = res.exists ? '该标题已被占用，请换一个' : ''
    } finally {
      if (current === requestSeq) checking.value = false
    }
  }

  return { checking, error, check }
}
```

### 坑二：组件卸载了，请求还在飞

如果用户在请求返回前切走了页面，回来时可能看到一条“幽灵提示”。
更好的做法是用 `AbortController` 把上一个请求直接取消：

```js [src/composables/useTitleUnique.js（带取消）]
import { ref, onUnmounted } from 'vue'
import { checkActivityTitle } from '@/api/activity'

export function useTitleUnique() {
  const checking = ref(false)
  const error = ref('')
  let controller = null

  async function check(title) {
    // 取消上一次还没回来的请求
    controller?.abort()
    controller = new AbortController()

    if (!title) {
      error.value = ''
      return
    }

    checking.value = true
    try {
      const res = await checkActivityTitle(title, { signal: controller.signal })
      error.value = res.exists ? '该标题已被占用，请换一个' : ''
    } catch (e) {
      // 主动取消不算错误，忽略
      if (e.name !== 'CanceledError' && e.name !== 'AbortError') throw e
    } finally {
      checking.value = false
    }
  }

  // 组件卸载时把在途请求一起取消
  onUnmounted(() => controller?.abort())

  return { checking, error, check }
}
```

配合防抖使用，效果最好：

```vue [src/components/TitleField.vue]
<script setup>
import { ref, watch } from 'vue'
import { useTitleUnique } from '@/composables/useTitleUnique'

const title = ref('')
const { checking, error, check } = useTitleUnique()

let timer = null
watch(title, (val) => {
  clearTimeout(timer)
  // 停顿 400 毫秒再发请求，避免每敲一个字都请求一次
  timer = setTimeout(() => check(val.trim()), 400)
})
</script>

<template>
  <input v-model="title" />
  <p v-if="checking" class="hint">检查中……</p>
  <p v-else-if="error" class="field-error">{{ error }}</p>
</template>
```

::: warning 定时器也要清理
`timer` 如果不清理，组件卸载后回调仍会执行，可能触发一次多余的请求。
完整的清理写法（把 `clearTimeout` 放进 `onUnmounted`）在[6.5 生命周期](/unit06/05-lifecycle)展开。
:::

## 提交时的处理顺序

校验通过之后，提交本身有一套固定顺序，**顺序错了就会出现各种奇怪状态**。

```js [src/components/ActivityForm.vue]
async function submit() {
  // 第 1 步：防重复 —— 已经在提交中就直接返回
  if (submitting.value) return

  // 第 2 步：校验 —— 全量校验，不通过就停在这里
  const passed = validateAll()
  if (!passed) {
    // 可选：把焦点移到第一个出错的字段
    focusFirstError()
    return
  }

  // 第 3 步：置提交中，让按钮进入禁用 + 加载态
  submitting.value = true
  try {
    // 第 4 步：发请求
    await createActivity(toPayload(form.value))
    // 第 5 步：成功反馈
    message.success('活动已发布')
    router.push('/activities')
  } catch (e) {
    // 失败反馈：字段级错误还是表单级错误，分开处理
    if (e.response?.data?.field) {
      errors.value[e.response.data.field] = e.response.data.message
    } else {
      formError.value = e.message || '提交失败，请稍后重试'
    }
  } finally {
    // 第 6 步：无论成功失败，都要解除提交中
    submitting.value = false
  }
}
```

有四个细节值得单独说：

1. **`return` 要早**：校验不通过直接返回，不要“先把 `submitting` 设成 `true` 再校验”。
2. **`finally` 必须有**：只在成功分支里恢复按钮，一旦失败按钮会永远禁用。
3. **成功和失败分开提示**：字段级错误写回对应字段，表单级错误显示在顶部。
4. **成功之后才跳转**：不要先 `router.push` 再发请求。

## 重复提交的三层防护

“点两次提交，产生两条报名记录”是上线后最常见的事故。防护要分层写，**每一层都能独立挡住一类情况**。

| 层 | 做法 | 挡住什么 |
| --- | --- | --- |
| 第一层：按钮禁用 | `<button :disabled="submitting" :loading="submitting">` | 用户手快连点 |
| 第二层：函数内标志 | 函数开头 `if (submitting.value) return` | 键盘回车 + 点击同时触发 |
| 第三层：请求层拦截 | 同一请求取消上一次 / 服务端幂等 | 网络慢时用户刷新页面重试 |

```vue [src/components/SubmitButton.vue]
<script setup>
defineProps({
  submitting: { type: Boolean, default: false }
})
</script>

<template>
  <!-- ✓ 第一层：提交中既禁用又显示加载态 -->
  <button type="submit" :disabled="submitting">
    {{ submitting ? '提交中……' : '提交报名' }}
  </button>
</template>
```

::: danger 只做第一层是不够的
按钮禁用能挡住鼠标连点，但**挡不住键盘**：用户按一次回车触发 `submit`，
再按一次仍然会触发 —— 因为 `submit` 事件不是按钮发出的。

所以第二层的 `if (submitting.value) return` 不能省。**它才是真正的兜底。**
:::

第三层通常在请求层做，属于[单元 10 的请求层封装](/unit10/04-request-layer)的内容。
这里先记住思路：**同一个请求在完成后要能被识别**。常见做法有两种：

- 前端：发请求前把上一次同参数的请求取消掉。
- 服务端：给表单生成一个一次性令牌，服务端只接受一次（真正的兜底，因为客户端逻辑可以被绕过）。

## 小结

- 校验时机推荐**混合方式**：首次提交全量校验，之后被碰过的字段改动就实时校验。
- 用户**还没离开字段**时不要报错，这是表单体验的第一原则。
- 错误信息默认用**每字段一条**，预留一个 `formError` 放表单级错误。
- 规则写成**纯函数**（`(value) => 错误信息`），单独放一个文件，可复用可测试；
  数组里 `required` 永远放第一个。
- 异步校验要处理两件事：**只认最新一次请求的结果**、**组件卸载时取消在途请求**。
- 提交顺序：防重复 → 全量校验 → 置提交中 → 发请求 → 给反馈 → `finally` 里恢复状态。
- 重复提交要**三层防护**：按钮禁用、函数内标志、请求层拦截。

## 常见坑

::: details 坑 1：`submitting` 在失败分支没恢复，按钮永久禁用
**现象**：第一次提交失败（比如网络超时），之后按钮一直是灰的，刷新页面才能再用。

**原因**：恢复 `submitting` 的代码只写在成功分支里。

**处理**：把 `submitting.value = false` 放进 `finally`。**只要有一个“恢复状态”的动作，
它就应该在 `finally` 里。**
:::

::: details 坑 2：异步校验的结果顺序错乱
**现象**：把标题改成一个可用的值，过一会儿又冒出来“标题已占用”。

**原因**：第一次（重复的标题）的请求比第二次（可用的标题）慢，返回时覆盖了新结果。

**处理**：给请求编号，只接受最新一次的结果；或者用 `AbortController` 取消上一次请求。
**任何“输入触发请求”的场景都要处理这件事。**
:::

::: details 坑 3：`.number` 让“格式错误”悄悄通过
**现象**：名额字段填 `12abc`，提交成功，存进去的是 `12`。

**原因**：`v-model.number` 内部用 `parseFloat`，`12abc` 会被解析成 `12`，无法解析的部分被丢弃了。

**处理**：数字字段优先用 `type="number"`；同时用 `range` 这类规则校验值的范围，
不要只依赖类型转换。**校验值本身，不只校验类型。**
:::

::: details 坑 4：错误提示只显示在表单顶部，用户找不到是哪个字段
**现象**：提交后顶部出现“请检查表单”，用户逐个字段找，找了半分钟。

**原因**：错误信息都堆在一个容器里，没有和字段对应。

**处理**：错误提示放在**对应字段的正下方**，并且给错误字段加边框高亮。
再加一步“把焦点移到第一个错误字段”，用户就能立刻定位。
:::

::: details 坑 5：把 `touched` 忘在提交校验外面
**现象**：点提交没反应，也没看到错误提示。

**原因**：`validateAll()` 把错误写进了 `errors`，但模板上写着
`v-if="touched.title && errors.title"`，而 `touched.title` 还是 `false`。

**处理**：`validateAll()` 里必须同时把字段标记为已触碰（前面的实现里已经这么做了）。
**“有错误”和“要不要显示这个错误”是两件事，别让后者挡住前者。**
:::

## 课后练习

::: details 练习 1：把一团 if 拆成规则
把本节开头那段 `submit` 里的四条判断改写成规则函数，并组装成 `activityRules`：

- 标题必填、不超过 30 个字
- 名额必填、1 到 500 之间
- 联系电话必填、必须是 11 位手机号
- 报名截止时间必填、不能早于今天

**参考思路**：直接复用 `src/utils/validators.js` 里的函数，不用自己再写。
写完检查顺序：`required` 是不是每条的第一位？为空时会不会同时报两条错？

:::

::: details 练习 2：给报名表单加上混合校验
给下面的表单加校验，要求：

- 首次进入不报错
- 每个字段失焦时校验一次
- 之后改动该字段实时更新提示
- 点提交时校验全部字段，不通过时把焦点移到第一个错误字段

```js
const form = ref({ studentName: '', studentId: '', phone: '' })
```

**参考思路**：`touched` 是这套机制的核心。焦点移动可以用模板引用：
给每个 `input` 一个 `ref`，按 `rules` 的字段顺序找第一个有错误的字段并调用 `.focus()`。
模板引用在[6.5](/unit06/05-lifecycle)会讲。

:::

::: details 练习 3：设计一个异步校验
“同一个场地、同一时段的场次不能重叠”这条规则需要问服务端。写出它的实现要点：

1. 用户改动时间时怎么触发
2. 怎么避免每改一次就请求一次
3. 怎么处理“旧结果覆盖新结果”
4. 组件卸载时怎么办

**参考思路**：这题不要求写完整代码，要求把四点各写两三句。
写完之后问自己：**如果服务端返回得很慢（3 秒），我的方案会不会出问题？**

:::

---

上一节：[6.3 表单绑定](/unit06/03-form-binding) ·
下一节：[6.5 生命周期与副作用清理](/unit06/05-lifecycle)
