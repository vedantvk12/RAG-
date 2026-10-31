"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { 
  LayoutDashboard, 
  MessageSquare, 
  FileText, 
  Activity, 
  GitMerge,
  Hexagon,
  ChevronRight,
  Settings
} from "lucide-react"
import { useAuth } from "@/hooks/use-auth"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

const routes = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/chat", label: "Agent Chat", icon: MessageSquare },
  { href: "/decisions", label: "Decision Intelligence", icon: GitMerge },
  { href: "/documents", label: "Knowledge Base", icon: FileText },
  { href: "/traces", label: "Trace Explorer", icon: Activity },
  { href: "/settings", label: "Settings", icon: Settings },
]

export function Sidebar() {
  const pathname = usePathname()
  const { logout, user } = useAuth()
  
  // Extract initials for avatar
  const initials = user?.email?.substring(0, 2).toUpperCase() || "EA"
  const email = user?.email || "admin@enterprise.ai"

  return (
    <div className="flex h-full w-[240px] flex-col bg-[#050505] text-[#FAFAFA] border-r border-[#1F1F1F]">
      <div className="flex h-16 items-center px-6 mb-2 border-b border-[#1F1F1F]">
        <Link href="/" className="flex items-center gap-2.5 group transition-opacity hover:opacity-80">
          <div className="flex items-center justify-center h-[30px] w-[30px] rounded-[6px] bg-white/10 text-white group-hover:bg-white group-hover:text-black transition-all">
            <Hexagon className="h-[16px] w-[16px] transition-transform duration-500 group-hover:rotate-180" />
          </div>
          <div className="flex flex-col">
            <span className="tracking-tight text-[13px] font-bold text-white leading-none">Enterprise Agentic</span>
            <span className="text-[10px] uppercase tracking-[0.08em] text-[#737373] mt-1 font-medium">Workstation</span>
          </div>
        </Link>
      </div>
      
      <div className="flex-1 overflow-y-auto py-4">
        <nav className="space-y-1.5 px-3">
          <div className="px-3 pb-2 text-[10px] font-bold text-[#525252] uppercase tracking-[0.08em]">
            Core Platform
          </div>
          {routes.map((route) => {
            const active = pathname === route.href || (route.href !== "/" && pathname.startsWith(route.href))
            const Icon = route.icon
            return (
              <Link
                key={route.href}
                href={route.href}
                className={`flex items-center gap-2.5 rounded-[6px] px-3 h-[38px] text-[13px] font-medium transition-all duration-150 group relative ${
                  active 
                    ? "bg-[#181818] text-white" 
                    : "text-[#A3A3A3] hover:bg-[#111111] hover:text-white"
                }`}
              >
                {active && (
                  <div className="absolute left-0 top-1/2 -translate-y-1/2 h-[20px] w-[2px] bg-white rounded-r-md" />
                )}
                <Icon className={`h-[15px] w-[15px] transition-transform duration-150 ${active ? "text-white" : "text-[#737373] group-hover:text-white"}`} strokeWidth={1.7} />
                {route.label}
              </Link>
            )
          })}
        </nav>
      </div>
      
      <div className="p-4 mt-auto border-t border-[#1F1F1F]">
        <DropdownMenu>
          <DropdownMenuTrigger className="flex items-center gap-2.5 w-full rounded-[6px] bg-transparent hover:bg-[#111111] p-2 transition-colors text-left outline-none group cursor-pointer border-none duration-150">
            <div className="flex h-[30px] w-[30px] items-center justify-center rounded-[6px] bg-[#1A1A1A] text-white text-[11px] font-mono font-bold tracking-tight border border-[#333333]">
              {initials}
            </div>
            <div className="flex flex-col flex-1 overflow-hidden">
              <span className="text-[12px] font-medium truncate text-[#FAFAFA]">
                {email}
              </span>
              <span className="text-[11px] text-[#737373] truncate">
                Administrator
              </span>
            </div>
              <ChevronRight className="h-[14px] w-[14px] text-[#525252] group-hover:text-white transition-colors" />
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-[228px] bg-[#111111] border border-[#333333] shadow-xl rounded-lg p-1.5 text-white">
            <DropdownMenuLabel className="font-normal text-[12px] text-[#A3A3A3] px-2 py-2">
              Signed in as <span className="font-semibold text-white truncate block mt-1">{email}</span>
            </DropdownMenuLabel>
            <DropdownMenuSeparator className="bg-[#333333] mx-1 my-1" />
            <DropdownMenuItem className="text-[13px] cursor-pointer px-2.5 py-2 rounded-md hover:bg-[#1A1A1A] hover:text-white focus:bg-[#1A1A1A] focus:text-white transition-colors">
              Platform Settings
            </DropdownMenuItem>
            <DropdownMenuItem className="text-[13px] cursor-pointer px-2.5 py-2 rounded-md hover:bg-[#1A1A1A] hover:text-white focus:bg-[#1A1A1A] focus:text-white transition-colors">
              Billing & Usage
            </DropdownMenuItem>
            <DropdownMenuSeparator className="bg-[#333333] mx-1 my-1" />
            <DropdownMenuItem 
              onClick={() => logout()}
              className="text-[13px] cursor-pointer px-2.5 py-2 rounded-md hover:bg-[#3F0000] hover:text-[#FF8080] focus:bg-[#3F0000] focus:text-[#FF8080] transition-colors"
            >
              Log out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  )
}
