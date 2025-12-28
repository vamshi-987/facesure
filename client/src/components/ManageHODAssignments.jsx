import { useEffect, useState } from "react";
import api from "../services/api";

export default function ManageHODAssignments({ onClose }) {
  const [college, setCollege] = useState("");
  const [faculty, setFaculty] = useState([]);
  const [selectedFaculty, setSelectedFaculty] = useState("");
  const [years, setYears] = useState([]);
  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(false);

  /* ================= FETCH FACULTY AFTER COLLEGE ================= */
  const fetchFaculty = async (selectedCollege) => {
    try {
      setLoading(true);
      const res = await api.get(`/faculty/college/${selectedCollege}`);
      setFaculty(res.data?.data || []);
    } catch (e) {
      alert("Failed to load faculty");
    } finally {
      setLoading(false);
    }
  };

  /* ================= HANDLERS ================= */
  const toggleYear = (y) => {
    setYears((p) =>
      p.includes(y) ? p.filter((x) => x !== y) : [...p, y]
    );
  };

  const toggleCourse = (c) => {
    setCourses((p) =>
      p.includes(c) ? p.filter((x) => x !== c) : [...p, c]
    );
  };

  /* ================= SUBMIT ================= */
  const assignHOD = async () => {
    if (!college || !selectedFaculty || years.length === 0 || courses.length === 0) {
      alert("Please select college, faculty, years and courses");
      return;
    }

    try {
      await api.post("/hod/assign", {
        faculty_id: selectedFaculty,
        college,
        years,
        courses
      });

      alert("✅ HOD assigned successfully");

      // reset
      setSelectedFaculty("");
      setYears([]);
      setCourses([]);
    } catch (e) {
      alert(e.response?.data?.detail || "HOD assignment failed");
    }
  };

  /* ================= UI ================= */
  return (
    <div className="relative bg-white dark:bg-gray-800 rounded-3xl shadow-lg border p-8">

      {/* ❌ CLOSE */}
      {onClose && (
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-2xl font-bold"
        >
          ×
        </button>
      )}

      <h3 className="text-xl font-extrabold mb-6">HOD Assignment</h3>

      {/* COLLEGE */}
      <select
        value={college}
        onChange={(e) => {
          setCollege(e.target.value);
          setSelectedFaculty("");
          setFaculty([]);
          fetchFaculty(e.target.value);
        }}
        className="w-full px-4 py-3 rounded-xl border mb-4 font-semibold"
      >
        <option value="">Select College</option>
        {["KMIT", "NGIT", "KMEC"].map((c) => (
          <option key={c} value={c}>{c}</option>
        ))}
      </select>

      {/* FACULTY LIST */}
      {college && (
        <select
          value={selectedFaculty}
          onChange={(e) => setSelectedFaculty(e.target.value)}
          className="w-full px-4 py-3 rounded-xl border mb-6 font-semibold"
        >
          <option value="">Select Faculty</option>
          {faculty.map((f) => (
            <option key={f._id} value={f._id}>
              {f.name} ({f._id})
            </option>
          ))}
        </select>
      )}

      {/* YEARS */}
      <div className="mb-6">
        <p className="font-bold mb-2">Assign Years</p>
        {[1, 2, 3, 4].map((y) => (
          <label key={y} className="block text-sm">
            <input
              type="checkbox"
              checked={years.includes(y)}
              onChange={() => toggleYear(y)}
            />{" "}
            Year {y}
          </label>
        ))}
      </div>

      {/* COURSES */}
      <div className="mb-6">
        <p className="font-bold mb-2">Assign Courses</p>
        {["CSE", "CSM", "ECE", "IT"].map((c) => (
          <label key={c} className="block text-sm">
            <input
              type="checkbox"
              checked={courses.includes(c)}
              onChange={() => toggleCourse(c)}
            />{" "}
            {c}
          </label>
        ))}
      </div>

      <button
        onClick={assignHOD}
        disabled={loading}
        className="w-full py-3 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-bold disabled:opacity-50"
      >
        Assign HOD
      </button>
    </div>
  );
}
