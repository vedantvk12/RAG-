import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { fetchApi } from "@/lib/api-client"

export function useAuth() {
  const queryClient = useQueryClient()

  const { data: user, isLoading, error } = useQuery({
    queryKey: ["auth", "me"],
    queryFn: () => fetchApi("/auth/me"),
    retry: false,
  })

  const loginMutation = useMutation({
    mutationFn: async (data: any) => {
      const formData = new URLSearchParams()
      formData.append("username", data.email)
      formData.append("password", data.password)
      
      return fetchApi("/auth/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: formData.toString(),
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["auth", "me"] })
    },
  })
  
  const logoutMutation = useMutation({
    mutationFn: () => fetchApi("/auth/logout", { method: "POST" }),
    onSuccess: () => {
      queryClient.setQueryData(["auth", "me"], null)
      if (typeof window !== "undefined") {
        window.location.href = "/login"
      }
    },
  })

  const currentOrgId = user?.memberships?.[0]?.org_id

  return {
    user,
    currentOrgId,
    isLoading,
    error,
    login: loginMutation.mutateAsync,
    logout: logoutMutation.mutateAsync,
  }
}
