const express = require("express");
const { createSession, getSession, destroySession, withTimeout, resolveJid } = require("./sessions");
const config = require("./config");

const router = express.Router();

function auth(req, res, next) {
  const secret = req.headers["x-gateway-secret"];
  if (secret !== config.gatewaySharedSecret) {
    return res.status(401).json({ error: "Unauthorized" });
  }
  next();
}

router.post("/sessions/:channelId/start", auth, (req, res) => {
  const { channelId } = req.params;
  createSession(channelId);
  res.json({ status: "ok", channelId });
});

router.get("/sessions/:channelId/qr", auth, (req, res) => {
  const { channelId } = req.params;
  const session = getSession(channelId);
  if (!session) {
    return res.status(404).json({ error: "Session not found" });
  }
  if (session.status !== "pending_qr" || !session.qr) {
    return res.json({ status: session.status, qr: null });
  }
  res.json({ status: "pending_qr", qr: session.qr });
});

router.get("/sessions/:channelId/status", auth, (req, res) => {
  const { channelId } = req.params;
  const session = getSession(channelId);
  if (!session) {
    return res.json({ status: "disconnected" });
  }
  res.json({ status: session.status });
});

router.post("/sessions/:channelId/send", auth, async (req, res) => {
  const { channelId } = req.params;
  const { to, body, fileUrl, caption } = req.body;
  const session = getSession(channelId);

  if (!session || session.status !== "connected") {
    return res.status(400).json({ error: "Session not connected" });
  }

  try {
    let targetJid = to;
    if (targetJid.endsWith("@lid")) {
      targetJid = await resolveJid(session.client, targetJid);
    }

    try {
      if (fileUrl) {
        const { MessageMedia } = require("whatsapp-web.js");
        const media = await MessageMedia.fromUrl(fileUrl);
        await session.client.sendMessage(targetJid, media, { caption: caption || "" });
      } else {
        await session.client.sendMessage(targetJid, body);
      }
      res.json({ status: "sent" });
    } catch (sendErr) {
      if (sendErr.message && sendErr.message.includes("No LID for user") && targetJid.endsWith("@c.us")) {
        const userPart = targetJid.split("@")[0];
        console.warn(`[${channelId}] Detected possible fake @c.us JID ${targetJid}. Retrying with resolved LID...`);
        const lidJid = `${userPart}@lid`;
        const resolved = await resolveJid(session.client, lidJid);
        if (fileUrl) {
          const { MessageMedia } = require("whatsapp-web.js");
          const media = await MessageMedia.fromUrl(fileUrl);
          await session.client.sendMessage(resolved, media, { caption: caption || "" });
        } else {
          await session.client.sendMessage(resolved, body);
        }
        res.json({ status: "sent" });
      } else {
        throw sendErr;
      }
    }
  } catch (err) {
    console.error(`[${channelId}] Send error:`, err.message);
    res.status(500).json({ error: err.message });
  }
});

router.get("/sessions/:channelId/screenshot", auth, async (req, res) => {
  const { channelId } = req.params;
  const session = getSession(channelId);
  if (!session || !session.client || !session.client.pupPage) {
    return res.status(404).json({ error: "Session or page not found" });
  }
  try {
    const screenshot = await session.client.pupPage.screenshot({ type: "png" });
    res.setHeader("Content-Type", "image/png");
    res.send(screenshot);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

router.delete("/sessions/:channelId", auth, (req, res) => {
  const { channelId } = req.params;
  destroySession(channelId);
  res.json({ status: "destroyed" });
});

module.exports = router;
