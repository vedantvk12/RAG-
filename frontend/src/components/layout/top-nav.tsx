"use client"

import { usePathname } from "next/navigation"
import { 
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"

export function TopNav() {
  const pathname = usePathname()
  
  const getPageTitle = () => {
    if (pathname === "/") return "Overview"
    if (pathname.startsWith("/chat")) return "Agent Chat"
    if (pathname.startsWith("/decisions")) return "Decision Intelligence"
    if (pathname.startsWith("/documents")) return "Documents"
    if (pathname.startsWith("/traces")) return "Trace Explorer"
    if (pathname.startsWith("/settings")) return "Settings"
    return "Overview"
  }

  return (
    <div className="flex h-14 items-center justify-between px-6 lg:px-8 border-b border-[#E5E5E5] bg-white">
      <div className="flex items-center gap-2">
        <span className="text-[12px] text-[#737373] font-medium">Workspace</span>
        <span className="text-[12px] text-[#D4D4D4] font-light">/</span>
        <h1 className="text-[14px] font-semibold text-black">{getPageTitle()}</h1>
      </div>
      
      <div className="flex items-center gap-4">
        <Tooltip>
          <TooltipTrigger className="flex items-center gap-[6px] px-2.5 py-1.5 rounded-full cursor-help hover:bg-[#F5F5F5] transition-colors border border-transparent hover:border-[#E5E5E5]">
            <div className="h-[6px] w-[6px] rounded-full bg-[#10B981] relative">
              <div className="absolute inset-0 rounded-full bg-[#10B981] animate-ping opacity-20" />
            </div>
            <span className="text-[10px] font-semibold text-[#525252] tracking-[0.05em] uppercase">System Operational</span>
          </TooltipTrigger>
          <TooltipContent side="bottom" className="bg-black text-white text-[11px] border-none font-medium px-3 py-1.5">
            <p>All core services are responding normally.</p>
          </TooltipContent>
        </Tooltip>
      </div>
    </div>
  )
}
