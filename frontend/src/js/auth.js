// Authentication and session handlers

const loginForm = document.getElementById('loginForm');
const emailInput = document.getElementById('email');
const passwordInput = document.getElementById('password');
const submitBtn = document.getElementById('submitBtn');
const errorBox = document.getElementById('errorMessage');

if (loginForm) {
    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const email = emailInput.value.trim();
        const password = passwordInput.value;
        
        if (!email || !password) return;
        
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span>Memproses log masuk…</span>';
        errorBox.classList.add('hidden');
        errorBox.textContent = '';
        
        try {
            const response = await fetch('/api/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });
            
            const data = await response.json();
            
            if (response.ok && data.status === 'success') {
                // Redirect to dashboard
                window.location.href = '/';
            } else {
                // Show user friendly error message
                errorBox.textContent = data.detail || 'E-mel atau kata laluan salah. Sila cuba lagi.';
                errorBox.classList.remove('hidden');
            }
        } catch (err) {
            console.error('Login error:', err);
            errorBox.textContent = 'Hubungan ke pelayan terputus. Cuba lagi.';
            errorBox.classList.remove('hidden');
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<span>Log Masuk ke Pejabat</span>';
        }
    });
}

// Global logout handler
async function handleLogout() {
    try {
        const response = await fetch('/api/logout', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        if (response.ok) {
            window.location.href = '/login';
        }
    } catch (err) {
        console.error('Logout error:', err);
        window.location.href = '/login'; // fallback redirection
    }
}

// Network status handling for Login Page
function checkNetworkStatus() {
    const offlineMessage = document.getElementById('offlineMessage');
    if (!offlineMessage) return; // Only run on login page
    
    if (!navigator.onLine) {
        offlineMessage.classList.remove('hidden');
        if (submitBtn) {
            submitBtn.disabled = true;
            if (!submitBtn.getAttribute('data-original-content')) {
                submitBtn.setAttribute('data-original-content', submitBtn.innerHTML);
            }
            submitBtn.innerHTML = '<span>Hubungan Terputus</span>';
        }
    } else {
        offlineMessage.classList.add('hidden');
        if (submitBtn) {
            submitBtn.disabled = false;
            const originalContent = submitBtn.getAttribute('data-original-content');
            if (originalContent) {
                submitBtn.innerHTML = originalContent;
                submitBtn.removeAttribute('data-original-content');
            } else {
                submitBtn.innerHTML = '<span>Log Masuk ke Pejabat</span>';
            }
        }
    }
}

if (loginForm) {
    window.addEventListener('online', checkNetworkStatus);
    window.addEventListener('offline', checkNetworkStatus);
    checkNetworkStatus();
}

