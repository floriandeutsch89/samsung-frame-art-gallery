<template>
  <div class="collection-picker-overlay" @click.self="$emit('close')">
    <div class="collection-picker">
      <div class="picker-header">
        <h3>Add to Collection</h3>
        <button class="close-btn" @click="$emit('close')">&times;</button>
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

        <div v-else-if="collections.length === 0" class="empty">
          No collections yet. Create one above.
        </div>

        <div v-else class="collections-list">
          <button
            v-for="collection in collections"
            :key="collection.id"
            class="collection-item"
            :disabled="adding"
            @click="addToCollection(collection.id)"
          >
            <span class="collection-name">{{ collection.name }}</span>
            <span class="collection-count">{{ collection.item_count }} items</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const props = defineProps({
  items: {
    type: Array,
    required: true
    // Array of {type: 'local', path: '...'} or {type: 'met', object_id: 123}
  }
})

const emit = defineEmits(['close', 'added'])

const collections = ref([])
const loading = ref(true)
const newName = ref('')
const creating = ref(false)
const adding = ref(false)

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
    // Create collection
    const createRes = await fetch('/api/collections', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name })
    })
    const collection = await createRes.json()

    // Add items to it
    await fetch(`/api/collections/${collection.id}/items`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ items: props.items })
    })

    emit('added', collection)
    emit('close')
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
    emit('added', collection)
    emit('close')
  } catch (e) {
    console.error('Failed to add to collection:', e)
  } finally {
    adding.value = false
  }
}

onMounted(loadCollections)
</script>

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
  border-radius: 8px;
  width: 90%;
  max-width: 400px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
}

.picker-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
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

.picker-content {
  padding: 1rem;
  overflow-y: auto;
}

.new-collection {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.new-collection input {
  flex: 1;
  padding: 0.5rem;
  border-radius: 4px;
  border: 1px solid #3a3a5e;
  background: #2a2a4e;
  color: white;
}

.new-collection input:focus {
  outline: none;
  border-color: #4a90d9;
}

.new-collection button {
  padding: 0.5rem 1rem;
  border-radius: 4px;
  border: none;
  background: #4a90d9;
  color: white;
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

.collections-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.collection-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  background: #2a2a4e;
  border: 1px solid #3a3a5e;
  border-radius: 4px;
  cursor: pointer;
  color: white;
  text-align: left;
}

.collection-item:hover:not(:disabled) {
  background: #3a3a5e;
  border-color: #4a90d9;
}

.collection-item:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.collection-name {
  font-weight: 500;
}

.collection-count {
  color: #888;
  font-size: 0.85rem;
}
</style>
