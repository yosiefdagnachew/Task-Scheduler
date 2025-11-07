import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Download, ArrowLeft, Trash2 } from 'lucide-react';
import { getSchedule, exportScheduleCSV, exportScheduleExcel, exportSchedulePDF, exportScheduleXLSX, updateAssignment, getTeamMembers, deleteSchedule } from '../services/api';
import { format, eachDayOfInterval, parseISO } from 'date-fns';
import { useAuth } from '../context/AuthContext';

const TASK_COLORS = {
  ATM_MORNING: 'bg-blue-100 text-blue-800',
  ATM_MIDNIGHT: 'bg-purple-100 text-purple-800',
  SYSAID_MAKER: 'bg-green-100 text-green-800',
  SYSAID_CHECKER: 'bg-yellow-100 text-yellow-800'
};

const TASK_LABELS = {
  ATM_MORNING: 'ATM Morning',
  ATM_MIDNIGHT: 'ATM Mid/Night',
  SYSAID_MAKER: 'SysAid Maker',
  SYSAID_CHECKER: 'SysAid Checker'
};

export default function ScheduleView() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [schedule, setSchedule] = useState(null);
  const [loading, setLoading] = useState(true);
  const [groupedAssignments, setGroupedAssignments] = useState({});
  const [team, setTeam] = useState([]);
  const { me } = useAuth();
  const isAdmin = me?.role === 'admin';

  useEffect(() => {
    loadSchedule();
    getTeamMembers().then(res => setTeam(res.data));
  }, [id]);

  const loadSchedule = async () => {
    try {
      const response = await getSchedule(id);
      setSchedule(response.data);
      
      // Group assignments by date
      const grouped = {};
      response.data.assignments.forEach(assignment => {
        const date = assignment.assignment_date;
        if (!grouped[date]) {
          grouped[date] = [];
        }
        grouped[date].push(assignment);
      });
      setGroupedAssignments(grouped);
    } catch (error) {
      console.error('Error loading schedule:', error);
      alert('Failed to load schedule');
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async () => {
    try {
      const response = await exportScheduleCSV(id);
      const blob = new Blob([response.data], { type: 'text/csv' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `schedule_${id}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Error exporting schedule:', error);
      alert('Failed to export schedule');
    }
  };

  const handleExportExcel = async () => {
    try {
      await exportScheduleExcel(id);
      alert('Excel export not implemented in API');
    } catch (e) { alert(e.response?.data?.detail || 'Failed'); }
  };
  const handleExportPDF = async () => {
    try {
      await exportSchedulePDF(id);
      alert('PDF export not implemented in API');
    } catch (e) { alert(e.response?.data?.detail || 'Failed'); }
  };

  const reassign = async (assignmentId, memberId) => {
    if (!memberId) return;
    try {
      await updateAssignment(assignmentId, memberId);
      await loadSchedule();
    } catch (e) {
      alert('Failed to update assignment');
    }
  };

  if (loading) {
    return <div className="text-center py-12">Loading schedule...</div>;
  }

  if (!schedule) {
    return <div className="text-center py-12">Schedule not found</div>;
  }

  const dates = eachDayOfInterval({
    start: parseISO(schedule.start_date),
    end: parseISO(schedule.end_date)
  });

  const renderAssignmentChips = (items, colorClass) => {
    if (!items || items.length === 0) {
      return <span className="text-gray-400">-</span>;
    }
    return (
      <div className="space-y-1">
        {items.map(item => (
          <div key={item.id} className="flex items-center space-x-2">
            <span className={`px-2 py-1 text-xs font-medium rounded ${colorClass}`}>
              {item.member_name}
              {item.shift_label ? <span className="block text-[10px] text-gray-600">{item.shift_label}</span> : null}
            </span>
            {isAdmin && (
              <select className="text-xs border px-1 py-0.5 rounded" value="" onChange={(e)=>{ if (e.target.value) { reassign(item.id, e.target.value); e.target.value=''; } }}>
                <option value="">Change</option>
                {team.map(m => (<option key={m.id} value={m.id}>{m.name}</option>))}
              </select>
            )}
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="px-4 py-6">
      <div className="mb-6 flex justify-between items-center">
        <div>
          <button
            onClick={() => navigate('/')}
            className="inline-flex items-center text-sm text-gray-500 hover:text-gray-700 mb-2"
          >
            <ArrowLeft className="w-4 h-4 mr-1" />
            Back to Dashboard
          </button>
          <h2 className="text-2xl font-bold text-gray-900">Schedule View</h2>
          <p className="mt-1 text-sm text-gray-500">
            {format(parseISO(schedule.start_date), 'MMM dd')} - {format(parseISO(schedule.end_date), 'MMM dd, yyyy')}
          </p>
        </div>
        <div className="space-x-2">
          {isAdmin && (
            <button
              onClick={async ()=>{
                if (!window.confirm('Delete this schedule? This cannot be undone.')) return;
                try { await deleteSchedule(id); navigate('/'); } catch(e){ alert('Failed to delete'); }
              }}
              className="inline-flex items-center px-4 py-2 border border-red-300 rounded-md text-red-700 hover:bg-red-50"
            >
              <Trash2 className="w-4 h-4 mr-2" />
              Delete
            </button>
          )}
          <button
            onClick={handleExport}
            className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
          >
            <Download className="w-4 h-4 mr-2" />
            CSV
          </button>
          <button onClick={handleExportExcel} className="px-3 py-2 border border-gray-300 rounded-md">Excel</button>
          <button
            onClick={async ()=>{
              try {
                const res = await exportScheduleXLSX(id);
                const blob = new Blob([res.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url; a.download = `schedule_${id}.xlsx`;
                document.body.appendChild(a); a.click();
                window.URL.revokeObjectURL(url); document.body.removeChild(a);
              } catch (e) { alert('Failed to export XLSX'); }
            }}
            className="px-3 py-2 border border-gray-300 rounded-md"
          >XLSX</button>
          <button onClick={handleExportPDF} className="px-3 py-2 border border-gray-300 rounded-md">PDF</button>
        </div>
      </div>

      <div className="bg-white shadow rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Date
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  ATM Morning
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  ATM Mid/Night
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  SysAid Maker
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  SysAid Checker
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {dates.map((date) => {
                const dateStr = format(date, 'yyyy-MM-dd');
                const assignments = groupedAssignments[dateStr] || [];
                
                const atmMorning = assignments.filter(a => a.task_type === 'ATM_MORNING');
                const atmMidnight = assignments.filter(a => a.task_type === 'ATM_MIDNIGHT');
                const sysaidMaker = assignments.filter(a => a.task_type === 'SYSAID_MAKER');
                const sysaidChecker = assignments.filter(a => a.task_type === 'SYSAID_CHECKER');

                return (
                  <tr key={dateStr}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      <div>{format(date, 'EEE, MMM dd')}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {renderAssignmentChips(atmMorning, TASK_COLORS.ATM_MORNING)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {renderAssignmentChips(atmMidnight, TASK_COLORS.ATM_MIDNIGHT)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {renderAssignmentChips(sysaidMaker, TASK_COLORS.SYSAID_MAKER)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {renderAssignmentChips(sysaidChecker, TASK_COLORS.SYSAID_CHECKER)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Assignment Summary & Fairness */}
      <div className="mt-6 bg-white shadow rounded-lg p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Assignment Summary</h3>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Object.entries(TASK_LABELS).map(([key, label]) => {
            const taskAssignments = schedule.assignments.filter(a => a.task_type === key);
            const uniqueMembers = new Set(taskAssignments.map(a => a.member_name));
            return (
              <div key={key} className="border rounded-lg p-4">
                <div className={`inline-block px-2 py-1 text-xs font-medium rounded mb-2 ${TASK_COLORS[key]}`}>
                  {label}
                </div>
                <div className="text-2xl font-bold text-gray-900">{uniqueMembers.size}</div>
                <div className="text-sm text-gray-500">unique members</div>
              </div>
            );
          })}
        </div>
        <div className="mt-6">
          <h4 className="font-medium mb-2">Fairness Score (variance and spread)</h4>
          <FairnessDetails assignments={schedule.assignments} />
        </div>
      </div>
    </div>
  );
}

function FairnessDetails({ assignments }) {
  // Compute per-member counts
  const counts = {};
  assignments.forEach(a => {
    counts[a.member_name] = (counts[a.member_name] || 0) + 1;
  });
  const values = Object.values(counts);
  if (values.length === 0) return <div className="text-sm text-gray-500">No data</div>;
  const avg = values.reduce((a,b)=>a+b,0) / values.length;
  const variance = values.reduce((acc, v)=> acc + Math.pow(v - avg, 2), 0) / values.length;
  const spread = Math.max(...values) - Math.min(...values);
  return (
    <div className="text-sm text-gray-700">
      <div>Members: {values.length}</div>
      <div>Average assignments: {avg.toFixed(2)}</div>
      <div>Variance: {variance.toFixed(2)}</div>
      <div>Max - Min: {spread}</div>
    </div>
  );
}

