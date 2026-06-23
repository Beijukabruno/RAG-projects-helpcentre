import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  FolderKanban, 
  Users as UsersIcon, 
  MessageSquare, 
  Activity,
  AlertCircle,
  TrendingUp,
  ShieldAlert
} from 'lucide-react';
import { 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  AreaChart,
  Area
} from 'recharts';

interface Stats {
  total_projects: number;
  total_users: number;
  total_messages: number;
  toxic_messages: number;
  system_health: {
    database: string;
    last_audit: string;
  };
  activity_data: { date: string; count: number }[];
  recent_audit_logs: any[];
}

const Dashboard = () => {
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchOverview();
  }, []);

  const fetchOverview = async () => {
    try {
      const resp = await axios.get('/admin/overview');
      setStats(resp.data);
    } catch (err: any) {
      console.error('Failed to fetch overview', err);
      setError('Could not load platform overview. Make sure you have Super Admin privileges.');
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div className="loading">Loading dashboard...</div>;

  return (
    <div className="dashboard">
      {error && (
        <div className="error-banner">
          <AlertCircle size={20} />
          <span>{error}</span>
        </div>
      )}
      
      <div className="stats-grid">
        <StatCard 
          title="Total Projects" 
          value={stats?.total_projects || 0} 
          icon={<FolderKanban size={24} />} 
          color="#3b82f6" 
          trend="Managed Collections"
        />
        <StatCard 
          title="Platform Users" 
          value={stats?.total_users || 0} 
          icon={<UsersIcon size={24} />} 
          color="#10b981" 
          trend="Authorized Admins"
        />
        <StatCard 
          title="Total Queries" 
          value={stats?.total_messages || 0} 
          icon={<MessageSquare size={24} />} 
          color="#8b5cf6" 
          trend="Processed Messages"
        />
        <StatCard 
          title="System Status" 
          value={stats?.system_health?.database === 'ok' ? 'Online' : 'Degraded'} 
          icon={<Activity size={24} />} 
          color={stats?.system_health?.database === 'ok' ? "#f59e0b" : "#ef4444"} 
          trend={stats?.system_health?.database === 'ok' ? "Database Connected" : "DB Connection Error"}
        />
      </div>

      <div className="charts-grid">
        <div className="chart-card">
          <div className="chart-header">
            <div className="header-text">
              <h3><TrendingUp size={18} /> Platform Activity</h3>
              <p>Daily query volume (Last 14 Days)</p>
            </div>
            {stats?.toxic_messages && stats.toxic_messages > 0 ? (
              <div className="toxicity-alert">
                <ShieldAlert size={16} />
                <span>{stats.toxic_messages} Content Alerts</span>
              </div>
            ) : null}
          </div>
          <div className="chart-wrapper">
            {stats?.activity_data && stats.activity_data.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={stats.activity_data}>
                  <defs>
                    <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.1}/>
                      <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                  <XAxis 
                    dataKey="date" 
                    axisLine={false} 
                    tickLine={false} 
                    tick={{fill: '#94a3b8', fontSize: 12}}
                    dy={10}
                    tickFormatter={(str) => {
                      try {
                        const date = new Date(str);
                        return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
                      } catch { return str; }
                    }}
                  />
                  <YAxis 
                    axisLine={false} 
                    tickLine={false} 
                    tick={{fill: '#94a3b8', fontSize: 12}}
                  />
                  <Tooltip 
                    contentStyle={{borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)'}}
                  />
                  <Area 
                    type="monotone" 
                    dataKey="count" 
                    stroke="#3b82f6" 
                    strokeWidth={2}
                    fillOpacity={1} 
                    fill="url(#colorCount)" 
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="empty-chart">No activity data available.</div>
            )}
          </div>
        </div>
      </div>
      
      <div className="recent-activity">
        <div className="section-header">
          <h3>Latest System Activity</h3>
          <p className="last-sync">Last update: {stats?.system_health?.last_audit ? new Date(stats.system_health.last_audit).toLocaleTimeString() : 'N/A'}</p>
        </div>
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Action</th>
                <th>Actor</th>
                <th>Target</th>
                <th>Time</th>
              </tr>
            </thead>
            <tbody>
              {stats?.recent_audit_logs?.map((log: any) => (
                <tr key={log.id}>
                  <td><span className="badge">{log.action}</span></td>
                  <td>{log.actor_email}</td>
                  <td>{log.entity_type}: {log.entity_id}</td>
                  <td>{new Date(log.created_at).toLocaleString()}</td>
                </tr>
              ))}
              {(!stats?.recent_audit_logs || stats.recent_audit_logs.length === 0) && (
                <tr>
                  <td colSpan={4} className="empty-state">No recent activity found.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <style>{`
        .dashboard { display: flex; flex-direction: column; gap: 2rem; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 1.5rem; }
        .stat-card { background: white; padding: 1.5rem; border-radius: 12px; border: 1px solid var(--border-color); display: flex; flex-direction: column; gap: 1rem; }
        .stat-top { display: flex; align-items: center; gap: 1rem; }
        .stat-icon { width: 40px; height: 40px; border-radius: 8px; display: flex; align-items: center; justify-content: center; color: white; }
        .stat-content h4 { font-size: 0.85rem; color: #64748b; margin-bottom: 0.1rem; }
        .stat-content p { font-size: 1.5rem; font-weight: 700; color: #0f172a; }
        .stat-trend { font-size: 0.75rem; color: #94a3b8; font-weight: 500; border-top: 1px solid #f1f5f9; padding-top: 0.75rem; }
        
        .chart-card { background: white; padding: 1.5rem; border-radius: 12px; border: 1px solid var(--border-color); }
        .chart-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 2rem; }
        .chart-header h3 { font-size: 1.1rem; display: flex; align-items: center; gap: 0.5rem; color: #1e293b; }
        .chart-header p { font-size: 0.85rem; color: #64748b; }
        .toxicity-alert { display: flex; align-items: center; gap: 0.5rem; background: #fee2e2; color: #991b1b; padding: 0.4rem 0.75rem; border-radius: 6px; font-size: 0.8rem; font-weight: 700; }

        .recent-activity { background: white; padding: 1.5rem; border-radius: 12px; border: 1px solid var(--border-color); }
        .section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; }
        .section-header h3 { font-size: 1.1rem; color: #0f172a; }
        .last-sync { font-size: 0.75rem; color: #94a3b8; }
        
        .table-wrapper { overflow-x: auto; }
        table { width: 100%; border-collapse: collapse; }
        th { text-align: left; padding: 0.75rem 1rem; font-size: 0.75rem; text-transform: uppercase; color: #64748b; border-bottom: 1px solid var(--border-color); }
        td { padding: 1rem; font-size: 0.9rem; border-bottom: 1px solid #f1f5f9; }
        .badge { background: #f1f5f9; padding: 0.25rem 0.6rem; border-radius: 4px; font-size: 0.75rem; font-weight: 600; color: #475569; }
        .loading { padding: 4rem; text-align: center; color: #64748b; }
      `}</style>
    </div>
  );
};

const StatCard = ({ title, value, icon, color, trend }: any) => (
  <div className="stat-card">
    <div className="stat-top">
      <div className="stat-icon" style={{ backgroundColor: color }}>
        {icon}
      </div>
      <div className="stat-content">
        <h4>{title}</h4>
        <p>{value}</p>
      </div>
    </div>
    <div className="stat-trend">
      {trend}
    </div>
  </div>
);

export default Dashboard;
