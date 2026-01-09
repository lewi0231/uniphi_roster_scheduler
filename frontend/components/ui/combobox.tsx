"use client";

import { Check, ChevronsUpDown } from "lucide-react";
import * as React from "react";

import { Button } from "@/components/ui/button";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { ScheduleRequestPayload } from "@/lib/scheduler";
import { cn } from "@/lib/utils";

const workDays = [
  {
    value: "monday",
    label: "Monday",
  },
  {
    value: "tuesday",
    label: "Tuesday",
  },
  {
    value: "wednesday",
    label: "Wednesday",
  },
  {
    value: "thursday",
    label: "Thursday",
  },
  {
    value: "friday",
    label: "Friday",
  },
  {
    value: "saturday",
    label: "Saturday",
  },
] as const;

type Props = {
  unavailableDays: ScheduleRequestPayload["employees"][number]["available_days"];
};

export function ComboBox({ unavailableDays }: Props) {
  const [open, setOpen] = React.useState(false);
  const [value, setValue] = React.useState("");

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="default"
          role="combobox"
          aria-expanded={open}
          className="w-2/3 "
        >
          {value
            ? workDays.find((workDay) => workDay.value === value)?.label
            : "Add another day..."}
          <ChevronsUpDown className="opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-2/3 p-0">
        <Command>
          <CommandInput placeholder="Search..." className="h-9" />
          <CommandList>
            <CommandEmpty>No days left.</CommandEmpty>
            <CommandGroup>
              {workDays
                .filter((day) => !unavailableDays.includes(day.value))
                .map((workday) => (
                  <CommandItem
                    key={workday.value}
                    value={workday.value}
                    onSelect={(currentValue) => {
                      setValue(currentValue === value ? "" : currentValue);
                      setOpen(false);
                    }}
                  >
                    {workday.label}
                    <Check
                      className={cn(
                        "ml-auto",
                        value === workday.value ? "opacity-100" : "opacity-0"
                      )}
                    />
                  </CommandItem>
                ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
