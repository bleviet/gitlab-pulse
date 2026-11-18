import { useMemo, useState } from "react";
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  type ColumnDef,
  type SortingState,
  useReactTable,
} from "@tanstack/react-table";
import { ArrowDown, ArrowUp, ArrowUpDown } from "lucide-react";
import { sortIssuesDefault, sortIssuesHierarchy, type HierarchyRow } from "../lib/board";
import { getPriorityColor, hexWithAlpha } from "../lib/colors";
import type { IssueFacets, IssueItem, LabelStyle, ThemeMode } from "../lib/types";

interface IssueTableProps {
  issues: IssueItem[];
  facets: IssueFacets;
  labelStyles: Record<string, LabelStyle>;
  palette: Record<string, string>;
  priorityOrder: string[];
  theme: ThemeMode;
  pageStart: number;
  pageStop: number;
}

const columnHelper = createColumnHelper<HierarchyRow>();

export function IssueTable({
  issues,
  facets,
  labelStyles,
  palette,
  priorityOrder,
  theme,
  pageStart,
  pageStop,
}: IssueTableProps) {
  const [sorting, setSorting] = useState<SortingState>([]);

  const data = useMemo(
    () => sortIssuesHierarchy(sortIssuesDefault(issues)),
    [issues],
  );

  const hasAnyContexts = useMemo(
    () => issues.some((issue) => issue.contexts.length > 0),
    [issues],
  );

  const columns = useMemo(() => {
    const showHierarchyIndent = sorting.length === 0;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const cols: ColumnDef<HierarchyRow, any>[] = [
      columnHelper.accessor((row) => row.issue.title, {
        id: "title",
        header: "Title",
        cell: (info) => {
          const { issue, depth } = info.row.original;
          const indentPx = showHierarchyIndent && depth > 0 ? depth * 18 : 0;
          const linkText = `#${issue.iid} - ${issue.title}`;
          return (
            <div style={{ paddingLeft: `${indentPx}px`, minWidth: "240px" }}>
              {showHierarchyIndent && depth > 0 && (
                <span style={{ color: "var(--muted)", marginRight: "0.3rem" }} aria-hidden="true">
                  ↳
                </span>
              )}
              {issue.web_url ? (
                <a
                  href={issue.web_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="issue-link"
                >
                  {linkText}
                </a>
              ) : (
                <span style={{ fontWeight: 600, color: "var(--heading)" }}>{linkText}</span>
              )}
            </div>
          );
        },
      }),
    ];

    if (hasAnyContexts) {
      cols.push(
        columnHelper.accessor((row) => row.issue.contexts.join(", "), {
          id: "context",
          header: "Context",
          cell: (info) => {
            const contexts = info.row.original.issue.contexts;
            if (contexts.length === 0) return null;
            return (
              <div style={{ display: "flex", flexWrap: "wrap", gap: "2px" }}>
                {contexts.map((ctx) => {
                  const style = labelStyles[ctx];
                  return (
                    <span
                      key={ctx}
                      className="context-pill"
                      style={
                        style
                          ? {
                              backgroundColor: style.color,
                              color: style.text_color,
                              borderColor: "transparent",
                            }
                          : { backgroundColor: "var(--surface)", color: "var(--text)" }
                      }
                    >
                      {ctx}
                    </span>
                  );
                })}
              </div>
            );
          },
        }),
      );
    }

    if (!facets.stage) {
      cols.push(
        columnHelper.accessor((row) => row.issue.stage, {
          id: "stage",
          header: "Stage",
          cell: (info) => <span style={{ whiteSpace: "nowrap" }}>{info.getValue()}</span>,
        }),
      );
    }

    cols.push(
      columnHelper.accessor((row) => row.issue.priority || "Unset", {
        id: "priority",
        header: "Priority",
        sortingFn: (rowA, rowB) => {
          const rankA = rowA.original.issue.priority_rank ?? Number.MAX_SAFE_INTEGER;
          const rankB = rowB.original.issue.priority_rank ?? Number.MAX_SAFE_INTEGER;
          if (rankA !== rankB) return rankA - rankB;
          return (rowA.original.issue.priority || "Unset").localeCompare(
            rowB.original.issue.priority || "Unset",
          );
        },
        cell: (info) => {
          const prio = info.getValue();
          const color = getPriorityColor(prio, palette, priorityOrder, theme);
          return (
            <span
              className="prio-badge"
              style={{
                backgroundColor: hexWithAlpha(color, 0.16),
                color,
              }}
            >
              {prio}
            </span>
          );
        },
      }),
      columnHelper.accessor((row) => row.issue.days_in_stage, {
        id: "days_in_stage",
        header: "In stage",
        cell: (info) => {
          const stale = info.row.original.issue.is_stale;
          return (
            <span
              style={{
                fontFamily: "var(--font-mono)",
                whiteSpace: "nowrap",
                color: stale ? "var(--node-pink)" : "var(--text)",
                fontWeight: stale ? 700 : 400,
              }}
            >
              {info.getValue()} d
            </span>
          );
        },
      }),
      columnHelper.accessor((row) => row.issue.milestone ?? "", {
        id: "milestone",
        header: "Milestone",
        cell: (info) => (
          <span style={{ whiteSpace: "nowrap", color: info.getValue() ? "var(--text)" : "var(--muted)" }}>
            {info.getValue() || "—"}
          </span>
        ),
      }),
      columnHelper.accessor((row) => row.issue.assignee, {
        id: "assignee",
        header: "Assignee",
        cell: (info) => (
          <span
            style={{
              whiteSpace: "nowrap",
              color: info.getValue() === "Unassigned" ? "var(--muted)" : "var(--text)",
            }}
          >
            {info.getValue()}
          </span>
        ),
      }),
      columnHelper.accessor((row) => row.issue.quality_hints.join(" | "), {
        id: "quality_hints",
        header: "Quality hints",
        cell: (info) => (
          <span style={{ color: "var(--gold)", fontSize: "0.78rem" }}>{info.getValue()}</span>
        ),
      }),
    );

    return cols;
  }, [facets.stage, hasAnyContexts, labelStyles, palette, priorityOrder, sorting.length, theme]);

  const table = useReactTable({
    data,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  const allRows = table.getRowModel().rows;
  const pageRows = allRows.slice(pageStart, pageStop);
  const showQualityHints = pageRows.some((row) => row.original.issue.quality_hints.length > 0);

  if (issues.length === 0) {
    return (
      <div style={{ padding: "1.5rem", textAlign: "center", color: "var(--muted)" }}>
        No matching issues.
      </div>
    );
  }

  return (
    <div className="issue-table-wrap">
      <table className="issue-table">
        <thead>
          {table.getHeaderGroups().map((headerGroup) => (
            <tr key={headerGroup.id}>
              {headerGroup.headers.map((header) => {
                if (header.column.id === "quality_hints" && !showQualityHints) {
                  return null;
                }
                const sorted = header.column.getIsSorted();
                return (
                  <th key={header.id}>
                    <button
                      type="button"
                      className="sort-header"
                      onClick={header.column.getToggleSortingHandler()}
                    >
                      <span>{flexRender(header.column.columnDef.header, header.getContext())}</span>
                      {sorted === "asc" ? (
                        <ArrowUp size={12} />
                      ) : sorted === "desc" ? (
                        <ArrowDown size={12} />
                      ) : (
                        <ArrowUpDown size={12} opacity={0.45} />
                      )}
                    </button>
                  </th>
                );
              })}
            </tr>
          ))}
        </thead>
        <tbody>
          {pageRows.map((row) => (
            <tr key={row.original.issue.id}>
              {row.getVisibleCells().map((cell) => {
                if (cell.column.id === "quality_hints" && !showQualityHints) {
                  return null;
                }
                return <td key={cell.id}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</td>;
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
