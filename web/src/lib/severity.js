// 안전 감지(화재/움직임/소음) 및 순찰 이벤트에서 공통으로 쓰는 심각도 등급.
// 실제 센서가 연결되면 warning/danger 값도 그대로 사용할 수 있도록 3단계로 정의한다.
export const SEVERITY = {
  NORMAL: 'normal',
  WARNING: 'warning',
  DANGER: 'danger',
}

// StatusBadge 등에서 이미 쓰는 tone 팔레트(green/amber/red)를 그대로 재사용한다.
export const SEVERITY_TONE = {
  [SEVERITY.NORMAL]: 'green',
  [SEVERITY.WARNING]: 'amber',
  [SEVERITY.DANGER]: 'red',
}

export const SEVERITY_LABEL = {
  [SEVERITY.NORMAL]: 'NORMAL',
  [SEVERITY.WARNING]: 'WARNING',
  [SEVERITY.DANGER]: 'DANGER',
}
