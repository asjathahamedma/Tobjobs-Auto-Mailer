import { motion } from "framer-motion";
import { BarChart3, CheckCircle2, Clock3, Filter, Search, ShieldX, UserRoundCheck } from "lucide-react";

import { SectionCard } from "@/components/ui/SectionCard";
import { StatCard } from "@/components/ui/StatCard";
import { StatusBadge } from "@/components/ui/StatusBadge";
import type { AppConfig, SnapshotResponse, WorkflowProgressState } from "@/lib/types";
import { formatDateTime } from "@/lib/utils";

interface DashboardPageProps {
  snapshot: SnapshotResponse | null;
  liveLogs: string[];
  running: boolean;
  config: AppConfig | null;
  progress: WorkflowProgressState | null;
}

export function DashboardPage({ snapshot, liveLogs, running, config, progress }: DashboardPageProps) {
  const summary = snapshot?.summary;
  const progressPercent = Math.max(0, Math.min(100, progress?.percent ?? 0));
  const readyToApply =
    snapshot?.jobs.filter((job) => job.status === "matched" || job.status === "").length ?? 0;
  const activityLines =
    running || liveLogs.length
      ? liveLogs
      : (snapshot?.recent_activity ?? []).map(
          (entry) => `${formatDateTime(entry.created_at)} [${entry.level}] ${entry.message}`
        );

  const setupChecks = [
    {
      label: "Sender profile",
      done: Boolean(config?.mailer.your_name.trim()),
      helper: "Add the full name used in your application emails.",
    },
    {
      label: "Gmail credentials",
      done: Boolean(config?.mailer.auth.sender_email.trim() && config?.mailer.auth.app_password.trim()),
      helper: "Save the Gmail address and app password in Settings.",
    },
    {
      label: "Resume profiles",
      done: Boolean(config && Object.keys(config.profiles).length),
      helper: "Import at least one PDF resume to auto-create a resume profile.",
    },
  ];
  const completedSetupCount = setupChecks.filter((item) => item.done).length;
  const todaySummary = summary?.today_summary;
  const todaySkipReasonCounts = todaySummary?.skip_reason_counts ?? {};
  const skipReasonCounts = summary?.skip_reason_counts ?? {};
  const profilePerformance = summary?.profile_performance ?? [];

  return (
    <div className="space-y-6">
      <SectionCard
        title="Live Workflow Progress"
        subtitle="See which stage is running right now and how far the current automation session has progressed."
        actions={
          <span className="inline-flex max-w-full rounded-full bg-horizon-background px-3 py-2 text-xs font-semibold text-horizon-muted">
            {progressPercent}% complete
          </span>
        }
      >
        <div className="space-y-4">
          <div className="w-full overflow-hidden rounded-full bg-horizon-border">
            <motion.div
              className="h-4 rounded-full bg-gradient-to-r from-brand-600 via-[#6b4dff] to-horizon-info"
              initial={{ width: 0 }}
              animate={{ width: `${progressPercent}%` }}
              transition={{ duration: 0.35, ease: "easeOut" }}
            />
          </div>

          <div className="grid gap-4 md:grid-cols-[1.1fr_0.9fr]">
            <div className="min-w-0 rounded-2xl border border-horizon-border bg-horizon-background px-5 py-4">
              <p className="mb-2 text-xs font-bold uppercase tracking-[0.22em] text-horizon-muted">
                Current Stage
              </p>
              <p className="text-lg font-bold capitalize text-horizon-text">
                {progress?.stage ? progress.stage.replace(/_/g, " ") : running ? "starting" : "idle"}
              </p>
              <p className="mt-2 break-words text-sm text-horizon-muted">
                {progress?.detail || (running ? "Waiting for workflow updates..." : "Start the workflow to see live progress here.")}
              </p>
            </div>

            <div className="min-w-0 rounded-2xl border border-horizon-border bg-horizon-background px-5 py-4">
              <p className="mb-2 text-xs font-bold uppercase tracking-[0.22em] text-horizon-muted">
                Stage Counter
              </p>
              <p className="text-lg font-bold text-horizon-text">
                {progress?.current && progress?.total
                  ? `${progress.current} / ${progress.total}`
                  : running
                    ? "Live"
                    : "Not running"}
              </p>
              <p className="mt-2 text-sm text-horizon-muted">
                {progress?.current && progress?.total
                  ? "Shows the current item being reviewed or applied in this stage."
                  : "Counters appear automatically when jobs or applications are being processed."}
              </p>
            </div>
          </div>
        </div>
      </SectionCard>

      <SectionCard
        title="Setup Checklist"
        subtitle="Everything a new user needs before starting automated applications on this computer."
        actions={
          <span className="rounded-full bg-horizon-background px-3 py-2 text-xs font-semibold text-horizon-muted">
            {completedSetupCount}/{setupChecks.length} complete
          </span>
        }
      >
        <div className="grid gap-4 lg:grid-cols-3">
          {setupChecks.map((item) => (
            <div
              key={item.label}
              className="rounded-2xl border border-horizon-border bg-horizon-background px-5 py-4"
            >
              <div className="mb-3 flex items-center justify-between gap-3">
                <p className="font-semibold text-horizon-text">{item.label}</p>
                <StatusBadge value={item.done ? "completed" : "pending"} />
              </div>
              <p className="text-sm text-horizon-muted">{item.helper}</p>
            </div>
          ))}
        </div>
      </SectionCard>

      <div className="grid gap-5 xl:grid-cols-5">
        <StatCard
          title="Jobs Found"
          value={summary?.searched ?? 0}
          caption="Total roles scanned in the current 30-day window."
          icon={<Search className="h-6 w-6" />}
          tone="brand"
        />
        <StatCard
          title="Filtered Jobs"
          value={summary?.filtered_out ?? 0}
          caption="Roles filtered out by profile and exclusion rules."
          icon={<Filter className="h-6 w-6" />}
          tone="warning"
        />
        <StatCard
          title="Skipped Jobs"
          value={summary?.rejected ?? 0}
          caption="Jobs skipped because of missing email, duplicates, or mismatch."
          icon={<ShieldX className="h-6 w-6" />}
          tone="danger"
        />
        <StatCard
          title="Ready to Apply"
          value={readyToApply}
          caption="Matched jobs still waiting for application."
          icon={<Clock3 className="h-6 w-6" />}
          tone="info"
        />
        <StatCard
          title="Applied"
          value={summary?.applied ?? 0}
          caption="Jobs successfully sent through the mailer."
          icon={<CheckCircle2 className="h-6 w-6" />}
          tone="success"
        />
      </div>

      <SectionCard
        title="Today Summary"
        subtitle="Current-day workflow totals from the latest automation history."
        actions={
          <span className="inline-flex max-w-full rounded-full bg-horizon-background px-3 py-2 text-xs font-semibold text-horizon-muted">
            {todaySummary?.date || "Today"}
          </span>
        }
      >
        <div className="grid gap-4 md:grid-cols-5">
          <MiniMetric label="Scanned" value={todaySummary?.scanned ?? 0} />
          <MiniMetric label="Reviewed" value={todaySummary?.reviewed ?? 0} />
          <MiniMetric label="Matched" value={todaySummary?.matched ?? 0} />
          <MiniMetric label="Skipped" value={todaySummary?.skipped ?? 0} />
          <MiniMetric label="Applied" value={todaySummary?.applied ?? 0} />
        </div>
        <div className="mt-5 rounded-2xl border border-horizon-border bg-horizon-background p-4">
          <div className="mb-4 flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="text-sm font-bold text-horizon-text">Skipped By Reason Today</p>
              <p className="text-xs text-horizon-muted">Shows why today&apos;s jobs did not move to a sent application.</p>
            </div>
            <span className="text-xs font-bold text-horizon-muted">
              {todaySummary?.skipped ?? 0} total skipped
            </span>
          </div>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {Object.entries(todaySkipReasonCounts).some(([, count]) => count > 0) ? (
              Object.entries(todaySkipReasonCounts).map(([reason, count]) => (
                <BarMetric
                  key={reason}
                  label={reason}
                  value={count}
                  max={Math.max(...Object.values(todaySkipReasonCounts), 1)}
                />
              ))
            ) : (
              <p className="text-sm text-horizon-muted">No skipped jobs recorded today.</p>
            )}
          </div>
        </div>
      </SectionCard>

      <div className="grid gap-6 2xl:grid-cols-[1.15fr_0.85fr]">
        <SectionCard
          title="Profile Performance"
          subtitle="Profiles ranked by matched jobs and successful applications."
          actions={<UserRoundCheck className="h-5 w-5 text-brand-600" />}
        >
          <div className="space-y-4">
            {profilePerformance.length ? (
              profilePerformance.slice(0, 6).map((profile) => (
                <div
                  key={profile.profile}
                  className="rounded-2xl border border-horizon-border bg-horizon-background px-4 py-4"
                >
                  <div className="mb-3 flex flex-col gap-1 sm:flex-row sm:items-start sm:justify-between">
                    <div className="min-w-0">
                      <p className="font-semibold text-horizon-text">{profile.profile}</p>
                      <p className="break-words text-xs text-horizon-muted">
                        {profile.resume_name || "No resume recorded"}
                      </p>
                    </div>
                    <span className="text-sm font-bold text-horizon-text">
                      {profile.applications} applied
                    </span>
                  </div>
                  <div className="grid gap-3 md:grid-cols-3">
                    <BarMetric label="Matches" value={profile.matches} max={maxProfileValue(profilePerformance, "matches")} />
                    <BarMetric label="Applied" value={profile.applications} max={maxProfileValue(profilePerformance, "applications")} />
                    <BarMetric label="Skipped" value={profile.skipped} max={maxProfileValue(profilePerformance, "skipped")} />
                  </div>
                  <p className="mt-3 text-xs font-semibold text-horizon-muted">
                    Average fit score: {profile.average_fit_score || "N/A"}
                  </p>
                </div>
              ))
            ) : (
              <p className="text-sm text-horizon-muted">No profile performance data yet.</p>
            )}
          </div>
        </SectionCard>

        <SectionCard
          title="Skip Reason Breakdown"
          subtitle="Why jobs were skipped across the current history window."
          actions={<BarChart3 className="h-5 w-5 text-brand-600" />}
        >
          <div className="space-y-4">
            {Object.entries(skipReasonCounts).some(([, count]) => count > 0) ? (
              Object.entries(skipReasonCounts).map(([reason, count]) => (
                <BarMetric
                  key={reason}
                  label={reason}
                  value={count}
                  max={Math.max(...Object.values(skipReasonCounts), 1)}
                />
              ))
            ) : (
              <p className="text-sm text-horizon-muted">No skipped jobs recorded yet.</p>
            )}
          </div>
        </SectionCard>
      </div>

      <div className="grid gap-6 2xl:grid-cols-[1.2fr_1fr]">
        <div className="space-y-6">
          <SectionCard
            title="Recent Runs"
            subtitle="Latest workflow sessions captured from the Python automation."
          >
            <div className="space-y-3">
              {snapshot?.runs.length ? (
                snapshot.runs.slice(0, 8).map((run) => (
                  <div
                    key={`${run.started_at}-${run.total_found}`}
                    className="flex flex-col items-start gap-3 rounded-2xl border border-horizon-border bg-horizon-background px-4 py-3 transition-colors hover:border-brand-200 hover:bg-white sm:flex-row sm:items-center sm:justify-between"
                  >
                    <div className="min-w-0">
                      <p className="font-semibold text-horizon-text">
                        {formatDateTime(run.started_at)}
                      </p>
                      <p className="break-words text-sm text-horizon-muted">
                        {run.total_found} found - {run.matching_criteria} matched - {run.emails_sent} applied
                      </p>
                    </div>
                    <StatusBadge value={run.status || "completed"} />
                  </div>
                ))
              ) : (
                <p className="text-sm text-horizon-muted">No runs recorded yet.</p>
              )}
            </div>
          </SectionCard>

          <SectionCard
            title="Recent Activity"
            subtitle="Live workflow output and the latest saved automation events."
          >
            <div className="max-h-[380px] space-y-3 overflow-auto pr-2">
              {activityLines.slice(0, running ? 200 : 40).map((line, index) => (
                <div
                  key={`${index}-${line}`}
                  className="rounded-2xl border border-horizon-border bg-[#fafbff] px-4 py-3 text-sm leading-6 text-horizon-text"
                >
                  {line}
                </div>
              ))}
              {!activityLines.length ? (
                <p className="text-sm text-horizon-muted">No activity yet.</p>
              ) : null}
            </div>
          </SectionCard>
        </div>

        <div className="space-y-6">
          <SectionCard
            title="Status Breakdown"
            subtitle="Application outcomes across the current 30-day window."
          >
            <div className="space-y-3">
              {summary ? (
                Object.entries(summary.status_counts)
                  .sort(([, left], [, right]) => right - left)
                  .map(([status, count]) => (
                    <div
                      key={status}
                      className="flex items-center justify-between rounded-2xl border border-horizon-border px-4 py-3 transition-colors hover:border-brand-200 hover:bg-horizon-background"
                    >
                      <StatusBadge value={status} />
                      <span className="text-lg font-bold text-horizon-text">{count}</span>
                    </div>
                  ))
              ) : (
                <p className="text-sm text-horizon-muted">No status data yet.</p>
              )}
            </div>
          </SectionCard>

          <SectionCard
            title="Latest Run Summary"
            subtitle="Most recent workflow totals from the Python backend."
          >
            <div className="space-y-3 text-sm">
              {snapshot?.runs[0] ? (
                <>
                  <SummaryRow label="Started" value={formatDateTime(snapshot.runs[0].started_at)} />
                  <SummaryRow label="Jobs Found" value={snapshot.runs[0].total_found} />
                  <SummaryRow
                    label="Filtered Jobs"
                    value={snapshot.runs[0].total_found - snapshot.runs[0].matching_criteria}
                  />
                  <SummaryRow
                    label="Ready to Apply"
                    value={Math.max(
                      snapshot.runs[0].matching_criteria -
                        snapshot.runs[0].emails_sent -
                        snapshot.runs[0].skipped_missing_email -
                        snapshot.runs[0].skipped_already_applied -
                        snapshot.runs[0].skipped_missing_resume,
                      0
                    )}
                  />
                  <SummaryRow label="Applied" value={snapshot.runs[0].emails_sent} />
                  <SummaryRow
                    label="Skipped"
                    value={
                      snapshot.runs[0].skipped_missing_email +
                      snapshot.runs[0].skipped_already_applied +
                      snapshot.runs[0].skipped_missing_resume
                    }
                  />
                  <SummaryRow label="Errors" value={snapshot.runs[0].errors} />
                </>
              ) : (
                <p className="text-sm text-horizon-muted">No run summary yet.</p>
              )}
            </div>
          </SectionCard>
        </div>
      </div>
    </div>
  );
}

function MiniMetric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-2xl border border-horizon-border bg-horizon-background px-4 py-4">
      <p className="text-xs font-bold uppercase tracking-[0.18em] text-horizon-muted">{label}</p>
      <p className="mt-2 text-2xl font-bold text-horizon-text">{value}</p>
    </div>
  );
}

function BarMetric({ label, value, max }: { label: string; value: number; max: number }) {
  const width = max > 0 ? Math.max(4, Math.round((value / max) * 100)) : 0;
  return (
    <div className="min-w-0">
      <div className="mb-2 flex items-center justify-between gap-3">
        <span className="truncate text-xs font-semibold text-horizon-muted">{label}</span>
        <span className="text-xs font-bold text-horizon-text">{value}</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-horizon-border">
        <div
          className="h-full rounded-full bg-gradient-to-r from-brand-600 to-horizon-info"
          style={{ width: `${width}%` }}
        />
      </div>
    </div>
  );
}

function maxProfileValue(
  profiles: Array<{ matches: number; applications: number; skipped: number }>,
  key: "matches" | "applications" | "skipped"
) {
  return Math.max(...profiles.map((profile) => profile[key]), 1);
}

function SummaryRow({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex flex-col gap-1 rounded-2xl border border-horizon-border bg-horizon-background px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
      <span className="text-horizon-muted">{label}</span>
      <span className="break-words font-semibold text-horizon-text">{value}</span>
    </div>
  );
}
