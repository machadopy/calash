# Estágio 1: Build (Compila o React)
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# Estágio 2: Nginx (Servidor Web)
FROM nginx:alpine
# Copia a pasta 'dist' gerada pelo Vite para a pasta pública do Nginx
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]