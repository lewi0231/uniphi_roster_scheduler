import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { DAYS_OF_WEEK } from "@/lib/constants";
import { DayOfWeek, DayRoster, Employee, YardSchedule } from "@/lib/scheduler";
import { cn } from "@/lib/utils";
import { GripVertical, Plus, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";

type RosterTimetableProps = {
  days: DayRoster[];
  employees: Employee[];
  onRemoveWorker: (day: DayOfWeek, yardId: number, workerName: string) => void;
  onAddWorker: (day: DayOfWeek, yardId: number, workerName: string) => void;
  onMoveShift?: (
    yard: YardSchedule,
    fromDay: DayOfWeek,
    toDay: DayOfWeek,
    targetIndex?: number
  ) => void;
};

/**
 * Capitalizes the first letter of a day name for display
 */
function capitalizeDay(day: string): string {
  return day.charAt(0).toUpperCase() + day.slice(1);
}

/**
 * YardCard component displays a single yard's schedule information
 *
 * Displays:
 * - Yard name (title)
 * - Draggable handle icon
 * - List of assigned workers as interactive badges (can be removed)
 * - Add worker dropdown
 */
function YardCard({
  yard,
  day,
  employees,
  onRemoveWorker,
  onAddWorker,
  onMoveShift,
}: {
  yard: YardSchedule;
  day: DayOfWeek;
  employees: Employee[];
  onRemoveWorker: (day: DayOfWeek, yardId: number, workerName: string) => void;
  onAddWorker: (day: DayOfWeek, yardId: number, workerName: string) => void;
  onMoveShift?: (
    yard: YardSchedule,
    fromDay: DayOfWeek,
    toDay: DayOfWeek
  ) => void;
}) {
  const [isAddingWorker, setIsAddingWorker] = useState(false);
  const [isDragging, setIsDragging] = useState(false);

  // Get available employees (not already assigned to this yard)
  const availableEmployees = employees.filter(
    (emp) => !yard.workers.includes(emp.name)
  );

  const handleAddWorker = (workerName: string) => {
    if (workerName === "none") {
      setIsAddingWorker(false);
      return;
    }
    if (workerName) {
      onAddWorker(day, yard.car_yard_id, workerName);
      setIsAddingWorker(false);
    }
  };

  const handleDragStart = (e: React.DragEvent) => {
    console.log("[Drag] Start - YardCard", {
      yardId: yard.car_yard_id,
      yardName: yard.car_yard_name,
      fromDay: day,
      workers: yard.workers,
      hasOnMoveShift: !!onMoveShift,
    });
    setIsDragging(true);
    e.dataTransfer.effectAllowed = "move";
    const dragData = { yard, fromDay: day };
    const dataString = JSON.stringify(dragData);
    e.dataTransfer.setData("application/json", dataString);
    console.log("[Drag] Data set in dataTransfer", {
      dataString,
      dataTransferTypes: Array.from(e.dataTransfer.types),
    });
    // Browser will automatically create a drag image from the element
    // No need to manually set drag image - it can cause issues with React components
  };

  const handleDragEnd = (e: React.DragEvent) => {
    const dropEffect = e.dataTransfer.dropEffect;
    const wasSuccessful = dropEffect === "move";
    console.log("[Drag] End - YardCard", {
      yardId: yard.car_yard_id,
      yardName: yard.car_yard_name,
      dropEffect,
      wasSuccessful,
      note: wasSuccessful
        ? "Drop appears successful"
        : "Drop may have been cancelled or failed",
    });
    setIsDragging(false);
  };

  return (
    <Card
      className={cn(
        "mb-3 border bg-gray-200/50 shadow-sm hover:shadow transition-shadow cursor-move",
        isDragging && "opacity-50"
      )}
      draggable={!!onMoveShift}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
    >
      <CardHeader className="pb-2 pt-3">
        <div className="flex items-center justify-between gap-2">
          <CardTitle className="text-sm font-semibold leading-tight flex-1">
            {yard.car_yard_name}
          </CardTitle>
          {onMoveShift && (
            <div
              className="text-muted-foreground hover:text-foreground transition-colors cursor-grab active:cursor-grabbing"
              onMouseDown={(e) => e.stopPropagation()}
            >
              <GripVertical className="h-4 w-4" />
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-2.5 pt-0 pb-3">
        {/* Workers List */}
        <div className="space-y-1.5">
          <div className="text-xs font-medium text-muted-foreground">
            Workers ({yard.workers.length}):
          </div>
          <div className="flex flex-wrap gap-1">
            {yard.workers.map((worker, index) => (
              <span
                key={index}
                className={cn(
                  "inline-flex items-center gap-1 rounded-md bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary ring-1 ring-primary/20"
                )}
              >
                {worker}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onRemoveWorker(day, yard.car_yard_id, worker);
                  }}
                  className="ml-0.5 hover:bg-primary/20 rounded-full p-0.5 transition-colors"
                  aria-label={`Remove ${worker} from ${yard.car_yard_name}`}
                >
                  <X className="h-3 w-3" />
                </button>
              </span>
            ))}
          </div>

          {/* Add Worker Dropdown */}
          {availableEmployees.length > 0 && (
            <div className="mt-2">
              {!isAddingWorker ? (
                <Button
                  variant="outline"
                  size="sm"
                  className="h-7 text-xs gap-1"
                  onClick={(e) => {
                    e.stopPropagation();
                    setIsAddingWorker(true);
                  }}
                >
                  <Plus className="h-3 w-3" />
                  Add Worker
                </Button>
              ) : (
                <Select onValueChange={handleAddWorker}>
                  <SelectTrigger className="h-7 text-xs w-full">
                    <SelectValue placeholder="Select worker..." />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">Cancel</SelectItem>
                    {availableEmployees.map((emp) => (
                      <SelectItem key={emp.id} value={emp.name}>
                        {emp.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

/**
 * DropZone component for inserting items at specific positions
 * Shows a visual indicator when active (being dragged over)
 */
function DropZone({
  onDrop,
  onDragOver,
  isActive,
}: {
  onDrop: (e: React.DragEvent) => void;
  onDragOver: (e: React.DragEvent) => void;
  isActive: boolean;
}) {
  return (
    <div
      className={cn(
        "w-full transition-all duration-150 cursor-pointer flex items-center justify-center rounded-md",
        "border border-dashed border-transparent",
        // Small height when not active to minimize gaps between cards
        isActive ? "h-12 border-primary bg-primary/5" : "h-2"
      )}
      onDragEnter={(e) => {
        // Ensure we can receive drops when entering
        e.preventDefault();
        e.stopPropagation();
      }}
      onDragOver={onDragOver}
      onDrop={onDrop}
      onDragLeave={(e) => {
        // Log when leaving drop zone for debugging
        console.log("[Drag] Leaving DropZone", {
          relatedTarget: e.relatedTarget,
          currentTarget: e.currentTarget,
        });
      }}
    />
  );
}

/**
 * RosterTimetable displays the weekly roster in a grid layout
 * with days as columns and yard schedules as cards within each day
 */
export function RosterTimetable({
  days,
  employees,
  onRemoveWorker,
  onAddWorker,
  onMoveShift,
}: RosterTimetableProps) {
  // Simplified state management with single object
  const [dragState, setDragState] = useState<{
    day: DayOfWeek | null;
    index: number | null;
  }>({ day: null, index: null });

  // Track if a drop was successful to help debug
  const dropSuccessfulRef = useRef(false);

  // Set up global drag end listener to clean up state
  useEffect(() => {
    const handleGlobalDragEnd = (e: DragEvent) => {
      console.log("[Drag] Global drag end - Cleaning up state", {
        dropEffect: e.dataTransfer?.dropEffect,
        dropWasSuccessful: dropSuccessfulRef.current,
      });
      setDragState({ day: null, index: null });
      dropSuccessfulRef.current = false;
    };

    document.addEventListener("dragend", handleGlobalDragEnd);
    return () => {
      document.removeEventListener("dragend", handleGlobalDragEnd);
    };
  }, []);

  // Create a map of day -> yards for efficient lookup
  const dayMap = new Map<string, YardSchedule[]>();
  days.forEach((dayRoster) => {
    dayMap.set(dayRoster.day, dayRoster.yards);
  });

  // Ensure we have data for all days in the correct order
  const orderedDays = DAYS_OF_WEEK.map((day) => ({
    day,
    yards: dayMap.get(day) || [],
  }));

  const handleDragOver = (
    e: React.DragEvent,
    day: DayOfWeek,
    index?: number
  ) => {
    e.preventDefault();
    e.stopPropagation(); // Stop propagation so column handler doesn't interfere
    e.dataTransfer.dropEffect = "move";
    const newState = { day, index: index ?? null };
    const stateChanged =
      dragState.day !== day || dragState.index !== (index ?? null);
    // Only log when entering a new drop zone to reduce noise
    if (stateChanged) {
      console.log("[Drag] Entering DropZone", {
        targetDay: day,
        targetIndex: index ?? null,
        previousZone: dragState.day
          ? `${dragState.day}:${dragState.index}`
          : "none",
      });
    }
    setDragState(newState);
  };

  const handleDrop = (
    e: React.DragEvent,
    toDay: DayOfWeek,
    targetIndex?: number
  ) => {
    console.log("[Drag] ✅ Drop event FIRED", {
      toDay,
      targetIndex,
      dataTransferTypes: Array.from(e.dataTransfer.types),
      hasOnMoveShift: !!onMoveShift,
    });

    e.preventDefault();
    e.stopPropagation();
    setDragState({ day: null, index: null });

    try {
      const rawData = e.dataTransfer.getData("application/json");

      if (!rawData) {
        console.error("[Drag] ❌ Drop - No data found in dataTransfer");
        return;
      }

      const data = JSON.parse(rawData) as {
        yard: YardSchedule;
        fromDay: DayOfWeek;
      };

      if (data.yard && data.fromDay && onMoveShift) {
        console.log("[Drag] ✅ Drop - Calling onMoveShift", {
          from: `${data.fromDay}`,
          to: `${toDay}`,
          index: targetIndex,
          yard: data.yard.car_yard_name,
        });
        onMoveShift(data.yard, data.fromDay, toDay, targetIndex);
        dropSuccessfulRef.current = true;
        console.log("[Drag] ✅ Drop - onMoveShift completed successfully");
      } else {
        console.warn("[Drag] ❌ Drop - Missing required data or callback", {
          hasYard: !!data.yard,
          hasFromDay: !!data.fromDay,
          hasOnMoveShift: !!onMoveShift,
        });
      }
    } catch (error) {
      console.error("[Drag] ❌ Drop - Failed to parse drag data", {
        error: error instanceof Error ? error.message : String(error),
      });
    }
  };

  return (
    <div className="w-full">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3 lg:grid-cols-6 ">
        {orderedDays.map(({ day, yards }) => (
          <div key={day} className="flex min-h-0 flex-col" data-column={day}>
            {/* Day Header */}
            <div className="mb-3 rounded-md px-3 py-2 text-center sticky top-0 z-10 bg-background/80 backdrop-blur-2xl">
              <h3 className="font-semibold text-foreground">
                {capitalizeDay(day)}
              </h3>
            </div>

            {/* Yard Cards for this day - Drop Zone */}
            <div
              className="flex-1 space-y-0 overflow-y-auto min-h-[200px] rounded-md"
              onDragOver={(e) => {
                // Column-level drag over handler to allow drops
                // Only preventDefault - don't stopPropagation so child drop zones can receive events
                e.preventDefault();
              }}
              onDrop={(e) => {
                // Fallback drop handler - if drop doesn't land on a specific drop zone,
                // use the current drag state to determine where to drop
                if (dragState.day === day && dragState.index !== null) {
                  console.log("[Drag] Fallback drop on column container", {
                    day,
                    targetIndex: dragState.index,
                  });
                  handleDrop(e, day as DayOfWeek, dragState.index);
                } else {
                  console.log("[Drag] Drop on column but no active drop zone", {
                    day,
                    dragState,
                  });
                }
              }}
            >
              {yards.length > 0 ? (
                <>
                  {/* Drop zone at the beginning */}
                  <DropZone
                    onDragOver={(e) => handleDragOver(e, day as DayOfWeek, 0)}
                    onDrop={(e) => handleDrop(e, day as DayOfWeek, 0)}
                    isActive={dragState.day === day && dragState.index === 0}
                  />
                  {yards.map((yard, index) => (
                    <div key={`${day}-${yard.car_yard_id}-${index}`}>
                      <YardCard
                        yard={yard}
                        day={day as DayOfWeek}
                        employees={employees}
                        onRemoveWorker={onRemoveWorker}
                        onAddWorker={onAddWorker}
                        onMoveShift={onMoveShift}
                      />
                      {/* Drop zone after each card */}
                      <DropZone
                        onDragOver={(e) =>
                          handleDragOver(e, day as DayOfWeek, index + 1)
                        }
                        onDrop={(e) =>
                          handleDrop(e, day as DayOfWeek, index + 1)
                        }
                        isActive={
                          dragState.day === day && dragState.index === index + 1
                        }
                      />
                    </div>
                  ))}
                </>
              ) : (
                <div
                  className={cn(
                    "rounded-md border border-dashed min-h-[100px] flex items-center justify-center text-center text-sm text-muted-foreground transition-colors",
                    dragState.day === day && "border-primary bg-primary/5"
                  )}
                  onDragOver={(e) => handleDragOver(e, day as DayOfWeek, 0)}
                  onDrop={(e) => handleDrop(e, day as DayOfWeek, 0)}
                >
                  {dragState.day === day ? "Drop here" : "No yards scheduled"}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
