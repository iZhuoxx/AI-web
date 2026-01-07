# Note Components Style Guide

统一设计规范，适用于 Note 模块内的所有组件（Panels、Modals、Buttons、Dropdowns）。

---

## 1. Panel 布局规范

适用于 NotesEditorView 内的所有 tab panel（Chat/Materials/Flashcards/MindMap/Quiz...）。

### 1.1 父级布局契约

**父链：** `tabs-panel` → `<Note*Panel>`，父已设置 `display: flex; flex: 1; min-height: 0; overflow: hidden;`

**子 panel 必须：**
```css
/* 根卡片 */
.xxx-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

/* 内部容器 */
.panel-shell {
  position: relative;
  height: 100%;
  display: flex;
  flex-direction: column;
  min-height: 0;
  min-width: 0;
  overflow: hidden;
  padding: 16px;
}
```

### 1.2 视图结构

**单视图** (如 Materials 预览)：用 `.panel-body` 包裹内容
**多视图** (如 Flashcards 列表/复习)：每个视图用 `.panel-view`，用 `v-if/v-else` 切换

```css
.panel-body,
.panel-view {
  flex: 1;
  min-height: 0;
  min-width: 0;
  display: flex;
  flex-direction: column;
  width: 100%;
}
```

### 1.3 滚动与溢出策略

- **原则：** 滚动只在内容区，`.panel-shell` 自身不滚动
- 内容区使用 `overflow: auto; min-height: 0;`（如 `.folders-grid`, `.preview-content`）
- 外层保持 `overflow: hidden;` 防止撑开
- 大固有宽度内容（画布、表格）容器需：
  ```css
  width: 100%;
  max-width: 100%;
  min-width: 0;
  overflow: auto; /* 需要时 */
  ```

**Mind map 示例：**
```css
.mindmap-canvas {
  flex: 1;
  min-height: 400px;
  min-width: 0;
  width: 100%;
  max-width: 100%;
  overflow: hidden;
  position: relative;
}

:deep(.mind-elixir),
:deep(.mind-elixir .map-container) {
  width: 100%;
  max-width: 100%;
  min-width: 0;
  height: 100%;
  overflow: auto;
}
```

### 1.4 遮罩与定位

- **全局遮罩：** 定位在 `.panel-shell`：`position: absolute; inset: 0; z-index: 10+`
- **局部遮罩：** 在相对容器内部 `absolute` 覆盖

### 1.5 浮动操作按钮 (FAB)

用于列表/网格视图底部居中显示主要操作（如"生成闪卡"、"AI生成"）。

**标准样式：**
```css
.generate-fab-center {
  position: absolute;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 10;
  border-radius: 16px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 0 26px;
  height: 48px;
  background: linear-gradient(135deg, #3b82f6, #2563eb);
  border: none;
  font-size: 15px;
  font-weight: 700;
  transition: transform 0.22s ease, filter 0.22s ease;
}

.generate-fab-center:hover {
  transform: translateX(-50%) translateY(-2px) scale(1.02);
  filter: brightness(1.04);
}

.generate-fab-center:active {
  transform: translateX(-50%) translateY(0);
  filter: brightness(0.98);
}
```

**定位要点：**
- 浮动按钮定位在 `.panel-shell` 上（`.panel-shell` 必须有 `position: relative`）
- 内层视图容器（`.list-view`, `.folder-view` 等）**不要**添加 `position: relative`
- 内层视图添加 `position: relative` 会导致按钮定位错误

### 1.6 开发步骤

1. 模板骨架：`a-card.xxx-panel` → `div.panel-shell` → `div.panel-body/panel-view` → 内容/滚动区
2. 先贴"父级布局契约"样式，再为内容区加 `overflow: auto`
3. 多视图用 `v-if/v-else` 隐藏未激活视图
4. 大固有尺寸组件包裹层加 `min-width: 0`、`width/max-width: 100%`
5. 手动检查：缩小窗口并切换 tab，确认无横向滚动条、内容可滚动、遮罩覆盖正确

### 1.7 检查清单

- [ ] 根与 shell 都有 `min-width: 0`、`min-height: 0`、`flex` 填满父级
- [ ] 滚动只在指定内容区，外层保持 hidden
- [ ] 大固有宽度组件容器已加 `min-width: 0` 且 `width/max-width: 100%`
- [ ] 多视图切换时未激活视图不撑开布局
- [ ] 遮罩定位在 shell 或局部容器，覆盖正确
- [ ] `.panel-shell` 有 `position: relative`
- [ ] 内层视图容器**没有** `position: relative`
- [ ] 浮动按钮使用 `.generate-fab-center` 样式，定位在 `.panel-shell` 上

---

## 2. 弹窗（Modal）规范

### 2.1 基础配置

```vue
<a-modal
  v-model:visible="modalState.open"
  :maskClosable="false"
  centered
  destroy-on-close
  wrap-class-name="rounded-modal"
  :width="宽度值"
>
  <!-- 内容 -->
</a-modal>
```

**必需属性：**
- `v-model:visible`: 控制显示/隐藏
- `:maskClosable="false"`: 禁止点击遮罩关闭
- `centered`: 弹窗垂直居中
- `destroy-on-close`: 关闭时销毁内容
- `wrap-class-name="rounded-modal"`: 统一样式类名

### 2.2 弹窗尺寸

| 用途 | 宽度 | 示例 |
|------|------|------|
| 简单确认/输入 | `420px` - `480px` | 重命名、简单表单 |
| 标准表单 | `520px` - `560px` | 编辑闪卡、生成设置 |
| 复杂内容 | `600px` 及以上 | 多字段表单 |

### 2.3 弹窗圆角

**圆角：`28px`** （通过 `.rounded-modal` 全局样式实现）

```css
/* 全局样式（不带 scoped） */
.rounded-modal .ant-modal-content {
  border-radius: 28px !important;
  overflow: hidden;
}

.rounded-modal .ant-modal-header {
  border-radius: 28px 28px 0 0 !important;
  padding: 20px 24px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
}

.rounded-modal .ant-modal-body {
  padding: 20px 24px;
}

.rounded-modal .ant-modal-footer {
  border-radius: 0 0 28px 28px !important;
  padding: 16px 24px;
  border-top: 1px solid rgba(0, 0, 0, 0.06);
}

.rounded-modal .ant-modal-title {
  font-size: 18px;
  font-weight: 700;
}
```

### 2.4 自定义 Footer 弹窗

```vue
<a-modal
  :footer="null"
  wrap-class-name="rounded-modal custom-modal-name"
>
  <div class="edit-modal__body">
    <div class="edit-modal__title">编辑标题</div>
    <label class="edit-label">字段标签</label>
    <a-input v-model:value="value" />
    <div class="modal-actions">
      <a-button @click="handleCancel">取消</a-button>
      <a-button type="primary" :loading="loading" @click="handleConfirm">
        保存
      </a-button>
    </div>
  </div>
</a-modal>
```

**样式（scoped）：**
```css
.edit-modal__body {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 8px 0;
}

.edit-modal__title {
  font-size: 20px;
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 4px;
}

.edit-label {
  font-size: 13px;
  color: #475569;
  font-weight: 600;
  margin-top: 4px;
}

.modal-actions {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
```

**全局样式（不带 scoped）：**
```css
.custom-modal-name .ant-modal-footer {
  display: none;
}
```

### 2.5 表单元素

**输入框圆角：`12px`**

```css
.rounded-modal .ant-input,
.rounded-modal .ant-input-number-input,
.rounded-modal .ant-select-selector,
.rounded-modal .ant-input-textarea-show-count textarea {
  border-radius: 12px !important;
}
```

### 2.6 弹窗内按钮

```css
.rounded-modal .ant-btn {
  border-radius: 12px !important;
  padding: 6px 16px;
  height: auto;
  font-weight: 600;
  font-size: 14px;
}
```

### 2.7 ConfirmModal 组件

统一的确认弹窗组件：`src/components/common/ConfirmModal.vue`

```vue
<ConfirmModal
  v-model="deleteModal.open"
  variant="danger"
  confirm-text="删除"
  cancel-text="取消"
  :on-confirm="handleDelete"
>
  <template v-if="deleteModal.target">
    要删除
    <span class="item-name-box">{{ deleteModal.target.name }}</span>
    吗?
  </template>
</ConfirmModal>
```

**高亮项目名称框：**
```css
.item-name-box {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 4px 12px;
  border-radius: 8px;
  background: #f5f5f5;
  color: #1a1a1a;
  font-weight: 500;
}
```

---

## 3. 按钮（Button）规范

### 3.1 工具栏按钮

```vue
<button class="toolbar-btn" type="button" @click="handleAction">
  <PlusIcon class="btn-icon" />
  添加
</button>
```

**样式：**
```css
.toolbar-btn {
  border: 1px solid rgba(0, 0, 0, 0.08);
  background: #fff;
  padding: 6px 12px;
  border-radius: 10px;
  font-weight: 600;
  font-size: 12px;
  color: #475569;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.toolbar-btn:hover {
  border-color: #3b82f6;
  color: #3b82f6;
  background: rgba(59, 130, 246, 0.04);
}

.toolbar-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

/* 主要按钮变体 */
.toolbar-btn--primary {
  background: #3b82f6;
  color: #fff;
  border-color: #3b82f6;
}

.toolbar-btn--primary:hover {
  background: #2563eb;
  border-color: #2563eb;
}

.toolbar-btn--primary:disabled {
  background: #93c5fd;
  border-color: #93c5fd;
}
```

### 3.2 图标按钮

```vue
<button class="icon-btn" type="button" @click="handleEdit">
  <Edit3Icon class="icon" />
</button>
```

**样式：**
```css
.icon-btn {
  border: 1.5px solid rgba(0, 0, 0, 0.06);
  background: #fff;
  border-radius: 12px;
  width: 36px;
  height: 36px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.icon-btn:hover {
  border-color: #6366f1;
  color: #6366f1;
  background: rgba(99, 102, 241, 0.04);
}

.icon-btn .icon {
  width: 16px;
  height: 16px;
}

/* Ghost 变体 */
.icon-btn.ghost {
  border-color: transparent;
  background: rgba(0, 0, 0, 0.03);
}
```

### 3.3 Pill 按钮

```css
.pill-btn {
  border: 1.5px solid rgba(0, 0, 0, 0.08);
  background: #fff;
  padding: 9px 16px;
  border-radius: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 13px;
  color: #334155;
}

.pill-btn:hover:not(:disabled) {
  border-color: #6366f1;
  color: #6366f1;
  background: rgba(99, 102, 241, 0.04);
}

.pill-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
```

### 3.4 返回按钮

```css
.back-btn {
  border: none;
  background: transparent;
  padding: 8px;
  border-radius: 12px;
  color: #64748b;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
}

.back-btn:hover {
  background: rgba(0, 0, 0, 0.05);
  color: #334155;
}

.back-icon {
  width: 20px;
  height: 20px;
}
```

### 3.5 按钮图标尺寸

```css
.btn-icon {
  width: 14px;
  height: 14px;
}
```

---

## 4. 下拉菜单（Dropdown）规范

### 4.1 基础配置

**设计原则：**
1. 使用 Ant Design 原生图标（`@ant-design/icons-vue`）而非 Lucide 图标
2. 使用 `<template #icon>` 插槽让 Ant Design 自动处理图标布局
3. 图标与文字间距：`12px`
4. 删除选项特殊处理：红色文字 + 灰色悬停背景，**不使用** `danger` 属性

**常用图标：**
```typescript
import {
  EditOutlined,      // 编辑/重命名
  DeleteOutlined,    // 删除
  DownloadOutlined,  // 下载
  CopyOutlined,      // 复制
  ShareAltOutlined,  // 分享
  SettingOutlined    // 设置
} from '@ant-design/icons-vue'
```

### 4.2 模板结构

```vue
<a-dropdown
  trigger="click"
  placement="bottomRight"
  overlay-class-name="rounded-dropdown your-custom-class-dropdown"
>
  <button class="more-btn" type="button" @click.stop>
    <MoreVerticalIcon class="more-icon" />
  </button>
  <template #overlay>
    <a-menu @click="onMenuClick">
      <a-menu-item key="rename">
        <template #icon>
          <EditOutlined />
        </template>
        重命名
      </a-menu-item>
      <a-menu-item key="download">
        <template #icon>
          <DownloadOutlined />
        </template>
        下载
      </a-menu-item>
      <a-menu-item key="delete" class="delete-menu-item">
        <template #icon>
          <DeleteOutlined />
        </template>
        删除
      </a-menu-item>
    </a-menu>
  </template>
</a-dropdown>
```

**要点：**
- `overlay-class-name` 包含两个类名：`rounded-dropdown`（全局）+ `your-custom-class-dropdown`（组件特定）

### 4.3 样式配置

**基础样式（scoped）：**
```css
/* 菜单容器 */
:deep(.rounded-dropdown .ant-dropdown-menu) {
  min-width: 170px;
  padding: 6px 0;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.12);
}

/* 菜单项 */
:deep(.your-custom-class-dropdown .ant-dropdown-menu-item) {
  padding: 10px 14px;
  line-height: 1.5;
  font-size: 14px;
}

:deep(.your-custom-class-dropdown .ant-dropdown-menu-item .ant-dropdown-menu-title-content) {
  display: flex;
  align-items: center;
}

/* 图标样式 */
:deep(.your-custom-class-dropdown .ant-dropdown-menu-item .anticon) {
  font-size: 14px;
  margin-right: 12px;
}
```

## 5. 卡片（Card）规范

### 5.1 文件夹卡片（Google Material Design Style）

**设计原则：**
- 遵循 Google Material Design 规范
- 统一的浅色背景，避免多彩渐变
- 使用微妙的阴影和边框
- 悬停时显示主题色侧边栏
- 图标与标题组合提升识别度

**基础样式：**
```css
.folder-card {
  background: #fafafa;              /* 浅灰背景，与白色区分 */
  border-radius: 16px;
  padding: 20px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

/* 左侧主题色条 - 悬停时显示 */
.folder-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 4px;
  height: 100%;
  background: linear-gradient(180deg, #3b82f6, #2563eb);  /* 蓝色用于闪卡 */
  /* background: linear-gradient(180deg, #16a34a, #15803d); */ /* 绿色用于思维导图 */
  opacity: 0;
  transition: opacity 0.2s ease;
  pointer-events: none;
}

.folder-card:hover {
  transform: translateY(-2px);
  background: #ffffff;              /* 悬停时变为纯白 */
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08), 0 2px 4px rgba(0, 0, 0, 0.04);
  border-color: rgba(59, 130, 246, 0.15);  /* 蓝色用于闪卡 */
  /* border-color: rgba(22, 163, 74, 0.15); */ /* 绿色用于思维导图 */
}

.folder-card:hover::before {
  opacity: 1;
}

.folder-card:active {
  transform: translateY(0);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}
```

**卡片标题结构：**
```vue
<div class="folder-title">
  <SquareStackIcon class="folder-icon" />
  <span class="folder-title-text">{{ folder.name }}</span>
</div>
```

**标题样式：**
```css
.folder-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 6px;
}

.folder-title-text {
  font-size: 16px;
  letter-spacing: -0.01em;
}

.folder-icon {
  width: 18px;
  height: 18px;
  color: #3b82f6;  /* 蓝色用于闪卡 */
  /* color: #16a34a; */ /* 绿色用于思维导图 */
}
```

**推荐图标：**
- 闪卡面板：`SquareStackIcon`（堆叠卡片）
- 思维导图面板：`NetworkIcon`（网络节点）

**主题色配置：**
| 面板类型 | 主题色 | 边框 Hover | 图标颜色 |
|---------|--------|-----------|---------|
| 闪卡 | 蓝色渐变 | `rgba(59, 130, 246, 0.15)` | `#3b82f6` |
| 思维导图 | 绿色渐变 | `rgba(22, 163, 74, 0.15)` | `#16a34a` |

**材料标签样式：**
```css
.material-tag {
  display: inline-flex;
  align-items: center;
  padding: 3px 10px;
  background: transparent;  /* 无背景，无边框 */
  border-radius: 12px;
  color: #6b7280;
  font-size: 12px;
  font-weight: 500;
}

.material-more {
  font-size: 12px;
  color: #6b7280;
  font-weight: 500;
}
```

### 5.2 内容卡片（闪卡列表项）

```css
.card-row {
  background: #fff;
  border-radius: 16px;
  border: 1.5px solid rgba(0, 0, 0, 0.04);
  padding: 18px 20px;
  display: flex;
  align-items: center;
  transition: all 0.2s ease;
  position: relative;
}

.card-row:hover {
  border-color: rgba(99, 102, 241, 0.2);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04);
}
```

### 5.3 文件夹卡片设计要点

**推荐：**
- 使用统一的纯白背景（`#ffffff`）
- 主题色仅在悬停时通过左侧边栏显示
- 图标与标题组合增强视觉识别
- 材料标签保持简洁无背景

---

## 6. 设计规范

### 6.1 颜色

**文字：**
| 用途 | 颜色值 |
|------|--------|
| 主标题 | `#0f172a` |
| 副标题 | `#1e293b` |
| 正文 | `#475569` |
| 辅助文字 | `#64748b` |
| 提示/禁用 | `#94a3b8` |

**品牌色：**
| 用途 | 颜色值 |
|------|--------|
| 主色（蓝） | `#3b82f6` |
| 主色 Hover | `#2563eb` |
| 主色淡化 | `rgba(59, 130, 246, 0.04)` |
| 紫色强调 | `#6366f1` |
| 紫色淡化 | `rgba(99, 102, 241, 0.04)` |

**语义色：**
| 用途 | 颜色值 |
|------|--------|
| 危险/删除 | `#ff4d4f` |
| 成功 | `#22c55e` |
| 警告 | `#fbbf24` |

### 6.2 圆角

| 元素 | 圆角值 |
|------|--------|
| 弹窗 | `28px` |
| 文件夹卡片 | `20px` |
| 内容卡片 | `16px` |
| FAB 按钮 | `16px` |
| Pill 按钮 | `14px` |
| 下拉菜单、表单元素、图标按钮 | `12px` |
| 工具栏按钮 | `10px` |
| 项目名称框 | `8px` |

### 6.3 间距

**组件间距：**
```css
gap: 5px;   /* 工具栏按钮内图标 */
gap: 6px;   /* 紧凑：按钮组、标签 */
gap: 8px;   /* FAB 按钮内、项目名称框 */
gap: 10px;  /* 标准：表单元素、按钮容器 */
gap: 12px;  /* 舒适：卡片列表、表单字段 */
gap: 16px;  /* 宽松：工具栏、大块内容 */
gap: 20px;  /* 大间距：卡片列表、内容分组 */
```

**内边距：**
```css
padding: 8px;          /* 小按钮 */
padding: 6px 12px;     /* 工具栏按钮 */
padding: 9px 16px;     /* Pill 按钮 */
padding: 10px 14px;    /* 下拉菜单项 */
padding: 0 26px;       /* FAB 按钮（高度 48px） */
padding: 18px 20px;    /* 卡片 */
padding: 20px 24px;    /* 弹窗 body */
```

### 6.4 阴影

```css
box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04);   /* 轻微 - 悬浮卡片 */
box-shadow: 0 8px 32px rgba(0, 0, 0, 0.08);   /* 标准 - 快速复习卡片 */
box-shadow: 0 12px 30px rgba(0, 0, 0, 0.12);  /* 强阴影 - 下拉菜单 */
```

### 6.5 过渡动画

```css
transition: all 0.2s ease;                           /* 快速响应：按钮、小元素 */
transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);  /* 流畅：卡片移动 */

/* 卡片翻转 */
transition: transform 0.6s;
transform-style: preserve-3d;
backface-visibility: hidden;
```

---

## 7. 样式作用域

### 7.1 局部 vs 全局

```vue
<style scoped>
/* 组件内部样式 */
</style>

<style>
/* 弹窗全局样式 - 不带 scoped */
.rounded-modal .ant-modal-content {
  border-radius: 28px !important;
}
</style>
```

### 7.2 :deep() 用法

对于需要深入修改第三方组件样式：

```css
:deep(.your-custom-class-dropdown .delete-menu-item) {
  color: #ff4d4f;
}
```

---

## 8. 响应式设计

```css
@media (max-width: 768px) {
  .panel-shell {
    padding: 12px;
  }

  .fast-footer {
    flex-direction: column;
    gap: 12px;
  }
}
```

---

## 9. 检查清单

### Panel 布局
- [ ] 根与 shell 都有 `min-width: 0`、`min-height: 0`、`flex` 填满父级
- [ ] 滚动只在指定内容区，外层保持 hidden
- [ ] `.panel-shell` 有 `position: relative`
- [ ] 内层视图容器**没有** `position: relative`
- [ ] 浮动按钮定位正确

### 弹窗
- [ ] 使用 `wrap-class-name="rounded-modal"`
- [ ] 弹窗圆角 `28px`
- [ ] 表单元素圆角 `12px`
- [ ] 使用 `edit-modal__body`、`edit-modal__title`、`edit-label`、`modal-actions` 类
- [ ] 全局弹窗样式不使用 scoped

### 按钮
- [ ] 使用标准颜色值
- [ ] hover 状态有 `0.2s ease` 过渡
- [ ] 禁用状态有适当的 opacity
- [ ] 按钮有合适的 `gap` 和图标尺寸

### 下拉菜单
- [ ] 使用 Ant Design 图标（不是 Lucide）
- [ ] 使用 `<template #icon>` 插槽
- [ ] 图标与文字间距 `12px`
- [ ] 删除选项使用 `class="delete-menu-item"`，**不使用** `danger` 属性

---
