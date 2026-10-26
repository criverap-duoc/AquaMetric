import { flexRender, useTable, type RowData } from "@tanstack/react-table";
import {
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ChevronUp,
  ChevronsUpDown,
  Inbox,
} from "lucide-react";

import {
  DATA_TABLE_FEATURES,
  type DataTableColumnDef,
} from "@/components/domain/data-table-features";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

const PAGE_SIZES = [25, 50, 100] as const;

/**
 * Row ceiling of the internal paginator when the server paginates.
 *
 * The table keeps its own pagination state (sorting lives in the row model), so the size has to
 * be large enough to hold a whole server page in a single internal page; otherwise the last rows
 * of the response would be silently hidden. It matches the largest page size the API accepts.
 */
const SERVER_PAGE_SIZE_CAP = 1000;

const SKELETON_ROWS = 10;

/**
 * Server-side pagination: the table renders exactly the rows it received and the footer talks to
 * the caller instead of slicing `data`.
 *
 * Necessary because `meta.total` counts every row that matches the filter, not the loaded page:
 * a client-side footer would print «mostrando 1–50 de 50» over a series of 1400 observations.
 * Sorting still applies to the loaded page only, which is the usual trade-off of a paginated API.
 */
export interface ServerPagination {
  /** Page that is loaded, from 1. */
  page: number;
  pageSize: number;
  /** Rows that match the filter on the server, across every page. */
  total: number;
  pageSizeOptions?: readonly number[];
  onPageChange: (page: number) => void;
  onPageSizeChange: (pageSize: number) => void;
}

export interface DataTableProps<TData extends RowData> {
  columns: DataTableColumnDef<TData>[];
  data: TData[];
  /** Rows per page at mount; the user can switch to 25/50/100 afterwards. */
  pageSize?: number;
  emptyMessage?: string;
  isLoading?: boolean;
  /** Accessible name of the table (`<caption>`): what the table lists. */
  caption: string;
  /** Set it to hand the pagination to the API instead of slicing `data` in the browser. */
  serverPagination?: ServerPagination;
}

function ariaSortValue(sorted: false | "asc" | "desc") {
  if (sorted === "asc") {
    return "ascending" as const;
  }

  if (sorted === "desc") {
    return "descending" as const;
  }

  return "none" as const;
}

function SortIcon({ sorted }: { sorted: false | "asc" | "desc" }) {
  if (sorted === "asc") {
    return <ChevronUp aria-hidden="true" className="size-3.5" />;
  }

  if (sorted === "desc") {
    return <ChevronDown aria-hidden="true" className="size-3.5" />;
  }

  return <ChevronsUpDown aria-hidden="true" className="size-3.5 text-muted-foreground" />;
}


/**
 * Dense data table (design-system §6.5): sticky header, sortable columns, 36 px rows and a
 * client-side page selector. No virtualization: demo volumes are small.
 */
export function DataTable<TData extends RowData>({
  columns,
  data,
  pageSize = 50,
  emptyMessage = "Sin datos para mostrar.",
  isLoading = false,
  caption,
  serverPagination,
}: DataTableProps<TData>) {
  const isServerPaginated = serverPagination !== undefined;
  const table = useTable({
    features: DATA_TABLE_FEATURES,
    columns,
    data,
    initialState: {
      pagination: {
        pageIndex: 0,
        pageSize: isServerPaginated ? SERVER_PAGE_SIZE_CAP : pageSize,
      },
    },
  });

  if (isLoading) {
    return (
      <div className="space-y-2" aria-busy="true">
        <Skeleton className="h-10 w-full" />
        {Array.from({ length: SKELETON_ROWS }, (_, index) => (
          <Skeleton key={index} className="h-10 w-full" />
        ))}
        <span className="sr-only">Cargando tabla…</span>
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="flex flex-col items-center gap-2 rounded-md border border-dashed border-border px-4 py-10 text-center">
        <Inbox aria-hidden="true" className="size-6 text-muted-foreground" />
        <p className="text-sm font-medium">{emptyMessage}</p>
        <p className="max-w-sm text-xs text-muted-foreground">
          Prueba ampliando el rango de fechas o cambiando de sitio o de parámetro.
        </p>
      </div>
    );
  }

  const { pageIndex, pageSize: currentPageSize } = table.state.pagination;
  // With server pagination the footer describes the API page, not the rows in memory.
  const total = serverPagination?.total ?? data.length;
  const pageNumber = serverPagination?.page ?? pageIndex + 1;
  const rowsPerPage = serverPagination?.pageSize ?? currentPageSize;
  const firstRow = total === 0 ? 0 : (pageNumber - 1) * rowsPerPage + 1;
  const lastRow = Math.min(total, pageNumber * rowsPerPage);
  const pageSizeOptions = serverPagination?.pageSizeOptions ?? PAGE_SIZES;
  const canGoBack = serverPagination ? pageNumber > 1 : table.getCanPreviousPage();
  const canGoForward = serverPagination
    ? pageNumber * rowsPerPage < total
    : table.getCanNextPage();

  return (
    <div className="flex flex-col gap-2">
      <div className="max-h-[28rem] overflow-y-auto rounded-md border border-border">
        <Table className="text-xs">
          <caption className="sr-only">{caption}</caption>
          <TableHeader className="sticky top-0 z-10 bg-card">
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id} className="hover:bg-transparent">
                {headerGroup.headers.map((header) => {
                  const canSort = header.column.getCanSort();
                  const sorted = header.column.getIsSorted();
                  const headerLabel = flexRender(
                    header.column.columnDef.header,
                    header.getContext(),
                  );

                  return (
                    <TableHead
                      key={header.id}
                      aria-sort={canSort ? ariaSortValue(sorted) : undefined}
                      className="h-9 text-xs font-medium uppercase tracking-wide text-muted-foreground"
                    >
                      {header.isPlaceholder ? null : canSort ? (
                        <button
                          type="button"
                          onClick={header.column.getToggleSortingHandler()}
                          className="flex items-center gap-1 rounded-sm transition-colors hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:outline-none"
                        >
                          {headerLabel}
                          <SortIcon sorted={sorted} />
                        </button>
                      ) : (
                        headerLabel
                      )}
                    </TableHead>
                  );
                })}
              </TableRow>
            ))}
          </TableHeader>

          <TableBody>
            {table.getRowModel().rows.map((row) => (
              <TableRow key={row.id} className="h-9">
                {row.getAllCells().map((cell) => (
                  <TableCell key={cell.id} className="py-0">
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs text-muted-foreground">
          Mostrando {firstRow}–{lastRow} de {total}
        </p>

        <div className="flex items-center gap-2">
          <Select
            value={String(rowsPerPage)}
            onValueChange={(value) => {
              const nextSize = Number(value);

              if (serverPagination) {
                serverPagination.onPageSizeChange(nextSize);
                return;
              }

              table.setPageSize(nextSize);
            }}
          >
            <SelectTrigger size="sm" aria-label="Filas por página" className="w-28">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {pageSizeOptions.map((size) => (
                <SelectItem key={size} value={String(size)}>
                  {size} filas
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Button
            type="button"
            variant="outline"
            size="icon-sm"
            aria-label="Página anterior"
            disabled={!canGoBack}
            onClick={() => {
              if (serverPagination) {
                serverPagination.onPageChange(pageNumber - 1);
                return;
              }

              table.previousPage();
            }}
          >
            <ChevronLeft aria-hidden="true" />
          </Button>
          <Button
            type="button"
            variant="outline"
            size="icon-sm"
            aria-label="Página siguiente"
            disabled={!canGoForward}
            onClick={() => {
              if (serverPagination) {
                serverPagination.onPageChange(pageNumber + 1);
                return;
              }

              table.nextPage();
            }}
          >
            <ChevronRight aria-hidden="true" />
          </Button>
        </div>
      </div>
    </div>
  );
}
