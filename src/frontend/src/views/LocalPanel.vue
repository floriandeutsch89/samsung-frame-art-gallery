<template>
  <div class="local-panel">
    <div class="panel-header">
      <div class="folder-select">
        <button
          :class="{ active: !currentFolder }"
          @click="currentFolder = null"
        >All</button>
        <select v-if="folders.length" v-model="currentFolder">
          <option :value="null">All Folders</option>
          <option v-for="f in folders" :key="f" :value="f">{{ f }}</option>
        </select>
      </div>
      <div class="header-actions">
        <span v-if="importError" class="import-error">{{ importError }}</span>
        <button class="add-image-btn" :disabled="importing" @click="triggerFileUpload">
          {{ importing ? 'Importing...' : '+ Add Image' }}
        </button>
        <input
          ref="fileInput"
          type="file"
          accept="image/*"
          multiple
          style="display:none"
          @change="handleFileUpload"
        />
      </div>
    </div>

    <ImageGrid
      :images="images"
      :selected-ids="selectedIds"
      :loading="loading"
      :is-local="true"
      @toggle="toggleSelection"
      @select-all="selectAll"
      @preview="(img) => $emit('preview', img, true)"
      @delete="deleteImage"
    />

    <ActionBar>
      <template #left>
        <div v-if="uploading" class="upload-progress">
          <div class="upload-spinner"></div>
          <div class="progress-info">
            <span v-if="uploadPhase === 'processing'" class="progress-label">Processing…</span>
            <span v-else class="progress-label">
              {{ uploadCurrent }} / {{ uploadTotal }}
              <span class="progress-name">· {{ uploadName }}</span>
            </span>
            <div class="progress-track">
              <div class="progress-fill" :style="{ width: uploadProgressPct + '%' }"></div>
            </div>
          </div>
        </div>
        <CropSettings
          v-else
          :has-selection="selectedIds.size > 0"
          @change="setSettings"
        />
      </template>
      <button
        class="secondary"
        :disabled="selectedIds.size === 0"
        @click="loadPreviews"
      >
        Preview
      </button>
      <button
        class="secondary"
        :disabled="selectedIds.size === 0"
        @click="showCollectionPicker = true"
      >
        + Collection
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

    <PreviewModal
      v-if="showPreview"
      :previews="previews"
      :crop-percent="cropPercent"
      :matte-percent="mattePercent"
      :loading="previewLoading"
      :reframe-enabled="reframeEnabled"
      :selected-paths="selectedPathsArray"
      @close="showPreview = false"
      @upload="uploadFromPreview"
      @offset-change="fetchPreviewWithOffset"
    />

    <CollectionPicker
      v-if="showCollectionPicker"
      :items="selectedItemsForCollection"
      @close="showCollectionPicker = false"
      @added="onAddedToCollection"
    />
  </div>
</template>

<script setup>
import { ref, watch, onMounted, computed } from 'vue'
import ImageGrid from '../components/ImageGrid.vue'
import ActionBar from '../components/ActionBar.vue'
import CropSettings from '../components/CropSettings.vue'
import PreviewModal from '../components/PreviewModal.vue'
import CollectionPicker from '../components/CollectionPicker.vue'
import { useUploadStream } from '../composables/useUploadStream.js'

const emit = defineEmits(['uploaded', 'preview'])

const { uploading, uploadPhase, uploadCurrent, uploadTotal, uploadName, uploadProgressPct, streamUpload } = useUploadStream()

const images = ref([])
const folders = ref([])
const currentFolder = ref(null)
const selectedIds = ref(new Set())
const loading = ref(false)
const importing = ref(false)
const importError = ref(null)
const fileInput = ref(null)
const cropPercent = ref(0)
const mattePercent = ref(10)
const showPreview = ref(false)
const previewLoading = ref(false)
const previews = ref([])
const reframeEnabled = ref(false)
const reframeOffsets = ref({})  // path -> {x, y}
const showCollectionPicker = ref(false)

const selectedPathsArray = computed(() => Array.from(selectedIds.value))

const selectedItemsForCollection = computed(() => {
  return selectedPathsArray.value.map(path => ({
    type: 'local',
    path
  }))
})

const loadImages = async () => {
  loading.value = true
  try {
    const url = currentFolder.value
      ? `/api/images?folder=${encodeURIComponent(currentFolder.value)}`
      : '/api/images'
    const res = await fetch(url)
    const data = await res.json()
    images.value = data.images || []
    selectedIds.value = new Set()
  } catch (e) {
    console.error('Failed to load images:', e)
  } finally {
    loading.value = false
  }
}

const loadFolders = async () => {
  try {
    const res = await fetch('/api/images/folders')
    const data = await res.json()
    folders.value = data.folders || []
  } catch (e) {
    console.error('Failed to load folders:', e)
  }
}

const toggleSelection = (image) => {
  const newSet = new Set(selectedIds.value)
  if (newSet.has(image.path)) {
    newSet.delete(image.path)
  } else {
    newSet.add(image.path)
  }
  selectedIds.value = newSet
}

const selectAll = (checked) => {
  if (checked) {
    selectedIds.value = new Set(images.value.map(i => i.path))
  } else {
    selectedIds.value = new Set()
  }
}

const setSettings = (settings) => {
  cropPercent.value = settings.crop
  mattePercent.value = settings.matte
  reframeEnabled.value = settings.reframe || false
}

const loadPreviews = async () => {
  if (selectedIds.value.size === 0) return

  showPreview.value = true
  previewLoading.value = false  // Don't show loading initially for reframe
  previews.value = []

  // Reset offsets when opening preview
  reframeOffsets.value = {}

  // For reframe mode with single image, we don't fetch preview immediately
  // The PreviewModal handles initial display and offset updates
  if (reframeEnabled.value && selectedIds.value.size === 1) {
    previewLoading.value = false
    return
  }

  previewLoading.value = true

  try {
    const res = await fetch('/api/tv/preview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        paths: Array.from(selectedIds.value),
        crop_percent: cropPercent.value,
        matte_percent: mattePercent.value,
        reframe_enabled: reframeEnabled.value,
        reframe_offsets: reframeOffsets.value
      })
    })
    const data = await res.json()
    previews.value = data.previews || []
  } catch (e) {
    console.error('Preview failed:', e)
  } finally {
    previewLoading.value = false
  }
}

const fetchPreviewWithOffset = async (path, offsetX, offsetY, zoom = 1.0) => {
  // Update stored offset + zoom
  reframeOffsets.value = {
    ...reframeOffsets.value,
    [path]: { x: offsetX, y: offsetY, zoom }
  }

  try {
    const res = await fetch('/api/tv/preview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        paths: [path],
        crop_percent: cropPercent.value,
        matte_percent: mattePercent.value,
        reframe_enabled: true,
        reframe_offsets: { [path]: { x: offsetX, y: offsetY, zoom } }
      })
    })
    const data = await res.json()
    if (data.previews && data.previews.length > 0) {
      previews.value = data.previews
    }
  } catch (e) {
    console.error('Preview update failed:', e)
  }
}

const uploadFromPreview = async () => {
  showPreview.value = false
  await upload(false)
}

const upload = async (display) => {
  if (selectedIds.value.size === 0) return
  await streamUpload(
    {
      paths: Array.from(selectedIds.value),
      crop_percent: cropPercent.value,
      matte_percent: mattePercent.value,
      display,
      reframe_enabled: reframeEnabled.value,
      reframe_offsets: reframeOffsets.value,
    },
    () => {
      selectedIds.value = new Set()
      emit('uploaded')
    }
  )
}

const triggerFileUpload = () => {
  fileInput.value?.click()
}

const handleFileUpload = async (event) => {
  const files = Array.from(event.target.files)
  if (!files.length) return

  importing.value = true
  importError.value = null

  try {
    const folder = currentFolder.value || 'uploads'
    for (const file of files) {
      const formData = new FormData()
      formData.append('file', file)
      const res = await fetch(`/api/images/upload?folder=${encodeURIComponent(folder)}`, {
        method: 'POST',
        body: formData,
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Upload failed')
      }
    }
    await loadImages()
    await loadFolders()
  } catch (e) {
    console.error('Import failed:', e)
    importError.value = e.message
    setTimeout(() => { importError.value = null }, 5000)
  } finally {
    importing.value = false
    event.target.value = ''
  }
}

const deleteImage = async (image) => {
  if (!confirm(`Delete "${image.name}"?`)) return
  try {
    const res = await fetch(`/api/images/${encodeURIComponent(image.path)}`, { method: 'DELETE' })
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || 'Delete failed')
    }
    images.value = images.value.filter(i => i.path !== image.path)
    selectedIds.value = new Set([...selectedIds.value].filter(p => p !== image.path))
  } catch (e) {
    alert(`Failed to delete: ${e.message}`)
  }
}

const onAddedToCollection = (collection) => {
  console.log(`Added ${selectedIds.value.size} items to collection: ${collection.name}`)
  // Optionally clear selection after adding
  // selectedIds.value = new Set()
}

watch(currentFolder, loadImages)

onMounted(() => {
  loadImages()
  loadFolders()
})
</script>

<style scoped>
.local-panel {
  display: contents; /* Let children participate in parent subgrid */
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  border-bottom: 1px solid #2a2a4e;
  background: #12121f;
}

.panel-header h2 {
  font-size: 1.1rem;
  margin: 0;
}

.folder-select {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.folder-select button {
  padding: 0.4rem 0.8rem;
  border-radius: 4px;
  border: 1px solid #3a3a5e;
  background: transparent;
  color: #aaa;
  cursor: pointer;
}

.folder-select button.active {
  background: #4a90d9;
  color: white;
  border-color: #4a90d9;
}

.folder-select select {
  padding: 0.4rem;
  border-radius: 4px;
  border: 1px solid #3a3a5e;
  background: #2a2a4e;
  color: white;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.add-image-btn {
  padding: 0.4rem 0.9rem;
  border-radius: 4px;
  border: 1px solid #4a90d9;
  background: transparent;
  color: #4a90d9;
  cursor: pointer;
  font-size: 0.9rem;
  white-space: nowrap;
}

.add-image-btn:hover:not(:disabled) {
  background: #4a90d9;
  color: white;
}

.add-image-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.import-error {
  font-size: 0.8rem;
  color: #e07070;
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Upload progress strip */
.upload-progress {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}

.upload-spinner {
  flex-shrink: 0;
  width: 20px;
  height: 20px;
  border: 2px solid #2a2a4e;
  border-top-color: #4a90d9;
  border-radius: 50%;
  animation: spin 0.9s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.progress-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 160px;
}

.progress-label {
  font-size: 0.85rem;
  color: #ccc;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 220px;
}

.progress-name {
  color: #888;
}

.progress-track {
  height: 3px;
  background: #2a2a4e;
  border-radius: 2px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: #4a90d9;
  border-radius: 2px;
  transition: width 0.3s ease;
}
</style>
