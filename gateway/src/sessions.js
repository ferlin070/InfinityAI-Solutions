const { Client, LocalAuth } = require("whatsapp-web.js");
const qrcode = require("qrcode");
const axios = require("axios");
const fs = require("fs");
const path = require("path");
const config = require("./config");

function withTimeout(promise, ms, defaultValue) {
  return new Promise((resolve) => {
    const timeout = setTimeout(() => {
      resolve(defaultValue);
    }, ms);
    promise
      .then((val) => {
        clearTimeout(timeout);
        resolve(val);
      })
      .catch(() => {
        clearTimeout(timeout);
        resolve(defaultValue);
      });
  });
}

const sessions = new Map(); // channelId -> { client, status, qr }

async function resolveJid(client, jid) {
  if (!jid || !jid.endsWith("@lid")) return jid;

  const lidUser = jid.split("@")[0];

  // 1. Try getContactLidAndPhone
  try {
    const results = await withTimeout(client.getContactLidAndPhone([jid]), 3000, null);
    if (results && results.length > 0 && results[0].pn) {
      let pn = results[0].pn;
      const pnUser = pn.split("@")[0];
      // Make sure the resolved phone number is not the LID itself
      if (pnUser !== lidUser) {
        if (!pn.endsWith("@c.us")) {
          pn = `${pn}@c.us`;
        }
        return pn;
      }
    }
  } catch (err) {
    console.error(`Error resolving LID JID via getContactLidAndPhone for ${jid}:`, err.message);
  }

  // 2. Try getContact as fallback
  try {
    const contact = await withTimeout(client.getContactById(jid), 3000, null);
    if (contact && contact.number && contact.number !== lidUser) {
      return `${contact.number}@c.us`;
    }
  } catch (err) {
    console.error(`Error resolving LID JID via getContact for ${jid}:`, err.message);
  }

  return jid; // Fallback to original @lid JID
}

function createSession(channelId) {
  if (sessions.has(channelId)) {
    return sessions.get(channelId);
  }

  const client = new Client({
    authStrategy: new LocalAuth({ clientId: channelId }),
    webVersionCache: {
      type: "remote",
      remotePath: "https://raw.githubusercontent.com/wppconnect-team/wa-version/main/html/{version}.html",
    },
    userAgent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    puppeteer: {
      headless: true,
      protocolTimeout: 120000,
      args: [
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--no-first-run",
        "--no-zygote",
        "--disable-sync",
        "--disable-blink-features=AutomationControlled",
        "--disable-features=IsolateOrigins,site-per-process",
        "--disable-site-isolation-trials",
        "--disable-accelerated-2d-canvas",
        "--js-flags=--max-old-space-size=256"
      ],
    },
  });

  const entry = { client, status: "pending_qr", qr: null };
  sessions.set(channelId, entry);

  client.on("qr", async (qrData) => {
    entry.qr = await qrcode.toDataURL(qrData);
    entry.status = "pending_qr";
  });

  client.on("ready", () => {
    entry.status = "connected";
    entry.qr = null;
  });

  client.on("disconnected", () => {
    entry.status = "disconnected";
  });

  client.on("message", async (msg) => {
    try {
      let body = msg.body;
      if (msg.type === "ciphertext" || !body) {
        // Wait 1.5 seconds for decryption
        await new Promise((resolve) => setTimeout(resolve, 1500));
        try {
          const reloaded = await msg.reload();
          if (reloaded && reloaded.body) {
            body = reloaded.body;
          }
        } catch (reloadErr) {
          console.error(`[${channelId}] Failed to reload message:`, reloadErr.message);
        }
      }

      const fromJid = await resolveJid(client, msg.from);

      await axios.post(
        config.fastapiWebhookUrl,
        {
          channel_id: channelId,
          from: fromJid,
          body: body,
          message_id: typeof msg.id === "object" ? (msg.id._serialized || msg.id.id) : msg.id,
          timestamp: msg.timestamp,
        },
        {
          headers: {
            "X-Gateway-Secret": config.gatewaySharedSecret,
            "Content-Type": "application/json",
          },
          timeout: 5000,
        }
      );
    } catch (err) {
      console.error(`[${channelId}] Failed to forward inbound message:`, err.message);
    }
  });

  // Clear stale Chrome profile locks before initializing
  const sessionDir = path.join(".wwebjs_auth", `session-${channelId}`);
  ["SingletonLock", "SingletonSocket", "SingletonCookie"].forEach((file) => {
    const fp = path.join(sessionDir, file);
    try { fs.unlinkSync(fp); } catch (_) { /* ignore if missing */ }
  });

  client.initialize().catch((err) => {
    console.error(`[${channelId}] Initialization error:`, err.message);
    entry.status = "disconnected";
  });

  return entry;
}

function getSession(channelId) {
  return sessions.get(channelId) || null;
}

function destroySession(channelId) {
  const entry = sessions.get(channelId);
  if (entry) {
    entry.client.destroy().catch(() => {});
    sessions.delete(channelId);
  }
  const sessionDir = path.join(".wwebjs_auth", `session-${channelId}`);
  try {
    fs.rmSync(sessionDir, { recursive: true, force: true });
  } catch (_) {}
}

module.exports = { createSession, getSession, destroySession, withTimeout, resolveJid };
