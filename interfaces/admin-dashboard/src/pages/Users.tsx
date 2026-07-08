import React, { useEffect, useMemo, useState } from 'react';
import api from '../lib/api';
import { Plus, Search, Shield, ShieldCheck, Trash2, Users as UsersIcon, X } from 'lucide-react';

type User = {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  roles: string[];
  project_ids: string[];
};

type Project = {
  id: string;
  name: string;
};

const Users = () => {
  const [users, setUsers] = useState<User[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showMembershipModal, setShowMembershipModal] = useState(false);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);

  const [formData, setFormData] = useState({
    email: '',
    password: '',
    full_name: '',
    role: 'project_admin',
  });

  const filteredUsers = useMemo(
    () => users.filter((u) =>
      u.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (u.full_name || '').toLowerCase().includes(searchTerm.toLowerCase()),
    ),
    [users, searchTerm],
  );

  useEffect(() => {
    void fetchInitialData();
  }, []);

  const fetchInitialData = async () => {
    setLoading(true);
    try {
      const [uResp, pResp] = await Promise.all([
        api.get('/admin/users'),
        api.get('/admin/projects'),
      ]);
      setUsers(uResp.data.users || []);
      setProjects(pResp.data.projects || []);
    } catch (err) {
      console.error('Failed to fetch users/projects', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post('/admin/users', {
        email: formData.email,
        password: formData.password,
        full_name: formData.full_name,
        role: formData.role,
      });
      setShowCreateModal(false);
      setFormData({ email: '', password: '', full_name: '', role: 'project_admin' });
      void fetchInitialData();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to create user');
    }
  };

  const toggleMembership = async (userId: string, projectId: string, isMember: boolean) => {
    try {
      if (isMember) {
        await api.delete(`/admin/projects/${projectId}/admins/${userId}`);
      } else {
        await api.post(`/admin/projects/${projectId}/admins`, { user_id: userId });
      }
      void fetchInitialData();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to update project membership');
    }
  };

  const toggleUserActive = async (user: User) => {
    try {
      await api.patch(`/admin/users/${user.id}/active`, { is_active: !user.is_active });
      void fetchInitialData();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to update user status');
    }
  };

  const toggleGlobalRole = async (user: User, role: 'super_admin' | 'project_admin') => {
    const hasRole = user.roles.includes(role);
    try {
      if (hasRole) {
        await api.delete(`/admin/users/${user.id}/roles/${role}`);
      } else {
        await api.post(`/admin/users/${user.id}/roles`, { role });
      }
      void fetchInitialData();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to update role');
    }
  };

  const deleteUser = async (user: User) => {
    if (!window.confirm(`Delete user ${user.email}?`)) return;
    try {
      await api.delete(`/admin/users/${user.id}`);
      void fetchInitialData();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to delete user');
    }
  };

  if (loading) return <div className="loading">Loading user directory...</div>;

  return (
    <div className="users-page">
      <div className="header-actions">
        <div className="search-bar">
          <Search size={18} />
          <input
            placeholder="Search by name or email..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
        <button className="btn-primary" onClick={() => setShowCreateModal(true)}>
          <Plus size={18} />
          <span>Create Admin User</span>
        </button>
      </div>

      <div className="table-card">
        <table>
          <thead>
            <tr>
              <th>User</th>
              <th>Status</th>
              <th>Roles</th>
              <th>Project Access</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredUsers.map((u) => (
              <tr key={u.id}>
                <td>
                  <div className="user-cell">
                    <div className="avatar">{u.full_name?.charAt(0) || u.email.charAt(0).toUpperCase()}</div>
                    <div className="info">
                      <span className="name">{u.full_name || 'N/A'}</span>
                      <span className="email">{u.email}</span>
                    </div>
                  </div>
                </td>
                <td>
                  <span className={`status-pill ${u.is_active ? 'active' : 'inactive'}`}>
                    {u.is_active ? 'Active' : 'Inactive'}
                  </span>
                </td>
                <td>
                  <div className="roles-list">
                    {u.roles.map((r) => (
                      <span key={r} className="role-pill">
                        {r === 'super_admin' ? <Shield size={12} /> : <ShieldCheck size={12} />}
                        {r.replace('_', ' ')}
                      </span>
                    ))}
                  </div>
                </td>
                <td>
                  <button className="btn-membership" onClick={() => { setSelectedUser(u); setShowMembershipModal(true); }}>
                    <UsersIcon size={14} />
                    <span>{u.project_ids.length} Projects</span>
                  </button>
                </td>
                <td>
                  <div className="actions">
                    <button className="btn-chip" onClick={() => toggleUserActive(u)}>
                      {u.is_active ? 'Deactivate' : 'Activate'}
                    </button>
                    <button className="btn-chip" onClick={() => toggleGlobalRole(u, 'super_admin')}>
                      {u.roles.includes('super_admin') ? 'Remove Super' : 'Make Super'}
                    </button>
                    <button className="btn-chip" onClick={() => toggleGlobalRole(u, 'project_admin')}>
                      {u.roles.includes('project_admin') ? 'Remove Project' : 'Make Project'}
                    </button>
                    <button className="btn-icon danger" onClick={() => deleteUser(u)}><Trash2 size={18} /></button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showCreateModal && (
        <div className="modal-overlay">
          <div className="modal">
            <div className="modal-header">
              <h3>Create Admin User</h3>
              <button className="btn-close" onClick={() => setShowCreateModal(false)}><X size={20} /></button>
            </div>
            <form onSubmit={handleCreateUser}>
              <div className="form-group"><label>Full Name</label><input value={formData.full_name} onChange={(e) => setFormData({ ...formData, full_name: e.target.value })} required /></div>
              <div className="form-group"><label>Email</label><input type="email" value={formData.email} onChange={(e) => setFormData({ ...formData, email: e.target.value })} required /></div>
              <div className="form-group"><label>Password</label><input type="password" value={formData.password} onChange={(e) => setFormData({ ...formData, password: e.target.value })} required /></div>
              <div className="form-group">
                <label>Global Role</label>
                <select value={formData.role} onChange={(e) => setFormData({ ...formData, role: e.target.value })}>
                  <option value="project_admin">Project Admin</option>
                  <option value="super_admin">Super Admin</option>
                </select>
              </div>
              <div className="modal-footer"><button type="submit" className="btn-primary">Create Account</button></div>
            </form>
          </div>
        </div>
      )}

      {showMembershipModal && selectedUser && (
        <div className="modal-overlay">
          <div className="modal membership-modal">
            <div className="modal-header">
              <div className="header-title">
                <h3>Project Access</h3>
                <p>Manage projects for <strong>{selectedUser.email}</strong>.</p>
              </div>
              <button className="btn-close" onClick={() => setShowMembershipModal(false)}><X size={20} /></button>
            </div>
            <div className="membership-list">
              {projects.map((proj) => {
                const isMember = selectedUser.project_ids.includes(proj.id);
                return (
                  <div key={proj.id} className={`membership-item ${isMember ? 'member' : ''}`}>
                    <div className="proj-info">
                      <strong>{proj.name}</strong>
                      <span>{proj.id}</span>
                    </div>
                    <button
                      className={`btn-toggle ${isMember ? 'remove' : 'add'}`}
                      onClick={() => toggleMembership(selectedUser.id, proj.id, isMember)}
                    >
                      {isMember ? <X size={16} /> : <Plus size={16} />}
                      <span>{isMember ? 'Revoke' : 'Grant'}</span>
                    </button>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      <style>{`
        .users-page { display: flex; flex-direction: column; gap: 1.5rem; }
        .header-actions { display: flex; justify-content: space-between; align-items: center; gap: 1rem; }
        .search-bar { flex: 1; display: flex; align-items: center; gap: 0.75rem; background: white; padding: 0.6rem 1rem; border-radius: 8px; border: 1px solid var(--border-color); max-width: 420px; }
        .search-bar input { border: none; outline: none; width: 100%; font-size: 0.9rem; }
        .table-card { background: white; border-radius: 12px; border: 1px solid var(--border-color); overflow: auto; }
        table { width: 100%; border-collapse: collapse; }
        th { text-align: left; padding: 1rem; background: #f8fafc; font-size: 0.75rem; text-transform: uppercase; color: #64748b; font-weight: 700; border-bottom: 1px solid var(--border-color); }
        td { padding: 1rem; border-bottom: 1px solid #f1f5f9; vertical-align: middle; }
        .user-cell { display: flex; align-items: center; gap: 1rem; }
        .avatar { width: 36px; height: 36px; background: #e2e8f0; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 0.8rem; }
        .name { font-weight: 600; font-size: 0.9rem; display: block; }
        .email { font-size: 0.75rem; color: #64748b; }
        .status-pill { padding: 0.2rem 0.5rem; border-radius: 999px; font-size: 0.7rem; font-weight: 700; text-transform: uppercase; }
        .status-pill.active { background: #dcfce7; color: #166534; }
        .status-pill.inactive { background: #fee2e2; color: #991b1b; }
        .roles-list { display: flex; gap: 0.4rem; flex-wrap: wrap; }
        .role-pill { background: #eff6ff; color: var(--primary-color); padding: 0.15rem 0.4rem; border-radius: 4px; font-size: 0.65rem; font-weight: 800; text-transform: uppercase; display: flex; align-items: center; gap: 0.25rem; }
        .btn-membership { display: inline-flex; align-items: center; gap: 0.5rem; background: white; border: 1px solid var(--border-color); padding: 0.4rem 0.6rem; border-radius: 6px; font-size: 0.8rem; font-weight: 600; color: #475569; }
        .btn-membership:hover { border-color: var(--primary-color); color: var(--primary-color); }
        .actions { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; }
        .btn-chip { border: 1px solid var(--border-color); background: #fff; color: #334155; font-size: 0.72rem; font-weight: 700; border-radius: 6px; padding: 0.22rem 0.5rem; }
        .btn-chip:hover { border-color: var(--primary-color); color: var(--primary-color); }
        .btn-icon { background: none; border: none; padding: 0.35rem; border-radius: 6px; }
        .btn-icon.danger { color: #b91c1c; }
        .modal-overlay { position: fixed; inset: 0; background: rgba(0, 0, 0, 0.4); display: flex; justify-content: center; align-items: center; z-index: 100; }
        .modal { background: white; border-radius: 12px; width: 420px; padding: 1.2rem; }
        .membership-modal { width: 540px; }
        .modal-header { display: flex; align-items: center; justify-content: space-between; }
        .btn-close { border: none; background: transparent; color: #64748b; }
        .form-group { margin-top: 0.8rem; display: flex; flex-direction: column; gap: 0.3rem; }
        .form-group input, .form-group select { border: 1px solid var(--border-color); border-radius: 8px; padding: 0.55rem 0.6rem; }
        .modal-footer { display: flex; justify-content: flex-end; margin-top: 1rem; }
        .btn-primary { background: var(--primary-color); color: white; border: none; border-radius: 8px; padding: 0.6rem 0.85rem; display: inline-flex; align-items: center; gap: 0.45rem; font-weight: 600; }
        .membership-list { display: flex; flex-direction: column; gap: 0.7rem; margin-top: 1rem; max-height: 420px; overflow-y: auto; }
        .membership-item { display: flex; align-items: center; justify-content: space-between; padding: 0.85rem; background: #f8fafc; border: 1px solid #f1f5f9; border-radius: 8px; }
        .membership-item.member { border-color: #dbeafe; background: #eff6ff; }
        .proj-info { display: flex; flex-direction: column; }
        .proj-info span { font-size: 0.72rem; color: #64748b; }
        .btn-toggle { display: inline-flex; align-items: center; gap: 0.4rem; padding: 0.35rem 0.65rem; border-radius: 6px; font-size: 0.75rem; font-weight: 700; border: none; }
        .btn-toggle.add { background: var(--primary-color); color: white; }
        .btn-toggle.remove { background: #fee2e2; color: #991b1b; }
        .loading { padding: 4rem; text-align: center; color: #94a3b8; }
      `}</style>
    </div>
  );
};

export default Users;
