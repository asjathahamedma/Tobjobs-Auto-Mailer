import { useMemo, useState } from "react";
import { RotateCcw } from "lucide-react";

import { SectionCard } from "@/components/ui/SectionCard";
import { StatusBadge } from "@/components/ui/StatusBadge";
import type { ApplicationRecord, JobRecord } from "@/lib/types";
import { formatDateTime } from "@/lib/utils";

interface JobsPageProps {
  jobs: JobRecord[];
  applications: ApplicationRecord[];
}

interface UnifiedJobRow {
  key: string;
  title: string;
  profile: string;
  fitScore: number;
  resumeName: string;
  status: string;
  note: string;
  recipient: string;
  updatedAt: string;
  dateFilterValue: string;
  url: string;
}

export function JobsPage({ jobs, applications }: JobsPageProps) {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [profileFilter, setProfileFilter] = useState("all");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");

  const resetFilters = () => {
    setSearch("");
    setStatusFilter("all");
    setProfileFilter("all");
    setFromDate("");
    setToDate("");
  };

  const rows = useMemo(() => {
    const map = new Map<string, UnifiedJobRow>();

    for (const job of jobs) {
      const key = job.url || `${job.title}-${job.last_seen_at}`;
      map.set(key, {
        key,
        title: job.title,
        profile: job.profile_label || "N/A",
        fitScore: job.fit_score,
        resumeName: fileNameFromPath(job.resume_path),
        status: job.status || "matched",
        note: job.note || "",
        recipient: job.company_email || "",
        updatedAt: job.last_seen_at || "",
        dateFilterValue: normalizeDateValue(job.date_posted || job.last_seen_at || ""),
        url: job.url,
      });
    }

    for (const application of applications) {
      const key = application.job_url || `${application.title}-${application.created_at}`;
      const existing = map.get(key);
      map.set(key, {
        key,
        title: application.title || existing?.title || "Untitled job",
        profile: application.profile || existing?.profile || "N/A",
        fitScore: existing?.fitScore || 0,
        resumeName: existing?.resumeName || "",
        status: application.status || existing?.status || "processed",
        note: application.note || existing?.note || "",
        recipient: application.recipient_email || existing?.recipient || "",
        updatedAt: application.created_at || existing?.updatedAt || "",
        dateFilterValue: normalizeDateValue(application.created_at || existing?.updatedAt || ""),
        url: application.job_url || existing?.url || "",
      });
    }

    return Array.from(map.values()).sort((left, right) => {
      const leftTime = Date.parse(left.updatedAt || "");
      const rightTime = Date.parse(right.updatedAt || "");
      return (Number.isNaN(rightTime) ? 0 : rightTime) - (Number.isNaN(leftTime) ? 0 : leftTime);
    });
  }, [applications, jobs]);

  const statusOptions = useMemo(
    () => ["all", ...Array.from(new Set(rows.map((row) => row.status).filter(Boolean))).sort()],
    [rows]
  );
  const profileOptions = useMemo(
    () => ["all", ...Array.from(new Set(rows.map((row) => row.profile).filter(Boolean))).sort()],
    [rows]
  );

  const filteredRows = useMemo(() => {
    const normalizedSearch = search.trim().toLowerCase();
    return rows.filter((row) => {
      const matchesSearch =
        !normalizedSearch ||
        row.title.toLowerCase().includes(normalizedSearch) ||
        row.profile.toLowerCase().includes(normalizedSearch) ||
        row.recipient.toLowerCase().includes(normalizedSearch) ||
        row.note.toLowerCase().includes(normalizedSearch);
      const matchesStatus = statusFilter === "all" || row.status === statusFilter;
      const matchesProfile = profileFilter === "all" || row.profile === profileFilter;
      const matchesFromDate = !fromDate || (row.dateFilterValue && row.dateFilterValue >= fromDate);
      const matchesToDate = !toDate || (row.dateFilterValue && row.dateFilterValue <= toDate);
      return matchesSearch && matchesStatus && matchesProfile && matchesFromDate && matchesToDate;
    });
  }, [fromDate, profileFilter, rows, search, statusFilter, toDate]);

  return (
    <SectionCard
      title="Jobs and Application Status"
      subtitle="One filtered view for matched jobs, applied jobs, missing-email jobs, skipped jobs, and failed sends."
      actions={
        <span className="rounded-full bg-horizon-background px-3 py-2 text-xs font-semibold text-horizon-muted">
          {filteredRows.length} shown / {rows.length} total
        </span>
      }
    >
      <div className="space-y-5">
        <div className="grid gap-4 xl:grid-cols-[1.1fr_0.75fr_0.75fr_0.7fr_0.7fr_auto]">
          <label className="min-w-0 space-y-2">
            <span className="text-sm font-semibold text-horizon-text">Search</span>
            <input
              className="input-base"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search by title, profile, email, or note"
            />
          </label>

          <label className="min-w-0 space-y-2">
            <span className="text-sm font-semibold text-horizon-text">Status</span>
            <select
              className="input-base"
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value)}
            >
              {statusOptions.map((option) => (
                <option key={option} value={option}>
                  {option === "all" ? "All statuses" : option.replace(/_/g, " ")}
                </option>
              ))}
            </select>
          </label>

          <label className="min-w-0 space-y-2">
            <span className="text-sm font-semibold text-horizon-text">Profile</span>
            <select
              className="input-base"
              value={profileFilter}
              onChange={(event) => setProfileFilter(event.target.value)}
            >
              {profileOptions.map((option) => (
                <option key={option} value={option}>
                  {option === "all" ? "All profiles" : option}
                </option>
              ))}
            </select>
          </label>

          <label className="min-w-0 space-y-2">
            <span className="text-sm font-semibold text-horizon-text">From Date</span>
            <input
              type="date"
              className="input-base"
              value={fromDate}
              onChange={(event) => setFromDate(event.target.value)}
            />
          </label>

          <label className="min-w-0 space-y-2">
            <span className="text-sm font-semibold text-horizon-text">To Date</span>
            <input
              type="date"
              className="input-base"
              value={toDate}
              onChange={(event) => setToDate(event.target.value)}
            />
          </label>

          <div className="flex min-w-0 items-end">
            <button
              type="button"
              onClick={resetFilters}
              className="action-button action-button-ghost h-12 w-full xl:w-auto"
            >
              <RotateCcw className="h-4 w-4" />
              Reset
            </button>
          </div>
        </div>

        <div className="table-shell">
          <div className="min-w-0 overflow-x-auto">
            <table className="w-full min-w-[840px]">
              <thead className="table-head">
                <tr>
                  {[
                    "Job",
                    "Profile",
                    "Match Score",
                    "Resume",
                    "Status",
                    "Reason / Note",
                    "Recipient",
                    "Updated",
                  ].map((label) => (
                    <th key={label} className="px-4 py-4">
                      {label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filteredRows.length ? (
                  filteredRows.map((row) => (
                    <tr key={row.key} className="hover:bg-[#fafbff]">
                      <td className="table-cell min-w-[250px]">
                        <div className="space-y-1">
                          <p className="break-words font-semibold text-horizon-text">{row.title}</p>
                          {row.url ? (
                            <a
                              className="text-xs text-brand-600 hover:underline"
                              href={row.url}
                              target="_blank"
                              rel="noreferrer"
                            >
                              Open listing
                            </a>
                          ) : (
                            <p className="text-xs text-horizon-muted">No listing URL available</p>
                          )}
                        </div>
                      </td>
                      <td className="table-cell">{row.profile}</td>
                      <td className="table-cell font-semibold">{row.fitScore || "N/A"}</td>
                      <td className="table-cell text-sm text-horizon-muted">{row.resumeName || "N/A"}</td>
                      <td className="table-cell">
                        <StatusBadge value={row.status || "matched"} />
                      </td>
                      <td className="table-cell max-w-[280px] text-sm text-horizon-muted">
                        <div className="break-words whitespace-normal">{row.note || "N/A"}</div>
                      </td>
                      <td className="table-cell text-sm text-horizon-muted">
                        <div className="max-w-[220px] break-words whitespace-normal">{row.recipient || "N/A"}</div>
                      </td>
                      <td className="table-cell text-sm text-horizon-muted">
                        {formatDateTime(row.updatedAt)}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={8} className="table-cell py-10 text-center text-horizon-muted">
                      No jobs matched the current filters.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </SectionCard>
  );
}

function fileNameFromPath(value: string) {
  return value.split(/[/\\]/).filter(Boolean).pop() || value;
}

function normalizeDateValue(value: string) {
  if (!value) {
    return "";
  }

  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    return value;
  }

  const parsedTime = Date.parse(value);
  if (Number.isNaN(parsedTime)) {
    return "";
  }

  return new Date(parsedTime).toISOString().slice(0, 10);
}
