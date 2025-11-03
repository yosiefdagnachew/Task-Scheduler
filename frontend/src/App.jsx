import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import { Calendar, Users, BarChart3 } from 'lucide-react';
import Dashboard from './components/Dashboard';
import TeamManagement from './components/TeamManagement';
import ScheduleGenerator from './components/ScheduleGenerator';
import ScheduleView from './components/ScheduleView';
import FairnessView from './components/FairnessView';

function Navigation() {
  const location = useLocation();
  
  const isActive = (path) => {
    return location.pathname === path || location.pathname.startsWith(path + '/');
  };

  return (
    <nav className="bg-white shadow-sm border-b">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex">
            <div className="flex-shrink-0 flex items-center">
              <Link to="/" className="text-xl font-bold text-gray-900">Task Scheduler</Link>
            </div>
            <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
              <Link
                to="/"
                className={`inline-flex items-center px-1 pt-1 text-sm font-medium ${
                  isActive('/') && location.pathname === '/'
                    ? 'text-gray-900 border-b-2 border-indigo-500'
                    : 'text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <Calendar className="w-4 h-4 mr-2" />
                Dashboard
              </Link>
              <Link
                to="/team"
                className={`inline-flex items-center px-1 pt-1 text-sm font-medium ${
                  isActive('/team')
                    ? 'text-gray-900 border-b-2 border-indigo-500'
                    : 'text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <Users className="w-4 h-4 mr-2" />
                Team
              </Link>
              <Link
                to="/schedule/generate"
                className={`inline-flex items-center px-1 pt-1 text-sm font-medium ${
                  isActive('/schedule')
                    ? 'text-gray-900 border-b-2 border-indigo-500'
                    : 'text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <Calendar className="w-4 h-4 mr-2" />
                Generate
              </Link>
              <Link
                to="/fairness"
                className={`inline-flex items-center px-1 pt-1 text-sm font-medium ${
                  isActive('/fairness')
                    ? 'text-gray-900 border-b-2 border-indigo-500'
                    : 'text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <BarChart3 className="w-4 h-4 mr-2" />
                Fairness
              </Link>
            </div>
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
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;

