export interface IssueItem {
  id: number;
  iid: number;
  project_id: number;
  title: string;
  state: "opened" | "closed";
  created_at: string;
  updated_at: string;
  closed_at: string | null;
  labels: string[];
  contexts: string[];
  work_item_type: string;
  parent_id: number | null;
  child_ids: number[];
  web_url: string | null;
  assignee: string;
  milestone: string | null;
  milestone_id: number | null;
  milestone_due_date: string | null;
  milestone_start_date: string | null;
  age_days: number;
  cycle_time: number | null;
  is_stale: boolean;
  issue_type: string | null;
  severity: string | null;
  priority: string;
  priority_rank: number | null;
  team: string | null;
  stage: string;
  stage_type: string | null;
  stage_order: number;
  days_in_stage: number;
  quality_signals: string[];
  quality_hints: string[];
}

export interface LabelStyle {
  color: string;
  text_color: string;
}

export interface StageMeta {
  name: string;
  type: string;
  description: string;
}

export interface ThemePalettes {
  light: Record<string, string>;
  dark: Record<string, string>;
  priority_order: string[];
}

export interface SyncStatus {
  status: string;
  last_sync: string;
}

export interface FilterOptions {
  teams: string[];
  contexts: string[];
  milestones: string[];
  min_date: string | null;
  max_date: string | null;
}

export interface DashboardPayload {
  issues: IssueItem[];
  filter_options: FilterOptions;
  label_styles: Record<string, LabelStyle>;
  stages: StageMeta[];
  palettes: ThemePalettes;
  sync_status: SyncStatus;
  version: string;
  generated_at: string;
}

export interface AdminStatusResponse {
  authenticated: boolean;
}

export interface AdminJobResponse {
  step: string;
  returncode: number;
  stdout: string;
  stderr: string;
  success: boolean;
}

export type IssueViewMode = "table" | "board";
export type ThemeMode = "dark" | "light";
export type TimePreset = "30d" | "90d" | "1y" | "all" | "custom";

export interface GlobalFilters {
  team: string;
  context: string;
  milestone: string;
  startDate: string;
  endDate: string;
  preset: TimePreset;
}

export interface IssueFacets {
  stage?: string;
  state?: "opened" | "closed" | "all";
  priority?: string;
  issue_type?: string;
  signal?: string;
  recent?: "created" | "closed";
  day?: string;
  day_kind?: "created" | "closed";
  query?: string;
}

export type ActiveChartId =
  | "open_donut"
  | "type_donut"
  | "quality_signal_chart"
  | "velocity_chart"
  | `stage_bar_${number}`
  | null;
