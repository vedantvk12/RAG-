import * as React from "react"
import { Input as InputPrimitive } from "@base-ui/react/input"

import { cn } from "@/lib/utils"

function Input({ className, type, ...props }: React.ComponentProps<"input">) {
  return (
    <InputPrimitive
      type={type}
      data-slot="input"
      className={cn(
        "flex h-[38px] w-full rounded-[6px] border border-[#D9D9D9] bg-[#FFFFFF] px-3 py-1 text-[13px] shadow-sm transition-all duration-150 outline-none file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-[#A3A3A3] hover:border-[#BDBDBD] focus-visible:border-[#111111] focus-visible:ring-0 focus-visible:shadow-[0_0_0_2px_rgba(0,0,0,0.05)] disabled:bg-[#F5F5F5] disabled:text-[#737373] disabled:cursor-not-allowed disabled:opacity-100",
        className
      )}
      {...props}
    />
  )
}

export { Input }
