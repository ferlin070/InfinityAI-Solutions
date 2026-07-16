// API Client utilities

async function fetchExecute(prompt, modelName) {
    const response = await fetch('/api/executions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt, model: modelName })
    });
    if (response.status === 401) {
        window.location.href = '/login';
        return { status: 'error', message: 'Sesi tamat. Sila log masuk semula.' };
    }
    return response.json();
}

async function fetchHistory() {
    const response = await fetch('/api/history');
    if (response.status === 401) {
        window.location.href = '/login';
        return [];
    }
    return response.json();
}

