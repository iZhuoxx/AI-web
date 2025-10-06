<!-- src/components/message.vue -->
<script setup lang="ts">
import type { TMessage } from '@/types'
import MarkdownRenderer from '@/components/MarkdownRenderer.vue'
import { ref } from 'vue'

const props = defineProps<{ message: TMessage }>()

/* 仅用于选择图标 */
function isImageType(t?: string) { return typeof t === 'string' && t.startsWith('image/') }
function isPdfType(t?: string)   { return t === 'application/pdf' }

/** 图片 Lightbox*/
const lightboxVisible = ref(false)
const lightboxSrc = ref<string>('')
function openLightbox(src: string) { lightboxSrc.value = src; lightboxVisible.value = true }
function closeLightbox() { lightboxVisible.value = false; lightboxSrc.value = '' }
</script>

<template>
  <div class="message-row" :class="props.message.type === 1 ? 'send' : 'replay'">
    <!-- 用户消息 -->
    <template v-if="props.message.type === 1">
      <div class="bubble user">
        <pre class="text" v-if="props.message.msg">{{ props.message.msg }}</pre>

        <!-- 图片（dataURL）+ 点击放大 -->
        <div v-if="props.message.images?.length" class="imgs">
          <img
            v-for="(src,i) in props.message.images"
            :key="'img-'+i"
            :src="src"
            alt="image"
            @click="openLightbox(src)"
            class="clickable"
          />
        </div>

        <!-- 文件（仅展示，不提供下载） -->
        <div v-if="props.message.files?.length" class="files">
          <template v-for="(f,i) in props.message.files" :key="'file-'+i">
            <!-- src/components/message.vue（节选：仅替换 <a> 标签这两处） -->
            <span class="pill" :title="f.name">
              {{ isImageType(f.type) ? '🖼️' : (isPdfType(f.type) ? '📄' : '📎') }} {{ f.name }}
            </span>
          </template>
        </div>
      </div>
    </template>

    <!-- AI 消息 -->
    <template v-else>
      <div class="bubble ai">
        <div v-if="props.message.meta?.loading && !props.message.msg" class="ai-status">正在思考…</div>
        <div v-else class="md-wrap">
          <MarkdownRenderer :source="props.message.msg" />
        </div>

        <!-- 图片（dataURL）+ 点击放大 -->
        <div v-if="props.message.images?.length" class="imgs">
          <img
            v-for="(src,i) in props.message.images"
            :key="'aiimg-'+i"
            :src="src"
            alt="image"
            @click="openLightbox(src)"
            class="clickable"
          />
        </div>

        <!-- 文件（仅展示，不提供下载） -->
        <div v-if="props.message.files?.length" class="files">
          <template v-for="(f,i) in props.message.files" :key="'aifile-'+i">
            <span class="pill" :title="f.name">
              {{ isImageType(f.type) ? '🖼️' : (isPdfType(f.type) ? '📄' : '📎') }} {{ f.name }}
            </span>
          </template>
        </div>
      </div>
    </template>
  </div>

  <!-- Lightbox -->
  <teleport to="body">
    <div v-if="lightboxVisible" class="lightbox" @click.self="closeLightbox">
      <button class="lightbox-close" @click="closeLightbox">✕</button>
      <img :src="lightboxSrc" alt="preview" />
    </div>
  </teleport>
</template>

<style scoped>
.message-row { display: flex; align-items: flex-start; width: 100%; gap: 8px; margin: 8px 0; }
.message-row.send   { justify-content: flex-end; }
.message-row.replay { justify-content: flex-start; }

.bubble { width: fit-content; max-width: 90%; border-radius: 12px; border: 1px solid #e5e7eb; box-shadow: 0 1px 3px rgba(0,0,0,.04); padding: 10px 12px; font-size: 14px; line-height: 1.6; }
.bubble.user { background: #e7f3ff; border-color: #d6e8ff; max-width: 60%; }
.bubble.ai   { background: #fff;    border-color: #e5e7eb; }

.ai-status { color: #64748b; font-size: 13px; }

.text { margin: 0; white-space: pre-wrap; word-break: break-word; }
.md-wrap :deep(.prose) { max-width: none; }

.imgs { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 8px; }
.imgs img { width: 120px; height: 120px; object-fit: cover; border-radius: 8px; border: 1px solid #e5e7eb; cursor: zoom-in; }

.files { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 8px; }
.pill { display: inline-flex; align-items: center; gap: 6px; padding: 6px 10px; border: 1px solid #e5e7eb; border-radius: 999px; background: #f9fafb; color: #111827; font-size: 13px; text-decoration: none; }

.lightbox {
  position: fixed; inset: 0; background: rgba(0,0,0,.65);
  display: flex; align-items: center; justify-content: center; z-index: 9999;
}
.lightbox img { max-width: 90vw; max-height: 85vh; border-radius: 8px; background:#fff; }
.lightbox-close {
  position: absolute; top: 24px; right: 24px;
  width: 36px; height: 36px; border-radius: 8px;
  background: rgba(255,255,255,.9); border: 1px solid #e5e7eb; cursor: pointer;
}
</style>
