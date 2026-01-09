import AddNameField from "@/components/add-name-field";
import Header from "@/components/header";
import SelectExcludedYards from "@/components/select-excluded-yards";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { AVAILABILITY_HEADINGS, DAYS_OF_WEEK } from "@/lib/constants";
import { ScheduleRequestPayload } from "@/lib/scheduler";
import { cn } from "@/lib/utils";
import { X } from "lucide-react";
import { Button } from "./ui/button";

type EmployeeAvailabilityDisplayProps = {
  workers: ScheduleRequestPayload["employees"];
  carYards: ScheduleRequestPayload["car_yards"];
  onUpdateWorker: (
    workerId: number,
    updater: (
      worker: ScheduleRequestPayload["employees"][number]
    ) => ScheduleRequestPayload["employees"][number]
  ) => void;
  onAddWorker: (name: string) => void;
  onRemoveWorker: (workerId: number) => void;
};

const EmployeeAvailabilityDisplay = ({
  workers,
  carYards,
  onUpdateWorker,
  onAddWorker,
  onRemoveWorker,
}: EmployeeAvailabilityDisplayProps) => {
  const handleToggleAvailability = (
    workerId: number,
    day: (typeof DAYS_OF_WEEK)[number],
    checked: boolean
  ) => {
    onUpdateWorker(workerId, (current) => {
      if (checked) {
        const nextDays = Array.from(new Set([...current.available_days, day]));
        return {
          ...current,
          available_days: nextDays,
        };
      }

      return {
        ...current,
        available_days: current.available_days.filter((d) => d !== day),
      };
    });
  };

  return (
    <section className="w-full space-y-4 border-b pb-4">
      <Header
        subText="Please add or alter the default values as you like. Note that setting
        changes will be lost on page refresh."
      >
        Employee Availability
      </Header>
      <div className="grid grid-cols-[minmax(12rem,1fr)_repeat(6,minmax(2rem,0.5fr))_minmax(8rem,1.5fr)_minmax(4rem,1.5fr)_minmax(4rem,1fr)]">
        <div className="border-r" />
        {AVAILABILITY_HEADINGS.map((headingObj, index) => (
          <div
            className={cn(
              " text-muted-foreground font-medium text-sm  w-full flex justify-center items-center py-4",
              [6, 7].includes(index) ? "border-r" : ""
            )}
            key={headingObj.heading}
          >
            <Tooltip>
              <TooltipTrigger asChild>
                <span className=" text-center font-medium text-wrap cursor-help">
                  {headingObj.heading.charAt(0).toUpperCase() +
                    headingObj.heading.substring(1)}
                </span>
              </TooltipTrigger>
              <TooltipContent>
                <p>{headingObj.tooltip}</p>
              </TooltipContent>
            </Tooltip>
          </div>
        ))}
      </div>
      <div className="w-full flex flex-col gap-4">
        {workers.map((worker) => (
          <div
            key={worker.id}
            className="grid grid-cols-[minmax(12rem,1fr)_repeat(6,minmax(2rem,0.5fr))_minmax(8rem,1.5fr)_minmax(4rem,1.5fr)_minmax(4rem,1fr)] w-full py-2 border-2 border-foreground/10 rounded-md bg-muted/50"
          >
            <div className="font-medium border-r  py-2 pl-2">{worker.name}</div>
            {DAYS_OF_WEEK.map((day) => (
              <div
                key={`${worker.id}-${day}`}
                className="w-full flex justify-center items-center"
              >
                <Checkbox
                  checked={worker.available_days.includes(day)}
                  onCheckedChange={(checked) =>
                    handleToggleAvailability(worker.id, day, Boolean(checked))
                  }
                  aria-label={`${worker.name} available on ${day}`}
                  className="border-2 border-foreground/30 data-[state=checked]:border-primary"
                />
              </div>
            ))}
            <div className="flex items-center justify-center border-l overflow-hidden">
              <SelectExcludedYards
                worker={worker}
                carYards={carYards}
                onUpdateWorker={(updater) => onUpdateWorker(worker.id, updater)}
              />
            </div>
            <div className="flex items-center justify-center border-l ">
              <Checkbox
                checked={worker.ranking === "below_average"}
                onCheckedChange={(checked) =>
                  onUpdateWorker(worker.id, (current) => ({
                    ...current,
                    ranking: checked ? "below_average" : "excellent",
                  }))
                }
                aria-label={`${worker.name} marked as under performing`}
                className="border-2 border-foreground/30 data-[state=checked]:border-primary"
              />
            </div>
            <div className="w-full flex justify-center items-center border-l">
              <Button
                size="icon"
                variant="ghost"
                className="h-8 w-8 hover:opacity-50 transition-opacity duration-300 cursor-pointer"
                onClick={() => onRemoveWorker(worker.id)}
              >
                <X />
              </Button>
            </div>
          </div>
        ))}
        <AddNameField handleAddWorker={onAddWorker} />
      </div>
    </section>
  );
};

export default EmployeeAvailabilityDisplay;
