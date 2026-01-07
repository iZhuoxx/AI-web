# 快速参考手册

> 快速查找常用样式类名和配置

---

## 🎯 我想要...

### 创建一个弹窗
```vue
<a-modal
  v-model:visible="modal.open"
  wrap-class-name="rounded-modal"
  :maskClosable="false"
  centered
  destroy-on-close
  :width="520"
>
  <!-- 内容 -->
</a-modal>
```

### 创建确认删除弹窗
```vue
<ConfirmModal
  v-model="deleteModal.open"
  variant="danger"
  confirm-text="删除"
  :on-confirm="handleDelete"
>
  要删除吗？
</ConfirmModal>
```

### 创建编辑表单弹窗
```vue
<a-modal :footer="null" wrap-class-name="rounded-modal">
  <div class="edit-modal__body">
    <div class="edit-modal__title">编辑</div>
    <label class="edit-label">标题</label>
    <a-input v-model:value="title" />
    <div class="modal-actions">
      <a-button @click="cancel">取消</a-button>
      <a-button type="primary" @click="save">保存</a-button>
    </div>
  </div>
</a-modal>
```

### 创建工具栏按钮
```vue
<button class="toolbar-btn" @click="action">
  <Icon class="btn-icon" />
  文字
</button>
```

### 创建主要操作按钮
```vue
<button class="toolbar-btn toolbar-btn--primary" @click="action">
  <Icon class="btn-icon" />
  主要操作
</button>
```

### 创建图标按钮
```vue
<button class="icon-btn" @click="action">
  <Icon class="icon" />
</button>
```

### 创建导航按钮
```vue
<button class="pill-btn" :disabled="disabled" @click="action">
  下一页
</button>
```

### 创建返回按钮
```vue
<button class="back-btn" @click="goBack">
  <ArrowLeftIcon class="back-icon" />
</button>
```

### 创建文件夹卡片
```vue
<div class="folder-card folder-card--color-0" @click="open">
  <div class="folder-card__head">
    <div class="folder-info">
      <div class="folder-title">标题</div>
      <div class="folder-desc">描述</div>
    </div>
  </div>
</div>
```

### 创建内容卡片
```vue
<div class="card-row">
  <div style="flex: 1;">内容</div>
  <button class="icon-btn"><Icon class="icon" /></button>
</div>
```

### 创建空状态
```vue
<div class="empty-panel">
  <Icon class="empty-icon" />
  <div class="empty-title">暂无内容</div>
  <p class="empty-desc">提示文字</p>
</div>
```

---

## 📐 常用尺寸

| 用途 | 值 |
|------|------|
| 弹窗圆角 | `28px` |
| 表单元素圆角 | `12px` |
| 按钮圆角 | `10px` - `14px` |
| 卡片圆角 | `16px` - `20px` |
| 弹窗宽度（小） | `420px` - `480px` |
| 弹窗宽度（中） | `520px` - `560px` |
| 图标按钮尺寸 | `36px × 36px` |
| 按钮图标大小 | `14px` |
| 卡片图标大小 | `16px` |

---

## 🎨 常用颜色

| 用途 | 值 |
|------|------|
| 主标题 | `#0f172a` |
| 正文 | `#475569` |
| 辅助文字 | `#64748b` |
| 提示文字 | `#94a3b8` |
| 主色（蓝） | `#3b82f6` |
| 主色深 | `#2563eb` |
| 强调（紫） | `#6366f1` |
| 危险 | `#ff4d4f` |

---

## 📏 常用间距

| 用途 | 值 |
|------|------|
| 紧凑间距 | `gap: 6px` |
| 标准间距 | `gap: 10px` |
| 舒适间距 | `gap: 12px` |
| 宽松间距 | `gap: 16px` |
| 大间距 | `gap: 20px` |

---

## 📦 导入样式

```vue
<style scoped>
@import '@/components/common/modal-styles.css';
@import '@/components/common/button-styles.css';
@import '@/components/common/card-styles.css';
</style>
```

---

## 必需属性

### 弹窗
- `wrap-class-name="rounded-modal"`
- `:maskClosable="false"`
- `centered`
- `destroy-on-close`

### 下拉菜单
- `overlay-class-name="rounded-dropdown"`

---

## 🔗 完整文档

- **详细设计规范**: `note/MODAL_STYLE_GUIDE.md`
- **代码示例**: `common/USAGE_EXAMPLES.md`
- **组织说明**: `common/README.md`
