import KpiStrip from "../components/KpiStrip";
import CompositeHistory from "../charts/CompositeHistory";
import CompositeDistribution from "../charts/CompositeDistribution";

export default function History() {
  return (
    <div>
      <KpiStrip />
      <CompositeHistory />
      <CompositeDistribution />
      <div className="chart-card">
        <h2>Three-lens decomposition</h2>
        <p className="muted">Coming soon — small-multiples of affordability, P/I, and P/R z-scores.</p>
      </div>
      <div className="chart-card">
        <h2>Regime comparison</h2>
        <p className="muted">Coming soon — side-by-side cards for 1980, 2006, 2012, current.</p>
      </div>
    </div>
  );
}
