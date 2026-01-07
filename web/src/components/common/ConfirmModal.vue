<template>
  <a-modal
    v-model:visible="visible"
    :footer="null"
    :maskClosable="false"
    :width="480"
    centered
    destroy-on-close
    wrap-class-name="rounded-modal confirm-modal-wrapper"
    @cancel="handleCancel"
  >
    <div class="confirm-modal__body">
      <div class="confirm-modal__text">
        <slot>{{ description }}</slot>
      </div>
      <div class="modal-actions">
        <a-button :disabled="loading" @click="handleCancel">
          {{ cancelText }}
        </a-button>
        <a-button
          type="primary"
          danger
          :loading="loading"
          @click="handleConfirm"
        >
          {{ confirmText }}
        </a-button>
      </div>
    </div>
  </a-modal>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'

interface Props {
  modelValue: boolean
  description?: string
  confirmText?: string
  cancelText?: string
  variant?: 'danger' | 'warning' | 'info' | 'success'
  onConfirm?: () => void | Promise<void>
}

const props = withDefaults(defineProps<Props>(), {
  description: '',
  confirmText: '确认',
  cancelText: '取消',
  variant: 'danger',
})

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'confirm'): void
  (e: 'cancel'): void
}>()

const visible = ref(props.modelValue)
const loading = ref(false)

watch(
  () => props.modelValue,
  (val) => {
    visible.value = val
  }
)

watch(visible, (val) => {
  emit('update:modelValue', val)
})

const handleCancel = () => {
  if (loading.value) return
  visible.value = false
  emit('cancel')
}

const handleConfirm = async () => {
  if (loading.value) return

  loading.value = true
  try {
    if (props.onConfirm) {
      await props.onConfirm()
    }
    emit('confirm')
    visible.value = false
  } catch (error) {
    // 错误由调用方处理
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.confirm-modal__body {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 8px 0;
}

.confirm-modal__text {
  font-size: 17px;
  color: #1a1a1a;
  line-height: 1.6;
  margin-bottom: 8px;
}

.modal-actions {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>
