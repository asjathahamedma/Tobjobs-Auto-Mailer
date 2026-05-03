import { ResumeProfilesManager } from "@/components/profiles/ResumeProfilesManager";
import type { AppConfig, ResumeInventoryItem } from "@/lib/types";

interface ProfilesPageProps {
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

export function ProfilesPage(props: ProfilesPageProps) {
  return (
    <ResumeProfilesManager
      title="Resume Profiles"
      subtitle="Import a resume first, review the detected profile details, edit anything you want, then add or cancel."
      {...props}
    />
  );
}
