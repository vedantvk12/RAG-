"use client"

import { useQuery } from "@tanstack/react-query"
import { fetchApi } from "@/lib/api-client"
import { ArrowLeft, Clock, Target, Zap, Server, CheckCircle2, Search, Cpu } from "lucide-react"
import Link from "next/link"
import ReactMarkdown from "react-markdown"
import { use } from "react"
import { Button } from "@/components/ui/button"

export default function TraceDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params)
  const { id } = resolvedParams

  const { data: trace, isLoading } = useQuery({
    queryKey: ["traces", id],
    queryFn: () => fetchApi(`/traces/${id}`),
  })

  if (isLoading) {
    return (
      <div className="flex w-full h-[60vh] flex-col items-center justify-center animate-in fade-in">
        <Server className="h-8 w-8 text-muted-foreground mb-4 animate-pulse" />
        <h3 className="text-[15px] font-medium text-foreground mb-1">Loading Trace Data</h3>
        <p className="text-[13px] text-muted-foreground">Retrieving execution pipeline details...</p>
      </div>
    )
  }

  if (!trace) {
    return (
      <div className="flex w-full h-[60vh] flex-col items-center justify-center text-center animate-in fade-in">
        <Server className="h-8 w-8 text-muted-foreground mb-4 opacity-50" />
        <h3 className="text-[15px] font-medium text-foreground mb-1">Trace Not Found</h3>
        <p className="text-[13px] text-muted-foreground mb-6 max-w-sm">
          The execution trace you're looking for doesn't exist or you don't have access.
        </p>
        <Link href="/traces">
          <Button variant="outline" size="sm">
            <ArrowLeft className="h-3.5 w-3.5 mr-2" /> Back to Explorer
          </Button>
        </Link>
      </div>
    )
  }

  const getStepIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case 'planning': return <Target className="h-4 w-4" />
      case 'retrieval': return <Search className="h-4 w-4" />
      case 'synthesis': return <Zap className="h-4 w-4" />
      default: return <Cpu className="h-4 w-4" />
    }
  }

  return (
    <div className="flex w-full flex-col max-w-[1150px] mx-auto space-y-8 animate-in fade-in duration-300 pt-8 pb-12">
      
      <div className="flex items-start gap-4">
        <Link href="/traces">
          <Button variant="outline" size="sm" className="h-8 w-8 p-0 shrink-0">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div className="flex flex-col gap-1 w-full">
          <div className="flex items-center gap-3">
            <h2 className="text-[20px] font-semibold tracking-tight text-foreground">Trace detail</h2>
            <span className={`inline-flex items-center px-2 py-0.5 rounded-[4px] text-[11px] font-medium border
              ${trace.status === 'completed' ? 'border-[#111111] bg-[#111111] text-white dark:bg-white dark:text-black dark:border-white' : ''}
              ${trace.status === 'failed' ? 'border-destructive/50 bg-destructive/10 text-destructive' : ''}
              ${trace.status !== 'completed' && trace.status !== 'failed' ? 'border-amber-500/50 bg-amber-500/10 text-amber-600 dark:text-amber-500' : ''}
            `}>
              {trace.status.charAt(0).toUpperCase() + trace.status.slice(1)}
            </span>
          </div>
          <div className="flex flex-wrap items-center gap-3 text-[12px] text-muted-foreground font-mono">
            <span className="bg-secondary px-1.5 py-0.5 rounded border border-border">ID: {trace.id}</span>
            <span>•</span>
            <span>{new Date(trace.created_at).toLocaleString()}</span>
            <span>•</span>
            <span className="flex items-center gap-1"><Clock className="h-3 w-3" /> {trace.total_latency_ms?.toFixed(0)} ms</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
        
        {/* Left: Query Context */}
        <div className="xl:col-span-1">
          <div className="rounded-md border border-border bg-card shadow-sm sticky top-6">
            <div className="border-b border-border px-5 py-4 bg-[#FAFAFA] dark:bg-[#111111]">
              <h3 className="text-[14px] font-semibold text-foreground">Input Query</h3>
            </div>
            <div className="p-5">
              <p className="text-[14px] text-foreground font-medium leading-relaxed font-serif border-l-2 border-[#111111] dark:border-white pl-4 italic">
                "{trace.original_query}"
              </p>
            </div>
          </div>
        </div>

        {/* Right: Execution Timeline */}
        <div className="xl:col-span-2 space-y-6">
          <h3 className="text-[16px] font-semibold flex items-center gap-2 text-foreground">
            <Cpu className="h-4 w-4" /> Execution Timeline
          </h3>
          
          <div className="relative border-l border-border ml-3 space-y-8 pb-4">
            {trace.steps?.map((step: any, idx: number) => {
              // Extract safe metadata
              const evidenceCount = step.payload?.sources?.length || step.payload?.evidence?.length;
              const hasResponse = !!step.payload?.response;
              
              return (
                <div key={step.id} className="relative pl-8">
                  {/* Timeline Dot */}
                  <div className="absolute -left-2.5 top-2 h-5 w-5 rounded-full bg-background border border-border flex items-center justify-center">
                    <div className="h-1.5 w-1.5 rounded-full bg-[#111111] dark:bg-white"></div>
                  </div>

                  <div className="rounded-md border border-border bg-card shadow-sm overflow-hidden">
                    <div className="flex flex-row items-center justify-between px-4 py-3 bg-[#FAFAFA] dark:bg-[#111111] border-b border-border">
                      <div className="flex items-center gap-3">
                        <div className="h-7 w-7 bg-background rounded-md shadow-sm border border-border flex items-center justify-center text-foreground">
                          {getStepIcon(step.step_type)}
                        </div>
                        <div className="flex flex-col">
                          <span className="text-[13px] font-bold uppercase tracking-wider text-foreground">0{idx + 1} {step.step_type}</span>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        {evidenceCount !== undefined && (
                          <span className="text-[11px] font-mono text-muted-foreground">{evidenceCount} sources</span>
                        )}
                        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-[4px] bg-background shadow-sm border border-border text-[11px] font-mono font-medium text-muted-foreground">
                          <Clock className="h-3 w-3" />
                          {step.latency_ms?.toFixed(0)} ms
                        </span>
                      </div>
                    </div>
                    
                    <div className="p-0">
                      {hasResponse ? (
                        <div className="p-5 prose prose-sm dark:prose-invert max-w-none text-[13px] text-foreground leading-relaxed bg-background">
                          <ReactMarkdown>{step.payload.response}</ReactMarkdown>
                        </div>
                      ) : (
                        <div className="bg-[#050505] p-5 overflow-x-auto border-t border-border">
                          {/* We only render safe JSON if needed, but since user asked to avoid raw JSON unless needed,
                              we will just show a summary if we can't parse it well. */}
                          <pre className="text-[#A3A3A3] font-mono text-[11px] leading-relaxed">
                            {JSON.stringify(
                              Object.fromEntries(
                                Object.entries(step.payload).filter(([k]) => !k.includes('token') && !k.includes('secret') && !k.includes('raw_'))
                              ), 
                              null, 
                              2
                            )}
                          </pre>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )
            })}
            
            {trace.steps?.length > 0 && (
              <div className="relative pl-8 pt-2">
                <div className="absolute -left-2.5 top-3 h-5 w-5 rounded-full bg-background border border-border flex items-center justify-center">
                  <CheckCircle2 className="h-3 w-3 text-foreground" />
                </div>
                <div className="text-[13px] font-medium text-muted-foreground pt-1">
                  Execution completed
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
