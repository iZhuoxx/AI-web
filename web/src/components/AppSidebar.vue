<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuth } from '@/composables/useAuth'
import { useNotebookStore } from '@/composables/useNotes'
import AuthPopup from '@/components/AuthPopup.vue'

interface SidebarItem {
  label: string
  name: string
}

const props = defineProps<{ isOpen: boolean }>()
const emit = defineEmits<{ (e: 'toggle'): void }>()

const router = useRouter()
const route = useRoute()
const auth = useAuth()
const notebookStore = useNotebookStore()

const navItems = computed<SidebarItem[]>(() => [
  { label: '笔记', name: 'notes' },
  { label: '聊天', name: 'chat' },
  { label: '关于', name: 'about' },
])

const tooltipText = computed(() => (props.isOpen ? '收起侧栏' : '展开侧栏'))
const isActive = (name: string) => {
  if (name === 'notes') return route.name === 'notes-list' || route.name === 'note-editor'
  return route.name === name
}

const handleNavigate = (name: string) => {
  if (name === 'notes') {
    const activeId = notebookStore.notebooksState.activeNotebook?.id
    const onEditor = route.name === 'note-editor'
    const onList = route.name === 'notes-list'

    if (onEditor) {
      notebookStore.clearActiveNotebook()
      void router.push({ name: 'notes-list' })
      return
    }

    if (onList) return

    if (activeId) {
      void router.push({ name: 'note-editor', params: { id: activeId } })
      return
    }

    void router.push({ name: 'notes-list' })
    return
  }
  if (route.name === name) return
  void router.push({ name })
}

const authPopupOpen = ref(false)

  const activeMembership = computed(() => auth.state.memberships.find(item => item.status === 'active'))
const membershipLabel = computed(() => {
  if (!auth.state.user) return '未登录 · 点击登录'
  const membership = activeMembership.value
  if (!membership) return '标准用户'
  const until = membership.ends_at ? new Date(membership.ends_at).toLocaleDateString('zh-CN') : '长期有效'
  return `${membership.plan} · ${until}`
})

const userInitial = computed(() => {
  const source = auth.state.user?.name || auth.state.user?.email || 'U'
  return source.slice(0, 1).toUpperCase()
})

const displayName = computed(() => auth.state.user?.name || auth.state.user?.email || '未登录')

const handleUserChipClick = async () => {
  if (!auth.state.ready) {
    try {
      await auth.bootstrap()
    } catch {
      // ignore bootstrap error, handled elsewhere
    }
  }
  authPopupOpen.value = true
}

onMounted(() => {
  void auth.bootstrap()
})
</script>

<template>
  <aside :class="['sidebar', { 'is-collapsed': !props.isOpen }]">
    <div class="sidebar__header">
      <div class="sidebar__brand">
        <span class="sidebar__brand-text">SparkNote</span>
      </div>
      <div class="toggle-wrap">
        <button class="toggle-btn" type="button" @click="emit('toggle')" :aria-label="tooltipText">
          <svg class="toggle-svg" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#0f172a" stroke-linecap="round" stroke-linejoin="round">
            <path d="M4 6a2 2 0 0 1 2 -2h12a2 2 0 0 1 2 2v12a2 2 0 0 1 -2 2H6a2 2 0 0 1 -2 -2z" stroke-width="2" />
            <path d="M9 4v16" stroke-width="2" />
          </svg>
        </button>
        <div class="toggle-tooltip">{{ tooltipText }}</div>
      </div>
    </div>

    <nav class="sidebar__nav">
      <button
        v-for="item in navItems"
        :key="item.name"
        :class="['sidebar__item', { 'is-active': isActive(item.name) }]"
        type="button"
        @click="handleNavigate(item.name)"
      >
        <span class="sidebar__icon" aria-hidden="true">
          <svg v-if="item.name === 'notes'" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
            <path
              fill="none"
              stroke="currentColor"
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="1.6"
              d="M16 3h2.6A2.4 2.4 0 0 1 21 5.4v15.2a2.4 2.4 0 0 1-2.4 2.4H5.4A2.4 2.4 0 0 1 3 20.6V5.4A2.4 2.4 0 0 1 5.4 3H8M7 13h4m-4-3h10M7 16h2M8.8 1h6.4a.8.8 0 0 1 .8.8v2.4a.8.8 0 0 1-.8.8H8.8a.8.8 0 0 1-.8-.8V1.8a.8.8 0 0 1 .8-.8m5.506 12.776l-.377 1.508a.2.2 0 0 1-.145.145l-1.508.377c-.202.05-.202.338 0 .388l1.508.377a.2.2 0 0 1 .145.145l.377 1.508c.05.202.338.202.388 0l.377-1.508a.2.2 0 0 1 .145-.145l1.508-.377c.202-.05.202-.337 0-.388l-1.508-.377a.2.2 0 0 1-.145-.145l-.377-1.508c-.05-.202-.338-.202-.388 0"
            />
          </svg>
          <svg v-else-if="item.name === 'chat'" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
            <g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="1.6">
              <path d="M19 16h-2.525a.99.99 0 0 0-.775.375l-2.925 3.65a1 1 0 0 1-1.562 0l-2.925-3.65A.99.99 0 0 0 7.512 16H5c-1.662 0-3-1.338-3-3V6c0-1.662 1.338-3 3-3h14c1.663 0 3 1.338 3 3v7c0 1.662-1.337 3-3 3" />
              <path d="m8.43 10.284l.376-1.508c.05-.202.338-.202.388 0l.377 1.508a.2.2 0 0 0 .145.145l1.508.377c.202.05.202.338 0 .388l-1.508.377a.2.2 0 0 0-.145.145l-.377 1.508c-.05.202-.338.202-.388 0l-.377-1.508a.2.2 0 0 0-.145-.145l-1.508-.377c-.202-.05-.202-.338 0-.388l1.508-.377a.2.2 0 0 0 .145-.145M15.1 7.6l.4-1.6l.4 1.6l1.6.4l-1.6.4l-.4 1.6l-.4-1.6l-1.6-.4z" />
            </g>
          </svg>
          <svg v-else xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
            <path fill="none" stroke="currentColor" stroke-width="1.6" d="M12 2.844L9.19 9.22l-6.377 2.811l6.377 2.811L12 21.22l2.812-6.377l6.376-2.811l-6.376-2.811z" />
          </svg>
        </span>
        <span class="sidebar__body">
          <span class="sidebar__label">{{ item.label }}</span>
        </span>
      </button>
    </nav>

    <footer class="sidebar__footer">
      <button class="user-chip" type="button" @click="handleUserChipClick">
        <div class="avatar">{{ userInitial }}</div>
        <div v-if="props.isOpen" class="user-chip__text">
          <span class="name">{{ displayName }}</span>
          <span class="plan">{{ membershipLabel }}</span>
        </div>
      </button>
    </footer>
  </aside>

  <AuthPopup v-model:open="authPopupOpen" />
</template>

<style scoped>
.sidebar {
  --rail-size: 44px;
  display: flex;
  flex-direction: column;
  border-right: 1px solid rgba(15, 23, 42, 0.08);
  padding: 18px 14px;
  height: 100%;
  box-sizing: border-box;
  background: #f1f5f9;
  gap: 14px;
  transition: padding 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  z-index: 2;
  overflow: visible;
}

.sidebar.is-collapsed {
  padding-left: 10px;
  padding-right: 10px;
}

.sidebar__header,
.sidebar__nav,
.sidebar__footer {
  padding-left: 4px;
  padding-right: 4px;
}

.sidebar__header {
  min-height: 48px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.sidebar__brand {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.sidebar__brand-text {
  font-weight: 700;
  font-size: 16px;
  color: #0f172a;
  white-space: nowrap;
  transition: opacity 0.25s ease, transform 0.25s ease;
}

.sidebar.is-collapsed .sidebar__brand-text {
  opacity: 0;
  transform: translateX(-8px);
  pointer-events: none;
}

.toggle-wrap {
  position: relative;
  display: flex;
  align-items: center;
  margin-left: auto;
}

.sidebar.is-collapsed .toggle-wrap {
  margin-left: 0;
  transform: translateX(-4px);
}

.toggle-btn {
  background: transparent;
  border: none;
  width: 32px;
  height: 32px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background 0.2s ease, transform 0.2s ease;
}

.toggle-btn:hover,
.toggle-btn:focus-visible {
  background: rgba(15, 23, 42, 0.08);
}

.toggle-svg {
  width: 20px;
  height: 20px;
}

.toggle-tooltip {
  position: absolute;
  left: calc(100% + 10px);
  top: 50%;
  transform: translateY(-50%);
  background: rgba(15, 23, 42, 0.9);
  color: #f1f5f9;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.2s ease, transform 0.2s ease;
  white-space: nowrap;
  z-index: 5;
}

.toggle-wrap:hover .toggle-tooltip,
.toggle-btn:focus-visible + .toggle-tooltip {
  opacity: 1;
  transform: translateY(-50%) translateX(2px);
}

.sidebar__nav {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1 1 auto;
}

.sidebar__item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 10px;
  border-radius: 12px;
  border: 1px solid transparent;
  background: #f1f5f9;
  cursor: pointer;
  transition: background 0.2s ease, border-color 0.2s ease, color 0.2s ease;
  font-size: 12px;
  color: #0f172a;
}

.sidebar__item:hover {
  background: #edeff3;
  border-color: rgba(15, 23, 42, 0.08);
}

.sidebar__item.is-active {
  background: rgba(37, 99, 235, 0.1);
  border-color: transparent;
  color: #1d4ed8;
}

.sidebar.is-collapsed .sidebar__item {
  width: var(--rail-size);
  height: var(--rail-size);
  padding: 0;
  justify-content: center;
  border-radius: 12px;
  margin: 0 auto;
}

.sidebar.is-collapsed .sidebar__item:not(.is-active) {
  border-color: transparent;
  background: #f1f5f9;
}

.sidebar__icon {
  width: 28px;
  height: 28px;
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: inherit;
}

.sidebar__icon svg {
  width: 20px;
  height: 20px;
}

.sidebar__body {
  flex: 1;
  display: flex;
  align-items: center;
}

.sidebar__label {
  font-weight: 600;
}

.sidebar.is-collapsed .sidebar__body {
  display: none;
}

.sidebar__footer {
  margin-top: auto;
  display: flex;
  justify-content: flex-start;
}

.sidebar.is-collapsed .sidebar__footer {
  justify-content: center;
}

.user-chip {
  width: 100%;
  border-radius: 16px;
  border: none;
  padding: 12px 14px;
  display: flex;
  align-items: center;
  gap: 12px;
  background: linear-gradient(135deg, rgba(37, 99, 235, 0.07), rgba(14, 165, 233, 0.08));
  cursor: pointer;
  box-shadow: 0 15px 35px rgba(15, 23, 42, 0.12);
  transition: transform 0.25s ease, box-shadow 0.25s ease, background 0.25s ease;
}

.user-chip:hover {
  transform: translateY(-2px);
  box-shadow: 0 20px 45px rgba(15, 23, 42, 0.18);
  background: linear-gradient(135deg, rgba(37, 99, 235, 0.12), rgba(14, 165, 233, 0.12));
}

.user-chip .avatar {
  width: 34px;
  height: 34px;
  border-radius: 12px;
  background: #f1f5f9;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  color: #1d4ed8;
  box-shadow: 0 8px 20px rgba(37, 99, 235, 0.25);
}

.user-chip__text {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.user-chip__text .plan {
  font-size: 12px;
  color: #6b7280;
}

.sidebar.is-collapsed .user-chip__text {
  display: none;
}

.sidebar.is-collapsed .user-chip {
  width: var(--rail-size);
  height: var(--rail-size);
  padding: 0;
  border-radius: 12px;
  background: rgba(37, 99, 235, 0.18);
  box-shadow: none;
  justify-content: center;
}

.sidebar.is-collapsed .user-chip .avatar {
  width: 100%;
  height: 100%;
  border-radius: 12px;
  box-shadow: none;
}
</style>
