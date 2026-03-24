"use client";

import { useState, useCallback } from "react";

interface UsePaginationReturn {
  page: number;
  pageSize: number;
  setPage: (page: number) => void;
  setPageSize: (size: number) => void;
  nextPage: () => void;
  prevPage: () => void;
  resetPage: () => void;
}

export function usePagination(
  initialPage: number = 1,
  initialPageSize: number = 20
): UsePaginationReturn {
  const [page, setPage] = useState(initialPage);
  const [pageSize, setPageSizeState] = useState(initialPageSize);

  const setPageSize = useCallback(
    (size: number) => {
      setPageSizeState(size);
      setPage(1);
    },
    []
  );

  const nextPage = useCallback(() => setPage((p) => p + 1), []);
  const prevPage = useCallback(() => setPage((p) => Math.max(1, p - 1)), []);
  const resetPage = useCallback(() => setPage(1), []);

  return { page, pageSize, setPage, setPageSize, nextPage, prevPage, resetPage };
}
