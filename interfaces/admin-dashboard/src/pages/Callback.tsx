import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import api from '../lib/api';
import { useAuth } from '../context/AuthContext';

const Callback = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { completeLogin } = useAuth();
  const [error, setError] = useState('');

  useEffect(() => {
    const code = searchParams.get('code');
    const redirectUri = `${window.location.origin}/callback`;

    if (!code) {
      setError('No authorization code was returned by Keycloak.');
      return;
    }

    const finishLogin = async () => {
      try {
        const resp = await api.post('/admin/auth/keycloak/callback', {
          code,
          redirect_uri: redirectUri,
        });
        completeLogin(resp.data);
        navigate('/');
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Keycloak login failed.');
      }
    };

    finishLogin();
  }, [completeLogin, navigate, searchParams]);

  return (
    <div style={{ padding: '2rem', textAlign: 'center' }}>
      {error ? <p>{error}</p> : <p>Signing you in with Keycloak...</p>}
    </div>
  );
};

export default Callback;
