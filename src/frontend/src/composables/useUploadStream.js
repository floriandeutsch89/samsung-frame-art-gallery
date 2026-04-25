import { ref, computed } from 'vue'

export function useUploadStream() {
  const uploading = ref(false)
  const uploadPhase = ref('idle')   // 'idle' | 'processing' | 'uploading'
  const uploadCurrent = ref(0)
  const uploadTotal = ref(0)
  const uploadName = ref('')

  const uploadProgressPct = computed(() => {
    if (!uploadTotal.value) return 0
    return Math.round((uploadCurrent.value / uploadTotal.value) * 100)
  })

  async function streamUpload(payload, onDone) {
    uploading.value = true
    uploadPhase.value = 'processing'
    uploadCurrent.value = 0
    uploadTotal.value = payload.paths?.length ?? 0
    uploadName.value = ''

    try {
      const res = await fetch('/api/tv/upload/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })

      if (!res.ok) throw new Error(`HTTP ${res.status}`)

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop()

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const event = JSON.parse(line.slice(6))
            if (event.type === 'processing') {
              uploadPhase.value = 'processing'
              uploadTotal.value = event.total
            } else if (event.type === 'uploading') {
              uploadPhase.value = 'uploading'
              uploadCurrent.value = event.current
              uploadTotal.value = event.total
              uploadName.value = event.name
            } else if (event.type === 'done') {
              onDone?.(event.results)
            }
          } catch { /* malformed line — ignore */ }
        }
      }
    } catch (e) {
      console.error('Upload stream failed:', e)
    } finally {
      uploading.value = false
      uploadPhase.value = 'idle'
      uploadCurrent.value = 0
      uploadTotal.value = 0
      uploadName.value = ''
    }
  }

  return {
    uploading,
    uploadPhase,
    uploadCurrent,
    uploadTotal,
    uploadName,
    uploadProgressPct,
    streamUpload,
  }
}
