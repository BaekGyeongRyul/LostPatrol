import { createContext, useCallback, useContext, useRef, useState } from 'react'

const ToastContext = createContext(null)

let nextId = 1

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])
  const timeoutsRef = useRef(new Map())

  const dismiss = useCallback((id) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id))
    clearTimeout(timeoutsRef.current.get(id))
    timeoutsRef.current.delete(id)
  }, [])

  const showToast = useCallback(
    (message, { tone = 'default', duration = 3200 } = {}) => {
      const id = nextId++
      setToasts((prev) => [...prev, { id, message, tone }])
      const timeoutId = setTimeout(() => dismiss(id), duration)
      timeoutsRef.current.set(id, timeoutId)
    },
    [dismiss],
  )

  return (
    <ToastContext.Provider value={showToast}>
      {children}
      <div className="toast-stack" role="status" aria-live="polite">
        {toasts.map((toast) => (
          <div key={toast.id} className={`toast toast--${toast.tone}`}>
            {toast.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast() {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used within ToastProvider')
  return ctx
}
