# App Development Skill

## When To Use
When building any feature for the app or website.

## Workflow
1. Read knowledge/security.md before writing ANY backend code
2. Read knowledge/ui_ux_principles.md before writing ANY frontend code
3. Read knowledge/tech_stack.md to use the correct libraries
4. Read knowledge/preferences.md for style and formatting preferences
5. Check templates/ for a relevant starter — do not start from scratch
6. Write code that passes all checks in config/
7. Test with data from fixtures/ when applicable

## Security Checklist (run before every response)
- All user input validated server-side with Zod
- No secrets hardcoded
- SQL uses parameterized queries (Prisma handles this)
- Auth checked on protected routes
- Rate limiting on API endpoints
- CSRF protection on mutations
- Error messages do not leak internals
- Security headers configured

## UI/UX Checklist
- Responsive (mobile-first)
- Dark mode supported
- Loading states shown
- Error states handled gracefully
- Keyboard navigable
- Accessible (semantic HTML, ARIA when needed)
- Animations respect prefers-reduced-motion
