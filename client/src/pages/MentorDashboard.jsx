import { useEffect, useState } from "react";
import Navbar from "../components/Navbar";
import RequestsTable from "../components/RequestsTable";
import api from "../services/api";

export default function MentorDashboard() {
  const userId = localStorage.getItem("userId");

  const [mentor, setMentor] = useState(null);
  const [loading, setLoading] = useState(true);

  /* ================= FETCH MENTOR ================= */
  useEffect(() => {
    const fetchMentor = async () => {
      if (!userId) {
        setLoading(false);
        return;
      }
      try {
        const res = await api.get(`/faculty/${userId}`);
        setMentor(res.data?.data || null);
      } catch (err) {
        console.error("Mentor fetch error:", err.response?.data || err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchMentor();
  }, [userId]);

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-gray-900">
      <Navbar basePath="/mentor" />

      <div className="pt-14 px-6">
        {/* HEADER */}
        <div className="text-center mb-8">
          <h2 className="text-3xl font-extrabold text-gray-800 dark:text-white">
            Welcome!
          </h2>
          <p className="text-sm text-gray-500 dark:text-gray-300">
            {loading ? "Loading..." : `Mentor${mentor?.name ? ` - ${mentor.name}` : ""}`}
          </p>
        </div>

        {/* ✅ REQUESTS TABLE (REUSED COMPONENT) */}
        <RequestsTable
          title="Today's Pending Student Requests"
          url={`/request/mentor/today/${userId}`}
          mode="MENTOR"
          mentorInfo={{
            id: userId,
            name: mentor?.name,
          }}
        />
      </div>
    </div>
  );
}