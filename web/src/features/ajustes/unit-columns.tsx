import type { DataTableColumnDef } from "@/components/domain/data-table-features";
import { formatNumber } from "@/lib/format";
import type { Unit } from "@/types/api";

const FACTOR_DECIMALS = 6;

/** Catalog units: the explicit factor that converts each one to its dimension's canonical unit. */
export function createUnitColumns(): DataTableColumnDef<Unit>[] {
  return [
    {
      accessorKey: "code",
      header: "Código",
      cell: ({ row }) => <span className="font-mono text-xs">{row.original.code}</span>,
    },
    {
      accessorKey: "nameEs",
      header: "Nombre",
      cell: ({ row }) => <span className="text-xs">{row.original.nameEs}</span>,
    },
    {
      accessorKey: "dimension",
      header: "Dimensión",
      cell: ({ row }) => (
        <span className="text-xs text-muted-foreground">{row.original.dimension}</span>
      ),
    },
    {
      accessorKey: "factorToCanonical",
      header: "Factor a la canónica",
      cell: ({ row }) => (
        <span className="block text-right font-mono tabular-nums">
          {formatNumber(row.original.factorToCanonical, FACTOR_DECIMALS)}
        </span>
      ),
    },
  ];
}
