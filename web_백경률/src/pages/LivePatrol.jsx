import { useState } from 'react'
import LiveCameraView from '../components/LiveCameraView'
import SafetyCard from '../components/SafetyCard'
import RobotStatusPill from '../components/RobotStatusPill'
import EmptyState from '../components/EmptyState'
import LoadingState from '../components/LoadingState'
import PageHeader from '../components/PageHeader'
import { useRobotStatus } from '../hooks/useRobotStatus'
import { useSafetyStatus } from '../hooks/useSafetyStatus'
import { usePatrolEvents } from '../hooks/usePatrolEvents'
import { useCameraFeed } from '../hooks/useCameraFeed'
import { SEVERITY_TONE } from '../lib/severity'
import { formatDateTime, formatEventTime } from '../lib/time'

export default function LivePatrol() {
  const { status, offline, loading: robotLoading } = useRobotStatus()
  const { safety } = useSafetyStatus()
  const { events } = usePatrolEvents({ limit: 8 })
  const { feed } = useCameraFeed()

  // streamUrl 문자열이 설정돼있는지만 보면(예전 방식) 서버가 꺼져있어도
  // 항상 ONLINE으로 나와서(2026.08.30), LiveCameraView가 실제 이미지
  // 로드 성공/실패를 감지한 결과를 여기로 받아서 정확하게 표시한다.
  const [cameraOnline, setCameraOnline] = useState(false)
  const zone = feed?.zone ?? '—'

  const fireLabel = !safety ? '—' : safety.fire.severity === 'normal' ? 'NORMAL' : 'FIRE WARNING'
  const motionLabel = !safety ? '—' : safety.motion.personDetected ? 'PERSON DETECTED' : 'NO MOTION'
  const soundLabel = !safety ? '—' : safety.sound.level === 'high' ? 'LOUD SOUND DETECTED' : 'NORMAL'

  return (
    <div className="page">
      <PageHeader title="실시간 순찰" subtitle="Live Patrol Monitoring" />

      <section className="panel">
        <div className="panel__header">
          <h2>Live Camera</h2>
        </div>
        <LiveCameraView streamUrl={feed?.cameraStreamUrl} onStatusChange={setCameraOnline} />
      </section>

      <section className="panel">
        <div className="panel__header">
          <h2>Safety Monitoring</h2>
        </div>

        {!safety ? (
          <LoadingState label="센서 상태를 불러오는 중…" />
        ) : (
          <div className="safety-grid">
            <SafetyCard
              icon="🔥"
              title="화재 위험"
              severity={safety.fire.severity}
              statusLabel={fireLabel}
              details={[
                `Flame: ${safety.fire.flameDetected ? 'Detected' : 'Not Detected'}`,
                `Temperature: ${safety.fire.temperatureC.toFixed(1)}°C`,
              ]}
            />
            <SafetyCard
              icon="👤"
              title="움직임 감지"
              severity={safety.motion.severity}
              statusLabel={motionLabel}
            />
            <SafetyCard
              icon="🔊"
              title="이상 고음량"
              severity={safety.sound.severity}
              statusLabel={soundLabel}
              details={[`Sound Level: ${safety.sound.level === 'high' ? 'High' : 'Low'}`]}
            />
          </div>
        )}
      </section>

      <section className="panel">
        <div className="panel__header">
          <h2>Patrol Status</h2>
        </div>
        <dl className="status-panel__grid">
          <div>
            <dt>Robot</dt>
            <dd>
              <RobotStatusPill status={status} offline={offline} loading={robotLoading} />
            </dd>
          </div>
          <div>
            <dt>Camera</dt>
            <dd>
              <span className={`robot-pill ${cameraOnline ? 'robot-pill--online' : 'robot-pill--offline'}`}>
                <span className="robot-pill__dot" />
                {cameraOnline ? 'ONLINE' : 'OFFLINE'}
              </span>
            </dd>
          </div>
          <div>
            <dt>Current Zone</dt>
            <dd>{zone}</dd>
          </div>
          <div>
            <dt>Last Update</dt>
            <dd>{status?.updated_at ? formatDateTime(status.updated_at) : '—'}</dd>
          </div>
        </dl>
      </section>

      <section className="panel">
        <div className="panel__header">
          <h2>최근 순찰 이벤트</h2>
        </div>
        {events.length === 0 ? (
          <EmptyState title="아직 기록된 순찰 이벤트가 없습니다" />
        ) : (
          <ul className="activity-list">
            {events.map((event) => (
              <li key={event.id}>
                <span className="activity-list__time">{formatEventTime(event.created_at)}</span>
                <span className="activity-list__command">
                  {event.location} · {event.message}
                </span>
                <span className={`badge badge--${SEVERITY_TONE[event.severity]}`}>
                  {event.severity.toUpperCase()}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}
