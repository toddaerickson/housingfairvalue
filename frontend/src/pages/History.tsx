import KpiStrip from "../components/KpiStrip";
import RegimeCards from "../components/RegimeCards";
import CompositeHistory from "../charts/CompositeHistory";
import CompositeDistribution from "../charts/CompositeDistribution";

export default function History() {
  return (
    <div>
      <KpiStrip />
      <CompositeHistory />
      <CompositeDistribution />
      <RegimeCards />
      <div className="chart-card">
        <h2>Three-lens decomposition</h2>
        <p className="muted">Coming soon — small-multiples of affordability, P/I, and P/R z-scores.</p>
      </div>
    </div>
  );
}
