FROM node:20-slim

# Dependencies for Puppeteer's bundled Chromium
RUN apt-get update && apt-get install -y \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcairo2 \
    libcups2 \
    libdrm2 \
    libgbm1 \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libpango-1.0-0 \
    libu2f-udev \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxkbcommon0 \
    libxrandr2 \
    libxrender1 \
    libxshmfence1 \
    libxtst6 \
    xdg-utils \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# whatsapp-web.js@1.34.7 bundles puppeteer@24.38.0 which downloads its own Chromium

WORKDIR /app
COPY gateway/package.json .
RUN npm install
COPY gateway/src/ src/

# Startup script: clean GPU/disk caches before launching node to avoid
# "No space left on device" errors from stale Chromium cache files
RUN printf '#!/bin/sh\nfind /app/.wwebjs_auth -name "GPUCache" -type d -exec rm -rf {} + 2>/dev/null || true\nfind /app/.wwebjs_auth -name "GPUPersistentCache" -type d -exec rm -rf {} + 2>/dev/null || true\nexec node src/index.js\n' > /app/start.sh && chmod +x /app/start.sh

EXPOSE 3000
CMD ["/app/start.sh"]
