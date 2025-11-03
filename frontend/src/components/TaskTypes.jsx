import React, { useEffect, useState } from 'react';
import { listTaskTypes, createTaskType, deleteTaskType } from '../services/api';

export default function TaskTypes() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({
    name: '',
    recurrence: 'daily',
    required_count: 1,
    role_labels: '',
    rules_json: '{}',
    shifts: [{ label: 'Shift', start_time: '09:00', end_time: '17:00', required_count: 1 }]
  });

  useEffect(() => { load(); }, []);

  const load = async () => {
    try {
      const res = await listTaskTypes();
      setItems(res.data);
    } finally { setLoading(false); }
  };

  const addShift = () => {
    setForm(prev => ({ ...prev, shifts: [...prev.shifts, { label: '', start_time: '09:00', end_time: '17:00', required_count: 1 }] }));
  };

  const save = async (e) => {
    e.preventDefault();
    const payload = {
      name: form.name,
      recurrence: form.recurrence,
      required_count: Number(form.required_count),
      role_labels: form.role_labels ? form.role_labels.split(',').map(s => s.trim()) : [],
      rules_json: JSON.parse(form.rules_json || '{}'),
      shifts: form.shifts.map(s => ({ ...s, required_count: Number(s.required_count) }))
    };
    await createTaskType(payload);
    setForm({ name: '', recurrence: 'daily', required_count: 1, role_labels: '', rules_json: '{}', shifts: [{ label: 'Shift', start_time: '09:00', end_time: '17:00', required_count: 1 }] });
    load();
  };

  const remove = async (id) => { await deleteTaskType(id); load(); };

  if (loading) return <div className="text-center py-12">Loading...</div>;

  return (
    <div className="px-4 py-6 max-w-4xl mx-auto">
      <h2 className="text-2xl font-bold text-gray-900 mb-4">Task Types</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white shadow rounded-lg p-6">
          <h3 className="text-lg font-medium mb-4">Create Task Type</h3>
          <form onSubmit={save} className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">Name</label>
              <input className="w-full border px-3 py-2 rounded" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} required />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium mb-1">Recurrence</label>
                <select className="w-full border px-3 py-2 rounded" value={form.recurrence} onChange={e => setForm({ ...form, recurrence: e.target.value })}>
                  <option value="daily">Daily</option>
                  <option value="weekly">Weekly</option>
                  <option value="monthly">Monthly</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Required Count</label>
                <input type="number" min="1" className="w-full border px-3 py-2 rounded" value={form.required_count} onChange={e => setForm({ ...form, required_count: e.target.value })} />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Role Labels (comma-separated)</label>
              <input className="w-full border px-3 py-2 rounded" value={form.role_labels} onChange={e => setForm({ ...form, role_labels: e.target.value })} />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Rules (JSON)</label>
              <textarea className="w-full border px-3 py-2 rounded font-mono text-sm" rows="4" value={form.rules_json} onChange={e => setForm({ ...form, rules_json: e.target.value })} />
            </div>
            <div>
              <div className="flex justify-between items-center mb-2">
                <label className="text-sm font-medium">Shifts</label>
                <button type="button" onClick={addShift} className="text-indigo-600">+ Add Shift</button>
              </div>
              <div className="space-y-2">
                {form.shifts.map((s, idx) => (
                  <div key={idx} className="grid grid-cols-4 gap-2">
                    <input placeholder="Label" className="border px-2 py-1 rounded" value={s.label} onChange={e => setForm(prev => ({ ...prev, shifts: prev.shifts.map((sh,i)=> i===idx? { ...sh, label: e.target.value }: sh) }))} />
                    <input type="time" className="border px-2 py-1 rounded" value={s.start_time} onChange={e => setForm(prev => ({ ...prev, shifts: prev.shifts.map((sh,i)=> i===idx? { ...sh, start_time: e.target.value }: sh) }))} />
                    <input type="time" className="border px-2 py-1 rounded" value={s.end_time} onChange={e => setForm(prev => ({ ...prev, shifts: prev.shifts.map((sh,i)=> i===idx? { ...sh, end_time: e.target.value }: sh) }))} />
                    <input type="number" min="1" className="border px-2 py-1 rounded" value={s.required_count} onChange={e => setForm(prev => ({ ...prev, shifts: prev.shifts.map((sh,i)=> i===idx? { ...sh, required_count: e.target.value }: sh) }))} />
                  </div>
                ))}
              </div>
            </div>
            <div className="flex justify-end">
              <button type="submit" className="px-4 py-2 bg-indigo-600 text-white rounded">Create</button>
            </div>
          </form>
        </div>
        <div className="bg-white shadow rounded-lg p-6">
          <h3 className="text-lg font-medium mb-4">Existing Task Types</h3>
          <div className="space-y-3">
            {items.map(item => (
              <div key={item.id} className="border rounded p-3">
                <div className="flex justify-between">
                  <div>
                    <div className="font-medium">{item.name} <span className="text-gray-400 text-sm">({item.recurrence})</span></div>
                    <div className="text-sm text-gray-500">Roles: {item.role_labels?.join(', ') || '-'}</div>
                  </div>
                  <button className="text-red-600" onClick={()=>remove(item.id)}>Delete</button>
                </div>
                {item.shifts?.length>0 && (
                  <div className="mt-2 text-sm">
                    <div className="text-gray-600">Shifts:</div>
                    <ul className="list-disc list-inside">
                      {item.shifts.map(s => (
                        <li key={s.id}>{s.label}: {s.start_time} - {s.end_time} (x{s.required_count})</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ))}
            {items.length===0 && <div className="text-gray-500 text-sm">No task types yet.</div>}
          </div>
        </div>
      </div>
    </div>
  );
}


