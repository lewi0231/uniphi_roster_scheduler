import { Clock8Icon } from "lucide-react";
import { ChangeEvent } from "react";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

type TimePickerProps = {
  value: string; // Format: "HH:MM" or "HH:MM:SS"
  onChange: (value: string) => void;
  label?: string;
  id?: string;
  className?: string;
  ariaLabel?: string;
  labelClassName?: string;
  contentClassName?: string;
  inputClassName?: string;
};

const TimePicker = ({
  value,
  onChange,
  label,
  id = "time-picker",
  className,
  ariaLabel,
  labelClassName,
  contentClassName,
  inputClassName,
}: TimePickerProps) => {
  const handleChange = (event: ChangeEvent<HTMLInputElement>) => {
    // Convert to HH:MM format if needed (remove seconds)
    const timeValue = event.target.value;
    const [hours, minutes] = timeValue.split(":");
    onChange(`${hours}:${minutes}:00`);
  };

  // Ensure value is in HH:MM:SS format for the input (HTML time input requires this)
  const inputValue =
    value.includes(":") && value.split(":").length === 2
      ? `${value}:00`
      : value;

  return (
    <div className={cn("w-full space-y-3", className)}>
      {label && (
        <Label htmlFor={id} className={labelClassName}>
          {label}
        </Label>
      )}
      <div className={cn("bg-muted/50 rounded-md p-3 ", contentClassName)}>
        <div className="relative">
          <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center justify-center pl-3 peer-disabled:opacity-50">
            <Clock8Icon className="size-4" />
            <span className="sr-only">Time</span>
          </div>
          <Input
            type="time"
            id={id}
            step="1"
            value={inputValue}
            onChange={handleChange}
            className={cn(
              "peer bg-muted appearance-none pl-9 [&::-webkit-calendar-picker-indicator]:hidden [&::-webkit-calendar-picker-indicator]:appearance-none cursor-text",
              inputClassName
            )}
            aria-label={ariaLabel || label}
          />
        </div>
      </div>
    </div>
  );
};

export default TimePicker;
