import { useState, useEffect, useRef } from "react";
import api from "../services/api";
import Alert from "../components/Alert";

const EMPTY_FORM = {
  id: "",
  name: "",
  phone: "",
  email: "",
  password: "",
  section: "",
  college: "",
  year: "",
  course: "",
  years: [],
  courses: []
};

export default function CreateUser() {
  const [role, setRole] = useState("");
  const [form, setForm] = useState(EMPTY_FORM);
  const [msg, setMsg] = useState("");
  const [alertType, setAlertType] = useState("");

  const alertRef = useRef(null);
  const loggedInUser = localStorage.getItem("userId");
  const loggedInRole = localStorage.getItem("role");

  useEffect(() => {
    setForm(EMPTY_FORM);
  }, [role]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    if (name === "name" || name === "section") {
      setForm((p) => ({ ...p, [name]: value.toUpperCase() }));
    } else {
      setForm((p) => ({ ...p, [name]: value }));
    }
  };

  const handleCheckboxChange = (name, val) => {
    setForm((prev) => {
      const list = prev[name];
      return {
        ...prev,
        [name]: list.includes(val)
          ? list.filter((i) => i !== val)
          : [...list, val]
      };
    });
  };

  const submit = async () => {
    setMsg("");

    try {
      let payload = {
        id: form.id,
        name: form.name,
        phone: form.phone,
        password: form.password,
        college: form.college,
        created_by: loggedInUser
      };

      // STUDENT
      if (role === "STUDENT") {
        payload = {
          ...payload,
          year: parseInt(form.year),
          course: form.course,
          section: form.section
        };
      }

      // FACULTY
      if (role === "FACULTY") {
        payload = {
          ...payload,
          email: form.email,
          years: form.years.map((y) => parseInt(y)),
          courses: form.courses
        };
      }

      const res = await api.post(`/${role.toLowerCase()}/create`, payload);

      setAlertType("success");
      setMsg(res.data.message || `${role} created successfully`);

      setForm(EMPTY_FORM);
      setRole("");
    } catch (err) {
      setAlertType("error");
      setMsg(
        err.response?.data?.detail ||
        err.response?.data?.message ||
        "Invalid data"
      );
    }

    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <div className="max-w-3xl mx-auto p-4">
      <div ref={alertRef}>
        <Alert msg={msg} type={alertType} onClose={() => setMsg("")} />
      </div>

      <div className="bg-white rounded-xl shadow-md p-8">
        <div className="mb-8 bg-gray-500 rounded-lg py-3 text-center text-white">
          <h2 className="text-lg font-semibold uppercase">
            {role ? `Create ${role}` : "Select Role"}
          </h2>
        </div>

        {/* ROLE SELECTION */}
        <div className="mb-8">
          <label className="block mb-2 font-bold">Select Role *</label>
          <div className="flex flex-wrap gap-4">
            {[
              "STUDENT",
              "FACULTY",
              "GUARD",
              ...(loggedInRole === "SUPER_ADMIN" ? ["ADMIN"] : [])
            ].map((r) => (
              <label
                key={r}
                className={`px-4 py-2 rounded-lg border cursor-pointer ${
                  role === r ? "border-blue-600 bg-blue-50" : "bg-gray-50"
                }`}
              >
                <input
                  type="radio"
                  checked={role === r}
                  onChange={() => {
                    setMsg("");
                    setRole(r);
                  }}
                  className="mr-2"
                />
                {r}
              </label>
            ))}
          </div>
        </div>

        {role && (
          <div className="space-y-6">
            {/* COMMON FIELDS */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {["id", "name", "phone", "password"].map((f) => (
                <div key={f}>
                  <label className="text-xs font-bold uppercase">{f}</label>
                  <input
                    type={f === "password" ? "password" : "text"}
                    name={f}
                    value={form[f]}
                    onChange={handleChange}
                    className="w-full p-2 bg-gray-100 rounded"
                  />
                </div>
              ))}

              {role === "FACULTY" && (
                <div>
                  <label className="text-xs font-bold uppercase">email</label>
                  <input
                    name="email"
                    value={form.email}
                    onChange={handleChange}
                    className="w-full p-2 bg-gray-100 rounded"
                  />
                </div>
              )}
            </div>

            {/* COLLEGE */}
            <div>
              <label className="text-xs font-bold uppercase">College *</label>
              <div className="flex gap-6">
                {["KMIT", "NGIT", "KMEC"].map((c) => (
                  <label key={c} className="flex gap-2 items-center">
                    <input
                      type="radio"
                      name="college"
                      value={c}
                      checked={form.college === c}
                      onChange={handleChange}
                    />
                    {c}
                  </label>
                ))}
              </div>
            </div>

            {/* FACULTY EXTRA */}
            {role === "FACULTY" && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-8 bg-blue-50 p-4 rounded">
                <div>
                  <label className="font-bold">Years *</label>
                  {[1, 2, 3, 4].map((y) => (
                    <label key={y} className="block">
                      <input
                        type="checkbox"
                        checked={form.years.includes(String(y))}
                        onChange={() =>
                          handleCheckboxChange("years", String(y))
                        }
                      />{" "}
                      Year {y}
                    </label>
                  ))}
                </div>

                <div>
                  <label className="font-bold">Courses *</label>
                  {["CSE", "CSM", "ECE", "IT"].map((c) => (
                    <label key={c} className="block">
                      <input
                        type="checkbox"
                        checked={form.courses.includes(c)}
                        onChange={() =>
                          handleCheckboxChange("courses", c)
                        }
                      />{" "}
                      {c}
                    </label>
                  ))}
                </div>
              </div>
            )}

            {/* STUDENT EXTRA */}
            {role === "STUDENT" && (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 bg-green-50 p-4 rounded">
                <select name="year" value={form.year} onChange={handleChange}>
                  <option value="">Year</option>
                  {[1, 2, 3, 4].map((y) => (
                    <option key={y}>{y}</option>
                  ))}
                </select>

                <select
                  name="course"
                  value={form.course}
                  onChange={handleChange}
                >
                  <option value="">Course</option>
                  {["CSE", "CSM", "ECE"].map((c) => (
                    <option key={c}>{c}</option>
                  ))}
                </select>

                <input
                  name="section"
                  placeholder="Section"
                  value={form.section}
                  onChange={handleChange}
                />
              </div>
            )}

            <button
              onClick={submit}
              className="w-full py-3 bg-blue-800 text-white font-bold rounded"
            >
              Register {role}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
