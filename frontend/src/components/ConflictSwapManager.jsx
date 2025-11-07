import React, { useEffect, useState } from 'react';
import { getSchedule, getTeamMembers, proposeSwap, decideSwap, listSwaps, respondSwap } from '../services/api';
import { useAuth } from '../context/AuthContext';

export default function ConflictSwapManager() {
  const [scheduleId, setScheduleId] = useState('');
  const [schedule, setSchedule] = useState(null);
  const [team, setTeam] = useState([]);
  const [loading, setLoading] = useState(false);
  const [swapLoading, setSwapLoading] = useState(false);
  const [swaps, setSwaps] = useState({ outgoing: [], incoming: [], admin_pending: [] });
  const { me } = useAuth();
  const isAdmin = me?.role === 'admin';
  const selfId = me?.member_id;

  useEffect(() => { getTeamMembers().then(res => setTeam(res.data)); }, []);

  const refreshSwaps = async () => {
    setSwapLoading(true);
    try {
      const res = await listSwaps();
      setSwaps(res.data);
    } catch (e) {
      console.error('Failed to load swaps', e);
    } finally {
      setSwapLoading(false);
    }
  };

  useEffect(() => { refreshSwaps(); }, []);

  const loadSchedule = async () => {
    if (!scheduleId) return;
    setLoading(true);
    try {
      const res = await getSchedule(scheduleId);
      setSchedule(res.data);
    } finally { setLoading(false); }
  };

  const submitSwap = async (assignmentId, proposedMemberId, reason) => {
    await proposeSwap({ assignment_id: assignmentId, proposed_member_id: proposedMemberId, reason });
    await refreshSwaps();
    alert('Swap proposed');
  };

  const approveSwap = async (swapId, approve) => {
    await decideSwap(swapId, approve);
    await refreshSwaps();
    if (scheduleId) {
      await loadSchedule();
    }
    alert(approve ? 'Swap approved' : 'Swap rejected');
  };

  const respondToSwap = async (swapId, accept) => {
    await respondSwap(swapId, accept);
    await refreshSwaps();
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
                  <div className="font-medium">{a.task_type}{a.shift_label ? ` (${a.shift_label})` : ''} - {a.assignment_date}</div>
                  <div className="text-sm text-gray-600">Assigned: {a.member_name} ({a.member_id})</div>
                </div>
                {selfId && a.member_id === selfId ? (
                  <div className="flex items-center space-x-2">
                    <select id={`proposed_${a.id}`} className="border px-2 py-1 rounded">
                      <option value="">Select replacement</option>
                      {team.filter(m => m.id !== selfId).map(m => (
                        <option key={m.id} value={m.id}>{m.name}</option>
                      ))}
                    </select>
                    <input id={`reason_${a.id}`} className="border px-2 py-1 rounded" placeholder="Reason (optional)" />
                    <button
                      onClick={() => {
                        const proposed = document.getElementById(`proposed_${a.id}`).value;
                        if (!proposed) { alert('Select a replacement'); return; }
                        const reason = document.getElementById(`reason_${a.id}`).value;
                        submitSwap(a.id, proposed, reason);
                      }}
                      className="px-3 py-1 bg-yellow-500 text-white rounded"
                    >Submit Request</button>
                  </div>
                ) : (
                  <div className="text-sm text-gray-500">Swap proposals available only for your own assignments.</div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
      <div className="mt-6 grid md:grid-cols-2 gap-6">
        <div className="bg-white rounded shadow p-4">
          <h3 className="font-medium mb-3">My Swap Requests</h3>
          {swaps.outgoing.length === 0 ? (
            <div className="text-sm text-gray-500">No swap requests submitted.</div>
          ) : (
            <div className="space-y-2">
              {swaps.outgoing.map(swap => (
                <div key={swap.id} className="border rounded p-3 text-sm">
                  <div className="font-semibold">{swap.task_type} - {swap.assignment_date}</div>
                  <div>To: {swap.proposed_member_name || swap.proposed_member_id}</div>
                  <div>Status: <span className="font-medium">{swap.status}</span></div>
                  {swap.peer_decision && <div>Peer decision: {swap.peer_decision}</div>}
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="bg-white rounded shadow p-4">
          <h3 className="font-medium mb-3">Requests Needing My Decision</h3>
          {swapLoading && <div className="text-sm text-gray-500">Loading...</div>}
          {(!swaps.incoming || swaps.incoming.length === 0) ? (
            <div className="text-sm text-gray-500">No pending requests.</div>
          ) : (
            <div className="space-y-2">
              {swaps.incoming.map(swap => (
                <div key={swap.id} className="border rounded p-3 text-sm space-y-2">
                  <div className="font-semibold">{swap.task_type} - {swap.assignment_date}</div>
                  <div>Requested by: {swap.requested_by_name || swap.requested_by}</div>
                  <div className="flex space-x-2">
                    <button className="px-3 py-1 bg-green-500 text-white rounded" onClick={() => respondToSwap(swap.id, true)}>Accept</button>
                    <button className="px-3 py-1 bg-red-500 text-white rounded" onClick={() => respondToSwap(swap.id, false)}>Reject</button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {isAdmin && (
        <div className="mt-6 bg-white rounded shadow p-4">
          <h3 className="font-medium mb-3">Pending Admin Approval</h3>
          {swaps.admin_pending.length === 0 ? (
            <div className="text-sm text-gray-500">No swaps awaiting approval.</div>
          ) : (
            <div className="space-y-2">
              {swaps.admin_pending.map(swap => (
                <div key={swap.id} className="border rounded p-3 text-sm space-y-2">
                  <div className="font-semibold">{swap.task_type} - {swap.assignment_date}</div>
                  <div>Requested by: {swap.requested_by_name || swap.requested_by}</div>
                  <div>Proposed: {swap.proposed_member_name || swap.proposed_member_id}</div>
                  <div className="flex space-x-2">
                    <button className="px-3 py-1 bg-green-500 text-white rounded" onClick={() => approveSwap(swap.id, true)}>Approve</button>
                    <button className="px-3 py-1 bg-red-500 text-white rounded" onClick={() => approveSwap(swap.id, false)}>Reject</button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}


