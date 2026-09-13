<script setup>
import { ref, computed } from 'vue'

const count = ref(0)

// 派生值：不需要单独存一份，count 变了它自动重算
const double = computed(() => count.value * 2)

// 判断状态用的派生值
const level = computed(() => {
  if (count.value === 0) return '尚未开始'
  if (count.value < 5) return '刚起步'
  if (count.value < 10) return '有点意思了'
  return '停不下来了'
})

// 操作记录，用来演示列表渲染
const logs = ref([])

function step(delta) {
  count.value += delta
  logs.value.unshift(`第 ${logs.value.length + 1} 次操作：${delta > 0 ? '+' : ''}${delta} → ${count.value}`)
}

function reset() {
  count.value = 0
  logs.value = []
}
</script>

<template>
  <div class="counter">
    <div class="show">
      <div class="num">{{ count }}</div>
      <div class="side">
        <div class="row">
          <span class="k">翻倍</span>
          <span class="v">{{ double }}</span>
        </div>
        <div class="row">
          <span class="k">状态</span>
          <span class="v">{{ level }}</span>
        </div>
      </div>
    </div>

    <div class="ops">
      <button type="button" @click="step(-1)">-1</button>
      <button type="button" @click="step(1)">+1</button>
      <button type="button" @click="step(5)">+5</button>
      <button type="button" class="ghost" @click="reset">重置</button>
    </div>

    <ul v-if="logs.length" class="logs">
      <li v-for="(item, i) in logs.slice(0, 4)" :key="i">{{ item }}</li>
    </ul>
    <p v-else class="empty">还没有任何操作，点上面的按钮试试。</p>
  </div>
</template>

<style scoped>
.counter {
  max-width: 420px;
}

.show {
  display: flex;
  align-items: center;
  gap: 20px;
}

.num {
  font-size: 46px;
  font-weight: 700;
  line-height: 1;
  color: var(--vp-c-brand-1);
  min-width: 90px;
  font-variant-numeric: tabular-nums;
}

.side {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.row {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  border-bottom: 1px dashed var(--vp-c-divider);
  padding-bottom: 4px;
}

.k {
  color: var(--vp-c-text-3);
}

.v {
  color: var(--vp-c-text-1);
  font-weight: 600;
}

.ops {
  display: flex;
  gap: 8px;
  margin-top: 18px;
}

.ops button {
  flex: 1;
  padding: 8px 0;
  font-size: 14px;
  font-weight: 600;
  border-radius: 8px;
  border: 1px solid var(--vp-c-brand-2);
  background: var(--vp-c-brand-2);
  color: #fff;
  cursor: pointer;
  transition: opacity 0.18s;
}

.ops button:hover {
  opacity: 0.86;
}

.ops button.ghost {
  background: transparent;
  color: var(--vp-c-text-2);
  border-color: var(--vp-c-divider);
}

.logs {
  list-style: none;
  margin: 16px 0 0;
  padding: 0;
}

.logs li {
  font-size: 12.5px;
  color: var(--vp-c-text-2);
  padding: 5px 0;
  border-bottom: 1px dashed var(--vp-c-divider);
  font-variant-numeric: tabular-nums;
}

.logs li:last-child {
  border-bottom: none;
}

.empty {
  margin: 16px 0 0 !important;
  font-size: 12.5px !important;
  color: var(--vp-c-text-3);
}
</style>
