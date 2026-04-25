export default function Methodology() {
  return (
    <div className="chart-card" style={{ maxWidth: 760 }}>
      <h2>Methodology</h2>
      <h3>Composite signal</h3>
      <p>
        Equal-weighted z-score blend of three lenses: payment-affordability
        (PITI / monthly income), price-to-income, price-to-rent. Each lens is
        z-scored against its 1980→present mean and standard deviation. The
        composite z is mapped to an overvaluation % via a calibrated
        std-to-pct factor and to a percentile rank via the empirical CDF over
        the same window.
      </p>

      <h3>Equal weighting is an assumption</h3>
      <p>
        Default weights are 1/3 each. The advanced toggle allows reweighting
        with a sum-to-one constraint. Different weightings can shift the
        headline reading materially and reflect a user's view on which lens
        best captures fair value.
      </p>

      <h3>Pre-1984 income stitch</h3>
      <p>
        FRED's median household income series (MEHOINUSA646N) starts in 1984.
        For the 1980-1983 window we backfill with real disposable personal
        income per capita (A229RX0), scaled to dollar-match the household
        income series at the January 1984 splice point. This is a stitch, not
        a reconstruction — the level is right but the methodology shift can
        introduce small distortions in pre-1984 readings.
      </p>

      <h3>Resampling</h3>
      <p>
        Monthly is the canonical grid. Quarterly (median price) and annual
        (income) series are forward-filled within their reporting period; we
        do not linearly interpolate within periods because that creates false
        intra-period precision.
      </p>

      <h3>Data sources</h3>
      <ul>
        <li>FRED — all macro and price series</li>
        <li>NBER — recession dates (overlay only)</li>
      </ul>

      <h3>Validation gate</h3>
      <p>
        CI requires the composite to reproduce the 2026 source workbook's 2024
        reading (within 1pp on overvaluation, 2pp on percentile rank) and
        match three historical inflection points (1980 trough, 2006 peak,
        2012 trough) within 2pp each.
      </p>
    </div>
  );
}
