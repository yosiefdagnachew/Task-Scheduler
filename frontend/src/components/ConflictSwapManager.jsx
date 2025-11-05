import React, { useEffect, useState } from 'react';
import { getSchedule, getTeamMembers, proposeSwap, decideSwap } from '../services/api';

export default function ConflictSwapManager() {
  const [scheduleId, setScheduleId] = useState('');
  const [schedule, setSchedule] = useState(null);
  const [team, setTeam] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => { getTeamMembers().then(res => setTeam(res.data)); }, []);

  const loadSchedule = async () => {
    if (!scheduleId) return;
    setLoading(true);
    try {
      const res = await getSchedule(scheduleId);
      setSchedule(res.data);
    } finally { setLoading(false); }
  };

  const submitSwap = async (assignmentId, requestedBy, proposedMemberId, reason) => {
    await proposeSwap({ assignment_id: assignmentId, requested_by: requestedBy, proposed_member_id: proposedMemberId, reason });
    alert('Swap proposed');
  };

  const approveSwap = async (swapId, approve) => {
    await decideSwap(swapId, approve);
    alert(approve ? 'Swap approved' : 'Swap rejected');
  };

  return (
    <div className="px-4 py-6 max-w-5xl mx-auto">
      <h2 className="text-2xl font-bold text-gray-900 mb-2">Conflict & Swap Manager</h2>
      <p className="text-sm text-gray-600 mb-4">Suggest a replacement for an assignment you cannot cover. Your request will be reviewed by an admin.</p>
      <div className="bg-white rounded shadow p-4 mb-4">
        <div className="flex space-x-3 items-end">
          <div>
            <label className="block text-sm font-medium mb-1">Schedule ID</label>
            <input className="border px-3 py-2 rounded" value={scheduleId} onChange={e => setScheduleId(e.target.value)} placeholder="e.g., 1" />
          </div>
          <button onClick={loadSchedule} className="px-4 py-2 bg-indigo-600 text-white rounded">Load</button>
        </div>
      </div>
      {loading && <div>Loading...</div>}
      {schedule && (
        <div className="bg-white rounded shadow p-4">
          <h3 className="font-medium mb-3">Assignments</h3>
          <div className="space-y-3">
            {schedule.assignments.map(a => (
              <div key={a.id} className="border rounded p-3 flex items-center justify-between">
                <div>
                  <div className="font-medium">{a.task_type} - {a.assignment_date}</div>
                  <div className="text-sm text-gray-600">Assigned: {a.member_name} ({a.member_id})</div>
                </div>
                <div className="flex items-center space-x-2">
                  <select id={`proposed_${a.id}`} className="border px-2 py-1 rounded">
                    <option value="">Select replacement</option>
                    {team.map(m => (
                      <option key={m.id} value={m.id}>{m.name}</option>
                    ))}
                  </select>
                  <input id={`reason_${a.id}`} className="border px-2 py-1 rounded" placeholder="Reason (optional)" />
                  <button
                    onClick={() => submitSwap(a.id, a.member_id, document.getElementById(`proposed_${a.id}`).value, document.getElementById(`reason_${a.id}`).value)}
                    className="px-3 py-1 bg-yellow-500 text-white rounded"
                  >Submit Request</button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}


