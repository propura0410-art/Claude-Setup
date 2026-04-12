# UI/UX Design Principles

## Core Principles
1. Clarity over cleverness — users should never wonder "what does this do?"
2. Consistency — same patterns everywhere (spacing, colors, interactions)
3. Feedback — every action gets a visible response (loading, success, error)
4. Forgiveness — undo actions, confirm destructive ones, auto-save
5. Progressive disclosure — show basics first, details on demand

## Layout
- Use 4px/8px spacing grid system
- Maximum content width: 1200px
- Generous whitespace — let content breathe
- Clear visual hierarchy with size, weight, and color
- Sticky navigation for long pages

## Typography
- Maximum 2 font families
- Clear heading hierarchy (h1 > h2 > h3)
- Body text: 16px minimum, 1.5+ line height
- Sufficient contrast ratios (4.5:1 for normal text)

## Color
- Define a clear palette: primary, secondary, accent, neutral, semantic
- Use color meaningfully, not decoratively
- Never use color alone to convey information
- Support both light and dark themes

## Components
- Buttons: clear primary/secondary/tertiary hierarchy
- Forms: inline validation, helpful error messages, clear labels
- Modals: use sparingly, always closeable, trap focus
- Tables: sortable, filterable, paginated for large datasets
- Loading: skeleton screens over spinners when possible

## Interaction
- Touch targets: minimum 44x44px
- Hover states on all interactive elements
- Focus indicators for keyboard navigation
- Smooth transitions (150-300ms)
- Disable submit buttons during loading

## Error Handling
- Friendly, human language ("Something went wrong" not "Error 500")
- Actionable messages ("Try again" button, not just text)
- Form errors: highlight the specific field + explain how to fix

## Accessibility
- Semantic HTML (nav, main, article, button — not div for everything)
- Alt text on all images
- Keyboard navigable (Tab, Enter, Escape, Arrow keys)
- Screen reader tested
- Reduced motion support (@media prefers-reduced-motion)
- Skip-to-content link
