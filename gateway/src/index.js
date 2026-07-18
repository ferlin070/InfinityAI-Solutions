const express = require("express");
const config = require("./config");
const routes = require("./routes");

const app = express();
app.use(express.json());
app.use(routes);

app.get("/healthz", (_req, res) => res.json({ status: "ok" }));

if (config.gatewaySharedSecret === "dev-secret-change-in-production") {
  console.warn(
    "[gateway] WARNING: GATEWAY_SHARED_SECRET is still the dev default. " +
    "Anyone who can reach this service's URL can control your WhatsApp session. " +
    "Set a real GATEWAY_SHARED_SECRET (and the matching value on the backend) before " +
    "deploying anywhere reachable from outside your own machine."
  );
}

app.listen(config.port, () => {
  console.log(`[gateway] listening on port ${config.port}`);
});
