# 3. 页面与路由

## 一个具体的场面

你照着管理端的思路，在用户端里做完了活动列表页。点一个活动卡片进详情页，看完再点左上角返回 —— 列表页的数据没了，只有一片空白，还得等它重新转圈。

更烦的是另一件事：你想从列表页把活动的 `id` 和 `title` 一起传给详情页，写了这样的代码：

```js
uni.navigateTo({ url: '/pages/activity/detail', params: { id: 1, title: '歌手大赛' } })
```

详情页里 `onLoad` 拿到的 `options` 是空的。

**这两件事都指向同一个原因：uni-app 的路由和管理端不是一回事。** 管理端用的是浏览器的 History API，页面状态存在内存里；小程序里没有浏览器，路由是“页面栈”模型，参数只能走 URL 字符串。

## 一、页面要在 pages.json 里登记

管理端的路由是“路由表指向组件”，少写一个组件文件，路由表里报错。**uni-app 反过来：页面清单本身就是路由表。**

```json [src/pages.json]
{
  "pages": [
    {
      "path": "pages/activity/list",
      "style": {
        "navigationBarTitleText": "校园活动"
      }
    },
    {
      "path": "pages/activity/detail",
      "style": {
        "navigationBarTitleText": "活动详情"
      }
    },
    {
      "path": "pages/signup/form",
      "style": {
        "navigationBarTitleText": "报名"
      }
    }
  ],
  "globalStyle": {
    "navigationBarTextStyle": "black",
    "navigationBarTitleText": "校园活动",
    "navigationBarBackgroundColor": "#ffffff",
    "backgroundColor": "#f5f5f5"
  }
}
```

三条规则：

1. **数组第一项就是启动页**，没有单独的“首页”配置
2. **没登记的页面访问不到** —— 你建了 `detail.vue` 但忘了写进 `pages`，`navigateTo` 会失败
3. **`path` 不带 `.vue` 后缀**，但 `style.navigationBarTitleText` 决定的是手机顶部那条标题栏上的文字，不是浏览器标签页

### 每个页面可以单独配的样式

`style` 里常用的几项：

| 配置 | 作用 |
| --- | --- |
| `navigationBarTitleText` | 顶部标题栏文字 |
| `navigationStyle` | 设成 `custom` 就隐藏系统标题栏，自己做导航（本项目详情页要这么做） |
| `enablePullDownRefresh` | 是否开启下拉刷新（列表页要开） |
| `onReachBottomDistance` | 距离底部多少像素时触发触底（默认 50） |
| `backgroundColor` | 下拉时露出的背景色 |

**`enablePullDownRefresh` 默认是 `false`。** 不开这个开关，你在页面里写 `onPullDownRefresh` 也不会触发 —— 这是新手最常见的“代码写了没反应”。

## 二、底部导航栏

用户端有 3 个主要入口，用底部 tabBar 装：

```json [src/pages.json]
{
  "tabBar": {
    "color": "#999999",
    "selectedColor": "#42b883",
    "backgroundColor": "#ffffff",
    "borderStyle": "black",
    "list": [
      { "pagePath": "pages/activity/list", "text": "活动" },
      { "pagePath": "pages/signup/my", "text": "我的报名" },
      { "pagePath": "pages/user/index", "text": "我的" }
    ]
  }
}
```

约束有两条，**违反了会编译不过**：

1. **`list` 里只能是 2 到 5 项**
2. **`pagePath` 必须在 `pages` 里已经登记过**

每一项还可以加 `iconPath` 和 `selectedIconPath` 指向图标文件。要不要加图标是设计选择：**纯文字也能用，而且省事**（图标要准备两套，还得注意尺寸），先不上图标不影响功能。

## 三、五种跳转方式，别用错

这是这一节最核心的一张表：

| 方法 | 行为 | 什么时候用 |
| --- | --- | --- |
| `uni.navigateTo` | 保留当前页，跳过去 | **列表 → 详情**，要能返回 |
| `uni.redirectTo` | 关闭当前页，跳过去 | 表单提交成功后跳结果页，**不让用户回到表单** |
| `uni.switchTab` | 跳到 tabBar 页面，**必须用这个** | 从任意页跳到三个主入口 |
| `uni.reLaunch` | 关掉所有页面，重新开始 | 退出登录后回首页 |
| `uni.navigateBack` | 返回上一层 | 详情页返回，或 `delta: 2` 退两层 |

**最容易错的是 `switchTab`。** 你从“我的报名”页想跳到“活动”列表页，写了 `uni.navigateTo({ url: '/pages/activity/list' })` —— 如果这个页面在 tabBar 里，会直接失败。**tabBar 页面只能用 `switchTab` 跳，且不能带参数。**

```js
// ✗ 跳 tabBar 页面用 navigateTo，会失败
uni.navigateTo({ url: '/pages/activity/list' })

// ✓ 用 switchTab
uni.switchTab({ url: '/pages/activity/list' })
```

### 页面栈有层数上限

`navigateTo` 是往栈里压页面。**微信小程序端这个栈最多 10 层**，压满了就跳不动了。

什么情况会压满？比如“列表 → 详情 → 报名 → 查看其他活动 → 详情 → 报名……”这样一路点下去。**用户点十几次是常有的事。**

处理原则：**同一类页面不要无限往栈里压。** 从详情页跳到另一个详情页时，用 `redirectTo` 替换掉当前页，而不是新压一层。

## 四、传参：只能传字符串

小程序页面之间**不能传对象**，参数只能放在 URL 里。这就是开头那段代码失败的原因。

```js
// ✓ 把参数拼进 url 的查询串
uni.navigateTo({
  url: '/pages/activity/detail?id=' + id
})

// ✓ 多个参数
uni.navigateTo({
  url: '/pages/signup/form?activityId=' + id + '&status=' + status
})
```

接收端在 `onLoad` 里拿：

```js
import { onLoad } from '@dcloudio/uni-app'

onLoad((options) => {
  // options 是解析好的对象：{ id: '1', status: 'SIGNING' }
  const id = options.id
  loadDetail(id)
})
```

::: warning 三条关于参数的注意事项
**一、拿到的一定是字符串。** `options.id` 是 `'1'` 不是 `1`。要比较或计算时先转：`Number(options.id)`。

**二、中文和特殊字符要编码。** 直接把活动标题拼进 URL，遇到 `&`、`#`、空格就会解析错：

```js
// ✗ 标题里有 & 就断了
url: '/pages/activity/detail?title=' + activity.title

// ✓ 用 encodeURIComponent
url: '/pages/activity/detail?title=' + encodeURIComponent(activity.title)
```

接收时用 `decodeURIComponent(options.title)` 还原。

**三、别把整个对象序列化后塞进 URL。** 有人用 `JSON.stringify` 加 `encodeURIComponent` 传对象，**URL 长度有限制，而且看着就不该这么写。** 正确做法是只传 `id`，详情页拿着 `id` 自己请求一次。这也符合管理端那条约定：**列表页和详情页各自请求自己需要的数据，不靠传值。**
:::

## 五、页面生命周期怎么和 Vue 生命周期配合

这是最容易搞混的一块。一个页面同时有两套生命周期钩子。

| 钩子 | 从哪导入 | 什么时候触发 | 典型用途 |
| --- | --- | --- | --- |
| `onLoad` | `@dcloudio/uni-app` | 页面**只加载一次**，能拿到参数 | 用 `id` 请求详情 |
| `onShow` | `@dcloudio/uni-app` | 每次页面**显示**都触发 | 从别的页返回时刷新数据 |
| `onReady` | `@dcloudio/uni-app` | 首次渲染完成 | 需要操作组件实例时 |
| `onHide` | `@dcloudio/uni-app` | 页面被隐藏（跳到别处） | 暂停定时器 |
| `onUnload` | `@dcloudio/uni-app` | 页面被销毁（返回走了） | 清定时器、清监听 |
| `onPullDownRefresh` | `@dcloudio/uni-app` | 下拉刷新 | 重新拉第一页 |
| `onReachBottom` | `@dcloudio/uni-app` | 滚动到底部 | 加载下一页 |
| `onMounted` | `vue` | 组件挂载 | 一般逻辑 |
| `onUnmounted` | `vue` | 组件卸载 | 清理副作用 |

三条使用原则：

**原则一：页面级的事情用页面钩子，组件级的事情用 Vue 钩子。** 页面参数、下拉刷新、触底加载都是页面级的，必须用 `@dcloudio/uni-app` 的钩子。

**原则二：请求数据一般写在 `onLoad` 里，不要写在 `onMounted` 里。** `onLoad` 能直接拿到路由参数，而且它一定早于 `onMounted`。

**原则三：需要“每次回到这个页都刷新”的数据，写在 `onShow` 里。** 典型场景：报名成功后返回“我的报名”列表，用户期望看到刚提交的那条记录。**`onLoad` 只跑一次，这时候不会重新请求。**

```js
import { onLoad, onShow } from '@dcloudio/uni-app'
import { ref } from 'vue'

const detail = ref(null)

// 只跑一次：拿参数、请求详情
onLoad((options) => {
  loadDetail(options.id)
})

// 每次显示都跑：从报名页回来时刷新一下名额
onShow(() => {
  if (detail.value) refreshQuota(detail.value.id)
})
```

## 六、用户端的路由表

按 5 个页面的设计，`pages.json` 里的完整清单是这样的：

| 路径 | 页面 | 在 tabBar 里 | 进入方式 |
| --- | --- | --- | --- |
| `pages/activity/list` | 活动列表 | 是 | 启动页、`switchTab` |
| `pages/activity/detail` | 活动详情 | 否 | 列表页 `navigateTo` |
| `pages/signup/form` | 报名表单 | 否 | 详情页 `navigateTo` |
| `pages/signup/my` | 我的报名 | 是 | 详情页报名成功后 `switchTab` |
| `pages/user/index` | 我的 | 是 | tabBar |

**注意顺序**：`pages` 数组第一项 `pages/activity/list` 是启动页 —— **用户打开小程序先看到活动列表，不是登录页。** 没登录也能浏览活动，只有点“报名”时才要求登录。**这是刻意的设计**：让人先看到内容，再决定要不要登录，比一上来就拦一道登录墙的转化率高得多。

::: tip 开发时直达某个页面
调试详情页时，每次都从列表点进去很烦。`pages.json` 里可以配 `condition`，让开发时直接启动到指定页面：

```json [src/pages.json]
{
  "condition": {
    "current": 0,
    "list": [
      { "name": "活动详情", "path": "pages/activity/detail", "query": "id=1" }
    ]
  }
}
```

这段配置**只在开发时生效，不会进生产包**，放心用。
:::

## 小结

- `pages.json` 的 `pages` 数组就是路由表，**没登记的页面跳不过去**，第一项是启动页
- tabBar 只能 2 到 5 项，**跳 tabBar 页面必须用 `switchTab`，且不能带参数**
- 五种跳转方式各有用途，**最容易用错的是 `switchTab` 和 `navigateTo` 混用**
- 页面间只能传字符串参数，**拼 URL 时中文要 `encodeURIComponent`，详情页只收 `id` 自己请求**
- 页面生命周期从 `@dcloudio/uni-app` 导入，**`onLoad` 只跑一次，`onShow` 每次显示都跑**
- 请求写在 `onLoad`，需要返回后刷新的数据写在 `onShow`，**下拉刷新要先在 `style` 里开 `enablePullDownRefresh`**

## 常见坑

::: details 点返回后列表页内容消失，要重新等加载

**现象：** 从详情页返回列表页，列表空了，转圈一会儿才回来。

**原因：** 把列表请求写在了 `onLoad` 里。返回时列表页**并不会重新加载**（它在页面栈里没被销毁），但如果你在 `onHide` 或者某处清空了数据，或者依赖了组件重新挂载，就会看到这个现象。

**怎么处理：** 先分清你期望的行为是哪种：

| 期望 | 怎么写 |
| --- | --- |
| 返回时保持原样，不重新请求 | 请求放 `onLoad`，什么都别在 `onHide` 里清 |
| 返回时数据要刷新 | 请求放 `onShow`，或者 `onLoad` 请求一次 + `onShow` 里判断是否需要刷新 |

**别两个都写**，那会请求两次。如果确实需要“首次加载 + 返回时刷新”，用 `onLoad` 请求、`onShow` 里加个标志位判断（第一次跳过）。

:::

::: details 传了 id 过去，详情页 `options.id` 是 undefined

**现象：** 跳转时 URL 里明明带了 `id=1`，`onLoad` 的 `options` 里没有 `id`。

**原因：** 三种可能：

1. **`onLoad` 写在了 `<script setup>` 外面**，没被注册到组件上
2. **页面没在 `pages.json` 里登记**，实际打开的是另一个页面
3. **用了 `switchTab` 跳转还带了参数** —— switchTab 会忽略参数

**怎么处理：** 先在 `onLoad` 里把整个 `options` 打印出来看：

```js
onLoad((options) => {
  console.log('收到参数：', JSON.stringify(options))
})
```

**打印出来是空对象，说明参数根本没传过去**，回去检查跳转的那一行；**打印出来有内容但字段名对不上**，是拼 URL 时字段名写错了。

:::

::: details 页面栈压满，`navigateTo` 直接失败

**现象：** 一路点下去，到某个时候点跳转没反应，控制台提示 `navigateTo:fail page limit exceeded` 之类。

**原因：** 小程序页面栈有上限（微信小程序是 10 层），一直用 `navigateTo` 会压满。

**怎么处理：** 两个办法。**一是判断当前栈深**，用 `getCurrentPages().length` 看还有没有空间；**二是从设计上避免**，同类页面之间跳转用 `redirectTo`：

```js
// 从活动详情跳到另一个活动详情：替换当前页，不新增层级
function goAnotherActivity(id) {
  uni.redirectTo({ url: '/pages/activity/detail?id=' + id })
}
```

**更好的做法是不让用户这么点。** 详情页底部推荐“相关活动”这种入口，本来就不该做成无限跳转的链条。

:::

::: details 下拉刷新写了 `onPullDownRefresh`，转圈不出现

**现象：** 页面里写了 `onPullDownRefresh`，下拉时没有任何反应。

**原因：** 两个必要条件缺一个：`pages.json` 里这个页面的 `style` 没写 `enablePullDownRefresh: true`；或者下拉动作被内容顶住了（页面没有滚动区域，或者用了 `scroll-view` 承接滚动）。

**怎么处理：** 先确认开关：

```json
{
  "path": "pages/activity/list",
  "style": {
    "enablePullDownRefresh": true,
    "backgroundTextStyle": "dark"
  }
}
```

再确认页面本身是可滚动的 —— **内容高度要超过屏幕高度，否则没有下拉的余地。** 开发时内容少，容易误判为“代码有问题”。

:::

## 课后练习

**给用户端配好完整的 `pages.json`，并把 5 个页面之间的跳转串起来。**

要求：

| 项 | 要求 |
| --- | --- |
| 页面 | 建 5 个空页面，都在 `pages.json` 里登记 |
| tabBar | 配 3 个入口，选中色用 `#42b883` |
| 跳转 | 列表页点卡片 → 详情页（带 `id`）；详情页点报名 → 表单页（带 `activityId`）；表单页提交成功 → 用 `switchTab` 回“我的报名” |
| 参数 | 在详情页和表单页把 `onLoad` 收到的参数显示在页面上，验证传参正确 |
| 返回 | 详情页顶部显示活动 `id`，用它验证参数确实到位 |
| 不许做的 | 页面里不要写任何接口请求，用假数据占位 |

::: details 验收标准与参考思路

**验收标准：**

| 项 | 要求 |
| --- | --- |
| 三个 tab | 底部导航能看到 3 项，点击能切换，选中态颜色正确 |
| 传参 | 详情页显示的 `id` 和列表页点的那一项一致 |
| switchTab | 表单页提交后跳到“我的报名”，**且底部 tabBar 的选中项跟着变了** |
| 栈深 | 反复在列表和详情间跳 12 次，不出现跳转失败（说明你没把栈压满） |
| 两个端 | H5 与微信小程序端都验证一遍 |

**不合格的写法：**

```js
// 从详情页跳“我的报名”，用了 navigateTo
uni.navigateTo({ url: '/pages/signup/my' })
```

如果 `pages/signup/my` 在 tabBar 里，这一行会失败；如果它不在 tabBar 里，那底部导航的设计就不对了。

**另一个常见的不合格写法：**

```js
// 把对象整个塞进 URL
uni.navigateTo({
  url: '/pages/activity/detail?activity=' + encodeURIComponent(JSON.stringify(activity))
})
```

**这次能跑，下次活动描述里有特殊字符就会崩。** 而且详情页拿到的是一个可能过期的快照 —— 用户看到的名额数还是列表页那一刻的。

**合格的写法：**

```js
// 列表页：只传 id
function goDetail(id) {
  uni.navigateTo({ url: '/pages/activity/detail?id=' + id })
}

// 详情页：拿 id，自己请求详情
onLoad((options) => {
  const id = Number(options.id)
  if (!id) {
    uni.showToast({ title: '参数错误', icon: 'none' })
    uni.navigateBack()
    return
  }
  loadDetail(id)
})
```

**注意那段参数校验** —— 参数是从 URL 来的，是不可信的外部输入，**该判空就判空**。这一点和管理端一样（URL 上的 `:id` 也要校验），只是处理方式换成了 `uni.showToast` 加返回上一页。

**参考思路：**

这道题的难点不在跳转本身，在两处边界：

| 边界 | 怎么处理 |
| --- | --- |
| 参数缺失或非法 | `onLoad` 里判空，提示并 `navigateBack` |
| 从表单页回了列表页，数据要不要刷新 | 如果要，用 `onShow`；如果不要，确认没在 `onHide` 里清数据 |

**验证栈深那条要求（跳 12 次）是个真实场景的缩写** —— 用户真的会这么点。你可以在详情页加一个“看看别的活动”的按钮，用 `redirectTo` 跳另一个 `id`，然后连点十几次验证一下。

:::

---

上一节：[建工程：从命令到跑起来](/mobile/02-scaffold) ·
下一节：[布局与样式](/mobile/04-layout-style)
