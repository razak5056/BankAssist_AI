const tokenKey = "bankassist_access_token";

const authPanel = document.querySelector("#auth-panel");
const adminWorkspace = document.querySelector("#admin-workspace");
const loginForm = document.querySelector("#admin-login-form");
const loginSubmit = document.querySelector("#login-submit");
const formMessage = document.querySelector("#form-message");
const logoutButton = document.querySelector("#logout-button");
const avatarButton = document.querySelector("#avatar-button");

function setMessage(message, type = "error") {
  if (!formMessage) return;
  formMessage.textContent = message;
  formMessage.classList.toggle("success", type === "success");
}

function escapeHtml(value) {
  if (!value) return "";
  return String(value).replace(/[&<>"']/g, (character) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[character]);
}

async function readResponse(response) {
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof data.detail === "string"
      ? data.detail
      : Array.isArray(data.detail)
        ? data.detail.map((item) => item.msg).join("; ")
        : "An unexpected error occurred.";
    throw new Error(detail);
  }
  return data;
}

async function loginAdmin(email, password) {
  const body = new URLSearchParams({ username: email, password });
  const response = await fetch("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  const data = await readResponse(response);
  sessionStorage.setItem(tokenKey, data.access_token);
  await initAdminDashboard();
}

async function initAdminDashboard() {
  const token = sessionStorage.getItem(tokenKey) || localStorage.getItem(tokenKey);
  if (!token) {
    showLoggedOut();
    return;
  }

  try {
    const meRes = await fetch("/auth/me", {
      headers: { Authorization: `Bearer ${token}` },
    });
    const user = await readResponse(meRes);

    // Auto-redirect if user signed in with Customer or Support account
    if (user.role === "Customer") {
      window.location.href = "/customer/portal";
      return;
    }
    if (["L1 Support", "L2 Senior Support", "L3 Support Manager"].includes(user.role)) {
      window.location.href = "/support/portal";
      return;
    }
    if (user.role !== "Admin") {
      throw new Error(`Current role '${user.role}' is not authorized for Admin Console.`);
    }

    showLoggedIn(user);
    await Promise.allSettled([
      loadAdminOverview(),
      loadAccounts(),
      loadRoutingConfig(),
      loadAdminEscalationsReport(),
    ]);
  } catch (err) {
    sessionStorage.removeItem(tokenKey);
    showLoggedOut();
    setMessage(err.message || "Admin session expired. Please sign in.");
  }
}

function showLoggedIn(user) {
  if (authPanel) authPanel.classList.add("hidden");
  if (adminWorkspace) adminWorkspace.classList.remove("hidden");
  if (logoutButton) logoutButton.classList.remove("hidden");
  avatarButton.textContent = "A";
}

window.__logout = function() {
  sessionStorage.removeItem(tokenKey);
  localStorage.removeItem(tokenKey);
  window.location.href = "/";
};

function showLoggedOut() {
  window.__logout();
}

async function loadAdminOverview() {
  const token = sessionStorage.getItem(tokenKey);
  if (!token) return;

  const res = await fetch("/admin/overview", {
    headers: { Authorization: `Bearer ${token}` },
  });
  const overview = await readResponse(res);

  document.querySelector("#account-count").textContent = String(overview.account_count ?? 0);
  if (overview.ticket_metrics) {
    document.querySelector("#admin-open-tickets").textContent = String(overview.ticket_metrics.open_tickets ?? 0);
    document.querySelector("#admin-escalation-count").textContent = String(overview.ticket_metrics.escalated_tickets ?? 0);
  }

  const chart = document.querySelector("#role-chart");
  chart.replaceChildren();
  const counts = Object.entries(overview.role_counts || {});
  const maxCount = Math.max(1, ...counts.map(([, count]) => count));

  for (const [role, count] of counts) {
    const row = document.createElement("div");
    row.className = "role-chart-row";
    const label = document.createElement("span");
    label.className = "role-chart-label";
    label.textContent = role;
    const track = document.createElement("div");
    track.className = "role-chart-track";
    const bar = document.createElement("span");
    bar.className = "role-chart-bar";
    bar.style.width = `${Math.max(count > 0 ? 8 : 0, (count / maxCount) * 100)}%`;
    track.append(bar);
    const value = document.createElement("strong");
    value.textContent = String(count);
    row.append(label, track, value);
    chart.append(row);
  }
}

async function loadAccounts() {
  const token = sessionStorage.getItem(tokenKey);
  const tbody = document.querySelector("#accounts-table-body");
  if (!tbody || !token) return;
  tbody.innerHTML = '<tr><td colspan="4" class="empty-table">Loading accounts…</td></tr>';

  try {
    const res = await fetch("/admin/users", {
      headers: { Authorization: `Bearer ${token}` },
    });
    const users = await readResponse(res);
    tbody.replaceChildren();

    if (!users.length) {
      tbody.innerHTML = '<tr><td colspan="4" class="empty-table">No accounts registered yet.</td></tr>';
      return;
    }

    for (const u of users) {
      const row = document.createElement("tr");
      row.innerHTML = `
        <td><strong>${escapeHtml(u.username)}</strong></td>
        <td>${escapeHtml(u.email)}</td>
        <td><span class="ticket-badge-pill" style="background:#f1f5f9;">${escapeHtml(u.role)}</span></td>
        <td><span class="status-pill"><i></i><b>${u.is_active ? "Active" : "Inactive"}</b></span></td>
      `;
      tbody.append(row);
    }
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="4" class="empty-table">${escapeHtml(err.message)}</td></tr>`;
  }
}

async function loadRoutingConfig() {
  const token = sessionStorage.getItem(tokenKey);
  if (!token) return;

  const tbody = document.querySelector("#routing-rules-body");
  try {
    const res = await fetch("/admin/config", {
      headers: { Authorization: `Bearer ${token}` },
    });
    const config = await readResponse(res);

    tbody.replaceChildren();
    for (const rule of config.routing_rules) {
      const row = document.createElement("tr");

      const catCell = document.createElement("td");
      catCell.innerHTML = `<strong>${escapeHtml(rule.category)}</strong>`;

      const tierCell = document.createElement("td");
      const tierSelect = document.createElement("select");
      tierSelect.className = "table-select routing-tier";
      tierSelect.dataset.category = rule.category;
      for (const t of ["L1 Support", "L2 Senior Support", "L3 Support Manager"]) {
        const opt = document.createElement("option");
        opt.value = t;
        opt.textContent = t;
        opt.selected = t === rule.support_tier;
        tierSelect.append(opt);
      }
      tierCell.append(tierSelect);

      const prioCell = document.createElement("td");
      const prioSelect = document.createElement("select");
      prioSelect.className = "table-select routing-priority";
      prioSelect.dataset.category = rule.category;
      for (const p of ["Low", "Normal", "High", "Urgent"]) {
        const opt = document.createElement("option");
        opt.value = p;
        opt.textContent = p;
        opt.selected = p === rule.priority;
        prioSelect.append(opt);
      }
      prioCell.append(prioSelect);

      row.append(catCell, tierCell, prioCell);
      tbody.append(row);
    }

    if (config.sla_targets) {
      if (document.querySelector("#sla-l1")) document.querySelector("#sla-l1").value = config.sla_targets["L1 Support"] || 24;
      if (document.querySelector("#sla-l2")) document.querySelector("#sla-l2").value = config.sla_targets["L2 Senior Support"] || 48;
      if (document.querySelector("#sla-l3")) document.querySelector("#sla-l3").value = config.sla_targets["L3 Support Manager"] || 72;
    }
  } catch (err) {
    if (tbody) tbody.innerHTML = `<tr><td colspan="3" class="empty-table">${escapeHtml(err.message)}</td></tr>`;
  }
}

async function loadAdminEscalationsReport() {
  const token = sessionStorage.getItem(tokenKey);
  const tbody = document.querySelector("#admin-escalations-tbody");
  if (!tbody || !token) return;

  try {
    const res = await fetch("/tickets/support/queue", {
      headers: { Authorization: `Bearer ${token}` },
    });
    const tickets = await readResponse(res);
    tbody.replaceChildren();

    const escalated = tickets.filter((t) => t.status.toLowerCase().includes("escalated") || t.assigned_tier !== "L1 Support");
    if (!escalated.length) {
      tbody.innerHTML = '<tr><td colspan="7" class="empty-table">No escalated disputes currently active. All cases within primary SLA.</td></tr>';
      return;
    }

    for (const t of escalated) {
      const row = document.createElement("tr");
      const slaFormatted = t.sla_deadline ? new Date(t.sla_deadline).toLocaleString() : `${t.sla_hours} hrs`;
      row.innerHTML = `
        <td><strong style="color:#059669;">${escapeHtml(t.ticket_number)}</strong></td>
        <td><span class="ticket-badge-pill" style="background:#f1f5f9;">${escapeHtml(t.category)}</span></td>
        <td>${escapeHtml(t.title)}</td>
        <td><span class="ticket-badge-pill badge-priority-${escapeHtml(t.priority)}">${escapeHtml(t.priority)}</span></td>
        <td>${escapeHtml(t.assigned_tier)}</td>
        <td><span class="ticket-badge-pill badge-status-Escalated">${escapeHtml(t.status)}</span></td>
        <td><small>${escapeHtml(slaFormatted)}</small></td>
      `;
      tbody.append(row);
    }
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="7" class="empty-table">${escapeHtml(err.message)}</td></tr>`;
  }
}

// Event Listeners
if (loginForm) {
  loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const email = document.querySelector("#email")?.value?.trim() || "";
    const password = document.querySelector("#password")?.value || "";
    if (loginSubmit) {
      loginSubmit.disabled = true;
      loginSubmit.textContent = "Signing in…";
    }
    setMessage("");

    try {
      await loginAdmin(email, password);
    } catch (err) {
      setMessage(err.message);
    } finally {
      if (loginSubmit) {
        loginSubmit.disabled = false;
        loginSubmit.innerHTML = 'Sign in as Administrator <span aria-hidden="true">→</span>';
      }
    }
  });
}

logoutButton?.addEventListener("click", (e) => {
  e.preventDefault();
  window.__logout();
});

document.querySelector("#refresh-accounts")?.addEventListener("click", loadAccounts);
document.querySelector("#refresh-admin-reports")?.addEventListener("click", loadAdminEscalationsReport);

// Create Account Handler
document.querySelector("#create-account-form")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.currentTarget;
  if (!form.reportValidity()) return;

  const btn = document.querySelector("#create-account-submit");
  const msg = document.querySelector("#admin-form-message");
  btn.disabled = true;
  btn.textContent = "Creating account…";
  msg.textContent = "";
  msg.classList.remove("success");

  try {
    const res = await fetch("/admin/users", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${sessionStorage.getItem(tokenKey)}`,
      },
      body: JSON.stringify({
        username: document.querySelector("#new-username").value.trim(),
        email: document.querySelector("#new-email").value.trim(),
        password: document.querySelector("#new-password").value,
        role: document.querySelector("#new-role").value,
      }),
    });
    const created = await readResponse(res);
    msg.textContent = `Success: ${created.role} account created for ${created.username}.`;
    msg.classList.add("success");
    form.reset();
    await Promise.allSettled([loadAccounts(), loadAdminOverview()]);
  } catch (err) {
    msg.textContent = err.message;
  } finally {
    btn.disabled = false;
    btn.innerHTML = 'Create Account <span aria-hidden="true">→</span>';
  }
});

// Save Routing Config Handler
document.querySelector("#routing-config-form")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const btn = document.querySelector("#save-routing-config");
  const msg = document.querySelector("#routing-form-message");
  btn.disabled = true;
  btn.textContent = "Saving…";
  msg.textContent = "";
  msg.classList.remove("success");

  const routingRules = [...document.querySelectorAll(".routing-tier")].map((tierSelect) => ({
    category: tierSelect.dataset.category,
    support_tier: tierSelect.value,
    priority: document.querySelector(`.routing-priority[data-category="${tierSelect.dataset.category}"]`).value,
  }));

  try {
    const res = await fetch("/admin/config", {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${sessionStorage.getItem(tokenKey)}`,
      },
      body: JSON.stringify({
        routing_rules: routingRules,
        sla_targets: {
          "L1 Support": Number(document.querySelector("#sla-l1").value),
          "L2 Senior Support": Number(document.querySelector("#sla-l2").value),
          "L3 Support Manager": Number(document.querySelector("#sla-l3").value),
        },
      }),
    });
    await readResponse(res);
    msg.textContent = "Success: Routing matrix and SLA policy successfully saved!";
    msg.classList.add("success");
  } catch (err) {
    msg.textContent = err.message;
  } finally {
    btn.disabled = false;
    btn.innerHTML = 'Save Routing & SLA Policy <span aria-hidden="true">→</span>';
  }
});

// Smooth nav scrolling
document.querySelector("#nav-admin-overview")?.addEventListener("click", (e) => {
  e.preventDefault();
  window.scrollTo({ top: 0, behavior: "smooth" });
});
document.querySelector("#nav-admin-users")?.addEventListener("click", (e) => {
  e.preventDefault();
  document.querySelector("#admin-users")?.scrollIntoView({ behavior: "smooth" });
});
document.querySelector("#nav-admin-routing")?.addEventListener("click", (e) => {
  e.preventDefault();
  document.querySelector("#admin-routing")?.scrollIntoView({ behavior: "smooth" });
});
document.querySelector("#nav-admin-reports")?.addEventListener("click", (e) => {
  e.preventDefault();
  document.querySelector("#admin-reports")?.scrollIntoView({ behavior: "smooth" });
});

// Run session check on load
initAdminDashboard();

