"use client"

import React, { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { fetchApi } from "@/lib/api-client"
import { useAuth } from "@/hooks/use-auth"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Activity, Clock, Search, ChevronRight, ChevronDown, Filter, Download, Waypoints, Code2 } from "lucide-react"

export default function TracesPage() {
  const { currentOrgId } = useAuth()
  const [expandedTraceId, setExpandedTraceId] = useState<string | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ["traces", currentOrgId],
    queryFn: () => fetchApi(`/traces?org_id=${currentOrgId}`),
    enabled: !!currentOrgId,
  })

  const toggleExpand = (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    setExpandedTraceId(prev => prev === id ? null : id)
  }

  return (
    <div className="flex w-full flex-col max-w-[1150px] mx-auto space-y-8 pb-12 pt-8 animate-in fade-in duration-300">
      
      {/* HEADER SECTION */}
      <div className="flex items-end justify-between border-b border-[#E5E5E5] pb-6">
        <div className="flex flex-col space-y-2">
          <span className="text-[11px] font-semibold text-[#737373] tracking-[0.05em] uppercase">
            Observability
          </span>
          <h2 className="text-[28px] md:text-[30px] font-semibold tracking-[-0.025em] text-[#111111] leading-none">
            Trace Explorer
          </h2>
          <p className="text-[13px] text-[#525252] max-w-[500px]">
            Monitor and audit deep research agent executions and telemetry.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button className="flex items-center justify-center h-9 w-9 rounded-md border border-[#E5E5E5] bg-white text-[#525252] hover:text-[#111111] hover:border-[#111111] hover:shadow-sm transition-all" title="Filter">
            <Filter className="h-4 w-4" />
          </button>
          <button className="flex items-center h-9 px-4 rounded-md border border-[#E5E5E5] bg-white text-[#111111] text-[13px] font-medium transition-all hover:bg-[#FAFAFA] hover:shadow-sm active:scale-95">
            <Download className="h-4 w-4 mr-2 text-[#737373]" />
            Export Data
          </button>
        </div>
      </div>

      <div className="rounded-lg border border-[#E5E5E5] bg-white shadow-sm overflow-hidden flex flex-col">
        {/* Table Toolbar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 px-5 py-4 border-b border-[#E5E5E5] bg-[#FAFAFA]">
          <div>
            <h3 className="text-[15px] font-semibold text-[#111111]">Execution Logs</h3>
            <p className="text-[13px] text-[#737373] mt-0.5">Recent agent queries and performance metrics.</p>
          </div>
          <div className="flex items-center gap-3">
            <div className="relative group">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-[#A3A3A3] group-focus-within:text-[#111111] transition-colors" />
              <input 
                type="text"
                placeholder="Search queries..." 
                className="pl-9 pr-4 w-[280px] h-9 text-[13px] rounded-md border border-[#D4D4D4] bg-white focus:outline-none focus:border-[#111111] focus:ring-1 focus:ring-[#111111] transition-all placeholder:text-[#A3A3A3]"
              />
            </div>
          </div>
        </div>
        
        <div className="w-full bg-white">
          <Table>
            <TableHeader className="bg-white">
              <TableRow className="border-b border-[#E5E5E5] hover:bg-transparent">
                <TableHead className="w-[40%] text-[11px] font-semibold text-[#737373] uppercase tracking-widest h-10 px-4">Query / Task</TableHead>
                <TableHead className="text-[11px] font-semibold text-[#737373] uppercase tracking-widest h-10">Classification</TableHead>
                <TableHead className="text-[11px] font-semibold text-[#737373] uppercase tracking-widest h-10">Status</TableHead>
                <TableHead className="text-[11px] font-semibold text-[#737373] uppercase tracking-widest h-10">Latency</TableHead>
                <TableHead className="text-[11px] font-semibold text-[#737373] uppercase tracking-widest h-10">Timestamp</TableHead>
                <TableHead className="text-right h-10 px-4"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <TableRow key={i} className="h-[52px] border-b border-[#E5E5E5]">
                    <TableCell className="px-4"><div className="h-4 w-3/4 bg-[#FAFAFA] animate-pulse rounded"></div></TableCell>
                    <TableCell><div className="h-4 w-24 bg-[#FAFAFA] animate-pulse rounded"></div></TableCell>
                    <TableCell><div className="h-4 w-20 bg-[#FAFAFA] animate-pulse rounded"></div></TableCell>
                    <TableCell><div className="h-4 w-16 bg-[#FAFAFA] animate-pulse rounded"></div></TableCell>
                    <TableCell><div className="h-4 w-32 bg-[#FAFAFA] animate-pulse rounded"></div></TableCell>
                    <TableCell></TableCell>
                  </TableRow>
                ))
              ) : data?.items?.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="h-64 text-center border-0 p-0">
                    <div className="flex flex-col items-center justify-center p-12 bg-white">
                      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-[#FAFAFA] border border-[#E5E5E5] mb-5 shadow-sm">
                        <Waypoints className="h-7 w-7 text-[#111111]" />
                      </div>
                      <p className="text-[18px] font-semibold text-[#111111] mb-2">No executions yet</p>
                      <p className="text-[14px] text-[#737373] max-w-sm mb-6 leading-relaxed">
                        Run an Agentic query in the Chat interface to generate your first trace telemetry.
                      </p>
                    </div>
                  </TableCell>
                </TableRow>
              ) : (
                data?.items?.map((trace: any) => {
                  const isExpanded = expandedTraceId === trace.id
                  const isSuccess = trace.status === 'completed'
                  const isFailed = trace.status === 'failed'
                  
                  return (
                    <React.Fragment key={trace.id}>
                      <TableRow 
                        className={`group border-b border-[#E5E5E5] hover:bg-[#F7F7F7] transition-colors relative cursor-pointer ${isExpanded ? 'bg-[#F7F7F7]' : 'h-[52px]'}`}
                        onClick={(e) => toggleExpand(trace.id, e)}
                      >
                        <TableCell className="font-medium max-w-[300px] px-4 py-3 relative">
                          <div className={`absolute left-0 top-0 bottom-0 w-[3px] transition-opacity ${
                            isSuccess ? 'bg-[#10B981]' : 
                            isFailed ? 'bg-[#EF4444]' : 
                            'bg-[#F59E0B]'
                          } opacity-0 group-hover:opacity-100 ${isExpanded ? 'opacity-100' : ''}`} />
                          <div className="truncate text-[13px] text-[#111111] font-medium" title={trace.original_query}>
                            {trace.original_query}
                          </div>
                        </TableCell>
                        <TableCell className="py-3">
                          <span className="inline-flex items-center px-2 py-0.5 rounded-[4px] border border-[#E5E5E5] bg-white text-[11px] font-mono uppercase tracking-widest text-[#525252] shadow-sm">
                            {trace.classification ? trace.classification.replace("_", " ") : "UNKNOWN"}
                          </span>
                        </TableCell>
                        <TableCell className="py-3">
                          <span className={`inline-flex items-center px-2 py-0.5 rounded-[4px] text-[11px] font-semibold uppercase tracking-widest border
                            ${isSuccess ? 'border-transparent bg-[#111111] text-white' : ''}
                            ${isFailed ? 'border-[#EF4444]/30 bg-[#EF4444]/10 text-[#DC2626]' : ''}
                            ${!isSuccess && !isFailed ? 'border-[#F59E0B]/30 bg-[#F59E0B]/10 text-[#D97706]' : ''}
                          `}>
                            {trace.status}
                          </span>
                        </TableCell>
                        <TableCell className="py-3 text-[#737373]">
                          <div className="flex items-center gap-2 text-[13px] font-mono">
                            <Clock className="h-3.5 w-3.5 text-[#A3A3A3]" />
                            {trace.total_latency_ms ? `${trace.total_latency_ms.toFixed(0)}ms` : "-"}
                          </div>
                        </TableCell>
                        <TableCell className="py-3 text-[13px] text-[#737373] font-mono">
                          {new Date(trace.created_at).toLocaleString(undefined, { 
                            month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit'
                          })}
                        </TableCell>
                        <TableCell className="text-right px-4 py-3">
                          <div className="flex items-center justify-end">
                            <button className="flex items-center justify-center h-7 w-7 rounded bg-transparent hover:bg-white border border-transparent hover:border-[#E5E5E5] hover:shadow-sm transition-all text-[#A3A3A3] hover:text-[#111111]">
                              {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                            </button>
                          </div>
                        </TableCell>
                      </TableRow>
                      
                      {/* Expanded Inline Detailed Trace */}
                      {isExpanded && (
                        <TableRow className="bg-[#FAFAFA] border-b border-[#E5E5E5]">
                          <TableCell colSpan={6} className="p-0">
                            <div className="p-6 flex flex-col gap-6 animate-in slide-in-from-top-2 duration-200 shadow-inner">
                              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                                
                                {/* Left: Trace Overview */}
                                <div className="lg:col-span-1 space-y-5">
                                  <div>
                                    <h4 className="text-[12px] font-semibold uppercase tracking-widest text-[#737373] mb-2">Query Details</h4>
                                    <p className="text-[14px] text-[#111111] leading-relaxed bg-white border border-[#E5E5E5] p-3 rounded-lg shadow-sm">
                                      {trace.original_query}
                                    </p>
                                  </div>
                                  <div className="flex flex-col gap-2 bg-white border border-[#E5E5E5] p-4 rounded-lg shadow-sm">
                                    <div className="flex items-center justify-between">
                                      <span className="text-[12px] font-medium text-[#737373]">Trace ID</span>
                                      <span className="text-[12px] font-mono text-[#111111] truncate max-w-[120px]">{trace.id}</span>
                                    </div>
                                    <div className="flex items-center justify-between">
                                      <span className="text-[12px] font-medium text-[#737373]">Organization</span>
                                      <span className="text-[12px] font-mono text-[#111111] truncate max-w-[120px]">{trace.org_id}</span>
                                    </div>
                                    <div className="flex items-center justify-between pt-2 border-t border-[#F5F5F5]">
                                      <span className="text-[12px] font-medium text-[#737373]">Total Latency</span>
                                      <span className="text-[12px] font-mono font-semibold text-[#111111]">{trace.total_latency_ms?.toFixed(2)} ms</span>
                                    </div>
                                  </div>
                                </div>

                                {/* Right: Execution Steps / Telemetry (Mocked UI) */}
                                <div className="lg:col-span-2 space-y-4 border border-[#E5E5E5] bg-white rounded-lg p-5 shadow-sm">
                                  <div className="flex items-center gap-2 mb-2 pb-3 border-b border-[#F5F5F5]">
                                    <Code2 className="h-[18px] w-[18px] text-[#111111]" />
                                    <h4 className="text-[14px] font-semibold text-[#111111]">Agentic Telemetry</h4>
                                  </div>
                                  
                                  <div className="space-y-4 pl-2 pt-2 relative">
                                    {/* Vertical Timeline Line */}
                                    <div className="absolute left-[11px] top-4 bottom-4 w-[2px] bg-[#F5F5F5]"></div>
                                    
                                    {[
                                      { name: "Query Classification", latency: "42ms", status: "success" },
                                      { name: "Document Retrieval", latency: "156ms", status: "success" },
                                      { name: "Evidence Synthesis", latency: trace.total_latency_ms ? `${(trace.total_latency_ms - 200).toFixed(0)}ms` : "640ms", status: isSuccess ? "success" : "failed" }
                                    ].map((step, idx) => (
                                      <div key={idx} className="flex items-start gap-4 relative z-10">
                                        <div className={`mt-0.5 flex h-[14px] w-[14px] shrink-0 items-center justify-center rounded-full border-2 bg-white ${
                                          step.status === 'success' ? 'border-[#10B981]' : 'border-[#EF4444]'
                                        }`}></div>
                                        <div className="flex-1 pb-4">
                                          <div className="flex items-center justify-between">
                                            <span className="text-[13px] font-medium text-[#111111]">{step.name}</span>
                                            <span className="text-[12px] font-mono text-[#737373] bg-[#FAFAFA] px-1.5 py-0.5 rounded border border-[#E5E5E5]">{step.latency}</span>
                                          </div>
                                          {idx === 2 && step.status === 'failed' && (
                                            <div className="mt-2 text-[12px] text-[#EF4444] bg-[#FEF2F2] p-2 rounded border border-[#FECACA] font-mono">
                                              Error: Failed to synthesize evidence from retrieved context.
                                            </div>
                                          )}
                                        </div>
                                      </div>
                                    ))}
                                  </div>
                                  
                                  <div className="mt-4 pt-4 border-t border-[#E5E5E5] flex justify-end">
                                    <button className="text-[12px] font-semibold text-[#111111] hover:underline underline-offset-2">
                                      View Raw JSON
                                    </button>
                                  </div>
                                </div>
                                
                              </div>
                            </div>
                          </TableCell>
                        </TableRow>
                      )}
                    </React.Fragment>
                  )
                })
              )}
            </TableBody>
          </Table>
        </div>
      </div>
    </div>
  )
}
