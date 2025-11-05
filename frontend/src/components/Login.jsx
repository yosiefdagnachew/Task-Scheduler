import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { authLogin } from '../services/api';

export default function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  const submit = async (e) => {
    e.preventDefault();
    setError(null);
    try {
      const res = await authLogin(username, password);
      localStorage.setItem('access_token', res.data.access_token);
      navigate('/');
    } catch (e) {
      setError(e.response?.data?.detail || 'Login failed');
    }
  };

  return (
    <div className="max-w-sm mx-auto card p-6">
      <h2 className="text-xl font-bold mb-4">Login</h2>
      {error && <div className="mb-3 text-red-600">{error}</div>}
      <form onSubmit={submit} className="space-y-3">
        <input className="input-field" placeholder="Username" value={username} onChange={e=>setUsername(e.target.value)} />
        <input className="input-field" type="password" placeholder="Password" value={password} onChange={e=>setPassword(e.target.value)} />
        <div className="flex justify-end">
          <button type="submit" className="btn-primary">Login</button>
        </div>
      </form>
    </div>
  );
}


