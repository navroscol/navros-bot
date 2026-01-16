FROM node:20-bullseye-slim

# INSTALAMOS FFMPEG (CRUCIAL PARA AUDIOS) Y OTRAS HERRAMIENTAS
RUN apt-get update && \
    apt-get install -y \
    ffmpeg \
    git \
    python3 \
    make \
    g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY package.json .
RUN npm install

COPY . .

CMD ["node", "index.js"]
