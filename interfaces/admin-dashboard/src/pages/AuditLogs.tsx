import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  History, 
  Search, 
  Filter, 
  Download,
  AlertTriangle,
  MessageSquare,
  ShieldAlert,
  ChevronRight
} from 'lucide-react';

interface AuditLog {
  id: string;
  actor_email: string;
  action: string;
  entity_type: string;
  entity_id: string;
  project_id: string;
  payload: any;
  created_at: string;
}

interface ToxicMessage {
  id: string;
  project_id: string;
  message: string;
  toxicity: any;
  created_at: string;
}

const AuditLogs = () => {
  const [activeTab, setActiveTab] = useState<'audit' | 'toxicity'>('audit');
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [toxicMsgs, setToxicMsgs] = useState<ToxicMessage[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [projectId, setProjectId] = useState('');

  useEffect(() => {
    if (activeTab === 'audit') fetchLogs();
    else fetchToxicity();
  }, [projectId, activeTab]);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const url = projectId 
        ? `/admin/projects/${projectId}/audit-logs` 
        : '/admin/audit-logs';
      const resp = await axios.get(url);
      setLogs(resp.data.logs);
    } catch (err) {
      console.error('Failed to fetch audit logs', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchToxicity = async () => {
    setLoading(true);
    try {
      const resp = await axios.get('/admin/toxicity-feed');
      setToxicMsgs(resp.data.messages);
    } catch (err) {
      console.error('Failed to fetch toxicity feed', err);
    } finally {
      setLoading(false);
    }
  };

  const filteredLogs = logs.filter(log => 
    log.actor_email.toLowerCase().includes(searchTerm.toLowerCase()) ||
    log.action.toLowerCase().includes(searchTerm.toLowerCase()) ||
    log.entity_id?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="audit-page">
      <div className="tab-header">
        <button 
          className={activeTab === 'audit' ? 'active' : ''} 
          onClick={() => setActiveTab('audit')}
        >
          <History size={18} />
          <span>System Audit Logs</span>
        </button>
        <button 
          className={activeTab === 'toxicity' ? 'active' : ''} 
          onClick={() => setActiveTab('toxicity')}
        >
          <ShieldAlert size={18} />
          <span>Toxicity Monitoring</span>
        </button>
      </div>

      <div className="filter-bar">
        <div className="search-box">
          <Search size={18} />
          <input 
            placeholder={activeTab === 'audit' ? "Filter logs..." : "Search toxic content..."} 
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
          />
        </div>
        
        {activeTab === 'audit' && (
          <div className="filters">
            <div className="filter-group">
              <Filter size={16} />
              <select value={projectId} onChange={e => setProjectId(e.target.value)}>
                <option value="">All Projects</option>
                <option value="tb">TB</option>
                <option value="cervical_cancer">Cervical Cancer</option>
              </select>
            </div>
          </div>
        )}
      </div>

      <div className="log-container card">
        {loading ? (
          <div className="loading-state">Synchronizing records...</div>
        ) : activeTab === 'audit' ? (
          <div className="log-list">
            {filteredLogs.map(log => (
              <div key={log.id} className="log-item">
                <div className="log-time">
                  <span className="date">{new Date(log.created_at).toLocaleDateString()}</span>
                  <span className="time">{new Date(log.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                </div>
                <div className="log-icon">
                  <div className={`circle ${log.action.includes('delete') ? 'danger' : 'info'}`}></div>
                </div>
                <div className="log-content">
                  <p className="log-msg">
                    <span className="actor">{log.actor_email}</span>
                    <span className="action">{log.action.replace('.', ' ')}</span>
                    <span className="entity">{log.entity_type}: {log.entity_id}</span>
                  </p>
                  {log.project_id && <span className="log-project">{log.project_id}</span>}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="toxic-list">
            {toxicMsgs.map(msg => (
              <div key={msg.id} className="toxic-item">
                <div className="toxic-meta">
                  <span className="badge danger">Toxic</span>
                  <span className="project">{msg.project_id}</span>
                  <span className="time">{new Date(msg.created_at).toLocaleString()}</span>
                </div>
                <div className="toxic-content">
                  <MessageSquare size={16} className="icon" />
                  <p>"{msg.message}"</p>
                </div>
                <div className="toxic-details">
                  <AlertTriangle size={14} color="#ef4444" />
                  <span>Flagged by Roberta Guardrail</span>
                  <pre>{JSON.stringify(msg.toxicity, null, 2)}</pre>
                </div>
              </div>
            ))}
            {toxicMsgs.length === 0 && <div className="empty-state">No toxicity alerts found.</div>}
          </div>
        )}
      </div>

      <style>{`
        .audit-page { display: flex; flex-direction: column; gap: 1.5rem; }
        .tab-header { display: flex; gap: 2rem; border-bottom: 1px solid var(--border-color); margin-bottom: 0.5rem; }
        .tab-header button {
          display: flex; align-items: center; gap: 0.6rem; padding: 1rem 0.5rem;
          background: none; border: none; border-bottom: 2px solid transparent;
          color: #64748b; font-weight: 600; cursor: pointer; transition: all 0.2s;
        }
        .tab-header button.active { color: var(--primary-color); border-bottom-color: var(--primary-color); }
        
        .filter-bar { display: flex; justify-content: space-between; align-items: center; gap: 1.5rem; }
        .search-box {
          flex: 1; display: flex; align-items: center; gap: 0.75rem; background: white;
          padding: 0.6rem 1rem; border-radius: 8px; border: 1px solid var(--border-color);
        }
        .search-box input { border: none; outline: none; width: 100%; font-size: 0.9rem; }
        .filter-group {
          display: flex; align-items: center; gap: 0.5rem; background: white;
          padding: 0.4rem 0.75rem; border-radius: 8px; border: 1px solid var(--border-color);
          color: #64748b; font-size: 0.85rem; font-weight: 500;
        }
        .filter-group select { border: none; outline: none; background: transparent; font-weight: 600; color: #1e293b; }
        
        .card { background: white; border-radius: 12px; border: 1px solid var(--border-color); overflow: hidden; }
        .log-item { display: flex; align-items: center; gap: 1.5rem; padding: 1.25rem; border-bottom: 1px solid #f1f5f9; }
        .log-time { display: flex; flex-direction: column; min-width: 100px; }
        .log-time .date { font-size: 0.85rem; font-weight: 600; }
        .log-time .time { font-size: 0.75rem; color: #94a3b8; }
        .circle { width: 10px; height: 10px; border-radius: 50%; }
        .circle.info { background: var(--primary-color); }
        .circle.danger { background: var(--error-color); }
        .log-content { flex: 1; display: flex; flex-direction: column; gap: 0.25rem; }
        .actor { font-weight: 700; color: #1e293b; margin-right: 0.5rem; }
        .action { font-weight: 600; color: var(--primary-color); margin-right: 0.5rem; }
        .log-project { font-size: 0.7rem; font-weight: 700; background: #f1f5f9; padding: 0.1rem 0.4rem; border-radius: 4px; width: fit-content; text-transform: uppercase; }

        .toxic-list { display: flex; flex-direction: column; }
        .toxic-item { padding: 1.5rem; border-bottom: 1px solid #f1f5f9; display: flex; flex-direction: column; gap: 1rem; }
        .toxic-meta { display: flex; align-items: center; gap: 1rem; font-size: 0.8rem; font-weight: 600; }
        .badge.danger { background: #fee2e2; color: #991b1b; padding: 0.2rem 0.5rem; border-radius: 4px; }
        .project { text-transform: uppercase; color: #64748b; }
        .toxic-content { display: flex; gap: 0.75rem; background: #f8fafc; padding: 1rem; border-radius: 8px; border-left: 4px solid #ef4444; }
        .toxic-content p { font-style: italic; color: #1e293b; }
        .toxic-details { display: flex; align-items: center; gap: 0.5rem; font-size: 0.75rem; color: #64748b; }
        .toxic-details pre { margin-left: auto; font-size: 0.65rem; background: #f1f5f9; padding: 0.25rem; border-radius: 4px; }

        .loading-state, .empty-state { padding: 4rem; text-align: center; color: #94a3b8; }
      `}</style>
    </div>
  );
};

export default AuditLogs;
