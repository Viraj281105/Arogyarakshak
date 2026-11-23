"use client";

import React, { useId, useMemo, useState } from "react";
import ArrowUpDown from "lucide-react/icons/arrow-up-down";
import ChevronDown from "lucide-react/icons/chevron-down";
import ChevronUp from "lucide-react/icons/chevron-up";

export type SortDir = "ascending" | "descending";

export interface Column<Row> {
  key: string;
  header: string;
  /** Cell content; defaults to String(row[key]). */
  cell?: (row: Row) => React.ReactNode;
  /** Present = sortable. Numbers sort numerically, strings with the locale collator. */
  sortValue?: (row: Row) => number | string | null;
  /** Right-align figures (and use tabular numerals). */
  numeric?: boolean;
}

const collator = new Intl.Collator("en-IN", { numeric: true, sensitivity: "base" });

/** Pure, stable sort used by DataTable. Nulls always go last, whatever the direction. */
export function sortRows<Row>(rows: readonly Row[], value: (row: Row) => number | string | null, dir: SortDir): Row[] {
  const sign = dir === "ascending" ? 1 : -1;
  return rows
    .map((row, i) => ({ row, i, v: value(row) }))
    .sort((a, b) => {
      if (a.v === null && b.v === null) return a.i - b.i;
      if (a.v === null) return 1;
      if (b.v === null) return -1;
      const c = typeof a.v === "number" && typeof b.v === "number" ? a.v - b.v : collator.compare(String(a.v), String(b.v));
      return c === 0 ? a.i - b.i : sign * c;
    })
    .map((x) => x.row);
}

/**
 * Accessible data table: a real <table> with a caption, sortable columns as buttons inside the
 * header cells (aria-sort on the <th>), and a focusable scroll region so wide tables scroll
 * sideways inside their container on phones instead of the page.
 */
export function DataTable<Row>({
  caption,
  columns,
  rows,
  rowKey,
  initialSort,
  empty = "No rows.",
}: {
  caption: string;
  columns: readonly Column<Row>[];
  rows: readonly Row[];
  rowKey: (row: Row) => string;
  initialSort?: { key: string; dir: SortDir };
  empty?: string;
}) {
  const id = useId();
  const [sort, setSort] = useState(initialSort ?? null);
  const sorted = useMemo(() => {
    const col = sort && columns.find((c) => c.key === sort.key);
    return sort && col?.sortValue ? sortRows(rows, col.sortValue, sort.dir) : [...rows];
  }, [rows, columns, sort]);

  const toggle = (key: string) =>
    setSort((s) => (s?.key === key ? { key, dir: s.dir === "ascending" ? "descending" : "ascending" } : { key, dir: "ascending" }));

  return (
    <div className="ui-table-scroll" role="region" aria-labelledby={`${id}-cap`} tabIndex={0}>
      <table className="ui-table">
        <caption id={`${id}-cap`}>{caption}</caption>
        <thead>
          <tr>
            {columns.map((c) => {
              const active = sort?.key === c.key;
              return (
                <th key={c.key} scope="col" aria-sort={active ? sort.dir : c.sortValue ? "none" : undefined} className={c.numeric ? "is-num" : undefined}>
                  {c.sortValue ? (
                    <button type="button" className="ui-sort" onClick={() => toggle(c.key)}>
                      {c.header}
                      {active ? (
                        sort.dir === "ascending" ? <ChevronUp size={14} aria-hidden="true" /> : <ChevronDown size={14} aria-hidden="true" />
                      ) : (
                        <ArrowUpDown size={14} aria-hidden="true" className="ui-sort-idle" />
                      )}
                    </button>
                  ) : (
                    c.header
                  )}
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {sorted.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="ui-table-empty">
                {empty}
              </td>
            </tr>
          ) : (
            sorted.map((row) => (
              <tr key={rowKey(row)}>
                {columns.map((c) => (
                  <td key={c.key} className={c.numeric ? "is-num code-tabular" : undefined}>
                    {c.cell ? c.cell(row) : String((row as Record<string, unknown>)[c.key] ?? "")}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
