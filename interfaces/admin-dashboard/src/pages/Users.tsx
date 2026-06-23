import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  UserPlus, 
  Shield, 
  ShieldCheck, 
  Trash2, 
  UserCheck, 
  UserX,
  Search,
  Users as UsersIcon,
  X,
  Plus,
  ArrowRight
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

interface User {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  roles: string[];
  project_ids: string[];
}

const Users = () => {
  const [users, setUsers] = useState<User[]>([]);
  const [projects, setProjects] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showMembershipModal, setShowMembershipModal] = useState(false);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  
  // Form state
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    full_name: '',
    role: 'project_admin'
  });

  useEffect(() => {
    fetchInitialData();
  }, []);

  const fetchInitialData = async () => {
    setLoading(true);
    try {
      const [uResp, pResp] = await Promise.all([
        axios.get('/admin/users'),
        axios.get('/admin/projects')
      ]);
      setUsers(uResp.data.users);
      setProjects(pResp.data.projects);
    } catch (err) {
      console.error('Failed to fetch data', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await axios.post('/admin/users', formData);
      setShowCreateModal(false);
      fetchInitialData();
      setFormData({ email: '', password: '', full_name: '', role: 'project_admin' });
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to create user');
    }
  };

  const toggleMembership = async (userId: string, projectId: string, isMember: boolean) => {
    try {
      if (isMember) {
        await axios.delete(`/admin/projects/${projectId}/admins/${userId}`);
      } else {
        await axios.post(`/admin/projects/${projectId}/admins`, { user_id: userId });
      }
      fetchInitialData();
    } catch (err) {
      alert('Failed to update membership');
    }
  };

  const filteredUsers = users.filter(u => 
    u.email.toLowerCase().includes(searchTerm.toLowerCase()) || 
    u.full_name?.toLowerCase().includes(searchTerm.toLowerCase())
  );

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
          <UserPlus size={18} />
          <span>Invite Member</span>
        </button>
      </div>

      <div className="table-card">
        <table>
          <thead>
            <tr>
              <th>User</th>
              <th>Status</th>
              <th>Roles</th>
              <th>Access</th>
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
                <td><span className={`status-pill ${u.is_active ? 'active' : 'inactive'}`}>{u.is_active ? 'Active' : 'Inactive'}</span></td>
                <td>
                  <div className="roles-list">
                    {u.roles.map(r => (
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
                    <button className="btn-icon danger" onClick={() => {/* Delete logic */}}><Trash2 size={18} /></button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Invite Modal */}
      {showCreateModal && (
        <div className="modal-overlay">
          <div className="modal">
            <div className="modal-header">
              <h3>Invite New Admin</h3>
              <button className="btn-close" onClick={() => setShowCreateModal(false)}><X size={20}/></button>
            </div>
            <form onSubmit={handleCreateUser}>
              <div className="form-group"><label>Full Name</label><input value={formData.full_name} onChange={e => setFormData({...formData, full_name: e.target.value})} required /></div>
              <div className="form-group"><label>Email</label><input type="email" value={formData.email} onChange={e => setFormData({...formData, email: e.target.value})} required /></div>
              <div className="form-group"><label>Password</label><input type="password" value={formData.password} onChange={e => setFormData({...formData, password: e.target.value})} required /></div>
              <div className="form-group">
                <label>Global Role</label>
                <select value={formData.role} onChange={e => setFormData({...formData, role: e.target.value})}>
                  <option value="project_admin">Project Admin</option>
                  <option value="super_admin">Super Admin</option>
                </select>
              </div>
              <div className="modal-footer"><button type="submit" className="btn-primary">Create Account</button></div>
            </form>
          </div>
        </div>
      )}

      {/* Membership Modal */}
      {showMembershipModal && selectedUser && (
        <div className="modal-overlay">
          <div className="modal membership-modal">
            <div className="modal-header">
              <div className="header-title">
                <h3>Project Access</h3>
                <p>Manage which projects <strong>{selectedUser.email}</strong> can administer.</p>
              </div>
              <button className="btn-close" onClick={() => setShowMembershipModal(false)}><X size={20}/></button>
            </div>
            <div className="membership-list">
              {projects.map(proj => {
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
        .header-actions { display: flex; justify-content: space-between; align-items: center; }
        .search-bar { flex: 1; display: flex; align-items: center; gap: 0.75rem; background: white; padding: 0.6rem 1rem; border-radius: 8px; border: 1px solid var(--border-color); max-width: 400px; }
        .search-bar input { border: none; outline: none; width: 100%; font-size: 0.9rem; }
        
        .table-card { background: white; border-radius: 12px; border: 1px solid var(--border-color); overflow: hidden; }
        table { width: 100%; border-collapse: collapse; }
        th { text-align: left; padding: 1rem; background: #f8fafc; font-size: 0.75rem; text-transform: uppercase; color: #64748b; font-weight: 700; border-bottom: 1px solid var(--border-color); }
        td { padding: 1rem; border-bottom: 1px solid #f1f5f9; }
        
        .user-cell { display: flex; align-items: center; gap: 1rem; }
        .avatar { width: 36px; height: 36px; background: #e2e8f0; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 0.8rem; }
        .name { font-weight: 600; font-size: 0.9rem; display: block; }
        .email { font-size: 0.75rem; color: #64748b; }
        
        .status-pill { padding: 0.2rem 0.5rem; border-radius: 99px; font-size: 0.7rem; font-weight: 700; text-transform: uppercase; }
        .status-pill.active { background: #dcfce7; color: #166534; }
        .status-pill.inactive { background: #fee2e2; color: #991b1b; }
        
        .role-pill { background: #eff6ff; color: var(--primary-color); padding: 0.15rem 0.4rem; border-radius: 4px; font-size: 0.65rem; font-weight: 800; text-transform: uppercase; display: flex; align-items: center; gap: 0.25rem; }
        
        .btn-membership { display: flex; align-items: center; gap: 0.5rem; background: white; border: 1px solid var(--border-color); padding: 0.4rem 0.6rem; border-radius: 6px; font-size: 0.8rem; font-weight: 600; cursor: pointer; color: #475569; }
        .btn-membership:hover { border-color: var(--primary-color); color: var(--primary-color); }
        
        .modal-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.4); display: flex; justify-content: center; align-items: center; z-index: 100; }
        .modal { background: white; border-radius: 12px; width: 400px; padding: 1.5rem; }
        .membership-modal { width: 500px; }
        .header-title p { font-size: 0.8rem; color: #64748b; margin-top: 0.25rem; }
        
        .membership-list { display: flex; flex-direction: column; gap: 0.75rem; margin-top: 1.5rem; max-height: 400px; overflow-y: auto; }
        .membership-item { display: flex; align-items: center; justify-content: space-between; padding: 1rem; background: #f8fafc; border-radius: 8px; border: 1px solid #f1f5f9; transition: all 0.2s; }
        .membership-item.member { border-color: #dbeafe; background: #eff6ff; }
        .proj-info { display: flex; flex-direction: column; gap: 0.1rem; }
        .proj-info strong { font-size: 0.9rem; }
        .proj-info span { font-size: 0.7rem; color: #64748b; font-family: monospace; }
        
        .btn-toggle { display: flex; align-items: center; gap: 0.4rem; padding: 0.4rem 0.75rem; border-radius: 6px; font-size: 0.75rem; font-weight: 700; cursor: pointer; border: 1px solid transparent; }
        .btn-toggle.add { background: var(--primary-color); color: white; }
        .btn-toggle.remove { background: #fee2e2; color: #991b1b; }
      `}</style>
    </div>
  );
};

export default Users;
