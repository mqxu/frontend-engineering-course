# 5. 组件与组件库

## 一个具体的场面

要做一个报名表单：四个输入项、一个提交按钮、校验规则、错误提示、提交中的禁用态、成功后的提示。

如果从零写，你要处理这些事：每个输入框的标签布局、聚焦态、错误信息的显示与清空、按钮的加载态、Toast 的显示与自动隐藏、软键盘弹起时页面被顶上去……**光输入框的样式就要写两百行，而且大概率做得不如组件库稳。**

这一节讲怎么用组件库把这些活省下来，以及**为什么 uni-app 里连 import 都不用写。**

## 一、easycom：不用 import 的组件

管理端用 Element Plus 时，每个页面开头都有一串 import。uni-app 里不用 —— 前提是配了 easycom。

```json [src/pages.json]
{
  "easycom": {
    "autoscan": true,
    "custom": {
      "^wd-(.*)": "@wot-ui/ui/components/wd-$1/wd-$1.vue"
    }
  }
}
```

这条规则的意思是：**模板里凡是 `<wd-` 开头的标签，编译器按这个路径去找组件文件。**

```vue
<template>
  <!-- 不用 import，不用注册，直接写 -->
  <wd-button type="primary">提交</wd-button>
</template>
```

::: warning 文档里的导入路径和你的项目不一样
Wot UI 支持两种安装方式，**它们写代码时的路径不同**：

| 安装方式 | 组件的引用路径 |
| --- | --- |
| uni_modules（把组件源码拷进 `src/uni_modules/`） | `@/uni_modules/wot-ui` |
| **npm 安装（本项目用的）** | `@wot-ui/ui` |

**官方文档的例子默认是按 uni_modules 写的**，所以你照着文档抄 `import { useToast } from '@/uni_modules/wot-ui'` 会报错。看到 `@/uni_modules/wot-ui` 就换成 `@wot-ui/ui`。

两种方式的差别：uni_modules 不用配置 easycom（天然支持），但升级时要处理代码差异；npm 要配 easycom，但升级只改 `package.json` 里的版本号。**工程化项目用 npm 更合适**，这也是本项目选它的原因。
:::

## 二、这一端会用到的组件

组件库有 100 来个组件，**不用都学**。按用户端的 5 个页面，实际用到的就这些：

| 分类 | 组件 | 用在哪 |
| --- | --- | --- |
| 基础 | `wd-button` | 提交、报名、取消 |
| | `wd-cell` / `wd-cell-group` | 表单外层、个人中心的信息行 |
| | `wd-divider` | 分节 |
| 表单 | `wd-form` / `wd-form-item` | 报名表单、登录表单 |
| | `wd-input` / `wd-textarea` | 输入框 |
| 展示 | `wd-tag` | 活动类型、报名状态 |
| | `wd-card` | 活动卡片（也可以自己写） |
| | `wd-empty` | 空状态 |
| | `wd-skeleton` | 加载骨架 |
| | `wd-loadmore` | 触底加载的状态提示 |
| | `wd-img` | 活动封面图（自带懒加载与错误兜底） |
| | `wd-steps` | 报名流程说明（选做） |
| 交互 | `wd-search` | 活动列表搜索 |
| | `wd-popup` | 底部弹出的筛选面板 |
| | `wd-action-sheet` | 操作菜单（取消报名等） |
| | `wd-toast` | 轻提示 |
| | `wd-dialog` | 二次确认 |

**建议先只装这十几个的用法**，其他组件用到再查。

## 三、表单：模型加规则

Wot UI 的表单思路和 Element Plus 不一样，**它是 `model` 加 `schema` 两个对象**。

```vue
<template>
  <wd-form ref="form" :model="model" :schema="schema">
    <wd-cell-group border>
      <wd-form-item title="姓名" prop="studentName">
        <wd-input v-model="model.studentName" placeholder="请输入真实姓名" clearable />
      </wd-form-item>

      <wd-form-item title="学号" prop="studentNo">
        <wd-input v-model="model.studentNo" placeholder="请输入 10 位学号" clearable />
      </wd-form-item>

      <wd-form-item title="班级" prop="studentClass">
        <wd-input v-model="model.studentClass" placeholder="例如：软件 2301" clearable />
      </wd-form-item>

      <wd-form-item title="备注" prop="remark">
        <wd-textarea
          v-model="model.remark"
          placeholder="有什么想说的可以写在这里（选填）"
          :maxlength="200"
          show-word-limit
          clearable
        />
      </wd-form-item>
    </wd-cell-group>

    <view class="footer">
      <wd-button type="primary" size="large" block :loading="submitting" @click="handleSubmit">
        提交报名
      </wd-button>
    </view>
  </wd-form>
</template>
```

三个绑定点：

| 地方 | 写什么 | 说明 |
| --- | --- | --- |
| `wd-form` 的 `:model` | 表单数据对象 | 一个 `reactive` 对象 |
| `wd-form` 的 `:schema` | 校验规则 | 见下 |
| `wd-form-item` 的 `prop` | 字段名 | **要和 model 里的键名一致** |
| `wd-form-item` 的 `title` | 标签文字 | **注意不是 `label`** |

**`title` 这一条容易踩。** Element Plus 用 `label`，Wot UI 用 `title`。写 `label="姓名"` 不会报错，只是标签不显示。

### 校验规则：两种写法

**写法一：用 zod 定义，组件库提供适配器。**

```bash
pnpm add zod
```

```js [src/pages/signup/form.vue]
import { reactive, ref } from 'vue'
import { z } from 'zod'
import { zodAdapter, useToast } from '@wot-ui/ui'

const model = reactive({
  studentName: '',
  studentNo: '',
  studentClass: '',
  remark: ''
})

const schema = zodAdapter(
  z.object({
    studentName: z.string().min(1, '请填写姓名').max(20, '姓名不超过 20 个字'),
    studentNo: z
      .string()
      .regex(/^\d{10}$/, '学号是 10 位数字'),
    studentClass: z.string().max(30, '班级不超过 30 个字').optional(),
    remark: z.string().max(200, '备注不超过 200 个字').optional()
  })
)
```

**zod 是一个独立的校验库，需要单独装**（组件库为了控制体积没有内置它）。它用方法链描述规则，读起来接近自然语言。

**写法二：自己写一个校验函数。**

不想引入 zod 的话，按组件库约定的结构手写也行：

```js
const schema = {
  // 返回所有没通过的项，每项含 path 和 message
  validate(formModel) {
    const issues = []
    if (!formModel.studentName) {
      issues.push({ path: ['studentName'], message: '请填写姓名' })
    }
    if (!/^\d{10}$/.test(formModel.studentNo)) {
      issues.push({ path: ['studentNo'], message: '学号是 10 位数字' })
    }
    return issues
  },
  // 只影响标签前的红星显示，不影响校验结果
  isRequired(path) {
    return path === 'studentName' || path === 'studentNo'
  }
}
```

::: tip 两种怎么写
**zod 的写法更短，规则和提示文字挨在一起，改起来直观。** 手写 `validate` 的写法依赖少，规则复杂时（比如跨字段校验、要查后端接口）自由度更高。

本项目的报名表单字段不多，**推荐用 zod**。字段多、规则又互相牵扯时，手写可能更清楚。
:::

### 提交：拿到表单实例调 validate

```js
const form = ref(null)
const submitting = ref(false)
const toast = useToast()

async function handleSubmit() {
  const { valid } = await form.value.validate()
  if (!valid) return

  submitting.value = true
  try {
    await createSignup({ ...model })
    toast.success('报名已提交，等待审核')
    uni.switchTab({ url: '/pages/signup/my' })
  } catch (err) {
    toast.error(err.message || '提交失败，请稍后重试')
  } finally {
    submitting.value = false
  }
}
```

`validate()` 返回一个 Promise，解出来是 `{ valid, errors }`。**它不抛异常，所以要用 `valid` 判断**，别写成 `try/catch` 包住校验。

`submitting` 这个变量有两个作用：**给按钮的 `:loading` 传值**（转圈，同时禁用点击），**在提交中的重复点击时提前返回**。这是防重复提交的标准做法，和管理端一样。

## 四、Toast 和 Dialog 要写在模板里

这是 uni-app 平台的一个限制，**很多人第一次会遇到**：

```vue
<template>
  <view class="page">
    <!-- 页面内容 -->
    <wd-button @click="handleSignup">报名</wd-button>

    <!-- 必须显式写这两个标签，否则调用了也没反应 -->
    <wd-toast />
    <wd-dialog />
  </view>
</template>
```

```js
import { useToast, useDialog } from '@wot-ui/ui'

const toast = useToast()
const dialog = useDialog()

toast.success('报名成功')
toast.error('名额已满')

async function confirmCancel() {
  const ok = await dialog.confirm({
    title: '确认取消报名',
    msg: '取消后需要重新报名，确定吗？'
  })
  if (ok) {
    // 执行取消
  }
}
```

**为什么必须在模板里写标签？** uni-app 不支持全局挂载组件，Toast 和 Dialog 也是普通组件，得有个地方渲染它们。写在根 `<view>` 里，它们就跟着页面一起渲染了。

**漏写标签的症状是“点了按钮什么都没发生”，控制台也不一定报错。** 遇到这个先检查标签写了没。

## 五、自己写组件：活动卡片

组件库给的是基础件，业务组件还得自己写。用户端第一个自定义组件是活动卡片。

```vue [src/components/activity-card.vue]
<script setup>
const props = defineProps({
  activity: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['click'])

// 类型标签的颜色，用组件库的主题色
const typeMap = {
  LECTURE: { label: '讲座', type: 'primary' },
  COMPETITION: { label: '比赛', type: 'warning' },
  PERFORMANCE: { label: '演出', type: 'success' },
  SPORTS: { label: '体育', type: 'danger' },
  VOLUNTEER: { label: '志愿服务', type: 'success' },
  OTHER: { label: '其他', type: 'default' }
}

const typeInfo = computed(() => typeMap[props.activity.type] || typeMap.OTHER)
const remaining = computed(() => props.activity.quota - props.activity.approvedCount)
const isFull = computed(() => remaining.value <= 0)
</script>

<template>
  <view class="card" @tap="emit('click', activity.id)">
    <view class="card-head">
      <text class="card-title">{{ activity.title }}</text>
      <wd-tag :type="typeInfo.type" plain>{{ typeInfo.label }}</wd-tag>
    </view>

    <view class="card-meta">
      <text>报名截止 {{ activity.signupDeadline }}</text>
    </view>

    <view class="card-foot">
      <text :class="['quota', { 'quota-full': isFull }]">
        {{ isFull ? '名额已满' : `还剩 ${remaining} 个名额` }}
      </text>
    </view>
  </view>
</template>
```

三个要点：

**一、`defineProps` 里写 `required: true` 和类型。** 少写不会报错，但组件被别人误用时也没有提示。**在管理端你已经养成了写全的习惯，这里保持。**

**二、用 `@tap` 而不是 `@click`。** 两者在手机上都会触发，`@tap` 的响应更贴合触屏的判定规则，**官方推荐用 `@tap`**。混用不会出错，但一个项目里统一更好。

**三、子组件不直接改 `props`。** 上面卡片只负责显示，点击时把 `id` 通过事件抛给父组件，由父组件决定怎么跳转。**这是单向数据流，和管理端的要求完全一样。**

::: details 自定义组件放哪、怎么被引用
放在 `src/components/` 下。**在 uni-app 里引用自定义组件要显式 import**（easycom 只管组件库那种命名规则的组件，不管你的业务组件）：

```vue
<script setup>
import ActivityCard from '@/components/activity-card.vue'
</script>

<template>
  <ActivityCard
    v-for="item in list"
    :key="item.id"
    :activity="item"
    @click="goDetail"
  />
</template>
```

如果你想让自己写的组件也走 easycom 自动引入，可以在 `pages.json` 里再加一条规则：

```json
"custom": {
  "^wd-(.*)": "@wot-ui/ui/components/wd-$1/wd-$1.vue",
  "^App(.*)": "@/components/app-$1.vue"
}
```

**本项目不建议这么做** —— 业务组件的显式 import 让依赖关系一眼可见，比省两行代码更重要。
:::

## 六、换掉默认的蓝色

组件库默认是蓝色主题，和校园活动的场景不太搭。改主色有两种做法。

**做法一：覆盖 CSS 变量（推荐，改一处全局生效）。**

```css [src/App.vue]
/* 注意这里不能加 scoped */
page {
  /* 主色与它的色阶，6 是主色，1 到 5 是从浅到深 */
  --wot-primary-6: #42b883;
  --wot-primary-5: #5ac394;
  --wot-primary-7: #359e6f;
  --wot-primary-4: #8ed5b5;
  --wot-primary-3: #b8e5cf;
}
```

**主色是 `--wot-primary-6`，但只改这一个不够** —— 按钮的按下态用 5 或 7，浅色背景用 3 或 4。**要完整改一套就把 1 到 10 都定义一遍**，或者接受“只有主色变了，浅深色阶还是原来的蓝”。

**做法二：用 `wd-config-provider` 组件包一层。**

```vue
<template>
  <wd-config-provider :theme-vars="{ primary6: '#42b883' }">
    <!-- 页面内容 -->
  </wd-config-provider>
</template>
```

用这个组件可以把主题限定在某个范围内（比如首页和登录页用不同主题）。**本项目全局一套色就够，用做法一更简单。**

## 小结

- easycom 让组件不用 import，**改完这个配置要手动触发一次编译才生效**
- 官方文档的例子按 uni_modules 写，**npm 安装的项目要把 `@/uni_modules/wot-ui` 换成 `@wot-ui/ui`**
- `wd-form` 用 `model` 加 `schema`，**`wd-form-item` 的标签属性是 `title` 不是 `label`**，字段名靠 `prop` 绑定
- 校验规则可以用 `zodAdapter` 配 zod，**zod 要单独装**；字段少时手写 `validate` 也很清楚
- 提交用 `ref` 拿表单实例调 `validate()`，**它返回 `{ valid, errors }` 而不是抛异常**
- **`<wd-toast />` 和 `<wd-dialog />` 必须显式写在页面模板里**，否则调了没反应
- 主色变量是 `--wot-primary-6`，**配套色阶 1 到 10 一起改才完整**

## 常见坑

::: details 调了 `useToast()` 但页面上什么都不弹

**现象：** 点击按钮，代码执行了，Toast 不出现。控制台没有报错。

**原因：** 页面模板里没有写 `<wd-toast />`。uni-app 不支持全局挂载组件，没有这个标签就没有渲染的载体。

**怎么处理：** 在页面根元素里加上：

```vue
<template>
  <view>
    <!-- 页面内容 -->
    <wd-toast />
  </view>
</template>
```

**注意要写在 `<template>` 的最外层 `<view>` 里，不要写在 `<view>` 外面** —— 一个组件的模板只能有一个根节点。

:::

::: details 校验规则写了，提交时完全不校验

**现象：** 表单能提交，`studentName` 是空的也照样通过。

**原因：** 三种可能：

1. **`wd-form-item` 的 `prop` 写错了**，和 `model` 的键名对不上 —— 校验靠 `prop` 找到对应的规则，找不到就跳过
2. **`validate()` 的返回值没用对**，写成 `try/catch` 了
3. **`schema` 里的字段名写错了**，比如 `validate` 里判断的是 `formModel.name`，而实际字段是 `studentName`

**怎么处理：** 先检查 `prop` 和 `model` 的键名是否逐字一致（**这里的大小写错误最难发现**）。然后在 `validate()` 后面打印结果：

```js
const res = await form.value.validate()
console.log('校验结果：', JSON.stringify(res))
// { valid: false, errors: [{ prop: 'studentNo', message: '学号是 10 位数字' }] }
```

**`errors` 是空的而 `valid` 是 `false`，说明规则没被匹配上**，回去查 `prop`。

:::

::: details `@click` 和 `@tap` 混用，某个端上点两次触发一次

**现象：** 有的事件处理器在小程序端被触发了两次，或者反过来，某些地方点了没反应。

**原因：** 在移动端，`@click` 会经过浏览器的点击延迟与合成逻辑，`@tap` 是原生触摸判定。**两者在某些场景下会叠加触发。**

**怎么处理：** **一个项目里统一用 `@tap`。** 已有的管理端代码是 `@click`，那是 Web 项目，不受影响；用户端这一侧统一改过来。要批量改的话，注意**组件自定义事件不能用 `@tap`**（比如 `<ActivityCard @click="...">` 里的 `click` 是你 `defineEmits` 声明的事件名，和触摸无关，保持 `click`）。

:::

::: details 表单在软键盘弹起时被顶得看不见

**现象：** 点输入框，软键盘弹出来，输入框被键盘挡在后面。

**原因：** 微信小程序会自己调整页面高度，但**如果输入框在页面的下半部分，或者外层用了固定定位**，调整后仍然可能被挡住。

**怎么处理：** 三个办法按优先级试：

1. **控制表单长度**，把输入项压在屏幕上半部分能放下的范围内
2. **输入框加 `adjust-position` 相关配置**，或者用 `cursor-spacing` 留出键盘与输入框的距离
3. **把输入项放在弹层里**（`wd-popup` 从底部弹起），弹出层会自动避开键盘

**这一条没法在模拟器里准确验证**，要用开发者工具的“预览”在真机上看。

:::

## 课后练习

**做一个活动卡片组件和一个报名表单页，两个都可复用。**

| 任务 | 要求 |
| --- | --- |
| 活动卡片 | 显示标题、类型标签、报名截止时间、剩余名额；名额为 0 时显示“名额已满”并变红 |
| 卡片事件 | 点击卡片把 `id` 抛给父组件，组件内部不做任何跳转 |
| 报名表单 | 4 个字段（姓名、学号、班级、备注），姓名与学号必填，学号 10 位数字 |
| 校验 | 用 `zodAdapter` 配 zod |
| 提交 | 按钮有加载态，提交中不可重复点击；成功后 Toast 提示并跳转 |
| 主题 | 把主色改成 `#42b883`，验证按钮、标签的颜色都跟着变了 |
| 不许做的 | 不要真的调接口，用一个延时 1 秒的假请求代替 |

::: details 验收标准与参考思路

**验收标准：**

| 项 | 要求 |
| --- | --- |
| 校验 | 空着姓名点提交，标签下方出现红字提示；输入后提示自动消失 |
| 学号 | 输入 `123` 点提交，提示“学号是 10 位数字”；输入 10 位数字通过 |
| 加载态 | 点提交后按钮变转圈，1 秒内再点不触发第二次提交 |
| 主题 | 提交按钮是绿色（`#42b883`），不是默认蓝 |
| 名额 | 把假数据的 `quota` 改成和 `approvedCount` 相等，卡片显示“名额已满”且文字变红 |
| 两个端 | H5 与微信小程序端都验证一遍 |

**不合格的写法：**

```js
// ✗ 校验和提交混在一起，用 try/catch 判断校验结果
async function handleSubmit() {
  try {
    await form.value.validate()
    await createSignup(model)
  } catch (e) {
    toast.error('请检查填写内容')
  }
}
```

问题在于：**`validate()` 不抛异常。** 校验失败时它正常 resolve，返回 `valid: false`，这段代码会带着没填完的数据继续提交。

**另一个常见的不合格写法：**

```vue
<!-- ✗ 卡片内部自己跳转，父组件无法控制 -->
<view @tap="uni.navigateTo({ url: '/pages/activity/detail?id=' + activity.id })">
```

卡片组件一旦自己跳转，就没法在别的地方复用它做别的事（比如在“我的报名”里点卡片应该跳到报名记录详情）。**抛事件给父组件，是让组件可复用的前提。**

**合格的写法：**

```js
const form = ref(null)
const submitting = ref(false)
const toast = useToast()

async function handleSubmit() {
  if (submitting.value) return          // 双保险：即使按钮没禁用住也不会重复提交

  const { valid } = await form.value.validate()
  if (!valid) return                     // 校验不通过，直接结束，不抛异常

  submitting.value = true
  try {
    await fakeCreateSignup({ ...model })
    toast.success('报名已提交')
    setTimeout(() => uni.switchTab({ url: '/pages/signup/my' }), 800)
  } catch (err) {
    toast.error(err.message || '提交失败')
  } finally {
    submitting.value = false
  }
}
```

**注意 `submitting.value` 在 `finally` 里复位** —— 成功和失败都要恢复按钮状态，否则失败一次之后按钮永远转圈。

**参考思路：**

两个地方值得多花点时间：

**一是主题定制后要通盘看一遍。** 只改 `--wot-primary-6` 的话，按钮的按下态、标签的浅色背景还是旧的蓝色，视觉上会打架。**至少把 3 到 7 这几个色阶都改掉。**

**二是“名额已满”这个状态要在三个地方一致。** 卡片上显示、详情页的按钮状态、提交时的错误处理（后端会返回名额已满的错误码）。**前端判断是为了体验，真正的判定在后端** —— 这一点在下一篇的请求层里会再讲一次。

:::

---

上一节：[布局与样式](/mobile/04-layout-style) ·
下一节：[请求封装与登录态](/mobile/06-request-auth)
