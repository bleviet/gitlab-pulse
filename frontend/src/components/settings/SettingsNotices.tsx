import { Lock } from "lucide-react";
import type { AdminJobResponse } from "../../lib/types";
import { UnlockForm } from "./UnlockForm";

export interface Notice {
  kind: "success" | "warning" | "error" | "conflict";
  text: string;
  job?: AdminJobResponse;
}

interface SettingsNoticesProps {
  loadErrorNotice: string | null;
  showUnlockBanner: boolean;
  unlockOpen: boolean;
  onOpenUnlock: () => void;
  onLogin: (password: string) => Promise<void>;
  onUnlocked: () => void;
  notice: Notice | null;
  onReloadLatest: () => void;
  unplacedProblems: string[];
}

export function SettingsNotices({
  loadErrorNotice,
  showUnlockBanner,
  unlockOpen,
  onOpenUnlock,
  onLogin,
  onUnlocked,
  notice,
  onReloadLatest,
  unplacedProblems,
}: SettingsNoticesProps) {
  return (
    <>
      {loadErrorNotice && (
        <div className="settings-notice warning" role="status">
          {loadErrorNotice}
        </div>
      )}

      {showUnlockBanner && (
        <div className="settings-notice info">
          <div className="settings-notice-row">
            <Lock size={14} aria-hidden="true" />
            <strong>View only</strong>
            <span>You can look at the rules, but editing needs the admin password.</span>
            {!unlockOpen && (
              <button type="button" className="pulse-btn-secondary" onClick={onOpenUnlock}>
                Unlock editing
              </button>
            )}
          </div>
          {unlockOpen && <UnlockForm onLogin={onLogin} onDone={onUnlocked} />}
        </div>
      )}

      {notice && (
        <div
          className={`settings-notice ${notice.kind === "success" ? "success" : notice.kind === "error" ? "error" : "warning"}`}
          role={notice.kind === "success" ? "status" : "alert"}
        >
          <div className="settings-notice-row">
            <span>{notice.text}</span>
            {notice.kind === "conflict" && (
              <button type="button" className="pulse-btn-secondary" onClick={onReloadLatest}>
                Reload latest
              </button>
            )}
          </div>
          {notice.job?.stdout && <pre className="admin-log">{notice.job.stdout}</pre>}
          {notice.job?.stderr && <pre className="admin-log">{notice.job.stderr}</pre>}
        </div>
      )}

      {unplacedProblems.length > 0 && (
        <div className="settings-notice error" role="alert">
          <strong>These rules have problems that cannot be fixed on this screen:</strong>
          <ul className="settings-problem-list">
            {unplacedProblems.map((text, i) => (
              <li key={i}>{text}</li>
            ))}
          </ul>
          <span>Ask the person who maintains the rule files to correct them.</span>
        </div>
      )}
    </>
  );
}
