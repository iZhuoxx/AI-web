<template>
  <a-card class="keywords-panel" :body-style="{ height: '100%' }">
    <template #title>
      <div class="panel-title">
        <HashIcon class="icon" />
        <div>
          <div class="heading">关键词</div>
          <div class="subheading">识别课堂核心概念</div>
        </div>
      </div>
    </template>
    <div class="keywords-body">
      <template v-if="keywords.length">
        <a-space size="small" wrap>
          <a-tag
            v-for="keyword in keywords"
            :key="keyword.id"
            color="blue"
            class="keyword-tag"
            @click="emit('keyword-selected', keyword.text)"
          >
            {{ keyword.text }}
          </a-tag>
        </a-space>
      </template>
      <div v-else class="empty">
        录音开始后会实时提取关键词
      </div>
    </div>
  </a-card>
</template>

<script setup lang="ts">
import { HashIcon } from 'lucide-vue-next'
import type { KeywordItem } from '@/types/notes'

defineProps<{
  keywords: KeywordItem[]
}>()

const emit = defineEmits<{
  (e: 'keyword-selected', value: string): void
}>()
</script>

<style scoped>
.keywords-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.panel-title {
  display: flex;
  align-items: center;
  gap: 10px;
}

.heading {
  font-weight: 600;
}

.subheading {
  font-size: 12px;
  color: rgba(0, 0, 0, 0.45);
}

.icon {
  width: 18px;
  height: 18px;
}

.keywords-body {
  flex: 1;
  overflow-y: auto;
  padding: 8px 2px 8px 0;
}

.keyword-tag {
  cursor: pointer;
  user-select: none;
}

.empty {
  height: 120px;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  color: rgba(0, 0, 0, 0.35);
}
</style>
