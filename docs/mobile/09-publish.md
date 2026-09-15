# 9. 打包与发布

## 一个具体的场面

功能做完了，管理端也早在两周前就上线了。现在要把学生端发出去。

**这和管理端上线不一样。** 管理端只要把 `dist` 传到服务器就行；用户端要发两个地方：

- **H5 版本**：传到自己服务器，学生用浏览器打开，也能在微信里点开链接
- **小程序版本**：传到微信平台，学生扫码就用 —— **这是主要入口**

而且小程序不是传上去就能用，**要走一遍上传、设体验版、提交审核的流程**。这一节把两条路都走一遍。

## 一、先改上线前必须改的三处配置

打开 `manifest.json`，有三处是开发阶段可以含糊、上线必须明确的：

```json [src/manifest.json]
{
  "name": "校园活动",
  "versionName": "1.0.0",
  "versionCode": "100",
  "mp-weixin": {
    "appid": "wx1234567890abcdef",
    "setting": {
      "urlCheck": true
    },
    "usingComponents": true
  },
  "h5": {
    "router": {
      "mode": "history",
      "base": "/mobile/"
    }
  }
}
```

| 改什么 | 开发时 | 上线时 | 不改的后果 |
| --- | --- | --- | --- |
| `mp-weixin.appid` | 空着或用测试号 | 真实 AppID | 上传时会报“不是自己的小程序” |
| `mp-weixin.setting.urlCheck` | `false` | **`true`** | 审核通过后所有接口请求不到 |
| `h5.router.base` | `/` | 实际部署路径 | 部署到子目录后资源全部 404 |

::: danger urlCheck 这一条最容易忘
开发时把它设成 `false` 是为了绕开“合法域名”检查。**上线前必须改成 `true`，并去微信公众平台把接口域名加进 `request 合法域名` 列表。**

**忘了改的症状很迷惑**：开发者工具里、体验版里一切正常（因为本地设置也关着检查），**提交审核后被驳回或者上线后白屏**。因为它只在正式环境下才真正生效。
:::

## 二、H5：构建、部署、验证

### 构建

```bash
pnpm build:h5
```

产物在 `dist/build/h5/`。**注意这个路径和 `dev` 不一样**：

| 命令 | 产物位置 | 说明 |
| --- | --- | --- |
| `pnpm dev:h5` | 不落盘（在内存里） | 开发服务器，改代码热更新 |
| `pnpm dev:mp-weixin` | `dist/dev/mp-weixin` | 带 SourceMap，能断点调试 |
| `pnpm build:h5` | `dist/build/h5` | 压缩过，用于上线 |
| `pnpm build:mp-weixin` | `dist/build/mp-weixin` | 压缩过，用于上传 |

**`dev` 和 `build` 的产物分别在两个目录，不要传错。** 传了 `dist/dev` 上去，等于把源码和调试信息一起发布了。

### 走 history 模式还是 hash 模式

上面配置里我写的是 `history`。两种模式的区别要讲清，因为它决定服务器怎么配：

| | hash 模式（默认） | history 模式 |
| --- | --- | --- |
| URL 长什么样 | `https://x.edu.cn/mobile/#/pages/activity/detail?id=1` | `https://x.edu.cn/mobile/activity/detail?id=1` |
| 刷新子页面 | **不会 404**，`#` 后面的部分不发给服务器 | **需要服务端配合**，否则 404 |
| 分享链接 | 带 `#`，看着不专业 | 干净 |
| 服务端配置 | 不需要 | 需要 `try_files` |

**推荐 history 模式**，理由和单元 12 讲的一样：URL 要让用户能看懂、能直接发给别人。代价是服务器要配一行。

### Nginx 配置

```nginx
server {
    listen 443 ssl;
    server_name activity.example.edu.cn;

    # H5 静态文件
    root /var/www/activity-mobile;
    index index.html;

    # history 模式必须有这一段：找不到文件就交给 index.html
    location / {
        try_files $uri $uri/ /index.html;
    }

    # 接口转发到后端
    location /api/ {
        proxy_pass http://127.0.0.1:8080/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # 静态资源缓存（文件名带哈希，可以长缓存）
    location ~* \.(js|css|png|jpg|svg|woff2?)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

**两处要对照单元 12 复习：**

1. **`try_files` 少一行，刷新子路由就 404。** 这是最常见的部署事故。
2. **`index.html` 不能设长缓存。** 上面这段把静态资源的缓存规则限定在 `js|css|png` 这类带哈希的文件名上，**`index.html` 不在其中**，所以它每次都取新的。如果给 `index.html` 也设了 `expires 30d`，前端发版后学生拿到的一直是旧页面。

**`base` 要和部署路径一致：** 部署在 `https://activity.example.edu.cn/mobile/` 下，`base` 就写 `/mobile/`；部署在根路径就写 `/`。

### 部署后的验证清单

```
1. 打开首页，能正常显示活动列表
2. 直接访问一个子路由并刷新（如 /mobile/activity/detail?id=1），不 404
3. 打开浏览器开发者工具的 Network，确认 index.html 的响应头里没有长缓存
4. 手机浏览器打开同一个地址，布局正常
5. 在微信里打开这个链接（发给自己），能打开且不发白
6. 登录、报名能走通（接口转发正常）
```

**第 2 条和第 3 条是最容易出问题的两项**，每次发版都要过一遍。

## 三、微信小程序：上传、体验版、审核

### 构建并上传

```bash
pnpm build:mp-weixin
```

产物在 `dist/build/mp-weixin/`。然后用微信开发者工具打开**这个目录**（不是 `dist/dev/mp-weixin`），点右上角的“上传”：

| 填什么 | 说明 |
| --- | --- |
| 版本号 | 和 `manifest.json` 的 `versionName` 保持一致，比如 `1.0.0` |
| 项目备注 | 写清这次改了什么，比如“报名流程完整版” |

上传成功后，去微信公众平台的操作流程：

```
版本管理 → 开发版本（刚上传的那个）→ 设为体验版 → 提交审核 → 审核通过后发布
```

**体验版是给学生试用的关键一步。** 设为体验版后会生成一个二维码，扫码就能用 —— **不需要审核，不需要发布**。答辩演示用体验版就够了。

### 体验版和正式版的关系

| | 体验版 | 正式版 |
| --- | --- | --- |
| 谁能用 | 你加进“体验成员”名单的人（上限 15 人左右） | 所有人 |
| 需要审核吗 | 不需要 | 需要 |
| 什么时候用 | 内部试用、答辩演示 | 真正给全校学生用 |
| 每次改动 | 重新上传、重新设体验版 | 重新走一遍审核 |

**答辩场景用体验版就够了**，把老师加进体验成员名单即可。省掉审核周期里等待和可能被驳回的麻烦。

### 上线前必做的一件事

去微信公众平台配置服务器域名：

```
开发管理 → 开发设置 → 服务器域名
  request 合法域名：https://activity.example.edu.cn
```

**三个硬要求**：必须是 HTTPS、不能带端口、不能是 IP 地址。**开发阶段用 `http://localhost:8080` 的那套，在这里全都用不了。**

## 四、真机调试

模拟器只能验证逻辑，**下面这些必须在真机上测**：

| 检查项 | 为什么模拟器不可靠 |
| --- | --- |
| 安全区（底部横条） | 模拟器的机型数据未必和真机一致 |
| 软键盘弹起时的布局 | 模拟器不一定模拟键盘行为 |
| 页面滚动性能 | 真机的性能差异大 |
| 分享、扫码等原生能力 | 部分能力模拟器不支持 |
| 弱网表现 | 可以在开发者工具里限速测，但真机更准 |

**怎么在真机上跑：**

```bash
# 小程序：用开发者工具的"预览"按钮，扫码在手机上打开
pnpm dev:mp-weixin     # 编译后，在开发者工具里点"预览"

# H5：让手机和电脑连同一个 Wi-Fi，用电脑的内网 IP 访问
# 先查出内网 IP
ipconfig getifaddr en0      # macOS
# 然后手机浏览器打开 http://192.168.x.x:5174
```

**H5 在手机上访问时接口会失败**，因为 `/api` 代理在 `vite.config.js` 里配的是转发到 `localhost:8080` —— 手机访问 `192.168.x.x` 时，代理的目标是电脑上的 `localhost`，这个是对的。**但要注意 Vite 的开发服务器默认只监听 `localhost`**，手机连不上：

```js
// vite.config.js
export default defineConfig({
  server: {
    host: '0.0.0.0',    // 监听所有网卡，手机才能连上
    port: 5174,
    proxy: {
      '/api': { target: 'http://localhost:8080', changeOrigin: true }
    }
  }
})
```

## 五、体积：什么时候该考虑分包

小程序对包体有大小限制（**主包上限当前是 2MB，具体以微信官方文档为准**），超了上传会失败。

**先别急着分包**，按顺序做这三件事：

| 顺序 | 做什么 | 通常能省多少 |
| --- | --- | --- |
| 1 | 删掉没用到的平台依赖（第 2 篇讲过） | 主要省的是构建时间和磁盘，不影响包体 |
| 2 | 图片压缩、大图放 CDN | 图片通常占大头 |
| 3 | 按需引入组件（easycom 本身就是按需的） | 有限 |
| 4 | **分包** | 把非首页的页面挪出主包 |

分包的配置：

```json [src/pages.json]
{
  "subPackages": [
    {
      "root": "pages-signup",
      "pages": [
        { "path": "form", "style": { "navigationBarTitleText": "报名" } },
        { "path": "my", "style": { "navigationBarTitleText": "我的报名" } }
      ]
    }
  ],
  "optimization": {
    "subPackages": true
  }
}
```

```json [src/manifest.json]
{
  "mp-weixin": {
    "optimization": {
      "subPackages": true
    }
  }
}
```

**注意 `subPackages` 的拼写**（不是 `subpackages`），配错了不生效且不报错。

**分包只影响小程序端，H5 端还是打成一个文件。** 所以对 H5 的体积优化靠的是构建层面的手段（单元 12 讲的那些）。

## 小结

- 上线前必须改三处：**真实 AppID、`urlCheck` 改回 `true`、`h5.router.base` 对齐部署路径**
- `dev` 和 `build` 的产物在不同目录，**别把 `dist/dev` 传上去**
- history 模式 URL 干净但**需要服务端 `try_files`**；hash 模式不用配但 URL 带 `#`
- **`index.html` 绝不能设长缓存**，带哈希的静态资源可以
- 小程序流程是：上传 → 设体验版 → 提交审核 → 发布；**答辩演示用体验版就够**
- 真机必测：安全区、软键盘、滚动、原生能力；**H5 真机调试要把 `server.host` 设成 `0.0.0.0`**
- 包体超限优先查图片，**最后才考虑分包**

## 常见坑

::: details H5 部署后打开是白屏，控制台报 404

**现象：** 传到服务器后打开，页面全白，Network 里一堆 JS 文件 404。

**原因：** `h5.router.base` 和实际部署路径不一致。部署在 `/mobile/` 下但 `base` 写的是 `/`，构建出来的资源引用路径就是 `/assets/xxx.js`，服务器上这个路径不存在。

**怎么处理：** 对齐两处：

| 部署位置 | base 写什么 |
| --- | --- |
| `https://x.edu.cn/`（根路径） | `/` |
| `https://x.edu.cn/mobile/`（子路径） | `/mobile/` |
| 不确定路径、想放哪都能跑 | `./` |

**`./` 这个值很有用** —— 用相对路径，放在任何目录下都能跑。代价是一些路由跳转的场景下相对路径会有歧义，**能确定路径时就写明确的值。**

**排查办法**：先在本地模拟一遍。把 `dist/build/h5` 用一个静态服务器起在子路径下，能打开说明配置对了。这一条比部署上去再查快得多。

:::

::: details 刷新子页面 404，但首页正常

**现象：** 从列表点进详情页没问题，在详情页按 F5 刷新，服务器返回 404。

**原因：** 用的是 history 模式，但 Nginx 没配 `try_files`。服务器收到 `/mobile/activity/detail` 这个请求，去找对应的文件，找不到就 404。

**怎么处理：** 加上这一行：

```nginx
location / {
    try_files $uri $uri/ /index.html;
}
```

**改完要重新加载 Nginx 配置**：

```bash
nginx -t          # 先测语法
nginx -s reload   # 再重载
```

**没有服务器权限的替代方案**：改回 hash 模式（去掉 `mode: "history"`）。URL 会带 `#`，但不需要服务端配合。

:::

::: details 小程序上传报“项目包大小超过限制”

**现象：** 在开发者工具里点上传，弹窗提示包体超限。

**原因：** 主包超了。**最常见的原因是图片没有压缩、或者放在了 `src/static/` 里跟着打包进去。**

**怎么处理：** 按这个顺序查：

1. **看 `static/` 目录有多大** —— 如果活动图片放在这里，全部会被打进包体
2. **大图改走网络** —— 活动封面图应该是后端返回 URL，不是本地文件
3. **检查有没有把设计稿、原型图这类文件误放进 `src/`**
4. 还不够就分包

```vue
<!-- ✗ 本地图片会被打进包体 -->
<image src="/static/activity-cover.png" />

<!-- ✓ 网络图片不占包体 -->
<wd-img :src="item.coverUrl" width="100%" height="320rpx" mode="aspectFill" />
```

**注意 `dev` 模式不检查体积，只有上传时才报。** 所以别等到要交的时候才发现 —— **中期就上传一次试一下。**

:::

::: details 体验版里接口请求失败，开发版却正常

**现象：** 开发者工具里一切正常，扫码用体验版打开，列表是空的，接口请求失败。

**原因：** 体验版是**在真机上跑的正式环境**，走的域名校验和开发者工具的“本地设置”没关系了。三种可能：

1. **`urlCheck` 还是 `false`**，但真机环境不认这个开关（它只影响开发者工具）
2. **接口域名没加进白名单**
3. **接口是 HTTP 不是 HTTPS**

**怎么处理：** 逐项确认：

| 检查 | 怎么查 |
| --- | --- |
| 域名白名单 | 微信公众平台 → 开发管理 → 开发设置 → 服务器域名，看 `request 合法域名` 里有没有你的域名 |
| HTTPS | 浏览器直接访问接口地址，看是不是 443 端口、证书是否有效 |
| 域名不带端口 | 白名单里不能写 `:8080` 这样的端口 |

**这一条和第 2 篇里那个 `urlCheck` 的坑是连着的** —— 开发时关掉检查是为了方便，代价就是**这些问题会推迟到体验版阶段才暴露**。所以建议：**中期就把域名配好，用体验版测一次。**

:::

## 课后练习

**把两个端都发布出去，并写一份部署文档。**

| 任务 | 要求 |
| --- | --- |
| H5 构建 | 用 history 模式，`base` 对齐部署路径 |
| 部署 | 配好 Nginx（含 `try_files` 与 `index.html` 不缓存） |
| 验证 | 完成上面那份 6 条验证清单，每条记录结果 |
| 小程序 | `build:mp-weixin` 后上传，设为体验版 |
| 真机 | 在真机上验证安全区、滚动、分享 |
| 部署文档 | 写清目录、Nginx 配置、更新步骤、回滚办法 |
| 不许做的 | 不要把 `dist/dev` 传上去 |

::: details 验收标准与参考思路

**验收标准：**

| 项 | 要求 |
| --- | --- |
| 子路由刷新 | 在详情页刷新不 404 |
| 缓存策略 | `index.html` 的响应头里没有 `max-age` 长缓存；带哈希的 js 文件有 |
| 手机浏览器 | 布局正常，底部按钮不被横条压住 |
| 微信内打开 | 链接能正常打开，不提示“已停止访问” |
| 体验版 | 扫码能用，登录与报名走通 |
| 部署文档 | 别人照着能部署出来，包括“忘了配 try_files 会怎样”这类说明 |

**不合格的写法：**

```nginx
# ✗ 三个问题
location / {
    root /var/www/activity-mobile;
}

location ~* \.(html|js|css)$ {
    expires 30d;          # index.html 被长缓存了
}
```

第一个问题：没有 `try_files`，刷新子路由 404。第二个问题：把 `html` 也纳入了长缓存，**前端发版后学生看到的还是旧页面**，而且这个问题非常难排查 —— 因为服务器上的文件确实是新的。

**合格的写法：**

```nginx
location / {
    try_files $uri $uri/ /index.html;
}

# 只给带哈希的静态资源设长缓存
location ~* \.(js|css|png|jpg|jpeg|gif|svg|woff2?)$ {
    expires 30d;
    add_header Cache-Control "public, immutable";
}

# index.html 明确不缓存
location = /index.html {
    add_header Cache-Control "no-cache, must-revalidate";
}
```

**参考思路：**

两个地方值得打磨：

**一是部署文档要写“怎么回滚”。** 新版本有问题时，最快的恢复办法是把上一版 `dist` 换回去。**如果部署时把旧的覆盖掉了，那就没得回滚了** —— 所以目录结构要留出历史版本的位置，比如 `releases/2026-03-01/` 加一个 `current` 软链指向当前版本。

**二是那份验证清单要真的逐条做。** 尤其是“刷新子路由”和“检查 index.html 缓存策略”这两条 —— **它们都是在开发环境里 100% 正常、上线后才会出问题的那类**，只能靠部署后主动验证。

:::

---

上一节：[报名表单与我的报名](/mobile/08-signup-form) ·
下一节：[AI 协作](/mobile/10-ai-collaboration) ·
返回：[用户端总览](/mobile/)
