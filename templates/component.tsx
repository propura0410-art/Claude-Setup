// Template: React Component
"use client";

import { useState } from "react";

interface ComponentNameProps {
  title: string;
  children?: React.ReactNode;
  className?: string;
}

export function ComponentName({ title, children, className = "" }: ComponentNameProps) {
  const [isLoading, setIsLoading] = useState(false);

  return (
    <div className={`rounded-xl border bg-card p-6 shadow-sm ${className}`}>
      <h2 className="text-xl font-semibold text-card-foreground">{title}</h2>
      <div className="mt-4">{children}</div>
    </div>
  );
}
