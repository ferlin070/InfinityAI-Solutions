FROM node:20-slim

RUN apt-get update && apt-get install -y \
    chromium \
    chromium-sandbox \
    && rm -rf /var/lib/apt/lists/*

# PUPPETEER_EXECUTABLE_PATH is the variable Puppeteer itself actually reads —
# a prior version of this file set CHROMIUM_PATH, which Puppeteer/whatsapp-web.js
# never looks at, so every session initialize() failed with "Could not find
# Chrome" despite Chromium being installed right above (confirmed via live
# Railway deployment logs). sessions.js also passes this explicitly as
# `executablePath` as a second line of defense, independent of env var pickup.
ENV PUPPETEER_SKIP_DOWNLOAD=true
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium

WORKDIR /app
COPY package.json .
RUN npm install
COPY src/ src/

EXPOSE 3000
CMD ["node", "src/index.js"]
