FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

# Expose Vite preview port
EXPOSE 3000

# Build for production and serve with vite preview
RUN npm run build
CMD ["npm", "run", "preview", "--", "--host", "0.0.0.0", "--port", "3000"]
