import api from "./api";

export async function loginApi(userId, password) {
  const res = await api.post("/auth/login", { userId, password });
  return res.data;
}
