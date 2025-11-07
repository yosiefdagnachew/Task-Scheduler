import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Calendar, Loader } from 'lucide-react';
import { generateSchedule, listTaskTypes } from '../services/api';
import { format } from 'date-fns';
import { useAuth } from '../context/AuthContext';

export default function ScheduleGenerator() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    start_date: '',
    end_date: '',
    tasks: [],
    seed: '',
    fairness_aggressiveness: 1
  });
  const [taskTypes, setTaskTypes] = useState([]);
  const [error, setError] = useState(null);
  const { me } = useAuth();
  const isAdmin = me?.role === 'admin';

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const payload = {
        start_date: formData.start_date,
        end_date: formData.end_date,
        tasks: formData.tasks,
        fairness_aggressiveness: formData.fairness_aggressiveness,
        seed: formData.seed ? Number(formData.seed) : undefined
      };
      const response = await generateSchedule(payload);
      
      // Navigate to the schedule view
      navigate(`/schedule/${response.data.schedule_id}`);
    } catch (err) {
      console.error('Error generating schedule:', err);
      setError(err.response?.data?.detail || 'Failed to generate schedule');
    } finally {
      setLoading(false);
    }
  };

  // Set default dates (next Monday to Sunday)
  React.useEffect(() => {
    listTaskTypes().then(res => setTaskTypes(res.data)).catch(() => setTaskTypes([]));
    const today = new Date();
    const daysUntilMonday = (8 - today.getDay()) % 7 || 7;
    const nextMonday = new Date(today);
    nextMonday.setDate(today.getDate() + daysUntilMonday);
    const nextSunday = new Date(nextMonday);
    nextSunday.setDate(nextMonday.getDate() + 6);

    setFormData(prev => ({
      ...prev,
      start_date: format(nextMonday, 'yyyy-MM-dd'),
      end_date: format(nextSunday, 'yyyy-MM-dd')
    }));
  }, []);

  if (!isAdmin) {
    return (
      <div className="px-4 py-6">
        <div className="max-w-2xl mx-auto card p-6">
          <h2 className="text-2xl font-bold mb-4">Access Restricted</h2>
          <p className="text-sm text-gray-600">Only administrators can generate schedules. Please contact your administrator for assistance.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="px-4 py-6 animate-fade-in">
      <div className="max-w-2xl mx-auto">
        <div className="mb-8 animate-slide-up">
          <h2 className="text-3xl font-bold bg-gradient-to-r from-gray-900 to-gray-700 bg-clip-text text-transparent">Generate Schedule</h2>
          <p className="mt-2 text-sm text-gray-600">Create a new schedule for the specified date range</p>
        </div>

        <div className="card p-6 animate-slide-up">
          <form onSubmit={handleSubmit}>
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 mb-6">
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Start Date
                </label>
                <input
                  type="date"
                  required
                  value={formData.start_date}
                  onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
                  className="input-field"
                />
              </div>
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  End Date
                </label>
                <input
                  type="date"
                  required
                  value={formData.end_date}
                  onChange={(e) => setFormData({ ...formData, end_date: e.target.value })}
                  className="input-field"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Tasks
                </label>
                <div className="space-y-2">
                  {taskTypes.length === 0 ? (
                    <div className="text-sm text-gray-500">No custom task types. Default ATM/SysAid will be used.</div>
                  ) : (
                    taskTypes.map(t => (
                      <label key={t.id} className="flex items-center">
                        <input
                          type="checkbox"
                          checked={formData.tasks.includes(t.name)}
                          onChange={(e) => {
                            const checked = e.target.checked;
                            setFormData(prev => ({
                              ...prev,
                              tasks: checked ? [...prev.tasks, t.name] : prev.tasks.filter(n => n !== t.name)
                            }));
                          }}
                          className="mr-2"
                        />
                        <span className="text-sm">{t.name} <span className="text-gray-400">({t.recurrence})</span></span>
                      </label>
                    ))
                  )}
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 mb-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Random Seed (optional)</label>
                <input
                  type="number"
                  value={formData.seed}
                  onChange={(e) => setFormData({ ...formData, seed: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  placeholder="e.g., 12345"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Fairness Aggressiveness</label>
                <input
                  type="range"
                  min="1"
                  max="5"
                  value={formData.fairness_aggressiveness}
                  onChange={(e) => setFormData({ ...formData, fairness_aggressiveness: Number(e.target.value) })}
                  className="w-full"
                />
                <div className="text-sm text-gray-500">{formData.fairness_aggressiveness} / 5</div>
              </div>
            </div>

            {error && (
              <div className="mb-4 bg-red-50 border-2 border-red-200 text-red-700 px-4 py-3 rounded-lg animate-fade-in">
                <div className="flex items-center">
                  <span className="text-red-600 mr-2">⚠️</span>
                  {error}
                </div>
              </div>
            )}

            <div className="flex justify-end space-x-3 pt-4">
              <button
                type="button"
                onClick={() => navigate('/')}
                className="btn-secondary"
                disabled={loading}
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading}
                className="btn-primary inline-flex items-center disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
              >
                {loading ? (
                  <>
                    <Loader className="w-4 h-4 mr-2 animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>
                    <Calendar className="w-4 h-4 mr-2" />
                    Generate Schedule
                  </>
                )}
              </button>
            </div>
          </form>
        </div>

        <div className="mt-6 bg-gradient-to-br from-blue-50 to-indigo-50 border-2 border-blue-200 rounded-xl p-6 shadow-md">
          <h3 className="text-base font-bold text-blue-900 mb-3 flex items-center">
            <span className="mr-2">📋</span>
            Scheduling Rules
          </h3>
          <ul className="text-sm text-blue-800 space-y-2">
            <li className="flex items-start">
              <span className="mr-2">•</span>
              <span>ATM monitoring: Mon-Fri two shifts (Morning & Mid/Night), Saturday four shifts, Sunday three shifts</span>
            </li>
            <li className="flex items-start">
              <span className="mr-2">•</span>
              <span>B-shift assignees get the next day off (rest rule)</span>
            </li>
            <li className="flex items-start">
              <span className="mr-2">•</span>
              <span>SysAid: Weekly Maker/Checker pair (Mon-Sat) with no overlap with ATM rest days</span>
            </li>
            <li className="flex items-start">
              <span className="mr-2">•</span>
              <span>Fairness: Equal distribution over rolling 90-day window</span>
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
}

