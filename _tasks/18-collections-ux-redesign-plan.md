# Collections UX Redesign - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform the Collections tab from a basic dropdown interface into a premium, curated experience with desktop sidebar, mobile bottom sheet, and polished visual identity.

**Architecture:** Desktop uses a fixed-width sidebar (200px) with collection cards on the left and content area on the right. Mobile uses a bottom sheet pattern for collection selection. Both share the same underlying state management and API calls. New components are created for reusable pieces (CollectionCard, CollectionsSidebar, SelectionPreview).

**Tech Stack:** Vue 3.4 Composition API, CSS custom properties for theming, CSS transitions for micro-interactions

---

## Task 1: Add Gold Accent CSS Variables

**Files:**
- Create: `src/frontend/src/assets/collections.css`
- Modify: `src/frontend/src/main.js`

**Step 1: Create the CSS variables file**

Create `src/frontend/src/assets/collections.css`:

```css
:root {
  /* Collections gold accent */
  --collection-accent: #D4A574;
  --collection-accent-hover: #E5B685;
  --collection-accent-muted: rgba(212, 165, 116, 0.3);

  /* Collection card backgrounds */
  --collection-card-bg: #1e1e32;
  --collection-card-bg-selected: #262640;
  --collection-card-bg-hover: #232338;

  /* Typography */
  --collection-text-primary: #ffffff;
  --collection-text-secondary: #888888;
  --collection-text-muted: #666666;
}
```

**Step 2: Import CSS in main.js**

In `src/frontend/src/main.js`, add import after existing imports:

```javascript
import './assets/collections.css'
```

**Step 3: Verify**

Run: `cd src/frontend && npm run dev`
Expected: Dev server starts without errors. Variables available in browser dev tools under `:root`.

**Step 4: Commit**

```bash
git add src/frontend/src/assets/collections.css src/frontend/src/main.js
git commit -m "feat(collections): add gold accent CSS variables"
```

---

## Task 2: Create CollectionCard Component

**Files:**
- Create: `src/frontend/src/components/CollectionCard.vue`

**Step 1: Create the CollectionCard component**

Create `src/frontend/src/components/CollectionCard.vue`:

```vue
<template>
  <button
    class="collection-card"
    :class="{ selected }"
    @click="$emit('select')"
  >
    <div class="card-thumbnail">
      <img
        v-if="collection.preview_thumbnail"
        :src="collection.preview_thumbnail"
        alt=""
        loading="lazy"
      />
      <div v-else class="placeholder-icon">📁</div>
    </div>
    <div class="card-info">
      <span class="card-name">{{ collection.name }}</span>
      <span class="card-count">{{ collection.item_count }} {{ collection.item_count === 1 ? 'item' : 'items' }}</span>
    </div>
  </button>
</template>

<script setup>
defineProps({
  collection: {
    type: Object,
    required: true
  },
  selected: {
    type: Boolean,
    default: false
  }
})

defineEmits(['select'])
</script>

<style scoped>
.collection-card {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  width: 100%;
  padding: 0.75rem;
  background: var(--collection-card-bg);
  border: none;
  border-radius: 8px;
  border-left: 3px solid transparent;
  cursor: pointer;
  text-align: left;
  color: var(--collection-text-primary);
  transition: all 0.2s ease;
}

.collection-card:hover {
  background: var(--collection-card-bg-hover);
  transform: translateY(-2px);
}

.collection-card.selected {
  border-left-color: var(--collection-accent);
  background: var(--collection-card-bg-selected);
}

.card-thumbnail {
  width: 40px;
  height: 40px;
  border-radius: 4px;
  overflow: hidden;
  background: #2a2a4e;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.card-thumbnail img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.placeholder-icon {
  font-size: 1.25rem;
  opacity: 0.5;
}

.card-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
  flex: 1;
}

.card-name {
  font-size: 0.9rem;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.card-count {
  font-size: 0.75rem;
  color: var(--collection-text-secondary);
}
</style>
```

**Step 2: Verify component renders**

Temporarily import in CollectionsPanel.vue and render one card to verify styling.

Run: `cd src/frontend && npm run dev`
Expected: Card renders with correct styling, hover effect works, selected state shows gold border.

**Step 3: Commit**

```bash
git add src/frontend/src/components/CollectionCard.vue
git commit -m "feat(collections): add CollectionCard component with gold accent"
```

---

## Task 3: Create CollectionsSidebar Component

**Files:**
- Create: `src/frontend/src/components/CollectionsSidebar.vue`

**Step 1: Create the sidebar component**

Create `src/frontend/src/components/CollectionsSidebar.vue`:

```vue
<template>
  <aside class="collections-sidebar">
    <div class="sidebar-header">
      <span class="sidebar-title">COLLECTIONS</span>
    </div>

    <button class="new-collection-btn" @click="$emit('create')">
      + New
    </button>

    <div class="collections-list">
      <CollectionCard
        v-for="collection in collections"
        :key="collection.id"
        :collection="collection"
        :selected="selectedId === collection.id"
        @select="$emit('select', collection.id)"
      />
    </div>
  </aside>
</template>

<script setup>
import CollectionCard from './CollectionCard.vue'

defineProps({
  collections: {
    type: Array,
    default: () => []
  },
  selectedId: {
    type: [String, Number],
    default: null
  }
})

defineEmits(['select', 'create'])
</script>

<style scoped>
.collections-sidebar {
  width: 200px;
  min-width: 200px;
  display: flex;
  flex-direction: column;
  background: #12121f;
  border-right: 1px solid #2a2a4e;
  overflow: hidden;
}

.sidebar-header {
  padding: 1rem;
  border-bottom: 1px solid #2a2a4e;
}

.sidebar-title {
  font-size: 0.7rem;
  font-weight: 600;
  letter-spacing: 0.1em;
  color: var(--collection-text-muted);
  text-transform: uppercase;
}

.new-collection-btn {
  margin: 0.75rem;
  padding: 0.6rem 1rem;
  background: var(--collection-accent);
  color: #1a1a2e;
  border: none;
  border-radius: 6px;
  font-weight: 600;
  font-size: 0.9rem;
  cursor: pointer;
  transition: background 0.2s;
}

.new-collection-btn:hover {
  background: var(--collection-accent-hover);
}

.collections-list {
  flex: 1;
  overflow-y: auto;
  padding: 0.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
</style>
```

**Step 2: Verify**

Run: `cd src/frontend && npm run dev`
Expected: Sidebar component ready for integration.

**Step 3: Commit**

```bash
git add src/frontend/src/components/CollectionsSidebar.vue
git commit -m "feat(collections): add CollectionsSidebar with new button and card list"
```

---

## Task 4: Create SelectionPreview Component

**Files:**
- Create: `src/frontend/src/components/SelectionPreview.vue`

**Step 1: Create the selection preview component**

Create `src/frontend/src/components/SelectionPreview.vue`:

```vue
<template>
  <div class="selection-preview" v-if="images.length > 0">
    <div class="preview-header">
      {{ images.length }} {{ images.length === 1 ? 'image' : 'images' }} selected
    </div>
    <div class="preview-thumbnails">
      <div
        v-for="(img, index) in displayImages"
        :key="img._id || index"
        class="preview-thumb"
      >
        <img :src="img.thumbnail" alt="" loading="lazy" />
      </div>
      <div v-if="overflowCount > 0" class="overflow-indicator">
        +{{ overflowCount }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const MAX_DISPLAY = 5

const props = defineProps({
  images: {
    type: Array,
    default: () => []
  }
})

const displayImages = computed(() => props.images.slice(0, MAX_DISPLAY))
const overflowCount = computed(() => Math.max(0, props.images.length - MAX_DISPLAY))
</script>

<style scoped>
.selection-preview {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0.75rem;
  background: #1e1e32;
  border-radius: 8px;
  min-width: 200px;
}

.preview-header {
  font-size: 0.85rem;
  color: var(--collection-text-primary);
  font-weight: 500;
}

.preview-thumbnails {
  display: flex;
  gap: 0.25rem;
  align-items: center;
}

.preview-thumb {
  width: 36px;
  height: 36px;
  border-radius: 4px;
  overflow: hidden;
  background: #2a2a4e;
}

.preview-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.overflow-indicator {
  width: 36px;
  height: 36px;
  border-radius: 4px;
  background: #3a3a5e;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  color: var(--collection-text-secondary);
}
</style>
```

**Step 2: Verify**

Run: `cd src/frontend && npm run dev`
Expected: Component ready for integration.

**Step 3: Commit**

```bash
git add src/frontend/src/components/SelectionPreview.vue
git commit -m "feat(collections): add SelectionPreview component for action bar"
```

---

## Task 5: Create Empty State Components

**Files:**
- Create: `src/frontend/src/components/EmptyCollections.vue`
- Create: `src/frontend/src/components/EmptyCollection.vue`

**Step 1: Create no-collections empty state**

Create `src/frontend/src/components/EmptyCollections.vue`:

```vue
<template>
  <div class="empty-collections">
    <div class="empty-illustration">
      <span class="icon">🖼️</span>
      <span class="arrow">→</span>
      <span class="icon">📁</span>
      <span class="arrow">→</span>
      <span class="icon">📺</span>
    </div>
    <h2>Curate your favorite artwork</h2>
    <p>Collect images from Local or Met Museum, then upload them to your TV in one go.</p>
    <button class="cta-btn" @click="$emit('create')">
      + Create First Collection
    </button>
  </div>
</template>

<script setup>
defineEmits(['create'])
</script>

<style scoped>
.empty-collections {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem 2rem;
  text-align: center;
  flex: 1;
}

.empty-illustration {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 2rem;
  font-size: 2rem;
}

.arrow {
  color: var(--collection-accent);
  font-size: 1.5rem;
}

h2 {
  margin: 0 0 0.5rem 0;
  font-size: 1.5rem;
  color: var(--collection-text-primary);
}

p {
  margin: 0 0 1.5rem 0;
  color: var(--collection-text-secondary);
  max-width: 300px;
  line-height: 1.5;
}

.cta-btn {
  padding: 0.75rem 1.5rem;
  background: var(--collection-accent);
  color: #1a1a2e;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  font-size: 1rem;
  cursor: pointer;
  transition: background 0.2s;
}

.cta-btn:hover {
  background: var(--collection-accent-hover);
}
</style>
```

**Step 2: Create empty-collection state**

Create `src/frontend/src/components/EmptyCollection.vue`:

```vue
<template>
  <div class="empty-collection">
    <div class="empty-illustration">
      <span class="folder-icon">📂</span>
    </div>
    <h2>This collection is empty</h2>
    <p>Go to Local or Met Museum tab and click '+ Collection' to add artwork here.</p>
    <button class="cta-btn" @click="$emit('go-to-local')">
      Go to Local Images
    </button>
  </div>
</template>

<script setup>
defineEmits(['go-to-local'])
</script>

<style scoped>
.empty-collection {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem 2rem;
  text-align: center;
  flex: 1;
}

.empty-illustration {
  margin-bottom: 1.5rem;
}

.folder-icon {
  font-size: 4rem;
  opacity: 0.5;
}

h2 {
  margin: 0 0 0.5rem 0;
  font-size: 1.25rem;
  color: var(--collection-text-primary);
}

p {
  margin: 0 0 1.5rem 0;
  color: var(--collection-text-secondary);
  max-width: 280px;
  line-height: 1.5;
}

.cta-btn {
  padding: 0.6rem 1.25rem;
  background: #3a3a5e;
  color: white;
  border: none;
  border-radius: 6px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
}

.cta-btn:hover {
  background: #4a4a6e;
}
</style>
```

**Step 3: Verify**

Run: `cd src/frontend && npm run dev`
Expected: Both components render correctly.

**Step 4: Commit**

```bash
git add src/frontend/src/components/EmptyCollections.vue src/frontend/src/components/EmptyCollection.vue
git commit -m "feat(collections): add empty state components with visual illustrations"
```

---

## Task 6: Restructure CollectionsPanel for Desktop Sidebar Layout

**Files:**
- Modify: `src/frontend/src/views/CollectionsPanel.vue`

**Step 1: Update template for sidebar layout**

Replace the entire `<template>` section in `src/frontend/src/views/CollectionsPanel.vue`:

```vue
<template>
  <div class="collections-panel" :class="{ 'has-sidebar': !isMobile }">
    <!-- Desktop: Sidebar Layout -->
    <template v-if="!isMobile">
      <CollectionsSidebar
        :collections="collections"
        :selected-id="selectedCollectionId"
        @select="selectCollection"
        @create="showNewModal = true"
      />

      <div class="main-content">
        <!-- No collections state -->
        <EmptyCollections
          v-if="collections.length === 0"
          @create="showNewModal = true"
        />

        <!-- Collection selected -->
        <template v-else-if="selectedCollection">
          <div class="content-header">
            <div class="header-info">
              <h2>{{ selectedCollection.name }}</h2>
              <span class="header-meta">
                {{ selectedCollection.item_count }} {{ selectedCollection.item_count === 1 ? 'item' : 'items' }}
                <span v-if="selectedCollection.created_at"> · Created {{ formatDate(selectedCollection.created_at) }}</span>
              </span>
            </div>
            <div class="header-actions">
              <button class="icon-btn" @click="showRenameModal = true" title="Rename">
                ✏️
              </button>
              <button class="icon-btn danger" @click="confirmDelete" title="Delete">
                🗑️
              </button>
            </div>
          </div>

          <div v-if="unavailableCount > 0" class="unavailable-notice">
            {{ unavailableCount }} image(s) unavailable
          </div>

          <!-- Empty collection -->
          <EmptyCollection
            v-if="items.length === 0 && !loading"
            @go-to-local="goToLocal"
          />

          <!-- Image grid -->
          <ImageGrid
            v-else
            :images="items"
            :selected-ids="selectedIds"
            :loading="loading"
            :is-local="false"
            @toggle="toggleSelection"
            @select-all="selectAll"
            @preview="(img) => $emit('preview', img, img.type === 'local')"
          />

          <!-- Action Bar -->
          <ActionBar v-if="items.length > 0" class="collections-action-bar">
            <template #left>
              <SelectionPreview :images="selectedImages" />
            </template>
            <template #default>
              <div class="action-bar-right">
                <button
                  class="remove-btn"
                  :disabled="selectedIds.size === 0"
                  @click="removeSelected"
                >
                  Remove from Collection
                </button>
                <div class="action-bar-controls">
                  <CropSettings
                    :has-selection="selectedIds.size > 0"
                    :allow-reframe="false"
                    @change="setSettings"
                  />
                  <div class="upload-buttons">
                    <button
                      class="secondary"
                      :disabled="selectedIds.size === 0 || uploading"
                      @click="upload(false)"
                    >
                      Upload to TV
                    </button>
                    <button
                      class="primary"
                      :disabled="selectedIds.size === 0 || uploading"
                      @click="upload(true)"
                    >
                      Upload & Display
                    </button>
                  </div>
                </div>
              </div>
            </template>
          </ActionBar>
        </template>
      </div>
    </template>

    <!-- Mobile: Original dropdown layout (to be replaced in Task 8) -->
    <template v-else>
      <div class="panel-header">
        <div class="collection-select">
          <select v-model="selectedCollectionId" @change="loadCollectionItems">
            <option :value="null" disabled>Select a collection...</option>
            <option
              v-for="c in collections"
              :key="c.id"
              :value="c.id"
            >
              {{ c.name }} ({{ c.item_count }})
            </option>
          </select>
          <button class="new-btn" @click="showNewModal = true" title="New collection">+</button>
        </div>

        <div v-if="selectedCollection" class="collection-actions">
          <button class="icon-btn" @click="showRenameModal = true" title="Rename">
            <span>Rename</span>
          </button>
          <button class="icon-btn danger" @click="confirmDelete" title="Delete">
            <span>Delete</span>
          </button>
        </div>
      </div>

      <div v-if="!selectedCollectionId" class="empty-state">
        <p>Select a collection to view its contents</p>
        <button @click="showNewModal = true">Create New Collection</button>
      </div>

      <template v-else>
        <div v-if="unavailableCount > 0" class="unavailable-notice">
          {{ unavailableCount }} image(s) unavailable
        </div>

        <ImageGrid
          :images="items"
          :selected-ids="selectedIds"
          :loading="loading"
          :is-local="false"
          @toggle="toggleSelection"
          @select-all="selectAll"
          @preview="(img) => $emit('preview', img, img.type === 'local')"
        />

        <ActionBar>
          <template #left>
            <CropSettings
              :has-selection="selectedIds.size > 0"
              :allow-reframe="false"
              @change="setSettings"
            />
          </template>
          <button
            class="secondary danger"
            :disabled="selectedIds.size === 0"
            @click="removeSelected"
          >
            Remove ({{ selectedIds.size }})
          </button>
          <button
            class="secondary"
            :disabled="selectedIds.size === 0 || uploading"
            @click="upload(false)"
          >
            Upload ({{ selectedIds.size }})
          </button>
          <button
            class="primary"
            :disabled="selectedIds.size === 0 || uploading"
            @click="upload(true)"
          >
            Upload & Display
          </button>
        </ActionBar>
      </template>
    </template>

    <!-- New Collection Modal -->
    <div v-if="showNewModal" class="modal-overlay" @click.self="showNewModal = false">
      <div class="modal">
        <h3>New Collection</h3>
        <input
          v-model="newCollectionName"
          type="text"
          placeholder="Collection name"
          @keyup.enter="createCollection"
        />
        <div class="modal-actions">
          <button class="secondary" @click="showNewModal = false">Cancel</button>
          <button class="primary" :disabled="!newCollectionName.trim()" @click="createCollection">Create</button>
        </div>
      </div>
    </div>

    <!-- Rename Modal -->
    <div v-if="showRenameModal" class="modal-overlay" @click.self="showRenameModal = false">
      <div class="modal">
        <h3>Rename Collection</h3>
        <input
          v-model="renameValue"
          type="text"
          placeholder="New name"
          @keyup.enter="renameCollection"
        />
        <div class="modal-actions">
          <button class="secondary" @click="showRenameModal = false">Cancel</button>
          <button class="primary" :disabled="!renameValue.trim()" @click="renameCollection">Rename</button>
        </div>
      </div>
    </div>
  </div>
</template>
```

**Step 2: Update script section**

Replace the `<script setup>` section:

```vue
<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import ImageGrid from '../components/ImageGrid.vue'
import ActionBar from '../components/ActionBar.vue'
import CropSettings from '../components/CropSettings.vue'
import CollectionsSidebar from '../components/CollectionsSidebar.vue'
import SelectionPreview from '../components/SelectionPreview.vue'
import EmptyCollections from '../components/EmptyCollections.vue'
import EmptyCollection from '../components/EmptyCollection.vue'

const emit = defineEmits(['uploaded', 'preview', 'switch-tab'])

// Responsive
const isMobile = ref(window.innerWidth <= 768)
const checkMobile = () => {
  isMobile.value = window.innerWidth <= 768
}

onMounted(() => {
  window.addEventListener('resize', checkMobile)
})

onUnmounted(() => {
  window.removeEventListener('resize', checkMobile)
})

const collections = ref([])
const selectedCollectionId = ref(null)
const selectedCollection = computed(() =>
  collections.value.find(c => c.id === selectedCollectionId.value)
)

const items = ref([])
const selectedIds = ref(new Set())
const loading = ref(false)
const uploading = ref(false)
const unavailableCount = ref(0)

const cropPercent = ref(0)
const mattePercent = ref(10)

const showNewModal = ref(false)
const newCollectionName = ref('')
const showRenameModal = ref(false)
const renameValue = ref('')

// Computed for selection preview
const selectedImages = computed(() =>
  items.value.filter(i => selectedIds.value.has(i._id))
)

// Format date helper
const formatDate = (dateStr) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

// Navigate to local tab
const goToLocal = () => {
  // Update URL and trigger parent to switch tabs
  const params = new URLSearchParams(window.location.search)
  params.set('tab', 'local')
  window.history.replaceState({}, '', `${window.location.pathname}?${params.toString()}`)
  window.location.reload()
}

const selectCollection = (id) => {
  selectedCollectionId.value = id
  loadCollectionItems()
}

const loadCollections = async () => {
  try {
    const res = await fetch('/api/collections')
    const data = await res.json()
    collections.value = data.collections || []

    // Auto-select first collection if none selected and collections exist
    if (!selectedCollectionId.value && collections.value.length > 0) {
      selectedCollectionId.value = collections.value[0].id
      await loadCollectionItems()
    }
  } catch (e) {
    console.error('Failed to load collections:', e)
  }
}

const loadCollectionItems = async () => {
  if (!selectedCollectionId.value) {
    items.value = []
    return
  }

  loading.value = true
  selectedIds.value = new Set()

  try {
    const res = await fetch(`/api/collections/${selectedCollectionId.value}/items`)
    const data = await res.json()

    // Transform items for ImageGrid compatibility
    items.value = (data.items || []).map(item => {
      if (item.type === 'local') {
        return {
          ...item,
          _id: `local:${item.path}`,
          thumbnail: `/api/images/${encodeURIComponent(item.path)}/thumbnail`
        }
      } else {
        return {
          ...item,
          _id: `met:${item.object_id}`,
          content_id: `met_${item.object_id}`,
          thumbnail: item.image_url_small || item.image_url
        }
      }
    })

    unavailableCount.value = data.unavailable_count || 0
  } catch (e) {
    console.error('Failed to load collection items:', e)
  } finally {
    loading.value = false
  }
}

const toggleSelection = (item) => {
  const id = item._id
  const newSet = new Set(selectedIds.value)
  if (newSet.has(id)) {
    newSet.delete(id)
  } else {
    newSet.add(id)
  }
  selectedIds.value = newSet
}

const selectAll = (checked) => {
  if (checked) {
    selectedIds.value = new Set(items.value.map(i => i._id))
  } else {
    selectedIds.value = new Set()
  }
}

const setSettings = (settings) => {
  cropPercent.value = settings.crop
  mattePercent.value = settings.matte
}

const createCollection = async () => {
  const name = newCollectionName.value.trim()
  if (!name) return

  try {
    const res = await fetch('/api/collections', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name })
    })
    const collection = await res.json()
    await loadCollections()
    selectedCollectionId.value = collection.id
    showNewModal.value = false
    newCollectionName.value = ''
  } catch (e) {
    console.error('Failed to create collection:', e)
  }
}

const renameCollection = async () => {
  const name = renameValue.value.trim()
  if (!name || !selectedCollectionId.value) return

  try {
    await fetch(`/api/collections/${selectedCollectionId.value}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name })
    })
    await loadCollections()
    showRenameModal.value = false
  } catch (e) {
    console.error('Failed to rename collection:', e)
  }
}

const confirmDelete = async () => {
  if (!selectedCollection.value) return
  if (!confirm(`Delete "${selectedCollection.value.name}"? This cannot be undone.`)) return

  try {
    await fetch(`/api/collections/${selectedCollectionId.value}`, {
      method: 'DELETE'
    })
    selectedCollectionId.value = null
    items.value = []
    await loadCollections()
  } catch (e) {
    console.error('Failed to delete collection:', e)
  }
}

const removeSelected = async () => {
  if (selectedIds.value.size === 0 || !selectedCollectionId.value) return

  const itemsToRemove = items.value
    .filter(i => selectedIds.value.has(i._id))
    .map(i => i.type === 'local'
      ? { type: 'local', path: i.path }
      : { type: 'met', object_id: i.object_id }
    )

  try {
    await fetch(`/api/collections/${selectedCollectionId.value}/items`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ items: itemsToRemove })
    })
    await loadCollectionItems()
    await loadCollections()
  } catch (e) {
    console.error('Failed to remove items:', e)
  }
}

const upload = async (display) => {
  if (selectedIds.value.size === 0) return

  uploading.value = true

  const selected = items.value.filter(i => selectedIds.value.has(i._id))
  const localPaths = selected.filter(i => i.type === 'local').map(i => i.path)
  const metIds = selected.filter(i => i.type === 'met').map(i => i.object_id)

  try {
    if (localPaths.length > 0) {
      await fetch('/api/tv/upload', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          paths: localPaths,
          crop_percent: cropPercent.value,
          matte_percent: mattePercent.value,
          display: display && metIds.length === 0
        })
      })
    }

    if (metIds.length > 0) {
      await fetch('/api/met/upload', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          object_ids: metIds,
          crop_percent: cropPercent.value,
          matte_percent: mattePercent.value,
          display
        })
      })
    }

    selectedIds.value = new Set()
    emit('uploaded')
  } catch (e) {
    console.error('Upload failed:', e)
  } finally {
    uploading.value = false
  }
}

watch(showRenameModal, (show) => {
  if (show && selectedCollection.value) {
    renameValue.value = selectedCollection.value.name
  }
})

onMounted(loadCollections)

defineExpose({ loadCollections })
</script>
```

**Step 3: Update styles section**

Replace the `<style scoped>` section:

```vue
<style scoped>
.collections-panel {
  display: contents;
}

.collections-panel.has-sidebar {
  display: flex;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.content-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 1rem 1.5rem;
  background: #12121f;
  border-bottom: 1px solid #2a2a4e;
}

.header-info h2 {
  margin: 0 0 0.25rem 0;
  font-size: 1.5rem;
  font-weight: 600;
}

.header-meta {
  font-size: 0.85rem;
  color: var(--collection-text-secondary);
}

.header-actions {
  display: flex;
  gap: 0.5rem;
  opacity: 0.6;
  transition: opacity 0.2s;
}

.content-header:hover .header-actions {
  opacity: 1;
}

.header-actions .icon-btn {
  padding: 0.4rem 0.6rem;
  background: transparent;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1rem;
  transition: background 0.2s;
}

.header-actions .icon-btn:hover {
  background: #2a2a4e;
}

.header-actions .icon-btn.danger:hover {
  background: #4a2a2e;
}

/* Action bar styling for collections */
.collections-action-bar {
  flex-wrap: nowrap;
  padding: 1rem 1.5rem;
}

.action-bar-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.75rem;
  flex: 1;
}

.remove-btn {
  padding: 0.4rem 0.75rem;
  background: transparent;
  border: 1px solid #4a3a3e;
  border-radius: 4px;
  color: #ff9999;
  cursor: pointer;
  font-size: 0.85rem;
  transition: all 0.2s;
}

.remove-btn:hover:not(:disabled) {
  background: #4a2a2e;
  border-color: #6a4a4e;
}

.remove-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.action-bar-controls {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.upload-buttons {
  display: flex;
  gap: 0.5rem;
}

/* Mobile/Original styles */
.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  border-bottom: 1px solid #2a2a4e;
  background: #12121f;
  gap: 1rem;
  flex-wrap: wrap;
}

.collection-select {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.collection-select select {
  padding: 0.4rem;
  border-radius: 4px;
  border: 1px solid #3a3a5e;
  background: #2a2a4e;
  color: white;
  min-width: 200px;
}

.new-btn {
  padding: 0.4rem 0.8rem;
  border-radius: 4px;
  border: 1px solid #3a3a5e;
  background: #4a90d9;
  color: white;
  cursor: pointer;
  font-size: 1rem;
  font-weight: bold;
}

.collection-actions {
  display: flex;
  gap: 0.5rem;
}

.icon-btn {
  padding: 0.4rem 0.8rem;
  border-radius: 4px;
  border: 1px solid #3a3a5e;
  background: #2a2a4e;
  color: #ccc;
  cursor: pointer;
  font-size: 0.85rem;
}

.icon-btn:hover {
  background: #3a3a5e;
}

.icon-btn.danger {
  color: #ff6b6b;
}

.icon-btn.danger:hover {
  background: #4a2a2e;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem 2rem;
  color: #888;
  gap: 1rem;
}

.empty-state button {
  padding: 0.75rem 1.5rem;
  border-radius: 4px;
  border: none;
  background: #4a90d9;
  color: white;
  cursor: pointer;
}

.unavailable-notice {
  padding: 0.5rem 1rem;
  background: #3a2a2e;
  color: #ff9999;
  font-size: 0.85rem;
  text-align: center;
}

/* Modal styles */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: #1a1a2e;
  border-radius: 8px;
  padding: 1.5rem;
  width: 90%;
  max-width: 400px;
}

.modal h3 {
  margin: 0 0 1rem 0;
}

.modal input {
  width: 100%;
  padding: 0.75rem;
  border-radius: 4px;
  border: 1px solid #3a3a5e;
  background: #2a2a4e;
  color: white;
  margin-bottom: 1rem;
  box-sizing: border-box;
}

.modal input:focus {
  outline: none;
  border-color: #4a90d9;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
}

.modal-actions button {
  padding: 0.5rem 1rem;
  border-radius: 4px;
  border: none;
  cursor: pointer;
}

.modal-actions button.primary {
  background: #4a90d9;
  color: white;
}

.modal-actions button.secondary {
  background: #3a3a5e;
  color: white;
}

.modal-actions button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
```

**Step 4: Verify desktop sidebar layout**

Run: `cd src/frontend && npm run dev`
Expected: On desktop (>768px), sidebar appears on left with collection cards. Selecting a collection shows content on right with header info and edit/delete icons.

**Step 5: Commit**

```bash
git add src/frontend/src/views/CollectionsPanel.vue
git commit -m "feat(collections): restructure panel with desktop sidebar layout"
```

---

## Task 7: Update main.js to Import CSS

**Files:**
- Modify: `src/frontend/src/main.js`

**Step 1: Read current main.js**

First read `src/frontend/src/main.js` to understand current structure.

**Step 2: Add CSS import if not already present**

Ensure this import exists after creating the app but before mounting:

```javascript
import './assets/collections.css'
```

**Step 3: Verify**

Run: `cd src/frontend && npm run dev`
Expected: No console errors, CSS variables work throughout app.

**Step 4: Commit (if changes were needed)**

```bash
git add src/frontend/src/main.js
git commit -m "feat(collections): ensure CSS variables are imported"
```

---

## Task 8: Create Mobile Bottom Sheet Component

**Files:**
- Create: `src/frontend/src/components/CollectionBottomSheet.vue`

**Step 1: Create the bottom sheet component**

Create `src/frontend/src/components/CollectionBottomSheet.vue`:

```vue
<template>
  <div class="bottom-sheet-container">
    <!-- Collapsed bar -->
    <button class="collection-bar" @click="isExpanded = true">
      <span class="bar-label">
        {{ selectedCollection ? selectedCollection.name : 'Select Collection' }}
      </span>
      <span class="bar-icon">▲</span>
    </button>

    <!-- Expanded sheet -->
    <Teleport to="body">
      <Transition name="sheet">
        <div v-if="isExpanded" class="sheet-overlay" @click.self="isExpanded = false">
          <div class="sheet-content">
            <div class="sheet-handle" @click="isExpanded = false">
              <div class="handle-bar"></div>
            </div>

            <h3 class="sheet-title">Your Collections</h3>

            <div class="sheet-list">
              <button
                v-for="collection in collections"
                :key="collection.id"
                class="sheet-item"
                :class="{ selected: selectedId === collection.id }"
                @click="selectAndClose(collection.id)"
                @contextmenu.prevent="showContextMenu($event, collection)"
              >
                <div class="item-thumbnail">
                  <img
                    v-if="collection.preview_thumbnail"
                    :src="collection.preview_thumbnail"
                    alt=""
                  />
                  <span v-else>📁</span>
                </div>
                <div class="item-info">
                  <span class="item-name">{{ collection.name }}</span>
                  <span class="item-count">{{ collection.item_count }} items</span>
                </div>
                <span v-if="selectedId === collection.id" class="item-check">✓</span>
              </button>
            </div>

            <button class="create-btn" @click="$emit('create'); isExpanded = false">
              + Create New Collection
            </button>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- Context menu -->
    <Teleport to="body">
      <div
        v-if="contextMenu.show"
        class="context-menu"
        :style="{ top: contextMenu.y + 'px', left: contextMenu.x + 'px' }"
      >
        <button @click="handleRename">Rename</button>
        <button class="danger" @click="handleDelete">Delete</button>
      </div>
      <div v-if="contextMenu.show" class="context-backdrop" @click="contextMenu.show = false"></div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'

const props = defineProps({
  collections: {
    type: Array,
    default: () => []
  },
  selectedId: {
    type: [String, Number],
    default: null
  },
  selectedCollection: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['select', 'create', 'rename', 'delete'])

const isExpanded = ref(false)
const contextMenu = reactive({
  show: false,
  x: 0,
  y: 0,
  collection: null
})

const selectAndClose = (id) => {
  emit('select', id)
  isExpanded.value = false
}

const showContextMenu = (event, collection) => {
  contextMenu.x = event.clientX
  contextMenu.y = event.clientY
  contextMenu.collection = collection
  contextMenu.show = true
}

const handleRename = () => {
  emit('rename', contextMenu.collection)
  contextMenu.show = false
}

const handleDelete = () => {
  emit('delete', contextMenu.collection)
  contextMenu.show = false
}
</script>

<style scoped>
.bottom-sheet-container {
  /* Container for collapsed bar */
}

.collection-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  padding: 0.75rem 1rem;
  background: #1a1a2e;
  border: none;
  border-bottom: 1px solid #2a2a4e;
  color: white;
  cursor: pointer;
}

.bar-label {
  font-weight: 500;
}

.bar-icon {
  font-size: 0.75rem;
  color: var(--collection-accent);
}

/* Sheet overlay and content */
.sheet-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 1000;
  display: flex;
  align-items: flex-end;
}

.sheet-content {
  width: 100%;
  max-height: 70vh;
  background: #1a1a2e;
  border-radius: 16px 16px 0 0;
  padding: 0 1rem 1rem;
  display: flex;
  flex-direction: column;
}

.sheet-handle {
  padding: 0.75rem 0;
  display: flex;
  justify-content: center;
  cursor: pointer;
}

.handle-bar {
  width: 40px;
  height: 4px;
  background: #3a3a5e;
  border-radius: 2px;
}

.sheet-title {
  margin: 0 0 1rem 0;
  font-size: 1.1rem;
  color: var(--collection-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: 600;
}

.sheet-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.sheet-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem;
  background: var(--collection-card-bg);
  border: none;
  border-radius: 8px;
  color: white;
  cursor: pointer;
  text-align: left;
}

.sheet-item.selected {
  background: var(--collection-card-bg-selected);
  border-left: 3px solid var(--collection-accent);
}

.item-thumbnail {
  width: 44px;
  height: 44px;
  border-radius: 6px;
  background: #2a2a4e;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.item-thumbnail img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.item-info {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.item-name {
  font-weight: 500;
}

.item-count {
  font-size: 0.85rem;
  color: var(--collection-text-secondary);
}

.item-check {
  color: var(--collection-accent);
  font-weight: bold;
}

.create-btn {
  width: 100%;
  padding: 0.75rem;
  background: var(--collection-accent);
  color: #1a1a2e;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
}

/* Context menu */
.context-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1001;
}

.context-menu {
  position: fixed;
  z-index: 1002;
  background: #2a2a4e;
  border-radius: 8px;
  padding: 0.5rem 0;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
}

.context-menu button {
  display: block;
  width: 100%;
  padding: 0.75rem 1.25rem;
  background: none;
  border: none;
  color: white;
  text-align: left;
  cursor: pointer;
}

.context-menu button:hover {
  background: #3a3a5e;
}

.context-menu button.danger {
  color: #ff6b6b;
}

/* Transitions */
.sheet-enter-active,
.sheet-leave-active {
  transition: opacity 0.3s ease;
}

.sheet-enter-active .sheet-content,
.sheet-leave-active .sheet-content {
  transition: transform 0.3s ease;
}

.sheet-enter-from,
.sheet-leave-to {
  opacity: 0;
}

.sheet-enter-from .sheet-content,
.sheet-leave-to .sheet-content {
  transform: translateY(100%);
}
</style>
```

**Step 2: Verify**

Run: `cd src/frontend && npm run dev`
Expected: Component ready for integration in mobile view.

**Step 3: Commit**

```bash
git add src/frontend/src/components/CollectionBottomSheet.vue
git commit -m "feat(collections): add mobile bottom sheet for collection selection"
```

---

## Task 9: Integrate Mobile Bottom Sheet into CollectionsPanel

**Files:**
- Modify: `src/frontend/src/views/CollectionsPanel.vue`

**Step 1: Add import for CollectionBottomSheet**

Add to imports at top of script section:

```javascript
import CollectionBottomSheet from '../components/CollectionBottomSheet.vue'
```

**Step 2: Replace mobile template section**

Replace the `<!-- Mobile: Original dropdown layout -->` section with:

```vue
    <!-- Mobile: Bottom Sheet Layout -->
    <template v-else>
      <CollectionBottomSheet
        :collections="collections"
        :selected-id="selectedCollectionId"
        :selected-collection="selectedCollection"
        @select="selectCollection"
        @create="showNewModal = true"
        @rename="(c) => { selectedCollectionId = c.id; showRenameModal = true }"
        @delete="(c) => { selectedCollectionId = c.id; confirmDelete() }"
      />

      <div v-if="!selectedCollectionId" class="empty-state">
        <EmptyCollections @create="showNewModal = true" />
      </div>

      <template v-else>
        <div v-if="unavailableCount > 0" class="unavailable-notice">
          {{ unavailableCount }} image(s) unavailable
        </div>

        <EmptyCollection
          v-if="items.length === 0 && !loading"
          @go-to-local="goToLocal"
        />

        <ImageGrid
          v-else
          :images="items"
          :selected-ids="selectedIds"
          :loading="loading"
          :is-local="false"
          @toggle="toggleSelection"
          @select-all="selectAll"
          @preview="(img) => $emit('preview', img, img.type === 'local')"
        />

        <!-- Mobile simplified footer -->
        <div v-if="items.length > 0" class="mobile-footer">
          <span class="selected-count">{{ selectedIds.size }} selected</span>
          <button class="settings-btn" @click="showMobileSettings = true">⚙️</button>
          <button
            class="primary"
            :disabled="selectedIds.size === 0 || uploading"
            @click="upload(true)"
          >
            Upload & Display
          </button>
        </div>
      </template>

      <!-- Mobile settings sheet -->
      <Teleport to="body">
        <div v-if="showMobileSettings" class="settings-overlay" @click.self="showMobileSettings = false">
          <div class="settings-sheet">
            <div class="settings-handle" @click="showMobileSettings = false">
              <div class="handle-bar"></div>
            </div>
            <CropSettings
              :has-selection="selectedIds.size > 0"
              :allow-reframe="false"
              @change="setSettings"
            />
            <div class="settings-actions">
              <button
                class="danger"
                :disabled="selectedIds.size === 0"
                @click="removeSelected(); showMobileSettings = false"
              >
                Remove from Collection
              </button>
              <button
                class="secondary"
                :disabled="selectedIds.size === 0 || uploading"
                @click="upload(false); showMobileSettings = false"
              >
                Upload to TV
              </button>
            </div>
          </div>
        </div>
      </Teleport>
    </template>
```

**Step 3: Add showMobileSettings ref**

Add to refs in script:

```javascript
const showMobileSettings = ref(false)
```

**Step 4: Add mobile footer styles**

Add to style section:

```css
/* Mobile footer */
.mobile-footer {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  background: #1a1a2e;
  border-top: 1px solid #2a2a4e;
}

.selected-count {
  flex: 1;
  font-size: 0.9rem;
  color: var(--collection-text-secondary);
}

.settings-btn {
  padding: 0.5rem;
  background: #2a2a4e;
  border: none;
  border-radius: 6px;
  font-size: 1.25rem;
  cursor: pointer;
}

.mobile-footer .primary {
  padding: 0.6rem 1rem;
  background: var(--collection-accent);
  color: #1a1a2e;
  border: none;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
}

.mobile-footer .primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Mobile settings sheet */
.settings-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 1000;
  display: flex;
  align-items: flex-end;
}

.settings-sheet {
  width: 100%;
  background: #1a1a2e;
  border-radius: 16px 16px 0 0;
  padding: 0 1rem 1.5rem;
}

.settings-handle {
  padding: 0.75rem 0;
  display: flex;
  justify-content: center;
  cursor: pointer;
}

.settings-handle .handle-bar {
  width: 40px;
  height: 4px;
  background: #3a3a5e;
  border-radius: 2px;
}

.settings-actions {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-top: 1rem;
}

.settings-actions button {
  width: 100%;
  padding: 0.75rem;
  border: none;
  border-radius: 6px;
  font-weight: 500;
  cursor: pointer;
}

.settings-actions .danger {
  background: #4a2a2e;
  color: #ff9999;
}

.settings-actions .secondary {
  background: #3a3a5e;
  color: white;
}
```

**Step 5: Verify mobile layout**

Run: `cd src/frontend && npm run dev`
Resize browser to <768px width.
Expected: Bottom sheet appears instead of dropdown. Tapping shows expanded list with context menu on long-press. Footer shows simplified controls.

**Step 6: Commit**

```bash
git add src/frontend/src/views/CollectionsPanel.vue
git commit -m "feat(collections): integrate mobile bottom sheet layout"
```

---

## Task 10: Enhance CollectionPicker with Preview Thumbnails

**Files:**
- Modify: `src/frontend/src/components/CollectionPicker.vue`

**Step 1: Add preview thumbnails to CollectionPicker**

Update the template to show image previews being added:

```vue
<template>
  <div class="collection-picker-overlay" @click.self="$emit('close')">
    <div class="collection-picker">
      <div class="picker-header">
        <h3>Add to Collection</h3>
        <button class="close-btn" @click="$emit('close')">&times;</button>
      </div>

      <!-- Preview of images being added -->
      <div class="items-preview" v-if="items.length > 0">
        <div class="preview-thumbnails">
          <div
            v-for="(item, index) in previewItems"
            :key="index"
            class="preview-thumb"
          >
            <img :src="getItemThumbnail(item)" alt="" loading="lazy" />
          </div>
          <div v-if="overflowCount > 0" class="overflow-badge">
            +{{ overflowCount }}
          </div>
        </div>
        <span class="preview-label">{{ items.length }} {{ items.length === 1 ? 'image' : 'images' }}</span>
      </div>

      <div class="picker-content">
        <div class="new-collection">
          <input
            v-model="newName"
            type="text"
            placeholder="Create new collection..."
            @keyup.enter="createAndAdd"
          />
          <button
            :disabled="!newName.trim() || creating"
            @click="createAndAdd"
          >
            Create
          </button>
        </div>

        <div v-if="loading" class="loading">Loading collections...</div>

        <template v-else-if="collections.length === 0">
          <div class="empty">
            No collections yet. Create one above.
          </div>
        </template>

        <template v-else>
          <div class="section-label">YOUR COLLECTIONS</div>
          <div class="collections-list">
            <button
              v-for="collection in collections"
              :key="collection.id"
              class="collection-item"
              :disabled="adding"
              @click="addToCollection(collection.id)"
            >
              <div class="item-thumb">
                <img
                  v-if="collection.preview_thumbnail"
                  :src="collection.preview_thumbnail"
                  alt=""
                />
                <span v-else>📁</span>
              </div>
              <div class="item-details">
                <span class="collection-name">{{ collection.name }}</span>
                <span class="collection-count">{{ collection.item_count }} items</span>
              </div>
            </button>
          </div>
        </template>
      </div>

      <!-- Success state -->
      <Transition name="fade">
        <div v-if="showSuccess" class="success-overlay">
          <div class="success-content">
            <div class="success-icon">✓</div>
            <h3>Added to collection</h3>
            <p>{{ successCollection?.name }}</p>
            <div class="success-actions">
              <button class="secondary" @click="$emit('close')">Done</button>
              <button class="primary" @click="viewCollection">View Collection</button>
            </div>
          </div>
        </div>
      </Transition>
    </div>
  </div>
</template>
```

**Step 2: Update script**

```vue
<script setup>
import { ref, computed, onMounted } from 'vue'

const MAX_PREVIEW = 5

const props = defineProps({
  items: {
    type: Array,
    required: true
  }
})

const emit = defineEmits(['close', 'added'])

const collections = ref([])
const loading = ref(true)
const newName = ref('')
const creating = ref(false)
const adding = ref(false)
const showSuccess = ref(false)
const successCollection = ref(null)

const previewItems = computed(() => props.items.slice(0, MAX_PREVIEW))
const overflowCount = computed(() => Math.max(0, props.items.length - MAX_PREVIEW))

const getItemThumbnail = (item) => {
  if (item.type === 'local') {
    return `/api/images/${encodeURIComponent(item.path)}/thumbnail`
  } else if (item.type === 'met') {
    return item.image_url_small || item.image_url || ''
  }
  return ''
}

const loadCollections = async () => {
  loading.value = true
  try {
    const res = await fetch('/api/collections')
    const data = await res.json()
    collections.value = data.collections || []
  } catch (e) {
    console.error('Failed to load collections:', e)
  } finally {
    loading.value = false
  }
}

const createAndAdd = async () => {
  const name = newName.value.trim()
  if (!name) return

  creating.value = true
  try {
    const createRes = await fetch('/api/collections', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name })
    })
    const collection = await createRes.json()

    await fetch(`/api/collections/${collection.id}/items`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ items: props.items })
    })

    successCollection.value = collection
    showSuccess.value = true
    emit('added', collection)
  } catch (e) {
    console.error('Failed to create collection:', e)
  } finally {
    creating.value = false
  }
}

const addToCollection = async (collectionId) => {
  adding.value = true
  try {
    await fetch(`/api/collections/${collectionId}/items`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ items: props.items })
    })

    const collection = collections.value.find(c => c.id === collectionId)
    successCollection.value = collection
    showSuccess.value = true
    emit('added', collection)
  } catch (e) {
    console.error('Failed to add to collection:', e)
  } finally {
    adding.value = false
  }
}

const viewCollection = () => {
  const params = new URLSearchParams(window.location.search)
  params.set('tab', 'collections')
  window.history.replaceState({}, '', `${window.location.pathname}?${params.toString()}`)
  window.location.reload()
}

onMounted(loadCollections)
</script>
```

**Step 3: Update styles**

```vue
<style scoped>
.collection-picker-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.collection-picker {
  background: #1a1a2e;
  border-radius: 12px;
  width: 90%;
  max-width: 420px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
}

.picker-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid #2a2a4e;
}

.picker-header h3 {
  margin: 0;
  font-size: 1.1rem;
}

.close-btn {
  background: transparent;
  border: none;
  color: #888;
  font-size: 1.5rem;
  cursor: pointer;
  padding: 0;
  line-height: 1;
}

.close-btn:hover {
  color: white;
}

/* Items preview */
.items-preview {
  padding: 1rem 1.25rem;
  background: #12121f;
  border-bottom: 1px solid #2a2a4e;
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.preview-thumbnails {
  display: flex;
  gap: 0.25rem;
}

.preview-thumb {
  width: 40px;
  height: 40px;
  border-radius: 4px;
  overflow: hidden;
  background: #2a2a4e;
}

.preview-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.overflow-badge {
  width: 40px;
  height: 40px;
  border-radius: 4px;
  background: #3a3a5e;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.8rem;
  color: var(--collection-text-secondary);
}

.preview-label {
  font-size: 0.9rem;
  color: var(--collection-text-secondary);
}

.picker-content {
  padding: 1rem 1.25rem;
  overflow-y: auto;
  flex: 1;
}

.new-collection {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.new-collection input {
  flex: 1;
  padding: 0.6rem 0.75rem;
  border-radius: 6px;
  border: 1px solid #3a3a5e;
  background: #2a2a4e;
  color: white;
}

.new-collection input:focus {
  outline: none;
  border-color: var(--collection-accent);
}

.new-collection button {
  padding: 0.6rem 1rem;
  border-radius: 6px;
  border: none;
  background: var(--collection-accent);
  color: #1a1a2e;
  font-weight: 600;
  cursor: pointer;
}

.new-collection button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.loading, .empty {
  text-align: center;
  color: #888;
  padding: 2rem;
}

.section-label {
  font-size: 0.7rem;
  font-weight: 600;
  letter-spacing: 0.1em;
  color: var(--collection-text-muted);
  text-transform: uppercase;
  margin-bottom: 0.75rem;
}

.collections-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.collection-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem;
  background: var(--collection-card-bg);
  border: 1px solid transparent;
  border-radius: 8px;
  cursor: pointer;
  color: white;
  text-align: left;
  transition: all 0.2s;
}

.collection-item:hover:not(:disabled) {
  background: var(--collection-card-bg-hover);
  border-color: var(--collection-accent-muted);
}

.collection-item:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.item-thumb {
  width: 44px;
  height: 44px;
  border-radius: 6px;
  background: #2a2a4e;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.item-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.item-details {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.collection-name {
  font-weight: 500;
}

.collection-count {
  color: var(--collection-text-secondary);
  font-size: 0.85rem;
}

/* Success overlay */
.success-overlay {
  position: absolute;
  inset: 0;
  background: #1a1a2e;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;
}

.success-content {
  text-align: center;
  padding: 2rem;
}

.success-icon {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: var(--collection-accent);
  color: #1a1a2e;
  font-size: 2rem;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 1.5rem;
}

.success-content h3 {
  margin: 0 0 0.5rem 0;
}

.success-content p {
  margin: 0 0 1.5rem 0;
  color: var(--collection-text-secondary);
}

.success-actions {
  display: flex;
  gap: 0.75rem;
  justify-content: center;
}

.success-actions button {
  padding: 0.6rem 1.25rem;
  border-radius: 6px;
  border: none;
  cursor: pointer;
  font-weight: 500;
}

.success-actions .primary {
  background: var(--collection-accent);
  color: #1a1a2e;
}

.success-actions .secondary {
  background: #3a3a5e;
  color: white;
}

/* Transitions */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
```

**Step 4: Verify**

Run: `cd src/frontend && npm run dev`
Expected: CollectionPicker shows thumbnail previews of images being added, has styled collection list with thumbnails, shows success animation after adding.

**Step 5: Commit**

```bash
git add src/frontend/src/components/CollectionPicker.vue
git commit -m "feat(collections): enhance picker with previews and success state"
```

---

## Task 11: Add Micro-interactions and Transitions

**Files:**
- Modify: `src/frontend/src/assets/collections.css`

**Step 1: Add animation keyframes**

Add to `src/frontend/src/assets/collections.css`:

```css
/* Micro-interactions */
@keyframes pulse-scale {
  0%, 100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.05);
  }
}

@keyframes fade-slide-out {
  from {
    opacity: 1;
    transform: translateX(0);
  }
  to {
    opacity: 0;
    transform: translateX(-20px);
  }
}

@keyframes fade-in {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.collection-card-enter-active {
  animation: pulse-scale 0.3s ease;
}

.collection-item-leave-active {
  animation: fade-slide-out 0.3s ease forwards;
}

.grid-crossfade-enter-active,
.grid-crossfade-leave-active {
  transition: opacity 0.2s ease;
}

.grid-crossfade-enter-from,
.grid-crossfade-leave-to {
  opacity: 0;
}
```

**Step 2: Verify**

Run: `cd src/frontend && npm run dev`
Expected: CSS animations defined and ready for use.

**Step 3: Commit**

```bash
git add src/frontend/src/assets/collections.css
git commit -m "feat(collections): add micro-interaction animations"
```

---

## Task 12: Final Integration and Testing

**Files:**
- Verify all components work together

**Step 1: Run full application**

```bash
docker-compose up --build
```

**Step 2: Test desktop layout**

1. Navigate to Collections tab (width > 768px)
2. Verify sidebar shows on left with gold "+ New" button
3. Create a new collection - verify it appears in sidebar
4. Select collection - verify gold border appears
5. Verify header shows collection name, item count, hover reveals edit/delete icons
6. Add images from Local/Met tabs
7. Verify selection preview shows in action bar
8. Verify "Remove from Collection" button is isolated from upload buttons

**Step 3: Test mobile layout**

1. Resize to < 768px or use mobile device
2. Verify bottom sheet bar appears
3. Tap to expand - verify collection list appears
4. Long-press collection - verify context menu appears
5. Verify simplified footer with gear icon for settings

**Step 4: Test empty states**

1. Delete all collections
2. Verify "Curate your favorite artwork" empty state appears
3. Create new collection
4. Verify "This collection is empty" state appears
5. Verify "Go to Local Images" button works

**Step 5: Test CollectionPicker**

1. Go to Local Images tab
2. Select images
3. Click "+ Collection"
4. Verify image preview thumbnails appear at top
5. Add to existing collection
6. Verify success animation with "View Collection" / "Done" buttons

**Step 6: Commit final changes**

```bash
git add -A
git commit -m "feat(collections): complete UX redesign with sidebar, bottom sheet, and visual polish"
```

---

## Summary

This plan implements the Collections UX Redesign with:

1. **CSS Variables** - Gold accent color system (`--collection-accent: #D4A574`)
2. **CollectionCard** - Reusable card with thumbnail, name, count, selected state
3. **CollectionsSidebar** - Desktop sidebar with "+ New" button and card list
4. **SelectionPreview** - Thumbnail strip showing selected images
5. **Empty States** - Two components for no-collections and empty-collection scenarios
6. **CollectionsPanel Restructure** - Sidebar layout on desktop, original layout on mobile (interim)
7. **CollectionBottomSheet** - Mobile bottom sheet with swipe, context menu
8. **Mobile Integration** - Simplified footer with settings gear icon
9. **CollectionPicker Enhancement** - Preview thumbnails, success animation
10. **Micro-interactions** - CSS animations for polish

Total: 12 tasks with bite-sized steps, complete code, and verification commands.
