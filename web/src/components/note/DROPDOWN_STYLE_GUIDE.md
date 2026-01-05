# Dropdown Style Guide

This guide explains how to properly configure and use Ant Design dropdown menu components in the project, ensuring consistency in icons, text styles, and interactions.

## Table of Contents

- [Basic Configuration](#basic-configuration)
- [HTML Template Structure](#html-template-structure)
- [Icon Imports](#icon-imports)
- [CSS Style Configuration](#css-style-configuration)
- [Delete Option Special Styling](#delete-option-special-styling)
- [Complete Examples](#complete-examples)

---

## Basic Configuration

### Design Principles

1. **Use Ant Design Native Icons** - Use icons from `@ant-design/icons-vue` instead of Lucide icons
2. **Use Icon Slots** - Use `<template #icon>` to let Ant Design handle icon layout automatically
3. **Proper Spacing** - Set 12px spacing between icons and text using CSS `margin-right: 12px`
4. **Consistent Visual Effects** - Maintain uniform styles and interactions across all dropdowns
5. **Special Handling for Delete Options** - Red text with gray hover background, do not use `danger` attribute

---

## HTML Template Structure

### Standard Dropdown Menu Structure

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
    <a-menu @click="onMenuClick(item, $event)">
      <!-- Regular menu items -->
      <a-menu-item key="rename">
        <template #icon>
          <EditOutlined />
        </template>
        Rename
      </a-menu-item>

      <a-menu-item key="download" :disabled="downloading === item.id">
        <template #icon>
          <DownloadOutlined />
        </template>
        Download
      </a-menu-item>

      <!-- Delete option (with special styling) -->
      <a-menu-item key="delete" class="delete-menu-item">
        <template #icon>
          <DeleteOutlined />
        </template>
        Remove
      </a-menu-item>
    </a-menu>
  </template>
</a-dropdown>
```

### Key Points

- `overlay-class-name` must include two class names:
  - `rounded-dropdown` - Global styling
  - `your-custom-class-dropdown` - Component-specific styling (e.g., `materials-actions-dropdown`)
- Use `<template #icon>` to add icons
- Add `class="delete-menu-item"` to delete options for red styling
- **Do NOT** add `<a-menu-divider />` before delete options

---

## Icon Imports

### Import Ant Design Icons

Import required icons in the `<script setup>` section:

```typescript
import {
  EditOutlined,      // Edit/Rename
  DeleteOutlined,    // Delete
  DownloadOutlined   // Download
} from '@ant-design/icons-vue'
```

### Common Icons List

| Function | Icon Component | Usage |
|---------|----------------|-------|
| Edit/Rename | `EditOutlined` | Modify content |
| Delete | `DeleteOutlined` | Delete operations |
| Download | `DownloadOutlined` | Download files |
| Copy | `CopyOutlined` | Copy content |
| Share | `ShareAltOutlined` | Share functionality |
| Settings | `SettingOutlined` | Settings options |

---

## CSS Style Configuration

### Basic Style Template

Add the following styles to your component's `<style scoped>` section:

```css
/* Dropdown menu container styles (global) */
:deep(.rounded-dropdown .ant-dropdown-menu) {
  min-width: 170px;
  padding: 6px 0;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.12);
}

/* Menu item styles */
:deep(.your-custom-class-dropdown .ant-dropdown-menu-item) {
  padding: 10px 14px;
  line-height: 1.5;
  font-size: 14px;
}

/* Menu item content container */
:deep(.your-custom-class-dropdown .ant-dropdown-menu-item .ant-dropdown-menu-title-content) {
  display: flex;
  align-items: center;
}

/* Icon styles */
:deep(.your-custom-class-dropdown .ant-dropdown-menu-item .anticon) {
  font-size: 14px;
  margin-right: 12px;  /* Spacing between icon and text */
}
```

### Style Explanations

- `padding: 10px 14px` - Menu item inner padding
- `font-size: 14px` - Text and icon size
- `margin-right: 12px` - Spacing between icon and text
- `border-radius: 12px` - Corner radius

---

## Delete Option Special Styling

Delete options require special red styling, but the hover background should remain consistent with other options.

### CSS Configuration

```css
/* Delete menu item default styles */
:deep(.your-custom-class-dropdown .delete-menu-item) {
  color: #ff4d4f;  /* Red text */
}

/* Delete menu item hover styles */
:deep(.your-custom-class-dropdown .delete-menu-item:hover) {
  color: #ff4d4f;  /* Keep red text */
  background-color: rgba(0, 0, 0, 0.04) !important;  /* Normal gray background */
}

/* Delete menu item icon styles */
:deep(.your-custom-class-dropdown .delete-menu-item .anticon) {
  color: #ff4d4f;  /* Red icon */
}
```

### Design Guidelines

- ✅ **DO**: Use red color (`#ff4d4f`) for text and icons
- ✅ **DO**: Use normal gray background (`rgba(0, 0, 0, 0.04)`) on hover
- ❌ **DON'T**: Use the `danger` attribute (causes red background)
- ❌ **DON'T**: Add a divider before delete options

---

## Complete Examples

### NoteMaterialsPanel.vue Example

#### HTML Template

```vue
<a-dropdown
  :trigger="['click']"
  placement="bottomRight"
  overlay-class-name="rounded-dropdown materials-actions-dropdown"
>
  <button class="more-btn" type="button" @click.stop>
    <MoreVerticalIcon class="more-icon" />
  </button>
  <template #overlay>
    <a-menu @click="onMenuClick(item, $event)">
      <a-menu-item key="rename">
        <template #icon>
          <EditOutlined />
        </template>
        Rename
      </a-menu-item>
      <a-menu-item key="download" :disabled="downloading === item.id">
        <template #icon>
          <DownloadOutlined />
        </template>
        Download
      </a-menu-item>
      <a-menu-item key="delete" class="delete-menu-item">
        <template #icon>
          <DeleteOutlined />
        </template>
        Remove
      </a-menu-item>
    </a-menu>
  </template>
</a-dropdown>
```

#### Script Section

```typescript
import { message } from 'ant-design-vue'
import {
  EditOutlined,
  DeleteOutlined,
  DownloadOutlined
} from '@ant-design/icons-vue'
import {
  MoreVerticalIcon,
  // ... other Lucide icons
} from 'lucide-vue-next'
```

#### CSS Styles

```css
/* Dropdown menu container */
:deep(.materials-actions-dropdown .ant-dropdown-menu) {
  min-width: 170px;
  padding: 6px 0;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.12);
}

/* Menu item base styles */
:deep(.materials-actions-dropdown .ant-dropdown-menu-item) {
  padding: 10px 14px;
  line-height: 1.5;
  font-size: 14px;
}

:deep(.materials-actions-dropdown .ant-dropdown-menu-item .ant-dropdown-menu-title-content) {
  display: flex;
  align-items: center;
}

/* Icon styles */
:deep(.materials-actions-dropdown .ant-dropdown-menu-item .anticon) {
  font-size: 14px;
  margin-right: 12px;
}

/* Delete option styles */
:deep(.materials-actions-dropdown .delete-menu-item) {
  color: #ff4d4f;
}

:deep(.materials-actions-dropdown .delete-menu-item:hover) {
  color: #ff4d4f;
  background-color: rgba(0, 0, 0, 0.04) !important;
}

:deep(.materials-actions-dropdown .delete-menu-item .anticon) {
  color: #ff4d4f;
}
```

---

## Other Component Examples

### NoteFlashcardsPanel.vue

Use `flashcard-actions-dropdown` as the custom class name:

```vue
<a-dropdown
  trigger="click"
  placement="bottomRight"
  overlay-class-name="rounded-dropdown flashcard-actions-dropdown"
>
  <!-- ... -->
</a-dropdown>
```

CSS styles are similar, just replace the class prefix:

```css
:deep(.flashcard-actions-dropdown .ant-dropdown-menu-item) { /* ... */ }
:deep(.flashcard-actions-dropdown .delete-menu-item) { /* ... */ }
```

### NoteMindMapPanel.vue

Use `mindmap-actions-dropdown` as the custom class name:

```vue
<a-dropdown
  trigger="click"
  placement="bottomRight"
  overlay-class-name="rounded-dropdown mindmap-actions-dropdown"
>
  <!-- ... -->
</a-dropdown>
```

---

## FAQ

### Q: Why is there no spacing between icons and text?

**A**: Make sure:
1. You're using `<template #icon>` instead of placing icons directly in a span
2. Your CSS includes `margin-right: 12px`
3. You're using `!important` to override default styles if needed

### Q: The delete option has a red background, how do I make it gray?

**A**:
1. Don't use the `danger` attribute
2. Use `class="delete-menu-item"`
3. Use `!important` in hover styles to override default styles

### Q: How do I add more menu items?

**A**: Follow the same pattern:

```vue
<a-menu-item key="your-action">
  <template #icon>
    <YourIconOutlined />
  </template>
  Action Name
</a-menu-item>
```

### Q: How should menu items be ordered?

**A**: Recommended order:
1. Primary actions (edit, rename, etc.)
2. Secondary actions (download, share, etc.)
3. Dangerous actions (delete) at the bottom

---

## Changelog

- **2024-01-04**: Initial version based on NoteMaterialsPanel, NoteFlashcardsPanel, and NoteMindMapPanel implementations
- Icon optimization: Migrated from Lucide icons to Ant Design icons
- Style optimization: Unified icon size and spacing
- Delete option optimization: Red text + gray hover background

---

## References

- [Ant Design Vue - Dropdown](https://antdv.com/components/dropdown)
- [Ant Design Icons Vue](https://antdv.com/components/icon)
- [Related Components]
  - `NoteMaterialsPanel.vue`
  - `NoteFlashcardsPanel.vue`
  - `NoteMindMapPanel.vue`
