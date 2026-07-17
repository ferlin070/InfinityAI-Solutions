const express = require("express");
const config = require("./config");
const routes = require("./routes");

const app = express();
app.use(express.json());
app.use(routes);

app.get("/healthz", (_req, res) => res.json({ status: "ok" }));

app.listen(config.port, () => {
  console.log(`[gateway] listening on port ${config.port}`);
});
