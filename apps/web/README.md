# ArogyaRakshak Web Client (`apps/web`)

The patient-facing web frontend for **ArogyaRakshak**, built with **Next.js 15/16 App Router**, **React 19**, and **TypeScript**. Designed with trilingual accessibility (English, Hindi, Marathi) and real-time Server-Sent Events (SSE) streaming.

---

## Features
- **Trilingual Scaffolding**: Built for plain-language accessibility across English, Hindi, and Marathi.
- **Document Ingestion Interface**: Drag-and-drop file upload for hospital bills, prescriptions, and claim denial letters.
- **Real-Time Audit Streaming**: Subscribes to backend SSE event streams to visualize multi-agent auditing steps live.
- **Responsive Layout**: Designed for mobile and desktop screens.

---

## Directory Layout
```text
apps/web/
├── app/
│   ├── globals.css          # Design tokens, typography, and styling variables
│   ├── layout.tsx           # Root layout with HTML metadata & header
│   └── page.tsx             # Interactive dashboard and intake portal
├── Dockerfile               # Node.js container definition
├── package.json             # Dependencies and scripts
└── tsconfig.json            # TypeScript configuration
```

---

## Getting Started

### Prerequisites
- Node.js 18+ or 20+
- npm (or yarn / pnpm)

### Development
```bash
# 1. Install dependencies
npm install

# 2. Run local dev server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to view the client.

### Building for Production
```bash
npm run build
npm run start
```

### Linting
```bash
npm run lint
```
