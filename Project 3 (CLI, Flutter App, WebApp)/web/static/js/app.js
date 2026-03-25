"use strict";
/**
 * NSU Degree Audit - Premium Web Application
 * Real-time OCR scanning with level-wise analysis display
 */

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

let analysisData = null;

// ─── Initialization ────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    initUpload();
    initTabs();
});

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

    // Show scanning UI
    showScanningUI();

    const formData = new FormData();
    formData.append('file', file);

    try {
        // Simulate scanning progress
        simulateScanProgress();

        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (result.success && result.data) {
            // Show extracted texts animation
            await showExtractedTexts(result.data.extracted_texts || []);

            // Complete progress
            scanProgress.style.width = '100%';
            progressText.textContent = 'Analysis complete!';

            await delay(500);

            analysisData = result.data;
            showResults(result.data);
        } else {
            showToast(result.error || 'Analysis failed.');
            resetToUpload();
        }
    } catch (error) {
        console.error('Upload error:', error);
        showToast('Network error. Please try again.');
        resetToUpload();
    }
}

// ─── Scanning UI ───────────────────────────────────────────────────────────────
function showScanningUI() {
    uploadSection.querySelector('.upload-card').setAttribute('style', 'display: none');
    scanningSection.style.display = 'block';
    extractedTextEl.innerHTML = '';
    scanProgress.style.width = '0%';
    progressText.textContent = 'Initializing OCR engine...';
}

function simulateScanProgress() {
    let progress = 0;
    const messages = [
        'Initializing OCR engine...',
        'Processing image...',
        'Detecting text regions...',
        'Extracting course data...',
        'Analyzing grades...',
        'Resolving retakes...'
    ];

    const interval = setInterval(() => {
        progress += Math.random() * 8;
        if (progress > 85) {
            progress = 85;
            clearInterval(interval);
        }
        scanProgress.style.width = progress + '%';

        const msgIndex = Math.min(Math.floor(progress / 15), messages.length - 1);
        progressText.textContent = messages[msgIndex];
    }, 300);
}

async function showExtractedTexts(texts) {
    const coursePattern = /^[A-Z]{2,4}\d{3}[A-Z]?$/;
    const gradePattern = /^(A-?|B[+-]?|C[+-]?|D[+-]?|F|W|I|P|TR)$/;

    for (let i = 0; i < Math.min(texts.length, 50); i++) {
        const text = texts[i];
        const item = document.createElement('div');
        item.className = 'text-item';

        // Highlight course codes and grades
        if (coursePattern.test(text) || gradePattern.test(text)) {
            item.classList.add('highlight');
        }

        item.textContent = text;
        extractedTextEl.appendChild(item);
        extractedTextEl.scrollTop = extractedTextEl.scrollHeight;

        await delay(30);
    }
}

// ─── Results Display ───────────────────────────────────────────────────────────
function showResults(data) {
    scanningSection.style.display = 'none';
    resultsSection.style.display = 'block';

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
}

// Global reset function
window.resetAnalysis = function() {
    resultsSection.style.display = 'none';
    uploadSection.querySelector('.upload-card').removeAttribute('style');
    scanningSection.style.display = 'none';
    fileInput.value = '';
    analysisData = null;
    uploadSection.scrollIntoView({ behavior: 'smooth' });
};
