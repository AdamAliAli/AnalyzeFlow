// ==================== Counter animation ====================
const counters = document.querySelectorAll(".counter");
const counterObserver = new IntersectionObserver((entries) => {
  entries.forEach((entry) => {
    if (entry.isIntersecting) {
      const counter = entry.target;
      const target = +counter.dataset.target;
      let count = 0;
      const updateCounter = () => {
        const increment = target / 50;
        if (count < target) {
          count += increment;
          counter.textContent = Math.ceil(count);
          requestAnimationFrame(updateCounter);
        } else {
          counter.textContent = target + "+";
        }
      };
      updateCounter();
      counterObserver.unobserve(counter);
    }
  });
});

// Don't observe yet — wait until loadDynamicData settles so the real
// data-target values are in place. See startCounterObservation() below.
function startCounterObservation() {
  counters.forEach((counter) => {
    counterObserver.observe(counter);
  });
}

// ==================== Framework cards toggle ====================
const frameworkCards = document.querySelectorAll(".framework-card");
frameworkCards.forEach((card) => {
  card.addEventListener("click", () => {
    card.classList.toggle("active");
  });
});

// ==================== Reveal on scroll ====================
const reveals = document.querySelectorAll(".reveal");

const observe = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("active");
      }
    });
  },
  {
    threshold: 0.15,
  },
);

reveals.forEach((item) => {
  observe.observe(item);
});

// Dead code — kept for Task 6 (report page score ring)
document.addEventListener("DOMContentLoaded", () => {
  const score = document.getElementById("score");
  const circle = document.querySelector(".progress-circle");

  if (!score || !circle) return;

  const radius = circle.r.baseVal.value;
  const circumference = 2 * Math.PI * radius;

  circle.style.strokeDasharray = circumference;
  circle.style.strokeDashoffset = circumference;

  const target = 92;
  let current = 0;

  function animate() {
    current++;

    score.textContent = current;

    const offset = circumference - (current / 100) * circumference;

    circle.style.strokeDashoffset = offset;

    if (current < target) {
      requestAnimationFrame(animate);
    }
  }

  animate();
});

// ==================== Auth UI ====================
const authModalOverlay = document.getElementById("authModalOverlay");
const authCloseBtn = document.getElementById("authCloseBtn");
const authNavLink = document.getElementById("authNavLink");
const loginForm = document.getElementById("loginForm");
const registerForm = document.getElementById("registerForm");
const authModalTitle = document.getElementById("authModalTitle");
const showRegisterLink = document.getElementById("showRegister");
const showLoginLink = document.getElementById("showLogin");
const loginSubmitBtn = document.getElementById("loginSubmitBtn");
const registerSubmitBtn = document.getElementById("registerSubmitBtn");
const loginError = document.getElementById("loginError");
const registerError = document.getElementById("registerError");

// Track whether we should open the wizard after sign-in
let _openWizardAfterAuth = false;

function updateAuthNav() {
  if (API.isSignedIn()) {
    const user = API.currentUser();
    authNavLink.textContent = user ? user.full_name : "Account";
    authNavLink.onclick = function (e) {
      e.preventDefault();
      API.logout();
      updateAuthNav();
    };
  } else {
    authNavLink.textContent = "Sign in";
    authNavLink.onclick = function (e) {
      e.preventDefault();
      _openWizardAfterAuth = false;
      openAuthModal("login");
    };
  }
}

function openAuthModal(mode) {
  if (mode === "register") {
    loginForm.style.display = "none";
    registerForm.style.display = "block";
    authModalTitle.textContent = "Create Account";
  } else {
    loginForm.style.display = "block";
    registerForm.style.display = "none";
    authModalTitle.textContent = "Sign In";
  }
  loginError.style.display = "none";
  registerError.style.display = "none";
  authModalOverlay.classList.add("active");
}

function closeAuthModal() {
  authModalOverlay.classList.remove("active");
}

authCloseBtn.addEventListener("click", closeAuthModal);
authModalOverlay.addEventListener("click", (e) => {
  if (e.target === authModalOverlay) closeAuthModal();
});

showRegisterLink.addEventListener("click", (e) => {
  e.preventDefault();
  openAuthModal("register");
});
showLoginLink.addEventListener("click", (e) => {
  e.preventDefault();
  openAuthModal("login");
});

// Client-side validation helpers
function validateEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function validatePassword(pw) {
  return pw.length >= 8 && /[a-zA-Z]/.test(pw) && /[0-9]/.test(pw);
}

loginSubmitBtn.addEventListener("click", async () => {
  const email = document.getElementById("loginEmail").value.trim();
  const password = document.getElementById("loginPassword").value;

  if (!email || !password) {
    loginError.textContent = "Please fill in all fields.";
    loginError.style.display = "block";
    return;
  }

  loginSubmitBtn.disabled = true;
  loginSubmitBtn.textContent = "Signing in...";
  loginError.style.display = "none";

  try {
    await API.login(email, password);
    updateAuthNav();
    closeAuthModal();
    if (_openWizardAfterAuth) {
      _openWizardAfterAuth = false;
      openAuditModal();
    }
  } catch (err) {
    loginError.textContent = err.message;
    loginError.style.display = "block";
  } finally {
    loginSubmitBtn.disabled = false;
    loginSubmitBtn.textContent = "Sign In";
  }
});

registerSubmitBtn.addEventListener("click", async () => {
  const fullName = document.getElementById("registerName").value.trim();
  const email = document.getElementById("registerEmail").value.trim();
  const password = document.getElementById("registerPassword").value;

  if (fullName.length < 2) {
    registerError.textContent = "Full name must be at least 2 characters.";
    registerError.style.display = "block";
    return;
  }
  if (!validateEmail(email)) {
    registerError.textContent = "Please enter a valid email address.";
    registerError.style.display = "block";
    return;
  }
  if (!validatePassword(password)) {
    registerError.textContent = "Password must be at least 8 characters and contain both letters and numbers.";
    registerError.style.display = "block";
    return;
  }

  registerSubmitBtn.disabled = true;
  registerSubmitBtn.textContent = "Creating account...";
  registerError.style.display = "none";

  try {
    await API.register(fullName, email, password);
    updateAuthNav();
    closeAuthModal();
    if (_openWizardAfterAuth) {
      _openWizardAfterAuth = false;
      openAuditModal();
    }
  } catch (err) {
    registerError.textContent = err.message;
    registerError.style.display = "block";
  } finally {
    registerSubmitBtn.disabled = false;
    registerSubmitBtn.textContent = "Create Account";
  }
});

updateAuthNav();

// ==================== Audit Modal ====================
const modal = document.getElementById("auditModalOverlay");
const auditModalTop = document.getElementById("auditModalTop");
const modalContent = modal.querySelector(".modal-content");
const modalFooter = modal.querySelector(".modal-footer");
const openBtn = document.querySelector(".Primary");
const closeBtn = modal.querySelector(".close-modal");
// Save a reference to the audit form before the progress screen replaces innerHTML
const auditFormEl = document.querySelector(".audit-form");

let pollInterval = null;
let pollTimeout = null;

function clearPolling() {
  if (pollInterval) { clearInterval(pollInterval); pollInterval = null; }
  if (pollTimeout) { clearTimeout(pollTimeout); pollTimeout = null; }
}

function openAuditModal() {
  resetWizard();
  modal.classList.add("active");
}

function closeAuditModal() {
  modal.classList.remove("active");
  clearPolling();
}

openBtn.addEventListener("click", () => {
  if (!API.isSignedIn()) {
    _openWizardAfterAuth = true;
    openAuthModal("login");
    return;
  }
  openAuditModal();
});

closeBtn.addEventListener("click", closeAuditModal);
modal.addEventListener("click", (e) => {
  if (e.target === modal) closeAuditModal();
});

// ==================== Wizard steps ====================
const goalCards = document.querySelectorAll(".goal-card");
goalCards.forEach((card) => {
  card.addEventListener("click", () => {
    goalCards.forEach((item) => {
      item.classList.remove("selected");
    });
    card.classList.add("selected");
  });
});

const formSteps = document.querySelectorAll(".form-step");
const nextBtn = modal.querySelector(".next-btn");
const backBtn = modal.querySelector(".back-btn");
const progressSteps = document.querySelectorAll(".progress-step");
const progressLines = document.querySelectorAll(".progress-line");

let currentFormStep = 0;

function resetWizard() {
  currentFormStep = 0;
  // Show wizard UI, hide progress view
  auditModalTop.style.display = "";
  modalFooter.style.display = "";
  modalContent.innerHTML = "";
  modalContent.appendChild(auditFormEl);
  auditFormEl.style.display = "";
  nextBtn.disabled = false;
  showStep();
}

function showStep() {
  formSteps.forEach((step) => {
    step.classList.remove("active");
  });

  formSteps[currentFormStep].classList.add("active");

  if (currentFormStep === 0) {
    backBtn.style.visibility = "hidden";
  } else {
    backBtn.style.visibility = "visible";
  }

  if (currentFormStep === formSteps.length - 1) {
    nextBtn.textContent = "Generate Report \u2192";
  } else {
    nextBtn.textContent = "Continue \u2192";
  }

  progressSteps.forEach((step, index) => {
    if (index <= currentFormStep) {
      step.classList.add("active");
    } else {
      step.classList.remove("active");
    }
  });
  progressLines.forEach((line, index) => {
    if (index < currentFormStep) {
      line.classList.add("active");
    } else {
      line.classList.remove("active");
    }
  });
}
showStep();

nextBtn.addEventListener("click", async () => {
  // STEP 1 VALIDATION
  if (currentFormStep === 0) {
    const businessName = document.getElementById("businessName").value.trim();
    const websiteUrl = document.getElementById("websiteUrl").value.trim();
    const industry = document.getElementById("industry").value;

    if (!businessName) {
      alert("Please enter your business name.");
      return;
    }
    if (!websiteUrl) {
      alert("Please enter your website URL.");
      return;
    }
    if (!industry) {
      alert("Please select your industry.");
      return;
    }
  }

  if (currentFormStep === 1) {
    const selectedGoal = document.querySelector(".goal-card.selected");

    if (!selectedGoal) {
      alert("Please select your primary business goal.");
      return;
    }
  }

  // STEP 3 VALIDATION
  if (currentFormStep === 2) {
    const selectedChallenges = document.querySelectorAll(
      ".challenge-card.selected",
    );

    if (selectedChallenges.length === 0) {
      alert("Please select at least one business challenge.");
      return;
    }
  }

  // STEP 4 — SUBMIT
  if (currentFormStep === 3) {
    const selectedStage = document.querySelector(".stage-card.selected");
    if (!selectedStage) {
      alert("Please select your business stage.");
      return;
    }

    const businessName = document.getElementById("businessName").value.trim();
    const websiteUrl = document.getElementById("websiteUrl").value.trim();
    const industry = document.getElementById("industry").value;
    const selectedGoal = document.querySelector(".goal-card.selected");
    const selectedChallenges = document.querySelectorAll(
      ".challenge-card.selected",
    );

    const challenges = [];
    selectedChallenges.forEach((challenge) => {
      challenges.push(challenge.dataset.value);
    });

    const payload = {
      business_name: businessName,
      website_url: websiteUrl,
      industry: industry,
      goal: selectedGoal.dataset.value,
      challenges: challenges,
      business_stage: selectedStage.dataset.value,
    };

    nextBtn.disabled = true;
    nextBtn.textContent = "Submitting...";

    try {
      const result = await API.createAudit(payload);
      const auditId = result.audit.audit_id;
      API.runAudit(auditId).catch(function () {});   // deliberately not awaited
      showProgressScreen(auditId);
    } catch (err) {
      nextBtn.disabled = false;
      nextBtn.textContent = "Generate Report \u2192";
      var msg = err.message;
      if (err.details && err.details.allowed) {
        msg += "\n\nAllowed values: " + err.details.allowed.join(", ");
      }
      alert(msg);
    }
    return;
  }

  if (currentFormStep < formSteps.length - 1) {
    currentFormStep++;
    showStep();
  }
});

backBtn.addEventListener("click", () => {
  if (currentFormStep > 0) {
    currentFormStep--;
    showStep();
  }
});

// step 3
const challengeCards = document.querySelectorAll(".challenge-card");

challengeCards.forEach((card) => {
  card.addEventListener("click", () => {
    card.classList.toggle("selected");
  });
});

// select from the step 4
const stageCards = document.querySelectorAll(".stage-card");

stageCards.forEach((card) => {
  card.addEventListener("click", () => {
    stageCards.forEach((item) => {
      item.classList.remove("selected");
    });
    card.classList.add("selected");
  });
});

// ==================== Task 5 — Progress screen ====================
const STAGE_LABELS = {
  queued: "Getting ready\u2026",
  fetching_site: "Fetching your website\u2026",
  extracting_signals: "Measuring the page\u2026",
  running_analysis: "Analysing\u2026",
  saving_report: "Preparing your report\u2026",
  done: "Done",
};

function showProgressScreen(auditId) {
  clearPolling();

  // Hide wizard header and footer
  auditModalTop.style.display = "none";
  modalFooter.style.display = "none";

  // Detach the form so it survives innerHTML replacement
  if (auditFormEl.parentNode) auditFormEl.parentNode.removeChild(auditFormEl);

  modalContent.innerHTML =
    '<div style="text-align: center; padding: 2rem 0;">' +
      '<h2 style="margin-bottom: 0.5rem; color: #0f172a;">Analyzing your website</h2>' +
      '<p style="color: #64748b; margin-bottom: 2rem;" id="progressStageLabel">Getting ready\u2026</p>' +
      '<div class="progress" style="width: 100%; max-width: 400px; margin: 0 auto 1rem; height: 12px;">' +
        '<div class="fill" id="progressFill" style="width: 0%; transition: width 0.4s ease;"></div>' +
      '</div>' +
      '<p style="color: #2563eb; font-weight: 600;" id="progressPercent">0%</p>' +
    '</div>';

  var elapsed = 0;
  var TIMEOUT_MS = 90000;

  pollInterval = setInterval(async () => {
    elapsed += 2000;

    if (elapsed > TIMEOUT_MS) {
      clearPolling();
      showFailureScreen(auditId, "The analysis is taking longer than expected. Please try again.");
      return;
    }

    try {
      var job = await API.getJob(auditId);

      var fill = document.getElementById("progressFill");
      var label = document.getElementById("progressStageLabel");
      var pct = document.getElementById("progressPercent");

      if (fill) fill.style.width = job.progress + "%";
      if (pct) pct.textContent = job.progress + "%";
      if (label) label.textContent = STAGE_LABELS[job.stage] || job.stage;

      if (job.status === "succeeded") {
        clearPolling();
        // Navigate to report page
        window.location.href = "report.html?audit=" + auditId;
      } else if (job.status === "failed") {
        clearPolling();
        showFailureScreen(auditId, job.error_message || "Something went wrong. Please try again.");
      }
    } catch (err) {
      // Network error — keep polling, it may recover
    }
  }, 2000);
}

function showFailureScreen(auditId, message) {
  modalContent.innerHTML =
    '<div style="text-align: center; padding: 2rem 0;">' +
      '<div style="width: 70px; height: 70px; margin: 0 auto 1.5rem; background: #fef2f2; border-radius: 50%; display: flex; align-items: center; justify-content: center;">' +
        '<i class="fa-solid fa-triangle-exclamation" style="font-size: 1.8rem; color: #dc2626;"></i>' +
      '</div>' +
      '<h2 style="margin-bottom: 0.75rem; color: #0f172a;">Analysis Failed</h2>' +
      '<p style="color: #64748b; margin-bottom: 2rem; max-width: 400px; margin-left: auto; margin-right: auto;">' +
        escapeHtml(message) +
      '</p>' +
      '<button type="button" id="retryBtn" class="next-btn" style="margin: 0 auto;">Try Again</button>' +
    '</div>';

  document.getElementById("retryBtn").addEventListener("click", async () => {
    var btn = document.getElementById("retryBtn");
    btn.disabled = true;
    btn.textContent = "Retrying...";
    try {
      await API.retryAudit(auditId);
      API.runAudit(auditId).catch(function () {});
      showProgressScreen(auditId);
    } catch (err) {
      btn.disabled = false;
      btn.textContent = "Try Again";
      alert(err.message);
    }
  });
}

function escapeHtml(str) {
  var div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

// ==================== Task 7 — Load dynamic data ====================
(async function loadDynamicData() {
  // Stats
  try {
    var stats = await API.getStats();
    var counterEls = document.querySelectorAll(".counter");
    if (stats.audits_completed !== undefined && counterEls[0]) {
      counterEls[0].dataset.target = stats.audits_completed;
    }
    if (stats.opportunities_found !== undefined && counterEls[1]) {
      counterEls[1].dataset.target = stats.opportunities_found;
    }
    if (stats.frameworks !== undefined && counterEls[2]) {
      counterEls[2].dataset.target = stats.frameworks;
    }
  } catch (_) {
    // Keep hard-coded fallback values
  }
  // Now that data-target values are settled, start observing
  startCounterObservation();

  // Lookups — populate wizard
  try {
    var lookups = await API.getLookups();

    // Industries
    if (lookups.industries && lookups.industries.length > 0) {
      var sel = document.getElementById("industry");
      // Clear existing options except placeholder
      while (sel.options.length > 1) sel.remove(1);
      lookups.industries.forEach(function (ind) {
        var opt = document.createElement("option");
        opt.value = ind.slug || ind.value || ind;
        opt.textContent = ind.label || ind.name || ind;
        sel.appendChild(opt);
      });
    }

    // Goals
    if (lookups.goals && lookups.goals.length > 0) {
      var goalGrid = document.querySelector(".goal-grid");
      goalGrid.innerHTML = "";
      lookups.goals.forEach(function (g) {
        var label = g.label || g.name || g;
        var slug = g.slug || g.value || label;
        var icon = g.icon || "fa-solid fa-bullseye";
        var desc = g.description || "";
        var card = document.createElement("div");
        card.className = "goal-card";
        card.dataset.value = label;
        card.innerHTML =
          '<i class="' + escapeHtml(icon) + '"></i>' +
          '<h3>' + escapeHtml(label) + '</h3>' +
          '<p>' + escapeHtml(desc) + '</p>';
        card.addEventListener("click", function () {
          document.querySelectorAll(".goal-card").forEach(function (c) { c.classList.remove("selected"); });
          card.classList.add("selected");
        });
        goalGrid.appendChild(card);
      });
    }

    // Challenges
    if (lookups.challenges && lookups.challenges.length > 0) {
      var challengeGrid = document.querySelector(".challenge-grid");
      challengeGrid.innerHTML = "";
      lookups.challenges.forEach(function (ch) {
        var label = ch.label || ch.name || ch;
        var icon = ch.icon || "fa-solid fa-exclamation-circle";
        var desc = ch.description || "";
        var card = document.createElement("div");
        card.className = "challenge-card";
        card.dataset.value = label;
        card.innerHTML =
          '<i class="' + escapeHtml(icon) + '"></i>' +
          '<h3>' + escapeHtml(label) + '</h3>' +
          '<p>' + escapeHtml(desc) + '</p>';
        card.addEventListener("click", function () {
          card.classList.toggle("selected");
        });
        challengeGrid.appendChild(card);
      });
    }

    // Business stages
    if (lookups.business_stages && lookups.business_stages.length > 0) {
      var stageGrid = document.querySelector(".stage-grid");
      stageGrid.innerHTML = "";
      lookups.business_stages.forEach(function (st) {
        var label = st.label || st.name || st;
        var icon = st.icon || "fa-solid fa-building";
        var desc = st.description || "";
        var card = document.createElement("div");
        card.className = "stage-card";
        card.dataset.value = label;
        card.innerHTML =
          '<i class="' + escapeHtml(icon) + '"></i>' +
          '<div><h3>' + escapeHtml(label) + '</h3>' +
          '<p>' + escapeHtml(desc) + '</p></div>';
        card.addEventListener("click", function () {
          document.querySelectorAll(".stage-card").forEach(function (c) { c.classList.remove("selected"); });
          card.classList.add("selected");
        });
        stageGrid.appendChild(card);
      });
    }
  } catch (_) {
    // Keep hard-coded fallback markup
  }

  // Case studies
  try {
    var studies = await API.getCaseStudies();
    if (studies && studies.length > 0) {
      var cs = studies[0];
      var caseCard = document.querySelector(".case-study-card");
      if (caseCard) {
        var h3 = caseCard.querySelector(".case-header h3");
        if (h3 && cs.title) h3.textContent = cs.title;
        var sub = caseCard.querySelector(".case-subtitle");
        if (sub && cs.summary) sub.textContent = cs.summary;
        var insight = caseCard.querySelector(".insight-box p");
        if (insight && cs.key_insight) insight.textContent = cs.key_insight;
        var link = caseCard.querySelector(".case-btn");
        if (link && cs.slug) link.href = "./case-study.html?slug=" + cs.slug;
      }
    }
  } catch (_) {
    // Keep hard-coded fallback
  }
})();
