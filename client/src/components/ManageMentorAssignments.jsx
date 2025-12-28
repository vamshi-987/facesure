import { useEffect, useState } from "react";
import api from "../services/api";

export default function ManageMentorAssignments({ onClose }) {
  const [mentors, setMentors] = useState([]);
  const [mentorAssignments, setMentorAssignments] = useState({});
  const [selectedMentors, setSelectedMentors] = useState([]);
  const [loading, setLoading] = useState(true);

  const [hodProfile, setHodProfile] = useState({
    college: "",
    courses: []
  });

  const [formData, setFormData] = useState({
    college: "",
    course: "",
    year: "",
    section: "A"
  });

  const isHODFaculty = (faculty) => {
        if (!faculty.years || !faculty.courses) return false;

        return faculty.years.some((y) =>
          hodProfile.years?.includes(y)
        ) &&
        faculty.courses.some((c) =>
          hodProfile.courses?.includes(c)
        );
      };

  /* ================= FETCH INITIAL DATA ================= */
  useEffect(() => {
    fetchInitialData();
  }, []);

  const fetchInitialData = async () => {
    try {
      setLoading(true);

      const userId = localStorage.getItem("userId");
      const role = localStorage.getItem("role");

      const pathPrefix =
        role === "HOD" ? "faculty" : role.toLowerCase();


      // 🔹 Fetch HOD
      const hodRes = await api.get(`/${pathPrefix}/${userId}`);
      const hod = hodRes.data?.data;

      setHodProfile(hod);
      setFormData({
        college: hod.college,
        course: "",
        year: "",
        section: "A"
      });

      // 🔹 Fetch faculty
      const facultyRes = await api.get(`/faculty/college/${hod.college}`);
      

      const facultyList = facultyRes.data?.data || [];
      setMentors(facultyList);

      // 🔹 Fetch mentor mappings (existing assignments)
      const mappingRes = await api.get("/mentor-mapping/all");
      const mappings = mappingRes.data?.data || [];

      // Build lookup: mentor_id → assignments[]
      const map = {};
      mappings.forEach((m) => {
        if (!map[m.mentor_id]) map[m.mentor_id] = [];
        map[m.mentor_id].push(
          `${m.course} - Year ${m.year} - Sec ${m.section}`
        );
      });

      setMentorAssignments(map);

    } catch (err) {
      console.error(err);
      alert("Failed to load mentor data");
    } finally {
      setLoading(false);
    }
  };

  /* ================= MENTOR SELECTION ================= */
  const toggleMentorSelection = (mentorId) => {
    if (selectedMentors.includes(mentorId)) {
      setSelectedMentors(selectedMentors.filter((m) => m !== mentorId));
      return;
    }
    if (selectedMentors.length === 2) {
      alert("You must select exactly 2 mentors");
      return;
    }
    setSelectedMentors([...selectedMentors, mentorId]);
  };

  /* ================= SUBMIT ================= */
  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!formData.course || !formData.year || !formData.section) {
      alert("Please fill all fields");
      return;
    }

    if (selectedMentors.length !== 2) {
      alert("Please select exactly 2 mentors");
      return;
    }

    try {
      await api.post("/mentor-mapping/assign", {
        college: formData.college,
        course: formData.course,
        year: Number(formData.year),
        section: formData.section.toUpperCase(),
        mentor_ids: selectedMentors
      });

      alert("✅ Mentors assigned successfully");
      setSelectedMentors([]);
      fetchInitialData(); // refresh assignment info

    } catch (err) {
      alert(err.response?.data?.detail || "Mentor assignment failed");
    }
  };

  if (loading) {
    return <div className="p-6 text-center">Loading...</div>;
  }

  /* ================= UI ================= */
  return (
    <div className="relative bg-white dark:bg-gray-800 rounded-3xl shadow-lg border p-8">

      {/* ❌ CLOSE */}
      <button
        onClick={onClose}
        className="absolute top-4 right-4 text-2xl font-bold text-gray-500 hover:text-red-600"
      >
        ×
      </button>

      <h3 className="text-xl font-extrabold mb-4">
        Mentor Assignment
      </h3>

      <form onSubmit={handleSubmit} className="space-y-6">

        {/* COURSE + YEAR */}
        <div className="grid grid-cols-2 gap-4">
          <select
            value={formData.course}
            onChange={(e) =>
              setFormData({ ...formData, course: e.target.value })
            }
            className="px-4 py-3 rounded-xl border font-semibold"
            required
          >
            <option value="">Select Course</option>
            {hodProfile.courses.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>

          <select
            value={formData.year}
            onChange={(e) =>
              setFormData({ ...formData, year: e.target.value })
            }
            className="px-4 py-3 rounded-xl border font-semibold"
            required
          >
            <option value="">Select Year</option>
            {[1, 2, 3, 4].map((y) => (
              <option key={y} value={y}>Year {y}</option>
            ))}
          </select>
        </div>

        {/* SECTION */}
        <input
          type="text"
          value={formData.section}
          onChange={(e) =>
            setFormData({ ...formData, section: e.target.value.toUpperCase() })
          }
          className="w-full px-4 py-3 rounded-xl border font-semibold"
          placeholder="Section"
          required
        />

        {/* MENTOR LIST */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
  {mentors
    .filter(m => m._id !== hodProfile._id) // ❌ hide self
    .map((m) => {

      const isHOD = isHODFaculty(m);
      const isDisabled = isHOD;

      return (
        <label
          key={m._id}
          className={`flex items-start gap-3 p-3 rounded-xl border cursor-pointer
            ${isDisabled
              ? "bg-gray-200 border-gray-300 cursor-not-allowed opacity-70"
              : selectedMentors.includes(m._id)
              ? "bg-green-100 border-green-400"
              : "bg-gray-50 dark:bg-gray-700"
            }`}
        >
          <input
            type="checkbox"
            disabled={isDisabled}
            checked={selectedMentors.includes(m._id)}
            onChange={() => !isDisabled && toggleMentorSelection(m._id)}
          />

          <div>
            <div className="font-semibold">
              {m.name} ({m._id})
            </div>

            {/* 🟡 Show HOD info */}
            {isDisabled && (
              <div className="text-xs text-red-600 mt-1 font-medium">
                Assigned as HOD for{" "}
                {m.years.join(", ")} – {m.courses.join(", ")}
              </div>
            )}

            {/* 🟢 Mentor assignments */}
            {mentorAssignments[m._id] && !isDisabled && (
              <div className="text-xs text-gray-600 mt-1">
                Assigned as Mentor to:{" "}
                {mentorAssignments[m._id].join(" | ")}
              </div>
            )}
          </div>
        </label>
      );
    })}
</div>

        <button
          type="submit"
          className="w-full py-3 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-bold"
        >
          Assign Mentors
        </button>
      </form>
    </div>
  );
}
