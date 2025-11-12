<template>
  <a-card class="placeholder-panel" :body-style="{ height: '100%', padding: '32px' }">
    <div class="placeholder-panel__content">
      <SparklesIcon class="placeholder-panel__icon" />
      <div class="placeholder-panel__title">闪卡练习</div>
      <p class="placeholder-panel__description">Upcoming soon · 根据课堂重点自动生成记忆卡片</p>
    </div>
  </a-card>
</template>

<script setup lang="ts">
import { SparklesIcon } from 'lucide-vue-next'
</script>

<style scoped>
.placeholder-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.placeholder-panel__content {
  flex: 1;
  border: 1px dashed rgba(0, 0, 0, 0.08);
  border-radius: 16px;
  background: rgba(22, 119, 255, 0.03);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  gap: 12px;
}

.placeholder-panel__icon {
  width: 32px;
  height: 32px;
  color: #1677ff;
}

.placeholder-panel__title {
  font-size: 18px;
  font-weight: 600;
}

.placeholder-panel__description {
  margin: 0;
  color: rgba(0, 0, 0, 0.45);
}
</style>
