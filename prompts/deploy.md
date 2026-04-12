# Deployment Checklist

## Before Every Deploy
1. All tests passing locally
2. No TypeScript errors (npm run type-check)
3. No lint warnings (npm run lint)
4. npm audit shows no high/critical vulnerabilities
5. .env.local values are set in production environment
6. No console.log statements left in code
7. All API routes have rate limiting
8. All forms have server-side validation

## First Deploy (Vercel)
1. Connect GitHub repo to Vercel
2. Set environment variables in Vercel dashboard:
   - DATABASE_URL
   - NEXTAUTH_SECRET (generate with: openssl rand -base64 32)
   - NEXTAUTH_URL (your production domain)
3. Set Node.js version to 20
4. Deploy and verify all pages load
5. Test auth flow end-to-end
6. Check security headers at securityheaders.com
7. Run Lighthouse audit (aim for 90+ all categories)
8. Test on mobile

## After Deploy
1. Verify no errors in Vercel logs
2. Check Sentry for new errors (if configured)
3. Test critical user flows manually
4. Verify email delivery works
5. Check database migrations ran successfully

## Rollback Plan
1. Go to Vercel dashboard > Deployments
2. Find the last working deployment
3. Click the three dots > Promote to Production
