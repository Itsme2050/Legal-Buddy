"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Scale } from "lucide-react";
import { cn } from "@/lib/utils";

const links = [
  { href: "/", label: "Home" },
  { href: "/dashboard", label: "Research" },
  { href: "/documents", label: "Documents" },
  { href: "/history", label: "History" },
  { href: "/pricing", label: "Pricing" },
];

export function SiteHeader() {
  const pathname = usePathname();
  return (
    <header className="sticky top-0 z-40 border-b border-navy-100 bg-white/95 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
        <Link href="/" className="flex items-center gap-2 font-semibold text-navy-900">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-navy-900 text-teal-300">
            <Scale className="h-4 w-4" aria-hidden />
          </span>
          <span>
            Legal Buddy
            <span className="ml-2 hidden text-xs font-normal text-navy-500 sm:inline">
              Understand the law.
            </span>
          </span>
        </Link>
        <nav className="flex items-center gap-1 text-sm">
          {links.map((l) => {
            const active =
              l.href === "/" ? pathname === "/" : pathname.startsWith(l.href);
            return (
              <Link
                key={l.href}
                href={l.href}
                className={cn(
                  "rounded-md px-3 py-2 transition-colors",
                  active
                    ? "bg-navy-50 text-navy-900 font-medium"
                    : "text-navy-600 hover:text-navy-900 hover:bg-navy-50"
                )}
              >
                {l.label}
              </Link>
            );
          })}
          <Link
            href="/dashboard"
            className="ml-2 hidden rounded-md bg-teal-600 px-3 py-2 font-medium text-white transition-colors hover:bg-teal-700 sm:inline-block"
          >
            Start Research
          </Link>
        </nav>
      </div>
    </header>
  );
}