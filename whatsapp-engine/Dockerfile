FROM node:20-bullseye-slim

# Instalar Git y dependencias necesarias
RUN apt-get update && apt-get install -y git python3 make g++

WORKDIR /app
COPY package.json .
RUN npm install
COPY . .
EXPOSE 3000
CMD ["node", "index.js"]
