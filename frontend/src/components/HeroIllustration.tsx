export function HeroIllustration() {
  return (
    <div className="hero-illustration" aria-hidden="true">
      <div className="hero-wave hero-wave--one" />
      <div className="hero-wave hero-wave--two" />
      <div className="hero-star hero-star--one" />
      <div className="hero-star hero-star--two" />
      <div className="hero-star hero-star--three" />
      <div className="hero-card hero-card--left">
        <span className="hero-card__line" />
        <span className="hero-card__line hero-card__line--short" />
      </div>
      <div className="hero-card hero-card--right">
        <span className="hero-bulb" />
      </div>
      <div className="laptop">
        <div className="robot-head">
          <span className="robot-eye" />
          <span className="robot-eye" />
          <span className="robot-mouth" />
        </div>
        <div className="laptop-screen">
          <div className="screen-checklist">
            <span />
            <span />
            <span />
          </div>
          <div className="screen-chart">
            <div className="chart-bar chart-bar--1" />
            <div className="chart-bar chart-bar--2" />
            <div className="chart-bar chart-bar--3" />
            <div className="chart-bar chart-bar--4" />
            <div className="chart-bar chart-bar--5" />
          </div>
          <div className="screen-pie" />
        </div>
        <div className="laptop-base" />
      </div>
    </div>
  );
}
