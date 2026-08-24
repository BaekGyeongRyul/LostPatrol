import { Camera, CctvOff } from 'lucide-react'

// streamUrl이 준비되면(Razbot 카메라 스트리밍 주소 또는 스냅샷 이미지 URL) 그대로 표시하고,
// 없으면 실제 카메라가 연결된 것처럼 꾸미지 않고 명확한 오프라인 플레이스홀더를 보여준다.
export default function LiveCameraView({ streamUrl }) {
  if (streamUrl) {
    return (
      <div className="live-camera live-camera--active">
        <img src={streamUrl} alt="로봇 실시간 카메라 화면" />
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
