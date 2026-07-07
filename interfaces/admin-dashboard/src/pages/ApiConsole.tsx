import React, { useEffect, useMemo, useState } from 'react';
import api, { DOCS_URL, DEFAULT_API_BASE_URL } from '../lib/api';
import { useAuth } from '../context/AuthContext';
import {
  Activity,
  AlertCircle,
  ArrowRight,
  BadgeCheck,
  BookOpen,
  CheckCircle2,
  ChevronRight,
  CircleDot,
  Copy,
  Database,
  FileText,
  KeyRound,
  Loader2,
  Play,
  Shield,
  Sparkles,
  Users,
  Waves,
} from 'lucide-react';

type HttpMethod = 'GET' | 'POST';

type ConsoleEndpoint = {
  id: string;
  group: 'System' | 'Auth' | 'Platform' | 'Content' | 'Monitoring';
  title: string;
  subtitle: string;
  description: string;
  method: HttpMethod;
  path: string;
  auth: 'none' | 'bearer';
  sampleBody?: Record<string, unknown>;
  accent: string;
  icon: React.ReactNode;
};

type ResultState = {
  title: string;
  method: HttpMethod;
  path: string;
  status: number;
  elapsedMs: number;
  body: unknown;
};

const endpoints: ConsoleEndpoint[] = [
  {
    id: 'health',
    group: 'System',
    title: 'Health check',
    subtitle: 'Deployment status',
    description: 'Confirm the live API is reachable from the browser.',
    method: 'GET',
    path: '/health',
    auth: 'none',
    accent: '#0ea5e9',
    icon: <CircleDot size={18} />,
  },
  {
    id: 'ready',
    group: 'System',
    title: 'Readiness check',
    subtitle: 'Service readiness',
    description: 'Confirm the service is ready to accept requests.',
    method: 'GET',
    path: '/ready',
    auth: 'none',
    accent: '#6366f1',
    icon: <BadgeCheck size={18} />,
  },
  {
    id: 'login',
    group: 'Auth',
    title: 'Admin login',
    subtitle: 'Token exchange',
    description: 'Exchange admin credentials for a bearer token.',
    method: 'POST',
    path: '/admin/auth/login',
    auth: 'none',
    sampleBody: { email: 'admin@example.com', password: 'change-me-immediately' },
    accent: '#db2777',
    icon: <KeyRound size={18} />,
  },
  {
    id: 'me',
    group: 'Auth',
    title: 'Current user',
    subtitle: 'Session identity',
    description: 'Show the authenticated admin profile and role set.',
    method: 'GET',
    path: '/admin/auth/me',
    auth: 'bearer',
    accent: '#f59e0b',
    icon: <Shield size={18} />,
  },
  {
    id: 'overview',
    group: 'Platform',
    title: 'Platform overview',
    subtitle: 'Live inventory',
    description: 'Summarize projects, users, queries, and health.',
    method: 'GET',
    path: '/admin/overview',
    auth: 'bearer',
    accent: '#10b981',
    icon: <Activity size={18} />,
  },
  {
    id: 'projects',
    group: 'Platform',
    title: 'Projects',
    subtitle: 'Deployed workspaces',
    description: 'Inspect all registered projects in the platform.',
    method: 'GET',
    path: '/admin/projects',
    auth: 'bearer',
    accent: '#2563eb',
    icon: <Database size={18} />,
  },
  {
    id: 'users',
    group: 'Platform',
    title: 'Users',
    subtitle: 'Operator accounts',
    description: 'Inspect admin users, roles, and memberships.',
    method: 'GET',
    path: '/admin/users',
    auth: 'bearer',
    accent: '#8b5cf6',
    icon: <Users size={18} />,
  },
  {
    id: 'audit',
    group: 'Monitoring',
    title: 'Audit trail',
    subtitle: 'Accountability log',
    description: 'Trace recent admin actions and config changes.',
    method: 'GET',
    path: '/admin/audit-logs?limit=10',
    auth: 'bearer',
    accent: '#ef4444',
    icon: <FileText size={18} />,
  },
  {
    id: 'toxicity',
    group: 'Monitoring',
    title: 'Toxicity feed',
    subtitle: 'Guardrail review',
    description: 'Inspect flagged messages from the moderation pipeline.',
    method: 'GET',
    path: '/admin/toxicity-feed?limit=10',
    auth: 'bearer',
    accent: '#f97316',
    icon: <AlertCircle size={18} />,
  },
  {
    id: 'kb',
    group: 'Content',
    title: 'Knowledge base',
    subtitle: 'Deployed content',
    description: 'List sources for the TB project and general audience.',
    method: 'GET',
    path: '/admin/projects/tb/knowledge-base?audience=general',
    auth: 'bearer',
    accent: '#14b8a6',
    icon: <BookOpen size={18} />,
  },
];

const groupedEndpoints = [
  { name: 'System', description: 'Check deployment health before any admin action.' },
  { name: 'Auth', description: 'Log in and confirm who is signed in.' },
  { name: 'Platform', description: 'Inspect what the platform already has deployed.' },
  { name: 'Content', description: 'Review the knowledge-base already attached to TB.' },
  { name: 'Monitoring', description: 'Audit logs and moderation outputs.' },
];

const ApiConsole = () => {
  const { user, login } = useAuth();
  const [email, setEmail] = useState('admin@example.com');
  const [password, setPassword] = useState('change-me-immediately');
  const [selectedId, setSelectedId] = useState('health');
  const [result, setResult] = useState<ResultState | null>(null);
  const [history, setHistory] = useState<ResultState[]>([]);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [message, setMessage] = useState('');

  useEffect(() => {
    if (user?.email) {
      setEmail(user.email);
    }
  }, [user?.email]);

  const selectedEndpoint = useMemo(
    () => endpoints.find((endpoint) => endpoint.id === selectedId) || endpoints[0],
    [selectedId],
  );

  const storeResult = (next: ResultState) => {
    setResult(next);
    setHistory((previous) => [next, ...previous].slice(0, 5));
  };

  const runEndpoint = async (endpoint: ConsoleEndpoint) => {
    setBusyId(endpoint.id);
    setMessage('');
    const startedAt = performance.now();

    try {
      let response;
      if (endpoint.id === 'login') {
        response = { status: 200, data: await login(email, password) };
      } else if (endpoint.method === 'GET') {
        response = await api.get(endpoint.path);
      } else {
        response = await api.post(endpoint.path, endpoint.sampleBody || {});
      }

      const nextResult = {
        title: endpoint.title,
        method: endpoint.method,
        path: endpoint.path,
        status: response.status,
        elapsedMs: Math.round(performance.now() - startedAt),
        body: response.data,
      };

      storeResult(nextResult);
      setMessage(endpoint.id === 'login' ? 'Login succeeded and token stored in the browser.' : `Loaded ${endpoint.title}.`);
    } catch (error: any) {
      const nextResult = {
        title: endpoint.title,
        method: endpoint.method,
        path: endpoint.path,
        status: error.response?.status || 0,
        elapsedMs: Math.round(performance.now() - startedAt),
        body: error.response?.data || { detail: error.message || 'Request failed' },
      };
      storeResult(nextResult);
      setMessage(error.response?.data?.detail || 'Request failed. Check your API host and auth token.');
    } finally {
      setBusyId(null);
    }
  };

  const copyDocs = async () => {
    await navigator.clipboard.writeText(DOCS_URL);
    setMessage('Docs URL copied to clipboard.');
  };

  const testConnection = async () => {
    await runEndpoint(endpoints[0]);
  };

  const authStatus = localStorage.getItem('admin_token') ? 'Authenticated' : 'Signed out';

  return (
    <div className="api-console">
      <section className="hero">
        <div className="hero-copy-block">
          <div className="eyebrow-row">
            <span className="eyebrow">Deployed admin surface</span>
            <span className="docs-pill"><Sparkles size={14} /> Live helpcentre</span>
          </div>
          <h1>See what is deployed and operate it from one polished dashboard.</h1>
          <p className="hero-copy">
            This is the admin workspace for the live helpcentre. It shows the deployed host, the current session state,
            and the major operator areas: auth, platform inventory, knowledge base, and monitoring.
          </p>

          <div className="hero-actions">
            <button className="primary-button" onClick={testConnection} type="button">
              <Waves size={16} />
              Check live API
            </button>
            <button className="secondary-button" onClick={copyDocs} type="button">
              <BookOpen size={16} />
              Open docs link
            </button>
          </div>

          <div className="hero-notes">
            <div className="note">
              <span className="note-label">API host</span>
              <strong>{DEFAULT_API_BASE_URL}</strong>
            </div>
            <div className="note">
              <span className="note-label">Session</span>
              <strong>{authStatus}</strong>
            </div>
            <div className="note">
              <span className="note-label">Docs</span>
              <a href={DOCS_URL} target="_blank" rel="noreferrer">/docs</a>
            </div>
          </div>
        </div>

        <div className="hero-panel card-surface">
          <div className="panel-header">
            <div>
              <p className="panel-kicker">Current identity</p>
              <h2>{user?.full_name || 'Not signed in'}</h2>
            </div>
            <div className={`status-badge ${localStorage.getItem('admin_token') ? 'active' : 'idle'}`}>
              {localStorage.getItem('admin_token') ? 'Token saved' : 'No token'}
            </div>
          </div>

          <div className="profile-stack">
            <div className="profile-chip">
              <Shield size={16} />
              <span>{user?.email || 'admin@example.com'}</span>
            </div>
            <div className="profile-chip muted">
              <Activity size={16} />
              <span>Deployed host: {DEFAULT_API_BASE_URL}</span>
            </div>
            <div className="profile-chip muted">
              <BadgeCheck size={16} />
              <span>Operator console designed for browser use</span>
            </div>
          </div>

          <div className="mini-grid">
            <div className="mini-card">
              <span>Live state</span>
              <strong>Health + readiness</strong>
            </div>
            <div className="mini-card">
              <span>Workflows</span>
              <strong>Login + inspection</strong>
            </div>
          </div>
        </div>
      </section>

      {message && <div className="notice">{message}</div>}

      <section className="operator-layout">
        <div className="left-column">
          <div className="card-surface auth-card">
            <div className="card-head">
              <div>
                <p className="card-label">Credentials</p>
                <h2>Sign in</h2>
              </div>
              <KeyRound size={18} />
            </div>
            <div className="auth-grid">
              <label className="field">
                <span>Email</span>
                <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="admin@example.com" />
              </label>
              <label className="field">
                <span>Password</span>
                <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="change-me-immediately" />
              </label>
            </div>
            <button className="primary-button full-width" onClick={() => runEndpoint(endpoints[2])} type="button">
              <Play size={16} />
              Run login
            </button>
            <p className="helper-text">
              The login response returns the bearer token and the user context that powers the rest of the dashboard.
            </p>
          </div>

          {groupedEndpoints.map((group) => (
            <div key={group.name} className="card-surface group-card">
              <div className="group-head">
                <div>
                  <p className="card-label">{group.name}</p>
                  <h2>{group.description}</h2>
                </div>
                <ChevronRight size={18} />
              </div>

              <div className="endpoint-stack">
                {endpoints
                  .filter((endpoint) => endpoint.group === group.name)
                  .map((endpoint) => (
                    <button
                      key={endpoint.id}
                      className={`endpoint-tile ${selectedId === endpoint.id ? 'active' : ''}`}
                      onClick={() => setSelectedId(endpoint.id)}
                      type="button"
                    >
                      <span className="tile-accent" style={{ background: endpoint.accent }} />
                      <div className="tile-content">
                        <div className="tile-title-row">
                          <div className="tile-title-block">
                            <div className="tile-icon" style={{ color: endpoint.accent }}>{endpoint.icon}</div>
                            <div>
                              <h3>{endpoint.title}</h3>
                              <p>{endpoint.subtitle}</p>
                            </div>
                          </div>
                          <span className={`method ${endpoint.method.toLowerCase()}`}>{endpoint.method}</span>
                        </div>
                        <div className="tile-footer">
                          <span>{endpoint.path}</span>
                          <span>{endpoint.auth === 'bearer' ? 'Bearer required' : 'Public'}</span>
                        </div>
                      </div>
                    </button>
                  ))}
              </div>
            </div>
          ))}
        </div>

        <div className="right-column">
          <div className="card-surface response-card">
            <div className="card-head">
              <div>
                <p className="card-label">Selected action</p>
                <h2>{selectedEndpoint.title}</h2>
              </div>
              <button className="ghost-button" type="button" onClick={() => runEndpoint(selectedEndpoint)} disabled={busyId === selectedEndpoint.id}>
                {busyId === selectedEndpoint.id ? <Loader2 size={16} className="spin" /> : <ArrowRight size={16} />}
                Execute
              </button>
            </div>

            <div className="selected-summary">
              <span className={`method ${selectedEndpoint.method.toLowerCase()}`}>{selectedEndpoint.method}</span>
              <div>
                <strong>{selectedEndpoint.path}</strong>
                <p>{selectedEndpoint.description}</p>
              </div>
            </div>

            <div className="result-shell">
              {result ? (
                <>
                  <div className="result-stats">
                    <div className="result-stat">
                      <span>Status</span>
                      <strong>{result.status}</strong>
                    </div>
                    <div className="result-stat">
                      <span>Elapsed</span>
                      <strong>{result.elapsedMs} ms</strong>
                    </div>
                    <div className="result-stat">
                      <span>Endpoint</span>
                      <strong>{result.method}</strong>
                    </div>
                  </div>
                  <pre className="result-body">{JSON.stringify(result.body, null, 2)}</pre>
                </>
              ) : (
                <div className="empty-state">
                  <FileText size={36} />
                  <p>Run any action to inspect the live payload here.</p>
                </div>
              )}
            </div>
          </div>

          <div className="card-surface live-card">
            <div className="card-head">
              <div>
                <p className="card-label">Live history</p>
                <h2>Recent checks</h2>
              </div>
              <Copy size={18} onClick={() => navigator.clipboard.writeText(DOCS_URL)} />
            </div>

            <div className="history-list">
              {history.length > 0 ? history.map((entry, index) => (
                <div key={`${entry.path}-${index}`} className="history-item">
                  <div className={`history-dot ${entry.status >= 400 ? 'warn' : 'ok'}`} />
                  <div className="history-content">
                    <strong>{entry.title}</strong>
                    <span>{entry.method} {entry.path}</span>
                  </div>
                  <span className="history-meta">{entry.status}</span>
                </div>
              )) : (
                <div className="history-empty">
                  <CheckCircle2 size={28} />
                  <p>No checks yet. Start with health or login.</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </section>

      <style>{`
        .api-console {
          display: flex;
          flex-direction: column;
          gap: 1.25rem;
          color: #0f172a;
        }
        .hero {
          display: grid;
          grid-template-columns: minmax(0, 1.5fr) minmax(320px, 0.85fr);
          gap: 1rem;
        }
        .hero-copy-block,
        .card-surface {
          background: linear-gradient(180deg, rgba(255,255,255,0.96), rgba(248,250,252,0.94));
          border: 1px solid rgba(148,163,184,0.18);
          border-radius: 24px;
          box-shadow: 0 24px 60px rgba(15,23,42,0.08);
          backdrop-filter: blur(12px);
        }
        .hero-copy-block {
          padding: 1.6rem;
        }
        .eyebrow-row,
        .panel-header,
        .card-head,
        .group-head,
        .tile-title-row,
        .hero-actions,
        .hero-notes,
        .result-stats,
        .history-item,
        .selected-summary {
          display: flex;
          align-items: center;
          gap: 0.9rem;
        }
        .eyebrow-row,
        .panel-header,
        .card-head,
        .group-head,
        .tile-title-row {
          justify-content: space-between;
        }
        .eyebrow {
          text-transform: uppercase;
          letter-spacing: 0.12em;
          font-size: 0.72rem;
          font-weight: 800;
          color: #2563eb;
        }
        .docs-pill,
        .status-badge,
        .method,
        .profile-chip,
        .note,
        .mini-card,
        .history-meta {
          border-radius: 999px;
          padding: 0.35rem 0.7rem;
          font-size: 0.78rem;
          font-weight: 800;
          background: #f1f5f9;
          color: #334155;
        }
        .docs-pill {
          display: inline-flex;
          align-items: center;
          gap: 0.4rem;
        }
        .status-badge.active {
          background: #dcfce7;
          color: #166534;
        }
        .status-badge.idle {
          background: #fee2e2;
          color: #991b1b;
        }
        .hero h1 {
          margin: 0.75rem 0 0.85rem;
          font-size: clamp(2.2rem, 4vw, 4rem);
          line-height: 1;
          letter-spacing: -0.04em;
        }
        .hero-copy {
          max-width: 70ch;
          margin: 0;
          color: #475569;
          font-size: 1rem;
          line-height: 1.7;
        }
        .hero-actions {
          margin-top: 1.25rem;
          flex-wrap: wrap;
        }
        .primary-button,
        .secondary-button,
        .ghost-button {
          border: none;
          border-radius: 14px;
          font-weight: 800;
          cursor: pointer;
          transition: transform 0.15s ease, box-shadow 0.15s ease, opacity 0.15s ease;
          display: inline-flex;
          align-items: center;
          gap: 0.55rem;
          justify-content: center;
        }
        .primary-button {
          padding: 0.9rem 1.1rem;
          background: linear-gradient(135deg, #2563eb, #1d4ed8);
          color: white;
          box-shadow: 0 16px 30px rgba(37, 99, 235, 0.24);
        }
        .secondary-button,
        .ghost-button {
          padding: 0.85rem 1rem;
          background: rgba(226,232,240,0.7);
          color: #0f172a;
        }
        .primary-button:hover,
        .secondary-button:hover,
        .ghost-button:hover {
          transform: translateY(-1px);
        }
        .primary-button:disabled,
        .ghost-button:disabled {
          opacity: 0.7;
          cursor: not-allowed;
        }
        .full-width {
          width: 100%;
        }
        .hero-notes {
          margin-top: 1.2rem;
          flex-wrap: wrap;
        }
        .note,
        .profile-chip,
        .mini-card {
          display: inline-flex;
          align-items: center;
          gap: 0.5rem;
          background: rgba(241,245,249,0.9);
          border: 1px solid rgba(148,163,184,0.18);
          border-radius: 16px;
        }
        .note {
          padding: 0.75rem 0.85rem;
          flex-direction: column;
          align-items: flex-start;
          min-width: 180px;
        }
        .note-label,
        .panel-kicker,
        .card-label {
          text-transform: uppercase;
          letter-spacing: 0.12em;
          font-size: 0.7rem;
          font-weight: 800;
          color: #64748b;
        }
        .note a {
          color: #2563eb;
          font-weight: 800;
          text-decoration: none;
        }
        .hero-panel {
          padding: 1.4rem;
        }
        .hero-panel h2,
        .card-surface h2 {
          margin: 0.2rem 0 0;
          font-size: 1.05rem;
        }
        .profile-stack,
        .endpoint-stack,
        .history-list {
          display: flex;
          flex-direction: column;
          gap: 0.75rem;
        }
        .profile-stack {
          margin-top: 1rem;
        }
        .profile-chip {
          border-radius: 16px;
          padding: 0.85rem 0.95rem;
          justify-content: flex-start;
          width: 100%;
        }
        .profile-chip.muted {
          color: #475569;
          font-weight: 700;
        }
        .mini-grid {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 0.75rem;
          margin-top: 1rem;
        }
        .mini-card {
          padding: 0.85rem;
          border-radius: 18px;
          display: flex;
          flex-direction: column;
          align-items: flex-start;
          gap: 0.25rem;
        }
        .mini-card span {
          color: #64748b;
          font-size: 0.75rem;
        }
        .mini-card strong {
          color: #0f172a;
        }
        .notice {
          padding: 0.95rem 1rem;
          border-radius: 16px;
          background: linear-gradient(135deg, #ecfeff, #eff6ff);
          border: 1px solid #bae6fd;
          color: #0f766e;
          font-weight: 700;
        }
        .operator-layout {
          display: grid;
          grid-template-columns: minmax(0, 0.96fr) minmax(0, 1.04fr);
          gap: 1rem;
          align-items: start;
        }
        .left-column,
        .right-column {
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }
        .card-surface {
          padding: 1.2rem;
        }
        .field {
          display: flex;
          flex-direction: column;
          gap: 0.45rem;
        }
        .field span,
        .helper-text,
        .tile-footer,
        .selected-summary p,
        .history-content span {
          color: #64748b;
          font-size: 0.85rem;
        }
        .field input {
          padding: 0.88rem 0.95rem;
          border-radius: 14px;
          border: 1px solid #cbd5e1;
          background: rgba(255,255,255,0.95);
          font-size: 0.95rem;
          outline: none;
        }
        .field input:focus {
          border-color: #60a5fa;
          box-shadow: 0 0 0 4px rgba(96, 165, 250, 0.14);
        }
        .auth-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 0.85rem;
          margin-bottom: 1rem;
        }
        .group-card h2 {
          max-width: 28ch;
        }
        .endpoint-tile {
          position: relative;
          width: 100%;
          border: 1px solid #e2e8f0;
          border-radius: 20px;
          background: rgba(255,255,255,0.9);
          padding: 0;
          display: flex;
          overflow: hidden;
          text-align: left;
          cursor: pointer;
        }
        .endpoint-tile.active {
          border-color: #93c5fd;
          box-shadow: 0 12px 24px rgba(37, 99, 235, 0.12);
        }
        .tile-accent {
          width: 10px;
          flex-shrink: 0;
        }
        .tile-content {
          padding: 0.95rem;
          flex: 1;
        }
        .tile-title-block {
          display: flex;
          align-items: center;
          gap: 0.85rem;
        }
        .tile-icon {
          width: 38px;
          height: 38px;
          border-radius: 12px;
          background: #f8fafc;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
        }
        .tile-title-block h3 {
          margin: 0;
          font-size: 0.98rem;
        }
        .tile-title-block p {
          margin: 0.15rem 0 0;
          color: #64748b;
          font-size: 0.82rem;
        }
        .tile-footer {
          margin-top: 0.8rem;
          display: flex;
          justify-content: space-between;
          gap: 1rem;
          font-size: 0.78rem;
        }
        .method {
          min-width: 58px;
          height: 28px;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          border-radius: 999px;
          color: white;
          font-size: 0.72rem;
          letter-spacing: 0.04em;
          flex-shrink: 0;
        }
        .method.get {
          background: linear-gradient(135deg, #0ea5e9, #2563eb);
        }
        .method.post {
          background: linear-gradient(135deg, #db2777, #7c3aed);
        }
        .response-card {
          min-height: 520px;
        }
        .selected-summary {
          padding: 0.85rem 0;
          border-top: 1px solid rgba(148,163,184,0.16);
          border-bottom: 1px solid rgba(148,163,184,0.16);
          margin: 0.75rem 0 1rem;
          align-items: start;
        }
        .selected-summary div {
          display: flex;
          flex-direction: column;
          gap: 0.2rem;
        }
        .selected-summary strong {
          font-size: 0.98rem;
        }
        .result-shell {
          min-height: 330px;
          display: flex;
          flex-direction: column;
          gap: 0.9rem;
        }
        .result-stats {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 0.75rem;
        }
        .result-stat {
          background: rgba(241,245,249,0.9);
          border: 1px solid rgba(148,163,184,0.18);
          border-radius: 16px;
          padding: 0.8rem;
          display: flex;
          flex-direction: column;
          gap: 0.25rem;
        }
        .result-stat span,
        .history-content span {
          font-size: 0.75rem;
          text-transform: uppercase;
          letter-spacing: 0.08em;
        }
        .result-stat strong {
          color: #0f172a;
          font-size: 0.95rem;
        }
        .result-body {
          flex: 1;
          margin: 0;
          border-radius: 20px;
          background: #0b1220;
          color: #dbeafe;
          padding: 1rem;
          overflow: auto;
          font-size: 0.82rem;
          line-height: 1.65;
        }
        .empty-state,
        .history-empty {
          min-height: 240px;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          gap: 0.75rem;
          color: #64748b;
          text-align: center;
          border: 1px dashed #cbd5e1;
          border-radius: 20px;
        }
        .history-list {
          margin-top: 0.5rem;
        }
        .history-item {
          align-items: center;
          padding: 0.9rem;
          border-radius: 16px;
          background: rgba(248,250,252,0.92);
          border: 1px solid rgba(148,163,184,0.16);
        }
        .history-dot {
          width: 10px;
          height: 10px;
          border-radius: 50%;
          flex-shrink: 0;
        }
        .history-dot.ok {
          background: #10b981;
        }
        .history-dot.warn {
          background: #ef4444;
        }
        .history-content {
          flex: 1;
          display: flex;
          flex-direction: column;
          gap: 0.2rem;
        }
        .helper-text {
          margin: 0.85rem 0 0;
          line-height: 1.6;
        }
        .spin {
          animation: spin 1s linear infinite;
        }
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        @media (max-width: 1100px) {
          .hero,
          .operator-layout {
            grid-template-columns: 1fr;
          }
        }
        @media (max-width: 720px) {
          .auth-grid,
          .mini-grid,
          .result-stats {
            grid-template-columns: 1fr;
          }
          .tile-title-row,
          .card-head,
          .group-head,
          .selected-summary,
          .history-item {
            flex-direction: column;
            align-items: flex-start;
          }
        }
      `}</style>
    </div>
  );
};

export default ApiConsole;