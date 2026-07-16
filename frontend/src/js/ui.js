// UI helpers and state management

async function executeTask(userPrompt, modelSelect, terminal, resultBox, sendBtn) {
    const p = userPrompt.value.trim();
    const m = modelSelect.value;
    if (!p) return;

    sendBtn.disabled = true;
    sendBtn.innerHTML = `<span>${t('btn-sending')}</span>`;
    terminal.innerHTML = '';
    resultBox.classList.add('hidden');

    addLog(terminal, t('receiving-instructions'));
    addLog(terminal, t('analyzing-tasks'), 'agent');

    try {
        const data = await fetchExecute(p, m);

        if (data.status === 'success') {
            let combinedResult = '';
            data.results.forEach(res => {
                addLog(terminal, t('agent-done', { agent: res.agent }), 'success');
                combinedResult += `--- HASIL KERJA ${res.agent} ---\n${res.result}\n\n`;
            });

            document.getElementById('agentBadge').innerText = `${t('minit-kerja')}: ${data.results.map(r => r.agent).join(', ')}`;
            document.getElementById('speedBadge').innerText = data.total_speed;
            document.getElementById('finalOutput').innerText = combinedResult;
            resultBox.classList.remove('hidden');
            const historyBody = document.getElementById('historyBody');
            updateHistory(historyBody);
        } else if (data.status === 'rejected') {
            addLog(terminal, t('claudia-rejected', { message: data.message }), 'error');
            document.getElementById('agentBadge').innerText = `Claudia: Ditolak`;
            document.getElementById('finalOutput').innerText = data.message;
            resultBox.classList.remove('hidden');
        } else {
            addLog(terminal, `Ralat: ${data.detail || data.message}`, 'error');
        }
    } catch (e) {
        addLog(terminal, t('connection-lost'), 'error');
        console.error('Execute error:', e);
    }
    sendBtn.disabled = false;
    sendBtn.innerHTML = `<span>${t('btn-send')}</span>`;
}

