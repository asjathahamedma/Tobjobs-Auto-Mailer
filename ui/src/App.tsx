import { getCurrentWindow } from "@tauri-apps/api/window";
import { AnimatePresence, motion } from "framer-motion";
import { useCallback, useEffect, useMemo, useRef, useState, useTransition } from "react";

import { AppShell } from "@/components/layout/AppShell";
import { DashboardPage } from "@/pages/DashboardPage";
import { JobsPage } from "@/pages/JobsPage";
import { ProfilesPage } from "@/pages/ProfilesPage";
import { SettingsPage } from "@/pages/SettingsPage";
import {
  analyzeResumeProfile,
  createResumeProfile,
  fetchConfig,
  fetchResumeInventory,
  fetchSnapshot,
  getLaunchContext,
  getWorkflowStatus,
  listenWorkflowEvents,
  saveConfig,
  startWorkflow,
  stopWorkflow,
} from "@/lib/tauri";
import type {
  AppConfig,
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
  const [resumeInventory, setResumeInventory] = useState<ResumeInventoryItem[]>([]);
  const [workflowStatus, setWorkflowStatus] = useState<WorkflowStatus>({ running: false, pid: null });
  const [launchContext, setLaunchContext] = useState<LaunchContext>({ startup: false });
  const [liveLogs, setLiveLogs] = useState<string[]>([]);
  const [workflowProgress, setWorkflowProgress] = useState<WorkflowProgressState | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [analyzingProfile, setAnalyzingProfile] = useState(false);
  const [creatingProfile, setCreatingProfile] = useState(false);
  const [error, setError] = useState<string | null>(null);
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
      const [snapshotData, configData, inventoryData, statusData, launchData] = await Promise.all([
        fetchSnapshot(30),
        fetchConfig(),
        fetchResumeInventory(),
        getWorkflowStatus(),
        getLaunchContext(),
      ]);

      startTransition(() => {
        setSnapshot(snapshotData);
        setConfig(configData);
        setResumeInventory(inventoryData);
        setWorkflowStatus(statusData);
        setLaunchContext(launchData);
      });
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : String(loadError));
    } finally {
      setLoading(false);
    }
  }, []);

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
    if (!config || !launchContext || autoStartAttempted.current || workflowStatus.running) {
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
  }, [config, handleStart, launchContext, workflowStatus.running]);

  useEffect(() => {
    if (!config?.app.start_minimized || minimizeAttempted.current) {
      return;
    }

    minimizeAttempted.current = true;
    void getCurrentWindow().minimize();
  }, [config]);

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
        return <SettingsPage config={config} onConfigChange={(nextConfig) => setConfig(nextConfig)} />;
      default:
        return null;
    }
  }, [analyzingProfile, config, creatingProfile, handleAnalyzeResumeProfile, handleCreateResumeProfile, liveLogs, page, resumeInventory, snapshot, workflowProgress, workflowStatus.running]);

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
