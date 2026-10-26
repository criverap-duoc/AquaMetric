import type { DataTableColumnDef } from "@/components/domain/data-table-features";
import { QcFlagBadge } from "@/components/domain/QcFlagBadge";
import { formatDateTime, formatNumber } from "@/lib/format";
import type { ObservationRead, ObservationSource } from "@/types/api";

const SOURCE_LABELS: Record<ObservationSource, string> = {
  lab: "Laboratorio",
  field: "Terreno",
  sensor: "Sensor",
};

/**
 * Columns of the observation table (design-system §6.5): dates in mono, values right-aligned
 * with the decimals of the catalog, quality flag as a badge with icon and text.
 */
export function createObservationColumns(
  unitCode: string,
  decimals: number,
): DataTableColumnDef<ObservationRead>[] {
  return [
    {
      accessorKey: "analyzedAt",
      header: "Fecha y hora",
      cell: ({ row }) => (
        <span className="font-mono tabular-nums">{formatDateTime(row.original.analyzedAt)}</span>
      ),
    },
    {
      id: "value",
      accessorFn: (observation) => observation.value ?? Number.NEGATIVE_INFINITY,
      header: `Valor (${unitCode})`,
      cell: ({ row }) => {
        const { value, loq } = row.original;

        if (value === null) {
          // Censored result: the operator stays visible, the value is never invented.
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
      accessorKey: "qcFlag",
      header: "Calidad",
      cell: ({ row }) => <QcFlagBadge flag={row.original.qcFlag} />,
    },
    {
      accessorKey: "source",
      header: "Fuente",
      cell: ({ row }) => SOURCE_LABELS[row.original.source],
    },
  ];
}
