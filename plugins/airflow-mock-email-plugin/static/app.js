const { useState, useEffect, useCallback, useMemo } = React;

const API = "api";

// Centralised so a Dag rename is a one line change (see the empty state copy).
const SETUP_DAG = "setup";
const MOCK_PROSPECT_DAG = "mock_prospect";

async function fetchJSON(path) {
  const res = await fetch(`${API}/${path}`);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

// ---------------------------------------------------------------------------
// Icons
// ---------------------------------------------------------------------------

function IconMail() {
  return (
    <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="4" width="20" height="16" rx="2" /><path d="M2 7l10 6 10-6" />
    </svg>
  );
}

function IconInbound() {
  return (
    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 5v14" /><path d="M19 12l-7 7-7-7" />
    </svg>
  );
}

function IconOutbound() {
  return (
    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 19V5" /><path d="M5 12l7-7 7 7" />
    </svg>
  );
}

function IconSteps() {
  return (
    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="6" cy="6" r="2" /><circle cx="6" cy="18" r="2" /><path d="M6 8v8" />
      <path d="M11 6h8M11 12h8M11 18h8" />
    </svg>
  );
}

function IconRefresh() {
  return (
    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="23 4 23 10 17 10" /><path d="M20.49 15a9 9 0 11-2.12-9.36L23 10" />
    </svg>
  );
}

function IconSun() {
  return (
    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="5" /><line x1="12" y1="1" x2="12" y2="3" /><line x1="12" y1="21" x2="12" y2="23" />
      <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" /><line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
      <line x1="1" y1="12" x2="3" y2="12" /><line x1="21" y1="12" x2="23" y2="12" />
      <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" /><line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
    </svg>
  );
}

function IconMoon() {
  return (
    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z" />
    </svg>
  );
}

function IconClose() {
  return (
    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  );
}

// ---------------------------------------------------------------------------
// Formatting helpers
// ---------------------------------------------------------------------------

function fmtMoney(n) {
  if (n === null || n === undefined || n === "") return null;
  const num = Number(n);
  if (Number.isNaN(num)) return String(n);
  return "$" + num.toLocaleString();
}

function fmtWhen(s) {
  if (!s) return "";
  const d = new Date(s);
  if (Number.isNaN(d.getTime())) return String(s);
  return d.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

function humanize(key) {
  return String(key).replace(/_/g, " ");
}

// ---------------------------------------------------------------------------
// Small presentational pieces
// ---------------------------------------------------------------------------

function StatusBadge({ booked, spend, responded }) {
  const money = fmtMoney(spend);
  if (booked === true) {
    return (
      <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-bGreen-50/15 text-bGreen-50 border border-bGreen-50/30">
        booked{money ? ` · ${money}` : ""}
      </span>
    );
  }
  if (booked === false) {
    return (
      <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-th-border/20 text-th-secondary border border-th-border/30">
        no booking
      </span>
    );
  }
  if (responded) {
    return (
      <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-th-border/20 text-th-secondary border border-th-border/30">
        closed
      </span>
    );
  }
  return (
    <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-bBlue-50/10 text-bBlue-50 border border-bBlue-50/30">
      open
    </span>
  );
}

function LoyaltyChip({ tier }) {
  if (!tier) return null;
  return (
    <span className="px-1.5 py-0.5 rounded text-[10px] font-medium font-mono bg-th-surface3 text-th-body uppercase tracking-wider">
      {tier}
    </span>
  );
}

// Map a decision_maker label to a colour family, tolerant of unknown values.
function decisionMakerStyle(rawMaker) {
  const m = String(rawMaker || "").toLowerCase();
  if (m.includes("human")) return { label: rawMaker || "human", cls: "bg-gold-40/15 text-gold-40 border-gold-40/30", dot: "#FFB32D" };
  if (m.includes("judge")) return { label: rawMaker || "judge", cls: "bg-bPurple-60/15 text-bPurple-60 border-bPurple-60/30", dot: "#872DED" };
  if (m.includes("ml") || m.includes("model") || m.includes("spend") || m.includes("regress")) return { label: rawMaker || "model", cls: "bg-bBlue-50/15 text-bBlue-50 border-bBlue-50/30", dot: "#2676FF" };
  if (m.includes("ai") || m.includes("llm") || m.includes("agent") || m.includes("draft")) return { label: rawMaker || "ai", cls: "bg-bPurple-60/15 text-bPurple-60 border-bPurple-60/30", dot: "#872DED" };
  if (m.includes("context") || m.includes("retriev") || m.includes("rag") || m.includes("system") || m.includes("tool")) return { label: rawMaker || "system", cls: "bg-bTeal-50/15 text-bTeal-50 border-bTeal-50/30", dot: "#13BDD7" };
  return { label: rawMaker || "step", cls: "bg-th-border/20 text-th-secondary border-th-border/30", dot: "#736D6D" };
}

// ---------------------------------------------------------------------------
// Thread list (left pane)
// ---------------------------------------------------------------------------

function ThreadList({ threads, selectedId, onSelect }) {
  return (
    <div className="divide-y divide-th-surface2">
      {threads.map((t) => {
        const isSel = String(t.thread_id) === String(selectedId);
        return (
          <button
            key={t.thread_id}
            onClick={() => onSelect(t)}
            className={`w-full text-left px-4 py-3 transition-colors flex flex-col gap-1 ${
              isSel ? "bg-th-accent/5 border-l-2 border-l-th-accent" : "border-l-2 border-l-transparent hover:bg-th-surface2/50"
            }`}
          >
            <div className="flex items-center justify-between gap-2">
              <span className="font-medium text-th-heading truncate">{t.subject || "(no subject)"}</span>
              <StatusBadge booked={t.booked} spend={t.outcome_spend_usd} responded={t.has_response} />
            </div>
            <span className="text-xs text-th-secondary font-mono truncate">{t.from_address || t.customer_name || `customer ${t.customer_id ?? ""}`}</span>
            <div className="flex items-center gap-2 text-[10px] text-th-muted font-mono">
              <span>{t.message_count} message{t.message_count === 1 ? "" : "s"}</span>
              {t.last_direction && <span>· last: {t.last_direction}</span>}
            </div>
          </button>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Conversation (centre pane)
// ---------------------------------------------------------------------------

function MessageBubble({ msg, trace, onOpenTrace }) {
  const outbound = msg.direction === "outbound";
  return (
    <div className={`flex ${outbound ? "justify-end" : "justify-start"}`}>
      <div className={`max-w-[80%] rounded-lg border ${
        outbound ? "bg-th-accent/10 border-th-accent/20" : "bg-th-surface2 border-th-border/20"
      }`}>
        <div className="px-4 pt-3 pb-1 flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 text-[10px] font-mono uppercase tracking-wider text-th-secondary">
            <span className={outbound ? "text-th-accent" : "text-bTeal-50"}>
              {outbound ? <IconOutbound /> : <IconInbound />}
            </span>
            <span>{outbound ? "AstroTrips agent" : "Prospect"}</span>
            {msg.turn != null && <span className="text-th-muted">· turn {msg.turn}</span>}
          </div>
          {outbound && trace && (
            <button
              onClick={() => onOpenTrace(trace)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-th-accent text-th-base text-sm font-medium hover:bg-th-accent2 transition-colors flex-shrink-0"
            >
              <IconSteps /> How this was decided
            </button>
          )}
        </div>
        <div className="px-4 pb-2 text-xs text-th-muted font-mono truncate">{msg.sender}</div>
        <div className="px-4 pb-3 text-sm text-th-body whitespace-pre-wrap leading-relaxed">{msg.body}</div>
        <div className="px-4 pb-3">
          <span className="text-[10px] text-th-muted font-mono">{fmtWhen(msg.created_at)}</span>
        </div>
      </div>
    </div>
  );
}

function ConversationPane({ thread, messages, loading, tracesByTurn, looseTraces, onOpenTrace }) {
  if (!thread) {
    return (
      <div className="flex-1 flex items-center justify-center text-th-secondary">
        <p className="text-sm">Select a thread to read the exchange.</p>
      </div>
    );
  }

  return (
    <div className="flex-1 min-w-0 flex flex-col">
      <div className="px-6 py-4 border-b border-th-border/20 banner-header">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-lg font-display text-th-heading tracking-wide truncate">{thread.subject || "(no subject)"}</h2>
          <div className="flex items-center gap-2 flex-shrink-0">
            <LoyaltyChip tier={thread.loyalty_tier} />
            <StatusBadge booked={thread.booked} spend={thread.outcome_spend_usd} responded={thread.has_response} />
          </div>
        </div>
        <p className="text-xs text-th-secondary font-mono mt-1 truncate">
          {thread.customer_name ? `${thread.customer_name} · ` : ""}{thread.from_address || ""}
        </p>
        {looseTraces.length > 0 && (
          <button
            onClick={() => onOpenTrace(looseTraces[0])}
            className="mt-2 flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-th-surface3 text-th-body text-[11px] font-medium hover:bg-th-accent hover:text-th-base transition-colors"
          >
            <IconSteps /> Decision trace
          </button>
        )}
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto px-6 py-5 space-y-4">
        {loading ? (
          <div className="flex justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-th-accent" />
          </div>
        ) : messages.length === 0 ? (
          <p className="text-sm text-th-secondary text-center py-8">No messages in this thread yet.</p>
        ) : (
          messages.map((m) => (
            <MessageBubble
              key={m.message_id ?? `${m.thread_id}-${m.turn}`}
              msg={m}
              trace={m.direction === "outbound" ? tracesByTurn[m.turn] : null}
              onOpenTrace={onOpenTrace}
            />
          ))
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Decision trace sidebar (right pane)
// ---------------------------------------------------------------------------

function KeyValueList({ obj }) {
  const entries = Object.entries(obj || {}).filter(([, v]) => v !== null && v !== undefined && v !== "");
  if (entries.length === 0) return null;
  return (
    <div className="space-y-1.5">
      {entries.map(([k, v]) => (
        <div key={k} className="flex justify-between gap-3 text-xs">
          <span className="text-th-secondary font-mono">{humanize(k)}</span>
          <span className="text-th-body font-mono text-right break-words max-w-[60%]">
            {typeof v === "object" ? JSON.stringify(v) : String(v)}
          </span>
        </div>
      ))}
    </div>
  );
}

function Collapsible({ title, badge, defaultOpen = false, children }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="rounded-lg border border-th-border/20 bg-th-surface2/40 overflow-hidden">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between gap-2 px-3 py-2 text-left hover:bg-th-surface3/40 transition-colors"
      >
        <span className="flex items-center gap-2 min-w-0">{title}{badge}</span>
        <svg className={`w-4 h-4 text-th-secondary flex-shrink-0 transition-transform ${open ? "rotate-180" : ""}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="6 9 12 15 18 9" /></svg>
      </button>
      {open && <div className="px-3 pb-3 pt-1 fade-in">{children}</div>}
    </div>
  );
}

function StepOutput({ output }) {
  if (output === null || output === undefined || output === "") return null;
  if (typeof output !== "object") {
    return <p className="text-xs text-th-body whitespace-pre-wrap leading-relaxed">{String(output)}</p>;
  }
  const { email, ...rest } = output;
  return (
    <div className="space-y-2">
      {email && (
        <div className="rounded bg-th-surface3/40 border border-th-border/20 px-2.5 py-2 text-xs text-th-body whitespace-pre-wrap leading-relaxed">{email}</div>
      )}
      {Object.keys(rest).length > 0 && <KeyValueList obj={rest} />}
    </div>
  );
}

function StepCard({ step, index }) {
  if (typeof step !== "object" || step === null) {
    return (
      <Collapsible title={<span className="text-sm font-medium text-th-heading">{`Step ${index + 1}`}</span>}>
        <p className="text-sm text-th-body whitespace-pre-wrap">{String(step)}</p>
      </Collapsible>
    );
  }

  const dm = step.decision_maker || {};
  const dmType = typeof dm === "object" ? (dm.type || "") : dm;
  const dmAgent = typeof dm === "object" ? (dm.agent || "") : "";
  const style = decisionMakerStyle(dmAgent || dmType);
  const label = step.step ?? step.name ?? step.title ?? step.action ?? `Step ${index + 1}`;

  const logic = step.logic || {};
  const detail = typeof logic === "object" ? (logic.reasoning ?? logic.explanation ?? logic.detail) : logic;
  const toolCalls = typeof logic === "object" && Array.isArray(logic.tool_calls) ? logic.tool_calls : [];
  const output = step.output ?? step.result ?? step.value;

  const title = (
    <span className="flex items-center gap-2 min-w-0">
      <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: style.dot }} />
      <span className="text-sm font-medium text-th-heading truncate">{label}</span>
    </span>
  );
  return (
    <Collapsible title={title}>
      {detail && <p className="text-xs text-th-secondary mb-2 leading-relaxed whitespace-pre-wrap">{detail}</p>}
      {toolCalls.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-2">
          {toolCalls.map((t, i) => (
            <span key={i} className="px-2 py-0.5 rounded text-[10px] font-mono bg-th-surface3 text-th-body">{typeof t === "object" ? JSON.stringify(t) : String(t)}</span>
          ))}
        </div>
      )}
      <StepOutput output={output} />
    </Collapsible>
  );
}

function ContextPiece({ piece }) {
  const obj = (piece && typeof piece === "object") ? piece : { chunk_id: piece };
  const label = obj.title || obj.chunk_id || "context unit";
  return (
    <Collapsible title={<span className="text-xs font-medium text-th-body truncate">{label}</span>}>
      {obj.text ? (
        <p className="text-xs text-th-body whitespace-pre-wrap leading-relaxed">{obj.text}</p>
      ) : (
        <p className="text-xs text-th-secondary font-mono break-all">{obj.chunk_id}</p>
      )}
    </Collapsible>
  );
}

function TracePanel({ trace, onClose }) {
  const steps = Array.isArray(trace?.steps) ? trace.steps : [];
  const context = trace?.context_used;
  const contextList = Array.isArray(context) ? context : (context ? [context] : []);
  const inputs = trace?.inputs || {};
  const outcome = (trace?.outcome && typeof trace.outcome === "object") ? trace.outcome : {};

  return (
    <aside className="w-full md:w-96 flex-shrink-0 border-l border-th-border/20 bg-th-surface flex flex-col">
      <div className="px-5 py-4 border-b border-th-border/20 flex items-center justify-between banner-header">
        <div className="flex items-center gap-2 text-th-accent">
          <IconSteps />
          <h3 className="text-base font-display text-th-heading tracking-wide">How this was decided</h3>
        </div>
        <button onClick={onClose} className="p-1.5 rounded-lg text-th-secondary hover:text-th-body hover:bg-th-surface3 transition-colors" title="Close">
          <IconClose />
        </button>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto px-4 py-4 fade-in">
        {!trace ? (
          <p className="text-sm text-th-secondary">No decision trace recorded for this reply yet.</p>
        ) : (
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              {trace.turn != null && (
                <span className="px-2 py-0.5 rounded text-[10px] font-medium font-mono bg-th-surface3 text-th-body">reply turn {trace.turn}</span>
              )}
              {outcome.status && (
                <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium border ${
                  outcome.status === "sent"
                    ? "bg-bGreen-50/15 text-bGreen-50 border-bGreen-50/30"
                    : "bg-bRed-50/15 text-bRed-50 border-bRed-50/30"
                }`}>{outcome.status}</span>
              )}
            </div>

            <Collapsible title={<span className="text-sm font-medium text-th-heading">Inputs</span>}>
              {inputs.subject && (
                <p className="text-xs text-th-secondary mb-1.5"><span className="font-mono">subject:</span> {inputs.subject}</p>
              )}
              {inputs.user_request ? (
                <div className="rounded bg-th-surface2 border border-th-border/20 px-2.5 py-2 text-xs text-th-body whitespace-pre-wrap leading-relaxed">{inputs.user_request}</div>
              ) : (
                <p className="text-xs text-th-secondary">No input recorded.</p>
              )}
            </Collapsible>

            <Collapsible
              title={<span className="text-sm font-medium text-th-heading">Context used</span>}
              badge={<span className="px-1.5 py-0.5 rounded-full text-[10px] font-mono bg-th-surface3 text-th-secondary">{contextList.length}</span>}
            >
              {contextList.length === 0 ? (
                <p className="text-xs text-th-secondary">No context units recorded.</p>
              ) : (
                <div className="space-y-1.5">
                  {contextList.map((c, i) => <ContextPiece key={i} piece={c} />)}
                </div>
              )}
            </Collapsible>

            <div>
              <h4 className="text-xs font-mono text-th-secondary uppercase tracking-wider mb-2 mt-1">Steps</h4>
              {steps.length === 0 ? (
                <p className="text-xs text-th-secondary">No steps recorded.</p>
              ) : (
                <div className="space-y-2">
                  {steps.map((s, i) => <StepCard key={i} step={s} index={i} />)}
                </div>
              )}
            </div>

            {Object.keys(outcome).length > 0 && (
              <Collapsible title={<span className="text-sm font-medium text-th-heading">Outcome</span>}>
                <KeyValueList obj={outcome} />
              </Collapsible>
            )}

            {trace.trace_id && (
              <p className="text-[10px] text-th-muted font-mono break-all pt-1">trace {trace.trace_id}</p>
            )}
          </div>
        )}
      </div>
    </aside>
  );
}

// ---------------------------------------------------------------------------
// Theme helpers
// ---------------------------------------------------------------------------

function getInitialTheme() {
  try {
    const saved = localStorage.getItem("inbox-theme");
    if (saved === "light" || saved === "dark") return saved;
  } catch {}
  return window.matchMedia?.("(prefers-color-scheme: light)").matches ? "light" : "dark";
}

function applyTheme(theme) {
  if (theme === "light") document.body.classList.add("light");
  else document.body.classList.remove("light");
  try { localStorage.setItem("inbox-theme", theme); } catch {}
}

// ---------------------------------------------------------------------------
// App
// ---------------------------------------------------------------------------

function App() {
  const [threads, setThreads] = useState([]);
  const [summary, setSummary] = useState({ threads: 0, messages: 0, booked: 0, traces: 0 });
  const [selected, setSelected] = useState(null);
  const [messages, setMessages] = useState([]);
  const [traces, setTraces] = useState([]);
  const [activeTrace, setActiveTrace] = useState(null);
  const [loading, setLoading] = useState(true);
  const [threadLoading, setThreadLoading] = useState(false);
  const [error, setError] = useState(null);
  const [theme, setTheme] = useState(getInitialTheme);

  useEffect(() => { applyTheme(theme); }, [theme]);
  const toggleTheme = useCallback(() => setTheme((p) => (p === "dark" ? "light" : "dark")), []);

  const loadThreads = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [t, s] = await Promise.all([fetchJSON("threads"), fetchJSON("summary")]);
      setThreads(t);
      setSummary(s);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadThreads(); }, [loadThreads]);

  const loadThread = useCallback(async (thread) => {
    setSelected(thread);
    setActiveTrace(null);
    setThreadLoading(true);
    try {
      const [m, tr] = await Promise.all([
        fetchJSON(`threads/${encodeURIComponent(thread.thread_id)}/messages`),
        fetchJSON(`threads/${encodeURIComponent(thread.thread_id)}/traces`),
      ]);
      setMessages(m);
      setTraces(tr);
    } catch (err) {
      setMessages([]);
      setTraces([]);
      setError(err.message);
    } finally {
      setThreadLoading(false);
    }
  }, []);

  const refresh = useCallback(() => {
    loadThreads();
    if (selected) loadThread(selected);
  }, [loadThreads, loadThread, selected]);

  const tracesByTurn = useMemo(() => {
    const map = {};
    traces.forEach((tr) => { if (tr.turn != null) map[tr.turn] = tr; });
    return map;
  }, [traces]);

  const looseTraces = useMemo(() => traces.filter((tr) => tr.turn == null), [traces]);

  if (loading && threads.length === 0) {
    return (
      <div className="h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-th-accent mx-auto mb-4" />
          <p className="text-th-secondary">Loading inbox...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col">
      <header className="banner-header border-b border-th-border/20 flex-shrink-0">
        <div className="px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-gradient-to-br from-th-accent to-th-accent2 rounded-xl text-th-base">
              <IconMail />
            </div>
            <div>
              <h1 className="text-xl font-display text-th-heading tracking-wide">AstroTrips Inbox</h1>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="hidden sm:flex items-center gap-3 text-xs font-mono text-th-secondary mr-1">
              <span><span className="text-th-heading font-semibold">{summary.threads}</span> thread{summary.threads === 1 ? "" : "s"}</span>
            </div>
            <button onClick={toggleTheme} className="p-2 rounded-lg hover:bg-th-surface3 text-th-secondary hover:text-th-body transition-colors" title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}>
              {theme === "dark" ? <IconSun /> : <IconMoon />}
            </button>
            <button onClick={refresh} disabled={loading} className="p-2 rounded-lg hover:bg-th-surface3 text-th-secondary hover:text-th-body transition-colors disabled:opacity-50" title="Refresh">
              <span className={loading ? "spin inline-block" : ""}><IconRefresh /></span>
            </button>
          </div>
        </div>
      </header>

      {error && (
        <div className="mx-6 mt-3 p-3 rounded-lg bg-bRed-50/10 border border-bRed-50/30 text-bRed-50 text-sm flex-shrink-0">
          {error}
        </div>
      )}

      {threads.length === 0 ? (
        <div className="flex-1 flex items-center justify-center px-6">
          <div className="text-center max-w-md fade-in">
            <div className="inline-flex p-3 rounded-2xl bg-th-surface border border-th-border/20 text-th-secondary mb-4">
              <IconMail />
            </div>
            <p className="text-lg text-th-heading mb-2">No data yet</p>
            <p className="text-sm text-th-secondary leading-relaxed">
              Run the <code className="font-mono text-th-accent">{SETUP_DAG}</code> Dag to create the schema and seed the inbox with example data,
              then run <code className="font-mono text-th-accent">{MOCK_PROSPECT_DAG}</code> to generate a new inquiry.
            </p>
          </div>
        </div>
      ) : (
        <div className="flex-1 min-h-0 flex">
          <div className="w-72 flex-shrink-0 border-r border-th-border/20 overflow-y-auto bg-th-surface/40">
            <ThreadList threads={threads} selectedId={selected?.thread_id} onSelect={loadThread} />
          </div>

          <ConversationPane
            thread={selected}
            messages={messages}
            loading={threadLoading}
            tracesByTurn={tracesByTurn}
            looseTraces={looseTraces}
            onOpenTrace={setActiveTrace}
          />

          {activeTrace && <TracePanel trace={activeTrace} onClose={() => setActiveTrace(null)} />}
        </div>
      )}
    </div>
  );
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(React.createElement(App));
