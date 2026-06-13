FROM node:24-alpine

WORKDIR /app
COPY package.json pnpm-workspace.yaml ./
COPY apps/web-dashboard ./apps/web-dashboard
RUN corepack enable && pnpm install --filter web-dashboard --prod=false
EXPOSE 5173
CMD ["pnpm", "--filter", "web-dashboard", "dev"]
