import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Calendar, Users, Plus, Eye, Trash } from 'lucide-react';
import { getSchedules, getTeamMembers, deleteSchedule } from '../services/api';
import { format } from 'date-fns';
import { useAuth } from '../context/AuthContext';

export default function Dashboard() {
  const [schedules, setSchedules] = useState([]);
  const [teamCount, setTeamCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [confirmDeleteId, setConfirmDeleteId] = useState(null);
  const { me } = useAuth();
  const isAdmin = me?.role === 'admin';

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [schedulesRes, teamRes] = await Promise.all([
        getSchedules(),
        getTeamMembers()
      ]);
      setSchedules(schedulesRes.data);
      setTeamCount(teamRes.data.length);
    } catch (error) {
      console.error('Error loading data:', error);
      console.error('Error details:', {
        message: error.message,
        response: error.response?.data,
        status: error.response?.status,
        url: error.config?.url
      });
      // Show user-friendly error
      if (error.response?.status === 401) {
        // Authentication error - will be handled by interceptor
      } else if (error.code === 'ECONNREFUSED' || error.message?.includes('Network Error')) {
        alert('Cannot connect to backend server. Please ensure the backend is running on http://localhost:8000');
      } else {
        alert(`Failed to load data: ${error.response?.data?.detail || error.message}`);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (scheduleId) => {
    if (!isAdmin) return;
    setConfirmDeleteId(scheduleId);
  };

  if (loading) {
    return <div className="text-center py-12">Loading...</div>;
  }

  return (
    <div className="px-4 py-6 animate-fade-in">
      <div className="mb-8 animate-slide-up">
        <h2 className="text-3xl font-bold bg-gradient-to-r from-gray-900 to-gray-700 bg-clip-text text-transparent">Dashboard</h2>
        <p className="mt-2 text-sm text-gray-600">Manage your task scheduling system</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-3 mb-8">
        <div className="card overflow-hidden group hover:scale-105 transition-transform duration-300">
          <div className="p-6 bg-gradient-to-br from-blue-50 to-indigo-50">
            <div className="flex items-center justify-between">
              <div className="flex-shrink-0">
                <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg flex items-center justify-center shadow-md">
                  <Calendar className="h-6 w-6 text-white" />
                </div>
              </div>
              <div className="ml-4 flex-1">
                <dt className="text-sm font-medium text-gray-600 truncate">Schedules</dt>
                <dd className="text-3xl font-bold text-gray-900 mt-1">{schedules.length}</dd>
              </div>
            </div>
          </div>
        </div>

        <div className="card overflow-hidden group hover:scale-105 transition-transform duration-300">
          <div className="p-6 bg-gradient-to-br from-purple-50 to-pink-50">
            <div className="flex items-center justify-between">
              <div className="flex-shrink-0">
                <div className="w-12 h-12 bg-gradient-to-br from-purple-500 to-pink-600 rounded-lg flex items-center justify-center shadow-md">
                  <Users className="h-6 w-6 text-white" />
                </div>
              </div>
              <div className="ml-4 flex-1">
                <dt className="text-sm font-medium text-gray-600 truncate">Team Members</dt>
                <dd className="text-3xl font-bold text-gray-900 mt-1">{teamCount}</dd>
              </div>
            </div>
          </div>
        </div>

        {isAdmin && (
          <div className="card overflow-hidden group hover:scale-105 transition-transform duration-300">
            <div className="p-6 bg-gradient-to-br from-green-50 to-emerald-50">
              <Link
                to="/schedule/generate"
                className="flex flex-col items-center justify-center h-full min-h-[80px] btn-primary"
              >
                <Plus className="w-5 h-5 mb-2" />
                <span className="font-semibold">Generate Schedule</span>
              </Link>
            </div>
          </div>
        )}
      </div>

      {/* Recent Schedules */}
      <div className="card animate-slide-up">
        <div className="px-6 py-6">
          <h3 className="text-xl font-bold text-gray-900 mb-6 flex items-center">
            <Calendar className="w-5 h-5 mr-2 text-indigo-600" />
            Recent Schedules
          </h3>
          {schedules.length === 0 ? (
            <div className="text-center py-12">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-gray-100 mb-4">
                <Calendar className="w-8 h-8 text-gray-400" />
              </div>
              <p className="text-gray-500 text-lg">No schedules yet.</p>
              <p className="text-gray-400 text-sm mt-2">Generate your first schedule to get started.</p>
            </div>
          ) : (
            <div className="overflow-hidden">
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gradient-to-r from-gray-50 to-gray-100">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                        Schedule ID
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                        Period
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                        Status
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                        Created
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-semibold text-gray-700 uppercase tracking-wider">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-100">
                    {schedules.map((schedule, idx) => (
                      <tr key={schedule.id} className="hover:bg-indigo-50/50 transition-colors duration-150">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm font-bold text-indigo-600">
                            #{schedule.id}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm font-medium text-gray-900">
                            {format(new Date(schedule.start_date), 'MMM dd')} - {format(new Date(schedule.end_date), 'MMM dd, yyyy')}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`badge ${
                            schedule.status === 'published' 
                              ? 'bg-green-100 text-green-800 border border-green-200' 
                              : 'bg-yellow-100 text-yellow-800 border border-yellow-200'
                          }`}>
                            {schedule.status}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                          {format(new Date(schedule.created_at), 'MMM dd, yyyy')}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium space-x-2">
                          {isAdmin && (
                            <button
                              onClick={() => handleDelete(schedule.id)}
                              className="inline-flex items-center px-3 py-1.5 text-red-600 hover:text-red-800 hover:bg-red-50 rounded-lg transition-all duration-200"
                            >
                              <Trash className="w-4 h-4 mr-1" />
                              Delete
                            </button>
                          )}
                          <Link
                            to={`/schedule/${schedule.id}`}
                            className="inline-flex items-center px-3 py-1.5 text-indigo-600 hover:text-indigo-800 hover:bg-indigo-50 rounded-lg transition-all duration-200"
                          >
                            <Eye className="w-4 h-4 mr-1" />
                            View
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </div>
      {/* Confirm Delete Modal */}
      {confirmDeleteId && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm overflow-y-auto h-full w-full z-50 flex items-center justify-center p-4">
          <div className="relative card w-full max-w-md p-6">
            <h3 className="text-lg font-bold mb-4">Delete Schedule</h3>
            <p className="text-sm text-gray-700 mb-6">Are you sure you want to delete schedule #{confirmDeleteId}? This action cannot be undone.</p>
            <div className="flex justify-end space-x-3">
              <button className="btn-secondary" onClick={() => setConfirmDeleteId(null)}>Cancel</button>
              <button className="btn-danger" onClick={async () => {
                try {
                  await deleteSchedule(confirmDeleteId);
                  setConfirmDeleteId(null);
                  await loadData();
                } catch (e) {
                  console.error('Failed to delete schedule', e);
                  alert(e.response?.data?.detail || 'Failed to delete schedule');
                }
              }}>Delete</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

