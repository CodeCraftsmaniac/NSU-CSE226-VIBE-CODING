/**
 * NSU Degree Audit - Authentication Module
 * =========================================
 * Handles Supabase Auth with Google OAuth
 */

// Supabase configuration - will be loaded from backend
let supabaseClient = null;
let currentUser = null;
let authConfig = null;
let isGuestMode = false;
let authInitialized = false;

// ─── Initialize Auth ───────────────────────────────────────────────────────────

async function initAuth() {
    // Check guest mode first
    isGuestMode = sessionStorage.getItem('nsu_guest_mode') === 'true';
    if (isGuestMode) {
        hideInitialLoading();
        showMainContent();
        return true;
    }
    
    try {
        // Get auth config from backend
        const response = await fetch(`${API_BASE_URL}/auth/config`);
        const data = await response.json();
        
        if (!data.success || !data.config || !data.config.supabase_url || !data.config.supabase_key) {
            console.warn('Auth config not available');
            hideInitialLoading();
            showAuthLanding();
            authInitialized = true;
            return false;
        }
        
        authConfig = data.config;
        
        if (typeof supabase === 'undefined') {
            console.warn('Supabase library not loaded');
            hideInitialLoading();
            showAuthLanding();
            authInitialized = true;
            return false;
        }
        
        const { createClient } = supabase;
        supabaseClient = createClient(authConfig.supabase_url, authConfig.supabase_key);
        
        // Check for existing session FIRST
        const { data: { session } } = await supabaseClient.auth.getSession();
        
        if (session) {
            // User has existing session - go directly to main content
            currentUser = session.user;
            hideInitialLoading();
            updateAuthUI(true);
            showMainContent();
            
            // Sync silently in background (no UI changes)
            syncUserToBackend().catch(err => console.warn('Background sync failed:', err));
            
            authInitialized = true;
            return true;
        }
        
        // No existing session - check if OAuth callback
        const hashParams = new URLSearchParams(window.location.hash.substring(1));
        const isOAuthCallback = hashParams.has('access_token');
        
        if (isOAuthCallback) {
            // OAuth callback - show loading and wait for Supabase to process
            hideInitialLoading();
            showAuthLoading();
            
            // Register ONE-TIME listener for this OAuth callback
            const { data: authListener } = supabaseClient.auth.onAuthStateChange(async (event, session) => {
                if (event === 'SIGNED_IN' && session) {
                    currentUser = session.user;
                    isGuestMode = false;
                    sessionStorage.removeItem('nsu_guest_mode');
                    
                    // Sync user to backend
                    try {
                        await Promise.race([
                            syncUserToBackend(),
                            new Promise((_, reject) => setTimeout(() => reject(new Error('timeout')), 5000))
                        ]);
                    } catch (error) {
                        console.warn('User sync error:', error);
                    }
                    
                    // Show success animation
                    await showAuthSuccess();
                    
                    // Update UI and show main content
                    updateAuthUI(true);
                    hideAuthLoading();
                    showMainContent();
                    
                    // Clear URL hash
                    if (window.location.hash) {
                        history.replaceState(null, '', window.location.pathname);
                    }
                    
                    // Unsubscribe this listener
                    authListener.subscription.unsubscribe();
                }
            });
        } else {
            // No session, no callback - show auth landing
            hideInitialLoading();
            showAuthLanding();
        }
        
        // Setup click outside to close user menu
        document.addEventListener('click', (e) => {
            const menu = document.getElementById('user-menu');
            const authButton = document.getElementById('auth-button');
            if (menu && !menu.contains(e.target) && !authButton.contains(e.target)) {
                menu.classList.remove('show');
            }
        });
        
        authInitialized = true;
        return true;
    } catch (error) {
        console.error('Auth init error:', error);
        hideInitialLoading();
        showAuthLanding();
        authInitialized = true;
        return false;
    }
}

// ─── Initial Loading Control ───────────────────────────────────────────────────

function hideInitialLoading() {
    const initialLoading = document.getElementById('initial-loading');
    if (initialLoading) initialLoading.style.display = 'none';
}

// ─── Auth Landing Control ──────────────────────────────────────────────────────

function showAuthLanding() {
    const landing = document.getElementById('auth-landing');
    const main = document.getElementById('main-content');
    const header = document.querySelector('header');
    const loadingOverlay = document.getElementById('auth-loading-overlay');
    
    if (landing) landing.style.display = 'flex';
    if (main) main.style.display = 'none';
    if (header) header.style.display = 'none';
    if (loadingOverlay) loadingOverlay.style.display = 'none';
}

function showMainContent() {
    const landing = document.getElementById('auth-landing');
    const main = document.getElementById('main-content');
    const header = document.querySelector('header');
    const loadingOverlay = document.getElementById('auth-loading-overlay');
    
    if (landing) landing.style.display = 'none';
    if (main) main.style.display = 'block';
    if (header) header.style.display = 'block';
    if (loadingOverlay) loadingOverlay.style.display = 'none';
}

function showAuthLoading() {
    const landing = document.getElementById('auth-landing');
    const main = document.getElementById('main-content');
    const header = document.querySelector('header');
    const loadingOverlay = document.getElementById('auth-loading-overlay');
    const title = document.getElementById('auth-loading-title');
    const subtitle = document.getElementById('auth-loading-subtitle');
    const spinner = document.querySelector('.auth-loading-spinner svg:first-child');
    const checkmark = document.querySelector('.checkmark');
    
    if (landing) landing.style.display = 'none';
    if (main) main.style.display = 'none';
    if (header) header.style.display = 'none';
    if (loadingOverlay) loadingOverlay.style.display = 'flex';
    if (title) title.textContent = 'Setting up your account...';
    if (subtitle) subtitle.textContent = 'Saving to database';
    
    // Reset spinner/checkmark state
    if (spinner) spinner.style.display = 'block';
    if (checkmark) checkmark.style.display = 'none';
}

async function showAuthSuccess() {
    const title = document.getElementById('auth-loading-title');
    const subtitle = document.getElementById('auth-loading-subtitle');
    const spinner = document.querySelector('.auth-loading-spinner svg:first-child');
    const checkmark = document.querySelector('.checkmark');
    
    // Wait a moment for sync to complete
    await new Promise(resolve => setTimeout(resolve, 300));
    
    // Show success state
    if (spinner) spinner.style.display = 'none';
    if (checkmark) checkmark.style.display = 'block';
    if (title) title.textContent = 'Account ready!';
    if (subtitle) subtitle.textContent = 'Redirecting to dashboard...';
    
    // Wait for animation
    await new Promise(resolve => setTimeout(resolve, 800));
}

function hideAuthLoading() {
    const loadingOverlay = document.getElementById('auth-loading-overlay');
    if (loadingOverlay) loadingOverlay.style.display = 'none';
}

function continueAsGuest() {
    isGuestMode = true;
    sessionStorage.setItem('nsu_guest_mode', 'true');
    hideInitialLoading();
    showMainContent();
    showToast('Continuing as guest. Your scans won\'t be saved.', 'info');
}

// ─── Sync User to Backend ──────────────────────────────────────────────────────

async function syncUserToBackend() {
    if (!currentUser) return;
    
    try {
        const headers = await getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/auth/user`, { headers });
        const data = await response.json();
        
        if (!data.success) {
            console.error('User sync failed:', data);
            throw new Error('Failed to sync user');
        }
        
        console.log('User synced successfully:', data.user);
        return data.user;
    } catch (error) {
        console.error('Sync user error:', error);
        throw error;
    }
}

// ─── Sign In with Google ───────────────────────────────────────────────────────

async function signInWithGoogle() {
    if (!supabaseClient) {
        await initAuth();
        if (!supabaseClient) {
            showToast('Failed to initialize authentication', 'error');
            return;
        }
    }
    
    try {
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
            throw error;
        }
        
    } catch (error) {
        console.error('Sign in error:', error);
    }
}

// ─── Sign Out ──────────────────────────────────────────────────────────────────

async function signOut() {
    if (!supabaseClient) return;
    
    try {
        await supabaseClient.auth.signOut();
        currentUser = null;
        isGuestMode = false;
        sessionStorage.removeItem('nsu_guest_mode');
        updateAuthUI(false);
        closeUserMenu();
        showAuthLanding();
        showToast('Signed out successfully', 'success');
    } catch (error) {
        console.error('Sign out error:', error);
    }
}

// ─── Get Access Token ──────────────────────────────────────────────────────────

async function getAccessToken() {
    if (!supabaseClient) return null;
    
    const { data: { session } } = await supabaseClient.auth.getSession();
    return session?.access_token || null;
}

// ─── Get Auth Headers ──────────────────────────────────────────────────────────

async function getAuthHeaders() {
    const token = await getAccessToken();
    if (token) {
        return { 'Authorization': `Bearer ${token}` };
    }
    return {};
}

// ─── Update UI Based on Auth State ─────────────────────────────────────────────

function updateAuthUI(isSignedIn) {
    const authButton = document.getElementById('auth-button');
    const userMenu = document.getElementById('user-menu');
    
    if (isSignedIn && currentUser) {
        if (authButton) {
            const avatarUrl = currentUser.user_metadata?.avatar_url || currentUser.user_metadata?.picture;
            const name = currentUser.user_metadata?.full_name || currentUser.user_metadata?.name || currentUser.email;
            
            authButton.innerHTML = `
                <img src="${avatarUrl || ''}" alt="Avatar" class="user-avatar" onerror="this.style.display='none'">
                <span class="user-name">${name.split(' ')[0]}</span>
                <svg viewBox="0 0 20 20" fill="currentColor" width="14" height="14">
                    <path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd"/>
                </svg>
            `;
            authButton.onclick = toggleUserMenu;
            authButton.classList.add('signed-in');
        }
        
        if (userMenu) {
            userMenu.style.display = 'block';
        }
    } else {
        if (authButton) {
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
        }
        
        if (userMenu) {
            userMenu.style.display = 'none';
            userMenu.classList.remove('show');
        }
    }
}

// ─── User Menu ─────────────────────────────────────────────────────────────────

function toggleUserMenu() {
    const menu = document.getElementById('user-menu');
    if (menu) {
        menu.classList.toggle('show');
    }
}

function closeUserMenu() {
    const menu = document.getElementById('user-menu');
    if (menu) {
        menu.classList.remove('show');
    }
}

// ─── Initial Loading Control ───────────────────────────────────────────────────

function hideInitialLoading() {
    const initialLoading = document.getElementById('initial-loading');
    if (initialLoading) initialLoading.style.display = 'none';
}

// ─── Auth Landing Control ──────────────────────────────────────────────────────

function showAuthLanding() {
    const landing = document.getElementById('auth-landing');
    const main = document.getElementById('main-content');
    const header = document.querySelector('header');
    const loadingOverlay = document.getElementById('auth-loading-overlay');
    
    if (landing) landing.style.display = 'flex';
    if (main) main.style.display = 'none';
    if (header) header.style.display = 'none';
    if (loadingOverlay) loadingOverlay.style.display = 'none';
}

function showMainContent() {
    const landing = document.getElementById('auth-landing');
    const main = document.getElementById('main-content');
    const header = document.querySelector('header');
    const loadingOverlay = document.getElementById('auth-loading-overlay');
    
    if (landing) landing.style.display = 'none';
    if (main) main.style.display = 'block';
    if (header) header.style.display = 'block';
    if (loadingOverlay) loadingOverlay.style.display = 'none';
}

function showAuthLoading() {
    const landing = document.getElementById('auth-landing');
    const main = document.getElementById('main-content');
    const header = document.querySelector('header');
    const loadingOverlay = document.getElementById('auth-loading-overlay');
    const title = document.getElementById('auth-loading-title');
    const subtitle = document.getElementById('auth-loading-subtitle');
    const spinner = document.querySelector('.auth-loading-spinner svg:first-child');
    const checkmark = document.querySelector('.checkmark');
    
    if (landing) landing.style.display = 'none';
    if (main) main.style.display = 'none';
    if (header) header.style.display = 'none';
    if (loadingOverlay) loadingOverlay.style.display = 'flex';
    if (title) title.textContent = 'Setting up your account...';
    if (subtitle) subtitle.textContent = 'Saving to database';
    
    // Reset spinner/checkmark state
    if (spinner) spinner.style.display = 'block';
    if (checkmark) checkmark.style.display = 'none';
}

async function showAuthSuccess() {
    const title = document.getElementById('auth-loading-title');
    const subtitle = document.getElementById('auth-loading-subtitle');
    const spinner = document.querySelector('.auth-loading-spinner svg:first-child');
    const checkmark = document.querySelector('.checkmark');
    
    // Wait a moment for sync to complete
    await new Promise(resolve => setTimeout(resolve, 300));
    
    // Show success state
    if (spinner) spinner.style.display = 'none';
    if (checkmark) checkmark.style.display = 'block';
    if (title) title.textContent = 'Account ready!';
    if (subtitle) subtitle.textContent = 'Redirecting to dashboard...';
    
    // Wait for animation
    await new Promise(resolve => setTimeout(resolve, 800));
}

function hideAuthLoading() {
    const loadingOverlay = document.getElementById('auth-loading-overlay');
    if (loadingOverlay) loadingOverlay.style.display = 'none';
}

function continueAsGuest() {
    isGuestMode = true;
    sessionStorage.setItem('nsu_guest_mode', 'true');
    hideInitialLoading();
    showMainContent();
    showToast('Continuing as guest. Your scans won\'t be saved.', 'info');
}

// ─── Sync User to Backend ──────────────────────────────────────────────────────

async function syncUserToBackend() {
    if (!currentUser) return;
    
    try {
        const headers = await getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/auth/user`, { headers });
        const data = await response.json();
        
        if (!data.success) {
            console.error('User sync failed:', data);
            throw new Error('Failed to sync user');
        }
        
        console.log('User synced successfully:', data.user);
        return data.user;
    } catch (error) {
        console.error('Sync user error:', error);
        throw error;
    }
}

// ─── Sign In with Google ───────────────────────────────────────────────────────

async function signInWithGoogle() {
    if (!supabaseClient) {
        await initAuth();
        if (!supabaseClient) {
            showToast('Failed to initialize authentication', 'error');
            return;
        }
    }
    
    try {
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
            throw error;
        }
        
    } catch (error) {
        console.error('Sign in error:', error);
    }
}

// ─── Sign Out ──────────────────────────────────────────────────────────────────

async function signOut() {
    if (!supabaseClient) return;
    
    try {
        await supabaseClient.auth.signOut();
        currentUser = null;
        isGuestMode = false;
        sessionStorage.removeItem('nsu_guest_mode');
        updateAuthUI(false);
        closeUserMenu();
        showAuthLanding();
        showToast('Signed out successfully', 'success');
    } catch (error) {
        console.error('Sign out error:', error);
    }
}

// ─── Get Access Token ──────────────────────────────────────────────────────────

async function getAccessToken() {
    if (!supabaseClient) return null;
    
    const { data: { session } } = await supabaseClient.auth.getSession();
    return session?.access_token || null;
}

// ─── Get Auth Headers ──────────────────────────────────────────────────────────

async function getAuthHeaders() {
    const token = await getAccessToken();
    if (token) {
        return { 'Authorization': `Bearer ${token}` };
    }
    return {};
}

// ─── Load Scan History ─────────────────────────────────────────────────────────

async function loadHistory() {
    const historyContent = document.getElementById('history-content');
    const historyModal = document.getElementById('history-modal');
    
    if (!currentUser) {
        showToast('Please sign in to view history', 'warning');
        return;
    }
    
    closeUserMenu();
    
    if (historyModal) {
        historyModal.classList.add('show');
    }
    
    if (historyContent) {
        historyContent.innerHTML = '<p class="loading-text">Loading history...</p>';
    }
    
    try {
        const headers = await getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/history`, { headers });
        const data = await response.json();
        
        if (data.success && data.history) {
            renderHistory(data.history);
        } else {
            if (historyContent) {
                historyContent.innerHTML = '<p class="no-history">No scan history yet</p>';
            }
        }
    } catch (error) {
        console.error('Load history error:', error);
        if (historyContent) {
            historyContent.innerHTML = '<p class="error-text">Failed to load history</p>';
        }
    }
}

function renderHistory(history) {
    const historyContent = document.getElementById('history-content');
    if (!historyContent) return;
    
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
    const historyModal = document.getElementById('history-modal');
    if (historyModal) {
        historyModal.classList.remove('show');
    }
}

async function viewHistoryItem(id) {
    try {
        const headers = await getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/history/${id}`, { headers });
        const data = await response.json();
        
        if (data.success && data.scan && data.scan.analysis_data) {
            closeHistoryModal();
            if (typeof displayResults === 'function') {
                displayResults(data.scan.analysis_data);
            }
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

// ─── Initialize on DOM Ready ───────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    initAuth();
});
