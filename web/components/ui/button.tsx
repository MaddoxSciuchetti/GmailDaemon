import * as React from "react";
import { cn } from "@/lib/utils";

type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "default" | "outline";
};

export function Button({ className, variant = "default", ...props }: ButtonProps) {
  return (
    <button
      className={cn(
        "inline-flex h-11 items-center justify-center rounded-2xl px-5 text-sm font-medium transition disabled:pointer-events-none disabled:opacity-40",
        variant === "default" && "bg-black text-white hover:bg-neutral-800",
        variant === "outline" && "border border-black bg-white text-black hover:bg-neutral-100",
        className,
      )}
      {...props}
    />
  );
}
