import { useState, useRef, useEffect } from "react";
import api from "../services/api";

const EMPTY_FORM = {};

export default function UpdateUser() {
  const [role, setRole] = useState("");
  const [searchId, setSearchId] = useState("");
  const [lockedId, setLockedId] = useState(null);

  const [form, setForm] = useState(EMPTY_FORM);
  const [originalForm, setOriginalForm] = useState(EMPTY_FORM);

  const [status, setStatus] = useState("");
  const [success, setSuccess] = useState(false);

  const alertRef = useRef(null);
  const loggedInRole = localStorage.getItem("role");

  useEffect(() => {
    setSearchId("");
    setLockedId(null);
    setForm(EMPTY_FORM);
    setOriginalForm(EMPTY_FORM);
    setStatus("");
    setSuccess(false);
  }, [role]);

  const scrollAlert = () => {
    setTimeout(() => {
      alertRef.current?.scrollIntoView({
        behavior: "smooth",
        block: "center",
      });
    }, 100);
  };

  const fetchUrl = (id) => {
    if (role === "ADMIN") return `/admin/${id}`;
    if (role === "STUDENT") return `/student/${id}`;
    if (role === "FACULTY") return `/faculty/${id}`;
    if (role === "GUARD") return `/guard/${id}`;
  };

  const submitUrl = () => {
    if (role === "STUDENT") return `/student/admin/update/${lockedId}`;
    return `/${role.toLowerCase()}/update/${lockedId}`;
  };

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;

    if (name === "id") {
      setSearchId(value);
      return;
    }

    if (type === "checkbox") {
      const list = form[name] || [];
      setForm({
        ...form,
        [name]: checked
          ? [...list, value]
          : list.filter((v) => v !== value),
      });
      return;
    }

    setForm({ ...form, [name]: value });
  };

  const loadUser = async () => {
    setStatus("");
    setSuccess(false);

    if (!searchId.trim()) {
      setStatus("Please enter User ID");
      scrollAlert();
      return;
    }

    if (loggedInRole === "ADMIN" && role === "ADMIN") {
      setStatus("Admins cannot update other admins");
      scrollAlert();
      return;
    }

    try {
      const res = await api.get(fetchUrl(searchId));
      const data = res.data.data || res.data;

      const resolvedId = data._id || data.id || searchId;

      setLockedId(resolvedId);
      setSearchId(resolvedId);
      setForm(data);
      setOriginalForm(data);

      setSuccess(true);
      setStatus("User loaded successfully");
    } catch {
      setSuccess(false);
      setStatus("User not found");
    }

    scrollAlert();
  };

  const fieldsChanged =
    JSON.stringify(form) !== JSON.stringify(originalForm);

  const idMismatch = lockedId && searchId !== lockedId;

  const adminBlocked =
    loggedInRole === "ADMIN" && role === "ADMIN";

  const canSubmit =
    lockedId && !idMismatch && !adminBlocked && fieldsChanged;

  const submit = async () => {
    setStatus("");
    setSuccess(false);

    if (!canSubmit) {
      setStatus("No changes to update");
      scrollAlert();
      return;
    }

    try {
      const payload = { ...form };
      delete payload.id;
      delete payload._id;
      delete payload.password_hash;
      delete payload.face_id;
      delete payload.created_by;

      if (role === "STUDENT" && payload.year !== undefined && payload.year !== "") {
        payload.year = parseInt(payload.year, 10);
      }

      if (role === "FACULTY" && Array.isArray(payload.years)) {
        payload.years = payload.years.map((y) => parseInt(y, 10));
      }

      await api.put(submitUrl(), payload);

      setOriginalForm(form);
      setSuccess(true);
      setStatus("User updated successfully");
    } catch {
      setSuccess(false);
      setStatus("Update failed");
    }

    scrollAlert();
  };

  return (
    <div className="max-w-3xl mx-auto">
      {status && (
        <div
          ref={alertRef}
          className={`
            mx-auto mb-6
            flex items-center gap-3
            px-6 py-4
            rounded-lg
            border
            shadow-md
            text-base font-semibold
            max-w-xl
            justify-center
            ${
              success
                ? "bg-green-100 text-green-800 border-green-400 dark:bg-green-900/40 dark:text-green-200 dark:border-green-500"
                : "bg-red-100 text-red-800 border-red-400 dark:bg-red-900/40 dark:text-red-200 dark:border-red-500"
            }
          `}
        >
          <span className="text-xl">{success ? "✓" : "⚠️"}</span>
          <span>{status}</span>
        </div>
      )}

      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-md p-8">
        <div className="mb-8 bg-gray-500 rounded-lg py-3 text-center">
          <h2 className="text-lg font-semibold text-white">
            Update User
          </h2>
        </div>

        <div className="mb-6">
          <label className="block mb-2 font-medium dark:text-white">
            Role <span className="text-red-500">*</span>
          </label>
          <select
            value={role}
            onChange={(e) => setRole(e.target.value)}
            className="px-4 py-2 bg-gray-100 dark:bg-gray-700 dark:text-white rounded text-gray-700 w-full"
          >
            <option value="">Select Role</option>
            <option value="STUDENT">Student</option>
            <option value="FACULTY">Faculty</option>
            <option value="GUARD">Guard</option>
            {loggedInRole === "SUPER_ADMIN" && (
              <option value="ADMIN">Admin</option>
            )}
          </select>
        </div>

        <div className="mb-4">
          <label className="block mb-2 font-medium dark:text-white">
            User ID <span className="text-red-500">*</span>
          </label>
          <input
            name="id"
            value={searchId}
            onChange={handleChange}
            className={`px-4 py-2 bg-gray-100 dark:bg-gray-700 dark:text-white rounded w-full ${
              idMismatch ? "border border-red-500" : ""
            }`}
          />
        </div>

        <button
          onClick={loadUser}
          className="px-6 py-2 rounded-lg bg-gray-600 text-white hover:bg-gray-700"
        >
          Find User
        </button>

        {lockedId && (
          <div className="mt-8 space-y-6">
            <div>
              <label className="block mb-2 dark:text-white">Name</label>
              <input
                name="name"
                value={form.name || ""}
                onChange={handleChange}
                className="px-4 py-2 bg-gray-100 dark:bg-gray-700 dark:text-white rounded w-full"
              />
            </div>

            <div>
              <label className="block mb-2 dark:text-white">Phone</label>
              <input
                name="phone"
                value={form.phone || ""}
                onChange={handleChange}
                className="px-4 py-2 bg-gray-100 dark:bg-gray-700 dark:text-white rounded w-full"
              />
            </div>

            {role === "STUDENT" && (
              <>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <label className="block mb-2 dark:text-white">Year</label>
                    <select
                      name="year"
                      value={form.year || ""}
                      onChange={handleChange}
                      className="px-4 py-2 bg-gray-100 dark:bg-gray-700 dark:text-white rounded w-full"
                    >
                      <option value="">Select Year</option>
                      {[1, 2, 3, 4].map((y) => (
                        <option key={y} value={y}>{y}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block mb-2 dark:text-white">Course</label>
                    <select
                      name="course"
                      value={form.course || ""}
                      onChange={handleChange}
                      className="px-4 py-2 bg-gray-100 dark:bg-gray-700 dark:text-white rounded w-full"
                    >
                      <option value="">Select Course</option>
                      {["CSE", "CSM", "ECE", "IT"].map((c) => (
                        <option key={c} value={c}>{c}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block mb-2 dark:text-white">Section</label>
                    <input
                      name="section"
                      value={form.section || ""}
                      onChange={handleChange}
                      className="px-4 py-2 bg-gray-100 dark:bg-gray-700 dark:text-white rounded w-full"
                    />
                  </div>
                </div>

                <div className="bg-yellow-50 dark:bg-yellow-900/20 p-4 rounded-lg">
                  <h4 className="font-semibold mb-3 dark:text-white">Parent Contact Numbers</h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block mb-2 text-sm dark:text-white">Father's Mobile</label>
                      <input
                        name="father_mobile"
                        value={form.father_mobile || ""}
                        onChange={handleChange}
                        placeholder="Father's Mobile Number"
                        className="px-4 py-2 bg-white dark:bg-gray-700 dark:text-white border rounded w-full"
                      />
                    </div>
                    <div>
                      <label className="block mb-2 text-sm dark:text-white">Mother's Mobile</label>
                      <input
                        name="mother_mobile"
                        value={form.mother_mobile || ""}
                        onChange={handleChange}
                        placeholder="Mother's Mobile Number"
                        className="px-4 py-2 bg-white dark:bg-gray-700 dark:text-white border rounded w-full"
                      />
                    </div>
                  </div>
                </div>
              </>
            )}

            {role === "FACULTY" && (
              <>
                <div>
                  <label className="block mb-2 dark:text-white">Email</label>
                  <input
                    name="email"
                    value={form.email || ""}
                    onChange={handleChange}
                    className="px-4 py-2 bg-gray-100 dark:bg-gray-700 dark:text-white rounded w-full"
                  />
                </div>

                <div>
                  <label className="block mb-2 dark:text-white">Courses</label>
                  <div className="flex flex-wrap gap-4 bg-gray-50 dark:bg-gray-700 p-3 rounded">
                    {["CSE", "CSM", "ECE", "IT"].map((c) => (
                      <label key={c} className="flex items-center gap-2 dark:text-white">
                        <input
                          type="checkbox"
                          name="courses"
                          value={c}
                          checked={form.courses?.includes(c) || false}
                          onChange={handleChange}
                        />
                        {c}
                      </label>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="block mb-2 dark:text-white">Years</label>
                  <div className="flex gap-4 bg-gray-50 dark:bg-gray-700 p-3 rounded">
                    {["1", "2", "3", "4"].map((y) => (
                      <label key={y} className="flex items-center gap-2 dark:text-white">
                        <input
                          type="checkbox"
                          name="years"
                          value={y}
                          checked={form.years?.map(String).includes(y) || false}
                          onChange={handleChange}
                        />
                        Year {y}
                      </label>
                    ))}
                  </div>
                </div>
              </>
            )}

            <div>
              <label className="block mb-2 dark:text-white">New Password (leave blank to keep current)</label>
              <input
                type="password"
                name="password"
                value={form.password || ""}
                onChange={handleChange}
                placeholder="Enter new password"
                className="px-4 py-2 bg-gray-100 dark:bg-gray-700 dark:text-white rounded w-full"
              />
            </div>

            <div className="flex justify-end">
              <button
                onClick={submit}
                disabled={!canSubmit}
                className="
                  px-6 py-2
                  rounded-lg
                  bg-blue-800 text-white
                  font-semibold
                  hover:bg-blue-900
                  transition
                  disabled:opacity-50
                "
              >
                Update User
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
