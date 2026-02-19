import { useState, useEffect, useRef } from "react";
import api from "../services/api";
import * as XLSX from "xlsx";
import { jsPDF } from "jspdf";
import { autoTable } from "jspdf-autotable";

const STATUS_OPTIONS = [
  { value: "approved", label: "Approved" },
  { value: "rejected", label: "Rejected" },
  { value: "pending", label: "Pending" },
  { value: "left", label: "Left" },
];

const ALL_STATUS_OPTIONS = [
  { value: "REQUESTED", label: "REQUESTED" },
  { value: "PENDING_MENTOR", label: "PENDING_MENTOR" },
  { value: "APPROVED_BY_MENTOR", label: "APPROVED_BY_MENTOR" },
  { value: "REJECTED_BY_MENTOR", label: "REJECTED_BY_MENTOR" },
  { value: "PENDING_HOD", label: "PENDING_HOD" },
  { value: "MENTOR_UNCHECKED", label: "MENTOR_UNCHECKED" },
  { value: "HOD_UNCHECKED", label: "HOD_UNCHECKED" },
  { value: "UNCHECKED", label: "UNCHECKED" },
  { value: "APPROVED", label: "APPROVED" },
  { value: "REJECTED", label: "REJECTED" },
  { value: "LEFT_CAMPUS", label: "LEFT_CAMPUS" },
  { value: "APPROVED_NOT_LEFT", label: "APPROVED_NOT_LEFT" },
];

const ALLOWED_FIELDS = {
  SUPER_ADMIN: ["studentId", "name", "year", "course", "section", "college", "startDate", "endDate", "status", "hodIds", "mentorIds"],
  ADMIN: ["studentId", "name", "year", "course", "section", "startDate", "endDate", "status", "hodIds", "mentorIds"],
  HOD: ["studentId", "name", "year", "course", "section", "startDate", "endDate", "status", "mentorIds"],
  MENTOR: ["studentId", "name", "startDate", "endDate", "status"],
};

export default function FilterRequestsModal({ open, onClose, role }) {
  const [filterOptions, setFilterOptions] = useState({ hods: [], mentors: [] });
  const [filters, setFilters] = useState({
    studentId: "",
    name: "",
    year: "",
    years: [],
    course: "",
    courses: [],
    section: "",
    sections: [],
    college: "",
    startDate: "",
    endDate: "",
    status: "",
    statuses: [],
    hodIds: [],
    mentorIds: [],
  });
  const [result, setResult] = useState(null);

  useEffect(() => {
    if (open && (role === "ADMIN" || role === "HOD" || role === "SUPER_ADMIN")) {
      api
        .get("/request/filter-options")
        .then((res) => {
          const data = res.data?.data ?? res.data;
          setFilterOptions({ hods: data?.hods ?? [], mentors: data?.mentors ?? [] });
        })
        .catch(() => setFilterOptions({ hods: [], mentors: [] }));
    }
  }, [open, role]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [page, setPage] = useState(1);
  const [downloadOpen, setDownloadOpen] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const downloadRef = useRef(null);
  const pageSize = 20;

  const allowed = ALLOWED_FIELDS[role] || ALLOWED_FIELDS.MENTOR;
  const hasHodCheckboxes = allowed.includes("hodIds");
  const hasMentorCheckboxes = allowed.includes("mentorIds");
  const hasDateFilter = allowed.includes("startDate") && allowed.includes("endDate");

  const toDateString = (d) => d.toISOString().slice(0, 10);

  const setDateRangePreset = (preset) => {
    const today = new Date();
    const todayStr = toDateString(today);
    let startStr = todayStr;
    let endStr = todayStr;
    if (preset === "today") {
      startStr = todayStr;
      endStr = todayStr;
    } else if (preset === "lastWeek") {
      const start = new Date(today);
      start.setDate(start.getDate() - 7);
      startStr = toDateString(start);
      endStr = todayStr;
    } else if (preset === "last15Days") {
      const start = new Date(today);
      start.setDate(start.getDate() - 15);
      startStr = toDateString(start);
      endStr = todayStr;
    } else if (preset === "past30Days") {
      const start = new Date(today);
      start.setDate(start.getDate() - 30);
      startStr = toDateString(start);
      endStr = todayStr;
    }
    setFilters((f) => ({ ...f, startDate: startStr, endDate: endStr }));
  };

  const buildPayload = () => {
    const payload = { page, pageSize: pageSize, sortBy: "request_time", sortOrder: "desc" };
    if (filters.studentId?.trim()) payload.studentId = filters.studentId.trim();
    if (filters.name?.trim()) payload.name = filters.name.trim();
    if (filters.year !== "" && filters.year != null) payload.year = Number(filters.year);
    if (filters.course?.trim()) payload.course = filters.course.trim();
    if (filters.section?.trim()) payload.section = filters.section.trim();
    if (role === "SUPER_ADMIN" && filters.college?.trim()) payload.college = filters.college.trim();
    if (filters.startDate?.trim()) payload.startDate = filters.startDate.trim();
    if (filters.endDate?.trim()) payload.endDate = filters.endDate.trim();
    if (filters.status?.trim()) payload.statuses = [filters.status.trim()];
    if (filters.statuses?.length) payload.statuses = filters.statuses;
    if (hasHodCheckboxes && filters.hodIds?.length) payload.hodIds = filters.hodIds;
    if (hasMentorCheckboxes && filters.mentorIds?.length) payload.mentorIds = filters.mentorIds;
    return payload;
  };

  const handleApply = async () => {
    setError("");
    setLoading(true);
    setResult(null);
    try {
      const res = await api.post("/request/filter", buildPayload());
      const data = res.data?.data ?? res.data;
      setResult(Array.isArray(data) ? { items: data, total: data.length, page: 1, pageSize } : data);
    } catch (err) {
      setError(err.response?.data?.detail || err.response?.data?.message || "Failed to fetch filtered requests.");
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    setFilters({
      studentId: "",
      name: "",
      year: "",
      years: [],
      course: "",
      courses: [],
      section: "",
      sections: [],
      college: "",
      startDate: "",
      endDate: "",
      status: "",
      statuses: [],
      hodIds: [],
      mentorIds: [],
    });
    setResult(null);
    setError("");
    setPage(1);
  };

  const fetchAllForDownload = async () => {
    const payload = { ...buildPayload(), page: 1, pageSize: Math.min(10000, total || 1000) };
    const res = await api.post("/request/filter", payload);
    const data = res.data?.data ?? res.data;
    return Array.isArray(data) ? data : (data?.items ?? []);
  };

  const handleDownload = async (format) => {
    setDownloadOpen(false);
    if (items.length === 0 && total === 0) return;
    setDownloading(true);
    try {
      const allItems = total <= pageSize ? items : await fetchAllForDownload();
      const headers = ["Student ID", "Name", "Course", "Year", "Section", "Reason", "Status", "Request time"];
      const rows = allItems.map((r) => [
        r.student_id ?? "",
        r.student_name ?? "",
        r.course ?? "",
        r.year ?? "",
        r.section ?? "",
        r.reason ?? "",
        r.status ?? "",
        r.request_time ? new Date(r.request_time).toLocaleString() : "—",
      ]);

      const filename = `filtered-requests-${new Date().toISOString().slice(0, 10)}`;

      if (format === "xlsx") {
        const ws = XLSX.utils.aoa_to_sheet([headers, ...rows]);
        const wb = XLSX.utils.book_new();
        XLSX.utils.book_append_sheet(wb, ws, "Requests");
        XLSX.writeFile(wb, `${filename}.xlsx`);
      } else {
        const doc = new jsPDF({ orientation: "landscape" });
        autoTable(doc, {
          head: [headers],
          body: rows,
          styles: { fontSize: 8 },
        });
        doc.save(`${filename}.pdf`);
      }
    } catch (err) {
      setError(err.response?.data?.detail || "Download failed.");
    } finally {
      setDownloading(false);
    }
  };

  useEffect(() => {
    const close = (e) => {
      if (downloadRef.current && !downloadRef.current.contains(e.target)) setDownloadOpen(false);
    };
    document.addEventListener("click", close);
    return () => document.removeEventListener("click", close);
  }, []);

  const handlePage = (dir) => {
    const next = page + dir;
    if (next < 1) return;
    setPage(next);
    setResult(null);
    setLoading(true);
    setError("");
    api
      .post("/request/filter", { ...buildPayload(), page: next })
      .then((res) => {
        const data = res.data?.data ?? res.data;
        setResult(Array.isArray(data) ? { items: data, total: data.length, page: next, pageSize } : data);
      })
      .catch((err) => setError(err.response?.data?.detail || "Failed to fetch."))
      .finally(() => setLoading(false));
  };

  if (!open) return null;

  const items = result?.items ?? [];
  const total = result?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose}>
      <div
        className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl max-w-6xl w-full max-h-[90vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center">
          <h3 className="text-lg font-semibold text-gray-800 dark:text-white">Custom View Requests</h3>
          <button
            type="button"
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 text-2xl leading-none"
            aria-label="Close"
          >
            &times;
          </button>
        </div>

        <div className="p-6 overflow-y-auto flex-1">
          {/* Filters */}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 mb-6">
            {allowed.includes("studentId") && (
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Student ID</label>
                <input
                  type="text"
                  value={filters.studentId}
                  onChange={(e) => setFilters((f) => ({ ...f, studentId: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                  placeholder="Optional"
                />
              </div>
            )}
            {allowed.includes("name") && (
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Name</label>
                <input
                  type="text"
                  value={filters.name}
                  onChange={(e) => setFilters((f) => ({ ...f, name: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                  placeholder="Optional"
                />
              </div>
            )}
            {allowed.includes("year") && (
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Year</label>
                <input
                  type="number"
                  min="1"
                  value={filters.year}
                  onChange={(e) => setFilters((f) => ({ ...f, year: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                  placeholder="Optional"
                />
              </div>
            )}
            {allowed.includes("course") && (
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Course</label>
                <input
                  type="text"
                  value={filters.course}
                  onChange={(e) => setFilters((f) => ({ ...f, course: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                  placeholder="Optional"
                />
              </div>
            )}
            {allowed.includes("section") && (
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Section</label>
                <input
                  type="text"
                  value={filters.section}
                  onChange={(e) => setFilters((f) => ({ ...f, section: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                  placeholder="Optional"
                />
              </div>
            )}
            {allowed.includes("college") && (
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">College</label>
                <input
                  type="text"
                  value={filters.college}
                  onChange={(e) => setFilters((f) => ({ ...f, college: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                  placeholder="Optional"
                />
              </div>
            )}
            {hasDateFilter && (
              <div className="col-span-2 md:col-span-3 lg:col-span-4">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Date range presets</label>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => setDateRangePreset("today")}
                    className="px-3 py-1.5 rounded-lg text-sm font-medium border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors"
                  >
                    Today
                  </button>
                  <button
                    type="button"
                    onClick={() => setDateRangePreset("lastWeek")}
                    className="px-3 py-1.5 rounded-lg text-sm font-medium border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors"
                  >
                    Last week
                  </button>
                  <button
                    type="button"
                    onClick={() => setDateRangePreset("last15Days")}
                    className="px-3 py-1.5 rounded-lg text-sm font-medium border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors"
                  >
                    Last 15 days
                  </button>
                  <button
                    type="button"
                    onClick={() => setDateRangePreset("past30Days")}
                    className="px-3 py-1.5 rounded-lg text-sm font-medium border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors"
                  >
                    Past 30 days
                  </button>
                </div>
              </div>
            )}
            {allowed.includes("startDate") && (
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Start date</label>
                <input
                  type="date"
                  value={filters.startDate}
                  onChange={(e) => setFilters((f) => ({ ...f, startDate: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                />
              </div>
            )}
            {allowed.includes("endDate") && (
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">End date</label>
                <input
                  type="date"
                  value={filters.endDate}
                  onChange={(e) => setFilters((f) => ({ ...f, endDate: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                />
              </div>
            )}
            {allowed.includes("status") && (
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Status</label>
                <select
                  value={filters.status}
                  onChange={(e) => setFilters((f) => ({ ...f, status: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                >
                  <option value="">All</option>
                  <optgroup label="Quick">
                    {STATUS_OPTIONS.map((o) => (
                      <option key={o.value} value={o.value}>
                        {o.label}
                      </option>
                    ))}
                  </optgroup>
                  <optgroup label="All statuses">
                    {ALL_STATUS_OPTIONS.map((o) => (
                      <option key={o.value} value={o.value}>
                        {o.label}
                      </option>
                    ))}
                  </optgroup>
                </select>
              </div>
            )}
            {hasHodCheckboxes && filterOptions.hods?.length > 0 && (
              <div className="col-span-2 md:col-span-3 lg:col-span-4">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">HODs</label>
                <div className="flex flex-wrap gap-3 p-3 rounded-lg border border-gray-200 dark:border-gray-600 bg-gray-50/50 dark:bg-gray-700/30 max-h-32 overflow-y-auto">
                  {filterOptions.hods.map((h) => (
                    <label key={h.id} className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={filters.hodIds?.includes(h.id) ?? false}
                        onChange={(e) => {
                          const checked = e.target.checked;
                          setFilters((f) => ({
                            ...f,
                            hodIds: checked ? [...(f.hodIds || []), h.id] : (f.hodIds || []).filter((id) => id !== h.id),
                          }));
                        }}
                        className="rounded border-gray-400"
                      />
                      <span className="text-sm text-gray-800 dark:text-gray-200">
                        {h.name} ({h.id})
                      </span>
                    </label>
                  ))}
                </div>
              </div>
            )}
            {hasMentorCheckboxes && filterOptions.mentors?.length > 0 && (
              <div className="col-span-2 md:col-span-3 lg:col-span-4">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Mentors</label>
                <div className="flex flex-wrap gap-3 p-3 rounded-lg border border-gray-200 dark:border-gray-600 bg-gray-50/50 dark:bg-gray-700/30 max-h-32 overflow-y-auto">
                  {filterOptions.mentors.map((m) => (
                    <label key={m.id} className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={filters.mentorIds?.includes(m.id) ?? false}
                        onChange={(e) => {
                          const checked = e.target.checked;
                          setFilters((f) => ({
                            ...f,
                            mentorIds: checked ? [...(f.mentorIds || []), m.id] : (f.mentorIds || []).filter((id) => id !== m.id),
                          }));
                        }}
                        className="rounded border-gray-400"
                      />
                      <span className="text-sm text-gray-800 dark:text-gray-200">
                        {m.name} ({m.id})
                      </span>
                    </label>
                  ))}
                </div>
              </div>
            )}
          </div>

          {error && (
            <div className="mb-4 px-4 py-2 rounded-lg bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 text-sm">
              {error}
            </div>
          )}

          <div className="flex gap-3 mb-6">
            <button
              type="button"
              onClick={handleApply}
              disabled={loading}
              className="px-4 py-2 rounded-lg bg-blue-600 text-white font-medium hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? "Loading…" : "Apply"}
            </button>
            <button
              type="button"
              onClick={handleClear}
              className="px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 font-medium hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              Clear
            </button>
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 font-medium hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              Close
            </button>
          </div>

          {/* Results */}
          {result !== null && (
            <div className="border border-gray-200 dark:border-gray-600 rounded-xl overflow-hidden">
              <div className="px-4 py-2 bg-gray-100 dark:bg-gray-700 text-sm text-gray-700 dark:text-gray-300 flex items-center justify-between gap-2 flex-wrap">
                <span>
                  Total: {total} | Page {result.page ?? page} of {totalPages}
                </span>
                <div className="relative" ref={downloadRef}>
                  <button
                    type="button"
                    onClick={() => setDownloadOpen((v) => !v)}
                    disabled={downloading || (items.length === 0 && total === 0)}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-gray-400 dark:border-gray-500 bg-white dark:bg-gray-600 text-gray-700 dark:text-gray-200 text-sm font-medium hover:bg-gray-50 dark:hover:bg-gray-500 disabled:opacity-50"
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                    </svg>
                    {downloading ? "Downloading…" : "Download"}
                  </button>
                  {downloadOpen && (
                    <div className="absolute right-0 top-full mt-1 py-1 bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg shadow-lg z-10 min-w-[120px]">
                      <button
                        type="button"
                        onClick={() => handleDownload("pdf")}
                        className="w-full px-4 py-2 text-left text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-600"
                      >
                        PDF
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDownload("xlsx")}
                        className="w-full px-4 py-2 text-left text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-600"
                      >
                        XLSX
                      </button>
                    </div>
                  )}
                </div>
              </div>
              <div className="overflow-x-auto max-h-80">
                <table className="min-w-full text-sm text-left text-gray-700 dark:text-gray-200">
                  <thead className="bg-gray-100 dark:bg-gray-700 sticky top-0">
                    <tr>
                      <th className="px-4 py-2">ID</th>
                      <th className="px-4 py-2">Name</th>
                      <th className="px-4 py-2">Course</th>
                      <th className="px-4 py-2">Year</th>
                      <th className="px-4 py-2">Section</th>
                      <th className="px-4 py-2">Reason</th>
                      <th className="px-4 py-2">Status</th>
                      <th className="px-4 py-2">Request time</th>
                    </tr>
                  </thead>
                  <tbody>
                    {items.length === 0 ? (
                      <tr>
                        <td colSpan={8} className="px-4 py-6 text-center text-gray-500">
                          No requests found.
                        </td>
                      </tr>
                    ) : (
                      items.map((r) => (
                        <tr key={r._id} className="border-t border-gray-200 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700/50">
                          <td className="px-4 py-2">{r.student_id}</td>
                          <td className="px-4 py-2">{r.student_name}</td>
                          <td className="px-4 py-2">{r.course}</td>
                          <td className="px-4 py-2">{r.year}</td>
                          <td className="px-4 py-2">{r.section}</td>
                          <td className="px-4 py-2">{r.reason}</td>
                          <td className="px-4 py-2 font-medium">{r.status}</td>
                          <td className="px-4 py-2">{r.request_time ? new Date(r.request_time).toLocaleString() : "—"}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
              {totalPages > 1 && (
                <div className="px-4 py-2 bg-gray-50 dark:bg-gray-700/50 flex justify-between items-center">
                  <button
                    type="button"
                    onClick={() => handlePage(-1)}
                    disabled={page <= 1}
                    className="px-3 py-1 rounded border border-gray-300 dark:border-gray-600 disabled:opacity-50"
                  >
                    Previous
                  </button>
                  <span className="text-sm">
                    Page {page} of {totalPages}
                  </span>
                  <button
                    type="button"
                    onClick={() => handlePage(1)}
                    disabled={page >= totalPages}
                    className="px-3 py-1 rounded border border-gray-300 dark:border-gray-600 disabled:opacity-50"
                  >
                    Next
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
