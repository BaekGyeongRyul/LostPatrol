import { useCallback, useState } from 'react'
import { Camera, Keyboard, MousePointerClick, PlayCircle, StopCircle, WifiOff } from 'lucide-react'
import VehicleController from '../components/VehicleController'
import PageHeader from '../components/PageHeader'
import RobotStatusPill from '../components/RobotStatusPill'
import { useRobotStatus } from '../hooks/useRobotStatus'
import { useKeyboardRobotControl } from '../hooks/useKeyboardRobotControl'
import { sendRobotCommand } from '../lib/api'
import { useToast } from '../hooks/useToast'
import { formatDateTime } from '../lib/time'

const CAPTURE_FLASH_MS = 220

export default function RobotControl() {
  const { status, offline, loading, refetch } = useRobotStatus()
  const showToast = useToast()
  const [pendingCommand, setPendingCommand] = useState(null)
  const [activeCommand, setActiveCommand] = useState(null)
  const [patrolRunning, setPatrolRunning] = useState(false)
  const [captureFlash, setCaptureFlash] = useState(false)

  const controlsDisabled = offline || pendingCommand !== null || patrolRunning

  const runCommand = useCallback(
    async (command, { silent = false } = {}) => {
      setPendingCommand(command)
      try {
        await sendRobotCommand(command)
        if (!silent) showToast('명령을 전송했습니다.', { tone: 'success' })
        refetch()
      } catch (err) {
        showToast(err.message ?? '명령 전송에 실패했습니다.', { tone: 'error' })
      } finally {
        setPendingCommand(null)
      }
    },
    [refetch, showToast],
  )

  // 키보드(↑ ↓ ← → · Space)도 화면 버튼과 완전히 동일한 runCommand → sendRobotCommand
  // 파이프라인을 사용한다. 키를 누르는 동안(activeCommand)에는 즉시 pressed 시각 피드백을 주고,
  // 실제 명령 전송 자체는 기존 mouse click 경로와 동일하게 처리된다.
  const handleKeyPress = useCallback(
    (command) => {
      setActiveCommand(command)
      runCommand(command)
    },
    [runCommand],
  )

  const handleKeyRelease = useCallback((command) => {
    setActiveCommand((current) => (current === command ? null : current))
  }, [])

  useKeyboardRobotControl({
    enabled: !controlsDisabled,
    onPress: handleKeyPress,
    onRelease: handleKeyRelease,
  })

  const pressedCommand = activeCommand ?? pendingCommand

  const handleCapture = () => {
    runCommand('capture')
    setCaptureFlash(true)
    setTimeout(() => setCaptureFlash(false), CAPTURE_FLASH_MS)
  }

  const handlePatrolStart = async () => {
    if (patrolRunning || offline) return
    setPatrolRunning(true)
    await runCommand('patrol_start', { silent: true })
    showToast('라인 트레이싱 자동순찰을 시작합니다.')
  }

  const handlePatrolStop = async () => {
    setPatrolRunning(false)
    await runCommand('patrol_stop', { silent: true })
    showToast('자동순찰을 종료했습니다.', { tone: 'default' })
  }

  return (
    <div className="page">
      <PageHeader title="Robot Control" subtitle="수동 방향 제어 · 촬영 · 자동 순찰 명령" />

      {offline && (
        <div className="offline-banner">
          <WifiOff size={16} />
          로봇이 오프라인 상태입니다. 명령이 전달되지 않을 수 있습니다.
        </div>
      )}

      <div className="control-hint-bar">
        <div className="control-hint">
          <Keyboard size={14} />
          <code>↑ ↓ ← →</code> 이동 · <code>SPACE</code> 정지
          <span className="badge badge--neutral control-hint__tag">PC 권장</span>
        </div>
        <div className="control-hint">
          <MousePointerClick size={14} />
          마우스 클릭 · 터치로 제어 가능
          <span className="badge badge--neutral control-hint__tag">모바일 권장</span>
        </div>
      </div>

      <VehicleController onCommand={runCommand} disabled={controlsDisabled} pressedCommand={pressedCommand} />

      <div className="action-bar">
        <button
          type="button"
          className={`btn btn--capture btn--lg${captureFlash ? ' is-flashing' : ''}`}
          disabled={controlsDisabled}
          onClick={handleCapture}
        >
          <Camera size={20} />
          CAPTURE
        </button>

        <div className="action-bar__patrol">
          <button type="button" className="btn btn--patrol-start" disabled={offline || patrolRunning} onClick={handlePatrolStart}>
            <PlayCircle size={18} />
            PATROL START
          </button>
          <button type="button" className="btn btn--patrol-stop" disabled={!patrolRunning} onClick={handlePatrolStop}>
            <StopCircle size={18} />
            PATROL STOP
          </button>
        </div>
      </div>

      <div className="control-status-strip">
        <RobotStatusPill status={status} offline={offline} loading={loading} />
        <span className="control-status-strip__item">
          Last Command: <strong>{status?.last_command ?? '—'}</strong>
        </span>
        <span className="control-status-strip__item">
          Last Update: <strong>{status?.updated_at ? formatDateTime(status.updated_at) : '—'}</strong>
        </span>
        <span className="control-status-strip__hint">
          robot_status.updated_at이 15초 이상 갱신되지 않으면 자동으로 OFFLINE으로 표시됩니다.
        </span>
      </div>
    </div>
  )
}
