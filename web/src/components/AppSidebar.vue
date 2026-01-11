<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuth } from '@/composables/useAuth'
import { useNotebookStore } from '@/composables/useNotes'
import { useLocale } from '@/composables/useLocale'
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
const { t } = useI18n()
const { currentLocale, supportedLocales, setLocale } = useLocale()

const navItems = computed<SidebarItem[]>(() => [
  { label: t('nav.notes'), name: 'notes' },
  { label: t('nav.chat'), name: 'chat' },
  { label: t('nav.about'), name: 'about' },
])

const tooltipText = computed(() => (props.isOpen ? t('nav.collapseSidebar') : t('nav.expandSidebar')))

// 语言切换
const langMenuOpen = ref(false)
const toggleLangMenu = () => {
  langMenuOpen.value = !langMenuOpen.value
}
const selectLocale = (locale: 'zh-CN' | 'en-US') => {
  setLocale(locale)
  langMenuOpen.value = false
}
const currentLocaleLabel = computed(() => {
  return supportedLocales.find(l => l.value === currentLocale.value)?.label ?? currentLocale.value
})
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
  if (!auth.state.user) return t('auth.clickToLogin')
  const membership = activeMembership.value
  if (!membership) return t('auth.standardUser')
  const until = membership.ends_at ? new Date(membership.ends_at).toLocaleDateString(currentLocale.value) : t('auth.validForever')
  return `${membership.plan} · ${until}`
})

const userInitial = computed(() => {
  const source = auth.state.user?.name || auth.state.user?.email || 'U'
  return source.slice(0, 1).toUpperCase()
})

const displayName = computed(() => auth.state.user?.name || auth.state.user?.email || t('auth.notLoggedIn'))

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
            <path d="M4 6a2 2 0 0 1 2 -2h12a2 2 0 0 1 2 2v12a2 2 0 0 1 -2 2H6a2 2 0 0 1 -2 -2z" stroke-width="1.6" />
            <path d="M9 4v16" stroke-width="1.6" />
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

    <div class="sidebar__settings">
      <div class="lang-switcher">
        <button class="lang-btn" type="button" @click="toggleLangMenu">
          <svg class="lang-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"/>
            <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
            <path d="M2 12h20"/>
          </svg>
          <span v-if="props.isOpen" class="lang-label">{{ currentLocaleLabel }}</span>
        </button>
        <div v-if="langMenuOpen" class="lang-menu">
          <button
            v-for="locale in supportedLocales"
            :key="locale.value"
            :class="['lang-menu-item', { 'is-active': currentLocale === locale.value }]"
            type="button"
            @click="selectLocale(locale.value)"
          >
            {{ locale.label }}
          </button>
        </div>
      </div>
    </div>

    <footer class="sidebar__footer">
      <button class="user-chip" type="button" @click="handleUserChipClick">
        <div class="avatar">{{ userInitial }}</div>
        <div v-if="props.isOpen" class="user-chip__text">
          <span class="plan-badge">{{ membershipLabel }}</span>
          <span class="name">{{ displayName }}</span>
        </div>
        <svg v-if="props.isOpen" class="chevron" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="6 9 12 15 18 9"></polyline>
        </svg>
      </button>
    </footer>
  </aside>

  <AuthPopup v-model:open="authPopupOpen" />
</template>

<style scoped>
.sidebar {
  --rail-size: 48px;
  display: flex;
  flex-direction: column;
  border-right: 1px solid rgba(15, 23, 42, 0.08);
  padding: 20px 16px;
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
  font-size: 17px;
  color: #0f172a;
  white-space: nowrap;
  transition: opacity 0.25s ease, transform 0.25s ease;
}

.sidebar.is-collapsed .sidebar__brand-text {
  opacity: 0;
  transform: translateX(-8px);
  pointer-events: none;
}

.sidebar.is-collapsed .sidebar__brand {
  display: none;
}

.toggle-wrap {
  position: relative;
  display: flex;
  align-items: center;
  margin-left: auto;
}

.sidebar.is-collapsed .sidebar__header {
  justify-content: center;
}

.sidebar.is-collapsed .toggle-wrap {
  margin-left: 0;
}

.sidebar.is-collapsed .toggle-btn {
  width: var(--rail-size);
  height: var(--rail-size);
}

.toggle-btn {
  background: transparent;
  border: none;
  width: 34px;
  height: 34px;
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
  width: 22px;
  height: 22px;
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
  gap: 12px;
  padding: 8px 12px;
  border-radius: 12px;
  border: 1px solid transparent;
  background: #f1f5f9;
  cursor: pointer;
  transition: background 0.2s ease, border-color 0.2s ease, color 0.2s ease;
  font-size: 13px;
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
  background: transparent;
}

.sidebar.is-collapsed .sidebar__item:not(.is-active):hover {
  background: rgba(15, 23, 42, 0.06);
}

.sidebar__icon {
  width: 30px;
  height: 30px;
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: inherit;
}

.sidebar__icon svg {
  width: 22px;
  height: 22px;
}

.sidebar__body {
  flex: 1;
  display: flex;
  align-items: center;
}

.sidebar__label {
  font-weight: 600;
  font-size: 14px;
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
  border-radius: 24px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  padding: 8px 12px;
  display: flex;
  align-items: center;
  gap: 10px;
  background: #fff;
  cursor: pointer;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08);
  transition: background 0.2s ease, box-shadow 0.2s ease;
}

.user-chip:hover {
  background: #fafafa;
  box-shadow: 0 2px 6px rgba(15, 23, 42, 0.12);
}

.user-chip .avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  flex-shrink: 0;
  background: #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 14px;
  color: #475569;
}

.user-chip__text {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  flex: 1;
  min-width: 0;
}

.user-chip__text .plan-badge {
  font-size: 11px;
  font-weight: 500;
  color: #16a34a;
  padding: 2px 8px;
  border: 1px solid #bbf7d0;
  border-radius: 12px;
  background: transparent;
  margin-bottom: 2px;
}

.user-chip__text .name {
  font-size: 13px;
  font-weight: 500;
  color: #1e293b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}

.user-chip .chevron {
  width: 16px;
  height: 16px;
  color: #64748b;
  flex-shrink: 0;
}

.sidebar.is-collapsed .user-chip__text,
.sidebar.is-collapsed .user-chip .chevron {
  display: none;
}

.sidebar.is-collapsed .user-chip {
  width: var(--rail-size);
  height: var(--rail-size);
  padding: 0;
  border-radius: 50%;
  justify-content: center;
}

.sidebar.is-collapsed .user-chip:hover {
  background: #f1f5f9;
  box-shadow: 0 2px 6px rgba(15, 23, 42, 0.12);
}

.sidebar.is-collapsed .user-chip .avatar {
  width: 32px;
  height: 32px;
}

/* 语言切换 */
.sidebar__settings {
  padding-left: 4px;
  padding-right: 4px;
}

.lang-switcher {
  position: relative;
}

.lang-btn {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 10px 12px;
  border: none;
  border-radius: 12px;
  background: transparent;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  color: #64748b;
  transition: background 0.2s ease, color 0.2s ease;
}

.lang-btn:hover {
  background: rgba(15, 23, 42, 0.06);
  color: #0f172a;
}

.lang-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
}

.lang-label {
  white-space: nowrap;
}

.sidebar.is-collapsed .lang-btn {
  width: var(--rail-size);
  height: var(--rail-size);
  padding: 0;
  justify-content: center;
  margin: 0 auto;
  background: transparent;
}

.sidebar.is-collapsed .lang-btn:hover {
  background: rgba(15, 23, 42, 0.06);
}

.sidebar.is-collapsed .lang-label {
  display: none;
}

.lang-menu {
  position: absolute;
  left: 100%;
  bottom: 0;
  margin-left: 8px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(15, 23, 42, 0.15);
  padding: 6px;
  min-width: 120px;
  z-index: 100;
}

.lang-menu-item {
  display: block;
  width: 100%;
  padding: 10px 14px;
  border: none;
  border-radius: 8px;
  background: transparent;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  color: #64748b;
  text-align: left;
  transition: background 0.15s ease, color 0.15s ease;
}

.lang-menu-item:hover {
  background: #f1f5f9;
  color: #0f172a;
}

.lang-menu-item.is-active {
  background: rgba(37, 99, 235, 0.1);
  color: #1d4ed8;
}
</style>
