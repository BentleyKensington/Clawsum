# DinoCrushBoss — dinocrushboss.com (DinoHawk game lane)
FROM node:20-bookworm-slim
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm install --include=dev
COPY . .
RUN npm run build
ENV NODE_ENV=production
ENV PORT=5000
ENV HOST=0.0.0.0
EXPOSE 5000
HEALTHCHECK --interval=20s --timeout=5s --start-period=40s --retries=5 \
  CMD node -e "fetch('http://127.0.0.1:'+(process.env.PORT||5000)+'/api/health').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"
USER node
CMD ["node", "dist/index.js"]
