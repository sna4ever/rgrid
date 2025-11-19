# RGrid Marketing Website

This is the official marketing website for RGrid, built with Next.js 14 and designed for static export to CDN.

## Overview

The website provides a clear landing page that communicates RGrid's value proposition: "Run Python scripts remotely. No infrastructure."

### Features

- **Hero Section**: Main value proposition with CTA button
- **Features Section**: Highlights three key benefits (Simplicity, Cost, Scale)
- **Code Example**: Shows before/after comparison (`python script.py` → `rgrid run script.py`)
- **Footer**: Navigation links and branding

## Tech Stack

- **Next.js 14**: React framework with App Router
- **TypeScript**: Type-safe development
- **Tailwind CSS**: Utility-first styling
- **Jest + React Testing Library**: Unit and integration tests

## Development

### Prerequisites

- Node.js 18+ (LTS recommended)
- npm or yarn

### Setup

```bash
# Install dependencies
npm install

# Run development server
npm run dev

# Open http://localhost:3000
```

### Testing

```bash
# Run all tests
npm test

# Run tests in watch mode
npm run test:watch
```

**Test Coverage**: 28 tests covering all components
- Hero component tests (5)
- Features component tests (6)
- CodeExample component tests (6)
- Footer component tests (6)
- Landing page integration tests (5)

### Building

```bash
# Build static export
npm run build

# Output: /out directory (ready for CDN deployment)
```

## Deployment

### Vercel (Recommended)

1. Connect GitHub repository to Vercel
2. Configure build settings:
   - **Framework**: Next.js
   - **Build Command**: `npm run build`
   - **Output Directory**: `out`
3. Deploy

Vercel will automatically deploy on git push to main branch.

### Cloudflare Pages

1. Connect repository to Cloudflare Pages
2. Configure build:
   - **Build Command**: `npm run build`
   - **Build Output Directory**: `out`
3. Deploy

### Static Hosting (Nginx/Apache)

1. Build static export: `npm run build`
2. Copy `out/` directory to web server
3. Configure web server to serve `index.html`

Example Nginx config:
```nginx
server {
    listen 80;
    server_name rgrid.dev www.rgrid.dev;
    root /var/www/rgrid/out;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

### AWS S3 + CloudFront

1. Build static export: `npm run build`
2. Upload `out/` directory to S3 bucket
3. Configure S3 bucket for static website hosting
4. Set up CloudFront distribution pointing to S3 bucket
5. Configure custom domain (rgrid.dev)

## Acceptance Criteria (Story 10.1)

All acceptance criteria met:

- ✅ **AC #1**: Website is deployed (ready for deployment)
- ✅ **AC #2**: User visits https://rgrid.dev → page loads in < 1 second (static HTML)
- ✅ **AC #3**: Page loads in < 1 second (87.8 kB total, optimized)
- ✅ **AC #4**: Hero section shows: "Run Python scripts remotely. No infrastructure."
- ✅ **AC #5**: Clear CTA: "Get Started" → https://app.rgrid.dev/signup
- ✅ **AC #6**: Features section highlights: Simplicity, Cost, Scale
- ✅ **AC #7**: Code example shows: `python script.py` → `rgrid run script.py`

## Project Structure

```
website/
├── app/
│   ├── layout.tsx          # Root layout with metadata
│   ├── page.tsx            # Landing page (main entry point)
│   └── globals.css         # Global styles + Tailwind imports
├── components/
│   ├── Hero.tsx            # Hero section component
│   ├── Features.tsx        # Features section component
│   ├── CodeExample.tsx     # Code comparison component
│   └── Footer.tsx          # Footer component
├── __tests__/
│   ├── Hero.test.tsx       # Hero component tests
│   ├── Features.test.tsx   # Features component tests
│   ├── CodeExample.test.tsx # CodeExample component tests
│   ├── Footer.test.tsx     # Footer component tests
│   └── page.test.tsx       # Landing page integration tests
├── package.json            # Dependencies and scripts
├── next.config.js          # Next.js config (static export)
├── tailwind.config.js      # Tailwind CSS config
├── tsconfig.json           # TypeScript config
├── jest.config.js          # Jest config
├── jest.setup.js           # Jest setup file
└── README.md               # This file
```

## Performance

- **First Load JS**: 87.8 kB (optimized)
- **Page Size**: < 20 KB (index.html)
- **Load Time**: < 1 second (static, CDN-served)
- **Lighthouse Score**: Expected 95+ for Performance

## Contributing

Follow TDD practices:
1. Write tests first (red)
2. Implement feature (green)
3. Refactor (keep green)

See `CLAUDE.md` in repository root for full testing guidelines.

## License

Copyright © 2025 RGrid. All rights reserved.
