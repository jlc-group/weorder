---
description: Layout and sizing standards for React dashboards
---

# Layout & Sizing Standards

## Pre-Development Checklist

Before starting any React/Vite project, **always check and fix `index.css`**:

```css
/* REMOVE Vite defaults that cause centering issues */
/* BAD: display: flex; place-items: center; */

/* CORRECT: Simple reset */
body { margin: 0; padding: 0; }
#root { width: 100%; }
```

## Bootstrap Grid Rules

### Stat Cards (4 columns)
```tsx
// Use col-3 for always 4 columns
<div className="col-3">...</div>

// Or with responsive fallback
<div className="col-6 col-lg-3">...</div>
```

### Sidebar + Main Content
```css
.sidebar { width: 240px; position: fixed; }
.main-content { margin-left: 240px; }
```

### Quick Actions vs Content Ratio
- Use `col-lg-4 : col-lg-8` for proper 1:2 ratio
- Add `text-nowrap` to buttons to prevent text wrapping

## Verification Steps

// turbo-all
1. Resize browser to 1920x1080 and verify full-width layout
2. Check for empty space on right side
3. Verify all text fits without wrapping
4. Compare with original design screenshot

## Common Mistakes to Avoid

1. **Vite default CSS** - Always check `index.css` for `place-items: center`
2. **Wrong breakpoints** - Use `col-lg-*` not `col-xl-*` for desktop
3. **Missing text-nowrap** - Add to buttons and labels in narrow containers
4. **Container constraints** - Don't use Bootstrap `container` class, use fluid layouts
