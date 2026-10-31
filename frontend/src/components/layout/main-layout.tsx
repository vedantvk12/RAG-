"use client"

import { Sidebar } from "./sidebar"
import { TopNav } from "./top-nav"
import { useAuth } from "@/hooks/use-auth"
import { useRouter, usePathname } from "next/navigation"
import { useEffect } from "react"
import { AmbientGrid } from "./ambient-grid"
import { PageTransition } from "./page-transition"
import { Loader2 } from "lucide-react"

export function MainLayout({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth()
  const router = useRouter()
  const pathname = usePathname()

  const isPublicRoute = pathname === "/login" || pathname === "/signup"

  useEffect(() => {
    if (!isLoading && !user && !isPublicRoute) {
      router.push("/login")
    }
  }, [user, isLoading, router, isPublicRoute])

  if (isLoading && !isPublicRoute) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-[#FFFFFF]">
        <Loader2 className="h-5 w-5 animate-spin text-[#050505]" />
      </div>
    )
  }

  if (!user && !isPublicRoute) {
    return null
  }

  if (isPublicRoute) {
    return <>{children}</>
  }

  const isChat = pathname === "/chat"

  return (
    <div className="flex h-screen overflow-hidden bg-[#FFFFFF]">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden relative">
        <TopNav />
        <main className={`flex-1 ${isChat ? 'overflow-hidden flex flex-col' : 'overflow-y-auto'} relative z-0`}>
          <AmbientGrid />
          <div className={`mx-auto h-full w-full ${isChat ? 'p-0 max-w-none' : 'max-w-[1400px] p-6 md:p-8 lg:p-10'} relative z-10`}>
            <PageTransition>
              {children}
            </PageTransition>
          </div>
        </main>
      </div>
    </div>
  )
}
