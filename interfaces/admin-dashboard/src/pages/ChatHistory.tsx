import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  MessageSquare, 
  Search, 
  Download, 
  ChevronDown, 
  ChevronUp, 
  ExternalLink,
  ShieldAlert,
  User,
  Database,
  Terminal
} from 'lucide-react';

interface ChatRecord {
  id: string;
  session_id: string;
  project_id: string;
  audience: string;
  is_user: boolean;
  message: string;
  llm_prompt: string;
  llm_model: string;
  llm_answer: string;
  sources: any[];
  toxicity_input: any;
  toxicity_output: any;
  created_at: string;
}

const ChatHistory = () => {
  const [records, setRecords] = useState<ChatRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [projectId, setProjectId] = useState('');

  useEffect(() => {
    fetchRecords();
  }, [projectId]);

  const fetchRecords = async () => {
    setLoading(true);
    try {
      const url = projectId 
        ? `/admin/projects/${projectId}/last-records?n=50` 
        : '/admin/last-records?n=50';
      const resp = await axios.get(url);
      setRecords(resp.data.records);
    } catch (err) {
      console.error('Failed to fetch chat records', err);
    } finally {
      setLoading(false);
    }
  };

  const downloadCSV = () => {
    const url = projectId 
      ? `/admin/projects/${projectId}/last-records-csv?n=1000` 
      : '/admin/last-records-csv?n=1000';
    window.open(url, '_blank');
  };

  return (
    <div className="chat-history-page">
      <div className="filter-bar">
        <div className="project-filter">
          <Database size={18} />
          <select value={projectId} onChange={e => setProjectId(e.target.value)}>
            <option value="">All Projects</option>
            <option value="tb">TB</option>
            <option value="cervical_cancer">Cervical Cancer</option>
          </select>
        </div>
        <button className="btn-outline" onClick={downloadCSV}>
          <Download size={16} />
          <span>Export Last 1000 (CSV)</span>
        </button>
      </div>

      <div className="records-list">
        {loading ? (
          <div className="loading-state">Retrieving conversation logs...</div>
        ) : (
          records.map(record => (
            <div key={record.id} className={`record-card ${expandedId === record.id ? 'expanded' : ''}`}>
              <div className="record-summary" onClick={() => setExpandedId(expandedId === record.id ? null : record.id)}>
                <div className="record-meta">
                  <span className={`audience-tag ${record.audience}`}>{record.audience}</span>
                  <span className="project-id">{record.project_id}</span>
                  <span className="timestamp">{new Date(record.created_at).toLocaleString()}</span>
                </div>
                <p className="message-preview">{record.message}</p>
                <div className="expand-icon">
                  {expandedId === record.id ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                </div>
              </div>

              {expandedId === record.id && (
                <div className="record-details">
                  <div className="detail-section">
                    <h4><Terminal size={14} /> LLM Reasoning (RAG Debugger)</h4>
                    <div className="debug-grid">
                      <div className="debug-item">
                        <label>Model</label>
                        <span>{record.llm_model || 'N/A'}</span>
                      </div>
                      <div className="debug-item">
                        <label>Toxicity Score</label>
                        <span className={record.toxicity_output?.toxic ? 'text-danger' : ''}>
                          {record.toxicity_output?.score ? (record.toxicity_output.score * 100).toFixed(1) + '%' : 'N/A'}
                        </span>
                      </div>
                    </div>
                    <div className="code-block">
                      <label>Final Prompt</label>
                      <pre>{record.llm_prompt || 'No prompt recorded.'}</pre>
                    </div>
                  </div>

                  <div className="detail-section">
                    <h4><Database size={14} /> Retrieved Sources</h4>
                    <div className="sources-list">
                      {record.sources && record.sources.length > 0 ? (
                        record.sources.map((src, idx) => (
                          <div key={idx} className="source-item">
                            <div className="source-header">
                              <strong>{src.header || 'Untitled Section'}</strong>
                              <span>{src.source_file}</span>
                            </div>
                            <p className="excerpt">"{src.excerpt}"</p>
                          </div>
                        ))
                      ) : (
                        <p className="empty-msg">No sources were retrieved for this query.</p>
                      )}
                    </div>
                  </div>

                  <div className="detail-section">
                    <h4><MessageSquare size={14} /> AI Response</h4>
                    <div className="ai-answer">
                      {record.llm_answer || 'No answer generated.'}
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))
        )}
        {!loading && records.length === 0 && <div className="empty-state">No chat records found.</div>}
      </div>

      <style>{`
        .chat-history-page { display: flex; flex-direction: column; gap: 1.5rem; }
        .filter-bar { display: flex; justify-content: space-between; align-items: center; }
        .project-filter {
          display: flex; align-items: center; gap: 0.5rem; background: white;
          padding: 0.5rem 0.75rem; border-radius: 8px; border: 1px solid var(--border-color);
        }
        .project-filter select { border: none; outline: none; font-weight: 600; }
        
        .records-list { display: flex; flex-direction: column; gap: 1rem; }
        .record-card {
          background: white; border-radius: 10px; border: 1px solid var(--border-color);
          overflow: hidden; transition: all 0.2s;
        }
        .record-card.expanded { border-color: var(--primary-color); box-shadow: 0 4px 12px rgba(0,0,0,0.05); }
        
        .record-summary {
          padding: 1.25rem; cursor: pointer; display: flex; align-items: center; gap: 1.5rem;
        }
        .record-summary:hover { background: #f8fafc; }
        
        .record-meta { display: flex; flex-direction: column; min-width: 140px; gap: 0.25rem; }
        .audience-tag { font-size: 0.65rem; font-weight: 800; text-transform: uppercase; padding: 0.1rem 0.4rem; border-radius: 4px; width: fit-content; }
        .audience-tag.general { background: #dcfce7; color: #166534; }
        .audience-tag.clinicians { background: #e0e7ff; color: #3730a3; }
        .project-id { font-size: 0.7rem; font-weight: 700; color: #64748b; text-transform: uppercase; }
        .timestamp { font-size: 0.7rem; color: #94a3b8; }
        
        .message-preview { flex: 1; font-size: 0.95rem; color: #1e293b; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .expand-icon { color: #94a3b8; }
        
        .record-details { padding: 0 1.25rem 1.25rem; border-top: 1px solid #f1f5f9; display: flex; flex-direction: column; gap: 1.5rem; background: #fcfdfe; }
        .detail-section { display: flex; flex-direction: column; gap: 0.75rem; padding-top: 1.25rem; }
        .detail-section h4 { font-size: 0.85rem; color: #475569; display: flex; align-items: center; gap: 0.5rem; border-bottom: 1px solid #f1f5f9; padding-bottom: 0.5rem; }
        
        .debug-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
        .debug-item { display: flex; flex-direction: column; gap: 0.2rem; }
        .debug-item label { font-size: 0.7rem; font-weight: 700; color: #94a3b8; text-transform: uppercase; }
        .debug-item span { font-size: 0.85rem; font-weight: 600; color: #1e293b; }
        
        .code-block { display: flex; flex-direction: column; gap: 0.4rem; }
        .code-block label { font-size: 0.7rem; font-weight: 700; color: #94a3b8; text-transform: uppercase; }
        .code-block pre { 
          background: #0f172a; color: #e2e8f0; padding: 1rem; border-radius: 6px; 
          font-size: 0.75rem; white-space: pre-wrap; word-break: break-all; max-height: 200px; overflow-y: auto;
        }
        
        .sources-list { display: flex; flex-direction: column; gap: 0.75rem; }
        .source-item { background: white; padding: 0.75rem; border-radius: 6px; border: 1px solid #e2e8f0; }
        .source-header { display: flex; justify-content: space-between; margin-bottom: 0.5rem; font-size: 0.75rem; }
        .source-header strong { color: var(--primary-color); }
        .source-header span { color: #94a3b8; font-family: monospace; }
        .excerpt { font-size: 0.8rem; color: #475569; font-style: italic; line-height: 1.4; }
        
        .ai-answer { background: #eff6ff; padding: 1rem; border-radius: 6px; color: #1e3a8a; font-size: 0.9rem; line-height: 1.5; border: 1px solid #dbeafe; }
        
        .loading-state, .empty-state { padding: 4rem; text-align: center; color: #94a3b8; }
        .text-danger { color: #ef4444; }
      `}</style>
    </div>
  );
};

export default ChatHistory;
