/*
ENYARD Frontend (single-file React component)

Instructions:
1. Create a new React app (Vite recommended):
   npm create vite@latest enyard-frontend --template react
   cd enyard-frontend
2. Install Tailwind (or use plain CSS):
   npm install -D tailwindcss postcss autoprefixer
   npx tailwindcss init -p
   // add Tailwind directives to ./src/index.css
3. Replace src/App.jsx with this file content. Start dev server:
   npm install
   npm run dev

API base: http://127.0.0.1:8000

This component lists employees, shows snapshots and logs, and allows downloading images.
*/

import React, { useEffect, useState } from "react";

const API_BASE = "http://127.0.0.1:8000";

export default function App() {
  const [employees, setEmployees] = useState([]);
  const [selectedEmp, setSelectedEmp] = useState(null);
  const [snapshots, setSnapshots] = useState([]);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [snapLimit, setSnapLimit] = useState(50);
  const [logLimit, setLogLimit] = useState(50);
  const [query, setQuery] = useState("");

  useEffect(() => {
    fetchEmployees();
  }, []);

  useEffect(() => {
    if (selectedEmp) fetchEmployeeDetails(selectedEmp.id);
  }, [selectedEmp, snapLimit, logLimit]);

  async function fetchEmployees() {
    try {
      setLoading(true);
      const res = await fetch(`${API_BASE}/employees`);
      const data = await res.json();
      setEmployees(data.employees || []);
    } catch (e) {
      console.error(e);
      alert("Failed to fetch employees. Is the API running?");
    } finally {
      setLoading(false);
    }
  }

  async function fetchEmployeeDetails(id) {
    try {
      setLoading(true);
      const res = await fetch(`${API_BASE}/employees/${id}?snaps_limit=${snapLimit}&logs_limit=${logLimit}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setSnapshots(data.snapshots || []);
      setLogs(data.logs || []);
    } catch (e) {
      console.error(e);
      alert("Failed to fetch employee details");
    } finally {
      setLoading(false);
    }
  }

  function onSelectEmployee(emp) {
    setSelectedEmp(emp);
    setSnapshots([]);
    setLogs([]);
  }

  function downloadSnapshot(snapshot) {
    // open download URL in new tab
    const url = `${API_BASE}/download?snapshot_id=${snapshot.id}`;
    window.open(url, "_blank");
  }

  function openSnapshotFull(snapshot) {
    const url = `${API_BASE}/download?snapshot_id=${snapshot.id}`;
    window.open(url, "_blank");
  }

  const filteredEmployees = employees.filter((e) => {
    if (!query) return true;
    const q = query.toLowerCase();
    return (e.employee_name || "").toLowerCase().includes(q) || (e.safe_name || "").toLowerCase().includes(q);
  });

  return (
    <div className="min-h-screen bg-gray-100 text-gray-800">
      <div className="max-w-7xl mx-auto p-4">
        <header className="flex items-center justify-between mb-4">
          <h1 className="text-2xl font-semibold">ENYARD Dashboard</h1>
          <div className="text-sm text-gray-600">API: {API_BASE}</div>
        </header>

        <div className="grid grid-cols-12 gap-4">
          {/* Sidebar */}
          <aside className="col-span-3 bg-white rounded shadow p-3">
            <div className="flex items-center gap-2 mb-3">
              <input
                type="text"
                placeholder="Search employees..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="w-full border rounded px-2 py-1 text-sm"
              />
            </div>
            <div className="text-xs text-gray-500 mb-2">Employees ({filteredEmployees.length})</div>
            <div className="space-y-1 max-h-[60vh] overflow-auto">
              {loading && employees.length === 0 ? (
                <div className="text-sm text-gray-500">Loading...</div>
              ) : filteredEmployees.length === 0 ? (
                <div className="text-sm text-gray-500">No employees found</div>
              ) : (
                filteredEmployees.map((emp) => (
                  <button
                    key={emp.id}
                    onClick={() => onSelectEmployee(emp)}
                    className={`w-full text-left p-2 rounded ${selectedEmp && selectedEmp.id === emp.id ? 'bg-indigo-50 border-l-4 border-indigo-500' : 'hover:bg-gray-50'}`}>
                    <div className="font-medium text-sm">{emp.employee_name}</div>
                    <div className="text-xs text-gray-500">{emp.safe_name}</div>
                  </button>
                ))
              )}
            </div>

            <div className="mt-4 flex gap-2">
              <button onClick={fetchEmployees} className="px-3 py-1 bg-indigo-600 text-white rounded text-sm">Refresh</button>
              <button onClick={() => { setQuery(''); }} className="px-3 py-1 border rounded text-sm">Clear</button>
            </div>
          </aside>

          {/* Main */}
          <main className="col-span-9">
            {!selectedEmp ? (
              <div className="bg-white rounded shadow p-6">Select an employee to view snapshots and logs.</div>
            ) : (
              <div className="space-y-4">
                <div className="bg-white rounded shadow p-4 flex items-center justify-between">
                  <div>
                    <div className="text-lg font-semibold">{selectedEmp.employee_name}</div>
                    <div className="text-sm text-gray-500">{selectedEmp.safe_name} • {selectedEmp.folder_path}</div>
                  </div>
                  <div className="flex items-center gap-2">
                    <label className="text-sm text-gray-600">Snaps</label>
                    <select value={snapLimit} onChange={e => setSnapLimit(Number(e.target.value))} className="border rounded px-2 py-1">
                      <option value={10}>10</option>
                      <option value={25}>25</option>
                      <option value={50}>50</option>
                      <option value={100}>100</option>
                    </select>
                    <label className="text-sm text-gray-600">Logs</label>
                    <select value={logLimit} onChange={e => setLogLimit(Number(e.target.value))} className="border rounded px-2 py-1">
                      <option value={10}>10</option>
                      <option value={25}>25</option>
                      <option value={50}>50</option>
                    </select>
                    <button onClick={() => fetchEmployeeDetails(selectedEmp.id)} className="px-3 py-1 bg-indigo-600 text-white rounded text-sm">Reload</button>
                  </div>
                </div>

                {/* Snapshots grid */}
                <section className="bg-white rounded shadow p-4">
                  <h2 className="font-semibold mb-3">Snapshots ({snapshots.length})</h2>
                  {snapshots.length === 0 ? (
                    <div className="text-sm text-gray-500">No snapshots yet.</div>
                  ) : (
                    <div className="grid grid-cols-4 gap-3">
                      {snapshots.map(s => (
                        <div key={s.id} className="border rounded overflow-hidden bg-gray-50">
                          <img
                            src={`${API_BASE}/download?snapshot_id=${s.id}`}
                            alt={s.window_title}
                            onClick={() => openSnapshotFull(s)}
                            className="w-full h-40 object-cover cursor-pointer"
                          />
                          <div className="p-2 text-xs">
                            <div className="truncate font-medium">{s.window_title}</div>
                            <div className="text-gray-500">{s.captured_at}</div>
                            <div className="mt-2 flex gap-2">
                              <button onClick={() => downloadSnapshot(s)} className="text-sm px-2 py-1 border rounded">Download</button>
                              <a href={`${API_BASE}/download?snapshot_id=${s.id}`} target="_blank" rel="noreferrer" className="text-sm px-2 py-1 border rounded">Open</a>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </section>

                {/* Logs */}
                <section className="bg-white rounded shadow p-4">
                  <h2 className="font-semibold mb-3">Recent Logs ({logs.length})</h2>
                  {logs.length === 0 ? (
                    <div className="text-sm text-gray-500">No logs yet.</div>
                  ) : (
                    <div className="space-y-2 max-h-64 overflow-auto">
                      {logs.map(l => (
                        <div key={l.id} className="text-sm">
                          <div className="text-xs text-gray-500">{l.created_at} • {l.level}</div>
                          <div>{l.message}</div>
                        </div>
                      ))}
                    </div>
                  )}
                </section>
              </div>
            )}
          </main>
        </div>
      </div>
    </div>
  );
}
