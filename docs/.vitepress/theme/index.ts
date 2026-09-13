import DefaultTheme from 'vitepress/theme'
import type { Theme } from 'vitepress'
import './style.css'

import UnitMeta from './components/UnitMeta.vue'
import Demo from './components/Demo.vue'

export default {
  extends: DefaultTheme,
  enhanceApp({ app }) {
    // 两个课程专用组件
    app.component('UnitMeta', UnitMeta)
    app.component('Demo', Demo)

    // 自动注册 components/demos 目录下的全部可运行示例
    // 文件名即组件名，例如 DemoCounter.vue 可直接写 <DemoCounter />
    const demos = import.meta.glob('./components/demos/*.vue', { eager: true }) as Record<
      string,
      { default: unknown }
    >
    for (const [path, mod] of Object.entries(demos)) {
      const name = path.split('/').pop()!.replace(/\.vue$/, '')
      app.component(name, mod.default as never)
    }
  }
} satisfies Theme
