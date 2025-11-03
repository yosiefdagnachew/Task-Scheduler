import React, { useEffect, useState } from 'react';
import { Plus, Edit, Trash2, Calendar as CalendarIcon } from 'lucide-react';
import {
  getTeamMembers,
  createTeamMember,
  updateTeamMember,
  deleteTeamMember,
  createUnavailablePeriod,
  deleteUnavailablePeriod
} from '../services/api';
import { format } from 'date-fns';

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
    office_days: [0, 1, 2, 3, 4]
  });
  const [unavailableForm, setUnavailableForm] = useState({
    start_date: '',
    end_date: '',
    reason: ''
  });

  useEffect(() => {
    loadMembers();
  }, []);

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
    try {
      if (selectedMember) {
        await updateTeamMember(selectedMember.id, formData);
      } else {
        await createTeamMember(formData);
      }
      setShowModal(false);
      setSelectedMember(null);
      setFormData({ name: '', id: '', office_days: [0, 1, 2, 3, 4] });
      loadMembers();
    } catch (error) {
      console.error('Error saving member:', error);
      alert('Failed to save team member');
    }
  };

  const handleDelete = async (memberId) => {
    if (!confirm('Are you sure you want to delete this team member?')) return;
    try {
      await deleteTeamMember(memberId);
      loadMembers();
    } catch (error) {
      console.error('Error deleting member:', error);
      alert('Failed to delete team member');
    }
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
    <div className="px-4 py-6">
      <div className="mb-6 flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Team Management</h2>
          <p className="mt-1 text-sm text-gray-500">Manage team members and their availability</p>
        </div>
        <button
          onClick={() => {
            setSelectedMember(null);
            setFormData({ name: '', id: '', office_days: [0, 1, 2, 3, 4] });
            setShowModal(true);
          }}
          className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700"
        >
          <Plus className="w-4 h-4 mr-2" />
          Add Member
        </button>
      </div>

      <div className="grid grid-cols-1 gap-4">
        {members.map((member) => (
          <div key={member.id} className="bg-white shadow rounded-lg p-6">
            <div className="flex justify-between items-start">
              <div className="flex-1">
                <h3 className="text-lg font-medium text-gray-900">{member.name}</h3>
                <p className="text-sm text-gray-500 mt-1">ID: {member.id}</p>
                <div className="mt-3">
                  <p className="text-sm font-medium text-gray-700">Office Days:</p>
                  <div className="flex flex-wrap gap-2 mt-1">
                    {member.office_days.map(day => (
                      <span key={day} className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded">
                        {WEEKDAYS[day]}
                      </span>
                    ))}
                  </div>
                </div>
                {member.unavailable_periods.length > 0 && (
                  <div className="mt-3">
                    <p className="text-sm font-medium text-gray-700">Unavailable Periods:</p>
                    <div className="mt-1 space-y-1">
                      {member.unavailable_periods.map(period => (
                        <div key={period.id} className="flex items-center justify-between text-sm bg-red-50 p-2 rounded">
                          <span>
                            {format(new Date(period.start_date), 'MMM dd')} - {format(new Date(period.end_date), 'MMM dd, yyyy')}
                            {period.reason && ` (${period.reason})`}
                          </span>
                          <button
                            onClick={() => handleDeleteUnavailable(period.id)}
                            className="text-red-600 hover:text-red-800"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
              <div className="flex space-x-2 ml-4">
                <button
                  onClick={() => {
                    setSelectedMember(member);
                    setFormData({
                      name: member.name,
                      id: member.id,
                      office_days: member.office_days
                    });
                    setShowModal(true);
                  }}
                  className="p-2 text-gray-600 hover:text-gray-900"
                >
                  <Edit className="w-5 h-5" />
                </button>
                <button
                  onClick={() => {
                    setSelectedMember(member);
                    setUnavailableForm({ start_date: '', end_date: '', reason: '' });
                    setShowUnavailableModal(true);
                  }}
                  className="p-2 text-gray-600 hover:text-gray-900"
                >
                  <CalendarIcon className="w-5 h-5" />
                </button>
                <button
                  onClick={() => handleDelete(member.id)}
                  className="p-2 text-red-600 hover:text-red-800"
                >
                  <Trash2 className="w-5 h-5" />
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Member Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
            <h3 className="text-lg font-bold mb-4">{selectedMember ? 'Edit' : 'Add'} Team Member</h3>
            <form onSubmit={handleSubmit}>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                />
              </div>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">ID</label>
                <input
                  type="text"
                  required
                  disabled={!!selectedMember}
                  value={formData.id}
                  onChange={(e) => setFormData({ ...formData, id: e.target.value.toLowerCase().replace(/\s+/g, '_') })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md disabled:bg-gray-100"
                />
              </div>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">Office Days</label>
                <div className="grid grid-cols-2 gap-2">
                  {WEEKDAYS.map((day, index) => (
                    <label key={index} className="flex items-center">
                      <input
                        type="checkbox"
                        checked={formData.office_days.includes(index)}
                        onChange={() => toggleOfficeDay(index)}
                        className="mr-2"
                      />
                      <span className="text-sm">{day}</span>
                    </label>
                  ))}
                </div>
              </div>
              <div className="flex justify-end space-x-3">
                <button
                  type="button"
                  onClick={() => {
                    setShowModal(false);
                    setSelectedMember(null);
                  }}
                  className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
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
    </div>
  );
}

