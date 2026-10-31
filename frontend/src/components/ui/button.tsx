import { Button as ButtonPrimitive } from "@base-ui/react/button"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "group/button inline-flex shrink-0 items-center justify-center rounded-md border border-transparent bg-clip-padding text-[12px] md:text-[13px] font-medium whitespace-nowrap transition-all duration-150 ease-[cubic-bezier(0.2,0.8,0.2,1)] outline-none select-none focus-visible:border-[#111111] focus-visible:ring-2 focus-visible:ring-black/5 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
  {
    variants: {
      variant: {
        default: "bg-[#050505] text-white border-[#050505] hover:bg-[#171717] hover:-translate-y-[1px] hover:shadow-[0_4px_12px_rgba(0,0,0,0.10)] active:scale-[0.98]",
        outline: "bg-white border-[#DCDCDC] text-[#171717] hover:bg-[#F7F7F7] hover:border-[#BFBFBF] active:scale-[0.98]",
        secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80 active:scale-[0.98]",
        ghost: "bg-transparent hover:bg-[#F5F5F5] active:scale-[0.98] text-[#525252] hover:text-[#111111]",
        destructive: "bg-destructive text-destructive-foreground hover:bg-destructive/90 shadow-sm active:scale-[0.98]",
        link: "text-primary underline-offset-4 hover:underline",
      },
      size: {
        default:
          "h-9 px-4 py-2",
        sm: "h-8 rounded-md px-3 text-xs",
        lg: "h-10 rounded-md px-8 text-sm",
        icon: "size-9",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

function Button({
  className,
  variant = "default",
  size = "default",
  ...props
}: ButtonPrimitive.Props & VariantProps<typeof buttonVariants>) {
  return (
    <ButtonPrimitive
      data-slot="button"
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  )
}

export { Button, buttonVariants }
