const tokenKey = "bankassist_access_token";

const authPanel = document.querySelector("#auth-panel");
const customerWorkspace = document.querySelector("#customer-workspace");
const loginForm = document.querySelector("#customer-login-form");
const loginSubmit = document.querySelector("#login-submit");
const formMessage = document.querySelector("#form-message");
const logoutButton = document.querySelector("#logout-button");
const avatarButton = document.querySelector("#avatar-button");

let pendingEvidenceTicketId = null;

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

function formatSlaInfo(slaHours, deadlineStr, status) {
  const hours = slaHours || 24;
  if (!deadlineStr) {
    return {
      hours,
      deadlineText: `${hours} hours from creation`,
      badgeText: `${hours}h SLA`,
      bg: "#f1f5f9",
      color: "#475569",
      status: "Normal",
    };
  }

  const deadlineDate = new Date(deadlineStr);
  const deadlineText = deadlineDate.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });

  if (status === "Resolved" || status === "Closed") {
    return {
      hours,
      deadlineText,
      badgeText: "✓ Completed",
      bg: "#ecfdf5",
      color: "#059669",
      status: "Resolved",
    };
  }

  const now = new Date();
  const diffMs = deadlineDate.getTime() - now.getTime();
  const diffHours = diffMs / (1000 * 60 * 60);

  if (diffHours < 0) {
    const overdueHours = Math.abs(Math.round(diffHours));
    return {
      hours,
      deadlineText,
      badgeText: `🚨 Breached (${overdueHours}h overdue)`,
      bg: "#fee2e2",
      color: "#991b1b",
      status: "Breached",
    };
  } else if (diffHours <= 4) {
    const remainingMins = Math.max(1, Math.round(diffHours * 60));
    return {
      hours,
      deadlineText,
      badgeText: `⚠️ Critical (${remainingMins}m left)`,
      bg: "#fef3c7",
      color: "#b45309",
      status: "Critical",
    };
  } else if (diffHours <= 12) {
    const remHours = Math.round(diffHours);
    return {
      hours,
      deadlineText,
      badgeText: `⏱️ ${remHours}h left`,
      bg: "#fef9c3",
      color: "#a16207",
      status: "Approaching",
    };
  } else {
    const remHours = Math.round(diffHours);
    return {
      hours,
      deadlineText,
      badgeText: `✓ On Track (${remHours}h left)`,
      bg: "#dcfce7",
      color: "#15803d",
      status: "On Track",
    };
  }
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

async function loginCustomer(email, password) {
  const body = new URLSearchParams({ username: email, password });
  const response = await fetch("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  const data = await readResponse(response);
  sessionStorage.setItem(tokenKey, data.access_token);
  await initCustomerDashboard();
}

async function initCustomerDashboard() {
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

    // Auto-redirect if user signed in with Support or Admin account
    if (["L1 Support", "L2 Senior Support", "L3 Support Manager"].includes(user.role)) {
      window.location.href = "/support/portal";
      return;
    }
    if (user.role === "Admin") {
      window.location.href = "/admin/portal";
      return;
    }

    const dashRes = await fetch("/customer/dashboard", {
      headers: { Authorization: `Bearer ${token}` },
    });
    const dashData = await readResponse(dashRes);

    showLoggedIn(user, dashData);
    await loadCustomerDisputes();
  } catch (err) {
    sessionStorage.removeItem(tokenKey);
    showLoggedOut();
    setMessage("Session expired or unauthorized. Please sign in again.");
  }
}

function showLoggedIn(user, dashData) {
  if (authPanel) authPanel.classList.add("hidden");
  if (customerWorkspace) customerWorkspace.classList.remove("hidden");
  if (logoutButton) logoutButton.classList.remove("hidden");

  const name = user.username || "Customer";
  const initials = name.trim().split(/\s+/).slice(0, 2).map((p) => p[0]).join("").toUpperCase() || "C";

  avatarButton.textContent = initials;
  document.querySelector("#profile-initials").textContent = initials;
  document.querySelector("#customer-display-name").textContent = name;
  document.querySelector("#profile-name").textContent = name;
  document.querySelector("#profile-email").textContent = user.email || "customer@bankassist.ai";
  document.querySelector("#account-status").textContent = dashData.customer?.account_status || "Active";

  const openCount = dashData.summary?.open_tickets || 0;
  document.querySelector("#customer-open-tickets").textContent = String(openCount);
  document.querySelector("#customer-nav-badge").textContent = String(openCount);
  document.querySelector("#customer-ticket-status").textContent = dashData.summary?.ticket_status || "No active disputes";
}

window.__logout = function() {
  sessionStorage.removeItem(tokenKey);
  localStorage.removeItem(tokenKey);
  window.location.href = "/";
};

function showLoggedOut() {
  window.__logout();
}

let customerTickets = [];
let chatHistory = [];

async function loadCustomerDisputes() {
  const token = sessionStorage.getItem(tokenKey);
  if (!token) return;
  const tbody = document.querySelector("#customer-disputes-body");
  if (!tbody) return;

  try {
    const res = await fetch("/tickets/my", {
      headers: { Authorization: `Bearer ${token}` },
    });
    const tickets = await readResponse(res);
    customerTickets = tickets;
    const openCount = tickets.filter((t) => !["Resolved", "Closed"].includes(t.status)).length;
    
    document.querySelector("#customer-nav-badge").textContent = String(openCount);
    document.querySelector("#customer-open-tickets").textContent = String(openCount);

    tbody.replaceChildren();
    if (!tickets.length) {
      tbody.innerHTML = '<tr><td colspan="8" class="empty-table">No support disputes found. Ask the AI Banking Agent above to report an issue.</td></tr>';
      return;
    }

    for (const t of tickets) {
      const row = document.createElement("tr");
      const slaInfo = formatSlaInfo(t.sla_hours, t.sla_deadline, t.status);
      const evidenceHtml = t.evidence_url
        ? `<a href="${escapeHtml(t.evidence_url)}" target="_blank" class="ticket-badge-pill" style="background:#e0f2fe; color:#0369a1; text-decoration:none;">📎 ${escapeHtml(t.evidence_filename || 'Evidence')}</a>`
        : `<button type="button" class="action-btn-sm action-btn-resolve upload-single-evidence-btn" data-ticket-id="${t.id}" data-ticket-num="${escapeHtml(t.ticket_number)}">+ Upload</button>`;

      const deskText = t.assigned_to_name ? `${t.assigned_to_name} (${t.assigned_tier})` : t.assigned_tier;
      const replySnippet = t.resolution_notes
        ? `<span style="color:#15803d; font-weight:600; font-size:11px;" title="${escapeHtml(t.resolution_notes)}">💬 ${escapeHtml(t.resolution_notes.length > 28 ? t.resolution_notes.slice(0, 28) + '…' : t.resolution_notes)}</span>`
        : `<span style="color:#64748b; font-size:11px;">⏳ Awaiting Review</span>`;

      row.innerHTML = `
        <td><strong style="color: #1a4d2e;">${escapeHtml(t.ticket_number)}</strong></td>
        <td>
          <span class="ticket-badge-pill" style="background:#f1f5f9;">${escapeHtml(t.category)}</span>
          <span class="ticket-badge-pill" style="background:#fee2e2; color:#991b1b; font-size:10px; font-weight:700;">${escapeHtml(t.case_type || "Complaint")}</span>
        </td>
        <td><strong>${escapeHtml(t.title)}</strong></td>
        <td><span class="ticket-badge-pill badge-status-${escapeHtml(t.status.replace(/\s+/g, ""))}">${escapeHtml(t.status)}</span></td>
        <td><small style="color:#1e3a8a; font-weight:600;">${escapeHtml(deskText)}</small></td>
        <td>${replySnippet}</td>
        <td>
          <div style="line-height:1.35;">
            <strong style="color:#0f172a; font-size:12px; display:block;">📅 ${escapeHtml(slaInfo.deadlineText)}</strong>
            <div style="display:flex; gap:4px; align-items:center; margin-top:2px; flex-wrap:wrap;">
              <span class="ticket-badge-pill" style="font-size:10px; padding:2px 6px; background:#f1f5f9; color:#334155;">${slaInfo.hours}h SLA</span>
              <span class="ticket-badge-pill" style="font-size:10px; padding:2px 6px; background:${slaInfo.bg}; color:${slaInfo.color}; font-weight:700;">${escapeHtml(slaInfo.badgeText)}</span>
            </div>
          </div>
        </td>
        <td>
          <div style="display:flex; gap:6px; align-items:center;">
            <button type="button" class="action-btn-sm view-cust-ticket-btn" data-ticket-id="${t.id}" style="padding:4px 8px; font-size:11px; background:#eff6ff; color:#1d4ed8; border:1px solid #bfdbfe;">🔍 View Reply</button>
            ${evidenceHtml}
          </div>
        </td>
      `;
      tbody.append(row);
    }
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="8" class="empty-table">${escapeHtml(err.message)}</td></tr>`;
  }
}

function openCustomerTicketModal(ticketId) {
  const t = customerTickets.find((item) => String(item.id) === String(ticketId));
  if (!t) return;

  const modal = document.querySelector("#customer-ticket-modal");
  if (!modal) return;

  document.querySelector("#custmodal-ticket-num").textContent = t.ticket_number;
  document.querySelector("#custmodal-priority-badge").textContent = t.priority;
  document.querySelector("#custmodal-priority-badge").className = `ticket-badge-pill badge-priority-${t.priority}`;
  document.querySelector("#custmodal-status-badge").textContent = t.status;
  document.querySelector("#custmodal-status-badge").className = `ticket-badge-pill badge-status-${t.status.replace(/\s+/g, "")}`;
  document.querySelector("#custmodal-ticket-title").textContent = t.title;

  // Prominently show Official Bank Response / Support Reply
  const replyBox = document.querySelector("#custmodal-reply-box");
  const replyInputSec = document.querySelector("#custmodal-reply-input-section");
  const hiddenId = document.querySelector("#custmodal-hidden-id");
  if (hiddenId) hiddenId.value = t.id;
  const replyInput = document.querySelector("#customer-reply-text");
  if (replyInput) replyInput.value = "";

  if (replyInputSec) {
    replyInputSec.style.display = ["Resolved", "Closed"].includes(t.status) ? "none" : "block";
  }

  if (t.status === "Awaiting Customer Response") {
    replyBox.style.background = "#fffbeb";
    replyBox.style.borderColor = "#fcd34d";
    replyBox.innerHTML = `
      <div style="display:flex; align-items:flex-start; gap:10px;">
        <span style="font-size:24px;">⚠️</span>
        <div style="flex:1;">
          <div style="font-size:11px; font-weight:700; color:#b45309; text-transform:uppercase; margin-bottom:4px;">
            Action Required: More Details Requested by ${escapeHtml(t.assigned_to_name || "Support Executive")} (${escapeHtml(t.assigned_tier)})
          </div>
          <div style="font-size:13.5px; font-weight:600; color:#78350f; white-space:pre-wrap; line-height:1.5;">
            "${escapeHtml(t.resolution_notes || "Please provide additional transaction details or upload a statement so we can investigate.")}"
          </div>
          <div style="margin-top:6px; font-size:11.5px; color:#92400e; font-weight:500;">
            ⬇️ Please type your response or attach documents in the box below to notify the executive.
          </div>
        </div>
      </div>
    `;
  } else if (t.resolution_notes) {
    replyBox.style.background = "#f0fdf4";
    replyBox.style.borderColor = "#86efac";
    replyBox.innerHTML = `
      <div style="display:flex; align-items:flex-start; gap:10px;">
        <span style="font-size:22px;">💬</span>
        <div style="flex:1;">
          <div style="font-size:11px; font-weight:700; color:#15803d; text-transform:uppercase; margin-bottom:4px;">
            Official Bank Response (from ${escapeHtml(t.assigned_to_name || "Support Executive")} · ${escapeHtml(t.assigned_tier)})
          </div>
          <div style="font-size:13.5px; font-weight:500; color:#14532d; white-space:pre-wrap; line-height:1.5;">
            "${escapeHtml(t.resolution_notes)}"
          </div>
        </div>
      </div>
    `;
  } else {
    replyBox.style.background = "#f8fafc";
    replyBox.style.borderColor = "#cbd5e1";
    replyBox.innerHTML = `
      <div style="display:flex; align-items:center; gap:10px; color:#475569;">
        <span style="font-size:20px;">⏳</span>
        <div>
          <strong style="color:#1e293b; font-size:12px; display:block;">Investigation In Progress</strong>
          <span>Your dispute is actively assigned to <b>${escapeHtml(t.assigned_to_name || t.assigned_tier)}</b>. Once the banking support executive investigates and verifies your issue, their official resolution reply will appear right here.</span>
        </div>
      </div>
    `;
  }

  const caseTypeEl = document.querySelector("#custmodal-case-type");
  if (caseTypeEl) caseTypeEl.textContent = t.case_type || "Complaint";
  document.querySelector("#custmodal-category").textContent = t.category;
  document.querySelector("#custmodal-assigned-desk").textContent = `${t.assigned_to_name || "Assigned Specialist"} (${t.assigned_tier})`;
  document.querySelector("#custmodal-tier").textContent = t.assigned_tier;

  const slaInfo = formatSlaInfo(t.sla_hours, t.sla_deadline, t.status);
  const createdFormatted = t.created_at ? new Date(t.created_at).toLocaleString() : "Recently";

  const createdEl = document.querySelector("#custmodal-created");
  if (createdEl) createdEl.textContent = createdFormatted;

  const slaWindowEl = document.querySelector("#custmodal-sla-window");
  if (slaWindowEl) slaWindowEl.textContent = `${slaInfo.hours} Hours (${t.assigned_tier} Resolution SLA)`;

  const deadlineEl = document.querySelector("#custmodal-deadline");
  if (deadlineEl) deadlineEl.textContent = `📅 ${slaInfo.deadlineText}`;

  const slaStatusEl = document.querySelector("#custmodal-sla-status");
  if (slaStatusEl) {
    slaStatusEl.innerHTML = `<span class="ticket-badge-pill" style="background:${slaInfo.bg}; color:${slaInfo.color}; font-weight:700;">${slaInfo.badgeText}</span>`;
  }

  const evidenceEl = document.querySelector("#custmodal-evidence-link");
  if (t.evidence_url) {
    evidenceEl.innerHTML = `<a href="${escapeHtml(t.evidence_url)}" target="_blank" style="color:#0369a1;font-weight:600;text-decoration:underline;">📎 ${escapeHtml(t.evidence_filename || "Attached Evidence")}</a> <small style="color:#64748b;">(stored unverified)</small>`;
  } else {
    evidenceEl.innerHTML = `<span style="color:#64748b;">None attached</span> &bull; <button type="button" class="upload-single-evidence-btn action-btn-sm" data-ticket-id="${t.id}" data-ticket-num="${escapeHtml(t.ticket_number)}" style="padding:2px 8px; font-size:10px; margin-left:4px;">+ Attach File</button>`;
  }

  document.querySelector("#custmodal-description").textContent = t.description || "No complaint text provided.";
  document.querySelector("#custmodal-ai-summary").textContent = t.ai_summary || "Standard banking procedure under regulatory turnaround guidelines.";

  // Populate timeline
  const historyDiv = document.querySelector("#custmodal-history-list");
  historyDiv.replaceChildren();
  if (!t.history || !t.history.length) {
    historyDiv.innerHTML = '<div style="color:#94a3b8;">Dispute registered. Awaiting initial support review.</div>';
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

  modal.classList.remove("hidden");
}

function closeCustomerTicketModal() {
  document.querySelector("#customer-ticket-modal")?.classList.add("hidden");
}

function addSearchBotMessage(text, kind, ticket = null, clarificationOptions = [], caseType = null, category = null) {
  const transcript = document.querySelector("#searchbot-transcript");
  const message = document.createElement("div");
  message.className = `searchbot-message ${kind}`;
  const label = document.createElement("div");
  label.className = "searchbot-message-label";
  label.style.display = "flex";
  label.style.justifyContent = "space-between";
  label.style.alignItems = "center";
  label.style.flexWrap = "wrap";
  label.style.gap = "6px";
  label.style.marginBottom = "4px";

  const senderName = kind === "user" ? "You" : kind === "ai" ? "AI Banking Agent" : "BankAssist Assistant";
  
  if (kind !== "user" && caseType) {
    const caseTypeColors = {
      "Complaint": { bg: "#fee2e2", text: "#991b1b", border: "#fca5a5", icon: "🚨" },
      "Inquiry": { bg: "#e0f2fe", text: "#0369a1", border: "#bae6fd", icon: "ℹ️" },
      "Service Request": { bg: "#fef3c7", text: "#b45309", border: "#fde68a", icon: "🛠️" },
      "Feedback": { bg: "#f3e8ff", text: "#7e22ce", border: "#e9d5ff", icon: "⭐" },
    };
    const cInfo = caseTypeColors[caseType] || { bg: "#f1f5f9", text: "#334155", border: "#cbd5e1", icon: "🏷️" };
    
    label.innerHTML = `
      <span>${senderName}</span>
      <span style="font-size:10px; font-weight:700; background:${cInfo.bg}; color:${cInfo.text}; border:1px solid ${cInfo.border}; padding:2px 8px; border-radius:12px; display:inline-flex; align-items:center; gap:4px; text-transform:uppercase;">
        ${cInfo.icon} Case Type: ${escapeHtml(caseType)}
      </span>
    `;
  } else {
    label.textContent = senderName;
  }

  const content = document.createElement("p");
  content.innerHTML = escapeHtml(text).replace(/\n/g, "<br>");
  message.append(label, content);

  if (ticket) {
    const ticketCard = document.createElement("div");
    ticketCard.className = "ticket-card-chat";
    const slaInfo = formatSlaInfo(ticket.sla_hours, ticket.sla_deadline, ticket.status);
    const createdDate = ticket.created_at ? new Date(ticket.created_at).toLocaleString(undefined, {
      month: "short", day: "numeric", hour: "2-digit", minute: "2-digit"
    }) : "Just now";

    ticketCard.innerHTML = `
      <div class="ticket-card-header">
        <span class="ticket-number-badge">🎫 ${escapeHtml(ticket.ticket_number)}</span>
        <span class="ticket-badge-pill badge-status-${escapeHtml(ticket.status.replace(/\s+/g, ""))}">${escapeHtml(ticket.status)}</span>
      </div>
      <div class="ticket-grid-meta">
        <div><span>CASE TYPE</span><strong style="color:#b91c1c;">${escapeHtml(ticket.case_type || "Complaint")}</strong></div>
        <div><span>CATEGORY</span><strong>${escapeHtml(ticket.category)}</strong></div>
        <div><span>PRIORITY</span><span class="ticket-badge-pill badge-priority-${escapeHtml(ticket.priority)}">${escapeHtml(ticket.priority)}</span></div>
        <div><span>ASSIGNED DESK</span><strong>${escapeHtml(ticket.assigned_to_name || ticket.assigned_tier)}</strong></div>
        <div><span>CREATED AT</span><strong style="font-size:11px;">${escapeHtml(createdDate)}</strong></div>
        <div><span>SLA WINDOW</span><strong style="color:#2563eb;">${slaInfo.hours} Hours</strong></div>
      </div>
      <div style="margin-top:10px; padding:8px 12px; background:#eff6ff; border:1px solid #bfdbfe; border-radius:6px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:6px;">
        <div>
          <span style="font-size:10px; text-transform:uppercase; letter-spacing:0.5px; color:#1e40af; font-weight:700; display:block;">TARGET RESOLUTION DEADLINE</span>
          <strong style="font-size:12px; color:#0f172a;">📅 ${escapeHtml(slaInfo.deadlineText)}</strong>
        </div>
        <span class="ticket-badge-pill" style="background:${slaInfo.bg}; color:${slaInfo.color}; font-weight:700; font-size:11px;">${escapeHtml(slaInfo.badgeText)}</span>
      </div>
    `;
    message.append(ticketCard);
  }

  if (clarificationOptions && clarificationOptions.length) {
    const chipsDiv = document.createElement("div");
    chipsDiv.style.display = "flex";
    chipsDiv.style.flexWrap = "wrap";
    chipsDiv.style.gap = "6px";
    chipsDiv.style.marginTop = "10px";
    for (const opt of clarificationOptions) {
      const btn = document.createElement("button");
      btn.className = "suggestion-chip";
      btn.type = "button";
      btn.textContent = opt;
      btn.addEventListener("click", () => {
        askHelpSearch(opt);
      });
      chipsDiv.append(btn);
    }
    message.append(chipsDiv);
  }

  transcript.append(message);
  transcript.classList.remove("hidden");
  transcript.scrollTop = transcript.scrollHeight;
}

async function askHelpSearch(query) {
  const cleanedQuery = query.trim();
  if (!cleanedQuery) return;

  document.querySelector("#searchbot-welcome").classList.add("hidden");
  document.querySelector("#searchbot-suggestions").classList.add("hidden");
  addSearchBotMessage(cleanedQuery, "user");

  // Record user message in conversational context
  chatHistory.push({ role: "user", content: cleanedQuery });

  const statusLabel = document.querySelector("#searchbot-status-label");
  statusLabel.textContent = "Analyzing query…";

  try {
    const response = await fetch("/assistant/ask", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${sessionStorage.getItem(tokenKey)}`,
      },
      body: JSON.stringify({
        question: cleanedQuery,
        history: chatHistory.slice(-8),
      }),
    });
    const result = await readResponse(response);
    
    // Record assistant reply in conversational context
    chatHistory.push({
      role: "assistant",
      content: result.answer,
      category: result.category,
      intent: result.intent,
      source: result.source,
      case_type: result.case_type,
      ticket_created: result.ticket_created,
    });

    const usesAI = result.mode === "ai" || result.mode === "banking_agent";
    statusLabel.textContent = result.ticket_created ? "Dispute Registered" : usesAI ? "AI Online (Groq)" : "Knowledge Base";
    addSearchBotMessage(result.answer, usesAI ? "ai" : "bot", result.ticket, result.clarification_options, result.case_type, result.category);
    
    if (result.ticket_created) {
      await loadCustomerDisputes();
    }
  } catch (error) {
    statusLabel.textContent = "Unavailable";
    addSearchBotMessage(error.message || "The assistant is unavailable. Please sign in or try again.", "bot");
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
      await loginCustomer(email, password);
    } catch (err) {
      setMessage(err.message);
    } finally {
      if (loginSubmit) {
        loginSubmit.disabled = false;
        loginSubmit.innerHTML = 'Sign in as Customer <span aria-hidden="true">→</span>';
      }
    }
  });
}

logoutButton?.addEventListener("click", (e) => {
  e.preventDefault();
  window.__logout();
});

document.querySelector("#refresh-disputes")?.addEventListener("click", loadCustomerDisputes);

document.querySelector("#searchbot-form").addEventListener("submit", (e) => {
  e.preventDefault();
  const input = document.querySelector("#searchbot-input");
  const submitBtn = e.currentTarget.querySelector("button[type='submit']");
  submitBtn.disabled = true;
  askHelpSearch(input.value).finally(() => {
    submitBtn.disabled = false;
    input.value = "";
    input.focus();
  });
});

document.querySelectorAll(".suggestion-chip").forEach((btn) => {
  btn.addEventListener("click", () => {
    askHelpSearch(btn.dataset.query || btn.textContent);
  });
});

document.querySelectorAll("[data-help-query]").forEach((btn) => {
  btn.addEventListener("click", () => {
    const q = btn.dataset.helpQuery;
    document.querySelector("#ai-agent")?.scrollIntoView({ behavior: "smooth" });
    document.querySelector("#searchbot-input").value = q;
    askHelpSearch(q);
  });
});

document.querySelector("#scroll-to-agent-btn")?.addEventListener("click", () => {
  document.querySelector("#ai-agent")?.scrollIntoView({ behavior: "smooth" });
  document.querySelector("#searchbot-input")?.focus();
});

// View details / support reply button in table
document.addEventListener("click", (e) => {
  const viewBtn = e.target.closest(".view-cust-ticket-btn");
  if (viewBtn) {
    e.preventDefault();
    openCustomerTicketModal(viewBtn.dataset.ticketId);
    return;
  }

  const uploadBtn = e.target.closest(".upload-single-evidence-btn");
  if (uploadBtn) {
    pendingEvidenceTicketId = uploadBtn.dataset.ticketId;
    document.querySelector("#evidence-file-input")?.click();
    return;
  }
});

// Modal close handlers
document.querySelector("#close-customer-ticket-modal")?.addEventListener("click", closeCustomerTicketModal);
document.querySelector("#customer-ticket-modal")?.addEventListener("click", (e) => {
  if (e.target.id === "customer-ticket-modal") {
    closeCustomerTicketModal();
  }
});

// Customer reply form handler (providing requested details to support)
document.querySelector("#customer-reply-form")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const token = sessionStorage.getItem(tokenKey);
  if (!token) return;
  const ticketId = document.querySelector("#custmodal-hidden-id")?.value;
  const text = document.querySelector("#customer-reply-text")?.value?.trim();
  if (!ticketId || !text) return;

  const btn = document.querySelector("#customer-send-reply-btn");
  if (btn) {
    btn.disabled = true;
    btn.textContent = "Sending details…";
  }

  try {
    const res = await fetch(`/tickets/my/${ticketId}/reply`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ message: text }),
    });
    await readResponse(res);
    alert("✓ Your additional details have been delivered to your assigned support desk!");
    closeCustomerTicketModal();
    await loadCustomerDisputes();
  } catch (err) {
    alert("Failed to submit details: " + err.message);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = "Send Details to Support Desk ➔";
    }
  }
});

// Modal attachment trigger
document.querySelector("#custmodal-upload-btn")?.addEventListener("click", () => {
  const ticketId = document.querySelector("#custmodal-hidden-id")?.value;
  if (!ticketId) return;
  pendingEvidenceTicketId = ticketId;
  document.querySelector("#evidence-file-input")?.click();
});

// General evidence upload button in overview
document.querySelector("#trigger-evidence-upload-btn")?.addEventListener("click", async () => {
  const token = sessionStorage.getItem(tokenKey);
  if (!token) return;
  try {
    const res = await fetch("/tickets/my", {
      headers: { Authorization: `Bearer ${token}` },
    });
    const tickets = await readResponse(res);
    const openTickets = tickets.filter((t) => !["Resolved", "Closed"].includes(t.status));
    if (!openTickets.length) {
      alert("You have no open disputes. Ask the AI Banking Agent to report an issue first.");
      return;
    }
    if (openTickets.length === 1) {
      pendingEvidenceTicketId = openTickets[0].id;
    } else {
      const ticketNums = openTickets.map((t, idx) => `${idx + 1}. Ticket #${t.ticket_number} (${t.category}: ${t.title})`).join("\n");
      const choice = prompt(`Select ticket index to attach evidence:\n\n${ticketNums}`, "1");
      if (!choice) return;
      const idx = parseInt(choice, 10) - 1;
      if (isNaN(idx) || idx < 0 || idx >= openTickets.length) {
        alert("Invalid selection.");
        return;
      }
      pendingEvidenceTicketId = openTickets[idx].id;
    }
    document.querySelector("#evidence-file-input")?.click();
  } catch (err) {
    alert("Could not load disputes: " + err.message);
  }
});

// Evidence file input handler
document.querySelector("#evidence-file-input")?.addEventListener("change", async (e) => {
  const file = e.target.files?.[0];
  if (!file || !pendingEvidenceTicketId) return;
  const token = sessionStorage.getItem(tokenKey);
  if (!token) return;

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch(`/tickets/my/${pendingEvidenceTicketId}/evidence`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: formData,
    });
    const updated = await readResponse(res);
    alert(`Evidence document '${file.name}' attached to Ticket #${updated.ticket_number}.\nStatus: Stored unverified for Support Executive investigation.`);
    await loadCustomerDisputes();
  } catch (err) {
    alert("Upload failed: " + err.message);
  } finally {
    e.target.value = "";
    pendingEvidenceTicketId = null;
  }
});

// Smooth scroll nav links
document.querySelector("#nav-overview")?.addEventListener("click", (e) => {
  e.preventDefault();
  window.scrollTo({ top: 0, behavior: "smooth" });
});
document.querySelector("#nav-agent")?.addEventListener("click", (e) => {
  e.preventDefault();
  document.querySelector("#ai-agent")?.scrollIntoView({ behavior: "smooth" });
});
document.querySelector("#nav-disputes")?.addEventListener("click", (e) => {
  e.preventDefault();
  document.querySelector("#my-disputes")?.scrollIntoView({ behavior: "smooth" });
});

// Run session check on load
initCustomerDashboard();

