import { RosterEmployeeView } from "@/components/roster-employee-view";
import { RosterTimetable } from "@/components/roster-timetable";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Assignment,
  DayOfWeek,
  Employee,
  ScheduleResponse,
  YardSchedule,
} from "@/lib/scheduler";
import { downloadExcel } from "@/lib/utils";
import { Download } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Button } from "./ui/button";

type Props = {
  isOpen: boolean;
  onOpenChange: (newState: boolean) => void;
  rosterData: ScheduleResponse | null;
  employees: Employee[];
};

export function RosterDisplaySheet({
  isOpen,
  onOpenChange,
  rosterData: initialRosterData,
  employees,
}: Props) {
  const [rosterData, setRosterData] = useState<ScheduleResponse | null>(
    initialRosterData
  );

  // Update local state when initial data changes
  useEffect(() => {
    setRosterData(initialRosterData);
  }, [initialRosterData]);

  const hasRosterData = rosterData?.roster && rosterData.roster.days.length > 0;
  const hasAssignments =
    rosterData?.assignments && rosterData.assignments.length > 0;

  // Helper function to find employee by name
  const findEmployeeByName = useCallback(
    (name: string): Employee | undefined => {
      return employees.find((emp) => emp.name === name);
    },
    [employees]
  );

  // Helper function to create/update an assignment
  const createAssignment = useCallback(
    (
      employee: Employee,
      yardId: number,
      yardName: string,
      day: DayOfWeek,
      startTime: string,
      finishTime: string
    ): Assignment => {
      return {
        employee_id: employee.id,
        employee_name: employee.name,
        car_yard_id: yardId,
        car_yard_name: yardName,
        day,
        start_time: startTime,
        finish_time: finishTime,
      };
    },
    []
  );

  // Handle removing a worker from a yard
  const handleRemoveWorker = useCallback(
    (day: DayOfWeek, yardId: number, workerName: string) => {
      setRosterData((prev) => {
        if (!prev) return prev;

        const updatedRoster = { ...prev };
        const updatedDays = updatedRoster.roster.days.map((dayRoster) => {
          if (dayRoster.day !== day) return dayRoster;

          const updatedYards = dayRoster.yards.map((yard) => {
            if (yard.car_yard_id !== yardId) return yard;

            return {
              ...yard,
              workers: yard.workers.filter((w) => w !== workerName),
            };
          });

          return { ...dayRoster, yards: updatedYards };
        });

        // Update assignments array
        const employee = findEmployeeByName(workerName);
        const updatedAssignments = prev.assignments?.filter(
          (assignment) =>
            !(
              assignment.day === day &&
              assignment.car_yard_id === yardId &&
              employee &&
              assignment.employee_id === employee.id
            )
        );

        return {
          ...updatedRoster,
          roster: { days: updatedDays },
          assignments: updatedAssignments || [],
        };
      });
    },
    [findEmployeeByName]
  );

  // Handle adding a worker to a yard
  const handleAddWorker = useCallback(
    (day: DayOfWeek, yardId: number, workerName: string) => {
      const employee = findEmployeeByName(workerName);
      if (!employee) return;

      setRosterData((prev) => {
        if (!prev) return prev;

        // Find the yard to get its time info
        const yardSchedule = prev.roster.days
          .find((d) => d.day === day)
          ?.yards.find((y) => y.car_yard_id === yardId);

        if (!yardSchedule) return prev;

        const updatedRoster = { ...prev };
        const updatedDays = updatedRoster.roster.days.map((dayRoster) => {
          if (dayRoster.day !== day) return dayRoster;

          const updatedYards = dayRoster.yards.map((yard) => {
            if (yard.car_yard_id !== yardId) return yard;

            // Don't add if already present
            if (yard.workers.includes(workerName)) return yard;

            return {
              ...yard,
              workers: [...yard.workers, workerName],
            };
          });

          return { ...dayRoster, yards: updatedYards };
        });

        // Add to assignments array
        const newAssignment = createAssignment(
          employee,
          yardId,
          yardSchedule.car_yard_name,
          day,
          yardSchedule.start_time,
          yardSchedule.finish_time
        );

        // Check if assignment already exists
        const assignmentExists = prev.assignments?.some(
          (a) =>
            a.employee_id === employee.id &&
            a.car_yard_id === yardId &&
            a.day === day
        );

        const updatedAssignments = assignmentExists
          ? prev.assignments
          : [...(prev.assignments || []), newAssignment];

        return {
          ...updatedRoster,
          roster: { days: updatedDays },
          assignments: updatedAssignments,
        };
      });
    },
    [findEmployeeByName, createAssignment]
  );

  // Handle moving/reordering a shift (yard schedule)
  const handleMoveShift = useCallback(
    (
      yard: YardSchedule,
      fromDay: DayOfWeek,
      toDay: DayOfWeek,
      targetIndex?: number
    ) => {
      setRosterData((prev) => {
        if (!prev) return prev;

        const updatedDays = prev.roster.days.map((dayRoster) => {
          // Reorder within the same day
          if (dayRoster.day === fromDay && fromDay === toDay) {
            const currentIndex = dayRoster.yards.findIndex(
              (y) => y.car_yard_id === yard.car_yard_id
            );
            if (currentIndex === -1) return dayRoster;

            const newYards = [...dayRoster.yards];
            // Remove from current position
            newYards.splice(currentIndex, 1);

            // Compute target index; default to end if undefined
            const insertIndex =
              typeof targetIndex === "number" && targetIndex >= 0
                ? targetIndex
                : newYards.length;

            newYards.splice(insertIndex, 0, yard);

            return { ...dayRoster, yards: newYards };
          }

          // Remove from source day when moving to a different day
          if (dayRoster.day === fromDay && fromDay !== toDay) {
            return {
              ...dayRoster,
              yards: dayRoster.yards.filter(
                (y) => y.car_yard_id !== yard.car_yard_id
              ),
            };
          }

          // Insert into target day
          if (dayRoster.day === toDay && fromDay !== toDay) {
            const newYards = [...dayRoster.yards];
            const insertIndex =
              typeof targetIndex === "number" && targetIndex >= 0
                ? targetIndex
                : newYards.length;
            newYards.splice(insertIndex, 0, yard);
            return { ...dayRoster, yards: newYards };
          }

          return dayRoster;
        });

        // Update assignments only when the day changes
        const updatedAssignments =
          fromDay === toDay
            ? prev.assignments
            : prev.assignments?.map((assignment) => {
                if (
                  assignment.car_yard_id === yard.car_yard_id &&
                  assignment.day === fromDay
                ) {
                  return { ...assignment, day: toDay };
                }
                return assignment;
              });

        return {
          ...prev,
          roster: { days: updatedDays },
          assignments: updatedAssignments || [],
        };
      });
    },
    []
  );

  return (
    <Sheet open={isOpen} onOpenChange={onOpenChange}>
      <SheetContent className="!w-[90vw] !max-w-7xl sm:!w-[95vw] sm:!max-w-7xl flex flex-col px-4 ">
        <SheetHeader className="flex-shrink-0">
          <SheetTitle>Weekly Roster</SheetTitle>
          <SheetDescription>
            View the scheduled assignments by day or by employee.
          </SheetDescription>
        </SheetHeader>
        <div className="mt-6 flex-1 min-h-0 flex flex-col">
          {hasRosterData || hasAssignments ? (
            <Tabs
              defaultValue="by-day"
              className="flex flex-1 flex-col min-h-0"
            >
              <TabsList className="w-full justify-start mb-4">
                <TabsTrigger value="by-day" className="flex-1 cursor-pointer">
                  By Day
                </TabsTrigger>
                <TabsTrigger
                  value="by-employee"
                  className="flex-1 cursor-pointer"
                >
                  By Employee
                </TabsTrigger>
              </TabsList>
              <TabsContent
                value="by-day"
                className="flex-1 min-h-0 overflow-y-auto border-2 border-foreground/10 rounded-md px-4"
              >
                {hasRosterData ? (
                  <RosterTimetable
                    days={rosterData.roster.days}
                    employees={employees}
                    onRemoveWorker={handleRemoveWorker}
                    onAddWorker={handleAddWorker}
                    onMoveShift={handleMoveShift}
                  />
                ) : (
                  <div className="flex items-center justify-center p-8 text-center text-muted-foreground">
                    No roster data available.
                  </div>
                )}
              </TabsContent>
              <TabsContent
                value="by-employee"
                className="flex-1 min-h-0 overflow-y-auto"
              >
                {hasAssignments ? (
                  <RosterEmployeeView
                    assignments={rosterData.assignments!}
                    stats={rosterData.stats}
                  />
                ) : (
                  <div className="flex items-center justify-center p-8 text-center text-muted-foreground">
                    No assignment data available.
                  </div>
                )}
              </TabsContent>
            </Tabs>
          ) : (
            <div className="flex items-center justify-center p-8 text-center text-muted-foreground">
              No roster data available. Generate a roster to view the schedule.
            </div>
          )}
        </div>
        <Button
          variant="default"
          className="my-4 text-lg w-1/4 h-20 mx-auto cursor-pointer hover:scale-110 transition-transform duration-300"
          disabled={!hasRosterData}
          onClick={() => {
            if (hasRosterData && rosterData?.roster?.days) {
              downloadExcel(rosterData.roster.days);
            }
          }}
        >
          <Download />
          <span>Export Roster</span>
        </Button>
      </SheetContent>
    </Sheet>
  );
}
