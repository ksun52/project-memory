import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getMe, logout } from "./api";
import type { User } from "./types";

export function useCurrentUser() {
  return useQuery<User>({
    queryKey: ["auth", "me"],
    queryFn: getMe,
    retry: false,
  });
}

export function useLogout() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: logout,
    onSuccess: () => {
      queryClient.clear();
    },
  });
}
