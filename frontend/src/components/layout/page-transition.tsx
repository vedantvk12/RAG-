"use client"

import { useEffect, useState } from "react"
import { usePathname } from "next/navigation"

export function PageTransition({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const [mounted, setMounted] = useState(false)
  const [show, setShow] = useState(false)
  const [isReducedMotion, setIsReducedMotion] = useState(false)

  useEffect(() => {
    setMounted(true)
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)')
    setIsReducedMotion(mediaQuery.matches)
    
    const listener = (e: MediaQueryListEvent) => setIsReducedMotion(e.matches)
    mediaQuery.addEventListener('change', listener)
    return () => mediaQuery.removeEventListener('change', listener)
  }, [])

  // Trigger animation on pathname change
  useEffect(() => {
    if (!mounted) return
    
    setShow(false)
    const timer = setTimeout(() => {
      setShow(true)
    }, 10)
    
    return () => clearTimeout(timer)
  }, [pathname, mounted])

  if (!mounted) {
    return <div className="opacity-0">{children}</div>
  }

  if (isReducedMotion) {
    return <>{children}</>
  }

  return (
    <div 
      className="transition-all ease-[cubic-bezier(0.2,0.8,0.2,1)]"
      style={{
        transitionDuration: '200ms',
        opacity: show ? 1 : 0,
        transform: show ? 'translateY(0)' : 'translateY(4px)'
      }}
    >
      {children}
    </div>
  )
}
