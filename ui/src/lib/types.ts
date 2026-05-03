export type PageKey = "dashboard" | "jobs" | "profiles" | "settings";

export interface RunSummary {
  window_days: number;
  runs_count: number;
  latest_run_at: string;
  searched: number;
  filtered_out: number;
  matched: number;
  reviewed: number;
  applied: number;
  rejected: number;
  unique_jobs: number;
  leads_saved: number;
  errors: number;
  missing_email: number;
  already_applied: number;
  missing_resume: number;
  status_counts: Record<string, number>;
  profile_counts: Record<string, number>;
  daily_applications: Record<string, number>;
  skip_reason_counts: Record<string, number>;
  today_summary: TodaySummary;
  profile_performance: ProfilePerformance[];
}

export interface TodaySummary {
  date: string;
  scanned: number;
  reviewed: number;
  matched: number;
  skipped: number;
  applied: number;
  skip_reason_counts: Record<string, number>;
}

export interface ProfilePerformance {
  profile: string;
  resume_name: string;
  matches: number;
  applications: number;
  skipped: number;
  average_fit_score: number;
}

export interface RunHistory {
  started_at: string;
  status: string;
  total_found: number;
  matching_criteria: number;
  new_leads_found: number;
  jobs_reviewed: number;
  emails_sent: number;
  skipped_already_applied: number;
  skipped_missing_email: number;
  skipped_missing_resume: number;
  jobs_reviewed_by_scraper: number;
  skipped_low_fit: number;
  skipped_senior_role: number;
  skipped_excluded_role: number;
  skipped_remote_required: number;
  errors: number;
}

export interface JobRecord {
  title: string;
  profile_label: string;
  fit_score: number;
  company_email: string;
  resume_path: string;
  status: string;
  note: string;
  date_posted: string;
  url: string;
  last_seen_at: string;
  matches_seen: number;
}

export interface ApplicationRecord {
  created_at: string;
  title: string;
  profile: string;
  recipient_email: string;
  status: string;
  note: string;
  job_url: string;
}

export interface ActivityRecord {
  created_at: string;
  level: string;
  message: string;
}

export interface SnapshotResponse {
  generated_at: string;
  window_days: number;
  summary: RunSummary;
  runs: RunHistory[];
  jobs: JobRecord[];
  applications: ApplicationRecord[];
  recent_activity: ActivityRecord[];
}

export interface ProfileConfig {
  label: string;
  resume_path: string;
  summary: string;
  title_keywords: string[];
  description_keywords: string[];
}

export interface ResumeProfileDraftInput {
  label: string;
  summary: string;
  title_keywords: string[];
  description_keywords: string[];
}

export interface ResumeProfileDraftResult {
  ok: boolean;
  preview: {
    draft: ResumeProfileDraftInput;
    meta: {
      resume_file_name: string;
      resume_path: string;
      inferred_template_key: string;
      extracted_text_length: number;
    };
  };
}

export interface MailerAuthConfig {
  sender_email: string;
  app_password: string;
}

export interface AppConfig {
  scraper: {
    level_keywords: string[];
    excluded_title_keywords: string[];
    excluded_seniority_keywords: string[];
    recent_job_window_days: number;
    require_remote: boolean;
    enable_ocr_for_ad_images: boolean;
    ocr_languages: string[];
    minimum_fit_score: number;
    category_urls: string[];
  };
  profiles: Record<string, ProfileConfig>;
  mailer: {
    your_name: string;
    default_resume_path: string;
    auth: MailerAuthConfig;
    contact_info: {
      phone: string;
      email: string;
      portfolio: string;
      linkedin: string;
      github: string;
    };
  };
  app: {
    run_at_startup: boolean;
    auto_run_on_launch: boolean;
    start_minimized: boolean;
    scan_only_mode: boolean;
    startup_delay_seconds: number;
    theme: string;
  };
}

export interface ResumeInventoryItem {
  profile_key: string;
  profile_label: string;
  resume_path: string;
  absolute_path: string;
  file_name: string;
  exists: boolean;
  size_bytes: number;
}

export interface ResumeImportResult {
  ok: boolean;
  config: AppConfig;
  resume_inventory: ResumeInventoryItem[];
  imported: {
    profile_key: string;
    profile: ProfileConfig;
    meta: {
      inferred_template_key: string;
      extracted_text_length: number;
    };
  };
}

export interface WorkflowStatus {
  running: boolean;
  pid?: number | null;
}

export interface LaunchContext {
  startup: boolean;
}

export interface WorkflowEventEnvelope {
  kind: string;
  payload: Record<string, unknown>;
}

export interface WorkflowProgressState {
  percent: number;
  stage: string;
  detail: string;
  current?: number;
  total?: number;
}
