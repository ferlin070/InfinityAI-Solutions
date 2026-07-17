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

// ─── Unified dashboard chat (live SSE) ───────────────────────

// EventSource doesn't support POST bodies, so the SSE stream is parsed by
// hand over a fetch() ReadableStream. `onEvent(eventType, payload)` is
// called for every "event: ...\ndata: ...\n\n" frame the server sends —
// progress events (status/tool_call/agent_start/agent_done) while Claudia
// and any specialists work, then a terminal "final" (or "error") event.
export async function streamChat(prompt, modelName, onEvent) {
    const response = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt, model: modelName })
    });

    if (response.status === 401) {
        window.location.href = '#login';
        return;
    }
    if (!response.ok || !response.body) {
        throw new Error('Sambungan streaming gagal.');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        let sepIndex;
        while ((sepIndex = buffer.indexOf('\n\n')) !== -1) {
            const rawEvent = buffer.slice(0, sepIndex);
            buffer = buffer.slice(sepIndex + 2);

            let eventType = 'message';
            let dataLine = null;
            for (const line of rawEvent.split('\n')) {
                if (line.startsWith('event: ')) eventType = line.slice(7);
                else if (line.startsWith('data: ')) dataLine = line.slice(6);
            }
            if (dataLine !== null) {
                try {
                    onEvent(eventType, JSON.parse(dataLine));
                } catch (e) {
                    console.error('Gagal parse SSE event:', e);
                }
            }
        }
    }
}

export async function fetchChatHistory() {
    return apiGet('/api/chat/history');
}

export async function clearChat() {
    return apiPost('/api/chat/clear', {});
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
