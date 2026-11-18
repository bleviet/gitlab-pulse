import { BarChart3, KanbanSquare, Moon, PanelLeft, Shield, Sun } from "lucide-react";
import type { OverviewLayout, ThemeMode } from "../lib/types";

interface TopBarProps {
  layout: OverviewLayout;
  theme: ThemeMode;
  activeSidebarCount: number;
  isAdmin: boolean;
  onToggleSidebar: () => void;
  onChangeLayout: (layout: OverviewLayout) => void;
  onToggleTheme: () => void;
  onOpenAdmin: () => void;
}

export function TopBar({
  layout,
  theme,
  activeSidebarCount,
  isAdmin,
  onToggleSidebar,
  onChangeLayout,
  onToggleTheme,
  onOpenAdmin,
}: TopBarProps) {
  return (
    <header className="pulse-topbar">
      <div className="pulse-topbar-left">
        <button
          type="button"
          className="pulse-icon-btn"
          aria-label="Toggle filters sidebar"
          onClick={onToggleSidebar}
        >
          <PanelLeft size={16} />
          <span>Filters</span>
          {activeSidebarCount > 0 && <span className="pulse-badge">{activeSidebarCount}</span>}
        </button>

        <div className="pulse-brand">
          <img
            src="/static/logo.svg"
            alt=""
            width={28}
            height={28}
            style={{ borderRadius: "7px", display: "block" }}
          />
          <span className="pulse-brand-title">
            <span className="pulse-brand-accent">GitLab</span>Pulse
          </span>
        </div>
      </div>

      <div className="pulse-topbar-right">
        <div className="pulse-segmented" role="group" aria-label="Overview layout">
          <button
            type="button"
            aria-pressed={layout === "analytics"}
            onClick={() => onChangeLayout("analytics")}
          >
            <BarChart3 size={14} />
            <span>Analytics</span>
          </button>
          <button
            type="button"
            aria-pressed={layout === "compact"}
            onClick={() => onChangeLayout("compact")}
          >
            <KanbanSquare size={14} />
            <span>Compact</span>
          </button>
        </div>

        <button
          type="button"
          className="pulse-icon-btn"
          aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}
          onClick={onToggleTheme}
          title={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}
        >
          {theme === "dark" ? <Sun size={15} /> : <Moon size={15} />}
        </button>

        <button
          type="button"
          className="pulse-icon-btn"
          aria-label="Open admin operations"
          onClick={onOpenAdmin}
          title="Admin operations"
        >
          <Shield size={15} color={isAdmin ? "var(--accent)" : undefined} />
          <span>{isAdmin ? "Admin" : "Ops"}</span>
        </button>
      </div>
    </header>
  );
}
