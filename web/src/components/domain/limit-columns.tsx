import type { DataTableColumnDef } from "@/components/domain/data-table-features";
import { LimitBadge } from "@/components/domain/LimitBadge";
import { formatNumber } from "@/lib/format";
import type { CatalogLimit, Parameter } from "@/types/api";

const DEFAULT_DECIMALS = 2;

/** Readable names for the `statistic` codes the catalog uses; unknown codes stay as they are. */
const STATISTIC_LABELS: Record<string, string> = {
  max_absolute: "Máximo",
  min_absolute: "Mínimo",
  P5_P95: "P5–P95",
};

/**
 * Columns of the limits tables (Screening and Ajustes): parameter, regulation, how the norm
 * evaluates it, the range, the unit and the validation state.
 *
 * `min`/`max` are formatted with the decimals of their parameter, taken from the catalog; a side
 * the regulation does not constrain stays as an em dash instead of a zero.
 */
export function createLimitColumns(parameters: Parameter[]): DataTableColumnDef<CatalogLimit>[] {
  const decimalsByCode = new Map(parameters.map((parameter) => [parameter.code, parameter.decimals]));

  const decimalsFor = (parameterCode: string) =>
    decimalsByCode.get(parameterCode) ?? DEFAULT_DECIMALS;

  const bound = (value: number | null, parameterCode: string) =>
    value === null ? (
      <span className="block text-right text-muted-foreground">—</span>
    ) : (
      <span className="block text-right font-mono tabular-nums">
        {formatNumber(value, decimalsFor(parameterCode))}
      </span>
    );

  return [
    {
      accessorKey: "parameterCode",
      header: "Parámetro",
      cell: ({ row }) => <span className="font-mono text-xs">{row.original.parameterCode}</span>,
    },
    {
      accessorKey: "regulationCode",
      header: "Regulación",
      cell: ({ row }) => <span className="text-xs">{row.original.regulationCode}</span>,
    },
    {
      accessorKey: "statistic",
      header: "Estadístico",
      cell: ({ row }) => (
        <span className="text-xs">
          {STATISTIC_LABELS[row.original.statistic] ?? row.original.statistic}
        </span>
      ),
    },
    {
      id: "min",
      accessorFn: (row) => row.min ?? Number.NEGATIVE_INFINITY,
      header: "Mín.",
      cell: ({ row }) => bound(row.original.min, row.original.parameterCode),
    },
    {
      id: "max",
      accessorFn: (row) => row.max ?? Number.NEGATIVE_INFINITY,
      header: "Máx.",
      cell: ({ row }) => bound(row.original.max, row.original.parameterCode),
    },
    {
      accessorKey: "unitCode",
      header: "Unidad",
      cell: ({ row }) => <span className="font-mono text-xs">{row.original.unitCode}</span>,
    },
    {
      accessorKey: "status",
      header: "Estado",
      cell: ({ row }) => <LimitBadge status={row.original.status} />,
    },
  ];
}
