FROM node:22-slim

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY . .

EXPOSE 5173

# VITE_API_URL is set by compose to http://backend:8000
# Vite reads it at dev-server startup for the proxy target
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
