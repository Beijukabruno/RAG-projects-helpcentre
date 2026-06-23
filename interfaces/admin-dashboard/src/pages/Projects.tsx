import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Link } from 'react-router-dom';
import { 
  Plus, 
  Database, 
  Settings,
  Trash2,
  CheckCircle2,
  XCircle,
  Save,
  X
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

interface Project {
  id: string;
  name: string;
  description: string;
  domain_owner: string;
  contact_email: string;
  enabled: boolean;
  status: string;
  audiences: string[];
}

const Projects = () => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showSettingsModal, setShowSettingsModal] = useState(false);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const { user } = useAuth();
  
  // Form state
  const [formData, setFormData] = useState({
    id: '',
    name: '',
    description: '',
    domain_owner: '',
    contact_email: '',
    audiences: 'general, clinicians'
  });

  useEffect(() => {
    fetchProjects();
  }, []);

  const fetchProjects = async () => {
    try {
      const resp = await axios.get('/admin/projects');
      setProjects(resp.data.projects);
    } catch (err) {
      console.error('Failed to fetch projects', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const payload = {
        ...formData,
        audiences: formData.audiences.split(',').map(s => s.trim())
      };
      await axios.post('/admin/projects', payload);
      setShowCreateModal(false);
      fetchProjects();
      setFormData({ id: '', name: '', description: '', domain_owner: '', contact_email: '', audiences: 'general, clinicians' });
    } catch (err: any) {
      const msg = err.response?.data?.detail;
      alert(typeof msg === 'string' ? msg : JSON.stringify(msg) || 'Failed to create project');
    }
  };

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedProject) return;
    try {
      await axios.patch(`/admin/projects/${selectedProject.id}`, selectedProject);
      setShowSettingsModal(false);
      fetchProjects();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to update project');
    }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm(`Are you sure you want to delete project "${id}"? This cannot be undone.`)) return;
    try {
      await axios.delete(`/admin/projects/${id}`);
      fetchProjects();
    } catch (err) {
      alert('Failed to delete project');
    }
  };

  const openSettings = (project: Project) => {
    setSelectedProject({ ...project });
    setShowSettingsModal(true);
  };

  if (loading) return <div className="loading">Loading projects...</div>;

  return (
    <div className="projects-page">
      <div className="action-bar">
        <p>{projects.length} projects registered</p>
        {user?.roles?.includes('super_admin') && (
          <button className="btn-primary" onClick={() => setShowCreateModal(true)}>
            <Plus size={18} />
            <span>Onboard New Project</span>
          </button>
        )}
      </div>

      <div className="project-grid">
        {projects.map((project) => (
          <div key={project.id} className="project-card">
            <div className="card-header">
              <div className="status-indicator">
                {project.enabled ? <CheckCircle2 size={16} color="var(--success-color)" /> : <XCircle size={16} color="var(--error-color)" />}
                <span className="project-id">{project.id}</span>
              </div>
              <div className="card-actions">
                {user?.roles?.includes('super_admin') && (
                  <button className="btn-icon danger" onClick={() => handleDelete(project.id)}>
                    <Trash2 size={16} />
                  </button>
                )}
              </div>
            </div>
            
            <h3>{project.name}</h3>
            <p className="description">{project.description || 'No description provided.'}</p>
            
            <div className="meta-info">
              <div className="meta-item">
                <span className="label">Owner:</span>
                <span className="value">{project.domain_owner || 'N/A'}</span>
              </div>
              <div className="meta-item">
                <span className="label">Audiences:</span>
                <div className="audiences">
                  {project.audiences.map(a => <span key={a} className="tag">{a}</span>)}
                </div>
              </div>
            </div>
            
            <div className="card-footer">
              <Link to={`/projects/${project.id}/kb`} className="btn-outline">
                <Database size={16} />
                <span>Knowledge Base</span>
              </Link>
              <button className="btn-outline" onClick={() => openSettings(project)}>
                <Settings size={16} />
                <span>Settings</span>
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Create Project Modal */}
      {showCreateModal && (
        <div className="modal-overlay">
          <div className="modal">
            <div className="modal-header">
              <h3>Onboard New Project</h3>
              <button className="btn-close" onClick={() => setShowCreateModal(false)}><X size={20}/></button>
            </div>
            <form onSubmit={handleCreate}>
              <div className="form-row">
                <div className="form-group">
                  <label>Project ID (Slug)</label>
                  <input 
                    placeholder="e.g. maternal_health" 
                    value={formData.id} 
                    onChange={e => setFormData({...formData, id: e.target.value})} 
                    required 
                  />
                </div>
                <div className="form-group">
                  <label>Display Name</label>
                  <input 
                    placeholder="e.g. Maternal Health Centre" 
                    value={formData.name} 
                    onChange={e => setFormData({...formData, name: e.target.value})} 
                    required 
                  />
                </div>
              </div>
              <div className="form-group">
                <label>Description</label>
                <textarea 
                  placeholder="What is this project about?" 
                  value={formData.description} 
                  onChange={e => setFormData({...formData, description: e.target.value})} 
                />
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Domain Owner</label>
                  <input 
                    placeholder="Entity or Person name" 
                    value={formData.domain_owner} 
                    onChange={e => setFormData({...formData, domain_owner: e.target.value})} 
                  />
                </div>
                <div className="form-group">
                  <label>Contact Email</label>
                  <input 
                    type="email" 
                    placeholder="owner@example.com" 
                    value={formData.contact_email} 
                    onChange={e => setFormData({...formData, contact_email: e.target.value})} 
                  />
                </div>
              </div>
              <div className="form-group">
                <label>Audiences (comma separated)</label>
                <input 
                  value={formData.audiences} 
                  onChange={e => setFormData({...formData, audiences: e.target.value})} 
                />
              </div>
              <div className="modal-footer">
                <button type="button" className="btn-outline" onClick={() => setShowCreateModal(false)}>Cancel</button>
                <button type="submit" className="btn-primary">Create Project</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Settings Modal */}
      {showSettingsModal && selectedProject && (
        <div className="modal-overlay">
          <div className="modal">
            <div className="modal-header">
              <h3>Project Settings: {selectedProject.id}</h3>
              <button className="btn-close" onClick={() => setShowSettingsModal(false)}><X size={20}/></button>
            </div>
            <form onSubmit={handleUpdate}>
              <div className="form-group">
                <label>Display Name</label>
                <input 
                  value={selectedProject.name} 
                  onChange={e => setSelectedProject({...selectedProject, name: e.target.value})} 
                  required 
                />
              </div>
              <div className="form-group">
                <label>Description</label>
                <textarea 
                  value={selectedProject.description} 
                  onChange={e => setSelectedProject({...selectedProject, description: e.target.value})} 
                />
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Status</label>
                  <select 
                    value={selectedProject.status}
                    onChange={e => setSelectedProject({...selectedProject, status: e.target.value})}
                  >
                    <option value="active">Active</option>
                    <option value="paused">Paused</option>
                    <option value="retired">Retired</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Enabled</label>
                  <div className="toggle-group">
                    <input 
                      type="checkbox" 
                      checked={selectedProject.enabled}
                      onChange={e => setSelectedProject({...selectedProject, enabled: e.target.checked})}
                    />
                    <span>Allow public traffic</span>
                  </div>
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn-outline" onClick={() => setShowSettingsModal(false)}>Cancel</button>
                <button type="submit" className="btn-primary">
                  <Save size={18} />
                  <span>Save Changes</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <style>{`
        .projects-page { display: flex; flex-direction: column; gap: 1.5rem; }
        .action-bar { display: flex; justify-content: space-between; align-items: center; padding-bottom: 1rem; border-bottom: 1px solid var(--border-color); }
        .action-bar p { font-size: 0.9rem; color: #64748b; font-weight: 500; }
        .btn-primary { background-color: var(--primary-color); color: white; border: none; padding: 0.6rem 1.25rem; border-radius: 6px; display: flex; align-items: center; gap: 0.5rem; font-weight: 600; transition: background 0.2s; }
        .btn-primary:hover { background-color: var(--primary-hover); }
        .btn-outline { background: white; color: #475569; border: 1px solid var(--border-color); padding: 0.5rem 0.75rem; border-radius: 6px; display: flex; align-items: center; gap: 0.4rem; font-size: 0.85rem; font-weight: 500; transition: all 0.2s; }
        .btn-outline:hover { background-color: #f8fafc; border-color: #cbd5e1; color: var(--primary-color); }
        .project-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 1.5rem; }
        .project-card { background: white; border-radius: 12px; border: 1px solid var(--border-color); padding: 1.5rem; display: flex; flex-direction: column; gap: 1rem; transition: transform 0.2s, box-shadow 0.2s; }
        .project-card:hover { transform: translateY(-2px); box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05); }
        .card-header { display: flex; justify-content: space-between; align-items: center; }
        .status-indicator { display: flex; align-items: center; gap: 0.5rem; }
        .project-id { font-family: monospace; font-size: 0.75rem; background: #f1f5f9; padding: 0.2rem 0.5rem; border-radius: 4px; color: #475569; }
        .project-card h3 { font-size: 1.15rem; color: #0f172a; }
        .description { font-size: 0.9rem; color: #64748b; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; min-height: 2.7rem; }
        .meta-info { background: #f8fafc; padding: 1rem; border-radius: 8px; display: flex; flex-direction: column; gap: 0.75rem; }
        .meta-item { display: flex; flex-direction: column; gap: 0.25rem; }
        .meta-item .label { font-size: 0.75rem; text-transform: uppercase; font-weight: 600; color: #94a3b8; }
        .meta-item .value { font-size: 0.85rem; font-weight: 500; color: #334155; }
        .audiences { display: flex; flex-wrap: wrap; gap: 0.4rem; }
        .tag { font-size: 0.75rem; background: #eff6ff; color: var(--primary-color); padding: 0.15rem 0.5rem; border-radius: 99px; font-weight: 600; }
        .card-footer { display: flex; gap: 0.75rem; margin-top: auto; padding-top: 0.5rem; }
        .btn-icon { background: none; border: none; padding: 0.4rem; border-radius: 4px; color: #94a3b8; transition: all 0.2s; }
        .btn-icon:hover { background: #f1f5f9; color: #475569; }
        .btn-icon.danger:hover { background: #fee2e2; color: var(--error-color); }
        .modal-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0, 0, 0, 0.4); display: flex; justify-content: center; align-items: center; z-index: 100; backdrop-filter: blur(4px); }
        .modal { background: white; width: 100%; max-width: 600px; border-radius: 12px; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1); overflow: hidden; }
        .modal-header { padding: 1.5rem; border-bottom: 1px solid var(--border-color); display: flex; justify-content: space-between; align-items: center; }
        .btn-close { background: none; border: none; color: #94a3b8; cursor: pointer; }
        form { padding: 1.5rem; display: flex; flex-direction: column; gap: 1.25rem; }
        .form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
        .form-group { display: flex; flex-direction: column; gap: 0.5rem; }
        .form-group label { font-size: 0.85rem; font-weight: 600; color: #475569; }
        .form-group input, .form-group textarea, .form-group select { padding: 0.65rem; border: 1px solid var(--border-color); border-radius: 6px; outline: none; }
        .form-group textarea { height: 80px; resize: vertical; }
        .toggle-group { display: flex; align-items: center; gap: 0.75rem; font-size: 0.85rem; color: #475569; }
        .toggle-group input { width: auto; }
        .modal-footer { display: flex; justify-content: flex-end; gap: 1rem; padding-top: 1rem; border-top: 1px solid var(--border-color); }
        .loading { padding: 4rem; text-align: center; color: #64748b; }
      `}</style>
    </div>
  );
};

export default Projects;
