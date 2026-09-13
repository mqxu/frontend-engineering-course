<script setup lang="ts">
defineProps<{
  /** 单元编号，如「单元 4」 */
  unit: string
  /** 单元标题 */
  title: string
  /** 学时，如「4 学时」 */
  hours?: string
  /** 周次，如「第 4 周」 */
  week?: string
  /** 所属模块 */
  module?: string
  /** 教学目标 */
  goals?: string[]
  /** 课堂产出 */
  outcomes?: string[]
}>()
</script>

<template>
  <section class="um">
    <header class="um-head">
      <span class="um-unit">{{ unit }}</span>
      <h1 class="um-title">{{ title }}</h1>
      <div class="um-meta">
        <span v-if="module" class="um-pill um-module">{{ module }}</span>
        <span v-if="hours" class="um-pill">{{ hours }}</span>
        <span v-if="week" class="um-pill">{{ week }}</span>
      </div>
    </header>

    <div v-if="goals?.length" class="um-block">
      <div class="um-label">学完这个单元，你应该能够</div>
      <ul class="um-goals">
        <li v-for="(g, i) in goals" :key="i">{{ g }}</li>
      </ul>
    </div>

    <div v-if="outcomes?.length" class="um-block">
      <div class="um-label">课堂产出</div>
      <div class="um-tags">
        <span v-for="(o, i) in outcomes" :key="i" class="um-tag">{{ o }}</span>
      </div>
    </div>
  </section>
</template>

<style scoped>
.um {
  border: 1px solid var(--vp-c-divider);
  border-radius: 12px;
  padding: 22px 24px 20px;
  margin: 8px 0 32px;
  background: linear-gradient(180deg, var(--vp-c-bg-soft), var(--vp-c-bg));
}

.um-head {
  border-bottom: 1px dashed var(--vp-c-divider);
  padding-bottom: 14px;
  margin-bottom: 16px;
}

.um-unit {
  display: inline-block;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: #fff;
  background: var(--vp-c-brand-2);
  border-radius: 999px;
  padding: 2px 12px;
  margin-bottom: 10px;
}

.um-title {
  margin: 0 !important;
  padding: 0 !important;
  border: none !important;
  font-size: 1.5rem !important;
  line-height: 1.35;
}

.um-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.um-pill {
  font-size: 12px;
  color: var(--vp-c-text-2);
  background: var(--vp-c-default-soft);
  border-radius: 6px;
  padding: 3px 10px;
}

.um-module {
  color: var(--vp-c-brand-1);
  background: var(--vp-c-brand-soft);
  font-weight: 600;
}

.um-block + .um-block {
  margin-top: 16px;
}

.um-label {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.04em;
  color: var(--vp-c-text-3);
  margin-bottom: 8px;
}

.um-goals {
  margin: 0;
  padding-left: 20px;
}

.um-goals li {
  margin: 4px 0 !important;
  font-size: 14px;
  color: var(--vp-c-text-1);
}

.um-goals li::marker {
  color: var(--vp-c-brand-2);
}

.um-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.um-tag {
  font-size: 13px;
  color: var(--vp-c-brand-1);
  border: 1px solid var(--vp-c-brand-soft);
  background: var(--vp-c-brand-soft);
  border-radius: 6px;
  padding: 3px 10px;
}
</style>
