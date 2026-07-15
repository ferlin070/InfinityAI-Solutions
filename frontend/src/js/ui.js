// UI helpers and state management

async function executeTask(userPrompt, modelSelect, terminal, resultBox, sendBtn) {
    const p = userPrompt.value.trim();
    const m = modelSelect.value;
    if (!p) return;

    sendBtn.disabled = true;
    sendBtn.innerHTML = `<span>Claudia sedang delegasi…</span>`;
    terminal.innerHTML = '';
    resultBox.classList.add('hidden');

    addLog(terminal, 'Menerima arahan dari Bos...');
    addLog(terminal, 'Claudia menganalisis tugas...', 'agent');

    try {
        const data = await fetchExecute(p, m);

        if (data.status === 'success') {
            let combinedResult = '';
            data.results.forEach(res => {
                addLog(terminal, `Ejen ${res.agent} telah menyiapkan tugasan.`, 'success');
                combinedResult += `--- HASIL KERJA ${res.agent} ---\n${res.result}\n\n`;
            });

            document.getElementById('agentBadge').innerText = `Kolaborasi: ${data.results.map(r => r.agent).join(', ')}`;
            document.getElementById('speedBadge').innerText = data.total_speed;
            document.getElementById('finalOutput').innerText = combinedResult;
            resultBox.classList.remove('hidden');
            const historyBody = document.getElementById('historyBody');
            updateHistory(historyBody);
        } else if (data.status === 'rejected') {
            addLog(terminal, `Claudia menolak tugasan: ${data.message}`, 'error');
            document.getElementById('agentBadge').innerText = `Claudia: Ditolak`;
            document.getElementById('finalOutput').innerText = data.message;
            resultBox.classList.remove('hidden');
        } else {
            addLog(terminal, `Ralat: ${data.detail || data.message}`, 'error');
        }
    } catch (e) {
        addLog(terminal, 'Sambungan ke pelayan terputus. Cuba hantar semula.', 'error');
        console.error('Execute error:', e);
    }
    sendBtn.disabled = false;
    sendBtn.innerHTML = `<span>Hantar Arahan ke Claudia</span>`;
}
