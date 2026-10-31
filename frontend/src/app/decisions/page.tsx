"use client"

import { useState } from "react"
import { useMutation } from "@tanstack/react-query"
import { fetchApi } from "@/lib/api-client"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Loader2, Sparkles, AlertTriangle, ShieldAlert, GitMerge, Activity, FileText, ArrowRight, BrainCircuit } from "lucide-react"

export default function DecisionsPage() {
  const [query, setQuery] = useState("")

  const analyzeMutation = useMutation({
    mutationFn: async (text: string) => {
      return fetchApi("/decisions/analyze", {
        method: "POST",
        body: JSON.stringify({ query: text }),
      })
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (query.trim() && !analyzeMutation.isPending) {
      analyzeMutation.mutate(query)
    }
  }

  const renderDecisionContent = (data: any) => {
    if (data.decision_type === "abstain") {
      return (
        <div className="mt-8 rounded-xl border border-[#FCD34D] bg-[#FFFBEB] p-8 shadow-sm">
          <div className="flex items-center gap-3 mb-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-[#FEF3C7]">
              <AlertTriangle className="h-5 w-5 text-[#D97706]" />
            </div>
            <h3 className="text-[18px] font-semibold text-[#92400E]">Insufficient Context</h3>
          </div>
          <p className="text-[15px] text-[#B45309] leading-relaxed ml-13 pl-[52px]">
            {data.reason || "The system could not formulate a confident decision based on the available data."}
          </p>
        </div>
      )
    }

    switch (data.decision_type) {
      case "comparison":
        return (
          <div className="grid gap-6 md:grid-cols-2 mt-8 animate-in slide-in-from-bottom-4 duration-500">
            <div className="rounded-xl border border-[#E5E5E5] bg-white shadow-sm overflow-hidden flex flex-col h-full">
              <div className="border-b border-[#E5E5E5] px-6 py-5 bg-[#FAFAFA] flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="h-2.5 w-2.5 rounded-full bg-[#10B981]" />
                  <h3 className="text-[16px] font-semibold text-[#111111]">Advantages</h3>
                </div>
              </div>
              <div className="p-6 flex-1 bg-white">
                <ul className="space-y-5">
                  {data.advantages?.map((adv: any, i: number) => (
                    <li key={i} className="flex items-start gap-4 p-4 rounded-lg bg-[#FAFAFA] border border-[#F5F5F5]">
                      <div className="text-[14px] text-[#111111] leading-relaxed flex-1">{adv.description}</div>
                      {adv.source_id && (
                        <span className="text-[11px] font-mono font-medium text-[#737373] bg-white px-2 py-1 rounded border border-[#E5E5E5] flex items-center gap-1.5 shrink-0 shadow-sm">
                          <FileText className="h-[10px] w-[10px]" /> src:{adv.source_id.substring(0,4)}
                        </span>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
            
            <div className="rounded-xl border border-[#E5E5E5] bg-white shadow-sm overflow-hidden flex flex-col h-full">
              <div className="border-b border-[#E5E5E5] px-6 py-5 bg-[#FAFAFA] flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="h-2.5 w-2.5 rounded-full bg-[#EF4444]" />
                  <h3 className="text-[16px] font-semibold text-[#111111]">Disadvantages</h3>
                </div>
              </div>
              <div className="p-6 flex-1 bg-white">
                <ul className="space-y-5">
                  {data.disadvantages?.map((dis: any, i: number) => (
                    <li key={i} className="flex items-start gap-4 p-4 rounded-lg bg-[#FAFAFA] border border-[#F5F5F5]">
                      <div className="text-[14px] text-[#111111] leading-relaxed flex-1">{dis.description}</div>
                      {dis.source_id && (
                        <span className="text-[11px] font-mono font-medium text-[#737373] bg-white px-2 py-1 rounded border border-[#E5E5E5] flex items-center gap-1.5 shrink-0 shadow-sm">
                          <FileText className="h-[10px] w-[10px]" /> src:{dis.source_id.substring(0,4)}
                        </span>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        )
      case "risk_analysis":
        return (
          <div className="space-y-4 mt-8 animate-in slide-in-from-bottom-4 duration-500">
            <h3 className="text-[18px] font-semibold flex items-center gap-2 text-[#111111] mb-6">
              <ShieldAlert className="h-5 w-5" /> Risk Assessment
            </h3>
            <div className="rounded-xl border border-[#E5E5E5] bg-white shadow-sm overflow-hidden">
              <Table>
                <TableHeader className="bg-[#FAFAFA]">
                  <TableRow className="border-b border-[#E5E5E5] hover:bg-transparent">
                    <TableHead className="text-[11px] font-semibold text-[#737373] uppercase tracking-widest h-12 px-6">Risk Factor</TableHead>
                    <TableHead className="w-32 text-[11px] font-semibold text-[#737373] uppercase tracking-widest h-12 px-6">Severity</TableHead>
                    <TableHead className="text-[11px] font-semibold text-[#737373] uppercase tracking-widest h-12 px-6">Recommended Mitigation</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.risks?.map((risk: any, i: number) => (
                    <TableRow key={i} className="border-b border-[#E5E5E5] hover:bg-[#F7F7F7] transition-colors">
                      <TableCell className="font-medium text-[14px] text-[#111111] px-6 py-4 leading-relaxed">{risk.description}</TableCell>
                      <TableCell className="px-6 py-4">
                        <span className={`inline-flex items-center px-2.5 py-1 rounded-[4px] text-[11px] font-semibold tracking-wide uppercase border
                          ${risk.severity.toLowerCase() === "high" ? 'border-transparent bg-[#111111] text-white shadow-sm' : 'border-[#E5E5E5] bg-white text-[#737373]'}
                        `}>
                          {risk.severity}
                        </span>
                      </TableCell>
                      <TableCell className="text-[14px] text-[#525252] px-6 py-4 leading-relaxed">{risk.mitigation || "Requires further analysis"}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </div>
        )
      case "recommendation":
        return (
          <div className="space-y-8 mt-8 animate-in slide-in-from-bottom-4 duration-500">
            <div className="rounded-2xl border-none bg-[#111111] p-10 shadow-xl relative overflow-hidden">
              {/* Subtle background glow effect */}
              <div className="absolute top-0 right-0 w-64 h-64 bg-white/5 blur-3xl rounded-full -translate-y-1/2 translate-x-1/2 pointer-events-none" />
              
              <div className="relative z-10">
                <div className="flex items-center gap-3 mb-6">
                  <div className="flex items-center justify-center h-8 w-8 rounded-lg bg-white/10">
                    <Sparkles className="h-4 w-4 text-white" />
                  </div>
                  <h3 className="text-[12px] uppercase tracking-widest font-semibold text-[#A3A3A3]">Executive Recommendation</h3>
                </div>
                <p className="font-semibold text-[24px] leading-tight text-white mb-6 max-w-4xl">
                  {data.recommendation}
                </p>
                <p className="text-[16px] text-[#A3A3A3] leading-relaxed max-w-4xl">
                  {data.reasoning}
                </p>
              </div>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {data.factors?.map((f: any, i: number) => (
                <div key={i} className="rounded-xl border border-[#E5E5E5] bg-white p-6 shadow-sm flex flex-col justify-between hover:shadow-md transition-shadow">
                  <span className="text-[15px] text-[#111111] leading-relaxed mb-6 font-medium">{f.description}</span>
                  <div className="flex justify-start pt-4 border-t border-[#F5F5F5]">
                    <span className="inline-flex items-center text-[11px] uppercase font-mono tracking-widest font-medium text-[#737373] bg-[#FAFAFA] px-2.5 py-1 rounded border border-[#E5E5E5]">
                      {f.source_id ? `SRC: ${f.source_id.substring(0,8)}` : 'INTERNAL KNOWLEDGE'}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )
      case "decision_matrix":
        const options = Array.from(new Set(data.scores?.map((s: any) => s.option))) as string[]
        
        return (
          <div className="space-y-4 mt-8 animate-in slide-in-from-bottom-4 duration-500">
            <h3 className="text-[18px] font-semibold flex items-center gap-2 text-[#111111] mb-6">
              <GitMerge className="h-5 w-5" /> Evaluation Matrix
            </h3>
            <div className="rounded-xl border border-[#E5E5E5] bg-white shadow-sm overflow-hidden">
              <Table>
                <TableHeader className="bg-[#FAFAFA]">
                  <TableRow className="border-b border-[#E5E5E5] hover:bg-transparent">
                    <TableHead className="w-[30%] text-[11px] font-semibold text-[#737373] uppercase tracking-widest h-14 px-6">Evaluation Criterion</TableHead>
                    <TableHead className="w-[10%] text-center text-[11px] font-semibold text-[#737373] uppercase tracking-widest h-14">Weight</TableHead>
                    {options.map((opt, i) => (
                      <TableHead key={i} className="text-center font-bold text-[#111111] text-[14px] h-14 px-6 bg-white border-l border-[#F5F5F5]">
                        {opt}
                      </TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.criteria?.map((c: any, i: number) => (
                    <TableRow key={i} className="border-b border-[#E5E5E5] hover:bg-[#F7F7F7] transition-colors">
                      <TableCell className="font-medium text-[14px] text-[#111111] px-6 py-4">{c.name}</TableCell>
                      <TableCell className="text-center text-[13px] text-[#737373] font-mono">{c.weight}</TableCell>
                      {options.map((opt, j) => {
                        const score = data.scores?.find((s: any) => s.criterion === c.name && s.option === opt)
                        const isHigh = score?.numeric_score > 7;
                        return (
                          <TableCell key={j} className={`text-center py-4 border-l border-[#F5F5F5] ${isHigh ? 'bg-[#FAFAFA]/50' : ''}`}>
                            {score ? (
                              <div className="flex flex-col items-center gap-1.5">
                                <span className={`font-semibold text-[18px] ${isHigh ? 'text-[#111111]' : 'text-[#737373]'}`}>{score.numeric_score}</span>
                                <span className="text-[10px] uppercase font-mono font-medium tracking-widest text-[#737373] bg-white px-2 py-0.5 rounded border border-[#E5E5E5] shadow-sm">
                                  {score.categorical_assessment}
                                </span>
                              </div>
                            ) : <span className="text-[#A3A3A3]">-</span>}
                          </TableCell>
                        )
                      })}
                    </TableRow>
                  ))}
                  <TableRow className="bg-[#111111] hover:bg-[#111111]">
                    <TableCell className="font-bold text-white text-[15px] px-6 py-5">Weighted Score</TableCell>
                    <TableCell className="border-r border-[#333333]"></TableCell>
                    {options.map((opt, i) => {
                      const totals = options.map(o => data.total_scores?.[o] || 0)
                      const max = Math.max(...totals)
                      const currentScore = data.total_scores?.[opt] || 0
                      const isWinner = currentScore === max && max > 0

                      return (
                        <TableCell key={i} className="text-center py-5 border-l border-[#333333]">
                          <div className="flex flex-col items-center gap-2">
                            <span className={`font-bold text-[24px] ${isWinner ? 'text-white' : 'text-[#A3A3A3]'}`}>
                              {currentScore.toFixed(2)}
                            </span>
                            {isWinner && (
                              <span className="text-[10px] uppercase font-bold tracking-widest bg-white text-black px-2.5 py-1 rounded-[4px] shadow-sm">
                                Recommended
                              </span>
                            )}
                          </div>
                        </TableCell>
                      )
                    })}
                  </TableRow>
                </TableBody>
              </Table>
            </div>
          </div>
        )
      default:
        return (
          <div className="mt-8 rounded-xl border border-[#E5E5E5] bg-white p-8 shadow-sm">
            <pre className="whitespace-pre-wrap text-[13px] font-mono text-[#525252] overflow-x-auto">
              {JSON.stringify(data, null, 2)}
            </pre>
          </div>
        )
    }
  }

  return (
    <div className="flex w-full flex-col max-w-[1150px] mx-auto space-y-8 pb-12 pt-8 animate-in fade-in duration-300">
      
      {/* HEADER SECTION */}
      <div className="flex items-end justify-between border-b border-[#E5E5E5] pb-6">
        <div className="flex flex-col space-y-2">
          <span className="text-[11px] font-semibold text-[#737373] tracking-[0.05em] uppercase">
            Workstation
          </span>
          <h2 className="text-[28px] md:text-[30px] font-semibold tracking-[-0.025em] text-[#111111] leading-none">
            Decision Intelligence
          </h2>
          <p className="text-[13px] text-[#525252] max-w-[600px]">
            Generate objective analytical frameworks and automated evaluations based on indexed organizational knowledge.
          </p>
        </div>
      </div>

      {/* COMPOSER */}
      <div className="rounded-xl border border-[#E5E5E5] bg-white shadow-[0_4px_24px_rgba(0,0,0,0.04)] overflow-hidden">
        <div className="p-6 border-b border-[#E5E5E5] bg-[#FAFAFA] flex items-center gap-3">
          <BrainCircuit className="h-5 w-5 text-[#111111]" />
          <div>
            <h3 className="text-[15px] font-semibold text-[#111111]">What decision do you need to make?</h3>
            <p className="text-[13px] text-[#737373] mt-0.5">The system will autonomously determine the optimal analytical framework.</p>
          </div>
        </div>
        <div className="p-6 bg-white">
          <form onSubmit={handleSubmit} className="flex flex-col gap-5">
            <div className="relative flex-1">
              <input 
                type="text"
                placeholder="E.g., Compare React and Angular for our new project, or what are the risks of migrating to AWS?" 
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                disabled={analyzeMutation.isPending}
                className="w-full text-[15px] text-[#111111] placeholder:text-[#A3A3A3] p-4 rounded-lg border border-[#D4D4D4] focus:outline-none focus:border-[#111111] focus:ring-1 focus:ring-[#111111] transition-all disabled:opacity-50 disabled:bg-[#FAFAFA]"
              />
            </div>
            <div className="flex justify-end border-t border-[#F5F5F5] pt-5">
              <button 
                type="submit" 
                disabled={!query.trim() || analyzeMutation.isPending} 
                className="group flex items-center h-10 px-6 rounded-md bg-[#111111] text-white text-[14px] font-medium transition-all hover:bg-[#1A1A1A] hover:shadow-[0_2px_8px_rgba(0,0,0,0.15)] active:scale-95 disabled:opacity-50 disabled:hover:shadow-none disabled:cursor-not-allowed"
              >
                {analyzeMutation.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    Synthesizing...
                  </>
                ) : (
                  <>
                    Analyze Decision <ArrowRight className="ml-2 h-4 w-4 transition-transform group-hover:translate-x-1" />
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      </div>

      {analyzeMutation.isError && (
        <div className="p-5 bg-[#FEF2F2] text-[#B91C1C] rounded-xl border border-[#FECACA] animate-in fade-in flex items-start gap-3 shadow-sm">
          <AlertTriangle className="h-5 w-5 shrink-0 mt-0.5 text-[#DC2626]" />
          <div>
            <h4 className="font-semibold text-[15px] text-[#991B1B]">Analysis Failed</h4>
            <p className="text-[14px] mt-1 text-[#B91C1C] leading-relaxed">{(analyzeMutation.error as any).message}</p>
          </div>
        </div>
      )}

      {analyzeMutation.data && (
        <div className="space-y-6 animate-in slide-in-from-bottom-4 duration-500 pb-12">
          {/* Metadata Bar */}
          <div className="flex flex-wrap items-center justify-between gap-4 p-4 rounded-lg bg-[#FAFAFA] border border-[#E5E5E5] shadow-sm">
            <div className="flex items-center gap-8">
              <div className="flex flex-col gap-1">
                <span className="text-[10px] uppercase tracking-widest text-[#737373] font-bold">Analysis Type</span>
                <span className="text-[13px] font-bold px-2.5 py-0.5 rounded-[4px] bg-[#111111] text-white tracking-wide uppercase">
                  {analyzeMutation.data.decision_type.replace("_", " ")}
                </span>
              </div>
              
              <div className="flex flex-col gap-1">
                <span className="text-[10px] uppercase tracking-widest text-[#737373] font-bold">Confidence</span>
                <span className="text-[15px] font-mono font-bold text-[#111111]">
                  {(analyzeMutation.data.confidence * 100).toFixed(0)}%
                </span>
              </div>
            </div>
            
            {analyzeMutation.data.decision_trace && (
              <div className="flex items-center gap-6 text-[13px] font-mono font-medium text-[#525252]">
                <span className="flex items-center gap-2 bg-white px-3 py-1.5 rounded-md border border-[#E5E5E5] shadow-sm">
                  <Activity className="h-4 w-4 text-[#A3A3A3]" /> {analyzeMutation.data.decision_trace.latency_ms.toFixed(0)}ms
                </span>
                <span className="flex items-center gap-2 bg-white px-3 py-1.5 rounded-md border border-[#E5E5E5] shadow-sm">
                  <span className="h-2 w-2 rounded-full bg-[#111111]"></span>
                  {analyzeMutation.data.decision_trace.llm_calls} LLM Calls
                </span>
              </div>
            )}
          </div>

          {/* Core Results */}
          {renderDecisionContent(analyzeMutation.data)}
        </div>
      )}
    </div>
  )
}
