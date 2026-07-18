// streamChatFactory — wraps fetch() with SSE parsing. Used by useAgentStream.
// Mirrors the existing streamChat in api.js but exposes the raw event
// stream (event_type, payload) instead of a single status-text update,
// so the Agent Workspace can render the full timeline.

export function streamChatFactory({ url, sessionToken, getSessionToken }) {
  return async function streamChat(prompt, model, onEvent) {
    let token = sessionToken;
    if (!token && typeof getSessionToken === 'function') {
      token = getSessionToken();
    }
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers['Cookie'] = `session_token=${token}`;

    const res = await fetch(url, {
      method: 'POST',
      headers,
      credentials: 'include',
      body: JSON.stringify({ prompt, model: model || 'gpt-4o-mini' }),
    });
    if (!res.ok || !res.body) {
      throw new Error(`Stream failed: ${res.status} ${res.statusText}`);
    }
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buf = '';
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      // SSE frames are separated by \n\n. Parse one at a time.
      let idx;
      while ((idx = buf.indexOf('\n\n')) !== -1) {
        const frame = buf.slice(0, idx);
        buf = buf.slice(idx + 2);
        const ev = parseFrame(frame);
        if (ev) {
          try { onEvent(ev.event, ev.data); } catch (_) { /* keep streaming */ }
        }
      }
    }
  };
}

function parseFrame(frame) {
  // Strip a leading "data: " (or repeated) and a trailing "data: [DONE]".
  const lines = frame.split('\n').map((l) => l.trim()).filter(Boolean);
  let event = 'message';
  const dataLines = [];
  for (const line of lines) {
    if (line.startsWith('event:')) event = line.slice(6).trim();
    else if (line.startsWith('data:')) dataLines.push(line.slice(5).trim());
  }
  const dataStr = dataLines.join('\n');
  if (!dataStr || dataStr === '[DONE]') return null;
  let data;
  try { data = JSON.parse(dataStr); } catch { data = { text: dataStr }; }
  return { event, data };
}
