import { useRef, useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import api from "../services/api";

export default function RequestsTable({
  url,
  mode = null, // "HOD" | "GUARD" | "MENTOR" | null
  title = "Requests",
  hodInfo = null,
  mentorInfo = null,
}) {
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);

  const [confirmBox, setConfirmBox] = useState({
    open: false,
    action: null, // approve | reject | left
    request: null,
  });

  const [mentorModal, setMentorModal] = useState({
    open: false,
    request: null,
    action: null, // approve | reject
    comment: "",
    parentContacted: false,
  });

  const [toast, setToast] = useState(null);
  const navigate = useNavigate();
  const requestsRef = useRef(null);

  /* ================= FETCH ================= */
  const fetchRequests = async () => {
    try {
      console.log("Fetching from URL:", url);
      const res = await api.get(url);
      console.log("Response data:", res.data);
      setRequests(res.data?.data || []);
    } catch (err) {
      console.error("Fetch failed", err);
      console.error("Error details:", err.response?.data);
      setRequests([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRequests();
  }, [url]);

  /* ================= MENTOR ACTION ================= */
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
      console.error("Action failed", err);
    }
  };

  /* ================= HOD ACTION ================= */
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
      console.error("Action failed", err);
    }
  };

  /* ================= GUARD ACTION ================= */
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
      console.error(err);
    }
  };

  return (
    <>
      {/* ✅ TOAST */}
      {toast && (
        <div className="fixed top-5 right-5 bg-green-600 text-white px-6 py-3 rounded shadow-lg z-50">
          {toast}
        </div>
      )}

      {/* TABLE */}
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
                <td colSpan="10" className="text-center py-10">
                  Loading requests...
                </td>
              </tr>
            ) : requests.length === 0 ? (
              <tr>
                <td colSpan="10" className="text-center py-10">
                  No requests found.
                </td>
              </tr>
            ) : (
              requests.map((r) => {
                const requestId = r._id || r.request_id;
                const isVerified =
                  localStorage.getItem(`face_verified_${requestId}`) === "true";

                return (
                  <tr key={requestId} className="hover:bg-gray-50">
                    <td className="px-4 py-3">{r.student_id}</td>
                    <td className="px-4 py-3">{r.student_name}</td>
                    <td className="px-4 py-3">{r.course}</td>
                    <td className="px-4 py-3">{r.year}</td>
                    <td className="px-4 py-3">{r.section}</td>
                    <td className="px-4 py-3">{r.reason}</td>

                    <td className="px-4 py-3">
                      {r.student_face ? (
                        <img
                          src={`data:image/jpeg;base64,${r.student_face}`}
                          className="w-10 h-10 rounded object-cover"
                        />
                      ) : (
                        "N/A"
                      )}
                    </td>

                    {mode !== "HOD" && mode !== "MENTOR" && (
                    <td className="px-4 py-3 font-semibold">{r.status}</td>
                    )}


                    {/* MENTOR ACTIONS */}
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

                    {/* HOD ACTIONS */}
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

                    {/* GUARD ACTIONS */}
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

      {/* CONFIRM MODAL (HOD + GUARD) */}
      {confirmBox.open && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-md">
            <h2 className="text-xl font-bold mb-3 text-center">
              {confirmBox.action === "approve" && "Confirm Approval"}
              {confirmBox.action === "reject" && "Confirm Rejection"}
              {confirmBox.action === "left" && "Confirm Leave"}
            </h2>

            <p className="text-center mb-4">
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
                className="px-6 py-2 bg-gray-300 rounded"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MENTOR MODAL (WITH COMMENT & PARENT CONTACTED) */}
      {mentorModal.open && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-lg">
            <h2 className="text-xl font-bold mb-4">
              {mentorModal.action === "approve" ? "Approve Request" : "Reject Request"}
            </h2>
            
            <div className="mb-4">
              <p className="text-sm text-gray-600 mb-2">
                <strong>Student:</strong> {mentorModal.request?.student_name} ({mentorModal.request?.student_id})
              </p>
              <p className="text-sm text-gray-600 mb-2">
                <strong>Reason:</strong> {mentorModal.request?.reason}
              </p>
            </div>

            <div className="mb-4">
              <label className="block text-sm font-semibold mb-2">Comment *</label>
              <textarea
                value={mentorModal.comment}
                onChange={(e) =>
                  setMentorModal({ ...mentorModal, comment: e.target.value })
                }
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                rows="3"
                placeholder="Enter your comment..."
              />
            </div>

            {mentorModal.action === "approve" && (
              <div className="mb-6">
                <label className="block text-sm font-semibold mb-2">Parents Contacted?</label>
                <div className="flex gap-4">
                  <label className="flex items-center">
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
                  <label className="flex items-center">
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
                className="px-4 py-2 bg-gray-300 rounded-lg hover:bg-gray-400"
              >
                Cancel
              </button>
              <button
                onClick={handleMentorAction}
                className={`px-4 py-2 text-white rounded-lg ${
                  mentorModal.action === "approve"
                    ? "bg-green-600 hover:bg-green-700"
                    : "bg-red-600 hover:bg-red-700"
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
