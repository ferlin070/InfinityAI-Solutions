// WhatsApp Operations UI

let waPollInterval = null;
let qrPollInterval = null;
let activeChannelId = null;

// ─── Channels (WhatsApp Connection) ──────────────────────────

async function loadChannels() {
    const list = document.getElementById('waChannelList');
    const count = document.getElementById('waConnCount');
    if (!list) return;
    try {
        const channels = await fetchChannels();
        if (!channels || channels.length === 0) {
            list.innerHTML = '<span style="font-size:12px;color:var(--ink-faint);" data-i18n="wa-no-channels">Belum ada nombor WhatsApp disambungkan.</span>';
            if (count) count.textContent = '0 bersambung';
            return;
        }
        const connected = channels.filter(c => c.status === 'connected').length;
        if (count) count.textContent = `${connected} bersambung`;
        list.innerHTML = channels.map(ch => {
            let badge = '';
            let actionBtn = '';
            if (ch.status === 'connected') {
                badge = '<span style="color:var(--green);font-weight:600;">● Connected</span>';
                actionBtn = `<button class="btn-stamp" style="width:auto;margin:0;padding:4px 10px;font-size:9px;background:var(--stamp);border-color:var(--stamp);" onclick="disconnectChannel('${ch.id}')">Putus</button>`;
            } else if (ch.status === 'pending_qr') {
                badge = '<span style="color:#c97d2e;font-weight:600;">● Waiting QR</span>';
                actionBtn = `<button class="btn-stamp" style="width:auto;margin:0;padding:4px 10px;font-size:9px;" onclick="showQR('${ch.id}')">Tunjuk QR</button>`;
            } else {
                badge = '<span style="color:var(--ink-faint);">● Disconnected</span>';
                actionBtn = `<button class="btn-stamp" style="width:auto;margin:0;padding:4px 10px;font-size:9px;" onclick="reconnectChannel('${ch.id}')">Sambung Semula</button>`;
            }
            return `
                <div style="display:flex;align-items:center;gap:10px;padding:8px 14px;border:1px solid var(--rule);border-radius:3px;background:var(--card);font-size:12px;">
                    <span style="font-family:'IBM Plex Mono',monospace;">${escapeHtml(ch.phone_number || 'Unknown')}</span>
                    ${badge}
                    ${actionBtn}
                </div>
            `;
        }).join('');
    } catch (e) {
        console.error('loadChannels error:', e);
    }
}

async function connectChannel() {
    const input = document.getElementById('waPhoneInput');
    const phone = input.value.trim();
    if (!phone) { alert('Sila masukkan nombor telefon.'); return; }

    const btn = document.getElementById('waConnectBtn');
    btn.disabled = true;
    btn.innerHTML = '<span>Menyambung...</span>';

    try {
        const channel = await fetchCreateChannel(phone);
        input.value = '';
        activeChannelId = channel.id;
        await loadChannels();
        await showQR(channel.id);
    } catch (e) {
        console.error('connectChannel error:', e);
        alert('Gagal menyambung. Pastikan Gateway sedang berjalan.');
    }
    btn.disabled = false;
    btn.innerHTML = '<span>Sambung Nombor Baru</span>';
}

async function showQR(channelId) {
    const display = document.getElementById('waQRDisplay');
    const img = document.getElementById('waQRImage');
    const status = document.getElementById('waQRStatus');
    display.classList.remove('hidden');
    activeChannelId = channelId;

    if (qrPollInterval) clearInterval(qrPollInterval);

    async function pollQR() {
        try {
            const data = await fetchChannelQR(channelId);
            if (!data) return;
            if (data.qr) {
                img.src = data.qr;
                status.textContent = 'Scan QR ini dengan WhatsApp anda...';
            }
            if (data.status === 'connected') {
                status.textContent = '✓ Bersambung!';
                status.style.color = 'var(--green)';
                clearInterval(qrPollInterval);
                qrPollInterval = null;
                display.classList.add('hidden');
                loadChannels();
            } else if (data.status === 'disconnected') {
                status.textContent = 'Sambungan terputus. Cuba lagi.';
            }
        } catch (e) {
            console.error('QR poll error:', e);
        }
    }

    await pollQR();
    qrPollInterval = setInterval(pollQR, 3000);
}

async function reconnectChannel(channelId) {
    try {
        await fetchCreateChannel('reconnect');
        activeChannelId = channelId;
        await loadChannels();
        await showQR(channelId);
    } catch (e) {
        console.error('reconnect error:', e);
    }
}

async function disconnectChannel(channelId) {
    if (!confirm('Putuskan sambungan WhatsApp ini?')) return;
    try {
        await fetchDeleteChannel(channelId);
        if (activeChannelId === channelId) {
            document.getElementById('waQRDisplay').classList.add('hidden');
            activeChannelId = null;
        }
        await loadChannels();
    } catch (e) {
        console.error('disconnect error:', e);
    }
}

// ─── Tab Switching ────────────────────────────────────────────

function switchWASubtab(subtab) {
    document.querySelectorAll('.wa-subtab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.wa-panel').forEach(p => p.classList.add('hidden'));

    const btn = document.querySelector(`.wa-subtab[data-panel="${subtab}"]`);
    if (btn) btn.classList.add('active');

    const panel = document.getElementById(`waPanel${subtab.charAt(0).toUpperCase() + subtab.slice(1)}`);
    if (panel) panel.classList.remove('hidden');

    if (subtab === 'conversations') loadConversations();
    else if (subtab === 'leads') loadLeads();
    else if (subtab === 'quotations') loadQuotations();
}

// ─── Conversations ────────────────────────────────────────────

async function loadConversations() {
    const list = document.getElementById('waConvList');
    if (!list) return;
    list.innerHTML = '<div class="wa-empty">Memuatkan perbualan...</div>';
    try {
        const data = await fetchConversations();
        if (!data || data.length === 0) {
            list.innerHTML = '<div class="wa-empty">Tiada perbualan aktif.</div>';
            return;
        }
        list.innerHTML = data.map(c => {
            const contact = c.contacts || {};
            const lastMsg = c.last_message || '';
            const score = contact.score || 'cold';
            const mode = c.mode === 'human' ? ' <span class="wa-conv-badge human">HUMAN</span>' : '';
            const scoreBadge = score !== 'cold' ? ` <span class="wa-conv-badge ${score}">${score.toUpperCase()}</span>` : '';
            return `
                <div class="wa-conv-item" data-id="${c.id}" data-channel="${c.channel_id || ''}" data-phone="${contact.phone || ''}"
                     onclick="selectConversation('${c.id}', '${c.channel_id || ''}', '${(contact.phone || '').replace(/'/g, "\\'")}')">
                    <div class="wa-conv-info">
                        <div class="wa-conv-name">${escapeHtml(contact.name || 'Unknown')}${scoreBadge}${mode}</div>
                        <div class="wa-conv-preview">${escapeHtml(lastMsg.substring(0, 80))}</div>
                    </div>
                    <div class="wa-conv-meta">
                        <div class="wa-conv-time">${escapeHtml(c.updated_at ? new Date(c.updated_at).toLocaleTimeString('ms-MY', { hour: '2-digit', minute: '2-digit' }) : '')}</div>
                    </div>
                </div>
            `;
        }).join('');
    } catch (e) {
        console.error('loadConversations error:', e);
        list.innerHTML = '<div class="wa-empty">Ralat memuatkan perbualan.</div>';
    }
}

let selectedConvId = null;
let selectedChannelId = null;
let selectedPhone = null;

async function selectConversation(convId, channelId, phone) {
    selectedConvId = convId;
    selectedChannelId = channelId;
    selectedPhone = phone;

    document.querySelectorAll('.wa-conv-item').forEach(el => el.classList.remove('active'));
    const el = document.querySelector(`.wa-conv-item[data-id="${convId}"]`);
    if (el) el.classList.add('active');

    const thread = document.getElementById('waMessageThread');
    const inputArea = document.getElementById('waInputArea');
    if (!thread) return;

    thread.innerHTML = '<div class="wa-empty">Memuatkan pesanan...</div>';
    inputArea.classList.add('hidden');

    if (phone) {
        document.getElementById('waTakeoverBtn').classList.remove('hidden');
    }

    try {
        const msgs = await fetchConversationMessages(convId);
        if (!msgs || msgs.length === 0) {
            thread.innerHTML = '<div class="wa-empty">Tiada pesanan dalam perbualan ini.</div>';
            return;
        }
        thread.innerHTML = msgs.map(m => {
            const isInbound = m.direction === 'inbound';
            return `
                <div class="wa-msg wa-msg-${isInbound ? 'inbound' : 'outbound'}">
                    <div class="wa-msg-bubble">${escapeHtml(m.body || '')}</div>
                    <div class="wa-msg-time">${escapeHtml(new Date(m.created_at).toLocaleString('ms-MY', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }))} · ${escapeHtml(m.sender)}</div>
                </div>
            `;
        }).join('');
        thread.scrollTop = thread.scrollHeight;
        inputArea.classList.remove('hidden');
    } catch (e) {
        console.error('selectConversation error:', e);
        thread.innerHTML = '<div class="wa-empty">Ralat memuatkan pesanan.</div>';
    }
}

async function takeoverConversation() {
    if (!selectedConvId) return;
    try {
        await fetchTakeover(selectedConvId);
        loadConversations();
        const thread = document.getElementById('waMessageThread');
        thread.innerHTML = '<div class="wa-empty">Perbualan telah diambil alih. Anda boleh balas secara manual.</div>';
        document.getElementById('waTakeoverBtn').classList.add('hidden');
    } catch (e) {
        console.error('takeover error:', e);
    }
}

async function sendWaMessage() {
    const input = document.getElementById('waReplyInput');
    const body = input.value.trim();
    if (!body || !selectedConvId || !selectedChannelId || !selectedPhone) return;

    input.disabled = true;
    try {
        await fetchSendMessage(selectedConvId, body, selectedChannelId, selectedPhone);
        input.value = '';
        selectConversation(selectedConvId, selectedChannelId, selectedPhone);
    } catch (e) {
        console.error('send message error:', e);
    }
    input.disabled = false;
    input.focus();
}

// ─── Leads ────────────────────────────────────────────────────

async function loadLeads(scoreFilter) {
    const grid = document.getElementById('waLeadGrid');
    if (!grid) return;
    grid.innerHTML = '<div class="wa-empty">Memuatkan leads...</div>';
    try {
        const data = await fetchLeads(scoreFilter);
        if (!data || data.length === 0) {
            grid.innerHTML = '<div class="wa-empty">Tiada leads dijumpai.</div>';
            return;
        }
        grid.innerHTML = data.map(l => {
            const contact = l.contacts || {};
            return `
                <div class="card wa-lead-card">
                    <div class="wa-lead-header">
                        <div>
                            <div class="wa-lead-name">${escapeHtml(contact.name || 'Unknown')}</div>
                            <div class="wa-lead-phone">${escapeHtml(contact.phone || '')}</div>
                        </div>
                        <div class="wa-lead-score ${l.score}">${escapeHtml(l.score)}</div>
                    </div>
                    <div class="wa-lead-meta">Status: <strong>${escapeHtml(l.status)}</strong></div>
                    <div class="wa-lead-meta">Minat: ${escapeHtml(l.interest_summary || 'Tiada')}</div>
                    <div class="wa-lead-reason">${escapeHtml(l.score_reason || '')}</div>
                </div>
            `;
        }).join('');
    } catch (e) {
        console.error('loadLeads error:', e);
        grid.innerHTML = '<div class="wa-empty">Ralat memuatkan leads.</div>';
    }
}

// ─── Quotations ───────────────────────────────────────────────

async function loadQuotations() {
    const list = document.getElementById('waQuoteList');
    if (!list) return;
    list.innerHTML = '<div class="wa-empty">Memuatkan quotation...</div>';
    try {
        const data = await fetchQuotations();
        if (!data || data.length === 0) {
            list.innerHTML = '<div class="wa-empty">Tiada quotation menunggu approval.</div>';
            return;
        }
        list.innerHTML = data.map(q => {
            const lead = q.leads || {};
            const contact = lead.contacts || {};
            return `
                <div class="wa-quote-item">
                    <div>
                        <div class="wa-quote-number">${escapeHtml(q.number)}</div>
                        <div class="wa-quote-contact">${escapeHtml(contact.name || 'Unknown')} — ${escapeHtml(q.currency || 'MYR')}</div>
                    </div>
                    <div class="wa-quote-total">RM${parseFloat(q.total || 0).toFixed(2)}</div>
                    <div class="wa-quote-actions">
                        <button class="wa-btn-approve" onclick="approveQuotation('${q.id}')">Approve</button>
                        <button class="wa-btn-reject" onclick="rejectQuotation('${q.id}')">Tolak</button>
                    </div>
                </div>
            `;
        }).join('');
    } catch (e) {
        console.error('loadQuotations error:', e);
        list.innerHTML = '<div class="wa-empty">Ralat memuatkan quotation.</div>';
    }
}

async function approveQuotation(quoteId) {
    try {
        await fetchApproveQuotation(quoteId);
        loadQuotations();
    } catch (e) {
        console.error('approve error:', e);
    }
}

function rejectQuotation(quoteId) {
    if (confirm('Tolak quotation ini?')) {
        loadQuotations();
    }
}

// ─── Polling ──────────────────────────────────────────────────

function startWAPolling() {
    stopWAPolling();
    loadChannels();
    const active = document.querySelector('.wa-subtab.active');
    if (active) switchWASubtab(active.dataset.panel);
    waPollInterval = setInterval(() => {
        loadChannels();
        const active = document.querySelector('.wa-subtab.active');
        if (!active) return;
        const panel = active.dataset.panel;
        if (panel === 'conversations') loadConversations();
    }, 10000);
}

function stopWAPolling() {
    if (waPollInterval) {
        clearInterval(waPollInterval);
        waPollInterval = null;
    }
    if (qrPollInterval) {
        clearInterval(qrPollInterval);
        qrPollInterval = null;
    }
}

// ─── Init ─────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    const connectBtn = document.getElementById('waConnectBtn');
    if (connectBtn) connectBtn.addEventListener('click', connectChannel);

    const phoneInput = document.getElementById('waPhoneInput');
    if (phoneInput) {
        phoneInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') connectChannel();
        });
    }

    const sendBtn = document.getElementById('waSendBtn');
    if (sendBtn) sendBtn.addEventListener('click', sendWaMessage);

    const replyInput = document.getElementById('waReplyInput');
    if (replyInput) {
        replyInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendWaMessage();
            }
        });
    }

    const takeoverBtn = document.getElementById('waTakeoverBtn');
    if (takeoverBtn) takeoverBtn.addEventListener('click', takeoverConversation);
});
