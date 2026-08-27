import { useEffect, useRef, useState } from 'react'
import { CheckCircle2, Flame, Volume2, VolumeX } from 'lucide-react'
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
  // 사용자가 "화재진압완료"로 이번 화재 이벤트를 직접 확인/해제했는지 여부.
  // Supabase safety_status는 절대 건드리지 않는, 순수 UI 상태(session-only, 새로고침 시 초기화됨).
  const [fireAcknowledged, setFireAcknowledged] = useState(false)
  const prevFireActiveRef = useRef(false)
  const prevSoundHighRef = useRef(false)

  const fireActive = Boolean(safety && (safety.fire.flameDetected || safety.fire.severity === 'danger'))
  const soundHigh = Boolean(safety && safety.sound.level === 'high')
  // 실제로 큰 경보(Overlay + 배너 + 사이렌)를 띄울지 여부. 센서는 여전히 fire=true여도
  // 사용자가 진압완료 처리했다면 더 이상 침해적인 경보를 다시 띄우지 않는다.
  const showFireAlert = fireActive && !fireAcknowledged

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

  // 센서가 실제로 normal로 돌아오면 다음 화재를 다시 정상적으로 감지할 수 있도록
  // 이번 이벤트에 대한 진압완료 처리 상태를 초기화한다.
  useEffect(() => {
    if (!fireActive) {
      setFireAcknowledged(false)
    }
  }, [fireActive])

  useEffect(() => {
    if (showFireAlert && !soundMuted) {
      startAlarm()
    } else {
      stopAlarm()
    }
  }, [showFireAlert, soundMuted])

  useEffect(() => () => stopAlarm(), [])

  useEffect(() => {
    if (soundHigh && !prevSoundHighRef.current) {
      showToast(LOUD_SOUND_MESSAGE, { tone: 'warning', duration: 5000 })
    }
    prevSoundHighRef.current = soundHigh
  }, [soundHigh, showToast])

  if (!fireActive) return null

  if (!showFireAlert) {
    // 센서는 아직 fire=true지만 사용자가 진압완료를 확인한 상태 — 침해적이지 않은 작은 배너만.
    return (
      <div className="fire-ack-banner" role="status">
        <CheckCircle2 size={14} />
        화재진압완료 처리됨 — 센서 상태를 확인 중입니다.
      </div>
    )
  }

  return (
    <div className="fire-alert-overlay" role="alert" aria-live="assertive">
      <div className="fire-alert-overlay__message">
        <Flame size={26} strokeWidth={2} />
        <div className="fire-alert-overlay__text">
          <p className="fire-alert-overlay__title">🔥 화재 위험 감지</p>
          <p className="fire-alert-overlay__subtitle">화재 위험이 감지되었습니다. 즉시 확인해주세요.</p>
        </div>
        <div className="fire-alert-overlay__actions">
          <button type="button" className="fire-alert-overlay__mute" onClick={() => setSoundMuted((m) => !m)}>
            {soundMuted ? <VolumeX size={14} /> : <Volume2 size={14} />}
            {soundMuted ? '경보음 꺼짐' : '경보음 끄기'}
          </button>
          <button type="button" className="fire-alert-overlay__ack" onClick={() => setFireAcknowledged(true)}>
            <CheckCircle2 size={14} />
            화재진압완료
          </button>
        </div>
      </div>
    </div>
  )
}
