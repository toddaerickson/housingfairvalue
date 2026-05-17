import KpiStrip from "../components/KpiStrip";
import RegimeCards from "../components/RegimeCards";
import CompositeHistory from "../charts/CompositeHistory";
import CompositeDistribution from "../charts/CompositeDistribution";
import LensDecomposition from "../charts/LensDecomposition";

export default function History() {
  return (
    <div>
      <KpiStrip />
      <CompositeHistory />
      <LensDecomposition />
      <CompositeDistribution />
      <RegimeCards />
    </div>
  );
}
