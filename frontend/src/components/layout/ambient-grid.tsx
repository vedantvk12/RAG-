"use client"

import { useEffect, useState } from "react"

export function AmbientGrid() {
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  if (!mounted) return null

  return (
    <div className="pointer-events-none fixed inset-0 z-[-1] overflow-hidden flex justify-center">
      {/* 
        Signature Dot Grid 
        Using a CSS radial gradient for zero runtime cost.
        Dots are 1px, rgba(0,0,0,0.07).
        Desktop: 24px spacing
        Mobile: 32px spacing (lower density)
      */}
      <div 
        className="ambient-dot-grid absolute inset-0 h-full w-full opacity-100"
        style={{
          backgroundImage: `radial-gradient(circle, rgba(0, 0, 0, 0.18) 1.5px, transparent 1px)`,
          backgroundPosition: 'center center',
          maskImage: 'radial-gradient(ellipse at 50% 30%, transparent 20%, black 80%)',
          WebkitMaskImage: 'radial-gradient(ellipse at 50% 30%, transparent 20%, black 80%)',
        }}
      >
        <style dangerouslySetInnerHTML={{__html: `
          @media (min-width: 768px) {
            .ambient-dot-grid { background-size: 24px 24px !important; }
          }
          @media (max-width: 767px) {
            .ambient-dot-grid { background-size: 32px 32px !important; }
          }
          @keyframes subtle-pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.4; transform: scale(0.85); box-shadow: 0 0 12px rgba(0,0,0,0.1); }
          }
          .animate-glow {
            animation: subtle-pulse 4s cubic-bezier(0.4, 0, 0.6, 1) infinite;
          }
        `}} />
      </div>

      {/* Occasional brighter dots for depth effect (pseudo-random positions) */}
      <div className="absolute inset-0 w-full max-w-[1200px] h-full mx-auto relative opacity-80 pointer-events-none">
        <div className="absolute top-[20%] left-[15%] w-1.5 h-1.5 bg-black/40 rounded-full shadow-[0_0_8px_rgba(0,0,0,0.3)] animate-glow" style={{ animationDelay: '0s' }} />
        <div className="absolute top-[45%] left-[85%] w-1.5 h-1.5 bg-black/40 rounded-full shadow-[0_0_8px_rgba(0,0,0,0.3)] animate-glow" style={{ animationDelay: '1s' }} />
        <div className="absolute top-[70%] left-[25%] w-1.5 h-1.5 bg-black/40 rounded-full shadow-[0_0_8px_rgba(0,0,0,0.3)] animate-glow" style={{ animationDelay: '2s' }} />
        <div className="absolute top-[15%] left-[75%] w-1.5 h-1.5 bg-black/40 rounded-full shadow-[0_0_8px_rgba(0,0,0,0.3)] animate-glow" style={{ animationDelay: '3s' }} />
      </div>
    </div>
  )
}
