import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "../../lib/utils";
import { LoadingSpinner } from "./loading-spinner";

const buttonVariants = cva(
  "relative inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg text-sm font-semibold transition-all duration-200 outline-none ring-offset-white focus-visible:ring-2 focus-visible:ring-sand-400 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 data-[loading=true]:pointer-events-none data-[loading=true]:opacity-90",
  {
    variants: {
      variant: {
        default:
          "bg-oxford-600 text-white shadow-[0_2px_10px_rgba(17,43,77,0.12)] hover:bg-oxford-700 hover:shadow-[0_4px_16px_rgba(17,43,77,0.2)]",
        secondary:
          "bg-sand-900 text-white shadow-sm hover:bg-sand-800",
        outline:
          "border border-sand-200 bg-white/85 text-sand-900 shadow-sm hover:bg-sand-50",
        ghost: "text-sand-900 hover:bg-sand-50",
        destructive:
          "bg-rose-600 text-white shadow-sm shadow-rose-600/20 hover:bg-rose-700 hover:shadow-md hover:shadow-rose-600/25",
        link: "text-oxford-500 underline-offset-4 hover:underline px-0",
      },
      size: {
        default: "h-11 px-5 py-2.5",
        sm: "h-9 rounded-md px-3.5 text-sm",
        lg: "h-12 rounded-lg px-6 text-base",
        icon: "h-11 w-11 rounded-lg",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);

type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean;
    isLoading?: boolean;
  };

const spinnerSizeByButtonSize: Record<
  NonNullable<ButtonProps["size"]>,
  "sm" | "md" | "lg"
> = {
  sm: "sm",
  default: "sm",
  lg: "md",
  icon: "sm",
};

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant,
      size,
      asChild = false,
      isLoading = false,
      disabled,
      type = "button",
      onClick,
      children,
      ...props
    },
    ref,
  ) => {
    const Comp = asChild ? Slot : "button";
    const isDisabled = disabled || isLoading;

    const handleClick: React.MouseEventHandler<HTMLButtonElement> = (event) => {
      if (isDisabled) {
        event.preventDefault();
        event.stopPropagation();
        return;
      }

      onClick?.(event);
    };

    return (
      <Comp
        ref={ref}
        className={cn(buttonVariants({ variant, size, className }))}
        data-loading={isLoading}
        data-disabled={isDisabled}
        aria-disabled={asChild && isDisabled ? true : undefined}
        disabled={!asChild ? isDisabled : undefined}
        onClick={handleClick}
        {...(!asChild ? { type } : {})}
        {...props}
      >
        <span
          className={cn(
            "inline-flex items-center justify-center gap-2 transition-opacity",
            isLoading && "opacity-0",
          )}
        >
          {children}
        </span>
        {isLoading ? (
          <span
            className="absolute inset-0 flex items-center justify-center"
            aria-hidden="true"
          >
            <LoadingSpinner
              size={spinnerSizeByButtonSize[size ?? "default"]}
              className="text-current"
            />
          </span>
        ) : null}
      </Comp>
    );
  },
);

Button.displayName = "Button";

export { Button };
export type { ButtonProps };
