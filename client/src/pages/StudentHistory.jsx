import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../services/api";

export default function StudentHistory() {
  const navigate = useNavigate();
  const userId = localStorage.getItem("userId");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [grouped, setGrouped] = useState({});

  useEffect(() => {
    const fetchHistory = async () => {
      setError("");
      try {
        const res = await api.get(`/request/student/${userId}`);
        const list = res?.data?.data || [];

        // Normalize records (stringify ids, timestamps)
        const normalized = list.map((r) => ({
          request_id: r._id?.$oid || r._id || String(r._id || ""),
          reason: r.reason,
          status: r.status,
          mentor_status: r.mentor_status,
          mentor_name: r.mentor_name,
          mentor_remark: r.mentor_remark,
          mentor_parent_contacted: r.mentor_parent_contacted,
          hod_name: r.hod_name,
          approve_on_behalf_of_hod: !!r.approve_on_behalf_of_hod,
          delegate_comment: r.delegate_comment,
          semester: r.semester,
          academic_year: r.academic_year,
          request_time: r.request_time,
          approval_time: r.approval_time,
          exit_mark_time: r.exit_mark_time,
        }));

        // Group by semester
        const bySem = normalized.reduce((acc, r) => {
          const key = r.semester ? `Semester ${r.semester}` : "Unknown Semester";
          acc[key] = acc[key] || [];
          acc[key].push(r);
          return acc;
        }, {});

        // Sort each group's entries by request_time desc
        Object.keys(bySem).forEach((key) => {
          bySem[key].sort((a, b) => new Date(b.request_time) - new Date(a.request_time));
        });

        setGrouped(bySem);
      } catch (err) {
        const msg = err.response?.data?.detail || err.response?.data?.message || "Failed to load history";
        setError(msg);
      } finally {
        setLoading(false);
      }
    };

    fetchHistory();
  }, [userId]);

  const formatTime = (t) => {
    if (!t) return "-";
    try {
      return new Date(t).toLocaleString();
    } catch {
      return String(t);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="w-10 h-10 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Loading history…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 shadow-sm">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-4 flex justify-between items-center">
          <h1 className="text-xl font-bold text-gray-800 dark:text-white">Gate Pass History</h1>
          <button
            onClick={() => navigate(-1)}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-gray-700 dark:text-gray-200 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-sm font-medium transition-colors"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            Back
          </button>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-8 space-y-6">
        {error && (
          <div className="p-4 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 text-sm font-medium">
            {error}
          </div>
        )}

        {Object.keys(grouped).length === 0 ? (
          <div className="rounded-2xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-12 text-center">
            <p className="text-gray-500 dark:text-gray-400">No history found.</p>
          </div>
        ) : (
          Object.entries(grouped)
            .sort((a, b) => {
              const getSem = (label) => (label.startsWith("Semester ") ? parseInt(label.replace("Semester ", ""), 10) : -1);
              return getSem(b[0]) - getSem(a[0]);
            })
            .map(([semLabel, items]) => (
              <section
                key={semLabel}
                className="rounded-2xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 overflow-hidden shadow-sm"
              >
                <div className="px-6 py-4 border-b border-gray-100 dark:border-gray-700 bg-gray-50/80 dark:bg-gray-800/80 flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-3">
                    <span className="w-1 h-8 rounded-full bg-indigo-500" />
                    <div>
                      <h2 className="text-base font-semibold text-gray-800 dark:text-white">{semLabel}</h2>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        Academic year: {items[0]?.academic_year || "—"}
                      </p>
                    </div>
                  </div>
                  <span className="text-xs font-medium text-gray-500 dark:text-gray-400 bg-gray-200/80 dark:bg-gray-700 px-2.5 py-1 rounded-md">
                    {items.length} request{items.length !== 1 ? "s" : ""}
                  </span>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left">
                    <thead>
                      <tr className="text-[11px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider border-b border-gray-200 dark:border-gray-700">
                        <th className="px-6 py-3">Reason</th>
                        <th className="px-6 py-3">Requested</th>
                        <th className="px-6 py-3">Mentor</th>
                        <th className="px-6 py-3">HOD</th>
                        <th className="px-6 py-3">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                      {items.map((r) => (
                        <tr key={r.request_id} className="hover:bg-gray-50 dark:hover:bg-gray-700/30 transition-colors">
                          <td className="px-6 py-4 text-sm font-medium text-gray-800 dark:text-gray-200">{r.reason}</td>
                          <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-400 whitespace-nowrap">{formatTime(r.request_time)}</td>
                          <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-400">
                            <div className="space-y-0.5">
                              <div className="font-medium text-gray-800 dark:text-gray-200">{r.mentor_name || "—"}</div>
                              {r.mentor_status && <div className="text-xs text-gray-500">{r.mentor_status}</div>}
                              {r.mentor_remark && <div className="text-xs text-gray-500 italic">{r.mentor_remark}</div>}
                            </div>
                          </td>
                          <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-400">
                            <div className="space-y-1">
                              <div>{r.hod_name || "—"}</div>
                              {r.approve_on_behalf_of_hod && (
                                <div className="text-xs text-amber-700 dark:text-amber-300">
                                  Approved on behalf of HOD by {r.mentor_name || "Mentor"}
                                </div>
                              )}
                              {r.delegate_comment && (
                                <div className="text-xs italic text-gray-500 dark:text-gray-400">
                                  "{r.delegate_comment}"
                                </div>
                              )}
                            </div>
                          </td>
                          <td className="px-6 py-4">
                            <span
                              className={`inline-flex px-2.5 py-1 rounded-lg text-[10px] font-semibold uppercase tracking-wide ${
                                r.status === "PENDING_MENTOR"
                                  ? "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300"
                                  : r.status === "PENDING_HOD"
                                  ? "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300"
                                  : r.status === "APPROVED" || r.status === "LEFT_CAMPUS"
                                  ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300"
                                  : r.status === "EXIT_ALLOWED"
                                  ? "bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300"
                                  : r.status === "UNCHECKED"
                                  ? "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300"
                                  : r.status === "APPROVED_NOT_LEFT"
                                  ? "bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-300"
                                  : "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300"
                              }`}
                            >
                              {r.status}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            ))
        )}
      </main>
    </div>
  );
}