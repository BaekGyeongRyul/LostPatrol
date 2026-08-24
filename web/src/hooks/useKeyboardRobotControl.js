import { useEffect, useRef } from 'react'

// 화면 버튼과 완전히 동일한 command 값으로 매핑한다 — 키보드 전용 별도 명령을 만들지 않는다.
const KEY_COMMAND_MAP = {
  ArrowUp: 'forward',
  ArrowDown: 'backward',
  ArrowLeft: 'left',
  ArrowRight: 'right',
  ' ': 'stop',
  Spacebar: 'stop',
}

function isTypingTarget(target) {
  if (!target) return false
  const tag = target.tagName
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return true
  return Boolean(target.isContentEditable)
}

// PC 사용자를 위한 방향키 + Space 로봇 조작. 화면 버튼이 호출하는 것과 동일한
// onPress(command) 콜백을 그대로 사용하므로 명령 전송 파이프라인은 완전히 공유된다.
export function useKeyboardRobotControl({ enabled, onPress, onRelease }) {
  const pressedKeysRef = useRef(new Set())
  const onPressRef = useRef(onPress)
  const onReleaseRef = useRef(onRelease)

  useEffect(() => {
    onPressRef.current = onPress
    onReleaseRef.current = onRelease
  }, [onPress, onRelease])

  useEffect(() => {
    if (!enabled) return undefined

    const handleKeyDown = (event) => {
      const command = KEY_COMMAND_MAP[event.key]
      if (!command) return
      if (isTypingTarget(event.target)) return

      // 방향키/Space로 페이지가 스크롤되는 기본 동작을 막는다.
      event.preventDefault()

      // OS의 키 반복(auto-repeat)으로 동일 명령이 계속 재전송되는 것을 막는다.
      if (event.repeat || pressedKeysRef.current.has(event.key)) return
      pressedKeysRef.current.add(event.key)

      onPressRef.current?.(command)
    }

    const handleKeyUp = (event) => {
      const command = KEY_COMMAND_MAP[event.key]
      if (!command) return
      pressedKeysRef.current.delete(event.key)
      onReleaseRef.current?.(command)
    }

    const handleBlur = () => {
      pressedKeysRef.current.clear()
    }

    window.addEventListener('keydown', handleKeyDown)
    window.addEventListener('keyup', handleKeyUp)
    window.addEventListener('blur', handleBlur)

    return () => {
      window.removeEventListener('keydown', handleKeyDown)
      window.removeEventListener('keyup', handleKeyUp)
      window.removeEventListener('blur', handleBlur)
      pressedKeysRef.current.clear()
    }
  }, [enabled])
}
