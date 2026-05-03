import {
  BriefcaseBusiness,
  LayoutDashboard,
  Menu,
  PanelLeftClose,
  PanelLeftOpen,
  Settings2,
  UserSquare2,
  WalletCards,
  X,
} from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";
import { useState, type ReactNode } from "react";

import type { PageKey } from "@/lib/types";
import { cn } from "@/lib/utils";

const navigation: Array<{ key: PageKey; label: string; icon: ReactNode }> = [
  { key: "dashboard", label: "Dashboard", icon: <LayoutDashboard className="h-4 w-4" /> },
  { key: "jobs", label: "Jobs", icon: <BriefcaseBusiness className="h-4 w-4" /> },
  { key: "profiles", label: "Resume Profiles", icon: <UserSquare2 className="h-4 w-4" /> },
  { key: "settings", label: "Settings", icon: <Settings2 className="h-4 w-4" /> },
];

interface AppShellProps {
  page: PageKey;
  onPageChange: (page: PageKey) => void;
  title: string;
  subtitle: string;
  running: boolean;
  statusLabel: string;
  startupEnabled: boolean;
  autoRunOnLaunch: boolean;
  onRefresh: () => void;
  onSave: () => void;
  onStart: () => void;
  onStop: () => void;
  children: ReactNode;
}

export function AppShell(props: AppShellProps) {
  const {
    page,
    onPageChange,
    title,
    subtitle,
    running,
    statusLabel,
    startupEnabled,
    autoRunOnLaunch,
    onRefresh,
    onSave,
    onStart,
    onStop,
    children,
  } = props;

  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [desktopSidebarOpen, setDesktopSidebarOpen] = useState(true);

  const showWorkflowAction = page === "dashboard";
  const showRefreshAction = page === "dashboard" || page === "jobs";
  const saveActionLabel =
    page === "settings" ? "Save Settings" : page === "profiles" ? "Save Profiles" : "";

  const renderNavigationPanel = (compact = false) => (
    <div className={cn("flex h-full flex-col", compact ? "items-center" : "")}>
      <div className={cn("mb-8 flex items-center gap-4", compact ? "flex-col" : "")}>
        <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-brand-600 to-horizon-info text-lg font-bold text-white shadow-soft">
          TJ
        </div>
        {!compact ? (
          <div className="min-w-0">
            <h1 className="text-lg font-bold text-horizon-text">TopJobs Mailer</h1>
            <p className="text-sm text-horizon-muted">Tauri Workflow Console</p>
          </div>
        ) : null}
        <button
          type="button"
          onClick={() => setDesktopSidebarOpen((current) => !current)}
          className="action-button action-button-ghost hidden h-11 w-11 shrink-0 px-0 xl:inline-flex"
          title={compact ? "Show navigation" : "Hide navigation"}
        >
          {compact ? <PanelLeftOpen className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
        </button>
      </div>

      {!compact ? (
        <div className="mb-3 px-3 text-xs font-bold uppercase tracking-[0.28em] text-horizon-muted">
        Navigation
        </div>
      ) : null}
      <nav className="space-y-2">
        {navigation.map((item, index) => (
          <motion.button
            key={item.key}
            type="button"
            initial={{ opacity: 0, x: -12 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.24, delay: index * 0.03 }}
            onClick={() => {
              onPageChange(item.key);
              setMobileMenuOpen(false);
            }}
            className={cn(
              "flex w-full items-center gap-3 rounded-2xl px-4 py-3 text-sm font-semibold transition-all duration-200",
              compact ? "h-12 w-12 justify-center px-0" : "",
              item.key === page
                ? "bg-horizon-text text-white shadow-soft"
                : "text-horizon-muted hover:-translate-y-0.5 hover:bg-horizon-background hover:text-horizon-text"
            )}
            title={compact ? item.label : undefined}
          >
            {item.icon}
            {!compact ? item.label : null}
          </motion.button>
        ))}
      </nav>

      {!compact ? (
        <motion.div
        initial={{ opacity: 0, y: 18 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, delay: 0.18 }}
        className="mt-8 rounded-2xl border border-horizon-border bg-horizon-background p-5"
      >
        <div className="mb-4 flex items-center gap-3">
          <div className="rounded-2xl bg-brand-600/10 p-3 text-brand-600">
            <WalletCards className="h-5 w-5" />
          </div>
          <div>
            <p className="font-semibold text-horizon-text">Automation Mode</p>
            <p className="text-sm text-horizon-muted">{running ? "Running now" : "Standing by"}</p>
          </div>
        </div>
        <div className="space-y-2 text-sm text-horizon-muted">
          <p>Startup: {startupEnabled ? "Enabled" : "Disabled"}</p>
          <p>Launch autorun: {autoRunOnLaunch ? "Enabled" : "Disabled"}</p>
          <p className="font-medium text-horizon-text">{statusLabel}</p>
        </div>
      </motion.div>
      ) : null}
    </div>
  );

  return (
    <div className="h-screen overflow-hidden bg-horizon-background">
      <AnimatePresence>
        {mobileMenuOpen ? (
          <>
            <motion.div
              className="fixed inset-0 z-40 bg-[#0f1535]/45 xl:hidden"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setMobileMenuOpen(false)}
            />
            <motion.aside
              className="fixed inset-y-0 left-0 z-50 w-[88vw] max-w-[320px] border-r border-horizon-border bg-white px-6 py-8 shadow-2xl xl:hidden"
              initial={{ x: -320, opacity: 0.9 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: -320, opacity: 0.9 }}
              transition={{ type: "spring", stiffness: 260, damping: 28 }}
            >
              <div className="mb-6 flex justify-end">
                <button
                  type="button"
                  className="action-button action-button-ghost"
                  onClick={() => setMobileMenuOpen(false)}
                >
                  <X className="h-4 w-4" />
                  Close
                </button>
              </div>
              {renderNavigationPanel(false)}
            </motion.aside>
          </>
        ) : null}
      </AnimatePresence>

      <div className="flex h-screen overflow-hidden">
        <aside
          className={cn(
            "hidden h-screen shrink-0 overflow-y-auto border-r border-horizon-border bg-white/95 shadow-[8px_0_28px_rgba(112,144,176,0.10)] backdrop-blur transition-all duration-300 xl:block",
            desktopSidebarOpen
              ? "w-[290px] px-6 py-8 opacity-100"
              : "w-[76px] px-3 py-8 opacity-100"
          )}
        >
          {renderNavigationPanel(!desktopSidebarOpen)}
        </aside>

        <main className="h-screen min-w-0 flex-1 overflow-y-auto overflow-x-hidden px-4 py-4 sm:px-6 sm:py-5 lg:px-7 xl:px-8">
          <div className="mb-5 flex items-center justify-between gap-3 xl:hidden">
            <button
              type="button"
              onClick={() => setMobileMenuOpen(true)}
              className="action-button action-button-ghost"
            >
              <Menu className="h-4 w-4" />
              Menu
            </button>
            <div className="max-w-[65vw] truncate rounded-2xl border border-horizon-border bg-white px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-horizon-muted shadow-soft">
              {statusLabel}
            </div>
          </div>

          <motion.div
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35 }}
            className="relative z-10 mb-6 rounded-[22px] border border-white/70 bg-white px-5 py-5 shadow-horizon sm:px-6"
          >
            <div className="flex flex-col gap-5">
              <div className="min-w-0">
                <h2 className="text-2xl font-bold tracking-tight text-horizon-text sm:text-3xl">
                  {title}
                </h2>
                <p className="mt-2 max-w-3xl text-sm text-horizon-muted">{subtitle}</p>
              </div>

              <div className="flex w-full flex-wrap items-center gap-3">
                <div className="hidden rounded-2xl border border-horizon-border bg-horizon-background px-4 py-3 text-sm font-medium text-horizon-text xl:block">
                  {statusLabel}
                </div>
                {showWorkflowAction ? (
                  <button
                    type="button"
                    onClick={running ? onStop : onStart}
                    className={cn(
                      "action-button text-white",
                      running
                        ? "bg-horizon-danger hover:bg-horizon-danger/90"
                        : "action-button-primary"
                    )}
                  >
                    {running ? "Stop Workflow" : "Start Workflow"}
                  </button>
                ) : null}
                {showRefreshAction ? (
                  <button type="button" onClick={onRefresh} className="action-button action-button-secondary">
                    Refresh
                  </button>
                ) : null}
                {saveActionLabel ? (
                  <button type="button" onClick={onSave} className="action-button action-button-accent">
                    {saveActionLabel}
                  </button>
                ) : null}
              </div>
            </div>
          </motion.div>

          <div className="page-shell min-w-0">{children}</div>
        </main>
      </div>
    </div>
  );
}
