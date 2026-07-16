// Frontend entry point and initialization

const terminal = document.getElementById('terminal');
const historyBody = document.getElementById('historyBody');
const userPrompt = document.getElementById('userPrompt');
const modelSelect = document.getElementById('modelSelect');
const sendBtn = document.getElementById('sendBtn');
const resultBox = document.getElementById('resultBox');

// Set up date dynamic formatting
function updateDate() {
    const locale = currentLang === 'en' ? 'en-US' : 'ms-MY';
    document.getElementById('tarikh').textContent =
        new Intl.DateTimeFormat(locale, { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }).format(new Date());
}

// Initial date setup
updateDate();

document.getElementById('refNo').textContent =
    'ARH/' + new Date().toISOString().slice(0, 10).replace(/-/g, '') + '/' + String(Math.floor(Math.random() * 900) + 100);

// Attach event handler
sendBtn.addEventListener('click', () => {
    executeTask(userPrompt, modelSelect, terminal, resultBox, sendBtn);
});

// Theme toggle logic (stored in memory)
const themeToggle = document.getElementById('themeToggle');
let isDarkMode = false;

themeToggle.addEventListener('click', () => {
    isDarkMode = !isDarkMode;
    if (isDarkMode) {
        document.documentElement.setAttribute('data-theme', 'dark');
        // Update tag default and text content
        themeToggle.setAttribute('data-i18n-default', 'Mod Siang');
        themeToggle.textContent = currentLang === 'en' ? 'Day Mode' : 'Mod Siang';
    } else {
        document.documentElement.removeAttribute('data-theme');
        themeToggle.setAttribute('data-i18n-default', 'Mod Malam');
        themeToggle.textContent = currentLang === 'en' ? 'Night Mode' : 'Mod Malam';
    }
});

// Language toggle logic
const langToggle = document.getElementById('langToggle');
if (langToggle) {
    langToggle.addEventListener('click', () => {
        if (currentLang === 'ms') {
            translatePage('en');
            langToggle.textContent = 'BM';
        } else {
            translatePage('ms');
            langToggle.textContent = 'EN';
        }
        updateDate();
    });
}

// Logout logic
const logoutBtn = document.getElementById('logoutBtn');
if (logoutBtn) {
    logoutBtn.addEventListener('click', () => {
        handleLogout();
    });
}

// Load dynamic user profile info
async function loadUserProfile() {
    try {
        const response = await fetch('/api/me');
        if (response.ok) {
            const data = await response.json();
            if (data.status === 'success') {
                const name = data.user.name;
                const email = data.user.email;
                
                const letterheadSub = document.getElementById('letterheadSub');
                
                // Update translations dictionary dynamically
                translations.en['sub-title'] = `Staff On Duty: ${name} (${email}) · Work saved to Google Drive`;
                
                // Update default value for fallback
                letterheadSub.setAttribute('data-i18n-default', `Kakitangan Bertugas: ${name} (${email}) · Hasil kerja disimpan ke Google Drive`);
                
                // Set initial text based on current language
                if (currentLang === 'en') {
                    letterheadSub.textContent = translations.en['sub-title'];
                } else {
                    letterheadSub.textContent = letterheadSub.getAttribute('data-i18n-default');
                }
            }
        }
    } catch (e) {
        console.error("Error loading user profile:", e);
    }
}

// Initialize history and profile
loadUserProfile();
updateHistory(historyBody);

// Update history every 10 seconds
setInterval(() => updateHistory(historyBody), 10000);

