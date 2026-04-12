# Code Review Workflow

## Steps
1. Security audit (see knowledge/security.md)
2. Input validation — is every user input validated?
3. Error handling — are errors caught and surfaced correctly?
4. Accessibility — semantic HTML, keyboard nav, screen reader support?
5. Performance — unnecessary re-renders, large bundles, unoptimized images?
6. Type safety — strict TypeScript, no any types?

## Output Format
For each finding:
- File: filename
- Line: number or range
- Severity: critical / high / medium / low
- Issue: what is wrong
- Fix: exact code to fix it
