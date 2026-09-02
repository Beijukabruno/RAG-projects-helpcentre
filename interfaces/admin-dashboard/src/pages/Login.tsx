import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';

const Login = () => {
  const { loginWithKeycloak } = useAuth();
  const [error, setError] = useState('');

  const handleKeycloakLogin = async () => {
    setError('');
    try {
      await loginWithKeycloak();
    } catch (err: any) {
      setError(err.message || 'Unable to start the Keycloak sign-in flow.');
    }
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <h1>Help Centre Admin</h1>
        <p>Use your authorised Keycloak account to access the admin console.</p>
        <p className="helper-text">You will be redirected to the Keycloak sign-in page, where you enter your work email and password. This app does not collect those credentials directly.</p>

        {error && <div className="error-message">{error}</div>}

        <button type="button" className="login-button" onClick={handleKeycloakLogin}>Continue with Keycloak</button>
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
        .helper-text {
          font-size: 0.9rem;
          color: #64748b;
          margin-bottom: 1.25rem;
          line-height: 1.5;
        }
        .divider {
          text-align: center;
          color: #64748b;
          margin: 1rem 0;
          font-size: 0.85rem;
        }
      `}</style>
    </div>
  );
};

export default Login;
