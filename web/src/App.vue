<script setup lang="ts">
import { ref } from 'vue'
import AppSidebar from '@/components/AppSidebar.vue'

const isSidebarOpen = ref(true)
const toggleSidebar = () => {
  isSidebarOpen.value = !isSidebarOpen.value
}
</script>

<template>
  <div :class="['app-shell', { 'is-collapsed': !isSidebarOpen }]">
    <AppSidebar :is-open="isSidebarOpen" @toggle="toggleSidebar" />
    <div class="app-main">
      <router-view />
    </div>
  </div>
</template>

<style scoped>
.app-shell {
  display: grid;
  grid-template-columns: 260px 1fr;
  height: 100vh;
  width: 100vw;
  background: #f7f7f8;
  color: #111827;
  transition: grid-template-columns 0.25s ease;
}

.app-shell.is-collapsed {
  grid-template-columns: 96px 1fr;
}

.app-main {
  position: relative;
  overflow: hidden;
  background: inherit;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

@media (max-width: 960px) {
  .app-shell {
    grid-template-columns: 220px 1fr;
  }

  .app-shell.is-collapsed {
    grid-template-columns: 72px 1fr;
  }
}
</style>
