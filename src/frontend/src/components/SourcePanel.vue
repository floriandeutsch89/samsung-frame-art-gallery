<template>
  <div class="source-panel">
    <div class="source-tabs" :class="{ 'collections-active': activeTab === 'collections' }">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        :class="{ active: activeTab === tab.id }"
        @click="activeTab = tab.id"
      >
        {{ tab.label }}
      </button>
    </div>

    <LocalPanel
      v-show="activeTab === 'local'"
      @uploaded="$emit('uploaded')"
      @preview="(img) => $emit('preview', img, true)"
    />

    <MetPanel
      v-show="activeTab === 'met'"
      @uploaded="$emit('uploaded')"
      @preview="(img) => $emit('preview', img, false)"
    />

    <ReframedPanel
      v-show="activeTab === 'reframed'"
      @uploaded="$emit('uploaded')"
      @preview="(img) => $emit('preview', img, false)"
    />

    <CollectionsPanel
      ref="collectionsPanel"
      v-show="activeTab === 'collections'"
      @uploaded="$emit('uploaded')"
      @preview="(img, isLocal) => $emit('preview', img, isLocal)"
    />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import LocalPanel from '../views/LocalPanel.vue'
import MetPanel from '../views/MetPanel.vue'
import ReframedPanel from '../views/ReframedPanel.vue'
import CollectionsPanel from '../views/CollectionsPanel.vue'

defineEmits(['uploaded', 'preview'])

const collectionsPanel = ref(null)
const metEnabled = ref(true)

const allTabs = [
  { id: 'local', label: 'Local Images' },
  { id: 'met', label: 'Metropolitan Museum of Art' },
  { id: 'reframed', label: 'Reframed Gallery' },
  { id: 'collections', label: 'Collections' }
]

const tabs = computed(() =>
  metEnabled.value ? allTabs : allTabs.filter(t => t.id !== 'met')
)

// Read tab from URL if specified
const getUrlTab = () => {
  const params = new URLSearchParams(window.location.search)
  return params.get('tab')
}

// Start with 'local', will switch to first external source if no local images
const activeTab = ref(getUrlTab() || 'local')

// Fetch config and check for local images on mount
onMounted(async () => {
  try {
    const res = await fetch('/api/tv/config')
    const config = await res.json()
    metEnabled.value = config.met_enabled !== false
  } catch (e) {
    // keep met visible if config fetch fails
  }

  // Only auto-switch if no tab specified in URL
  if (!getUrlTab()) {
    try {
      const res = await fetch('/api/images')
      const data = await res.json()
      if (!data.images || data.images.length === 0) {
        activeTab.value = metEnabled.value ? 'met' : 'reframed'
      }
    } catch (e) {
      // stay on local tab
    }
  }
})

// Update URL when tab changes and refresh data
watch(activeTab, (newTab) => {
  const params = new URLSearchParams(window.location.search)
  params.set('tab', newTab)
  const newUrl = `${window.location.pathname}?${params.toString()}`
  window.history.replaceState({}, '', newUrl)

  // Refresh collections when switching to collections tab
  if (newTab === 'collections' && collectionsPanel.value) {
    collectionsPanel.value.loadCollections()
  }
})
</script>

<style scoped>
.source-panel {
  display: contents; /* Let children participate in parent subgrid */
}

.source-tabs {
  display: flex;
  background: #1a1a2e;
  border-bottom: 1px solid #2a2a4e;
}

.source-tabs button {
  flex: 1;
  padding: 0.75rem;
  border: none;
  background: transparent;
  color: #888;
  cursor: pointer;
  font-size: 0.9rem;
  transition: all 0.2s;
}

.source-tabs button:hover {
  color: #aaa;
}

.source-tabs button.active {
  color: white;
  border-bottom: 2px solid #4a90d9;
}

/* When Collections tab is active, add left padding to align with sidebar */
.source-tabs.collections-active {
  padding-left: 200px; /* Match sidebar width */
}
</style>
