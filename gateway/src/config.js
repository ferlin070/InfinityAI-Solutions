const config = {
  // Railway/Render inject $PORT dynamically at runtime — that must win when
  // present. $GATEWAY_PORT is the docker-compose-only local dev fallback
  // (see docker-compose.yml), then 3000 if neither is set.
  port: parseInt(process.env.PORT || process.env.GATEWAY_PORT || "3000", 10),
  fastapiWebhookUrl: process.env.FASTAPI_WEBHOOK_URL || "http://backend:7860/webhooks/wa-gateway",
  gatewaySharedSecret: process.env.GATEWAY_SHARED_SECRET || "dev-secret-change-in-production",
};

module.exports = config;
