import { cn } from "@/lib/utils";
import { ChangeEvent, useCallback } from "react";
import { Input } from "./ui/input";

function InputCounter({
  step,
  min,
  value,
  max,
  disabled,
  ariaLabel,
  className,
  onValueChange,
}: {
  step: number;
  min: number;
  value: number;
  disabled?: boolean;
  max: number;
  ariaLabel?: string;
  className?: string;
  onValueChange: (value: number) => void;
}) {
  const handleChange = useCallback(
    (event: ChangeEvent<HTMLInputElement>) => {
      const nextValue = Number(event.target.value);
      if (Number.isNaN(nextValue)) {
        return;
      }
      onValueChange(nextValue);
    },
    [onValueChange]
  );

  return (
    <Input
      type="number"
      inputMode="decimal"
      step={step}
      min={min}
      disabled={disabled}
      max={max}
      value={value}
      onChange={handleChange}
      className={cn(" text-center ", className)}
      aria-label={ariaLabel}
    />
  );
}

export default InputCounter;
