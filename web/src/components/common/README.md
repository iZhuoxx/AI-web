# Common Components & Styles

本文件夹包含项目中可复用的公共组件和样式文件。

---

## 📁 文件结构

```
common/
├── README.md                    # 本文件
├── ConfirmModal.vue             # 通用确认弹窗组件
├── modal-styles.css             # 弹窗统一样式
├── button-styles.css            # 按钮统一样式
├── card-styles.css              # 卡片统一样式
└── USAGE_EXAMPLES.md            # 使用示例代码集合
```

**Note 文件夹下的额外文档：**
```
note/
└── MODAL_STYLE_GUIDE.md         # 详细的弹窗风格设计规范
```

---

## 📖 文档说明

### 1. MODAL_STYLE_GUIDE.md
**位置：** `src/components/note/MODAL_STYLE_GUIDE.md`

**用途：**
- 详细的设计规范文档
- 包含圆角、颜色、字体、间距等所有设计 token
- 说明设计理念和标准
- 适合设计师和开发者参考

**何时查阅：**
- 需要了解设计规范的完整细节
- 设计新功能时需要参考标准
- 团队新成员学习项目规范

### 2. USAGE_EXAMPLES.md
**位置：** `src/components/common/USAGE_EXAMPLES.md`

**用途：**
- 提供可直接复制的代码示例
- 涵盖常见使用场景
- 包含完整的 Vue 组件示例

**何时查阅：**
- 需要快速实现某个功能
- 不确定如何使用某个样式
- 想要参考最佳实践

---

## 🎨 样式文件

### modal-styles.css
弹窗和下拉菜单的统一样式，包括：
- `.rounded-modal` - 弹窗圆角和布局
- `.rounded-dropdown` - 下拉菜单样式
- `.edit-modal__body`、`.form-modal__body` - 表单布局
- `.modal-actions` - 按钮容器

### button-styles.css
各种按钮样式，包括：
- `.toolbar-btn` - 工具栏按钮
- `.icon-btn` - 图标按钮
- `.pill-btn` - Pill 按钮
- `.back-btn` - 返回按钮
- `.ghost-btn` - Ghost 按钮
- `.generate-fab-center` - FAB 浮动按钮
- `.mode-btn` - 模式切换按钮

### card-styles.css
卡片和布局样式，包括：
- `.folder-card` - 文件夹卡片
- `.card-row` - 内容卡片行
- `.empty-panel` - 空状态面板
- `.fast-card` - 快速复习卡片
- `.panel-shell` - 面板容器

---

## 🧩 组件

### ConfirmModal.vue
通用确认弹窗组件

**Props:**
- `modelValue: boolean` - 控制显示/隐藏
- `description?: string` - 描述文字（可选）
- `confirmText?: string` - 确认按钮文字（默认：确认）
- `cancelText?: string` - 取消按钮文字（默认：取消）
- `variant?: 'danger' | 'warning' | 'info' | 'success'` - 样式变体（默认：danger）
- `onConfirm?: () => void | Promise<void>` - 确认回调

**使用示例：**
```vue
<ConfirmModal
  v-model="deleteModal.open"
  variant="danger"
  confirm-text="删除"
  cancel-text="取消"
  :on-confirm="handleDelete"
>
  要删除 <span class="item-name-box">{{ item.name }}</span> 吗?
</ConfirmModal>
```

---

## 🚀 快速开始

### 1. 导入样式文件

在你的 Vue 组件中导入需要的样式：

```vue
<style scoped>
@import '@/components/common/modal-styles.css';
@import '@/components/common/button-styles.css';
@import '@/components/common/card-styles.css';
</style>
```

### 2. 使用预定义类名

```vue
<template>
  <!-- 弹窗 -->
  <a-modal wrap-class-name="rounded-modal" :maskClosable="false" centered>
    <div class="edit-modal__body">
      <div class="edit-modal__title">标题</div>
      <label class="edit-label">字段</label>
      <a-input />
      <div class="modal-actions">
        <a-button>取消</a-button>
        <a-button type="primary">确认</a-button>
      </div>
    </div>
  </a-modal>

  <!-- 按钮 -->
  <button class="toolbar-btn toolbar-btn--primary">
    <PlusIcon class="btn-icon" />
    添加
  </button>

  <!-- 卡片 -->
  <div class="card-row">
    内容
  </div>
</template>
```

### 3. 使用通用组件

```vue
<script setup lang="ts">
import ConfirmModal from '@/components/common/ConfirmModal.vue'
</script>

<template>
  <ConfirmModal
    v-model="modal.open"
    :on-confirm="handleConfirm"
  >
    确认执行此操作吗？
  </ConfirmModal>
</template>
```

---

## 📋 检查清单

在开发新功能时，请确保：

- [ ] 弹窗使用了 `wrap-class-name="rounded-modal"`
- [ ] 下拉菜单使用了 `overlay-class-name="rounded-dropdown"`
- [ ] 按钮使用了预定义的类名（如 `.toolbar-btn`、`.icon-btn` 等）
- [ ] 卡片样式符合统一标准
- [ ] 导入了需要的样式文件
- [ ] 弹窗设置了 `:maskClosable="false"` 和 `centered`
- [ ] 使用了标准的颜色、字体和间距

---

## 🎯 设计原则

1. **一致性优先**：使用统一的圆角、颜色和间距
2. **可复用性**：优先使用预定义的类名和组件
3. **可维护性**：将样式集中管理，避免重复代码
4. **渐进增强**：从简单到复杂，优先使用现有组件
5. **响应式设计**：考虑移动端适配

---

## 🔧 维护指南

### 添加新样式
1. 首先检查是否可以使用现有样式
2. 如果需要新样式，添加到对应的 CSS 文件中
3. 更新 USAGE_EXAMPLES.md 添加使用示例
4. 如果是设计规范的更改，同步更新 MODAL_STYLE_GUIDE.md

### 修改现有样式
1. 评估修改的影响范围
2. 在所有使用该样式的地方进行测试
3. 更新相关文档

### 添加新组件
1. 在 `common/` 文件夹中创建新组件
2. 遵循现有的命名和结构规范
3. 在本 README 中添加组件说明
4. 在 USAGE_EXAMPLES.md 中添加使用示例

---

## 🤝 贡献

如果你发现：
- 样式不一致的地方
- 可以抽象为公共组件的重复代码
- 文档需要改进的地方
- 新的最佳实践

欢迎提出改进建议！

---

## 📚 相关资源

- [Ant Design Vue](https://www.antdv.com/) - 基础 UI 组件库
- [Lucide Icons](https://lucide.dev/) - 图标库
- [Tailwind Colors](https://tailwindcss.com/docs/customizing-colors) - 色彩参考

---

**最后更新：** 2026-01-05
**维护者：** Web Dev Team
