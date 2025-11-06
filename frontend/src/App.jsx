import React, { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation, Navigate } from 'react-router-dom';
import { Calendar, Users, BarChart3, Moon, Sun, Monitor } from 'lucide-react';
import Dashboard from './components/Dashboard';
import TeamManagement from './components/TeamManagement';
import ScheduleGenerator from './components/ScheduleGenerator';
import ScheduleView from './components/ScheduleView';
import FairnessView from './components/FairnessView';
import TaskTypes from './components/TaskTypes';
import ConflictSwapManager from './components/ConflictSwapManager';
import Login from './components/Login';
import { getMe } from './services/api';
import ChangePassword from './components/ChangePassword';

function Navigation() {
  const location = useLocation();
  const [theme, setTheme] = useState(localStorage.getItem('theme') || 'auto');
  const [me, setMe] = useState(null);
  const [menuOpen, setMenuOpen] = useState(false);

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

  const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;
  const onLoginPage = location.pathname === '/login' && !token;

  return (
    <nav className="bg-white/95 dark:bg-gray-800/95 backdrop-blur-sm shadow-lg border-b border-gray-200 dark:border-gray-700 sticky top-0 z-50 text-gray-900 dark:text-gray-100">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex">
            <div className="flex-shrink-0 flex items-center">
              <Link to="/" className="text-2xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent hover:from-indigo-700 hover:to-purple-700 transition-all duration-200">
                📅 Task Scheduler
              </Link>
            </div>
            {!onLoginPage && (
            <div className="hidden md:ml-8 md:flex md:space-x-2">
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
               {me?.role === 'admin' && (
               <Link
                to="/schedule/generate"
                className={isActive('/schedule') ? 'nav-link-active' : 'nav-link'}
              >
                <Calendar className="w-4 h-4 mr-2" />
                Generate
               </Link>)}
               <Link
                to="/fairness"
                className={isActive('/fairness') ? 'nav-link-active' : 'nav-link'}
              >
                <BarChart3 className="w-4 h-4 mr-2" />
                Fairness
              </Link>
               {me?.role === 'admin' && (
               <Link
                to="/task-types"
                className={isActive('/task-types') ? 'nav-link-active' : 'nav-link'}
              >
                ⚙️ Task Types
               </Link>)}
              <Link
                to="/conflicts"
                className={isActive('/conflicts') ? 'nav-link-active' : 'nav-link'}
              >
                🔄 Swaps
              </Link>
            </div>
            )}
          </div>
          <div className="flex items-center space-x-3">
            {!onLoginPage && (
              <button onClick={()=>setMenuOpen(!menuOpen)} className="md:hidden p-2 rounded border border-gray-300 dark:border-gray-700">☰</button>
            )}
            <button
              onClick={() => setTheme(theme === 'light' ? 'dark' : theme === 'dark' ? 'auto' : 'light')}
              className="p-2 rounded-lg border border-gray-300 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-700"
              title={`Theme: ${theme}`}
            >
              {theme === 'light' && <Sun className="w-4 h-4" />}
              {theme === 'dark' && <Moon className="w-4 h-4" />}
              {theme === 'auto' && <Monitor className="w-4 h-4" />}
            </button>
            {!onLoginPage && me ? (
              <>
                <span className="text-sm text-gray-600 dark:text-gray-200">{me.username} ({me.role})</span>
                <button
                  onClick={() => { localStorage.removeItem('access_token'); window.location.href = '/login'; }}
                  className="btn-secondary"
                >Logout</button>
              </>
            ) : (
              <Link to="/login" className="nav-link">Login</Link>
            )}
          </div>
        </div>
      </div>
      {!onLoginPage && menuOpen && (
        <div className="md:hidden px-4 pb-3 space-y-2 bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700">
          <Link to="/" className="block nav-link" onClick={()=>setMenuOpen(false)}>Dashboard</Link>
          <Link to="/team" className="block nav-link" onClick={()=>setMenuOpen(false)}>Team</Link>
          {me?.role === 'admin' && <Link to="/schedule/generate" className="block nav-link" onClick={()=>setMenuOpen(false)}>Generate</Link>}
          <Link to="/fairness" className="block nav-link" onClick={()=>setMenuOpen(false)}>Fairness</Link>
          {me?.role === 'admin' && <Link to="/task-types" className="block nav-link" onClick={()=>setMenuOpen(false)}>Task Types</Link>}
          <Link to="/conflicts" className="block nav-link" onClick={()=>setMenuOpen(false)}>Swaps</Link>
        </div>
      )}
    </nav>
  );
}

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 dark:text-gray-100">
        <Navigation />

        {/* Main Content */}
        <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/change-password" element={<RequireAuth><ChangePassword /></RequireAuth>} />
            <Route path="/" element={<RequireAuth><Dashboard /></RequireAuth>} />
            <Route path="/team" element={<RequireAuth><TeamManagement /></RequireAuth>} />
            <Route path="/schedule/generate" element={<RequireAuth><ScheduleGenerator /></RequireAuth>} />
            <Route path="/schedule/:id" element={<RequireAuth><ScheduleView /></RequireAuth>} />
            <Route path="/fairness" element={<RequireAuth><FairnessView /></RequireAuth>} />
            <Route path="/task-types" element={<RequireAuth><TaskTypes /></RequireAuth>} />
            <Route path="/conflicts" element={<RequireAuth><ConflictSwapManager /></RequireAuth>} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;

function RequireAuth({ children }) {
  const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return children;
}
