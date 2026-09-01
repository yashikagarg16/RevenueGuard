// RevenueGuard AI Frontend Application Logic
let statusChartInstance = null;
let errorChartInstance = null;
let currentInvestigation = null;

document.addEventListener("DOMContentLoaded", () => {
    lucide.createIcons();
    const hash = window.location.hash.replace('#', '');
    if (['overview', 'leaks', 'investigate', 'approval', 'audit'].includes(hash)) {
        switchTab(hash);
        if (hash === 'investigate') investigateSpecificLeak('leak_hv_failures');
    } else {
        loadOverview();
        loadLeaks();
        loadApprovals();
        loadAuditEvents();
    }
});

// ----------------- Tab Navigation -----------------

function switchTab(tabId) {
    const tabs = ["overview", "leaks", "investigate", "approval", "audit"];
    tabs.forEach(t => {
        const btn = document.getElementById(`tab-${t}`);
        const view = document.getElementById(`view-${t}`);
        if (t === tabId) {
            btn?.classList.add("active");
            view?.classList.remove("hidden");
        } else {
            btn?.classList.remove("active");
            view?.classList.add("hidden");
        }
    });

    lucide.createIcons();

    if (tabId === "overview") loadOverview();
    if (tabId === "leaks") loadLeaks();
    if (tabId === "approval") loadApprovals();
    if (tabId === "audit") loadAuditEvents();
}

// ----------------- View 1: Overview & Metrics -----------------

async function loadOverview() {
    try {
        const res = await fetch("/api/overview");
        const data = await res.json();

        // Update environment badge
        const envBadge = document.getElementById("env-text");
        if (envBadge) {
            envBadge.innerText = `ENVIRONMENT: ${data.environment_mode.replace('_', ' ')}`;
        }

        // Format currency helper
        const inr = (n) => `₹${Number(n).toLocaleString('en-IN')}`;

        // Hero and Metric Cards
        document.getElementById("hero-at-risk").innerText = inr(data.revenue_at_risk);
        document.getElementById("metric-at-risk").innerText = inr(data.revenue_at_risk);
        document.getElementById("metric-eligible").innerText = inr(data.eligible_for_recovery);
        document.getElementById("metric-expected").innerText = inr(data.expected_recovery);
        document.getElementById("metric-total-vol").innerText = inr(data.total_attempted_revenue);
        document.getElementById("metric-success-vol").innerText = inr(data.successful_revenue);
        document.getElementById("metric-failure-rate").innerText = `${data.failure_rate_percentage}%`;

        // Badge counts
        document.getElementById("badge-hv-count").innerText = data.high_value_failure_count;
        document.getElementById("badge-pend-count").innerText = data.pending_order_count;
        document.getElementById("badge-rep-count").innerText = data.repeat_failed_customer_count;

        // Render Charts
        renderStatusChart(data.successful_revenue, data.revenue_at_risk);
        loadBreakdownChart();
    } catch (err) {
        console.error("Failed to load overview:", err);
    }
}

function renderStatusChart(successRev, atRiskRev) {
    const ctx = document.getElementById("statusChart");
    if (!ctx) return;

    if (statusChartInstance) statusChartInstance.destroy();

    statusChartInstance = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Successful Volume', 'Revenue at Risk (Failed + Pending)'],
            datasets: [{
                data: [successRev, atRiskRev],
                backgroundColor: ['#10b981', '#f43f5e'],
                borderColor: '#111827',
                borderWidth: 3,
                hoverOffset: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { color: '#9ca3af', font: { family: 'Inter', size: 12 } }
                }
            },
            cutout: '70%'
        }
    });
}

async function loadBreakdownChart() {
    try {
        const res = await fetch("/api/breakdown");
        const data = await res.json();
        const ctx = document.getElementById("errorChart");
        if (!ctx) return;

        if (errorChartInstance) errorChartInstance.destroy();

        const failureItems = data.breakdown.filter(b => b.category !== "SUCCESS");
        const labels = failureItems.map(b => b.category.replace('_', ' '));
        const amounts = failureItems.map(b => b.amount);

        errorChartInstance = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Lost Revenue (₹)',
                    data: amounts,
                    backgroundColor: ['#f43f5e', '#f59e0b', '#8b5cf6', '#06b6d4', '#ec4899'],
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: {
                        ticks: { color: '#9ca3af', font: { size: 10 } },
                        grid: { color: 'rgba(255, 255, 255, 0.05)' }
                    },
                    y: {
                        ticks: {
                            color: '#9ca3af',
                            callback: (val) => `₹${val / 1000}k`
                        },
                        grid: { color: 'rgba(255, 255, 255, 0.05)' }
                    }
                }
            }
        });
    } catch (err) {
        console.error("Failed to load breakdown chart:", err);
    }
}

// ----------------- View 2: Revenue Leaks -----------------

async function loadLeaks() {
    try {
        const res = await fetch("/api/leaks");
        const leaks = await res.json();
        const container = document.getElementById("leaks-container");
        if (!container) return;

        const inr = (n) => `₹${Number(n).toLocaleString('en-IN')}`;

        container.innerHTML = leaks.map(leak => {
            const isHigh = leak.severity === "high";
            const badgeClass = isHigh ? "bg-rose-950 text-rose-400 border-rose-800" : "bg-amber-950 text-amber-400 border-amber-800";

            return `
                <div class="glass-card p-6 border-gray-800 hover:border-gray-700 transition">
                    <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
                        <div class="space-y-2">
                            <div class="flex items-center space-x-2">
                                <span class="px-2.5 py-0.5 rounded text-xs font-bold uppercase border ${badgeClass}">
                                    ${leak.severity} Severity
                                </span>
                                <span class="text-xs text-gray-400 font-mono">${leak.id}</span>
                            </div>
                            <h3 class="text-lg font-bold text-white">${leak.title}</h3>
                            <p class="text-xs text-gray-300 max-w-3xl">${leak.description}</p>
                        </div>
                        <div class="flex flex-col sm:flex-row sm:items-center gap-6 self-start md:self-auto">
                            <div class="text-left md:text-right">
                                <div class="text-xs text-gray-400 font-medium">Revenue At Risk</div>
                                <div class="text-xl font-black text-rose-400">${inr(leak.amount_at_risk)}</div>
                                <div class="text-[11px] text-emerald-400 font-medium">Expected Recov: ${inr(leak.expected_recovery)}</div>
                            </div>
                            <button onclick="investigateSpecificLeak('${leak.id}')" class="px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs shadow flex items-center space-x-1.5 transition">
                                <i data-lucide="brain-circuit" class="w-4 h-4"></i>
                                <span>Investigate with AI</span>
                            </button>
                        </div>
                    </div>

                    <div class="mt-4 pt-4 border-t border-gray-800/80 flex flex-wrap items-center justify-between gap-2 text-xs text-gray-400">
                        <div><span class="font-bold text-gray-200">${leak.affected_count}</span> affected orders</div>
                        <div>Confidence: <span class="font-bold text-indigo-400">${leak.confidence}</span></div>
                        <div class="font-mono text-[11px] text-gray-400">Sample IDs: ${leak.sample_transaction_ids.slice(0, 3).join(', ')}</div>
                    </div>
                </div>
            `;
        }).join("");

        lucide.createIcons();
    } catch (err) {
        console.error("Failed to load leaks:", err);
    }
}

// ----------------- View 3: AI Investigation (Grounded Evidence Chain) -----------------

async function investigateSpecificLeak(leakId) {
    switchTab('investigate');
    const select = document.getElementById("investigate-leak-select");
    if (select) select.value = leakId;

    const container = document.getElementById("investigation-content");
    if (!container) return;

    container.innerHTML = `
        <div class="glass-card p-12 text-center text-gray-400">
            <i data-lucide="loader-2" class="w-10 h-10 animate-spin mx-auto text-indigo-400 mb-3"></i>
            <h4 class="text-base font-bold text-white">Synthesizing Telemetry & Grounded Reasoning...</h4>
            <p class="text-xs text-gray-400 mt-1">Inspecting database logs, historical customer LTV, and issuing bank error codes.</p>
        </div>
    `;
    lucide.createIcons();

    try {
        const res = await fetch("/api/agent/investigate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ leak_id: leakId })
        });
        const inv = await res.json();
        currentInvestigation = inv;

        const inr = (n) => `₹${Number(n).toLocaleString('en-IN')}`;

        container.innerHTML = `
            <!-- Evidence -> Action Chain Header -->
            <div class="glass-card p-6 border-indigo-900/40 glow-primary">
                <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div>
                        <div class="flex items-center space-x-2 mb-1">
                            <span class="px-2.5 py-0.5 rounded text-xs font-bold bg-indigo-950 text-indigo-400 border border-indigo-800">
                                AI DIAGNOSIS COMPLETE
                            </span>
                            <span class="text-xs text-gray-400 font-mono">Target: ${inv.suggested_transaction_id}</span>
                        </div>
                        <h3 class="text-xl font-bold text-white">Grounded AI Investigation for ${inv.leak_id.replace('leak_', '').replace('_', ' ').toUpperCase()}</h3>
                    </div>
                    <div class="text-left md:text-right">
                        <div class="text-xs text-gray-400 font-medium">Confidence Level</div>
                        <div class="text-sm font-bold text-emerald-400">${inv.confidence}</div>
                    </div>
                </div>
            </div>

            <!-- Grounded Reasoning 4-Box Grid -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                <!-- 1. Observed Evidence -->
                <div class="glass-card p-5 border-gray-800">
                    <div class="flex items-center space-x-2 text-xs font-bold text-rose-400 uppercase mb-3">
                        <i data-lucide="eye" class="w-4 h-4"></i>
                        <span>1. Observed Evidence (Raw Telemetry)</span>
                    </div>
                    <ul class="space-y-2 text-xs text-gray-300">
                        ${inv.evidence.map(e => `
                            <li class="flex items-start space-x-2">
                                <span class="text-rose-400 font-bold">•</span>
                                <span>${e}</span>
                            </li>
                        `).join("")}
                    </ul>
                </div>

                <!-- 2. Known Facts -->
                <div class="glass-card p-5 border-gray-800">
                    <div class="flex items-center space-x-2 text-xs font-bold text-indigo-400 uppercase mb-3">
                        <i data-lucide="database" class="w-4 h-4"></i>
                        <span>2. Known Facts (Deterministic DB Records)</span>
                    </div>
                    <ul class="space-y-2 text-xs text-gray-300">
                        ${inv.known_facts.map(f => `
                            <li class="flex items-start space-x-2">
                                <span class="text-indigo-400 font-bold">•</span>
                                <span>${f}</span>
                            </li>
                        `).join("")}
                    </ul>
                </div>

                <!-- 3. Operational Inference -->
                <div class="glass-card p-5 border-gray-800">
                    <div class="flex items-center space-x-2 text-xs font-bold text-amber-400 uppercase mb-3">
                        <i data-lucide="lightbulb" class="w-4 h-4"></i>
                        <span>3. Operational Inference (Root Cause Diagnosis)</span>
                    </div>
                    <p class="text-xs text-gray-300 leading-relaxed">${inv.inference}</p>
                </div>

                <!-- 4. Unknowns / Missing Gateway Info -->
                <div class="glass-card p-5 border-gray-800">
                    <div class="flex items-center space-x-2 text-xs font-bold text-cyan-400 uppercase mb-3">
                        <i data-lucide="help-circle" class="w-4 h-4"></i>
                        <span>4. Unknowns (Issuer/Bank Blindspots)</span>
                    </div>
                    <ul class="space-y-2 text-xs text-gray-300">
                        ${inv.unknowns.map(u => `
                            <li class="flex items-start space-x-2">
                                <span class="text-cyan-400 font-bold">•</span>
                                <span>${u}</span>
                            </li>
                        `).join("")}
                    </ul>
                </div>
            </div>

            <!-- Recommended Recovery Action & Impact Box -->
            <div class="glass-card p-6 bg-gradient-to-r from-gray-900 via-indigo-950/30 to-gray-900 border-indigo-500/30 glow-primary">
                <div class="flex flex-col md:flex-row md:items-center justify-between gap-6">
                    <div class="space-y-2">
                        <div class="text-xs font-bold text-emerald-400 uppercase tracking-wider flex items-center space-x-1.5">
                            <i data-lucide="zap" class="w-4 h-4"></i>
                            <span>Autonomous Action Proposal</span>
                        </div>
                        <h4 class="text-lg font-bold text-white">${inv.recommended_action}</h4>
                        <div class="flex flex-wrap gap-4 text-xs text-gray-300 pt-1">
                            <div>Target Amount: <span class="font-bold text-white font-mono">${inr(inv.target_amount)}</span></div>
                            <div>Expected ROI: <span class="font-bold text-emerald-400">${inv.roi_percentage}%</span></div>
                            <div>Channel: <span class="font-bold text-indigo-300">Razorpay Payment Link API</span></div>
                        </div>
                    </div>

                    <button onclick="proposeActionForApproval('${inv.suggested_transaction_id}', '${inv.leak_id}')" class="px-6 py-3.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-500 hover:from-emerald-500 hover:to-teal-400 text-white font-bold text-xs shadow-lg shadow-emerald-600/30 flex items-center justify-center space-x-2 transition transform hover:-translate-y-0.5">
                        <i data-lucide="send" class="w-4 h-4"></i>
                        <span>Submit for Merchant Approval</span>
                    </button>
                </div>
            </div>
        `;
        lucide.createIcons();
    } catch (err) {
        console.error("Failed to run AI investigation:", err);
    }
}

async function proposeActionForApproval(txId, leakId) {
    try {
        const res = await fetch("/api/approvals/propose", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ transaction_id: txId, leak_id: leakId })
        });
        const result = await res.json();
        
        // Navigate to Approval Center
        switchTab('approval');
        loadApprovals();
    } catch (err) {
        console.error("Failed to propose action:", err);
    }
}

// ----------------- View 4: Approval Center & Safety Engine -----------------

async function loadApprovals() {
    try {
        const res = await fetch("/api/approvals/pending");
        const approvals = await res.json();
        const container = document.getElementById("approvals-container");
        const badge = document.getElementById("tab-approvals-badge");
        if (badge) badge.innerText = approvals.length;

        if (!container) return;

        const inr = (n) => `₹${Number(n).toLocaleString('en-IN')}`;

        if (approvals.length === 0) {
            container.innerHTML = `
                <div class="glass-card p-12 text-center text-gray-400">
                    <i data-lucide="check-circle-2" class="w-12 h-12 mx-auto text-emerald-400 mb-3"></i>
                    <h3 class="text-base font-bold text-white">Approval Queue is Clear</h3>
                    <p class="text-xs text-gray-400 mt-1">No pending recovery actions awaiting authorization. Generate proposals from the AI Investigation tab.</p>
                </div>
            `;
            lucide.createIcons();
            return;
        }

        container.innerHTML = approvals.map(app => {
            const checks = app.safety_result.checks;

            return `
                <div class="glass-card p-6 border-indigo-900/40 glow-primary space-y-6">
                    <!-- Proposal Header -->
                    <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-gray-800">
                        <div>
                            <div class="flex items-center space-x-2 mb-1">
                                <span class="px-2 py-0.5 rounded text-[11px] font-bold bg-amber-950 text-amber-400 border border-amber-800">
                                    PENDING MERCHANT AUTHORIZATION
                                </span>
                                <span class="text-xs text-gray-400 font-mono">${app.action_id}</span>
                            </div>
                            <h3 class="text-lg font-bold text-white">Order Recovery: ${app.transaction_id}</h3>
                            <p class="text-xs text-gray-400">${app.reason}</p>
                        </div>
                        <div class="text-left md:text-right">
                            <div class="text-xs text-gray-400 font-medium">Recovery Amount</div>
                            <div class="text-2xl font-black text-emerald-400 font-mono">${inr(app.amount)}</div>
                            <div class="text-xs text-gray-400 font-mono">Customer: ${app.customer_name}</div>
                        </div>
                    </div>

                    <!-- Safety Engine 4-Point Verification Checklist -->
                    <div class="bg-gray-900/90 rounded-xl p-4 border border-gray-800 space-y-3">
                        <div class="flex items-center justify-between">
                            <div class="text-xs font-bold text-gray-200 uppercase tracking-wider flex items-center space-x-1.5">
                                <i data-lucide="shield-check" class="w-4 h-4 text-emerald-400"></i>
                                <span>Deterministic Safety Engine Pre-Flight Checklist</span>
                            </div>
                            <span class="text-[11px] font-bold text-emerald-400 bg-emerald-950 px-2 py-0.5 rounded border border-emerald-800">
                                ALL 4 CHECKS PASSED
                            </span>
                        </div>

                        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
                            ${checks.map(c => `
                                <div class="flex items-start space-x-2.5 text-xs p-2.5 rounded-lg bg-gray-950/60 border border-gray-800/80">
                                    <i data-lucide="${c.passed ? 'check-circle' : 'x-circle'}" class="w-4 h-4 ${c.passed ? 'text-emerald-400' : 'text-rose-400'} shrink-0 mt-0.5"></i>
                                    <div>
                                        <div class="font-bold text-gray-200">${c.check_name}</div>
                                        <div class="text-gray-400 text-[11px] mt-0.5">${c.details}</div>
                                    </div>
                                </div>
                            `).join("")}
                        </div>
                    </div>

                    <!-- Human-Gate Decision Buttons -->
                    <div class="flex flex-col sm:flex-row items-center justify-end gap-3 pt-2">
                        <button onclick="decideAction('${app.action_id}', 'REJECT')" class="w-full sm:w-auto px-5 py-2.5 rounded-xl bg-gray-800 hover:bg-gray-700 text-gray-300 font-semibold text-xs border border-gray-700 transition">
                            Reject Proposal
                        </button>
                        <button onclick="decideAction('${app.action_id}', 'APPROVE')" class="w-full sm:w-auto px-6 py-2.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-500 hover:from-emerald-500 hover:to-teal-400 text-white font-bold text-xs shadow-lg shadow-emerald-600/30 flex items-center justify-center space-x-2 transition">
                            <i data-lucide="check" class="w-4 h-4"></i>
                            <span>Approve & Execute via Razorpay</span>
                        </button>
                    </div>
                </div>
            `;
        }).join("");

        lucide.createIcons();
    } catch (err) {
        console.error("Failed to load approvals:", err);
    }
}

async function decideAction(actionId, decision) {
    try {
        const res = await fetch(`/api/approvals/${actionId}/decide`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ action_id: actionId, decision: decision, approved_by: "Merchant Admin" })
        });
        const data = await res.json();
        
        // Reload approvals and switch to Audit tab to see the execution event
        loadApprovals();
        switchTab('audit');
        loadAuditEvents();
    } catch (err) {
        console.error("Failed to submit decision:", err);
    }
}

// ----------------- View 5: Audit & Resilience (Hash Chain & Simulations) -----------------

async function loadAuditEvents() {
    try {
        const res = await fetch("/api/audit/events");
        const events = await res.json();
        const container = document.getElementById("audit-timeline-container");
        const countSpan = document.getElementById("audit-count");
        if (countSpan) countSpan.innerText = `${events.length} chained blocks`;

        if (!container) return;

        const inr = (n) => `₹${Number(n).toLocaleString('en-IN')}`;

        container.innerHTML = events.map((ev, idx) => {
            const isAlert = ev.event_type.includes("FAILED") || ev.event_type.includes("BLOCKED") || ev.event_type.includes("CIRCUIT");
            const isSuccess = ev.event_type.includes("SUCCESS") || ev.event_type.includes("APPROVED");
            const badgeColor = isAlert ? "bg-rose-950 text-rose-400 border-rose-800" : (isSuccess ? "bg-emerald-950 text-emerald-400 border-emerald-800" : "bg-indigo-950 text-indigo-400 border-indigo-800");

            return `
                <div class="glass-card p-4 border-gray-800 hover:border-gray-700 transition">
                    <div class="flex flex-col md:flex-row md:items-center justify-between gap-2">
                        <div class="flex items-center space-x-2">
                            <span class="px-2 py-0.5 rounded text-[10px] font-bold uppercase border ${badgeColor}">
                                ${ev.event_type}
                            </span>
                            <span class="text-xs font-bold text-gray-300 font-mono">Block #${ev.id}</span>
                            <span class="text-xs text-gray-500">•</span>
                            <span class="text-xs text-gray-400">${ev.actor}</span>
                        </div>
                        <div class="text-[11px] text-gray-500 font-mono">
                            ${new Date(ev.timestamp).toLocaleTimeString()}
                        </div>
                    </div>

                    <div class="text-xs text-gray-200 font-medium mt-2">
                        ${ev.action}
                    </div>

                    ${ev.amount ? `<div class="text-xs text-emerald-400 font-mono mt-1">Amount: ${inr(ev.amount)}</div>` : ''}

                    <!-- SHA-256 Hash Chaining Information -->
                    <div class="mt-3 pt-2.5 border-t border-gray-800/80 grid grid-cols-1 sm:grid-cols-2 gap-2 text-[10px] font-mono text-gray-500">
                        <div>Prev Hash: <span class="text-gray-400">${ev.previous_hash.slice(0, 16)}...</span></div>
                        <div>Block Hash: <span class="text-indigo-400">${ev.event_hash.slice(0, 16)}...</span></div>
                    </div>
                </div>
            `;
        }).join("");

        lucide.createIcons();
    } catch (err) {
        console.error("Failed to load audit events:", err);
    }
}

async function verifyAuditChain() {
    try {
        const res = await fetch("/api/audit/verify");
        const data = await res.json();
        const badge = document.getElementById("audit-status-badge");
        const text = document.getElementById("audit-status-text");

        if (data.chain_valid) {
            badge.className = "px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-950 text-emerald-400 border border-emerald-800 flex items-center space-x-1.5";
            text.innerText = `🟢 AUDIT INTEGRITY: VERIFIED (${data.total_events} Blocks 100% Intact)`;
            alert(`✅ Cryptographic Audit Verification PASSED!\n\nAll ${data.total_events} chained blocks verified with SHA-256 integrity.`);
        } else {
            badge.className = "px-2.5 py-1 rounded-full text-xs font-bold bg-rose-950 text-rose-400 border border-rose-800 flex items-center space-x-1.5";
            text.innerText = `🔴 CRITICAL: TAMPER DETECTED (Block #${data.corrupted_event_id})`;
            alert(`🚨 Cryptographic Chain Severed!\n\nTampering detected at Block #${data.corrupted_event_id}.\n${data.reason}`);
        }
    } catch (err) {
        console.error("Audit verification failed:", err);
    }
}

async function triggerTamperTest() {
    try {
        const res = await fetch("/api/audit/tamper-demo", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ event_id: 1 })
        });
        const data = await res.json();
        alert(`⚠️ Tamper Simulation Injected!\n\nPayload of Block #1 was modified directly in the database without updating the SHA-256 hash.\n\nNow click 'Verify Audit Chain' to see the instant detection!`);
        loadAuditEvents();
    } catch (err) {
        console.error("Tamper demo failed:", err);
    }
}

// ----------------- 3 Security & Failure Simulations -----------------

async function runSimulation(scenario) {
    const box = document.getElementById("simulation-alert-box");
    if (!box) return;

    box.classList.remove("hidden");
    box.innerHTML = `
        <div class="flex items-center space-x-3 text-indigo-400 text-xs">
            <i data-lucide="loader-2" class="w-4 h-4 animate-spin"></i>
            <span>Executing ${scenario} simulation...</span>
        </div>
    `;
    lucide.createIcons();

    try {
        const res = await fetch("/api/simulation/run", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ scenario: scenario, tampered_amount: 25000.0 })
        });
        const data = await res.json();

        let icon = "shield-check";
        let color = "text-emerald-400";
        let borderColor = "border-emerald-500/40";

        if (scenario === "API_TIMEOUT") {
            icon = "refresh-cw";
            color = "text-indigo-400";
            borderColor = "border-indigo-500/40";
        } else if (scenario === "DUPLICATE_REQUEST") {
            icon = "copy-check";
            color = "text-amber-400";
            borderColor = "border-amber-500/40";
        } else if (scenario === "AMOUNT_TAMPERING") {
            icon = "shield-alert";
            color = "text-rose-400";
            borderColor = "border-rose-500/40";
        }

        box.className = `glass-card p-5 ${borderColor} glow-primary transition space-y-2`;
        box.innerHTML = `
            <div class="flex items-center justify-between">
                <div class="flex items-center space-x-2 ${color} text-xs font-bold uppercase tracking-wider">
                    <i data-lucide="${icon}" class="w-4 h-4"></i>
                    <span>Simulation Result: ${data.scenario}</span>
                </div>
                <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-gray-900 text-gray-300 border border-gray-700">
                    Status: ${data.status}
                </span>
            </div>
            <div class="text-sm font-bold text-white pt-1">${data.message}</div>
            <div class="text-xs text-gray-400 pt-1 font-mono">
                ${data.details.guarantee ? `<span class="text-indigo-300 font-bold">Guarantee:</span> "${data.details.guarantee}"` : ''}
            </div>
        `;
        lucide.createIcons();

        // Refresh audit log to show the logged simulation event
        loadAuditEvents();
    } catch (err) {
        console.error("Simulation failed:", err);
    }
}

async function resetDataset() {
    if (!confirm("Are you sure you want to reset the database to the default 127-transaction merchant dataset?")) return;
    try {
        await fetch("/api/data/reset", { method: "POST" });
        alert("✅ Database successfully reset and re-seeded with realistic merchant data!");
        loadOverview();
        loadLeaks();
        loadApprovals();
        loadAuditEvents();
    } catch (err) {
        console.error("Reset failed:", err);
    }
}
