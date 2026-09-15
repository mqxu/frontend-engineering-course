# 4. 布局与样式

## 一个具体的场面

设计稿给你了，是一个 750px 宽的手机界面。你照着量出来的尺寸写 CSS：卡片高 160px，左右内边距 24px，标题 32px。

在浏览器里调到手机模式看，还行。拿到真机上一看，全乱了：

- 在大屏手机上，卡片扁得像一条缝
- 在 iPhone 上，底部固定的“立即报名”按钮被系统的小黑条压住了一截
- 有一处用了 `float` 的布局，在小程序端完全没生效

**三个问题，三个不同的原因。** 这一节把移动端样式的这几件事说清楚。

## 一、rpx：解决屏幕宽度不一的问题

`px` 的问题是它是个绝对单位。设计稿 750px 宽的界面，在 375px 宽的屏幕上，所有东西都会挤成一半 —— 但**你不希望文字变成 8px 那么小，你希望整体等比缩小。**

这就是 `rpx` 存在的理由：

**750rpx 永远等于屏幕的宽度。**

换算方式：

| 设备 | 屏幕宽度 | 1rpx 等于 |
| --- | --- | --- |
| iPhone SE | 320px | 0.427px |
| iPhone 8 | 375px | 0.5px |
| iPhone 15 Pro Max | 430px | 0.573px |
| 平板 | 768px | 1.024px |

**换算规则记一条就够了：设计稿是按 750px 宽做的，那么设计稿上标注多少 px，你就写多少 rpx。**

设计稿上卡片高 160px → 写 `height: 160rpx`。不用算，不用除二。

### 什么时候用 px，什么时候用 rpx

不是所有尺寸都该用 rpx。判断标准是**“这个尺寸要不要随屏幕大小变”**：

| 用 rpx | 用 px |
| --- | --- |
| 容器的宽高、内外边距 | 边框宽度（`border: 1px solid`） |
| 字号、图标大小 | 阴影偏移与模糊半径 |
| 圆角半径 | 需要精确到物理像素的细线 |

**边框用 `px` 是有实际原因的。** 写 `border: 1rpx solid #ddd`，在小屏手机上这条线可能窄到 0.4 物理像素，渲染出来是断断续续的虚线。写 `1px` 则由系统按设备像素比处理，看起来更稳。

```css
/* ✗ 细线用 rpx，小屏上会断 */
.card { border: 1rpx solid #eeeeee; }

/* ✓ 细线用 px */
.card { border: 1px solid #eeeeee; }
```

::: warning 大屏上 rpx 的表现会让人意外
在平板或者桌面浏览器里打开 H5 版本，`rpx` 会让元素变得特别大 —— 因为它按“屏幕宽度等于 750rpx”算，而屏幕有一千多像素宽。

**H5 端要限制最大宽度**，让内容居中，两边留白：

```css
/* App.vue 里，只对 H5 生效 */
/* #ifdef H5 */
page {
  max-width: 750px;
  margin: 0 auto;
}
/* #endif */
```

**小程序端不用管这件事**，因为小程序只运行在手机上。
:::

### 一个开关要提一下

`manifest.json` 里有个 `transformPx` 字段（模板里默认是 `false`）。它的作用是把代码里的 `px` 自动转成 `rpx` —— **官方标注已废弃，新项目不要开启。** 开了之后你写 `1px` 边框也会被转，就是上面说的那种虚线问题。**保持 `false`，自己决定哪里写 px、哪里写 rpx。**

## 二、移动端的 flex 布局套路

移动端布局基本就是 flex 的三种用法，记住模板就行。

### 套路一：列表卡片（上下结构）

```css
.card {
  display: flex;
  flex-direction: column;
  padding: 24rpx;
  background: #ffffff;
  border-radius: 16rpx;
  margin-bottom: 20rpx;
}

.card-footer {
  display: flex;
  justify-content: space-between;   /* 两端对齐：左边名额，右边按钮 */
  align-items: center;
}
```

### 套路二：标题行（图标 + 文字 + 右侧操作）

```css
.row {
  display: flex;
  align-items: center;
  gap: 16rpx;
}

.row-title {
  flex: 1;              /* 占满剩余空间 */
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;  /* 标题过长省略，不换行 */
}
```

**`flex: 1` 加省略号这三行是固定搭配。** 少写 `min-width: 0` 时，在某些浏览器里 `flex` 子元素会被内容撑开而不省略 —— 小程序端一般没这个问题，但 H5 端会遇到。

### 套路三：底部固定操作栏

```css
.footer-bar {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  padding: 20rpx 24rpx;
  background: #ffffff;
  border-top: 1px solid #eeeeee;
}

/* 页面内容要给底部栏留出空间，否则最后一条会被盖住 */
.page-body {
  padding-bottom: 160rpx;
}
```

**“最后一条被固定栏盖住”是最常见的移动端 bug。** 写完固定栏，一定记得给内容容器加一个不小于固定栏高度的 `padding-bottom`。

## 三、安全区：别让按钮被小黑条压住

iPhone 从 X 开始底部有个横条（Home Indicator），底部固定的元素如果贴着屏幕边缘，会被它压住。

解决办法是给底部栏加安全区留白：

```css
.footer-bar {
  padding-bottom: 20rpx;
  /* iOS 11.2 之前 */
  padding-bottom: constant(safe-area-inset-bottom);
  /* iOS 11.2 及以后 */
  padding-bottom: calc(20rpx + env(safe-area-inset-bottom));
}
```

写法说明：

- **两行要按顺序写**，后面的覆盖前面的 —— 老系统不认 `env()` 就保留上一行的值
- `constant()` 是老写法，`env()` 是标准写法，两个都写是为了兼容旧设备
- 不需要算具体数值，系统会把安全区高度填进 `env(safe-area-inset-bottom)`

::: details H5 端不生效，怎么查
`env(safe-area-inset-*)` 生效有两个前提：

1. 页面的 viewport meta 里有 `viewport-fit=cover`
2. 是在有安全区的设备上（用浏览器模拟器时要选带刘海的机型）

uni-app 的 H5 端默认已经处理了 viewport meta，**如果还是没效果，先确认你是不是在模拟一个没有安全区的机型。**

**小程序端不需要额外配置**，系统会把安全区高度算好。
:::

## 四、样式的作用域与全局样式

管理端你可能习惯了“每个组件的样式自动隔离”（`<style scoped>`）。uni-app 里规则差不多，但有两点不同。

### 全局样式写在 App.vue

```vue [src/App.vue]
<script setup>
import { onLaunch } from '@dcloudio/uni-app'

onLaunch(() => {
  console.log('应用启动了')
})
</script>

<style>
/* 这里没有 scoped，是全局样式 */
page {
  background-color: #f5f5f5;
  font-size: 28rpx;
  color: #333333;
}

/* 通用工具类 */
.text-ellipsis {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
```

**注意 `page` 这个选择器。** 它相当于整个页面容器的根节点，在小程序里就是那个最外层的容器。**页面背景色要设在 `page` 上，写在某个 `view` 上是没用的**（内容不够高时露出的还是默认白底）。

### uni.scss 放变量

```scss [src/uni.scss]
$brand-color: #42b883;
$text-main: #333333;
$text-sub: #999999;
$border-color: #eeeeee;
$page-bg: #f5f5f5;
```

这个文件里定义的变量**在每个组件的 `<style lang="scss">` 里都能直接用**，编译器会自动注入，不用 `@use`。

```vue
<style lang="scss" scoped>
.tag {
  color: $brand-color;
  background: $page-bg;
}
</style>
```

**不要用 `@import` 去引它**，会重复注入导致变量冲突。

## 五、条件编译：给不同的端写不同的代码

这是 uni-app 最有用的特性之一。同一份代码，在不同平台上走不同分支。

```js
// 判断平台
// #ifdef H5
console.log('这段只在 H5 里执行')
// #endif

// #ifdef MP-WEIXIN
console.log('这段只在微信小程序里执行')
// #endif

// #ifndef MP-WEIXIN
console.log('除了微信小程序，其他端都执行')
// #endif
```

三个位置都能用，注释符号不同：

```vue
<template>
  <view class="page">
    <!-- #ifdef H5 -->
    <view class="h5-only">这段只在 H5 渲染</view>
    <!-- #endif -->

    <!-- #ifdef MP-WEIXIN -->
    <button open-type="share">分享给同学</button>
    <!-- #endif -->
  </view>
</template>

<style>
/* #ifdef H5 */
.page { max-width: 750px; margin: 0 auto; }
/* #endif */
</style>
```

常用的平台标识：

| 标识 | 平台 |
| --- | --- |
| `H5` | 浏览器 |
| `MP-WEIXIN` | 微信小程序 |
| `MP-ALIPAY` | 支付宝小程序 |
| `APP-PLUS` | App |
| `MP` | 所有小程序 |

**用它的场合要克制。** 条件编译的正确用法是处理平台差异（分享按钮、H5 的最大宽度、原生 API 差异），**不是拿来写两套业务逻辑**。如果一个页面里到处都是 `#ifdef`，说明设计出了问题。

### 本项目会用到的三处平台差异

| 差异点 | 处理方式 |
| --- | --- |
| H5 需要限制最大宽度并居中 | `#ifdef H5` 给 `page` 加 `max-width` |
| 小程序有分享按钮，H5 没有 | `#ifdef MP-WEIXIN` 包住分享相关代码 |
| 登录方式不同（小程序走微信授权） | 在请求层用条件编译分开，页面层不用管 |

## 小结

- **750rpx 等于屏幕宽度**，设计稿按 750px 做的，量出多少 px 就写多少 rpx
- 边框、阴影用 `px`，尺寸、字号用 `rpx`，**别开 `transformPx` 自动转换**
- 移动端布局就是三个套路：纵向卡片、`flex: 1` 加省略号、底部固定栏加内容留白
- 底部固定元素要加 `env(safe-area-inset-bottom)`，**否则会被 iOS 的横条压住**
- 全局样式写在 `App.vue` 的无 `scoped` 样式块里，**页面背景色要设在 `page` 选择器上**
- 条件编译用来处理平台差异，**不要用它写两套业务**

## 常见坑

::: details 页面背景色设了，但下半部分还是白的

**现象：** 给最外层的 `view` 设了背景色，内容不够长时下面露出的还是白色。

**原因：** 最外层 `view` 的高度只到内容底部，剩下的区域属于页面容器本身。

**怎么处理：** 背景色设在 `page` 上：

```css
/* ✗ 外层 view 只包住内容 */
.container { background: #f5f5f5; }

/* ✓ 设在 page 上，整屏都是这个色 */
page { background: #f5f5f5; min-height: 100vh; }
```

**`page` 是 uni-app 提供的页面根节点选择器**，小程序端和 H5 端都支持。这条和管理端的区别是：管理端的 `body` 背景在全局 CSS 里设一次就行，这里必须用 `page`。

:::

::: details 底部固定栏把最后一条内容盖住了

**现象：** 列表滚到底，最后一张卡片被底部按钮栏挡住一半。

**原因：** 固定定位的元素脱离了文档流，内容区不知道它存在。

**怎么处理：** 给内容容器加 `padding-bottom`，值不小于固定栏的实际高度（含安全区）：

```css
.page-body {
  /* 底部栏内容高度 100rpx + 上下内边距 40rpx + 安全区 */
  padding-bottom: calc(140rpx + env(safe-area-inset-bottom));
}
```

**固定栏高度变了，这里也要跟着改。** 嫌麻烦就用 scss 变量把高度定义在一处，两边引用同一个变量。

:::

::: details 用 `float` 或 `position: absolute` 精确定位，小程序端全乱

**现象：** 在 H5 端调好的绝对定位布局，小程序端位置全偏了。

**原因：** 小程序端的渲染引擎和浏览器不完全一致，**`float` 的支持不完整，绝对定位的参照物（`position: relative` 的祖先）在小程序里有时表现不同。** 加上小程序有自带的顶部导航栏，页面可用区域的高度和你以为的不一样。

**怎么处理：** **移动端布局统一用 flex，不要用 float。** 需要叠放时用 `position: relative` 加 `absolute`，并且确保父元素明确写了 `position: relative`（不要依赖默认值）。**这一条不管端不端的，用 flex 都更省事。**

:::

::: details 条件编译写了没生效，两端行为还是一样

**现象：** 加了 `#ifdef H5` 的代码，在小程序里照样执行了。

**原因：** 注释符号写错了。**不同位置的注释符号不同，这是最容易错的地方：**

| 位置 | 正确写法 |
| --- | --- |
| js / ts | `// #ifdef H5` |
| template | `<!-- #ifdef H5 -->` |
| css / scss | `/* #ifdef H5 */` |
| json | `// #ifdef H5` |

**怎么处理：** 检查注释符号是否和文件类型匹配。**另一个常见错误是 `#ifdef` 拼成了 `#ifdef` 以外的形式**（比如 `#ifdef H5` 写成 `#ifdefH5`）—— 中间必须有空格。

**验证办法：** 在条件块里写一句明显的 `console.log('H5 分支')`，两端分别跑一遍看哪个端打印了。

:::

## 课后练习

**把活动列表页的样式按移动端规范重写一遍，用设计稿的尺寸。**

假设设计稿（750px 宽）标注如下：

| 元素 | 设计稿标注 |
| --- | --- |
| 卡片 | 左右外边距 24px，内边距 24px，圆角 16px，卡片间距 20px |
| 卡片标题 | 字号 32px，加粗，单行超出省略 |
| 类型标签 | 字号 24px，内边距上下 6px 左右 16px，圆角 8px |
| 名额进度 | 字号 26px，右对齐 |
| 卡片细边框 | 1px |
| 底部固定报名栏 | 高 100px，内边距上下 20px |

要求：

| 项 | 要求 |
| --- | --- |
| 单位 | 尺寸用 rpx，细线和阴影用 px，并在注释里说明为什么 |
| 布局 | 全部用 flex，不许出现 float |
| 安全区 | 底部固定栏加安全区处理，在 iPhone 机型上验证 |
| 全局 | 页面背景色设在 `page` 上，设成 `#f5f5f5` |
| 两个端 | H5 与微信小程序端都要验证，且 H5 端要限制最大宽度 |

::: details 验收标准与参考思路

**验收标准：**

| 项 | 要求 |
| --- | --- |
| 尺寸换算 | 设计稿 24px 对应代码里 24rpx，**不是 12rpx**（常见错误：按 375 宽的设计稿习惯除了 2） |
| 长标题 | 标题很长时单行省略，不换行、不撑破卡片 |
| 最后一条 | 滚到底部，最后一张卡片完整可见，没被固定栏遮挡 |
| 安全区 | iPhone 模拟器上底部按钮不贴边，上方留出横条空间 |
| H5 宽屏 | 浏览器拉宽到 1200px，内容居中且不至于被拉得特别大 |

**不合格的写法：**

```css
/* ✗ 三个问题：用的是 px、用了 float、固定栏没留白 */
.card { height: 160px; float: left; }
.footer-bar { position: fixed; bottom: 0; height: 100px; }
```

用 `px` 意味着换个屏幕尺寸就变形；`float` 在小程序端表现不可靠；固定栏没给内容留空间，最后一条必然被盖。

**合格的写法：**

```vue
<style lang="scss" scoped>
.card {
  display: flex;
  flex-direction: column;
  padding: 24rpx;              /* 设计稿 24px，直接写 24rpx */
  margin: 0 24rpx 20rpx;
  background: #ffffff;
  border: 1px solid $border-color;   /* 细线用 px，小屏上不会断 */
  border-radius: 16rpx;
}

.card-title {
  flex: 1;
  min-width: 0;
  font-size: 32rpx;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.page-body {
  padding-bottom: calc(140rpx + env(safe-area-inset-bottom));
}

.footer-bar {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  height: 100rpx;
  padding: 20rpx 24rpx;
  padding-bottom: calc(20rpx + env(safe-area-inset-bottom));
  background: #ffffff;
  border-top: 1px solid $border-color;
}
</style>
```

**参考思路：**

多数人会在两个地方卡住：

**一是 rpx 的换算方向。** 记住“设计稿多宽就写多少 rpx”，**不要除以 2**。如果你拿到的设计稿是 375px 宽的（有些工具默认这个尺寸），那量出来的数值要乘 2 再写成 rpx。

**二是安全区在小程序里的验证方式。** 微信开发者工具的模拟器里可以选机型，选 iPhone 15 Pro 这类带安全区的机型，**但模拟器不一定准确反映真机效果**。有条件的话用“预览”功能在真机上扫一下，这是唯一可靠的验证方式。

:::

---

上一节：[页面与路由](/mobile/03-pages-router) ·
下一节：[组件与组件库](/mobile/05-components)
