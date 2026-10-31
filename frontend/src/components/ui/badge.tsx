import { mergeProps } from "@base-ui/react/merge-props"
import { useRender } from "@base-ui/react/use-render"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "group/badge inline-flex h-5 w-fit shrink-0 items-center justify-center gap-1 overflow-hidden rounded-4xl border border-transparent px-2 py-0.5 text-xs font-medium whitespace-nowrap transition-all focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 has-data-[icon=inline-end]:pr-1.5 has-data-[icon=inline-start]:pl-1.5 aria-invalid:border-destructive aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 [&>svg]:pointer-events-none [&>svg]:size-3!",
  {
    variants: {
      variant: {
        default: "bg-[#050505] text-[#FFFFFF] [a]:hover:bg-[#171717] transition-all",
        secondary: "bg-[#F5F5F5] text-[#111111] [a]:hover:bg-[#E5E5E5] transition-all",
        destructive: "bg-[#FEF2F2] text-[#991B1B] border border-[#FCA5A5] [a]:hover:bg-[#FEE2E2] transition-all",
        outline: "border-[#E5E5E5] text-[#525252] bg-white [a]:hover:bg-[#FAFAFA] [a]:hover:text-[#111111] transition-all",
        ghost: "hover:bg-[#F5F5F5] hover:text-[#111111] text-[#737373] transition-all",
        link: "text-[#111111] underline-offset-4 hover:underline",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

function Badge({
  className,
  variant = "default",
  render,
  ...props
}: useRender.ComponentProps<"span"> & VariantProps<typeof badgeVariants>) {
  return useRender({
    defaultTagName: "span",
    props: mergeProps<"span">(
      {
        className: cn(badgeVariants({ variant }), className),
      },
      props
    ),
    render,
    state: {
      slot: "badge",
      variant,
    },
  })
}

export { Badge, badgeVariants }
