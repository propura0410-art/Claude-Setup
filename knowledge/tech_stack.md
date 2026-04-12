# Tech Stack Reference

## Frontend
- Framework: Next.js 14+ (App Router)
- Language: TypeScript (strict mode)
- Styling: Tailwind CSS + CSS variables for theming
- Components: shadcn/ui as base (customize heavily)
- State: React Server Components + minimal client state (zustand if needed)
- Forms: React Hook Form + Zod validation
- Animation: Framer Motion
- Icons: Lucide React

## Backend
- API: Next.js API Routes or Route Handlers
- Database: PostgreSQL via Prisma ORM
- Auth: NextAuth.js v5
- Validation: Zod (shared between client and server)
- Email: Resend or Nodemailer
- File Storage: Uploadthing or S3-compatible

## Testing
- Unit: Jest + React Testing Library
- E2E: Playwright
- API: Supertest

## DevOps
- Hosting: Vercel
- CI/CD: GitHub Actions
- Monitoring: Vercel Analytics + Sentry
- Linting: ESLint + Prettier

## Package Managers
- Node: pnpm (preferred) or npm
- Python: pip with venv
