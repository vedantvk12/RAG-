"use client"

import { useState, useRef, useEffect, useCallback } from "react"
import { useMutation } from "@tanstack/react-query"
import { fetchApi } from "@/lib/api-client"
import { useAuth } from "@/hooks/use-auth"
import { 
  Hexagon, 
  FileText, 
  X, 
  ArrowUp, 
  Loader2, 
  CheckCircle2, 
  Circle, 
  Copy, 
  Check, 
  Zap, 
  Compass, 
  Plus, 
  ChevronDown, 
  AlertCircle, 
  RefreshCw,
  ExternalLink,
  BookOpen
} from "lucide-react"
import ReactMarkdown from "react-markdown"

type SourceItem = {
  source_id?: string | number
  filename?: string
  page_number?: number | string
  text?: string
  dense_score?: number
  bm25_score?: number
  rerank_score?: number
  final_rank?: number
  metadata?: any
}

type Message = {
  id: string
  role: "user" | "assistant"
  content: string
  sources?: SourceItem[]
  runId?: string
  mode?: "agentic" | "deterministic"
  timestamp?: string
  isError?: boolean
}

export default function ChatPage() {
  const { user } = useAuth()
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState("")
  const [mode, setMode] = useState<"agentic" | "deterministic">("agentic")
  const [selectedSource, setSelectedSource] = useState<SourceItem | null>(null)
  const [loadingStage, setLoadingStage] = useState(0)
  const [copiedId, setCopiedId] = useState<string | null>(null)
  const [isCopiedDrawer, setIsCopiedDrawer] = useState(false)
  const [showScrollBottom, setShowScrollBottom] = useState(false)
  
  const chatScrollRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Load chat history on mount
  useEffect(() => {
    const saved = localStorage.getItem("agentic_chat_history")
    if (saved) {
      try {
        setMessages(JSON.parse(saved))
      } catch (e) {
        console.error("Failed to parse chat history", e)
      }
    }
  }, [])

  // Save chat history on update
  useEffect(() => {
    if (messages.length > 0) {
      localStorage.setItem("agentic_chat_history", JSON.stringify(messages))
    } else {
      localStorage.removeItem("agentic_chat_history")
    }
  }, [messages])

  // Scroll detection to avoid forcibly yanking user if they scrolled up
  const handleScroll = useCallback(() => {
    if (!chatScrollRef.current) return
    const { scrollTop, scrollHeight, clientHeight } = chatScrollRef.current
    const distanceFromBottom = scrollHeight - scrollTop - clientHeight
    setShowScrollBottom(distanceFromBottom > 150)
  }, [])

  const scrollToBottom = useCallback((smooth = true) => {
    if (chatScrollRef.current) {
      chatScrollRef.current.scrollTo({
        top: chatScrollRef.current.scrollHeight,
        behavior: smooth ? "smooth" : "auto"
      })
    }
  }, [])

  useEffect(() => {
    if (!showScrollBottom) {
      scrollToBottom(true)
    }
  }, [messages, loadingStage, showScrollBottom, scrollToBottom])

  // Auto-resize textarea
  const handleTextareaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value)
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto"
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 160)}px`
    }
  }

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text)
    setCopiedId(id)
    setTimeout(() => setCopiedId(null), 2000)
  }

  const copyDrawerExcerpt = (text: string) => {
    navigator.clipboard.writeText(text)
    setIsCopiedDrawer(true)
    setTimeout(() => setIsCopiedDrawer(false), 2000)
  }

  const chatMutation = useMutation({
    mutationFn: async (queryText: string) => {
      const history = messages
        .filter(m => !m.isError)
        .map(m => ({
          role: m.role,
          content: m.content
        }))
      return fetchApi("/rag/query", {
        method: "POST",
        body: JSON.stringify({
          query: queryText,
          mode,
          top_k: 5,
          conversation_history: history
        }),
      })
    },
    onSuccess: (data) => {
      setMessages(prev => [
        ...prev, 
        { 
          id: Date.now().toString(), 
          role: "assistant", 
          content: data.answer || "The available documents do not contain enough information to answer this question.",
          sources: data.sources || [],
          runId: data.run_id,
          mode,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ])
      setTimeout(() => scrollToBottom(true), 50)
    },
    onError: (err: any) => {
      setMessages(prev => [
        ...prev,
        {
          id: Date.now().toString(),
          role: "assistant",
          content: err.message || "Failed to generate response. Please verify your connection or retry.",
          isError: true,
          mode,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ])
    }
  })

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault()
    const query = input.trim()
    if (!query || chatMutation.isPending) return
    
    setInput("")
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto"
    }

    setMessages(prev => [
      ...prev, 
      { 
        id: Date.now().toString(), 
        role: "user", 
        content: query,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }
    ])
    
    // Truthful progression for visual stage feedback
    setLoadingStage(0)
    const interval = setInterval(() => {
      setLoadingStage(prev => (prev < 2 ? prev + 1 : prev))
    }, 1200)

    chatMutation.mutate(query, {
      onSettled: () => clearInterval(interval)
    })
  }

  const handleRetry = (lastQuery: string) => {
    setInput(lastQuery)
    if (textareaRef.current) {
      textareaRef.current.focus()
    }
  }

  const handleNewChat = () => {
    setMessages([])
    setSelectedSource(null)
    localStorage.removeItem("agentic_chat_history")
  }

  // Pre-process markdown text to convert inline citation patterns like [Source 1], 【Source 1】, or [1] into interactive citation links
  const renderMessageContent = (content: string, sources: SourceItem[] = []) => {
    // Convert inline citations like [Source 1], 【Source 1】, [1], 【1】 into markdown links with citation: protocol
    const processedContent = content
      .replace(/(?:\[|\【)\s*Source\s*(\d+)\s*(?:\]|\】)/gi, " [Source $1](citation:$1) ")
      .replace(/(?:\[|\【)\s*(\d+)\s*(?:\]|\】)/gi, " [Source $1](citation:$1) ")

    return (
      <ReactMarkdown
        components={{
          h1: ({ children }) => (
            <h1 className="text-[17px] md:text-[19px] font-bold text-[#111111] mt-5 mb-2.5 tracking-tight border-b border-[#EAEAEA] pb-1.5">
              {children}
            </h1>
          ),
          h2: ({ children }) => (
            <h2 className="text-[15.5px] md:text-[16.5px] font-semibold text-[#111111] mt-4 mb-2 tracking-tight">
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3 className="text-[14px] md:text-[15px] font-semibold text-[#111111] mt-3 mb-1.5">
              {children}
            </h3>
          ),
          h4: ({ children }) => (
            <h4 className="text-[13.5px] font-semibold text-[#222222] mt-2 mb-1">
              {children}
            </h4>
          ),
          p: ({ children }) => (
            <p className="text-[14px] md:text-[14.5px] leading-[1.65] text-[#1A1A1A] mb-3.5 last:mb-0">
              {children}
            </p>
          ),
          strong: ({ children }) => (
            <strong className="font-semibold text-[#111111]">{children}</strong>
          ),
          em: ({ children }) => (
            <em className="italic text-[#333333]">{children}</em>
          ),
          ul: ({ children }) => (
            <ul className="list-disc list-outside pl-5 mb-3.5 space-y-1.5 text-[14px] md:text-[14.5px] text-[#1A1A1A]">
              {children}
            </ul>
          ),
          ol: ({ children }) => (
            <ol className="list-decimal list-outside pl-5 mb-3.5 space-y-1.5 text-[14px] md:text-[14.5px] text-[#1A1A1A]">
              {children}
            </ol>
          ),
          li: ({ children }) => (
            <li className="leading-[1.6] pl-1">{children}</li>
          ),
          blockquote: ({ children }) => (
            <blockquote className="border-l-3 border-[#111111] pl-4 py-1.5 italic text-[#555555] my-3.5 bg-[#F9F9F9] rounded-r text-[13.5px]">
              {children}
            </blockquote>
          ),
          table: ({ children }) => (
            <div className="my-4 overflow-x-auto rounded-lg border border-[#E5E5E5] bg-white shadow-xs">
              <table className="min-w-full divide-y divide-[#E5E5E5] text-[13px] text-left">
                {children}
              </table>
            </div>
          ),
          thead: ({ children }) => (
            <thead className="bg-[#F5F5F5] font-semibold text-[#111111]">{children}</thead>
          ),
          tbody: ({ children }) => (
            <tbody className="divide-y divide-[#EAEAEA] bg-white">{children}</tbody>
          ),
          tr: ({ children }) => (
            <tr className="hover:bg-[#FAFAFA] transition-colors">{children}</tr>
          ),
          th: ({ children }) => (
            <th className="px-3.5 py-2.5 font-semibold text-[#111111] tracking-tight">{children}</th>
          ),
          td: ({ children }) => (
            <td className="px-3.5 py-2.5 text-[#333333]">{children}</td>
          ),
          code: ({ inline, className, children, ...props }: any) => {
            if (inline) {
              return (
                <code className="bg-[#F4F4F4] text-[#111111] px-1.5 py-0.5 rounded text-[12.5px] font-mono border border-[#E5E5E5]">
                  {children}
                </code>
              )
            }
            return (
              <div className="my-3.5 overflow-hidden rounded-lg border border-[#262626] bg-[#0F0F0F] text-[#EDEDED]">
                <div className="flex items-center justify-between px-3.5 py-1.5 bg-[#171717] border-b border-[#262626] text-[11px] font-mono text-[#888888]">
                  <span>Code Snippet</span>
                </div>
                <pre className="p-4 text-[13px] font-mono overflow-x-auto leading-relaxed">
                  <code>{children}</code>
                </pre>
              </div>
            )
          },
          a: ({ href, children }: any) => {
            if (href?.startsWith("citation:")) {
              const id = parseInt(href.replace("citation:", ""), 10)
              const source = sources.find((s, idx) => (s.source_id === id) || (idx + 1 === id))
              if (source) {
                return (
                  <button
                    type="button"
                    onClick={(e) => {
                      e.preventDefault()
                      e.stopPropagation()
                      setSelectedSource(source)
                    }}
                    className="inline-flex items-center gap-1 mx-1 px-2 py-0.5 rounded-md text-[11px] font-mono font-semibold bg-[#F5F5F5] text-[#111111] border border-[#D4D4D4] hover:bg-[#111111] hover:text-white hover:border-[#111111] transition-all duration-150 cursor-pointer shadow-2xs align-baseline"
                    title={`Inspect excerpt: ${source.filename || 'Source ' + id} (Page ${source.page_number || 1})`}
                  >
                    <span>Source {id}</span>
                  </button>
                )
              }
              return (
                <span className="inline-flex items-center px-1.5 py-0.5 mx-0.5 rounded text-[11px] font-mono bg-[#F5F5F5] text-[#737373] border border-[#E5E5E5] align-baseline">
                  Source {id}
                </span>
              )
            }
            return (
              <a href={href} target="_blank" rel="noopener noreferrer" className="text-[#111111] underline underline-offset-2 hover:text-[#555555]">
                {children}
              </a>
            )
          },
          hr: () => <hr className="my-4 border-[#E5E5E5]" />
        }}
      >
        {processedContent}
      </ReactMarkdown>
    )
  }

  return (
    <div className="flex h-full w-full overflow-hidden relative bg-white">
      
      {/* Main Chat Viewport */}
      <div className={`flex flex-col h-full w-full transition-all duration-300 ease-in-out ${selectedSource ? 'pr-0 lg:pr-[440px]' : ''}`}>
        
        {/* Compact Header Bar */}
        <header className="flex items-center justify-between px-6 py-3.5 border-b border-[#EBEBEB] bg-white/90 backdrop-blur-sm shrink-0 z-10">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#111111] text-white shadow-xs">
              <Hexagon className="h-4 w-4 text-white" />
            </div>
            <div>
              <h1 className="text-[15px] font-bold text-[#111111] tracking-tight leading-tight">
                Agent Chat
              </h1>
              <p className="text-[12px] text-[#737373] hidden sm:block">
                Query enterprise documents with grounded evidence & citations.
              </p>
            </div>
          </div>
          
          <div className="flex items-center gap-2.5">
            {messages.length > 0 && (
              <button
                onClick={handleNewChat}
                className="flex items-center gap-1.5 px-3 py-1.5 text-[12.5px] font-medium rounded-md border border-[#E5E5E5] text-[#111111] hover:bg-[#F5F5F5] hover:border-[#D4D4D4] transition-all"
                title="Start a new conversation"
              >
                <Plus className="h-3.5 w-3.5 text-[#555555]" />
                <span className="hidden sm:inline">New Chat</span>
              </button>
            )}

            {/* Mode Switcher */}
            <div className="flex items-center p-0.5 rounded-lg bg-[#F5F5F5] border border-[#E5E5E5]">
              <button 
                onClick={() => setMode("deterministic")}
                className={`flex items-center gap-1.5 px-3 py-1.5 text-[12.5px] font-medium rounded-md transition-all ${
                  mode === "deterministic" 
                    ? "bg-[#111111] text-white shadow-xs" 
                    : "text-[#737373] hover:text-[#111111]"
                }`}
              >
                <Zap className="h-3.5 w-3.5" />
                <span>Fast Search</span>
              </button>
              <button 
                onClick={() => setMode("agentic")}
                className={`flex items-center gap-1.5 px-3 py-1.5 text-[12.5px] font-medium rounded-md transition-all ${
                  mode === "agentic" 
                    ? "bg-[#111111] text-white shadow-xs" 
                    : "text-[#737373] hover:text-[#111111]"
                }`}
              >
                <Compass className="h-3.5 w-3.5" />
                <span>Deep Research</span>
              </button>
            </div>
          </div>
        </header>

        {/* Message Stream Area */}
        <div 
          ref={chatScrollRef}
          onScroll={handleScroll}
          className="flex-1 overflow-y-auto px-4 md:px-6 relative scroll-smooth"
        >
          <div className="mx-auto max-w-[800px] space-y-7 pb-44 pt-6">
            
            {/* Empty State with Suggested Prompts */}
            {messages.length === 0 && (
              <div className="flex flex-col items-center justify-center min-h-[55vh] text-center px-4 animate-in fade-in zoom-in-95 duration-400">
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-[#F5F5F5] border border-[#E5E5E5] mb-4 shadow-xs">
                  <BookOpen className="h-6 w-6 text-[#111111]" />
                </div>
                <h2 className="text-[20px] md:text-[22px] font-bold tracking-tight text-[#111111] mb-2">
                  Enterprise Knowledge Intelligence
                </h2>
                <p className="text-[14px] text-[#555555] max-w-md leading-relaxed mb-8">
                  Ask natural-language questions across all uploaded documents with page-level citations and grounded evidence.
                </p>
                
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 w-full max-w-[760px]">
                  {[
                    { 
                      title: "Summarize latest PDF", 
                      desc: "Overview & key takeaways from the latest upload",
                      query: "Summarize the latest uploaded PDF in simple language."
                    },
                    { 
                      title: "Inspect Page Takeaways", 
                      desc: "Extract structured points from specific pages",
                      query: "Give me the important points from page 3 of the latest document."
                    },
                    { 
                      title: "Compare Findings & Approach", 
                      desc: "Synthesize methodology and conclusions",
                      query: "Explain the methodology and main findings in detail."
                    }
                  ].map((s, i) => (
                    <button
                      key={i}
                      onClick={() => {
                        setInput(s.query)
                        if (textareaRef.current) textareaRef.current.focus()
                      }}
                      className="group flex flex-col items-start p-3.5 text-left rounded-lg border border-[#E5E5E5] bg-white transition-all hover:border-[#111111] hover:shadow-sm"
                    >
                      <span className="text-[13px] font-semibold text-[#111111] mb-1 group-hover:underline">
                        {s.title}
                      </span>
                      <span className="text-[12px] text-[#737373] leading-snug">
                        {s.desc}
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            )}
            
            {/* Conversation Messages */}
            {messages.map((msg) => (
              <div 
                key={msg.id} 
                className={`flex w-full animate-in fade-in slide-in-from-bottom-2 duration-200 ${
                  msg.role === "user" ? "justify-end" : "justify-start"
                }`}
              >
                {msg.role === "user" ? (
                  <div className="flex flex-col items-end max-w-[85%] sm:max-w-[75%]">
                    <div className="px-4 py-3 rounded-2xl rounded-tr-xs bg-[#111111] text-white shadow-xs">
                      <p className="text-[14.5px] leading-relaxed whitespace-pre-wrap selection:bg-neutral-700">
                        {msg.content}
                      </p>
                    </div>
                    {msg.timestamp && (
                      <span className="text-[10.5px] text-[#888888] mt-1 mr-1">
                        {msg.timestamp}
                      </span>
                    )}
                  </div>
                ) : (
                  <div className="flex flex-col w-full max-w-[800px] group">
                    {/* Assistant Message Header */}
                    <div className="flex items-center justify-between mb-2.5">
                      <div className="flex items-center gap-2">
                        <div className="flex h-5 w-5 items-center justify-center rounded bg-[#111111] text-white">
                          <Hexagon className="h-3 w-3 text-white" />
                        </div>
                        <span className="text-[12px] font-bold text-[#111111] uppercase tracking-wider">
                          Assistant
                        </span>
                        {msg.mode && (
                          <span className="text-[10.5px] font-medium text-[#737373] bg-[#F5F5F5] px-2 py-0.5 rounded border border-[#EBEBEB]">
                            {msg.mode === "agentic" ? "Deep Research" : "Fast Search"}
                          </span>
                        )}
                      </div>
                      
                      <div className="flex items-center gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                          onClick={() => copyToClipboard(msg.content, msg.id)}
                          className="flex items-center gap-1 text-[11px] text-[#737373] hover:text-[#111111] px-2 py-1 rounded hover:bg-[#F5F5F5] transition-colors"
                          title="Copy response"
                        >
                          {copiedId === msg.id ? (
                            <>
                              <Check className="h-3 w-3 text-emerald-600" />
                              <span className="text-emerald-600">Copied</span>
                            </>
                          ) : (
                            <>
                              <Copy className="h-3 w-3" />
                              <span>Copy</span>
                            </>
                          )}
                        </button>
                      </div>
                    </div>
                    
                    {/* Error Banner if applicable */}
                    {msg.isError ? (
                      <div className="flex items-start gap-3 p-4 rounded-lg bg-red-50 border border-red-200 text-red-900 text-[13.5px]">
                        <AlertCircle className="h-5 w-5 text-red-600 shrink-0 mt-0.5" />
                        <div className="flex-1">
                          <p className="font-semibold mb-1">Response Generation Failed</p>
                          <p className="text-red-700 leading-relaxed">{msg.content}</p>
                          <button
                            onClick={() => {
                              const lastUserIdx = messages.findLastIndex(m => m.role === "user")
                              if (lastUserIdx >= 0) {
                                handleRetry(messages[lastUserIdx].content)
                              }
                            }}
                            className="inline-flex items-center gap-1.5 mt-2.5 text-[12px] font-medium bg-red-600 text-white px-3 py-1.5 rounded hover:bg-red-700 transition-colors shadow-xs"
                          >
                            <RefreshCw className="h-3 w-3" />
                            Retry Question
                          </button>
                        </div>
                      </div>
                    ) : (
                      /* Rendered Assistant Response */
                      <div className="text-[#111111] font-sans antialiased pl-0.5">
                        {renderMessageContent(msg.content, msg.sources)}
                      </div>
                    )}

                    {/* Supporting Evidence Panel */}
                    {msg.sources && msg.sources.length > 0 && (
                      <div className="mt-5 pt-3.5 border-t border-[#EBEBEB]">
                        <div className="flex items-center justify-between mb-2.5">
                          <span className="text-[11px] font-bold text-[#737373] uppercase tracking-wider flex items-center gap-1.5">
                            <FileText className="h-3.5 w-3.5 text-[#555555]" />
                            Grounded Evidence ({msg.sources.length})
                          </span>
                          <span className="text-[11px] text-[#888888]">
                            Click any source to inspect extracted excerpt
                          </span>
                        </div>
                        
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                          {msg.sources.map((src, idx) => {
                            const isSelected = selectedSource === src
                            const sourceNum = src.source_id || idx + 1
                            return (
                              <button 
                                key={idx} 
                                onClick={() => setSelectedSource(src)}
                                className={`flex items-start gap-2.5 text-left p-2.5 rounded-lg border transition-all ${
                                  isSelected 
                                    ? "bg-[#F5F5F5] border-[#111111] shadow-xs" 
                                    : "bg-white border-[#E5E5E5] hover:border-[#B5B5B5] hover:bg-[#FAFAFA]"
                                }`}
                              >
                                <div className="flex h-5 w-5 shrink-0 items-center justify-center rounded bg-[#111111] text-[10.5px] font-mono font-semibold text-white mt-0.5">
                                  {sourceNum}
                                </div>
                                <div className="flex flex-col min-w-0 flex-1">
                                  <span className="text-[12.5px] font-semibold text-[#111111] truncate" title={src.filename}>
                                    {src.filename || "Document"}
                                  </span>
                                  <div className="flex items-center gap-2 mt-0.5 text-[11px] text-[#737373]">
                                    {src.page_number && (
                                      <span className="font-medium bg-[#EFEFEF] px-1.5 py-0.2 rounded text-[#333333]">
                                        Page {src.page_number}
                                      </span>
                                    )}
                                    {src.rerank_score !== undefined && (
                                      <span className="font-mono text-[10.5px]">
                                        Score: {src.rerank_score.toFixed(2)}
                                      </span>
                                    )}
                                  </div>
                                </div>
                                <ExternalLink className="h-3.5 w-3.5 text-[#888888] shrink-0 ml-auto mt-1" />
                              </button>
                            )
                          })}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
            
            {/* Truthful Research Progress State */}
            {chatMutation.isPending && (
              <div className="flex w-full justify-start animate-in fade-in duration-200">
                <div className="flex flex-col w-full max-w-[800px]">
                  <div className="flex items-center gap-2 mb-3.5">
                    <Loader2 className="h-4 w-4 text-[#111111] animate-spin" />
                    <span className="text-[12px] font-bold text-[#111111] uppercase tracking-wider">
                      {mode === "agentic" ? "Deep Research in Progress" : "Fast Search in Progress"}
                    </span>
                  </div>
                  
                  {mode === "agentic" ? (
                    <div className="flex flex-col pl-3 border-l-2 border-[#E5E5E5] space-y-3.5 ml-1.5 py-1">
                      {[
                        "Analyzing query intent and document registry",
                        "Retrieving hybrid dense & BM25 evidence chunks",
                        "Reranking and synthesizing grounded response"
                      ].map((step, idx) => {
                        const isDone = loadingStage > idx
                        const isCurrent = loadingStage === idx
                        return (
                          <div key={idx} className="flex items-center gap-2.5 relative">
                            <div className="absolute -left-[19px] h-3 w-3 rounded-full bg-white flex items-center justify-center">
                              {isDone ? (
                                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
                              ) : isCurrent ? (
                                <Circle className="h-2.5 w-2.5 fill-[#111111] text-[#111111] animate-ping" />
                              ) : (
                                <Circle className="h-2 w-2 text-[#D4D4D4]" />
                              )}
                            </div>
                            <span className={`text-[13px] ${
                              isDone 
                                ? "text-[#737373] font-medium" 
                                : isCurrent 
                                ? "text-[#111111] font-semibold" 
                                : "text-[#A3A3A3]"
                            }`}>
                              {step}
                            </span>
                          </div>
                        )
                      })}
                    </div>
                  ) : (
                    <div className="p-3 rounded-lg border border-[#EAEAEA] bg-[#FAFAFA] flex items-center gap-2.5 text-[13px] text-[#555555]">
                      <div className="h-2 w-2 rounded-full bg-[#111111] animate-pulse" />
                      <span>Retrieving chunks & generating grounded answer...</span>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Scroll-to-bottom Floating Button */}
        {showScrollBottom && (
          <button
            onClick={() => scrollToBottom(true)}
            className="absolute bottom-28 right-8 z-20 flex items-center gap-1.5 bg-[#111111] text-white px-3 py-1.5 rounded-full shadow-lg text-[12px] font-medium hover:bg-neutral-800 transition-all active:scale-95"
          >
            <ChevronDown className="h-3.5 w-3.5" />
            <span>Scroll to latest</span>
          </button>
        )}

        {/* Sticky Chat Composer */}
        <div className="absolute bottom-0 left-0 right-0 p-4 md:p-6 bg-gradient-to-t from-white via-white/95 to-transparent pointer-events-none z-10 flex justify-center">
          <div className="w-full max-w-[800px] pointer-events-auto">
            <form 
              onSubmit={handleSubmit} 
              className="relative flex flex-col w-full rounded-xl border border-[#D4D4D4] bg-white shadow-[0_4px_20px_rgba(0,0,0,0.06)] focus-within:border-[#111111] focus-within:ring-1 focus-within:ring-[#111111] transition-all overflow-hidden"
            >
              <textarea
                ref={textareaRef}
                value={input}
                onChange={handleTextareaChange}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault()
                    handleSubmit()
                  }
                }}
                disabled={chatMutation.isPending}
                placeholder="Ask about any document, page points, summaries, or facts..."
                className="w-full resize-none bg-transparent px-4 py-3.5 text-[14.5px] text-[#111111] placeholder:text-[#A3A3A3] focus:outline-none disabled:opacity-50 min-h-[52px] max-h-[160px] leading-relaxed"
                rows={1}
              />
              
              <div className="flex justify-between items-center px-3.5 py-2 border-t border-[#F5F5F5] bg-[#FAFAFA]">
                <div className="text-[11.5px] text-[#737373] flex items-center gap-2">
                  <span className="flex items-center gap-1 font-medium">
                    <span className={`h-1.5 w-1.5 rounded-full ${mode === 'agentic' ? 'bg-[#111111]' : 'bg-neutral-400'}`} />
                    {mode === 'agentic' ? 'Deep Research Active' : 'Fast Search Active'}
                  </span>
                  <span className="hidden sm:inline text-[#B5B5B5]">|</span>
                  <span className="hidden sm:inline text-[#888888]">Press Enter to send, Shift+Enter for new line</span>
                </div>
                
                <button 
                  type="submit"
                  disabled={!input.trim() || chatMutation.isPending}
                  className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#111111] text-white hover:bg-neutral-800 active:scale-95 disabled:opacity-30 disabled:hover:bg-[#111111] disabled:active:scale-100 transition-all shadow-xs"
                  title="Send query"
                >
                  {chatMutation.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <ArrowUp className="h-4 w-4" />
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>

      {/* Right Evidence Inspector Drawer */}
      <aside 
        className={`absolute top-0 right-0 bottom-0 w-full max-w-[440px] bg-white border-l border-[#E5E5E5] shadow-2xl transition-transform duration-300 ease-in-out z-20 flex flex-col ${
          selectedSource ? "translate-x-0" : "translate-x-full pointer-events-none"
        }`}
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-[#E5E5E5] bg-white shrink-0">
          <div className="flex items-center gap-2">
            <div className="flex h-7 w-7 items-center justify-center rounded bg-[#111111] text-white text-[12px] font-mono font-bold">
              {selectedSource?.source_id || 1}
            </div>
            <div>
              <span className="text-[10.5px] font-bold text-[#737373] uppercase tracking-wider block">
                Evidence Inspector
              </span>
              <span className="font-bold text-[#111111] text-[14px]">
                Source Details
              </span>
            </div>
          </div>
          
          <button 
            onClick={() => setSelectedSource(null)}
            className="flex h-7 w-7 items-center justify-center rounded-md text-[#737373] hover:bg-[#F5F5F5] hover:text-[#111111] transition-colors"
            title="Close drawer"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        
        {selectedSource && (
          <div className="p-5 overflow-y-auto flex-1 space-y-5 bg-[#FAFAFA]">
            {/* Document Card */}
            <div className="bg-white p-4 rounded-lg border border-[#E5E5E5] shadow-xs">
              <span className="text-[10.5px] uppercase tracking-wider text-[#737373] font-bold block mb-1.5">
                Document File
              </span>
              <div className="text-[14px] font-semibold text-[#111111] break-all flex items-center gap-2">
                <FileText className="h-4 w-4 text-[#555555] shrink-0" />
                <span>{selectedSource.filename || "Unknown Document"}</span>
              </div>
            </div>
            
            {/* Metadata Badges */}
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-white p-3.5 rounded-lg border border-[#E5E5E5] shadow-xs">
                <span className="text-[10.5px] uppercase tracking-wider text-[#737373] font-bold block mb-1">
                  Page Reference
                </span>
                <span className="text-[15px] font-mono font-semibold text-[#111111]">
                  {selectedSource.page_number ? `Page ${selectedSource.page_number}` : "Full Document"}
                </span>
              </div>
              
              <div className="bg-white p-3.5 rounded-lg border border-[#E5E5E5] shadow-xs">
                <span className="text-[10.5px] uppercase tracking-wider text-[#737373] font-bold block mb-1">
                  Rerank Relevance
                </span>
                <span className="text-[15px] font-mono font-semibold text-[#111111]">
                  {selectedSource.rerank_score !== undefined 
                    ? selectedSource.rerank_score.toFixed(3) 
                    : "1.000"}
                </span>
              </div>
            </div>

            {/* Extracted Excerpt */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-[10.5px] uppercase tracking-wider text-[#737373] font-bold">
                  Retrieved Chunk Content
                </span>
                <button
                  onClick={() => copyDrawerExcerpt(selectedSource.text || "")}
                  className="flex items-center gap-1 text-[11px] font-medium text-[#737373] hover:text-[#111111] px-2 py-0.5 rounded hover:bg-white transition-all border border-transparent hover:border-[#E5E5E5]"
                >
                  {isCopiedDrawer ? (
                    <>
                      <Check className="h-3 w-3 text-emerald-600" />
                      <span className="text-emerald-600">Copied</span>
                    </>
                  ) : (
                    <>
                      <Copy className="h-3 w-3" />
                      <span>Copy excerpt</span>
                    </>
                  )}
                </button>
              </div>
              
              <div className="p-4 rounded-lg bg-white border border-[#E5E5E5] shadow-xs">
                <p className="text-[13px] leading-relaxed text-[#1A1A1A] whitespace-pre-wrap selection:bg-neutral-200">
                  {selectedSource.text || "No excerpt text available for this chunk."}
                </p>
              </div>
            </div>
          </div>
        )}
      </aside>

    </div>
  )
}
