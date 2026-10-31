"use client"

import { useState, useRef, useEffect } from "react"
import { useAuth } from "@/hooks/use-auth"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Eye, EyeOff, Hexagon, Loader2, ArrowRight, Mail, Lock, Shield, Database, BarChart2 } from "lucide-react"
import Link from "next/link"

export default function LoginPage() {
  const { login } = useAuth()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  
  const [mousePos, setMousePos] = useState({ x: 0, y: 0, rawX: 0, rawY: 0, hasMoved: false })
  const panelRef = useRef<HTMLDivElement>(null)
  const [activeShape, setActiveShape] = useState(0)

  useEffect(() => {
    // Cycle shapes every 3.5 seconds
    const interval = setInterval(() => {
      setActiveShape((prev) => (prev + 1) % 7)
    }, 3500)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    // Set initial position for the disk to be center-right
    if (panelRef.current && !mousePos.hasMoved) {
      const rect = panelRef.current.getBoundingClientRect()
      setMousePos({ x: 0, y: 0, rawX: rect.width * 0.75, rawY: rect.height * 0.25, hasMoved: false })
    }
  }, [])

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!panelRef.current) return
    const rect = panelRef.current.getBoundingClientRect()
    // -10 to 10 for 3D rotation
    const x = ((e.clientX - rect.left) / rect.width - 0.5) * 20
    const y = ((e.clientY - rect.top) / rect.height - 0.5) * 20
    
    // Absolute position relative to the panel
    const rawX = e.clientX - rect.left
    const rawY = e.clientY - rect.top

    setMousePos({ x, y, rawX, rawY, hasMoved: true })
  }
  
  const handleMouseLeave = () => {
    if (!panelRef.current) return
    const rect = panelRef.current.getBoundingClientRect()
    // Return to default position when mouse leaves
    setMousePos({ x: 0, y: 0, rawX: rect.width * 0.75, rawY: rect.height * 0.25, hasMoved: false })
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setIsLoading(true)
    
    try {
      await login({ email, password })
      window.location.href = "/"
    } catch (err: any) {
      setError(err.message || "Failed to sign in. Please check your credentials.")
      setIsLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen w-full bg-background font-sans animate-in fade-in duration-300">
      
      {/* Required CSS for custom SVG animations */}
      <style dangerouslySetInnerHTML={{__html: `
        @keyframes drawShape {
          0% { stroke-dashoffset: 2000; opacity: 0; }
          10% { opacity: 1; }
          100% { stroke-dashoffset: 0; opacity: 1; }
        }
        @keyframes drawDot {
          0% { opacity: 0; transform: scale(0); }
          100% { opacity: 1; transform: scale(1); }
        }
        .animate-draw {
          stroke-dasharray: 2000;
          animation: drawShape 2.5s cubic-bezier(0.4, 0, 0.2, 1) forwards;
        }
        .animate-dot {
          opacity: 0;
          animation: drawDot 0.4s cubic-bezier(0.4, 0, 0.2, 1) forwards;
        }
      `}} />

      {/* Left Panel - Branding (55%) */}
      <div 
        ref={panelRef}
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
        className="hidden lg:flex w-[55%] flex-col justify-between bg-[#050505] p-12 text-[#FAFAFA] relative overflow-hidden"
      >
        
        {/* Background Network Mesh Emulation */}
        <div className="absolute inset-0 z-0 pointer-events-none opacity-60">
          <svg className="absolute inset-0 h-full w-full" xmlns="http://www.w3.org/2000/svg" width="100%" height="100%">
            <defs>
              <pattern id="grid" width="100" height="100" patternUnits="userSpaceOnUse">
                <path d="M 100 0 L 0 0 0 100" fill="none" stroke="rgba(255,255,255,0.03)" strokeWidth="1"/>
              </pattern>
              
              <filter id="glow">
                <feGaussianBlur stdDeviation="6" result="coloredBlur"/>
                <feMerge>
                  <feMergeNode in="coloredBlur"/>
                  <feMergeNode in="SourceGraphic"/>
                </feMerge>
              </filter>
            </defs>
            <rect width="100%" height="100%" fill="url(#grid)" />
          </svg>
          
          <svg className="absolute inset-0 h-full w-full" viewBox="0 0 1000 1000" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg">
            <g transform="translate(500, 500)" filter="url(#glow)">
              
              {/* 0. Circle */}
              {(activeShape === 0 || activeShape === 6) && (
                <g key={`circle-${activeShape}`}>
                  <circle cx="0" cy="0" r="280" fill="none" stroke="#ffffff" strokeWidth="2" className="animate-draw" />
                  <circle cx="0" cy="-280" r="6" fill="#fff" className="animate-dot" style={{ animationDelay: '0s' }} />
                  <circle cx="280" cy="0" r="6" fill="#fff" className="animate-dot" style={{ animationDelay: '0.6s' }} />
                  <circle cx="0" cy="280" r="6" fill="#fff" className="animate-dot" style={{ animationDelay: '1.2s' }} />
                  <circle cx="-280" cy="0" r="6" fill="#fff" className="animate-dot" style={{ animationDelay: '1.8s' }} />
                </g>
              )}

              {/* 1. Triangle */}
              {(activeShape === 1 || activeShape === 6) && (
                <g key={`triangle-${activeShape}`}>
                  <polygon points="0,-280 242.5,140 -242.5,140" fill="none" stroke="#ffffff" strokeWidth="2" className="animate-draw" />
                  <circle cx="0" cy="-280" r="6" fill="#fff" className="animate-dot" style={{ animationDelay: '0s' }} />
                  <circle cx="242.5" cy="140" r="6" fill="#fff" className="animate-dot" style={{ animationDelay: '0.8s' }} />
                  <circle cx="-242.5" cy="140" r="6" fill="#fff" className="animate-dot" style={{ animationDelay: '1.6s' }} />
                </g>
              )}

              {/* 2. Square */}
              {(activeShape === 2 || activeShape === 6) && (
                <g key={`square-${activeShape}`}>
                  <polygon points="-198,-198 198,-198 198,198 -198,198" fill="none" stroke="#ffffff" strokeWidth="2" className="animate-draw" />
                  <circle cx="-198" cy="-198" r="6" fill="#fff" className="animate-dot" style={{ animationDelay: '0s' }} />
                  <circle cx="198" cy="-198" r="6" fill="#fff" className="animate-dot" style={{ animationDelay: '0.6s' }} />
                  <circle cx="198" cy="198" r="6" fill="#fff" className="animate-dot" style={{ animationDelay: '1.2s' }} />
                  <circle cx="-198" cy="198" r="6" fill="#fff" className="animate-dot" style={{ animationDelay: '1.8s' }} />
                </g>
              )}

              {/* 3. Pentagon */}
              {(activeShape === 3 || activeShape === 6) && (
                <g key={`pentagon-${activeShape}`}>
                  <polygon points="0,-280 266.3,-86.5 164.6,226.5 -164.6,226.5 -266.3,-86.5" fill="none" stroke="#ffffff" strokeWidth="2" className="animate-draw" />
                  <circle cx="0" cy="-280" r="6" fill="#fff" className="animate-dot" style={{ animationDelay: '0s' }} />
                  <circle cx="266.3" cy="-86.5" r="6" fill="#fff" className="animate-dot" style={{ animationDelay: '0.5s' }} />
                  <circle cx="164.6" cy="226.5" r="6" fill="#fff" className="animate-dot" style={{ animationDelay: '1s' }} />
                  <circle cx="-164.6" cy="226.5" r="6" fill="#fff" className="animate-dot" style={{ animationDelay: '1.5s' }} />
                  <circle cx="-266.3" cy="-86.5" r="6" fill="#fff" className="animate-dot" style={{ animationDelay: '2s' }} />
                </g>
              )}

              {/* 4. Hexagon */}
              {(activeShape === 4 || activeShape === 6) && (
                <g key={`hexagon-${activeShape}`}>
                  <polygon points="0,-280 242.5,-140 242.5,140 0,280 -242.5,140 -242.5,-140" fill="none" stroke="#ffffff" strokeWidth="2" className="animate-draw" />
                  <circle cx="0" cy="-280" r="6" fill="#fff" className="animate-dot" style={{ animationDelay: '0s' }} />
                  <circle cx="242.5" cy="-140" r="6" fill="#fff" className="animate-dot" style={{ animationDelay: '0.4s' }} />
                  <circle cx="242.5" cy="140" r="6" fill="#fff" className="animate-dot" style={{ animationDelay: '0.8s' }} />
                  <circle cx="0" cy="280" r="6" fill="#fff" className="animate-dot" style={{ animationDelay: '1.2s' }} />
                  <circle cx="-242.5" cy="140" r="6" fill="#fff" className="animate-dot" style={{ animationDelay: '1.6s' }} />
                  <circle cx="-242.5" cy="-140" r="6" fill="#fff" className="animate-dot" style={{ animationDelay: '2s' }} />
                </g>
              )}

              {/* 5. Octagon */}
              {(activeShape === 5 || activeShape === 6) && (
                <g key={`octagon-${activeShape}`}>
                  <polygon points="0,-280 198,-198 280,0 198,198 0,280 -198,198 -280,0 -198,-198" fill="none" stroke="#ffffff" strokeWidth="2" className="animate-draw" />
                  <circle cx="0" cy="-280" r="6" fill="#fff" className="animate-dot" style={{ animationDelay: '0s' }} />
                  <circle cx="198" cy="-198" r="6" fill="#fff" className="animate-dot" style={{ animationDelay: '0.3s' }} />
                  <circle cx="280" cy="0" r="6" fill="#fff" className="animate-dot" style={{ animationDelay: '0.6s' }} />
                  <circle cx="198" cy="198" r="6" fill="#fff" className="animate-dot" style={{ animationDelay: '0.9s' }} />
                  <circle cx="0" cy="280" r="6" fill="#fff" className="animate-dot" style={{ animationDelay: '1.2s' }} />
                  <circle cx="-198" cy="198" r="6" fill="#fff" className="animate-dot" style={{ animationDelay: '1.5s' }} />
                  <circle cx="-280" cy="0" r="6" fill="#fff" className="animate-dot" style={{ animationDelay: '1.8s' }} />
                  <circle cx="-198" cy="-198" r="6" fill="#fff" className="animate-dot" style={{ animationDelay: '2.1s' }} />
                </g>
              )}

            </g>
          </svg>
        </div>

        {/* Isometric Hexagon Graphic (Moves anywhere on the panel) */}
        <div 
          className={`absolute w-[300px] h-[300px] pointer-events-none z-10 ease-out ${mousePos.hasMoved ? 'transition-none' : 'transition-all duration-1000'}`}
          style={{ 
            perspective: "1200px",
            // Center the 300x300 block on the cursor
            left: mousePos.rawX ? mousePos.rawX - 150 : '50%',
            top: mousePos.rawY ? mousePos.rawY - 150 : '50%',
          }}
        >
          {/* Intense Glow following the block */}
          <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-[400px] h-[400px] bg-white opacity-25 rounded-full blur-[100px]"></div>

          <div 
            className="relative w-full h-full flex items-center justify-center transition-transform duration-100 ease-out"
            style={{ transform: `rotateX(${-mousePos.y * 2}deg) rotateY(${mousePos.x * 2}deg)` }}
          >
            {/* Stacked layers simulating the 3D isometric glass block */}
            <div className="absolute w-[220px] h-[250px] bg-[#1a1b26]/50 rounded-[30px] border border-white/10 transform -rotate-[30deg] skew-y-[20deg] shadow-[0_0_50px_rgba(0,0,0,0.8)] transition-all duration-300" style={{ boxShadow: `0px 20px 50px rgba(0,0,0,0.8), ${-mousePos.x * 2}px ${-mousePos.y * 2}px 40px rgba(255,255,255,0.1)` }}></div>
            <div className="absolute w-[220px] h-[250px] bg-[#1a1b26]/60 rounded-[30px] border border-white/10 transform -rotate-[30deg] skew-y-[20deg] -translate-y-3 shadow-[0_0_30px_rgba(0,0,0,0.8)]"></div>
            
            {/* Top glowing block */}
            <div className="absolute w-[220px] h-[250px] bg-[#222436]/80 rounded-[30px] border border-white/40 transform -rotate-[30deg] skew-y-[20deg] -translate-y-6 backdrop-blur-md flex items-center justify-center shadow-[inset_0_0_40px_rgba(255,255,255,0.2)] transition-all duration-300">
              
              {/* White Hexagon on top, reacting to glow */}
              <div className="transform rotate-[30deg] -skew-y-[20deg] drop-shadow-[0_0_25px_rgba(255,255,255,1)]">
                <Hexagon className="w-20 h-20 text-white drop-shadow-2xl" strokeWidth={3} />
              </div>
            </div>
          </div>
        </div>

        {/* Content Wrapper */}
        <div className="relative z-20 flex flex-col h-full justify-between max-w-xl pointer-events-none">
          
          {/* Top Logo */}
          <div className="flex items-center gap-2 pointer-events-auto">
            <Hexagon className="h-7 w-7 text-white" strokeWidth={2} />
            <span className="text-[18px] font-semibold tracking-tight text-white">Enterprise Agentic</span>
          </div>

          {/* Main Typography & Features */}
          <div className="space-y-10 mt-12 pointer-events-auto">
            
            <div className="space-y-4">
              <h1 className="text-[32px] font-semibold tracking-[-0.025em] text-white leading-tight drop-shadow-lg">
                Knowledge & <br /> Decision Intelligence
              </h1>
              <p className="text-[14px] text-[#A3A3A3] leading-relaxed max-w-md">
                Turn organizational knowledge into grounded answers, verifiable retrieval, and explainable decisions.
              </p>
            </div>
            
            <div className="flex flex-col gap-8 pt-4">
              
              {/* Feature 1 */}
              <div className="flex items-start gap-5">
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-[#13141C]/80 backdrop-blur-sm border border-white/20 shadow-lg">
                  <Shield className="h-5 w-5 text-white/90" />
                </div>
                <div className="flex flex-col gap-1 pt-0.5">
                  <span className="text-[15px] font-bold text-white">Enterprise Security</span>
                  <span className="text-[13px] text-[#8F9098] leading-relaxed max-w-[280px]">
                    Admin-controlled access, tenant isolation, and secure data handling.
                  </span>
                </div>
              </div>

              {/* Feature 2 */}
              <div className="flex items-start gap-5">
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-[#13141C]/80 backdrop-blur-sm border border-white/20 shadow-lg">
                  <Database className="h-5 w-5 text-white/90" />
                </div>
                <div className="flex flex-col gap-1 pt-0.5">
                  <span className="text-[15px] font-bold text-white">Knowledge at Scale</span>
                  <span className="text-[13px] text-[#8F9098] leading-relaxed max-w-[280px]">
                    Index and retrieve from large document collections in seconds.
                  </span>
                </div>
              </div>

              {/* Feature 3 */}
              <div className="flex items-start gap-5">
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-[#13141C]/80 backdrop-blur-sm border border-white/20 shadow-lg">
                  <BarChart2 className="h-5 w-5 text-white/90" />
                </div>
                <div className="flex flex-col gap-1 pt-0.5">
                  <span className="text-[15px] font-bold text-white">Observability & Audit</span>
                  <span className="text-[13px] text-[#8F9098] leading-relaxed max-w-[280px]">
                    Trace every decision with verifiable logs and execution timelines.
                  </span>
                </div>
              </div>

            </div>
          </div>

          {/* Footer */}
          <div className="flex flex-col gap-1 text-[11px] font-medium text-[#71727A] uppercase tracking-widest mt-12 pointer-events-auto">
            <span>VERSION 2.0.0 • ENTERPRISE</span>
            <span className="normal-case tracking-normal">© 2026 Enterprise Agentic. All rights reserved.</span>
          </div>

        </div>
      </div>

      {/* Right Panel - Login Form (45%) */}
      <div className="flex w-full lg:w-[45%] flex-col items-center justify-center p-8 lg:p-12 bg-white">
        <div className="w-full max-w-[400px] space-y-8">
          
          <div className="flex flex-col space-y-2 text-center lg:text-left">
            <div className="flex lg:hidden items-center justify-center gap-2 mb-4">
              <Hexagon className="h-6 w-6" />
            </div>
            <h2 className="text-[28px] font-bold tracking-tight text-[#111111]">Sign in</h2>
            <p className="text-[14px] text-[#71727A]">
              Enter your details to access your workspace
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            {error && (
              <Alert variant="destructive" className="animate-in fade-in slide-in-from-top-2 rounded-md">
                <AlertDescription className="text-[13px]">{error}</AlertDescription>
              </Alert>
            )}
            
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="email" className="text-[12px] font-medium text-[#71727A]">Work Email</Label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[#A3A3A3]" />
                  <Input 
                    id="email" 
                    type="email" 
                    placeholder="name@organization.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    autoComplete="email"
                    className="pl-9 h-11 text-[14px] bg-[#F4F5F7] border-transparent focus:bg-white focus:border-[#111111] focus:ring-1 focus:ring-[#111111]"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <Label htmlFor="password" className="text-[12px] font-medium text-[#71727A]">Password</Label>
                  <Link href="#" className="text-[11px] font-medium text-[#111111] hover:underline">Forgot password?</Link>
                </div>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[#A3A3A3]" />
                  <Input 
                    id="password" 
                    type={showPassword ? "text" : "password"}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    className="pl-9 pr-10 h-11 text-[14px] bg-[#F4F5F7] border-transparent focus:bg-white focus:border-[#111111] focus:ring-1 focus:ring-[#111111]"
                    autoComplete="current-password"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-[#A3A3A3] hover:text-[#111111] transition-colors"
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>
            </div>

            <Button 
              type="submit" 
              className="w-full flex items-center justify-center group h-11 text-[14px] font-medium mt-6 bg-[#111111] hover:bg-[#1A1A1A] transition-all hover:shadow-md"
              disabled={isLoading}
            >
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Authenticating...
                </>
              ) : (
                <>
                  Sign In
                  <ArrowRight className="ml-2 h-4 w-4 transition-transform group-hover:translate-x-1" />
                </>
              )}
            </Button>
          </form>

          <div className="relative flex items-center justify-center text-[12px] text-[#71727A] uppercase my-6 before:absolute before:inset-x-0 before:h-px before:bg-border before:z-0">
            <span className="bg-white px-3 relative z-10">or</span>
          </div>
          
          <Button variant="outline" className="w-full h-11 text-[14px] font-medium text-[#111111] border-[#E5E5E5] hover:bg-[#FAFAFA] transition-all">
            <svg className="w-4 h-4 mr-2" viewBox="0 0 24 24">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.31-1.04 2.41-2.14 3.15v2.62h3.46c2.03-1.87 3.32-4.64 3.32-7.78z" />
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.46-2.62c-.99.66-2.26 1.05-3.82 1.05-2.94 0-5.43-1.98-6.32-4.66H2.07v2.71C3.89 20.45 7.64 23 12 23z" />
              <path fill="#FBBC05" d="M5.68 14.11c-.22-.66-.35-1.36-.35-2.11s.13-1.45.35-2.11V7.18H2.07C1.35 8.62 1 10.25 1 12s.35 3.38 1.07 4.82l3.61-2.71z" />
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.64 1 3.89 3.55 2.07 7.18l3.61 2.71c.89-2.68 3.38-4.66 6.32-4.66z" />
            </svg>
            Continue with Google
          </Button>

          <div className="text-center text-[13px] text-[#71727A]">
            Don't have an account?{" "}
            <Link href="/signup" className="font-bold text-[#111111] hover:underline underline-offset-4 transition-all">
              Create workspace
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
