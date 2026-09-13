# 12.3 部署上线

## “在我电脑上是好的”

这句话是开发界的经典笑话，但它描述的是一个真实的问题：**你的电脑上有一堆别人机器上没有的东西。**

- 你本地跑着 Vite 开发服务器（`localhost:5173`），它帮你做了代理转发。
- 你本地的 `node_modules` 里有依赖。
- 你本地的 Node 版本是 24，学校服务器上装的是 18。

部署要做的事是：**把这些依赖全部拿掉，只留一堆静态文件，放到一台任何人都能访问的机器上。**

这一节讲三件事：怎么打出正确的包、怎么用 Nginx 提供服务、怎么验证真的成功了。

## 第一步：打包前最后检查

打包之前有几件事必须先确认。**这些是最常见打包后症状的根源：**

| 检查项 | 为什么 | 怎么改 |
| --- | --- | --- |
| 生产环境的接口地址 | 打包后代理不存在了，接口会请求到自己身上 | `.env.production` 里的 `VITE_API_BASE_URL` |
| `base` 路径 | 部署在子路径时必须改 | `vite.config.js` 的 `base` |
| 路由模式 | history 模式需要服务端回退配置 | 见下面“history 模式 404”一节 |
| 有没有硬编码的 `localhost` | 打包后会请求部署服务器自己的 8080 端口 | 全局搜一下代码 |
| 有没有把密钥写进 `VITE_` 变量 | 会明文出现在产物里 | 全局搜 `.env` 文件 |

### 接口地址的三种部署方式

| 部署方式 | `VITE_API_BASE_URL` 该写什么 | 为什么 |
| --- | --- | --- |
| 前后端同域，Nginx 转发 | `/api` | 请求打到自己域名下的 `/api`，Nginx 转给后端 |
| 前后端不同域 | `https://api.example.com` | 直接请求后端域名，需要后端配 CORS |
| 部署到静态托管平台 | 后端真实地址 | 平台不支持自定义转发 |

**第一种最省事，也是推荐的做法。** 因为同域就不存在跨域问题，也不用后端配 CORS。

```bash [.env.production]
VITE_API_BASE_URL=/api
VITE_APP_TITLE=校园活动服务平台
```

### 先全局搜一遍隐患

```bash
# 搜硬编码的本机地址
grep -rn "localhost\|127.0.0.1" src/ || echo "干净"

# 搜可能泄露的密钥
grep -rn "password\|secret\|api_key\|token" .env* || echo "无 .env 文件"

# 搜遗留的调试代码
grep -rn "console.log\|debugger" src/ | head -20
```

::: warning 打包前必须清掉 `console.log`
不是因为性能，是因为**`console.log` 可能打印敏感信息**。

比如调试时写了：

```js
console.log('登录响应', res)       // 里面包含 token
console.log('用户信息', userStore.userInfo)   // 里面有手机号
```

这些会出现在用户的浏览器控制台里。**别人打开开发者工具就能看到。**

**养成习惯：提交代码之前搜一遍 `console.log`，调试用的全删掉。** 不要指望构建工具帮你清理 —— 那只是兜底。
:::

## 第二步：打包

```bash
pnpm build
```

产物在 `dist/` 目录。看一下里面有什么：

```
dist/
├── assets/
│   ├── ActivityList-a1b2c3d4.js
│   ├── ActivityForm-e5f6g7h8.js
│   ├── index-i9j0k1l2.js
│   ├── index-m3n4o5p6.css
│   ├── element-plus-q7r8s9t0.js
│   └── vue-vendor-u1v2w3x4.js
├── logo.svg
└── index.html
```

**文件名里的那串乱码是哈希值。** 内容变了哈希就变，所以浏览器可以放心地长期缓存 —— 内容没变的话，用户不会重复下载。

先在本地确认产物是好的：

```bash
pnpm preview
```

`preview` 会起一个静态服务器，模拟生产环境的加载方式。**这一步很重要** —— 它和 `pnpm dev` 完全不是一回事。白屏、样式丢失、接口地址不对，都会在这一步暴露出来。

::: details 为什么 `preview` 能发现 `dev` 发现不了的问题
| 差异 | `pnpm dev` | `pnpm preview` |
| --- | --- | --- |
| 模块加载方式 | 按需编译，浏览器里是几十上百个模块 | 打包后的几个文件 |
| 代理配置 | `server.proxy` 生效 | **不生效** |
| 环境变量 | 读 `.env.development` | 读 `.env.production` |
| 代码压缩 | 不压 | 压 |
| 路由处理 | 开发服务器自动回退 | preview 也支持回退 |

**“代理不生效”这一条最致命。** 开发时你的 `/api` 请求被 Vite 转发到 `localhost:8080`，`preview` 时没有代理，请求会打到 `localhost:4173/api`，直接 404。

**这就是为什么生产环境的接口地址必须提前配好。** 在 `preview` 下测接口如果不通，说明配置有问题 —— 而这个问题在 `dev` 下永远看不到。
:::

## 第三步：部署到服务器

这里用一个完整例子走一遍。假设：

- 服务器 IP 是 `10.20.30.40`
- 域名是 `activity.example.edu.cn`
- 部署目录是 `/var/www/activity-admin`
- 后端接口在 `http://127.0.0.1:8080`

### 上传产物

```bash
# 方式一：从本地上传（简单，适合第一次）
scp -r dist/* user@10.20.30.40:/var/www/activity-admin/

# 方式二：在服务器上从 Git 拉代码并构建（推荐）
ssh user@10.20.30.40
cd /var/www
git clone <你的仓库地址> activity-admin-src
cd activity-admin-src
pnpm install
pnpm build
```

**方式二更好的原因**：改一行代码，只需要 `git pull && pnpm build`，不用每次从本地上传整个目录。而且**服务器上构建能保证依赖版本就是 `pnpm-lock.yaml` 里锁定的那份**。

**方式二的前提**：服务器上装了 Node 和 pnpm。检查：

```bash
node -v      # 需要 >= 20.19（课程的基线是 Node 24 LTS）
pnpm -v
```

没装的话，用 fnm 或 nvm 装一个：

```bash
# 用 fnm 装 Node 24
curl -fsSL https://fnm.vercel.app/install | bash
fnm install 24
fnm use 24
# 再装 pnpm
npm i -g pnpm
```

### Nginx 配置

```nginx [/etc/nginx/conf.d/activity-admin.conf]
server {
    listen 80;
    server_name activity.example.edu.cn;

    root /var/www/activity-admin;
    index index.html;

    # ① history 模式必需：找不到的文件回退到 index.html
    location / {
        try_files $uri $uri/ /index.html;
    }

    # ② 静态资源长期缓存：文件名带哈希，内容变了文件名就变
    location /assets/ {
        expires 1y;
        add_header Cache-Control "public, immutable";
        access_log off;
    }

    # ③ index.html 不缓存：否则用户会拿到旧的入口文件
    location = /index.html {
        add_header Cache-Control "no-cache, no-store, must-revalidate";
    }

    # ④ 接口转发给后端
    location /api/ {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # ⑤ 开启 gzip
    gzip on;
    gzip_min_length 1k;
    gzip_comp_level 6;
    gzip_types text/plain text/css application/javascript application/json image/svg+xml;
    gzip_vary on;

    # ⑥ 如果有预压缩的 .gz 文件，优先用它
    gzip_static on;
}
```

**六个配置逐条说。**

**① `try_files`** —— 这是 history 模式能工作的关键，下面单独讲。

**② 静态资源长期缓存** —— `/assets/` 下的文件名都带哈希，内容变了文件名就变。所以可以设一年缓存。

```nginx
expires 1y;
add_header Cache-Control "public, immutable";
```

`immutable` 告诉浏览器“这个文件永远不会变，不要再发请求来检查”。

**收益很明显**：用户第二次访问时，所有 JS / CSS 都直接从本地缓存读，一个字节都不用下载。

**③ `index.html` 不缓存** —— 这是和 ② 配套的，**少了这一条，前面的缓存就成了麻烦**。

原因：`index.html` 里引用了 `index-i9j0k1l2.js`。如果你更新了代码，新文件名是 `index-z9y8x7w6.js`，但用户的浏览器还在用缓存的旧 `index.html`，于是继续加载已经不存在的旧文件 —— 页面白屏。

**所以规则是：带哈希的文件可以缓存一年，入口 html 必须每次都检查。**

**④ 接口转发** —— `proxy_pass http://127.0.0.1:8080` 后面**不要加斜杠**。

这是一个极常见的坑：

```nginx
# ✗ 加了斜杠：请求 /api/activities 会被转成 /activities，后端 404
location /api/ {
    proxy_pass http://127.0.0.1:8080/;
}

# ✓ 不加斜杠：请求 /api/activities 原样转过去
location /api/ {
    proxy_pass http://127.0.0.1:8080;
}
```

**规则**：`location` 路径以斜杠结尾、`proxy_pass` 也以斜杠结尾时，Nginx 会把匹配到的前缀替换掉。加不加这个斜杠，行为完全不同。

**⑤ gzip** —— `gzip_types` 里**不要加 `text/html`**。Nginx 默认就对 HTML 压缩，加进去会有一条警告。

**⑥ `gzip_static on`** —— 如果有构建时预压缩的 `.gz` 文件，优先发送它。没生成 `.gz` 文件的话这一行可以去掉。

### 加载配置并重启

```bash
# 先测试配置语法，这一步能拦下大部分手误
sudo nginx -t

# 语法没问题再重载（reload 比 restart 平滑，不会中断已有连接）
sudo nginx -s reload
```

::: warning 一定要先 `nginx -t`
`nginx -t` 会检查配置语法和文件路径。**跳过这一步直接 reload，配置写错了会导致整个 Nginx 起不来**，服务器上其他站点也跟着挂掉。

`nginx -t` 的输出会告诉你哪一行有问题：

```
nginx: [emerg] unexpected "}" in /etc/nginx/conf.d/activity-admin.conf:47
nginx: configuration file /etc/nginx/nginx.conf test failed
```

**看到这个先去改第 47 行，不要反复 reload 试。**
:::

## history 模式为什么刷新会 404

这是部署时最经典的问题。搞懂它，其他都是细节。

**用户的操作**：在 `https://activity.example.edu.cn/activity` 这个页面按 F5。

**浏览器的行为**：向服务器请求 `/activity` 这个路径。

**服务器的行为**：在 `root` 目录（`/var/www/activity-admin`）下找有没有叫 `activity` 的文件或目录。**没有。** 返回 404。

**问题出在哪**：`/activity` 这个路径在**前端路由表里存在**，在**服务器的文件系统里不存在**。前端路由是虚拟的，服务器不知道。

**解决办法**：告诉服务器“找不到文件就返回 `index.html`”，让前端路由接管。

```nginx
location / {
    try_files $uri $uri/ /index.html;
}
```

这行的意思是：先找 `$uri` 对应的文件 → 没有就找 `$uri/` 目录 → 都没有就返回 `index.html`。

**为什么返回 `index.html` 就对了**：`index.html` 会加载 JS，JS 启动前端路由，前端路由看到地址是 `/activity`，渲染活动列表页。**用户看到的是正确的页面。**

::: details 三种路由模式的对比
| 模式 | 地址长什么样 | 需要服务端配置 | 适用 |
| --- | --- | --- | --- |
| `createWebHistory` | `/activity/42` | **需要** | 常规项目，推荐 |
| `createWebHashHistory` | `/#/activity/42` | 不需要 | 服务端配置改不了的场景 |
| `createMemoryHistory` | 地址栏不变 | 不需要 | 服务端渲染、测试 |

**hash 模式的原理**：`#` 后面的内容**不会发送给服务器**。所以浏览器请求的永远是 `/`，服务器永远返回 `index.html`，不存在 404。

**为什么还是不推荐 hash 模式**：

- 地址难看，`/#/activity/42` 分享给别人显得不专业。
- `#` 后面的内容对搜索引擎不可见（对后台系统影响不大，但如果是面向公众的页面就是问题）。
- URL 里带 `#`，做埋点统计时要特殊处理（很多统计工具默认忽略 `#` 之后的内容）。

**什么时候用 hash**：实在改不了服务端配置（比如只能上传文件到某个共享主机），就用 hash。**这是可接受的降级方案，不是错误方案。**
:::

## 加上 HTTPS

只要涉及登录，就应该上 HTTPS。**没有 HTTPS 的话，token 在网络上明文传输** —— 同一个校园网里的人可以抓包看到。

### 用 Let's Encrypt 免费证书

```bash
# 装 certbot（Ubuntu / Debian）
sudo apt install certbot python3-certbot-nginx

# 自动申请并配置（它会自己改 Nginx 配置）
sudo certbot --nginx -d activity.example.edu.cn

# 测试自动续期
sudo certbot renew --dry-run
```

certbot 会自动做完这几件事：

- 申请证书
- 改 Nginx 配置加 443 端口和证书路径
- 加一条 80 端口跳转到 443 的规则
- 配置一个定时任务自动续期（证书 90 天有效）

改完之后 Nginx 配置大致是这样：

```nginx
server {
    listen 80;
    server_name activity.example.edu.cn;
    # 所有 http 请求跳转到 https
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name activity.example.edu.cn;

    ssl_certificate     /etc/letsencrypt/live/activity.example.edu.cn/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/activity.example.edu.cn/privkey.pem;

    # ...上面那些 location 配置
}
```

### 没有域名怎么办

HTTPS 证书需要绑定域名，用 IP 访问申请不到公共证书。三种办法：

| 办法 | 说明 |
| --- | --- |
| 申请一个免费域名 | 有些平台提供免费二级域名 |
| 自签证书 | `openssl` 生成，浏览器会警告“不安全”，只适合内部测试 |
| 用带 HTTPS 的平台 | 部署到静态托管平台，它们自动提供 HTTPS |

**课程项目推荐最后一种**，见下面“其他部署方式”。

## 其他部署方式

不是每个人都能拿到一台服务器。这里有三种替代方案，都能得到一个能访问的地址。

### 静态托管平台

**Vercel / Netlify / Cloudflare Pages** 都支持静态站点，免费额度对课程项目完全够用。

以 Vercel 为例：

```bash
# 装 CLI
pnpm add -g vercel

# 在项目根目录执行
vercel
```

之后每次 `vercel --prod` 就会重新部署。

**它们自动处理这些事**：

- HTTPS 证书
- gzip / brotli 压缩
- history 模式的回退（会自动识别 SPA）

**唯一要自己处理的是接口调用。** 因为前后端不同域，需要后端配 CORS，或者用平台提供的重写规则（`vercel.json` 里的 `rewrites`）。

```json [vercel.json]
{
  "rewrites": [
    { "source": "/api/(.*)", "destination": "https://api.example.com/api/$1" }
  ]
}
```

**注意**：这种重写是**服务端转发**，不是浏览器跳转，所以不涉及跨域。但请求会经过 Vercel 的服务器，延迟略高。

### 用 Docker

如果服务器上装了 Docker，打一个镜像更省事：

```dockerfile [Dockerfile]
# 构建阶段
FROM node:24-alpine AS builder
WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile
COPY . .
RUN pnpm build

# 运行阶段：只要 Nginx 和产物
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

```bash
docker build -t activity-admin .
docker run -d -p 8081:80 --name activity-admin activity-admin
```

**`--frozen-lockfile` 不能漏** —— 它保证装的依赖版本和锁文件一致。漏了的话 `pnpm install` 可能装到新版本，导致“本地能跑、服务器不能跑”。

**多阶段构建的好处**：最终镜像里只有 Nginx 和几个静态文件，大概 50 MB。如果用单阶段，镜像里会带上整个 `node_modules`，可能 1 GB 以上。

### 打包成压缩包直接给老师

如果只是要交作业，也可以：

```bash
pnpm build
cd dist && zip -r ../activity-admin-dist.zip . && cd ..
```

**但要说明一点**：`dist` 里的 `index.html` **不能直接双击打开**。因为：

- `file://` 协议下加载模块会被浏览器拦截（CORS 限制）
- 路由无法工作
- 接口请求无法跨域

**必须用 HTTP 服务器打开。** 临时起一个：

```bash
# 在最简单的场景下，用 Python 自带服务器
cd dist && python3 -m http.server 8080
```

**所以交作业最好的方式是"线上地址 + 部署脚本 + 部署说明"**，而不是压缩包。如果只能用压缩包，就在说明里写清怎么本地起服务器。

## 部署验证清单

部署完之后，**换一台设备**（手机就行）访问线上地址，逐项验证：

| 检查项 | 怎么验证 | 不通过说明什么 |
| --- | --- | --- |
| 首页能打开 | 直接输入域名访问 | Nginx 配置或 root 路径有问题 |
| 资源加载成功 | Network 面板看 JS / CSS 是不是 200 | `base` 配错了 |
| 压缩已生效 | 响应头里有 `Content-Encoding: gzip` | Nginx 的 gzip 没配或没生效 |
| 接口能通 | 登录成功 | 接口地址或 `proxy_pass` 有问题 |
| **二级路由刷新不 404** | 在 `/activity` 页面按 F5 | `try_files` 没配 |
| **深链接能直接打开** | 直接在地址栏输入 `/activity` | 同上 |
| HTTPS 正常 | 地址栏有锁标志，没有混合内容警告 | 证书没配，或有 http 资源 |
| 静态资源走缓存 | 刷新页面，看 JS 是不是 200 (from disk cache) | 缓存配置没生效 |
| html 不走缓存 | 看 `index.html` 响应头有 `no-cache` | 会出现“更新后白屏” |
| 手机能访问 | 用手机浏览器打开 | 防火墙或只监听了 127.0.0.1 |
| 退出登录正常 | 点退出后回到登录页，再访问后台被拦 | 前端登录态清理有问题 |

::: warning “二级路由刷新不 404”是必测项
这是最容易漏、也最容易在演示时翻车的一项。

**为什么容易漏**：开发时的操作路径都是“点菜单进入某个页面”，从来不会在子路由上按 F5。演示的时候老师说“我来点一下”，随手就是一次刷新 —— 404。

**所以自己先测一遍。** 而且要在多个路由上测，不要只测一个。
:::

::: details 验收时老师可能问的问题，提前准备好答案
| 问题 | 你想过没有 |
| --- | --- |
| 这个地址，我用自己的电脑能打开吗？ | 检查有没有绑 `127.0.0.1`、防火墙有没有放行 80 端口 |
| 为什么用这个域名？ | 能说出域名从哪来的 |
| 前端怎么知道后端地址的？ | 能说清环境变量的作用和打包时机 |
| 如果后端换了一台服务器，你要改什么？ | 能说出改 `.env.production` 重新打包 |
| 你更新了代码，用户需要做什么才能看到新版？ | 能说清 `index.html` 不缓存 + 资源带哈希这套机制 |
| 为什么刷新页面不会 404？ | 能解释 `try_files` 和 history 模式 |
| 接口为什么不会被跨域拦？ | 能说清同域 + Nginx 转发 vs CORS 的区别 |

**第七个问题是核心知识点。** 答不上来的话，说明你是照着配置抄的，没理解为什么。
:::

## 小结

- **部署是把“依赖本机环境”的东西变成“一堆静态文件 + 一台服务器”。**
- **打包前四件事**：生产环境接口地址、`base` 路径、路由模式、清掉 `console.log` 和硬编码地址。
- **`pnpm preview` 必须跑一遍。** 它和 `dev` 差别很大，尤其是代理不生效这一点。
- **Nginx 六个关键配置**：`try_files`（回退）、`/assets/` 长期缓存、`index.html` 不缓存、`/api/` 转发、gzip、`gzip_static`。
- **`try_files $uri $uri/ /index.html;`** 解决 history 模式刷新 404，这是必配项。
- **`proxy_pass` 后面加不加斜杠，行为完全不同。** 路径前缀要对上，别乱加。
- **`index.html` 不缓存 + 带哈希的资源长期缓存**，这两条是配套的，少一条就会出问题。
- **`nginx -t` 必须先跑**，配置写错会导致整个 Nginx 起不来。
- **有登录就必须上 HTTPS**，否则 token 在网络上是明文。
- **没有服务器可以用静态托管平台**，它们自动处理 HTTPS、压缩、SPA 回退。
- **`dist` 不能双击打开**，必须用 HTTP 服务器。
- **验收时一定要在子路由上按 F5。** 这是最容易翻车的一项。

## 常见坑

::: details 部署后页面白屏，Network 里资源 404
**现象**：访问域名，页面全白，控制台报 `Failed to load module script` 或资源 404。

**原因**：`base` 路径配错了。请求的是 `/assets/index-xxx.js`，但实际文件在 `/activity-admin/assets/index-xxx.js`。

**怎么处理**：如果部署在子路径（`https://school.edu.cn/activity-admin/`），必须改 `base`：

```js [vite.config.js]
export default defineConfig({
  base: '/activity-admin/'    // 前后斜杠都不能少
})
```

**另一种情况**：`base` 配了 `./`（相对路径）。这在单页应用里会出问题 —— 因为二级路由（`/activity`）下，`./assets/xxx.js` 会被解析成 `/activity/assets/xxx.js`。

**所以 `base` 只用两种值**：`'/'`（部署在根路径）或 `'/子路径/'`（前后都带斜杠）。**不要用 `'./'`。**
:::

::: details 接口 404，但接口地址看起来是对的
**现象**：线上页面能打开，但所有接口都 404，Network 里请求的地址是 `https://activity.example.edu.cn/api/activities` —— 看起来完全正确。

**原因**：Nginx 的 `location /api/` 和 `proxy_pass` 的斜杠配错了，或者 `location` 的路径没匹配上。

**怎么处理**：按这个顺序查。

**一、确认 `location` 匹配上了。** 看 Nginx 的错误日志：

```bash
sudo tail -f /var/log/nginx/error.log
```

**二、检查斜杠。** 记住这条规则：

| `location` | `proxy_pass` | 请求 `/api/activities` 转成 |
| --- | --- | --- |
| `/api/` | `http://127.0.0.1:8080` | `/api/activities` ✓ |
| `/api/` | `http://127.0.0.1:8080/` | `/activities` ✗ |
| `/api` | `http://127.0.0.1:8080` | `/api/activities` ✓ |

**三、确认后端真的在监听。** 在服务器上直接 curl：

```bash
curl http://127.0.0.1:8080/api/activities
```

**这一步很关键** —— 如果服务器上 curl 后端也不通，说明后端没起来或者没监听对地址（比如只监听了 `localhost` 而 Nginx 走的是 `127.0.0.1`，或者后端在容器里没映射端口）。
:::

::: details 更新代码后，用户还是看到旧版本
**现象**：重新部署了，自己电脑上强制刷新能看到新版，但同事打开还是旧的。

**原因**：`index.html` 被缓存了。

**怎么处理**：加上这条配置：

```nginx
location = /index.html {
    add_header Cache-Control "no-cache, no-store, must-revalidate";
}
```

**为什么之前会缓存 `index.html`**：如果 Nginx 配置里对 `location /` 设了缓存，或者用了某些默认会缓存的托管平台，`index.html` 也会被缓存。**而 `index.html` 是所有问题的入口** —— 它缓存了，用户就永远加载不到新的资源文件名。

**注意 `no-cache` 和 `no-store` 的区别**：

| 指令 | 含义 |
| --- | --- |
| `no-cache` | 可以缓存，但每次使用前必须向服务器验证 |
| `no-store` | 完全不缓存 |

`no-cache` 已经够了（体积本来就很小）。写两个是为了兼容一些老代理的行为。
:::

::: details 手机能打开首页，但登录一直转圈
**现象**：电脑上正常，手机上点登录一直 loading。

**原因**：有三种，都是移动端特有的。

**一、请求被混合内容拦截。** 页面是 HTTPS，但接口地址写的是 `http://`。浏览器会阻止这种请求。控制台会报 `Mixed Content`。

**怎么处理**：`.env.production` 里接口地址用相对路径 `/api`（同域就不存在这个问题），或者用 `https://`。

**二、接口地址写的是内网 IP。** 比如 `VITE_API_BASE_URL=http://192.168.1.100:8080`。电脑在同一个局域网能通，手机用流量访问就连不上。

**怎么处理**：改成公网可访问的地址，或者用相对路径 + Nginx 转发。

**三、超时时间太短。** 手机上网络慢，10 秒超时不够。

**怎么处理**：适当放宽超时，并且**超时要给明确提示**，不能让用户一直看着转圈：

```js
const request = axios.create({ timeout: 15000 })

request.interceptors.response.use(null, (error) => {
  if (error.code === 'ECONNABORTED') {
    ElMessage.error('请求超时，请检查网络后重试')
  }
  return Promise.reject(error)
})
```

**排查方法**：用手机连上电脑的代理（Charles / Whistle / 或者 Chrome 的远程调试），看手机上到底发了什么请求。**光看手机屏幕是查不出来的。**
:::

::: details `sudo nginx -s reload` 报错，网站全挂了
**现象**：改完配置 reload，所有站点都访问不了。

**原因**：配置文件有语法错误，reload 失败后 Nginx 可能处于异常状态。

**怎么处理**：

```bash
# 先测试语法，看具体哪一行错了
sudo nginx -t

# 改好之后再 reload
sudo nginx -s reload
```

**如果 Nginx 已经起不来了**：

```bash
sudo systemctl status nginx     # 看状态和错误信息
sudo journalctl -u nginx -n 50  # 看最近 50 行日志
```

**最稳的做法是先备份再改**：

```bash
sudo cp /etc/nginx/conf.d/activity-admin.conf{,.bak}
# 改配置
sudo nginx -t && sudo nginx -s reload
```

**`-t` 通过才 reload**，这是保命习惯。

**另外**：如果确实改坏了又不知道怎么改回来，先把这个配置文件删掉或改名，让 Nginx 恢复到没有这个站点的状态（至少别的站点能继续工作），再慢慢查。
:::

::: details 用了静态托管平台，接口跨域报错
**现象**：部署到 Vercel，页面正常，接口全部 CORS 报错。

**原因**：前端在 `xxx.vercel.app`，后端在 `api.example.com`，不同域。

**怎么处理**：三种办法。

**一、平台重写规则**（推荐）：

```json [vercel.json]
{
  "rewrites": [
    { "source": "/api/(.*)", "destination": "https://api.example.com/api/$1" }
  ]
}
```

然后把 `VITE_API_BASE_URL` 改成 `/api`。**因为重写是服务端做的，浏览器看到的还是同域请求。**

**二、让后端配 CORS。** 加允许的来源：

```
Access-Control-Allow-Origin: https://xxx.vercel.app
```

**注意不能写 `*`**，如果请求带了 `Authorization` 头或者用了 `credentials`，通配符是不允许的。

**三、换个方式部署。** 如果后端完全改不了、平台重写也不方便，那就找一台能配 Nginx 的服务器。

**判断顺序**：先看能不能改后端（最干净），不能再看平台有没有重写能力，最后才考虑换部署方式。
:::

## 课后练习

::: details 练习 1：完成一次完整部署并写部署文档
把项目部署到一个可以被别人访问的地址上，写一份 `docs/deploy.md`。

**必须包含**：

- 部署环境的说明（服务器的系统、Node 版本、Nginx 版本、目录位置）
- 完整的部署步骤（从拉代码到访问成功）
- Nginx 配置文件全文（附上每一段的作用注释）
- 部署过程中遇到的问题和解决方式
- 如何更新代码（写清楚改代码后要执行哪几条命令）
- 线上地址

**思路提示**：

- “如何更新代码”这一节很容易漏，但它是文档里最实用的部分。写成可以复制执行的形式：

```bash
cd /var/www/activity-admin-src
git pull
pnpm install --frozen-lockfile
pnpm build
sudo cp -r dist/* /var/www/activity-admin/
```

- 判断文档是否合格的标准：**一个没参与项目的人能不能照着这份文档从零部署成功？** 找人试一遍。
:::

::: details 练习 2：写一个自动部署脚本
把部署命令写成一个脚本，一条命令完成部署。

**思路提示**：

```bash [scripts/deploy.sh]
#!/usr/bin/env bash
set -euo pipefail

SERVER="user@10.20.30.40"
REMOTE_DIR="/var/www/activity-admin"
LOCAL_DIST="./dist"

echo "1/4 检查工作区是否干净…"
if [ -n "$(git status --porcelain)" ]; then
  echo "工作区有未提交的改动，请先提交"
  exit 1
fi

echo "2/4 构建…"
pnpm build

echo "3/4 上传…"
rsync -avz --delete "$LOCAL_DIST/" "$SERVER:$REMOTE_DIR/"

echo "4/4 完成，访问 https://activity.example.edu.cn"
```

**三个要点**：

- **`set -euo pipefail`** —— 任何一步失败就退出，不要带着错误继续往下跑。`-u` 是“用了未定义变量就报错”，`-o pipefail` 是“管道里任何一环失败都算失败”。
- **`git status` 检查** —— 工作区有未提交的改动时，服务器拉到的代码和你本地测的不是同一份。**这个检查能避免“我本地明明改好了”这类问题。**
- **`rsync --delete`** —— 删除目标目录里本地没有的文件。**不加的话，旧的文件会一直留在服务器上**（因为文件名带哈希，永远不会被覆盖）。

**注意 `--delete` 有风险**，它会删除目标目录里的多余文件。**所以 `REMOTE_DIR` 必须是一个只放这个项目产物的目录**，不能指向 `dist` 的上级目录。

**再加一步**：脚本执行前先备份当前线上版本，出问题时能快速回滚。

```bash
ssh "$SERVER" "cp -r $REMOTE_DIR $REMOTE_DIR.bak.$(date +%Y%m%d%H%M)"
```
:::

::: details 练习 3：做一次故障演练
故意制造三种故障，验证你的排查能力：

1. 把 Nginx 配置里的 `try_files` 注释掉，然后刷新子路由，看是什么现象。
2. 把 `.env.production` 的接口地址改成 `http://localhost:8080`，重新部署，看是什么现象。
3. 把 `base` 改成 `'/wrong/'`，重新部署，看是什么现象。

每次记录：现象、控制台的报错、Network 里的表现、你是怎么定位的。

**思路提示**：

- 第 1 种现象是 404，**注意此时 F5 刷新挂、点菜单正常** —— 这个“刷新挂但操作正常”的组合特征，能立刻让你想到 history 回退问题。
- 第 2 种现象是接口全部连接失败，Network 里的请求地址是 `http://localhost:8080/api/...`（注意是**用户自己电脑**的 localhost，不是服务器的）。**看到请求地址里有 `localhost` 就立刻知道是打包时的环境变量没配对。**
- 第 3 种现象是白屏 404，Network 里资源路径是 `/wrong/assets/xxx.js`。

**做完这个练习之后，这三个现象你会记一辈子。** 而且下次遇到时，排查时间从半小时降到一分钟。

**演练完记得改回来。**
:::

::: details 练习 4：给项目加上版本号与更新提示
用户停留在页面上，你部署了新版本。请实现“检测到新版本，点击刷新”的提示。

**思路提示**：

- 最简单的做法：把版本号写进 `index.html` 能访问到的地方，页面定时拉一次 `index.html` 或一个 `version.json` 比对。

```js [vite.config.js]
import { writeFileSync } from 'node:fs'

export default defineConfig({
  plugins: [
    {
      name: 'write-version',
      closeBundle() {
        writeFileSync('dist/version.json', JSON.stringify({ version: Date.now() }))
      }
    }
  ]
})
```

```js [src/composables/useVersionCheck.js]
import { ref, onMounted, onUnmounted } from 'vue'

export function useVersionCheck(interval = 5 * 60 * 1000) {
  const hasNewVersion = ref(false)
  let current = null
  let timer = null

  async function check() {
    try {
      const res = await fetch(`/version.json?t=${Date.now()}`)
      const { version } = await res.json()
      if (current === null) {
        current = version
      } else if (version !== current) {
        hasNewVersion.value = true
      }
    } catch {
      // 拉不到就跳过
    }
  }

  onMounted(() => {
    check()
    timer = setInterval(check, interval)
  })
  onUnmounted(() => clearInterval(timer))

  return { hasNewVersion }
}
```

- **注意 `fetch` 要加 `?t=${Date.now()}`** 绕过缓存，否则拿到的永远是缓存的旧版本号。
- **不要自动刷新页面。** 用户可能正在填表单，自动刷新会丢掉数据。**给一个提示，让用户自己决定什么时候刷新。**
- **写一段思考**：这个功能对后台系统有必要吗？（提示：后台系统用户停留时间长、且经常长时间不刷新，价值比较大。如果是电商前台，用户很快就走了，价值小得多）
:::

---

上一节：[12.2 构建优化](/unit12/02-build-optimize) · 下一节：[12.4 交付材料与答辩](/unit12/04-delivery)
