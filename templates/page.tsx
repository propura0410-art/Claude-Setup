// Template: Next.js Page Component
// Usage: Copy and customize for new pages

import { Metadata } from "next";

export const metadata: Metadata = {
  title: "{{PAGE_TITLE}}",
  description: "{{PAGE_DESCRIPTION}}",
};

export default function PageName() {
  return (
    <main className="min-h-screen bg-background">
      <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
        <h1 className="text-4xl font-bold tracking-tight text-foreground">
          Page Title
        </h1>
        <p className="mt-4 text-lg text-muted-foreground">
          Page description goes here.
        </p>
        <section className="mt-12">
          {/* Page content here */}
        </section>
      </div>
    </main>
  );
}
