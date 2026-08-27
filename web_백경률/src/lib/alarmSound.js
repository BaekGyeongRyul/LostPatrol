// 화재 경보음 — 외부 오디오 라이브러리 없이 Web Audio API만으로 2음 사이렌을 재생한다.
// 브라우저 autoplay 정책 때문에 사용자의 첫 interaction 전에는 소리가 나지 않을 수 있어서,
// unlockAlarmAudio()를 첫 click/keydown에서 한 번 호출해 AudioContext를 미리 resume해둔다.

let audioCtx = null
let oscillator = null
let gainNode = null
let sirenTimer = null

function ensureContext() {
  if (audioCtx) return audioCtx
  const AudioContextClass = window.AudioContext || window.webkitAudioContext
  if (!AudioContextClass) return null
  audioCtx = new AudioContextClass()
  return audioCtx
}

export function unlockAlarmAudio() {
  const ctx = ensureContext()
  if (ctx && ctx.state === 'suspended') {
    ctx.resume().catch(() => {})
  }
}

export function startAlarm() {
  const ctx = ensureContext()
  if (!ctx || oscillator) return
  if (ctx.state === 'suspended') ctx.resume().catch(() => {})

  oscillator = ctx.createOscillator()
  gainNode = ctx.createGain()
  oscillator.type = 'sine'
  gainNode.gain.value = 0
  oscillator.connect(gainNode)
  gainNode.connect(ctx.destination)
  oscillator.start()

  let toneHigh = true
  const tick = () => {
    if (!oscillator) return
    const now = ctx.currentTime
    oscillator.frequency.setTargetAtTime(toneHigh ? 880 : 660, now, 0.05)
    gainNode.gain.setTargetAtTime(0.12, now, 0.05)
    toneHigh = !toneHigh
  }
  tick()
  sirenTimer = setInterval(tick, 500)
}

export function stopAlarm() {
  if (sirenTimer) {
    clearInterval(sirenTimer)
    sirenTimer = null
  }
  if (oscillator) {
    const ctx = audioCtx
    const now = ctx.currentTime
    gainNode.gain.setTargetAtTime(0, now, 0.05)
    oscillator.stop(now + 0.2)
    oscillator = null
    gainNode = null
  }
}
