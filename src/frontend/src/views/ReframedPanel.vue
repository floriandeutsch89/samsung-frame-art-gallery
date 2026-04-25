<template>
  <div class="reframed-panel">
    <div class="panel-header">
      <div class="header-controls">

        <!-- Mode buttons -->
        <div class="mode-toggle">
          <button :class="{ active: mode === 'recent' }" @click="setMode('recent')">Recent</button>
          <button :class="{ active: mode === 'colors' }" @click="setMode('colors')">Colors</button>
          <button :class="{ active: mode === 'collections' }" :disabled="loadingMeta" @click="setMode('collections')">Collections</button>
          <button :class="{ active: mode === 'artists' }" :disabled="loadingMeta" @click="setMode('artists')">Artists</button>
        </div>

        <!-- Colors: small select (only 14 items) -->
        <select
          v-if="mode === 'colors'"
          v-model="colorSlug"
          @change="onSecondaryChange"
          class="secondary-select"
        >
          <option v-for="c in colors" :key="c.slug" :value="c.slug">{{ c.name }}</option>
        </select>

        <!-- Collections / Artists: search + filtered select -->
        <template v-if="mode === 'collections' || mode === 'artists'">
          <div class="search-box">
            <input
              v-model="searchFilter"
              type="text"
              :placeholder="`Search ${mode}…`"
            />
            <button v-if="searchFilter" class="clear-search" @click="searchFilter = ''">&#x2715;</button>
          </div>
          <select
            v-model="secondarySlug"
            @change="onSecondaryChange"
            class="secondary-select"
          >
            <option
              v-for="item in filteredSecondaryList"
              :key="item.slug"
              :value="item.slug"
            >{{ item.name }}</option>
          </select>
        </template>

      </div>
    </div>

    <ImageGrid
      :images="artwork"
      :selected-ids="selectedIds"
      :loading="loading"
      :loading-more="loadingMore"
      :is-local="false"
      :has-more-external="hasMore"
      :total-count="totalCount"
      @toggle="toggleSelection"
      @select-all="selectAll"
      @preview="(img) => $emit('preview', img)"
      @load-more="loadMore"
    />

    <ActionBar>
      <template #left>
        <CropSettings
          :has-selection="selectedIds.size > 0"
          :allow-reframe="false"
          @change="setSettings"
          @preview="loadPreviews"
        />
      </template>
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
      @close="showPreview = false"
      @upload="uploadFromPreview"
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
import { ref, computed, watch, onMounted } from 'vue'
import ImageGrid from '../components/ImageGrid.vue'
import ActionBar from '../components/ActionBar.vue'
import CropSettings from '../components/CropSettings.vue'
import PreviewModal from '../components/PreviewModal.vue'
import CollectionPicker from '../components/CollectionPicker.vue'

// Module-level cache — survives tab switches, cleared on page reload.
const _cache = new Map()
const CACHE_TTL = 60 * 60 * 1000

function _getCached(key) {
  const entry = _cache.get(key)
  if (entry && entry.expiresAt > Date.now()) return entry.data
  return null
}
function _setCached(key, data) {
  _cache.set(key, { data, expiresAt: Date.now() + CACHE_TTL })
}

const emit = defineEmits(['uploaded', 'preview'])

// --- State ---
const mode = ref('recent')          // recent | colors | collections | artists
const colorSlug = ref('')           // selected color slug
const secondarySlug = ref('')       // selected collection or artist slug
const searchFilter = ref('')        // live filter for collections / artists

const colors = [
  { slug: 'red', name: 'Red' }, { slug: 'orange', name: 'Orange' },
  { slug: 'gold', name: 'Gold' }, { slug: 'yellow', name: 'Yellow' },
  { slug: 'green', name: 'Green' }, { slug: 'teal', name: 'Teal' },
  { slug: 'blue', name: 'Blue' }, { slug: 'navy', name: 'Navy' },
  { slug: 'purple', name: 'Purple' }, { slug: 'pink', name: 'Pink' },
  { slug: 'earth', name: 'Earth' }, { slug: 'black', name: 'Black' },
  { slug: 'white', name: 'White' }, { slug: 'neutral', name: 'Neutral' },
]

const collections = ref([])
const artists = ref([])
const loadingMeta = ref(false)

const artwork = ref([])
const selectedIds = ref(new Set())
const loading = ref(false)
const loadingMore = ref(false)
const uploading = ref(false)
const cropPercent = ref(0)
const mattePercent = ref(10)
const showPreview = ref(false)
const previewLoading = ref(false)
const previews = ref([])
const currentPage = ref(1)
const hasMore = ref(false)
const totalCount = ref(0)
const showCollectionPicker = ref(false)

// --- Computed ---
const filteredSecondaryList = computed(() => {
  const list = mode.value === 'collections' ? collections.value : artists.value
  const q = searchFilter.value.trim().toLowerCase()
  return q ? list.filter(i => i.name.toLowerCase().includes(q)) : list
})

const selectedSource = computed(() => {
  if (mode.value === 'recent') return 'recent'
  if (mode.value === 'colors') return colorSlug.value ? `color:${colorSlug.value}` : null
  if (mode.value === 'collections') return secondarySlug.value ? `collection:${secondarySlug.value}` : null
  if (mode.value === 'artists') return secondarySlug.value ? `artist:${secondarySlug.value}` : null
  return null
})

const selectedItemsForCollection = computed(() =>
  Array.from(selectedIds.value).map(image_id => {
    const item = artwork.value.find(a => a.object_id === image_id)
    return { type: 'reframed', image_id, title: item?.title || 'Untitled' }
  })
)

// --- URL sync ---
const updateUrl = () => {
  const params = new URLSearchParams(window.location.search)
  params.set('tab', 'reframed')
  if (selectedSource.value) params.set('rsource', selectedSource.value)
  if (currentPage.value > 1) params.set('rpage', String(currentPage.value))
  else params.delete('rpage')
  window.history.replaceState({}, '', `${window.location.pathname}?${params.toString()}`)
}

// --- Meta loading ---
const loadMeta = async () => {
  const cached = _getCached('meta')
  if (cached) {
    collections.value = cached.collections
    artists.value = cached.artists
    return
  }
  loadingMeta.value = true
  try {
    const [colRes, artRes] = await Promise.all([
      fetch('/api/reframed/collections'),
      fetch('/api/reframed/artists'),
    ])
    const [colData, artData] = await Promise.all([colRes.json(), artRes.json()])
    collections.value = colData.collections || []
    artists.value = artData.artists || []
    _setCached('meta', { collections: collections.value, artists: artists.value })
  } catch (e) {
    console.error('Failed to load Reframed metadata:', e)
  } finally {
    loadingMeta.value = false
  }
}

// --- Artwork loading ---
const buildEndpoint = (source, page) => {
  if (source === 'recent') return `/api/reframed/recent?page=${page}`
  const [type, slug] = source.split(':')
  if (type === 'color')      return `/api/reframed/color/${encodeURIComponent(slug)}?page=${page}`
  if (type === 'collection') return `/api/reframed/collection/${encodeURIComponent(slug)}?page=${page}`
  if (type === 'artist')     return `/api/reframed/artist/${encodeURIComponent(slug)}?page=${page}`
  return null
}

const loadArtwork = async (append = false) => {
  const source = selectedSource.value
  if (!source) return

  if (!append) {
    currentPage.value = 1
    artwork.value = []
    totalCount.value = 0
    selectedIds.value = new Set()
  }

  const endpoint = buildEndpoint(source, currentPage.value)
  if (!endpoint) return

  const cacheKey = `artwork:${source}:${currentPage.value}`
  const cached = _getCached(cacheKey)
  if (cached && !append) {
    artwork.value = cached.objects
    hasMore.value = cached.has_more
    totalCount.value = cached.total
    return
  }

  append ? (loadingMore.value = true) : (loading.value = true)

  try {
    const res = await fetch(endpoint)
    const data = await res.json()

    const newArtwork = (data.objects || []).map(obj => ({
      ...obj,
      content_id: `reframed_${obj.object_id}`,
      path: null,
    }))

    _setCached(cacheKey, {
      objects: newArtwork,
      has_more: data.has_more || false,
      total: data.total || (artwork.value.length + newArtwork.length),
    })

    artwork.value = append ? [...artwork.value, ...newArtwork] : newArtwork
    hasMore.value = data.has_more || false
    totalCount.value = data.total || artwork.value.length
    updateUrl()
  } catch (e) {
    console.error('Failed to load Reframed artwork:', e)
  } finally {
    loading.value = false
    loadingMore.value = false
  }
}

// --- Event handlers ---
const setMode = (newMode) => {
  mode.value = newMode
  searchFilter.value = ''

  if (newMode === 'recent') {
    loadArtwork()
  } else if (newMode === 'colors') {
    colorSlug.value = colors[0].slug
    loadArtwork()
  } else {
    const list = newMode === 'collections' ? collections.value : artists.value
    secondarySlug.value = list[0]?.slug || ''
    if (secondarySlug.value) loadArtwork()
    else { artwork.value = []; selectedIds.value = new Set() }
  }
}

// When search changes, auto-select the first match and load it
let searchDebounce = null
watch(searchFilter, () => {
  clearTimeout(searchDebounce)
  searchDebounce = setTimeout(() => {
    const list = filteredSecondaryList.value
    if (list.length > 0) {
      secondarySlug.value = list[0].slug
      loadArtwork()
    }
  }, 400)
})

const onSecondaryChange = () => {
  loadArtwork()
}

const loadMore = async () => {
  if (hasMore.value && !loading.value && !loadingMore.value) {
    currentPage.value++
    await loadArtwork(true)
  }
}

const toggleSelection = (image) => {
  const newSet = new Set(selectedIds.value)
  const id = image.object_id
  newSet.has(id) ? newSet.delete(id) : newSet.add(id)
  selectedIds.value = newSet
}

const selectAll = (checked) => {
  selectedIds.value = checked
    ? new Set(artwork.value.map(a => a.object_id))
    : new Set()
}

const setSettings = (settings) => {
  cropPercent.value = settings.crop
  mattePercent.value = settings.matte
}

const buildRequestItems = () =>
  Array.from(selectedIds.value).map(image_id => {
    const item = artwork.value.find(a => a.object_id === image_id)
    return { image_id, title: item?.title || 'Untitled' }
  })

const loadPreviews = async () => {
  if (selectedIds.value.size === 0) return
  showPreview.value = true
  previewLoading.value = true
  previews.value = []
  try {
    const res = await fetch('/api/reframed/preview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        items: buildRequestItems(),
        crop_percent: cropPercent.value,
        matte_percent: mattePercent.value,
      }),
    })
    previews.value = (await res.json()).previews || []
  } catch (e) {
    console.error('Preview failed:', e)
  } finally {
    previewLoading.value = false
  }
}

const upload = (display) => {
  if (selectedIds.value.size === 0) return
  doUpload(display)
}

const uploadFromPreview = () => {
  showPreview.value = false
  doUpload(false)
}

const doUpload = async (display) => {
  uploading.value = true
  try {
    const res = await fetch('/api/reframed/upload', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        items: buildRequestItems(),
        crop_percent: cropPercent.value,
        matte_percent: mattePercent.value,
        display,
      }),
    })
    console.log('Reframed upload results:', await res.json())
    selectedIds.value = new Set()
    emit('uploaded')
  } catch (e) {
    console.error('Upload failed:', e)
  } finally {
    uploading.value = false
  }
}

const onAddedToCollection = () => {}

onMounted(async () => {
  await loadMeta()
  await loadArtwork()
})

defineExpose({ loadMore, hasMore })
</script>

<style scoped>
.reframed-panel {
  display: contents;
}

.panel-header {
  display: flex;
  align-items: center;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid #2a2a4e;
  background: #12121f;
  overflow: visible;
  position: relative;
  z-index: 10;
}

.header-controls {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  flex-wrap: wrap;
  width: 100%;
}

/* Mode buttons */
.mode-toggle {
  display: flex;
  border: 1px solid #3a3a5e;
  border-radius: 6px;
  overflow: hidden;
  flex-shrink: 0;
}

.mode-toggle button {
  padding: 0.35rem 0.75rem;
  border: none;
  background: #2a2a4e;
  color: #888;
  cursor: pointer;
  font-size: 0.85rem;
  transition: all 0.15s;
  white-space: nowrap;
}

.mode-toggle button:hover:not(:disabled) {
  color: #ccc;
}

.mode-toggle button.active {
  background: #4a90d9;
  color: white;
}

.mode-toggle button:disabled {
  opacity: 0.4;
  cursor: default;
}

/* Secondary controls */
.secondary-select {
  padding: 0.35rem 0.5rem;
  border-radius: 4px;
  border: 1px solid #3a3a5e;
  background: #2a2a4e;
  color: white;
  font-size: 0.85rem;
  min-width: 160px;
}

.secondary-select:focus {
  outline: none;
  border-color: #4a90d9;
}

/* Search box */
.search-box {
  position: relative;
  display: flex;
  align-items: center;
}

.search-box input {
  padding: 0.35rem 1.6rem 0.35rem 0.5rem;
  border-radius: 4px;
  border: 1px solid #3a3a5e;
  background: #2a2a4e;
  color: white;
  font-size: 0.85rem;
  width: 150px;
}

.search-box input::placeholder { color: #555; }
.search-box input:focus { outline: none; border-color: #4a90d9; }

.clear-search {
  position: absolute;
  right: 4px;
  background: transparent;
  border: none;
  color: #666;
  font-size: 1rem;
  cursor: pointer;
  padding: 0 3px;
  line-height: 1;
}
.clear-search:hover { color: white; }

@media (max-width: 600px) {
  .panel-header { flex-direction: column; align-items: stretch; }
  .header-controls { flex-direction: column; }
  .secondary-select, .search-box, .search-box input { width: 100%; min-width: 0; }
}
</style>
