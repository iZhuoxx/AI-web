<template>
  <a-card class="learning-panel" :body-style="{ height: '100%', padding: '16px' }">
    <template #title>
      <div class="panel-title">
        <TrendingUpIcon class="icon" />
        <div>
          <div class="heading">学习路径推荐</div>
          <div class="subheading">根据课堂笔记实时生成</div>
        </div>
      </div>
    </template>
    <template #extra v-if="learningPath.length">
      <div class="progress">
        <span>完成度 {{ progress }}%</span>
        <a-progress :percent="progress" size="small" :show-info="false" />
      </div>
    </template>
    <div class="learning-body">
      <a-spin v-if="isLoading" tip="正在为你整理学习路径..." />
      <div v-else-if="!learningPath.length" class="empty">
        开始录音后，系统会基于关键词生成个性化学习路径
      </div>
      <div v-else class="path-steps">
        <div
          v-for="(step, index) in learningPath"
          :key="step.id"
          class="step"
        >
          <div class="step-header">
            <div class="step-index">{{ index + 1 }}</div>
            <div>
              <div class="step-title">{{ step.title }}</div>
              <div class="step-description">{{ step.description }}</div>
            </div>
          </div>
          <div class="materials">
            <div
              v-for="material in step.materials"
              :key="material.id"
              class="material-card"
            >
              <div class="material-info">
                <div class="material-title">{{ material.title }}</div>
                <div class="material-description">{{ material.description }}</div>
                <div class="material-tags">
                  <a-tag v-for="(tag, i) in material.keywords.slice(0, 3)" :key="i" color="geekblue">
                    {{ tag }}
                  </a-tag>
                </div>
              </div>
              <a-button type="link" @click="openMaterial(material.url)">查看</a-button>
            </div>
          </div>
          <a-divider v-if="index < learningPath.length - 1" />
        </div>
      </div>
    </div>
  </a-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { TrendingUpIcon } from 'lucide-vue-next'
import type { KeywordItem, LearningMaterial } from '@/types/notes'

const props = defineProps<{
  materials: LearningMaterial[]
  keywords: KeywordItem[]
  isLoading: boolean
}>()

interface LearningStep {
  id: string
  title: string
  description: string
  materials: LearningMaterial[]
}

const learningPath = computed<LearningStep[]>(() => {
  if (!props.keywords.length) return []
  return [
    {
      id: 'step-1',
      title: '基础知识回顾',
      description: '从核心概念入手回顾课堂内容，建立整体框架。',
      materials: props.materials.slice(0, 2),
    },
    {
      id: 'step-2',
      title: '重点难点突破',
      description: '深入理解关键算法与推导，关注课堂提到的易错点。',
      materials: props.materials.slice(2, 4),
    },
    {
      id: 'step-3',
      title: '拓展与实践',
      description: '结合案例与进阶材料，进行扩展学习与实战训练。',
      materials: props.materials.slice(4),
    },
  ].filter(step => step.materials.length > 0)
})

const progress = computed(() => 0)

const openMaterial = (url: string) => {
  window.open(url || '#', '_blank')
}
</script>

<style scoped>
.learning-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
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

.progress {
  min-width: 140px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
  color: rgba(0, 0, 0, 0.45);
}

.learning-body {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.empty {
  height: 120px;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  color: rgba(0, 0, 0, 0.35);
}

.path-steps {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.step {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.step-header {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.step-index {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #1677ff22;
  color: #1677ff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
}

.step-title {
  font-weight: 600;
}

.step-description {
  font-size: 13px;
  color: rgba(0, 0, 0, 0.45);
}

.materials {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.material-card {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 8px;
  padding: 12px;
  background: #fafafa;
}

.material-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.material-title {
  font-weight: 500;
}

.material-description {
  font-size: 13px;
  color: rgba(0, 0, 0, 0.55);
}

.material-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
</style>
