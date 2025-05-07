# Multi-stage build for frontend

# ============= Build Stage =============
FROM node:18-alpine as build

# Set working directory
WORKDIR /app

# Copy package files
COPY package.json package-lock.json ./

# Install dependencies
RUN npm ci

# Copy the rest of the code
COPY . .

# Set environment variables for build
ARG API_URL
ENV VITE_API_URL=${API_URL}
ENV NODE_ENV=production

# Build the application
RUN npm run build

# ============= Runtime Stage =============
FROM nginx:alpine

# Copy nginx configuration
COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf

# Copy built assets from build stage
COPY --from=build /app/dist /usr/share/nginx/html

# Add runtime environment configuration script
COPY nginx/env.sh /docker-entrypoint.d/40-env.sh
RUN chmod +x /docker-entrypoint.d/40-env.sh

# Copy env.template used by above script
COPY nginx/env.template.js /usr/share/nginx/html/env.template.js
RUN touch /usr/share/nginx/html/env.js

# Expose port
EXPOSE 80

# Set user to non-root for better security
USER nginx

# Command to start nginx
CMD ["nginx", "-g", "daemon off;"]