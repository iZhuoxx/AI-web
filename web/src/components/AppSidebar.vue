<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

type SidebarItem = {
  label: string
  name: string
  description?: string
  icon?: string
}

const props = defineProps<{ isOpen: boolean }>()
const emit = defineEmits<{ (e: 'toggle'): void }>()

const router = useRouter()
const route = useRoute()

const items = computed<SidebarItem[]>(() => [
  { label: '聊天', name: 'chat', description: '与模型对话', icon: '💬' },
  { label: '笔记', name: 'notetaker', description: '记录并生成笔记', icon: '🔗' },
  { label: '关于', name: 'about', description: '关于本网站', icon: '🌟' },
])

const isActive = (name: string) => route.name === name
const handleNavigate = (name: string) => {
  if (route.name === name) return
  void router.push({ name })
}

const tooltipText = computed(() => (props.isOpen ? 'Close sidebar' : 'Open sidebar'))
</script>

<template>
  <aside :class="['sidebar', { 'is-collapsed': !props.isOpen }]">
    <div class="sidebar__header">
      <span class="sidebar__brand">All In AI</span>

      <!-- ChatGPT 风格按钮 -->
      <div class="toggle-wrap">
        <button class="toggle-btn" type="button" @click="emit('toggle')" :aria-label="tooltipText">
          <span class="toggle-icon" :class="{ 'is-closed': !props.isOpen }"></span>
        </button>

        <div class="toggle-tooltip">
          {{ tooltipText }}
        </div>
      </div>
    </div>

    <nav class="sidebar__nav">
      <button
        v-for="item in items"
        :key="item.name"
        :class="['sidebar__item', { 'is-active': isActive(item.name) }]"
        type="button"
        @click="handleNavigate(item.name)"
      >
        <span class="sidebar__icon" aria-hidden="true">{{ item.icon }}</span>
        <span class="sidebar__body">
          <span class="sidebar__label">{{ item.label }}</span>
          <span class="sidebar__description">{{ item.description }}</span>
        </span>
      </button>
    </nav>
  </aside>
</template>

<style scoped>
/* ===== layout ===== */
.sidebar {
  display: flex;
  flex-direction: column;
  background: #ffffff;
  border-right: 1px solid rgba(15, 23, 42, 0.08);
  padding: 20px 16px;
  height: 100%;
  box-sizing: border-box;
  gap: 16px;
  transition: padding 0.2s ease;
}

.sidebar__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  font-weight: 600;
  font-size: 18px;
  color: #111827;
}

.sidebar__brand {
  white-space: nowrap;
}

/* ===== Toggle 按钮（纯 CSS 图标） ===== */
.toggle-wrap {
  position: relative;
  display: inline-block;
}

.toggle-btn {
  background: #fff;
  border: 0px solid rgba(0, 0, 0, 0.08);
  color: #4b5563;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background 0.18s ease, color 0.18s ease, border-color 0.18s ease;
  position: relative;
}

.toggle-btn:hover {
  background: #f3f4f6;
  color: #111827;
  border-color: rgba(0, 0, 0, 0.12);
}

.toggle-icon {
  width: 14px;
  height: 14px;
  position: relative;
  display: inline-block;
  border-radius: 3px;
  box-sizing: border-box;
}

.toggle-icon::before,
.toggle-icon::after {
  content: "";
  position: absolute;
  top: 0;
  height: 100%;
  width: 40%;
  border-radius: 3px;
  background: currentColor;
  transition: all 0.2s ease;
}

/* 左栏 + 右栏 */
.toggle-icon::before {
  left: 0;
  opacity: 0.9;
}
.toggle-icon::after {
  right: 0;
  opacity: 0.5;
}

/* 关闭状态：反转位置 */
.toggle-icon.is-closed::before {
  left: auto;
  right: 0;
  opacity: 0.9;
}
.toggle-icon.is-closed::after {
  left: 0;
  right: auto;
  opacity: 0.5;
}

/* Tooltip */
.toggle-tooltip {
  position: absolute;
  left: 50%;
  transform: translate(-50%, 6px);
  top: 100%;
  pointer-events: none;
  opacity: 0;
  background: #000;
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  padding: 6px 10px;
  border-radius: 8px;
  white-space: nowrap;
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.28);
  transition: opacity 0.15s ease, transform 0.15s ease;
  z-index: 20;
}

.toggle-wrap:hover .toggle-tooltip {
  opacity: 1;
  transform: translate(-50%, 10px);
}

/* ===== nav ===== */
.sidebar__nav {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 1 1 auto;
}

.sidebar__item {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 12px;
  align-items: center;
  padding: 12px;
  border-radius: 12px;
  border: 1px solid transparent;
  background: transparent;
  text-align: left;
  cursor: pointer;
  transition: all 0.2s ease;
  color: inherit;
  font: inherit;
  width: 100%;
}

.sidebar__icon {
  font-size: 20px;
  line-height: 1;
}

.sidebar__label {
  font-size: 15px;
  font-weight: 600;
}

.sidebar__description {
  font-size: 12px;
  color: #6b7280;
  margin-top: 2px;
}

.sidebar__body {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.sidebar__item:hover {
  border-color: rgba(37, 99, 235, 0.25);
  background: rgba(37, 99, 235, 0.08);
}

.sidebar__item.is-active {
  border-color: rgba(37, 99, 235, 0.5);
  background: rgba(37, 99, 235, 0.12);
}

/* ===== collapsed mode ===== */
.sidebar.is-collapsed {
  padding: 16px 8px;
  align-items: center;
  gap: 12px;
  width: 72px;
}

.sidebar.is-collapsed .sidebar__brand {
  display: none;
}

.sidebar.is-collapsed .sidebar__nav {
  align-items: center;
}

.sidebar.is-collapsed .sidebar__item {
  grid-template-columns: 1fr;
  gap: 6px;
  justify-items: center;
  padding: 10px 8px;
}

.sidebar.is-collapsed .sidebar__body {
  display: none;
}

.sidebar.is-collapsed .sidebar__icon {
  font-size: 18px;
}

/* ===== responsive ===== */
@media (max-width: 960px) {
  .sidebar {
    padding: 16px 12px;
  }
  .sidebar__header {
    font-size: 16px;
  }
}
</style>
