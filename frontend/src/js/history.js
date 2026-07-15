// Activity log management

async function updateHistory(historyBody) {
    try {
        const logs = await fetchHistory();
        document.getElementById('totalTasks').innerText = logs.length;
        document.getElementById('completedTasks').innerText = logs.filter(l => l.status === 'Success').length;
        historyBody.innerHTML = logs.map(l => `
            <tr>
                <td class="t-time">${escapeHtml(l.timestamp)}</td>
                <td class="t-agent">${escapeHtml(l.agent)}</td>
                <td class="t-model">${escapeHtml(l.model)}</td>
                <td><span class="chip">${escapeHtml(l.status)}</span></td>
                <td class="t-speed t-right">${escapeHtml(l.speed)}</td>
            </tr>
        `).join('');
    } catch (e) {
        console.error('Error fetching history:', e);
    }
}
