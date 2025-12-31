import React, { useEffect, useState } from 'react';
import { BarChart3, RefreshCw, Download } from 'lucide-react';
import { getFairnessTable, recalcFairness } from '../services/api';
import api from '../services/api';
import ConfirmDialog from './ConfirmDialog';

export default function FairnessView() {
  const [columns, setColumns] = useState([]);
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);

  useEffect(() => {
    loadFairness();
  }, []);

  const loadFairness = async () => {
    try {
      setRefreshing(true);
      const response = await getFairnessTable({ statuses: 'draft,published' });
      const data = response.data || {};
      setColumns(Array.isArray(data.columns) ? data.columns : []);
      setRows(Array.isArray(data.rows) ? data.rows : []);
    } catch (error) {
      console.error('Error loading fairness data:', error);
      alert('Failed to load fairness data');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleExportPDF = async () => {
    try {
      const response = await api.get('/fairness/export/pdf', { responseType: 'blob', params: { statuses: 'draft,published' } });
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `fairness_${new Date().toISOString().split('T')[0]}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Error exporting fairness PDF:', error);
      alert('Failed to export fairness PDF');
    }
  };

  const handleRecalculate = async () => {
    try {
      setRefreshing(true);
      await recalcFairness();
      await loadFairness();
    } catch (error) {
      console.error('Error recalculating fairness:', error);
      alert('Failed to recalculate fairness');
    } finally {
      setRefreshing(false);
      setConfirmOpen(false);
    }
  };

  if (loading) {
    return <div className="text-center py-12">Loading...</div>;
  }

  const maxCount = Math.max(...rows.map(f => f.total), 1);

  return (
    <>
    <div className="px-4 py-6">
      <div className="mb-6 flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Fairness Tracking</h2>
          <p className="mt-1 text-sm text-gray-500">Assignment distribution across team members</p>
        </div>
        <div className="flex space-x-2">
          <button
            onClick={loadFairness}
            disabled={refreshing}
            className={`inline-flex items-center px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 transition-all duration-200 ${
              refreshing ? 'opacity-50 cursor-not-allowed' : 'hover:scale-105'
            }`}
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
            {refreshing ? 'Refreshing...' : 'Refresh'}
          </button>
          <button
            onClick={handleExportPDF}
            className="inline-flex items-center px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition-all duration-200 hover:scale-105"
          >
            <Download className="w-4 h-4 mr-2" />
            Export PDF
          </button>
            <button
              onClick={() => setConfirmOpen(true)}
              disabled={refreshing}
              className="inline-flex items-center px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 transition-all duration-200 hover:scale-105"
            >
              <BarChart3 className="w-4 h-4 mr-2" />
              Recalculate
            </button>
        </div>
      </div>

      <div className="bg-white shadow rounded-lg p-6">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 table-fixed">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Member</th>
                {columns.map((c) => (
                  <th key={c} className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider whitespace-pre-wrap break-words" title={c}>
                    {c.replaceAll('_',' ')}
                  </th>
                ))}
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Total</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Balance</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {rows.map((member) => (
                <tr key={member.member_id}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{member.member_name}</td>
                  {columns.map((c) => (
                    <td key={c} className="px-4 py-4 whitespace-nowrap text-sm text-gray-900">{member.counts?.[c] ?? 0}</td>
                  ))}
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{member.total}</td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="w-32 bg-gray-200 rounded-full h-2">
                      <div
                        className={`h-2 rounded-full ${
                          member.total <= maxCount * 0.8
                            ? 'bg-green-600'
                            : member.total <= maxCount * 1.2
                            ? 'bg-yellow-600'
                            : 'bg-red-600'
                        }`}
                        style={{ width: `${(member.total / maxCount) * 100}%` }}
                      />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h3 className="text-sm font-medium text-blue-900 mb-2">Fairness Metrics</h3>
        <ul className="text-sm text-blue-800 space-y-1">
          <li>• Fairness window: 90 days (rolling)</li>
          <li>• Goal: Equal distribution across all task types</li>
          <li>• Green: Well balanced (&lt; 80% of max)</li>
          <li>• Yellow: Moderate (80-120% of max)</li>
          <li>• Red: Needs attention (&gt; 120% of max)</li>
        </ul>
      </div>
    </div>
    <ConfirmDialog
      open={confirmOpen}
      title="Recalculate Fairness?"
      message="This will rebuild fairness counters within the configured window. Continue?"
      onCancel={() => setConfirmOpen(false)}
      onConfirm={handleRecalculate}
    />
    </>
  );
}

