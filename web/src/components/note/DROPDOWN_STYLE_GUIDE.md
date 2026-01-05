# Dropdown Rounded Style Guide

Quick checklist for giving Ant Design Vue dropdowns the rounded look used across the note panels (Flashcards, Mind Map, Materials).

## How to apply
1) **Add the class on the dropdown overlay:**  
   `overlay-class-name="rounded-dropdown"` (you can append extra classes, e.g., `"rounded-dropdown materials-actions-dropdown"`).
2) **Use shared rounded styles (global block):**
   ```css
   .rounded-dropdown .ant-dropdown-menu {
     border-radius: 12px !important;
     overflow: hidden;
     box-shadow: 0 12px 30px rgba(0, 0, 0, 0.12);
     padding: 6px 0;
   }
   .rounded-dropdown .ant-dropdown-menu-item {
     border-radius: 0;
   }
   ```
   Place this in an unscoped or `:deep` block so it can reach the AntD overlay.
3) **Align menu content:**  
   - Set item layout: `display: flex; align-items: center; gap: 8-10px; padding: 8px 12px; line-height: 1.2;`  
   - Keep icons small and fixed: `width/height: 14px; flex-shrink: 0;`  
   - Consider reducing trigger icon size (e.g., three-dot icon to 16px) for better balance.

## Common pitfalls
- Forgetting `overlay-class-name` means the overlay won’t pick up the rounded styles.
- Scoped styles don’t affect the overlay; use global CSS or `:deep`.
- Some AntD defaults reintroduce square corners; the `!important` on `border-radius` prevents regressions.

Follow these steps to ensure dropdowns match the rounded, elevated style across panels.
