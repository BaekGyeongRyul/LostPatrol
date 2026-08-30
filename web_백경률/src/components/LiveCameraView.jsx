import { useEffect, useState } from 'react'
import { Camera, CctvOff } from 'lucide-react'

// streamUrl이 설정돼있어도, 실제로 그 주소에 스트리밍 서버(stream_server.py)가
// 떠있는지는 별개다 — 예전엔 streamUrl 문자열이 있으면(설정만 돼있으면) 무조건
// "ONLINE"으로 표시해서, 서버가 꺼져있어도 웹에서는 계속 온라인으로 나오는
// 문제가 있었다(2026.08.30). <img> 태그의 onLoad/onError를 직접 감지해서
// 실제로 화면이 뜨는지 확인하고, 그 결과를 onStatusChange로 부모(LivePatrol)에
// 알려줘서 Patrol Status의 Camera 상태 표시도 같이 정확해지게 한다.
export default function LiveCameraView({ streamUrl, onStatusChange }) {
  const [loadFailed, setLoadFailed] = useState(false)

  useEffect(() => {
    setLoadFailed(false)  // 주소가 바뀌면 다시 시도해볼 수 있게 초기화
    if (!streamUrl) onStatusChange?.(false)
  }, [streamUrl, onStatusChange])

  const online = Boolean(streamUrl) && !loadFailed

  if (online) {
    return (
      <div className="live-camera live-camera--active">
        <img
          src={streamUrl}
          alt="로봇 실시간 카메라 화면"
          onLoad={() => onStatusChange?.(true)}
          onError={() => {
            setLoadFailed(true)
            onStatusChange?.(false)
          }}
        />
      </div>
    )
  }

  return (
    <div className="live-camera">
      <span className="live-camera__badge">
        <CctvOff size={13} />
        CAMERA OFFLINE
      </span>
      <Camera size={40} strokeWidth={1.4} />
      <p className="live-camera__title">실시간 화면 송출 예정</p>
      <p className="live-camera__hint">Razbot 카메라 연결 후 실시간 순찰 화면이 표시됩니다.</p>
    </div>
  )
}
