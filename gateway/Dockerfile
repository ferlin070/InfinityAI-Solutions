FROM node:20-slim

RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    && wget -q -O- https://dl-ssl.google.com/linux/linux_signing_key.pub | gpg --dearmour -o /usr/share/keyrings/google-chrome.gpg \
    && sh -c 'echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] https://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list' \
    && apt-get update \
    && apt-get install -y google-chrome-stable --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

ENV PUPPETEER_SKIP_DOWNLOAD=true
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/google-chrome

WORKDIR /app
COPY gateway/package.json .
RUN npm install
COPY gateway/src/ src/

EXPOSE 3000
CMD ["node", "src/index.js"]
