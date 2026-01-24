FROM node:20-alpine

WORKDIR /app

# Enable pnpm
RUN corepack enable

# Copy package files
COPY package.json pnpm-workspace.yaml ./
COPY apps/web/package.json ./apps/web/

# Install dependencies
RUN pnpm install

# Copy source code
COPY . .

# Expose port
EXPOSE 3000

# Start development server
CMD ["pnpm", "--filter", "tasteos-web", "dev", "--hostname", "0.0.0.0"]
