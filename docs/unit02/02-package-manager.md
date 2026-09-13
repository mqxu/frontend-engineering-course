# 2.2 包管理器与依赖安装

## “我这边能跑，你那边报错”

校园活动服务平台做到第二周，你负责活动列表页，用了 `dayjs` 格式化报名截止时间：

```js [src/utils/format.js]
import dayjs from 'dayjs'

export function formatDeadline(time) {
  return dayjs(time).format('YYYY-MM-DD HH:mm')
}
```

你本地跑得好好的，`pnpm dev` 一切正常。然后你把代码推上去，同组同学拉下来，一运行就报：

```text [同学终端里的报错]
Failed to resolve import "dayjs" from "src/utils/format.js".
Does the file exist?
```

他查了 `package.json`，里面**没有 `dayjs`**：

```json [package.json（出问题的版本）]
{
  "dependencies": {
    "element-plus": "^2.14.5",
    "vue": "^3.5.42"
  }
}
```

那为什么你本地能跑？因为你前两周装 `element-plus` 的时候，`dayjs` 作为它的依赖
被一起装进 `node_modules` 了。你直接 `import 'dayjs'` 能拿到 —— 但这条路是“蹭”来的，
`package.json` 里根本没有声明。这就是**幽灵依赖**。

这一节就把这类问题的来龙去脉讲清楚。

## 三个包管理器有什么不一样

| 对比项 | npm | pnpm | yarn |
| --- | --- | --- | --- |
| 安装速度 | 中等 | 快（内容寻址存储 + 硬链接） | 较快（有全局缓存） |
| 磁盘占用 | 每个项目一份 | 多个项目共享一份 | 每个项目一份（可配 PnP） |
| `node_modules` 结构 | 扁平 | 严格（依赖只能访问自己声明的包） | 扁平 |
| 幽灵依赖 | 存在 | **默认被拦住** | 存在 |
| 锁文件 | `package-lock.json` | `pnpm-lock.yaml` | `yarn.lock` |
| 是否适合 monorepo | 一般 | 好 | 好 |
| 本课程使用 | ✗ | ✓ | ✗ |

本课程统一用 pnpm，原因不是“它更时髦”，而是**它的严格结构能在本地就把幽灵依赖暴露出来**。
换句话说，它让你在提交代码之前发现问题，而不是等同学拉下来才报错。

::: warning 三个包管理器不要混用
一个项目里只用一种，并且**用哪个就在 `packageManager` 字段里写清楚**。

混用的后果很直接：npm 生成 `package-lock.json`，pnpm 读 `pnpm-lock.yaml`，
两边解析出的依赖版本可能不同，于是又回到“我这边能跑”的老路上。
:::

## pnpm 为什么装得快、占得少

先说一个结论：**你机器上装了 10 个 Vue 项目，`vue` 这个包只会被下载一次。**

### 全局存储 + 硬链接

pnpm 把所有下载过的包放在一个全局目录里（叫 store）：

```text
~/Library/pnpm/store/v10/        # macOS 默认位置
├── files/                       # 所有包的文件内容，按内容哈希存放
└── ...
```

每个项目里的 `node_modules` 不复制文件，而是**创建硬链接指向 store**。
硬链接可以理解成“同一个文件的另一个名字”：占用的磁盘空间还是那一份，
但两个路径都能读到它。

```text [终端]
# 看 store 的路径和大小
pnpm store path
du -sh "$(pnpm store path)"
```

对比一下就清楚了：

| 方式 | 10 个项目的磁盘占用 | 安装时要不要重新下载 |
| --- | --- | --- |
| 复制文件 | 10 × 依赖体积 | 每个项目都要下 |
| 硬链接 + 内容寻址 | 约 1 × 依赖体积 | 只下没有的部分 |

### 内容寻址存储（CAS）

“内容寻址”的意思是用**文件内容的哈希值**当文件名。带来的好处有两条：

1. **同一个文件在不同包之间只存一份**。10 个包都用同一个版本的图标文件，store 里只有一份。
2. **校验天然可靠**。文件名就是内容的指纹，下载损坏一眼就能发现。

### 安装快还有第二个原因

pnpm 的安装是分阶段的，能并行的部分尽量并行。而且因为大部分文件已经在 store 里，
“安装”这个动作很多时候只是建链接 —— 建链接比写文件快得多。

::: tip 所以不要随便删 store
`rm -rf node_modules` 之后重装很快，正是因为 store 还在。如果连 store 也删了，
下次装依赖要从头下载。

真要清理 store，用 `pnpm store prune` —— 它只删**没有项目在引用**的那部分，比较安全。
:::

## 严格模式怎么提前暴露幽灵依赖

回到开头的例子。在 npm 的扁平结构下，`node_modules` 长这样（简化）：

```text [npm 的 node_modules（扁平）]
node_modules/
├── element-plus/        ← 你声明的
├── dayjs/               ← 你没声明，但被提升到顶层了，所以能 import 到
└── vue/                 ← 你声明的
```

`dayjs` 本来应该躺在 `element-plus/node_modules/` 里，但 npm 为了减少重复，
把它“提升”到了顶层。结果就是：**你没声明的包，也能 import 成功。**

pnpm 的结构不一样：

```text [pnpm 的 node_modules（严格）]
node_modules/
├── .pnpm/                        ← 真实的包都在这里，按“包名@版本”分目录
│   ├── element-plus@2.14.5/
│   │   └── node_modules/
│   │       ├── element-plus/     ← 软链接
│   │       └── dayjs/            ← element-plus 自己的依赖，只有它能看到
│   └── dayjs@1.11.13/
├── element-plus -> .pnpm/element-plus@2.14.5/node_modules/element-plus
└── vue -> .pnpm/vue@3.5.42/node_modules/vue
```

顶层只有你**在 `package.json` 里声明过的包**。`dayjs` 只出现在 `element-plus` 的
私有目录里，别人拿不到。

于是同一条 `import dayjs from 'dayjs'` 会变成：

```
Failed to resolve import "dayjs" from "src/utils/format.js"
```

**这个报错是好消息。** 它在开发机上报出来，而不是在周报演示时白屏。
处理方式不是“想办法绕过”，而是老老实实安装并写进 `package.json`：

```bash [终端]
pnpm add dayjs
```

::: danger 不要用“再装一个到顶层”的办法绕过
有人会想：既然别的地方能 import 到，那我手动在 `node_modules` 里建个链接不就行了？

不行。这样做的问题是：**`package.json` 依然没声明这个依赖。**
换一台机器、或者重新 `rm -rf node_modules && pnpm install`，问题立刻复现。

判断标准只有一条：**`node_modules` 删掉重装之后还能跑，才算依赖声明正确。**
:::

## 常用命令

```bash [常用命令]
# 安装依赖（读 package.json 和锁文件）
pnpm install

# 添加运行时依赖（写进 dependencies）
pnpm add axios

# 添加开发依赖（写进 devDependencies）
pnpm add -D eslint

# 添加指定版本或范围
pnpm add vue@3.5.42
pnpm add -D "eslint@^10.0.0"

# 移除依赖
pnpm remove dayjs

# 按 package.json 里写的范围升级到最新可用版本
pnpm update

# 只升级某一个包
pnpm update vue

# 查看某个包为什么被装进来（排查依赖来源最有用）
pnpm why dayjs

# 不改 package.json，临时运行一个命令行工具
pnpm dlx create-vue campus-activity-admin
```

`pnpm why` 值得单独说。它是排查“这个包是哪儿来的”的第一工具：

```bash [终端]
pnpm why dayjs
```

输出会告诉你哪些包依赖了 `dayjs`、分别要求什么版本范围。遇到
“怎么多了一个没见过的包”时，第一条命令就是它。

::: tip 装包用 add，不要手改 package.json
手写 `package.json` 再 `pnpm install` 也能装，但有两个小问题：
一是版本号得自己查，容易写成不存在的版本；二是写错了要等安装时才发现。

**用 `pnpm add`，让它负责查最新版、写字段、更新锁文件这三件事。**
:::

## 锁文件为什么必须提交

`pnpm-lock.yaml` 记录的是**一棵解析完成的依赖树**：哪个包用了哪个精确版本、
从哪个地址下载、内容哈希是多少。

它解决的问题是：`package.json` 里写的是**范围**，不同时间安装可能得到不同版本。

```json [package.json 里写的是范围]
{ "dependencies": { "vue": "^3.5.42" } }
```

```yaml [pnpm-lock.yaml 里写的是精确结果]
dependencies:
  vue:
    specifier: ^3.5.42
    version: 3.5.42
```

`^3.5.42` 的意思是“3.5.42 及以上、但不到 4.0.0”。下周 3.5.43 发布了，
A 同学装到 3.5.43，B 同学一个月后装到 3.5.48 —— 两人跑的是不同代码。
**锁文件的作用就是让所有人装出完全一样的依赖树。**

| 文件 | 记录内容 | 谁生成 | 要不要提交 |
| --- | --- | --- | --- |
| `package.json` | 依赖的**范围** | 你（用 `pnpm add`） | 提交 |
| `pnpm-lock.yaml` | 依赖的**精确结果** | pnpm | **必须提交** |

::: warning 锁文件的三条纪律
1. **提交它**，不要放进 `.gitignore`。
2. **不要手改它**。要改依赖就改 `package.json`（用命令），让 pnpm 重新生成锁文件。
3. **不要直接删了重装就提交**。删除锁文件会让所有人的依赖版本范围重新解析一遍，
   可能一次引入好几个不相关的版本变化。
:::

## 依赖装不上时，按这个顺序排查

报错千奇百怪，但原因基本落在五层里。**按下面的顺序查，每次只改一个变量。**

| 顺序 | 查什么 | 怎么查 | 典型现象 |
| --- | --- | --- | --- |
| 1 | 网络与镜像 | `pnpm config get registry`、浏览器打开镜像地址 | `ERR_PNPM_META_FETCH_FAIL`、`ETIMEDOUT` |
| 2 | Node 与包管理器版本 | `node -v`、`pnpm -v`，对照 `engines` | `ERR_PNPM_UNSUPPORTED_ENGINE` |
| 3 | 文件权限 | 看报错里有没有 `EACCES`、`EPERM` | 装到一半失败，或某几个文件失败 |
| 4 | 缓存损坏 | `pnpm store prune` 后重装 | `ERR_PNPM_TARBALL_INTEGRITY`、哈希不匹配 |
| 5 | 锁文件冲突 | 看 Git 有没有冲突标记 | `ERR_PNPM_LOCKFILE_BREAKING_CHANGE` |

展开说前两层和第五层。

### 第 1 层：网络与镜像

国内直连 `registry.npmjs.org` 经常超时。切到国内镜像：

```bash [终端]
pnpm config get registry
pnpm config set registry https://registry.npmmirror.com
```

::: danger 镜像不要写进项目里的 .npmrc
在自己机器上设置全局镜像（上面的命令就是全局的），**不要把镜像地址提交到项目里**。
有的公司有内网镜像，外网的同学拿不到；写进项目会让别人装不了。

个人偏好放在自己的全局配置里；团队统一的东西才写进项目。
:::

### 第 2 层：Node 与包管理器版本

就是 2.1 讲的那套。先看报错里有没有 `Expected` 和 `Got`，有就是版本问题。

### 第 5 层：锁文件冲突

多人协作时 `pnpm-lock.yaml` 会冲突。**不要手动去解冲突**，正确做法是
“以其中一方的 `package.json` 为准，重新生成锁文件”：

```bash [终端]
# 1. 先把 package.json 的冲突解决掉（这部分必须人工判断）
# 2. 删掉冲突过的锁文件，重新生成
rm pnpm-lock.yaml
pnpm install
# 3. 检查 git 状态，确认锁文件是重新生成的，然后提交
git status
```

注意第 1 步必须人工判断 —— `package.json` 里的冲突是**真实意图的冲突**，
到底要保留哪个依赖、用哪个版本范围，只有你知道。锁文件是结果，`package.json` 是原因，
先定原因再生成结果。

::: tip 预防锁文件冲突的两条习惯
1. **每次拉代码之后先装依赖**，不要在旧锁文件上继续开发。
2. **改依赖单独提交**。不要在一次提交里既改业务代码又升级依赖 ——
   后者会让冲突解决时无从判断哪部分是你的意图。
:::

## 小结

- npm / pnpm / yarn 的核心差别在 `node_modules` 结构：pnpm 是严格的，能拦住幽灵依赖。
- pnpm 用全局 store + 硬链接 + 内容寻址存储，所以省磁盘、装得快。
- 幽灵依赖是“没声明却能 import 到”的包，`package.json` 里必须显式声明。
- 常用命令：`add`、`add -D`、`remove`、`update`、`why`、`dlx`。
- 锁文件记录精确依赖树，**必须提交，不要手改**。
- 安装失败按五层排查：网络与镜像 → Node 版本 → 权限 → 缓存 → 锁文件冲突。

## 常见坑

::: details 坑 1：删了 node_modules 重装还是同样报错
**现象**：报错说某个包有问题，删掉 `node_modules` 重装，一模一样。

**原因**：有两种可能 —— 锁文件本身有问题，或者 pnpm store 里的那份文件是坏的。
删 `node_modules` 只是删了链接，store 里的坏文件还在。

**处理**：先 `pnpm store prune` 清掉缓存里没人引用的部分，再删 `node_modules` 重装。
还不行的，按 2.1 的坑 4 检查 Node 版本是否和当初装的时候一致。
:::

::: details 坑 2：CI 上装依赖报锁文件不匹配
**现象**：本地好的，流水线里 `pnpm install --frozen-lockfile` 报
`Cannot install with "frozen-lockfile" because pnpm-lock.yaml is not up to date`。

**原因**：你改了 `package.json` 却没有把更新后的锁文件一起提交。

**处理**：本地执行 `pnpm install`，把更新后的 `pnpm-lock.yaml` 一起提交。

**为什么会用 `--frozen-lockfile`**：CI 里要的就是“不许改锁文件，只能按它装”。
这样能确保流水线装出来的依赖和你本地完全一致。**这条报错是好事，它在提醒你漏提交了文件。**
:::

::: details 坑 3：`pnpm why` 输出一堆，看不懂
**现象**：执行 `pnpm why dayjs` 输出十几行，不知道该看哪一行。

**原因**：`dayjs` 可能被好几个包同时依赖，`why` 会把所有路径都列出来。

**怎么读**：看**最后一层**。每条路径的最后一跳就是直接依赖它的那个包。
如果你只想知道“是不是我自己装的”，往下看 `package.json` 里有没有 ——
`why` 的输出会区分“直接依赖”和“间接依赖”。
:::

::: details 坑 4：三个人用三种包管理器
**现象**：仓库里同时出现 `package-lock.json`、`pnpm-lock.yaml`、`yarn.lock`，
每个人的改动都很大。

**原因**：项目没写 `packageManager` 字段，各人凭习惯用。

**处理**：定一个（课程里定 pnpm），删掉其余锁文件，在 `package.json` 里写：

```json [package.json]
{ "packageManager": "pnpm@12.4.1" }
```

然后在 `.gitignore` 里不需要额外加什么 —— 但要在 `README.md` 里写清“本项目用 pnpm”。
**新同学照着 README 做，就不会用错。**
:::

::: details 坑 5：以为 `pnpm add -D` 是“装个小一点的版本”
**现象**：把 `axios` 用 `-D` 装进去了，本地跑没问题，打包后线上报错。

**原因**：理解反了。`-D` 是 `--save-dev` 的缩写，意思是“写进 `devDependencies`”，
和包的大小、版本都没有关系。

**判断方法**：把 `node_modules` 删掉、只部署构建产物，这个包还需要存在吗？
需要就放 `dependencies`，不需要才是 `devDependencies`。

**`axios` 要放 `dependencies`** —— 它会被 import 进业务代码，进入最终产物。
:::

## 课后练习

::: details 练习 1：制造并修复一个幽灵依赖
任务：在练习项目里故意写出一次幽灵依赖，观察 pnpm 的报错，然后正确修复。

思路：

1. 先 `pnpm add element-plus`，然后**不安装 `dayjs`**，直接
   `import dayjs from 'dayjs'` 并在页面里用一下。
2. 启动 `pnpm dev`，看报错是不是 `Failed to resolve import "dayjs"`。
3. 用 `pnpm why dayjs` 看看这个包是不是被 `element-plus` 间接装进来的。
4. 用 `pnpm add dayjs` 正确修复。

**验收点**：`package.json` 的 `dependencies` 里出现 `dayjs`，
并且 `rm -rf node_modules && pnpm install` 之后仍然能跑。
:::

::: details 练习 2：读一次锁文件
打开 `pnpm-lock.yaml`，找到 `vue` 这一项，回答三个问题：

1. `specifier` 是什么？`version` 是什么？两者有什么区别？
2. 文件里有没有 `integrity` 字段？它是干什么的？
3. 把 `package.json` 里 `vue` 的范围从 `^3.5.42` 改成 `~3.5.42`，
   执行 `pnpm install`，锁文件里哪些内容变了？

**参考思路**：`specifier` 是你写的范围，`version` 是解析出的精确版本。
`integrity` 是内容哈希，用来校验下载的文件没被改过。
第三问的关键是：范围变小之后，如果当前装的版本仍然满足，锁文件的 `version` 不变，
只有 `specifier` 变 —— **这正是锁文件“锁住结果”的价值。**
:::

::: details 练习 3：写一份依赖排查单
按 [2.2 的排查顺序](/unit02/02-package-manager#依赖装不上时按这个顺序排查)，
给自己遇到的**每一个**安装报错建一条记录。

至少记录三条。格式：

| 时间 | 报错原文 | 排查到了哪一层 | 试了什么 | 结果 | 结论 |
| --- | --- | --- | --- | --- | --- |

**验收点**：至少有一条能明确说出“是第几层的问题”。
如果三条都只写了“重装就好了”，说明排查过程记录得还不够细 ——
回去把每次动作补上：改了哪个配置、命令输出有什么不同。

**这份排查单就是这个单元的产出之一**，后面还要用。
:::

::: details 练习 4：对比 npm 与 pnpm 的 node_modules 结构
在同一个最小项目里，分别用 npm 和 pnpm 装一次 `element-plus`，然后用
`ls node_modules | head -30` 对比两边的顶层目录。

回答：

1. npm 那边顶层有多少个包是你**没有**声明的？
2. pnpm 那边顶层有哪些？和 `package.json` 的 `dependencies` 对得上吗？

**参考思路**：npm 那边你会看到几十个没声明的包（都是被提升上来的），
pnpm 那边顶层基本只有 `.pnpm`、`.modules.yaml` 和你声明的包。

**这个对比就是这一节最直观的证据。** 亲手做过一次，以后看到幽灵依赖的报错
就不会以为是“pnpm 有问题”了。
:::

---

上一节：[2.1 Node.js 与版本管理](/unit02/01-node) ·
下一节：[2.3 package.json 逐字段精讲](/unit02/03-package-json)
