import React, { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import { Calendar, Users, BarChart3 } from 'lucide-react';
import Dashboard from './components/Dashboard';
import TeamManagement from './components/TeamManagement';
import ScheduleGenerator from './components/ScheduleGenerator';
import ScheduleView from './components/ScheduleView';
import FairnessView from './components/FairnessView';
import TaskTypes from './components/TaskTypes';
import ConflictSwapManager from './components/ConflictSwapManager';
import Login from './components/Login';
import { getMe } from './services/api';

function Navigation() {
  const location = useLocation();
  const [theme, setTheme] = useState(localStorage.getItem('theme') || 'auto');
  const [me, setMe] = useState(null);

  useEffect(() => {
    const root = document.documentElement;
    const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    const enableDark = theme === 'dark' || (theme === 'auto' && prefersDark);
    root.classList.toggle('dark', !!enableDark);
    localStorage.setItem('theme', theme);
  }, [theme]);

  useEffect(() => {
    getMe().then(res => setMe(res.data)).catch(() => setMe(null));
  }, [location.pathname]);
  
  const isActive = (path) => {
    return location.pathname === path || location.pathname.startsWith(path + '/');
  };

  return (
    <nav className="bg-white/95 backdrop-blur-sm shadow-lg border-b border-gray-200 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex">
            <div className="flex-shrink-0 flex items-center">
              <Link to="/" className="text-2xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent hover:from-indigo-700 hover:to-purple-700 transition-all duration-200">
                📅 Task Scheduler
              </Link>
            </div>
            <div className="hidden sm:ml-8 sm:flex sm:space-x-2">
              <Link
                to="/"
                className={isActive('/') && location.pathname === '/' ? 'nav-link-active' : 'nav-link'}
              >
                <Calendar className="w-4 h-4 mr-2" />
                Dashboard
              </Link>
              <Link
                to="/team"
                className={isActive('/team') ? 'nav-link-active' : 'nav-link'}
              >
                <Users className="w-4 h-4 mr-2" />
                Team
              </Link>
              <Link
                to="/schedule/generate"
                className={isActive('/schedule') ? 'nav-link-active' : 'nav-link'}
              >
                <Calendar className="w-4 h-4 mr-2" />
                Generate
              </Link>
              <Link
                to="/fairness"
                className={isActive('/fairness') ? 'nav-link-active' : 'nav-link'}
              >
                <BarChart3 className="w-4 h-4 mr-2" />
                Fairness
              </Link>
              <Link
                to="/task-types"
                className={isActive('/task-types') ? 'nav-link-active' : 'nav-link'}
              >
                ⚙️ Task Types
              </Link>
              <Link
                to="/conflicts"
                className={isActive('/conflicts') ? 'nav-link-active' : 'nav-link'}
              >
                🔄 Swaps
              </Link>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <select value={theme} onChange={e=>setTheme(e.target.value)} className="border px-2 py-1 rounded text-sm">
              <option value="light">Light</option>
              <option value="dark">Dark</option>
              <option value="auto">Auto</option>
            </select>
            {me ? (
              <span className="text-sm text-gray-600">{me.username} ({me.role})</span>
            ) : (
              <Link to="/login" className="nav-link">Login</Link>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
}

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gray-50">
        <Navigation />

        {/* Main Content */}
        <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/team" element={<TeamManagement />} />
            <Route path="/schedule/generate" element={<ScheduleGenerator />} />
            <Route path="/schedule/:id" element={<ScheduleView />} />
            <Route path="/fairness" element={<FairnessView />} />
            <Route path="/task-types" element={<TaskTypes />} />
            <Route path="/conflicts" element={<ConflictSwapManager />} />
            <Route path="/login" element={<Login />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;

