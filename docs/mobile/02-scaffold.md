# 2. 建工程：从命令到跑起来

## 一个具体的场面

上一节分析完差异，这一节开始动手。

你敲下创建项目的命令，等它跑完，打开 `src/` 一看：

```
src/
├── App.vue
├── main.js
├── manifest.json
├── pages.json
├── pages/index/index.vue
├── static/logo.png
└── uni.scss
```

没有 `index.html`，没有 `router/`，没有 `vite.config.js` 在 `src` 里 —— 但根目录有一个。`pages.json` 和 `manifest.json` 这两个文件，你在管理端从没见过。

**这一节要做四件事**：把项目建出来、看懂这四个新文件、把它跑起来、装上组件库。做完之后，你的工程能同时在浏览器和微信开发者工具里显示同一个页面。

## 一、创建工程

```bash
# 在你想放项目的目录下执行
npx degit dcloudio/uni-preset-vue#vite activity-mobile
cd activity-mobile
pnpm install
```

`degit` 做的事很简单：把 GitHub 上 `dcloudio/uni-preset-vue` 仓库的 `vite` 分支下载下来，不带 Git 历史。

::: warning 国内网络下这条命令经常失败
`degit` 要从 GitHub 拉代码，校园网里失败是常态。**失败就换 Gitee 的备份地址**：

```bash
curl -L -o vite.zip https://gitee.com/dcloud/uni-preset-vue/repository/archive/vite.zip
unzip vite.zip
mv uni-preset-vue-vite activity-mobile
cd activity-mobile && pnpm install
```

两个地址拿到的是同一个模板，只是来源不同。官方文档里也是这么建议的。
:::

装完之后先看 `package.json`，你会发现两件和管理端不一样的事：

```json
{
  "dependencies": {
    "@dcloudio/uni-app": "3.0.0-5020420260813003",
    "@dcloudio/uni-h5": "3.0.0-5020420260813003",
    "@dcloudio/uni-mp-weixin": "3.0.0-5020420260813003",
    "vue": "^3.4.21"
  },
  "devDependencies": {
    "@dcloudio/vite-plugin-uni": "3.0.0-5020420260813003",
    "vite": "5.2.8"
  }
}
```

**第一件事：版本号长得很怪。** `3.0.0-5020420260813003` 是 uni-app 的版本格式，横线后面那一串是编译日期与内部版本。这些包的版本必须完全一致，**不要单独升级其中一个**。

**第二件事：Vite 是 5.2.8，Vue 是 3.4.21。** 管理端用的是 Vite 8.3.0 和 Vue 3.5.42。这不是模板没更新，是 uni-app 编译器把这套组合当作经过验证的基线。**不要动它们。**

## 二、模板里的一堆平台包，删掉用不到的

模板默认装了十一个平台的支持包：

```
@dcloudio/uni-mp-alipay    @dcloudio/uni-mp-baidu     @dcloudio/uni-mp-jd
@dcloudio/uni-mp-kuaishou  @dcloudio/uni-mp-lark      @dcloudio/uni-mp-qq
@dcloudio/uni-mp-toutiao   @dcloudio/uni-mp-xhs       @dcloudio/uni-quickapp-webview
@dcloudio/uni-app-harmony  @dcloudio/uni-app-plus
```

我们只做 H5 和微信小程序，其余十个可以不装。打开 `package.json`，把 `dependencies` 里用不到的删掉，只留这几个：

```json [package.json]
{
  "dependencies": {
    "@dcloudio/uni-app": "3.0.0-5020420260813003",
    "@dcloudio/uni-components": "3.0.0-5020420260813003",
    "@dcloudio/uni-h5": "3.0.0-5020420260813003",
    "@dcloudio/uni-mp-weixin": "3.0.0-5020420260813003",
    "vue": "^3.4.21"
  }
}
```

同时 `package.json` 的 `scripts` 里有一大半的脚本（`dev:mp-alipay`、`build:mp-alipay`……）也用不到了。**留着不影响运行**，删了更清爽。这里建议先留着 —— 万一后面想加个支付宝小程序试试，不用再改回来。

删完重新装一次：

```bash
pnpm install
```

**删完必须把两个端都跑一遍**（下一节就做），确认没删错。模板里的包有隐式依赖，删多了会在编译时报找不到模块。

## 三、三个必须看懂的文件

### pages.json —— 这里定义有哪些页面

```json [src/pages.json]
{
  "pages": [
    {
      "path": "pages/index/index",
      "style": {
        "navigationBarTitleText": "校园活动"
      }
    }
  ],
  "globalStyle": {
    "navigationBarTextStyle": "black",
    "navigationBarTitleText": "校园活动",
    "navigationBarBackgroundColor": "#F8F8F8",
    "backgroundColor": "#F8F8F8"
  }
}
```

三个要点：

1. **`pages` 数组的第一项就是启动页**，没有别的入口配置
2. **页面必须在这里注册才能访问**，光有 `.vue` 文件不够 —— 这是和管理端最大的不同，管理端是路由表反过来指向组件，这里是页面清单本身
3. **`path` 不带 `.vue` 后缀**，写 `pages/index/index`，实际文件是 `src/pages/index/index.vue`

### manifest.json —— 各平台的应用配置

这个文件管的是“应用级别”的东西：应用叫什么名字、微信小程序的 AppID 是什么、H5 部署在哪个路径下。

```json [src/manifest.json]
{
  "name": "校园活动学生端",
  "appid": "",
  "description": "校园活动服务平台 · 用户端",
  "versionName": "1.0.0",
  "versionCode": "100",
  "mp-weixin": {
    "appid": "",
    "setting": {
      "urlCheck": false
    },
    "usingComponents": true
  },
  "h5": {
    "router": {
      "base": "/"
    }
  },
  "vueVersion": "3"
}
```

**`mp-weixin.appid` 和顶层的 `appid` 是两回事。** 顶层的 `appid` 由 DCloud 分配（用云服务时才需要），`mp-weixin.appid` 才是微信小程序的 AppID —— 在微信公众平台注册小程序后拿到的那串 `wx` 开头的字符。**现在没注册可以先留空**，微信开发者工具里选“测试号”也能跑。

**`urlCheck: false` 这一条要留意。** 它的意思是“不检查安全域名”，开发阶段必须关掉，否则你连 `localhost:8080` 的接口都请求不了。**但上线前必须改回 `true` 并去微信公众平台配好合法域名** —— 这个开关只是开发期的便利，不是可以带到生产的设置。

### uni.scss —— 全局样式变量

```scss [src/uni.scss]
$uni-color-primary: #42b883;
$uni-text-color: #333;
$uni-bg-color: #f5f5f5;
```

这个文件里定义的变量，**每个组件的 `<style>` 里都能直接用，不用 import**。管理端如果你用了 sass，是要在每个文件里 `@use` 一次的；这里编译器帮你自动注入了。

**别往这个文件里写实际的 CSS 规则**，它只应该放变量。真正的全局样式写在 `App.vue` 的 `<style>` 里。

## 四、跑起来

### 跑在浏览器里

```bash
pnpm dev:h5
```

终端会打印出地址（默认 `http://localhost:3000`）。打开就能看到模板自带的那个页面 —— 白底，中间一行灰字。

**这是最快的一环，也是整个开发过程中你用得最多的一个命令。** 改代码保存，浏览器自动刷新。

### 跑在微信开发者工具里

```bash
pnpm dev:mp-weixin
```

这条命令**不会自动打开任何窗口**，它只是把编译结果输出到 `dist/dev/mp-weixin` 目录，然后一直等着你改代码。

要看到效果，还得打开微信开发者工具（去微信公众平台下载），选“导入项目”，目录选到 `dist/dev/mp-weixin`：

| 导入项 | 填什么 |
| --- | --- |
| 项目目录 | 项目路径 `/dist/dev/mp-weixin` |
| AppID | 有就填自己的，没有点“测试号” |
| 后端服务 | 选“不使用云服务” |

导入之后，左边的模拟器就会显示出页面。

::: tip 两个命令可以同时开
开两个终端窗口，一个跑 `dev:h5`，一个跑 `dev:mp-weixin`。**改一次代码，两端都会重新编译。** 这是日常开发的标准姿势 —— 因为你不知道哪个写法只在某一端出问题。
:::

## 五、装上组件库

`@wot-ui/ui` 是这一栏要用的组件库。它的前身叫 `wot-design-uni`，2026 年换了包名，**搜教程时看到旧名字要认出这是同一个东西的两代**。

```bash
pnpm add @wot-ui/ui
pnpm add -D sass
```

**装 sass 是必须的**，组件库的样式用 scss 写，它的要求是 sass 版本高于 1.78。

### 配置自动引入

组件库有 100 来个组件，**不需要一个个 import**。在 `pages.json` 里加一段 `easycom` 配置：

```json [src/pages.json]
{
  "easycom": {
    "autoscan": true,
    "custom": {
      "^wd-(.*)": "@wot-ui/ui/components/wd-$1/wd-$1.vue"
    }
  },
  "pages": [
    // 省略
  ]
}
```

规则的意思是：**模板里凡是 `<wd-` 开头的标签，都去 `@wot-ui/ui/components/` 下按同名目录找组件文件。**

配好之后，你在任何页面里直接写 `<wd-button>提交</wd-button>` 就能用，不用 import，不用注册。**这套机制叫 easycom，是 uni-app 特有的，管理端没有对应物。**

::: warning easycom 有个坑：改配置不会立即生效
`pages.json` 的 easycom 配置改了之后，**编译器不会重新编译**。你以为写错了，其实只是没生效。

**处理办法：随便改一下某个页面的内容（加个空格再删掉），触发一次重新编译。** 还不行就重启 `dev` 命令。
:::

### 让 sass 不刷警告

sass 1.80 之后废弃了一批旧 API，而 uni-app 仍在使用它们，编译时会刷一片 `Deprecation Warning [legacy-js-api]`。**警告不影响运行，但会淹没有效信息。** 在根目录的 `vite.config.js` 里加一段配置压掉它：

```js [vite.config.js]
import { defineConfig } from 'vite'
import uni from '@dcloudio/vite-plugin-uni'

export default defineConfig({
  plugins: [uni()],
  css: {
    preprocessorOptions: {
      scss: {
        api: 'modern-compiler',
        silenceDeprecations: ['legacy-js-api']
      }
    }
  },
  server: {
    port: 5174,
    proxy: {
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true
      }
    }
  }
})
```

后面那一段 `proxy` 是开发期的跨域代理，**和管理端的 Vite 配置是同一个写法**。这一点是好事：请求地址在两端保持一致，都是 `/api` 开头。

::: details 为什么代理要写在 vite.config.js，而不是 manifest.json
uni-app 的 `manifest.json` 里有个 `h5.devServer` 节点，Vue 3 项目里它对应 Vite 的 `server` 配置。但官方文档明确说：**只支持简单类型的属性，函数等复杂类型不支持。**

`proxy` 里将来如果要写 `pathRewrite` 之类的函数式配置，manifest 里就写不了。**与其分两个地方配，不如统一写在 `vite.config.js` 里** —— 这是标准的 Vite 配置，写法你在管理端已经会了。
:::

## 六、验收：两个端都要能看见

做完这一节，按这个清单自查：

- [ ] `pnpm dev:h5` 能启动，浏览器里能看到页面
- [ ] `pnpm dev:mp-weixin` 能启动，微信开发者工具导入 `dist/dev/mp-weixin` 后能看到同样的页面
- [ ] 在页面里加一个 `<wd-button type="primary">提交</wd-button>`，**两个端都能显示出蓝色按钮**
- [ ] `src/pages.json` 里 `easycom` 配置生效（按钮能显示就说明生效了）
- [ ] 终端里没有 `Deprecation Warning [legacy-js-api]` 刷屏

**第三项是本节的关键验收点。** 组件库能在两个端都正常渲染，说明工程配置没问题，后面可以直接写业务了。

## 小结

- 创建命令是 `npx degit dcloudio/uni-preset-vue#vite 项目名`，**国内失败就换 Gitee 的 zip 包**
- uni-app 的依赖版本格式特殊（`3.0.0-5020420260813003`），**这一组版本要一致，不要单独升级**
- `pages.json` 管页面清单和 easycom，`manifest.json` 管各平台应用配置，`uni.scss` 管全局变量，**三者职责不要混**
- 两个必须有：`pnpm dev:h5` 看浏览器端，`pnpm dev:mp-weixin` 加微信开发者工具看小程序端
- 组件库装完要在 `pages.json` 里配 easycom，**改完这个配置要手动触发一次编译**

## 常见坑

::: details 导入小程序后是白屏，控制台没有明显报错

**现象：** 微信开发者工具里导入 `dist/dev/mp-weixin`，模拟器一片空白，或者提示“找不到 app.json”。

**原因：** 三种可能，按概率排序：

1. **`dev:mp-weixin` 命令没在跑。** 这个命令是编译服务，关掉终端它就不编译了，`dist` 目录里是上一次的残骸
2. **项目目录选错了。** 选了项目根目录，而不是 `dist/dev/mp-weixin`
3. **编译失败但你没注意。** 终端里有红色报错，编译中断了

**怎么处理：** 先看终端有没有报错，再看 `dist/dev/mp-weixin` 里有没有 `app.json` 这个文件 —— **没有就是编译没成功，跟开发者工具没关系。** 确认有之后，在开发者工具里重新导入，目录选到 `dist/dev/mp-weixin`。

:::

::: details 组件库的按钮显示了，但样式全丢

**现象：** `<wd-button>` 渲染成了一个没样式的方块，或者文字堆在一起。

**原因：** sass 没装，或者版本太低。组件库的样式是 scss 写的，**编译器找不到 sass 时不会报错中断，只是样式不生效** —— 这种“不报错的失败”最难查。

**怎么处理：** 确认 `package.json` 的 `devDependencies` 里有 `sass`，跑一下 `pnpm list sass` 看版本是否高于 1.78。没有就 `pnpm add -D sass`，装完重启 `dev` 命令（改了依赖必须重启）。

:::

::: details 两个 dev 命令一起跑，H5 端热更新变得很慢

**现象：** 单开一个 `dev:h5` 时保存代码一秒刷新，同时开 `dev:mp-weixin` 后要等三四秒。

**原因：** 两个进程都要重新编译，抢 CPU。这是正常的资源竞争，不是配置问题。

**怎么处理：** 调页面样式时只开 `dev:h5`，改完准备在小程序里验收了再开另一个。**真正要保证的是“提交前两端都跑过”，不是“随时都开着”。** 机器内存小于 16G 的话，同时开着两个编辑器加两个编译进程会明显卡。

:::

::: details 端口 3000 被占用，启动直接失败

**现象：** `pnpm dev:h5` 报 `Port 3000 is already in use`。

**原因：** 上次没正常退出，进程还在后台跑；或者你之前在这个端口跑过别的项目。

**怎么处理：** 在 `vite.config.js` 里显式指定端口（上面示例里写的是 5174，就是为了跟管理端错开）：

```bash
# 查一下是谁占着
lsof -i :3000
# 确认是自己之前的进程，杀掉
kill -9 <进程号>
```

**建议直接配一个固定端口**，别每次靠系统随机分配，省得连开发者工具时地址还在变。

:::

## 课后练习

**给工程配一个能跑通的请求链路，先不写业务。**

要求：

| 项 | 要求 |
| --- | --- |
| 接口 | 后端管理端的登录接口（见 `docs/project/api.md` 第五章），或任何已存在的接口 |
| 目标 | 在用户端页面里成功拿到一次响应，并把 `code` 打印到页面上 |
| 两个端 | H5 端和微信小程序端都要能拿到 |
| 不许做的 | 不要写请求层封装，直接用 `uni.request` 调一次（封装是下一篇的事） |

在页面上放两个按钮：一个发请求，一个清空结果。请求结果（成功或失败的 `code` 与 `message`）显示在按钮下方。

::: details 验收标准与参考思路

**验收标准：**

| 项 | 要求 |
| --- | --- |
| H5 端 | 点击按钮，页面上出现后端返回的 `code`，不是 `undefined` |
| 小程序端 | 同上，且开发者工具的网络面板里能看到这次请求 |
| 失败也算通过 | 如果后端没起，能在页面上看到“请求失败”的提示，也算通过 —— **但要知道失败在哪一步** |
| 排错记录 | 写下你遇到的跨域或域名问题，以及怎么解决的 |

**不合格的写法：**

```js
// 只在控制台打印，页面上什么都不显示
uni.request({
  url: '/api/auth/login',
  method: 'POST',
  data: { username: 'x', password: 'y' },
  success: (res) => console.log(res)
})
```

问题有两个：**页面看不到结果**（你得一直盯着控制台），**没有处理 `fail` 回调**（请求失败时你什么都不知道）。

**合格的写法：**

```js
const result = ref('还没请求')

function sendRequest() {
  uni.request({
    url: '/api/auth/login',
    method: 'POST',
    data: { username: 'organizer', password: '123456' },
    header: { 'Content-Type': 'application/json' },
    success: (res) => {
      result.value = '状态码 ' + res.statusCode + '，业务码 ' + res.data.code
    },
    fail: (err) => {
      result.value = '请求失败：' + err.errMsg
    }
  })
}
```

**参考思路：**

两端会遇到不同的问题，这是这道练习的重点：

| 端 | 可能遇到的问题 | 怎么确认 |
| --- | --- | --- |
| H5 | 跨域（CORS），请求被浏览器拦掉 | 浏览器控制台会有 CORS 相关报错；配了 `server.proxy` 就不该出现 |
| 微信小程序 | 报“不在以下 request 合法域名列表中” | 开发者工具“详情 → 本地设置”里勾上“不校验合法域名” |

**小程序端更容易踩坑的地方在 `method` 和 `data` 的处理上**：`uni.request` 对 `POST` 加 `application/json` 时，会把 `data` 序列化成 JSON 字符串；如果你的 `header` 没写 `Content-Type`，发出去的可能是表单格式，后端收不到参数。**这是下一节封装请求层要统一处理的事情之一**，先在这里踩一次，下一节印象更深。

:::

---

上一节：[为什么是 uni-app](/mobile/01-why-uniapp) ·
下一节：[页面与路由](/mobile/03-pages-router)
