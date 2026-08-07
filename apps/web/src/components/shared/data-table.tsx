"use client";

import { useMemo, useState } from "react";
import {
  columnVisibilityFeature,
  createPaginatedRowModel,
  createSortedRowModel,
  rowPaginationFeature,
  rowSortingFeature,
  sortFn_alphanumeric,
  sortFn_basic,
  sortFn_text,
  tableFeatures,
  useTable,
  type ColumnDef,
  type RowData,
} from "@tanstack/react-table";
import {
  ArrowDown,
  ArrowUp,
  ArrowUpDown,
  ChevronLeft,
  ChevronRight,
  Columns3,
  Search,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { EmptyState } from "@/components/shared/empty-state";
import { Database } from "lucide-react";

export const dataTableFeatures = tableFeatures({
  columnVisibilityFeature,
  rowSortingFeature,
  sortedRowModel: createSortedRowModel(),
  sortFns: {
    alphanumeric: sortFn_alphanumeric,
    basic: sortFn_basic,
    text: sortFn_text,
  },
  rowPaginationFeature,
  paginatedRowModel: createPaginatedRowModel(),
});

export type DataTableColumn<TData extends RowData> = ColumnDef<
  typeof dataTableFeatures,
  TData
>;

export function DataTable<TData extends RowData>({
  data,
  columns,
  searchText,
  searchPlaceholder = "Search...",
  toolbar,
  pageSize = 10,
  emptyTitle = "No results",
  emptyMessage = "Try changing the search or filter criteria.",
}: {
  data: TData[];
  columns: DataTableColumn<TData>[];
  searchText?: (row: TData) => string;
  searchPlaceholder?: string;
  toolbar?: React.ReactNode;
  pageSize?: number;
  emptyTitle?: string;
  emptyMessage?: string;
}) {
  const [query, setQuery] = useState("");
  const normalizedQuery = query.trim().toLowerCase();
  const filteredData = useMemo(() => {
    if (!normalizedQuery || !searchText) return data;
    return data.filter((row) =>
      searchText(row).toLowerCase().includes(normalizedQuery),
    );
  }, [data, normalizedQuery, searchText]);

  const table = useTable({
    features: dataTableFeatures,
    data: filteredData,
    columns,
    initialState: { pagination: { pageIndex: 0, pageSize } },
  });

  const rowCount = table.getRowCount();
  const pageCount = Math.max(table.getPageCount(), 1);
  const pageIndex = table.state.pagination.pageIndex;

  return (
    <div>
      <div className="flex flex-col gap-2 border-b p-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex min-w-0 flex-1 flex-col gap-2 sm:flex-row sm:items-center">
          {searchText && (
            <div className="relative w-full sm:max-w-xs">
              <Search className="pointer-events-none absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder={searchPlaceholder}
                className="h-8 pl-8"
                aria-label={searchPlaceholder}
              />
            </div>
          )}
          {toolbar}
        </div>
        <DropdownMenu>
          <DropdownMenuTrigger
            render={
              <Button variant="outline" size="sm" className="self-start" />
            }
          >
            <Columns3 /> Columns
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-48">
            <DropdownMenuGroup>
              <DropdownMenuLabel>Visible columns</DropdownMenuLabel>
            </DropdownMenuGroup>
            <DropdownMenuSeparator />
            <div className="space-y-1 p-1">
              {table
                .getAllLeafColumns()
                .filter((column) => column.getCanHide())
                .map((column) => (
                  <label
                    key={column.id}
                    className="flex items-center gap-2 rounded-md px-1.5 py-1 text-sm hover:bg-muted"
                  >
                    <Checkbox
                      checked={column.getIsVisible()}
                      onCheckedChange={(checked) =>
                        column.toggleVisibility(Boolean(checked))
                      }
                    />
                    <span className="truncate">{column.id}</span>
                  </label>
                ))}
            </div>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => {
                  const sortable = header.column.getCanSort();
                  const sorted = header.column.getIsSorted();
                  return (
                    <TableHead key={header.id} className="h-9 whitespace-nowrap">
                      {header.isPlaceholder ? null : sortable ? (
                        <button
                          className="flex items-center gap-1 font-medium hover:text-foreground"
                          onClick={header.column.getToggleSortingHandler()}
                        >
                          <table.FlexRender header={header} />
                          {sorted === "asc" ? (
                            <ArrowUp className="size-3" />
                          ) : sorted === "desc" ? (
                            <ArrowDown className="size-3" />
                          ) : (
                            <ArrowUpDown className="size-3 opacity-45" />
                          )}
                        </button>
                      ) : (
                        <table.FlexRender header={header} />
                      )}
                    </TableHead>
                  );
                })}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {table.getRowModel().rows.length ? (
              table.getRowModel().rows.map((row) => (
                <TableRow key={row.id}>
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id} className="h-11 py-2">
                      <table.FlexRender cell={cell} />
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell
                  colSpan={Math.max(table.getVisibleLeafColumns().length, 1)}
                  className="p-0"
                >
                  <EmptyState
                    icon={Database}
                    title={emptyTitle}
                    message={emptyMessage}
                  />
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      <div className="flex items-center justify-between gap-3 border-t px-3 py-2 text-xs text-muted-foreground">
        <span className="numeric">
          {rowCount} {rowCount === 1 ? "row" : "rows"}
        </span>
        <div className="flex items-center gap-2">
          <span className="numeric">
            Page {pageIndex + 1} of {pageCount}
          </span>
          <div className="flex gap-1">
            <Button
              variant="outline"
              size="icon-xs"
              onClick={() => table.previousPage()}
              disabled={!table.getCanPreviousPage()}
              aria-label="Previous page"
            >
              <ChevronLeft />
            </Button>
            <Button
              variant="outline"
              size="icon-xs"
              onClick={() => table.nextPage()}
              disabled={!table.getCanNextPage()}
              aria-label="Next page"
            >
              <ChevronRight />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
