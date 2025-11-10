<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { message } from 'ant-design-vue'
import { useAuth } from '@/composables/useAuth'

const props = defineProps<{ open: boolean }>()
const emit = defineEmits<{ (e: 'update:open', value: boolean): void }>()

const auth = useAuth()
const authMode = ref<'login' | 'register'>('login')
const formState = reactive({ email: '', password: '', name: '' })

const isSubmitting = computed(() => auth.state.loading)
const displayName = computed(() => auth.state.user?.name || auth.state.user?.email || '未登录')
const userInitial = computed(() => {
  const source = auth.state.user?.name || auth.state.user?.email || 'U'
  return source.slice(0, 1).toUpperCase()
})

const activeMembership = computed(() => auth.state.memberships.find(item => item.status === 'active'))
const membershipLabel = computed(() => {
  const membership = activeMembership.value
  if (!membership) return '标准用户'
  const until = membership.ends_at ? new Date(membership.ends_at).toLocaleDateString('zh-CN') : '长期有效'
  return `${membership.plan} · ${until}`
})

const handleClose = () => {
  emit('update:open', false)
}

const validateForm = () => {
  if (!formState.email.trim()) {
    message.warning('请输入邮箱')
    return false
  }
  if (!formState.password.trim()) {
    message.warning('请输入密码')
    return false
  }
  if (authMode.value === 'register' && !formState.name.trim()) {
    message.warning('请输入昵称')
    return false
  }
  return true
}

const handleSubmit = async () => {
  if (!validateForm()) return
  try {
    if (authMode.value === 'login') {
      await auth.login(formState.email, formState.password)
    } else {
      await auth.register({ email: formState.email, password: formState.password, name: formState.name })
    }
    formState.password = ''
  } catch (err) {
    // handled by useAuth
  }
}

const handleLogout = async () => {
  try {
    await auth.logout()
  } catch (err) {
    // handled by useAuth
  }
}

watch(
  () => props.open,
  open => {
    if (open && !auth.state.ready) {
      void auth.bootstrap()
    }
    if (!open) {
      formState.password = ''
    }
  }
)

watch(
  () => auth.state.user,
  user => {
    if (!user) {
      authMode.value = 'login'
    }
  }
)
</script>

<template>
  <Teleport to="body">
    <transition name="auth-popup-fade">
      <div v-if="props.open" class="auth-popup">
        <div class="auth-popup__panel">
          <button class="auth-popup__close" type="button" aria-label="关闭" @click="handleClose">×</button>

          <template v-if="!auth.state.ready">
            <div class="auth-popup__loading">
              <a-spin />
            </div>
          </template>

          <template v-else-if="auth.isAuthenticated.value">
            <div class="auth-popup__session">
              <div class="session-avatar">{{ userInitial }}</div>
              <div class="session-info">
                <strong>{{ displayName }}</strong>
                <span>{{ membershipLabel }}</span>
              </div>
            </div>
            <a-button type="default" block danger :loading="isSubmitting" @click="handleLogout">
              退出登录
            </a-button>
          </template>

          <template v-else>
            <div class="auth-popup__header">
              <h3>{{ authMode === 'login' ? '欢迎回来' : '创建账户' }}</h3>
              <p>{{ authMode === 'login' ? '登录以继续使用所有功能' : '注册后即可同步和保存你的学习资料' }}</p>
            </div>
            <div class="auth-popup__switch">
              <button type="button" :class="['switch-btn', { 'is-active': authMode === 'login' }]" @click="authMode = 'login'">
                登录
              </button>
              <button type="button" :class="['switch-btn', { 'is-active': authMode === 'register' }]" @click="authMode = 'register'">
                注册
              </button>
            </div>
            <a-form layout="vertical">
              <a-form-item label="邮箱">
                <a-input v-model:value="formState.email" type="email" autocomplete="email" placeholder="name@example.com" />
              </a-form-item>
              <a-form-item label="密码">
                <a-input-password v-model:value="formState.password" autocomplete="current-password" placeholder="请输入密码" />
              </a-form-item>
              <a-form-item v-if="authMode === 'register'" label="昵称">
                <a-input v-model:value="formState.name" autocomplete="nickname" placeholder="你的称呼" />
              </a-form-item>
              <a-button type="primary" block :loading="isSubmitting" @click="handleSubmit">
                {{ authMode === 'login' ? '登录' : '注册并登录' }}
              </a-button>
            </a-form>
          </template>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<style scoped>
.auth-popup {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  padding: 20px;
}

.auth-popup__panel {
  position: relative;
  width: min(420px, 90vw);
  border-radius: 24px;
  padding: 56px 32px 32px;
  background: #fff;
  box-shadow: 0 30px 80px rgba(15, 23, 42, 0.35);
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.auth-popup__close {
  position: absolute;
  top: 16px;
  right: 16px;
  width: 34px;
  height: 34px;
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.05);
  border: none;
  cursor: pointer;
  font-size: 18px;
  line-height: 1;
  transition: background 0.2s ease;
}

.auth-popup__close:hover {
  background: rgba(15, 23, 42, 0.12);
}

.auth-popup__loading {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 180px;
}

.auth-popup__session {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  border-radius: 18px;
  background: #f3f6ff;
  margin-top: 8px;
}

.session-avatar {
  width: 48px;
  height: 48px;
  border-radius: 16px;
  background: linear-gradient(135deg, #2563eb, #60a5fa);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 18px;
}

.session-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.session-info span {
  color: #64748b;
  font-size: 13px;
}

.auth-popup__header h3 {
  margin: 0;
  font-size: 20px;
}

.auth-popup__header p {
  margin: 4px 0 0;
  color: #6b7280;
}

.auth-popup__switch {
  display: inline-flex;
  border: 1px solid rgba(15, 23, 42, 0.1);
  border-radius: 999px;
  overflow: hidden;
  align-self: center;
}

.switch-btn {
  border: none;
  background: transparent;
  padding: 8px 22px;
  cursor: pointer;
  font-weight: 600;
  color: #475569;
  transition: background 0.2s ease, color 0.2s ease;
}

.switch-btn.is-active {
  background: #2563eb;
  color: #fff;
}

.auth-popup-fade-enter-active,
.auth-popup-fade-leave-active {
  transition: opacity 0.2s ease;
}

.auth-popup-fade-enter-from,
.auth-popup-fade-leave-to {
  opacity: 0;
}
</style>
