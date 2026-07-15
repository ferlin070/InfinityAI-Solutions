// API Client utilities

async function fetchExecute(prompt, modelName) {
    const response = await fetch('/api/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt, model_name: modelName })
    });
    return response.json();
}

async function fetchHistory() {
    const response = await fetch('/api/history');
    return response.json();
}
