import type { DataTableColumnDef } from "@/components/domain/data-table-features";
import { LimitBadge } from "@/components/domain/LimitBadge";
import type { Parameter } from "@/types/api";

/**
 * Read-only catalog parameters: what the UI can plot, in which canonical unit and with how many
 * decimals. `status` travels with each row because a `draft-verified` parameter is still pending
 * the chemist's signature.
 */
export function createParameterColumns(): DataTableColumnDef<Parameter>[] {
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
      accessorKey: "category",
      header: "Categoría",
      cell: ({ row }) => <span className="text-xs text-muted-foreground">{row.original.category}</span>,
    },
    {
      accessorKey: "canonicalUnitCode",
      header: "Unidad canónica",
      cell: ({ row }) => <span className="font-mono text-xs">{row.original.canonicalUnitCode}</span>,
    },
    {
      accessorKey: "decimals",
      header: "Decimales",
      cell: ({ row }) => (
        <span className="block text-right font-mono tabular-nums">{row.original.decimals}</span>
      ),
    },
    {
      accessorKey: "measurementType",
      header: "Tipo de medición",
      cell: ({ row }) => (
        <span className="text-xs text-muted-foreground">{row.original.measurementType}</span>
      ),
    },
    {
      accessorKey: "status",
      header: "Estado",
      cell: ({ row }) => <LimitBadge status={row.original.status} />,
    },
  ];
}
