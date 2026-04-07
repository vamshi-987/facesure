import { useRef, useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import api from "../services/api";

export default function RequestsTable({
  url,
  mode = null,
  title = "Requests",
  hodInfo = null,
  mentorInfo = null,
}) {
  const [imagePreview, setImagePreview] = useState(null);
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);

  const [confirmBox, setConfirmBox] = useState({
    open: false,
    action: null,
    request: null,
  });

  const [mentorModal, setMentorModal] = useState({
    open: false,
    request: null,
    action: null,
    comment: "",
    delegateComment: "",
    parentContacted: false,
    approveOnBehalfOfHod: false,
  });

  const [studentModal, setStudentModal] = useState({
    open: false,
    loading: false,
    student: null,
    history: [],
  });

  const [toast, setToast] = useState(null);
  const navigate = useNavigate();
  const requestsRef = useRef(null);

  const fetchRequests = async () => {
    try {
      const res = await api.get(url);
      setRequests(res.data?.data || []);
    } catch (err) {
      console.error("Fetch failed", err);
      setRequests([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRequests();
    
    // Auto-refresh every 5 seconds when in MENTOR or HOD mode to keep status updated
    let interval;
    if (mode === "MENTOR" || mode === "HOD") {
      interval = setInterval(fetchRequests, 5000);
    }
    
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [url, mode]);

  const handleMentorAction = async () => {
    const { request, action, comment, delegateComment, approveOnBehalfOfHod } = mentorModal;
    if (!request || !action || !mentorInfo) return;

    if (action === "approve" && !comment.trim()) {
      setToast("Comment is required.");
      setTimeout(() => setToast(null), 3000);
      return;
    }

    if (action === "approve" && approveOnBehalfOfHod && !delegateComment.trim()) {
      setToast("Please explain why approved on behalf of HOD.");
      setTimeout(() => setToast(null), 3000);
      return;
    }

    try {
      await api.post(
        `/request/${request._id || request.request_id}/mentor/${action}`,
        {
          mentor_id: mentorInfo.id,
          mentor_name: mentorInfo.name,
          remark: comment,
          delegate_comment:
            action === "approve" && approveOnBehalfOfHod
              ? delegateComment
              : null,
          parent_contacted: mentorModal.parentContacted,
          approve_on_behalf_of_hod:
            action === "approve" ? !!approveOnBehalfOfHod : false,
        }
      );

      setToast(
        action === "approve"
          ? "Request Approved Successfully"
          : "Request Rejected Successfully"
      );

      setMentorModal({
        open: false,
        request: null,
        action: null,
        comment: "",
        delegateComment: "",
        parentContacted: false,
        approveOnBehalfOfHod: false,
      });
      fetchRequests();
      setTimeout(() => setToast(null), 2500);
    } catch (err) {
      // Extract meaningful error message from backend
      const errorMessage = err.response?.data?.detail || 
                          err.response?.data?.message ||
                          "Action failed. Please try again.";
      
      setToast(errorMessage);
      console.error("Action failed", err);
      setTimeout(() => setToast(null), 3500);
    }
  };

  const handleConfirmedHodAction = async () => {
    const { request, action } = confirmBox;
    if (!request || !action || !hodInfo) return;

    try {
      await api.post(
        `/request/${request._id || request.request_id}/${action}`,
        {
          hod_id: hodInfo.id,
          hod_name: hodInfo.name,
        }
      );

      setToast(
        action === "approve"
          ? "Request Approved Successfully"
          : "Request Rejected Successfully"
      );

      setConfirmBox({ open: false, action: null, request: null });
      fetchRequests();
      setTimeout(() => setToast(null), 2500);
    } catch (err) {
      // Extract meaningful error message from backend
      const errorMessage = err.response?.data?.detail || 
                          err.response?.data?.message ||
                          "Action failed. Please try again.";
      
      setToast(errorMessage);
      console.error("Action failed", err);
      setTimeout(() => setToast(null), 3500);
    }
  };

  const handleConfirmLeft = async () => {
    const { request } = confirmBox;
    if (!request) return;

    try {
      await api.post(`/request/${request._id || request.request_id}/left`);

      localStorage.removeItem(`face_verified_${request._id || request.request_id}`);

      setToast(`Student ${request.student_name} marked as LEFT CAMPUS`);

      setConfirmBox({ open: false, action: null, request: null });
      fetchRequests();
      setTimeout(() => setToast(null), 2500);
    } catch (err) {
      // Extract meaningful error message from backend
      const errorMessage = err.response?.data?.detail || 
                          err.response?.data?.message ||
                          "Action failed. Please try again.";
      
      setToast(errorMessage);
      console.error("Action failed", err);
      setTimeout(() => setToast(null), 3500);
    }
  };

  const openStudentModal = async (studentId) => {
    setStudentModal({ open: true, loading: true, student: null, history: [] });
    try {
      const [stuRes, histRes] = await Promise.all([
        api.get(`/student/${studentId}`),
        api.get(`/request/student/history/${studentId}`)
      ]);

      const student = stuRes.data?.data || stuRes.data;
      const history = histRes.data?.data || histRes.data;

      setStudentModal({ open: true, loading: false, student, history });
    } catch (err) {
      console.error("Failed to fetch student details", err);
      setToast(err.response?.data?.message || err.message || "Failed to load student details");
      setStudentModal({ open: false, loading: false, student: null, history: [] });
      setTimeout(() => setToast(null), 3500);
    }
  };

  return (
    <>
      {toast && (
        <div className="fixed top-5 right-5 bg-green-600 text-white px-6 py-3 rounded shadow-lg z-50">
          {toast}
        </div>
      )}
      <div
        ref={requestsRef}
        className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl border p-4 overflow-x-auto"
      >
        <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-4">
          {title}
        </h3>

        <table className="min-w-full text-sm text-left text-gray-700 dark:text-gray-200">
          <thead className="bg-gray-100 dark:bg-gray-700">
            <tr>
              <th className="px-4 py-3">ID</th>
              <th className="px-4 py-3">Name</th>
              <th className="px-4 py-3">Course</th>
              <th className="px-4 py-3">Year</th>
              <th className="px-4 py-3">Section</th>
              <th className="px-4 py-3">Reason</th>
              {mode === "MENTOR" && (
                <>
                  <th className="px-4 py-3">Father Mobile</th>
                  <th className="px-4 py-3">Mother Mobile</th>
                </>
              )}
              <th className="px-4 py-3">Face</th>
              {mode !== "HOD" && mode !== "MENTOR" && (
                <th className="px-4 py-3">Status</th>
              )}

              {mode === "HOD" && (
                <>
                  <th className="px-4 py-3">Approve</th>
                  <th className="px-4 py-3">Reject</th>
                </>
              )}

              {mode === "MENTOR" && (
                <>
                  <th className="px-4 py-3">Approve</th>
                  <th className="px-4 py-3">Reject</th>
                </>
              )}

              {mode === "GUARD" && (
                <>
                  <th className="px-4 py-3">Verify</th>
                  <th className="px-4 py-3">Left</th>
                </>
              )}
            </tr>
          </thead>

          <tbody>
            {loading ? (
              <tr>
                <td colSpan="12" className="text-center py-10">
                  Loading requests...
                </td>
              </tr>
            ) : requests.length === 0 ? (
              <tr>
                <td colSpan="12" className="text-center py-10">
                  No requests found.
                </td>
              </tr>
            ) : (
              requests.map((r) => {
                const requestId = r._id || r.request_id;
                const isVerified =
                  localStorage.getItem(`face_verified_${requestId}`) === "true";

                return (
                  <tr key={requestId} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                    <td className="px-4 py-3">
                      {mode === "GUARD" ? (
                        <span className="text-gray-700 dark:text-gray-300">{r.student_id}</span>
                      ) : (
                        <button
                          onClick={() => openStudentModal(r.student_id)}
                          className="text-blue-600 hover:underline"
                        >
                          {r.student_id}
                        </button>
                      )}
                    </td>
                    <td className="px-4 py-3">{r.student_name}</td>
                    <td className="px-4 py-3">{r.course}</td>
                    <td className="px-4 py-3">{r.year}</td>
                    <td className="px-4 py-3">{r.section}</td>
                    <td className="px-4 py-3">{r.reason}</td>

                    {mode === "MENTOR" && (
                      <>
                        <td className="px-4 py-3">
                          {r.father_mobile ? (
                            <a href={`tel:${r.father_mobile}`} className="text-blue-600 hover:underline">
                              {r.father_mobile}
                            </a>
                          ) : (
                            <span className="text-gray-400">N/A</span>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          {r.mother_mobile ? (
                            <a href={`tel:${r.mother_mobile}`} className="text-blue-600 hover:underline">
                              {r.mother_mobile}
                            </a>
                          ) : (
                            <span className="text-gray-400">N/A</span>
                          )}
                        </td>
                      </>
                    )}

                    <td className="px-4 py-3">
                      {r.student_face ? (
                        <img
                          src={`data:image/jpeg;base64,${r.student_face}`}
                          className="w-10 h-10 rounded object-cover cursor-zoom-in"
                          alt="Student"
                          onClick={() => setImagePreview(`data:image/jpeg;base64,${r.student_face}`)}
                        />
                      ) : (
                        "N/A"
                      )}
                          {/* Enlarged Image Modal for requests table */}
                          {imagePreview && (
                            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-80" onClick={() => setImagePreview(null)}>
                              <div className="relative max-w-3xl w-full flex flex-col items-center">
                                <button
                                  className="absolute top-2 right-2 text-white text-3xl font-bold bg-black bg-opacity-40 rounded-full px-3 py-1 hover:bg-opacity-70 focus:outline-none"
                                  onClick={(e) => { e.stopPropagation(); setImagePreview(null); }}
                                  aria-label="Close"
                                >
                                  &times;
                                </button>
                                <img
                                  src={imagePreview}
                                  alt="Enlarged Face"
                                  className="rounded-lg shadow-2xl max-h-[80vh] max-w-full border-4 border-white"
                                  onClick={e => e.stopPropagation()}
                                />
                              </div>
                            </div>
                          )}
                    </td>

                    {mode !== "HOD" && mode !== "MENTOR" && (
                      <td className="px-4 py-3 font-semibold">{r.status}</td>
                    )}

                    {mode === "MENTOR" && (
                      <>
                        <td className="px-4 py-3">
                          <button
                            onClick={() =>
                              setMentorModal({
                                open: true,
                                action: "approve",
                                request: r,
                                comment: "",
                                delegateComment: "",
                                parentContacted: false,
                                approveOnBehalfOfHod: false,
                              })
                            }
                            className="px-3 py-1 rounded text-white bg-green-600 hover:bg-green-700"
                          >
                            Approve
                          </button>
                        </td>

                        <td className="px-4 py-3">
                          <button
                            onClick={() =>
                              setMentorModal({
                                open: true,
                                action: "reject",
                                request: r,
                                comment: "",
                                delegateComment: "",
                                parentContacted: false,
                                approveOnBehalfOfHod: false,
                              })
                            }
                            className="px-3 py-1 rounded text-white bg-red-600 hover:bg-red-700"
                          >
                            Reject
                          </button>
                        </td>
                      </>
                    )}

                    {mode === "HOD" && (
                      <>
                        <td className="px-4 py-3">
                          <button
                            onClick={() =>
                              setConfirmBox({
                                open: true,
                                action: "approve",
                                request: r,
                              })
                            }
                            className="px-3 py-1 rounded text-white bg-green-600 hover:bg-green-700"
                          >
                            Approve
                          </button>
                        </td>

                        <td className="px-4 py-3">
                          <button
                            onClick={() =>
                              setConfirmBox({
                                open: true,
                                action: "reject",
                                request: r,
                              })
                            }
                            className="px-3 py-1 rounded text-white bg-red-600 hover:bg-red-700"
                          >
                            Reject
                          </button>
                        </td>
                      </>
                    )}

                    {mode === "GUARD" && (
                      <>
                        <td className="px-4 py-3">
                          <button
                            onClick={() =>
                              navigate(
                                `/guard/verify-face/${r.student_id}/${requestId}`
                              )
                            }
                            className="px-3 py-1 bg-blue-600 text-white rounded"
                          >
                            Verify
                          </button>
                        </td>

                        <td className="px-4 py-3">
                          <button
                            disabled={!isVerified}
                            onClick={() =>
                              setConfirmBox({
                                open: true,
                                action: "left",
                                request: r,
                              })
                            }
                            className={`px-3 py-1 rounded text-white ${
                              isVerified
                                ? "bg-purple-600 hover:bg-purple-700"
                                : "bg-gray-400 cursor-not-allowed"
                            }`}
                          >
                            Left
                          </button>
                        </td>
                      </>
                    )}
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {confirmBox.open && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-xl p-6 w-full max-w-md">
            <h2 className="text-xl font-bold mb-3 text-center dark:text-white">
              {confirmBox.action === "approve" && "Confirm Approval"}
              {confirmBox.action === "reject" && "Confirm Rejection"}
              {confirmBox.action === "left" && "Confirm Leave"}
            </h2>

            <p className="text-center mb-4 dark:text-gray-300">
              Are you sure you want to{" "}
              <b>{confirmBox.action.toUpperCase()}</b> the request of{" "}
              <span className="font-bold">
                {confirmBox.request.student_name} (
                {confirmBox.request.student_id})
              </span>
              ?
            </p>

            <div className="flex justify-center gap-4">
              <button
                onClick={
                  confirmBox.action === "left"
                    ? handleConfirmLeft
                    : handleConfirmedHodAction
                }
                className="px-6 py-2 bg-green-600 text-white rounded"
              >
                Confirm
              </button>

              <button
                onClick={() =>
                  setConfirmBox({ open: false, action: null, request: null })
                }
                className="px-6 py-2 bg-gray-300 dark:bg-gray-600 dark:text-white rounded"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {studentModal.open && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
          onClick={() => setStudentModal({ open: false, loading: false, student: null, history: [] })}
        >
          <div
            className="bg-white dark:bg-gray-800 rounded-2xl w-full max-w-3xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700 bg-gray-50/80 dark:bg-gray-800/80">
              <button
                onClick={() => setStudentModal({ open: false, loading: false, student: null, history: [] })}
                className="flex items-center gap-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white font-medium px-3 py-2 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
                aria-label="Close"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                </svg>
                <span className="hidden sm:inline">Back</span>
              </button>
              <h2 className="text-lg font-semibold text-gray-800 dark:text-white">Student Details & History</h2>
              <button
                onClick={() => setStudentModal({ open: false, loading: false, student: null, history: [] })}
                className="p-2 rounded-lg text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
                aria-label="Close"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {studentModal.loading ? (
              <div className="flex flex-col items-center justify-center py-16 gap-3">
                <div className="w-10 h-10 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
                <p className="text-sm text-gray-500 dark:text-gray-400">Loading student details…</p>
              </div>
            ) : (
              <div className="overflow-y-auto flex-1">
                <div className="flex flex-col sm:flex-row gap-6 p-6 sm:items-stretch">
                  {/* Profile card - same height as details */}
                  <div className="flex flex-col items-center flex-shrink-0 sm:self-stretch">
                    <div className="relative w-40 sm:w-44 h-[13rem] sm:h-[14rem] rounded-xl border border-gray-200 dark:border-gray-600 shadow-lg bg-gray-100 dark:bg-gray-700 overflow-hidden flex-shrink-0">
                      <img
                        src={
                          studentModal.student?.student_face || studentModal.student?.face_id
                            ? `data:image/jpeg;base64,${studentModal.student?.student_face || studentModal.student?.face_id}`
                            : "https://placehold.co/200x260?text=No+Photo"
                        }
                        alt="Student"
                        className="w-full h-full object-cover cursor-zoom-in transition"
                        onClick={() => {
                          if (studentModal.student?.student_face || studentModal.student?.face_id) {
                            setImagePreview(`data:image/jpeg;base64,${studentModal.student?.student_face || studentModal.student?.face_id}`);
                          }
                        }}
                      />
                      <span className="absolute bottom-2 left-1/2 -translate-x-1/2 px-2.5 py-0.5 bg-indigo-600 text-white text-[10px] font-semibold uppercase tracking-wide rounded-full shadow">
                        Student
                      </span>
                    </div>
                  </div>

                  {/* Details card - same height as image */}
                  <div className="flex-1 min-w-0 flex flex-col min-h-0">
                    <div className="rounded-xl border border-gray-200 dark:border-gray-600 bg-gray-50/50 dark:bg-gray-700/30 p-5 h-[13rem] sm:h-[14rem] overflow-auto">
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div>
                          <p className="text-[11px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-0.5">Roll No</p>
                          <p className="text-base font-semibold text-gray-900 dark:text-white font-mono break-all">{studentModal.student?._id || studentModal.student?.id || '—'}</p>
                        </div>
                        <div>
                          <p className="text-[11px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-0.5">Name</p>
                          <p className="text-base font-semibold text-gray-900 dark:text-white break-words">{studentModal.student?.name || '—'}</p>
                        </div>
                        <div>
                          <p className="text-[11px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-0.5">Father Mobile</p>
                          <p className="text-sm text-gray-800 dark:text-gray-200 break-all">
                            {studentModal.student?.father_mobile ? (
                              <a href={`tel:${studentModal.student.father_mobile}`} className="text-blue-600 dark:text-blue-400 hover:underline">
                                {studentModal.student.father_mobile}
                              </a>
                            ) : '—'}
                          </p>
                        </div>
                        <div>
                          <p className="text-[11px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-0.5">Mother Mobile</p>
                          <p className="text-sm text-gray-800 dark:text-gray-200 break-all">
                            {studentModal.student?.mother_mobile ? (
                              <a href={`tel:${studentModal.student.mother_mobile}`} className="text-blue-600 dark:text-blue-400 hover:underline">
                                {studentModal.student.mother_mobile}
                              </a>
                            ) : '—'}
                          </p>
                        </div>
                        <div>
                          <p className="text-[11px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-0.5">Phone</p>
                          <p className="text-sm text-gray-800 dark:text-gray-200 break-all">{studentModal.student?.phone || '—'}</p>
                        </div>
                        <div>
                          <p className="text-[11px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-0.5">Created By</p>
                          <p className="text-sm text-gray-800 dark:text-gray-200 break-all">{studentModal.student?.created_by || '—'}</p>
                        </div>
                        <div>
                          <p className="text-[11px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-0.5">College</p>
                          <p className="text-sm text-gray-800 dark:text-gray-200 break-all">{studentModal.student?.college || '—'}</p>
                        </div>
                        <div>
                          <p className="text-[11px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-0.5">Course</p>
                          <p className="text-sm text-gray-800 dark:text-gray-200 break-all">{studentModal.student?.course || '—'}</p>
                        </div>
                        <div className="sm:col-span-2">
                          <p className="text-[11px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-0.5">Year / Section</p>
                          <p className="text-sm text-gray-800 dark:text-gray-200">{studentModal.student?.year != null ? `${studentModal.student.year} / ${studentModal.student?.section ?? '—'}` : '—'}</p>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Request history - full width */}
                <div className="w-full px-6 pb-6">
                  <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3 flex items-center gap-2">
                    <span className="w-1 h-4 rounded bg-indigo-500" />
                    Request History
                  </h4>
                  <div className="rounded-xl border border-gray-200 dark:border-gray-600 overflow-hidden bg-white dark:bg-gray-800/50 w-full">
                    {(!studentModal.history || studentModal.history.length === 0) ? (
                      <div className="py-8 text-center text-sm text-gray-500 dark:text-gray-400">No history found.</div>
                    ) : (
                      <div className="max-h-52 overflow-auto">
                        <table className="min-w-full text-sm w-full">
                          <thead className="bg-gray-100 dark:bg-gray-700/80 sticky top-0">
                            <tr>
                              <th className="px-4 py-2.5 text-left text-[11px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">When</th>
                              <th className="px-4 py-2.5 text-left text-[11px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Reason</th>
                              <th className="px-4 py-2.5 text-left text-[11px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Status</th>
                              <th className="px-4 py-2.5 text-left text-[11px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Mentor</th>
                              <th className="px-4 py-2.5 text-left text-[11px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">HOD</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                            {studentModal.history.map((h) => (
                              <tr key={h._id} className="hover:bg-gray-50 dark:hover:bg-gray-700/30 transition-colors">
                                <td className="px-4 py-2.5 text-gray-600 dark:text-gray-400 whitespace-nowrap">{h.request_time ? new Date(h.request_time).toLocaleString() : '—'}</td>
                                <td className="px-4 py-2.5 text-gray-800 dark:text-gray-200 break-words max-w-[180px]">{h.reason}</td>
                                <td className="px-4 py-2.5">
                                  <span className={`inline-flex px-2 py-0.5 rounded-md text-[10px] font-semibold uppercase tracking-wide ${
                                    (h.status === 'APPROVED' || h.status === 'LEFT_CAMPUS') ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300' :
                                    (h.status === 'REJECTED' || h.status === 'REJECTED_BY_MENTOR') ? 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300' :
                                    (h.status === 'PENDING_MENTOR' || h.status === 'PENDING_HOD' || h.status === 'REQUESTED') ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300' :
                                    'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
                                  }`}>
                                    {h.status}
                                  </span>
                                </td>
                                <td className="px-4 py-2.5 text-gray-600 dark:text-gray-400 break-words max-w-[120px]">{h.mentor_name || '—'}</td>
                                <td className="px-4 py-2.5 text-gray-600 dark:text-gray-400 break-words max-w-[220px]">
                                  <div className="space-y-1">
                                    <div>{h.hod_name || '—'}</div>
                                    {h.approve_on_behalf_of_hod && (
                                      <div className="text-xs text-amber-700 dark:text-amber-300">
                                        Approved on behalf of HOD by {h.mentor_name || 'Mentor'}
                                      </div>
                                    )}
                                    {h.delegate_comment && (
                                      <div className="text-xs italic text-gray-500 dark:text-gray-400">
                                        "{h.delegate_comment}"
                                      </div>
                                    )}
                                  </div>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Enlarged image overlay (unchanged behavior) */}
      {imagePreview && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/90 p-4" onClick={() => setImagePreview(null)}>
          <button
            className="absolute top-4 right-4 z-10 p-2 rounded-full bg-white/10 hover:bg-white/20 text-white transition-colors"
            onClick={(e) => { e.stopPropagation(); setImagePreview(null); }}
            aria-label="Close"
          >
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
          </button>
          <img
            src={imagePreview}
            alt="Enlarged profile"
            className="rounded-xl shadow-2xl max-h-[85vh] max-w-full object-contain border-2 border-white/20"
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      )}

      {mentorModal.open && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-xl p-6 w-full max-w-lg">
            <h2 className="text-xl font-bold mb-4 dark:text-white">
              {mentorModal.action === "approve" ? "Approve Request" : "Reject Request"}
            </h2>
            <div className="mb-4">
              <p className="text-sm text-gray-600 dark:text-gray-300 mb-2">
                <strong>Student:</strong> {mentorModal.request?.student_name} ({mentorModal.request?.student_id})
              </p>
              <p className="text-sm text-gray-600 dark:text-gray-300 mb-2">
                <strong>Reason:</strong> {mentorModal.request?.reason}
              </p>
              {mentorModal.request?.father_mobile && (
                <p className="text-sm text-gray-600 dark:text-gray-300 mb-1">
                  <strong>Father:</strong>{" "}
                  <a href={`tel:${mentorModal.request.father_mobile}`} className="text-blue-600 hover:underline">
                    {mentorModal.request.father_mobile}
                  </a>
                </p>
              )}
              {mentorModal.request?.mother_mobile && (
                <p className="text-sm text-gray-600 dark:text-gray-300 mb-1">
                  <strong>Mother:</strong>{" "}
                  <a href={`tel:${mentorModal.request.mother_mobile}`} className="text-blue-600 hover:underline">
                    {mentorModal.request.mother_mobile}
                  </a>
                </p>
              )}
            </div>
            {mentorModal.action === "approve" && (
              <div className="mb-6">
                <div className="mb-4">
                  <label className="block text-sm font-semibold mb-2 dark:text-white">Comment <span className="text-red-500">*</span></label>
                  <textarea
                    value={mentorModal.comment}
                    onChange={(e) =>
                      setMentorModal({ ...mentorModal, comment: e.target.value })
                    }
                    className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white dark:border-gray-600"
                    rows="3"
                    placeholder="Enter your comment..."
                  />
                </div>

                <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 p-3 dark:border-amber-800 dark:bg-amber-900/20">
                  <label className="flex items-center gap-2 text-sm font-semibold dark:text-white">
                    <input
                      type="checkbox"
                      checked={mentorModal.approveOnBehalfOfHod === true}
                      onChange={(e) =>
                        setMentorModal({
                          ...mentorModal,
                          approveOnBehalfOfHod: e.target.checked,
                        })
                      }
                      className="mr-1"
                    />
                    Approve on behalf of HOD (directly to guard)
                  </label>
                  {mentorModal.approveOnBehalfOfHod && (
                    <div className="mt-3">
                      <label className="block text-sm font-semibold mb-2 text-amber-900 dark:text-amber-200">
                        Why approved on behalf of HOD <span className="text-red-500">*</span>
                      </label>
                      <textarea
                        value={mentorModal.delegateComment}
                        onChange={(e) =>
                          setMentorModal({ ...mentorModal, delegateComment: e.target.value })
                        }
                        className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-500 dark:bg-gray-700 dark:text-white dark:border-gray-600"
                        rows="3"
                        placeholder="Enter why this was approved on behalf of HOD..."
                      />
                    </div>
                  )}
                </div>

                <label className="block text-sm font-semibold mb-2 dark:text-white">Parents Contacted?</label>
                <div className="flex gap-4">
                  <label className="flex items-center dark:text-white">
                    <input
                      type="radio"
                      name="parentContacted"
                      checked={mentorModal.parentContacted === true}
                      onChange={() =>
                        setMentorModal({ ...mentorModal, parentContacted: true })
                      }
                      className="mr-2"
                    />
                    Yes
                  </label>
                  <label className="flex items-center dark:text-white">
                    <input
                      type="radio"
                      name="parentContacted"
                      checked={mentorModal.parentContacted === false}
                      onChange={() =>
                        setMentorModal({ ...mentorModal, parentContacted: false })
                      }
                      className="mr-2"
                    />
                    No
                  </label>
                </div>
              </div>
            )}

            {mentorModal.action === "reject" && (
              <div className="mb-4">
                <label className="block text-sm font-semibold mb-2 dark:text-white">Comment <span className="text-red-500">*</span></label>
                <textarea
                  value={mentorModal.comment}
                  onChange={(e) =>
                    setMentorModal({ ...mentorModal, comment: e.target.value })
                  }
                  className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white dark:border-gray-600"
                  rows="3"
                  placeholder="Enter your comment..."
                />
              </div>
            )}

            <div className="flex justify-end gap-3">
              <button
                onClick={() =>
                  setMentorModal({
                    open: false,
                    request: null,
                    action: null,
                    comment: "",
                    delegateComment: "",
                    parentContacted: false,
                    approveOnBehalfOfHod: false,
                  })
                }
                className="px-4 py-2 bg-gray-300 dark:bg-gray-600 dark:text-white rounded-lg hover:bg-gray-400"
              >
                Cancel
              </button>
              <button
                onClick={handleMentorAction}
                disabled={
                  (mentorModal.action === "approve" && (!mentorModal.comment.trim() || (mentorModal.approveOnBehalfOfHod && !mentorModal.delegateComment.trim()) || mentorModal.parentContacted !== true)) ||
                  (mentorModal.action === "reject" && !mentorModal.comment.trim())
                }
                className={`px-4 py-2 text-white rounded-lg ${
                  mentorModal.action === "approve"
                    ? ((!mentorModal.comment.trim() || (mentorModal.approveOnBehalfOfHod && !mentorModal.delegateComment.trim()) || mentorModal.parentContacted !== true)
                        ? "bg-green-300 cursor-not-allowed"
                        : "bg-green-600 hover:bg-green-700")
                    : (!mentorModal.comment.trim()
                        ? "bg-red-300 cursor-not-allowed"
                        : "bg-red-600 hover:bg-red-700")
                }`}
              >
                {mentorModal.action === "approve"
                  ? mentorModal.approveOnBehalfOfHod
                    ? "Approve on behalf of HOD"
                    : "Approve"
                  : "Reject"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
