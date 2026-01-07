# 删除确认弹窗 - 最终版本 ✅

## 设计说明

完全参考 NoteFlashcardsPanel 中其他弹窗（编辑闪卡、添加闪卡）的设计风格，实现了统一的视觉效果。

## 视觉布局

### 删除闪卡弹窗
```
┌──────────────────────────────────┐
│                                  │
│  要删除                          │
│  ┌────────────────────┐          │
│  │ 闪卡问题           │          │
│  └────────────────────┘          │
│  吗?                             │
│                                  │
│                  [取消]  [删除]  │
│                   灰色    红色   │
└──────────────────────────────────┘
```

## 设计规范

### 布局
- **宽度**: 480px (与编辑/添加弹窗一致)
- **圆角**: 28px (使用 rounded-modal)
- **内边距**: 标准弹窗内边距
- **按钮位置**: 右下角

### 文字
- **字号**: 17px
- **颜色**: #1a1a1a (纯黑)
- **行高**: 1.6
- **对齐**: 左对齐

### 名称框
- **背景**: #f5f5f5 (浅灰)
- **颜色**: #1a1a1a
- **内边距**: 4px 12px
- **圆角**: 8px
- **字重**: 500

### 按钮
- **位置**: 右下角
- **间距**: 10px
- **使用**: Ant Design 标准按钮

#### 取消按钮
- 默认样式的 a-button

#### 删除按钮
- type="primary" danger
- Ant Design 红色危险按钮

## 使用示例

### 删除闪卡
```vue
<ConfirmModal
  v-model="deleteCardModal.open"
  variant="danger"
  confirm-text="删除"
  cancel-text="取消"
  :on-confirm="handleDeleteCard"
>
  要删除
  <span class="item-name-box">
    {{ card.question }}
  </span>
  吗?
</ConfirmModal>
```

### 删除合集
```vue
<ConfirmModal
  v-model="deleteFolderModal.open"
  variant="danger"
  confirm-text="删除"
  cancel-text="取消"
  :on-confirm="handleDeleteFolder"
>
  要删除合集
  <span class="item-name-box">
    {{ folder.name }}
  </span>
  吗?
</ConfirmModal>
```

## 关键特点

✅ **与其他弹窗一致** - 480px 宽度，rounded-modal 样式
✅ **按钮右对齐** - 与编辑/添加弹窗的按钮位置一致
✅ **纯黑文字** - #1a1a1a 而非灰色，更清晰
✅ **灰色名称框** - #f5f5f5 背景，突出显示要删除的项目
✅ **Ant Design 按钮** - 使用标准的 danger 按钮样式
✅ **左对齐内容** - 文本左对齐，不居中

## 文件变更

- ✅ [ConfirmModal.vue](web/src/components/common/ConfirmModal.vue) - 完全重构
- ✅ [NoteFlashcardsPanel.vue](web/src/components/note/NoteFlashcardsPanel.vue) - 使用新弹窗
- ✅ [ConfirmModal.md](web/src/components/common/ConfirmModal.md) - 更新文档

## 统一性

现在 NoteFlashcardsPanel 的删除确认弹窗与其他弹窗（编辑闪卡、添加闪卡）保持完全一致的视觉风格! 🎉
