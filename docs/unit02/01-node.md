# 2.1 Node.js 与版本管理

## 一个几乎每个人都会遇到的报错

克隆了同学的校园活动服务平台仓库，按 `README.md` 敲下第一条命令：

```bash [终端]
pnpm install
```

终端吐出一段红字：

```text [报错输出]
 ERR_PNPM_UNSUPPORTED_ENGINE  Unsupported environment (bad pnpm and/or Node.js version)

Your Node version is incompatible with "/Users/you/projects/campus-activity-admin".

Expected version: >=20.19.0
Got: v18.20.4
```

这时候多数人的第一反应是“把 Node 卸了装最新版”。但装最新版有两个风险：一是别的项目
可能又跑不起来；二是下一次换项目还要重来一遍。**正确做法是让机器同时装多个 Node 版本，
按项目切换。**

这一节先把 Node 是什么说清楚，再讲怎么管版本。

## Node 到底是什么

一句话：**Node 是一个可以脱离浏览器运行 JavaScript 的程序。**

浏览器的 JavaScript 引擎叫 V8，Node 把 V8 抠出来，外面包了一层“能读文件、能开网络端口、
能运行子进程”的能力，就成了 Node。所以 Node 能做的事，浏览器里的 JS 做不了；
浏览器里能做的事（比如操作页面上的 DOM），Node 也做不了 —— 它根本没有 DOM 这个概念。

在前端工程里，Node 承担两类活：

| 角色 | 具体例子 | 你要不要写这部分代码 |
| --- | --- | --- |
| 工具链的运行环境 | `pnpm`、`vite`、`eslint`、`vitest` 都是 Node 程序 | **不用写**，只是在用 |
| 本地开发服务器的执行环境 | `pnpm dev` 启动的那个服务器就是 Node 起的 | 不用写，但要知道它在跑 |

用 `exe` 和 Windows 的关系类比一下：

```text
一个 .exe 文件     ←→  一段 JavaScript 工具代码（比如 vite）
双击运行           ←→  node ./node_modules/vite/bin/vite.js
Windows 操作系统   ←→  Node
```

你不需要会写病毒软件，但你的电脑得有个操作系统才能双击 `.exe`。同理，你不写后端，
但你的机器得装 Node 才能跑 `vite`。

::: tip 顺手验证一下这个说法
在项目目录里执行下面这条命令，看看 `vite` 到底是什么：

```bash [终端]
node -e "console.log(require.resolve('vite/bin/vite.js'))"
```

输出是一个 `.js` 文件的绝对路径。这就是你敲 `pnpm dev` 时真正被执行的那个文件 ——
它是一段 JavaScript，由 Node 运行。

理解了这一点，后面看到“Node 版本不对导致构建失败”就不会觉得莫名其妙：
**工具的代码是用新语法写的，老版本的 Node 读不懂。**
:::

## LTS 与 Current 该怎么选

Node 的版本分两条线：

| 类型 | 含义 | 发布节奏 | 适合谁 |
| --- | --- | --- | --- |
| Current | 最新特性版本，编号为偶数时进入下一轮候选 | 每年 4 月、10 月各发一次 | 想试新特性、给 Node 提反馈的人 |
| LTS（长期支持） | 从 Current 里挑出来的稳定版，维护 30 个月 | 每年 10 月转正一次 | **绝大多数项目、绝大多数人** |

LTS 内部还分阶段：前 12 个月是“活跃维护”，修 bug 也修安全问题；之后 18 个月只修安全问题。

本课程统一用 **Node 24 LTS（代号 Krypton），最低 20.19**。为什么是 20.19 这个具体数字？
因为 Vite 8 用到了 Node 20.19 才稳定的一个模块加载特性，低于它启动就会直接报错。

::: warning 不要追 Current
Current 版本每半年换一次，新语法可能刚合进去就改。**你追不动，也没有必要追。**

判断标准很简单：一个项目写清楚了自己要哪个版本，你就装哪个版本，不要去改它的要求。
:::

## 用 fnm 或 nvm 管版本

版本管理工具解决的就是“多个项目要不同 Node”的问题。主流有两个：

| 工具 | 全称 | 平台 | 特点 |
| --- | --- | --- | --- |
| fnm | Fast Node Manager | Windows / macOS / Linux | 用 Rust 写的，启动快；支持自动切换 |
| nvm | Node Version Manager | macOS / Linux（Windows 用 nvm-windows） | 出现早、资料多，但启动慢一些 |

第 1 周你已经装过其中一个。这里用 fnm 演示，nvm 的命令几乎一一对应。

```bash [安装与常用命令（fnm）]
# 安装 Node 24 的最新版
fnm install 24

# 查看本机装了哪些版本（* 号表示当前正在用的）
fnm list

# 切换到 24
fnm use 24

# 设为默认版本（新开终端就用它）
fnm default 24

# 查看当前版本
node -v
```

nvm 的对应写法是 `nvm install 24`、`nvm use 24`、`nvm alias default 24`。

### 让项目自己声明要哪个版本

光在自己机器上切来切去还不够，**版本要求应该写在项目里，跟着 Git 一起提交**。
两个常见的声明文件：

```text [.node-version]
24.9.0
```

```text [.nvmrc]
24
```

两个文件的作用一样，只是工具不同：fnm 读 `.node-version`，nvm 读 `.nvmrc`。
两个都写、内容一致，是最省事的做法。

再加上 fnm 的自动切换，进目录就自动切版本：

```bash [~/.zshrc（macOS）或 ~/.bashrc（Linux）]
eval "$(fnm env --use-on-cd --shell zsh)"
```

`--use-on-cd` 的意思是：**当你 `cd` 进一个带有 `.node-version` 的目录时，
自动切换到文件里写的版本。** 这样你就不用记“这个项目要哪个版本”。

Windows PowerShell 里对应的写法是：

```powershell [Microsoft.PowerShell_profile.ps1]
fnm env --use-on-cd | Out-String | Invoke-Expression
```

## `engines` 字段：项目对 Node 的硬性要求

`.node-version` 是给版本管理工具看的，`engines` 是给包管理器看的。它写在
`package.json` 里：

```json [package.json]
{
  "name": "campus-activity-admin",
  "engines": {
    "node": ">=20.19.0",
    "pnpm": ">=12.0.0"
  },
  "packageManager": "pnpm@12.4.1"
}
```

三个字段的分工：

| 字段 | 谁读它 | 作用 |
| --- | --- | --- |
| `engines.node` | pnpm / npm | Node 版本不满足时**警告**（默认不阻止安装） |
| `engines.pnpm` | pnpm | 同上，针对包管理器版本 |
| `packageManager` | Corepack | 指定这个项目该用哪个包管理器的哪个版本 |

默认情况下，`engines` 不满足只给警告，安装照样继续。这往往不是好事 ——
装完了再报一堆莫名其妙的错，不如一开始就拦下来。pnpm 提供了严格模式：

```ini [.npmrc]
engine-strict=true
```

加上这一行，版本不满足时 `pnpm install` 会直接失败，并且明确告诉你期望什么、实际是什么。
**本课程的项目统一加上这一行。**

::: tip 为什么第 1 周的报错里能看到 Expected 和 Got
因为那个项目已经配了 `engine-strict=true`。报错里的两行信息刚好回答了排查最重要的两个问题：

- `Expected version: >=20.19.0` —— 要求是什么
- `Got: v18.20.4` —— 你现在是什么

看到这种报错，处理方式就一条：**按它要求的版本装，而不是去改它的要求。**
:::

## 常见的“版本不对”报错长什么样

这一类报错的文案五花八门，但都有共同特征：**报错里会同时出现一个版本号和一句语法或模块相关的抱怨。**
认出来之后，处理方式都一样。

| 报错片段 | 出现场景 | 真实原因 |
| --- | --- | --- |
| `ERR_PNPM_UNSUPPORTED_ENGINE` | 安装依赖时 | `engines` 不满足，且开了严格模式 |
| `You are using Node.js 18.x. Vite requires Node.js version 20.19+` | 启动 `vite` | Vite 自己做了一次版本检查 |
| `SyntaxError: Unexpected token '?'` | 运行工具时 | 老 Node 不认识 `??` 这类新语法 |
| `Cannot find module 'node:path'` | 运行脚本时 | `node:` 前缀在老版本里不完整 |
| `ReferenceError: fetch is not defined` | 代码里用了 `fetch` | 全局 `fetch` 是 Node 18 才稳定的 |
| `The engine "node" is incompatible with this module` | 安装某个依赖 | **某个依赖自己的 `engines` 要求更高** |

最后一行值得单独说。有一种报错不是你的项目要求高，而是某个依赖要求高：

```text [报错输出]
error some-package@3.0.0: The engine "node" is incompatible with this module.
Expected version ">=22". Got "20.19.0"
```

这种时候你有两个选择：**升级 Node**，或者**把那个依赖降到支持当前 Node 的版本**。
选哪个取决于团队能不能一起升级 —— 不要自己一个人升完就提交，别人会跑不起来。

## 版本切换后必须做的一件事

切换 Node 版本之后，**旧的 `node_modules` 可能不再适用**。

原因是有些依赖在安装时会根据当前 Node 版本下载对应的二进制文件（比如构建工具的原生模块）。
你用 Node 18 装了一遍，切到 Node 24 之后那些二进制还是老的，运行时报出各种奇怪的错。

处理方式很简单，切完版本重新装一次：

```bash [终端]
rm -rf node_modules
pnpm install
```

::: danger 不要在不同 Node 版本之间来回切换同一个项目的 node_modules
这不是“重装一下就好了”的麻烦，而是排查成本极高的一类问题 —— 报错位置和真实原因
隔得很远，比如报错在“找不到某个 DLL 或 `.node` 文件”，而原因是三天前切过 Node 版本。

**规则：切了 Node 版本，就重装依赖，并且在排查单里记一笔。**
:::

## 小结

- Node 是工具链的运行环境，本课程不用它写后端服务；`pnpm`、`vite` 都是跑在 Node 上的程序。
- 统一用 **LTS**，不要追 Current。本课程基线是 Node 24 LTS，最低 20.19。
- 用 fnm / nvm 管多版本，配合 `.node-version` 与 `--use-on-cd` 自动切换。
- `engines` 是项目对 Node 的要求，`.npmrc` 里的 `engine-strict=true` 让它从警告变成拦截。
- 看到“Expected / Got”这种报错，按要求的版本装，不要去改项目的要求。
- 切换 Node 版本后要重装 `node_modules`。

## 常见坑

::: details 坑 1：装完新版本，`node -v` 还是老的
**现象**：`fnm install 24` 成功，`fnm use 24` 也成功，但新开一个终端 `node -v` 又变回旧版本。

**原因**：`fnm use` 只对当前这个终端会话生效。新开的终端走的是默认版本。

**处理**：执行 `fnm default 24` 把默认版本改掉，然后检查 shell 配置里有没有
`eval "$(fnm env ...)"` 这一行。没有这一行的话，fnm 的版本设置根本不会注入到终端里。
:::

::: details 坑 2：Windows 上提示“禁止运行脚本”
**现象**：在 PowerShell 里执行 `fnm env | Out-String | Invoke-Expression` 报
`无法加载文件，因为在此系统上禁止运行脚本`。

**原因**：PowerShell 默认的执行策略不允许运行脚本。

**处理**：以管理员身份打开 PowerShell，执行
`Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`，输入 `Y` 确认。
`-Scope CurrentUser` 表示只影响你自己，不改全局策略。
:::

::: details 坑 3：团队里有人 Node 版本高，有人低
**现象**：A 同学在 Node 24 上开发一切正常，B 同学 Node 20 报语法错误，两人代码完全一样。

**原因**：项目没有把版本要求写进仓库，全靠各人自己记得。

**处理**：按顺序做三件事 —— 提交 `.node-version`、在 `package.json` 里写 `engines`、
在 `.npmrc` 里加 `engine-strict=true`。

**判断标准：新同学克隆下来之后，不做任何额外确认就能跑起来。** 做不到就是配置没写全。
:::

::: details 坑 4：升级 Node 之后 ESLint 报一堆 `Parsing error`
**现象**：切到 Node 24 后，`pnpm lint` 报大量语法解析错误，代码却没改过。

**原因**：`node_modules` 是旧版本时代装的，里面的解析器二进制和当前 Node 不匹配。

**处理**：删掉 `node_modules` 重装。如果还不行，再清一次 pnpm 缓存
（`pnpm store prune`），然后再装。

**记住顺序：先重装，再清缓存。** 反过来做会多花十几分钟下载。
:::

::: details 坑 5：`packageManager` 字段和实际用的包管理器不一致
**现象**：`package.json` 里写的是 `"packageManager": "pnpm@12.4.1"`，但你在用 npm 安装，
结果报 `This project is configured to use pnpm`。

**原因**：Corepack 读到了 `packageManager` 字段，发现你用的不是它指定的工具。

**处理**：两条路 —— 要么按它的要求用 pnpm；要么在执行时关掉 Corepack 检查。
**推荐第一条** —— 字段是团队统一约定的，不要为了图方便绕过去。
:::

## 课后练习

::: details 练习 1：给你的机器装两个 Node 版本
要求：装上 Node 24 和 Node 20.19，能在同一个终端里来回切换，并把切换结果记录下来。

命令思路：

```bash [终端]
fnm install 24
fnm install 20.19.0
fnm list
fnm use 20.19.0 && node -v   # 应该是 v20.19.x
fnm use 24 && node -v        # 应该是 v24.x
```

**验收点**：`fnm list` 里有两个版本，且 `*` 号会跟着 `fnm use` 移动。
如果在某个版本下 `node -v` 输出的还是另一个版本，说明 shell 配置有问题，回去查坑 1。
:::

::: details 练习 2：造一个“版本不对”的报错
在练习目录里建一个最小项目，故意把 `engines` 写成超出你当前版本的范围，
加上 `engine-strict=true`，然后执行 `pnpm install`，观察报错。

```json [package.json]
{
  "name": "engine-test",
  "version": "1.0.0",
  "private": true,
  "engines": { "node": ">=99.0.0" }
}
```

```ini [.npmrc]
engine-strict=true
```

**为什么值得做**：你把报错“制造”出来过一次，以后在真实项目里遇到就不会慌。
注意观察报错里的 `Expected` 与 `Got` 两行 —— 这两行就是排查的全部线索。

**接着做一步**：把 `engine-strict=true` 去掉再装一次，看看是不是只给警告不报错。
对比之后你就明白这个配置的作用了。
:::

::: details 练习 3：写一份 .node-version 并验证自动切换
在项目里创建 `.node-version`，内容写 `20.19.0`。然后：

1. 确保 shell 配置里有 `--use-on-cd`。
2. 退出当前目录，再重新进入。
3. 执行 `node -v`，看是否自动切成了 `20.19.0`。

**没生效怎么办**：先确认 `fnm env --use-on-cd` 这一行在配置文件里（不是 `.zshrc` 写成了
`.bashrc`），然后 `source ~/.zshrc` 让配置生效，再试一次。

**进阶**：把 `.node-version` 改成 `24`，再进一次目录，看是否切换。
体会一下“写大版本号”和“写精确版本号”的区别 —— 前者会自动用最新的 24.x。
:::

::: details 练习 4：认出五条报错分别是什么原因
下面五条报错，分别是什么问题、第一步该查什么？不查资料，凭这一节学到的内容回答。

1. `ERR_PNPM_UNSUPPORTED_ENGINE ... Expected version: >=20.19.0, Got: v18.20.4`
2. `SyntaxError: Unexpected token '??'`
3. `error vite@8.3.0: The engine "node" is incompatible with this module. Expected ">=20.19"`
4. `pnpm: command not found`
5. `fnm: command not found`

**参考思路**：区分三件事 —— **Node 版本不对**（1、3）、**语法特性不支持**（2）、
**工具本身没装或没进 PATH**（4、5）。第 4 题如果 Node 是好的，说明 pnpm 没装；
第 5 题说明 fnm 装了但 shell 没加载，回去查 shell 配置。

**关键判断**：报错里出现 `Expected` / `Got` 就是版本问题；出现 `command not found`
就是安装或 PATH 问题。这两类占日常报错的一大半。
:::

---

上一节：[单元 2 导学](/unit02/) ·
下一节：[2.2 包管理器与依赖安装](/unit02/02-package-manager)
