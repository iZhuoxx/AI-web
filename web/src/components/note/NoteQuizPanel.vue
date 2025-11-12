<template>
  <a-card class="placeholder-panel" :body-style="{ height: '100%', padding: '32px' }">
    <div class="placeholder-panel__content">
      <ClipboardListIcon class="placeholder-panel__icon" />
      <div class="placeholder-panel__title">测验挑战</div>
      <p class="placeholder-panel__description">Upcoming soon · 智能生成的练习题帮助你即时自测</p>
    </div>
  </a-card>
</template>

<script setup lang="ts">
import { ClipboardListIcon } from 'lucide-vue-next'
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
  background: rgba(24, 144, 255, 0.03);
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
  color: #fa8c16;
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
