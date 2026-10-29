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
      const slaFormatted = t.sla_deadline ? new Date(t.sla_deadline).toLocaleString() : `${t.sla_hours} hrs`;
      const evidenceHtml = t.evidence_url
        ? `<a href="${escapeHtml(t.evidence_url)}" target="_blank" class="ticket-badge-pill" style="background:#e0f2fe; color:#0369a1; text-decoration:none;">📎 ${escapeHtml(t.evidence_filename || 'Evidence')}</a>`
        : `<button type="button" class="action-btn-sm action-btn-resolve upload-single-evidence-btn" data-ticket-id="${t.id}" data-ticket-num="${escapeHtml(t.ticket_number)}">+ Upload</button>`;

      row.innerHTML = `
        <td><strong style="color: #1a4d2e;">${escapeHtml(t.ticket_number)}</strong></td>
        <td><span class="ticket-badge-pill" style="background:#f1f5f9;">${escapeHtml(t.category)}</span></td>
        <td>${escapeHtml(t.title)}</td>
        <td><span class="ticket-badge-pill badge-priority-${escapeHtml(t.priority)}">${escapeHtml(t.priority)}</span></td>
        <td>${escapeHtml(t.assigned_tier)}</td>
        <td><span class="ticket-badge-pill badge-status-${escapeHtml(t.status.replace(/\s+/g, ""))}">${escapeHtml(t.status)}</span></td>
        <td><small>${escapeHtml(slaFormatted)}</small></td>
        <td>${evidenceHtml}</td>
      `;
      tbody.append(row);
    }
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="8" class="empty-table">${escapeHtml(err.message)}</td></tr>`;
  }
}

function addSearchBotMessage(text, kind, ticket = null, clarificationOptions = []) {
  const transcript = document.querySelector("#searchbot-transcript");
  const message = document.createElement("div");
  message.className = `searchbot-message ${kind}`;
  const label = document.createElement("span");
  label.className = "searchbot-message-label";
  label.textContent = kind === "user" ? "You" : kind === "ai" ? "AI Banking Agent" : "BankAssist Assistant";
  const content = document.createElement("p");
  content.innerHTML = escapeHtml(text).replace(/\n/g, "<br>");
  message.append(label, content);

  if (ticket) {
    const ticketCard = document.createElement("div");
    ticketCard.className = "ticket-card-chat";
    const slaDeadline = ticket.sla_deadline ? new Date(ticket.sla_deadline).toLocaleString() : `${ticket.sla_hours || 24} hours`;
    ticketCard.innerHTML = `
      <div class="ticket-card-header">
        <span class="ticket-number-badge">🎫 ${escapeHtml(ticket.ticket_number)}</span>
        <span class="ticket-badge-pill badge-status-${escapeHtml(ticket.status.replace(/\s+/g, ""))}">${escapeHtml(ticket.status)}</span>
      </div>
      <div class="ticket-grid-meta">
        <div><span>CATEGORY</span><strong>${escapeHtml(ticket.category)}</strong></div>
        <div><span>PRIORITY</span><span class="ticket-badge-pill badge-priority-${escapeHtml(ticket.priority)}">${escapeHtml(ticket.priority)}</span></div>
        <div><span>ASSIGNED TIER</span><strong>${escapeHtml(ticket.assigned_tier)}</strong></div>
        <div><span>SLA TARGET</span><strong>${escapeHtml(slaDeadline)}</strong></div>
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

  const statusLabel = document.querySelector("#searchbot-status-label");
  statusLabel.textContent = "Analyzing query…";

  try {
    const response = await fetch("/assistant/ask", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${sessionStorage.getItem(tokenKey)}`,
      },
      body: JSON.stringify({ question: cleanedQuery }),
    });
    const result = await readResponse(response);
    const usesAI = result.mode === "ai" || result.mode === "banking_agent";
    statusLabel.textContent = result.ticket_created ? "Dispute Registered" : usesAI ? "AI Online (Groq)" : "Knowledge Base";
    addSearchBotMessage(result.answer, usesAI ? "ai" : "bot", result.ticket, result.clarification_options);
    
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

// Single evidence upload button in table
document.addEventListener("click", (e) => {
  const btn = e.target.closest(".upload-single-evidence-btn");
  if (!btn) return;
  pendingEvidenceTicketId = btn.dataset.ticketId;
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

