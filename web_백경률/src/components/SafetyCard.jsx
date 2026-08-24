import { SEVERITY_TONE } from '../lib/severity'

export default function SafetyCard({ icon, title, severity, statusLabel, details = [] }) {
  const tone = SEVERITY_TONE[severity] ?? 'neutral'

  return (
    <div className={`safety-card safety-card--${tone}`}>
      <div className="safety-card__head">
        <span className="safety-card__icon" aria-hidden="true">
          {icon}
        </span>
        <span>{title}</span>
      </div>
      <p className="safety-card__status">{statusLabel}</p>
      {details.map((line) => (
        <p key={line} className="safety-card__detail">
          {line}
        </p>
      ))}
    </div>
  )
}
