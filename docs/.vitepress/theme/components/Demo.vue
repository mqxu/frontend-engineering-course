<script setup lang="ts">
import { ref, computed, useSlots } from 'vue'

const props = defineProps<{
  /** 示例标题 */
  title?: string
  /** 一句话说明这个示例演示什么 */
  desc?: string
  /** 默认展开哪个标签页 */
  defaultTab?: 'preview' | 'code'
  /** 预览区高度是否自适应（默认自适应；设为 true 可固定一个舒适高度并内部滚动） */
  fixedHeight?: boolean
}>()

const slots = useSlots()
const hasCode = computed(() => Boolean(slots.code))
const tab = ref<'preview' | 'code'>(props.defaultTab ?? 'preview')
</script>

<template>
  <div class="fd">
    <div class="fd-head">
      <div class="fd-name">
        <span class="fd-dot" aria-hidden="true"></span>
        <span class="fd-text">{{ title || '可运行示例' }}</span>
      </div>
      <div v-if="hasCode" class="fd-tabs">
        <button
          type="button"
          class="fd-tab"
          :class="{ on: tab === 'preview' }"
          @click="tab = 'preview'"
        >
          运行效果
        </button>
        <button type="button" class="fd-tab" :class="{ on: tab === 'code' }" @click="tab = 'code'">
          查看代码
        </button>
      </div>
      <span v-else class="fd-badge">实时预览</span>
    </div>

    <p v-if="desc" class="fd-desc">{{ desc }}</p>

    <div v-show="tab === 'preview'" class="fd-stage" :class="{ fixed: fixedHeight }">
      <slot />
    </div>

    <div v-if="hasCode" v-show="tab === 'code'" class="fd-code">
      <slot name="code" />
    </div>
  </div>
</template>

<style scoped>
.fd {
  border: 1px solid var(--vp-c-divider);
  border-radius: 10px;
  overflow: hidden;
  margin: 20px 0;
  background: var(--vp-c-bg);
}

.fd-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 9px 14px;
  background: var(--vp-c-bg-soft);
  border-bottom: 1px solid var(--vp-c-divider);
}

.fd-name {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 600;
  color: var(--vp-c-text-1);
  min-width: 0;
}

.fd-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--vp-c-brand-2);
  flex: none;
}

.fd-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.fd-tabs {
  display: flex;
  gap: 4px;
  flex: none;
}

.fd-tab {
  font-size: 12px;
  line-height: 1;
  padding: 5px 11px;
  border-radius: 6px;
  border: 1px solid transparent;
  background: transparent;
  color: var(--vp-c-text-2);
  cursor: pointer;
  transition: all 0.18s;
}

.fd-tab:hover {
  color: var(--vp-c-brand-1);
}

.fd-tab.on {
  background: var(--vp-c-bg);
  border-color: var(--vp-c-divider);
  color: var(--vp-c-brand-1);
  font-weight: 600;
}

.fd-badge {
  font-size: 11px;
  letter-spacing: 0.04em;
  color: var(--vp-c-brand-1);
  background: var(--vp-c-brand-soft);
  border-radius: 999px;
  padding: 3px 10px;
  flex: none;
}

.fd-desc {
  margin: 0 !important;
  padding: 10px 16px 0;
  font-size: 13px !important;
  color: var(--vp-c-text-2);
}

.fd-stage {
  padding: 18px 16px;
}

.fd-stage.fixed {
  max-height: 380px;
  overflow: auto;
}

.fd-code :deep(div[class*='language-']) {
  margin: 0;
  border: none;
  border-radius: 0;
  border-top: 1px solid var(--vp-c-divider);
}

.fd-code :deep(div[class*='language-'] pre) {
  padding: 16px;
}
</style>
