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
    parentContacted: false,
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
    const { request, action, comment } = mentorModal;
    if (!request || !action || !mentorInfo) return;

    try {
      await api.post(
        `/request/${request._id || request.request_id}/mentor/${action}`,
        {
          mentor_id: mentorInfo.id,
          mentor_name: mentorInfo.name,
          remark: comment,
          parent_contacted: mentorModal.parentContacted,
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
        parentContacted: false,
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
                      <button
                        onClick={() => openStudentModal(r.student_id)}
                        className="text-blue-600 hover:underline"
                      >
                        {r.student_id}
                      </button>
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
                                parentContacted: false,
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
                                parentContacted: false,
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
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
          onClick={() => setStudentModal({ open: false, loading: false, student: null, history: [] })}
        >
          <div
            className="bg-white dark:bg-gray-800 rounded-xl p-4 w-full max-w-2xl md:max-w-4xl shadow-lg overflow-y-auto max-h-[95vh]"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-2">
              <button
                onClick={() => setStudentModal({ open: false, loading: false, student: null, history: [] })}
                className="flex items-center gap-2 text-gray-600 dark:text-gray-200 hover:text-blue-600 dark:hover:text-blue-400 font-semibold px-3 py-1 rounded focus:outline-none focus:ring-2 focus:ring-blue-400"
                aria-label="Back"
              >
                <span className="text-2xl leading-none">←</span>
                <span className="hidden sm:inline">Back</span>
              </button>
              <h2 className="text-xl font-bold dark:text-white text-center flex-1">Student Details & History</h2>
              <span className="w-16" />
            </div>

            {studentModal.loading ? (
              <div className="py-10 text-center">Loading...</div>
            ) : (
              <div className="flex flex-col md:flex-row gap-6 items-stretch w-full">
                <div className="flex flex-col items-center flex-shrink-0 w-full md:w-56">
                    <img
                      src={
                        studentModal.student?.student_face || studentModal.student?.face_id
                          ? `data:image/jpeg;base64,${studentModal.student?.student_face || studentModal.student?.face_id}`
                          : "https://placehold.co/220x280?text=No+Photo"
                      }
                      alt="Profile"
                      className="w-44 h-60 object-cover rounded-lg border shadow-lg bg-gray-50 max-w-full cursor-zoom-in"
                      style={{ maxWidth: '100%' }}
                      onClick={() => {
                        if (studentModal.student?.student_face || studentModal.student?.face_id) {
                          setImagePreview(`data:image/jpeg;base64,${studentModal.student?.student_face || studentModal.student?.face_id}`);
                        }
                      }}
                    />
                        {/* Enlarged Image Modal */}
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
                                alt="Enlarged Profile"
                                className="rounded-lg shadow-2xl max-h-[80vh] max-w-full border-4 border-white"
                                onClick={e => e.stopPropagation()}
                              />
                            </div>
                          </div>
                        )}
                  <span className="mt-3 px-3 py-1 bg-indigo-100 text-indigo-700 rounded-full text-xs font-bold uppercase whitespace-nowrap">
                    STUDENT
                  </span>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="border-2 border-indigo-300 rounded-lg bg-indigo-50 dark:bg-indigo-900 p-4 md:p-6 shadow-md mb-2 w-full overflow-x-auto">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-2">
                      <div className="truncate">
                        <p className="text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase">Roll Number</p>
                        <p className="text-lg font-bold text-indigo-700 dark:text-indigo-300 font-mono break-all">{studentModal.student?._id || studentModal.student?.id}</p>
                      </div>
                      <div className="truncate">
                        <p className="text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase">Name</p>
                        <p className="text-lg font-bold text-indigo-700 dark:text-indigo-300 break-words">{studentModal.student?.name}</p>
                      </div>
                      <div className="truncate">
                        <p className="text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase">Father Mobile</p>
                        <p className="text-base font-semibold text-indigo-600 dark:text-indigo-400 break-all">
                          {studentModal.student?.father_mobile ? (
                            <a href={`tel:${studentModal.student.father_mobile}`} className="text-blue-600 hover:underline">
                              {studentModal.student.father_mobile}
                            </a>
                          ) : (
                            '—'
                          )}
                        </p>
                      </div>
                      <div className="truncate">
                        <p className="text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase">Mother Mobile</p>
                        <p className="text-base font-semibold text-indigo-600 dark:text-indigo-400 break-all">
                          {studentModal.student?.mother_mobile ? (
                            <a href={`tel:${studentModal.student.mother_mobile}`} className="text-blue-600 hover:underline">
                              {studentModal.student.mother_mobile}
                            </a>
                          ) : (
                            '—'
                          )}
                        </p>
                      </div>
                      <div className="truncate">
                        <p className="text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase">Created By</p>
                        <p className="text-base font-semibold text-indigo-600 dark:text-indigo-400 break-all">{studentModal.student?.created_by || '—'}</p>
                      </div>
                      <div className="truncate">
                        <p className="text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase">Phone</p>
                        <p className="text-base font-semibold text-indigo-600 dark:text-indigo-400 break-all">{studentModal.student?.phone || '—'}</p>
                      </div>
                      <div className="truncate">
                        <p className="text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase">College</p>
                        <p className="text-base font-semibold text-indigo-600 dark:text-indigo-400 break-all">{studentModal.student?.college || '—'}</p>
                      </div>
                      <div className="truncate">
                        <p className="text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase">Course</p>
                        <p className="text-base font-semibold text-indigo-600 dark:text-indigo-400 break-all">{studentModal.student?.course || '—'}</p>
                      </div>
                      <div className="truncate">
                        <p className="text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase">Year / Section</p>
                        <p className="text-base font-semibold text-indigo-600 dark:text-indigo-400 break-all">{studentModal.student?.year} / {studentModal.student?.section}</p>
                      </div>
                    </div>
                  </div>
                  <div className="border rounded-lg overflow-hidden bg-white shadow-sm mb-4">
                    {/* Removed: Father Mobile, Mother Mobile, Created By (now in top grid) */}
                  </div>
                  <div>
                    <h4 className="text-lg font-semibold mb-2 dark:text-white">Request History</h4>
                    <div className="max-h-56 md:max-h-64 overflow-auto rounded border bg-white dark:bg-gray-900 shadow-inner w-full">
                      {(!studentModal.history || studentModal.history.length === 0) ? (
                        <div className="text-sm text-gray-500 p-4">No history found.</div>
                      ) : (
                        <div className="overflow-x-auto w-full">
                          <table className="min-w-full w-full text-sm text-left text-gray-700 dark:text-gray-200">
                            <thead className="bg-gray-100 dark:bg-gray-700 sticky top-0 z-10">
                              <tr>
                                <th className="px-3 py-2">When</th>
                                <th className="px-3 py-2">Reason</th>
                                <th className="px-3 py-2">Status</th>
                                <th className="px-3 py-2">Mentor</th>
                                <th className="px-3 py-2">HOD</th>
                              </tr>
                            </thead>
                            <tbody>
                              {studentModal.history.map((h) => (
                                <tr key={h._id} className="odd:bg-white even:bg-gray-50 dark:even:bg-gray-700">
                                  <td className="px-3 py-2 whitespace-nowrap">{h.request_time ? new Date(h.request_time).toLocaleString() : '—'}</td>
                                  <td className="px-3 py-2 break-words max-w-xs">{h.reason}</td>
                                  <td className="px-3 py-2 font-semibold whitespace-nowrap">{h.status}</td>
                                  <td className="px-3 py-2 break-words max-w-xs">{h.mentor_name || '—'}</td>
                                  <td className="px-3 py-2 break-words max-w-xs">{h.hod_name || '—'}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
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
            {mentorModal.action === "approve" && (
              <div className="mb-6">
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
            <div className="flex justify-end gap-3">
              <button
                onClick={() =>
                  setMentorModal({
                    open: false,
                    request: null,
                    action: null,
                    comment: "",
                    parentContacted: false,
                  })
                }
                className="px-4 py-2 bg-gray-300 dark:bg-gray-600 dark:text-white rounded-lg hover:bg-gray-400"
              >
                Cancel
              </button>
              <button
                onClick={handleMentorAction}
                disabled={
                  (mentorModal.action === "approve" && (!mentorModal.comment.trim() || mentorModal.parentContacted !== true)) ||
                  (mentorModal.action === "reject" && !mentorModal.comment.trim())
                }
                className={`px-4 py-2 text-white rounded-lg ${
                  mentorModal.action === "approve"
                    ? (!mentorModal.comment.trim() || mentorModal.parentContacted !== true
                        ? "bg-green-300 cursor-not-allowed"
                        : "bg-green-600 hover:bg-green-700")
                    : (!mentorModal.comment.trim()
                        ? "bg-red-300 cursor-not-allowed"
                        : "bg-red-600 hover:bg-red-700")
                }`}
              >
                {mentorModal.action === "approve" ? "Approve" : "Reject"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
