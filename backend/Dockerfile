FROM node:18-alpine

WORKDIR /app

# Копируем package.json
COPY package*.json ./

# Устанавливаем зависимости
RUN npm install --production

# Копируем код backend
COPY ..

# Render устанавливает PORT автоматически
EXPOSE 8000

# Запускаем сервер (используем $PORT из env)
CMD ["node", "server.js"]
