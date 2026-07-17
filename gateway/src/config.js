const config = {
  port: parseInt(process.env.GATEWAY_PORT || "3000", 10),
  fastapiWebhookUrl: process.env.FASTAPI_WEBHOOK_URL || "http://backend:7860/webhooks/wa-gateway",
  gatewaySharedSecret: process.env.GATEWAY_SHARED_SECRET || "dev-secret-change-in-production",
};

module.exports = config;
