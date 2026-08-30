// 데모 모드에서 외부 네트워크 없이도 항상 표시되는 자리표시 이미지를 SVG data URI로 생성한다.
const TYPE_ICON = {
  backpack: 'M9 8V6a3 3 0 0 1 6 0v2M7 8h10l1 12a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L7 8Z',
  handbag: 'M9 8V6a3 3 0 0 1 6 0v2M6 8h12l-1 12a2 2 0 0 1-2 2H9a2 2 0 0 1-2-2L6 8Z',
  suitcase: 'M4 8h16v11a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V8Zm4 0V6a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2',
  wallet: 'M21 12V7H5a2 2 0 0 1 0-4h14v4M3 5v14a2 2 0 0 0 2 2h16v-5M18 12a2 2 0 0 0 0 4h4v-4Z',
  bottle: 'M10 2h4v4l2 3v11a2 2 0 0 1-2 2h-4a2 2 0 0 1-2-2V9l2-3V2Z',
  unknown: 'M12 17h.01M9.5 9a2.5 2.5 0 1 1 3.4 2.3c-.8.3-1.4 1-1.4 1.9v.3',
}

const TYPE_COLOR = {
  backpack: '#2563eb',
  handbag: '#7c3aed',
  suitcase: '#0f766e',
  wallet: '#334155',
  bottle: '#0891b2',
  unknown: '#64748b',
}

export function mockPhotoFor(itemType) {
  const icon = TYPE_ICON[itemType] ?? TYPE_ICON.unknown
  const color = TYPE_COLOR[itemType] ?? TYPE_COLOR.unknown
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="640" height="480" viewBox="0 0 640 480">
    <defs>
      <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stop-color="${color}" stop-opacity="0.16"/>
        <stop offset="1" stop-color="${color}" stop-opacity="0.32"/>
      </linearGradient>
    </defs>
    <rect width="640" height="480" fill="url(#g)"/>
    <g transform="translate(272,168)" stroke="${color}" stroke-width="2.5" fill="none" stroke-linecap="round" stroke-linejoin="round">
      <path transform="scale(4)" d="${icon}"/>
    </g>
    <text x="320" y="420" text-anchor="middle" font-family="Inter, sans-serif" font-size="15" fill="${color}" opacity="0.75">DEMO IMAGE — vision preview</text>
  </svg>`
  return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`
}
