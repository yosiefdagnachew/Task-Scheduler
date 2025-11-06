import axios from 'axios';

const API_BASE_URL = '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Attach token if present
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Team Members
export const getTeamMembers = () => api.get('/team-members');
export const createTeamMember = (member) => api.post('/team-members', member);
export const updateTeamMember = (memberId, member) => api.put(`/team-members/${memberId}`, member);
export const deleteTeamMember = (memberId) => api.delete(`/team-members/${memberId}`);
export const changeMemberId = (memberId, newId) => api.patch(`/team-members/${memberId}/id`, { new_id: newId });

// Unavailable Periods
export const createUnavailablePeriod = (period) => api.post('/unavailable-periods', period);
export const deleteUnavailablePeriod = (periodId) => api.delete(`/unavailable-periods/${periodId}`);

// Schedules
export const generateSchedule = (request) => api.post('/schedules/generate', request);
export const getSchedules = () => api.get('/schedules');
export const getSchedule = (scheduleId) => api.get(`/schedules/${scheduleId}`);
export const exportScheduleCSV = (scheduleId) => api.get(`/schedules/${scheduleId}/export/csv`, { responseType: 'blob' });
export const exportScheduleExcel = (scheduleId) => api.get(`/schedules/${scheduleId}/export/excel`, { responseType: 'blob' });
export const exportSchedulePDF = (scheduleId) => api.get(`/schedules/${scheduleId}/export/pdf`, { responseType: 'blob' });
export const exportScheduleXLSX = (scheduleId) => api.get(`/schedules/${scheduleId}/export/xlsx`, { responseType: 'blob' });
export const deleteSchedule = (scheduleId) => api.delete(`/schedules/${scheduleId}`);

// Fairness
export const getFairnessCounts = () => api.get('/fairness');

// Configuration
export const getConfig = () => api.get('/config');

// Task Types
export const listTaskTypes = () => api.get('/task-types');
export const createTaskType = (payload) => api.post('/task-types', payload);
export const updateTaskType = (id, payload) => api.put(`/task-types/${id}`, payload);
export const deleteTaskType = (id) => api.delete(`/task-types/${id}`);

// Swaps
export const proposeSwap = (payload) => api.post('/swaps', payload);
export const decideSwap = (swapId, approve) => api.post(`/swaps/${swapId}/decision`, null, { params: { approve } });

// Assignments
export const updateAssignment = (assignmentId, memberId) => api.patch(`/assignments/${assignmentId}`, { member_id: memberId });

// Auth
export const authLogin = (username, password) =>
  api.post(
    '/auth/login',
    new URLSearchParams({ username, password }),
    { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }
  );
export const authRegister = (payload) => api.post('/auth/register', payload);
export const getMe = () => api.get('/me');

export default api;

