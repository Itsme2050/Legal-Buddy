"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, Scale, X } from "lucide-react";
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
  const [mobileOpen, setMobileOpen] = useState(false);

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

        {/* Desktop nav */}
        <nav className="hidden items-center gap-1 text-sm md:flex">
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
            className="ml-2 rounded-md bg-teal-600 px-3 py-2 font-medium text-white transition-colors hover:bg-teal-700"
          >
            Start Research
          </Link>
        </nav>

        {/* Mobile menu button */}
        <div className="flex items-center gap-2 md:hidden">
          <Link
            href="/dashboard"
            className="rounded-md bg-teal-600 px-2.5 py-1.5 text-xs font-medium text-white hover:bg-teal-700"
          >
            Research
          </Link>
          <button
            onClick={() => setMobileOpen((o) => !o)}
            aria-label={mobileOpen ? "Close menu" : "Open menu"}
            className="rounded-md border border-navy-200 p-1.5 text-navy-700 hover:bg-navy-50"
          >
            {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </div>

      {/* Mobile nav drawer */}
      {mobileOpen && (
        <div className="border-t border-navy-100 bg-white px-4 py-3 md:hidden">
          <nav className="flex flex-col gap-1 text-sm">
            {links.map((l) => {
              const active =
                l.href === "/" ? pathname === "/" : pathname.startsWith(l.href);
              return (
                <Link
                  key={l.href}
                  href={l.href}
                  onClick={() => setMobileOpen(false)}
                  className={cn(
                    "rounded-md px-3 py-2 transition-colors",
                    active
                      ? "bg-navy-50 text-navy-900 font-medium"
                      : "text-navy-600 hover:bg-navy-50"
                  )}
                >
                  {l.label}
                </Link>
              );
            })}
          </nav>
        </div>
      )}
    </header>
  );
}