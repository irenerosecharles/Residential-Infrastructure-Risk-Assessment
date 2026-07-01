const API_BASE = "http://localhost:8000";

// App State
let properties = [];
let selectedProperty = null;
let selectedRoomId = null;

// Chart Instances
let riskHistoryChart = null;
let defectDoughnutChart = null;

// DOM Elements
const propertyList = document.getElementById("propertyList");
const selectedPropertyName = document.getElementById("selectedPropertyName");
const selectedPropertyAddress = document.getElementById("selectedPropertyAddress");
const overallRiskScoreText = document.getElementById("overallRiskScoreText");
const overallRiskGaugeFill = document.getElementById("overallRiskGaugeFill");
const overallRiskStatusBadge = document.getElementById("overallRiskStatusBadge");
const trendProjectedText = document.getElementById("trendProjectedText");
const trendDescriptionText = document.getElementById("trendDescriptionText");
const activeDefectsText = document.getElementById("activeDefectsText");
const defectsSubtitleText = document.getElementById("defectsSubtitleText");
const overrideRateText = document.getElementById("overrideRateText");
const overrideCountText = document.getElementById("overrideCountText");
const roomsGrid = document.getElementById("roomsGrid");

// Inspection Workspace DOM Elements
const inspectionWorkspace = document.getElementById("inspectionWorkspace");
const currentInspectionRoomName = document.getElementById("currentInspectionRoomName");
const btnCloseWorkspace = document.getElementById("btnCloseWorkspace");
const inspectionForm = document.getElementById("inspectionForm");
const formRoomId = document.getElementById("formRoomId");
const uploadZone = document.getElementById("uploadZone");
const fileInput = document.getElementById("fileInput");
const uploadInner = document.getElementById("uploadInner");
const previewContainer = document.getElementById("previewContainer");
const imagePreview = document.getElementById("imagePreview");
const btnRemovePreview = document.getElementById("btnRemovePreview");
const notesText = document.getElementById("notesText");
const btnSubmitInspection = document.getElementById("btnSubmitInspection");

// Outputs DOM Elements
const outputEmptyState = document.getElementById("outputEmptyState");
const pipelineLoader = document.getElementById("pipelineLoader");
const pipelineStatusText = document.getElementById("pipelineStatusText");
const validationWarningCard = document.getElementById("validationWarningCard");
const valSceneText = document.getElementById("valSceneText");
const valConfidenceText = document.getElementById("valConfidenceText");
const valReasonText = document.getElementById("valReasonText");
const aiResultsBlock = document.getElementById("aiResultsBlock");
const resDefectClass = document.getElementById("resDefectClass");
const resSeverityBadge = document.getElementById("resSeverityBadge");
const resConfidenceFill = document.getElementById("resConfidenceFill");
const resConfidenceText = document.getElementById("resConfidenceText");
const resRagCodesList = document.getElementById("resRagCodesList");
const resRecommendationText = document.getElementById("resRecommendationText");
const roomFindingsList = document.getElementById("roomFindingsList");
const existingFindingsBox = document.getElementById("existingFindingsBox");
const timelineFeed = document.getElementById("timelineFeed");
const btnExportPdf = document.getElementById("btnExportPdf");

// HITL Override Form Elements
const overrideForm = document.getElementById("overrideForm");
const overrideFindingId = document.getElementById("overrideFindingId");
const overrideDefectClass = document.getElementById("overrideDefectClass");
const overrideSeverity = document.getElementById("overrideSeverity");
const overrideReason = document.getElementById("overrideReason");

/* ==========================================================================
   Initialization
   ========================================================================== */

document.addEventListener("DOMContentLoaded", () => {
    init();
    setupEventListeners();
});

function init() {
    fetchProperties();
}

function setupEventListeners() {
    // Workspace Close
    btnCloseWorkspace.addEventListener("click", () => {
        inspectionWorkspace.style.display = "none";
        selectedRoomId = null;
        renderRooms();
    });

    // File Upload Handler
    uploadZone.addEventListener("click", () => fileInput.click());
    fileInput.addEventListener("change", handleFileSelect);
    
    // Drag & Drop
    uploadZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        uploadZone.style.borderColor = "var(--primary)";
    });
    uploadZone.addEventListener("dragleave", () => {
        uploadZone.style.borderColor = "rgba(255, 255, 255, 0.1)";
    });
    uploadZone.addEventListener("drop", (e) => {
        e.preventDefault();
        uploadZone.style.borderColor = "rgba(255, 255, 255, 0.1)";
        if (e.dataTransfer.files.length) {
            fileInput.files = e.dataTransfer.files;
            handleFileSelect();
        }
    });

    btnRemovePreview.addEventListener("click", (e) => {
        e.stopPropagation();
        resetUploadPreview();
    });

    // Form Submissions
    inspectionForm.addEventListener("submit", submitInspection);
    overrideForm.addEventListener("submit", submitOverride);
    
    // PDF Export
    btnExportPdf.addEventListener("click", exportPdf);
}

/* ==========================================================================
   Data Fetching & Rendering
   ========================================================================== */

async function fetchProperties() {
    try {
        const response = await fetch(`${API_BASE}/api/properties`);
        properties = await response.json();
        renderSidebarProperties();
        if (properties.length > 0) {
            selectProperty(properties[0].id);
        }
    } catch (error) {
        console.error("Error fetching properties:", error);
    }
}

function renderSidebarProperties() {
    propertyList.innerHTML = "";
    properties.forEach(p => {
        const item = document.createElement("li");
        item.className = `property-item ${selectedProperty && selectedProperty.id === p.id ? 'active' : ''}`;
        
        let riskClass = "OK";
        if (p.overall_risk_score >= 70) riskClass = "Critical";
        else if (p.overall_risk_score >= 45) riskClass = "High";
        else if (p.overall_risk_score >= 20) riskClass = "Medium";
        
        item.innerHTML = `
            <span class="property-name">${p.name}</span>
            <span class="property-address">${p.address}</span>
            <span class="property-risk-badge status-badge ${riskClass}">${riskClass}: ${p.overall_risk_score.toFixed(1)}</span>
        `;
        item.addEventListener("click", () => selectProperty(p.id));
        propertyList.appendChild(item);
    });
}

async function selectProperty(propertyId) {
    try {
        const response = await fetch(`${API_BASE}/api/properties/${propertyId}`);
        selectedProperty = await response.json();
        
        // Update active class in sidebar
        renderSidebarProperties();
        
        // Update property details on screen
        selectedPropertyName.innerText = selectedProperty.name;
        selectedPropertyAddress.innerText = selectedProperty.address;
        
        // Dynamic KPIs and Charts
        animateRiskScoreGauge(selectedProperty.overall_risk_score);
        renderKPIs();
        drawCharts();
        renderRooms();
        renderTimeline();
        
        // Hide Workspace if property switches
        if (selectedRoomId) {
            const hasRoom = selectedProperty.rooms.some(r => r.id === selectedRoomId);
            if (!hasRoom) {
                inspectionWorkspace.style.display = "none";
                selectedRoomId = null;
            } else {
                // Update selected room details
                const activeRoom = selectedProperty.rooms.find(r => r.id === selectedRoomId);
                renderRoomFindings(activeRoom);
            }
        }
    } catch (error) {
        console.error("Error loading property details:", error);
    }
}

/* ==========================================================================
   KPIs & Score Animations
   ========================================================================== */

function animateRiskScoreGauge(targetScore) {
    // 1. Text number counting animation
    let currentScore = parseFloat(overallRiskScoreText.innerText) || 0.0;
    const duration = 1000; // 1 second
    const steps = 60;
    const increment = (targetScore - currentScore) / steps;
    let stepCount = 0;
    
    const interval = setInterval(() => {
        currentScore += increment;
        stepCount++;
        overallRiskScoreText.innerText = currentScore.toFixed(1);
        
        if (stepCount >= steps) {
            clearInterval(interval);
            overallRiskScoreText.innerText = targetScore.toFixed(1);
        }
    }, duration / steps);

    // 2. Gauge SVG circular dash fill animation
    const circumference = 2 * Math.PI * 40; // 251.2
    overallRiskGaugeFill.style.strokeDasharray = circumference;
    const offset = circumference - (targetScore / 100.0) * circumference;
    
    // Set status styling class
    let riskClass = "OK";
    let color = "var(--risk-ok)";
    if (targetScore >= 70) {
        riskClass = "Critical";
        color = "var(--risk-critical)";
    } else if (targetScore >= 45) {
        riskClass = "High";
        color = "var(--risk-high)";
    } else if (targetScore >= 20) {
        riskClass = "Medium";
        color = "var(--risk-medium)";
    }
    
    overallRiskGaugeFill.style.stroke = color;
    overallRiskGaugeFill.style.strokeDashoffset = offset;
    overallRiskStatusBadge.className = `status-badge ${riskClass}`;
    overallRiskStatusBadge.innerText = riskClass;
}

function renderKPIs() {
    // Trend Forecast
    const trends = selectedProperty.trends;
    trendProjectedText.innerText = trends.trend_direction;
    trendDescriptionText.innerText = trends.trend_description;
    
    // Stylize Trend Color
    trendProjectedText.className = "metric-value";
    if (trends.trend_direction === "Increasing") {
        trendProjectedText.classList.add("tag-crit");
    } else if (trends.trend_direction === "Decreasing") {
        trendProjectedText.classList.add("tag-ok");
    } else {
        trendProjectedText.classList.add("text-glow");
    }

    // Active Defects
    let defectCount = 0;
    let overrideCount = 0;
    let totalDetections = 0;
    
    selectedProperty.rooms.forEach(r => {
        defectCount += r.findings.length;
        r.findings.forEach(f => {
            totalDetections++;
            if (f.is_overridden) {
                overrideCount++;
            }
        });
    });
    
    activeDefectsText.innerText = defectCount;
    defectsSubtitleText.innerText = `${selectedProperty.rooms.length} rooms inspected`;

    // Overrides
    overrideCountText.innerText = `${overrideCount} override(s) logged`;
    if (totalDetections > 0) {
        const rate = (overrideCount / totalDetections) * 100;
        overrideRateText.innerText = `${rate.toFixed(0)}%`;
    } else {
        overrideRateText.innerText = "0%";
    }
}

/* ==========================================================================
   Room Selection Grid
   ========================================================================== */

function renderRooms() {
    roomsGrid.innerHTML = "";
    selectedProperty.rooms.forEach(r => {
        const card = document.createElement("div");
        card.className = `room-card ${selectedRoomId === r.id ? 'active' : ''}`;
        
        let color = "var(--risk-ok)";
        if (r.status === "Critical") color = "var(--risk-critical)";
        else if (r.status === "High") color = "var(--risk-high)";
        else if (r.status === "Medium") color = "var(--risk-medium)";
        
        card.innerHTML = `
            <div class="room-header">
                <span class="room-title">${r.name}</span>
                <span class="room-multiplier" title="Score multiplier based on safety importance">${r.importance_multiplier.toFixed(1)}x mult</span>
            </div>
            <div class="room-risk-box">
                <span class="room-risk-val">${r.current_risk_score.toFixed(1)}</span>
                <span class="gauge-max">risk</span>
                <span class="status-badge ${r.status}" style="margin-left:auto; font-size:9px; padding:2px 6px;">${r.status}</span>
            </div>
            <div class="room-status-bar">
                <div class="room-status-bar-fill" style="width: ${r.current_risk_score}%; background-color: ${color};"></div>
            </div>
        `;
        
        card.addEventListener("click", () => selectRoom(r.id));
        roomsGrid.appendChild(card);
    });
}

function selectRoom(roomId) {
    selectedRoomId = roomId;
    renderRooms();
    
    const activeRoom = selectedProperty.rooms.find(r => r.id === roomId);
    
    // Open Inspection Workspace
    inspectionWorkspace.style.display = "block";
    currentInspectionRoomName.innerText = activeRoom.name;
    formRoomId.value = roomId;
    
    // Clear outputs block to default empty state
    resetPipelineStepper();
    outputEmptyState.style.display = "flex";
    pipelineLoader.style.display = "none";
    validationWarningCard.style.display = "none";
    aiResultsBlock.style.display = "none";
    
    resetUploadPreview();
    notesText.value = "";
    
    // Load findings
    renderRoomFindings(activeRoom);
    
    // Scroll workspace into view smoothly
    inspectionWorkspace.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function renderRoomFindings(room) {
    roomFindingsList.innerHTML = "";
    
    if (room.findings.length === 0) {
        existingFindingsBox.style.display = "none";
        return;
    }
    
    existingFindingsBox.style.display = "block";
    
    room.findings.forEach(f => {
        const item = document.createElement("div");
        item.className = "finding-item";
        
        const isOverridden = f.is_overridden === 1 || f.is_overridden === true;
        const severity = isOverridden ? f.inspector_severity : f.ai_severity;
        const defectClass = isOverridden ? f.inspector_defect_class : f.ai_defect_class;
        
        let codeBadgesHtml = "";
        if (f.retrieved_codes && f.retrieved_codes.length > 0) {
            codeBadgesHtml = f.retrieved_codes.map(c => `<span class="badge info">${c}</span>`).join(" ");
        }
        
        let overrideHtml = "";
        if (isOverridden) {
            overrideHtml = `
                <div class="finding-recs" style="background:rgba(239, 68, 68, 0.02); color:var(--risk-critical); border:1px solid rgba(239, 68, 68, 0.1); margin-top:8px;">
                    <strong>HITL Override by ${f.override_by || 'Inspector'}:</strong> Changed category/severity.<br/>
                    <i>Reason: ${f.override_reason}</i>
                </div>
            `;
        }
        
        // Build image path. If relative, prefix API base url
        const imgPath = f.image_url.startsWith("http") ? f.image_url : `${API_BASE}${f.image_url}`;
        
        item.innerHTML = `
            <img src="${imgPath}" class="finding-img" alt="Inspection photo">
            <div class="finding-details">
                <div class="finding-meta">
                    <span class="status-badge ${severity}">${severity}</span>
                    <span class="finding-timestamp">${f.timestamp.replace("T", " ").replace("Z", "")}</span>
                </div>
                <strong class="room-title" style="font-size:13px; color:var(--text-primary); margin-top:2px;">${defectClass}</strong>
                <p class="finding-notes">"${f.notes_text}"</p>
                <div class="finding-recs">
                    <strong>AI Recommendation:</strong> ${f.ai_recommendation}
                </div>
                ${overrideHtml}
                <div class="finding-tag-group" style="margin-top:6px;">
                    <span class="badge info">Confidence: ${(f.ai_confidence * 100).toFixed(0)}%</span>
                    ${codeBadgesHtml}
                    ${f.repeat_count > 1 ? `<span class="badge bg-red">Repeated issue (x${f.repeat_count})</span>` : ''}
                </div>
            </div>
        `;
        
        roomFindingsList.appendChild(item);
    });
}

/* ==========================================================================
   Image Validation & Inspection Upload Pipeline
   ========================================================================== */

function handleFileSelect() {
    const file = fileInput.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = (e) => {
            imagePreview.src = e.target.result;
            previewContainer.style.display = "block";
            uploadInner.style.display = "none";
            
            // Mark step 0 (Upload) as complete
            setPipelineStep(0, "success");
        };
        reader.readAsDataURL(file);
    }
}

function resetUploadPreview() {
    fileInput.value = "";
    imagePreview.src = "";
    previewContainer.style.display = "none";
    uploadInner.style.display = "flex";
    setPipelineStep(0, "idle");
}

function resetPipelineStepper() {
    for (let i = 0; i <= 5; i++) {
        setPipelineStep(i, "idle");
    }
}

function setPipelineStep(index, status) {
    const steps = document.querySelectorAll(".pipeline-step");
    if (steps[index]) {
        steps[index].className = `pipeline-step ${status}`;
    }
}

async function submitInspection(e) {
    e.preventDefault();
    if (!selectedRoomId) return;
    if (!fileInput.files.length) {
        alert("Please upload an inspection image to continue.");
        return;
    }
    
    // UI Loading state
    outputEmptyState.style.display = "none";
    validationWarningCard.style.display = "none";
    aiResultsBlock.style.display = "none";
    pipelineLoader.style.display = "flex";
    
    // Disable submit
    btnSubmitInspection.disabled = true;
    btnSubmitInspection.innerText = "Analyzing Workspace...";

    const formData = new FormData(inspectionForm);
    
    try {
        // Step 1: Validation loading state
        setPipelineStep(1, "active");
        pipelineStatusText.innerText = "Running Stage 0: Content Validation...";
        
        const response = await fetch(`${API_BASE}/api/properties/inspect`, {
            method: "POST",
            body: formData
        });
        
        const result = await response.json();
        
        if (!result.success) {
            // Stage 0: Validation Failed
            setPipelineStep(1, "failed");
            pipelineLoader.style.display = "none";
            
            validationWarningCard.style.display = "block";
            valSceneText.innerText = result.scene_type || "Invalid Target";
            valConfidenceText.innerText = `${((result.confidence || 0.0) * 100).toFixed(0)}%`;
            valReasonText.innerText = result.reason;
            
            // Update buttons
            btnSubmitInspection.disabled = false;
            btnSubmitInspection.innerText = "Run Intelligent Inspection";
            return;
        }
        
        // Stage 0 Validated
        setPipelineStep(1, "success");
        
        // Trigger Stage 1 & 2 loading
        setPipelineStep(2, "active");
        pipelineStatusText.innerText = "Running Stage 1: Gemini Multimodal Vision...";
        await sleep(800); // Visual pacing
        setPipelineStep(2, "success");
        
        setPipelineStep(3, "active");
        pipelineStatusText.innerText = "Running Stage 2: Guidelines Vector RAG Query...";
        await sleep(600);
        setPipelineStep(3, "success");
        
        setPipelineStep(4, "active");
        pipelineStatusText.innerText = "Running Stage 3: LLM Contextual Synthesis...";
        await sleep(800);
        setPipelineStep(4, "success");
        
        setPipelineStep(5, "active");
        pipelineStatusText.innerText = "Running risk score engine & trend calculations...";
        await sleep(500);
        setPipelineStep(5, "success");
        
        // Hide loader & show results
        pipelineLoader.style.display = "none";
        aiResultsBlock.style.display = "block";
        
        // Render Defect results
        const defect = result.defect_analysis;
        resDefectClass.innerText = defect.defect_class;
        resSeverityBadge.innerText = defect.severity;
        resSeverityBadge.className = `status-badge ${defect.severity}`;
        
        // Confidence bar representation
        const confPercent = `${(defect.confidence * 100).toFixed(0)}%`;
        resConfidenceText.innerText = confPercent;
        resConfidenceFill.style.width = confPercent;
        
        // RAG references list
        resRagCodesList.innerHTML = "";
        result.retrieved_codes.forEach(c => {
            const card = document.createElement("div");
            card.className = "rag-code-card";
            card.innerHTML = `
                <div class="rag-code-header">
                    <span>${c.code} &mdash; ${c.category}</span>
                    <span class="status-badge ${c.severity}" style="font-size:8px; padding:1px 5px;">${c.severity}</span>
                </div>
                <strong>${c.title}</strong>
                <p class="rag-code-desc">${c.description}</p>
            `;
            resRagCodesList.appendChild(card);
        });
        
        // RAG recommendation
        resRecommendationText.innerText = result.synthesis.recommendation;
        
        // Configure Override Form
        overrideFindingId.value = result.finding_id;
        overrideDefectClass.value = defect.defect_class;
        overrideSeverity.value = defect.severity;
        overrideReason.value = "";
        
        // Reload overall property scores and charts
        await selectProperty(selectedProperty.id);
        
    } catch (error) {
        console.error("Error during room inspection pipeline:", error);
        alert("An error occurred during inspection analysis.");
        pipelineLoader.style.display = "none";
        outputEmptyState.style.display = "flex";
        resetPipelineStepper();
    } finally {
        btnSubmitInspection.disabled = false;
        btnSubmitInspection.innerText = "Run Intelligent Inspection";
    }
}

/* ==========================================================================
   Human-in-the-Loop Overrides
   ========================================================================== */

async function submitOverride(e) {
    e.preventDefault();
    const findingId = overrideFindingId.value;
    const defect = overrideDefectClass.value;
    const severity = overrideSeverity.value;
    const reason = overrideReason.value;
    
    if (!findingId || !reason) {
        alert("Please fill out override justification parameters.");
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/api/properties/override`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                finding_id: findingId,
                inspector_defect_class: defect,
                inspector_severity: severity,
                override_reason: reason
            })
        });
        
        const res = await response.json();
        if (res.success) {
            alert("Inspector override successfully logged to governance timeline.");
            
            // Reload property
            await selectProperty(selectedProperty.id);
            
            // Re-select room to refresh findings
            if (selectedRoomId) {
                const activeRoom = selectedProperty.rooms.find(r => r.id === selectedRoomId);
                renderRoomFindings(activeRoom);
            }
        }
    } catch (error) {
        console.error("Error submitting override:", error);
        alert("Failed to submit override data.");
    }
}

/* ==========================================================================
   Timeline / Audit Logs
   ========================================================================== */

function renderTimeline() {
    timelineFeed.innerHTML = "";
    if (selectedProperty.timeline.length === 0) {
        timelineFeed.innerHTML = "<p style='color:var(--text-muted); font-size:13px; text-align:center;'>No audit events logged.</p>";
        return;
    }
    
    selectedProperty.timeline.forEach(t => {
        const node = document.createElement("div");
        node.className = `timeline-node ${t.event_type}`;
        
        const cleanTime = t.timestamp.replace("T", " ").replace("Z", "");
        
        node.innerHTML = `
            <div class="timeline-dot"></div>
            <div class="timeline-content">
                <div class="timeline-time">${cleanTime}</div>
                <div class="timeline-text">${t.message}</div>
            </div>
        `;
        timelineFeed.appendChild(node);
    });
}

/* ==========================================================================
   Chart Rendering (Chart.js)
   ========================================================================== */

function drawCharts() {
    // 1. History & Trend Prediction Line Chart
    const historyLogs = selectedProperty.risk_history || [];
    const trends = selectedProperty.trends || {};
    
    const labels = historyLogs.map(h => {
        const date = new Date(h.timestamp);
        return date.toLocaleDateString(undefined, {month: 'short', day: 'numeric', hour: '2-digit'});
    });
    const dataPoints = historyLogs.map(h => h.score);
    
    // Add trend prediction dotted lines if forecast exists
    let trendLabels = [...labels];
    let trendPoints = historyLogs.map(h => null); // Keep historical points empty in prediction dataset
    
    if (trends.projection_data && trends.projection_data.length > 0) {
        // Find forecast points
        const projPoints = trends.projection_data;
        // Last historic score connects to first forecast point
        trendPoints[trendPoints.length - 1] = dataPoints[dataPoints.length - 1];
        
        projPoints.slice(1).forEach(pt => {
            const date = new Date(pt.timestamp);
            trendLabels.push(date.toLocaleDateString(undefined, {month: 'short', day: 'numeric'}) + " (Proj)");
            trendPoints.push(pt.score);
            dataPoints.push(null); // Keep history points empty during projection dataset
        });
    }

    if (riskHistoryChart) riskHistoryChart.destroy();
    const ctxHistory = document.getElementById("riskHistoryChart").getContext("2d");
    riskHistoryChart = new Chart(ctxHistory, {
        type: 'line',
        data: {
            labels: trendLabels,
            datasets: [
                {
                    label: 'Historical Risk Score',
                    data: dataPoints,
                    borderColor: '#0ea5e9',
                    backgroundColor: 'rgba(14, 165, 233, 0.05)',
                    fill: true,
                    tension: 0.2,
                    spanGaps: true
                },
                {
                    label: 'Projected Trend (NumPy Regression)',
                    data: trendPoints,
                    borderColor: '#f59e0b',
                    backgroundColor: 'transparent',
                    borderDash: [6, 6],
                    tension: 0,
                    spanGaps: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { labels: { color: '#9ca3af', font: { family: 'Inter' } } }
            },
            scales: {
                x: { grid: { color: 'rgba(255, 255, 255, 0.04)' }, ticks: { color: '#6b7280' } },
                y: { min: 0, max: 100, grid: { color: 'rgba(255, 255, 255, 0.04)' }, ticks: { color: '#6b7280' } }
            }
        }
    });

    // 2. Defect Category breakdown Doughnut Chart
    const categories = {
        "Electrical Safety": 0,
        "Structural Integrity": 0,
        "Water Damage & Dampness": 0,
        "Fire Safety": 0,
        "Mechanical & Plumbing": 0,
        "Quality & Finish": 0
    };
    
    selectedProperty.rooms.forEach(r => {
        r.findings.forEach(f => {
            const cat = f.is_overridden ? f.inspector_defect_class : f.ai_defect_class;
            if (categories.hasOwnProperty(cat)) {
                categories[cat]++;
            }
        });
    });
    
    const doughnutLabels = Object.keys(categories).filter(k => categories[k] > 0);
    const doughnutData = doughnutLabels.map(k => categories[k]);

    if (defectDoughnutChart) defectDoughnutChart.destroy();
    const ctxDoughnut = document.getElementById("defectDoughnutChart").getContext("2d");
    
    if (doughnutLabels.length === 0) {
        // Draw empty helper doughnut
        defectDoughnutChart = new Chart(ctxDoughnut, {
            type: 'doughnut',
            data: {
                labels: ['Clear / Safe'],
                datasets: [{ data: [1], backgroundColor: ['rgba(255, 255, 255, 0.02)'], borderColor: ['rgba(255, 255, 255, 0.05)'] }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } }
            }
        });
    } else {
        defectDoughnutChart = new Chart(ctxDoughnut, {
            type: 'doughnut',
            data: {
                labels: doughnutLabels,
                datasets: [{
                    data: doughnutData,
                    backgroundColor: [
                        '#f87171', // Red
                        '#fbbf24', // Yellow
                        '#38bdf8', // Blue
                        '#34d399', // Emerald
                        '#a78bfa', // Purple
                        '#fb923c'  // Orange
                    ],
                    borderColor: '#0b0f19',
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: { color: '#9ca3af', boxWidth: 12, font: { family: 'Inter', size: 10 } }
                    }
                }
            }
        });
    }
}

/* ==========================================================================
   PDF Exporter
   ========================================================================== */

function exportPdf() {
    if (!selectedProperty) return;
    window.location.href = `${API_BASE}/api/properties/${selectedProperty.id}/export`;
}

/* ==========================================================================
   Utilities
   ========================================================================== */

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}
