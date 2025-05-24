# Stage 1: Build the React application
FROM node:18-alpine AS builder

WORKDIR /app

# Copy package.json and package-lock.json (if available)
# If package-lock.json is not consistently present, only copy package.json
# However, it's best practice to commit and use a lock file.
COPY package.json package-lock.json* ./
# If you use yarn, you would copy yarn.lock instead of package-lock.json*

# Install dependencies
RUN npm install
# If using yarn: RUN yarn install

# Copy the rest of the application code
COPY . .

# Build the React application
RUN npm run build
# If using yarn: RUN yarn build

# Stage 2: Serve the application with Nginx
FROM nginx:alpine

# Copy custom Nginx configuration
# This replaces the default Nginx configuration.
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy the build output from the builder stage to Nginx's web root directory
COPY --from=builder /app/build /usr/share/nginx/html

# Expose port 80 (default Nginx port)
EXPOSE 80

# Start Nginx in the foreground
CMD ["nginx", "-g", "daemon off;"]
