import React, { useEffect, useState } from 'react';
import { Plus, Edit, Trash2, Calendar as CalendarIcon, Mail } from 'lucide-react';
import {
  getTeamMembers,
  createTeamMember,
  updateTeamMember,
  deleteTeamMember,
  createUnavailablePeriod,
  deleteUnavailablePeriod,
  changeMemberId,
  resendCredentials
} from '../services/api';
import { format } from 'date-fns';
import { useAuth } from '../context/AuthContext';

const WEEKDAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

export default function TeamManagement() {
  const [members, setMembers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [showUnavailableModal, setShowUnavailableModal] = useState(false);
  const [selectedMember, setSelectedMember] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    id: '',
    office_days: [0, 1, 2, 3, 4],
    email: ''
  });
  const [unavailableForm, setUnavailableForm] = useState({
    start_date: '',
    end_date: '',
    reason: ''
  });
  const { me } = useAuth();
  const isAdmin = me?.role === 'admin';
  const selfId = me?.member_id;
  const [resendInfo, setResendInfo] = useState(null);

  useEffect(() => {
    loadMembers();
  }, []);

  useEffect(() => {
    if (!resendInfo) return;
    const timer = setTimeout(() => setResendInfo(null), 6000);
    return () => clearTimeout(timer);
  }, [resendInfo]);

  const loadMembers = async () => {
    try {
      const response = await getTeamMembers();
      setMembers(response.data);
    } catch (error) {
      console.error('Error loading members:', error);
      alert('Failed to load team members');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!isAdmin) return;
    try {
      if (selectedMember) {
        // If ID changed, update ID first, then other fields
        if (selectedMember.id !== formData.id) {
          await changeMemberId(selectedMember.id, formData.id);
        }
        await updateTeamMember(formData.id, formData);
      } else {
        await createTeamMember(formData);
      }
      setShowModal(false);
      setSelectedMember(null);
      setFormData({ name: '', id: '', office_days: [0, 1, 2, 3, 4], email: '' });
      loadMembers();
    } catch (error) {
      console.error('Error saving member:', error);
      alert('Failed to save team member');
    }
  };

  const [confirmDeleteId, setConfirmDeleteId] = useState(null);
  const handleDelete = async (memberId) => {
    setConfirmDeleteId(memberId);
  };

  const handleAddUnavailable = async (e) => {
    e.preventDefault();
    try {
      await createUnavailablePeriod({
        member_id: selectedMember.id,
        ...unavailableForm
      });
      setShowUnavailableModal(false);
      setUnavailableForm({ start_date: '', end_date: '', reason: '' });
      loadMembers();
    } catch (error) {
      console.error('Error adding unavailable period:', error);
      alert('Failed to add unavailable period');
    }
  };

  const handleDeleteUnavailable = async (periodId) => {
    try {
      await deleteUnavailablePeriod(periodId);
      loadMembers();
    } catch (error) {
      console.error('Error deleting period:', error);
      alert('Failed to delete unavailable period');
    }
  };

  const handleResendCredentials = async (member) => {
    try {
      const res = await resendCredentials(member.id);
      const msg = res.data.email_sent && member.email
        ? `Credentials emailed to ${member.email}`
        : `New temporary password for ${member.name}: ${res.data.temp_password}${member.email ? ' (email delivery failed)' : ' (no email on file)'}`;
      setResendInfo(msg);
    } catch (error) {
      alert(error.response?.data?.detail || 'Failed to resend credentials');
    }
  };

  const toggleOfficeDay = (day) => {
    setFormData(prev => ({
      ...prev,
      office_days: prev.office_days.includes(day)
        ? prev.office_days.filter(d => d !== day)
        : [...prev.office_days, day]
    }));
  };

  if (loading) {
    return <div className="text-center py-12">Loading...</div>;
  }

  return (
    <div className="px-4 py-6 animate-fade-in">
      <div className="mb-8 flex justify-between items-center animate-slide-up">
        <div>
          <h2 className="text-3xl font-bold bg-gradient-to-r from-gray-900 to-gray-700 bg-clip-text text-transparent">Team Management</h2>
          <p className="mt-2 text-sm text-gray-600">Manage team members and their availability</p>
          {!isAdmin && <p className="mt-1 text-xs text-gray-500">View-only mode: you can add unavailable dates for yourself but cannot edit other members.</p>}
        </div>
        {isAdmin && (
          <button
            onClick={() => {
              setSelectedMember(null);
              setFormData({ name: '', id: '', office_days: [0, 1, 2, 3, 4], email: '' });
              setShowModal(true);
            }}
            className="btn-primary inline-flex items-center"
          >
            <Plus className="w-4 h-4 mr-2" />
            Add Member
          </button>
        )}
      </div>

      {resendInfo && (
        <div className="mb-4 bg-indigo-50 border border-indigo-200 text-indigo-800 px-4 py-3 rounded-lg text-sm">
          {resendInfo}
        </div>
      )}
      <div className="grid grid-cols-1 gap-4">
        {members.map((member, idx) => {
          const isSelf = member.id === selfId;
          return (
          <div key={member.id} className="card p-6 animate-slide-up hover:scale-[1.02] transition-transform duration-300" style={{ animationDelay: `${idx * 0.1}s` }}>
            <div className="flex justify-between items-start">
              <div className="flex-1">
                <div className="flex items-center mb-3">
                  <div className="w-10 h-10 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-full flex items-center justify-center text-white font-bold text-lg mr-3 shadow-md">
                    {member.name.charAt(0)}
                  </div>
                  <div>
                    <h3 className="text-lg font-bold text-gray-900">{member.name}</h3>
                    <p className="text-xs text-gray-500 mt-0.5">ID: {member.id}</p>
                  {member.email && <p className="text-xs text-gray-500">{member.email}</p>}
                  </div>
                </div>
                <div className="mt-4">
                  <p className="text-sm font-semibold text-gray-700 mb-2">Office Days:</p>
                  <div className="flex flex-wrap gap-2">
                    {member.office_days.map(day => (
                      <span key={day} className="badge bg-blue-100 text-blue-800 border border-blue-200">
                        {WEEKDAYS[day]}
                      </span>
                    ))}
                  </div>
                </div>
                {member.unavailable_periods.length > 0 && (
                  <div className="mt-4">
                    <p className="text-sm font-semibold text-gray-700 mb-2">Unavailable Periods:</p>
                    <div className="space-y-2">
                      {member.unavailable_periods.map(period => (
                        <div key={period.id} className="flex items-center justify-between text-sm bg-red-50 border border-red-200 p-3 rounded-lg">
                          <span className="text-red-800">
                            {format(new Date(period.start_date), 'MMM dd')} - {format(new Date(period.end_date), 'MMM dd, yyyy')}
                            {period.reason && <span className="text-red-600"> ({period.reason})</span>}
                          </span>
                          {(isAdmin || isSelf) && (
                            <button
                              onClick={() => handleDeleteUnavailable(period.id)}
                              className="text-red-600 hover:text-red-800 hover:bg-red-100 p-1 rounded transition-colors"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
              <div className="flex space-x-2 ml-4">
                {isAdmin && (
                  <button
                    onClick={() => {
                      setSelectedMember(member);
                      setFormData({
                        name: member.name,
                        id: member.id,
                        office_days: member.office_days,
                        email: member.email || ''
                      });
                      setShowModal(true);
                    }}
                    className="p-2 text-indigo-600 hover:text-indigo-800 hover:bg-indigo-50 rounded-lg transition-all duration-200"
                    title="Edit"
                  >
                    <Edit className="w-5 h-5" />
                  </button>
                )}
                {(isAdmin || member.id === selfId) && (
                  <button
                    onClick={() => {
                      setSelectedMember(member);
                      setUnavailableForm({ start_date: '', end_date: '', reason: '' });
                      setShowUnavailableModal(true);
                    }}
                    className="p-2 text-blue-600 hover:text-blue-800 hover:bg-blue-50 rounded-lg transition-all duration-200"
                    title="Add Unavailable Period"
                  >
                    <CalendarIcon className="w-5 h-5" />
                  </button>
                )}
                {isAdmin && (
                  <>
                    <button
                      onClick={() => handleResendCredentials(member)}
                      className={`p-2 text-green-600 hover:text-green-800 hover:bg-green-50 rounded-lg transition-all duration-200 ${!member.email ? 'opacity-50 cursor-not-allowed' : ''}`}
                      title="Resend Credentials"
                      disabled={!member.email}
                    >
                      <Mail className="w-5 h-5" />
                    </button>
                    <button
                      onClick={() => handleDelete(member.id)}
                      className="p-2 text-red-600 hover:text-red-800 hover:bg-red-50 rounded-lg transition-all duration-200"
                      title="Delete"
                    >
                      <Trash2 className="w-5 h-5" />
                    </button>
                  </>
                )}
              </div>
            </div>
          </div>
        )})}
      </div>

      {/* Member Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm overflow-y-auto h-full w-full z-50 flex items-center justify-center p-4">
          <div className="relative card w-full max-w-md p-6 animate-slide-up">
            <h3 className="text-xl font-bold mb-6 text-gray-900">{selectedMember ? 'Edit' : 'Add'} Team Member</h3>
            <form onSubmit={handleSubmit} className="space-y-5">
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">Name</label>
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="input-field"
                  placeholder="Enter member name"
                />
              </div>
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">Email (for credentials)</label>
                <input
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  className="input-field"
                  placeholder="name@example.com"
                />
              </div>
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">ID</label>
                <input
                  type="text"
                  required
                  value={formData.id}
                  onChange={(e) => setFormData({ ...formData, id: e.target.value.toLowerCase().replace(/\s+/g, '_') })}
                  className="input-field"
                  placeholder="member_id"
                />
              </div>
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-3">Office Days</label>
                <div className="grid grid-cols-2 gap-3">
                  {WEEKDAYS.map((day, index) => (
                    <label key={index} className="flex items-center p-3 border-2 rounded-lg cursor-pointer hover:bg-indigo-50 hover:border-indigo-300 transition-all duration-200" style={{ borderColor: formData.office_days.includes(index) ? '#6366f1' : '#e5e7eb' }}>
                      <input
                        type="checkbox"
                        checked={formData.office_days.includes(index)}
                        onChange={() => toggleOfficeDay(index)}
                        className="mr-3 w-4 h-4 text-indigo-600 rounded focus:ring-indigo-500"
                      />
                      <span className="text-sm font-medium text-gray-700">{day}</span>
                    </label>
                  ))}
                </div>
              </div>
              <div className="flex justify-end space-x-3 pt-4">
                <button
                  type="button"
                  onClick={() => {
                    setShowModal(false);
                    setSelectedMember(null);
                  }}
                  className="btn-secondary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn-primary"
                >
                  {selectedMember ? 'Update' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Unavailable Period Modal */}
      {showUnavailableModal && selectedMember && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
            <h3 className="text-lg font-bold mb-4">Add Unavailable Period - {selectedMember.name}</h3>
            <form onSubmit={handleAddUnavailable}>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">Start Date</label>
                <input
                  type="date"
                  required
                  value={unavailableForm.start_date}
                  onChange={(e) => setUnavailableForm({ ...unavailableForm, start_date: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                />
              </div>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">End Date</label>
                <input
                  type="date"
                  required
                  value={unavailableForm.end_date}
                  onChange={(e) => setUnavailableForm({ ...unavailableForm, end_date: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                />
              </div>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">Reason (optional)</label>
                <input
                  type="text"
                  value={unavailableForm.reason}
                  onChange={(e) => setUnavailableForm({ ...unavailableForm, reason: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  placeholder="e.g., Vacation, Training"
                />
              </div>
              <div className="flex justify-end space-x-3">
                <button
                  type="button"
                  onClick={() => setShowUnavailableModal(false)}
                  className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
                >
                  Add
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Confirm Delete Modal */}
      {confirmDeleteId && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm overflow-y-auto h-full w-full z-50 flex items-center justify-center p-4">
          <div className="relative card w-full max-w-md p-6">
            <h3 className="text-lg font-bold mb-4">Delete Team Member</h3>
            <p className="text-sm text-gray-700 mb-6">Are you sure you want to delete this member? This action cannot be undone.</p>
            <div className="flex justify-end space-x-3">
              <button className="btn-secondary" onClick={()=>setConfirmDeleteId(null)}>Cancel</button>
              <button className="btn-danger" onClick={async()=>{
                try { await deleteTeamMember(confirmDeleteId); setConfirmDeleteId(null); loadMembers(); } catch(e){ alert('Failed to delete'); }
              }}>Delete</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

