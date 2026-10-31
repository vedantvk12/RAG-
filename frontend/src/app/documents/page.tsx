"use client"

import { useState, useRef } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { fetchApi } from "@/lib/api-client"
import { useAuth } from "@/hooks/use-auth"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog"
import { UploadCloud, Loader2, FileText, Trash2, RefreshCw, CheckCircle2, AlertCircle, ArrowRight, Network, X } from "lucide-react"

export default function DocumentsPage() {
  const queryClient = useQueryClient()
  const { currentOrgId } = useAuth()
  const [file, setFile] = useState<File | null>(null)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const { data: documents, isLoading } = useQuery({
    queryKey: ["documents", currentOrgId],
    queryFn: () => fetchApi(`/organizations/${currentOrgId}/documents/`),
    enabled: !!currentOrgId,
    refetchInterval: (data) => {
      const isProcessing = Array.isArray(data) && data.some((doc: any) => doc.status === "processing")
      return isProcessing ? 5000 : false
    },
  })

  const uploadMutation = useMutation({
    mutationFn: async (fileToUpload: File) => {
      const formData = new FormData()
      formData.append("file", fileToUpload)

      const response = await fetch(`http://localhost:8000/api/v1/organizations/${currentOrgId}/documents/`, {
        method: "POST",
        credentials: "include",
        body: formData, 
      })

      if (!response.ok) {
        let errMsg = "Failed to upload document"
        try {
          const errData = await response.json()
          if (errData.detail) {
            if (Array.isArray(errData.detail)) {
              if (errData.detail.length > 1) {
                errMsg = "Validation failed:\n• " + errData.detail.map((e: any) => e.msg || "Unknown error").join("\n• ")
              } else if (errData.detail.length === 1) {
                errMsg = "Validation failed: " + (errData.detail[0].msg || "Unknown error")
              }
            } else if (typeof errData.detail === 'string') {
              errMsg = errData.detail
            } else if (typeof errData.detail === 'object') {
              errMsg = errData.detail.message || errData.detail.msg || JSON.stringify(errData.detail)
            }
          } else if (errData.message) {
            errMsg = errData.message
          } else if (errData.msg) {
            errMsg = errData.msg
          }
        } catch(e) {}
        throw new Error(errMsg)
      }
      return response.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents", currentOrgId] })
      setFile(null)
      setIsUploadModalOpen(false)
    },
    onError: (err: any) => {
      setUploadError(err.message || "Upload failed")
    }
  })

  const deleteMutation = useMutation({
    mutationFn: (docId: string) => fetchApi(`/organizations/${currentOrgId}/documents/${docId}`, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents", currentOrgId] })
    }
  })

  const indexMutation = useMutation({
    mutationFn: (docId: string) => fetchApi(`/organizations/${currentOrgId}/documents/${docId}/index`, { method: "POST" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents", currentOrgId] })
    }
  })

  const handleUpload = () => {
    if (file) {
      setUploadError(null)
      uploadMutation.mutate(file)
    }
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0])
      setUploadError(null)
    }
  }

  return (
    <div className="flex w-full flex-col max-w-[1150px] mx-auto space-y-8 pb-12 pt-8 animate-in fade-in duration-300">
      {/* HEADER SECTION */}
      <div className="flex items-end justify-between border-b border-[#E5E5E5] pb-6">
        <div className="flex flex-col space-y-2">
          <span className="text-[11px] font-semibold text-[#737373] tracking-[0.05em] uppercase">
            Knowledge Base
          </span>
          <h2 className="text-[28px] md:text-[30px] font-semibold tracking-[-0.025em] text-[#111111] leading-none">
            Documents
          </h2>
          <p className="text-[13px] text-[#525252] max-w-[500px]">
            Manage organizational knowledge and indexing.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button 
            onClick={() => queryClient.invalidateQueries({ queryKey: ["documents", currentOrgId] })}
            className="flex items-center justify-center h-9 w-9 rounded-md border border-[#E5E5E5] bg-white text-[#525252] hover:text-[#111111] hover:border-[#111111] hover:shadow-sm transition-all"
            title="Refresh"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
          <button 
            onClick={() => setIsUploadModalOpen(true)}
            className="flex items-center h-9 px-4 rounded-md bg-[#111111] text-white text-[13px] font-medium transition-all hover:bg-[#1A1A1A] hover:shadow-[0_2px_8px_rgba(0,0,0,0.15)] active:scale-95"
          >
            Upload Document
          </button>
        </div>
      </div>

      <div className="w-full">
        {isLoading ? (
          <div className="space-y-3">
            {[1, 2, 3, 4].map(i => (
              <div key={i} className="h-[52px] w-full animate-pulse rounded-md bg-white border border-[#E5E5E5]" />
            ))}
          </div>
        ) : !documents || documents.length === 0 ? (
          <div className="flex flex-col items-center justify-center p-20 text-center rounded-xl border border-[#E5E5E5] bg-white shadow-sm mt-8">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-[#FAFAFA] border border-[#E5E5E5] mb-6 shadow-sm">
              <Network className="h-7 w-7 text-[#111111]" />
            </div>
            <h3 className="text-[18px] font-semibold text-[#111111] mb-2">No documents indexed</h3>
            <p className="text-[14px] text-[#737373] max-w-sm mx-auto mb-8 leading-relaxed">
              Upload your first document to begin building your organization's knowledge base.
            </p>
            <button 
              onClick={() => setIsUploadModalOpen(true)}
              className="group flex items-center h-10 px-5 rounded-md bg-[#111111] text-white text-[14px] font-medium transition-all hover:bg-[#1A1A1A] hover:shadow-[0_2px_8px_rgba(0,0,0,0.15)] active:scale-95 mb-6"
            >
              Upload Document <ArrowRight className="ml-2 h-4 w-4 transition-transform group-hover:translate-x-1" />
            </button>
            <div className="text-[12px] font-medium text-[#A3A3A3] tracking-widest uppercase">
              Supported formats: PDF · DOCX · TXT · CSV
            </div>
          </div>
        ) : (
          <div className="rounded-lg border border-[#E5E5E5] bg-white overflow-hidden shadow-sm">
            <Table>
              <TableHeader className="bg-[#FAFAFA]">
                <TableRow className="border-b border-[#E5E5E5] hover:bg-transparent">
                  <TableHead className="text-[11px] font-semibold text-[#737373] uppercase tracking-widest h-10 px-4">Name</TableHead>
                  <TableHead className="text-[11px] font-semibold text-[#737373] uppercase tracking-widest h-10">Status</TableHead>
                  <TableHead className="hidden md:table-cell text-[11px] font-semibold text-[#737373] uppercase tracking-widest h-10">Updated</TableHead>
                  <TableHead className="text-right text-[11px] font-semibold text-[#737373] uppercase tracking-widest h-10 px-4">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {documents.map((doc: any) => (
                  <TableRow 
                    key={doc.id} 
                    className="group border-b border-[#E5E5E5] hover:bg-[#F7F7F7] transition-colors relative h-[52px]"
                  >
                    <TableCell className="font-medium text-[#111111] px-4 relative">
                      <div className="absolute left-0 top-0 bottom-0 w-[2px] bg-[#111111] opacity-0 group-hover:opacity-100 transition-opacity" />
                      <div className="flex items-center gap-3">
                        <FileText className="h-[14px] w-[14px] text-[#A3A3A3]" />
                        <span className="truncate max-w-[200px] md:max-w-[400px] text-[13px]">{doc.filename}</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-[4px] text-[11px] font-medium tracking-wide uppercase border
                        ${doc.status === 'indexed' ? 'border-transparent bg-[#111111] text-white' : ''}
                        ${doc.status === 'ready' ? 'border-[#E5E5E5] bg-[#FAFAFA] text-[#737373]' : ''}
                        ${doc.status === 'processing' || doc.status === 'indexing' ? 'border-[#F59E0B]/30 bg-[#F59E0B]/10 text-[#D97706]' : ''}
                        ${doc.status === 'failed' ? 'border-[#EF4444]/30 bg-[#EF4444]/10 text-[#DC2626]' : ''}
                      `}>
                        {(doc.status === 'processing' || doc.status === 'indexing') && <Loader2 className="h-3 w-3 animate-spin" />}
                        {doc.status === 'indexed' && <CheckCircle2 className="h-3 w-3" />}
                        {doc.status.toUpperCase()}
                      </span>
                    </TableCell>
                    <TableCell className="hidden md:table-cell text-[#737373] text-[13px] font-mono">
                      {new Date(doc.created_at).toLocaleDateString()}
                    </TableCell>
                    <TableCell className="text-right px-4">
                      <div className="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        {doc.status === 'ready' && (
                          <button 
                            onClick={() => indexMutation.mutate(doc.id)}
                            disabled={indexMutation.isPending}
                            className="h-7 px-3 text-[11px] font-semibold tracking-wide uppercase border border-[#E5E5E5] rounded-md text-[#111111] bg-white hover:border-[#111111] disabled:opacity-50 transition-colors"
                          >
                            Index
                          </button>
                        )}
                        <button 
                          className="flex items-center justify-center h-7 w-7 rounded-md text-[#A3A3A3] hover:text-[#DC2626] hover:bg-[#FEF2F2] transition-colors disabled:opacity-50"
                          onClick={() => deleteMutation.mutate(doc.id)}
                          disabled={deleteMutation.isPending || indexMutation.isPending}
                          title="Delete"
                        >
                          <Trash2 className="h-[14px] w-[14px]" />
                        </button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </div>

      <Dialog open={isUploadModalOpen} onOpenChange={setIsUploadModalOpen}>
        <DialogContent className="max-w-[480px] p-0 overflow-hidden border-[#E5E5E5] bg-white shadow-2xl rounded-xl">
          <div className="p-6 border-b border-[#E5E5E5] bg-white">
            <DialogHeader>
              <DialogTitle className="text-[20px] font-semibold text-[#111111] tracking-tight">Upload Documents</DialogTitle>
              <DialogDescription className="text-[14px] text-[#737373] mt-1">
                Add new files to your organization's knowledge base.
              </DialogDescription>
            </DialogHeader>
          </div>
          
          <div className="p-6 space-y-6 bg-[#FAFAFA]">
            <div 
              className={`border-2 border-dashed rounded-xl p-10 flex flex-col items-center justify-center text-center transition-all cursor-pointer ${
                isDragging ? 'border-[#111111] bg-[#111111]/5 scale-[1.01]' : 'border-[#D4D4D4] bg-white hover:border-[#111111] hover:shadow-[0_4px_12px_rgba(0,0,0,0.02)]'
              }`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => !file && fileInputRef.current?.click()}
            >
              <div className={`flex h-12 w-12 items-center justify-center rounded-full mb-4 transition-colors ${isDragging ? 'bg-[#111111] text-white' : 'bg-[#F5F5F5] text-[#525252]'}`}>
                <UploadCloud className="h-6 w-6" />
              </div>
              <h3 className="text-[15px] font-semibold text-[#111111] mb-1">
                {isDragging ? 'Drop files here' : 'Upload files here'}
              </h3>
              <p className="text-[13px] text-[#737373] mb-6">
                or <span className="font-medium text-[#111111] underline underline-offset-2">Browse files</span>
              </p>
              <input 
                type="file" 
                ref={fileInputRef}
                onChange={(e) => setFile(e.target.files?.[0] || null)}
                className="hidden"
                accept=".pdf,.docx,.txt,.md,.csv,.xlsx"
              />
            </div>

            {file && (
              <div className="p-3 pl-4 rounded-lg border border-[#E5E5E5] bg-white shadow-[0_2px_8px_rgba(0,0,0,0.04)] flex items-center justify-between animate-in slide-in-from-bottom-2">
                <div className="flex items-center gap-3 overflow-hidden">
                  <FileText className="h-[18px] w-[18px] text-[#A3A3A3] shrink-0" />
                  <div className="flex flex-col truncate">
                    <span className="text-[13px] font-semibold text-[#111111] truncate">{file.name}</span>
                    <span className="text-[12px] font-mono text-[#737373]">
                      {(file.size / 1024 / 1024).toFixed(2)} MB
                    </span>
                  </div>
                </div>
                <button 
                  onClick={() => setFile(null)}
                  className="p-2 text-[#A3A3A3] hover:text-[#DC2626] hover:bg-[#FEF2F2] rounded-md transition-colors"
                  disabled={uploadMutation.isPending}
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            )}
            
            {uploadError && (
              <div className="p-4 rounded-lg bg-[#FEF2F2] border border-[#FECACA] text-[13px] text-[#B91C1C] flex items-start gap-3 animate-in slide-in-from-top-2">
                <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
                <span className="whitespace-pre-wrap leading-relaxed font-medium">{uploadError}</span>
              </div>
            )}
          </div>

          <div className="flex items-center justify-end gap-3 p-4 border-t border-[#E5E5E5] bg-white">
            <button 
              className="px-4 py-2 text-[13px] font-medium text-[#737373] hover:text-[#111111] transition-colors"
              onClick={() => setIsUploadModalOpen(false)}
            >
              Cancel
            </button>
            <button 
              className="group flex items-center h-9 px-4 rounded-md bg-[#111111] text-white text-[13px] font-medium transition-all hover:bg-[#1A1A1A] hover:shadow-[0_2px_8px_rgba(0,0,0,0.15)] disabled:opacity-50 disabled:hover:shadow-none disabled:cursor-not-allowed"
              onClick={handleUpload} 
              disabled={!file || !currentOrgId || uploadMutation.isPending}
            >
              {uploadMutation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  Processing...
                </>
              ) : (
                <>
                  Process Documents <ArrowRight className="ml-2 h-[14px] w-[14px] transition-transform group-hover:translate-x-0.5 group-disabled:translate-x-0" />
                </>
              )}
            </button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
