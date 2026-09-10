import * as React from "react";
import { cn } from "../../lib/utils";

const inputBaseStyles =
  "flex h-11 w-full rounded-lg border border-sand-200 bg-white/90 px-4 py-2 text-sm text-sand-950 shadow-xs outline-none transition-all duration-200 placeholder:text-sand-400 focus:border-oxford-400 focus:bg-white focus:ring-1 focus:ring-oxford-400/50 disabled:cursor-not-allowed disabled:opacity-50";

type InputProps = React.InputHTMLAttributes<HTMLInputElement>;

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type = "text", ...props }, ref) => {
    return (
      <input
        ref={ref}
        type={type}
        className={cn(inputBaseStyles, className)}
        {...props}
      />
    );
  },
);

Input.displayName = "Input";

export { Input };
export type { InputProps };
