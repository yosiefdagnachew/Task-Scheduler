import React, { useState } from 'react';
import { changePassword } from '../services/api';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function ChangePassword() {
  const [current, setCurrent] = useState('');
  const [nextPwd, setNextPwd] = useState('');
  const [error, setError] = useState(null);
  const navigate = useNavigate();
  const { refresh } = useAuth();

  const submit = async (e) => {
    e.preventDefault();
    setError(null);
    try {
      await changePassword({ current_password: current || undefined, new_password: nextPwd });
      await refresh();
      navigate('/');
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to change password');
    }
  };

  return (
    <div className="max-w-sm mx-auto card p-6">
      <h2 className="text-xl font-bold mb-4">Change Password</h2>
      {error && <div className="mb-3 text-red-600">{error}</div>}
      <form onSubmit={submit} className="space-y-3">
        <input className="input-field" type="password" placeholder="Current password (if prompted)" value={current} onChange={e=>setCurrent(e.target.value)} />
        <input className="input-field" type="password" placeholder="New password" value={nextPwd} onChange={e=>setNextPwd(e.target.value)} required />
        <div className="flex justify-end">
          <button type="submit" className="btn-primary">Save</button>
        </div>
      </form>
    </div>
  );
}


