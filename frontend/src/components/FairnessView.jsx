import React, { useEffect, useState } from 'react';
import { BarChart3, RefreshCw } from 'lucide-react';
import { getFairnessCounts } from '../services/api';

export default function FairnessView() {
  const [fairness, setFairness] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadFairness();
  }, []);

  const loadFairness = async () => {
    try {
      const response = await getFairnessCounts();
      setFairness(response.data);
    } catch (error) {
      console.error('Error loading fairness data:', error);
      alert('Failed to load fairness data');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="text-center py-12">Loading...</div>;
  }

  const maxCount = Math.max(...fairness.map(f => f.total), 1);

  return (
    <div className="px-4 py-6">
      <div className="mb-6 flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Fairness Tracking</h2>
          <p className="mt-1 text-sm text-gray-500">Assignment distribution across team members</p>
        </div>
        <button
          onClick={loadFairness}
          className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
        >
          <RefreshCw className="w-4 h-4 mr-2" />
          Refresh
        </button>
      </div>

      <div className="bg-white shadow rounded-lg p-6">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Member
                </th>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                  ATM Morning
                </th>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                  ATM Mid/Night
                </th>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                  SysAid Maker
                </th>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                  SysAid Checker
                </th>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Total
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Balance
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {fairness.map((member) => (
                <tr key={member.member_id}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    {member.member_name}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-center">
                    <div className="flex items-center justify-center">
                      <span className="text-sm text-gray-900 mr-2">{member.counts.ATM_MORNING || 0}</span>
                      <div className="w-16 bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-blue-600 h-2 rounded-full"
                          style={{ width: `${((member.counts.ATM_MORNING || 0) / maxCount) * 100}%` }}
                        />
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-center">
                    <div className="flex items-center justify-center">
                      <span className="text-sm text-gray-900 mr-2">{member.counts.ATM_MIDNIGHT || 0}</span>
                      <div className="w-16 bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-purple-600 h-2 rounded-full"
                          style={{ width: `${((member.counts.ATM_MIDNIGHT || 0) / maxCount) * 100}%` }}
                        />
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-center">
                    <div className="flex items-center justify-center">
                      <span className="text-sm text-gray-900 mr-2">{member.counts.SYSAID_MAKER || 0}</span>
                      <div className="w-16 bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-green-600 h-2 rounded-full"
                          style={{ width: `${((member.counts.SYSAID_MAKER || 0) / maxCount) * 100}%` }}
                        />
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-center">
                    <div className="flex items-center justify-center">
                      <span className="text-sm text-gray-900 mr-2">{member.counts.SYSAID_CHECKER || 0}</span>
                      <div className="w-16 bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-yellow-600 h-2 rounded-full"
                          style={{ width: `${((member.counts.SYSAID_CHECKER || 0) / maxCount) * 100}%` }}
                        />
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-center text-sm font-medium text-gray-900">
                    {member.total}
                  </td>
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
  );
}

