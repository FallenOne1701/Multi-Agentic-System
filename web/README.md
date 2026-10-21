# Groww Support Reply — Web UI

Next.js App Router UI rebuilt from `Stitch_WebDesign/`. Deployed on Vercel (root `vercel.json` sets `rootDirectory: web`).

## Local

```bash
cp .env.example .env.local
# set NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
npm install
npm run dev
```

API (repo root):

```bash
uvicorn groww_support.api:app --reload --port 8000
```
