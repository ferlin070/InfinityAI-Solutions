// Terminal logger utilities

function escapeHtml(str) {
    if (!str) return '';
    return str.toString()
              .replace(/&/g, "&amp;")
              .replace(/</g, "&lt;")
              .replace(/>/g, "&gt;")
              .replace(/"/g, "&quot;")
              .replace(/'/g, "&#039;");
}

function addLog(terminal, msg, type = 'info') {
    const div = document.createElement('div');
    let cls = '';
    if (type === 'success') cls = 'log-success';
    if (type === 'error') cls = 'log-error';
    if (type === 'agent') cls = 'log-agent';
    div.className = `log-line ${cls}`;

    const prefix = document.createElement('span');
    prefix.className = 'log-prefix';
    prefix.textContent = new Date().toLocaleTimeString('ms-MY', { hour12: false }).slice(0, 5);

    const content = document.createTextNode(msg);

    div.appendChild(prefix);
    div.appendChild(content);
    terminal.appendChild(div);
    terminal.scrollTop = terminal.scrollHeight;
}
