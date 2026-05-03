import { listen } from "@tauri-apps/api/event";
import { invoke } from "@tauri-apps/api/core";

import type {
  AppConfig,
  LaunchContext,
  ResumeImportResult,
  ResumeProfileDraftInput,
  ResumeProfileDraftResult,
  ResumeInventoryItem,
  SnapshotResponse,
  WorkflowEventEnvelope,
  WorkflowStatus
} from "@/lib/types";

export async function fetchSnapshot(windowDays = 30) {
  return invoke<SnapshotResponse>("get_snapshot", { windowDays });
}

export async function fetchConfig() {
  return invoke<AppConfig>("get_config");
}

export async function saveConfig(config: AppConfig) {
  return invoke("save_config", { config });
}

export async function fetchResumeInventory() {
  return invoke<ResumeInventoryItem[]>("get_resume_inventory");
}

export async function importResume(fileName: string, contentBase64: string) {
  return invoke<ResumeImportResult>("import_resume", { fileName, contentBase64 });
}

export async function analyzeResumeProfile(fileName: string, contentBase64: string) {
  return invoke<ResumeProfileDraftResult>("analyze_resume_profile", { fileName, contentBase64 });
}

export async function createResumeProfile(
  fileName: string,
  contentBase64: string,
  profile: ResumeProfileDraftInput
) {
  return invoke<ResumeImportResult>("create_resume_profile", { fileName, contentBase64, profile });
}

export async function getWorkflowStatus() {
  return invoke<WorkflowStatus>("get_workflow_status");
}

export async function getLaunchContext() {
  return invoke<LaunchContext>("get_launch_context");
}

export async function startWorkflow(startup = false) {
  return invoke("start_workflow", { startup });
}

export async function stopWorkflow() {
  return invoke("stop_workflow");
}

export async function listenWorkflowEvents(
  handler: (event: WorkflowEventEnvelope) => void
) {
  return listen<WorkflowEventEnvelope>("workflow:event", (event) => handler(event.payload));
}
