/**
 * NSU Degree Audit - Authentication Module
 * =========================================
 * Handles Supabase Auth with Google OAuth
 */

// Use API_BASE_URL from app.js (already declared as const)

// Supabase configuration
let supabaseClient = null;
let currentUser = null;
let authConfig = null;
let isGuestMode = false;

// History cache for instant loading
let historyCache = null;
let historyCacheTime = 0;
const HISTORY_CACHE_TTL = 30000; // 30 seconds cache

// ─── Initialize Auth ───────────────────────────────────────────────────────────

async function initAuth() {
    // Check guest mode
    isGuestMode = sessionStorage.getItem('nsu_guest_mode') === 'true';
    if (isGuestMode) {
        hideInitialLoading();
        showMainContent();
        return;
    }
    
    try {
        // Get auth config
        const response = await fetch(`${API_BASE_URL}/auth/config`);
        const data = await response.json();
        
        if (!data.success || !data.config) {
            hideInitialLoading();
            showAuthLanding();
            return;
        }
        
        authConfig = data.config;
        
        if (typeof supabase === 'undefined') {
            hideInitialLoading();
            showAuthLanding();
            return;
        }
        
        const { createClient } = supabase;
        supabaseClient = createClient(authConfig.supabase_url, authConfig.supabase_key);
        
        // Check if OAuth callback FIRST (before session check)
        const hashParams = new URLSearchParams(window.location.hash.substring(1));
        const isOAuthCallback = hashParams.has('access_token');
        
        // Check for existing session
        const { data: { session } } = await supabaseClient.auth.getSession();
        
        if (session && !isOAuthCallback) {
            // Has session AND not OAuth callback - go directly to main content
            currentUser = session.user;
            hideInitialLoading();
            updateAuthUI(true);
            showMainContent();
            syncUserToBackend().catch(e => console.warn('Sync failed:', e));
            return;
        }
        
        if (isOAuthCallback) {
            // OAuth callback - show loading and handle
            hideInitialLoading();
            showAuthLoading();
            
            // Wait for Supabase to process the callback
            await new Promise(resolve => setTimeout(resolve, 1000));
            
            // Check session again
            const { data: { session: newSession } } = await supabaseClient.auth.getSession();
            if (newSession) {
                currentUser = newSession.user;
                
                // Sync to backend
                try {
                    await syncUserToBackend();
                } catch (e) {
                    console.warn('Sync error:', e);
                }
                
                // Show success
                await showAuthSuccess();
                
                // Go to main
                updateAuthUI(true);
                hideAuthLoading();
                showMainContent();
                
                // Clear hash
                history.replaceState(null, '', window.location.pathname);
                
                // Prefetch history in background for instant loading later
                prefetchHistory();
            } else {
                // Callback failed
                hideAuthLoading();
                showAuthLanding();
                showToast('Sign in failed. Please try again.', 'error');
            }
            return;
        }
        
        // No session, no callback - show auth
        hideInitialLoading();
        showAuthLanding();
        
    } catch (error) {
        console.error('Auth init error:', error);
        hideInitialLoading();
        showAuthLanding();
    }
}

// ─── UI Control Functions ──────────────────────────────────────────────────────

function hideInitialLoading() {
    const el = document.getElementById('initial-loading');
    if (el) el.style.display = 'none';
}

function showAuthLanding() {
    document.getElementById('auth-landing').style.display = 'flex';
    document.getElementById('main-content').style.display = 'none';
    document.querySelector('header').style.display = 'none';
    document.getElementById('auth-loading-overlay').style.display = 'none';
}

function showMainContent() {
    document.getElementById('auth-landing').style.display = 'none';
    document.getElementById('main-content').style.display = 'block';
    document.querySelector('header').style.display = 'block';
    document.getElementById('auth-loading-overlay').style.display = 'none';
}

function showAuthLoading() {
    document.getElementById('auth-landing').style.display = 'none';
    document.getElementById('main-content').style.display = 'none';
    document.querySelector('header').style.display = 'none';
    document.getElementById('auth-loading-overlay').style.display = 'flex';
    document.getElementById('auth-loading-title').textContent = 'Setting up your account...';
    document.getElementById('auth-loading-subtitle').textContent = 'Saving to database';
    
    const spinner = document.querySelector('.auth-loading-spinner svg:first-child');
    const checkmark = document.querySelector('.checkmark');
    if (spinner) spinner.style.display = 'block';
    if (checkmark) checkmark.style.display = 'none';
}

async function showAuthSuccess() {
    await new Promise(r => setTimeout(r, 300));
    
    const spinner = document.querySelector('.auth-loading-spinner svg:first-child');
    const checkmark = document.querySelector('.checkmark');
    if (spinner) spinner.style.display = 'none';
    if (checkmark) checkmark.style.display = 'block';
    
    document.getElementById('auth-loading-title').textContent = 'Account ready!';
    document.getElementById('auth-loading-subtitle').textContent = 'Redirecting to dashboard...';
    
    await new Promise(r => setTimeout(r, 800));
}

function hideAuthLoading() {
    document.getElementById('auth-loading-overlay').style.display = 'none';
}

function continueAsGuest() {
    isGuestMode = true;
    sessionStorage.setItem('nsu_guest_mode', 'true');
    hideInitialLoading();
    showMainContent();
    showToast('Continuing as guest. Your scans won\'t be saved.', 'info');
}

// ─── Auth Functions ────────────────────────────────────────────────────────────

async function syncUserToBackend() {
    if (!currentUser) return;
    
    const headers = await getAuthHeaders();
    const response = await fetch(`${API_BASE_URL}/auth/user`, { headers });
    const data = await response.json();
    
    if (!data.success) throw new Error('Sync failed');
    return data.user;
}

async function signInWithGoogle() {
    if (!supabaseClient) {
        await initAuth();
        if (!supabaseClient) {
            showToast('Failed to initialize authentication', 'error');
            return;
        }
    }
    
    const { error } = await supabaseClient.auth.signInWithOAuth({
        provider: 'google',
        options: {
            redirectTo: window.location.origin,
            queryParams: {
                access_type: 'offline',
                prompt: 'consent',
            }
        }
    });
    
    if (error) {
        console.error('OAuth error:', error);
        showToast('Sign in failed: ' + error.message, 'error');
    }
}

async function signOut() {
    if (!supabaseClient) return;
    
    await supabaseClient.auth.signOut();
    currentUser = null;
    isGuestMode = false;
    sessionStorage.removeItem('nsu_guest_mode');
    updateAuthUI(false);
    closeUserMenu();
    showAuthLanding();
    showToast('Signed out successfully', 'success');
}

async function getAccessToken() {
    if (!supabaseClient) return null;
    const { data: { session } } = await supabaseClient.auth.getSession();
    return session?.access_token || null;
}

async function getAuthHeaders() {
    const token = await getAccessToken();
    return token ? { 'Authorization': `Bearer ${token}` } : {};
}

function updateAuthUI(isSignedIn) {
    const authButton = document.getElementById('auth-button');
    const userMenu = document.getElementById('user-menu');
    
    if (isSignedIn && currentUser) {
        const avatarUrl = currentUser.user_metadata?.avatar_url || currentUser.user_metadata?.picture;
        const name = currentUser.user_metadata?.full_name || currentUser.user_metadata?.name || currentUser.email;
        
        authButton.innerHTML = `
            <img src="${avatarUrl || ''}" alt="Avatar" class="user-avatar" onerror="this.style.display='none'">
            <span class="user-name">${name.split(' ')[0]}</span>
            <svg viewBox="0 0 20 20" fill="currentColor" width="14" height="14" class="menu-chevron">
                <path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd"/>
            </svg>
        `;
        authButton.onclick = toggleUserMenu;
        authButton.classList.add('signed-in');
        // Don't force display:block - let toggle control visibility via .show class
        userMenu.classList.remove('show');
    } else {
        authButton.innerHTML = `
            <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
                <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
                <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
            </svg>
            <span>Sign in</span>
        `;
        authButton.onclick = signInWithGoogle;
        authButton.classList.remove('signed-in');
        userMenu.classList.remove('show');
    }
}

function toggleUserMenu() {
    document.getElementById('user-menu').classList.toggle('show');
}

function closeUserMenu() {
    document.getElementById('user-menu').classList.remove('show');
}

// ─── History Functions ─────────────────────────────────────────────────────────

async function loadHistory() {
    if (!currentUser) {
        showToast('Please sign in to view history', 'warning');
        return;
    }
    
    closeUserMenu();
    document.getElementById('history-modal').classList.add('show');
    
    // Check cache first for instant display
    const now = Date.now();
    if (historyCache && (now - historyCacheTime) < HISTORY_CACHE_TTL) {
        renderHistory(historyCache);
        // Refresh in background
        refreshHistoryInBackground();
        return;
    }
    
    document.getElementById('history-content').innerHTML = '<p class="loading-text">Loading history...</p>';
    
    try {
        const headers = await getAuthHeaders();
        
        // Add timeout for faster response
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 8000); // 8 second timeout
        
        const response = await fetch(`${API_BASE_URL}/history`, { 
            headers,
            signal: controller.signal
        });
        clearTimeout(timeoutId);
        
        if (!response.ok) {
            if (response.status === 401) {
                document.getElementById('history-content').innerHTML = '<p class="error-text">Session expired. Please sign in again.</p>';
                signOut();
                return;
            }
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.success && data.history) {
            // Cache the result
            historyCache = data.history;
            historyCacheTime = Date.now();
            renderHistory(data.history);
        } else {
            document.getElementById('history-content').innerHTML = '<p class="no-history">No scan history yet</p>';
        }
    } catch (error) {
        console.error('Load history error:', error);
        if (error.name === 'AbortError') {
            document.getElementById('history-content').innerHTML = '<p class="error-text">Request timed out. Please try again.</p>';
        } else if (error.message?.includes('401') || error.message?.includes('Unauthorized')) {
            document.getElementById('history-content').innerHTML = '<p class="error-text">Session expired. Please sign in again.</p>';
            // Trigger re-auth
            signOut();
        } else {
            document.getElementById('history-content').innerHTML = '<p class="error-text">Failed to load history. Please try again.</p>';
        }
    }
}

async function refreshHistoryInBackground() {
    try {
        const headers = await getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/history`, { headers });
        const data = await response.json();
        
        if (data.success && data.history) {
            historyCache = data.history;
            historyCacheTime = Date.now();
            // Update display if modal still open
            const modal = document.getElementById('history-modal');
            if (modal && modal.classList.contains('show')) {
                renderHistory(data.history);
            }
        }
    } catch (error) {
        // Silent fail for background refresh
    }
}

// Invalidate cache when a new scan is done
function invalidateHistoryCache() {
    historyCache = null;
    historyCacheTime = 0;
}

// Prefetch history on login for instant loading
async function prefetchHistory() {
    try {
        const headers = await getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/history`, { headers });
        const data = await response.json();
        
        if (data.success && data.history) {
            historyCache = data.history;
            historyCacheTime = Date.now();
        }
    } catch (error) {
        // Silent fail
    }
}

function renderHistory(history) {
    const historyContent = document.getElementById('history-content');
    
    if (!history || history.length === 0) {
        historyContent.innerHTML = '<p class="no-history">No scan history yet. Upload a transcript to get started!</p>';
        return;
    }
    
    historyContent.innerHTML = `
        <div class="history-list">
            ${history.map(scan => `
                <div class="history-item" data-id="${scan.id}">
                    <div class="history-info">
                        <span class="history-filename">${scan.filename || 'Transcript'}</span>
                        <span class="history-date">${new Date(scan.created_at).toLocaleDateString('en-US', { 
                            year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
                        })}</span>
                    </div>
                    <div class="history-stats">
                        <span class="history-cgpa">CGPA: ${parseFloat(scan.cgpa || 0).toFixed(2)}</span>
                        <span class="history-courses">${scan.total_courses || 0} courses</span>
                        <span class="history-credits">${scan.total_credits || 0} credits</span>
                    </div>
                    <div class="history-actions">
                        <button class="btn-view" onclick="viewHistoryItem('${scan.id}')">View</button>
                        <button class="btn-delete" onclick="deleteHistoryItem('${scan.id}')">Delete</button>
                    </div>
                </div>
            `).join('')}
        </div>
    `;
}

function closeHistoryModal() {
    document.getElementById('history-modal').classList.remove('show');
}

async function viewHistoryItem(id) {
    try {
        // Show loading state
        showToast('Loading scan details...', 'info');
        closeHistoryModal();
        
        const headers = await getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/history/${id}`, { headers });
        
        if (!response.ok) {
            const errorData = await response.json();
            console.error('API error:', response.status, errorData);
            showToast(errorData.detail || 'Failed to load scan details', 'error');
            return;
        }
        
        const data = await response.json();
        console.log('History detail response:', data);
        
        if (data.success && data.scan && data.scan.analysis_data) {
            // Set currentScanId for export functionality using the helper function if available
            if (typeof setCurrentScanId === 'function') {
                setCurrentScanId(id);
            } else {
                window.currentScanId = id;
            }
            
            // Hide upload section completely (same as when scanning completes)
            const uploadSection = document.getElementById('upload-section');
            const heroContent = document.querySelector('.hero-content');
            const uploadCard = uploadSection?.querySelector('.upload-card');
            
            if (heroContent) heroContent.classList.add('hidden');
            if (uploadCard) uploadCard.style.display = 'none';
            
            // Also hide the entire upload section
            if (uploadSection) {
                uploadSection.style.display = 'none';
            }
            
            // Ensure scan_id is in the analysis_data for export
            const analysisData = data.scan.analysis_data;
            if (!analysisData.scan_id) {
                analysisData.scan_id = id;
            }
            
            // Use showResults from app.js
            if (typeof showResults === 'function') {
                showResults(analysisData);
            } else {
                console.error('showResults function not found');
                showToast('Unable to display results', 'error');
            }
        } else {
            console.error('Invalid response structure:', data);
            showToast('No analysis data found for this scan', 'warning');
        }
    } catch (error) {
        console.error('View history error:', error);
        showToast('Failed to load scan details', 'error');
    }
}

async function deleteHistoryItem(id) {
    if (!confirm('Are you sure you want to delete this scan?')) return;
    
    try {
        const headers = await getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/history/${id}`, { 
            method: 'DELETE',
            headers 
        });
        const data = await response.json();
        
        if (data.success) {
            showToast('Scan deleted successfully', 'success');
            loadHistory();
        } else {
            showToast('Failed to delete scan', 'error');
        }
    } catch (error) {
        console.error('Delete history error:', error);
        showToast('Failed to delete scan', 'error');
    }
}

// ─── Initialize ────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    initAuth();
    
    // Close user menu when clicking outside
    document.addEventListener('click', (e) => {
        const userMenu = document.getElementById('user-menu');
        const authButton = document.getElementById('auth-button');
        
        if (userMenu && userMenu.classList.contains('show')) {
            // Check if click is outside menu and button
            if (!userMenu.contains(e.target) && !authButton.contains(e.target)) {
                userMenu.classList.remove('show');
            }
        }
    });
    
    // Close history modal when clicking overlay
    const historyModal = document.getElementById('history-modal');
    if (historyModal) {
        historyModal.addEventListener('click', (e) => {
            if (e.target === historyModal) {
                closeHistoryModal();
            }
        });
    }
});
