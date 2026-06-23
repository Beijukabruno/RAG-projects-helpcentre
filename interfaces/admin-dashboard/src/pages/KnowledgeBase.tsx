import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  Upload, 
  FileText, 
  File as FileIcon, 
  CheckCircle, 
  Clock, 
  AlertCircle,
  Play,
  Trash2,
  RefreshCcw,
  ExternalLink,
  ChevronLeft,
  Search,
  Zap
} from 'lucide-react';

interface KBAsset {
  id: string;
  source_name: string;
  source_url: string;
  source_file: string;
  status: string;
  created_at: string;
}

const KnowledgeBase = () => {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const [assets, setAssets] = useState<KBAsset[]>([]);
  const [audience, setAudience] = useState('general');
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  
  // Test Search state
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [searching, setSearching] = useState(false);
  
  // Upload form
  const [file, setFile] = useState<File | null>(null);
  const [sourceName, setSourceName] = useState('');
  const [sourceUrl, setSourceUrl] = useState('');

  useEffect(() => {
    fetchAssets();
  }, [projectId, audience]);

  const fetchAssets = async () => {
    setLoading(true);
    try {
      const resp = await axios.get(`/admin/projects/${projectId}/knowledge-base?audience=${audience}`);
      setAssets(resp.data.assets);
    } catch (err) {
      console.error('Failed to fetch KB assets', err);
    } finally {
      setLoading(false);
    }
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('audience', audience);
    if (sourceName) formData.append('source_name', sourceName);
    if (sourceUrl) formData.append('source_url', sourceUrl);

    try {
      await axios.post(`/admin/projects/${projectId}/knowledge-base`, formData);
      setFile(null);
      setSourceName('');
      setSourceUrl('');
      fetchAssets();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const activateAsset = async (assetId: string) => {
    try {
      const resp = await axios.post(`/admin/projects/${projectId}/knowledge-base/${assetId}/activate?audience=${audience}`);
      alert(`Asset activated! Chunks created: ${resp.data.chunk_count}. Retrieval check: ${resp.data.verification?.retrieval_ok ? 'PASSED' : 'FAILED'}`);
      fetchAssets();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Activation failed');
    }
  };

  const deleteAsset = async (fileName: string) => {
    if (!window.confirm(`Delete ${fileName}? This will also remove its indexed chunks.`)) return;
    try {
      await axios.delete(`/admin/projects/${projectId}/knowledge-base/${fileName}?audience=${audience}`);
      fetchAssets();
    } catch (err) {
      alert('Failed to delete asset');
    }
  };

  const handleTestSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    setSearching(true);
    try {
      // Use the public search endpoint to verify indexing
      const resp = await axios.post(`/api/search/${audience}`, { 
        query: searchQuery, 
        k: 3,
        project_id: projectId 
      });
      setSearchResults(resp.data.matches || []);
    } catch (err) {
      console.error('Search verification failed', err);
      alert('Search failed. The project index might not be ready yet.');
    } finally {
      setSearching(false);
    }
  };

  return (
    <div className="kb-page">
      <div className="breadcrumb">
        <button className="btn-back" onClick={() => navigate('/projects')}>
          <ChevronLeft size={18} />
          <span>Back to Projects</span>
        </button>
      </div>

      <div className="kb-header">
        <div className="project-info">
          <h1>{projectId} Knowledge Base</h1>
          <div className="tabs">
            <button className={audience === 'general' ? 'active' : ''} onClick={() => setAudience('general')}>General Audience</button>
            <button className={audience === 'clinicians' ? 'active' : ''} onClick={() => setAudience('clinicians')}>Clinicians</button>
          </div>
        </div>
      </div>

      <div className="kb-layout">
        <div className="kb-sidebar">
          <section className="upload-section card">
            <h3>Upload New Source</h3>
            <form onSubmit={handleUpload}>
              <div className="dropzone" onClick={() => document.getElementById('fileInput')?.click()}>
                <Upload size={32} />
                <span>{file ? file.name : 'Select .md, .pdf, or .csv'}</span>
                <input id="fileInput" type="file" style={{ display: 'none' }} onChange={e => setFile(e.target.files?.[0] || null)} accept=".md,.pdf,.csv" />
              </div>
              <div className="form-group">
                <label>Source Name</label>
                <input placeholder="Friendly name" value={sourceName} onChange={e => setSourceName(e.target.value)} />
              </div>
              <button type="submit" className="btn-primary" disabled={!file || uploading}>
                {uploading ? <RefreshCcw size={18} className="spin" /> : <Upload size={18} />}
                <span>{uploading ? 'Processing...' : 'Upload Source'}</span>
              </button>
            </form>
          </section>

          <section className="search-verify-section card">
            <h3><Zap size={16} /> Retrieval Preview</h3>
            <p className="hint">Test if your indexed content is searchable.</p>
            <form onSubmit={handleTestSearch} className="search-verify-form">
              <div className="search-input-wrapper">
                <Search size={16} />
                <input 
                  placeholder="Enter keywords..." 
                  value={searchQuery}
                  onChange={e => setSearchQuery(e.target.value)}
                />
              </div>
              <button type="submit" disabled={searching}>Verify</button>
            </form>

            <div className="verify-results">
              {searching ? <div className="searching">Querying index...</div> : 
               searchResults.map((res, i) => (
                <div key={i} className="verify-item">
                  <span className="res-file">{res.source_file}</span>
                  <p className="res-text">"{res.markdown?.substring(0, 100)}..."</p>
                </div>
              ))}
              {!searching && searchQuery && searchResults.length === 0 && <div className="no-res">No chunks found.</div>}
            </div>
          </section>
        </div>

        <section className="assets-section card">
          <div className="section-header">
            <h3>Managed Assets</h3>
            <button className="btn-icon" onClick={fetchAssets}><RefreshCcw size={16} /></button>
          </div>
          
          <div className="asset-list">
            {loading ? <div className="list-loading">Loading...</div> : 
             assets.length === 0 ? <div className="empty-state">No assets found.</div> :
             assets.map(asset => (
              <div key={asset.id} className="asset-item">
                <div className="asset-icon">{asset.source_file.endsWith('.pdf') ? <FileText color="#ef4444" /> : <FileIcon color="#3b82f6" />}</div>
                <div className="asset-info">
                  <span className="asset-name">{asset.source_name}</span>
                  <span className="asset-file">{asset.source_file}</span>
                </div>
                <div className={`asset-status ${asset.status}`}><span>{asset.status.replace('_', ' ')}</span></div>
                <div className="asset-actions">
                  {asset.status === 'pending_review' && (
                    <button className="btn-activate" onClick={() => activateAsset(asset.id)}>
                      <Play size={14} /> <span>Activate</span>
                    </button>
                  )}
                  <button className="btn-icon danger" onClick={() => deleteAsset(asset.source_file)}><Trash2 size={16} /></button>
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>

      <style>{`
        .kb-page { display: flex; flex-direction: column; gap: 1.5rem; }
        .btn-back { display: flex; align-items: center; gap: 0.5rem; background: none; border: none; color: #64748b; font-weight: 500; cursor: pointer; }
        .kb-header { margin-bottom: 1rem; }
        .project-info h1 { font-size: 1.5rem; margin-bottom: 1rem; text-transform: uppercase; }
        .tabs { display: flex; gap: 1rem; border-bottom: 1px solid var(--border-color); }
        .tabs button { padding: 0.75rem 1.25rem; background: none; border: none; border-bottom: 2px solid transparent; color: #64748b; font-weight: 600; cursor: pointer; }
        .tabs button.active { color: var(--primary-color); border-bottom-color: var(--primary-color); }
        
        .kb-layout { display: grid; grid-template-columns: 350px 1fr; gap: 1.5rem; align-items: start; }
        .kb-sidebar { display: flex; flex-direction: column; gap: 1.5rem; }
        .card { background: white; border-radius: 12px; border: 1px solid var(--border-color); padding: 1.5rem; }
        .card h3 { font-size: 1rem; margin-bottom: 1rem; display: flex; align-items: center; gap: 0.5rem; }
        
        .dropzone { border: 2px dashed var(--border-color); border-radius: 8px; padding: 1.5rem 1rem; display: flex; flex-direction: column; align-items: center; gap: 0.5rem; color: #64748b; font-size: 0.8rem; cursor: pointer; margin-bottom: 1rem; text-align: center; }
        .form-group { margin-bottom: 1rem; display: flex; flex-direction: column; gap: 0.4rem; }
        .form-group label { font-size: 0.8rem; font-weight: 600; }
        .form-group input { padding: 0.6rem; border: 1px solid var(--border-color); border-radius: 6px; }
        
        .search-verify-section { background: #fcfdfe; }
        .search-verify-form { display: flex; gap: 0.5rem; margin-bottom: 1rem; }
        .search-input-wrapper { flex: 1; display: flex; align-items: center; gap: 0.5rem; background: white; border: 1px solid var(--border-color); padding: 0.4rem 0.75rem; border-radius: 6px; }
        .search-input-wrapper input { border: none; outline: none; width: 100%; font-size: 0.85rem; }
        .search-verify-form button { background: var(--primary-color); color: white; border: none; padding: 0.4rem 0.8rem; border-radius: 6px; font-weight: 600; font-size: 0.85rem; cursor: pointer; }
        .verify-results { display: flex; flex-direction: column; gap: 0.5rem; max-height: 200px; overflow-y: auto; }
        .verify-item { padding: 0.6rem; background: white; border: 1px solid #f1f5f9; border-radius: 6px; }
        .res-file { font-size: 0.65rem; font-weight: 700; color: var(--primary-color); text-transform: uppercase; }
        .res-text { font-size: 0.75rem; color: #64748b; font-style: italic; }
        
        .section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; }
        .asset-list { display: flex; flex-direction: column; gap: 0.75rem; }
        .asset-item { display: flex; align-items: center; gap: 1rem; padding: 1rem; background: #f8fafc; border-radius: 10px; border: 1px solid #f1f5f9; }
        .asset-info { flex: 1; display: flex; flex-direction: column; gap: 0.1rem; }
        .asset-name { font-weight: 600; font-size: 0.9rem; }
        .asset-file { font-size: 0.75rem; color: #64748b; font-family: monospace; }
        .asset-status { font-size: 0.65rem; font-weight: 700; text-transform: uppercase; padding: 0.2rem 0.5rem; border-radius: 99px; }
        .asset-status.active { background: #dcfce7; color: #166534; }
        .asset-status.pending_review { background: #fef9c3; color: #854d0e; }
        .btn-activate { background: var(--primary-color); color: white; border: none; padding: 0.3rem 0.6rem; border-radius: 4px; font-size: 0.7rem; font-weight: 700; display: flex; align-items: center; gap: 0.3rem; cursor: pointer; }
        .spin { animation: spin 1s linear infinite; }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
};

export default KnowledgeBase;
