import type { DataTableColumnDef } from "@/components/domain/data-table-features";
import { QcFlagBadge } from "@/components/domain/QcFlagBadge";
import type { ChartRow } from "@/features/control/chart-rows";
import { formatDateTime, formatNumber } from "@/lib/format";

/**
 * Columns of the tabular alternative of the control chart (04 §2.8): sequence, instant, value,
 * moving range, quality flag and the signal of the point. Censored values keep the operator and
 * never become a zero.
 */
export function createControlColumns(
  unitCode: string,
  decimals: number,
): DataTableColumnDef<ChartRow>[] {
  return [
    {
      accessorKey: "index",
      header: "#",
      cell: ({ row }) => (
        <span className="font-mono tabular-nums text-muted-foreground">
          {row.original.index + 1}
        </span>
      ),
    },
    {
      accessorKey: "analyzedAt",
      header: "Fecha y hora",
      cell: ({ row }) => (
        <span className="font-mono tabular-nums">{formatDateTime(row.original.analyzedAt)}</span>
      ),
    },
    {
      id: "value",
      accessorFn: (row) => row.value ?? Number.NEGATIVE_INFINITY,
      header: `Valor (${unitCode})`,
      cell: ({ row }) => {
        const { value, loq } = row.original;

        if (value === null) {
          return (
            <span className="block text-right font-mono tabular-nums text-muted-foreground">
              {loq === null ? "—" : `< ${formatNumber(loq, decimals)}`}
            </span>
          );
        }

        return (
          <span className="block text-right font-mono tabular-nums">
            {formatNumber(value, decimals)}
          </span>
        );
      },
    },
    {
      id: "movingRange",
      accessorFn: (row) => row.movingRange ?? Number.NEGATIVE_INFINITY,
      header: `MR (${unitCode})`,
      cell: ({ row }) => (
        <span className="block text-right font-mono tabular-nums text-muted-foreground">
          {row.original.movingRange === null
            ? "—"
            : formatNumber(row.original.movingRange, decimals)}
        </span>
      ),
    },
    {
      accessorKey: "qcFlag",
      header: "Calidad",
      cell: ({ row }) => <QcFlagBadge flag={row.original.qcFlag} />,
    },
    {
      accessorKey: "signal",
      header: "Señal",
      cell: ({ row }) => (
        <span className="font-mono text-xs">{row.original.signal ?? "—"}</span>
      ),
    },
  ];
}
