import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { Link, useNavigate } from 'react-router-dom';
import { DOCS_URL } from '../lib/api';

const Login = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      await login(email, password);
      navigate('/');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Login failed. Please check your credentials.');
    }
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <h1>Help Centre Admin</h1>
        <p>Sign in to manage your medical chatbot projects.</p>
        <p className="login-hint">The bootstrap admin email and password come from BOOTSTRAP_SUPER_ADMIN_EMAIL and BOOTSTRAP_SUPER_ADMIN_PASSWORD. In the sample env, that is admin@example.com / change-me-immediately.</p>
        <a className="docs-link" href={DOCS_URL} target="_blank" rel="noreferrer">Open API docs</a>
        <Link className="docs-link console-link" to="/console">Open endpoint console</Link>
        
        {error && <div className="error-message">{error}</div>}
        
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="email">Email Address</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="admin@example.com"
              required
            />
          </div>
          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
            />
          </div>
          <button type="submit" className="login-button">Sign In</button>
        </form>
      </div>
      
      <style>{`
        .login-container {
          display: flex;
          justify-content: center;
          align-items: center;
          height: 100vh;
          background-color: var(--bg-color);
        }
        .login-card {
          background: white;
          padding: 2.5rem;
          border-radius: 12px;
          box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1);
          width: 100%;
          max-width: 400px;
        }
        h1 {
          font-size: 1.5rem;
          margin-bottom: 0.5rem;
          color: var(--primary-color);
          text-align: center;
        }
        p {
          text-align: center;
          color: #64748b;
          margin-bottom: 2rem;
          font-size: 0.9rem;
        }
        .login-hint {
          margin-top: -1rem;
          margin-bottom: 1.5rem;
          font-size: 0.8rem;
          line-height: 1.5;
          color: #475569;
        }
        .docs-link {
          display: inline-flex;
          margin: 0 auto 1.25rem;
          color: var(--primary-color);
          font-size: 0.85rem;
          font-weight: 700;
          text-decoration: none;
        }
        .form-group {
          margin-bottom: 1.25rem;
        }
        label {
          display: block;
          font-size: 0.85rem;
          font-weight: 500;
          margin-bottom: 0.5rem;
          color: #475569;
        }
        input {
          width: 100%;
          padding: 0.75rem;
          border: 1px solid var(--border-color);
          border-radius: 6px;
          font-size: 1rem;
          outline: none;
          transition: border-color 0.2s;
        }
        input:focus {
          border-color: var(--primary-color);
          box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
        }
        .login-button {
          width: 100%;
          padding: 0.75rem;
          background-color: var(--primary-color);
          color: white;
          border: none;
          border-radius: 6px;
          font-size: 1rem;
          font-weight: 600;
          margin-top: 1rem;
          transition: background-color 0.2s;
        }
        .login-button:hover {
          background-color: var(--primary-hover);
        }
        .error-message {
          background-color: #fee2e2;
          color: var(--error-color);
          padding: 0.75rem;
          border-radius: 6px;
          margin-bottom: 1.5rem;
          font-size: 0.85rem;
          text-align: center;
          border: 1px solid #fecaca;
        }
      `}</style>
    </div>
  );
};

export default Login;
