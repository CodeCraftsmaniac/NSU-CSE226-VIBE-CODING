/**
 * NSU Degree Audit - Premium Web Application
 * Real-time OCR scanning with level-wise analysis display
 */

// ─── Type Definitions ──────────────────────────────────────────────────────────

interface Course {
    code: string;
    credits: number;
    grade: string;
    semester: string;
    status: string;
    grade_points: number | null;
    quality_points: number;
}

interface Retake {
    code: string;
    attempts: number;
    grades: string[];
    best: string;
}

interface Level1 {
    total_entries: number;
    unique_courses: number;
    total_credits_attempted: number;
    earned_credits: number;
    failed_credits: number;
    retakes_count: number;
    retakes: Retake[];
    progress_130: number;
}

interface Level2 {
    cgpa: number;
    gpa_credits: number;
    total_quality_points: number;
    standing: string;
    stars: string;
    grade_distribution: Record<string, number>;
    waiver: { level: string; name: string; color: string } | null;
}

interface ElectiveStatus {
    required: number;
    completed: number;
    courses: string[];
    satisfied: boolean;
}

interface Level3 {
    program: string;
    program_name: string;
    mandatory_total: number;
    mandatory_completed: number;
    mandatory_missing: string[];
    mandatory_progress: number;
    elective_status: Record<string, ElectiveStatus>;
    graduation_ready: boolean;
}

interface OCRInfo {
    engine: string;
    confidence: number;
    raw_text_count: number;
    student_name: string;
    student_id: string;
}

interface AnalysisResult {
    level1: Level1;
    level2: Level2;
    level3: Level3 | null;
    courses: Course[];
    ocr_info: OCRInfo;
    extracted_texts: string[];
}

interface APIResponse {
    success: boolean;
    data?: AnalysisResult;
    error?: string;
}

// ─── DOM Elements ──────────────────────────────────────────────────────────────

const uploadArea = document.getElementById('upload-area') as HTMLElement;
const fileInput = document.getElementById('file-input') as HTMLInputElement;
const uploadSection = document.getElementById('upload-section') as HTMLElement;
const scanningSection = document.getElementById('scanning-section') as HTMLElement;
const resultsSection = document.getElementById('results-section') as HTMLElement;
const extractedTextEl = document.getElementById('extracted-text') as HTMLElement;
const scanProgress = document.getElementById('scan-progress') as HTMLElement;
const progressText = document.getElementById('progress-text') as HTMLElement;
const toast = document.getElementById('toast') as HTMLElement;

let analysisData: AnalysisResult | null = null;

// ─── Initialization ────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    initUpload();
    initTabs();
});

function initUpload(): void {
    uploadArea.addEventListener('click', () => fileInput.click());

    fileInput.addEventListener('change', (e: Event) => {
        const target = e.target as HTMLInputElement;
        if (target.files && target.files.length > 0) {
            handleFile(target.files[0]);
        }
    });

    uploadArea.addEventListener('dragover', (e: DragEvent) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });

    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragover');
    });

    uploadArea.addEventListener('drop', (e: DragEvent) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        if (e.dataTransfer?.files.length) {
            handleFile(e.dataTransfer.files[0]);
        }
    });
}

function initTabs(): void {
    document.querySelectorAll('.level-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            const level = (tab as HTMLElement).dataset.level;
            switchLevel(level!);
        });
    });
}

// ─── File Handling ─────────────────────────────────────────────────────────────

async function handleFile(file: File): Promise<void> {
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

        const result: APIResponse = await response.json();

        if (result.success && result.data) {
            // Show extracted texts animation
            await showExtractedTexts(result.data.extracted_texts);

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
        showToast('Network error. Please try again.');
        resetToUpload();
    }
}

// ─── Scanning UI ───────────────────────────────────────────────────────────────

function showScanningUI(): void {
    uploadSection.querySelector('.upload-card')!.setAttribute('style', 'display: none');
    scanningSection.style.display = 'block';
    extractedTextEl.innerHTML = '';
    scanProgress.style.width = '0%';
    progressText.textContent = 'Initializing OCR engine...';
}

function simulateScanProgress(): void {
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

async function showExtractedTexts(texts: string[]): Promise<void> {
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

function showResults(data: AnalysisResult): void {
    scanningSection.style.display = 'none';
    resultsSection.style.display = 'block';

    // OCR Summary
    const ocrConf = document.getElementById('ocr-confidence')!;
    const ocrCourses = document.getElementById('ocr-courses')!;
    ocrConf.textContent = `Confidence: ${data.ocr_info.confidence}%`;
    ocrCourses.textContent = `${data.courses.length} courses extracted`;

    // Populate all levels
    populateLevel1(data.level1);
    populateLevel2(data.level2);
    populateLevel3(data.level3);
    populateCourseTable(data.courses);

    // Show Level 1 by default
    switchLevel('1');

    resultsSection.scrollIntoView({ behavior: 'smooth' });
}

function populateLevel1(level1: Level1): void {
    const statsGrid = document.getElementById('level1-stats')!;
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

    // Retakes
    const retakesCard = document.getElementById('retakes-card')!;
    const retakesList = document.getElementById('retakes-list')!;

    if (level1.retakes.length > 0) {
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

function populateLevel2(level2: Level2): void {
    // CGPA Display
    const cgpaDisplay = document.getElementById('cgpa-display')!;
    cgpaDisplay.innerHTML = `
        <div class="cgpa-value">${level2.cgpa.toFixed(2)}</div>
        <div class="cgpa-label">Cumulative GPA</div>
        <div class="standing-badge">${esc(level2.standing)} ${level2.stars}</div>
    `;

    // Stats
    const statsGrid = document.getElementById('level2-stats')!;
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

    // Waiver
    const waiverCard = document.getElementById('waiver-card')!;
    if (level2.waiver) {
        waiverCard.style.display = 'block';
        waiverCard.innerHTML = `
            <h3>🎉 ${esc(level2.waiver.name)}</h3>
            <div class="waiver-level">${esc(level2.waiver.level)}</div>
            <p>Tuition Waiver Eligible</p>
        `;
    } else {
        waiverCard.style.display = 'none';
    }

    // Grade Distribution
    const gradeBars = document.getElementById('grade-bars')!;
    const grades = Object.entries(level2.grade_distribution);
    const maxCount = Math.max(...grades.map(([, c]) => c), 1);

    gradeBars.innerHTML = grades.map(([grade, count]) => `
        <div class="grade-bar-item">
            <div class="grade-bar">
                <div class="grade-bar-fill ${getGradeClass(grade)}"
                     style="height: ${(count / maxCount) * 100}%; background: var(--grade-${getGradeClass(grade)})"></div>
            </div>
            <div class="grade-bar-label">${esc(grade)}</div>
            <div class="grade-bar-count">${count}</div>
        </div>
    `).join('');
}

function populateLevel3(level3: Level3 | null): void {
    const content = document.getElementById('level3-content')!;

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

            ${level3.mandatory_missing.length > 0 ? `
                <div class="missing-courses">
                    <h4>Missing Mandatory Courses (${level3.mandatory_missing.length})</h4>
                    <div class="missing-list">
                        ${level3.mandatory_missing.map(c => `<span class="missing-item">${esc(c)}</span>`).join('')}
                    </div>
                </div>
            ` : `
                <div style="background: rgba(16, 185, 129, 0.1); padding: 1rem; border-radius: 8px; margin-top: 1rem; color: var(--success);">
                    ✓ All mandatory courses completed!
                </div>
            `}
        </div>
    `;
}

function populateCourseTable(courses: Course[]): void {
    const tbody = document.getElementById('course-tbody')!;
    const countEl = document.getElementById('course-count')!;

    countEl.textContent = `${courses.length} courses`;

    tbody.innerHTML = courses.map(c => `
        <tr>
            <td class="course-code">${esc(c.code)}</td>
            <td>${c.credits}</td>
            <td><span class="grade-badge ${getGradeClass(c.grade)}">${esc(c.grade)}</span></td>
            <td>${c.quality_points}</td>
            <td>${esc(c.semester) || '-'}</td>
        </tr>
    `).join('');
}

function switchLevel(level: string): void {
    // Update tabs
    document.querySelectorAll('.level-tab').forEach(tab => {
        tab.classList.toggle('active', (tab as HTMLElement).dataset.level === level);
    });

    // Update content
    document.querySelectorAll('.level-content').forEach(content => {
        (content as HTMLElement).style.display = content.id === `level-${level}` ? 'block' : 'none';
    });
}

// ─── Helpers ───────────────────────────────────────────────────────────────────

function getGradeClass(grade: string): string {
    if (!grade) return 'other';
    if (grade.startsWith('A')) return 'a';
    if (grade.startsWith('B')) return 'b';
    if (grade.startsWith('C')) return 'c';
    if (grade.startsWith('D')) return 'd';
    if (grade === 'F') return 'f';
    return 'other';
}

function esc(str: string): string {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
}

function showToast(message: string): void {
    toast.textContent = message;
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 4000);
}

function resetToUpload(): void {
    scanningSection.style.display = 'none';
    uploadSection.querySelector('.upload-card')!.removeAttribute('style');
    fileInput.value = '';
}

// Global reset function
(window as any).resetAnalysis = function(): void {
    resultsSection.style.display = 'none';
    uploadSection.querySelector('.upload-card')!.removeAttribute('style');
    scanningSection.style.display = 'none';
    fileInput.value = '';
    analysisData = null;
    uploadSection.scrollIntoView({ behavior: 'smooth' });
};
