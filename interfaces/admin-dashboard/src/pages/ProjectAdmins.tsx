import React, { useEffect, useMemo, useState } from 'react';
import { UserPlus, UserMinus, ShieldCheck, RefreshCcw } from 'lucide-react';
import api from '../lib/api';
import { useAuth } from '../context/AuthContext';

type Project = {
  id: string;
  name: string;
};

type User = {
  id: string;
  email: string;
  full_name: string | null;
  roles: string[];
  project_ids: string[];
};

type ProjectAdmin = {
  user_id: string;
  email: string;
  full_name: string | null;
  membership_role: string;
};

const ProjectAdmins = () => {
  const { user } = useAuth();
  const isSuperAdmin = user?.roles?.includes('super_admin') ?? false;

  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState('');
  const [admins, setAdmins] = useState<ProjectAdmin[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [selectedUserId, setSelectedUserId] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const candidateUsers = useMemo(
    () => users.filter((u) => !admins.some((a) => a.user_id === u.id)),
    [users, admins],
  );

  useEffect(() => {
    void bootstrap();
  }, []);

  useEffect(() => {
    if (selectedProject) {
      void loadProjectAdmins(selectedProject);
    }
  }, [selectedProject]);

  const bootstrap = async () => {
    setLoading(true);
    try {
      if (isSuperAdmin) {
        const [projectsResp, usersResp] = await Promise.all([
          api.get('/admin/projects'),
          api.get('/admin/users'),
        ]);
        const nextProjects: Project[] = (projectsResp.data.projects || []).map((p: any) => ({ id: p.id, name: p.name }));
        setProjects(nextProjects);
        setUsers(usersResp.data.users || []);
        setSelectedProject(nextProjects[0]?.id || '');
      } else {
        const allowed = user?.project_ids || [];
        const rows = await Promise.all(allowed.map((projectId) => api.get(`/admin/projects/${projectId}`)));
        const nextProjects: Project[] = rows.map((resp) => ({ id: resp.data.id, name: resp.data.name }));
        setProjects(nextProjects);
        setSelectedProject(nextProjects[0]?.id || '');
      }
    } catch (err) {
      console.error('Failed to load project admin data', err);
    } finally {
      setLoading(false);
    }
  };

  const loadProjectAdmins = async (projectId: string) => {
    try {
      const resp = await api.get(`/admin/projects/${projectId}/admins`);
      setAdmins(resp.data.admins || []);
    } catch (err) {
      console.error('Failed to load project admins', err);
      setAdmins([]);
    }
  };

  const handleAdd = async () => {
    if (!selectedProject || !selectedUserId) return;
    setSaving(true);
    try {
      await api.post(`/admin/projects/${selectedProject}/admins`, { user_id: selectedUserId });
      setSelectedUserId('');
      await loadProjectAdmins(selectedProject);
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to add project admin');
    } finally {
      setSaving(false);
    }
  };

  const handleRemove = async (userId: string) => {
    if (!selectedProject) return;
    if (!window.confirm('Remove this user from project admins?')) return;
    setSaving(true);
    try {
      await api.delete(`/admin/projects/${selectedProject}/admins/${userId}`);
      await loadProjectAdmins(selectedProject);
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to remove project admin');
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="loading">Loading project admins...</div>;

  return (
    <div className="project-admins-page">
      <div className="header-row">
        <div>
          <h2>Project Admins</h2>
          <p>Manage project-level admin membership using live admin endpoints.</p>
        </div>
        <button className="btn-outline" onClick={() => selectedProject && loadProjectAdmins(selectedProject)}>
          <RefreshCcw size={16} />
          <span>Refresh</span>
        </button>
      </div>

      <div className="card controls">
        <div className="field">
          <label>Project</label>
          <select value={selectedProject} onChange={(e) => setSelectedProject(e.target.value)}>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>{p.name} ({p.id})</option>
            ))}
          </select>
        </div>

        {isSuperAdmin && (
          <>
            <div className="field">
              <label>Add Admin User</label>
              <select value={selectedUserId} onChange={(e) => setSelectedUserId(e.target.value)}>
                <option value="">Select a user</option>
                {candidateUsers.map((u) => (
                  <option key={u.id} value={u.id}>{u.full_name || u.email} ({u.email})</option>
                ))}
              </select>
            </div>
            <button className="btn-primary" disabled={!selectedUserId || saving} onClick={handleAdd}>
              <UserPlus size={16} />
              <span>Add Project Admin</span>
            </button>
          </>
        )}
      </div>

      <div className="card">
        <div className="list-head">
          <ShieldCheck size={16} />
          <span>Current admins for {selectedProject || 'selected project'}</span>
        </div>
        <div className="admin-list">
          {admins.map((admin) => (
            <div key={admin.user_id} className="admin-item">
              <div>
                <strong>{admin.full_name || admin.email}</strong>
                <p>{admin.email}</p>
              </div>
              <div className="item-actions">
                <span className="role-pill">{admin.membership_role}</span>
                {isSuperAdmin && (
                  <button className="btn-icon danger" onClick={() => handleRemove(admin.user_id)}>
                    <UserMinus size={16} />
                  </button>
                )}
              </div>
            </div>
          ))}
          {admins.length === 0 && <div className="empty">No project admins assigned.</div>}
        </div>
      </div>

      <style>{`
        .project-admins-page { display: flex; flex-direction: column; gap: 1rem; }
        .header-row { display: flex; justify-content: space-between; align-items: flex-start; gap: 1rem; }
        .header-row h2 { font-size: 1.2rem; }
        .header-row p { color: #64748b; font-size: 0.9rem; }
        .card { background: white; border: 1px solid var(--border-color); border-radius: 12px; padding: 1rem; }
        .controls { display: grid; grid-template-columns: 1fr 1fr auto; gap: 0.8rem; align-items: end; }
        .field { display: flex; flex-direction: column; gap: 0.35rem; }
        .field label { font-size: 0.8rem; color: #64748b; font-weight: 600; }
        .field select { border: 1px solid var(--border-color); border-radius: 8px; padding: 0.55rem 0.6rem; }
        .list-head { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.8rem; font-weight: 600; }
        .admin-list { display: flex; flex-direction: column; gap: 0.6rem; }
        .admin-item { display: flex; justify-content: space-between; align-items: center; border: 1px solid #f1f5f9; background: #f8fafc; border-radius: 8px; padding: 0.75rem; }
        .admin-item p { color: #64748b; font-size: 0.82rem; }
        .item-actions { display: flex; align-items: center; gap: 0.5rem; }
        .role-pill { font-size: 0.72rem; text-transform: uppercase; font-weight: 700; background: #dbeafe; color: #1d4ed8; padding: 0.2rem 0.45rem; border-radius: 999px; }
        .btn-primary { background: var(--primary-color); color: white; border: none; border-radius: 8px; padding: 0.6rem 0.85rem; display: inline-flex; align-items: center; gap: 0.45rem; font-weight: 600; }
        .btn-outline { background: white; border: 1px solid var(--border-color); color: #475569; border-radius: 8px; padding: 0.45rem 0.7rem; display: inline-flex; align-items: center; gap: 0.35rem; }
        .btn-icon { border: none; background: white; border-radius: 6px; padding: 0.35rem; }
        .btn-icon.danger { color: #b91c1c; }
        .empty { text-align: center; color: #94a3b8; padding: 1.2rem; }
        .loading { padding: 2rem; color: #64748b; }
      `}</style>
    </div>
  );
};

export default ProjectAdmins;
