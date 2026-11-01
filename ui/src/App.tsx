import { getCurrentWindow } from "@tauri-apps/api/window";
import { AnimatePresence, motion } from "framer-motion";
import { useCallback, useEffect, useMemo, useRef, useState, useTransition } from "react";

import { AppShell } from "@/components/layout/AppShell";
import { DashboardPage } from "@/pages/DashboardPage";
import { JobsPage } from "@/pages/JobsPage";
import { ProfilesPage } from "@/pages/ProfilesPage";
import { SettingsPage } from "@/pages/SettingsPage";
import { WelcomePage } from "@/pages/WelcomePage";
import { AccountPage } from "@/pages/AccountPage";
import {
  analyzeResumeProfile,
  createResumeProfile,
  fetchConfig,
  fetchAccountStatus,
  fetchResumeInventory,
  fetchSnapshot,
  getLaunchContext,
  getWorkflowStatus,
  listenWorkflowEvents,
  loginAccount,
  registerAccount,
  saveConfig,
  startWorkflow,
  stopWorkflow,
} from "@/lib/tauri";
import type {
  AppConfig,
  AccountStatus,
  LaunchContext,
  PageKey,
  ResumeProfileDraftInput,
  ResumeProfileDraftResult,
  ResumeInventoryItem,
  SnapshotResponse,
  WorkflowProgressState,
  WorkflowStatus,
} from "@/lib/types";
import { formatDateTime, summarizeWorkflowEvent } from "@/lib/utils";
import { checkForAppUpdate, openLatestRelease, type AppUpdate } from "@/lib/updates";

const PAGE_COPY: Record<PageKey, { title: string; subtitle: string }> = {
  dashboard: {
    title: "Automation Dashboard",
    subtitle:
      "Track the TopJobs workflow, review saved activity, and control the Python automation without leaving the desktop app.",
  },
  jobs: {
    title: "Jobs and Status",
    subtitle:
      "Review matched jobs, applied jobs, skipped jobs, and failed sends in one filtered workspace.",
  },
  profiles: {
    title: "Resume Profiles",
    subtitle:
      "Create a profile from a selected resume, refine the suggested keywords, and control which jobs match each profile.",
  },
  settings: {
    title: "Settings",
    subtitle:
      "Control startup behavior, launch automation, sender details, search categories, and fit thresholds.",
  },
};

export default function App() {
  const [page, setPage] = useState<PageKey>("dashboard");
  const [snapshot, setSnapshot] = useState<SnapshotResponse | null>(null);
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [accountStatus, setAccountStatus] = useState<AccountStatus | null>(null);
  const [authenticated, setAuthenticated] = useState(false);
  const [resumeInventory, setResumeInventory] = useState<ResumeInventoryItem[]>([]);
  const [workflowStatus, setWorkflowStatus] = useState<WorkflowStatus>({ running: false, pid: null });
  const [launchContext, setLaunchContext] = useState<LaunchContext>({ startup: false });
  const [liveLogs, setLiveLogs] = useState<string[]>([]);
  const [workflowProgress, setWorkflowProgress] = useState<WorkflowProgressState | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [authenticating, setAuthenticating] = useState(false);
  const [analyzingProfile, setAnalyzingProfile] = useState(false);
  const [creatingProfile, setCreatingProfile] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [appUpdate, setAppUpdate] = useState<AppUpdate | null>(null);
  const [updateError, setUpdateError] = useState<string | null>(null);
  const [updateDismissed, setUpdateDismissed] = useState(false);
  const [isPending, startTransition] = useTransition();

  const autoStartAttempted = useRef(false);
  const minimizeAttempted = useRef(false);

  const refreshSnapshotOnly = useCallback(async () => {
    const snapshotData = await fetchSnapshot(30);
    startTransition(() => {
      setSnapshot(snapshotData);
    });
  }, []);

  const refreshWorkspace = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [snapshotData, configData, inventoryData, statusData, launchData, accountData] = await Promise.all([
        fetchSnapshot(30),
        fetchConfig(),
        fetchResumeInventory(),
        getWorkflowStatus(),
        getLaunchContext(),
        fetchAccountStatus(),
      ]);

      startTransition(() => {
        setSnapshot(snapshotData);
        setConfig(configData);
        setResumeInventory(inventoryData);
        setWorkflowStatus(statusData);
        setLaunchContext(launchData);
        setAccountStatus(accountData);
      });
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : String(loadError));
    } finally {
      setLoading(false);
    }
  }, []);

  const handleAuthenticate = useCallback(
    async (mode: "register" | "login", email: string, password: string) => {
      setAuthenticating(true);
      setError(null);
      try {
        const account = mode === "register"
          ? await registerAccount(email, password)
          : await loginAccount(email, password);
        setAccountStatus(account);
        setAuthenticated(true);
      } catch (authError) {
        setError(authError instanceof Error ? authError.message : String(authError));
      } finally {
        setAuthenticating(false);
      }
    },
    []
  );

  const handleSignOut = useCallback(async () => {
    if (workflowStatus.running) {
      try {
        await stopWorkflow();
        setWorkflowStatus({ running: false, pid: null });
      } catch (stopError) {
        setError(stopError instanceof Error ? stopError.message : String(stopError));
        return;
      }
    }
    setError(null);
    setAuthenticated(false);
  }, [workflowStatus.running]);

  const handleRefresh = useCallback(async () => {
    try {
      await refreshWorkspace();
    } catch (refreshError) {
      setError(refreshError instanceof Error ? refreshError.message : String(refreshError));
    }
  }, [refreshWorkspace]);

  const handleSave = useCallback(async () => {
    if (!config) return;
    setSaving(true);
    setError(null);
    try {
      await saveConfig(config);
      const [configData, inventoryData] = await Promise.all([fetchConfig(), fetchResumeInventory()]);
      startTransition(() => {
        setConfig(configData);
        setResumeInventory(inventoryData);
      });
      setLiveLogs((current) => [
        `Settings saved at ${formatDateTime(new Date().toISOString())}.`,
        ...current,
      ].slice(0, 200));
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : String(saveError));
    } finally {
      setSaving(false);
    }
  }, [config]);

  const runUpdateCheck = useCallback(async () => {
    setUpdateError(null);
    try {
      setAppUpdate(await checkForAppUpdate());
    } catch (checkError) {
      setUpdateError(checkError instanceof Error ? checkError.message : String(checkError));
    }
  }, []);

  const handleCompleteOnboarding = useCallback(async (nextConfig: AppConfig) => {
    setSaving(true);
    setError(null);
    try {
      await saveConfig(nextConfig);
      setConfig(await fetchConfig());
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : String(saveError));
    } finally {
      setSaving(false);
    }
  }, []);

  const handleStart = useCallback(
    async (startup = false) => {
      setError(null);
      try {
        setWorkflowProgress({
          percent: 0,
          stage: "starting",
          detail: "Launching automation workflow.",
        });
        await startWorkflow(startup);
        setWorkflowStatus((current) => ({ ...current, running: true }));
      } catch (startError) {
        setError(startError instanceof Error ? startError.message : String(startError));
      }
    },
    []
  );

  const handleStop = useCallback(async () => {
    setError(null);
    try {
      await stopWorkflow();
      setWorkflowStatus({ running: false, pid: null });
      setWorkflowProgress({
        percent: 0,
        stage: "stopped",
        detail: "Workflow stop requested by the user.",
      });
      setLiveLogs((current) => ["Workflow stop requested.", ...current].slice(0, 200));
    } catch (stopError) {
      setError(stopError instanceof Error ? stopError.message : String(stopError));
    }
  }, []);

  const toBase64 = useCallback(
    (file: File) =>
      new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => {
          const result = typeof reader.result === "string" ? reader.result : "";
          const base64 = result.includes(",") ? result.split(",")[1] : result;
          resolve(base64);
        };
        reader.onerror = () => reject(reader.error ?? new Error("Could not read the selected file."));
        reader.readAsDataURL(file);
      }),
    []
  );

  const handleAnalyzeResumeProfile = useCallback(async (file: File): Promise<ResumeProfileDraftResult> => {
    setAnalyzingProfile(true);
    setError(null);
    try {
      const base64 = await toBase64(file);
      return await analyzeResumeProfile(file.name, base64);
    } catch (analyzeError) {
      setError(analyzeError instanceof Error ? analyzeError.message : String(analyzeError));
      throw analyzeError;
    } finally {
      setAnalyzingProfile(false);
    }
  }, [toBase64]);

  const handleCreateResumeProfile = useCallback(async (file: File, draft: ResumeProfileDraftInput) => {
    setCreatingProfile(true);
    setError(null);
    try {
      const base64 = await toBase64(file);
      const result = await createResumeProfile(file.name, base64, draft);
      startTransition(() => {
        setConfig(result.config);
        setResumeInventory(result.resume_inventory);
      });
      setLiveLogs((current) => [
        `Created profile "${result.imported.profile.label}" from ${file.name}.`,
        ...current,
      ].slice(0, 200));
    } catch (importError) {
      setError(importError instanceof Error ? importError.message : String(importError));
    } finally {
      setCreatingProfile(false);
    }
  }, [toBase64]);

  useEffect(() => {
    void refreshWorkspace();
  }, [refreshWorkspace]);

  useEffect(() => {
    void runUpdateCheck();
  }, [runUpdateCheck]);

  useEffect(() => {
    let disposed = false;

    const subscribe = async () => {
      const unlisten = await listenWorkflowEvents((event) => {
        if (disposed) return;

        const line = summarizeWorkflowEvent(event.kind, event.payload);
        setLiveLogs((current) => [line, ...current].slice(0, 200));

        if (event.kind === "state") {
          const status = typeof event.payload.status === "string" ? event.payload.status : "";
          if (status === "started" || status === "starting") {
            setWorkflowStatus((current) => ({ ...current, running: true }));
            setWorkflowProgress({
              percent: 0,
              stage: "starting",
              detail: "Preparing workflow runtime.",
            });
          }
          if (status === "finished") {
            setWorkflowStatus({ running: false, pid: null });
            setWorkflowProgress({
              percent: 100,
              stage: "complete",
              detail: "Workflow finished.",
            });
            void refreshSnapshotOnly();
          }
        }

        if (event.kind === "progress") {
          setWorkflowProgress({
            percent: typeof event.payload.percent === "number" ? event.payload.percent : 0,
            stage: typeof event.payload.stage === "string" ? event.payload.stage : "",
            detail: typeof event.payload.detail === "string" ? event.payload.detail : "",
            current: typeof event.payload.current === "number" ? event.payload.current : undefined,
            total: typeof event.payload.total === "number" ? event.payload.total : undefined,
          });
        }

        if (event.kind === "summary") {
          setWorkflowProgress({
            percent: 100,
            stage: "complete",
            detail: "Workflow finished. Summary saved.",
          });
          void refreshSnapshotOnly();
        }

        if (event.kind === "process-exit") {
          setWorkflowStatus({ running: false, pid: null });
          setWorkflowProgress((current) => current ?? {
            percent: 100,
            stage: "complete",
            detail: "Workflow process exited.",
          });
          void refreshSnapshotOnly();
        }

        if (event.kind === "error") {
          setWorkflowProgress((current) => ({
            percent: current?.percent ?? 100,
            stage: "failed",
            detail:
              typeof event.payload.message === "string"
                ? event.payload.message
                : "Workflow error received.",
          }));
          setError(
            typeof event.payload.message === "string"
              ? event.payload.message
              : "Workflow error received."
          );
        }
      });

      return unlisten;
    };

    let unlistenPromise = subscribe();
    return () => {
      disposed = true;
      void unlistenPromise.then((unlisten) => unlisten());
    };
  }, [refreshSnapshotOnly]);

  useEffect(() => {
    if (
      !config ||
      !authenticated ||
      !config.app.onboarding_completed ||
      !launchContext ||
      autoStartAttempted.current ||
      workflowStatus.running
    ) {
      return;
    }

    const shouldAutoStart =
      (launchContext.startup && config.app.run_at_startup) ||
      (!launchContext.startup && config.app.auto_run_on_launch);

    if (!shouldAutoStart) {
      autoStartAttempted.current = true;
      return;
    }

    autoStartAttempted.current = true;
    void handleStart(launchContext.startup);
  }, [authenticated, config, handleStart, launchContext, workflowStatus.running]);

  useEffect(() => {
    if (
      !authenticated ||
      !config?.app.onboarding_completed ||
      !config.app.start_minimized ||
      minimizeAttempted.current
    ) {
      return;
    }

    minimizeAttempted.current = true;
    void getCurrentWindow().minimize();
  }, [authenticated, config]);

  const pageContent = useMemo(() => {
    switch (page) {
      case "dashboard":
        return (
          <DashboardPage
            snapshot={snapshot}
            liveLogs={liveLogs}
            running={workflowStatus.running}
            config={config}
            progress={workflowProgress}
          />
        );
      case "jobs":
        return <JobsPage jobs={snapshot?.jobs ?? []} applications={snapshot?.applications ?? []} />;
      case "profiles":
        return (
          <ProfilesPage
            config={config}
            resumes={resumeInventory}
            analyzing={analyzingProfile}
            creating={creatingProfile}
            onConfigChange={(nextConfig) => setConfig(nextConfig)}
            onAnalyzeProfile={handleAnalyzeResumeProfile}
            onCreateProfile={handleCreateResumeProfile}
          />
        );
      case "settings":
        return (
          <SettingsPage
            config={config}
            accountEmail={accountStatus?.email ?? ""}
            onSignOut={() => void handleSignOut()}
            onConfigChange={(nextConfig) => setConfig(nextConfig)}
          />
        );
      default:
        return null;
    }
  }, [accountStatus?.email, analyzingProfile, config, creatingProfile, handleAnalyzeResumeProfile, handleCreateResumeProfile, handleSignOut, liveLogs, page, resumeInventory, snapshot, workflowProgress, workflowStatus.running]);

  const statusLabel = useMemo(() => {
    if (loading || isPending) return "Loading workspace data...";
    if (saving) return "Saving settings...";
    if (analyzingProfile) return "Analyzing resume...";
    if (creatingProfile) return "Creating resume profile...";
    if (workflowStatus.running) {
      return workflowProgress
        ? `Workflow running - ${workflowProgress.percent}%`
        : "Workflow running";
    }
    if (error) return "Action needed";
    if (snapshot?.summary.latest_run_at) {
      return `Last run ${formatDateTime(snapshot.summary.latest_run_at)}`;
    }
    return "Ready";
  }, [analyzingProfile, creatingProfile, error, isPending, loading, saving, snapshot?.summary.latest_run_at, workflowProgress, workflowStatus.running]);

  const pageCopy = PAGE_COPY[page];

  if (loading) {
    return (
      <main className="flex h-screen items-center justify-center bg-horizon-background px-5">
        <div className="rounded-2xl border border-horizon-border bg-white px-6 py-5 text-sm text-horizon-muted shadow-horizon">
          Loading your workspace...
        </div>
      </main>
    );
  }

  if (!accountStatus) {
    return (
      <main className="flex h-screen flex-col items-center justify-center gap-4 bg-horizon-background px-5 text-center">
        <p role="alert" className="max-w-lg text-sm text-horizon-danger">
          {error || "Could not load the local account. Your workspace was not opened."}
        </p>
        <button type="button" className="action-button action-button-primary" onClick={() => void refreshWorkspace()}>
          Retry
        </button>
      </main>
    );
  }

  if (!authenticated) {
    return (
      <AccountPage
        account={accountStatus}
        busy={authenticating}
        error={error}
        onAuthenticate={handleAuthenticate}
      />
    );
  }

  if (config && !config.app.onboarding_completed) {
    return (
      <WelcomePage
        config={config}
        saving={saving}
        error={error}
        onComplete={handleCompleteOnboarding}
      />
    );
  }

  return (
    <AppShell
      page={page}
      onPageChange={setPage}
      title={pageCopy.title}
      subtitle={pageCopy.subtitle}
      running={workflowStatus.running}
      statusLabel={statusLabel}
      startupEnabled={Boolean(config?.app.run_at_startup)}
      autoRunOnLaunch={Boolean(config?.app.auto_run_on_launch)}
      onRefresh={handleRefresh}
      onSave={handleSave}
      onStart={() => void handleStart(false)}
      onStop={() => void handleStop()}
    >
      <div className="space-y-5">
        {appUpdate && !updateDismissed ? (
          <section className="flex flex-col gap-4 rounded-3xl border border-brand-600/20 bg-brand-600/5 p-5 sm:flex-row sm:items-center sm:justify-between">
            <div className="min-w-0">
              <p className="font-bold text-horizon-text">TopJobs Mailer {appUpdate.version} is available</p>
              <p className="mt-1 text-sm text-horizon-muted">
                Download the latest Windows installer from the GitHub release page to update this app.
              </p>
            </div>
            <div className="flex shrink-0 flex-wrap gap-2">
              <button
                type="button"
                className="action-button action-button-primary"
                onClick={() => {
                  void openLatestRelease().catch((openError) =>
                    setError(openError instanceof Error ? openError.message : String(openError))
                  );
                }}
              >
                View update
              </button>
              <button
                type="button"
                className="action-button action-button-secondary"
                onClick={() => setUpdateDismissed(true)}
              >
                Later
              </button>
            </div>
          </section>
        ) : null}
        {updateError ? (
          <div className="flex flex-col gap-3 rounded-2xl border border-horizon-border bg-white px-4 py-3 text-sm text-horizon-muted sm:flex-row sm:items-center sm:justify-between">
            <span>Could not check for app updates: {updateError}</span>
            <button type="button" className="action-button action-button-secondary" onClick={() => void runUpdateCheck()}>
              Try again
            </button>
          </div>
        ) : null}
        {error ? (
          <div className="rounded-3xl border border-horizon-danger/20 bg-horizon-danger/10 px-5 py-4 text-sm text-horizon-danger">
            {error}
          </div>
        ) : null}
        {loading && !snapshot ? (
          <div className="panel p-8 text-sm text-horizon-muted">Loading TopJobs automation data...</div>
        ) : (
          <AnimatePresence mode="wait">
            <motion.div
              key={page}
              initial={{ opacity: 0, y: 18, scale: 0.99 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -12, scale: 0.99 }}
              transition={{ duration: 0.24, ease: "easeOut" }}
            >
              {pageContent}
            </motion.div>
          </AnimatePresence>
        )}
      </div>
    </AppShell>
  );
}
