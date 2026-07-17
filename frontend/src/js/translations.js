// Simple Translation dictionary and helpers for i18n
let currentLang = 'ms'; // Default: Bahasa Melayu

const translations = {
    en: {
        "wordmark": "InfinityAI Solutions · AI Command Center System",
        "title": "Daily Operations Office",
        "sub-title": "Eight agents active · Work saved to Google Drive",
        "borang-title": "Work Order Form",
        "borang-note": "Copy: Operations File",
        "total-tasks": "Total Tasks",
        "completed-tasks": "Completed",
        "ref-no": "Ref. Number",
        "kepada": "To",
        "claudia-desc": "Claudia — Chief of Staff (delegation to relevant agents)",
        "enjin-ai": "AI Engine",
        "butiran-arahan": "Order Details",
        "placeholder-arahan": "Write work instructions for the team here...",
        "btn-send": "Send Order to Claudia",
        "btn-sending": "Claudia is delegating...",
        "log-title": "Communication Log",
        "log-note": "Real-time",
        "log-empty": "No records yet. Logs will be written here as soon as orders are sent.",
        "minit-kerja": "Minutes of Work",
        "roster-title": "Staff On Duty Today",
        "roster-note": "8 / 8 present",
        "staff-01": "Staff No. 01",
        "staff-02": "Staff No. 02",
        "staff-03": "Staff No. 03",
        "staff-04": "Staff No. 04",
        "staff-05": "Staff No. 05",
        "staff-06": "Staff No. 06",
        "staff-07": "Staff No. 07",
        "staff-08": "Staff No. 08",
        "status-coordinating": "Coordinating",
        "status-ready": "Ready",
        "role-claudia": "Chief of Staff",
        "role-zara": "Finance",
        "role-maya": "Sales & CRM",
        "role-aiman": "Marketing",
        "role-danish": "Creative Content",
        "role-hakim": "System Architect",
        "role-amelia": "Training",
        "role-adila": "Operations",
        "buku-log": "Activity Logbook",
        "log-limit": "Last 50 entries",
        "log-update": "Updates every 10s",
        "th-time": "Time",
        "th-agent": "Agent",
        "th-engine": "Engine",
        "th-status": "Status",
        "th-speed": "Speed",
        "footer-doc": "InfinityAI Solutions — Internal Document",
        "footer-power": "Powered by 8 AI Agents",
        "mod-malam": "Night Mode",
        "mod-siang": "Day Mode",
        "log-keluar": "Log Out",
        
        // Dynamic messaging translations
        "receiving-instructions": "Receiving instructions from Bos...",
        "analyzing-tasks": "Claudia is analyzing tasks...",
        "agent-done": "Agent {agent} has completed the task.",
        "claudia-rejected": "Claudia rejected the task: {message}",
        "connection-lost": "Connection to server lost. Try sending again.",
        "status-offline": "DISCONNECTED / OFFLINE",
        "btn-offline": "Offline / Disconnected",
        "login-offline": "Disconnected. Cannot authenticate.",

        // WhatsApp Operations
        "tab-workorder": "Work Order",
        "tab-whatsapp": "WhatsApp Ops",
        "wa-conversations": "Conversations",
        "wa-leads": "Leads",
        "wa-quotations": "Quotations",
        "wa-conv-title": "Active Conversations",
        "wa-conv-note": "10s refresh",
        "wa-msg-title": "Messages",
        "wa-takeover": "Take Over",
        "wa-select-conv": "Select a conversation from the list.",
        "wa-reply-placeholder": "Type a reply...",
        "wa-send": "Send",
        "wa-filter-all": "All",
        "wa-quote-title": "Pending Approval",

        // WhatsApp Connection
        "wa-connection-title": "WhatsApp Connection",
        "wa-phone-placeholder": "+60123456789",
        "wa-connect-btn": "Connect New Number",
        "wa-scan-qr": "Scan this QR code with your WhatsApp Business app:",
        "wa-no-channels": "No WhatsApp numbers connected yet."
    }
};

const msFallback = {
    "total-tasks": "Jumlah Tugasan",
    "completed-tasks": "Selesai",
    "roster-title": "Senarai Bertugas Hari Ini",
    "roster-note": "8 / 8 hadir",
    "staff-01": "No. Staf 01",
    "staff-02": "No. Staf 02",
    "staff-03": "No. Staf 03",
    "staff-04": "No. Staf 04",
    "staff-05": "No. Staf 05",
    "staff-06": "No. Staf 06",
    "staff-07": "No. Staf 07",
    "staff-08": "No. Staf 08",
    "status-coordinating": "Menyelaras",
    "status-ready": "Sedia",
    "role-claudia": "Ketua Turus",
    "role-zara": "Kewangan",
    "role-maya": "Jualan & CRM",
    "role-aiman": "Pemasaran",
    "role-danish": "Kandungan Kreatif",
    "role-hakim": "Arkitek Sistem",
    "role-amelia": "Latihan",
    "role-adila": "Operasi",
    "buku-log": "Buku Log Aktiviti",
    "log-limit": "50 entri terakhir",
    "log-update": "Kemas kini setiap 10 saat",
    "receiving-instructions": "Menerima arahan dari Bos...",
    "analyzing-tasks": "Claudia menganalisis tugas...",
    "agent-done": "Ejen {agent} telah menyiapkan tugasan.",
    "claudia-rejected": "Claudia menolak tugasan: {message}",
    "connection-lost": "Sambungan ke pelayan terputus. Cuba hantar semula.",
    "btn-send": "Hantar Arahan ke Claudia",
    "btn-sending": "Claudia sedang delegasi…",
    "status-offline": "SAMBUNGAN TERPUTUS / OFFLINE",
    "btn-offline": "Tiada Talian / Offline",
    "login-offline": "Rangkaian Terputus. Log masuk tidak dapat disahkan.",

    // WhatsApp Operations
    "tab-workorder": "Arahan Kerja",
    "tab-whatsapp": "Operasi WhatsApp",
    "wa-conversations": "Perbualan",
    "wa-leads": "Prospek",
    "wa-quotations": "Sebut Harga",
    "wa-conv-title": "Perbualan Aktif",
    "wa-conv-note": "10 saat",
    "wa-msg-title": "Pesanan",
    "wa-takeover": "Ambil Alih",
    "wa-select-conv": "Pilih perbualan dari senarai.",
    "wa-reply-placeholder": "Taip balasan...",
    "wa-send": "Hantar",
    "wa-filter-all": "Semua",
    "wa-quote-title": "Menunggu Kelulusan",

    // WhatsApp Connection
    "wa-connection-title": "Sambungan WhatsApp",
    "wa-phone-placeholder": "+60123456789",
    "wa-connect-btn": "Sambung Nombor Baru",
    "wa-scan-qr": "Scan QR ini dengan WhatsApp Business anda:",
    "wa-no-channels": "Belum ada nombor WhatsApp disambungkan."
};

function t(key, replacements = {}) {
    if (currentLang === 'en' && translations.en[key]) {
        let text = translations.en[key];
        for (const [k, v] of Object.entries(replacements)) {
            text = text.replace(`{${k}}`, v);
        }
        return text;
    }
    
    let text = msFallback[key] || key;
    for (const [k, v] of Object.entries(replacements)) {
        text = text.replace(`{${k}}`, v);
    }
    return text;
}

// Function to translate all static elements with data-i18n attributes
function translatePage(lang) {
    currentLang = lang;
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        
        // Store default value on first pass
        if (!el.hasAttribute('data-i18n-default')) {
            if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
                el.setAttribute('data-i18n-default', el.placeholder || '');
            } else {
                el.setAttribute('data-i18n-default', el.textContent.trim());
            }
        }
        
        const defaultText = el.getAttribute('data-i18n-default');
        
        if (lang === 'en' && translations.en[key]) {
            if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
                el.placeholder = translations.en[key];
            } else {
                // If it's the button, only replace text inside it, keeping span/icons if any
                const span = el.querySelector('span');
                if (span) {
                    span.textContent = translations.en[key];
                } else {
                    el.textContent = translations.en[key];
                }
            }
        } else {
            // Restore default
            if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
                el.placeholder = defaultText;
            } else {
                const span = el.querySelector('span');
                if (span) {
                    span.textContent = defaultText;
                } else {
                    el.textContent = defaultText;
                }
            }
        }
    });
}
