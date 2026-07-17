// API Client utilities for React Frontend

export async function apiGet(path) {
    const response = await fetch(path);
    if (response.status === 401) {
        window.location.href = '#login';
        return null;
    }
    return response.json();
}

export async function apiPost(path, body) {
    const response = await fetch(path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
    });
    if (response.status === 401) {
        window.location.href = '#login';
        return null;
    }
    return response.json();
}

export async function fetchExecute(prompt, modelName) {
    return apiPost('/api/executions', { prompt, model: modelName });
}

export async function fetchHistory() {
    return apiGet('/api/history');
}

// ─── WhatsApp API ─────────────────────────────────────────────

export async function fetchConversations(status) {
    const path = status ? `/api/conversations?status=${status}` : '/api/conversations';
    return apiGet(path);
}

export async function fetchConversationMessages(convId, limit) {
    const path = limit ? `/api/conversations/${convId}/messages?limit=${limit}` : `/api/conversations/${convId}/messages`;
    return apiGet(path);
}

export async function fetchTakeover(convId) {
    return apiPost(`/api/conversations/${convId}/takeover`, {});
}

export async function fetchSendMessage(convId, body, channelId, to) {
    return apiPost(`/api/conversations/${convId}/send`, { body, channel_id: channelId, to });
}

export async function fetchLeads(scoreFilter) {
    const path = scoreFilter ? `/api/leads?score=${scoreFilter}` : '/api/leads';
    return apiGet(path);
}

export async function fetchQuotations(status) {
    const path = status ? `/api/quotations?status=${status}` : '/api/quotations';
    return apiGet(path);
}

export async function fetchApproveQuotation(quoteId) {
    return apiPost(`/api/quotations/${quoteId}/approve`, { approved_by: 'Bos' });
}

// ─── Channels API ─────────────────────────────────────────────

export async function fetchChannels() {
    return apiGet('/api/channels');
}

export async function fetchCreateChannel(phoneNumber) {
    return apiPost('/api/channels', { phone_number: phoneNumber });
}

export async function fetchChannelQR(channelId) {
    return apiGet(`/api/channels/${channelId}/qr`);
}

export async function fetchChannelStatus(channelId) {
    return apiGet(`/api/channels/${channelId}/status`);
}

export async function fetchDeleteChannel(channelId) {
    return apiPost(`/api/channels/${channelId}/disconnect`, {});
}

// ─── Auth API ──────────────────────────────────────────────────

export async function login(email, password) {
    return apiPost('/api/login', { email, password });
}

export async function logout() {
    return apiPost('/api/logout', {});
}

export async function checkMe() {
    return apiGet('/api/me');
}
