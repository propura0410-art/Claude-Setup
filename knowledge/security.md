# Security Guidelines

## Authentication & Authorization
- Use established auth libraries (NextAuth.js, Supabase Auth) — never roll your own
- Enforce strong passwords: 12+ chars, mixed case, numbers, symbols
- Implement rate limiting on all auth endpoints
- Use HTTP-only, Secure, SameSite cookies for sessions
- Add CSRF protection on all state-changing requests
- Implement proper role-based access control (RBAC)

## Input Validation
- Validate ALL user input server-side (never trust the client)
- Use parameterized queries — NEVER string concatenation for SQL
- Sanitize HTML output to prevent XSS
- Validate file uploads: type, size, and content
- Use allowlists over denylists

## API Security
- Use HTTPS everywhere, no exceptions
- Implement proper CORS configuration (specific origins, not *)
- Add rate limiting to all API endpoints
- Validate and sanitize all request parameters
- Return generic error messages to users (log details server-side)
- Use API keys or JWT tokens with short expiry

## Headers & Transport
- Content-Security-Policy (CSP)
- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY
- Strict-Transport-Security (HSTS)
- Referrer-Policy: strict-origin-when-cross-origin
- Permissions-Policy: restrict unnecessary browser features

## Data Protection
- Encrypt sensitive data at rest
- Hash passwords with bcrypt (cost factor 12+)
- Never log sensitive data (passwords, tokens, PII)
- Implement proper data backup and recovery
- Follow principle of least privilege for database access

## Dependencies
- Audit dependencies regularly (npm audit, pip audit)
- Pin dependency versions
- Use lock files (package-lock.json, poetry.lock)
- Remove unused dependencies

## Environment
- Never commit secrets to git (.env in .gitignore)
- Use environment variables for all configuration
- Separate configs for dev/staging/production
- Rotate secrets regularly
