// App State
let token = localStorage.getItem("token") || "";
let userRole = localStorage.getItem("role") || "";
let userData = null;
let currentPlacementId = null;
let placementStartDate = null;

// API Helper Wrapper
async function apiRequest(endpoint, method = "GET", body = null, isMultipart = false) {
    const headers = {};
    if (token) {
        headers["Authorization"] = `Bearer ${token}`;
    }
    
    let options = { method, headers };
    
    if (body) {
        if (isMultipart) {
            options.body = body; // let browser set content-type for multipart form data
        } else {
            headers["Content-Type"] = "application/json";
            options.body = JSON.stringify(body);
        }
    }
    
    try {
        const response = await fetch(endpoint, options);
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.detail || "Something went wrong");
        }
        return data;
    } catch (error) {
        showToast(error.message, "error");
        throw error;
    }
}

// Quick Demo Login Helper for Testing & Defense Presentations
function quickFillDemoCredentials() {
    const val = document.getElementById("quick-demo-select").value;
    const emailInput = document.getElementById("login-email");
    const passwordInput = document.getElementById("login-password");
    
    if (val === "student") {
        emailInput.value = "student1@university.edu.ng";
        passwordInput.value = "password123";
    } else if (val === "supervisor") {
        emailInput.value = "supervisor1@brighttech.com";
        passwordInput.value = "password123";
    } else if (val === "coordinator") {
        emailInput.value = "coordinator@university.edu.ng";
        passwordInput.value = "password123";
    }
}

// Toast notification helper
function showToast(message, type = "info") {
    const container = document.getElementById("toast-container");
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.innerHTML = message;
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = "0";
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// Live Clock in Header
function updateClock() {
    const now = new Date();
    document.getElementById("live-time").innerText = now.toLocaleString();
}
setInterval(updateClock, 1000);
updateClock();

// Switch between Login and Registration forms
function switchAuthTab(tab) {
    const loginForm = document.getElementById("login-form");
    const regForm = document.getElementById("register-form");
    const tabs = document.querySelectorAll(".auth-tab");
    
    tabs.forEach(t => t.classList.remove("active"));
    
    if (tab === "login") {
        loginForm.classList.remove("hidden");
        regForm.classList.add("hidden");
        tabs[0].classList.add("active");
    } else {
        loginForm.classList.add("hidden");
        regForm.classList.remove("hidden");
        tabs[1].classList.add("active");
    }
}

function toggleStudentRegFields() {
    const roleSelect = document.getElementById("reg-role");
    const studentFields = document.getElementById("student-only-reg-fields");
    if (roleSelect && studentFields) {
        if (roleSelect.value === "student") {
            studentFields.classList.remove("hidden");
        } else {
            studentFields.classList.add("hidden");
        }
    }
}

// Authentication Actions
async function handleLogin(e) {
    e.preventDefault();
    const email = document.getElementById("login-email").value;
    const password = document.getElementById("login-password").value;
    
    try {
        const formData = new URLSearchParams();
        formData.append("username", email);
        formData.append("password", password);

        const response = await fetch("/api/v1/auth/login", {
            method: "POST",
            headers: {
                "Content-Type": "application/x-www-form-urlencoded"
            },
            body: formData
        });
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.detail || "Incorrect email or password");
        }
        
        token = data.access_token;
        userRole = data.role;
        
        localStorage.setItem("token", token);
        localStorage.setItem("role", userRole);
        
        showToast("Logged in successfully", "success");
        initDashboard();
    } catch (err) {
        showToast(err.message, "error");
    }
}

async function handleRegister(e) {
    e.preventDefault();
    const fullName = document.getElementById("reg-name").value;
    const email = document.getElementById("reg-email").value;
    const password = document.getElementById("reg-password").value;
    const role = document.getElementById("reg-role").value;
    
    const payload = {
        full_name: fullName,
        email: email,
        password: password,
        role: role
    };

    if (role === "student") {
        payload.matric_number = document.getElementById("reg-matric").value || null;
        payload.department = document.getElementById("reg-dept").value || null;
        payload.level = document.getElementById("reg-level").value || null;
    }
    
    try {
        await apiRequest("/api/v1/auth/register", "POST", payload);
        showToast("Registration successful! You can now log in.", "success");
        switchAuthTab("login");
    } catch (err) {
        // Handled by apiRequest wrapper
    }
}

function handleLogout() {
    token = "";
    userRole = "";
    userData = null;
    currentPlacementId = null;
    localStorage.removeItem("token");
    localStorage.removeItem("role");
    
    document.getElementById("auth-section").classList.remove("hidden");
    document.getElementById("dashboard-section").classList.add("hidden");
}

// Initialize Dashboards
async function initDashboard() {
    document.getElementById("auth-section").classList.add("hidden");
    document.getElementById("dashboard-section").classList.remove("hidden");
    
    // Set user profile in sidebar
    try {
        userData = await apiRequest("/api/v1/auth/me");
        document.getElementById("sidebar-user-name").innerText = userData.full_name;
        document.getElementById("sidebar-user-role").innerText = userData.role;
        document.getElementById("user-avatar").innerText = userData.full_name.charAt(0).toUpperCase();
        
        // Toggle view sidebar controls
        document.querySelectorAll(".nav-group").forEach(el => el.classList.add("hidden"));
        
        if (userData.role === "student") {
            document.querySelector(".student-nav").classList.remove("hidden");
            switchDashboardView("student-overview");
        } else if (userData.role === "supervisor") {
            document.querySelector(".supervisor-nav").classList.remove("hidden");
            switchDashboardView("supervisor-overview");
        } else if (userData.role === "coordinator" || userData.role === "admin") {
            document.querySelector(".coordinator-nav").classList.remove("hidden");
            switchDashboardView("coordinator-overview");
        }
    } catch (err) {
        handleLogout();
    }
}

// Switch between sidebar tabs/views
async function switchDashboardView(viewId) {
    document.querySelectorAll(".dashboard-view").forEach(v => v.classList.add("hidden"));
    document.querySelectorAll(".nav-link").forEach(l => l.classList.remove("active"));
    
    // Mark clicked nav active
    const activeLink = document.querySelector(`a[onclick="switchDashboardView('${viewId}')"]`);
    if (activeLink) activeLink.classList.add("active");
    
    const titleHeader = document.getElementById("current-view-title");
    
    if (viewId === "student-overview") {
        titleHeader.innerText = "Student Progress Overview";
        document.getElementById("view-student-overview").classList.remove("hidden");
        loadStudentOverview();
    } else if (viewId === "student-placement") {
        titleHeader.innerText = "My Placement Organization";
        document.getElementById("view-student-placement").classList.remove("hidden");
        loadStudentPlacement();
    } else if (viewId === "student-logbook") {
        titleHeader.innerText = "Weekly Logbook Workspace";
        document.getElementById("view-student-logbook").classList.remove("hidden");
        loadStudentLogbook();
    } else if (viewId === "supervisor-overview") {
        titleHeader.innerText = "Assigned Students Monitoring";
        document.getElementById("view-supervisor-overview").classList.remove("hidden");
        loadSupervisorStudents();
    } else if (viewId === "supervisor-verification") {
        titleHeader.innerText = "Student Placement Verifications";
        document.getElementById("view-supervisor-verification").classList.remove("hidden");
        loadSupervisorVerificationQueue();
    } else if (viewId === "coordinator-overview") {
        titleHeader.innerText = "SIWES Administrative Dashboard";
        document.getElementById("view-coordinator-overview").classList.remove("hidden");
        loadCoordinatorDashboard();
    } else if (viewId === "coordinator-placements") {
        titleHeader.innerText = "Placement Verification Queue";
        document.getElementById("view-coordinator-placements").classList.remove("hidden");
        loadCoordinatorPlacements();
    } else if (viewId === "coordinator-sessions") {
        titleHeader.innerText = "Manage Academic Sessions";
        document.getElementById("view-coordinator-sessions").classList.remove("hidden");
        loadCoordinatorSessions();
    } else if (viewId === "coordinator-students") {
        titleHeader.innerText = "Verify Student Identities";
        document.getElementById("view-coordinator-students").classList.remove("hidden");
        loadCoordinatorStudentsList();
    }
}

// Student Dashboard: Load Overview
async function loadStudentOverview() {
    try {
        const stats = await apiRequest("/api/v1/dashboard/student");
        
        // 1. Set next step message immediately
        const nextStepMsg = document.getElementById("student-next-step-msg");
        if (nextStepMsg) {
            const statusLower = (stats.placement_status || "").toLowerCase();
            if (statusLower === "approved") {
                nextStepMsg.innerHTML = `Your SIWES placement is <strong>APPROVED</strong>! Go to the <strong>Logbook tab</strong> to fill and submit your Weekly Logbook Entry (Completed: <strong>${stats.completed_weeks} of ${stats.total_weeks} Weeks</strong>).`;
            } else if (statusLower.includes("pending") || statusLower.includes("verification") || statusLower.includes("submitted")) {
                nextStepMsg.innerHTML = `Your placement proposal is <strong>UNDER VERIFICATION</strong>. Copy your supervisor invitation link from the <strong>Placement tab</strong> and send it to your supervisor to confirm.`;
            } else {
                nextStepMsg.innerHTML = `Please go to the <strong>Placement tab</strong> to fill and submit your SIWES Placement Proposal for coordinator verification.`;
            }
        }

        // Show/hide unverified identity alert
        const isVerified = (userData && userData.student_profile) ? userData.student_profile.is_verified : false;
        const alertEl = document.getElementById("student-unverified-alert");
        if (alertEl) {
            if (isVerified) {
                alertEl.classList.add("hidden");
            } else {
                alertEl.classList.remove("hidden");
            }
        }
        
        if (userData) {
            document.querySelector(".student-name").innerText = userData.full_name;
        }
        document.getElementById("stat-weeks-logged").innerText = `${stats.completed_weeks} / ${stats.total_weeks}`;
        
        const placementStatusEl = document.getElementById("stat-placement-status");
        placementStatusEl.innerText = stats.placement_status;
        placementStatusEl.className = `status-badge ${stats.placement_status === "approved" ? "text-emerald" : "text-yellow"}`;
        
        document.getElementById("dashboard-progress-fill").style.width = `${stats.progress_percentage}%`;
        document.getElementById("progress-percentage-label").innerText = `${stats.progress_percentage}% Completed`;

        // Try loading final assessment details safely
        if (stats.placement_details) {
            currentPlacementId = stats.placement_details.id;
            placementStartDate = stats.placement_details.start_date;
            try {
                const res = await fetch(`/api/v1/assessments/placement/${currentPlacementId}`, {
                    headers: { "Authorization": `Bearer ${token}` }
                });
                if (res.ok) {
                    const assess = await res.json();
                    document.getElementById("stat-student-score").innerText = `${assess.total_score} / 100`;
                } else {
                    document.getElementById("stat-student-score").innerText = "-- / 100";
                }
            } catch (err) {
                document.getElementById("stat-student-score").innerText = "-- / 100";
            }
        }
    } catch (err) {
        console.error("Error loading student overview:", err);
    }
}

// Student Dashboard: Load Placement Details
// Student Dashboard: Load Placement Details
async function loadStudentPlacement() {
    const unregBox = document.getElementById("placement-unregistered-box");
    const regBox = document.getElementById("placement-registered-box");
    
    unregBox.classList.add("hidden");
    regBox.classList.add("hidden");
    
    try {
        // First try getting active verified placement details
        const placement = await apiRequest("/api/v1/placements/me");
        regBox.classList.remove("hidden");
        
        document.getElementById("view-place-org").innerText = placement.organization ? placement.organization.name : "N/A";
        document.getElementById("view-place-dates").innerText = `${placement.start_date} to ${placement.end_date} (${placement.duration_weeks} Weeks)`;
        document.getElementById("view-place-supervisor").innerText = placement.supervisor && placement.supervisor.user ? placement.supervisor.user.full_name : "Unassigned";
        
        const statusEl = document.getElementById("view-place-status");
        statusEl.innerText = "VERIFIED & ACTIVE";
        statusEl.className = "badge accent-emerald";
        
        // Show report upload section if active
        document.getElementById("final-report-section").classList.remove("hidden");
    } catch (err) {
        // If no active placement, fetch verification request
        unregBox.classList.remove("hidden");
        try {
            const req = await apiRequest("/api/v1/verification/request/my");
            const isVerified = userData.student_profile ? userData.student_profile.is_verified : false;
            if (!isVerified) {
                document.getElementById("placement-request-id").value = "";
                document.getElementById("verification-status-card").classList.remove("hidden");
                badge.innerText = "UNVERIFIED IDENTITY";
                badge.className = "badge accent-rose";
                explanation.innerText = "Identity Verification Pending. You must be verified by the coordinator before saving or submitting placement proposals.";
                setPlacementFormReadonly(true);
                document.getElementById("btn-save-request").classList.add("hidden");
                document.getElementById("btn-submit-request").classList.add("hidden");
                document.getElementById("invitation-link-box").classList.add("hidden");
                return;
            }

            if (!req) {
                // Completely new request draft
                document.getElementById("placement-request-id").value = "";
                document.getElementById("verification-status-card").classList.add("hidden");
                setPlacementFormReadonly(false);
                document.getElementById("btn-save-request").classList.remove("hidden");
                document.getElementById("btn-submit-request").classList.add("hidden");
                document.getElementById("invitation-link-box").classList.add("hidden");
                return;
            }

            // Populate form fields
            document.getElementById("placement-request-id").value = req.id;
            document.getElementById("place-org").value = req.proposed_company_name;
            document.getElementById("place-addr").value = req.proposed_company_address;
            document.getElementById("place-industry").value = req.proposed_company_industry || "";
            document.getElementById("place-email").value = req.proposed_company_email || "";
            document.getElementById("place-phone").value = req.proposed_company_phone || "";
            document.getElementById("place-sup-name").value = req.proposed_supervisor_name;
            document.getElementById("place-sup-title").value = req.proposed_supervisor_job_title;
            document.getElementById("place-sup-email").value = req.proposed_supervisor_email;
            document.getElementById("place-sup-phone").value = req.proposed_supervisor_phone;
            document.getElementById("place-start").value = req.start_date;
            document.getElementById("place-end").value = req.end_date;
            document.getElementById("place-duration-weeks").value = req.duration_weeks;
            document.getElementById("place-obtained").value = req.how_obtained || "Personal Contact / Search";
            document.getElementById("place-expected-work").value = req.expected_work || "";

            // Display verification tracker card
            document.getElementById("verification-status-card").classList.remove("hidden");
            const badge = document.getElementById("verification-badge");
            const explanation = document.getElementById("verification-explanation");
            
            badge.innerText = req.status.toUpperCase();
            badge.className = `badge ${req.status === 'verified' || req.status === 'active' ? 'accent-emerald' : req.status === 'rejected' ? 'accent-rose' : 'accent-yellow'}`;
            
            // Set explanations
            if (req.status === "draft") {
                explanation.innerText = "Draft created. Fill all fields and click 'Submit Request' when ready.";
                setPlacementFormReadonly(false);
                document.getElementById("btn-save-request").classList.remove("hidden");
                document.getElementById("btn-submit-request").classList.remove("hidden");
                document.getElementById("invitation-link-box").classList.add("hidden");
                document.getElementById("appeal-form-box").classList.add("hidden");
            } else if (req.status === "correction_required") {
                explanation.innerText = "Coordinator requested corrections. Please update fields and save.";
                setPlacementFormReadonly(false);
                document.getElementById("btn-save-request").classList.remove("hidden");
                document.getElementById("btn-submit-request").classList.add("hidden");
                document.getElementById("invitation-link-box").classList.add("hidden");
                document.getElementById("appeal-form-box").classList.add("hidden");
            } else {
                // Locked status
                setPlacementFormReadonly(true);
                document.getElementById("btn-save-request").classList.add("hidden");
                document.getElementById("btn-submit-request").classList.add("hidden");

                if (req.status === "awaiting_supervisor") {
                    explanation.innerText = "Awaiting supervisor to accept invitation and confirm details.";
                    document.getElementById("invitation-link-box").classList.remove("hidden");
                    const token = localStorage.getItem(`invite_token_${req.id}`) || "TOKEN";
                    document.getElementById("invite-link-url").value = `${window.location.origin}/#invite/${token}`;
                    document.getElementById("appeal-form-box").classList.add("hidden");
                } else if (req.status === "rejected") {
                    explanation.innerText = "Request was rejected by the Departmental Coordinator.";
                    document.getElementById("invitation-link-box").classList.add("hidden");
                    document.getElementById("appeal-form-box").classList.remove("hidden");
                } else {
                    document.getElementById("invitation-link-box").classList.add("hidden");
                    document.getElementById("appeal-form-box").classList.add("hidden");
                }
            }
        } catch (err2) {
            console.error(err2);
        }
    }
}

function setPlacementFormReadonly(isReadonly) {
    const fields = [
        "place-org", "place-addr", "place-industry", "place-email", "place-phone",
        "place-sup-name", "place-sup-title", "place-sup-email", "place-sup-phone",
        "place-sup-experience", "place-sup-dept", "place-sup-relationship", "place-sup-conflict",
        "place-rep-name", "place-rep-email", "place-start", "place-end", "place-duration-weeks", "place-obtained", "place-expected-work"
    ];
    fields.forEach(f => {
        const el = document.getElementById(f);
        if (el) el.disabled = isReadonly;
    });
}

// Submit/Save placement request draft
async function handlePlacementSubmit(e) {
    e.preventDefault();
    const reqId = document.getElementById("placement-request-id").value;
    
    const techAreas = [];
    document.querySelectorAll("input[name='tech-area']:checked").forEach(cb => {
        techAreas.push(cb.value);
    });

    const payload = {
        proposed_company_name: document.getElementById("place-org").value,
        proposed_company_address: document.getElementById("place-addr").value,
        proposed_company_industry: document.getElementById("place-industry").value || null,
        proposed_company_email: document.getElementById("place-email").value || null,
        proposed_company_phone: document.getElementById("place-phone").value || null,
        proposed_supervisor_name: document.getElementById("place-sup-name").value,
        proposed_supervisor_job_title: document.getElementById("place-sup-title").value,
        proposed_supervisor_email: document.getElementById("place-sup-email").value,
        proposed_supervisor_phone: document.getElementById("place-sup-phone").value,
        proposed_supervisor_experience: parseInt(document.getElementById("place-sup-experience").value) || null,
        proposed_supervisor_department: document.getElementById("place-sup-dept").value || null,
        relationship_to_student: document.getElementById("place-sup-relationship").value || null,
        conflict_declaration: document.getElementById("place-sup-conflict").value || null,
        company_representative_name: document.getElementById("place-rep-name").value || null,
        company_representative_email: document.getElementById("place-rep-email").value || null,
        start_date: document.getElementById("place-start").value,
        end_date: document.getElementById("place-end").value,
        duration_weeks: parseInt(document.getElementById("place-duration-weeks").value) || 24,
        how_obtained: document.getElementById("place-obtained").value,
        proposed_duties: document.getElementById("place-expected-work").value,
        technical_areas: techAreas,
        expected_work: document.getElementById("place-expected-work").value || null
    };
    
    try {
        if (reqId) {
            await apiRequest(`/api/v1/verification/request/${reqId}`, "PATCH", payload);
            showToast("Placement request draft updated!", "success");
        } else {
            await apiRequest("/api/v1/verification/request", "POST", payload);
            showToast("Placement request draft saved!", "success");
        }
        loadStudentPlacement();
    } catch (err) {}
}

async function submitVerificationRequest() {
    const reqId = document.getElementById("placement-request-id").value;
    if (!reqId) return;
    try {
        const res = await apiRequest(`/api/v1/verification/request/${reqId}/submit`, "POST");
        showToast("Verification request submitted successfully!", "success");
        localStorage.setItem(`invite_token_${reqId}`, res.invitation_token);
        loadStudentPlacement();
    } catch (err) {}
}

function copyInviteLink() {
    const linkInput = document.getElementById("invite-link-url");
    linkInput.select();
    linkInput.setSelectionRange(0, 99999);
    navigator.clipboard.writeText(linkInput.value);
    showToast("Invitation link copied to clipboard!", "success");
}

let currentSelectedWeek = 1;
let loadedEntries = {};

// Helper to calculate start & end dates for a given week based on placementStartDate
function calculateDatesForWeek(weekNum) {
    if (!placementStartDate) return { start: "", end: "" };
    const start = new Date(placementStartDate);
    start.setDate(start.getDate() + (weekNum - 1) * 7);
    const end = new Date(start);
    end.setDate(end.getDate() + 5);
    return {
        start: start.toISOString().split("T")[0],
        end: end.toISOString().split("T")[0]
    };
}

// Select a specific week page
function selectLogbookWeek(weekNum) {
    currentSelectedWeek = weekNum;
    
    // Highlight active button in pagination grid
    document.querySelectorAll(".week-btn").forEach(btn => {
        btn.classList.remove("active");
        if (parseInt(btn.dataset.week) === weekNum) {
            btn.classList.add("active");
        }
    });

    const entry = loadedEntries[weekNum];
    if (entry) {
        loadEntryToForm(entry);
    } else {
        // Prepare new draft for this week
        document.getElementById("logbook-entry-id").value = "";
        document.getElementById("log-week").value = weekNum;
        
        const dates = calculateDatesForWeek(weekNum);
        document.getElementById("log-start").value = dates.start;
        document.getElementById("log-end").value = dates.end;
        
        // Reset inputs
        document.getElementById("log-activities").value = "";
        document.getElementById("log-monday").value = "";
        document.getElementById("log-tuesday").value = "";
        document.getElementById("log-wednesday").value = "";
        document.getElementById("log-thursday").value = "";
        document.getElementById("log-friday").value = "";
        document.getElementById("log-saturday").value = "";
        document.getElementById("log-tools").value = "";
        document.getElementById("log-challenges").value = "";
        document.getElementById("log-outcome").value = "";
        
        // Enable form for editing new draft
        setLogbookFormReadonly(false, "draft");
        
        // Hide AI review section for empty new drafts
        document.getElementById("ai-feedback-card").classList.add("hidden");
    }
}

// Student Dashboard: Load Logbook pages list
async function loadStudentLogbook() {
    let totalWeeks = 24;
    
    try {
        const stats = await apiRequest("/api/v1/dashboard/student");
        if (stats.placement_details) {
            placementStartDate = stats.placement_details.start_date;
        }
        if (stats.total_weeks) {
            totalWeeks = stats.total_weeks;
        }
    } catch (err) {}

    const paginationContainer = document.getElementById("logbook-weeks-pagination");
    if (paginationContainer) {
        paginationContainer.innerHTML = `<p class="empty-text" style="grid-column: span 4;">Loading weeks...</p>`;
    }
    
    try {
        const entries = await apiRequest("/api/v1/logbook-entries/me");
        loadedEntries = {};
        entries.forEach(entry => {
            loadedEntries[entry.week_number] = entry;
        });
        
        if (paginationContainer) {
            paginationContainer.innerHTML = "";
            
            for (let w = 1; w <= totalWeeks; w++) {
                const btn = document.createElement("button");
                btn.type = "button";
                btn.className = "btn week-btn";
                btn.dataset.week = w;
                btn.style.padding = "10px 5px";
                btn.style.fontSize = "0.85rem";
                btn.style.display = "flex";
                btn.style.flexDirection = "column";
                btn.style.alignItems = "center";
                btn.style.gap = "4px";
                
                const entry = loadedEntries[w];
                let statusBadge = "not started";
                let btnClass = "btn-secondary";
                
                if (entry) {
                    statusBadge = entry.status;
                    if (entry.status === "approved") {
                        btnClass = "btn-emerald";
                    } else if (entry.status === "submitted") {
                        btnClass = "btn-teal";
                    } else if (entry.status === "revision_requested" || entry.status === "rejected") {
                        btnClass = "btn-rose";
                    } else {
                        btnClass = "btn-yellow";
                    }
                }
                
                btn.classList.add(btnClass);
                btn.innerHTML = `
                    <strong>W${w}</strong>
                    <span style="font-size: 0.65rem; opacity: 0.85; text-transform: uppercase;">${statusBadge}</span>
                `;
                
                btn.onclick = () => selectLogbookWeek(w);
                paginationContainer.appendChild(btn);
            }
        }
        
        // Select active week page
        selectLogbookWeek(currentSelectedWeek);
        
    } catch (err) {
        if (paginationContainer) {
            paginationContainer.innerHTML = `<p class="empty-text" style="grid-column: span 4;">Failed to load weeks.</p>`;
        }
    }
}

function setLogbookFormReadonly(isReadonly, status) {
    const fields = [
        "log-start", "log-monday", "log-tuesday", "log-wednesday", "log-thursday",
        "log-friday", "log-saturday", "log-activities", "log-tools", "log-challenges", "log-outcome"
    ];
    fields.forEach(f => {
        const el = document.getElementById(f);
        if (el) el.disabled = isReadonly;
    });

    const saveBtn = document.getElementById("btn-save-logbook");
    const submitBtn = document.getElementById("btn-submit-logbook");
    const evidenceForm = document.getElementById("evidence-section");

    if (isReadonly) {
        if (saveBtn) saveBtn.classList.add("hidden");
        if (submitBtn) submitBtn.classList.add("hidden");
        if (evidenceForm) evidenceForm.classList.add("hidden");
    } else {
        if (saveBtn) saveBtn.classList.remove("hidden");
        const entryId = document.getElementById("logbook-entry-id").value;
        if (entryId && (status === "draft" || status === "rejected" || status === "revision_requested")) {
            if (submitBtn) submitBtn.classList.remove("hidden");
            if (evidenceForm) evidenceForm.classList.remove("hidden");
        } else {
            if (submitBtn) submitBtn.classList.add("hidden");
            if (evidenceForm) evidenceForm.classList.add("hidden");
        }
    }
}

// Load individual entry into edit form
function loadEntryToForm(entry) {
    document.getElementById("logbook-entry-id").value = entry.id;
    document.getElementById("log-week").value = entry.week_number;
    document.getElementById("log-start").value = entry.start_date;
    document.getElementById("log-end").value = entry.end_date;
    document.getElementById("log-activities").value = entry.activities;
    document.getElementById("log-monday").value = entry.monday_activity || "";
    document.getElementById("log-tuesday").value = entry.tuesday_activity || "";
    document.getElementById("log-wednesday").value = entry.wednesday_activity || "";
    document.getElementById("log-thursday").value = entry.thursday_activity || "";
    document.getElementById("log-friday").value = entry.friday_activity || "";
    document.getElementById("log-saturday").value = entry.saturday_activity || "";
    document.getElementById("log-tools").value = entry.tools_used || "";
    document.getElementById("log-challenges").value = entry.challenges || "";
    document.getElementById("log-outcome").value = entry.learning_outcome || "";
    
    // Render supervisor feedback if available
    let feedbackBox = document.getElementById("supervisor-feedback-banner");
    if (!feedbackBox) {
        feedbackBox = document.createElement("div");
        feedbackBox.id = "supervisor-feedback-banner";
        feedbackBox.className = "card hidden";
        feedbackBox.style.marginBottom = "16px";
        feedbackBox.style.background = "#FFFBEB";
        feedbackBox.style.border = "1px solid #FDE68A";
        const formHeader = document.querySelector("#logbook-form").parentNode;
        formHeader.insertBefore(feedbackBox, document.querySelector("#logbook-form"));
    }

    if (entry.feedback && entry.feedback.length > 0) {
        const latestFeedback = entry.feedback[entry.feedback.length - 1];
        feedbackBox.innerHTML = `
            <div style="display: flex; gap: 12px; align-items: flex-start;">
                <i class="fa-solid fa-comments" style="font-size: 1.2rem; color: #D97706; margin-top: 2px;"></i>
                <div>
                    <h5 style="margin: 0 0 2px 0; color: #92400E;">Supervisor Review Feedback (${latestFeedback.decision.toUpperCase()})</h5>
                    <p style="margin: 0; font-size: 0.88rem; color: #B45309;">${latestFeedback.comment}</p>
                </div>
            </div>
        `;
        feedbackBox.classList.remove("hidden");
    } else {
        feedbackBox.classList.add("hidden");
    }

    // Toggle evidence form display and form readonly
    const isLocked = entry.status === "approved" || entry.status === "submitted";
    setLogbookFormReadonly(isLocked, entry.status);
    
    // If AI evaluation already exists, display it
    if (entry.ai_reviews && entry.ai_reviews.length > 0) {
        displayAIReviewResults(entry.ai_reviews[entry.ai_reviews.length - 1]);
    } else {
        document.getElementById("ai-feedback-card").classList.add("hidden");
    }
}

// Submit/Save logbook entry draft
async function handleLogbookSubmit(e) {
    e.preventDefault();
    const entryId = document.getElementById("logbook-entry-id").value;
    
    const payload = {
        week_number: parseInt(document.getElementById("log-week").value),
        start_date: document.getElementById("log-start").value,
        end_date: document.getElementById("log-end").value,
        activities: document.getElementById("log-activities").value,
        monday_activity: document.getElementById("log-monday").value || null,
        tuesday_activity: document.getElementById("log-tuesday").value || null,
        wednesday_activity: document.getElementById("log-wednesday").value || null,
        thursday_activity: document.getElementById("log-thursday").value || null,
        friday_activity: document.getElementById("log-friday").value || null,
        saturday_activity: document.getElementById("log-saturday").value || null,
        weekly_summary: document.getElementById("log-activities").value || null,
        tools_used: document.getElementById("log-tools").value || null,
        challenges: document.getElementById("log-challenges").value || null,
        learning_outcome: document.getElementById("log-outcome").value || null
    };
    
    try {
        if (entryId) {
            // Update
            await apiRequest(`/api/v1/logbook-entries/${entryId}`, "PATCH", payload);
            showToast("Logbook draft updated successfully", "success");
        } else {
            // Create
            const entry = await apiRequest("/api/v1/logbook-entries", "POST", payload);
            document.getElementById("logbook-entry-id").value = entry.id;
            document.getElementById("evidence-section").classList.remove("hidden");
            showToast("Logbook draft saved! You can now run AI Assistant or submit.", "success");
        }
        loadStudentLogbook();
    } catch (err) {}
}

// Submit entry to supervisor
async function submitEntryToSupervisor(id) {
    try {
        await apiRequest(`/api/v1/logbook-entries/${id}/submit`, "POST");
        showToast("Logbook entry submitted to your industry supervisor!", "success");
        loadStudentLogbook();
    } catch (err) {}
}

async function submitCurrentEntryToSupervisor() {
    const entryId = document.getElementById("logbook-entry-id").value;
    if (!entryId) {
        showToast("Please save the logbook entry first.", "warning");
        return;
    }
    await submitEntryToSupervisor(entryId);
}


// Upload evidence file
async function handleEvidenceUpload(e) {
    e.preventDefault();
    const entryId = document.getElementById("logbook-entry-id").value;
    if (!entryId) {
        showToast("Please save the logbook draft first.", "warning");
        return;
    }
    
    const fileInput = document.getElementById("evidence-file");
    const formData = new FormData();
    formData.append("file", fileInput.files[0]);
    
    try {
        await apiRequest(`/api/v1/logbook-entries/${entryId}/upload-evidence`, "POST", formData, true);
        showToast("Evidence file uploaded successfully!", "success");
        fileInput.value = "";
    } catch (err) {}
}

// Submit final SIWES report
async function handleFinalReportSubmit(e) {
    e.preventDefault();
    const fileInput = document.getElementById("report-file");
    const formData = new FormData();
    formData.append("file", fileInput.files[0]);
    
    try {
        await apiRequest("/api/v1/reports", "POST", formData, true);
        showToast("Final SIWES report uploaded successfully!", "success");
        fileInput.value = "";
    } catch (err) {}
}

// Run Custom Local AI review
async function runAIReview() {
    const entryId = document.getElementById("logbook-entry-id").value;
    if (!entryId) {
        showToast("Save the logbook entry draft before running the AI review.", "warning");
        return;
    }
    
    showToast("Analyzing logbook entry completeness...", "info");
    
    try {
        const review = await apiRequest(`/api/v1/logbook-entries/${entryId}/ai-review`, "POST");
        displayAIReviewResults(review);
        showToast("Local AI review completed!", "success");
    } catch (err) {}
}

function displayAIReviewResults(review) {
    const card = document.getElementById("ai-feedback-card");
    card.classList.remove("hidden");
    
    document.getElementById("ai-score-val").innerText = `${review.completeness_score}%`;
    document.getElementById("ai-category-val").innerText = review.category;
    document.getElementById("ai-disclaimer").innerText = "Advisory: This local assistant uses heuristics for technical completeness checks. Decisions are determined solely by supervisor assessments.";
    
    const list = document.getElementById("ai-suggestions-list");
    list.innerHTML = "";
    if (review.suggestions.length === 0) {
        list.innerHTML = "<li>Excellent! No suggestions. The entry is technically robust.</li>";
    } else {
        review.suggestions.forEach(s => {
            const li = document.createElement("li");
            li.innerText = s;
            list.appendChild(li);
        });
    }
    
    const repAlert = document.getElementById("ai-repetition-alert");
    if (review.repetition_flag) {
        repAlert.classList.remove("hidden");
    } else {
        repAlert.classList.add("hidden");
    }
}

// SUPERVISOR WORKSPACE: Load Assigned Students
async function loadSupervisorStudents() {
    const tableBody = document.getElementById("supervisor-students-table");
    tableBody.innerHTML = `<tr><td colspan="6" class="text-center">Loading assigned students...</td></tr>`;
    
    try {
        const stats = await apiRequest("/api/v1/dashboard/supervisor");
        document.getElementById("stat-assigned-students").innerText = stats.assigned_students_count;
        document.getElementById("stat-pending-reviews").innerText = stats.pending_reviews_count;
        
        if (stats.students.length === 0) {
            tableBody.innerHTML = `<tr><td colspan="6" class="text-center">No assigned students found.</td></tr>`;
            return;
        }
        
        tableBody.innerHTML = "";
        stats.students.forEach(student => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td>${student.matric_number}</td>
                <td><strong>${student.student_name}</strong></td>
                <td>${student.department}</td>
                <td>${student.completed_weeks} Weeks</td>
                <td><small>${student.latest_activity}</small></td>
                <td><button class="btn btn-primary btn-small" onclick="openSupervisorWorkspace(${student.placement_id}, '${student.student_name}', ${student.duration_weeks || 24})">Grade / Review</button></td>
            `;
            tableBody.appendChild(tr);
        });
    } catch (err) {}
}

// Open Supervisor assessment workspace for student
async function openSupervisorWorkspace(placementId, studentName, durationWeeks = 24) {
    currentPlacementId = placementId;
    document.getElementById("workspace-title").innerText = `Assessing: ${studentName}`;
    document.getElementById("supervisor-review-workspace").classList.remove("hidden");
    
    // Store current workspace placement ID globally for week selector
    window.currentSupervisorPlacementId = placementId;

    // 1. Fetch all submitted entries for this placement to populate week selector
    const workspaceEntries = await apiRequest("/api/v1/logbook-entries/supervisor/entries");
    const studentEntries = workspaceEntries.filter(e => e.placement_id === placementId);
    window.currentSupervisorEntries = studentEntries;

    const select = document.getElementById("supervisor-logbook-week-select");
    select.innerHTML = '<option value="">Select Logbook Week...</option>';
    studentEntries.forEach(e => {
        const opt = document.createElement("option");
        opt.value = e.id;
        opt.innerText = `Week ${e.week_number} (${e.status.toUpperCase()})`;
        select.appendChild(opt);
    });

    const activeEntry = studentEntries.find(e => e.status === "submitted") || studentEntries[studentEntries.length - 1];
    if (activeEntry) {
        select.value = activeEntry.id;
        renderSupervisorLogbookDetail(activeEntry);
    } else {
        document.getElementById("review-log-week").innerText = "-";
        document.getElementById("review-log-dates").innerText = "-";
        document.getElementById("review-log-activities").innerText = "No submitted entries for this student yet.";
        document.getElementById("review-log-tools").innerText = "None";
        document.getElementById("review-log-challenges").innerText = "None";
        document.getElementById("review-log-outcome").innerText = "None";
    }

    // 2. Fetch Final SIWES Report status
    const reportStatus = document.getElementById("sup-final-report-status");
    const reportActions = document.getElementById("sup-final-report-actions");
    reportStatus.innerText = "Checking final report...";
    reportActions.innerHTML = "";

    try {
        const reportRes = await apiRequest(`/api/v1/reports/placement/${placementId}`);
        if (reportRes && reportRes.submitted && reportRes.file_url) {
            reportStatus.innerHTML = `<span class="badge accent-emerald">SUBMITTED (${new Date(reportRes.submitted_at).toLocaleDateString()})</span>`;
            reportActions.innerHTML = `
                <button onclick="openPdfModal('${reportRes.file_url}')" class="btn btn-teal btn-small">
                    <i class="fa-solid fa-eye"></i> Preview Final Report PDF
                </button>
            `;
        } else {
            reportStatus.innerHTML = `<span class="badge text-yellow">NOT SUBMITTED YET</span>`;
        }
    } catch (err) {
        reportStatus.innerText = "Pending submission at end of internship.";
    }

    // 3. Unlock Final Grading Assessment form ONLY IF max approved week >= placement duration (or final week)!
    const maxApprovedWeek = studentEntries.filter(e => e.status === "approved").reduce((max, e) => Math.max(max, e.week_number), 0);
    const targetFinalWeek = durationWeeks || 24;
    const isFinalWeekApproved = maxApprovedWeek > 0 && maxApprovedWeek >= targetFinalWeek;

    const lockedNotice = document.getElementById("sup-final-grading-locked-notice");
    const unlockedPanel = document.getElementById("sup-final-grading-unlocked-panel");
    const lockedMsg = document.getElementById("sup-final-grading-locked-msg");

    if (lockedMsg) {
        lockedMsg.innerHTML = `The Final SIWES Assessment form is locked. It will automatically unlock once you have reviewed and <strong>approved Week ${targetFinalWeek} (the final week of the ${targetFinalWeek}-week internship)</strong>. Currently, highest approved week is <strong>Week ${maxApprovedWeek}</strong>.`;
    }

    if (isFinalWeekApproved) {
        lockedNotice.classList.add("hidden");
        unlockedPanel.classList.remove("hidden");
    } else {
        lockedNotice.classList.remove("hidden");
        unlockedPanel.classList.add("hidden");
    }

    // 4. Fetch existing assessment for this placement if available
    try {
        const assess = await apiRequest(`/api/v1/assessments/placement/${placementId}`);
        if (assess) {
            document.getElementById("grade-punctuality").value = assess.punctuality_score;
            document.getElementById("grade-technical").value = assess.technical_score;
            document.getElementById("grade-communication").value = assess.communication_score;
            document.getElementById("grade-professional").value = assess.professionalism_score;
            if (assess.remarks) document.getElementById("grade-remarks").value = assess.remarks;
        }
    } catch (err) {}
}

function insertSupervisorPresetComment(text) {
    const commentField = document.getElementById("review-comment");
    if (commentField) {
        commentField.value = text;
    }
}

function renderSupervisorLogbookDetail(entry) {
    document.getElementById("review-log-week").innerText = entry.week_number;
    document.getElementById("review-log-dates").innerText = `${entry.start_date} to ${entry.end_date}`;
    document.getElementById("review-log-activities").innerText = entry.activities;
    document.getElementById("review-log-tools").innerText = entry.tools_used || "None";
    document.getElementById("review-log-challenges").innerText = entry.challenges || "None";
    document.getElementById("review-log-outcome").innerText = entry.learning_outcome || "None";
    document.getElementById("review-decision-form").onsubmit = (e) => handleReviewSubmit(e, entry.id);
}

function switchSupervisorLogbookWeekView() {
    const selectedId = parseInt(document.getElementById("supervisor-logbook-week-select").value);
    if (!selectedId) return;
    const entry = (window.currentSupervisorEntries || []).find(e => e.id === selectedId);
    if (entry) renderSupervisorLogbookDetail(entry);
}

async function handleReviewSubmit(e, entryId) {
    e.preventDefault();
    const payload = {
        decision: document.getElementById("review-decision").value,
        score: parseInt(document.getElementById("review-score").value),
        comment: document.getElementById("review-comment").value
    };
    
    try {
        await apiRequest(`/api/v1/logbook-entries/${entryId}/reviews`, "POST", payload);
        showToast("Logbook review submitted!", "success");
        loadSupervisorStudents();
        document.getElementById("supervisor-review-workspace").classList.add("hidden");
    } catch (err) {}
}

async function submitAttendance(e) {
    e.preventDefault();
    const payload = {
        attendance_date: document.getElementById("att-date").value,
        status: document.getElementById("att-status").value,
        note: document.getElementById("att-note").value || null
    };
    
    try {
        await apiRequest(`/api/v1/attendance?placement_id=${currentPlacementId}`, "POST", payload);
        showToast("Attendance recorded successfully", "success");
        document.getElementById("att-date").value = "";
        document.getElementById("att-note").value = "";
    } catch (err) {}
}

async function submitFinalAssessment(e) {
    e.preventDefault();
    const payload = {
        punctuality_score: parseInt(document.getElementById("grade-punctuality").value),
        technical_score: parseInt(document.getElementById("grade-technical").value),
        communication_score: parseInt(document.getElementById("grade-communication").value),
        professionalism_score: parseInt(document.getElementById("grade-professional").value),
        remarks: document.getElementById("grade-remarks").value || null
    };
    
    try {
        await apiRequest(`/api/v1/assessments?placement_id=${currentPlacementId}`, "POST", payload);
        showToast("Draft assessment grades saved!", "success");
    } catch (err) {}
}

async function finalizeAssessment() {
    if (!currentPlacementId) return;
    try {
        // First get the assessment id
        const assess = await apiRequest(`/api/v1/assessments/placement/${currentPlacementId}`);
        await apiRequest(`/api/v1/assessments/${assess.id}/finalize`, "POST");
        showToast("SIWES Assessment finalized and locked!", "success");
        loadSupervisorStudents();
        document.getElementById("supervisor-review-workspace").classList.add("hidden");
    } catch (err) {}
}

// COORDINATOR CONTROL: Load Dashboard
async function loadCoordinatorDashboard() {
    try {
        const stats = await apiRequest("/api/v1/dashboard/coordinator");
        document.getElementById("coord-total-students").innerText = stats.total_students;
        document.getElementById("coord-approved-placements").innerText = stats.approved_placements;
        document.getElementById("coord-pending-placements").innerText = stats.pending_placements;
        document.getElementById("coord-placement-rate").innerText = `${stats.placement_rate_pct}%`;
        
        const riskList = document.getElementById("coordinator-risk-list");
        riskList.innerHTML = "";
        
        if (stats.students_at_risk.length === 0) {
            riskList.innerHTML = `<li class="empty-text">No students flagged as at risk of falling behind.</li>`;
            return;
        }
        
        stats.students_at_risk.forEach(student => {
            const li = document.createElement("li");
            li.innerHTML = `
                <div style="display: flex; justify-content: space-between; width: 100%;">
                    <span><strong>${student.student_name}</strong> (${student.matric_number})</span>
                    <span class="badge accent-rose">${student.completed_weeks} Weeks Logged</span>
                </div>
                <div style="font-size: 0.85rem; color: var(--text-secondary); margin-top: 3px;">
                    Placement at: ${student.organization}
                </div>
            `;
            riskList.appendChild(li);
        });
    } catch (err) {}
}

// COORDINATOR WORKSPACE: Load Placement Verification Queue
async function loadCoordinatorPlacements() {
    const tableBody = document.getElementById("coordinator-placements-table");
    tableBody.innerHTML = `<tr><td colspan="6" class="text-center">Loading verification queue...</td></tr>`;
    
    try {
        const requests = await apiRequest("/api/v1/verification/queue");
        
        if (requests.length === 0) {
            tableBody.innerHTML = `<tr><td colspan="6" class="text-center">No pending placement verifications found.</td></tr>`;
            return;
        }
        
        tableBody.innerHTML = "";
        requests.forEach(r => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td>SIWES-${r.id}</td>
                <td><strong>Verification Candidate</strong></td>
                <td>${r.proposed_company_name}</td>
                <td>${r.proposed_supervisor_name}</td>
                <td><span class="badge accent-yellow">${r.status.toUpperCase()}</span></td>
                <td><button class="btn btn-teal btn-small" onclick="openVerificationReviewPanel(${r.id})">Review Package</button></td>
            `;
            tableBody.appendChild(tr);
        });
    } catch (err) {}
}

async function openVerificationReviewPanel(reqId) {
    document.getElementById("assign-placement-id").value = reqId;
    document.getElementById("coordinator-assign-panel").classList.remove("hidden");
    
    try {
        const req = await apiRequest(`/api/v1/verification/request/${reqId}/detail`);
        
        // 1. Populate comparison table
        const compBody = document.getElementById("coordinator-comparison-table-body");
        compBody.innerHTML = "";
        
        const comparisons = req.comparisons || [];
        if (comparisons.length === 0) {
            compBody.innerHTML = `<tr><td colspan="4" class="text-center text-secondary">No comparisons processed yet. Supervisor has not confirmed details.</td></tr>`;
        } else {
            comparisons.forEach(c => {
                let badgeClass = "accent-yellow";
                if (c.match_status === "MATCH") badgeClass = "accent-emerald";
                else if (c.match_status === "LIKELY_MATCH") badgeClass = "accent-teal";
                else if (c.match_status === "MISMATCH") badgeClass = "accent-rose";
                else if (c.match_status === "CORRECTION") badgeClass = "accent-orange";

                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td><strong>${c.field_name.replace(/_/g, ' ')}</strong></td>
                    <td class="text-secondary">${c.student_value || 'N/A'}</td>
                    <td>${c.supervisor_value || 'N/A'}</td>
                    <td><span class="badge ${badgeClass}">${c.match_status}</span></td>
                `;
                compBody.appendChild(tr);
            });
        }

        // 2. Populate Evidence Details
        const evidenceBox = document.getElementById("coordinator-evidence-details");
        evidenceBox.innerHTML = "";
        const evidenceList = req.evidence || [];
        if (evidenceList.length === 0) {
            evidenceBox.innerHTML = `<p class="empty-text">No evidence uploaded by supervisor yet.</p>`;
        } else {
            evidenceList.forEach(e => {
                const item = document.createElement("div");
                item.style.marginBottom = "10px";
                item.innerHTML = `
                    <p><strong>Type:</strong> ${e.evidence_type}</p>
                    <p><strong>Title:</strong> ${e.title}</p>
                    <p><strong>Issuer:</strong> ${e.issuer_name || 'N/A'} (${e.issuer_contact || 'N/A'})</p>
                    <p><strong>Notes:</strong> <small class="text-secondary">${e.notes || 'No supervisor notes'}</small></p>
                    <div style="display: flex; gap: 8px; margin-top: 8px;">
                        <button onclick="openPdfModal('${e.file_url}')" class="btn btn-teal btn-small">
                            <i class="fa-solid fa-eye"></i> Preview PDF In-App
                        </button>
                        <a href="${e.file_url}" target="_blank" class="btn btn-secondary btn-small">
                            <i class="fa-solid fa-download"></i> Download Document
                        </a>
                    </div>
                `;
                evidenceBox.appendChild(item);
            });
        }

        // 3. Populate Status History / Audit Logs
        const historyBox = document.getElementById("coordinator-history-details");
        historyBox.innerHTML = "";
        const historyList = req.history || [];
        if (historyList.length === 0) {
            historyBox.innerHTML = `<p class="empty-text">No status transitions recorded.</p>`;
        } else {
            historyList.forEach(h => {
                const row = document.createElement("div");
                row.style.borderBottom = "1px solid rgba(255,255,255,0.05)";
                row.style.padding = "5px 0";
                row.innerHTML = `
                    <div style="display: flex; justify-content: space-between;">
                        <strong class="text-teal">${h.new_status.toUpperCase()}</strong>
                        <small class="text-secondary">${new Date(h.created_at).toLocaleString()}</small>
                    </div>
                    <p style="margin: 2px 0 0 0; color: var(--text-secondary);"><small>${h.reason || 'No description'}</small></p>
                `;
                historyBox.appendChild(row);
            });
        }

    } catch (err) {}
}

async function handlePlacementApproval(e) {
    e.preventDefault();
    const reqId = document.getElementById("assign-placement-id").value;
    const payload = {
        decision: document.getElementById("assign-decision").value,
        reason: document.getElementById("assign-reason").value
    };
    
    try {
        await apiRequest(`/api/v1/verification/request/${reqId}/review`, "POST", payload);
        showToast("Placement verification decision submitted!", "success");
        loadCoordinatorPlacements();
        document.getElementById("coordinator-assign-panel").classList.add("hidden");
    } catch (err) {}
}

function autoCalculateSaturday() {
    const startInput = document.getElementById("log-start");
    const endInput = document.getElementById("log-end");
    if (!startInput.value) return;
    
    // Parse the date as UTC/local accurately without timezone shifts
    const parts = startInput.value.split('-');
    const startDate = new Date(parts[0], parts[1] - 1, parts[2]);
    
    // Monday is start, Saturday is 5 days later (Monday + 5 days)
    const endDate = new Date(startDate);
    endDate.setDate(startDate.getDate() + 5);
    
    // Format to YYYY-MM-DD
    const yyyy = endDate.getFullYear();
    const mm = String(endDate.getMonth() + 1).padStart(2, '0');
    const dd = String(endDate.getDate()).padStart(2, '0');
    
    endInput.value = `${yyyy}-${mm}-${dd}`;
}

function autoPopulateDatesByWeek() {
    const weekInput = document.getElementById("log-week");
    const startInput = document.getElementById("log-start");
    
    if (!weekInput.value || !placementStartDate) return;
    
    const weekNum = parseInt(weekInput.value);
    
    // Parse start date accurately
    const parts = placementStartDate.split('-');
    const baseDate = new Date(parts[0], parts[1] - 1, parts[2]);
    
    // Find the Monday of that start week
    const day = baseDate.getDay();
    const diff = baseDate.getDate() - day + (day === 0 ? -6 : 1);
    const mondayOfStart = new Date(baseDate.setDate(diff));
    
    // Add (weekNum - 1) * 7 days to get the Monday of the target week
    const targetMonday = new Date(mondayOfStart);
    targetMonday.setDate(mondayOfStart.getDate() + (weekNum - 1) * 7);
    
    // Format to YYYY-MM-DD
    const yyyy = targetMonday.getFullYear();
    const mm = String(targetMonday.getMonth() + 1).padStart(2, '0');
    const dd = String(targetMonday.getDate()).padStart(2, '0');
    
    startInput.value = `${yyyy}-${mm}-${dd}`;
    autoCalculateSaturday();
}

function compileDailyLogsToSummary() {
    const monday = document.getElementById("log-monday").value.trim();
    const tuesday = document.getElementById("log-tuesday").value.trim();
    const wednesday = document.getElementById("log-wednesday").value.trim();
    const thursday = document.getElementById("log-thursday").value.trim();
    const friday = document.getElementById("log-friday").value.trim();
    const saturday = document.getElementById("log-saturday").value.trim();
    
    let compiled = [];
    if (monday) compiled.push(`Monday: ${monday}`);
    if (tuesday) compiled.push(`Tuesday: ${tuesday}`);
    if (wednesday) compiled.push(`Wednesday: ${wednesday}`);
    if (thursday) compiled.push(`Thursday: ${thursday}`);
    if (friday) compiled.push(`Friday: ${friday}`);
    if (saturday) compiled.push(`Saturday: ${saturday}`);
    
    if (compiled.length === 0) {
        showToast("Please fill in some daily activities first.", "warning");
        return;
    }
    
    document.getElementById("log-activities").value = compiled.join("\n");
    showToast("Weekly summary compiled from daily logs!", "success");
}

// URL Hash Router
async function handleUrlRouting() {
    const hash = window.location.hash;
    if (hash.startsWith("#invite/")) {
        const token = hash.split("/")[1];
        if (!token) return;
        
        // Hide all major screens
        document.getElementById("auth-section").classList.add("hidden");
        document.getElementById("dashboard-section").classList.add("hidden");
        document.getElementById("invite-section").classList.remove("hidden");
        
        try {
            const invite = await apiRequest(`/api/v1/verification/invitation/${token}`);
            document.getElementById("invite-token").value = token;
            document.getElementById("invite-student-name").innerText = invite.student_name;
            document.getElementById("invite-company-name").innerText = invite.proposed_company_name;
        } catch (err) {
            showToast("Invitation link is invalid or has expired.", "danger");
            window.location.hash = "";
            showLoginCard();
        }
    } else {
        document.getElementById("invite-section").classList.add("hidden");
        if (token) {
            initDashboard();
        } else {
            showLoginCard();
        }
    }
}

function showLoginCard() {
    document.getElementById("invite-section").classList.add("hidden");
    document.getElementById("dashboard-section").classList.add("hidden");
    document.getElementById("auth-section").classList.remove("hidden");
    document.getElementById("login-card").classList.remove("hidden");
    document.getElementById("register-card").classList.add("hidden");
}

async function handleInviteAcceptSubmit(e) {
    e.preventDefault();
    const token = document.getElementById("invite-token").value;
    
    const formData = new FormData();
    formData.append("full_name", document.getElementById("invite-fullname").value);
    formData.append("job_title", document.getElementById("invite-job-title").value);
    formData.append("phone", document.getElementById("invite-phone").value);
    formData.append("password", document.getElementById("invite-password").value);
    formData.append("confirm_statement", document.getElementById("invite-confirm-statement").checked);

    try {
        await apiRequest(`/api/v1/verification/invitation/${token}/accept`, "POST", formData, true);
        showToast("Invitation accepted! Please log in to complete verification.", "success");
        window.location.hash = "";
        showLoginCard();
    } catch (err) {}
}

// SUPERVISOR WORKSPACE: Verification Workflow
async function loadSupervisorVerificationQueue() {
    const tableBody = document.getElementById("supervisor-verification-table");
    tableBody.innerHTML = `<tr><td colspan="5" class="text-center">Loading pending requests...</td></tr>`;
    
    try {
        const queue = await apiRequest("/api/v1/verification/supervisor/queue");
        if (queue.length === 0) {
            tableBody.innerHTML = `<tr><td colspan="5" class="text-center">No pending student verification requests found.</td></tr>`;
            return;
        }
        
        tableBody.innerHTML = "";
        queue.forEach(r => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td><strong>Student Candidate</strong></td>
                <td>${r.proposed_company_name}</td>
                <td>${r.expected_work ? r.expected_work.substring(0, 50) + "..." : "N/A"}</td>
                <td><span class="badge accent-yellow">${r.status.toUpperCase()}</span></td>
                <td>
                    <button class="btn btn-primary btn-small" onclick="openSupervisorVerificationWorkspace(${r.id}, 'Student')">Complete Verification</button>
                </td>
            `;
            tableBody.appendChild(tr);
        });
    } catch (err) {}
}

async function openSupervisorVerificationWorkspace(reqId, studentName) {
    document.getElementById("verify-placement-request-id").value = reqId;
    document.getElementById("verify-workspace-student-name").innerText = studentName;
    document.getElementById("supervisor-verify-workspace").classList.remove("hidden");
    
    try {
        const req = await apiRequest(`/api/v1/verification/request/${reqId}/detail`);
        document.getElementById("verify-st-company-name").innerText = req.proposed_company_name;
        document.getElementById("verify-st-company-address").innerText = req.proposed_company_address;
        document.getElementById("verify-st-supervisor-name").innerText = req.proposed_supervisor_name;
        document.getElementById("verify-st-supervisor-title").innerText = req.proposed_supervisor_job_title;
        document.getElementById("verify-st-start-date").innerText = req.start_date;
        document.getElementById("verify-st-end-date").innerText = req.end_date;
        document.getElementById("verify-st-duration-weeks").innerText = `${req.duration_weeks} Weeks`;
        document.getElementById("corr-duration-weeks").value = req.duration_weeks;
    } catch (err) {}
}

function toggleVerifyCorrection(field) {
    const isChecked = document.getElementById(`chk-confirm-${field}`).checked;
    const corrGroup = document.getElementById(`corr-group-${field}`);
    if (isChecked) {
        corrGroup.classList.add("hidden");
    } else {
        corrGroup.classList.remove("hidden");
    }
}

async function submitSupervisorVerification(e) {
    e.preventDefault();
    const reqId = document.getElementById("verify-placement-request-id").value;
    
    const fields = ["company-name", "company-address", "supervisor-name", "supervisor-title", "start-date", "end-date", "duration-weeks"];
    const confirmations = {};
    const corrections = {};
    
    fields.forEach(f => {
        const isChecked = document.getElementById(`chk-confirm-${f}`).checked;
        confirmations[f.replace(/-/g, '_')] = isChecked;
        if (!isChecked) {
            corrections[f.replace(/-/g, '_')] = document.getElementById(`corr-${f}`).value;
        } else {
            corrections[f.replace(/-/g, '_')] = "";
        }
    });

    const formData = new FormData();
    formData.append("evidence_type", document.getElementById("verify-evidence-type").value);
    formData.append("title", document.getElementById("verify-evidence-title").value);
    formData.append("issuer_name", document.getElementById("verify-evidence-issuer").value || "");
    formData.append("issuer_contact", document.getElementById("verify-evidence-contact").value || "");
    formData.append("notes", document.getElementById("verify-evidence-notes").value || "");
    formData.append("field_confirmations", JSON.stringify(confirmations));
    formData.append("field_corrections", JSON.stringify(corrections));
    
    const fileInput = document.getElementById("verify-evidence-file");
    if (fileInput.files.length > 0) {
        formData.append("file", fileInput.files[0]);
    }

    try {
        await apiRequest(`/api/v1/verification/request/${reqId}/confirm`, "POST", formData, true);
        showToast("Verification package submitted successfully!", "success");
        document.getElementById("supervisor-verify-workspace").classList.add("hidden");
        loadSupervisorVerificationQueue();
    } catch (err) {}
}

// Notifications dropdown toggle
function toggleNotificationDropdown(e) {
    if (e) e.stopPropagation();
    const dropdown = document.getElementById("notification-dropdown");
    dropdown.classList.toggle("hidden");
    if (!dropdown.classList.contains("hidden")) {
        loadInAppNotifications();
    }
}

async function loadInAppNotifications() {
    try {
        const notifs = await apiRequest("/api/v1/verification/notifications");
        const badge = document.getElementById("notification-badge-count");
        const list = document.getElementById("notification-items-list");
        
        const unreadCount = notifs.filter(n => !n.read_at).length;
        if (unreadCount > 0) {
            badge.innerText = unreadCount;
            badge.classList.remove("hidden");
        } else {
            badge.classList.add("hidden");
        }

        if (notifs.length === 0) {
            list.innerHTML = `<p class="empty-text" style="padding: 15px; margin: 0; font-size: 0.8rem; text-align: center;">No new alerts.</p>`;
            return;
        }

        list.innerHTML = "";
        notifs.forEach(n => {
            const item = document.createElement("div");
            item.style.padding = "10px 15px";
            item.style.borderBottom = "1px solid rgba(255,255,255,0.03)";
            item.style.background = n.read_at ? "transparent" : "rgba(255, 255, 255, 0.02)";
            item.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                    <strong style="font-size: 0.85rem; color: #fff;">${n.title}</strong>
                    <small style="font-size: 0.7rem; color: var(--text-secondary);">${new Date(n.created_at).toLocaleTimeString()}</small>
                </div>
                <p style="margin: 5px 0 0 0; font-size: 0.8rem; color: var(--text-secondary); line-height: 1.3;">${n.message}</p>
            `;
            // Add click-to-read
            if (!n.read_at) {
                item.style.cursor = "pointer";
                item.onclick = async () => {
                    await apiRequest(`/api/v1/verification/notifications/${n.id}/read`, "POST");
                    loadInAppNotifications();
                };
            }
            list.appendChild(item);
        });
    } catch (err) {}
}

async function markAllNotificationsRead(e) {
    if (e) e.stopPropagation();
    try {
        const notifs = await apiRequest("/api/v1/verification/notifications");
        const unreads = notifs.filter(n => !n.read_at);
        for (let n of unreads) {
            await apiRequest(`/api/v1/verification/notifications/${n.id}/read`, "POST");
        }
        showToast("All notifications cleared!", "success");
        loadInAppNotifications();
    } catch (err) {}
}

// Academic Sessions callbacks
async function loadCoordinatorSessions() {
    const tableBody = document.getElementById("coordinator-sessions-table-body");
    tableBody.innerHTML = `<tr><td colspan="3" class="text-center">Loading sessions...</td></tr>`;
    try {
        const sessions = await apiRequest("/api/v1/sessions");
        if (sessions.length === 0) {
            tableBody.innerHTML = `<tr><td colspan="3" class="text-center">No academic sessions created yet.</td></tr>`;
            return;
        }
        tableBody.innerHTML = "";
        sessions.forEach(s => {
            const tr = document.createElement("tr");
            const isAct = s.status === "active";
            tr.innerHTML = `
                <td><strong>${s.name}</strong></td>
                <td><span class="badge ${isAct ? 'accent-emerald' : 'accent-yellow'}">${s.status.toUpperCase()}</span></td>
                <td>
                    ${isAct ? '<span class="text-secondary">Current Active</span>' : `<button class="btn btn-teal btn-small" onclick="activateSession(${s.id})">Activate</button>`}
                </td>
            `;
            tableBody.appendChild(tr);
        });
    } catch (err) {}
}

async function handleCreateSession(e) {
    e.preventDefault();
    const payload = {
        name: document.getElementById("sess-name").value,
        registration_start: document.getElementById("sess-reg-start").value,
        registration_end: document.getElementById("sess-reg-end").value,
        placement_deadline: document.getElementById("sess-place-dead").value,
        assessment_deadline: document.getElementById("sess-assess-dead").value
    };
    try {
        await apiRequest("/api/v1/sessions", "POST", payload);
        showToast("Academic session created successfully!", "success");
        document.getElementById("create-session-form").reset();
        loadCoordinatorSessions();
    } catch (err) {}
}

async function activateSession(sessId) {
    try {
        await apiRequest(`/api/v1/sessions/${sessId}/activate`, "POST");
        showToast("Academic session activated!", "success");
        loadCoordinatorSessions();
    } catch (err) {}
}

// Student Identity Verification list
async function loadCoordinatorStudentsList() {
    const tableBody = document.getElementById("coordinator-students-table-body");
    tableBody.innerHTML = `<tr><td colspan="5" class="text-center">Loading student directory...</td></tr>`;
    try {
        const students = await apiRequest("/api/v1/verification/students");
        if (students.length === 0) {
            tableBody.innerHTML = `<tr><td colspan="5" class="text-center">No registered students found.</td></tr>`;
            return;
        }
        tableBody.innerHTML = "";
        students.forEach(s => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td>${s.matric_number}</td>
                <td><strong>${s.full_name}</strong></td>
                <td>${s.email}</td>
                <td><span class="badge ${s.is_verified ? 'accent-emerald' : 'accent-yellow'}">${s.is_verified ? 'VERIFIED' : 'UNVERIFIED'}</span></td>
                <td>
                    ${s.is_verified ? '<span class="text-secondary"><i class="fa-solid fa-circle-check text-emerald"></i> Identity Confirmed</span>' : `<button class="btn btn-primary btn-small" onclick="verifyStudentProfile(${s.id})">Confirm Identity</button>`}
                </td>
            `;
            tableBody.appendChild(tr);
        });
    } catch (err) {}
}

async function verifyStudentProfile(studentId) {
    try {
        await apiRequest(`/api/v1/verification/students/${studentId}/verify`, "POST");
        showToast("Student identity confirmed!", "success");
        loadCoordinatorStudentsList();
    } catch (err) {}
}

// Student Appeals handler
async function handleAppealSubmit(e) {
    e.preventDefault();
    const reqId = document.getElementById("placement-request-id").value;
    const formData = new FormData();
    formData.append("appeal_description", document.getElementById("appeal-text").value);
    try {
        await apiRequest(`/api/v1/verification/request/${reqId}/appeal`, "POST", formData, true);
        showToast("Appeal submitted successfully! Re-entered verification queue.", "success");
        document.getElementById("appeal-form").reset();
        loadStudentPlacement();
    } catch (err) {}
}

// Close notifications when clicking elsewhere
document.addEventListener("click", () => {
    document.getElementById("notification-dropdown").classList.add("hidden");
});

// PDF In-App Preview Modal Handler
function openPdfModal(url) {
    let modal = document.getElementById("pdf-preview-modal");
    if (!modal) {
        modal = document.createElement("div");
        modal.id = "pdf-preview-modal";
        modal.style.position = "fixed";
        modal.style.top = "0";
        modal.style.left = "0";
        modal.style.width = "100vw";
        modal.style.height = "100vh";
        modal.style.backgroundColor = "rgba(0, 0, 0, 0.85)";
        modal.style.zIndex = "99999";
        modal.style.display = "flex";
        modal.style.flexDirection = "column";
        modal.style.alignItems = "center";
        modal.style.justifyContent = "center";
        modal.style.padding = "20px";

        modal.innerHTML = `
            <div style="width: 90%; max-width: 900px; height: 85vh; background: #0f172a; border-radius: 12px; display: flex; flex-direction: column; overflow: hidden; border: 1px solid rgba(255,255,255,0.1);">
                <div style="display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; background: #1e293b; color: #fff;">
                    <strong style="font-size: 1rem;"><i class="fa-solid fa-file-pdf text-rose"></i> In-App Document Evidence Viewer</strong>
                    <button onclick="closePdfModal()" class="btn btn-secondary btn-small"><i class="fa-solid fa-xmark"></i> Close</button>
                </div>
                <iframe id="pdf-modal-iframe" style="width: 100%; height: 100%; border: none;" src=""></iframe>
            </div>
        `;
        document.body.appendChild(modal);
    }
    document.getElementById("pdf-modal-iframe").src = url;
    modal.style.display = "flex";
}

function closePdfModal() {
    const modal = document.getElementById("pdf-preview-modal");
    if (modal) {
        modal.style.display = "none";
        document.getElementById("pdf-modal-iframe").src = "";
    }
}

// Export Departmental Grades CSV
async function exportGradesCSV() {
    showToast("Preparing Departmental Grades Matrix CSV...", "info");
    try {
        const response = await fetch("/api/v1/reports/export/csv", {
            headers: { "Authorization": `Bearer ${token}` }
        });
        if (!response.ok) {
            throw new Error("Failed to export CSV. Permission denied.");
        }
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "SIWES_Departmental_Grades_Matrix.csv";
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
    } catch (err) {
        showToast(err.message, "error");
    }
}

// Initial Bootup
window.addEventListener("hashchange", handleUrlRouting);
handleUrlRouting();

// Set interval to periodically fetch notifications
setInterval(loadInAppNotifications, 30000);
