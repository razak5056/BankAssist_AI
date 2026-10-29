const tokenKey = "bankassist_access_token";

const authPanel = document.querySelector("#auth-panel");
const supportWorkspace = document.querySelector("#support-workspace");
const loginForm = document.querySelector("#support-login-form");
const loginSubmit = document.querySelector("#login-submit");
const formMessage = document.querySelector("#form-message");
const logoutButton = document.querySelector("#logout-button");
const avatarButton = document.querySelector("#avatar-button");

let allQueueTickets = [];

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

async function loginSupport(email, password) {
  const body = new URLSearchParams({ username: email, password });
  const response = await fetch("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  const data = await readResponse(response);
  sessionStorage.setItem(tokenKey, data.access_token);
  await initSupportDashboard();
}

async function initSupportDashboard() {
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

    // Auto-redirect if user signed in with Customer or Admin account
    if (user.role === "Customer") {
      window.location.href = "/customer/portal";
      return;
    }
    if (user.role === "Admin") {
      window.location.href = "/admin/portal";
      return;
    }

    const supportEndpoints = {
      "L1 Support": "/support/l1/dashboard",
      "L2 Senior Support": "/support/l2/dashboard",
      "L3 Support Manager": "/support/l3/dashboard",
    };
    const endpoint = supportEndpoints[user.role] || "/support/dashboard";

    const dashRes = await fetch(endpoint, {
      headers: { Authorization: `Bearer ${token}` },
    });
    const dashData = await readResponse(dashRes);

    showLoggedIn(user, dashData);
    await Promise.allSettled([loadSupportQueue(), loadSupportTeam()]);
  } catch (err) {
    sessionStorage.removeItem(tokenKey);
    showLoggedOut();
    setMessage("Support session expired or invalid credentials. Please sign in again.");
  }
}

let currentExecutive = null;

function showLoggedIn(user, dashData) {
  currentExecutive = user;
  if (authPanel) authPanel.classList.add("hidden");
  if (supportWorkspace) supportWorkspace.classList.remove("hidden");
  if (logoutButton) logoutButton.classList.remove("hidden");

  const roleName = user.role || "Support Executive";
  const initials = (user.username || "S").slice(0, 1).toUpperCase();

  avatarButton.textContent = initials;
  document.querySelector("#executive-tier-title").textContent = roleName;
  document.querySelector("#header-tier-chip").textContent = `${roleName.toUpperCase()} WORKSPACE`;
  document.querySelector("#welcome-copy").textContent = `Welcome back, ${escapeHtml(user.username)}. Your workspace is filtered for ${escapeHtml(roleName)} SLA resolution.`;

  const activeDeskEl = document.querySelector("#active-desk-name");
  if (activeDeskEl) activeDeskEl.textContent = `${user.username}`;
  const escDeskEl = document.querySelector("#escalation-active-desk-name");
  if (escDeskEl) escDeskEl.textContent = `${user.username}`;

  const metrics = dashData.metrics || {};
  document.querySelector("#support-assigned-count").textContent = String(metrics.assigned_to_me ?? 0);
  document.querySelector("#support-queue-count").textContent = String(metrics.awaiting_response ?? 0);
  document.querySelector("#support-escalations-count").textContent = String(metrics.escalations ?? 0);
}

window.__logout = function() {
  currentExecutive = null;
  sessionStorage.removeItem(tokenKey);
  localStorage.removeItem(tokenKey);
  window.location.href = "/";
};

function showLoggedOut() {
  window.__logout();
}

async function loadSupportQueue() {
  const token = sessionStorage.getItem(tokenKey);
  if (!token) return;

  const queueTbody = document.querySelector("#support-queue-table-body");
  const escTbody = document.querySelector("#support-escalations-table-body");
  if (queueTbody) queueTbody.innerHTML = '<tr><td colspan="8" class="empty-table">Loading tickets…</td></tr>';

  try {
    const res = await fetch("/tickets/support/queue?desk_only=true", {
      headers: { Authorization: `Bearer ${token}` },
    });
    const tickets = await readResponse(res);
    allQueueTickets = tickets;

    const assignedCount = tickets.filter((t) => !["Resolved", "Closed"].includes(t.status)).length;
    const escCount = tickets.filter((t) => t.status.toLowerCase().includes("escalated")).length;

    document.querySelector("#support-assigned-count").textContent = String(assignedCount);
    document.querySelector("#support-queue-count").textContent = String(tickets.length);
    document.querySelector("#support-escalations-count").textContent = String(escCount);
    document.querySelector("#queue-nav-badge").textContent = String(tickets.length);
    document.querySelector("#escalation-nav-badge").textContent = String(escCount);

    renderQueueTable();
    renderEscalationsTable();
  } catch (err) {
    if (queueTbody) queueTbody.innerHTML = `<tr><td colspan="8" class="empty-table">${escapeHtml(err.message)}</td></tr>`;
  }
}

function renderQueueTable() {
  const tbody = document.querySelector("#support-queue-table-body");
  if (!tbody) return;

  const selectedCategory = document.querySelector("#category-filter")?.value || "ALL";
  let tickets = allQueueTickets;

  if (selectedCategory !== "ALL") {
    tickets = tickets.filter((t) => t.category === selectedCategory);
  }

  tbody.replaceChildren();
  if (!tickets.length) {
    tbody.innerHTML = '<tr><td colspan="8" class="empty-table">No active tickets currently assigned to your desk.</td></tr>';
    return;
  }

  for (const t of tickets) {
    const row = document.createElement("tr");
    const slaFormatted = t.sla_deadline ? new Date(t.sla_deadline).toLocaleString() : `${t.sla_hours} hrs`;
    const canEscalate = !t.status.includes("Resolved") && !t.status.includes("Closed") && t.assigned_tier !== "L3 Support Manager";
    const canResolve = !t.status.includes("Resolved") && !t.status.includes("Closed");

    const evidenceHtml = t.evidence_url
      ? `<a href="${escapeHtml(t.evidence_url)}" target="_blank" class="ticket-badge-pill" style="background:#e0f2fe; color:#0369a1; text-decoration:none;">📎 ${escapeHtml(t.evidence_filename || 'Evidence')}</a>`
      : `<small style="color:#94a3b8;">None</small>`;

    let actionsHtml = `<button class="action-btn-sm" style="background:#f1f5f9;color:#0f172a;border:1px solid #cbd5e1;margin-right:4px;" data-action="investigate" data-id="${t.id}">🔍 Investigate</button> `;
    if (canResolve) {
      actionsHtml += `<button class="action-btn-sm action-btn-resolve" data-action="resolve" data-id="${t.id}">Resolve</button> `;
    }
    if (canEscalate) {
      actionsHtml += `<button class="action-btn-sm action-btn-escalate" data-action="escalate" data-id="${t.id}">Escalate ↗</button>`;
    }
    if (!canResolve && !canEscalate) {
      actionsHtml += `<small style="color:#7d8781;">Completed</small>`;
    }

    row.innerHTML = `
      <td><a href="#" data-action="investigate" data-id="${t.id}" style="color:#1a4d2e;text-decoration:underline;font-weight:700;">${escapeHtml(t.ticket_number)}</a></td>
      <td>${escapeHtml(t.customer_name || "Customer")}</td>
      <td><span class="ticket-badge-pill" style="background:#f1f5f9;">${escapeHtml(t.category)}</span></td>
      <td><span class="ticket-badge-pill badge-priority-${escapeHtml(t.priority)}">${escapeHtml(t.priority)}</span></td>
      <td><span class="ticket-badge-pill badge-status-${escapeHtml(t.status.replace(/\s+/g, ""))}">${escapeHtml(t.status)}</span></td>
      <td><small>${escapeHtml(slaFormatted)}</small></td>
      <td>${evidenceHtml}</td>
      <td>${actionsHtml}</td>
    `;
    tbody.append(row);
  }
}

function renderEscalationsTable() {
  const tbody = document.querySelector("#support-escalations-table-body");
  if (!tbody) return;

  const escalated = allQueueTickets.filter((t) => t.status.toLowerCase().includes("escalated"));
  tbody.replaceChildren();

  if (!escalated.length) {
    tbody.innerHTML = '<tr><td colspan="7" class="empty-table">No escalated tickets in this tier queue.</td></tr>';
    return;
  }

  for (const t of escalated) {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td><a href="#" data-action="investigate" data-id="${t.id}" style="color:#1a4d2e;text-decoration:underline;font-weight:700;">${escapeHtml(t.ticket_number)}</a></td>
      <td>${escapeHtml(t.customer_name || "Customer")}</td>
      <td><span class="ticket-badge-pill" style="background:#f1f5f9;">${escapeHtml(t.category)}</span></td>
      <td><span class="ticket-badge-pill badge-priority-${escapeHtml(t.priority)}">${escapeHtml(t.priority)}</span></td>
      <td><span class="ticket-badge-pill badge-status-Escalated">${escapeHtml(t.status)}</span></td>
      <td>${escapeHtml(t.assigned_to_name || t.assigned_tier)}</td>
      <td>
        <button class="action-btn-sm" style="background:#f1f5f9;color:#0f172a;border:1px solid #cbd5e1;margin-right:4px;" data-action="investigate" data-id="${t.id}">🔍 Investigate</button>
        <button class="action-btn-sm action-btn-resolve" data-action="resolve" data-id="${t.id}">Resolve</button>
      </td>
    `;
    tbody.append(row);
  }
}

async function loadSupportTeam() {
  const token = sessionStorage.getItem(tokenKey);
  if (!token) return;
  const container = document.querySelector("#l1-team-grid");
  if (!container) return;

  try {
    const res = await fetch("/support/team", {
      headers: { Authorization: `Bearer ${token}` },
    });
    const data = await readResponse(res);
    container.replaceChildren();

    const icons = {
      "UPI & Digital Payments": "📱",
      "ATM & Cash Withdrawal": "🏧",
      "Account & Balance": "💳",
      "Account Access & KYC": "🪪",
    };

    for (const exec of data.l1_executives || []) {
      const card = document.createElement("div");
      card.style.background = exec.is_current ? "#eff6ff" : "#fff";
      card.style.border = exec.is_current ? "2px solid #2563eb" : "1px solid #e2e8f0";
      card.style.borderRadius = "8px";
      card.style.padding = "14px";
      card.style.display = "flex";
      card.style.flexDirection = "column";
      card.style.gap = "8px";

      const icon = icons[exec.category] || "🎧";
      const badgeText = exec.is_current ? "Active You" : "Online";
      const badgeBg = exec.is_current ? "#dbeafe" : "#dcfce7";
      const badgeColor = exec.is_current ? "#1d4ed8" : "#15803d";

      card.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:flex-start;">
          <div style="display:flex; align-items:center; gap:8px;">
            <span style="font-size:22px;">${icon}</span>
            <div>
              <strong style="color:#0f172a; font-size:13px; display:block;">${escapeHtml(exec.username)}</strong>
              <small style="color:#64748b; font-size:11px;">L1 Banking Support Desk</small>
            </div>
          </div>
          <span class="ticket-badge-pill" style="background:${badgeBg}; color:${badgeColor}; font-weight:700;">${badgeText}</span>
        </div>
        <div style="font-size:11px; color:#334155; margin-top:2px;">
          <span>Category Desk:</span> <b style="color:#0369a1;">${escapeHtml(exec.category)}</b>
        </div>
        <div style="font-size:11px; color:#475569; display:flex; justify-content:space-between; align-items:center; padding-top:6px; border-top:1px solid #f1f5f9; margin-top:4px;">
          <span>Active Assigned Disputes:</span>
          <strong style="color:#1e3a8a; font-size:13px;">${exec.active_tickets}</strong>
        </div>
        ${exec.is_current ? `
          <div style="text-align:center; font-size:11px; color:#1d4ed8; font-weight:700; margin-top:6px; padding:6px; background:#dbeafe; border-radius:6px;">
            ✓ Currently Signed-In Desk
          </div>
        ` : `
          <div style="text-align:center; font-size:11px; color:#64748b; margin-top:6px; padding:6px; background:#f8fafc; border-radius:6px; border:1px solid #e2e8f0;">
            Sign in with email to access
          </div>
        `}
      `;
      container.append(card);
    }

    // Populate L2 Senior Support / Specialists Grid (HLD: 2 Persons)
    const l2Container = document.querySelector("#l2-team-grid");
    if (l2Container) {
      l2Container.replaceChildren();
      for (const spec of data.l2_specialists || []) {
        const card = document.createElement("div");
        card.style.background = spec.is_current ? "#faf5ff" : "#fff";
        card.style.border = spec.is_current ? "2px solid #9333ea" : "1px solid #e9d5ff";
        card.style.borderRadius = "8px";
        card.style.padding = "14px";
        card.style.display = "flex";
        card.style.flexDirection = "column";
        card.style.gap = "8px";

        const badgeText = spec.is_current ? "Active You" : "Online";
        const badgeBg = spec.is_current ? "#fae8ff" : "#dcfce7";
        const badgeColor = spec.is_current ? "#7e22ce" : "#15803d";
        const icon = spec.role_title === "Senior Support" ? "🎯" : "🌐";

        card.innerHTML = `
          <div style="display:flex; justify-content:space-between; align-items:flex-start;">
            <div style="display:flex; align-items:center; gap:8px;">
              <span style="font-size:22px;">${icon}</span>
              <div>
                <strong style="color:#0f172a; font-size:13px; display:block;">${escapeHtml(spec.username)}</strong>
                <small style="color:#64748b; font-size:11px;">L2 Escalation Desk</small>
              </div>
            </div>
            <span class="ticket-badge-pill" style="background:${badgeBg}; color:${badgeColor}; font-weight:700;">${badgeText}</span>
          </div>
          <div style="font-size:11px; color:#334155; margin-top:2px;">
            <span>HLD Role:</span> <b style="color:#6b21a8;">${escapeHtml(spec.role_title)}</b>
          </div>
          <div style="font-size:11px; color:#475569;">
            <span>Specialization:</span> <b>${escapeHtml(spec.focus)}</b>
          </div>
          <div style="font-size:11px; color:#475569; display:flex; justify-content:space-between; align-items:center; padding-top:6px; border-top:1px solid #f1f5f9; margin-top:4px;">
            <span>Active Escalated Disputes:</span>
            <strong style="color:#6b21a8; font-size:13px;">${spec.active_tickets}</strong>
          </div>
          ${spec.is_current ? `
            <div style="text-align:center; font-size:11px; color:#7e22ce; font-weight:700; margin-top:6px; padding:6px; background:#fae8ff; border-radius:6px;">
              ✓ Currently Signed-In Desk
            </div>
          ` : `
            <div style="text-align:center; font-size:11px; color:#64748b; margin-top:6px; padding:6px; background:#f8fafc; border-radius:6px; border:1px solid #e2e8f0;">
              Sign in with email to access
            </div>
          `}
        `;
        l2Container.append(card);
      }
    }
  } catch (err) {
    container.innerHTML = `<div style="color:#94a3b8; font-size:12px;">Notice: Could not refresh team roster: ${escapeHtml(err.message)}</div>`;
  }
}


function openInvestigationModal(ticketId) {
  const t = allQueueTickets.find((item) => String(item.id) === String(ticketId));
  if (!t) return;

  document.querySelector("#modal-ticket-id").value = t.id;
  document.querySelector("#modal-ticket-num").textContent = t.ticket_number;
  document.querySelector("#modal-priority-badge").textContent = t.priority;
  document.querySelector("#modal-priority-badge").className = `ticket-badge-pill badge-priority-${t.priority}`;
  document.querySelector("#modal-status-badge").textContent = t.status;
  document.querySelector("#modal-status-badge").className = `ticket-badge-pill badge-status-${t.status.replace(/\s+/g, "")}`;
  document.querySelector("#modal-ticket-title").textContent = t.title;

  document.querySelector("#modal-customer-name").textContent = t.customer_name || "Customer";
  document.querySelector("#modal-customer-email").textContent = t.customer_email || "customer@bankassist.ai";
  document.querySelector("#modal-category").textContent = t.category;
  const slaFormatted = t.sla_deadline ? new Date(t.sla_deadline).toLocaleString() : `${t.sla_hours} hrs`;
  document.querySelector("#modal-sla").textContent = slaFormatted;
  document.querySelector("#modal-tier").textContent = `${t.assigned_tier} (${t.assigned_to_name || "Queue"})`;

  const evidenceEl = document.querySelector("#modal-evidence-link");
  if (t.evidence_url) {
    evidenceEl.innerHTML = `<a href="${escapeHtml(t.evidence_url)}" target="_blank" style="color:#0369a1;font-weight:600;text-decoration:underline;">📎 ${escapeHtml(t.evidence_filename || "Attached Evidence")}</a> <small style="color:#64748b;">(unverified)</small>`;
  } else {
    evidenceEl.textContent = "None provided";
  }

  document.querySelector("#modal-description").textContent = t.description || "No description provided.";
  document.querySelector("#modal-ai-summary").textContent = t.ai_summary || "Automated classification and routing applied.";

  // History list
  const historyDiv = document.querySelector("#modal-history-list");
  historyDiv.replaceChildren();
  if (!t.history || !t.history.length) {
    historyDiv.innerHTML = '<div style="color:#94a3b8;">No history events recorded yet.</div>';
  } else {
    for (const h of t.history) {
      const entry = document.createElement("div");
      entry.style.padding = "4px 0";
      entry.style.borderBottom = "1px solid #f1f5f9";
      const timeStr = new Date(h.created_at).toLocaleTimeString();
      entry.innerHTML = `<strong>${escapeHtml(h.action)}</strong> by <span style="color:#0f172a;">${escapeHtml(h.actor_name || "System")}</span> <small style="color:#94a3b8;">(${timeStr})</small>: ${escapeHtml(h.details)}`;
      historyDiv.append(entry);
    }
  }

  // Pre-fill notes if existing
  document.querySelector("#modal-notes-input").value = t.resolution_notes || "";
  if (["In Progress", "Resolved", "Closed"].includes(t.status)) {
    document.querySelector("#modal-status-select").value = t.status;
  }

  // Disable escalate if at L3
  const escBtn = document.querySelector("#modal-escalate-btn");
  if (escBtn) {
    escBtn.style.display = t.assigned_tier === "L3 Support Manager" ? "none" : "inline-block";
  }

  document.querySelector("#investigation-modal").classList.remove("hidden");
}

function closeInvestigationModal() {
  document.querySelector("#investigation-modal")?.classList.add("hidden");
}

async function handleSupportAction(action, ticketId) {
  const token = sessionStorage.getItem(tokenKey);
  if (!token) return;

  if (action === "investigate") {
    openInvestigationModal(ticketId);
    return;
  }

  if (action === "resolve") {
    const notes = prompt("Enter resolution notes for this ticket:", "Dispute verified against NPCI/CBS logs; resolved.");
    if (notes === null) return;
    try {
      const response = await fetch(`/tickets/support/${ticketId}/update`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          status: "Resolved",
          resolution_notes: notes,
          escalate: false,
        }),
      });
      await readResponse(response);
      await loadSupportQueue();
    } catch (err) {
      alert("Error resolving ticket: " + err.message);
    }
  } else if (action === "escalate") {
    const reason = prompt("Enter reason for escalation to next support tier:", "Complex transaction dispute requiring senior specialist review.");
    if (reason === null) return;
    try {
      const response = await fetch(`/tickets/support/${ticketId}/update`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          status: "Escalated",
          escalate: true,
          escalation_reason: reason,
        }),
      });
      await readResponse(response);
      await loadSupportQueue();
    } catch (err) {
      alert("Error escalating ticket: " + err.message);
    }
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
      await loginSupport(email, password);
    } catch (err) {
      setMessage(err.message);
    } finally {
      if (loginSubmit) {
        loginSubmit.disabled = false;
        loginSubmit.innerHTML = 'Sign in as Support Executive <span aria-hidden="true">→</span>';
      }
    }
  });
}

logoutButton?.addEventListener("click", (e) => {
  e.preventDefault();
  window.__logout();
});

document.querySelector("#refresh-support-queue")?.addEventListener("click", loadSupportQueue);
document.querySelector("#refresh-escalations-queue")?.addEventListener("click", loadSupportQueue);
document.querySelector("#category-filter")?.addEventListener("change", renderQueueTable);

document.addEventListener("click", (e) => {
  const btn = e.target.closest("[data-action]");
  if (btn) {
    e.preventDefault();
    const action = btn.dataset.action;
    const ticketId = btn.dataset.id;
    if (action && ticketId) {
      handleSupportAction(action, ticketId);
    }
  }
});

// Modal listeners
document.querySelector("#close-investigation-modal")?.addEventListener("click", closeInvestigationModal);
document.querySelector("#investigation-modal")?.addEventListener("click", (e) => {
  if (e.target.id === "investigation-modal") closeInvestigationModal();
});

document.querySelector("#investigation-action-form")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const token = sessionStorage.getItem(tokenKey);
  if (!token) return;

  const ticketId = document.querySelector("#modal-ticket-id").value;
  const status = document.querySelector("#modal-status-select").value;
  const notes = document.querySelector("#modal-notes-input").value;
  const saveBtn = document.querySelector("#modal-save-btn");
  saveBtn.disabled = true;
  saveBtn.textContent = "Saving…";

  try {
    const res = await fetch(`/tickets/support/${ticketId}/update`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        status: status,
        resolution_notes: notes,
        escalate: false,
      }),
    });
    await readResponse(res);
    closeInvestigationModal();
    await loadSupportQueue();
  } catch (err) {
    alert("Update failed: " + err.message);
  } finally {
    saveBtn.disabled = false;
    saveBtn.textContent = "Save Status Update";
  }
});

document.querySelector("#modal-escalate-btn")?.addEventListener("click", () => {
  const ticketId = document.querySelector("#modal-ticket-id").value;
  if (!ticketId) return;
  closeInvestigationModal();
  handleSupportAction("escalate", ticketId);
});

// Nav smooth scrolling
document.querySelector("#nav-support-overview")?.addEventListener("click", (e) => {
  e.preventDefault();
  window.scrollTo({ top: 0, behavior: "smooth" });
});
document.querySelector("#nav-support-queue")?.addEventListener("click", (e) => {
  e.preventDefault();
  document.querySelector("#support-queue")?.scrollIntoView({ behavior: "smooth" });
});
document.querySelector("#nav-support-escalations")?.addEventListener("click", (e) => {
  e.preventDefault();
  document.querySelector("#support-escalations")?.scrollIntoView({ behavior: "smooth" });
});

// Run session check on load
initSupportDashboard();

