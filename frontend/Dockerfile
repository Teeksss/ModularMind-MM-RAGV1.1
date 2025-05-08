# Yapım aşaması
FROM node:18-alpine AS builder

WORKDIR /app

# Bağımlılıkları kopyala ve kur
COPY package.json package-lock.json ./
RUN npm ci

# Kaynak kodları kopyala
COPY . .

# Uygulamayı derle
RUN npm run build

# Çalışma aşaması
FROM nginx:alpine

# Nginx yapılandırması
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Builder aşamasından derlenen dosyaları kopyala
COPY --from=builder /app/dist /usr/share/nginx/html

# Sağlık kontrolü
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost/ || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]