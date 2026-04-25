<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal">
      <div class="modal-header">
        <h2>{{ tvInfo && tvInfo.connected ? 'TV Status' : 'Connect to TV' }}</h2>
        <button class="close-btn" @click="$emit('close')">&times;</button>
      </div>

      <div class="modal-body">

        <!-- TV Stats (shown when connected) -->
        <div v-if="tvInfo && tvInfo.connected" class="tv-stats">
          <button class="expand-btn" @click="statsExpanded = !statsExpanded">
            <span>Developer information</span>
            <span class="expand-arrow" :class="{ open: statsExpanded }">›</span>
          </button>
          <table v-if="statsExpanded" class="stats-table">
            <tbody>
              <tr>
                <td>IP Address</td>
                <td>{{ tvInfo.tv_ip }}</td>
              </tr>
              <tr>
                <td>API Version</td>
                <td>{{ tvInfo.api_version || '—' }}</td>
              </tr>
              <tr>
                <td>Art Mode</td>
                <td>{{ tvInfo.art_mode_supported ? 'Supported' : 'Not supported' }}</td>
              </tr>
              <tr>
                <td>Custom Artworks</td>
                <td :class="{ 'value-warning': tvInfo.artwork_count >= 90 }">
                  {{ tvInfo.artwork_count !== null ? tvInfo.artwork_count : '—' }}
                  <span v-if="tvInfo.artwork_count >= 90" class="warning-hint"> — near limit</span>
                </td>
              </tr>
              <tr>
                <td>SSL Thumbnails</td>
                <td>{{ tvInfo.uses_ssl_thumbnails ? 'Yes' : 'No' }}</td>
              </tr>
              <template v-for="(val, key) in flatDeviceInfo" :key="key">
                <tr>
                  <td>{{ formatKey(key) }}</td>
                  <td>{{ val }}</td>
                </tr>
              </template>
            </tbody>
          </table>
          <div class="divider"><span>Change TV</span></div>
        </div>

        <!-- Loading TV info -->
        <div v-else-if="infoLoading" class="info-loading">
          <div class="spinner small"></div>
          <span>Loading TV info…</span>
        </div>

        <!-- Scanning state -->
        <div v-if="scanning" class="scanning">
          <div class="spinner"></div>
          <p>Scanning for Samsung TVs...</p>
        </div>

        <!-- TV List -->
        <div v-else-if="tvs.length > 0" class="tv-list">
          <div
            v-for="tv in tvs"
            :key="tv.ip"
            class="tv-card"
            :class="{ selected: selectedIp === tv.ip, connecting: connecting && selectedIp === tv.ip }"
            @click="selectTV(tv)"
          >
            <div class="tv-icon">📺</div>
            <div class="tv-info">
              <div class="tv-name">{{ tv.name }}</div>
              <div class="tv-ip">{{ tv.ip }}</div>
            </div>
            <div v-if="connecting && selectedIp === tv.ip" class="connecting-indicator">
              <div class="spinner small"></div>
            </div>
          </div>

          <button class="rescan-btn" @click="scan" :disabled="scanning">
            Rescan
          </button>
        </div>

        <!-- No TVs found -->
        <div v-else class="no-tvs">
          <p>No Samsung TVs found on your network.</p>
          <button class="rescan-btn" @click="scan">Scan Again</button>
        </div>

        <!-- Manual entry -->
        <div class="manual-entry">
          <div class="divider">
            <span>or enter IP manually</span>
          </div>
          <div class="manual-form">
            <input
              v-model="manualIp"
              type="text"
              placeholder="192.168.0.100"
              :disabled="connecting"
              @keyup.enter="connectManual"
            />
            <button @click="connectManual" :disabled="!manualIp || connecting">
              Connect
            </button>
          </div>
        </div>

        <!-- Error message -->
        <div v-if="error" class="error">
          {{ error }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

const emit = defineEmits(['close', 'connected'])

const tvs = ref([])
const scanning = ref(false)
const connecting = ref(false)
const selectedIp = ref(null)
const manualIp = ref('')
const error = ref(null)
const tvInfo = ref(null)
const infoLoading = ref(false)
const statsExpanded = ref(false)

const flatDeviceInfo = computed(() => {
  const info = tvInfo.value?.device_info
  if (!info || typeof info !== 'object') return {}
  const result = {}
  for (const [k, v] of Object.entries(info)) {
    if (typeof v === 'string' || typeof v === 'number' || typeof v === 'boolean') {
      result[k] = v
    }
  }
  return result
})

const formatKey = (key) =>
  key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())

const scan = async () => {
  scanning.value = true
  error.value = null
  tvs.value = []

  try {
    const res = await fetch('/api/tv/discover')
    const data = await res.json()
    tvs.value = data.tvs || []

    // Auto-select if only one TV found
    if (tvs.value.length === 1) {
      setTimeout(() => selectTV(tvs.value[0]), 500)
    }
  } catch (e) {
    error.value = 'Failed to scan for TVs'
  } finally {
    scanning.value = false
  }
}

const selectTV = async (tv) => {
  if (connecting.value) return

  selectedIp.value = tv.ip
  connecting.value = true
  error.value = null

  try {
    const res = await fetch('/api/tv/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ip: tv.ip,
        name: tv.name,
        manual_entry: false
      })
    })

    if (!res.ok) {
      const data = await res.json()
      throw new Error(data.detail || 'Connection failed')
    }

    emit('connected', tv)
  } catch (e) {
    error.value = e.message || 'Failed to connect to TV'
    selectedIp.value = null
  } finally {
    connecting.value = false
  }
}

const connectManual = async () => {
  if (!manualIp.value || connecting.value) return

  // Basic IP validation
  const ipRegex = /^(\d{1,3}\.){3}\d{1,3}$/
  if (!ipRegex.test(manualIp.value)) {
    error.value = 'Please enter a valid IP address'
    return
  }

  connecting.value = true
  selectedIp.value = manualIp.value
  error.value = null

  try {
    const res = await fetch('/api/tv/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ip: manualIp.value,
        name: 'Samsung TV',
        manual_entry: true
      })
    })

    if (!res.ok) {
      const data = await res.json()
      throw new Error(data.detail || 'Connection failed')
    }

    emit('connected', { ip: manualIp.value, name: 'Samsung TV' })
  } catch (e) {
    error.value = e.message || 'Failed to connect to TV'
    selectedIp.value = null
  } finally {
    connecting.value = false
  }
}

const loadTvInfo = async () => {
  infoLoading.value = true
  try {
    const res = await fetch('/api/tv/info')
    if (res.ok) {
      tvInfo.value = await res.json()
    }
  } catch {}
  infoLoading.value = false
}

onMounted(async () => {
  try {
    const res = await fetch('/api/tv/settings')
    const data = await res.json()
    if (data.env_ip) {
      manualIp.value = data.env_ip
    }
  } catch {}
  loadTvInfo()
  scan()
})
</script>

<style scoped>
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
  border-radius: 12px;
  width: 90%;
  max-width: 450px;
  max-height: 80vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem;
  border-bottom: 1px solid #2a2a4e;
}

.modal-header h2 {
  margin: 0;
  font-size: 1.25rem;
  color: white;
}

.close-btn {
  background: none;
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

.modal-body {
  padding: 1.5rem;
  overflow-y: auto;
}

.scanning {
  text-align: center;
  padding: 2rem 0;
  color: #888;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #2a2a4e;
  border-top-color: #4a90d9;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 1rem;
}

.spinner.small {
  width: 20px;
  height: 20px;
  border-width: 2px;
  margin: 0;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.tv-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.tv-card {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  background: #2a2a4e;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.tv-card:hover {
  background: #3a3a5e;
}

.tv-card.selected {
  background: #4a90d9;
}

.tv-card.connecting {
  opacity: 0.7;
  pointer-events: none;
}

.tv-icon {
  font-size: 2rem;
}

.tv-info {
  flex: 1;
}

.tv-name {
  color: white;
  font-weight: 500;
}

.tv-ip {
  color: #888;
  font-size: 0.85rem;
}

.tv-card.selected .tv-ip {
  color: rgba(255, 255, 255, 0.7);
}

.rescan-btn {
  margin-top: 0.5rem;
  padding: 0.5rem 1rem;
  background: transparent;
  border: 1px solid #4a90d9;
  color: #4a90d9;
  border-radius: 6px;
  cursor: pointer;
  align-self: center;
}

.rescan-btn:hover:not(:disabled) {
  background: rgba(74, 144, 217, 0.1);
}

.rescan-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.no-tvs {
  text-align: center;
  padding: 2rem 0;
  color: #888;
}

.manual-entry {
  margin-top: 1.5rem;
}

.divider {
  display: flex;
  align-items: center;
  gap: 1rem;
  color: #666;
  font-size: 0.85rem;
  margin-bottom: 1rem;
}

.divider::before,
.divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: #2a2a4e;
}

.manual-form {
  display: flex;
  gap: 0.75rem;
}

.manual-form input {
  flex: 1;
  padding: 0.75rem 1rem;
  background: #2a2a4e;
  border: 1px solid #3a3a5e;
  border-radius: 6px;
  color: white;
  font-size: 1rem;
}

.manual-form input:focus {
  outline: none;
  border-color: #4a90d9;
}

.manual-form button {
  padding: 0.75rem 1.5rem;
  background: #4a90d9;
  border: none;
  border-radius: 6px;
  color: white;
  cursor: pointer;
  font-weight: 500;
}

.manual-form button:hover:not(:disabled) {
  background: #5a9fe9;
}

.manual-form button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.error {
  margin-top: 1rem;
  padding: 0.75rem 1rem;
  background: rgba(255, 68, 68, 0.1);
  border: 1px solid rgba(255, 68, 68, 0.3);
  border-radius: 6px;
  color: #ff6b6b;
  font-size: 0.9rem;
}

.tv-stats {
  margin-bottom: 0.5rem;
}

.expand-btn {
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0.25rem;
  background: none;
  border: none;
  color: #888;
  font-size: 0.8rem;
  cursor: pointer;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.expand-btn:hover {
  color: #aaa;
}

.expand-arrow {
  font-size: 1.1rem;
  line-height: 1;
  transition: transform 0.2s;
  display: inline-block;
}

.expand-arrow.open {
  transform: rotate(90deg);
}

.stats-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
  margin-bottom: 1.25rem;
}

.stats-table td {
  padding: 0.45rem 0.5rem;
  border-bottom: 1px solid #2a2a4e;
  vertical-align: top;
}

.stats-table td:first-child {
  color: #888;
  width: 45%;
  white-space: nowrap;
}

.stats-table td:last-child {
  color: #e0e0e0;
  font-family: monospace;
  font-size: 0.82rem;
  word-break: break-all;
}

.value-warning {
  color: #ffb347 !important;
}

.warning-hint {
  color: #ffb347;
  font-family: sans-serif;
  font-size: 0.78rem;
}

.info-loading {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  color: #888;
  font-size: 0.85rem;
  padding: 0.75rem 0 1rem;
}
</style>
