<template>
  <div class="collections-panel">
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

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import ImageGrid from '../components/ImageGrid.vue'
import ActionBar from '../components/ActionBar.vue'
import CropSettings from '../components/CropSettings.vue'

const emit = defineEmits(['uploaded', 'preview'])

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

const loadCollections = async () => {
  try {
    const res = await fetch('/api/collections')
    const data = await res.json()
    collections.value = data.collections || []
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
          // Use path as unique ID for local items
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
    await loadCollections() // Update item counts
  } catch (e) {
    console.error('Failed to remove items:', e)
  }
}

const upload = async (display) => {
  if (selectedIds.value.size === 0) return

  uploading.value = true

  // Separate local and met items
  const selected = items.value.filter(i => selectedIds.value.has(i._id))
  const localPaths = selected.filter(i => i.type === 'local').map(i => i.path)
  const metIds = selected.filter(i => i.type === 'met').map(i => i.object_id)

  try {
    // Upload local images
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

    // Upload Met images
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

// Open rename modal with current name
watch(showRenameModal, (show) => {
  if (show && selectedCollection.value) {
    renameValue.value = selectedCollection.value.name
  }
})

onMounted(loadCollections)
</script>

<style scoped>
.collections-panel {
  display: contents;
}

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
