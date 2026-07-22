import type { MonthlyCost } from "../api/types";
import { money } from "../lib/format";

/** Lightweight dependency-free stacked-ish bar chart for monthly costs. */
export default function BarChart({ data, currency }: { data: MonthlyCost[]; currency: string }) {
  if (!data.length) {
    return <div className="empty">No cost data yet.</div>;
  }
  const max = Math.max(1, ...data.map((d) => Math.max(d.fuel, d.service)));
  const recent = data.slice(-12);

  return (
    <div>
      <div className="chart">
        {recent.map((d) => (
          <div className="col" key={d.month} title={`${d.month}: ${money(d.total, currency)}`}>
            <div className="bars">
              <div
                className="bar fuel"
                style={{ height: `${(d.fuel / max) * 100}%` }}
                title={`Fuel ${money(d.fuel, currency)}`}
              />
              <div
                className="bar service"
                style={{ height: `${(d.service / max) * 100}%` }}
                title={`Service ${money(d.service, currency)}`}
              />
            </div>
            <div className="xlabel">{d.month.slice(2)}</div>
          </div>
        ))}
      </div>
      <div className="legend">
        <span>
          <span className="dot" style={{ background: "var(--primary)" }} />
          Fuel
        </span>
        <span>
          <span className="dot" style={{ background: "#f59e0b" }} />
          Service
        </span>
      </div>
    </div>
  );
}
