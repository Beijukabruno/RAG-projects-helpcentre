import React from 'react';
import { Outlet, Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { 
  LayoutDashboard, 
  FolderKanban, 
  Users as UsersIcon, 
  History, 
  LogOut,
  ChevronRight,
  ShieldCheck,
  MessageSquare
} from 'lucide-react';

const Layout = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  
  const isSuperAdmin = user?.roles?.includes('super_admin');

  const navItems = [
    { path: '/', label: 'Dashboard', icon: <LayoutDashboard size={20} /> },
    { path: '/projects', label: 'Projects', icon: <FolderKanban size={20} /> },
    { path: '/history', label: 'Chat History', icon: <MessageSquare size={20} /> },
    ...(isSuperAdmin ? [{ path: '/users', label: 'User Management', icon: <UsersIcon size={20} /> }] : []),
    { path: '/audit-logs', label: 'System Logs', icon: <History size={20} /> },
  ];

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const getPageTitle = () => {
    const item = navItems.find(i => i.path === location.pathname);
    if (item) return item.label;
    if (location.pathname.includes('/kb')) return 'Knowledge Base';
    return 'Admin Portal';
  };

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="sidebar-header">
          <ShieldCheck color="var(--primary-color)" size={32} />
          <div className="logo-text">
            <span>Help Centre</span>
            <small>Admin Portal</small>
          </div>
        </div>
        
        <nav className="nav-menu">
          {navItems.map((item) => (
            <Link 
              key={item.path} 
              to={item.path} 
              className={`nav-item ${location.pathname === item.path ? 'active' : ''}`}
            >
              <span className="icon">{item.icon}</span>
              <span className="label">{item.label}</span>
              {location.pathname === item.path && <ChevronRight size={16} className="active-indicator" />}
            </Link>
          ))}
        </nav>
        
        <div className="sidebar-footer">
          <div className="user-info">
            <p className="user-name">{user?.full_name}</p>
            <p className="user-role">{isSuperAdmin ? 'Super Admin' : 'Project Admin'}</p>
          </div>
          <button onClick={handleLogout} className="logout-button">
            <LogOut size={18} />
            <span>Sign Out</span>
          </button>
        </div>
      </aside>
      
      <main className="main-content">
        <header className="top-header">
          <h2>{getPageTitle()}</h2>
        </header>
        <div className="page-container">
          <Outlet />
        </div>
      </main>
      
      <style>{`
        .layout { display: flex; height: 100vh; }
        .sidebar { width: 280px; background: var(--sidebar-bg); border-right: 1px solid var(--border-color); display: flex; flex-direction: column; z-index: 10; }
        .sidebar-header { padding: 2rem 1.5rem; display: flex; align-items: center; gap: 0.75rem; }
        .logo-text { display: flex; flex-direction: column; }
        .logo-text span { font-weight: 700; font-size: 1.1rem; color: #0f172a; }
        .logo-text small { font-size: 0.75rem; color: #64748b; font-weight: 500; }
        .nav-menu { flex: 1; padding: 0.5rem; }
        .nav-item { display: flex; align-items: center; gap: 0.75rem; padding: 0.75rem 1rem; border-radius: 8px; margin-bottom: 0.25rem; color: #64748b; font-weight: 500; transition: all 0.2s; }
        .nav-item:hover { background-color: #f1f5f9; color: var(--primary-color); }
        .nav-item.active { background-color: #eff6ff; color: var(--primary-color); }
        .active-indicator { margin-left: auto; }
        .sidebar-footer { padding: 1.5rem; border-top: 1px solid var(--border-color); }
        .user-info { margin-bottom: 1rem; }
        .user-name { font-weight: 600; font-size: 0.9rem; color: #0f172a; }
        .user-role { font-size: 0.75rem; color: #64748b; }
        .logout-button { display: flex; align-items: center; gap: 0.5rem; width: 100%; padding: 0.6rem; background: none; border: 1px solid #e2e8f0; border-radius: 6px; color: #64748b; font-weight: 500; transition: all 0.2s; }
        .logout-button:hover { background-color: #fee2e2; color: var(--error-color); border-color: #fecaca; }
        .main-content { flex: 1; overflow-y: auto; display: flex; flex-direction: column; }
        .top-header { background: white; padding: 1.25rem 2rem; border-bottom: 1px solid var(--border-color); display: flex; align-items: center; justify-content: space-between; position: sticky; top: 0; z-index: 5; }
        .top-header h2 { font-size: 1.25rem; font-weight: 600; color: #0f172a; }
        .page-container { padding: 2rem; max-width: 1200px; width: 100%; margin: 0 auto; }
      `}</style>
    </div>
  );
};

export default Layout;
