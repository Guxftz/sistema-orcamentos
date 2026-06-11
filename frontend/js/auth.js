function getToken() {
  return localStorage.getItem("token");
}

function getUsername() {
  return localStorage.getItem("username") || "admin";
}

function requireAuth() {
  if (!getToken()) {
    window.location.href = "/index.html";
  }
}

function logout() {
  localStorage.removeItem("token");
  localStorage.removeItem("username");
  window.location.href = "/index.html";
}

async function apiFetch(path, options = {}) {
  const token = getToken();
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(API_URL + path, { ...options, headers });
  if (res.status === 401) {
    logout();
    return null;
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Erro na requisição");
  }
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return res.json();
  return res;
}

function formatBRL(value) {
  const v = parseFloat(value) || 0;
  return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function formatDate(dateStr) {
  if (!dateStr) return "";
  return dateStr;
}

function today() {
  const d = new Date();
  return `${String(d.getDate()).padStart(2,"0")}/${String(d.getMonth()+1).padStart(2,"0")}/${d.getFullYear()}`;
}

function showToast(msg, type = "success") {
  const toastEl = document.getElementById("toast");
  const toastMsg = document.getElementById("toastMsg");
  if (!toastEl) return;
  toastMsg.textContent = msg;
  toastEl.className = `toast align-items-center text-white border-0 show bg-${type === "error" ? "danger" : type === "warning" ? "warning" : "success"}`;
  setTimeout(() => toastEl.classList.remove("show"), 3500);
}

function sidebarActive(page) {
  document.querySelectorAll(".sidebar-link").forEach(el => {
    el.classList.remove("active");
    if (el.dataset.page === page) el.classList.add("active");
  });
}
