import SensitivityHeatmap from "../charts/SensitivityHeatmap";
import SensitivityTornado from "../charts/SensitivityTornado";

export default function Sensitivity() {
  return (
    <div className="layout-2col">
      <aside>
        <div className="chart-card">
          <h2>Inputs</h2>
          <p className="muted">Sliders coming soon — charts below use defaults from the latest monthly_fact row.</p>
        </div>
      </aside>
      <section>
        <SensitivityHeatmap />
        <SensitivityTornado />
        <div className="chart-card">
          <h2>Breakpoints / years-to-FV / Monte Carlo</h2>
          <p className="muted">Wired in subsequent phases. API endpoints already exist.</p>
        </div>
      </section>
    </div>
  );
}
