// Robot Control / 실시간 순찰 / Lost Items 등 "서비스 섹션" 페이지 상단에 공통으로 쓰는
// 큰 타이틀 + 설명 헤더. Dashboard의 Hero(더 크고 CTA가 있는 랜딩형 헤더)와는 별개다.
export default function PageHeader({ title, subtitle, actions }) {
  return (
    <div className="page-hero">
      <div className="page-hero__text">
        <h1 className="page-hero__title">{title}</h1>
        {subtitle && <p className="page-hero__subtitle">{subtitle}</p>}
      </div>
      {actions && <div className="page-hero__actions">{actions}</div>}
    </div>
  )
}
