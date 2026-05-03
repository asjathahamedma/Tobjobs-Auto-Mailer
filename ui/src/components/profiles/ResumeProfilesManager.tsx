import { FilePlus2, Sparkles, Trash2 } from "lucide-react";
import { useRef, useState } from "react";

import type { AppConfig, ResumeInventoryItem } from "@/lib/types";
import { formatBytes, parseMultiline, toMultiline } from "@/lib/utils";

interface ResumeProfilesManagerProps {
  title: string;
  subtitle: string;
  config: AppConfig | null;
  resumes: ResumeInventoryItem[];
  analyzing: boolean;
  creating: boolean;
  onConfigChange: (config: AppConfig) => void;
  onAnalyzeProfile: (file: File) => Promise<{
    preview: {
      draft: {
        label: string;
        summary: string;
        title_keywords: string[];
        description_keywords: string[];
      };
    };
  }>;
  onCreateProfile: (
    file: File,
    draft: {
      label: string;
      summary: string;
      title_keywords: string[];
      description_keywords: string[];
    }
  ) => Promise<void>;
}

export function ResumeProfilesManager({
  title,
  subtitle,
  config,
  resumes,
  analyzing,
  creating,
  onConfigChange,
  onAnalyzeProfile,
  onCreateProfile,
}: ResumeProfilesManagerProps) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [draftLoaded, setDraftLoaded] = useState(false);
  const [draftLabel, setDraftLabel] = useState("");
  const [draftSummary, setDraftSummary] = useState("");
  const [draftTitleKeywords, setDraftTitleKeywords] = useState("");
  const [draftDescriptionKeywords, setDraftDescriptionKeywords] = useState("");

  if (!config) {
    return <div className="panel p-6 text-sm text-horizon-muted">Loading resume profiles...</div>;
  }

  const updateProfileField = (
    profileKey: string,
    field: "label" | "summary" | "title_keywords" | "description_keywords",
    value: string | string[]
  ) => {
    onConfigChange({
      ...config,
      profiles: {
        ...config.profiles,
        [profileKey]: {
          ...config.profiles[profileKey],
          [field]: value,
        },
      },
    });
  };

  const removeProfile = (profileKey: string) => {
    const nextProfiles = { ...config.profiles };
    delete nextProfiles[profileKey];
    onConfigChange({
      ...config,
      profiles: nextProfiles,
    });
  };

  const resetDraft = () => {
    setSelectedFile(null);
    setDraftLoaded(false);
    setDraftLabel("");
    setDraftSummary("");
    setDraftTitleKeywords("");
    setDraftDescriptionKeywords("");
    if (inputRef.current) {
      inputRef.current.value = "";
    }
  };

  const handleResumeSelected = async (files: FileList | null) => {
    const nextFile = files?.[0] ?? null;
    setDraftLoaded(false);
    setDraftLabel("");
    setDraftSummary("");
    setDraftTitleKeywords("");
    setDraftDescriptionKeywords("");
    setSelectedFile(nextFile);
    if (!nextFile) {
      return;
    }

    try {
      const result = await onAnalyzeProfile(nextFile);
      const draft = result.preview.draft;
      setDraftLabel(draft.label || humanizeFileName(nextFile.name));
      setDraftSummary(draft.summary || "");
      setDraftTitleKeywords(toMultiline(draft.title_keywords));
      setDraftDescriptionKeywords(toMultiline(draft.description_keywords));
      setDraftLoaded(true);
    } catch {
      resetDraft();
    }
  };

  const handleCreateProfile = async () => {
    if (!selectedFile || !draftLoaded) {
      return;
    }

    await onCreateProfile(selectedFile, {
      label: draftLabel.trim(),
      summary: draftSummary.trim(),
      title_keywords: parseMultiline(draftTitleKeywords),
      description_keywords: parseMultiline(draftDescriptionKeywords),
    });

    resetDraft();
  };

  const inventoryByPath = new Map(resumes.map((resume) => [resume.resume_path, resume]));

  return (
    <div className="space-y-6">
      <section className="panel overflow-hidden">
        <div className="panel-header flex-col items-start gap-4 md:flex-row md:items-center md:justify-between">
          <div className="min-w-0">
            <h3 className="text-xl font-bold text-horizon-text">{title}</h3>
            <p className="mt-1 text-sm text-horizon-muted">{subtitle}</p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <span className="rounded-full bg-horizon-background px-4 py-2 text-xs font-semibold uppercase tracking-[0.22em] text-horizon-muted">
              {Object.keys(config.profiles).length} profiles
            </span>
            <button
              type="button"
              onClick={() => inputRef.current?.click()}
              className="action-button action-button-secondary"
              disabled={analyzing || creating}
            >
              <FilePlus2 className="h-4 w-4" />
              {selectedFile ? "Change Resume" : "Import Resume PDF"}
            </button>
            <input
              ref={inputRef}
              type="file"
              accept=".pdf,application/pdf"
              className="hidden"
              onChange={(event) => {
                void handleResumeSelected(event.target.files);
              }}
            />
          </div>
        </div>

        <div className="panel-body space-y-5">
          {!selectedFile && !analyzing ? (
            <div className="flex flex-col items-start gap-5 rounded-3xl border border-dashed border-brand-600/20 bg-brand-600/5 px-5 py-6 sm:flex-row sm:items-center sm:justify-between">
              <div className="min-w-0">
                <p className="text-base font-bold text-horizon-text">Import a resume to create a profile</p>
                <p className="mt-1 text-sm text-horizon-muted">
                  The profile draft appears here after the PDF is analyzed.
                </p>
              </div>
              <button
                type="button"
                onClick={() => inputRef.current?.click()}
                className="action-button action-button-primary"
              >
                <FilePlus2 className="h-4 w-4" />
                Import Resume
              </button>
            </div>
          ) : (
            <>
              <div className="grid gap-5 xl:grid-cols-[0.86fr_1.14fr]">
                <div className="field-shell space-y-4">
                  <div className="flex items-start gap-3">
                    <div className="rounded-2xl bg-brand-600/10 p-3 text-brand-600">
                      <Sparkles className="h-5 w-5" />
                    </div>
                    <div className="min-w-0">
                      <p className="field-label mb-1">Imported Resume</p>
                      <p className="field-value text-base font-semibold">
                        {selectedFile?.name || "Analyzing resume..."}
                      </p>
                      <p className="mt-2 text-xs text-horizon-muted">
                        {analyzing
                          ? "Reading the uploaded resume and extracting suggested details..."
                          : "Detected from the uploaded resume. You can edit anything before adding."}
                      </p>
                    </div>
                  </div>

                  <div className="grid gap-4 sm:grid-cols-2">
                    <div>
                      <p className="mb-2 text-xs font-bold uppercase tracking-[0.22em] text-horizon-muted">
                        Size
                      </p>
                      <p className="text-sm font-semibold text-horizon-text">
                        {selectedFile ? formatBytes(selectedFile.size) : "Analyzing"}
                      </p>
                    </div>
                    <div>
                      <p className="mb-2 text-xs font-bold uppercase tracking-[0.22em] text-horizon-muted">
                        Flow
                      </p>
                      <p className="text-sm font-semibold text-horizon-text">
                        {"Resume -> Profile -> Match -> Apply"}
                      </p>
                    </div>
                  </div>
                </div>

                <div className="grid gap-5">
                  <label className="min-w-0 space-y-2">
                    <span className="text-sm font-semibold text-horizon-text">Profile Label</span>
                    <input
                      className="input-base"
                      value={draftLabel}
                      onChange={(event) => setDraftLabel(event.target.value)}
                      disabled={analyzing}
                      placeholder="Example: Frontend Development"
                    />
                  </label>

                  <label className="min-w-0 space-y-2">
                    <span className="text-sm font-semibold text-horizon-text">Summary</span>
                    <textarea
                      className="textarea-base"
                      value={draftSummary}
                      onChange={(event) => setDraftSummary(event.target.value)}
                      disabled={analyzing}
                      placeholder="Detected summary appears here."
                    />
                  </label>
                </div>
              </div>

              <div className="grid gap-5 xl:grid-cols-2">
                <label className="min-w-0 space-y-2">
                  <span className="text-sm font-semibold text-horizon-text">Title Keywords</span>
                  <textarea
                    className="textarea-base"
                    value={draftTitleKeywords}
                    onChange={(event) => setDraftTitleKeywords(event.target.value)}
                    disabled={analyzing}
                    placeholder="Detected title keywords appear here."
                  />
                </label>
                <label className="min-w-0 space-y-2">
                  <span className="text-sm font-semibold text-horizon-text">Description Keywords</span>
                  <textarea
                    className="textarea-base"
                    value={draftDescriptionKeywords}
                    onChange={(event) => setDraftDescriptionKeywords(event.target.value)}
                    disabled={analyzing}
                    placeholder="Detected description keywords appear here."
                  />
                </label>
              </div>

              <div className="flex flex-col gap-3 rounded-3xl border border-horizon-border bg-horizon-background px-4 py-4 sm:flex-row sm:items-center sm:justify-between">
                <p className="text-sm text-horizon-muted">
                  Review the detected details, then add the profile or cancel this draft.
                </p>
                <div className="flex flex-wrap items-center gap-3">
                  <button
                    type="button"
                    onClick={resetDraft}
                    className="action-button action-button-ghost"
                    disabled={analyzing || creating}
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={() => void handleCreateProfile()}
                    className="action-button action-button-primary"
                    disabled={!draftLoaded || analyzing || creating}
                  >
                    <FilePlus2 className="h-4 w-4" />
                    {creating ? "Adding Profile..." : "Add Profile"}
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </section>

      {!Object.keys(config.profiles).length ? (
        <div className="panel p-8 text-sm text-horizon-muted">
          No resume profiles yet. Choose a resume, add the details you want, and create the first
          profile.
        </div>
      ) : null}

      <div className="grid gap-6 2xl:grid-cols-2">
        {Object.entries(config.profiles).map(([profileKey, profile]) => {
          const inventory = inventoryByPath.get(profile.resume_path);
          const resumeName = inventory?.file_name || fileNameFromPath(profile.resume_path);
          return (
            <section key={profileKey} className="panel profile-card overflow-hidden">
              <div className="panel-header">
                <div className="min-w-0 flex items-center gap-3">
                  <div className="rounded-2xl bg-brand-600/10 p-3 text-brand-600">
                    <Sparkles className="h-5 w-5" />
                  </div>
                  <div className="min-w-0">
                    <h4 className="truncate text-lg font-bold text-horizon-text">{profile.label}</h4>
                    <p className="truncate text-sm text-horizon-muted">Profile key: {profileKey}</p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => removeProfile(profileKey)}
                  className="action-button action-button-ghost"
                >
                  <Trash2 className="h-4 w-4" />
                  Remove
                </button>
              </div>

              <div className="panel-body space-y-5">
                <div className="grid gap-5 xl:grid-cols-[1fr_0.95fr]">
                  <label className="min-w-0 space-y-2">
                    <span className="text-sm font-semibold text-horizon-text">Profile Label</span>
                    <input
                      className="input-base"
                      value={profile.label}
                      onChange={(event) => updateProfileField(profileKey, "label", event.target.value)}
                    />
                  </label>
                  <div className="field-shell">
                    <p className="field-label">Selected Resume</p>
                    <p className="field-value text-base font-semibold">{resumeName || "Not found"}</p>
                  </div>
                </div>

                <div className="grid gap-4 md:grid-cols-3">
                  <div className="field-shell">
                    <p className="field-label">Resume File</p>
                    <p className="field-value">{resumeName || "Not found"}</p>
                  </div>
                  <div className="field-shell">
                    <p className="field-label">Exists</p>
                    <p className="field-value">{inventory?.exists ? "Yes" : "No"}</p>
                  </div>
                  <div className="field-shell">
                    <p className="field-label">Size</p>
                    <p className="field-value">{formatBytes(inventory?.size_bytes || 0)}</p>
                  </div>
                </div>

                <label className="min-w-0 space-y-2">
                  <span className="text-sm font-semibold text-horizon-text">Summary</span>
                  <textarea
                    className="textarea-base"
                    value={profile.summary}
                    onChange={(event) => updateProfileField(profileKey, "summary", event.target.value)}
                  />
                </label>

                <div className="grid gap-5 xl:grid-cols-2">
                  <label className="min-w-0 space-y-2">
                    <span className="text-sm font-semibold text-horizon-text">Title Keywords</span>
                    <textarea
                      className="textarea-base"
                      value={toMultiline(profile.title_keywords)}
                      onChange={(event) =>
                        updateProfileField(
                          profileKey,
                          "title_keywords",
                          parseMultiline(event.target.value)
                        )
                      }
                    />
                  </label>
                  <label className="min-w-0 space-y-2">
                    <span className="text-sm font-semibold text-horizon-text">
                      Description Keywords
                    </span>
                    <textarea
                      className="textarea-base"
                      value={toMultiline(profile.description_keywords)}
                      onChange={(event) =>
                        updateProfileField(
                          profileKey,
                          "description_keywords",
                          parseMultiline(event.target.value)
                        )
                      }
                    />
                  </label>
                </div>
              </div>
            </section>
          );
        })}
      </div>
    </div>
  );
}

function fileNameFromPath(value: string) {
  return value.split(/[/\\]/).filter(Boolean).pop() || value;
}

function humanizeFileName(value: string) {
  return value.replace(/\.pdf$/i, "").replace(/[_-]+/g, " ").trim();
}
