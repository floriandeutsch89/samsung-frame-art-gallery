# Collections UX Redesign - Design Document

## Overview

Redesign the Collections feature from a basic dropdown-based interface to a premium, curated experience with a desktop sidebar, mobile bottom sheet, and polished visual identity.

## Problems Addressed

1. **Empty state is bland** - No visual interest or guidance
2. **Header is cluttered** - Actions compete for attention, unclear hierarchy
3. **No visual differentiation** - Collections looks identical to Local/Met tabs
4. **Collection picker is basic** - No context, plain list
5. **Footer is cramped** - Destructive/constructive actions too close together

---

## Design Specifications

### 1. Desktop Layout - Collections Sidebar

**Structure:**
- Left sidebar (200px fixed width) containing collection cards
- Main content area showing selected collection's images
- Sidebar scrolls independently

**Sidebar elements:**
- "+ New" button at top (prominent, gold accent)
- Collection cards showing: name, item count, thumbnail preview
- Selected card: highlighted with gold left border

**Main area header:**
- Collection name (large)
- Item count + created date (muted)
- Edit/delete icons (appear on hover, subtle)

```
┌───────────────┬─────────────────────────────────────────────────┐
│  COLLECTIONS  │  Impressionist Favorites                        │
│  ───────────  │  12 items · Created Dec 1              [✏️][🗑️] │
│  [+ New]      │  ─────────────────────────────────────────────  │
│               │                                                  │
│ ┌───────────┐ │  (image grid)                                   │
│ │ ★ Impres- │ │                                                  │
│ │   sionist │ │                                                  │
│ │   12 items│ │                                                  │
│ └───────────┘ │                                                  │
│ ┌───────────┐ │                                                  │
│ │ Nature    │ │                                                  │
│ └───────────┘ │                                                  │
└───────────────┴─────────────────────────────────────────────────┘
```

### 2. Redesigned Action Bar (Desktop)

**Layout:**
- Left: Selection preview (thumbnails + count)
- Top-right: "Remove from Collection" (isolated, muted style)
- Middle-right: Crop/Matte settings
- Bottom-right: Upload buttons (primary actions)

```
┌─────────────────────────────────────────────────────────────────┐
│  ┌──────────────────────────────┐       [Remove from Collection]│
│  │ 3 images selected            │                               │
│  │ [thumb] [thumb] [thumb]      │    Crop [5]%  Matte [10]%     │
│  └──────────────────────────────┘           [Preview]           │
│                                                                  │
│                          [ Upload to TV ]  [ Upload & Display ] │
└─────────────────────────────────────────────────────────────────┘
```

### 3. Mobile Layout - Bottom Sheet

**Collapsed state:**
- Collection selector bar showing current collection name
- Tap or swipe up to expand

**Expanded state:**
- Drag handle at top
- "Your Collections" header
- Collection rows (tap to select, closes sheet)
- "+ Create New Collection" at bottom
- Long-press for edit/delete context menu

**Mobile footer (simplified):**
```
┌─────────────────────────────────┐
│ 2 selected  [⚙️]  [Upload & Display] │
└─────────────────────────────────┘
```
- Gear icon opens crop/matte settings in mini bottom sheet

### 4. Empty States

**No collections yet:**
- Simple line illustration: image → collection → TV flow
- Heading: "Curate your favorite artwork"
- Subtext: "Collect images from Local or Met Museum, then upload them to your TV in one go."
- CTA: "+ Create First Collection"

**Empty collection:**
- Empty folder illustration
- Heading: "This collection is empty"
- Subtext: "Go to Local or Met Museum tab and click '+ Collection' to add artwork here."
- CTA: "Go to Local Images"

### 5. Collection Picker Modal

**Redesigned structure:**
1. Header: "Add to Collection"
2. Preview: Thumbnails of images being added (max 5, then "+X more")
3. Create input: Prominent at top
4. Section label: "YOUR COLLECTIONS"
5. Collection rows: Thumbnail preview + name + item count

**Success state:**
- Checkmark animation
- "Added to collection" + collection name
- Buttons: "View Collection" / "Done"

### 6. Visual Identity

**Accent color:** Warm gold/amber (#D4A574)
- Selected collection border
- "+ New" button
- Collection icons
- Empty state illustration accent

**Styling:**
```css
.collection-card {
  background: #1e1e32;
  border-radius: 8px;
  border-left: 3px solid transparent;
}

.collection-card.selected {
  border-left-color: #D4A574;
  background: #262640;
}
```

**Typography:**
- Collection name: 16px, medium, white
- Item count: 13px, regular, #888
- Section headers: 11px, uppercase, letter-spaced, #666

**Micro-interactions:**
- Adding to collection: Brief scale pulse
- Removing images: Fade out with slide
- Switching collections: Crossfade between grids
- Hover on card: Subtle lift (translateY -2px)

---

## Implementation Scope

### New Components
- `CollectionsSidebar.vue` - Desktop sidebar
- `CollectionCard.vue` - Individual collection card
- `CollectionBottomSheet.vue` - Mobile collection selector
- `SelectionPreview.vue` - Thumbnail strip for action bar

### Modified Components
- `CollectionsPanel.vue` - Major restructure for sidebar layout
- `CollectionPicker.vue` - Add previews, improve styling
- `ActionBar.vue` - Support expanded mode with selection preview

### CSS/Styling
- New gold accent color variables
- Collection-specific component styles
- Animation keyframes for micro-interactions
- Mobile-specific bottom sheet styles

---

## Breakpoints

- **Desktop:** > 768px - Sidebar layout
- **Mobile:** <= 768px - Bottom sheet layout
