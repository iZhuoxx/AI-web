# 弹窗和按钮使用示例

本文档提供了常见弹窗和按钮的使用示例代码，可直接复制使用。

---

## 目录

1. [弹窗示例](#弹窗示例)
2. [按钮示例](#按钮示例)
3. [卡片示例](#卡片示例)
4. [完整组件示例](#完整组件示例)

---

## 弹窗示例

### 1. 标准确认弹窗（使用 ConfirmModal 组件）

```vue
<template>
  <ConfirmModal
    v-model="deleteModal.open"
    variant="danger"
    confirm-text="删除"
    cancel-text="取消"
    :on-confirm="handleDelete"
  >
    要删除
    <span class="item-name-box">
      {{ deleteModal.target?.name }}
    </span>
    吗?
  </ConfirmModal>
</template>

<script setup lang="ts">
import { reactive } from 'vue'
import ConfirmModal from '@/components/common/ConfirmModal.vue'

const deleteModal = reactive({
  open: false,
  target: null as { id: string; name: string } | null,
})

const promptDelete = (item: { id: string; name: string }) => {
  deleteModal.target = item
  deleteModal.open = true
}

const handleDelete = async () => {
  if (!deleteModal.target) return
  // 执行删除操作
  console.log('Deleting:', deleteModal.target.id)
}
</script>

<style scoped>
@import '@/components/common/modal-styles.css';
</style>
```

---

### 2. 标准编辑弹窗（自定义 Footer）

```vue
<template>
  <a-modal
    v-model:visible="editModal.open"
    :footer="null"
    :maskClosable="false"
    :width="520"
    centered
    destroy-on-close
    wrap-class-name="rounded-modal"
  >
    <div class="edit-modal__body">
      <div class="edit-modal__title">编辑项目</div>

      <label class="edit-label">标题</label>
      <a-input v-model:value="editModal.title" placeholder="输入标题" />

      <label class="edit-label">描述</label>
      <a-textarea
        v-model:value="editModal.description"
        :auto-size="{ minRows: 2, maxRows: 6 }"
        placeholder="输入描述"
      />

      <div class="modal-actions">
        <a-button @click="closeEdit">取消</a-button>
        <a-button type="primary" :loading="editModal.loading" @click="handleSave">
          保存
        </a-button>
      </div>
    </div>
  </a-modal>
</template>

<script setup lang="ts">
import { reactive } from 'vue'

const editModal = reactive({
  open: false,
  loading: false,
  title: '',
  description: '',
})

const openEdit = (item: any) => {
  editModal.title = item.title
  editModal.description = item.description
  editModal.open = true
}

const closeEdit = () => {
  editModal.open = false
  editModal.title = ''
  editModal.description = ''
}

const handleSave = async () => {
  editModal.loading = true
  try {
    // 保存逻辑
    console.log('Saving:', editModal.title, editModal.description)
    closeEdit()
  } catch (error) {
    console.error(error)
  } finally {
    editModal.loading = false
  }
}
</script>

<style scoped>
@import '@/components/common/modal-styles.css';
</style>
```

---

### 3. 生成/表单弹窗（带标准 Footer）

```vue
<template>
  <a-modal
    v-model:visible="generateModal.open"
    :confirm-loading="generateModal.loading"
    title="AI 生成内容"
    okText="确认"
    cancelText="取消"
    :maskClosable="false"
    :width="560"
    centered
    destroy-on-close
    wrap-class-name="rounded-modal"
    @ok="handleGenerate"
    @cancel="closeGenerateModal"
  >
    <div class="generate-form">
      <label class="form-label">数量</label>
      <a-input
        v-model:value="generateModal.count"
        type="number"
        min="1"
        placeholder="自动"
      />

      <label class="form-label">选择类型</label>
      <a-select
        v-model:value="generateModal.type"
        style="width: 100%"
        placeholder="请选择类型"
      >
        <a-select-option value="type1">类型 1</a-select-option>
        <a-select-option value="type2">类型 2</a-select-option>
      </a-select>

      <label class="form-label">备注</label>
      <a-textarea
        v-model:value="generateModal.notes"
        :auto-size="{ minRows: 2, maxRows: 4 }"
        placeholder="可选备注信息"
      />
    </div>
  </a-modal>
</template>

<script setup lang="ts">
import { reactive } from 'vue'

const generateModal = reactive({
  open: false,
  loading: false,
  count: '',
  type: undefined as string | undefined,
  notes: '',
})

const openGenerateModal = () => {
  generateModal.count = ''
  generateModal.type = undefined
  generateModal.notes = ''
  generateModal.open = true
}

const closeGenerateModal = () => {
  generateModal.open = false
  generateModal.loading = false
}

const handleGenerate = async () => {
  generateModal.loading = true
  try {
    // 生成逻辑
    console.log('Generating with:', generateModal)
    generateModal.open = false
  } catch (error) {
    console.error(error)
  } finally {
    generateModal.loading = false
  }
}
</script>

<style scoped>
@import '@/components/common/modal-styles.css';
</style>
```

---

## 按钮示例

### 1. 工具栏按钮组

```vue
<template>
  <div class="toolbar">
    <div class="toolbar-left">
      <span class="toolbar-title">项目列表</span>
      <span class="toolbar-count">({{ items.length }})</span>
    </div>
    <div class="toolbar-right">
      <button class="toolbar-btn" type="button" @click="handleAdd">
        <PlusIcon class="btn-icon" />
        添加
      </button>
      <button
        class="toolbar-btn toolbar-btn--primary"
        type="button"
        :disabled="generating"
        @click="handleGenerate"
      >
        <a-spin v-if="generating" size="small" class="btn-spin" />
        <SparklesIcon v-else class="btn-icon" />
        {{ generating ? '生成中...' : 'AI生成' }}
      </button>
      <button class="toolbar-btn" type="button" @click="handleExport">
        <DownloadIcon class="btn-icon" />
        导出
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { PlusIcon, SparklesIcon, DownloadIcon } from 'lucide-vue-next'

const items = ref([])
const generating = ref(false)

const handleAdd = () => console.log('Add')
const handleGenerate = () => console.log('Generate')
const handleExport = () => console.log('Export')
</script>

<style scoped>
@import '@/components/common/button-styles.css';

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 0 16px;
  gap: 16px;
  flex-wrap: wrap;
}

.toolbar-title {
  font-size: 16px;
  font-weight: 600;
  color: #0f172a;
}

.toolbar-count {
  font-size: 14px;
  color: #94a3b8;
  font-weight: 500;
}
</style>
```

---

### 2. 图标按钮

```vue
<template>
  <div class="icon-buttons-demo">
    <!-- 标准图标按钮 -->
    <button class="icon-btn" type="button" @click="handleEdit">
      <Edit3Icon class="icon" />
    </button>

    <!-- Ghost 图标按钮 -->
    <button class="icon-btn ghost" type="button" @click="handleSettings">
      <SettingsIcon class="icon" />
    </button>

    <!-- 小图标按钮 -->
    <button class="icon-btn small" type="button" @click="handleInfo">
      <InfoIcon class="icon small" />
    </button>
  </div>
</template>

<script setup lang="ts">
import { Edit3Icon, SettingsIcon, InfoIcon } from 'lucide-vue-next'

const handleEdit = () => console.log('Edit')
const handleSettings = () => console.log('Settings')
const handleInfo = () => console.log('Info')
</script>

<style scoped>
@import '@/components/common/button-styles.css';

.icon-buttons-demo {
  display: flex;
  gap: 8px;
  align-items: center;
}
</style>
```

---

### 3. 导航 Pill 按钮

```vue
<template>
  <div class="nav-group">
    <button
      class="pill-btn"
      type="button"
      :disabled="currentIndex === 0"
      @click="handlePrev"
    >
      上一页
    </button>
    <div class="counter">{{ currentIndex + 1 }} / {{ total }}</div>
    <button
      class="pill-btn"
      type="button"
      :disabled="currentIndex >= total - 1"
      @click="handleNext"
    >
      下一页
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const currentIndex = ref(0)
const total = ref(10)

const handlePrev = () => {
  if (currentIndex.value > 0) currentIndex.value--
}

const handleNext = () => {
  if (currentIndex.value < total.value - 1) currentIndex.value++
}
</script>

<style scoped>
@import '@/components/common/button-styles.css';

.counter {
  font-weight: 700;
  color: #0f172a;
  font-size: 14px;
  min-width: 60px;
  text-align: center;
}
</style>
```

---

### 4. FAB 浮动按钮

```vue
<template>
  <div class="page-container">
    <!-- 页面内容 -->

    <a-button
      type="primary"
      class="generate-fab-center"
      size="large"
      :loading="loading"
      @click="handleAction"
    >
      <SparklesIcon class="fab-icon" />
      生成内容
    </a-button>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { SparklesIcon } from 'lucide-vue-next'

const loading = ref(false)

const handleAction = () => {
  loading.value = true
  // 执行操作
  setTimeout(() => {
    loading.value = false
  }, 2000)
}
</script>

<style scoped>
@import '@/components/common/button-styles.css';

.page-container {
  position: relative;
  min-height: 400px;
}
</style>
```

---

### 5. 模式切换按钮

```vue
<template>
  <div class="mode-switch-wrapper">
    <div class="mode-switch">
      <button
        class="mode-btn"
        :class="{ 'mode-btn--active': mode === 'list' }"
        type="button"
        @click="setMode('list')"
      >
        列表模式
      </button>
      <button
        class="mode-btn"
        :class="{ 'mode-btn--active': mode === 'grid' }"
        type="button"
        @click="setMode('grid')"
      >
        网格模式
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

type Mode = 'list' | 'grid'
const mode = ref<Mode>('list')

const setMode = (newMode: Mode) => {
  mode.value = newMode
}
</script>

<style scoped>
@import '@/components/common/button-styles.css';
</style>
```

---

## 卡片示例

### 1. 文件夹卡片

```vue
<template>
  <div class="folders-grid">
    <div
      v-for="(folder, index) in folders"
      :key="folder.id"
      class="folder-card"
      :class="`folder-card--color-${index % 6}`"
      @click="openFolder(folder.id)"
    >
      <div class="folder-card__head">
        <div class="folder-info">
          <div class="folder-title">{{ folder.name }}</div>
          <div v-if="folder.description" class="folder-desc">
            {{ folder.description }}
          </div>
          <div class="folder-materials">
            <span class="material-tag">资料 1</span>
            <span class="material-tag">资料 2</span>
            <span class="material-more">+3</span>
          </div>
        </div>
      </div>

      <!-- 菜单按钮 -->
      <a-dropdown
        trigger="click"
        placement="bottomRight"
        overlay-class-name="rounded-dropdown"
      >
        <button class="folder-menu-btn" type="button" @click.stop>
          <MoreVerticalIcon class="menu-icon" />
        </button>
        <template #overlay>
          <a-menu>
            <a-menu-item @click.stop="handleDelete(folder)">
              <template #icon><DeleteOutlined /></template>
              删除
            </a-menu-item>
          </a-menu>
        </template>
      </a-dropdown>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { MoreVerticalIcon } from 'lucide-vue-next'
import { DeleteOutlined } from '@ant-design/icons-vue'

const folders = ref([
  { id: '1', name: '文件夹 1', description: '描述文字' },
  { id: '2', name: '文件夹 2', description: null },
])

const openFolder = (id: string) => console.log('Open folder:', id)
const handleDelete = (folder: any) => console.log('Delete:', folder)
</script>

<style scoped>
@import '@/components/common/card-styles.css';
@import '@/components/common/button-styles.css';
@import '@/components/common/modal-styles.css';
</style>
```

---

### 2. 内容卡片行

```vue
<template>
  <section class="card-list">
    <div v-for="card in cards" :key="card.id" class="card-row">
      <div class="qa">
        <div class="question">{{ card.question }}</div>
        <div class="divider"></div>
        <div class="answer">{{ card.answer }}</div>
      </div>

      <!-- 编辑按钮 -->
      <button class="card-edit-btn" type="button" @click.stop="openEdit(card)">
        <Edit3Icon class="edit-icon" />
      </button>

      <!-- 菜单按钮 -->
      <a-dropdown
        trigger="click"
        placement="bottomRight"
        overlay-class-name="rounded-dropdown"
      >
        <button class="card-menu-btn" type="button" @click.stop>
          <MoreVerticalIcon class="menu-icon" />
        </button>
        <template #overlay>
          <a-menu>
            <a-menu-item @click.stop="handleDelete(card)" class="delete-menu-item">
              <template #icon><DeleteOutlined /></template>
              删除
            </a-menu-item>
          </a-menu>
        </template>
      </a-dropdown>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Edit3Icon, MoreVerticalIcon } from 'lucide-vue-next'
import { DeleteOutlined } from '@ant-design/icons-vue'

const cards = ref([
  { id: '1', question: '问题 1', answer: '答案 1' },
  { id: '2', question: '问题 2', answer: '答案 2' },
])

const openEdit = (card: any) => console.log('Edit:', card)
const handleDelete = (card: any) => console.log('Delete:', card)
</script>

<style scoped>
@import '@/components/common/card-styles.css';
@import '@/components/common/button-styles.css';
@import '@/components/common/modal-styles.css';

.qa {
  flex: 1;
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  gap: 20px;
  align-items: flex-start;
  padding-right: 50px;
}

.question {
  font-weight: 600;
  color: #0f172a;
  font-size: 14px;
  line-height: 1.6;
}

.divider {
  width: 1.5px;
  height: 100%;
  background: linear-gradient(to bottom, transparent, rgba(0, 0, 0, 0.1), transparent);
}

.answer {
  color: #475569;
  font-size: 14px;
  line-height: 1.6;
}

/* 删除菜单项样式 */
:deep(.delete-menu-item) {
  color: #ff4d4f;
}

:deep(.delete-menu-item:hover) {
  color: #ff4d4f;
  background-color: rgba(0, 0, 0, 0.04) !important;
}

:deep(.delete-menu-item .anticon) {
  color: #ff4d4f;
}
</style>
```

---

### 3. 空状态面板

```vue
<template>
  <div class="empty-panel">
    <SparklesIcon class="empty-icon" />
    <div class="empty-title">暂无内容</div>
    <p class="empty-desc">点击下方按钮开始创建</p>
  </div>
</template>

<script setup lang="ts">
import { SparklesIcon } from 'lucide-vue-next'
</script>

<style scoped>
@import '@/components/common/card-styles.css';
</style>
```

---

## 完整组件示例

### 综合示例：带弹窗和按钮的列表面板

```vue
<template>
  <a-card class="panel" :bordered="false">
    <div class="panel-shell">
      <!-- 顶部工具栏 -->
      <div class="toolbar">
        <div class="toolbar-left">
          <span class="toolbar-title">我的项目</span>
          <span class="toolbar-count">({{ items.length }})</span>
        </div>
        <div class="toolbar-right">
          <button class="toolbar-btn" type="button" @click="openAddModal">
            <PlusIcon class="btn-icon" />
            添加
          </button>
          <button class="toolbar-btn toolbar-btn--primary" type="button" @click="openGenerateModal">
            <SparklesIcon class="btn-icon" />
            AI生成
          </button>
        </div>
      </div>

      <!-- 内容列表 -->
      <section v-if="items.length" class="card-list">
        <div v-for="item in items" :key="item.id" class="card-row">
          <div style="flex: 1;">
            <div style="font-weight: 600;">{{ item.title }}</div>
            <div style="color: #64748b; font-size: 13px;">{{ item.description }}</div>
          </div>
          <button class="icon-btn" type="button" @click="openEditModal(item)">
            <Edit3Icon class="icon" />
          </button>
        </div>
      </section>

      <!-- 空状态 -->
      <div v-else class="empty-panel">
        <SparklesIcon class="empty-icon" />
        <div class="empty-title">暂无项目</div>
        <p class="empty-desc">点击"添加"按钮创建第一个项目</p>
      </div>
    </div>
  </a-card>

  <!-- 编辑弹窗 -->
  <a-modal
    v-model:visible="editModal.open"
    :footer="null"
    :maskClosable="false"
    :width="520"
    centered
    destroy-on-close
    wrap-class-name="rounded-modal"
  >
    <div class="edit-modal__body">
      <div class="edit-modal__title">编辑项目</div>
      <label class="edit-label">标题</label>
      <a-input v-model:value="editModal.title" placeholder="输入标题" />
      <label class="edit-label">描述</label>
      <a-textarea v-model:value="editModal.description" :auto-size="{ minRows: 2 }" />
      <div class="modal-actions">
        <a-button @click="closeEditModal">取消</a-button>
        <a-button type="primary" :loading="editModal.loading" @click="handleSave">
          保存
        </a-button>
      </div>
    </div>
  </a-modal>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { PlusIcon, SparklesIcon, Edit3Icon } from 'lucide-vue-next'

const items = ref<Array<{ id: string; title: string; description: string }>>([])

const editModal = reactive({
  open: false,
  loading: false,
  title: '',
  description: '',
  targetId: null as string | null,
})

const openAddModal = () => {
  editModal.title = ''
  editModal.description = ''
  editModal.targetId = null
  editModal.open = true
}

const openEditModal = (item: any) => {
  editModal.title = item.title
  editModal.description = item.description
  editModal.targetId = item.id
  editModal.open = true
}

const closeEditModal = () => {
  editModal.open = false
}

const handleSave = async () => {
  editModal.loading = true
  try {
    // 保存逻辑
    console.log('Save:', editModal)
    closeEditModal()
  } finally {
    editModal.loading = false
  }
}

const openGenerateModal = () => {
  console.log('Open generate modal')
}
</script>

<style scoped>
@import '@/components/common/modal-styles.css';
@import '@/components/common/button-styles.css';
@import '@/components/common/card-styles.css';

.panel {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 0 16px;
  gap: 16px;
  flex-wrap: wrap;
}

.toolbar-title {
  font-size: 16px;
  font-weight: 600;
  color: #0f172a;
}

.toolbar-count {
  font-size: 14px;
  color: #94a3b8;
  font-weight: 500;
}
</style>

<style>
/* 全局弹窗样式需要在不带 scoped 的 style 标签中 */
</style>
```

---

## 快速复制清单

**导入样式文件：**

```vue
<style scoped>
@import '@/components/common/modal-styles.css';
@import '@/components/common/button-styles.css';
@import '@/components/common/card-styles.css';
</style>
```

**弹窗必需属性：**

```vue
wrap-class-name="rounded-modal"
:maskClosable="false"
centered
destroy-on-close
```

**下拉菜单必需属性：**

```vue
overlay-class-name="rounded-dropdown"
```

---

**文档更新：** 2026-01-05
