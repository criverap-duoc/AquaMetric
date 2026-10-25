import type { DataTableColumnDef } from "@/components/domain/data-table-features";
import { Badge } from "@/components/ui/badge";
import { formatDateTime } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { BatchSummary } from "@/types/api";

/**
 * Columns of the ingest log: the idempotency key, when it arrived, how it ended and how many rows
 * it wrote or skipped. `duplicates` is not a failure — it is the natural key doing its job
 * (ADR-009).
 */
export function createBatchColumns(): DataTableColumnDef<BatchSummary>[] {
  return [
    {
      accessorKey: "key",
      header: "Idempotency-Key",
      cell: ({ row }) => (
        <span className="font-mono text-xs text-muted-foreground">
          {row.original.key.slice(0, 16)}…
        </span>
      ),
    },
    {
      accessorKey: "receivedAt",
      header: "Recibido",
      cell: ({ row }) => (
        <span className="font-mono tabular-nums">{formatDateTime(row.original.receivedAt)}</span>
      ),
    },
    {
      accessorKey: "status",
      header: "Estado",
      cell: ({ row }) => (
        <Badge
          className={cn(
            "rounded-sm",
            row.original.status === "success"
              ? "bg-success-soft text-success-soft-foreground"
              : "bg-destructive-soft text-destructive-soft-foreground",
          )}
        >
          {row.original.status === "success" ? "Aceptado" : "Fallido"}
        </Badge>
      ),
    },
    {
      accessorKey: "accepted",
      header: "Aceptadas",
      cell: ({ row }) => (
        <span className="block text-right font-mono tabular-nums">{row.original.accepted}</span>
      ),
    },
    {
      accessorKey: "duplicates",
      header: "Duplicadas",
      cell: ({ row }) => (
        <span className="block text-right font-mono tabular-nums text-muted-foreground">
          {row.original.duplicates}
        </span>
      ),
    },
  ];
}
