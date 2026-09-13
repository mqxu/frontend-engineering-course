# 开发环境准备

这一页的目标很明确：**在干净机器上把前端开发环境装好，并且能通过自检。**

装环境失败是新手最常见的卡点，而且失败的体验很糟 —— 报错信息看不懂，不知道哪一步错了。
所以下面每一步都附了**验证命令**。命令输出对得上，才继续下一步。

## 需要装什么

| 工具 | 作用 | 版本要求 |
| --- | --- | --- |
| Node.js | 前端工具链的运行基础 | 24 LTS（最低 20.19） |
| pnpm | 包管理器，负责装依赖 | 12.x |
| 编辑器 | 写代码的地方，推荐 VSCode | 最新版 |
| 浏览器 | 运行与调试页面，推荐 Chrome | 最新版 |
| Git | 版本管理 | 2.40 以上 |

::: tip 版本说明
文中版本为编写时核对的结果。Node 用 **24 LTS（Krypton）**，它的维护周期到 2028 年。
Node 22 是维护版，也能跑，但不建议新环境再用。**不要用 Current 版本做课程作业** ——
它的更新节奏太快，教学环境容易出不一致。
:::

## 第一步：安装 Node.js

**不要直接去官网下载安装包。** 原因是你迟早需要同时保留几个 Node 版本：
项目 A 要 Node 20，项目 B 要 Node 24，直接装会互相覆盖。用版本管理工具才是正解。

### macOS 与 Linux

```bash [终端]
# 用 Homebrew 装 fnm（一个快速的 Node 版本管理器）
brew install fnm

# 让 shell 认识 fnm（zsh 用户）
echo 'eval "$(fnm env --use-on-cd)"' >> ~/.zshrc
source ~/.zshrc

# 装并切换到 Node 24
fnm install 24
fnm default 24
```

### Windows

```powershell [PowerShell]
# 用 winget 装 fnm
winget install Schniz.fnm

# 新开一个终端后，装并切换到 Node 24
fnm install 24
fnm default 24
```

::: details 不想用版本管理器？也可以装 nvm
nvm 更老牌，资料更多，但速度比 fnm 慢。
macOS 与 Linux 用 [nvm-sh](https://github.com/nvm-sh/nvm)，Windows 用 [nvm-windows](https://github.com/coreybutler/nvm-windows)。
命令大同小异，把 `fnm install 24` 换成 `nvm install 24 && nvm use 24` 即可。
:::

**验证**

```bash [终端]
node -v   # 期望输出 v24.x.x
npm -v    # 期望输出 11.x 或更高
```

输出对得上，第一步完成。

## 第二步：安装 pnpm

pnpm 比 npm 快得多，而且它用硬链接共享依赖 —— 十个项目用同一个版本的 Vue，
磁盘上只存一份。对要反复建工程的学生来说，这个差别很实在。

```bash [终端]
npm install -g pnpm
```

**验证**

```bash [终端]
pnpm -v   # 期望输出 12.x
```

::: warning Windows 上遇到"权限不足"
用管理员身份打开 PowerShell 再执行。或者改用 Node 自带的 corepack：`corepack enable pnpm`。
:::

::: details 为什么不用 npm？
npm 能用，但有两个现实问题：一是它把依赖平铺在 `node_modules` 里，同一个包的不同版本会重复存很多份；
二是它对"幽灵依赖"（用了没声明的包）很宽容，本地能跑、别人机器上就报 `Cannot find module`。
pnpm 的严格模式会提前把这些错误暴露出来，这在教学里是好事。
:::

## 第三步：安装编辑器与插件

推荐 VSCode。装完后**必须**装这几个扩展，否则后面的规范章节会缺工具：

| 扩展 | 作用 |
| --- | --- |
| Vue - Official | Vue 单文件组件的语法高亮、类型提示、格式化 |
| ESLint | 在编辑器里直接标出代码问题 |
| Prettier - Code formatter | 保存时自动格式化 |
| EditorConfig for VS Code | 统一缩进与换行符 |

装完把这两项打开（`设置` → 搜索）：

- **Editor: Format On Save** —— 勾选。保存即格式化，省掉一堆格式争论。
- **Files: Eol** —— 设为 `\n`。避免 Windows 和 macOS 之间因为换行符产生整文件级的假冲突。

## 第四步：浏览器准备

用 Chrome 或 Edge，按 `F12` 打开开发者工具。这几个面板你会反复用到：

| 面板 | 什么时候用 |
| --- | --- |
| Console | 看报错、临时执行一段代码 |
| Elements | 看 DOM 结构和最终生效的 CSS |
| Network | 看接口请求的地址、参数、状态码、响应体 |
| Application | 看 localStorage 里的登录凭证 |

::: tip 装一个扩展：Vue.js devtools
它能让你直接看到组件的层级、每个组件当前的 props 与状态。
排查"数据传丢了"这类问题时，比 `console.log` 快得多。
:::

## 第五步：Git 基础配置

```bash [终端]
git config --global user.name "你的姓名"
git config --global user.email "你的邮箱"
git config --global init.defaultBranch main
git config --global core.autocrlf input
```

最后一条是换行符设置：提交时统一转成 `\n`，检出时不转换。**团队协作时这一条能省掉大量假冲突。**

**验证**

```bash [终端]
git config --list | head -20
```

## 环境自检清单

把下面每一项都跑一遍，全部打勾才算环境就绪：

- [ ] `node -v` 输出 v24 开头
- [ ] `npm -v` 输出 11 以上
- [ ] `pnpm -v` 输出 12 开头
- [ ] VSCode 已装 4 个扩展，且保存时能自动格式化
- [ ] 浏览器按 F12 能打开开发者工具，Console 面板能输入 `1 + 1` 得到 `2`
- [ ] `git config --global user.name` 能输出你的名字
- [ ] 能创建一个测试仓库并成功提交一次

```bash [一条命令跑完主要检查]
node -v && npm -v && pnpm -v && git --version
```

## 常见问题

::: details 提示 "command not found: node"
说明 Node 没装好，或者环境变量没生效。**先关闭终端再重新打开** —— 大多数情况是这个问题。
还不行就检查 fnm 的初始化语句是否写进了正确的配置文件（zsh 是 `~/.zshrc`，bash 是 `~/.bash_profile`）。
:::

::: details 提示 "无法加载文件，因为在此系统上禁止运行脚本"（Windows）
PowerShell 的执行策略太严。以管理员身份运行 `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser`，
输入 `Y` 确认即可。
:::

::: details pnpm install 卡住不动
大概率是网络问题。换镜像源后重试：

```bash [终端]
pnpm config set registry https://registry.npmmirror.com
```

:::

::: details 装完依赖启动报 "Cannot find module"
先确认三件事：`node_modules` 存在、`package.json` 里确实声明了这个包、你没在错误的目录里执行命令
（必须在有 `package.json` 的那一层）。
:::

## 下一步

环境装好了，接着读：

- [12 周课程地图](/guide/roadmap) —— 看清整门课的推进节奏
- [单元 1：工程化认知与开发环境](/unit01/) —— 从这里正式开始
- [常见报错与排查](/appendix/errors) —— 收藏这一页，后面会反复用
