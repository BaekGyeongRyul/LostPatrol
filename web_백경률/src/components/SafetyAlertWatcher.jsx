import { useEffect, useRef, useState } from 'react'
import { Flame, Volume2, VolumeX } from 'lucide-react'
import { useSafetyStatus } from '../hooks/useSafetyStatus'
import { useToast } from '../hooks/useToast'
import { unlockAlarmAudio, startAlarm, stopAlarm } from '../lib/alarmSound'

const LOUD_SOUND_MESSAGE = '🔊 이상 고음량 감지 — 주변에서 비정상적으로 큰 소리가 감지되었습니다.'

// safety_status를 어느 페이지에 있든 공통으로 감시해서, 화재는 전체 화면 경보(Overlay + 사이렌),
// 이상 고음량은 Toast 팝업으로 알린다. AppShell에 한 번만 마운트되므로 alert state는 항상 하나만 존재한다.
export default function SafetyAlertWatcher() {
  const { safety } = useSafetyStatus()
  const showToast = useToast()
  const [soundMuted, setSoundMuted] = useState(false)
  const prevFireActiveRef = useRef(false)
  const prevSoundHighRef = useRef(false)

  const fireActive = Boolean(safety && (safety.fire.flameDetected || safety.fire.severity === 'danger'))
  const soundHigh = Boolean(safety && safety.sound.level === 'high')

  // 로봇 조작 키보드 입력을 가로채지 않는 별도 리스너로, 첫 클릭/키 입력 시 한 번만 AudioContext를 활성화한다.
  useEffect(() => {
    const unlock = () => unlockAlarmAudio()
    window.addEventListener('pointerdown', unlock, { once: true, passive: true })
    window.addEventListener('keydown', unlock, { once: true, passive: true })
    return () => {
      window.removeEventListener('pointerdown', unlock)
      window.removeEventListener('keydown', unlock)
    }
  }, [])

  // 새 화재 상황이 시작될 때마다 이전에 꺼둔 경보음을 다시 켜지도록 초기화한다.
  useEffect(() => {
    if (fireActive && !prevFireActiveRef.current) {
      setSoundMuted(false)
    }
    prevFireActiveRef.current = fireActive
  }, [fireActive])

  useEffect(() => {
    if (fireActive && !soundMuted) {
      startAlarm()
    } else {
      stopAlarm()
    }
  }, [fireActive, soundMuted])

  useEffect(() => () => stopAlarm(), [])

  useEffect(() => {
    if (soundHigh && !prevSoundHighRef.current) {
      showToast(LOUD_SOUND_MESSAGE, { tone: 'warning', duration: 5000 })
    }
    prevSoundHighRef.current = soundHigh
  }, [soundHigh, showToast])

  if (!fireActive) return null

  return (
    <div className="fire-alert-overlay" role="alert" aria-live="assertive">
      <div className="fire-alert-overlay__message">
        <Flame size={26} strokeWidth={2} />
        <div className="fire-alert-overlay__text">
          <p className="fire-alert-overlay__title">🔥 화재 위험 감지</p>
          <p className="fire-alert-overlay__subtitle">화재 위험이 감지되었습니다. 즉시 확인해주세요.</p>
        </div>
        <button type="button" className="fire-alert-overlay__mute" onClick={() => setSoundMuted((m) => !m)}>
          {soundMuted ? <VolumeX size={14} /> : <Volume2 size={14} />}
          {soundMuted ? '경보음 꺼짐' : '경보음 끄기'}
        </button>
      </div>
    </div>
  )
}
