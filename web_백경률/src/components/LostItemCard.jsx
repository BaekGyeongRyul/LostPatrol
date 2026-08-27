import { Link } from 'react-router-dom'
import { MapPin, Clock } from 'lucide-react'
import StatusBadge from './StatusBadge'
import { formatItemType } from '../lib/statusMap'
import { mockPhotoFor } from '../data/mockImage'
import { formatRelativeTime } from '../lib/time'

export default function LostItemCard({ item }) {
  const photo = item.image_url ?? mockPhotoFor(item.item_type)

  return (
    <Link to={`/lost-items/${item.id}`} className="item-card">
      <div className="item-card__photo">
        <img src={photo} alt={formatItemType(item.item_type)} loading="lazy" />
      </div>
      <div className="item-card__body">
        <div className="item-card__top">
          <h3>{formatItemType(item.item_type)}</h3>
          <StatusBadge status={item.status} />
        </div>
        <div className="item-card__meta">
          <span>
            <MapPin size={13} /> {item.location ?? '위치 미확인'}
          </span>
          <span>
            <Clock size={13} /> {formatRelativeTime(item.detected_at)}
          </span>
        </div>
      </div>
    </Link>
  )
}
