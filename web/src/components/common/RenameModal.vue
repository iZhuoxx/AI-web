<template>
  <a-modal
    v-model:visible="visible"
    :footer="null"
    :maskClosable="false"
    :width="width"
    centered
    destroy-on-close
    wrap-class-name="rounded-modal"
    @cancel="handleCancel"
  >
    <div class="rename-modal__body">
      <div class="rename-modal__title">{{ title }}</div>
      <div v-if="subtitle" class="rename-modal__subtitle">{{ subtitle }}</div>
      <label v-if="label" class="rename-modal__label">{{ label }}</label>
      <a-input
        v-model:value="inputValue"
        :maxlength="maxLength"
        :placeholder="placeholder"
      />
      <div class="rename-modal__actions">
        <a-button :disabled="loading" @click="handleCancel">
          {{ cancelText }}
        </a-button>
        <a-button type="primary" :loading="loading" @click="handleConfirm">
          {{ confirmText }}
        </a-button>
      </div>
    </div>
  </a-modal>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  modelValue: boolean
  value: string
  title?: string
  subtitle?: string
  label?: string
  placeholder?: string
  confirmText?: string
  cancelText?: string
  width?: number
  maxLength?: number
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: false,
  value: '',
  title: '重命名',
  label: '名称',
  placeholder: '请输入名称',
  confirmText: '保存',
  cancelText: '取消',
  width: 520,
  maxLength: 255,
  loading: false,
})

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'update:value', value: string): void
  (e: 'confirm'): void
  (e: 'cancel'): void
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
})

const inputValue = computed({
  get: () => props.value,
  set: (val) => emit('update:value', val),
})

const handleCancel = () => {
  if (props.loading) return
  visible.value = false
  emit('cancel')
}

const handleConfirm = () => {
  if (props.loading) return
  emit('confirm')
}
</script>

<style scoped>
.rename-modal__body {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 8px 0;
}

.rename-modal__title {
  font-size: 20px;
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 4px;
}

.rename-modal__subtitle {
  font-size: 13px;
  color: #64748b;
}

.rename-modal__label {
  font-size: 13px;
  color: #475569;
  font-weight: 600;
  margin-top: 4px;
}

.rename-modal__actions {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>
