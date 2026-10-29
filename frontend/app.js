const tokenKey = "bankassist_access_token";

const singleLoginForm = document.querySelector("#single-login-form");
const loginEmail = document.querySelector("#login-email");
const loginPassword = document.querySelector("#login-password");
const loginSubmit = document.querySelector("#login-submit-btn");
const formMessage = document.querySelector("#form-message");

function setMessage(msg, isSuccess = false) {
  if (!formMessage) return;
  formMessage.textContent = msg;
  formMessage.className = "form-message";
  if (isSuccess) {
    formMessage.classList.add("success");
    formMessage.style.color = "#15803d";
  } else {
    formMessage.style.color = "#b91c1c";
  }
}

async function readResponse(response) {
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof data.detail === "string"
      ? data.detail
      : Array.isArray(data.detail)
        ? data.detail.map((item) => item.msg).join("; ")
        : "Sign-in failed. Please verify your email and password.";
    throw new Error(detail);
  }
  return data;
}

function getPortalUrlForRole(role) {
  if (role === "Customer") {
    return "/customer/portal";
  }
  if (["L1 Support", "L2 Senior Support", "L3 Support Manager"].includes(role)) {
    return "/support/portal";
  }
  if (role === "Admin") {
    return "/admin/portal";
  }
  return "/customer/portal";
}

if (singleLoginForm) {
  singleLoginForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const email = loginEmail ? loginEmail.value.trim() : "";
    const password = loginPassword ? loginPassword.value : "";

    if (!email || !password) {
      setMessage("Please enter both your email address and password.");
      return;
    }

    if (loginSubmit) {
      loginSubmit.disabled = true;
      loginSubmit.innerHTML = 'Verifying credentials…';
    }
    setMessage("");

    try {
      const body = new URLSearchParams({ username: email, password });
      const res = await fetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body,
      });
      const data = await readResponse(res);
      
      // Store token in both session and local storage
      sessionStorage.setItem(tokenKey, data.access_token);
      localStorage.setItem(tokenKey, data.access_token);

      const role = data.user?.role || "Customer";
      const targetPortal = getPortalUrlForRole(role);
      
      setMessage(`✓ Signed in as ${data.user?.username || email} (${role}). Redirecting…`, true);

      setTimeout(() => {
        window.location.href = targetPortal;
      }, 400);
    } catch (err) {
      setMessage(err.message || "Invalid email or password. Please try again.");
      if (loginSubmit) {
        loginSubmit.disabled = false;
        loginSubmit.innerHTML = 'Sign in securely <span aria-hidden="true">→</span>';
      }
    }
  });
}

// Check existing session on load
(async function checkExistingSession() {
  const token = sessionStorage.getItem(tokenKey) || localStorage.getItem(tokenKey);
  if (!token) return;
  try {
    const res = await fetch("/auth/me", {
      headers: { Authorization: `Bearer ${token}` },
    });
    const user = await readResponse(res);
    const role = user.role || "Customer";
    const targetUrl = getPortalUrlForRole(role);

    if (formMessage) {
      formMessage.className = "form-message success";
      formMessage.style.color = "#15803d";
      formMessage.innerHTML = `Active session: <b>${user.username}</b> (${role}). <a href="${targetUrl}" style="color:#176f51; font-weight:700; text-decoration:underline; margin: 0 6px;">Go to Dashboard →</a> | <button type="button" id="landing-signout-btn" style="background:none; border:none; color:#dc2626; text-decoration:underline; cursor:pointer; font-weight:700; margin-left:6px; font-family:inherit; font-size:inherit;">Sign out</button>`;
      
      document.querySelector("#landing-signout-btn")?.addEventListener("click", () => {
        sessionStorage.removeItem(tokenKey);
        localStorage.removeItem(tokenKey);
        formMessage.textContent = "Signed out successfully. Please enter your credentials to log in.";
        formMessage.className = "form-message";
        formMessage.style.color = "#15803d";
      });
    }
  } catch {
    sessionStorage.removeItem(tokenKey);
    localStorage.removeItem(tokenKey);
  }
})();
