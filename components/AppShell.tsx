"use client";

import { BriefcaseBusiness, ChartNoAxesCombined, FileText, FileStack, Settings, LogOut, UserRound } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ReactNode, useState } from "react";
import { createClient } from "@/lib/supabase/browser";

const navigation = [
  { href: "/dashboard", label: "Overview", icon: ChartNoAxesCombined },
  { href: "/profile", label: "Profile", icon: UserRound },
  { href: "/jobs", label: "Matched jobs", icon: BriefcaseBusiness },
  { href: "/applications", label: "Applications", icon: FileText },
  { href: "/answer-bank", label: "Answer bank", icon: FileStack },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [signingOut, setSigningOut] = useState(false);

  async function signOut() {
    setSigningOut(true);
    const { error } = await createClient().auth.signOut();
    if (error) {
      setSigningOut(false);
      window.alert(`Could not sign out: ${error.message}`);
      return;
    }
    router.replace("/login");
    router.refresh();
  }

  return (
    <div className="app-frame">
      <aside className="sidebar">
        <Link href="/dashboard" className="brand">
          <span className="brand-mark">TJ</span>
          <span><strong>TopJobs</strong><small>Auto Mailer</small></span>
        </Link>
        <p className="nav-caption">WORKSPACE</p>
        <nav className="nav-list" aria-label="Main navigation">
          {navigation.map(({ href, label, icon: Icon }) => (
            <Link key={href} href={href} className={`nav-link ${pathname === href ? "active" : ""}`}>
              <Icon size={18} strokeWidth={1.8} />{label}
            </Link>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="privacy-note"><span className="status-dot" />Private workspace<br /><small>Your search data is account scoped.</small></div>
          <button className="nav-link signout" onClick={signOut} disabled={signingOut}>
            <LogOut size={18} />{signingOut ? "Signing out…" : "Sign out"}
          </button>
        </div>
      </aside>
      <main className="main-content">{children}</main>
    </div>
  );
}
