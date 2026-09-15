import { defineConfig } from 'vitepress'
import { sidebar } from './sidebar.mts'

// 部署在 GitHub Pages 的子路径下，base 必须与仓库名一致。
// 若以后改用自定义域名（站点在根路径），把 DOCS_BASE 环境变量设为 / 即可：
//   DOCS_BASE=/ npm run build
const base = process.env.DOCS_BASE ?? '/frontend-engineering-course/'

export default defineConfig({
  lang: 'zh-CN',
  title: '前端工程化开发',
  description: '48 学时配套教程 · Vue 3 + Vite 工程化实践 · 校园活动服务平台项目驱动 · 管理端 Web + 用户端 uni-app 双端',

  head: [
    ['meta', { name: 'theme-color', content: '#42b883' }],
    ['meta', { name: 'author', content: '前端工程化开发课程组' }],
    ['link', { rel: 'icon', type: 'image/svg+xml', href: `${base}logo.svg` }]
  ],

  base,

  lastUpdated: true,

  // 关闭 cleanUrls：GitHub Pages 是否把 /foo 映射到 /foo.html 并无稳定保证，
  // 赌错的后果是学生点任何链接都 404。这里老老实实生成 .html 链接。
  cleanUrls: false,
  ignoreDeadLinks: true,

  markdown: {
    lineNumbers: false,
    theme: { light: 'github-light', dark: 'github-dark' },
    headers: { level: [2, 3] },
    config(md) {
      // 中文排版：句间不加空格，行内代码两侧保留空格
      md.set({ linkify: true, breaks: false })

      // 给所有行内 <code> 加 v-pre。
      // 原因：VitePress 把 Markdown 当 Vue 模板编译，行内代码里的 {{ }} 不会被转义，
      // 会被当成插值真的去执行 —— 写了 `{{ doneCount() }}` 就是构建期报错
      // "doneCount is not a function"，写了 `{{ }}` 就是渲染出空白。
      // 加了 v-pre 之后，教程正文里可以放心写 {{ }} 做语法说明。
      const rules = md.renderer.rules
      const original = rules.code_inline
      rules.code_inline = (tokens, idx, options, env, self) => {
        const html = original
          ? original(tokens, idx, options, env, self)
          : `<code>${md.utils.escapeHtml(tokens[idx].content)}</code>`
        return html.replace(/^<code/, '<code v-pre')
      }
    }
  },

  themeConfig: {
    logo: '/logo.svg',
    siteTitle: '前端工程化开发',

    nav: [
      { text: '课程导学', link: '/guide/', activeMatch: '^/guide/' },
      { text: '12 个单元', link: '/unit01/', activeMatch: '^/unit' },
      { text: '综合项目', link: '/project/', activeMatch: '^/project/' },
      { text: '用户端', link: '/mobile/', activeMatch: '^/mobile/' },
      { text: '案例库', link: '/cases/', activeMatch: '^/cases/' },
      { text: '附录', link: '/appendix/', activeMatch: '^/appendix/' }
    ],

    sidebar,

    outline: { level: [2, 3], label: '本页目录' },

    search: {
      provider: 'local',
      options: {
        translations: {
          button: { buttonText: '搜索教程', buttonAriaLabel: '搜索教程' },
          modal: {
            displayDetails: '显示详情',
            resetButtonTitle: '清除条件',
            backButtonTitle: '返回',
            noResultsText: '没有找到相关内容',
            footer: {
              selectText: '选择',
              navigateText: '切换',
              closeText: '关闭'
            }
          }
        }
      }
    },

    socialLinks: [
      { icon: 'github', link: 'https://github.com/mqxu/frontend-engineering-course' }
    ],

    docFooter: { prev: '上一节', next: '下一节' },
    darkModeSwitchLabel: '主题',
    sidebarMenuLabel: '目录',
    returnToTopLabel: '回到顶部',
    lastUpdatedText: '最后更新',
    outlineTitle: '本页目录',

    footer: {
      message: '配套教材 · 依据 Vue 官方文档与工程实践编写',
      copyright: '前端工程化开发 48 学时 · 校园活动服务平台项目驱动（管理端 Vue 3 + 用户端 uni-app）'
    }
  }
})
