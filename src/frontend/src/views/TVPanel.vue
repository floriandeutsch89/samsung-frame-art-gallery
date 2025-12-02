<template>
  <div class="tv-panel">
    <!-- Row 1: Tabs placeholder to align with source tabs -->
    <div class="tabs-placeholder">
      <span class="placeholder-text">&nbsp;</span>
    </div>

    <!-- Row 2: Panel header -->
    <div class="panel-header">
      <h2>TV Artwork</h2>
      <button class="refresh-btn" @click="loadArtwork" :disabled="loading">
        Refresh
      </button>
    </div>

    <!-- Slideshow settings (only visible when TV connected) -->
    <div v-if="connected" class="slideshow-settings">
      <h4>Slideshow</h4>
      <div class="slideshow-controls">
        <label class="toggle-label">
          <input
            type="checkbox"
            v-model="slideshowEnabled"
            @change="updateSlideshow"
            :disabled="slideshowLoading"
          />
          <span>Enable slideshow</span>
        </label>

        <div v-if="slideshowEnabled" class="slideshow-options">
          <label>
            <span>Change every:</span>
            <select v-model.number="slideshowDuration" @change="updateSlideshow" :disabled="slideshowLoading">
              <option :value="5">5 minutes</option>
              <option :value="10">10 minutes</option>
              <option :value="15">15 minutes</option>
              <option :value="30">30 minutes</option>
              <option :value="60">1 hour</option>
            </select>
          </label>

          <label class="toggle-label">
            <input
              type="checkbox"
              v-model="slideshowShuffle"
              @change="updateSlideshow"
              :disabled="slideshowLoading"
            />
            <span>Shuffle order</span>
          </label>
        </div>
      </div>
    </div>

    <!-- Row 3: Image grid -->
    <ImageGrid
      :images="artwork"
      :selected-ids="selectedIds"
      :current-id="currentId"
      :loading="loading"
      :is-local="false"
      @toggle="toggleSelection"
      @select-all="selectAll"
      @preview="(img) => $emit('preview', img, false)"
    />

    <!-- Row 4: Action bar -->
    <ActionBar>
      <template #left>
        <span class="selected-count">{{ selectedIds.size }} selected</span>
      </template>
      <button
        class="secondary"
        :disabled="selectedIds.size !== 1"
        @click="setAsCurrent"
      >
        Display
      </button>
      <button
        class="danger"
        :disabled="selectedIds.size === 0 || deleting"
        @click="deleteSelected"
      >
        Delete ({{ selectedIds.size }})
      </button>
    </ActionBar>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import ImageGrid from '../components/ImageGrid.vue'
import ActionBar from '../components/ActionBar.vue'

const emit = defineEmits(['preview'])

const artwork = ref([])
const currentId = ref(null)
const selectedIds = ref(new Set())
const loading = ref(false)
const deleting = ref(false)

// Slideshow state
const connected = ref(false)
const slideshowEnabled = ref(false)
const slideshowDuration = ref(15)
const slideshowShuffle = ref(true)
const slideshowLoading = ref(false)

const loadArtwork = async () => {
  loading.value = true
  try {
    const [artRes, currentRes] = await Promise.all([
      fetch('/api/tv/artwork'),
      fetch('/api/tv/artwork/current')
    ])
    const artData = await artRes.json()
    const currentData = await currentRes.json()

    artwork.value = artData.artwork || []
    currentId.value = currentData.content_id || null
    selectedIds.value = new Set()

    // Check if TV is connected
    connected.value = true

    // Load slideshow status when we successfully connect
    await loadSlideshowStatus()
  } catch (e) {
    console.error('Failed to load TV artwork:', e)
    connected.value = false
  } finally {
    loading.value = false
  }
}

const loadSlideshowStatus = async () => {
  try {
    const res = await fetch('/api/tv/slideshow')
    const data = await res.json()
    if (!data.error) {
      // Parse the response - format varies by TV
      slideshowEnabled.value = data.value !== 'off' && data.value !== '0'
      if (data.duration) {
        slideshowDuration.value = parseInt(data.duration) || 15
      }
      if (data.type !== undefined) {
        slideshowShuffle.value = data.type === true || data.type === 'shuffle'
      }
    }
  } catch (e) {
    console.error('Failed to load slideshow status:', e)
  }
}

const updateSlideshow = async () => {
  slideshowLoading.value = true
  try {
    await fetch('/api/tv/slideshow', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        enabled: slideshowEnabled.value,
        duration: slideshowDuration.value,
        shuffle: slideshowShuffle.value
      })
    })
  } catch (e) {
    console.error('Failed to update slideshow:', e)
  } finally {
    slideshowLoading.value = false
  }
}

const toggleSelection = (image) => {
  const newSet = new Set(selectedIds.value)
  if (newSet.has(image.content_id)) {
    newSet.delete(image.content_id)
  } else {
    newSet.add(image.content_id)
  }
  selectedIds.value = newSet
}

const selectAll = (checked) => {
  if (checked) {
    selectedIds.value = new Set(artwork.value.map(a => a.content_id))
  } else {
    selectedIds.value = new Set()
  }
}

const setAsCurrent = async () => {
  const contentId = Array.from(selectedIds.value)[0]
  if (!contentId) return

  try {
    await fetch('/api/tv/artwork/current', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content_id: contentId })
    })
    currentId.value = contentId
    selectedIds.value = new Set()
  } catch (e) {
    console.error('Failed to set current artwork:', e)
  }
}

const deleteSelected = async () => {
  if (selectedIds.value.size === 0) return

  deleting.value = true
  try {
    for (const contentId of selectedIds.value) {
      await fetch(`/api/tv/artwork/${contentId}`, { method: 'DELETE' })
    }
    await loadArtwork()
  } catch (e) {
    console.error('Failed to delete artwork:', e)
  } finally {
    deleting.value = false
  }
}

onMounted(loadArtwork)

defineExpose({ loadArtwork })
</script>

<style scoped>
.tv-panel {
  display: contents; /* Let children participate in parent subgrid */
}

/* Row 1: Placeholder to align with source-tabs */
.tabs-placeholder {
  display: flex;
  background: #1a1a2e;
  border-bottom: 1px solid #2a2a4e;
}

/* Match source-tabs button styling exactly for same height */
.placeholder-text {
  padding: 0.75rem;
  font-size: 0.9rem;
}

/* Row 2: Panel header */
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

.refresh-btn {
  padding: 0.4rem 0.8rem;
  border-radius: 4px;
  border: 1px solid #3a3a5e;
  background: transparent;
  color: #aaa;
  cursor: pointer;
}

.refresh-btn:hover:not(:disabled) {
  background: #2a2a4e;
}

.selected-count {
  color: #888;
  font-size: 0.9rem;
}

/* Slideshow settings */
.slideshow-settings {
  padding: 1rem;
  background: #12121f;
  border-bottom: 1px solid #2a2a4e;
}

.slideshow-settings h4 {
  margin: 0 0 0.75rem 0;
  font-size: 0.9rem;
  color: #888;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.slideshow-controls {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.slideshow-options {
  display: flex;
  gap: 1.5rem;
  flex-wrap: wrap;
  padding-left: 1.5rem;
}

.toggle-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
}

.toggle-label input[type="checkbox"] {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.slideshow-options label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.slideshow-options select {
  padding: 0.3rem 0.5rem;
  border-radius: 4px;
  border: 1px solid #3a3a5e;
  background: #2a2a4e;
  color: white;
  cursor: pointer;
}

.slideshow-options select:focus {
  outline: none;
  border-color: #4a90d9;
}

.slideshow-options select:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
