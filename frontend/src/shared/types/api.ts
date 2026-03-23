export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface ApiError {
  error: {
    code: string;
    message: string;
  };
}

export interface PaginationParams {
  page?: number;
  page_size?: number;
}
