import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../lib/api';
import { useAuth } from '../context/AuthContext';
import {
  Activity,
  AlertCircle,
  ArrowRight,
  BookOpen,
  ChevronRight,
  CircleDot,
  Database,
  FileText,
  FolderKanban,
  LayoutGrid,
  ShieldAlert,
  Sparkles,
  TrendingUp,
  Users,
} from 'lucide-react';
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

type Audience = 'general' | 'clinicians';

type Project = {
  id: string;
  name: string;
  description?: string;
  domain_owner?: string;
  contact_email?: string;
  enabled: boolean;
  status: string;
  config_json?: Record<string, unknown> | null;
  audiences: string[];
};

type ProjectWithOverview = Project & {
  overview?: ProjectOverview | null;
};

type ProjectOverview = {
  project_id: string;
  project_name: string;
  total_user_messages: number;
  average_rating: number;
  total_sources: number;
  active_ingestion_jobs: number;
  activity_data: { date: string; count: number }[];
  recent_audit_logs: AuditLog[];
};

type PlatformOverview = {
  total_projects: number;
  total_users: number;
  total_messages: number;
  toxic_messages: number;
  system_health: {
    database: { available: boolean; reason: string | null };
    last_audit: string | null;
  };
};

type ProjectAdmin = {
  user_id: string;
  email: string;
  full_name: string | null;
  membership_role: string;
};

type SourceAsset = {
  id: string;
  source_name: string;
  source_url: string | null;
  source_file: string | null;
  status: string;
  created_at: string | null;
};

type KBSource = {
  source_name: string;
  source_url: string | null;
  source_file: string | null;
};

type AuditLog = {
  id: string;
  actor_email: string;
  action: string;
  entity_type: string | null;
  entity_id: string | null;
  project_id: string | null;
  created_at: string | null;
};

const tabs = ['overview', 'admins', 'sources', 'ingestion', 'logs', 'health'] as const;
type TabId = (typeof tabs)[number];

const Dashboard = () => {
  const { user } = useAuth();
  const isSuperAdmin = user?.roles?.includes('super_admin') ?? false;

  const [projects, setProjects] = useState<ProjectWithOverview[]>([]);
  const [platformOverview, setPlatformOverview] = useState<PlatformOverview | null>(null);
  const [selectedProjectId, setSelectedProjectId] = useState('');
  const [selectedAudience, setSelectedAudience] = useState<Audience>('general');
  const [projectOverview, setProjectOverview] = useState<ProjectOverview | null>(null);
  const [projectAdmins, setProjectAdmins] = useState<ProjectAdmin[]>([]);
  const [knowledgeSources, setKnowledgeSources] = useState<KBSource[]>([]);
  const [knowledgeAssets, setKnowledgeAssets] = useState<SourceAsset[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [activeTab, setActiveTab] = useState<TabId>('overview');
  const [loadingProjects, setLoadingProjects] = useState(true);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [error, setError] = useState('');

  const selectedProject = useMemo(
    () => projects.find((project) => project.id === selectedProjectId) || null,
    [projects, selectedProjectId],
  );

  useEffect(() => {
    void loadProjects();
  }, [user]);

  useEffect(() => {
    if (selectedProjectId) {
      void loadProjectDetail(selectedProjectId, selectedAudience);
    }
  }, [selectedProjectId, selectedAudience]);

  const loadProjects = async () => {
    setLoadingProjects(true);
    setError('');

    try {
      if (isSuperAdmin) {
        const [projectsResp, overviewResp] = await Promise.all([
          api.get('/admin/projects'),
          api.get('/admin/overview'),
        ]);

        const projectRows: Project[] = projectsResp.data.projects || [];
        const overviewMap = new Map<string, ProjectOverview>();

        await Promise.all(
          projectRows.map(async (project) => {
            try {
              const response = await api.get(`/admin/projects/${project.id}/overview`);
              overviewMap.set(project.id, response.data);
            } catch (overviewError) {
              console.error(`Failed to fetch overview for ${project.id}`, overviewError);
            }
          }),
        );

        const nextProjects: ProjectWithOverview[] = projectRows.map((project) => ({
          ...project,
          overview: overviewMap.get(project.id) || null,
        }));

        setProjects(nextProjects);
        setPlatformOverview(overviewResp.data);
        setSelectedProjectId((current) => current || nextProjects[0]?.id || '');
      } else {
        const projectIds = user?.project_ids || [];
        const nextProjects = await Promise.all(
          projectIds.map(async (projectId) => {
            const response = await api.get(`/admin/projects/${projectId}`);
            return response.data as Project;
          }),
        );

        setProjects(nextProjects);
        setSelectedProjectId((current) => current || nextProjects[0]?.id || '');
      }
    } catch (loadError) {
      console.error('Failed to load projects', loadError);
      setError('Could not load project data. Check your admin permissions and API connection.');
    } finally {
      setLoadingProjects(false);
    }
  };

  const loadProjectDetail = async (projectId: string, audience: Audience) => {
    setLoadingDetails(true);
    setError('');

    try {
      const [overviewResp, adminsResp, kbResp, logsResp] = await Promise.all([
        api.get(`/admin/projects/${projectId}/overview`),
        api.get(`/admin/projects/${projectId}/admins`),
        api.get(`/admin/projects/${projectId}/knowledge-base?audience=${audience}`),
        api.get(`/admin/projects/${projectId}/audit-logs?limit=8`),
      ]);

      setProjectOverview(overviewResp.data);
      setProjectAdmins(adminsResp.data.admins || []);
      setKnowledgeSources(kbResp.data.sources || []);
      setKnowledgeAssets(kbResp.data.assets || []);
      setAuditLogs(logsResp.data.logs || []);
    } catch (loadError) {
      console.error('Failed to load project detail', loadError);
      setError('Could not load the selected project. Verify that you can access it from this account.');
      setProjectOverview(null);
      setProjectAdmins([]);
      setKnowledgeSources([]);
      setKnowledgeAssets([]);
      setAuditLogs([]);
    } finally {
      setLoadingDetails(false);
    }
  };

  const currentOverview = selectedProject?.overview || projectOverview;

  if (loadingProjects) {
    return <div className="loading-shell">Loading project workspace...</div>;
  }

  return (
    <div className="project-workspace">
      <section className="hero-card">
        <div className="hero-copy">
          <div className="eyebrow-row">
            <span className="eyebrow">Project-first admin workspace</span>
            <span className="live-pill">
              <CircleDot size={14} />
              Live endpoints
            </span>
          </div>
          <h1>Manage each deployed project from one simulated control room.</h1>
          <p>
            Start with the live project list, then drill into admins, sources, ingestion, logs, and health using the
            real production admin API.
          </p>
          <div className="hero-actions">
            <Link className="primary-action" to="/projects">
              <FolderKanban size={18} />
              <span>Open project management</span>
            </Link>
            <Link className="secondary-action" to="/audit-logs">
              <FileText size={18} />
              <span>View full logs</span>
            </Link>
          </div>
        </div>

        <div className="hero-snapshot">
          <div className="snapshot-card">
            <span>Accessible projects</span>
            <strong>{projects.length}</strong>
          </div>
          <div className="snapshot-card">
            <span>Selected project</span>
            <strong>{selectedProject?.name || 'None'}</strong>
          </div>
          <div className="snapshot-card">
            <span>Platform users</span>
            <strong>{platformOverview?.total_users ?? 'N/A'}</strong>
          </div>
          <div className="snapshot-card">
            <span>Database</span>
            <strong>{platformOverview?.system_health.database.available ? 'Online' : 'Degraded'}</strong>
          </div>
        </div>
      </section>

      {error && (
        <div className="error-banner">
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      <section className="workspace-grid">
        <aside className="project-rail">
          <div className="rail-header">
            <div>
              <h2>Live projects</h2>
              <p>Select a project to inspect its operational view.</p>
            </div>
            <Sparkles size={18} />
          </div>

          <div className="project-list">
            {projects.map((project) => {
              const overview = (project as Project & { overview?: ProjectOverview | null }).overview;

              return (
                <button
                  key={project.id}
                  className={`project-item ${selectedProjectId === project.id ? 'active' : ''}`}
                  onClick={() => {
                    setSelectedProjectId(project.id);
                    setActiveTab('overview');
                  }}
                >
                  <div className="project-item-top">
                    <div>
                      <h3>{project.name}</h3>
                      <span className="project-id">{project.id}</span>
                    </div>
                    {project.enabled ? (
                      <span className="status-pill success">Active</span>
                    ) : (
                      <span className="status-pill muted">Disabled</span>
                    )}
                  </div>
                  <p>{project.description || 'No description provided.'}</p>
                  <div className="project-tags">
                    {project.audiences.map((audience) => (
                      <span key={audience} className="tag">
                        {audience}
                      </span>
                    ))}
                  </div>
                  <div className="project-mini-metrics">
                    <span>
                      <Users size={14} />
                      {overview?.total_user_messages ?? 0} queries
                    </span>
                    <span>
                      <Database size={14} />
                      {overview?.total_sources ?? 0} sources
                    </span>
                    <span>
                      <Activity size={14} />
                      {overview?.active_ingestion_jobs ?? 0} active jobs
                    </span>
                  </div>
                </button>
              );
            })}
          </div>
        </aside>

        <main className="detail-pane">
          <div className="detail-header">
            <div>
              <p className="detail-kicker">Project drilldown</p>
              <h2>{selectedProject?.name || 'Select a project'}</h2>
              <p className="detail-subtitle">
                {selectedProject?.description || 'Use the project list to inspect its current operational surface.'}
              </p>
            </div>

            <div className="detail-actions">
              <div className="audience-switch">
                <button className={selectedAudience === 'general' ? 'active' : ''} onClick={() => setSelectedAudience('general')}>
                  General
                </button>
                <button className={selectedAudience === 'clinicians' ? 'active' : ''} onClick={() => setSelectedAudience('clinicians')}>
                  Clinicians
                </button>
              </div>
              <Link className="inline-link" to={`/projects/${selectedProject?.id || ''}/kb`}>
                Open KB manager <ArrowRight size={16} />
              </Link>
            </div>
          </div>

          <div className="tab-bar">
            {tabs.map((tab) => (
              <button key={tab} className={activeTab === tab ? 'active' : ''} onClick={() => setActiveTab(tab)}>
                {tab}
              </button>
            ))}
          </div>

          {loadingDetails ? (
            <div className="loading-details">Loading project detail...</div>
          ) : (
            <>
              {activeTab === 'overview' && (
                <section className="overview-stack">
                  <div className="metric-grid">
                    <MetricCard title="User queries" value={currentOverview?.total_user_messages ?? 0} helper="User-side chat volume" icon={<TrendingUp size={18} />} />
                    <MetricCard title="Sources" value={currentOverview?.total_sources ?? 0} helper="Tracked knowledge-base sources" icon={<BookOpen size={18} />} />
                    <MetricCard title="Avg rating" value={currentOverview?.average_rating ? currentOverview.average_rating.toFixed(1) : '0.0'} helper="Latest feedback signal" icon={<ShieldAlert size={18} />} />
                    <MetricCard title="Active jobs" value={currentOverview?.active_ingestion_jobs ?? 0} helper="Queued or processing ingestion work" icon={<Activity size={18} />} />
                  </div>

                  <div className="chart-card">
                    <div className="section-heading">
                      <div>
                        <h3>Recent activity</h3>
                        <p>Project-side activity over the last 14 days.</p>
                      </div>
                      <span className="section-note">Selected audience: {selectedAudience}</span>
                    </div>
                    <div className="chart-wrap">
                      {currentOverview?.activity_data?.length ? (
                        <ResponsiveContainer width="100%" height={260}>
                          <AreaChart data={currentOverview.activity_data}>
                            <defs>
                              <linearGradient id="projectActivity" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#2563eb" stopOpacity={0.18} />
                                <stop offset="95%" stopColor="#2563eb" stopOpacity={0} />
                              </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                            <XAxis
                              dataKey="date"
                              axisLine={false}
                              tickLine={false}
                              tick={{ fill: '#94a3b8', fontSize: 12 }}
                              tickFormatter={(value) => {
                                try {
                                  return new Date(value).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
                                } catch {
                                  return value;
                                }
                              }}
                            />
                            <YAxis axisLine={false} tickLine={false} tick={{ fill: '#94a3b8', fontSize: 12 }} />
                            <Tooltip contentStyle={{ borderRadius: 12, border: 'none', boxShadow: '0 12px 30px rgba(15, 23, 42, 0.08)' }} />
                            <Area type="monotone" dataKey="count" stroke="#2563eb" strokeWidth={2} fill="url(#projectActivity)" />
                          </AreaChart>
                        </ResponsiveContainer>
                      ) : (
                        <div className="empty-state">No activity data has been recorded for this project yet.</div>
                      )}
                    </div>
                  </div>
                </section>
              )}

              {activeTab === 'admins' && (
                <section className="card-panel">
                  <div className="section-heading">
                    <div>
                      <h3>Project admins</h3>
                      <p>Users who can administer the selected project.</p>
                    </div>
                    <span className="section-note">{projectAdmins.length} admin records</span>
                  </div>
                  <div className="table-list">
                    {projectAdmins.length ? (
                      projectAdmins.map((admin) => (
                        <div key={`${admin.user_id}-${admin.membership_role}`} className="row-item">
                          <div>
                            <strong>{admin.full_name || admin.email}</strong>
                            <p>{admin.email}</p>
                          </div>
                          <span className="row-pill">{admin.membership_role.replace('_', ' ')}</span>
                        </div>
                      ))
                    ) : (
                      <div className="empty-state">No project admins are assigned yet.</div>
                    )}
                  </div>
                </section>
              )}

              {activeTab === 'sources' && (
                <section className="card-panel">
                  <div className="section-heading">
                    <div>
                      <h3>Knowledge sources</h3>
                      <p>Disk sources and tracked assets for the selected audience.</p>
                    </div>
                    <span className="section-note">{knowledgeAssets.length} tracked assets</span>
                  </div>

                  <div className="sources-grid">
                    <div className="source-card">
                      <h4>Tracked assets</h4>
                      {knowledgeAssets.length ? (
                        knowledgeAssets.map((asset) => (
                          <div key={asset.id} className="source-row">
                            <div>
                              <strong>{asset.source_name}</strong>
                              <p>{asset.source_file || 'No source file recorded.'}</p>
                            </div>
                            <span className={`row-pill ${asset.status}`}>{asset.status.replace('_', ' ')}</span>
                          </div>
                        ))
                      ) : (
                        <div className="empty-state compact">No assets are attached for this audience.</div>
                      )}
                    </div>

                    <div className="source-card">
                      <h4>Disk sources</h4>
                      {knowledgeSources.length ? (
                        knowledgeSources.map((source) => (
                          <div key={`${source.source_file || source.source_name}`} className="source-row">
                            <div>
                              <strong>{source.source_name || source.source_file}</strong>
                              <p>{source.source_url || source.source_file || 'No source URL available.'}</p>
                            </div>
                            <span className="row-pill muted">{selectedAudience}</span>
                          </div>
                        ))
                      ) : (
                        <div className="empty-state compact">No markdown sources were returned for this audience.</div>
                      )}
                    </div>
                  </div>
                </section>
              )}

              {activeTab === 'ingestion' && (
                <section className="card-panel">
                  <div className="section-heading">
                    <div>
                      <h3>Ingestion snapshot</h3>
                      <p>What the backend currently knows about indexing activity.</p>
                    </div>
                    <span className="section-note">Read-only view</span>
                  </div>

                  <div className="metric-grid compact-grid">
                    <MetricCard title="Total sources" value={currentOverview?.total_sources ?? 0} helper="Attached to the project" icon={<Database size={18} />} />
                    <MetricCard title="Active jobs" value={currentOverview?.active_ingestion_jobs ?? 0} helper="Queued or processing jobs" icon={<Activity size={18} />} />
                    <MetricCard title="Average rating" value={currentOverview?.average_rating ? currentOverview.average_rating.toFixed(1) : '0.0'} helper="Feedback signal" icon={<TrendingUp size={18} />} />
                  </div>

                  <div className="note-panel">
                    <strong>Current limitation</strong>
                    <p>The deployed API already exposes ingestion status summaries, but not a dedicated job list. This UI stays truthful by showing the available counts rather than inventing a deeper list view.</p>
                  </div>
                </section>
              )}

              {activeTab === 'logs' && (
                <section className="card-panel">
                  <div className="section-heading">
                    <div>
                      <h3>Project audit log</h3>
                      <p>Recent actions for the selected project.</p>
                    </div>
                    <Link className="inline-link" to="/audit-logs">
                      Open full log view <ChevronRight size={16} />
                    </Link>
                  </div>

                  <div className="table-list">
                    {auditLogs.length ? (
                      auditLogs.map((log) => (
                        <div key={log.id} className="row-item log-row">
                          <div>
                            <strong>{log.action}</strong>
                            <p>
                              {log.actor_email} · {log.entity_type || 'event'} {log.entity_id ? `· ${log.entity_id}` : ''}
                            </p>
                          </div>
                          <span className="row-pill muted">{log.project_id || selectedProjectId}</span>
                        </div>
                      ))
                    ) : (
                      <div className="empty-state">No project audit logs are available yet.</div>
                    )}
                  </div>
                </section>
              )}

              {activeTab === 'health' && (
                <section className="health-grid">
                  <div className="health-card">
                    <div className="section-heading">
                      <div>
                        <h3>Platform health</h3>
                        <p>Global state from the production admin API.</p>
                      </div>
                    </div>
                    <div className="health-items">
                      <HealthItem label="Database" value={platformOverview?.system_health.database.available ? 'Online' : 'Degraded'} detail={platformOverview?.system_health.database.reason || 'Connected'} />
                      <HealthItem label="Projects" value={platformOverview?.total_projects ?? 'N/A'} detail="Configured in production" />
                      <HealthItem label="Users" value={platformOverview?.total_users ?? 'N/A'} detail="Admin identities available" />
                      <HealthItem label="Toxic messages" value={platformOverview?.toxic_messages ?? 'N/A'} detail="Guardrail review queue" />
                    </div>
                  </div>

                  <div className="health-card">
                    <div className="section-heading">
                      <div>
                        <h3>Project health</h3>
                        <p>What matters for the selected project.</p>
                      </div>
                    </div>
                    <div className="health-items">
                      <HealthItem label="Project status" value={selectedProject?.status || 'Unknown'} detail={selectedProject?.enabled ? 'Enabled for traffic' : 'Disabled'} />
                      <HealthItem label="Audiences" value={selectedProject?.audiences.length || 0} detail="General and clinician paths" />
                      <HealthItem label="Average rating" value={currentOverview?.average_rating ? currentOverview.average_rating.toFixed(1) : '0.0'} detail="User feedback signal" />
                      <HealthItem label="Activity window" value={currentOverview?.activity_data?.length || 0} detail="Days with recent traffic" />
                    </div>
                  </div>
                </section>
              )}
            </>
          )}
        </main>
      </section>

      <style>{`
        .project-workspace {
          display: flex;
          flex-direction: column;
          gap: 1.5rem;
        }

        .hero-card {
          display: grid;
          grid-template-columns: minmax(0, 1.6fr) minmax(320px, 0.9fr);
          gap: 1.5rem;
          padding: 1.75rem;
          border-radius: 24px;
          background:
            radial-gradient(circle at top right, rgba(37, 99, 235, 0.12), transparent 28%),
            linear-gradient(135deg, #f8fbff 0%, #ffffff 60%, #f8fafc 100%);
          border: 1px solid rgba(148, 163, 184, 0.18);
          box-shadow: 0 16px 40px rgba(15, 23, 42, 0.05);
        }

        .hero-copy h1 {
          font-size: clamp(1.9rem, 3vw, 2.9rem);
          line-height: 1.05;
          margin: 0.75rem 0 0.9rem;
          color: #0f172a;
          max-width: 14ch;
        }

        .hero-copy p {
          color: #475569;
          max-width: 62ch;
          font-size: 0.98rem;
          line-height: 1.6;
        }

        .eyebrow-row {
          display: flex;
          flex-wrap: wrap;
          gap: 0.75rem;
          align-items: center;
        }

        .eyebrow,
        .live-pill,
        .section-note,
        .row-pill,
        .tag,
        .project-id {
          font-size: 0.75rem;
          font-weight: 700;
          letter-spacing: 0.03em;
        }

        .eyebrow,
        .live-pill,
        .section-note {
          text-transform: uppercase;
        }

        .eyebrow {
          color: #2563eb;
        }

        .live-pill,
        .section-note,
        .row-pill.muted,
        .project-id {
          color: #64748b;
        }

        .live-pill {
          display: inline-flex;
          align-items: center;
          gap: 0.35rem;
          color: #0f172a;
          background: rgba(37, 99, 235, 0.08);
          padding: 0.35rem 0.6rem;
          border-radius: 999px;
        }

        .hero-actions {
          display: flex;
          flex-wrap: wrap;
          gap: 0.75rem;
          margin-top: 1.5rem;
        }

        .primary-action,
        .secondary-action,
        .inline-link {
          display: inline-flex;
          align-items: center;
          gap: 0.5rem;
          text-decoration: none;
          font-weight: 700;
          border-radius: 14px;
          transition: transform 0.15s ease, box-shadow 0.15s ease, background 0.15s ease;
        }

        .primary-action {
          background: linear-gradient(135deg, #2563eb, #1d4ed8);
          color: white;
          padding: 0.8rem 1.1rem;
          box-shadow: 0 12px 24px rgba(37, 99, 235, 0.22);
        }

        .secondary-action,
        .inline-link {
          color: #0f172a;
          background: rgba(255, 255, 255, 0.78);
          border: 1px solid rgba(148, 163, 184, 0.22);
          padding: 0.8rem 1.1rem;
        }

        .primary-action:hover,
        .secondary-action:hover,
        .inline-link:hover {
          transform: translateY(-1px);
        }

        .hero-snapshot {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 0.75rem;
          align-content: start;
        }

        .snapshot-card {
          padding: 1rem;
          border-radius: 16px;
          background: rgba(255, 255, 255, 0.88);
          border: 1px solid rgba(148, 163, 184, 0.18);
        }

        .snapshot-card span {
          display: block;
          color: #64748b;
          font-size: 0.78rem;
          margin-bottom: 0.45rem;
        }

        .snapshot-card strong {
          font-size: 1rem;
          color: #0f172a;
        }

        .error-banner {
          display: inline-flex;
          align-items: center;
          gap: 0.5rem;
          background: #fff7ed;
          color: #9a3412;
          border: 1px solid #fed7aa;
          border-radius: 14px;
          padding: 0.8rem 1rem;
        }

        .workspace-grid {
          display: grid;
          grid-template-columns: minmax(280px, 350px) minmax(0, 1fr);
          gap: 1.25rem;
          align-items: start;
        }

        .project-rail,
        .detail-pane,
        .card-panel,
        .health-card {
          background: white;
          border: 1px solid rgba(148, 163, 184, 0.18);
          border-radius: 24px;
          box-shadow: 0 16px 40px rgba(15, 23, 42, 0.04);
        }

        .project-rail {
          padding: 1rem;
          position: sticky;
          top: 1rem;
        }

        .rail-header,
        .detail-header,
        .section-heading {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 1rem;
        }

        .rail-header h2,
        .detail-header h2,
        .section-heading h3 {
          color: #0f172a;
        }

        .rail-header p,
        .detail-subtitle,
        .section-heading p {
          color: #64748b;
          font-size: 0.9rem;
          line-height: 1.5;
        }

        .project-list {
          display: flex;
          flex-direction: column;
          gap: 0.75rem;
          margin-top: 1rem;
        }

        .project-item {
          text-align: left;
          background: linear-gradient(180deg, #ffffff, #f8fafc);
          border: 1px solid #e2e8f0;
          border-radius: 18px;
          padding: 1rem;
          cursor: pointer;
          transition: transform 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease;
        }

        .project-item:hover,
        .project-item.active {
          transform: translateY(-1px);
          border-color: rgba(37, 99, 235, 0.3);
          box-shadow: 0 16px 26px rgba(15, 23, 42, 0.06);
        }

        .project-item-top {
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          gap: 1rem;
          margin-bottom: 0.5rem;
        }

        .project-item h3 {
          color: #0f172a;
          font-size: 1rem;
        }

        .project-item p {
          color: #64748b;
          font-size: 0.85rem;
          line-height: 1.45;
          margin: 0.65rem 0;
        }

        .status-pill,
        .tag,
        .row-pill {
          display: inline-flex;
          align-items: center;
          gap: 0.25rem;
          border-radius: 999px;
          padding: 0.28rem 0.55rem;
        }

        .status-pill.success {
          background: #dcfce7;
          color: #166534;
        }

        .status-pill.muted {
          background: #e2e8f0;
          color: #475569;
        }

        .project-tags,
        .project-mini-metrics {
          display: flex;
          flex-wrap: wrap;
          gap: 0.5rem;
        }

        .tag {
          background: #eff6ff;
          color: #1d4ed8;
        }

        .project-mini-metrics span {
          display: inline-flex;
          align-items: center;
          gap: 0.35rem;
          background: rgba(241, 245, 249, 0.82);
          border: 1px solid #e2e8f0;
          border-radius: 999px;
          padding: 0.35rem 0.6rem;
          color: #334155;
          font-size: 0.78rem;
          font-weight: 600;
        }

        .detail-pane {
          padding: 1.25rem;
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }

        .detail-kicker {
          text-transform: uppercase;
          letter-spacing: 0.08em;
          color: #2563eb;
          font-size: 0.72rem;
          font-weight: 800;
          margin-bottom: 0.25rem;
        }

        .detail-actions {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          flex-wrap: wrap;
          justify-content: flex-end;
        }

        .audience-switch {
          display: inline-flex;
          background: #f1f5f9;
          border-radius: 999px;
          padding: 0.2rem;
          border: 1px solid #e2e8f0;
        }

        .audience-switch button,
        .tab-bar button {
          border: none;
          background: transparent;
          cursor: pointer;
          font-weight: 700;
          color: #64748b;
        }

        .audience-switch button {
          padding: 0.55rem 0.85rem;
          border-radius: 999px;
        }

        .audience-switch button.active,
        .tab-bar button.active {
          background: white;
          color: #0f172a;
          box-shadow: 0 10px 20px rgba(15, 23, 42, 0.06);
        }

        .tab-bar {
          display: flex;
          flex-wrap: wrap;
          gap: 0.5rem;
          padding: 0.3rem;
          border-radius: 18px;
          background: #f8fafc;
          border: 1px solid #e2e8f0;
        }

        .tab-bar button {
          padding: 0.65rem 0.9rem;
          border-radius: 14px;
        }

        .overview-stack,
        .health-grid,
        .sources-grid {
          display: grid;
          gap: 1rem;
        }

        .metric-grid {
          display: grid;
          grid-template-columns: repeat(4, minmax(0, 1fr));
          gap: 0.9rem;
        }

        .compact-grid {
          grid-template-columns: repeat(3, minmax(0, 1fr));
        }

        .metric-card {
          padding: 1rem;
          border-radius: 18px;
          background: linear-gradient(180deg, #ffffff, #f8fafc);
          border: 1px solid #e2e8f0;
        }

        .metric-top {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 0.75rem;
          margin-bottom: 0.75rem;
        }

        .metric-top span {
          font-size: 0.8rem;
          font-weight: 800;
          color: #64748b;
          text-transform: uppercase;
          letter-spacing: 0.04em;
        }

        .metric-value {
          font-size: 1.8rem;
          line-height: 1;
          font-weight: 800;
          color: #0f172a;
        }

        .metric-helper {
          margin-top: 0.55rem;
          color: #64748b;
          font-size: 0.82rem;
          line-height: 1.45;
        }

        .chart-card,
        .card-panel,
        .health-card {
          padding: 1.1rem;
        }

        .chart-card {
          border-radius: 20px;
          border: 1px solid #e2e8f0;
          background: linear-gradient(180deg, #ffffff, #f8fafc);
        }

        .chart-wrap {
          margin-top: 1rem;
        }

        .table-list,
        .health-items {
          display: flex;
          flex-direction: column;
          gap: 0.7rem;
          margin-top: 1rem;
        }

        .row-item {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 1rem;
          padding: 0.95rem 1rem;
          border-radius: 16px;
          background: #f8fafc;
          border: 1px solid #e2e8f0;
        }

        .row-item strong {
          color: #0f172a;
          display: block;
          margin-bottom: 0.2rem;
        }

        .row-item p {
          color: #64748b;
          font-size: 0.84rem;
          line-height: 1.45;
        }

        .row-pill {
          background: #eff6ff;
          color: #1d4ed8;
          white-space: nowrap;
        }

        .row-pill.muted {
          background: #e2e8f0;
          color: #475569;
        }

        .row-pill.active {
          background: #dcfce7;
          color: #166534;
        }

        .sources-grid {
          grid-template-columns: repeat(2, minmax(0, 1fr));
        }

        .source-card {
          border-radius: 18px;
          border: 1px solid #e2e8f0;
          padding: 1rem;
          background: #fff;
        }

        .source-card h4 {
          color: #0f172a;
          margin-bottom: 0.75rem;
        }

        .source-row {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 1rem;
          padding: 0.85rem 0;
          border-top: 1px solid #f1f5f9;
        }

        .source-row:first-of-type {
          border-top: none;
          padding-top: 0;
        }

        .source-row p {
          color: #64748b;
          font-size: 0.8rem;
          margin-top: 0.15rem;
          line-height: 1.4;
        }

        .note-panel {
          margin-top: 1rem;
          padding: 1rem;
          border-radius: 16px;
          background: #eff6ff;
          border: 1px solid #bfdbfe;
          color: #1e3a8a;
        }

        .note-panel p {
          margin-top: 0.35rem;
          color: #1e3a8a;
          line-height: 1.5;
        }

        .health-grid {
          grid-template-columns: repeat(2, minmax(0, 1fr));
        }

        .health-card {
          border-radius: 20px;
          border: 1px solid #e2e8f0;
          background: linear-gradient(180deg, #ffffff, #f8fafc);
        }

        .health-item {
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          gap: 1rem;
          padding: 0.9rem 1rem;
          border-radius: 16px;
          background: white;
          border: 1px solid #e2e8f0;
        }

        .health-item strong {
          display: block;
          color: #0f172a;
          margin-bottom: 0.25rem;
        }

        .health-item span {
          display: block;
          color: #64748b;
          font-size: 0.82rem;
          line-height: 1.45;
        }

        .loading-shell,
        .loading-details,
        .empty-state {
          display: flex;
          align-items: center;
          justify-content: center;
          min-height: 220px;
          border-radius: 18px;
          background: #f8fafc;
          border: 1px dashed #cbd5e1;
          color: #64748b;
          padding: 2rem;
          text-align: center;
        }

        .empty-state.compact {
          min-height: 140px;
        }

        @media (max-width: 1100px) {
          .hero-card,
          .workspace-grid,
          .health-grid,
          .sources-grid,
          .metric-grid {
            grid-template-columns: 1fr;
          }

          .project-rail {
            position: static;
          }
        }

        @media (max-width: 720px) {
          .project-workspace {
            gap: 1rem;
          }

          .hero-card,
          .detail-pane,
          .project-rail,
          .chart-card,
          .card-panel,
          .health-card {
            padding: 1rem;
            border-radius: 18px;
          }

          .detail-header,
          .section-heading,
          .rail-header {
            align-items: flex-start;
            flex-direction: column;
          }

          .detail-actions {
            justify-content: flex-start;
          }

          .row-item,
          .source-row,
          .health-item {
            flex-direction: column;
            align-items: flex-start;
          }
        }
      `}</style>
    </div>
  );
};

const MetricCard = ({
  title,
  value,
  helper,
  icon,
}: {
  title: string;
  value: string | number;
  helper: string;
  icon: React.ReactNode;
}) => (
  <div className="metric-card">
    <div className="metric-top">
      <span>{title}</span>
      {icon}
    </div>
    <div className="metric-value">{value}</div>
    <div className="metric-helper">{helper}</div>
  </div>
);

const HealthItem = ({
  label,
  value,
  detail,
}: {
  label: string;
  value: string | number;
  detail: string;
}) => (
  <div className="health-item">
    <div>
      <strong>{label}</strong>
      <span>{detail}</span>
    </div>
    <span className="row-pill muted">{value}</span>
  </div>
);

export default Dashboard;
