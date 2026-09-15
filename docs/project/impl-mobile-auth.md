# 用户端 · 登录与登录态参考实现

这一页是**用户端**登录部分的参考实现。管理端的[登录与鉴权](/project/impl-auth)已经讲过一遍思路，这一页讲用户端不同的地方。

**先读三份文档再动手**：[用户端需求规格](/project/mobile) 里有页面清单与字段，[接口约定](/project/api) 的第十章是学生端接口，[用户端 · 请求封装与登录态](/mobile/06-request-auth) 讲了请求层怎么搭。

## 一、范围与页面

登录在用户端不是一个独立模块，它混在几个页面里：

| 页面 | 路由 | 需要登录 | 有没有登录相关的东西 |
| --- | --- | --- | --- |
| 活动列表 | `pages/activity/list` | 否 | 无 |
| 活动详情 | `pages/activity/detail` | 否 | 点报名按钮时触发登录判断 |
| 报名表单 | `pages/signup/form` | 是 | `onLoad` 里判断，未登录直接退回 |
| 我的报名 | `pages/signup/my` | 是 | `onLoad` 里判断 |
| 我的 | `pages/user/index` | 是 | 显示登录态、退出登录入口 |
| 登录 | `pages/login/index` | 否 | 账号密码加微信一键登录 |

**和管理端的最大差别：登录页不在 tabBar 里，也不在启动路径上。**

管理端一打开就是登录页；用户端一打开是活动列表，**登录发生在“用户想报名的那一刻”**。这个设计决定了后面所有代码的组织方式 —— 没有全局守卫，判断散在需要的地方。

## 二、涉及的文件

| 文件 | 职责 |
| --- | --- |
| `src/utils/request.js` | 请求封装、自动带 token、401 处理 |
| `src/utils/auth.js` | 登录判断、`ensureLogin`、登录态读写 |
| `src/api/auth.js` | 登录、退出、获取当前用户 |
| `src/pages/login/index.vue` | 登录页 |
| `src/pages/user/index.vue` | 我的（显示与退出） |
| `src/main.js` | 注入 401 处理器 |

**注意没有 store 文件夹。** 用户端的状态比管理端简单得多：token 和 userInfo 存在 storage 里，用工具函数读写就够了，**不必引入 Pinia**。

::: tip 什么情况下才需要引入 Pinia
如果出现这两种情况之一，可以考虑：

1. 同一份数据要**同时**在三个以上页面里响应式地更新（比如“报名成功后，我的报名列表和详情页的名额都要立刻变”）
2. 需要跨页面共享复杂状态（购物车这类）

用户端目前没有这种需求 —— 各页面自己请求自己的数据，**用 storage 加工具函数更轻，也更好排查。**

**不要因为“管理端用了 Pinia”就在这里也装一个。** 技术选型跟着需求走，不跟着习惯走。
:::

## 三、请求层

请求层的完整代码在[第 6 篇](/mobile/06-request-auth)里，这里只列出用户端特有的两处。

### 3.1 基础路径

```js [src/utils/request.js]
// 不带 /api 前缀，请求层统一补
const BASE_URL = '/api'
```

开发环境由 `vite.config.js` 的 `server.proxy` 转发到 `localhost:8080`，生产环境由 Nginx 转发。**两个环境的代码完全一样**，和管理端的约定一致。

### 3.2 401 的注入

```js [src/main.js]
import { createSSRApp } from 'vue'
import App from './App.vue'
import { setUnauthorizedHandler } from '@/utils/request'

export function createApp() {
  const app = createSSRApp(App)

  setUnauthorizedHandler(() => {
    clearLoginState()
    uni.showToast({ title: '登录已过期，请重新登录', icon: 'none' })
    setTimeout(() => {
      uni.navigateTo({ url: '/pages/login/index' })
    }, 800)
  })

  return { app }
}
```

**为什么用注入而不是直接 import？** 和单元 10 讲过的坑同源：`main.js` 执行时应用还没挂载完，在模块顶层做需要运行时环境的事会出问题。**把依赖注入进来，模块之间不反向依赖。**

## 四、登录态：存什么、存哪

```js [src/utils/auth.js]
const TOKEN_KEY = 'token'
const USER_KEY = 'userInfo'

export function getToken() {
  return uni.getStorageSync(TOKEN_KEY) || ''
}

export function getUserInfo() {
  return uni.getStorageSync(USER_KEY) || null
}

export function isLoggedIn() {
  return !!getToken()
}

export function saveLoginState(token, userInfo) {
  uni.setStorageSync(TOKEN_KEY, token)
  if (userInfo) {
    uni.setStorageSync(USER_KEY, userInfo)
  }
}

export function clearLoginState() {
  uni.removeStorageSync(TOKEN_KEY)
  uni.removeStorageSync(USER_KEY)
}

/**
 * 需要登录的操作前调用。未登录则提示并跳登录页，返回 false
 */
export function ensureLogin() {
  if (isLoggedIn()) return true
  uni.showToast({ title: '请先登录', icon: 'none' })
  setTimeout(() => {
    uni.navigateTo({ url: '/pages/login/index' })
  }, 600)
  return false
}
```

### 为什么 token 和 userInfo 分开存

`token` 是请求层每次都要读的；`userInfo` 主要是报名表单预填用。分开存的好处是**退出登录和登录过期时可以只清 token 保留一部分信息**（本项目两个一起清，但结构上留了余地）。

### 关于 token 的安全性

**前端存 token 没有绝对安全的位置。** 小程序的 storage 相对隔离，但包被反编译后结构可见；H5 端就是 `localStorage`，XSS 就能读。

**用户端要做的只有三件事**：不要 `console.log` 打印 token、不要拼进 URL、不要写进代码。剩下的靠服务端 —— 短有效期、关键操作二次校验、异常登录检测。

**这一条对应单元 9 的结论：前端的判断不是安全边界。**

## 五、登录页

### 5.1 两种登录方式的呈现

```vue [src/pages/login/index.vue]
<template>
  <view class="page">
    <view class="brand">
      <text class="brand-title">校园活动</text>
      <text class="brand-sub">用微信一键登录，或使用学号登录</text>
    </view>

    <!-- #ifdef MP-WEIXIN -->
    <!-- 小程序端：主入口是微信一键登录 -->
    <view class="block">
      <wd-button type="primary" size="large" block :loading="weixinLoading" @click="handleWeixinLogin">
        微信一键登录
      </wd-button>
    </view>

    <view class="divider">
      <wd-divider>或使用学号登录</wd-divider>
    </view>
    <!-- #endif -->

    <wd-form ref="form" :model="model" :schema="schema">
      <wd-cell-group border>
        <!-- #ifdef H5 -->
        <wd-form-item title="账号" prop="username">
          <wd-input v-model="model.username" placeholder="请输入账号" clearable />
        </wd-form-item>
        <!-- #endif -->

        <!-- #ifdef MP-WEIXIN -->
        <wd-form-item title="学号" prop="username">
          <wd-input v-model="model.username" type="number" placeholder="请输入学号" clearable />
        </wd-form-item>
        <!-- #endif -->

        <wd-form-item title="密码" prop="password">
          <wd-input v-model="model.password" show-password clearable placeholder="请输入密码" />
        </wd-form-item>
      </wd-cell-group>
    </wd-form>

    <view class="block">
      <wd-button type="primary" size="large" block :loading="loading" @click="handlePasswordLogin">
        登录
      </wd-button>
    </view>

    <wd-toast />
  </view>
</template>
```

**条件编译在这里有实际用处**：小程序端的账号就是学号（学生不会记另一个账号），H5 端调试时用管理端那套账号方便。**这不是为了炫技，是两端的实际使用习惯不同。**

### 5.2 账号密码登录

```js
import { reactive, ref } from 'vue'
import { z } from 'zod'
import { zodAdapter, useToast } from '@wot-ui/ui'
import { loginByPassword } from '@/api/auth'
import { saveLoginState } from '@/utils/auth'

const toast = useToast()
const form = ref(null)
const loading = ref(false)
const weixinLoading = ref(false)

const model = reactive({ username: '', password: '' })

const schema = zodAdapter(
  z.object({
    username: z.string().min(1, '请输入账号'),
    password: z.string().min(6, '密码至少 6 位')
  })
)

async function handlePasswordLogin() {
  if (loading.value) return
  const { valid } = await form.value.validate()
  if (!valid) return

  loading.value = true
  try {
    const res = await loginByPassword({ ...model })
    saveLoginState(res.token, res.userInfo)
    toast.success('登录成功')
    setTimeout(() => backToPrev(), 600)
  } catch (err) {
    // 登录失败的具体原因由后端给，直接用它的文案
    if (err.code !== 1001) {
      toast.error(err.message || '登录失败')
    }
  } finally {
    loading.value = false
  }
}
```

**注意 `catch` 里那行判断。** `1001`（未登录）是请求层统一处理跳登录页的码，登录接口本身返回 `1001` 表示“账号或密码错误”时会有点绕。**这种情况要和后端约定清楚**：登录接口的失败用 `1003`（参数校验失败）而不是 `1001`，避免请求层误跳登录页。

### 5.3 微信一键登录

```js
// #ifdef MP-WEIXIN
async function handleWeixinLogin() {
  if (weixinLoading.value) return
  weixinLoading.value = true
  try {
    // 第一步：拿临时 code，这一步不涉及后端
    const { code } = await new Promise((resolve, reject) => {
      uni.login({
        provider: 'weixin',
        success: (res) => (res.code ? resolve(res) : reject(new Error('未拿到 code'))),
        fail: () => reject(new Error('微信授权失败'))
      })
    })

    // 第二步：把 code 发给后端，后端去换 openid 并签发自己的 token
    const res = await loginByWeixin(code)
    saveLoginState(res.token, res.userInfo)

    // 首次登录的学生还没填过学号，引导去补全
    if (!res.userInfo.studentNo) {
      uni.showModal({
        title: '还需要补充信息',
        content: '第一次使用需要填写学号和班级，报名时会用到',
        showCancel: false,
        success: () => uni.navigateTo({ url: '/pages/user/profile' })
      })
      return
    }

    toast.success('登录成功')
    setTimeout(() => backToPrev(), 600)
  } catch (err) {
    toast.error(err.message || '微信登录失败')
  } finally {
    weixinLoading.value = false
  }
}
// #endif
```

::: danger 关于那段“补充信息”
**`uni.login()` 只给你一个 `code`，它拿不到姓名和学号。** 微信的用户信息接口能拿到的信息非常有限（昵称和头像也受限制），**学号必须让学生自己填。**

**不要试图让用户填姓名。** 报名记录里的姓名应该取登录用户的信息 —— 让学生自己填，等于允许他随便写，审核就失去了意义。所以报名表单里**姓名是预填且不可改的**（或者只能由学生在“资料”页改，改的时候留下记录）。
:::

### 5.4 登录成功后回哪儿

```js
function backToPrev() {
  const pages = getCurrentPages()
  if (pages.length > 1) {
    // 有上一页，退回去（用户是从报名按钮过来的）
    uni.navigateBack()
  } else {
    // 直接打开登录页的（比如过期后自动跳来），回首页
    uni.switchTab({ url: '/pages/activity/list' })
  }
}
```

**`getCurrentPages()` 返回页面栈数组**，长度大于 1 说明有来源页。这一段让“从报名按钮来”的用户登录完直接回到原来的位置，不用重新找一遍活动。

**注意 `navigateBack` 之后，来源页需要重新判断登录态。** 如果那一页在 `onLoad` 里判断过，`navigateBack` 回去不会重新触发 —— 因为它没有被销毁。**所以报名这种操作要用 `ensureLogin()` 在点击时判断，而不是只在 `onLoad` 里判断。**

## 六、登录判断放哪

用户端没有全局路由守卫。三个位置按场景选：

### 位置一：点击时判断（推荐）

```js
// 详情页的报名按钮
function handleSignup() {
  if (!ensureLogin()) return
  uni.navigateTo({ url: '/pages/signup/form?activityId=' + activity.value.id })
}
```

**这是最可靠的位置** —— 用户在真正要做需要登录的事的那一刻被拦下，回来的路径也最自然。

### 位置二：页面 `onLoad` 判断（整页需要登录时）

```js
// 我的报名页
onLoad(() => {
  if (!isLoggedIn()) {
    uni.showToast({ title: '请先登录', icon: 'none' })
    setTimeout(() => {
      uni.redirectTo({ url: '/pages/login/index' })
    }, 600)
    return
  }
  loadList()
})
```

**注意用 `redirectTo`**，不要用 `navigateTo` —— 否则用户登录后 `navigateBack` 又会回到这个页面，然后又被拦一次，卡在循环里。

### 位置三：`uni.addInterceptor` 统一拦截

```js
const NEED_LOGIN_PAGES = ['/pages/signup/form', '/pages/signup/my', '/pages/user/index']

uni.addInterceptor('navigateTo', {
  invoke(args) {
    const path = args.url.split('?')[0]
    if (NEED_LOGIN_PAGES.includes(path) && !isLoggedIn()) {
      uni.showToast({ title: '请先登录', icon: 'none' })
      uni.navigateTo({ url: '/pages/login/index' })
      return false
    }
  }
})
```

**拦截器看起来最省事，但它有两个问题**：要维护一份名单（漏一个就是漏洞），而且 **`switchTab` 也要单独拦一次**（它是另一个 API）。本项目用前两种，**不用第三种**。

## 七、“我的”页与退出登录

```vue [src/pages/user/index.vue]
<template>
  <view class="page">
    <view class="user-card">
      <view class="avatar">{{ avatarText }}</view>
      <view class="info">
        <text class="name">{{ userInfo ? userInfo.realName : '未登录' }}</text>
        <text class="sub">{{ userInfo ? userInfo.studentNo : '登录后可以报名活动' }}</text>
      </view>
    </view>

    <wd-cell-group border>
      <wd-cell title="我的报名" is-link @click="goMySignup" />
      <wd-cell title="关于" is-link @click="showAbout" />
    </wd-cell-group>

    <view class="footer">
      <wd-button v-if="userInfo" type="error" plain block @click="handleLogout">退出登录</wd-button>
      <wd-button v-else type="primary" block @click="goLogin">去登录</wd-button>
    </view>

    <wd-dialog />
  </view>
</template>
```

```js
const userInfo = ref(null)
const dialog = useDialog()

onShow(() => {
  // 每次显示都重读，因为可能在别的页面登录或退出了
  userInfo.value = getUserInfo()
})

async function handleLogout() {
  const ok = await dialog.confirm({
    title: '确认退出',
    msg: '退出后需要重新登录才能报名'
  })
  if (!ok) return

  try {
    await logout()        // 通知后端作废 token，失败也不影响本地清理
  } catch (e) {
    // 忽略：本地登录态该清还是要清
  }
  clearLoginState()
  userInfo.value = null
  uni.showToast({ title: '已退出登录', icon: 'none' })
}
```

**两个细节：**

**一、`onShow` 里重读 userInfo。** 用户可能在“我的报名”页被跳去登录并登录成功，回来时“我的”页的数据要是新的。

**二、退出登录时后端调用失败也要清本地。** 后端请求失败（网络问题）不该导致用户退不出去 —— **本地清干净，用户在感知上就是退出了**，服务端那份 token 让它自然过期。

## 八、容易出问题的地方

::: details 登录成功后返回，报名按钮还是提示“请先登录”

**现象：** 从详情页点报名 → 跳登录页 → 登录成功 → 返回详情页 → 再点报名，还是提示“请先登录”。

**原因：** 详情页在 `onLoad` 里读过一次登录态并**缓存到了一个变量里**，`navigateBack` 回去不会重新执行 `onLoad`。

**怎么处理：** 把登录判断改成**每次点击时实时读**，不要在页面初始化时缓存：

```js
// ✗ 页面加载时读一次，之后不再更新
const logged = isLoggedIn()
function handleSignup() {
  if (!logged) { /* ... */ }
}

// ✓ 每次点击都读一次
function handleSignup() {
  if (!ensureLogin()) return
  // ...
}
```

**`uni.getStorageSync` 是同步的、开销极小**，每次读没有性能问题。**缓存登录态是这一端最常见的自找麻烦。**

:::

::: details 小程序端登录报“code 无效”或“已被使用”

**现象：** 调微信登录，后端返回 code 无效。

**原因：** 微信的登录 `code` **是一次性的、几分钟就过期**。出现这个报错通常是：

1. **前端把同一个 code 用了两次**（比如重试逻辑里复用了变量）
2. **用户授权后隔了很久才发出请求**
3. **后端调 `code2session` 时传错了 AppID 或 AppSecret**

**怎么处理：** 前端这两条要保证：

```js
async function handleWeixinLogin() {
  // 每次登录都重新拿 code，不要缓存
  const { code } = await new Promise((resolve, reject) => {
    uni.login({ provider: 'weixin', success: resolve, fail: reject })
  })
  // 拿到就立刻发出去，不要在这里做别的异步操作
  const res = await loginByWeixin(code)
}
```

**AppID 和 AppSecret 的问题只能后端查。** 注意区分两个 AppID：`manifest.json` 里 `mp-weixin.appid` 是小程序的，后端配置的 AppSecret 必须和这个小程序对应 —— **两者不匹配是这类报错最常见的原因。**

:::

::: details H5 端没有 `uni.login`，整个页面报错

**现象：** 在浏览器里打开登录页，报 `uni.login is not a function` 或者页面白屏。

**原因：** `uni.login` 在小程序端是微信授权，**H5 端没有这个能力**（浏览器里没有微信的授权体系）。虽然 uni-app 提供了同名 API，但在 H5 上它走的是另一套实现，没有 `provider: 'weixin'` 这种用法。

**怎么处理：** 用条件编译把整段包起来：

```js
// #ifdef MP-WEIXIN
async function handleWeixinLogin() {
  // ...
}
// #endif
```

**模板里的按钮也要包**，否则 H5 端会显示一个点了没反应的按钮：

```vue
<!-- #ifdef MP-WEIXIN -->
<wd-button @click="handleWeixinLogin">微信一键登录</wd-button>
<!-- #endif -->
```

**验证办法**：改完在两个端各跑一遍，确认 H5 端看不到微信登录按钮，小程序端看得到。

:::

::: details 退出登录后，某个页面还能看到上一个人的数据

**现象：** 退出登录后换一个账号登进来，发现“我的报名”列表里还是上一个人的记录。

**原因：** 页面数据被缓存了。`navigateBack` 或者 tabBar 切换时页面没有销毁，`onLoad` 不会重新执行，于是列表还是旧的。

**怎么处理：** 用户身份变化时，**所有依赖身份的数据都要失效**。两种做法：

| 做法 | 怎么做 |
| --- | --- |
| 退出时清页面数据 | 复杂，要通知每个页面 |
| **数据请求放 `onShow`，或加身份校验** | 推荐 |

最省事的一种：在需要登录的页面的 `onShow` 里检查当前用户 id 有没有变过：

```js
onShow(() => {
  const currentId = getUserInfo() && getUserInfo().id
  if (currentId !== loadedUserId.value) {
    loadedUserId.value = currentId
    page.value = 1
    list.value = []
    loadList()
  }
})
```

**更彻底的做法是退出登录时用 `reLaunch` 回首页**，把所有页面栈清掉。**代价小，效果确定** —— 用户端页面不多，重新进一次不费事。

:::

## 九、验收清单

- [ ] 未登录时能正常浏览活动列表和详情
- [ ] 未登录点报名，提示并跳登录页
- [ ] 登录后自动返回原来的位置，能继续报名
- [ ] 账号密码登录：密码错误时提示具体原因，不跳登录页
- [ ] 小程序端能用微信一键登录（真机验证）
- [ ] 首次微信登录后引导补充学号
- [ ] 退出登录后，token 和 userInfo 都清空了
- [ ] 退出后换账号登录，“我的报名”显示的是新账号的数据
- [ ] 手动把 token 改成乱码，发请求后自动跳到登录页
- [ ] 上述各项在 H5 与微信小程序端都跑过一遍

## 十、可以继续做的事

1. **登录态过期前的续期。** 后端如果返回 `expiresIn`，可以在快过期时静默刷新 token，用户不会被打断
2. **登录前的表单暂存。** 用户填完报名表单点提交，结果 token 过期跳走了 —— 把表单数据暂存，登录回来后恢复
3. **微信手机号快捷验证。** 小程序提供手机号快速验证组件，可以让补充资料这一步更省事（需要企业主体的小程序）
4. **把“家长/老师代看”这类场景排除掉**。用户端只需要学生一种身份，**不要为假想的角色增加复杂度**

---

上一页：[用户端需求规格](/project/mobile) ·
下一页：[用户端 · 活动浏览与报名](/project/impl-mobile-browse)
