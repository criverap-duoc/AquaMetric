import {
  createPaginatedRowModel,
  createSortedRowModel,
  rowPaginationFeature,
  rowSortingFeature,
  sortFns,
  tableFeatures,
  type ColumnDef,
  type RowData,
} from "@tanstack/react-table";

/**
 * Feature set of every `DataTable`: column sorting and client-side pagination.
 *
 * TanStack Table v9 asks for the features explicitly so the bundle only ships what is used
 * (`tableFeatures`). Kept in a `.ts` module because `react-refresh/only-export-components`
 * forbids exporting values next to a component.
 */
export const DATA_TABLE_FEATURES = tableFeatures({
  rowSortingFeature,
  rowPaginationFeature,
  sortedRowModel: createSortedRowModel(),
  paginatedRowModel: createPaginatedRowModel(),
  sortFns,
});

export type DataTableFeatures = typeof DATA_TABLE_FEATURES;

/** Column definition bound to the features above, so callers never repeat the generic. */
export type DataTableColumnDef<TData extends RowData, TValue = unknown> = ColumnDef<
  DataTableFeatures,
  TData,
  TValue
>;
