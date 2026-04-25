import KpiStrip from "../components/KpiStrip";
import CompositeHistory from "../charts/CompositeHistory";

export default function History() {
  return (
    <div>
      <KpiStrip />
      <CompositeHistory />
      <div className="chart-card">
        <h2>Three-lens decomposition</h2>
        <p className="muted">Coming soon — small-multiples of affordability, P/I, and P/R z-scores.</p>
      </div>
      <div className="chart-card">
        <h2>Distribution / percentile strip</h2>
        <p className="muted">Coming soon — histogram of monthly composite readings since 1980.</p>
      </div>
      <div className="chart-card">
        <h2>Regime comparison</h2>
        <p className="muted">Coming soon — side-by-side cards for 1980, 2006, 2012, current.</p>
      </div>
    </div>
  );
}
