# Note Panels Layout Guide

适用于 NotesEditorView 内的所有 tab panel（Chat/Materials/Flashcards/MindMap/Quiz...）。目标：继承父容器尺寸、不被大内容撑开、滚动位置可预期。

## 父级布局契约

- 父链：`tabs-panel` → `<Note*Panel>`，父已 `display: flex; flex: 1; min-height: 0; overflow: hidden;`.
- 子 panel 必须：
  - 根卡片 `.xxx-panel`：`height: 100%; display: flex; flex-direction: column; min-width: 0;`
  - `.panel-shell`：`position: relative; height: 100%; display: flex; flex-direction: column; min-height: 0; min-width: 0; overflow: hidden; padding: 16px;`

## 视图结构（单视图或多视图皆可）

- 单视图（如 Materials 预览、纯列表）：用 `.panel-body` 包裹内容。
- 多视图（如 Flashcards 列表/复习、MindMap 列表/画布）：每个视图用 `.panel-view`，用 `v-if/v-else` 切换，未激活视图不应撑开。
- 通用容器样式：
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

## 滚动与溢出策略

- 让滚动只发生在内容区，不要让 `.panel-shell` 自身滚动。
- 内容区/列表区/预览区使用 `overflow: auto; min-height: 0;`（如 `.folders-grid`, `.folder-scroll`, `.preview-content`）。
- 外层（根、shell、view/body）保持 `overflow: hidden;` 防止撑开。
- 大固有宽度内容（画布、大表格、长代码块）所在容器需：
  - `width: 100%; max-width: 100%; min-width: 0;`
  - 需要滚动时加 `overflow: auto;`（MindElixir 的 `.map-container` 就按此处理）。

Mind map 例子：
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

## 遮罩与定位

- 全局 loading/保存遮罩定位在 `.panel-shell`：`position: absolute; inset: 0; z-index: 10+`.
- 局部遮罩（如画布加载、卡片局部）在相对容器内部再 `absolute` 覆盖。

## 开发步骤

1) 模板骨架：`a-card.xxx-panel` → `div.panel-shell` → `div.panel-body/ panel-view` → 内容/滚动区。  
2) 先贴“父级布局契约”里的根和 shell 样式，再为内容区单独加 `overflow: auto`。  
3) 多视图用 `v-if/v-else` 隐藏未激活视图，避免撑开。  
4) 若引入大固有尺寸组件（画布、第三方表格），其包裹层加 `min-width: 0`、`width/max-width: 100%`，必要时再加内部滚动。  
5) 手动检查：缩小窗口并切换 tab，确认无横向滚动条、内容可滚动、遮罩覆盖正确。

## 检查清单

- [ ] 根与 shell 都有 `min-width: 0`、`min-height: 0`、`flex` 填满父级。  
- [ ] 滚动只在指定内容区出现，外层保持 hidden。  
- [ ] 大固有宽度组件的容器已加 `min-width: 0` 且 `width/max-width: 100%`。  
- [ ] 多视图切换时未激活视图不撑开布局。  
- [ ] 遮罩定位在 shell 或局部容器，覆盖正确。  
