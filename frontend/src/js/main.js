// Frontend entry point and initialization

const terminal = document.getElementById('terminal');
const historyBody = document.getElementById('historyBody');
const userPrompt = document.getElementById('userPrompt');
const modelSelect = document.getElementById('modelSelect');
const sendBtn = document.getElementById('sendBtn');
const resultBox = document.getElementById('resultBox');

// Set up letterhead with today's date and reference number
document.getElementById('tarikh').textContent =
    new Intl.DateTimeFormat('ms-MY', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }).format(new Date());

document.getElementById('refNo').textContent =
    'ARH/' + new Date().toISOString().slice(0, 10).replace(/-/g, '') + '/' + String(Math.floor(Math.random() * 900) + 100);

// Attach event handler
sendBtn.addEventListener('click', () => {
    executeTask(userPrompt, modelSelect, terminal, resultBox, sendBtn);
});

// Initialize history
updateHistory(historyBody);

// Update history every 10 seconds
setInterval(() => updateHistory(historyBody), 10000);
