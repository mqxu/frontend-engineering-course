# 1.4 开发环境搭建与自检

## 这一节的目标

把环境装好，并**通过自检**。听起来是体力活，但这一步做不干净，后面每个单元都会出问题 ——
而且是那种"报错信息看不懂、不知道从哪查"的问题。

所以这一节有两个要求：

1. **每一步都跑验证命令**。不要一口气装完再回头验证，一旦中间某步错了，后面全跟着错。
2. **把过程记下来**。装环境时遇到的报错和解决办法，写进你的环境自检报告。

详细版说明在[开发环境准备](/guide/environment)，包含原理与其他平台的安装方式。这一节按课堂节奏走，
是精简的操作版。

## 要装的东西

| 工具 | 版本要求 | 作用 |
| --- | --- | --- |
| Node.js | 24 LTS（最低 20.19） | 工具链的运行基础 |
| pnpm | 12.x | 装依赖 |
| VSCode | 最新版 | 写代码 |
| Chrome / Edge | 最新版 | 调试页面 |
| Git | 2.40 以上 | 版本管理 |

::: tip 为什么是 Node 24
Node 24（代号 Krypton）是当前的长期支持版本，维护到 2028 年。Node 22 是维护版，能跑但不建议新环境再用。

**不要用 Current 版本做课程作业** —— 它每几个月就大版本更新，教学环境容易出现"你和同学跑的不是一个东西"。
:::

## 步骤一：装 Node（用版本管理工具）

::: warning 不要直接下载安装包
直接装会带来一个麻烦：项目 A 要 Node 20、项目 B 要 Node 24 时，你只能来回卸载重装。
用版本管理工具，切换只需要一行命令。
:::

**macOS / Linux**

```bash [终端]
brew install fnm
echo 'eval "$(fnm env --use-on-cd)"' >> ~/.zshrc
source ~/.zshrc
fnm install 24
fnm default 24
```

**Windows**

```powershell [PowerShell]
winget install Schniz.fnm
# 装完后新开一个终端
fnm install 24
fnm default 24
```

**验证**

```bash [终端]
node -v   # 期望 v24.x.x
npm -v    # 期望 11.x 或更高
```

::: details 输出是 "command not found"
九成是环境变量没生效。**先关闭终端重新打开**（不是新开标签页，是完全退出）。还不行就检查初始化语句
是否写进了正确的文件：zsh 用 `~/.zshrc`，bash 用 `~/.bash_profile`。
:::

## 步骤二：装 pnpm

```bash [终端]
npm install -g pnpm
```

**验证**

```bash [终端]
pnpm -v   # 期望 12.x
```

::: details 为什么用 pnpm 而不是 npm
三个原因：

1. **快** —— 装同样的东西，pnpm 通常比 npm 快一倍以上。
2. **省磁盘** —— 依赖用硬链接共享，十个项目共用一份 Vue，而不是存十份。
3. **严格** —— 你没在 `package.json` 里声明的包，pnpm 不让你 import。这会把"幽灵依赖"提前暴露出来，
   避免出现"我本地能跑，别人拉下来报 `Cannot find module`"。
:::

## 步骤三：装编辑器扩展

VSCode 装好后，**必须**装这四个扩展：

| 扩展 | 作用 |
| --- | --- |
| Vue - Official | `.vue` 文件的语法高亮、类型提示、格式化 |
| ESLint | 在编辑器里实时标出代码问题 |
| Prettier - Code formatter | 保存时自动格式化 |
| EditorConfig for VS Code | 统一缩进与换行符 |

然后改两个设置（`Ctrl + ,` 打开设置，搜下面两项）：

| 设置项 | 值 | 为什么 |
| --- | --- | --- |
| Editor: Format On Save | 勾选 | 保存即格式化，省掉一堆格式争论 |
| Files: Eol | `\n` | 避免 Windows 与 macOS 之间因换行符产生整文件级的假冲突 |

::: warning 装完扩展要重启 VSCode
扩展装完不重启，有时不会生效 —— 表现为"代码里明明有错误但没标红"。
:::

## 步骤四：浏览器准备

用 Chrome 或 Edge，按 `F12` 打开开发者工具。这几个面板你后面会反复用：

| 面板 | 用来干什么 |
| --- | --- |
| Console | 看报错、临时执行一段代码 |
| Elements | 看 DOM 结构和最终生效的 CSS |
| Network | 看接口的地址、参数、状态码、响应内容 |
| Application | 看 localStorage 里的登录凭证 |

::: tip 建议装 Vue.js devtools
它能在浏览器的开发者工具里多出一个 "Vue" 面板，直接看到组件树、
每个组件当前的 props 和状态。排查"数据没传过去"这类问题时，
比在代码里插 `console.log` 快得多。
:::

## 步骤五：配置 Git

```bash [终端]
git config --global user.name "你的姓名"
git config --global user.email "你的邮箱"
git config --global init.defaultBranch main
git config --global core.autocrlf input
```

最后一条是换行符处理：提交时把 Windows 的 `\r\n` 统一转成 `\n`，检出时不转换。
**团队协作时这一条能省掉大量"整个文件都显示为改动"的假冲突。**

**验证**

```bash [终端]
git config --global user.name
git config --global user.email
```

两条都能输出正确内容即可。

## 完整自检清单

逐项跑一遍，全部打勾才算环境就绪：

- [ ] `node -v` 输出 `v24.` 开头
- [ ] `npm -v` 输出 11 以上
- [ ] `pnpm -v` 输出 12 开头
- [ ] VSCode 装好四个扩展，且保存文件时能自动格式化
- [ ] 浏览器 `F12` 能打开开发者工具，Console 里输入 `1 + 1` 得到 `2`
- [ ] `git config --global user.name` 能输出你的名字
- [ ] 能创建一个测试仓库并完成一次提交

**一条命令跑完主要检查：**

```bash [终端]
node -v && npm -v && pnpm -v && git --version
```

期望输出大致是这样（版本号可能略有差异）：

```text [期望输出]
v24.21.0
11.6.2
12.4.1
git version 2.43.0
```

::: details 顺手验证一次 Git 提交流程
```bash [终端]
mkdir ~/git-test && cd ~/git-test
git init
echo "# 测试" > README.md
git add README.md
git commit -m "chore: 初始化测试仓库"
git log --oneline
```

能输出一行提交记录，说明 Git 配置正确。验证完可以把这个目录删掉。
:::

## 常见报错速查

| 报错 / 现象 | 原因 | 解决 |
| --- | --- | --- |
| `command not found: node` | Node 没装好或环境变量没生效 | 完全退出终端重开；检查 shell 配置文件里的初始化语句 |
| `无法加载文件，因为在此系统上禁止运行脚本`（Windows） | PowerShell 执行策略太严 | 管理员运行 `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` |
| `pnpm install` 卡住不动 | 网络问题 | `pnpm config set registry https://registry.npmmirror.com` |
| `Cannot find module 'xxx'` | 依赖没装 / 装错位置 / 目录不对 | 确认在 `package.json` 所在目录执行；删掉 `node_modules` 重装 |
| `EACCES: permission denied` | 权限不足，常见于全局安装 | macOS 用 `sudo`；Windows 用管理员终端 |
| `Unsupported engine` | Node 版本太低 | `fnm install 24 && fnm use 24` |
| 编辑器里 `.vue` 文件没有高亮 | 扩展没装或没重启 | 装 Vue - Official，重启 VSCode |

更多问题见[常见报错与排查](/appendix/errors)。

## 环境自检报告怎么写

这是本单元的产出之一。**它不是截图堆砌，而是一份能说明"我的环境是什么状态"的记录。**

一个合格的报告长这样：

```md [环境自检报告.md]
# 环境自检报告

## 一、版本信息

| 工具 | 版本 | 安装方式 |
| --- | --- | --- |
| Node | v24.21.0 | fnm |
| npm | 11.6.2 | 随 Node 安装 |
| pnpm | 12.4.1 | npm install -g |
| Git | 2.43.0 | Homebrew |

## 二、自检清单结果

- [x] node -v 输出 v24 开头
- [x] npm -v 输出 11 以上
- [x] pnpm -v 输出 12 开头
- [x] VSCode 四个扩展已装，保存自动格式化生效
- [x] 浏览器 F12 可用
- [x] git config 已配置
- [x] 完成一次测试提交

## 三、遇到的问题与解决

**问题**：装完 fnm 后 `node -v` 提示 command not found。
**排查过程**：先怀疑没装成功，用 `fnm list` 看到版本已经装上了，说明是环境变量问题。
**解决**：发现初始化语句写进了 `~/.bash_profile`，但我的 shell 是 zsh。
改写到 `~/.zshrc` 后重新加载，问题解决。
**学到的**：环境变量问题先确认"当前用的是什么 shell"，`echo $SHELL` 可以查。
```

::: tip 报告里最有价值的是第三部分
"遇到的问题与解决"这一栏不是形式主义。这一次记下的排查思路，会在后面每个单元反复用上 ——
**因为工程化遇到的问题，八成都是环境、版本、路径这三类。**
:::

## 小结

- 用版本管理工具装 Node（fnm 或 nvm），不要直接下载安装包。
- pnpm 比 npm 快、省磁盘、更严格，教学统一用 pnpm。
- 编辑器要装四个扩展，并且**打开保存自动格式化**。
- Git 的换行符设置（`core.autocrlf input`）能避免大量假冲突。
- 每一步都跑验证命令，不要一次性装完再验证。
- 环境自检报告的重点是"遇到的问题与解决过程"。

## 常见坑

::: details 坑 1：用安装包直接装 Node，后来又装 fnm
两个 Node 共存时，`node -v` 显示的可能是安装包那个旧版本。

**处理方法**：macOS 卸载掉 `pkg` 安装的 Node（`/usr/local/bin` 下相关文件），Windows 从
"添加或删除程序"里卸载，然后只用 fnm 管理。
:::

::: details 坑 2：全局安装了项目依赖
```bash
npm install -g vue    # ✗ 不要这样
```

全局装的包，项目的 `package.json` 里没有记录，别人拉下代码跑不起来，
自己也说不清用的是哪个版本。**依赖一律装到项目本地。**
:::

::: details 坑 3：把 `node_modules` 拷给同学
`node_modules` 里有大量针对当前操作系统的二进制文件，拷到别的系统大概率报错。

正确做法是把 `package.json` 和锁文件给对方，让他自己 `pnpm install`。
:::

::: details 坑 4：改了配置没重启
Vite 的配置文件（`vite.config.js`）改完需要重启开发服务器才生效。
排查"配置明明改了却没生效"时，先重启再怀疑其他原因。
:::

## 课后练习

::: details 练习 1：完成环境自检报告
按上面的模板写一份完整报告，包含版本信息、自检清单、遇到的问题与解决过程。

**参考思路**：如果没有遇到任何问题，就写一条"最容易出错的环节"作为替代 ——
比如解释"为什么 `core.autocrlf` 要设成 `input`"。关键是要有思考，不能只填空。
:::

::: details 练习 2：故意制造一个错误
在测试项目里执行下面这条命令，观察报错内容，然后解释报错在说什么：

```bash [终端]
pnpm add vue@99.99.99
```

**参考思路**：报错会提到"No matching version found"。**重点不是这个错误本身，而是养成读报错的习惯** ——
npm 的报错最后几行通常已经写清了原因（`No matching version found for vue@99.99.99`）
和可用版本范围。学会看这几行，能省一半搜索时间。
:::

::: details 练习 3：验证换行符设置的作用
1. 把 `core.autocrlf` 设置为 `true`，提交一次一个文本文件的修改。
2. 改回 `input`，再提交一次。
3. 用 `git diff` 观察两次的差异描述有什么不同。

**参考思路**：`true` 模式下 Git 会在提交时转换换行符，可能让 `git status` 显示整个文件被改动。
这个练习的目的是让你亲眼看到"配置不同会导致什么现象"，而不是记住结论。
:::

---

上一节：[1.3 学习路线与岗位方向](/unit01/03-learning-path) ·
下一节：[单元 1 课后练习](/unit01/practice)
