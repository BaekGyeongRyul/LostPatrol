import { ArrowUp, ArrowDown, RotateCcw, RotateCw, Octagon } from 'lucide-react'

// 자동차를 위에서 내려다보는 형태의 generic한 실루엣이다.
// 특정 브랜드 차량 디자인을 참고하지 않은 단순 도형(둥근 사각형 차체 + 앞/뒤 유리 + 바퀴)으로만 구성했다.
function CarGraphic() {
  return (
    <svg viewBox="0 0 160 280" className="car-graphic" aria-hidden="true" focusable="false">
      <rect x="24" y="16" width="112" height="248" rx="42" className="car-graphic__body" />
      <path d="M40 62 h80 l-9 34 h-62 z" className="car-graphic__glass" />
      <path d="M40 218 h80 l-9 -34 h-62 z" className="car-graphic__glass" />
      <line x1="80" y1="108" x2="80" y2="172" className="car-graphic__line" />
      <rect x="2" y="52" width="16" height="46" rx="8" className="car-graphic__wheel" />
      <rect x="142" y="52" width="16" height="46" rx="8" className="car-graphic__wheel" />
      <rect x="2" y="182" width="16" height="46" rx="8" className="car-graphic__wheel" />
      <rect x="142" y="182" width="16" height="46" rx="8" className="car-graphic__wheel" />
    </svg>
  )
}

// 자동차 모티브의 대형 인터랙티브 컨트롤러. onCommand/disabled/pressedCommand는
// 기존 DirectionPad와 동일한 계약을 유지해, RobotControl 페이지의 command 파이프라인
// (마우스 클릭·터치·키보드가 모두 같은 runCommand를 호출하는 구조)을 그대로 재사용한다.
export default function VehicleController({ onCommand, disabled, pressedCommand }) {
  const isPressed = (command) => pressedCommand === command

  return (
    <div className="vehicle-controller">
      <button
        type="button"
        className={`vehicle-zone vehicle-zone--forward${isPressed('forward') ? ' is-pressed' : ''}`}
        disabled={disabled}
        aria-busy={isPressed('forward')}
        onClick={() => onCommand('forward')}
      >
        <ArrowUp size={34} strokeWidth={2.4} />
        <span>FORWARD</span>
      </button>

      <div className="vehicle-controller__middle">
        <button
          type="button"
          className={`vehicle-zone vehicle-zone--side vehicle-zone--left${isPressed('left') ? ' is-pressed' : ''}`}
          disabled={disabled}
          aria-busy={isPressed('left')}
          onClick={() => onCommand('left')}
        >
          <RotateCcw size={28} strokeWidth={2.2} />
          <span>LEFT</span>
        </button>

        <div className="vehicle-controller__car">
          <CarGraphic />
          <button
            type="button"
            className={`vehicle-stop${isPressed('stop') ? ' is-pressed' : ''}`}
            disabled={disabled}
            aria-busy={isPressed('stop')}
            aria-label="정지"
            onClick={() => onCommand('stop')}
          >
            <Octagon size={24} strokeWidth={2.4} />
            <span>STOP</span>
          </button>
        </div>

        <button
          type="button"
          className={`vehicle-zone vehicle-zone--side vehicle-zone--right${isPressed('right') ? ' is-pressed' : ''}`}
          disabled={disabled}
          aria-busy={isPressed('right')}
          onClick={() => onCommand('right')}
        >
          <RotateCw size={28} strokeWidth={2.2} />
          <span>RIGHT</span>
        </button>
      </div>

      <button
        type="button"
        className={`vehicle-zone vehicle-zone--backward${isPressed('backward') ? ' is-pressed' : ''}`}
        disabled={disabled}
        aria-busy={isPressed('backward')}
        onClick={() => onCommand('backward')}
      >
        <span>BACKWARD</span>
        <ArrowDown size={34} strokeWidth={2.4} />
      </button>
    </div>
  )
}
