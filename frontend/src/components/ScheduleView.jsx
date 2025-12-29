import React, { useEffect, useState } from 'react';
import ErrorBoundary from './ErrorBoundary';
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

function ScheduleView() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [schedule, setSchedule] = useState(null);
  const [loading, setLoading] = useState(true);
  const [groupedAssignments, setGroupedAssignments] = useState({});
  const [dynamicAssignments, setDynamicAssignments] = useState([]);
  const [taskFilter, setTaskFilter] = useState('all');
  const [team, setTeam] = useState([]);
  const { me } = useAuth();
  const isAdmin = me?.role === 'admin';
  const DEFAULT_TASK_TYPES = new Set(['ATM_MORNING', 'ATM_MIDNIGHT', 'SYSAID_MAKER', 'SYSAID_CHECKER']);

  const dynamicAssignmentsByTask = React.useMemo(() => {
    const groups = {};
    dynamicAssignments.forEach(item => {
      const key = item.task_type || item.custom_task_name || 'Custom Task';
      if (!groups[key]) groups[key] = [];
      groups[key].push(item);
    });
    Object.values(groups).forEach(items => {
      items.sort((a, b) => new Date(a.assignment_date) - new Date(b.assignment_date));
    });
    return groups;
  }, [dynamicAssignments]);

  useEffect(() => {
    loadSchedule();
    getTeamMembers().then(res => setTeam(res.data));
  }, [id]);

  const loadSchedule = async () => {
    try {
      const response = await getSchedule(id);
      setSchedule(response.data);
      const defaultTaskTypes = new Set(['ATM_MORNING', 'ATM_MIDNIGHT', 'SYSAID_MAKER', 'SYSAID_CHECKER']);
      const grouped = {};
      const dynamicOnly = [];
      // New API stores dynamic tasks using their task identifier string (task_type)
      response.data.assignments.forEach(assignment => {
        const date = assignment.assignment_date;
        if (defaultTaskTypes.has(assignment.task_type)) {
          if (!grouped[date]) grouped[date] = [];
          grouped[date].push(assignment);
        } else {
          // Any non-default task_type is considered a custom/dynamic task
          dynamicOnly.push(assignment);
        }
      });
      setGroupedAssignments(grouped);
      setDynamicAssignments(dynamicOnly);
    } catch (error) {
      console.error('Error loading schedule:', error);
      alert('Failed to load schedule');
    } finally {
      setLoading(false);
    }
  };

  const getDefaultColumns = () => ([
    { key: 'ATM_MORNING', label: 'ATM Morning', color: TASK_COLORS.ATM_MORNING },
    { key: 'ATM_MIDNIGHT', label: 'ATM Mid/Night', color: TASK_COLORS.ATM_MIDNIGHT },
    { key: 'SYSAID_MAKER', label: 'SysAid Maker', color: TASK_COLORS.SYSAID_MAKER },
    { key: 'SYSAID_CHECKER', label: 'SysAid Checker', color: TASK_COLORS.SYSAID_CHECKER }
  ]);

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
      const response = await exportScheduleExcel(id);
      const blob = new Blob([response.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `schedule_${id}.xlsx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (e) { 
      alert(e.response?.data?.detail || 'Failed to export Excel');
    }
  };
  const handleExportPDF = async () => {
    try {
      const response = await exportSchedulePDF(id);
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `schedule_${id}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (e) { 
      alert(e.response?.data?.detail || 'Failed to export PDF');
    }
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

  const hasDefaultAssignments = Object.keys(groupedAssignments).length > 0;
  const isDynamicOnly = schedule.assignments.length > 0 && schedule.assignments.every(a => !DEFAULT_TASK_TYPES.has(a.task_type));
  const dates = hasDefaultAssignments
    ? eachDayOfInterval({
        start: parseISO(schedule.start_date),
        end: parseISO(schedule.end_date)
      })
    : [];

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


  const recurrenceLabel = (recurrence) => {
    if (!recurrence) return 'Custom';
    return recurrence.charAt(0).toUpperCase() + recurrence.slice(1);
  };

  const safeFormat = (dateStr, fmt) => {
    try {
      if (!dateStr) return '';
      return format(parseISO(dateStr), fmt);
    } catch (e) {
      return String(dateStr);
    }
  };

  const renderDynamicTaskBody = (items, recurrence) => {
    if (recurrence === 'weekly') {
      const weeks = {};
      items.forEach(item => {
        const key = item.week_start || item.assignment_date;
        if (!weeks[key]) weeks[key] = {};
        const role = item.custom_task_shift || item.shift_label || 'Role';
        if (!weeks[key][role]) weeks[key][role] = new Map();
        weeks[key][role].set(item.member_id, item.member_name);
      });
      return (
        <div className="mt-3 space-y-3">
          {Object.entries(weeks)
            .sort((a, b) => new Date(a[0]) - new Date(b[0]))
            .map(([weekKey, roles]) => (
              <div key={weekKey} className="bg-gray-50 border rounded-lg p-3">
                <div className="text-xs text-gray-500">Week of {safeFormat(weekKey, 'MMM dd')}</div>
                <div className="mt-2 grid gap-2 sm:grid-cols-2">
                  {Object.entries(roles).map(([role, members]) => (
                    <div key={role}>
                      <div className="text-xs text-gray-500">{role}</div>
                      <div className="text-sm font-medium text-gray-900">
                        {Array.from(members.values()).join(', ')}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
        </div>
      );
    }
    
    const datesMap = {};
    items.forEach(item => {
      const key = item.assignment_date;
      if (!datesMap[key]) datesMap[key] = [];
      datesMap[key].push(item);
    });
    
    return (
      <div className="mt-3 space-y-2">
        {Object.entries(datesMap)
          .sort((a, b) => new Date(a[0]) - new Date(b[0]))
          .map(([dateStr, entries]) => (
              <div key={dateStr} className="flex flex-col sm:flex-row sm:items-center sm:justify-between border-b last:border-b-0 pb-2">
              <div className="text-sm text-gray-500">{safeFormat(dateStr, 'EEE, MMM dd')}</div>
              <div className="text-sm font-medium text-gray-900">
                {entries.map(entry => `${entry.member_name}${entry.custom_task_shift ? ` (${entry.custom_task_shift})` : ''}`).join(', ')}
              </div>
            </div>
          ))}
      </div>
    );
  };

  const renderDynamicAssignmentsSection = (filterTask) => {
    if (dynamicAssignments.length === 0) return null;
    const entries = Object.entries(dynamicAssignmentsByTask).filter(([taskName]) => {
      return !filterTask || filterTask === 'all' || filterTask === taskName;
    });
    if (entries.length === 0) return null;
    return (
      <div className="mt-8 bg-white shadow rounded-lg p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Custom Task Assignments</h3>
        <div className="space-y-4">
          {entries.map(([taskName, items]) => {
            const recurrence = items[0]?.recurrence || 'custom';
            return (
              <div key={taskName} className="border rounded-lg p-4">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
                  <div className="text-base font-semibold text-gray-900">{taskName}</div>
                  <span className="text-xs uppercase tracking-wide text-gray-500 mt-1 sm:mt-0">
                    {recurrenceLabel(recurrence)} recurrence
                  </span>
                </div>
                {renderDynamicTaskBody(items, recurrence)}
              </div>
            );
          })}
        </div>
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
            {safeFormat(schedule.start_date, 'MMM dd')} - {safeFormat(schedule.end_date, 'MMM dd, yyyy')}
          </p>
        </div>
        <div className="space-x-2">
          <select value={taskFilter} onChange={(e)=>setTaskFilter(e.target.value)} className="mr-2 px-2 py-1 border rounded">
            <option value="all">All tasks</option>
            <option value="default">Default (ATM/SysAid)</option>
            {Object.keys(dynamicAssignmentsByTask).map(k => (
              <option key={k} value={k}>{k}</option>
            ))}
          </select>
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

      {(!isDynamicOnly && (taskFilter === 'all' || taskFilter === 'default') && hasDefaultAssignments) && (
        <div className="bg-white shadow rounded-lg overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Date
                  </th>
                  {getDefaultColumns().map(column => (
                    <th key={column.key} className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      {column.label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {dates.map((date) => {
                  const dateStr = format(date, 'yyyy-MM-dd');
                  const assignments = groupedAssignments[dateStr] || [];
                  const columns = getDefaultColumns();
                  
                  const getAssignmentsForColumn = (column) => {
                    return assignments.filter(a => a.task_type === column.key);
                  };

                  return (
                    <tr key={dateStr}>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        <div>{format(date, 'EEE, MMM dd')}</div>
                      </td>
                      {columns.map(column => (
                        <td key={column.key} className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {renderAssignmentChips(getAssignmentsForColumn(column), column.color)}
                        </td>
                      ))}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {renderDynamicAssignmentsSection(taskFilter === 'default' ? null : taskFilter)}

      {/* Assignment Summary & Fairness */}
      {(!isDynamicOnly && hasDefaultAssignments) && (
        <div className="mt-6 bg-white shadow rounded-lg p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Assignment Summary</h3>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {getDefaultColumns().map(column => {
            const taskAssignments = schedule.assignments.filter(a => {
                return a.task_type === column.key;
              });
              const uniqueMembers = new Set(taskAssignments.map(a => a.member_name));
              return (
                <div key={column.key} className="border rounded-lg p-4">
                  <div className={`inline-block px-2 py-1 text-xs font-medium rounded mb-2 ${column.color}`}>
                    {column.label}
                  </div>
                  <div className="text-2xl font-bold text-gray-900">{uniqueMembers.size}</div>
                  <div className="text-sm text-gray-500">unique members</div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {!isDynamicOnly && (
        <div className="mt-6 bg-white shadow rounded-lg p-6">
          <h4 className="font-medium mb-2">Fairness Score (variance and spread)</h4>
          <FairnessDetails assignments={schedule.assignments} />
        </div>
      )}
    </div>
  );
}

const WrappedScheduleView = (props) => (
  <ErrorBoundary>
    <ScheduleView {...props} />
  </ErrorBoundary>
);

export default WrappedScheduleView;

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

