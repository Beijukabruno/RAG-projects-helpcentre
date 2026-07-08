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
  id: string;
  group: ConsoleEndpoint['group'];
  title: string;
  method: HttpMethod;
  path: string;
  auth: 'none' | 'bearer';
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
        id: endpoint.id,
        group: endpoint.group,
        title: endpoint.title,
        method: endpoint.method,
        path: endpoint.path,
        auth: endpoint.auth,
        status: response.status,
        elapsedMs: Math.round(performance.now() - startedAt),
        body: response.data,
      };

      storeResult(nextResult);
      setMessage(endpoint.id === 'login' ? 'Login succeeded and token stored in the browser.' : `Loaded ${endpoint.title}.`);
    } catch (error: any) {
      const nextResult = {
        id: endpoint.id,
        group: endpoint.group,
        title: endpoint.title,
        method: endpoint.method,
        path: endpoint.path,
        auth: endpoint.auth,
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
  const selectedRequestBody = selectedEndpoint.sampleBody ? JSON.stringify(selectedEndpoint.sampleBody, null, 2) : '';

  const isRecord = (value: unknown): value is Record<string, unknown> =>
    typeof value === 'object' && value !== null && !Array.isArray(value);

  const toDisplayText = (value: unknown, fallback = 'N/A'): string => {
    if (typeof value === 'string') {
      return value || fallback;
    }
    if (typeof value === 'number' || typeof value === 'boolean') {
      return String(value);
    }
    return fallback;
  };

  const renderKeyValue = (label: string, value: React.ReactNode, accentClass?: string) => (
    <div className={`kv-card ${accentClass || ''}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );

  const renderResultDetails = () => {
    if (!result) {
      return (
        <div className="empty-response">
          <FileText size={36} />
          <h3>Run an operation to see a structured response.</h3>
          <p>Use the controls on the left to exercise the live admin API and inspect the actual payloads here.</p>
        </div>
      );
    }

    const data = result.body;
    const isSuccess = result.status > 0 && result.status < 400;

    if (result.id === 'login' && isRecord(data)) {
      const user = isRecord(data.user) ? data.user : null;

      return (
        <div className="response-stack">
          <div className={`response-banner ${isSuccess ? 'success' : 'error'}`}>
            <CheckCircle2 size={18} />
            <div>
              <strong>{isSuccess ? 'Login succeeded' : 'Login failed'}</strong>
              <p>The console stored the bearer token in the browser and returned the signed-in user profile.</p>
            </div>
          </div>

          <div className="stats-grid">
            {renderKeyValue('Token type', String(data.token_type || 'bearer'))}
            {renderKeyValue('Token preview', typeof data.access_token === 'string' ? `${data.access_token.slice(0, 16)}…${data.access_token.slice(-8)}` : 'N/A')}
            {renderKeyValue('User role', Array.isArray(user?.roles) ? user.roles.join(', ') : 'N/A')}
            {renderKeyValue('Projects', Array.isArray(user?.project_ids) ? user.project_ids.length : 0)}
          </div>

          <div className="detail-grid">
            <div className="detail-panel">
              <h3>Signed-in user</h3>
              <div className="detail-lines">
                <div><span>Name</span><strong>{toDisplayText(user?.full_name)}</strong></div>
                <div><span>Email</span><strong>{toDisplayText(user?.email)}</strong></div>
                <div><span>Roles</span><strong>{Array.isArray(user?.roles) ? user.roles.join(', ') : 'N/A'}</strong></div>
              </div>
            </div>
            <div className="detail-panel code-panel">
              <h3>Raw response</h3>
              <pre>{JSON.stringify(data, null, 2)}</pre>
            </div>
          </div>
        </div>
      );
    }

    if (result.id === 'overview' && isRecord(data)) {
      const health = isRecord(data.system_health) ? data.system_health : null;
      const database = isRecord(health?.database) ? health.database : null;
      const databaseAvailable = typeof database?.available === 'boolean' ? database.available : false;
      return (
        <div className="response-stack">
          <div className="stats-grid">
            {renderKeyValue('Projects', toDisplayText(data.total_projects))}
            {renderKeyValue('Users', toDisplayText(data.total_users))}
            {renderKeyValue('Messages', toDisplayText(data.total_messages))}
            {renderKeyValue('Toxic messages', toDisplayText(data.toxic_messages), 'warn')}
          </div>
          <div className="detail-grid">
            <div className="detail-panel">
              <h3>System health</h3>
              <div className="detail-lines">
                <div><span>Database</span><strong>{databaseAvailable ? 'Available' : 'Unavailable'}</strong></div>
                <div><span>Reason</span><strong>{toDisplayText(database?.reason, 'None reported')}</strong></div>
                <div><span>Last audit</span><strong>{toDisplayText(health?.last_audit, 'Not available')}</strong></div>
              </div>
            </div>
            <div className="detail-panel code-panel">
              <h3>Raw response</h3>
              <pre>{JSON.stringify(data, null, 2)}</pre>
            </div>
          </div>
        </div>
      );
    }

    if (result.id === 'projects' && isRecord(data)) {
      const projects = Array.isArray(data.projects) ? data.projects : [];
      return (
        <div className="response-stack">
          <div className="stats-grid">
            {renderKeyValue('Projects returned', projects.length)}
            {renderKeyValue('Response shape', 'projects[]')}
            {renderKeyValue('Auth', result.auth === 'bearer' ? 'Bearer' : 'Public')}
            {renderKeyValue('Latency', `${result.elapsedMs} ms`)}
          </div>
          <div className="list-panel">
            {projects.map((project: any) => (
              <div key={project.id} className="list-item card-item">
                <div>
                  <strong>{project.name || project.id}</strong>
                  <p>{project.description || 'No description provided.'}</p>
                </div>
                <div className="pill-row">
                  <span className="pill">{project.id}</span>
                  <span className="pill">{project.enabled ? 'Enabled' : 'Disabled'}</span>
                </div>
              </div>
            ))}
            {projects.length === 0 && <div className="empty-inline">No projects were returned by the API.</div>}
          </div>
        </div>
      );
    }

    if (result.id === 'users' && isRecord(data)) {
      const users = Array.isArray(data.users) ? data.users : [];
      return (
        <div className="response-stack">
          <div className="stats-grid">
            {renderKeyValue('Users returned', users.length)}
            {renderKeyValue('Role scope', 'Admin access')}
            {renderKeyValue('Auth', result.auth === 'bearer' ? 'Bearer' : 'Public')}
            {renderKeyValue('Latency', `${result.elapsedMs} ms`)}
          </div>
          <div className="list-panel">
            {users.map((entry: any) => (
              <div key={entry.id} className="list-item card-item">
                <div>
                  <strong>{entry.full_name || entry.email}</strong>
                  <p>{entry.email}</p>
                </div>
                <div className="pill-row">
                  <span className="pill">{Array.isArray(entry.roles) ? entry.roles.join(', ') : 'No roles'}</span>
                  <span className="pill">{Array.isArray(entry.project_ids) ? `${entry.project_ids.length} projects` : '0 projects'}</span>
                </div>
              </div>
            ))}
            {users.length === 0 && <div className="empty-inline">No users were returned by the API.</div>}
          </div>
        </div>
      );
    }

    if (result.id === 'audit' && isRecord(data)) {
      const logs = Array.isArray(data.logs) ? data.logs : [];
      return (
        <div className="response-stack">
          <div className="stats-grid">
            {renderKeyValue('Log entries', logs.length)}
            {renderKeyValue('Audience', 'Operational trace')}
            {renderKeyValue('Auth', result.auth === 'bearer' ? 'Bearer' : 'Public')}
            {renderKeyValue('Latency', `${result.elapsedMs} ms`)}
          </div>
          <div className="list-panel">
            {logs.map((entry: any) => (
              <div key={entry.id} className="list-item card-item">
                <div>
                  <strong>{entry.action}</strong>
                  <p>{entry.actor_email} · {entry.entity_type || 'entity'}{entry.entity_id ? ` · ${entry.entity_id}` : ''}</p>
                </div>
                <div className="pill-row">
                  <span className="pill">{entry.project_id || 'global'}</span>
                  <span className="pill">{entry.created_at ? new Date(entry.created_at).toLocaleString() : 'No timestamp'}</span>
                </div>
              </div>
            ))}
            {logs.length === 0 && <div className="empty-inline">No audit logs were returned by the API.</div>}
          </div>
        </div>
      );
    }

    if (result.id === 'toxicity' && isRecord(data)) {
      const messages = Array.isArray(data.messages) ? data.messages : [];
      return (
        <div className="response-stack">
          <div className="stats-grid">
            {renderKeyValue('Flagged messages', messages.length)}
            {renderKeyValue('Review mode', 'Guardrail output')}
            {renderKeyValue('Auth', result.auth === 'bearer' ? 'Bearer' : 'Public')}
            {renderKeyValue('Latency', `${result.elapsedMs} ms`)}
          </div>
          <div className="list-panel">
            {messages.map((entry: any) => (
              <div key={entry.id} className="list-item card-item toxicity-item">
                <div>
                  <strong>{entry.project_id}</strong>
                  <p>{entry.message}</p>
                </div>
                <div className="pill-row">
                  <span className="pill danger">Toxic</span>
                  <span className="pill">{entry.created_at ? new Date(entry.created_at).toLocaleString() : 'No timestamp'}</span>
                </div>
                <pre>{JSON.stringify(entry.toxicity, null, 2)}</pre>
              </div>
            ))}
            {messages.length === 0 && <div className="empty-inline">No toxicity alerts were returned by the API.</div>}
          </div>
        </div>
      );
    }

    if (result.id === 'kb' && isRecord(data)) {
      const sources = Array.isArray(data.sources) ? data.sources : [];
      const assets = Array.isArray(data.assets) ? data.assets : [];
      return (
        <div className="response-stack">
          <div className="stats-grid">
            {renderKeyValue('Sources', sources.length)}
            {renderKeyValue('Assets', assets.length)}
            {renderKeyValue('Audience', selectedEndpoint.path.includes('clinicians') ? 'Clinicians' : 'General')}
            {renderKeyValue('Latency', `${result.elapsedMs} ms`)}
          </div>
          <div className="detail-grid">
            <div className="detail-panel">
              <h3>Sources</h3>
              <div className="list-panel compact">
                {sources.map((source: any, index: number) => (
                  <div key={`${source.source_name || 'source'}-${index}`} className="list-item card-item">
                    <div>
                      <strong>{source.source_name || 'Untitled source'}</strong>
                      <p>{source.source_file || source.source_url || 'No file or URL provided.'}</p>
                    </div>
                  </div>
                ))}
                {sources.length === 0 && <div className="empty-inline">No sources were returned by the API.</div>}
              </div>
            </div>
            <div className="detail-panel code-panel">
              <h3>Assets payload</h3>
              <pre>{JSON.stringify(assets, null, 2)}</pre>
            </div>
          </div>
        </div>
      );
    }

    return (
      <div className="detail-grid">
        <div className="detail-panel code-panel full-span">
          <h3>Raw response</h3>
          <pre>{JSON.stringify(data, null, 2)}</pre>
        </div>
      </div>
    );
  };

  return (
    <div className="api-console-shell">
      <section className="console-hero">
        <div className="hero-copy-block glass-panel">
          <div className="eyebrow-row">
            <span className="eyebrow">Admin operations studio</span>
            <span className="docs-pill"><Sparkles size={14} /> Live helpcentre</span>
          </div>
          <h1>Operate the platform from a real control room, not a ping tester.</h1>
          <p className="hero-copy">
            Sign in, inspect the deployed inventory, and run workflows that expose the actual payloads behind each
            admin action. Each response is rendered as a readable operational summary, with raw JSON available only as
            backup.
          </p>

          <div className="hero-actions">
            <button className="primary-button" onClick={testConnection} type="button">
              <Waves size={16} />
              Check live API
            </button>
            <button className="secondary-button" onClick={copyDocs} type="button">
              <BookOpen size={16} />
              Copy docs link
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
              <a href={DOCS_URL} target="_blank" rel="noreferrer">Open docs</a>
            </div>
          </div>
        </div>

        <div className="hero-panel glass-panel">
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
              <span>Operator workspace for live admin tasks</span>
            </div>
          </div>

          <div className="mini-grid">
            <div className="mini-card">
              <span>Surface</span>
              <strong>Auth · Platform · Monitoring</strong>
            </div>
            <div className="mini-card">
              <span>Response mode</span>
              <strong>Structured summaries</strong>
            </div>
          </div>
        </div>
      </section>

      {message && <div className="notice">{message}</div>}

      <section className="workspace-grid">
        <aside className="sidebar-stack">
          <div className="glass-panel auth-panel">
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
              The login response should return the bearer token and the user context that powers the rest of the admin
              UI.
            </p>
          </div>

          {groupedEndpoints.map((group) => (
            <div key={group.name} className="glass-panel group-card">
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
                        <p className="tile-description">{endpoint.description}</p>
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
        </aside>

        <main className="main-stack">
          <div className="glass-panel response-panel">
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

            <div className="request-response-grid">
              <div className="request-panel">
                <div className="subpanel-head">
                  <div>
                    <p className="card-label">Request preview</p>
                    <h3>How this action will run</h3>
                  </div>
                  <span className="pill muted">{selectedEndpoint.auth === 'bearer' ? 'Bearer required' : 'Public endpoint'}</span>
                </div>
                <div className="request-details">
                  <div><span>Method</span><strong>{selectedEndpoint.method}</strong></div>
                  <div><span>Path</span><strong>{selectedEndpoint.path}</strong></div>
                  <div><span>Group</span><strong>{selectedEndpoint.group}</strong></div>
                </div>
                {selectedRequestBody ? (
                  <div className="request-body-card">
                    <span>Sample payload</span>
                    <pre>{selectedRequestBody}</pre>
                  </div>
                ) : (
                  <div className="request-body-card empty">
                    <span>No request body is needed for this action.</span>
                  </div>
                )}
              </div>

              <div className="result-panel">
                <div className="subpanel-head">
                  <div>
                    <p className="card-label">Result view</p>
                    <h3>{result ? result.title : 'Awaiting execution'}</h3>
                  </div>
                  {result && (
                    <span className={`result-status ${result.status >= 400 ? 'warn' : 'ok'}`}>
                      {result.status || 'N/A'} · {result.elapsedMs} ms
                    </span>
                  )}
                </div>
                {renderResultDetails()}
              </div>
            </div>
          </div>

          <div className="glass-panel history-panel">
            <div className="card-head">
              <div>
                <p className="card-label">Live history</p>
                <h2>Recent checks</h2>
              </div>
              <button className="ghost-button compact" type="button" onClick={() => navigator.clipboard.writeText(DOCS_URL)}>
                <Copy size={16} />
                Copy docs
              </button>
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
        </main>
      </section>

      <style>{`
        .api-console-shell {
          display: flex;
          flex-direction: column;
          gap: 1.2rem;
          color: #0f172a;
          background:
            radial-gradient(circle at top left, rgba(37, 99, 235, 0.12), transparent 34%),
            radial-gradient(circle at top right, rgba(14, 165, 233, 0.1), transparent 28%),
            linear-gradient(180deg, #f8fbff 0%, #eef4fb 100%);
          min-height: calc(100vh - 4rem);
          padding: 1rem;
          border-radius: 28px;
        }
        .console-hero {
          display: grid;
          grid-template-columns: minmax(0, 1.5fr) minmax(320px, 0.85fr);
          gap: 1rem;
        }
        .workspace-grid {
          display: grid;
          grid-template-columns: minmax(320px, 0.92fr) minmax(0, 1.08fr);
          gap: 1rem;
          align-items: start;
        }
        .sidebar-stack,
        .main-stack {
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }
        .glass-panel {
          background: linear-gradient(180deg, rgba(255,255,255,0.98), rgba(248,250,252,0.95));
          border: 1px solid rgba(148,163,184,0.18);
          border-radius: 26px;
          box-shadow: 0 24px 60px rgba(15,23,42,0.08);
          backdrop-filter: blur(14px);
        }
        .hero-copy-block,
        .hero-panel,
        .auth-panel,
        .group-card,
        .response-panel,
        .history-panel {
          padding: 1.25rem;
        }
        .eyebrow-row,
        .panel-header,
        .card-head,
        .group-head,
        .tile-title-row,
        .hero-actions,
        .hero-notes,
        .selected-summary,
        .subpanel-head,
        .history-item,
        .request-details {
          display: flex;
          align-items: center;
          gap: 0.9rem;
        }
        .eyebrow-row,
        .panel-header,
        .card-head,
        .group-head,
        .tile-title-row,
        .subpanel-head {
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
        .pill,
        .history-meta,
        .result-status {
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
        .status-badge.active,
        .result-status.ok {
          background: #dcfce7;
          color: #166534;
        }
        .status-badge.idle,
        .result-status.warn {
          background: #fee2e2;
          color: #991b1b;
        }
        .hero h1 {
          margin: 0.75rem 0 0.85rem;
          font-size: clamp(2.1rem, 4vw, 3.7rem);
          line-height: 1;
          letter-spacing: -0.04em;
        }
        .hero-copy {
          max-width: 72ch;
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
          padding: 0.95rem 1.15rem;
          background: linear-gradient(135deg, #2563eb, #1d4ed8);
          color: white;
          box-shadow: 0 16px 30px rgba(37, 99, 235, 0.24);
        }
        .secondary-button,
        .ghost-button {
          padding: 0.9rem 1rem;
          background: rgba(226,232,240,0.75);
          color: #0f172a;
        }
        .ghost-button.compact {
          padding: 0.7rem 0.9rem;
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
        .mini-card,
        .pill,
        .result-status {
          display: inline-flex;
          align-items: center;
          gap: 0.5rem;
          background: rgba(241,245,249,0.9);
          border: 1px solid rgba(148,163,184,0.18);
        }
        .note {
          padding: 0.75rem 0.85rem;
          flex-direction: column;
          align-items: flex-start;
          min-width: 180px;
        }
        .note-label,
        .panel-kicker,
        .card-label,
        .subpanel-head h3,
        .request-body-card span,
        .detail-panel h3 {
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
        .hero-panel h2,
        .card-head h2,
        .group-head h2,
        .subpanel-head h3 {
          margin: 0.2rem 0 0;
        }
        .profile-stack,
        .endpoint-stack,
        .history-list,
        .list-panel,
        .response-stack {
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
        .mini-card span,
        .field span,
        .helper-text,
        .tile-footer,
        .tile-description,
        .selected-summary p,
        .history-content span,
        .request-details span,
        .detail-lines span,
        .kv-card span {
          color: #64748b;
          font-size: 0.85rem;
        }
        .mini-card strong,
        .kv-card strong,
        .detail-lines strong,
        .request-details strong {
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
        .field {
          display: flex;
          flex-direction: column;
          gap: 0.45rem;
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
        .tile-description {
          margin: 0.65rem 0 0;
          line-height: 1.5;
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
        .request-response-grid {
          display: grid;
          grid-template-columns: minmax(0, 0.95fr) minmax(0, 1.05fr);
          gap: 1rem;
          align-items: start;
        }
        .request-panel,
        .result-panel {
          background: rgba(248,250,252,0.9);
          border: 1px solid rgba(148,163,184,0.16);
          border-radius: 22px;
          padding: 1rem;
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
        .request-details {
          flex-wrap: wrap;
          align-items: stretch;
          margin-bottom: 0.9rem;
        }
        .request-details div {
          flex: 1 1 140px;
          padding: 0.85rem;
          border-radius: 16px;
          background: rgba(255,255,255,0.92);
          border: 1px solid rgba(148,163,184,0.18);
          display: flex;
          flex-direction: column;
          gap: 0.25rem;
        }
        .request-body-card {
          border-radius: 18px;
          border: 1px solid rgba(148,163,184,0.18);
          background: rgba(255,255,255,0.92);
          padding: 0.9rem;
        }
        .request-body-card.empty {
          color: #64748b;
        }
        .request-body-card pre,
        .code-panel pre,
        .toxicity-item pre {
          margin: 0.65rem 0 0;
          border-radius: 16px;
          background: #0b1220;
          color: #dbeafe;
          padding: 1rem;
          overflow: auto;
          font-size: 0.82rem;
          line-height: 1.65;
          white-space: pre-wrap;
          word-break: break-word;
        }
        .stats-grid {
          display: grid;
          grid-template-columns: repeat(4, minmax(0, 1fr));
          gap: 0.75rem;
        }
        .kv-card {
          border-radius: 16px;
          padding: 0.85rem;
          display: flex;
          flex-direction: column;
          gap: 0.25rem;
          background: rgba(255,255,255,0.92);
          border: 1px solid rgba(148,163,184,0.16);
        }
        .kv-card.warn {
          background: #fff7ed;
          border-color: #fdba74;
        }
        .detail-grid {
          display: grid;
          grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
          gap: 0.75rem;
        }
        .detail-panel,
        .code-panel,
        .list-item.card-item {
          border-radius: 18px;
          border: 1px solid rgba(148,163,184,0.18);
          background: rgba(255,255,255,0.94);
          padding: 0.95rem;
        }
        .detail-lines {
          display: flex;
          flex-direction: column;
          gap: 0.65rem;
          margin-top: 0.7rem;
        }
        .detail-lines div {
          display: flex;
          flex-direction: column;
          gap: 0.15rem;
        }
        .code-panel pre {
          min-height: 260px;
        }
        .list-panel.compact {
          gap: 0.55rem;
        }
        .list-item {
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          gap: 0.8rem;
        }
        .list-item strong {
          display: block;
          margin-bottom: 0.15rem;
        }
        .list-item p {
          color: #64748b;
          font-size: 0.85rem;
          margin: 0;
        }
        .pill-row {
          display: flex;
          flex-wrap: wrap;
          gap: 0.45rem;
          justify-content: flex-end;
        }
        .pill.muted {
          background: #e2e8f0;
          color: #475569;
        }
        .pill.danger {
          background: #fee2e2;
          color: #991b1b;
        }
        .toxicity-item {
          display: flex;
          flex-direction: column;
        }
        .toxicity-item pre {
          min-height: 120px;
        }
        .empty-response,
        .history-empty,
        .empty-inline {
          min-height: 220px;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          gap: 0.75rem;
          color: #64748b;
          text-align: center;
          border: 1px dashed #cbd5e1;
          border-radius: 20px;
          padding: 1.5rem;
        }
        .empty-response h3,
        .empty-inline {
          margin: 0;
        }
        .empty-response p {
          margin: 0;
          max-width: 42ch;
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
        @media (max-width: 1180px) {
          .console-hero,
          .workspace-grid,
          .request-response-grid,
          .detail-grid {
            grid-template-columns: 1fr;
          }
        }
        @media (max-width: 720px) {
          .auth-grid,
          .mini-grid,
          .stats-grid {
            grid-template-columns: 1fr;
          }
          .tile-title-row,
          .card-head,
          .group-head,
          .selected-summary,
          .history-item,
          .subpanel-head,
          .request-details,
          .list-item {
            flex-direction: column;
            align-items: flex-start;
          }
          .pill-row {
            justify-content: flex-start;
          }
          .api-console-shell {
            padding: 0.75rem;
            border-radius: 20px;
          }
        }
      `}</style>
    </div>
  );
};

export default ApiConsole;