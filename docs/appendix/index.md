# 附录

这五份附录是教程的"工具区"。正文按顺序讲知识，附录按**你此刻遇到的问题**来查。

- 写着写着忘了某个 API 怎么写 → 翻[速查手册](/appendix/cheatsheet)。
- 终端报了一个看不懂的错 → 翻[常见报错与排查](/appendix/errors)。
- 不确定某个包该装哪个版本、某个工具是干什么的 → 翻[工具链与版本清单](/appendix/tools)。
- 要用 AI 写代码，但不确定怎么描述、怎么审 → 翻 [AI 编程工具速查](/appendix/ai-tools)。
- 两个概念傻傻分不清（比如"打包"和"编译"）→ 翻[术语表](/appendix/glossary)。

## 五份附录各解决什么问题

| 附录 | 解决什么问题 | 什么时候翻 |
| --- | --- | --- |
| [API 速查手册](/appendix/cheatsheet) | 记不住某个语法/函数的写法与使用场景 | 写代码时手边常备，按主题查 |
| [常见报错与排查](/appendix/errors) | 遇到报错不知道从哪下手 | 终端或浏览器一出红字就翻 |
| [工具链与版本清单](/appendix/tools) | 不知道要装什么、装什么版本、这个工具干什么用 | 配环境、新建项目、升级依赖时 |
| [术语表](/appendix/glossary) | 概念听懂了但说不清差别，或者看文档时被术语卡住 | 概念混淆时，或读英文文档前 |
| [AI 编程工具速查](/appendix/ai-tools) | 工具怎么选、提示词怎么写、AI 的代码怎么审 | 让 AI 写代码的前后 |

### 使用建议

- **速查手册不要通读**。它是字典，不是教材。写代码时遇到"这个怎么拼"就查一下，
  几次之后自然就记住了。
- **报错排查要按顺序做**。每一条都按"现象 → 原因 → 解决 → 怎么预防"写，
  先看现象对不对得上，再看原因，别跳过原因直接抄解决命令。
  **抄命令能解决一次，看懂原因能解决一类。**
- **版本清单在新建项目时对照一遍**。版本不对会引出一批莫名其妙的报错，
  一开始就用基线版本最省事。
- **术语表适合"读文档前预习"**。很多英文文档读不懂不是英语问题，
  是术语没对上。先在术语表里找一遍，读起来会顺很多。

::: tip 附录也是可以提意见的
如果你遇到的报错不在[常见报错](/appendix/errors)里，
或者某条排查步骤看完还是不懂，记下来告诉老师。
**下一版的附录就靠这些反馈补全。**
:::

## 本课程知识点与附录对照

这张表帮你从正文跳到对应附录。左边是正文节次，右边是写代码时最可能用到的附录内容。

| 课程内容 | 位置 | 相关附录 |
| --- | --- | --- |
| 工程化认知与环境搭建 | [单元 1](/unit01/) | [工具链清单](/appendix/tools)、[环境类报错](/appendix/errors#环境类) |
| Node 生态与包管理 | [单元 2](/unit02/) | [依赖类报错](/appendix/errors#依赖类)、[工具链清单](/appendix/tools) |
| package.json 与构建工具 | [单元 2.3](/unit02/03-package-json)、[2.4](/unit02/04-vite) | [依赖版本约定](/appendix/glossary)、[Vite 类报错](/appendix/errors#vite-与构建类) |
| 环境变量与配置 | [单元 2.5](/unit02/05-env-config) | [环境变量读到 undefined](/appendix/errors#vite-与构建类) |
| 代码规范与 Git 协作 | [单元 3](/unit03/) | [工具链清单](/appendix/tools)、[术语表](/appendix/glossary) |
| 模板语法与响应式 | [单元 4](/unit04/) | [模板语法速查](/appendix/cheatsheet#模板语法)、[响应式速查](/appendix/cheatsheet#响应式) |
| 计算属性与渲染控制 | [单元 5](/unit05/) | [响应式速查](/appendix/cheatsheet#响应式)、[Vue 运行类报错](/appendix/errors#vue-运行类) |
| 表单绑定与生命周期 | [单元 6](/unit06/) | [组件速查](/appendix/cheatsheet#组件)、[生命周期速查](/appendix/cheatsheet#生命周期) |
| 组件通信与插槽 | [单元 7](/unit07/)、[单元 8](/unit08/) | [组件速查](/appendix/cheatsheet#组件) |
| 路由与登录鉴权 | [单元 9](/unit09/) | [路由速查](/appendix/cheatsheet#路由)、[路由类报错](/appendix/errors#路由类) |
| Pinia 与请求层 | [单元 10](/unit10/) | [请求速查](/appendix/cheatsheet#请求)、[请求类报错](/appendix/errors#请求类) |
| 联调、构建优化与部署 | [单元 12](/unit12/) | [Vite 与构建类报错](/appendix/errors#vite-与构建类)、[工具链清单](/appendix/tools) |
| AI 协作（贯穿全课程） | [AI 编程导论](/guide/ai-coding) | [AI 编程工具速查](/appendix/ai-tools)、[项目 AI 协作规范](/project/ai-collaboration) |

## 怎么用这套附录配合正文

举一个真实的排查流程，你会看到附录之间怎么配合：

1. 终端报 `Failed to resolve import "@/stores/auth"`。
2. 翻[常见报错](/appendix/errors)，在"Vite 与构建类"里找到这一条，
   按"现象 → 原因"定位到是**路径大小写**或**别名没配**。
3. 按"解决"里的命令检查，同时去[工具链清单](/appendix/tools)确认 Vite 版本与别名配置写法。
4. 修好后，在[术语表](/appendix/glossary)里确认自己理解了"路径别名"是什么，
   下次遇到类似的报错能自己判断。

**排查一次，把这一类问题的原因搞懂，比记住十条命令有用。**

---

上一节：[单元 12 · 联调优化部署与答辩](/unit12/) ·
下一节：[API 速查手册](/appendix/cheatsheet)
