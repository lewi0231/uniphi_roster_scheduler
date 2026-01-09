import Header from "@/components/header";
import InputCounter from "@/components/input-counter";
import SelectLinkedYard from "@/components/select-linked-yard";
import SelectCarYardRegion from "@/components/select-region";
import { Checkbox } from "@/components/ui/checkbox";
import TimePicker from "@/components/ui/time-picker";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { CAR_YARD_HEADINGS, DAYS_OF_WEEK } from "@/lib/constants";
import { ScheduleRequestPayload } from "@/lib/scheduler";
import { X } from "lucide-react";
import AddNameField from "./add-name-field";
import { Button } from "./ui/button";

type CarYardCustomizationDisplayProps = {
  carYards: ScheduleRequestPayload["car_yards"];
  baseStartTime: string; // Format: "HH:MM" - from general settings
  onUpdateCarYard: (
    yardId: number,
    updater: (
      yard: ScheduleRequestPayload["car_yards"][number]
    ) => ScheduleRequestPayload["car_yards"][number]
  ) => void;
  onAddCarYard: (name: string) => void;
  onRemoveCarYard: (yardId: number) => void;
  numWorkers: number;
};

const CarYardCustomizationDisplay = ({
  numWorkers,
  carYards,
  baseStartTime,
  onUpdateCarYard,
  onAddCarYard,
  onRemoveCarYard,
}: CarYardCustomizationDisplayProps) => {
  return (
    <section className="w-full mx-auto border-b pb-8">
      <Header
        subText="Please add or alter the default values as you like. Note that setting
        changes will be lost on page refresh."
      >
        Car Yard Details
      </Header>
      <div className="overflow-x-auto">
        {/* Header row with sticky name column placeholder */}
        <div className="grid grid-cols-[13rem_repeat(2,minmax(5rem,1fr))_minmax(8rem,1fr)_minmax(5rem,1fr)_repeat(3,minmax(5rem,1fr))_minmax(10rem,1fr)_minmax(12rem,1fr)_minmax(5rem,1fr)_minmax(12rem,1fr)_4rem]  border-b pb-4 text-wrap pt-10 min-w-fit">
          {/* Sticky name column header - empty since name is self-explanatory */}
          <div className="sticky left-0 z-20 border-r backdrop-blur-xs" />
          {CAR_YARD_HEADINGS.map((headingObj, index) => (
            <div
              key={headingObj.heading + index}
              className="flex w-full items-center justify-center border-r"
            >
              <Tooltip>
                <TooltipTrigger asChild>
                  <span className="text-center text-sm text-muted-foreground h-full cursor-help">
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
          {carYards
            .sort(
              (yard_a, yard_b) =>
                yard_a.north_south_position - yard_b.north_south_position
            )
            .map((yard) => {
              const visitsRequired = yard.per_week?.[0] ?? 0;
              const daysBetweenVisits = yard.per_week?.[1] ?? 0;

              return (
                <div
                  key={yard.id}
                  className="grid grid-cols-[13rem_repeat(2,minmax(5rem,1fr))_minmax(8rem,1fr)_minmax(5rem,1fr)_repeat(3,minmax(5rem,1fr))_minmax(10rem,1fr)_minmax(12rem,1fr)_minmax(5rem,1fr)_minmax(12rem,1fr)_4rem] min-w-fit border-2 border-foreground/10 rounded-2xl px-2 bg-muted/50"
                >
                  {/* Sticky name column - stays visible while scrolling */}
                  <div className="sticky left-0 z-10 flex items-center justify-start font-medium border-r backdrop-blur-3xl pl-2">
                    {yard.name}
                  </div>
                  {/* <div className="flex items-center justify-center border-r py-2 text-center">
                <span>{yard.id}</span>
              </div> */}
                  <div className="flex items-center justify-center border-r py-2 text-center bg-muted/50">
                    <InputCounter
                      min={1}
                      step={1}
                      value={visitsRequired}
                      onValueChange={(newValue) =>
                        onUpdateCarYard(yard.id, (current) => {
                          const [, currentGapDays = 0] = current.per_week ?? [
                            1, 0,
                          ];
                          return {
                            ...current,
                            per_week: [newValue, currentGapDays],
                          };
                        })
                      }
                      max={3}
                      ariaLabel={`${yard.name} visits per week`}
                    />
                  </div>
                  <div className="flex items-center justify-center text-center bg-muted/50">
                    <InputCounter
                      min={0}
                      step={1}
                      value={daysBetweenVisits}
                      disabled={visitsRequired <= 1}
                      onValueChange={(newValue) => {
                        if (yard.per_week?.[0] <= 1) return;
                        onUpdateCarYard(yard.id, (current) => {
                          const [currentVisits = 1] = current.per_week ?? [
                            1, 0,
                          ];
                          return {
                            ...current,
                            per_week: [currentVisits, newValue],
                          };
                        });
                      }}
                      max={6}
                      ariaLabel={`${yard.name} days between visits`}
                    />
                  </div>
                  <div className="flex items-center justify-center border-r text-center bg-muted/50">
                    <SelectCarYardRegion
                      value={yard.region}
                      onSelect={(region) =>
                        onUpdateCarYard(yard.id, (current) => ({
                          ...current,
                          region,
                        }))
                      }
                      triggerClassName="h-10"
                      placeholder="Select region"
                    />
                  </div>
                  <div className="flex items-center justify-center border-r text-center bg-muted/50">
                    <InputCounter
                      min={0}
                      step={1}
                      value={yard.north_south_position}
                      onValueChange={(newValue) =>
                        onUpdateCarYard(yard.id, (current) => ({
                          ...current,
                          north_south_position: newValue,
                        }))
                      }
                      max={100}
                      ariaLabel={`${yard.name} north-south position`}
                    />
                  </div>
                  <div className="flex items-center justify-center border-r text-center bg-muted/50">
                    <InputCounter
                      min={1}
                      step={1}
                      value={yard.min_employees}
                      onValueChange={(newValue) =>
                        onUpdateCarYard(yard.id, (current) => {
                          return {
                            ...current,
                            min_employees: newValue,
                          };
                        })
                      }
                      max={
                        yard.max_employees <= numWorkers
                          ? yard.max_employees
                          : numWorkers
                      }
                      ariaLabel={`${yard.name} minimum employees`}
                    />
                  </div>
                  <div className="flex items-center justify-center border-r text-center bg-muted/50">
                    <InputCounter
                      min={yard.min_employees}
                      step={1}
                      value={
                        yard.max_employees <= numWorkers
                          ? yard.max_employees
                          : numWorkers
                      }
                      onValueChange={(newValue) =>
                        onUpdateCarYard(yard.id, (current) => {
                          return {
                            ...current,
                            max_employees: newValue,
                          };
                        })
                      }
                      max={4}
                      ariaLabel={`${yard.name} maximum employees`}
                    />
                  </div>
                  <div className="flex items-center justify-center border-r text-center bg-muted/50">
                    <InputCounter
                      min={0}
                      step={0.5}
                      value={yard.hours_required}
                      onValueChange={(newValue) =>
                        onUpdateCarYard(yard.id, (current) => {
                          return {
                            ...current,
                            hours_required: newValue,
                          };
                        })
                      }
                      max={24}
                      ariaLabel={`${yard.name} hours required`}
                    />
                  </div>
                  <div className="flex items-center justify-center border-r text-center bg-muted/50">
                    <TimePicker
                      value={yard.startTime ?? baseStartTime}
                      onChange={(time) =>
                        onUpdateCarYard(yard.id, (current) => {
                          // If the time matches the base time, remove the override
                          if (time === baseStartTime) {
                            const { startTime, ...rest } = current;
                            return rest;
                          }
                          return {
                            ...current,
                            startTime: time,
                          };
                        })
                      }
                      id={`start-time-${yard.id}`}
                      ariaLabel={`${yard.name} start time`}
                      className="w-full space-y-0"
                      inputClassName="border-2 border-foreground/10"
                    />
                  </div>
                  <div className="flex items-center justify-center border-r py-2 text-center bg-muted/50">
                    <SelectLinkedYard
                      carYards={carYards}
                      currentYardId={yard.id}
                      value={yard.linked_yard?.[0]}
                      onSelect={(linkedYardId) =>
                        onUpdateCarYard(yard.id, (current) => {
                          if (linkedYardId === undefined) {
                            const { linked_yard, ...rest } = current;
                            return rest;
                          }
                          // Preserve existing gap days if link already exists, otherwise default to 0
                          const currentGapDays = current.linked_yard?.[1] ?? 0;
                          return {
                            ...current,
                            linked_yard: [linkedYardId, currentGapDays],
                          };
                        })
                      }
                      triggerClassName="h-10"
                      placeholder="None"
                    />
                  </div>
                  <div className="flex items-center justify-center border-r py-2 text-center bg-muted/50">
                    <InputCounter
                      min={0}
                      step={1}
                      value={yard.linked_yard?.[1] ?? 0}
                      disabled={!yard.linked_yard}
                      onValueChange={(newValue) =>
                        onUpdateCarYard(yard.id, (current) => {
                          if (!current.linked_yard) return current;
                          return {
                            ...current,
                            linked_yard: [current.linked_yard[0], newValue],
                          };
                        })
                      }
                      max={7}
                      ariaLabel={`${yard.name} gap days between linked yards`}
                    />
                  </div>
                  <div className="flex items-center justify-center gap-2 border-r py-2 text-center bg-muted/50">
                    {DAYS_OF_WEEK.map((day) => {
                      const isChecked = (yard.required_days ?? []).includes(
                        day
                      );
                      return (
                        <label
                          key={`${yard.id}-${day}`}
                          className="flex flex-col items-center gap-1 text-xs"
                        >
                          <span className="font-medium uppercase">
                            {day.charAt(0)}
                          </span>
                          <Checkbox
                            checked={isChecked}
                            onCheckedChange={(checked) =>
                              onUpdateCarYard(yard.id, (current) => {
                                const required = new Set(
                                  current.required_days ?? []
                                );
                                if (checked) {
                                  required.add(day);
                                } else {
                                  required.delete(day);
                                }

                                // Preserve the display order to prevent layout jitter.
                                const ordered = DAYS_OF_WEEK.filter((weekday) =>
                                  required.has(weekday)
                                );

                                return {
                                  ...current,
                                  required_days: ordered.length
                                    ? ordered
                                    : undefined,
                                };
                              })
                            }
                            aria-label={`${day} required for ${yard.name}`}
                            className="border-2 border-foreground/10 data-[state=checked]:border-primary"
                          />
                        </label>
                      );
                    })}
                  </div>
                  <div className="flex items-center justify-center">
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => {
                        onRemoveCarYard(yard.id);
                      }}
                      className="h-8 w-8 cursor-pointer hover:opacity-50 transition-opacity duration-300"
                    >
                      <X />
                    </Button>
                  </div>
                </div>
              );
            })}
        </div>
      </div>
      <AddNameField handleAddCarYard={onAddCarYard} />
    </section>
  );
};

export default CarYardCustomizationDisplay;
