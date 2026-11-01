import { getVersion } from "@tauri-apps/api/app";
import { invoke } from "@tauri-apps/api/core";

export interface AppUpdate {
  version: string;
  releaseUrl: string;
  notes: string;
}

interface GitHubRelease {
  tag_name?: string;
  html_url?: string;
  body?: string;
  draft?: boolean;
  prerelease?: boolean;
}

export async function checkForAppUpdate(): Promise<AppUpdate | null> {
  const [currentVersion, response] = await Promise.all([
    getVersion(),
    fetch("https://api.github.com/repos/asjathahamedma/Tobjobs-Auto-Mailer/releases/latest", {
      headers: { Accept: "application/vnd.github+json" },
    }),
  ]);
  if (!response.ok) {
    throw new Error(`GitHub returned ${response.status} while checking for updates.`);
  }

  const release = (await response.json()) as GitHubRelease;
  if (!release.tag_name || !release.html_url || release.draft || release.prerelease) {
    return null;
  }

  const latestVersion = release.tag_name.replace(/^v/i, "");
  if (compareVersions(latestVersion, currentVersion) <= 0) {
    return null;
  }

  return {
    version: latestVersion,
    releaseUrl: release.html_url,
    notes: release.body?.trim() ?? "",
  };
}

export function openLatestRelease(): Promise<void> {
  return invoke("open_release_page");
}

function compareVersions(left: string, right: string): number {
  const leftParts = parseVersion(left);
  const rightParts = parseVersion(right);
  if (!leftParts || !rightParts) return 0;

  for (let index = 0; index < 3; index += 1) {
    if (leftParts[index] !== rightParts[index]) {
      return leftParts[index] > rightParts[index] ? 1 : -1;
    }
  }
  return 0;
}

function parseVersion(version: string): [number, number, number] | null {
  const match = version.match(/^(\d+)\.(\d+)\.(\d+)(?:[-+][\w.-]+)?$/);
  if (!match) return null;
  return [Number(match[1]), Number(match[2]), Number(match[3])];
}
