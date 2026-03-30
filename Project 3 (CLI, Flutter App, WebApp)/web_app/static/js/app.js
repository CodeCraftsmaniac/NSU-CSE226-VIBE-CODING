"use strict";
/**
 * NSU Degree Audit - Premium Web Application
 * Real-time OCR scanning with level-wise analysis display
 * 
 * Connects to Cloud Run backend API
 */

// ─── API Configuration ─────────────────────────────────────────────────────────
// Cloud Run Backend API
const API_BASE_URL = 'https://ocrapi.nsunexus.app';

// ─── DOM Elements ──────────────────────────────────────────────────────────────
const uploadArea = document.getElementById('upload-area');
const fileInput = document.getElementById('file-input');
const uploadSection = document.getElementById('upload-section');
const scanningSection = document.getElementById('scanning-section');
const resultsSection = document.getElementById('results-section');
const extractedTextEl = document.getElementById('extracted-text');
const scanProgress = document.getElementById('scan-progress');
const progressText = document.getElementById('progress-text');
const toast = document.getElementById('toast');
const heroContent = document.querySelector('.hero-content');
const restartBtn = document.getElementById('btn-restart');

let analysisData = null;
let elapsedTimerInterval = null;
let processingStartTime = null;
let currentUploadController = null;
let currentUploadedFile = null; // Store file for preview

// ─── Initialization ────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    initUpload();
    initTabs();
    initParticles();
    initRestartButton();
    initCancelButton();
});

// ─── Particle Background ───────────────────────────────────────────────────────
function initParticles() {
    const canvas = document.getElementById('particle-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let w, h, particles = [];

    function resize() {
        w = canvas.width = window.innerWidth;
        h = canvas.height = window.innerHeight;
    }
    resize();
    window.addEventListener('resize', resize);

    const PARTICLE_COUNT = 55;
    for (let i = 0; i < PARTICLE_COUNT; i++) {
        particles.push({
            x: Math.random() * window.innerWidth,
            y: Math.random() * window.innerHeight,
            r: Math.random() * 1.5 + 0.3,
            dx: (Math.random() - 0.5) * 0.3,
            dy: (Math.random() - 0.5) * 0.3,
            o: Math.random() * 0.4 + 0.1,
            gold: Math.random() < 0.25
        });
    }

    function draw() {
        ctx.clearRect(0, 0, w, h);
        particles.forEach(p => {
            p.x += p.dx;
            p.y += p.dy;
            if (p.x < 0) p.x = w;
            if (p.x > w) p.x = 0;
            if (p.y < 0) p.y = h;
            if (p.y > h) p.y = 0;
            ctx.beginPath();
            ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
            ctx.fillStyle = p.gold
                ? `rgba(56,189,248,${p.o})`
                : `rgba(100,140,255,${p.o})`;
            ctx.fill();
        });
        // Draw connection lines between close particles
        for (let i = 0; i < particles.length; i++) {
            for (let j = i + 1; j < particles.length; j++) {
                const dx = particles[i].x - particles[j].x;
                const dy = particles[i].y - particles[j].y;
                const dist = Math.sqrt(dx * dx + dy * dy);
                if (dist < 120) {
                    ctx.beginPath();
                    ctx.moveTo(particles[i].x, particles[i].y);
                    ctx.lineTo(particles[j].x, particles[j].y);
                    const alpha = (1 - dist / 120) * 0.06;
                    ctx.strokeStyle = `rgba(0,82,155,${alpha})`;
                    ctx.lineWidth = 0.8;
                    ctx.stroke();
                }
            }
        }
        requestAnimationFrame(draw);
    }
    draw();
}

function initUpload() {
    uploadArea.addEventListener('click', () => fileInput.click());

    fileInput.addEventListener('change', (e) => {
        const target = e.target;
        if (target.files && target.files.length > 0) {
            handleFile(target.files[0]);
        }
    });

    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });

    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragover');
    });

    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        if (e.dataTransfer?.files.length) {
            handleFile(e.dataTransfer.files[0]);
        }
    });
}

function initTabs() {
    document.querySelectorAll('.level-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            const level = tab.dataset.level;
            switchLevel(level);
        });
    });
}

// ─── File Handling ─────────────────────────────────────────────────────────────
async function handleFile(file) {
    const allowedExtensions = ['.pdf', '.png', '.jpg', '.jpeg'];
    const ext = '.' + (file.name.split('.').pop()?.toLowerCase() || '');

    if (!allowedExtensions.includes(ext)) {
        showToast('Invalid file type. Only PDF, PNG, JPG allowed.');
        return;
    }

    if (file.size > 16 * 1024 * 1024) {
        showToast('File too large. Maximum 16MB.');
        return;
    }

    // Store file for later preview
    currentUploadedFile = file;

    // Reset log counter & show scanning UI with file info
    _logCount = 0;
    showScanningUI(file);

    const formData = new FormData();
    formData.append('file', file);

    // Create abort controller for cancel functionality
    currentUploadController = new AbortController();

    // Log where request is going
    console.log(`📡 Sending to: ${API_BASE_URL}/upload`);

    try {
        // --- Run stage 1 & 2 (init + preprocess) immediately while fetch is in flight ---
        const fetchPromise = fetch(`${API_BASE_URL}/upload`, { 
            method: 'POST', 
            body: formData,
            signal: currentUploadController.signal
        });
        await runEarlyStages();                     // init + preprocess (~2.5s)

        // --- Wait for server response ---
        const response = await fetchPromise;
        const result = await response.json();

        if (result.success && result.data) {
            // --- Run extract stage with table + approval gate ---
            const approved = await runLateStages(
                result.data.extracted_texts || [],
                result.data.courses || []
            );
            if (!approved) {
                stopElapsedTimer();
                return; // user cancelled
            }

            analysisData = result.data;
            stopElapsedTimer();
            await delay(400);
            showResults(result.data);
        } else {
            stopElapsedTimer();
            showToast(result.error || 'Analysis failed.');
            resetToUpload();
        }
    } catch (error) {
        stopElapsedTimer();
        if (error.name === 'AbortError') {
            // User cancelled - already handled
            return;
        }
        console.error('Upload error:', error);
        showToast('Network error. Please try again.');
        resetToUpload();
    } finally {
        currentUploadController = null;
    }
}

// ─── Scanning UI ───────────────────────────────────────────────────────────────
function showScanningUI(file) {
    // Hide hero section with smooth transition
    if (heroContent) {
        heroContent.classList.add('hidden');
    }
    
    // Hide upload card
    uploadSection.querySelector('.upload-card').setAttribute('style', 'display: none');
    
    // Show scanning section
    scanningSection.style.display = 'block';
    
    // Add scanning state to document for CSS targeting
    document.body.classList.add('scanning-active');
    
    // Show restart button in header
    if (restartBtn) {
        restartBtn.classList.add('visible');
    }
    
    // Update file info in processing header
    if (file) {
        const filenameEl = document.getElementById('processing-filename');
        const filemetaEl = document.getElementById('processing-filemeta');
        if (filenameEl) filenameEl.textContent = file.name;
        if (filemetaEl) {
            const sizeMB = (file.size / (1024 * 1024)).toFixed(2);
            filemetaEl.textContent = `${sizeMB} MB`;
        }
        
        // Show correct file type icon
        updateFileTypeIcon(file);
        
        // Generate thumbnail for images, or show PDF icon
        updateFileThumbnail(file);
    }
    
    // Start real elapsed timer
    startElapsedTimer();
    
    extractedTextEl.innerHTML = '<div class="cursor-blink">|</div>';
    scanProgress.style.width = '0%';
    if (progressText) progressText.textContent = '0%';
    const stageEl = document.getElementById('scanning-stage');
    if (stageEl) stageEl.textContent = 'Initializing...';
    // Reset all steps to initial state
    document.querySelectorAll('.scan-step').forEach(el => {
        el.classList.remove('active', 'done');
        const dot = el.querySelector('.step-dot');
        if (dot) dot.textContent = '';
    });
    document.getElementById('step-init')?.classList.add('active');
}

// ─── File Type Icon Handler ────────────────────────────────────────────────────
function updateFileTypeIcon(file) {
    const pdfIcon = document.getElementById('file-icon-pdf');
    const imageIcon = document.getElementById('file-icon-image');
    const ext = file.name.split('.').pop()?.toLowerCase();
    
    if (pdfIcon && imageIcon) {
        if (ext === 'pdf') {
            pdfIcon.style.display = 'block';
            imageIcon.style.display = 'none';
        } else {
            pdfIcon.style.display = 'none';
            imageIcon.style.display = 'block';
        }
    }
}

// ─── File Thumbnail Preview ────────────────────────────────────────────────────
function updateFileThumbnail(file) {
    const thumbnail = document.getElementById('file-thumbnail');
    const defaultIcon = document.getElementById('scan-icon-default');
    const scanningIcon = document.getElementById('scanning-icon-container');
    const ext = file.name.split('.').pop()?.toLowerCase();
    
    if (!thumbnail || !defaultIcon || !scanningIcon) return;
    
    // For images, show actual preview
    if (['png', 'jpg', 'jpeg'].includes(ext)) {
        const reader = new FileReader();
        reader.onload = (e) => {
            thumbnail.src = e.target.result;
            thumbnail.style.display = 'block';
            defaultIcon.style.display = 'none';
            scanningIcon.classList.add('has-thumbnail');
        };
        reader.readAsDataURL(file);
    } else {
        // For PDF, keep default icon
        thumbnail.style.display = 'none';
        defaultIcon.style.display = 'block';
        scanningIcon.classList.remove('has-thumbnail');
    }
}

// ─── Real Elapsed Timer ────────────────────────────────────────────────────────
function startElapsedTimer() {
    processingStartTime = Date.now();
    const counterEl = document.getElementById('elapsed-counter');
    
    // Clear any existing timer
    if (elapsedTimerInterval) {
        clearInterval(elapsedTimerInterval);
    }
    
    // Update immediately
    if (counterEl) counterEl.textContent = '0:00';
    
    // Update every second
    elapsedTimerInterval = setInterval(() => {
        if (!processingStartTime) return;
        
        const elapsed = Math.floor((Date.now() - processingStartTime) / 1000);
        const minutes = Math.floor(elapsed / 60);
        const seconds = elapsed % 60;
        
        if (counterEl) {
            counterEl.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
        }
    }, 1000);
}

function stopElapsedTimer() {
    if (elapsedTimerInterval) {
        clearInterval(elapsedTimerInterval);
        elapsedTimerInterval = null;
    }
    processingStartTime = null;
}

// ─── Cancel Button Handler ─────────────────────────────────────────────────────
function initCancelButton() {
    const cancelBtn = document.getElementById('btn-cancel-upload');
    if (cancelBtn) {
        cancelBtn.addEventListener('click', () => {
            // Abort any ongoing upload
            if (currentUploadController) {
                currentUploadController.abort();
                currentUploadController = null;
            }
            
            stopElapsedTimer();
            resetToInitial();
            showToast('Processing cancelled');
        });
    }
}

// Stage-specific terminal log content
const STAGE_LOGS = {
    init: [
        { text: '[SYS]  Loading OCR pipeline...', type: 'sys', delay: 80 },
        { text: '[SYS]  Initializing OCR engine...', type: 'sys', delay: 90 },
        { text: '[CFG]  Max file size: 16MB', type: 'cfg', delay: 80 },
        { text: '[CFG]  Supported formats: PDF, PNG, JPG', type: 'cfg', delay: 90 },
        { text: '[OK]   Pipeline initialized ✓', type: 'ok', delay: 120 },
    ],
    preprocess: [
        { text: '[IMG]  Reading file buffer...', type: 'sys', delay: 70 },
        { text: '[IMG]  Detecting document format...', type: 'sys', delay: 90 },
        { text: '[PRE]  Rendering document...', type: 'cfg', delay: 100 },
        { text: '[PRE]  Applying image enhancements...', type: 'cfg', delay: 80 },
        { text: '[PRE]  Optimizing for OCR...', type: 'cfg', delay: 90 },
        { text: '[OK]   Preprocessing complete ✓', type: 'ok', delay: 120 },
    ],
    extract: [
        { text: '[OCR]  Sending to OCR engine...', type: 'sys', delay: 80 },
        { text: '[OCR]  Processing document...', type: 'sys', delay: 100 },
        { text: '[OCR]  Extracting text blocks...', type: 'sys', delay: 80 },
        { text: '[TXT]  Parsing extracted content...', type: 'sys', delay: 70 },
        { text: '[OK]   Text extraction complete ✓', type: 'ok', delay: 120 },
    ],
    parse: [
        { text: '[PARSE] Analyzing extracted text...', type: 'sys', delay: 70 },
        { text: '[PARSE] Identifying course codes...', type: 'sys', delay: 90 },
        { text: '[PARSE] Extracting grades...', type: 'sys', delay: 80 },
        { text: '[PARSE] Extracting credit hours...', type: 'sys', delay: 80 },
        { text: '[PARSE] Resolving retakes...', type: 'cfg', delay: 90 },
        { text: '[PARSE] Detecting semesters...', type: 'sys', delay: 80 },
        { text: '[OK]   Data parsing complete ✓', type: 'ok', delay: 120 },
    ],
    analyze: [
        { text: '[L1]   Running credit tally...', type: 'sys', delay: 70 },
        { text: '[L1]   Calculating earned credits...', type: 'sys', delay: 80 },
        { text: '[L2]   Computing CGPA...', type: 'sys', delay: 70 },
        { text: '[L2]   Determining academic standing...', type: 'sys', delay: 80 },
        { text: '[L2]   Checking waiver eligibility...', type: 'cfg', delay: 90 },
        { text: '[L3]   Running degree audit...', type: 'sys', delay: 80 },
        { text: '[L3]   Checking graduation requirements...', type: 'cfg', delay: 90 },
        { text: '[OK]   Analysis complete ✓', type: 'ok', delay: 120 },
    ]
};

let _scanIntervalId = null;
let _currentStageAbort = false;

async function runScanningStages(realTexts) {
    const stages = [
        { id: 'step-init',       key: 'init',       pct: 18, label: 'Initializing OCR engine...' },
        { id: 'step-preprocess', key: 'preprocess',  pct: 38, label: 'Preprocessing image...' },
        { id: 'step-extract',    key: 'extract',     pct: 62, label: 'Extracting text tokens...' },
        { id: 'step-parse',      key: 'parse',       pct: 80, label: 'Parsing course data...' },
        { id: 'step-analyze',    key: 'analyze',     pct: 96, label: 'Running degree audit...' },
    ];

    clearTerminal();
    let textCount = 0;

    for (let s = 0; s < stages.length; s++) {
        const stage = stages[s];

        // Mark step active
        document.querySelectorAll('.scan-step').forEach(el => el.classList.remove('active'));
        if (s > 0) markStepDone(stages[s - 1].id);
        const stepEl = document.getElementById(stage.id);
        if (stepEl) stepEl.classList.add('active');

        // Animate progress to this stage's %
        await animateProgress(stage.pct, stage.label);

        // Stream logs for this stage
        const logs = STAGE_LOGS[stage.key] || [];

        // On extract stage, inject real OCR texts mid-stream
        let injected = false;
        for (const log of logs) {
            if (stage.key === 'extract' && !injected && log.type === 'highlight' && realTexts.length > 0) {
                // Inject actual extracted tokens
                await streamRealTexts(realTexts, textCount);
                textCount += Math.min(realTexts.length, 12);
                injected = true;
            }
            await appendLog(log.text, log.type, log.delay);
        }

        // Small pause between stages
        await delay(200);
    }

    // Final step done
    markStepDone(stages[stages.length - 1].id);
    await animateProgress(100, 'Analysis complete!');
    await delay(300);
}

// Runs init + preprocess stages WHILE the server fetch is in-flight
async function runEarlyStages() {
    const early = [
        { id: 'step-init',       key: 'init',      pct: 18, label: 'Initializing OCR engine...' },
        { id: 'step-preprocess', key: 'preprocess', pct: 40, label: 'Preprocessing image...' },
    ];
    clearTerminal();
    for (let s = 0; s < early.length; s++) {
        const stage = early[s];
        document.querySelectorAll('.scan-step').forEach(el => el.classList.remove('active'));
        if (s > 0) markStepDone(early[s - 1].id);
        const stepEl = document.getElementById(stage.id);
        if (stepEl) stepEl.classList.add('active');
        await animateProgress(stage.pct, stage.label);
        for (const log of (STAGE_LOGS[stage.key] || [])) {
            await appendLog(log.text, log.type, log.delay);
        }
        await delay(150);
    }
    markStepDone('step-preprocess');
}

// Runs extract + parse + analyze stages AFTER server returns real data
// Returns true if user approved, false if cancelled
async function runLateStages(realTexts, courses) {
    // ── STAGE 3: Text Extraction ───────────────────────────────────────────
    setStageActive('step-extract', null);
    await animateProgress(62, 'Extracting text tokens...');

    // Stream extract logs
    const extractLogs = STAGE_LOGS['extract'].slice(0, 4); // first 4 lines
    for (const log of extractLogs) await appendLog(log.text, log.type, log.delay);

    // Show animated table header
    await appendLog('', 'sys', 50);
    await appendLog('[TBL]  ━━━ Structured Course Data ━━━━━━━━━━━━━━━━━━━━', 'table-header', 80);
    await renderCourseTable(courses);
    await appendLog('[OK]   Text extraction complete — ' + courses.length + ' courses found ✓', 'ok', 100);

    // Stop timer when extraction is complete
    stopElapsedTimer();

    // Show split review UI with PDF preview and courses
    const approved = await showSplitReviewUI(courses);
    if (!approved) { resetToUpload(); return false; }

    // Restart timer for remaining phases
    startElapsedTimer();

    markStepDone('step-extract');

    // ── STAGE 4: Data Parsing ──────────────────────────────────────────────
    setStageActive('step-parse', null);
    await animateProgress(82, 'Parsing course data...');
    for (const log of STAGE_LOGS['parse']) await appendLog(log.text, log.type, log.delay);
    await delay(150);
    markStepDone('step-parse');

    // ── STAGE 5: Analysis ──────────────────────────────────────────────────
    setStageActive('step-analyze', null);
    await animateProgress(96, 'Running degree audit...');
    for (const log of STAGE_LOGS['analyze']) await appendLog(log.text, log.type, log.delay);
    await delay(150);
    markStepDone('step-analyze');

    // Stop timer when complete
    stopElapsedTimer();

    await animateProgress(100, 'Analysis complete! ✓');
    return true;
}

function setStageActive(id, prevId) {
    document.querySelectorAll('.scan-step').forEach(el => el.classList.remove('active'));
    if (prevId) markStepDone(prevId);
    document.getElementById(id)?.classList.add('active');
}

// Render course table row by row into the terminal
async function renderCourseTable(courses) {
    if (!courses || courses.length === 0) return;

    const container = document.createElement('div');
    container.className = 'course-table-wrap';

    // Table header
    const header = document.createElement('div');
    header.className = 'ct-row ct-header';
    header.innerHTML = `
        <span class="ct-code">Course</span>
        <span class="ct-cr">Cr</span>
        <span class="ct-grade">Grade</span>
        <span class="ct-sem">Semester</span>`;
    container.appendChild(header);
    extractedTextEl.appendChild(container);
    extractedTextEl.scrollTop = extractedTextEl.scrollHeight;
    await delay(120);

    // Rows streamed one by one
    for (const course of courses) {
        const row = document.createElement('div');
        row.className = 'ct-row';
        const gradeClass = getGradeClass(course.grade);
        row.innerHTML = `
            <span class="ct-code">${course.code || '—'}</span>
            <span class="ct-cr">${course.credits ?? '—'}</span>
            <span class="ct-grade ${gradeClass}">${course.grade || '—'}</span>
            <span class="ct-sem">${course.semester || '—'}</span>`;
        container.appendChild(row);
        extractedTextEl.scrollTop = extractedTextEl.scrollHeight;
        _logCount++;
        const textCountEl = document.getElementById('text-count');
        if (textCountEl) textCountEl.textContent = `${_logCount} rows`;
        await delay(55);
    }
    await delay(100);
}

function getGradeClass(grade) {
    if (!grade) return 'grade-na';
    if (grade === 'A' || grade === 'A-') return 'grade-a-cls';
    if (grade.startsWith('B')) return 'grade-b-cls';
    if (grade.startsWith('C')) return 'grade-c-cls';
    if (grade === 'D' || grade.startsWith('D')) return 'grade-d-cls';
    if (grade === 'F') return 'grade-f-cls';
    if (grade === 'W') return 'grade-w-cls';
    return '';
}

// Show split review UI: PDF preview on left, extracted courses on right
// This takes over the full page
async function showSplitReviewUI(courses) {
    return new Promise(resolve => {
        // Hide the scanning section entirely for fullscreen review
        scanningSection.style.display = 'none';
        
        // Add fullscreen review class to body
        document.body.classList.add('review-active');
        document.body.classList.remove('scanning-active');

        // Build fullscreen split review element
        const reviewUI = document.createElement('div');
        reviewUI.className = 'split-review-ui fullscreen';
        reviewUI.id = 'split-review-ui';

        // Generate file preview HTML - use object for PDF to hide toolbar
        let filePreviewHTML = '';
        if (currentUploadedFile) {
            const ext = currentUploadedFile.name.split('.').pop()?.toLowerCase();
            if (['png', 'jpg', 'jpeg'].includes(ext)) {
                filePreviewHTML = `<img id="review-file-preview" class="review-file-image" alt="Uploaded file"/>`;
            } else {
                // For PDF - use object with toolbar disabled
                filePreviewHTML = `<object id="review-file-preview" class="review-file-pdf" type="application/pdf"></object>`;
            }
        }

        // Generate course rows HTML
        let courseRowsHTML = '';
        courses.forEach((course, idx) => {
            const gradeClass = getGradeClass(course.grade);
            courseRowsHTML += `
                <tr class="review-course-row" style="animation-delay: ${idx * 20}ms">
                    <td class="course-code">${course.code || '—'}</td>
                    <td class="course-credits">${course.credits ?? '—'}</td>
                    <td class="course-grade ${gradeClass}">${course.grade || '—'}</td>
                    <td class="course-semester">${course.semester || '—'}</td>
                </tr>`;
        });

        reviewUI.innerHTML = `
            <div class="review-header-bar">
                <div class="review-title-section">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="28" height="28">
                        <circle cx="12" cy="12" r="10" fill="rgba(16, 185, 129, 0.15)" stroke="#10B981"/>
                        <path d="M8 12l3 3 5-6" stroke="#10B981" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                    <div>
                        <h2>Extraction Complete</h2>
                        <p>Review the extracted data before proceeding to analysis</p>
                    </div>
                </div>
                <div class="review-stats-bar">
                    <div class="stat-chip">
                        <span class="stat-num">${courses.length}</span>
                        <span class="stat-lbl">Courses</span>
                    </div>
                    <div class="stat-chip">
                        <span class="stat-num">${courses.reduce((sum, c) => sum + (parseFloat(c.credits) || 0), 0).toFixed(0)}</span>
                        <span class="stat-lbl">Credits</span>
                    </div>
                </div>
            </div>
            <div class="review-split-content">
                <div class="review-panel review-panel-left">
                    <div class="panel-label">
                        <svg viewBox="0 0 20 20" fill="currentColor" width="16" height="16">
                            <path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z"/>
                        </svg>
                        Uploaded Document
                    </div>
                    <div class="panel-content panel-pdf-content">
                        ${filePreviewHTML}
                    </div>
                </div>
                <div class="review-panel review-panel-right">
                    <div class="panel-label">
                        <svg viewBox="0 0 20 20" fill="currentColor" width="16" height="16">
                            <path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z"/>
                            <path fill-rule="evenodd" d="M4 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v11a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm3 4a1 1 0 000 2h.01a1 1 0 100-2H7zm3 0a1 1 0 000 2h3a1 1 0 100-2h-3zm-3 4a1 1 0 100 2h.01a1 1 0 100-2H7zm3 0a1 1 0 100 2h3a1 1 0 100-2h-3z"/>
                        </svg>
                        Extracted Courses (${courses.length})
                    </div>
                    <div class="panel-content panel-table-wrap">
                        <table class="review-courses-table">
                            <thead>
                                <tr>
                                    <th>Course</th>
                                    <th>Credits</th>
                                    <th>Grade</th>
                                    <th>Semester</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${courseRowsHTML}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
            <div class="review-actions-bar">
                <button class="btn-review-cancel" id="btn-review-cancel" type="button">
                    <svg viewBox="0 0 20 20" fill="currentColor" width="16" height="16">
                        <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"/>
                    </svg>
                    Cancel & Re-upload
                </button>
                <button class="btn-review-approve" id="btn-review-approve" type="button">
                    <svg viewBox="0 0 20 20" fill="currentColor" width="16" height="16">
                        <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"/>
                    </svg>
                    Approve & Continue Analysis
                </button>
            </div>`;

        // Insert into body directly for true fullscreen
        document.body.appendChild(reviewUI);

        // Load file preview
        if (currentUploadedFile) {
            const previewEl = document.getElementById('review-file-preview');
            if (previewEl) {
                const fileURL = URL.createObjectURL(currentUploadedFile);
                const ext = currentUploadedFile.name.split('.').pop()?.toLowerCase();
                if (ext === 'pdf') {
                    // Add parameters to hide PDF toolbar
                    previewEl.data = fileURL + '#toolbar=0&navpanes=0&scrollbar=0&view=FitH';
                } else {
                    previewEl.src = fileURL;
                }
            }
        }

        // Trigger entrance animation
        requestAnimationFrame(() => {
            reviewUI.classList.add('visible');
        });

        // Event handlers for buttons
        const approveBtn = document.getElementById('btn-review-approve');
        const cancelBtn = document.getElementById('btn-review-cancel');
        
        if (approveBtn) {
            approveBtn.onclick = () => {
                reviewUI.classList.remove('visible');
                document.body.classList.remove('review-active');
                document.body.classList.add('scanning-active');
                setTimeout(() => {
                    reviewUI.remove();
                    scanningSection.style.display = 'block';
                }, 300);
                resolve(true);
            };
        }

        if (cancelBtn) {
            cancelBtn.onclick = () => {
                reviewUI.classList.remove('visible');
                document.body.classList.remove('review-active');
                setTimeout(() => {
                    reviewUI.remove();
                }, 300);
                resolve(false);
            };
        }
    });
}

// Legacy function - kept for compatibility
async function showApproveGate(count) {
    return showSplitReviewUI([]);
}

async function animateProgress(targetPct, label) {
    const current = parseFloat(scanProgress.style.width) || 0;
    const steps = 20;
    const delta = (targetPct - current) / steps;
    // Update the stage label (separate from the % counter)
    const stageEl = document.getElementById('scanning-stage');
    if (label && stageEl) stageEl.textContent = label;
    for (let i = 0; i < steps; i++) {
        const val = Math.min(current + delta * (i + 1), targetPct);
        scanProgress.style.width = val + '%';
        const progressGlowEl = document.getElementById('progress-glow');
        if (progressGlowEl) progressGlowEl.style.width = val + '%';
        if (progressText) progressText.textContent = Math.round(val) + '%';
        await delay(30);
    }
}

function clearTerminal() {
    extractedTextEl.innerHTML = '';
    const textCountEl = document.getElementById('text-count');
    if (textCountEl) textCountEl.textContent = '0 items';
}

let _logCount = 0;
async function appendLog(text, type, ms) {
    const item = document.createElement('div');
    item.className = 'text-item';
    if (type === 'ok') item.classList.add('log-ok');
    else if (type === 'highlight') item.classList.add('highlight');
    else if (type === 'grade') item.classList.add('grade-highlight');
    else if (type === 'cfg') item.classList.add('log-cfg');
    else item.classList.add('log-sys');

    item.textContent = text;
    extractedTextEl.appendChild(item);
    extractedTextEl.scrollTop = extractedTextEl.scrollHeight;
    _logCount++;

    const textCountEl = document.getElementById('text-count');
    if (textCountEl) textCountEl.textContent = `${_logCount} lines`;

    await delay(ms || 80);
}

async function streamRealTexts(texts, startIdx) {
    const coursePattern = /^[A-Z]{2,4}\d{3}[A-Z]?$/;
    const gradePattern = /^(A-?|B[+-]?|C[+-]?|D[+-]?|F|W|I|P|TR)$/;
    const slice = texts.slice(startIdx, startIdx + 12);
    for (const text of slice) {
        const item = document.createElement('div');
        item.className = 'text-item';
        if (coursePattern.test(text)) item.classList.add('highlight');
        else if (gradePattern.test(text)) item.classList.add('grade-highlight');
        item.textContent = `[RAW]  ${text}`;
        extractedTextEl.appendChild(item);
        extractedTextEl.scrollTop = extractedTextEl.scrollHeight;
        _logCount++;
        await delay(25);
    }
}

function markStepDone(stepId) {
    const el = document.getElementById(stepId);
    if (!el) return;
    el.classList.remove('active');
    el.classList.add('done');
    // Replace dot with checkmark
    const dot = el.querySelector('.step-dot');
    if (dot) dot.textContent = '✓';
}

// ─── Results Display ───────────────────────────────────────────────────────────
function showResults(data) {
    // Ensure hero remains hidden
    if (heroContent) {
        heroContent.classList.add('hidden');
    }
    
    scanningSection.style.display = 'none';
    resultsSection.style.display = 'block';
    
    // Update body class for results state
    document.body.classList.remove('scanning-active');
    document.body.classList.add('results-active');
    
    // Keep restart button visible
    if (restartBtn) {
        restartBtn.classList.add('visible');
    }

    // OCR Summary Banner
    const ocrMeta = document.getElementById('ocr-meta');
    const ocrCoursesCount = document.getElementById('ocr-courses-count');
    const ocrConfidence = document.getElementById('ocr-confidence-value');

    if (ocrMeta && data.ocr_info) {
        ocrMeta.textContent = `Engine: ${data.ocr_info.engine || 'OCR.space'}`;
    }
    if (ocrCoursesCount) {
        ocrCoursesCount.textContent = data.courses.length;
    }
    if (ocrConfidence && data.ocr_info) {
        ocrConfidence.textContent = `${data.ocr_info.confidence || 85}%`;
    }

    // Student Card
    const studentCard = document.getElementById('student-card');
    const studentName = document.getElementById('student-name');
    const studentId = document.getElementById('student-id');

    if (data.ocr_info && (data.ocr_info.student_name || data.ocr_info.student_id)) {
        if (studentCard) studentCard.style.display = 'flex';
        if (studentName) studentName.textContent = data.ocr_info.student_name || '—';
        if (studentId) studentId.textContent = data.ocr_info.student_id || '—';
    }

    // Populate all levels
    populateLevel1(data.level1);
    populateLevel2(data.level2);
    populateLevel3(data.level3);
    populateSemesterTables(data.semesters || [], data.courses || []);

    // Credit progress
    const creditsEarnedLabel = document.getElementById('credits-earned-label');
    const creditProgressFill = document.getElementById('credit-progress-fill');
    if (creditsEarnedLabel && data.level1) {
        creditsEarnedLabel.textContent = data.level1.earned_credits;
    }
    if (creditProgressFill && data.level1) {
        creditProgressFill.style.width = `${Math.min(data.level1.progress_130, 100)}%`;
    }

    // Show Level 1 by default
    switchLevel('1');

    resultsSection.scrollIntoView({ behavior: 'smooth' });
}

function populateLevel1(level1) {
    if (!level1) return;

    const statsGrid = document.getElementById('level1-stats');
    if (statsGrid) {
        statsGrid.innerHTML = `
            <div class="stat-card">
                <span class="stat-value">${level1.total_entries}</span>
                <span class="stat-label">Total Entries</span>
            </div>
            <div class="stat-card">
                <span class="stat-value">${level1.unique_courses}</span>
                <span class="stat-label">Unique Courses</span>
            </div>
            <div class="stat-card">
                <span class="stat-value">${level1.earned_credits}</span>
                <span class="stat-label">Credits Earned</span>
            </div>
            <div class="stat-card">
                <span class="stat-value">${level1.progress_130}%</span>
                <span class="stat-label">Progress (130)</span>
            </div>
            <div class="stat-card">
                <span class="stat-value">${level1.retakes_count}</span>
                <span class="stat-label">Retakes</span>
            </div>
            <div class="stat-card">
                <span class="stat-value">${level1.failed_credits}</span>
                <span class="stat-label">Failed Credits</span>
            </div>
        `;
    }

    // Retakes
    const retakesCard = document.getElementById('retakes-card');
    const retakesList = document.getElementById('retakes-list');

    if (retakesCard && retakesList) {
        if (level1.retakes && level1.retakes.length > 0) {
            retakesCard.style.display = 'block';
            retakesList.innerHTML = level1.retakes.map(r => `
                <div class="retake-item">
                    <span class="retake-code">${esc(r.code)}</span>
                    <div class="retake-grades">
                        ${r.grades.map((g, i) => `
                            <span class="grade-badge ${getGradeClass(g)}">${esc(g)}</span>
                            ${i < r.grades.length - 1 ? '<span class="retake-arrow">→</span>' : ''}
                        `).join('')}
                    </div>
                    <span class="retake-best">Best: ${esc(r.best)}</span>
                </div>
            `).join('');
        } else {
            retakesCard.style.display = 'none';
        }
    }
}

function populateLevel2(level2) {
    if (!level2) return;

    // CGPA Display
    const cgpaDisplay = document.getElementById('cgpa-display');
    if (cgpaDisplay) {
        cgpaDisplay.innerHTML = `
            <div class="cgpa-value">${level2.cgpa.toFixed(2)}</div>
            <div class="cgpa-label">Cumulative GPA</div>
            <div class="standing-badge">${esc(level2.standing)} ${level2.stars}</div>
        `;
    }

    // CGPA Warning (if mismatch detected)
    const cgpaWarning = document.getElementById('cgpa-warning');
    if (cgpaWarning && analysisData && analysisData.cgpa_warning) {
        const warn = analysisData.cgpa_warning;
        cgpaWarning.style.display = 'block';
        cgpaWarning.innerHTML = `
            <div class="warning-icon">⚠️</div>
            <div class="warning-text">
                <strong>CGPA Verification Warning</strong><br>
                PDF shows: <strong>${warn.pdf_value}</strong> | Calculated: <strong>${warn.calculated_value}</strong><br>
                <small>Difference: ${warn.difference} - Some courses may be missing or incorrectly parsed</small>
            </div>
        `;
    } else if (cgpaWarning) {
        cgpaWarning.style.display = 'none';
    }

    // Stats
    const statsGrid = document.getElementById('level2-stats');
    if (statsGrid) {
        statsGrid.innerHTML = `
            <div class="stat-card">
                <span class="stat-value">${level2.gpa_credits}</span>
                <span class="stat-label">GPA Credits</span>
            </div>
            <div class="stat-card">
                <span class="stat-value">${level2.total_quality_points}</span>
                <span class="stat-label">Quality Points</span>
            </div>
        `;
    }

    // Waiver
    const waiverCard = document.getElementById('waiver-card');
    if (waiverCard) {
        if (level2.waiver) {
            waiverCard.style.display = 'block';
            waiverCard.innerHTML = `
                <h3>${esc(level2.waiver.name)}</h3>
                <div class="waiver-level">${esc(level2.waiver.level)}</div>
                <p>Tuition Waiver Eligible</p>
            `;
        } else {
            waiverCard.style.display = 'none';
        }
    }

    // Grade Distribution
    const gradeBars = document.getElementById('grade-bars');
    if (gradeBars && level2.grade_distribution) {
        const grades = Object.entries(level2.grade_distribution);
        const maxCount = Math.max(...grades.map(([, c]) => c), 1);

        gradeBars.innerHTML = grades.map(([grade, count]) => `
            <div class="grade-bar-item">
                <div class="grade-bar">
                    <div class="grade-bar-fill ${getGradeClass(grade)}"
                         style="height: ${(count / maxCount) * 100}%"></div>
                </div>
                <div class="grade-bar-label">${esc(grade)}</div>
                <div class="grade-bar-count">${count}</div>
            </div>
        `).join('');
    }
}

function populateLevel3(level3) {
    const content = document.getElementById('level3-content');
    if (!content) return;

    if (!level3) {
        content.innerHTML = `
            <div class="no-audit">
                <p>Program not detected. Upload a transcript with recognized course codes.</p>
            </div>
        `;
        return;
    }

    content.innerHTML = `
        <div class="stats-grid">
            <div class="stat-card">
                <span class="stat-value">${level3.mandatory_completed}/${level3.mandatory_total}</span>
                <span class="stat-label">Mandatory</span>
            </div>
            <div class="stat-card">
                <span class="stat-value">${level3.mandatory_progress}%</span>
                <span class="stat-label">Progress</span>
            </div>
        </div>

        <div class="audit-progress">
            <h3 style="margin-bottom: 1rem; color: var(--nsu-blue);">${esc(level3.program_name)}</h3>
            <div class="audit-progress-bar">
                <div class="audit-progress-fill" style="width: ${level3.mandatory_progress}%"></div>
            </div>
            <p style="color: var(--text-muted); font-size: 0.9rem;">
                ${level3.mandatory_completed} of ${level3.mandatory_total} mandatory courses completed
            </p>

            ${level3.mandatory_missing && level3.mandatory_missing.length > 0 ? `
                <div class="missing-courses">
                    <h4>Missing Mandatory Courses (${level3.mandatory_missing.length})</h4>
                    <div class="missing-list">
                        ${level3.mandatory_missing.map(c => `<span class="missing-item">${esc(c)}</span>`).join('')}
                    </div>
                </div>
            ` : `
                <div style="background: rgba(16, 185, 129, 0.1); padding: 1rem; border-radius: 8px; margin-top: 1rem; color: var(--success);">
                    All mandatory courses completed!
                </div>
            `}
        </div>
    `;
}

function populateSemesterTables(semesters, courses) {
    const container = document.getElementById('semester-tables');
    const countEl = document.getElementById('course-count');

    if (countEl) {
        countEl.textContent = `${courses.length} courses`;
    }

    if (!container) return;

    // If we have semester groups, display them
    if (semesters && semesters.length > 0) {
        container.innerHTML = semesters.map(sem => `
            <div class="semester-group">
                <h4 class="semester-title">${esc(sem.name)}</h4>
                <table class="course-table">
                    <thead>
                        <tr>
                            <th>Course</th>
                            <th>Credits</th>
                            <th>Grade</th>
                            <th>QP</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${sem.courses.map(c => `
                            <tr>
                                <td class="course-code">${esc(c.code)}</td>
                                <td>${c.credits}</td>
                                <td><span class="grade-badge ${getGradeClass(c.grade)}">${esc(c.grade)}</span></td>
                                <td>${c.quality_points || 0}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `).join('');
    } else if (courses && courses.length > 0) {
        // Fallback: show all courses in a single table
        container.innerHTML = `
            <table class="course-table">
                <thead>
                    <tr>
                        <th>Course</th>
                        <th>Credits</th>
                        <th>Grade</th>
                        <th>QP</th>
                        <th>Semester</th>
                    </tr>
                </thead>
                <tbody>
                    ${courses.map(c => `
                        <tr>
                            <td class="course-code">${esc(c.code)}</td>
                            <td>${c.credits}</td>
                            <td><span class="grade-badge ${getGradeClass(c.grade)}">${esc(c.grade)}</span></td>
                            <td>${c.quality_points || 0}</td>
                            <td>${esc(c.semester) || '-'}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
    }
}

function switchLevel(level) {
    // Update tabs
    document.querySelectorAll('.level-tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.level === level);
    });

    // Update content
    document.querySelectorAll('.level-content').forEach(content => {
        content.style.display = content.id === `level-${level}` ? 'block' : 'none';
    });
}

// ─── Helpers ───────────────────────────────────────────────────────────────────
function getGradeClass(grade) {
    if (!grade) return 'other';
    if (grade.startsWith('A')) return 'a';
    if (grade.startsWith('B')) return 'b';
    if (grade.startsWith('C')) return 'c';
    if (grade.startsWith('D')) return 'd';
    if (grade === 'F') return 'f';
    return 'other';
}

function esc(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

function showToast(message) {
    toast.textContent = message;
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 4000);
}

function resetToUpload() {
    scanningSection.style.display = 'none';
    uploadSection.querySelector('.upload-card').removeAttribute('style');
    fileInput.value = '';
    
    // Remove scanning active class so upload section reappears
    document.body.classList.remove('scanning-active');
    
    // Keep hero hidden during error recovery (still in same session)
    // Hero only returns when user explicitly clicks "Upload New File"
}

function resetToInitial() {
    // Full reset - return to landing page state
    scanningSection.style.display = 'none';
    resultsSection.style.display = 'none';
    uploadSection.querySelector('.upload-card').removeAttribute('style');
    fileInput.value = '';
    analysisData = null;
    
    // Stop elapsed timer
    stopElapsedTimer();
    
    // Reset thumbnail/icon state
    const thumbnail = document.getElementById('file-thumbnail');
    const defaultIcon = document.getElementById('scan-icon-default');
    const scanningIcon = document.getElementById('scanning-icon-container');
    if (thumbnail) thumbnail.style.display = 'none';
    if (defaultIcon) defaultIcon.style.display = 'block';
    if (scanningIcon) scanningIcon.classList.remove('has-thumbnail');
    
    // Clear file reference
    currentUploadedFile = null;
    
    // Remove active state classes
    document.body.classList.remove('scanning-active', 'results-active');
    
    // Show hero section again with animation
    if (heroContent) {
        heroContent.classList.remove('hidden');
    }
    
    // Hide restart button
    if (restartBtn) {
        restartBtn.classList.remove('visible');
    }
    
    // Scroll to top smoothly
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function initRestartButton() {
    if (restartBtn) {
        restartBtn.addEventListener('click', () => {
            resetToInitial();
            showToast('Ready for new upload');
        });
    }
}

// Global reset function
window.resetAnalysis = function() {
    resetToInitial();
};
