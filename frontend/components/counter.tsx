import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Minus, Plus } from "lucide-react";

type CounterProps = {
  value: number;
  min?: number;
  max?: number;
  step?: number;
  onValueChange?: (value: number) => void;
  className?: string;
  "aria-label"?: string;
};

function Counter({
  value,
  min = 0,
  max,
  step = 1,
  onValueChange,
  className,
  "aria-label": ariaLabel,
}: CounterProps) {
  const canIncrement = max === undefined ? true : value + step <= max;
  const canDecrement = value - step >= min;

  const handleChange = (delta: 1 | -1) => {
    const nextValue = value + delta * step;
    if (delta === 1 && !canIncrement) return;
    if (delta === -1 && !canDecrement) return;
    onValueChange?.(nextValue);
  };

  return (
    <div
      className={cn(
        "flex h-full justify-center w-full items-center rounded-md bg-background text-sm",
        className
      )}
    >
      <Button
        type="button"
        variant="ghost"
        size="icon"
        aria-label={ariaLabel ? `Decrease ${ariaLabel}` : "Decrease value"}
        className="h-6 w-6 rounded-none cursor-pointer"
        disabled={!canDecrement || !onValueChange}
        onClick={() => handleChange(-1)}
      >
        <Minus className="h-3.5 w-3.5" />
      </Button>
      <div className="min-w-[2.5rem] text-center font-medium">{value}</div>
      <Button
        type="button"
        variant="ghost"
        size="icon"
        aria-label={ariaLabel ? `Increase ${ariaLabel}` : "Increase value"}
        className="h-6 w-6 rounded-none cursor-pointer"
        disabled={!canIncrement || !onValueChange}
        onClick={() => handleChange(1)}
      >
        <Plus className="h-3.5 w-3.5" />
      </Button>
    </div>
  );
}

export default Counter;
