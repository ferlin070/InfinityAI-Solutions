// API Client utilities

async function apiGet(path) {
    const response = await fetch(path);
    if (response.status === 401) { window.location.href = '/login'; return null; }
    return response.json();
}

async function apiPost(path, body) {
    const response = await fetch(path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
    });
    if (response.status === 401) { window.location.href = '/login'; return null; }
    return response.json();
}

async function fetchExecute(prompt, modelName) {
    return apiPost('/api/executions', { prompt, model: modelName });
}

async function fetchHistory() {
    return apiGet('/api/history');
}

// ─── WhatsApp API ─────────────────────────────────────────────

async function fetchConversations(status) {
    const path = status ? `/api/conversations?status=${status}` : '/api/conversations';
    return apiGet(path);
}

async function fetchConversationMessages(convId, limit) {
    const path = limit ? `/api/conversations/${convId}/messages?limit=${limit}` : `/api/conversations/${convId}/messages`;
    return apiGet(path);
}

async function fetchTakeover(convId) {
    return apiPost(`/api/conversations/${convId}/takeover`, {});
}

async function fetchSendMessage(convId, body, channelId, to) {
    return apiPost(`/api/conversations/${convId}/send`, { body, channel_id: channelId, to });
}

async function fetchLeads(scoreFilter) {
    const path = scoreFilter ? `/api/leads?score=${scoreFilter}` : '/api/leads';
    return apiGet(path);
}

async function fetchQuotations(status) {
    const path = status ? `/api/quotations?status=${status}` : '/api/quotations';
    return apiGet(path);
}

async function fetchApproveQuotation(quoteId) {
    return apiPost(`/api/quotations/${quoteId}/approve`, { approved_by: 'Bos' });
}

// ─── Channels API ─────────────────────────────────────────────

async function fetchChannels() {
    return apiGet('/api/channels');
}

async function fetchCreateChannel(phoneNumber) {
    return apiPost('/api/channels', { phone_number: phoneNumber });
}

async function fetchChannelQR(channelId) {
    return apiGet(`/api/channels/${channelId}/qr`);
}

async function fetchChannelStatus(channelId) {
    return apiGet(`/api/channels/${channelId}/status`);
}

async function fetchDeleteChannel(channelId) {
    return apiPost(`/api/channels/${channelId}/disconnect`, {});
}

