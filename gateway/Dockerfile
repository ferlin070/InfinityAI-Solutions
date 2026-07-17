FROM node:20-slim

RUN apt-get update && apt-get install -y \
    chromium \
    chromium-sandbox \
    && rm -rf /var/lib/apt/lists/*

ENV PUPPETEER_SKIP_DOWNLOAD=true
ENV CHROMIUM_PATH=/usr/bin/chromium

WORKDIR /app
COPY package.json .
RUN npm install
COPY src/ src/

EXPOSE 3000
CMD ["node", "src/index.js"]
