<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-content">
      <div class="modal-header">
        <h2 v-if="reframeEnabled">Re-framing Preview</h2>
        <h2 v-else>Preview (Crop: {{ cropPercent }}%, Matte: {{ mattePercent }}%)</h2>
        <button class="close-btn" @click="$emit('close')">&times;</button>
      </div>

      <!-- Zoom slider for single-image reframe -->
      <div v-if="reframeEnabled && selectedPaths.length === 1" class="zoom-bar">
        <label>Zoom</label>
        <input
          type="range"
          v-model.number="reframeZoom"
          min="1"
          max="5"
          step="0.05"
          @input="onZoomChange"
        />
        <span class="zoom-value">{{ reframeZoom.toFixed(1) }}×</span>
      </div>

      <!-- Reframe info message for multiple images -->
      <div v-if="reframeEnabled && selectedPaths.length > 1" class="info-banner">
        Re-framing uses center crop for multiple images. Select a single image for manual positioning.
      </div>

      <div v-if="loading" class="loading-state">
        <div class="spinner"></div>
        <p>Generating previews...</p>
      </div>

      <!-- Single image reframe mode with drag -->
      <div v-else-if="reframeEnabled && selectedPaths.length === 1" class="reframe-container" ref="containerRef">
        <!-- Close button shown only in landscape where header is hidden -->
        <button class="close-landscape" @click="$emit('close')">&times;</button>
        <!-- Fullscreen toggle shown only in landscape -->
        <button class="fullscreen-btn" @click="toggleFullscreen" :title="isFullscreen ? 'Exit fullscreen' : 'Enter fullscreen'">
          <svg v-if="!isFullscreen" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"/>
          </svg>
          <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M8 3v3a2 2 0 0 1-2 2H3m18 0h-3a2 2 0 0 1-2-2V3m0 18v-3a2 2 0 0 1 2-2h3M3 16h3a2 2 0 0 1 2 2v3"/>
          </svg>
        </button>
        <div class="reframe-instructions">
          Drag the image to position within the frame. Darkened areas will be cropped.
        </div>
        <div
          class="reframe-canvas"
          ref="viewportRef"
          :style="canvasPixelWidth ? { width: canvasPixelWidth + 'px', height: canvasPixelHeight + 'px' } : {}"
          @mousedown="startDrag"
          @touchstart="startDrag"
        >
          <img
            v-if="originalImageUrl"
            :src="originalImageUrl"
            class="reframe-image"
            :style="canvasImageStyle"
            draggable="false"
            @load="onImageLoad"
          />
          <!-- Frame overlay showing crop boundaries -->
          <div class="crop-overlay">
            <div class="crop-window" :style="cropWindowStyle"></div>
          </div>
        </div>
      </div>

      <!-- Standard preview mode -->
      <div v-else-if="previews.length === 0" class="empty-state">
        <p>No previews available</p>
      </div>

      <div v-else class="previews-container">
        <div v-for="preview in previews" :key="preview.name" class="preview-item">
          <h3>{{ preview.name }}</h3>
          <div class="comparison">
            <div class="image-box">
              <h4>Original</h4>
              <img :src="preview.original_url" :alt="`Original ${preview.name}`" />
            </div>
            <div class="image-box">
              <h4>Processed</h4>
              <img :src="preview.processed_url" :alt="`Processed ${preview.name}`" />
            </div>
          </div>
        </div>
      </div>

      <div class="modal-footer">
        <button class="secondary" @click="$emit('close')">Cancel</button>
        <button
          class="primary"
          @click="$emit('upload')"
          :disabled="loading || (previews.length === 0 && !reframeEnabled)"
        >
          Upload All
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'

const emit = defineEmits(['close', 'upload', 'offset-change'])
const props = defineProps({
  previews: {
    type: Array,
    default: () => []
  },
  cropPercent: {
    type: Number,
    default: 0
  },
  mattePercent: {
    type: Number,
    default: 10
  },
  loading: {
    type: Boolean,
    default: false
  },
  reframeEnabled: {
    type: Boolean,
    default: false
  },
  selectedPaths: {
    type: Array,
    default: () => []
  }
})

// Fullscreen
const isFullscreen = ref(false)

const toggleFullscreen = async () => {
  if (!document.fullscreenElement) {
    try {
      await document.documentElement.requestFullscreen({ navigationUI: 'hide' })
    } catch {
      // iOS Safari doesn't support requestFullscreen — nothing to do
    }
  } else {
    try {
      await document.exitFullscreen()
    } catch {}
  }
}

const onFullscreenChange = () => {
  isFullscreen.value = !!document.fullscreenElement
}

// Reframe drag state
const viewportRef = ref(null)
const containerRef = ref(null)
const originalImageUrl = ref(null)
const imageNaturalWidth = ref(0)
const imageNaturalHeight = ref(0)
const offsetX = ref(0.5)
const offsetY = ref(0.5)
const reframeZoom = ref(1.0)
const isDragging = ref(false)
const dragStartX = ref(0)
const dragStartY = ref(0)
const dragStartOffsetX = ref(0)
const dragStartOffsetY = ref(0)

const TARGET_RATIO = 16 / 9
const CANVAS_WIDTH = 800
const CANVAS_HEIGHT = 500  // Larger than 16:9 to show context

// JS-driven canvas sizing: only active in landscape mobile where iOS Safari's
// aspect-ratio + max-height: 100% is unreliable on flex items.
// In portrait and desktop, CSS handles it correctly and JS stays out of the way.
const canvasPixelWidth = ref(0)
const canvasPixelHeight = ref(0)

const landscapeQuery = typeof window !== 'undefined'
  ? window.matchMedia('(orientation: landscape) and (max-height: 600px)')
  : null

const updateCanvasSize = () => {
  const el = containerRef.value
  if (!el || !landscapeQuery?.matches) {
    canvasPixelWidth.value = 0
    canvasPixelHeight.value = 0
    return
  }
  const { width, height } = el.getBoundingClientRect()
  const aspect = CANVAS_WIDTH / CANVAS_HEIGHT  // 8/5 = 1.6
  if (width / height > aspect) {
    canvasPixelHeight.value = height
    canvasPixelWidth.value = height * aspect
  } else {
    canvasPixelWidth.value = width
    canvasPixelHeight.value = width / aspect
  }
}

let resizeObserver = null

// Calculate image dimensions for the canvas view (as percentages of CANVAS_WIDTH/HEIGHT)
const canvasImageStyle = computed(() => {
  if (!imageNaturalWidth.value || !imageNaturalHeight.value) return {}

  const imgRatio = imageNaturalWidth.value / imageNaturalHeight.value
  let imgDisplayWidth, imgDisplayHeight

  if (imgRatio > CANVAS_WIDTH / CANVAS_HEIGHT) {
    imgDisplayWidth = CANVAS_WIDTH
    imgDisplayHeight = CANVAS_WIDTH / imgRatio
  } else {
    imgDisplayHeight = CANVAS_HEIGHT
    imgDisplayWidth = CANVAS_HEIGHT * imgRatio
  }

  // Use percentages so the canvas can be any CSS size
  return {
    width: `${imgDisplayWidth / CANVAS_WIDTH * 100}%`,
    height: `${imgDisplayHeight / CANVAS_HEIGHT * 100}%`,
  }
})

// Calculate crop window position and size
const cropWindowStyle = computed(() => {
  if (!imageNaturalWidth.value || !imageNaturalHeight.value) return {}

  const imgRatio = imageNaturalWidth.value / imageNaturalHeight.value

  // Get displayed image dimensions
  let imgDisplayWidth, imgDisplayHeight
  if (imgRatio > CANVAS_WIDTH / CANVAS_HEIGHT) {
    imgDisplayWidth = CANVAS_WIDTH
    imgDisplayHeight = CANVAS_WIDTH / imgRatio
  } else {
    imgDisplayHeight = CANVAS_HEIGHT
    imgDisplayWidth = CANVAS_HEIGHT * imgRatio
  }

  // Base crop window at zoom 1.0
  let baseCropWidth, baseCropHeight
  if (imgRatio > TARGET_RATIO) {
    baseCropHeight = imgDisplayHeight
    baseCropWidth = baseCropHeight * TARGET_RATIO
  } else {
    baseCropWidth = imgDisplayWidth
    baseCropHeight = baseCropWidth / TARGET_RATIO
  }

  // Shrink crop window by zoom (mirrors backend)
  const cropWidth = baseCropWidth / reframeZoom.value
  const cropHeight = baseCropHeight / reframeZoom.value

  // Calculate max offset for crop window positioning
  const maxOffsetX = imgDisplayWidth - cropWidth
  const maxOffsetY = imgDisplayHeight - cropHeight

  // Position crop window based on offset
  const cropLeft = (CANVAS_WIDTH - imgDisplayWidth) / 2 + maxOffsetX * offsetX.value
  const cropTop = (CANVAS_HEIGHT - imgDisplayHeight) / 2 + maxOffsetY * offsetY.value

  // Use percentages so the canvas can be any CSS size
  return {
    width: `${cropWidth / CANVAS_WIDTH * 100}%`,
    height: `${cropHeight / CANVAS_HEIGHT * 100}%`,
    left: `${cropLeft / CANVAS_WIDTH * 100}%`,
    top: `${cropTop / CANVAS_HEIGHT * 100}%`,
  }
})

const onImageLoad = (e) => {
  imageNaturalWidth.value = e.target.naturalWidth
  imageNaturalHeight.value = e.target.naturalHeight
}

const startDrag = (e) => {
  e.preventDefault()
  isDragging.value = true

  const clientX = e.touches ? e.touches[0].clientX : e.clientX
  const clientY = e.touches ? e.touches[0].clientY : e.clientY

  dragStartX.value = clientX
  dragStartY.value = clientY
  dragStartOffsetX.value = offsetX.value
  dragStartOffsetY.value = offsetY.value

  document.addEventListener('mousemove', onDrag)
  document.addEventListener('mouseup', stopDrag)
  document.addEventListener('touchmove', onDrag, { passive: false })
  document.addEventListener('touchend', stopDrag)
  document.addEventListener('touchcancel', stopDrag)
}

const onDrag = (e) => {
  if (!isDragging.value) return
  e.preventDefault()

  const clientX = e.touches ? e.touches[0].clientX : e.clientX
  const clientY = e.touches ? e.touches[0].clientY : e.clientY

  const imgRatio = imageNaturalWidth.value / imageNaturalHeight.value

  // Scale from screen pixels to canvas coordinate pixels (separate X/Y for robustness)
  const canvasEl = viewportRef.value
  const rect = canvasEl ? canvasEl.getBoundingClientRect() : null
  const scaleX = rect ? CANVAS_WIDTH / rect.width : 1
  const scaleY = rect ? CANVAS_HEIGHT / rect.height : 1

  const deltaX = (clientX - dragStartX.value) * scaleX
  const deltaY = (clientY - dragStartY.value) * scaleY

  // Get displayed image dimensions (same calc as canvasImageStyle)
  let imgDisplayWidth, imgDisplayHeight
  if (imgRatio > CANVAS_WIDTH / CANVAS_HEIGHT) {
    imgDisplayWidth = CANVAS_WIDTH
    imgDisplayHeight = CANVAS_WIDTH / imgRatio
  } else {
    imgDisplayHeight = CANVAS_HEIGHT
    imgDisplayWidth = CANVAS_HEIGHT * imgRatio
  }

  // Base crop dimensions at zoom 1.0, then shrink by zoom
  let baseCropWidth, baseCropHeight
  if (imgRatio > TARGET_RATIO) {
    baseCropHeight = imgDisplayHeight
    baseCropWidth = baseCropHeight * TARGET_RATIO
  } else {
    baseCropWidth = imgDisplayWidth
    baseCropHeight = baseCropWidth / TARGET_RATIO
  }
  const cropWidth = baseCropWidth / reframeZoom.value
  const cropHeight = baseCropHeight / reframeZoom.value

  // Calculate max offset (how far crop window can move)
  const maxOffsetX = imgDisplayWidth - cropWidth
  const maxOffsetY = imgDisplayHeight - cropHeight

  // Drag moves the crop window; positive delta = positive offset
  if (maxOffsetX > 0) {
    offsetX.value = Math.max(0, Math.min(1, dragStartOffsetX.value + deltaX / maxOffsetX))
  }
  if (maxOffsetY > 0) {
    offsetY.value = Math.max(0, Math.min(1, dragStartOffsetY.value + deltaY / maxOffsetY))
  }
}

const stopDrag = () => {
  if (!isDragging.value) return
  isDragging.value = false

  document.removeEventListener('mousemove', onDrag)
  document.removeEventListener('mouseup', stopDrag)
  document.removeEventListener('touchmove', onDrag)
  document.removeEventListener('touchend', stopDrag)
  document.removeEventListener('touchcancel', stopDrag)

  // Emit offset change to parent
  if (props.selectedPaths.length === 1) {
    emit('offset-change', props.selectedPaths[0], offsetX.value, offsetY.value, reframeZoom.value)
  }
}

// Load original image for reframe mode
const loadOriginalImage = async () => {
  if (!props.reframeEnabled || props.selectedPaths.length !== 1) return

  const path = props.selectedPaths[0]
  originalImageUrl.value = `/api/images/${encodeURIComponent(path)}/thumbnail?size=1200`

  // Reset offset and zoom
  offsetX.value = 0.5
  offsetY.value = 0.5
  reframeZoom.value = 1.0
}

const onZoomChange = () => {
  if (props.selectedPaths.length === 1) {
    emit('offset-change', props.selectedPaths[0], offsetX.value, offsetY.value, reframeZoom.value)
  }
}

watch(() => [props.reframeEnabled, props.selectedPaths], loadOriginalImage, { immediate: true })

watch(containerRef, (el) => {
  if (resizeObserver) {
    resizeObserver.disconnect()
    resizeObserver = null
  }
  if (el) {
    resizeObserver = new ResizeObserver(updateCanvasSize)
    resizeObserver.observe(el)
    updateCanvasSize()
  }
})

onMounted(() => {
  document.addEventListener('fullscreenchange', onFullscreenChange)
  landscapeQuery?.addEventListener('change', updateCanvasSize)
})


onUnmounted(() => {
  document.removeEventListener('mousemove', onDrag)
  document.removeEventListener('mouseup', stopDrag)
  document.removeEventListener('touchmove', onDrag)
  document.removeEventListener('touchend', stopDrag)
  document.removeEventListener('touchcancel', stopDrag)
  document.removeEventListener('fullscreenchange', onFullscreenChange)
  landscapeQuery?.removeEventListener('change', updateCanvasSize)
  resizeObserver?.disconnect()
  if (document.fullscreenElement) {
    document.exitFullscreen().catch(() => {})
  }
})
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 1rem;
}

.modal-content {
  background: #1a1a2e;
  border-radius: 8px;
  max-width: 1400px;
  max-height: 90vh;
  width: 100%;
  display: flex;
  flex-direction: column;
  border: 1px solid #2a2a4e;
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
  font-size: 1.2rem;
  color: white;
}

.close-btn {
  background: transparent;
  border: none;
  color: #aaa;
  font-size: 2rem;
  cursor: pointer;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
}

.close-btn:hover {
  color: white;
}

.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem;
  color: #aaa;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #2a2a4e;
  border-top-color: #4a90d9;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.previews-container {
  flex: 1;
  overflow-y: auto;
  padding: 1.5rem;
}

.preview-item {
  margin-bottom: 2rem;
}

.preview-item:last-child {
  margin-bottom: 0;
}

.preview-item h3 {
  margin: 0 0 1rem 0;
  font-size: 1rem;
  color: white;
  font-weight: 500;
}

.comparison {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.image-box {
  background: #12121f;
  border: 1px solid #2a2a4e;
  border-radius: 4px;
  padding: 0.75rem;
}

.image-box h4 {
  margin: 0 0 0.5rem 0;
  font-size: 0.9rem;
  color: #aaa;
  font-weight: 500;
}

.image-box img {
  width: 100%;
  height: auto;
  display: block;
  border-radius: 2px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  padding: 1rem 1.5rem;
  border-top: 1px solid #2a2a4e;
}

.modal-footer button {
  padding: 0.5rem 1rem;
  border-radius: 4px;
  border: none;
  cursor: pointer;
  font-weight: 500;
  transition: opacity 0.2s;
}

.modal-footer button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.modal-footer button.primary {
  background: #4a90d9;
  color: white;
}

.modal-footer button.secondary {
  background: #3a3a5e;
  color: white;
}

/* Mobile portrait: stack comparison images */
@media (max-width: 768px) {
  .comparison {
    grid-template-columns: 1fr;
  }
}

/* Reframe mode styles */
.zoom-bar {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem 1.5rem;
  background: #12121f;
  border-bottom: 1px solid #2a2a4e;
}

.zoom-bar label {
  font-size: 0.85rem;
  color: #aaa;
  white-space: nowrap;
}

.zoom-bar input[type="range"] {
  flex: 1;
  accent-color: #4a90d9;
}

.zoom-value {
  font-size: 0.85rem;
  color: #ccc;
  width: 2.5rem;
  text-align: right;
}

.info-banner {
  background: #2a3a5e;
  color: #8ab4f8;
  padding: 0.75rem 1.5rem;
  font-size: 0.9rem;
  border-bottom: 1px solid #3a4a6e;
}

.reframe-container {
  flex: 1;
  min-height: 0;
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 0.75rem 1.25rem;
  overflow: hidden;
  gap: 0.5rem;
}

.reframe-instructions {
  color: #aaa;
  font-size: 0.85rem;
  flex-shrink: 0;
}

.reframe-canvas {
  position: relative;
  /* CSS handles sizing on desktop and portrait mobile.
     JS (ResizeObserver) overrides width+height only in landscape mobile
     where iOS Safari's aspect-ratio + max-height: 100% is unreliable. */
  width: 100%;
  max-width: 800px;
  aspect-ratio: 8 / 5;
  max-height: 100%;
  cursor: grab;
  border-radius: 4px;
  background: #1a1a2e;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.reframe-canvas:active {
  cursor: grabbing;
}

.reframe-image {
  user-select: none;
  pointer-events: none;
  position: relative;
  z-index: 1;
}

.crop-overlay {
  position: absolute;
  inset: 0;
  z-index: 2;
  pointer-events: none;
}

.crop-window {
  position: absolute;
  /* Transparent window showing the crop area */
  background: transparent;
  border: 2px solid #4a90d9;
  border-radius: 2px;
  box-shadow:
    0 0 0 9999px rgba(0, 0, 0, 0.6),
    inset 0 0 0 1px rgba(255, 255, 255, 0.2);
}

/* Corner indicators */
.crop-window::before,
.crop-window::after {
  content: '';
  position: absolute;
  width: 20px;
  height: 20px;
  border-color: #fff;
  border-style: solid;
}

.crop-window::before {
  top: -2px;
  left: -2px;
  border-width: 3px 0 0 3px;
}

.crop-window::after {
  bottom: -2px;
  right: -2px;
  border-width: 0 3px 3px 0;
}

/* Close + fullscreen buttons overlaid on canvas in landscape (hidden otherwise) */
.close-landscape,
.fullscreen-btn {
  display: none;
  position: absolute;
  z-index: 10;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.5);
  border: none;
  color: white;
  cursor: pointer;
  align-items: center;
  justify-content: center;
  padding: 6px;
}

.close-landscape {
  top: 6px;
  right: 6px;
  font-size: 1.1rem;
  line-height: 1;
}

.fullscreen-btn {
  top: 6px;
  right: 44px;
}

.fullscreen-btn svg {
  width: 100%;
  height: 100%;
}

.close-landscape:hover,
.fullscreen-btn:hover {
  background: rgba(0, 0, 0, 0.75);
}

/* ── Landscape mobile (phones in landscape) ── */
@media (orientation: landscape) and (max-height: 600px) {
  .modal-overlay {
    padding: 0;
  }

  .modal-content {
    border-radius: 0;
    max-height: 100dvh;
    height: 100dvh;
  }

  /* Hide title bar — close button moves to overlay */
  .modal-header {
    display: none;
  }

  .close-landscape,
  .fullscreen-btn {
    display: flex;
  }

  /* Canvas container fills all remaining height */
  .reframe-container {
    flex: 1;
    min-height: 0;
    padding: 4px;
    gap: 0;
  }

  .reframe-instructions {
    display: none;
  }

  /* Slim zoom + footer row */
  .zoom-bar {
    padding: 0.25rem 0.75rem;
    border-top: 1px solid #2a2a4e;
    border-bottom: none;
  }

  .modal-footer {
    padding: 0.35rem 0.75rem;
  }
}

/* Portrait mobile: full-screen modal, compact chrome */
@media (max-width: 768px) and (orientation: portrait) {
  .modal-overlay {
    padding: 0;
  }

  .modal-content {
    border-radius: 0;
    max-height: 100dvh;
  }

  .modal-header {
    padding: 0.5rem 1rem;
  }

  .modal-header h2 {
    font-size: 0.9rem;
  }

  .modal-footer {
    padding: 0.5rem 1rem;
  }

  .zoom-bar {
    padding: 0.3rem 0.75rem;
  }

  .reframe-container {
    padding: 0.25rem 0.5rem;
    gap: 0.25rem;
  }

  .reframe-instructions {
    display: none;
  }
}
</style>
