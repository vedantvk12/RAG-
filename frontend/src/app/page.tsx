"use client"

import { useQuery } from "@tanstack/react-query"
import { fetchApi } from "@/lib/api-client"
import { useAuth } from "@/hooks/use-auth"
import { Activity, FileText, MessageSquare, Database, ArrowRight, GitMerge, Search, Hexagon } from "lucide-react"
import Link from "next/link"

export default function Dashboard() {
  const { currentOrgId, user } = useAuth()

  const { data: stats, isLoading } = useQuery({
    queryKey: ["dashboard", "stats", currentOrgId],
    queryFn: () => fetchApi(`/dashboard/stats?org_id=${currentOrgId}`),
    enabled: !!currentOrgId,
  })

  const hour = new Date().getHours()
  const greeting = hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening"
  const userName = user?.email?.split('@')[0] || "Administrator"
  const formattedName = userName.charAt(0).toUpperCase() + userName.slice(1)

  const metrics = [
    {
      title: "DOCUMENTS",
      value: stats?.documents?.total || 0,
      icon: FileText,
      description: "Total indexed",
    },
    {
      title: "AGENT RUNS",
      value: stats?.agent_runs?.total || 0,
      icon: Activity,
      description: "Total executions",
    },
    {
      title: "TOTAL QUERIES",
      value: stats?.queries?.total || 0,
      icon: MessageSquare,
      description: "Processed",
    },
    {
      title: "SYSTEM STATUS",
      value: "Healthy",
      icon: Database,
      description: "100% uptime",
    },
  ]

  return (
    <div className="flex w-full flex-col max-w-[1150px] mx-auto space-y-8 animate-in fade-in duration-300 pb-12 pt-8">
      {/* HEADER SECTION */}
      <div className="flex flex-col space-y-2 border-b border-[#E5E5E5] pb-6">
        <div>
          <span className="text-[11px] font-semibold text-[#737373] tracking-[0.05em] uppercase mb-2 flex items-center gap-1.5">
            <Hexagon className="h-3 w-3" strokeWidth={2} /> Workspace Overview
          </span>
          <h2 className="text-[28px] md:text-[30px] font-semibold tracking-[-0.025em] text-[#111111] leading-tight">
            {greeting}, {formattedName}
          </h2>
          <p className="text-[13px] text-[#525252] mt-1 max-w-[700px] leading-relaxed">
            Monitor your organization's knowledge base, deep research agents, and autonomous decision workflows.
          </p>
        </div>
        
        <div className="flex items-center gap-3 mt-2">
          <div className="flex items-center justify-center h-5 w-5 rounded-full bg-[#ECFDF5] border border-[#A7F3D0]">
            <div className="h-2 w-2 rounded-full bg-[#10B981] animate-pulse" />
          </div>
          <span className="text-[13px] font-medium text-[#111111] tracking-wide">All agentic systems operational</span>
        </div>
      </div>
      
      {/* METRIC STRIP */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {isLoading ? (
          Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="rounded-xl border border-[#E5E5E5] bg-white p-6 shadow-sm">
              <div className="h-3 w-16 bg-[#F5F5F5] animate-pulse rounded mb-5" />
              <div className="h-10 w-16 bg-[#F5F5F5] animate-pulse rounded" />
              <div className="h-3 w-20 bg-[#F5F5F5] animate-pulse rounded mt-4" />
            </div>
          ))
        ) : (
          metrics.map((metric, i) => (
            <div 
              key={i} 
              className="group rounded-xl border border-[#E5E5E5] bg-white p-6 transition-all duration-300 hover:-translate-y-1 hover:border-[#111111] hover:shadow-[0_12px_24px_rgba(0,0,0,0.06)] relative overflow-hidden"
            >
              {/* Subtle hover gradient background */}
              <div className="absolute inset-0 bg-gradient-to-br from-[#FAFAFA] to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
              
              <div className="relative z-10">
                <div className="flex items-center gap-2.5 mb-4">
                  <metric.icon className="h-4 w-4 text-[#737373] group-hover:text-[#111111] transition-colors" />
                  <h3 className="text-[11px] font-bold tracking-widest text-[#737373] uppercase group-hover:text-[#111111] transition-colors">
                    {metric.title}
                  </h3>
                </div>
                <div>
                  <div className="text-[36px] font-bold tracking-tight text-[#111111] leading-none mb-2">
                    {metric.value}
                  </div>
                  <div className="text-[13px] font-medium text-[#737373]">
                    {metric.description}
                  </div>
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* LOWER SECTION: ACTIVITY & ACTIONS */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* ACTIVITY TIMELINE */}
        <div className="lg:col-span-2 flex flex-col space-y-4 animate-in slide-in-from-bottom-4 duration-500 delay-100">
          <h3 className="text-[12px] font-bold text-[#111111] tracking-widest uppercase flex items-center gap-2">
            <Activity className="h-3.5 w-3.5" /> Recent Activity
          </h3>
          <div className="flex-1 rounded-xl border border-[#E5E5E5] bg-white p-8 lg:p-12 relative overflow-hidden shadow-sm hover:shadow-md transition-shadow duration-300 group">
            {/* Empty state timeline visual */}
            <div className="absolute left-8 top-12 bottom-12 w-[2px] bg-gradient-to-b from-transparent via-[#E5E5E5] to-transparent" />
            <div className="absolute left-[31px] top-1/3 h-2 w-2 rounded-full border-2 border-[#111111] bg-white" />
            <div className="absolute left-[31px] top-2/3 h-2 w-2 rounded-full border-2 border-[#D4D4D4] bg-white group-hover:border-[#111111] transition-colors duration-500" />
            
            <div className="pl-10 flex flex-col items-start justify-center h-full relative z-10">
              <span className="text-[18px] font-semibold text-[#111111] mb-2">No activity recorded yet</span>
              <p className="text-[15px] text-[#737373] max-w-[360px] mb-8 leading-relaxed">
                When you upload documents, run research queries, or generate decision matrices, they will appear here in your timeline.
              </p>
              <Link 
                href="/documents" 
                className="group/btn inline-flex h-11 items-center justify-center rounded-lg bg-[#111111] px-6 text-[14px] font-medium text-white transition-all hover:bg-[#1A1A1A] hover:shadow-[0_4px_12px_rgba(0,0,0,0.15)] active:scale-[0.98]"
              >
                Upload your first document 
                <ArrowRight className="ml-2.5 h-4 w-4 transition-transform duration-300 group-hover/btn:translate-x-1.5" />
              </Link>
            </div>
          </div>
        </div>
        
        {/* QUICK ACTIONS */}
        <div className="flex flex-col space-y-4 animate-in slide-in-from-bottom-4 duration-500 delay-200">
          <h3 className="text-[12px] font-bold text-[#111111] tracking-widest uppercase flex items-center gap-2">
            <Search className="h-3.5 w-3.5" /> Quick Actions
          </h3>
          <div className="flex flex-col gap-4">
            
            <Link href="/chat" className="group flex items-center p-5 rounded-xl border border-[#E5E5E5] bg-white transition-all duration-300 hover:border-[#111111] hover:shadow-[0_8px_24px_rgba(0,0,0,0.06)] relative overflow-hidden">
              <div className="absolute inset-0 bg-[#FAFAFA] opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
              <div className="relative z-10 flex items-center w-full">
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-[#FAFAFA] border border-[#E5E5E5] group-hover:bg-[#111111] transition-colors duration-300 mr-4 shadow-sm">
                  <Search className="h-5 w-5 text-[#525252] group-hover:text-white transition-colors duration-300" />
                </div>
                <div className="flex flex-col flex-1">
                  <span className="text-[13px] font-bold tracking-widest text-[#111111] uppercase mb-1 leading-tight group-hover:translate-x-1 transition-transform duration-300">Agent Chat</span>
                  <span className="text-[13px] text-[#737373] leading-tight group-hover:translate-x-1 transition-transform duration-300 delay-75">Deep search organizational knowledge</span>
                </div>
                <ArrowRight className="h-5 w-5 text-[#A3A3A3] transition-all duration-300 group-hover:translate-x-1 group-hover:text-[#111111]" />
              </div>
            </Link>
            
            <Link href="/decisions" className="group flex items-center p-5 rounded-xl border border-[#E5E5E5] bg-white transition-all duration-300 hover:border-[#111111] hover:shadow-[0_8px_24px_rgba(0,0,0,0.06)] relative overflow-hidden">
              <div className="absolute inset-0 bg-[#FAFAFA] opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
              <div className="relative z-10 flex items-center w-full">
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-[#FAFAFA] border border-[#E5E5E5] group-hover:bg-[#111111] transition-colors duration-300 mr-4 shadow-sm">
                  <GitMerge className="h-5 w-5 text-[#525252] group-hover:text-white transition-colors duration-300" />
                </div>
                <div className="flex flex-col flex-1">
                  <span className="text-[13px] font-bold tracking-widest text-[#111111] uppercase mb-1 leading-tight group-hover:translate-x-1 transition-transform duration-300">Decision Analysis</span>
                  <span className="text-[13px] text-[#737373] leading-tight group-hover:translate-x-1 transition-transform duration-300 delay-75">Generate evidence-backed evaluations</span>
                </div>
                <ArrowRight className="h-5 w-5 text-[#A3A3A3] transition-all duration-300 group-hover:translate-x-1 group-hover:text-[#111111]" />
              </div>
            </Link>
            
            <Link href="/documents" className="group flex items-center p-5 rounded-xl border border-[#E5E5E5] bg-white transition-all duration-300 hover:border-[#111111] hover:shadow-[0_8px_24px_rgba(0,0,0,0.06)] relative overflow-hidden">
              <div className="absolute inset-0 bg-[#FAFAFA] opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
              <div className="relative z-10 flex items-center w-full">
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-[#FAFAFA] border border-[#E5E5E5] group-hover:bg-[#111111] transition-colors duration-300 mr-4 shadow-sm">
                  <FileText className="h-5 w-5 text-[#525252] group-hover:text-white transition-colors duration-300" />
                </div>
                <div className="flex flex-col flex-1">
                  <span className="text-[13px] font-bold tracking-widest text-[#111111] uppercase mb-1 leading-tight group-hover:translate-x-1 transition-transform duration-300">Knowledge Base</span>
                  <span className="text-[13px] text-[#737373] leading-tight group-hover:translate-x-1 transition-transform duration-300 delay-75">Upload and index documents</span>
                </div>
                <ArrowRight className="h-5 w-5 text-[#A3A3A3] transition-all duration-300 group-hover:translate-x-1 group-hover:text-[#111111]" />
              </div>
            </Link>
            
          </div>
        </div>
        
      </div>
    </div>
  )
}
