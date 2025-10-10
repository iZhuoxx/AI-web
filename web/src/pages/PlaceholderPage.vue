<script setup lang="ts">
const props = defineProps<{
  title: string
  description?: string
}>()
</script>

<template>
  <section class="placeholder">
    <div class="placeholder__card">
      <h1>{{ props.title }}</h1>
      <p v-if="props.description">{{ props.description }}</p>
      <p class="placeholder__hint">
        功能正在开发中，敬请期待。
      </p>
    </div>
  </section>
</template>

<style scoped>
.placeholder {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f7f7f8;
  padding: 32px;
  box-sizing: border-box;
}

.placeholder__card {
  width: min(480px, 100%);
  background: #ffffff;
  padding: 32px;
  border-radius: 18px;
  box-shadow: 0 18px 36px rgba(15, 23, 42, 0.08);
  text-align: center;
}

.placeholder__card h1 {
  margin: 0 0 16px;
  font-size: 24px;
  font-weight: 600;
  color: #111827;
}

.placeholder__card p {
  margin: 8px 0;
  color: #4b5563;
}

.placeholder__hint {
  font-size: 13px;
  color: #9ca3af;
}
</style>
