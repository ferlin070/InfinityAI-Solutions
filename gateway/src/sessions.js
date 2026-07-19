const { Client, LocalAuth } = require("whatsapp-web.js");
const qrcode = require("qrcode");
const axios = require("axios");
const fs = require("fs");
const path = require("path");
const config = require("./config");

const sessions = new Map(); // channelId -> { client, status, qr }

function createSession(channelId) {
  if (sessions.has(channelId)) {
    return sessions.get(channelId);
  }

  const client = new Client({
    authStrategy: new LocalAuth({ clientId: channelId }),
    webVersionCache: {
      type: "remote",
      remotePath: "https://raw.githubusercontent.com/wppconnect-team/wa-version/main/html/2.2412.54.html",
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
      await axios.post(
        config.fastapiWebhookUrl,
        {
          channel_id: channelId,
          from: msg.from,
          body: msg.body,
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

module.exports = { createSession, getSession, destroySession };
