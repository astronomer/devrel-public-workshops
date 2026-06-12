const { useState, useEffect, useCallback, useMemo } = React;

const API = "api";

async function fetchJSON(path) {
  const res = await fetch(`${API}/${path}`);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

// ---------------------------------------------------------------------------
// Icons (inline SVG components)
// ---------------------------------------------------------------------------

function IconFlask() {
  return (
    <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 3h6M12 3v7l-5 8.5a2 2 0 001.7 3h6.6a2 2 0 001.7-3L12 10V3"/>
    </svg>
  );
}

function IconChart() {
  return (
    <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 3v18h18"/><path d="M7 16l4-8 4 4 4-6"/>
    </svg>
  );
}

function IconBox() {
  return (
    <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z"/>
      <polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/>
    </svg>
  );
}

function IconImage() {
  return (
    <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/>
      <polyline points="21 15 16 10 5 21"/>
    </svg>
  );
}

function IconRefresh() {
  return (
    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 11-2.12-9.36L23 10"/>
    </svg>
  );
}

function IconTrendUp() {
  return (
    <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/>
    </svg>
  );
}

function IconCompare() {
  return (
    <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="7" height="18" rx="1"/><rect x="14" y="3" width="7" height="18" rx="1"/>
      <path d="M10 8h4M10 12h4M10 16h4"/>
    </svg>
  );
}

function IconSun() {
  return (
    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/>
      <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
      <line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/>
      <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
    </svg>
  );
}

function IconMoon() {
  return (
    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"/>
    </svg>
  );
}

// ---------------------------------------------------------------------------
// Stage / Status badges
// ---------------------------------------------------------------------------

function StageBadge({ stage }) {
  const colors = {
    development: "bg-gold-40/15 text-gold-40 border-gold-40/30",
    staging: "bg-bBlue-50/15 text-bBlue-50 border-bBlue-50/30",
    production: "bg-bGreen-50/15 text-bGreen-50 border-bGreen-50/30",
    archived: "bg-th-border/20 text-th-secondary border-th-border/30",
  };
  return (
    <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium border ${colors[stage] || "bg-th-border/20 text-th-secondary border-th-border/30"}`}>
      {stage}
    </span>
  );
}

function StatusBadge({ status }) {
  const s = (status || "").toUpperCase();
  const colors = {
    COMPLETED: "bg-bGreen-50/15 text-bGreen-50",
    RUNNING: "bg-bBlue-50/15 text-bBlue-50",
    FAILED: "bg-bRed-50/15 text-bRed-50",
  };
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium ${colors[s] || "bg-th-border/20 text-th-secondary"}`}>
      {s}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Checkbox
// ---------------------------------------------------------------------------

function Checkbox({ checked, onChange }) {
  return (
    <button
      onClick={onChange}
      className={`w-4 h-4 rounded border flex-shrink-0 flex items-center justify-center transition-colors ${
        checked ? "bg-th-accent border-th-accent text-th-base" : "border-th-muted hover:border-th-secondary"
      }`}
    >
      {checked && (
        <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
          <polyline points="20 6 9 17 4 12"/>
        </svg>
      )}
    </button>
  );
}

// ---------------------------------------------------------------------------
// ML glossary
// ---------------------------------------------------------------------------

const ML_GLOSSARY = {
  rmse: "Root Mean Squared Error: prediction error in the same units as the target. Lower is better.",
  mae: "Mean Absolute Error: average distance between prediction and actual value. Lower is better.",
  mse: "Mean Squared Error: average of squared prediction errors. Lower is better.",
  r2: "R-squared: how much of the variation the model explains. 1.0 = perfect fit, 0 = no better than guessing the average.",
  r2_score: "R-squared: how much of the variation the model explains. 1.0 = perfect fit.",
  accuracy: "Fraction of predictions the model got right. 1.0 = every prediction correct.",
  precision: "Of everything the model flagged as positive, how many actually were. High precision = few false alarms.",
  recall: "Of all actual positives, how many the model found. High recall = few missed cases.",
  f1: "Harmonic mean of precision and recall; balances both into one number. 1.0 is perfect.",
  f1_score: "Harmonic mean of precision and recall; balances both into one number. 1.0 is perfect.",
  f1_weighted: "F1 score weighted by class frequency; accounts for class imbalance.",
  silhouette_score: "How well-separated clusters are. Ranges from −1 (wrong cluster) to 1 (perfectly separated).",
  inertia: "Sum of distances from each point to its cluster center. Lower = tighter, more compact clusters.",
  n_clusters: "Number of groups the algorithm divided the data into.",
  train_size: "Number of samples used to train the model.",
  test_size: "Fraction (or count) of data held back to evaluate the model; not seen during training.",
  learning_rate: "Step size for model weight updates. Smaller = slower training but often more precise.",
  max_depth: "Maximum levels in a decision tree. Deeper trees can memorize noise (overfit).",
  n_estimators: "Number of trees in the ensemble. More trees = more stable predictions but slower training.",
  colsample_bytree: "Fraction of features randomly sampled for each tree. Helps prevent overfitting.",
  random_state: "Random seed for reproducibility; same seed guarantees same results every run.",
  model_type: "The algorithm used for training (e.g., XGBoost, Random Forest, KMeans).",
  features: "Input variables (columns) the model uses to make predictions.",
  enriched: "Whether additional engineered features were added beyond the raw columns.",
};

function InfoTooltip({ text }) {
  const [pos, setPos] = useState(null);
  const ref = React.useRef(null);

  const handleEnter = () => {
    if (ref.current) {
      const rect = ref.current.getBoundingClientRect();
      let left = rect.left + rect.width / 2;
      let transformX = "-50%";
      if (left < 150) { left = rect.left; transformX = "0"; }
      else if (window.innerWidth - left < 150) { left = rect.right; transformX = "-100%"; }
      setPos({ top: rect.top - 8, left, transformX });
    }
  };

  return (
    <span
      ref={ref}
      className="relative inline-flex ml-1 align-middle"
      onMouseEnter={handleEnter}
      onMouseLeave={() => setPos(null)}
    >
      <svg className="w-3.5 h-3.5 text-th-muted hover:text-th-accent cursor-help transition-colors flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10"/>
        <line x1="12" y1="16" x2="12" y2="12"/>
        <line x1="12" y1="8" x2="12.01" y2="8"/>
      </svg>
      {pos && ReactDOM.createPortal(
        <span
          className="fixed px-3 py-2 rounded-lg bg-th-surface3 border border-th-border/30 text-th-body text-xs leading-relaxed max-w-[280px] w-max whitespace-normal z-[9999] shadow-xl shadow-black/30 pointer-events-none font-body font-normal"
          style={{ top: pos.top, left: pos.left, transform: `translate(${pos.transformX}, -100%)` }}
        >
          {text}
        </span>,
        document.body
      )}
    </span>
  );
}

function MetricLabel({ name }) {
  const key = (name || "").toLowerCase().replace(/[\s-]/g, "_");
  const tip = ML_GLOSSARY[key];
  return tip ? (
    <span className="inline-flex items-center gap-0">
      {name}
      <InfoTooltip text={tip} />
    </span>
  ) : <span>{name}</span>;
}

// ---------------------------------------------------------------------------
// Summary cards
// ---------------------------------------------------------------------------

function SummaryCard({ label, value, icon, color, onClick }) {
  const clickable = typeof onClick === "function";
  return (
    <div
      className={`bg-th-surface p-6 border border-th-border/20 fade-in transition-colors ${clickable ? "hover:border-th-accent/40 cursor-pointer" : ""}`}
      onClick={onClick}
    >
      <div className="flex items-center justify-between mb-3">
        <div className={`p-2.5 rounded-xl ${color}`}>{icon}</div>
      </div>
      <p className="text-3xl font-bold text-th-heading">{value}</p>
      <p className="text-xs text-th-secondary mt-1 font-mono uppercase tracking-wider">{label}</p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Param value formatting
// ---------------------------------------------------------------------------

// A feature->weight map (feature_importances for a forest, coefficients for a
// linear model) renders as its top features by magnitude, not "[object Object]".
function topFeatures(obj, n = 3) {
  return Object.entries(obj)
    .filter(([, v]) => typeof v === "number")
    .sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))
    .slice(0, n)
    .map(([name, v]) => `${name} ${v.toFixed(3)}`)
    .join(", ");
}

function formatParamValue(v) {
  if (Array.isArray(v)) return v.join(", ");
  if (v && typeof v === "object") return topFeatures(v) || JSON.stringify(v);
  return String(v);
}

// ---------------------------------------------------------------------------
// Metric pill
// ---------------------------------------------------------------------------

function MetricPill({ name, value }) {
  const fmt = typeof value === "number"
    ? (Math.abs(value) < 1 ? value.toFixed(4) : value.toFixed(2))
    : String(value);
  return (
    <div className="flex items-center gap-2 bg-th-surface2 rounded-lg px-3 py-1.5 border border-th-border/30">
      <span className="text-xs text-th-secondary font-medium inline-flex items-center"><MetricLabel name={name} /></span>
      <span className="text-sm font-semibold text-th-body font-mono">{fmt}</span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sparkline chart
// ---------------------------------------------------------------------------

const CHART_COLORS = ["#2676FF", "#FFB32D", "#19BA5A", "#13BDD7", "#F03A47"];

function MetricsOverTimeChart({ runs, height = 220 }) {
  if (!runs || runs.length < 2) return null;

  const sortedRuns = [...runs].sort((a, b) => {
    if (a.run_ts && b.run_ts) return a.run_ts.localeCompare(b.run_ts);
    return (a.run_id || 0) - (b.run_id || 0);
  });

  const allMetricKeys = new Set();
  sortedRuns.forEach(r => {
    Object.entries(r.metrics || {}).forEach(([k, v]) => {
      if (typeof v === "number" && !k.includes("size") && !k.includes("n_customers")) {
        allMetricKeys.add(k);
      }
    });
  });
  const metricKeys = Array.from(allMetricKeys);
  if (metricKeys.length === 0) return null;

  const [activeMetrics, setActiveMetrics] = useState(() => new Set(metricKeys.slice(0, 2)));
  const [hoveredRun, setHoveredRun] = useState(null);

  const W = 600, H = height, PAD = { top: 20, right: 20, bottom: 40, left: 55 };
  const plotW = W - PAD.left - PAD.right;
  const plotH = H - PAD.top - PAD.bottom;

  const visibleMetrics = metricKeys.filter(k => activeMetrics.has(k));

  let yMin = Infinity, yMax = -Infinity;
  visibleMetrics.forEach(key => {
    sortedRuns.forEach(r => {
      const v = (r.metrics || {})[key];
      if (typeof v === "number") {
        yMin = Math.min(yMin, v);
        yMax = Math.max(yMax, v);
      }
    });
  });

  if (yMin === yMax) { yMin -= 0.1; yMax += 0.1; }
  const yPad = (yMax - yMin) * 0.1;
  yMin -= yPad;
  yMax += yPad;

  const xScale = (i) => PAD.left + (i / (sortedRuns.length - 1)) * plotW;
  const yScale = (v) => PAD.top + plotH - ((v - yMin) / (yMax - yMin)) * plotH;

  const yTicks = 5;
  const yTickVals = Array.from({ length: yTicks }, (_, i) => yMin + (i / (yTicks - 1)) * (yMax - yMin));

  const toggleMetric = (key) => {
    setActiveMetrics(prev => {
      const next = new Set(prev);
      if (next.has(key)) { if (next.size > 1) next.delete(key); }
      else next.add(key);
      return next;
    });
  };

  return (
    <div className="bg-th-surface rounded-lg border border-th-border/20 p-6 mb-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2 text-th-accent">
          <IconTrendUp />
          <h3 className="text-lg font-display text-th-heading tracking-wide">Metrics Over Time</h3>
        </div>
        <div className="flex gap-2 flex-wrap">
          {metricKeys.map((key, ki) => (
            <button
              key={key}
              onClick={() => toggleMetric(key)}
              className={`px-2.5 py-1 rounded-full text-xs font-medium border transition-all ${
                activeMetrics.has(key)
                  ? "border-current shadow-sm"
                  : "bg-th-surface2 text-th-secondary border-th-border/30"
              }`}
              style={activeMetrics.has(key) ? { color: CHART_COLORS[ki % CHART_COLORS.length], borderColor: CHART_COLORS[ki % CHART_COLORS.length], backgroundColor: CHART_COLORS[ki % CHART_COLORS.length] + "20" } : {}}
            >
              {key}
            </button>
          ))}
        </div>
      </div>

      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ maxHeight: `${H}px` }}>
        {yTickVals.map((v, i) => (
          <g key={i}>
            <line x1={PAD.left} y1={yScale(v)} x2={W - PAD.right} y2={yScale(v)}
              stroke="rgb(var(--th-border) / 0.3)" strokeWidth="1" strokeDasharray={i === 0 ? "0" : "4,4"} />
            <text x={PAD.left - 8} y={yScale(v) + 4} textAnchor="end"
              fontSize="11" fill="rgb(var(--th-secondary))" fontFamily="Roboto Mono, monospace">{Math.abs(v) < 1 ? v.toFixed(3) : v.toFixed(1)}</text>
          </g>
        ))}

        {sortedRuns.map((r, i) => (
          <g key={i}>
            <line x1={xScale(i)} y1={PAD.top} x2={xScale(i)} y2={H - PAD.bottom}
              stroke={hoveredRun === i ? "rgb(var(--th-border) / 0.5)" : "transparent"} strokeWidth="1" />
            <text x={xScale(i)} y={H - PAD.bottom + 16} textAnchor="middle"
              fontSize="10" fill="rgb(var(--th-secondary))" fontFamily="Roboto Mono, monospace">
              {(r.tags?.iteration || `#${r.run_number || r.run_id}`).substring(0, 12)}
            </text>
          </g>
        ))}

        {visibleMetrics.map((key, ki) => {
          const color = CHART_COLORS[metricKeys.indexOf(key) % CHART_COLORS.length];
          const points = sortedRuns
            .map((r, i) => {
              const v = (r.metrics || {})[key];
              return typeof v === "number" ? { x: xScale(i), y: yScale(v), v } : null;
            })
            .filter(Boolean);

          if (points.length < 2) return null;
          const pathD = points.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ");

          return (
            <g key={key}>
              <path d={pathD} fill="none" stroke={color} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
              {points.map((p, pi) => (
                <circle key={pi} cx={p.x} cy={p.y} r={hoveredRun === sortedRuns.indexOf(sortedRuns[pi]) ? 5 : 3.5}
                  fill="rgb(var(--th-chart-dot))" stroke={color} strokeWidth="2" />
              ))}
            </g>
          );
        })}

        {sortedRuns.map((_, i) => (
          <rect key={i} x={xScale(i) - plotW / sortedRuns.length / 2} y={PAD.top}
            width={plotW / sortedRuns.length} height={plotH}
            fill="transparent"
            onMouseEnter={() => setHoveredRun(i)}
            onMouseLeave={() => setHoveredRun(null)}
          />
        ))}
      </svg>

      {hoveredRun !== null && sortedRuns[hoveredRun] && (
        <div className="mt-2 px-3 py-2 bg-th-surface2 rounded-lg border border-th-border/30 text-sm">
          <span className="font-medium text-th-body">
            Run #{sortedRuns[hoveredRun].run_number || sortedRuns[hoveredRun].run_id}
            {sortedRuns[hoveredRun].tags?.iteration && ` · ${sortedRuns[hoveredRun].tags.iteration}`}
          </span>
          <div className="flex gap-3 mt-1">
            {visibleMetrics.map(key => {
              const v = (sortedRuns[hoveredRun].metrics || {})[key];
              return v != null ? (
                <span key={key} className="text-xs">
                  <span className="text-th-secondary">{key}:</span>{" "}
                  <span className="font-semibold font-mono">{typeof v === "number" ? (Math.abs(v) < 1 ? v.toFixed(4) : v.toFixed(2)) : v}</span>
                </span>
              ) : null;
            })}
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Feature comparison table
// ---------------------------------------------------------------------------

function FeatureComparisonTable({ runs }) {
  if (!runs || runs.length < 2) return null;

  const sorted = [...runs].sort((a, b) => {
    if (a.run_ts && b.run_ts) return a.run_ts.localeCompare(b.run_ts);
    return (a.run_id || 0) - (b.run_id || 0);
  });

  const featureSets = sorted.map(r => {
    const feats = (r.params || {}).features;
    return Array.isArray(feats) ? feats : [];
  });

  const allFeatures = [...new Set(featureSets.flat())];
  if (allFeatures.length === 0) return null;

  const stableOrder = [];
  featureSets.forEach(fs => {
    fs.forEach(f => { if (!stableOrder.includes(f)) stableOrder.push(f); });
  });

  return (
    <div className="bg-th-surface rounded-lg border border-th-border/20 p-6 mb-6">
      <h3 className="text-lg font-display text-th-heading tracking-wide mb-4">Feature Evolution</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-th-border/30">
              <th className="text-left py-2 px-3 text-th-secondary font-medium font-mono text-xs uppercase tracking-wider">Feature</th>
              {sorted.map((r, i) => (
                <th key={i} className="text-center py-2 px-2 text-th-secondary font-medium whitespace-nowrap">
                  <div className="text-xs font-mono">{r.tags?.iteration || `#${r.run_number || r.run_id}`}</div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {stableOrder.map(feat => (
              <tr key={feat} className="border-b border-th-surface2 hover:bg-th-surface2/50">
                <td className="py-1.5 px-3 font-mono text-xs text-th-body">{feat}</td>
                {featureSets.map((fs, i) => {
                  const has = fs.includes(feat);
                  const prevHas = i > 0 && featureSets[i - 1].includes(feat);
                  const isNew = has && !prevHas && i > 0;
                  const isRemoved = !has && prevHas;
                  return (
                    <td key={i} className="text-center py-1.5 px-2">
                      {has ? (
                        <span className={`inline-block w-5 h-5 rounded-full text-xs leading-5 ${
                          isNew ? "bg-bGreen-50/20 text-bGreen-50 ring-2 ring-bGreen-50/40" : "bg-bBlue-50/20 text-bBlue-50"
                        }`}>✓</span>
                      ) : isRemoved ? (
                        <span className="inline-block w-5 h-5 rounded-full bg-bRed-50/10 text-bRed-50/60 text-xs leading-5">✗</span>
                      ) : (
                        <span className="text-th-muted">-</span>
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}


// ---------------------------------------------------------------------------
// Dashboard view
// ---------------------------------------------------------------------------

function DashboardView({ summary, runs, models, onSelectRun, onNavigate }) {
  const recentRuns = (runs || []).slice(0, 8);
  const modelCount = new Set((models || []).map(m => m.model_name)).size;
  return (
    <div className="fade-in">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 mb-8">
        <SummaryCard label="Runs" value={summary.runs} icon={<IconChart />} color="bg-th-accent/20 text-th-accent" />
        <SummaryCard label="Experiments" value={summary.experiments} icon={<IconFlask />} color="bg-bPurple-60/20 text-bPurple-60" onClick={() => onNavigate("experiments")} />
        <SummaryCard label="Models" value={modelCount} icon={<IconBox />} color="bg-bGreen-50/20 text-bGreen-50" onClick={() => onNavigate("models")} />
        <SummaryCard label="Visualizations" value={summary.plots} icon={<IconImage />} color="bg-bTeal-50/20 text-bTeal-50" onClick={() => onNavigate("plots")} />
      </div>

      <div className="bg-th-surface rounded-lg border border-th-border/20 overflow-hidden">
        <div className="px-6 py-4 border-b border-th-border/20">
          <h2 className="text-lg font-display text-th-heading tracking-wide">Recent Runs</h2>
        </div>
        {recentRuns.length === 0 ? (
          <div className="px-6 py-12 text-center text-th-secondary">
            <p className="text-lg mb-2">No runs yet</p>
            <p className="text-sm">Train an ML model and track it with the MlopsTracker to see results here.</p>
          </div>
        ) : (
          <div className="divide-y divide-th-surface2">
            {recentRuns.map((run, i) => (
              <div
                key={`${run.run_id}-${i}`}
                className="px-6 py-4 hover:bg-th-surface2/50 cursor-pointer transition-colors flex items-center gap-4"
                onClick={() => onSelectRun(run)}
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-medium text-th-heading truncate">{run.experiment_name}</span>
                    <StatusBadge status={run.status} />
                    {run.tags?.iteration && (
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-medium font-mono bg-th-surface3 text-th-body">{run.tags.iteration}</span>
                    )}
                    {run.source === "xcom" && <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-bPurple-60/15 text-bPurple-60">live</span>}
                  </div>
                  <p className="text-xs text-th-secondary font-mono">
                    {run.dag_id} &middot; Run #{run.run_number || run.run_id}
                    {run.run_ts && ` · ${new Date(run.run_ts).toLocaleDateString()}`}
                  </p>
                </div>
                <div className="flex gap-2 flex-wrap justify-end">
                  {Object.entries(run.metrics || {}).filter(([k]) => !k.includes("size") && !k.includes("n_")).slice(0, 3).map(([k, v]) => (
                    <MetricPill key={k} name={k} value={v} />
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Experiments view
// ---------------------------------------------------------------------------

function ExperimentsView({ experiments, runs, onSelectRun, selectedRunIds, onToggleRun, onCompare, onClearSelection }) {
  const [expanded, setExpanded] = useState(null);

  const totalSelected = selectedRunIds.size;

  return (
    <div className="space-y-4 fade-in">
      <div className="mb-6 flex items-center gap-3">
        <div className="p-2 bg-bPurple-60/20 rounded-xl text-bPurple-60"><IconFlask /></div>
        <div>
          <h2 className="text-xl font-display text-th-heading tracking-wide">All Experiments</h2>
          <p className="text-xs text-th-secondary font-mono tracking-wider">{(experiments || []).length} experiment{(experiments || []).length !== 1 ? "s" : ""}</p>
        </div>
      </div>
      {totalSelected >= 2 && (
        <div className="sticky top-[73px] z-40 flex items-center gap-3 px-5 py-3 rounded-lg bg-th-accent/10 border border-th-accent/20 glass-dark">
          <IconCompare />
          <span className="text-sm text-th-accent font-medium font-mono">{totalSelected} runs selected</span>
          <div className="flex-1" />
          <button
            onClick={onCompare}
            className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-th-accent text-th-base text-sm font-medium hover:bg-th-accent2 transition-colors shadow-lg shadow-th-accent/20"
          >
            <IconCompare />
            Compare
          </button>
          <button
            onClick={onClearSelection}
            className="px-3 py-1.5 rounded-lg bg-th-surface3 text-th-body text-xs font-medium hover:bg-th-border hover:text-th-heading transition-colors"
          >
            Clear
          </button>
        </div>
      )}

      {(experiments || []).map((exp) => {
        const expRuns = (runs || []).filter(r => r.experiment_name === exp.experiment_name);
        const isOpen = expanded === exp.experiment_name;

        const sortedExpRuns = [...expRuns].sort((a, b) => {
          if (a.run_ts && b.run_ts) return a.run_ts.localeCompare(b.run_ts);
          return (a.run_id || 0) - (b.run_id || 0);
        });

        const selectedInExp = sortedExpRuns.filter(r => selectedRunIds.has(r.run_id)).length;

        return (
          <div key={exp.experiment_name} className="bg-th-surface rounded-lg border border-th-border/20 overflow-hidden">
            <div
              className="px-6 py-4 cursor-pointer hover:bg-th-surface2/50 transition-colors flex items-center justify-between"
              onClick={() => setExpanded(isOpen ? null : exp.experiment_name)}
            >
              <div>
                <h3 className="font-display text-th-heading tracking-wide text-lg">{exp.experiment_name}</h3>
                <p className="text-sm text-th-secondary">{exp.description || "No description"}</p>
              </div>
              <div className="flex items-center gap-3">
                {selectedInExp > 0 && (
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-th-accent/15 text-th-accent border border-th-accent/30">
                    {selectedInExp} selected
                  </span>
                )}
                <span className="text-sm text-th-secondary font-mono">{expRuns.length} run{expRuns.length !== 1 ? "s" : ""}</span>
                <svg className={`w-5 h-5 text-th-secondary transition-transform ${isOpen ? "rotate-180" : ""}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="6 9 12 15 18 9"/></svg>
              </div>
            </div>
            {isOpen && (
              <div className="border-t border-th-border/20 px-6 py-4">
                <MetricsOverTimeChart runs={sortedExpRuns} />
                <FeatureComparisonTable runs={sortedExpRuns} />

                <div className="bg-th-surface2 rounded-lg border border-th-border/20 overflow-hidden">
                  <div className="px-4 py-3 border-b border-th-border/20 flex items-center justify-between">
                    <h4 className="text-xs font-mono text-th-secondary uppercase tracking-wider">All Runs</h4>
                    {sortedExpRuns.length > 1 && (
                      <button
                        onClick={() => {
                          const allIds = sortedExpRuns.map(r => r.run_id);
                          const allSelected = allIds.every(id => selectedRunIds.has(id));
                          if (allSelected) allIds.forEach(id => onToggleRun(id));
                          else allIds.filter(id => !selectedRunIds.has(id)).forEach(id => onToggleRun(id));
                        }}
                        className="text-[10px] font-mono text-th-secondary hover:text-th-accent transition-colors"
                      >
                        {sortedExpRuns.every(r => selectedRunIds.has(r.run_id)) ? "Deselect all" : "Select all"}
                      </button>
                    )}
                  </div>
                  {sortedExpRuns.length === 0 ? (
                    <p className="px-4 py-4 text-sm text-th-secondary">No runs for this experiment.</p>
                  ) : (
                    <div className="divide-y divide-th-border/30">
                      {sortedExpRuns.map((run, i) => {
                        const isSelected = selectedRunIds.has(run.run_id);
                        return (
                          <div
                            key={`${run.run_id}-${i}`}
                            className={`px-4 py-3 hover:bg-th-surface3/30 cursor-pointer transition-colors flex items-start gap-3 ${
                              isSelected ? "bg-th-accent/5 border-l-2 border-l-th-accent" : "border-l-2 border-l-transparent"
                            }`}
                            onClick={() => onSelectRun(run)}
                          >
                            <div className="pt-0.5" onClick={(e) => { e.stopPropagation(); onToggleRun(run.run_id); }}>
                              <Checkbox checked={isSelected} onChange={() => {}} />
                            </div>
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center justify-between mb-1">
                                <div className="flex items-center gap-2">
                                  <span className="text-sm font-medium text-th-body">Run #{run.run_number || run.run_id}</span>
                                  <StatusBadge status={run.status} />
                                  {run.tags?.iteration && (
                                    <span className="px-1.5 py-0.5 rounded text-[10px] font-medium font-mono bg-th-surface3 text-th-body">{run.tags.iteration}</span>
                                  )}
                                </div>
                                <span className="text-xs text-th-secondary font-mono">
                                  {run.run_ts ? new Date(run.run_ts).toLocaleDateString() : run.dag_id}
                                </span>
                              </div>
                              <div className="flex gap-2 flex-wrap">
                                {Object.entries(run.metrics || {}).filter(([k]) => !k.includes("size") && !k.includes("n_")).map(([k, v]) => (
                                  <MetricPill key={k} name={k} value={v} />
                                ))}
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        );
      })}
      {(experiments || []).length === 0 && (
        <div className="bg-th-surface rounded-lg border border-th-border/20 px-6 py-12 text-center text-th-secondary">
          <p className="text-lg mb-2">No experiments yet</p>
          <p className="text-sm">Train an ML model and track it with the MlopsTracker to see results here.</p>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Run detail view
// ---------------------------------------------------------------------------

function RunDetailView({ run, onBack }) {
  const [plots, setPlots] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetchJSON(`runs/${run.run_id}/plots`)
      .then(setPlots)
      .catch(() => setPlots([]))
      .finally(() => setLoading(false));
  }, [run.run_id]);

  return (
    <div className="fade-in">
      <button onClick={onBack} className="mb-4 text-sm text-th-accent hover:text-th-accent2 font-medium flex items-center gap-1 transition-colors">
        <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="15 18 9 12 15 6"/></svg>
        Back
      </button>

      <div className="bg-th-surface rounded-lg border border-th-border/20 p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-xl font-display text-th-heading tracking-wide">Run #{run.run_number || run.run_id}</h2>
            <p className="text-sm text-th-secondary font-mono">
              {run.experiment_name} &middot; {run.dag_id}
              {run.run_ts && ` · ${new Date(run.run_ts).toLocaleString()}`}
            </p>
            {run.tags?.iteration && (
              <p className="text-xs text-th-muted mt-1 font-mono">{run.tags.iteration}</p>
            )}
          </div>
          <StatusBadge status={run.status} />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <h3 className="text-xs font-mono text-th-secondary mb-3 uppercase tracking-wider">Metrics</h3>
            <div className="space-y-2">
              {Object.entries(run.metrics || {}).map(([k, v]) => (
                <div key={k} className="flex justify-between items-center py-1.5 border-b border-th-border/30">
                  <span className="text-sm text-th-body inline-flex items-center"><MetricLabel name={k} /></span>
                  <span className="text-sm font-semibold text-th-body font-mono">
                    {typeof v === "number" ? (Math.abs(v) < 1 ? v.toFixed(6) : v.toFixed(2)) : String(v)}
                  </span>
                </div>
              ))}
            </div>
          </div>
          <div>
            <h3 className="text-xs font-mono text-th-secondary mb-3 uppercase tracking-wider">Hyperparameters</h3>
            <div className="space-y-2">
              {Object.entries(run.params || {}).map(([k, v]) => (
                <div key={k} className="flex justify-between items-center py-1.5 border-b border-th-border/30">
                  <span className="text-sm text-th-body inline-flex items-center"><MetricLabel name={k} /></span>
                  <span className="text-sm font-medium text-th-body font-mono truncate max-w-[200px]">
                    {formatParamValue(v)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="bg-th-surface rounded-lg border border-th-border/20 p-6">
        <h3 className="text-lg font-display text-th-heading tracking-wide mb-4">Visualizations</h3>
        {loading ? (
          <div className="flex justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-th-accent"></div>
          </div>
        ) : plots.length === 0 ? (
          <p className="text-sm text-th-secondary text-center py-8">No visualizations for this run.</p>
        ) : (
          <div className="space-y-6">
            {plots.map((p, i) => (
              <div key={i} className="rounded-lg overflow-hidden border border-th-border/20 bg-th-surface2">
                <div className="px-4 py-2 bg-th-surface3 border-b border-th-border/20">
                  <span className="text-sm font-medium text-th-body">{p.plot_name}</span>
                </div>
                <div className="p-4">
                  <img src={`data:image/png;base64,${p.plot_data}`} alt={p.plot_name} className="w-full rounded" />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Models view
// ---------------------------------------------------------------------------

function ModelsView({ models }) {
  const grouped = {};
  (models || []).forEach(m => {
    if (!grouped[m.model_name]) grouped[m.model_name] = [];
    grouped[m.model_name].push(m);
  });

  return (
    <div className="space-y-6 fade-in">
      <div className="mb-6 flex items-center gap-3">
        <div className="p-2 bg-bGreen-50/20 rounded-xl text-bGreen-50"><IconBox /></div>
        <div>
          <h2 className="text-xl font-display text-th-heading tracking-wide">All Models</h2>
          <p className="text-xs text-th-secondary font-mono tracking-wider">{Object.keys(grouped).length} model{Object.keys(grouped).length !== 1 ? "s" : ""} registered</p>
        </div>
      </div>
      {Object.entries(grouped).map(([name, versions]) => (
        <div key={name} className="bg-th-surface rounded-lg border border-th-border/20 overflow-hidden">
          <div className="px-6 py-4 border-b border-th-border/20 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-bGreen-50/20 rounded-xl text-bGreen-50"><IconBox /></div>
              <div>
                <h3 className="font-display text-th-heading tracking-wide text-lg">{name}</h3>
                <p className="text-xs text-th-secondary font-mono">{versions[0]?.model_type}</p>
              </div>
            </div>
            <span className="text-sm text-th-secondary font-mono">{versions.length} version{versions.length !== 1 ? "s" : ""}</span>
          </div>
          <div className="divide-y divide-th-surface2">
            {versions.map((v, i) => (
              <div key={`${v.model_version}-${i}`} className="px-6 py-3 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="text-sm font-mono text-th-body">v{v.model_version}</span>
                  <StageBadge stage={v.stage} />
                  {v.source === "xcom" && <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-bPurple-60/15 text-bPurple-60">live</span>}
                </div>
                <span className="text-xs text-th-secondary font-mono">Run #{v.run_number || v.run_id}</span>
              </div>
            ))}
          </div>
        </div>
      ))}
      {Object.keys(grouped).length === 0 && (
        <div className="bg-th-surface rounded-lg border border-th-border/20 px-6 py-12 text-center text-th-secondary">
          <p className="text-lg mb-2">No models registered</p>
          <p className="text-sm">Train an ML model and track it with the MlopsTracker to see results here.</p>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Parallel coordinates chart for run comparison
// ---------------------------------------------------------------------------

function ParallelCoordinatesChart({ runs }) {
  const [hoveredIdx, setHoveredIdx] = useState(null);

  const axes = useMemo(() => {
    const paramKeys = new Set();
    const metricKeys = new Set();
    runs.forEach(r => {
      Object.entries(r.params || {}).forEach(([k, v]) => {
        if (typeof v === "number") paramKeys.add(k);
      });
      Object.entries(r.metrics || {}).forEach(([k, v]) => {
        if (typeof v === "number" && !k.includes("size") && !k.includes("n_customers")) metricKeys.add(k);
      });
    });

    const result = [];
    paramKeys.forEach(k => {
      const vals = runs.map(r => (r.params || {})[k]).filter(v => typeof v === "number");
      if (vals.length > 0) result.push({ key: k, isMetric: false, min: Math.min(...vals), max: Math.max(...vals) });
    });
    metricKeys.forEach(k => {
      const vals = runs.map(r => (r.metrics || {})[k]).filter(v => typeof v === "number");
      if (vals.length > 0) result.push({ key: k, isMetric: true, min: Math.min(...vals), max: Math.max(...vals) });
    });
    return result;
  }, [runs]);

  if (axes.length < 2) return null;

  const W = 800, H = 320, PAD = { top: 50, right: 50, bottom: 35, left: 50 };
  const plotW = W - PAD.left - PAD.right;
  const plotH = H - PAD.top - PAD.bottom;

  const xScale = (i) => PAD.left + (i / (axes.length - 1)) * plotW;
  const yScale = (axis, val) => {
    if (axis.min === axis.max) return PAD.top + plotH / 2;
    return PAD.top + plotH - ((val - axis.min) / (axis.max - axis.min)) * plotH;
  };

  const fmtVal = (v) => Math.abs(v) < 1 ? v.toFixed(4) : v.toFixed(2);

  return (
    <div className="bg-th-surface rounded-lg border border-th-border/20 p-6 mb-6">
      <div className="flex items-center gap-2 mb-4 text-th-accent">
        <IconTrendUp />
        <h3 className="text-lg font-display text-th-heading tracking-wide">Parallel Coordinates</h3>
      </div>

      <div className="flex gap-4 flex-wrap mb-4">
        {runs.map((r, i) => (
          <div
            key={r.run_id}
            className={`flex items-center gap-1.5 text-xs cursor-pointer transition-opacity ${hoveredIdx !== null && hoveredIdx !== i ? "opacity-30" : ""}`}
            onMouseEnter={() => setHoveredIdx(i)}
            onMouseLeave={() => setHoveredIdx(null)}
          >
            <span className="w-3 h-3 rounded-full" style={{ backgroundColor: CHART_COLORS[i % CHART_COLORS.length] }} />
            <span className="text-th-body font-mono">{r.tags?.iteration || `Run #${r.run_number || r.run_id}`}</span>
          </div>
        ))}
      </div>

      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ maxHeight: `${H}px` }}>
        {axes.map((axis, ai) => (
          <g key={axis.key}>
            <line x1={xScale(ai)} y1={PAD.top} x2={xScale(ai)} y2={PAD.top + plotH}
              stroke="rgb(var(--th-border) / 0.4)" strokeWidth="1" />
            <text x={xScale(ai)} y={PAD.top - 14} textAnchor="middle"
              fontSize="10" fill={axis.isMetric ? "rgb(var(--th-accent))" : "rgb(var(--th-secondary))"} fontFamily="Roboto Mono, monospace" fontWeight={axis.isMetric ? "600" : "400"}>
              {axis.key}
            </text>
            <text x={xScale(ai)} y={PAD.top - 3} textAnchor="middle"
              fontSize="8" fill="rgb(var(--th-muted))" fontFamily="Roboto Mono, monospace">
              {axis.isMetric ? "metric" : "param"}
            </text>
            <text x={xScale(ai)} y={PAD.top + plotH + 14} textAnchor="middle"
              fontSize="9" fill="rgb(var(--th-muted))" fontFamily="Roboto Mono, monospace">
              {fmtVal(axis.min)}
            </text>
            <text x={xScale(ai)} y={PAD.top - 24} textAnchor="middle"
              fontSize="9" fill="rgb(var(--th-muted))" fontFamily="Roboto Mono, monospace">
              {axis.min !== axis.max ? fmtVal(axis.max) : ""}
            </text>
          </g>
        ))}

        {runs.map((run, ri) => {
          const color = CHART_COLORS[ri % CHART_COLORS.length];
          const isHovered = hoveredIdx === ri;
          const opacity = hoveredIdx === null ? 0.65 : (isHovered ? 1 : 0.1);

          const points = axes.map((axis, ai) => {
            const val = axis.isMetric ? (run.metrics || {})[axis.key] : (run.params || {})[axis.key];
            if (typeof val !== "number") return null;
            return { x: xScale(ai), y: yScale(axis, val) };
          });

          const validPoints = points.filter(Boolean);
          if (validPoints.length < 2) return null;

          const segments = [];
          let current = [];
          points.forEach(p => {
            if (p) current.push(p);
            else { if (current.length > 1) segments.push(current); current = []; }
          });
          if (current.length > 1) segments.push(current);

          return (
            <g key={run.run_id} style={{ transition: "opacity 0.2s" }} opacity={opacity}>
              {segments.map((seg, si) => {
                const pathD = seg.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ");
                return <path key={si} d={pathD} fill="none" stroke={color} strokeWidth={isHovered ? 3.5 : 2} strokeLinecap="round" strokeLinejoin="round" />;
              })}
              {validPoints.map((p, pi) => (
                <circle key={pi} cx={p.x} cy={p.y} r={isHovered ? 4.5 : 3}
                  fill="rgb(var(--th-chart-dot))" stroke={color} strokeWidth="2" />
              ))}
            </g>
          );
        })}

        {runs.map((run, ri) => {
          const points = axes.map((axis, ai) => {
            const val = axis.isMetric ? (run.metrics || {})[axis.key] : (run.params || {})[axis.key];
            if (typeof val !== "number") return null;
            return { x: xScale(ai), y: yScale(axis, val) };
          }).filter(Boolean);
          if (points.length < 2) return null;
          const pathD = points.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ");
          return (
            <path key={`h-${run.run_id}`} d={pathD} fill="none" stroke="transparent"
              strokeWidth="14" strokeLinecap="round"
              onMouseEnter={() => setHoveredIdx(ri)}
              onMouseLeave={() => setHoveredIdx(null)} />
          );
        })}
      </svg>

      {hoveredIdx !== null && runs[hoveredIdx] && (
        <div className="mt-2 px-4 py-2.5 bg-th-surface2 rounded-lg border border-th-border/30 text-sm">
          <span className="font-medium text-th-body">
            {runs[hoveredIdx].tags?.iteration || `Run #${runs[hoveredIdx].run_number || runs[hoveredIdx].run_id}`}
          </span>
          <div className="flex gap-4 mt-1 flex-wrap">
            {axes.map(axis => {
              const val = axis.isMetric
                ? (runs[hoveredIdx].metrics || {})[axis.key]
                : (runs[hoveredIdx].params || {})[axis.key];
              return typeof val === "number" ? (
                <span key={axis.key} className="text-xs">
                  <span className={axis.isMetric ? "text-th-accent" : "text-th-secondary"}>{axis.key}:</span>{" "}
                  <span className="font-semibold font-mono">{fmtVal(val)}</span>
                </span>
              ) : null;
            })}
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Metrics comparison bar chart
// ---------------------------------------------------------------------------

function MetricsBarChart({ runs }) {
  const metricKeys = useMemo(() => {
    const keys = new Set();
    runs.forEach(r => {
      Object.entries(r.metrics || {}).forEach(([k, v]) => {
        if (typeof v === "number" && !k.includes("size") && !k.includes("n_customers")) keys.add(k);
      });
    });
    return Array.from(keys);
  }, [runs]);

  if (metricKeys.length === 0) return null;

  const barH = 20;
  const groupGap = 16;
  const barGap = 3;
  const labelW = 120;
  const valueW = 60;
  const W = 600;
  const groupH = runs.length * (barH + barGap) - barGap;
  const totalH = metricKeys.length * (groupH + groupGap) - groupGap + 20;

  const ranges = useMemo(() => {
    const r = {};
    metricKeys.forEach(k => {
      const vals = runs.map(run => (run.metrics || {})[k]).filter(v => typeof v === "number");
      r[k] = { min: Math.min(0, ...vals), max: Math.max(...vals) };
      if (r[k].min === r[k].max) r[k].max += 0.1;
    });
    return r;
  }, [runs, metricKeys]);

  const barW = W - labelW - valueW;
  const fmtVal = (v) => Math.abs(v) < 1 ? v.toFixed(4) : v.toFixed(2);

  return (
    <div className="bg-th-surface rounded-lg border border-th-border/20 p-6 mb-6">
      <div className="flex items-center gap-2 mb-4 text-th-accent">
        <IconChart />
        <h3 className="text-lg font-display text-th-heading tracking-wide">Metrics Comparison</h3>
      </div>

      <div className="flex gap-4 flex-wrap mb-4">
        {runs.map((r, i) => (
          <div key={r.run_id} className="flex items-center gap-1.5 text-xs">
            <span className="w-3 h-3 rounded-full" style={{ backgroundColor: CHART_COLORS[i % CHART_COLORS.length] }} />
            <span className="text-th-body font-mono">{r.tags?.iteration || `Run #${r.run_number || r.run_id}`}</span>
          </div>
        ))}
      </div>

      <svg viewBox={`0 0 ${W} ${totalH}`} className="w-full" style={{ maxHeight: `${totalH}px` }}>
        {metricKeys.map((key, gi) => {
          const yOffset = gi * (groupH + groupGap);
          const range = ranges[key];
          const bestVal = Math.max(...runs.map(r => (r.metrics || {})[key]).filter(v => typeof v === "number"));

          return (
            <g key={key}>
              <text x={0} y={yOffset + groupH / 2 + 4} fontSize="11" fill="rgb(var(--th-secondary))"
                fontFamily="Roboto Mono, monospace" fontWeight="500">
                {key}
              </text>
              {runs.map((run, ri) => {
                const val = (run.metrics || {})[key];
                if (typeof val !== "number") return null;
                const color = CHART_COLORS[ri % CHART_COLORS.length];
                const w = ((val - range.min) / (range.max - range.min)) * barW;
                const y = yOffset + ri * (barH + barGap);
                const isBest = val === bestVal && runs.length > 1;

                return (
                  <g key={ri}>
                    <rect x={labelW} y={y} width={barW} height={barH} rx="4" fill="rgb(var(--th-border) / 0.15)" />
                    <rect x={labelW} y={y} width={Math.max(w, 2)} height={barH} rx="4"
                      fill={color} opacity={0.85} />
                    {isBest && (
                      <rect x={labelW} y={y} width={Math.max(w, 2)} height={barH} rx="4"
                        fill="none" stroke="rgb(var(--th-accent))" strokeWidth="1.5" opacity="0.6" />
                    )}
                    <text x={labelW + barW + 6} y={y + barH / 2 + 4} fontSize="10"
                      fill={isBest ? "rgb(var(--th-accent))" : "rgb(var(--th-secondary))"} fontFamily="Roboto Mono, monospace"
                      fontWeight={isBest ? "600" : "400"}>
                      {fmtVal(val)}
                    </text>
                  </g>
                );
              })}
            </g>
          );
        })}
      </svg>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Side-by-side comparison table
// ---------------------------------------------------------------------------

function CompareDetailsTable({ runs }) {
  const metricKeys = useMemo(() => {
    const keys = new Set();
    runs.forEach(r => Object.entries(r.metrics || {}).forEach(([k, v]) => {
      if (typeof v === "number") keys.add(k);
    }));
    return Array.from(keys);
  }, [runs]);

  const paramKeys = useMemo(() => {
    const keys = new Set();
    runs.forEach(r => Object.entries(r.params || {}).forEach(([k]) => keys.add(k)));
    return Array.from(keys);
  }, [runs]);

  const bestMetrics = useMemo(() => {
    const best = {};
    metricKeys.forEach(k => {
      const vals = runs.map(r => (r.metrics || {})[k]).filter(v => typeof v === "number");
      if (vals.length > 0) best[k] = Math.max(...vals);
    });
    return best;
  }, [runs, metricKeys]);

  const fmtVal = (v) => {
    if (v == null) return "-";
    if (typeof v === "number") return Math.abs(v) < 1 ? v.toFixed(6) : v.toFixed(2);
    if (Array.isArray(v)) return v.join(", ");
    return String(v);
  };

  return (
    <div className="bg-th-surface rounded-lg border border-th-border/20 p-6">
      <div className="flex items-center gap-2 mb-4 text-th-accent">
        <IconCompare />
        <h3 className="text-lg font-display text-th-heading tracking-wide">Run Details</h3>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-th-border/30">
              <th className="text-left py-2 px-3 text-th-secondary font-mono text-xs uppercase tracking-wider sticky left-0 bg-th-surface">Property</th>
              {runs.map((r, i) => (
                <th key={r.run_id} className="text-center py-2 px-3 whitespace-nowrap min-w-[120px]">
                  <div className="flex items-center justify-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: CHART_COLORS[i % CHART_COLORS.length] }} />
                    <span className="text-xs font-mono text-th-body">{r.tags?.iteration || `Run #${r.run_number || r.run_id}`}</span>
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {metricKeys.length > 0 && (
              <tr>
                <td colSpan={runs.length + 1} className="pt-4 pb-1 px-3">
                  <span className="text-[10px] font-mono text-th-accent uppercase tracking-widest">Metrics</span>
                </td>
              </tr>
            )}
            {metricKeys.map(k => (
              <tr key={`m-${k}`} className="border-b border-th-surface2 hover:bg-th-surface2/30">
                <td className="py-1.5 px-3 font-mono text-xs text-th-body sticky left-0 bg-th-surface whitespace-nowrap"><MetricLabel name={k} /></td>
                {runs.map((r, i) => {
                  const val = (r.metrics || {})[k];
                  const isBest = typeof val === "number" && val === bestMetrics[k] && runs.length > 1;
                  return (
                    <td key={i} className={`text-center py-1.5 px-3 font-mono text-xs ${
                      isBest ? "text-th-accent font-semibold" : "text-th-body"
                    }`}>
                      {fmtVal(val)}
                    </td>
                  );
                })}
              </tr>
            ))}

            {paramKeys.length > 0 && (
              <tr>
                <td colSpan={runs.length + 1} className="pt-4 pb-1 px-3">
                  <span className="text-[10px] font-mono text-bBlue-50 uppercase tracking-widest">Hyperparameters</span>
                </td>
              </tr>
            )}
            {paramKeys.map(k => (
              <tr key={`p-${k}`} className="border-b border-th-surface2 hover:bg-th-surface2/30">
                <td className="py-1.5 px-3 font-mono text-xs text-th-body sticky left-0 bg-th-surface whitespace-nowrap"><MetricLabel name={k} /></td>
                {runs.map((r, i) => {
                  const val = (r.params || {})[k];
                  return (
                    <td key={i} className="text-center py-1.5 px-3 font-mono text-xs text-th-body">
                      {fmtVal(val)}
                    </td>
                  );
                })}
              </tr>
            ))}

            <tr>
              <td colSpan={runs.length + 1} className="pt-4 pb-1 px-3">
                <span className="text-[10px] font-mono text-th-muted uppercase tracking-widest">Run Info</span>
              </td>
            </tr>
            {["experiment_name", "dag_id", "task_id", "status"].map(k => (
              <tr key={`i-${k}`} className="border-b border-th-surface2 hover:bg-th-surface2/30">
                <td className="py-1.5 px-3 font-mono text-xs text-th-body sticky left-0 bg-th-surface">{k}</td>
                {runs.map((r, i) => (
                  <td key={i} className="text-center py-1.5 px-3 font-mono text-xs text-th-body">
                    {r[k] || "-"}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Compare runs view
// ---------------------------------------------------------------------------

function CompareRunsView({ runs, onBack }) {
  return (
    <div className="fade-in">
      <button onClick={onBack} className="mb-4 text-sm text-th-accent hover:text-th-accent2 font-medium flex items-center gap-1 transition-colors">
        <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="15 18 9 12 15 6"/></svg>
        Back to experiments
      </button>

      <div className="mb-6 flex items-center gap-3">
        <div className="p-2 bg-th-accent/20 rounded-xl text-th-accent"><IconCompare /></div>
        <div>
          <h2 className="text-xl font-display text-th-heading tracking-wide">
            Comparing {runs.length} runs
          </h2>
          <p className="text-xs text-th-secondary font-mono tracking-wider">
            {runs.map(r => r.tags?.iteration || `#${r.run_number || r.run_id}`).join(" vs ")}
          </p>
        </div>
      </div>

      <ParallelCoordinatesChart runs={runs} />
      <MetricsBarChart runs={runs} />
      <CompareDetailsTable runs={runs} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Visualizations gallery view
// ---------------------------------------------------------------------------

function VisualizationsView({ onSelectRun, runs }) {
  const [plots, setPlots] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetchJSON("plots")
      .then(setPlots)
      .catch(() => setPlots([]))
      .finally(() => setLoading(false));
  }, []);

  const grouped = useMemo(() => {
    const g = {};
    plots.forEach(p => {
      const key = p.experiment_name || `Run #${p.run_id}`;
      if (!g[key]) g[key] = [];
      g[key].push(p);
    });
    return g;
  }, [plots]);

  return (
    <div className="fade-in">
      <div className="mb-6 flex items-center gap-3">
        <div className="p-2 bg-bTeal-50/20 rounded-xl text-bTeal-50"><IconImage /></div>
        <div>
          <h2 className="text-xl font-display text-th-heading tracking-wide">All Visualizations</h2>
          <p className="text-xs text-th-secondary font-mono tracking-wider">{plots.length} plot{plots.length !== 1 ? "s" : ""} across all experiments</p>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-16">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-th-accent"></div>
        </div>
      ) : plots.length === 0 ? (
        <div className="bg-th-surface rounded-lg border border-th-border/20 px-6 py-12 text-center text-th-secondary">
          <p className="text-lg mb-2">No visualizations yet</p>
          <p className="text-sm">Train an ML model and track it with the MlopsTracker to see results here.</p>
        </div>
      ) : (
        <div className="space-y-8">
          {Object.entries(grouped).map(([expName, expPlots]) => (
            <div key={expName}>
              <h3 className="text-sm font-display text-th-heading tracking-wide mb-3">{expName}</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {expPlots.map((p, i) => (
                  <div
                    key={`${p.plot_id}-${i}`}
                    className="rounded-lg overflow-hidden border border-th-border/20 bg-th-surface hover:border-th-accent/30 transition-colors cursor-pointer"
                    onClick={() => {
                      const run = (runs || []).find(r => r.run_id === p.run_id);
                      if (run) onSelectRun(run);
                    }}
                  >
                    <div className="px-4 py-2 bg-th-surface2 border-b border-th-border/20 flex items-center justify-between">
                      <span className="text-sm font-medium text-th-body">{p.plot_name}</span>
                      <span className="text-[10px] font-mono text-th-secondary">Run #{p.run_number || p.run_id}</span>
                    </div>
                    <div className="p-3">
                      <img src={`data:image/png;base64,${p.plot_data}`} alt={p.plot_name} className="w-full rounded" />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Navigation
// ---------------------------------------------------------------------------

function NavItem({ label, icon, active, onClick }) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2.5 px-4 py-2.5 rounded-xl text-sm font-medium transition-all ${
        active
          ? "bg-th-accent text-th-base shadow-lg shadow-th-accent/20"
          : "text-th-body hover:bg-th-surface3 hover:text-th-heading"
      }`}
    >
      {icon}
      {label}
    </button>
  );
}

// ---------------------------------------------------------------------------
// Theme helpers
// ---------------------------------------------------------------------------

function getInitialTheme() {
  try {
    const saved = localStorage.getItem("mlops-theme");
    if (saved === "light" || saved === "dark") return saved;
  } catch {}
  return window.matchMedia?.("(prefers-color-scheme: light)").matches ? "light" : "dark";
}

function applyTheme(theme) {
  if (theme === "light") {
    document.body.classList.add("light");
  } else {
    document.body.classList.remove("light");
  }
  try { localStorage.setItem("mlops-theme", theme); } catch {}
}

// ---------------------------------------------------------------------------
// App
// ---------------------------------------------------------------------------

function App() {
  const [view, setView] = useState("dashboard");
  const [selectedRun, setSelectedRun] = useState(null);
  const [selectedRunIds, setSelectedRunIds] = useState(new Set());
  const [summary, setSummary] = useState({ experiments: 0, runs: 0, models: 0, plots: 0 });
  const [experiments, setExperiments] = useState([]);
  const [runs, setRuns] = useState([]);
  const [models, setModels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [theme, setTheme] = useState(getInitialTheme);

  useEffect(() => { applyTheme(theme); }, [theme]);

  const toggleTheme = useCallback(() => {
    setTheme(prev => prev === "dark" ? "light" : "dark");
  }, []);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [s, e, r, m] = await Promise.all([
        fetchJSON("summary"),
        fetchJSON("experiments"),
        fetchJSON("runs"),
        fetchJSON("models"),
      ]);
      setSummary(s);
      setExperiments(e);
      setRuns(r);
      setModels(m);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleSelectRun = (run) => {
    setSelectedRun(run);
    setView("run-detail");
  };

  const toggleRunSelection = useCallback((runId) => {
    setSelectedRunIds(prev => {
      const next = new Set(prev);
      if (next.has(runId)) next.delete(runId);
      else next.add(runId);
      return next;
    });
  }, []);

  const clearRunSelection = useCallback(() => setSelectedRunIds(new Set()), []);

  const handleCompare = useCallback(() => {
    if (selectedRunIds.size >= 2) setView("compare");
  }, [selectedRunIds]);

  const navigateTo = useCallback((v) => {
    setView(v);
    setSelectedRun(null);
    if (v !== "experiments" && v !== "compare") setSelectedRunIds(new Set());
  }, []);

  const compareRuns = useMemo(() => {
    return runs.filter(r => selectedRunIds.has(r.run_id));
  }, [runs, selectedRunIds]);

  if (loading && !summary.runs) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-th-accent mx-auto mb-4"></div>
          <p className="text-th-secondary">Loading MLOps data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <header className="banner-header sticky top-0 z-50 border-b border-th-border/20 relative overflow-hidden">
        {theme === "dark" && (
          <img src="assets/banner2.png" alt="" className="absolute right-0 top-0 h-full w-auto object-contain object-right opacity-40 pointer-events-none select-none" />
        )}
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between relative">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-gradient-to-br from-th-accent to-th-accent2 rounded-xl text-th-base">
              <IconChart />
            </div>
            <div>
              <h1 className="text-xl font-display text-th-heading tracking-wide">MLOps Dashboard</h1>
              <p className="text-xs text-th-secondary font-mono tracking-wider">Experiment Tracking &middot; Model Registry</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {summary.workshop_mode && (
              <span className="px-3 py-1 rounded-full text-xs font-medium bg-bPurple-60/15 text-bPurple-60 border border-bPurple-60/30">
                Workshop Mode
              </span>
            )}
            <button
              onClick={toggleTheme}
              className="p-2 rounded-lg hover:bg-th-surface3 text-th-secondary hover:text-th-body transition-colors"
              title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
            >
              {theme === "dark" ? <IconSun /> : <IconMoon />}
            </button>
            <button
              onClick={loadData}
              disabled={loading}
              className="p-2 rounded-lg hover:bg-th-surface3 text-th-secondary hover:text-th-body transition-colors disabled:opacity-50"
              title="Refresh"
            >
              <span className={loading ? "spin inline-block" : ""}>
                <IconRefresh />
              </span>
            </button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-6">
        <nav className="flex gap-2 mb-6">
          <NavItem label="Dashboard" icon={<IconChart />} active={view === "dashboard"} onClick={() => navigateTo("dashboard")} />
          <NavItem label="Experiments" icon={<IconFlask />} active={view === "experiments" || view === "compare"} onClick={() => navigateTo("experiments")} />
          <NavItem label="Models" icon={<IconBox />} active={view === "models"} onClick={() => navigateTo("models")} />
          <NavItem label="Visualizations" icon={<IconImage />} active={view === "plots"} onClick={() => navigateTo("plots")} />
        </nav>

        {error && (
          <div className="mb-6 p-4 rounded-lg bg-bRed-50/10 border border-bRed-50/30 text-bRed-50 text-sm">
            {error}
          </div>
        )}

        {view === "dashboard" && <DashboardView summary={summary} runs={runs} models={models} onSelectRun={handleSelectRun} onNavigate={navigateTo} />}
        {view === "experiments" && (
          <ExperimentsView
            experiments={experiments}
            runs={runs}
            onSelectRun={handleSelectRun}
            selectedRunIds={selectedRunIds}
            onToggleRun={toggleRunSelection}
            onCompare={handleCompare}
            onClearSelection={clearRunSelection}
          />
        )}
        {view === "models" && <ModelsView models={models} />}
        {view === "run-detail" && selectedRun && (
          <RunDetailView run={selectedRun} onBack={() => navigateTo("experiments")} />
        )}
        {view === "compare" && compareRuns.length >= 2 && (
          <CompareRunsView runs={compareRuns} onBack={() => setView("experiments")} />
        )}
        {view === "plots" && (
          <VisualizationsView runs={runs} onSelectRun={handleSelectRun} />
        )}
      </div>
    </div>
  );
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(React.createElement(App));
