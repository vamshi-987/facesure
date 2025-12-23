import { useEffect, useState } from "react";
import Navbar from "../components/Navbar";
import GetUser from "../components/GetUser";
import RequestsTable from "../components/RequestsTable";
import api from "../services/api";

export default function HODDashboard() {
  const userId = localStorage.getItem("userId");

  const [hod, setHod] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showGetUser, setShowGetUser] = useState(false);

  /* ================= FETCH HOD ================= */
  useEffect(() => {
    const fetchHod = async () => {
      if (!userId) {
        setLoading(false);
        return;
      }
      try {
        const res = await api.get(`/hod/${userId}`);
        setHod(res.data?.data || null);
      } catch (err) {
        console.error("HOD fetch error:", err.response?.data || err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchHod();
  }, [userId]);

  const deptLabel = hod
    ? Array.isArray(hod.courses)
      ? hod.courses.join(", ")
      : hod.courses || hod.college || userId
    : userId;

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-gray-900">
      <Navbar basePath="/hod" />

      <div className="pt-14 px-6">
        {/* HEADER */}
        <div className="text-center mb-8">
          <h2 className="text-3xl font-extrabold text-gray-800 dark:text-white">
            Welcome!
          </h2>
          <p className="text-sm text-gray-500 dark:text-gray-300">
            {loading ? "Loading..." : `HOD of ${deptLabel}`}
          </p>
        </div>

        {/* GET USER BUTTON */}
        <div className="flex justify-center mb-8">
          <button
            onClick={() => setShowGetUser((v) => !v)}
            className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl border px-12 py-6 hover:shadow-2xl transition"
          >
            <div className="text-center">
              <div className="text-blue-600 mb-2">
                <svg
                  className="h-10 w-10 mx-auto"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M15 11a3 3 0 11-6 0 3 3 0 016 0zM5.121 17.804A13.937 13.937 0 0112 15c2.5 0 4.847.66 6.879 1.804"
                  />
                </svg>
              </div>
              <h3 className="text-lg font-bold text-gray-800 dark:text-white">
                Get User Details
              </h3>
            </div>
          </button>
        </div>

        {/* GET USER */}
        {showGetUser && (
          <div className="mb-12">
            <GetUser />
          </div>
        )}

        {/* ✅ REQUESTS TABLE (REUSED COMPONENT) */}
        <RequestsTable
          title="Pending Leave Requests"
          url={`/request/hod/pending/${userId}`}
          mode="HOD"
          hodInfo={{
            id: userId,
            name: hod?.name,
          }}
        />
      </div>
    </div>
  );
}
