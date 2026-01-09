"use client";

import CarYardCustomizationDisplay from "@/components/car-yard-customization-display";
import EmployeeAvailabilityDisplay from "@/components/employee-availability-display";
import GeneralSettingsDisplay from "@/components/general-settings-display";
import { RosterDisplaySheet } from "@/components/roster-display-sheet";
import { Button } from "@/components/ui/button";
import {
  loadSchedulerState,
  useSchedulerPersistence,
} from "@/hooks/use-scheduler-persistence";
import { generateRoster } from "@/lib/actions";
import { DAYS_OF_WEEK } from "@/lib/constants";
import {
  CarYard,
  Employee,
  payload,
  ScheduleRequestPayload,
  ScheduleResponse,
} from "@/lib/scheduler";
import { Calendar, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";

// Default state - moved outside component to avoid recreation on each render
const defaultState = {
  workers: payload.employees,
  carYards: payload.car_yards,
  maxHoursPerDay: payload.max_hours_per_day ?? 6.0,
  earliestStartTime: payload.earliest_start_time ?? "06:00:00",
  maxRadius: payload.max_radius ?? 20,
  radiusMode: payload.radius_mode ?? "soft",
};

const SchedulerPage = () => {
  // Always start with default state to avoid hydration mismatches
  // We'll load from localStorage in useEffect after mount
  const [workers, setWorkers] = useState<ScheduleRequestPayload["employees"]>(
    defaultState.workers
  );
  const [isLoading, setIsLoading] = useState(false);
  const [carYards, setCarYards] = useState(defaultState.carYards);
  const [maxHoursPerDay, setMaxHoursPerDay] = useState(
    defaultState.maxHoursPerDay
  );
  const [earliestStartTime, setEarliestStartTime] = useState(
    defaultState.earliestStartTime
  );
  const [maxRadius, setMaxRadius] = useState(defaultState.maxRadius);
  const [radiusMode, setRadiusMode] = useState<"soft" | "hard" | "off">(
    defaultState.radiusMode as "soft" | "hard" | "off"
  );
  const [rosterDisplayIsOpen, setRosterDisplayIsOpen] = useState(false);
  const [rosterData, setRosterData] = useState<ScheduleResponse | null>(null);

  // Load saved state from localStorage on client mount (after SSR)
  // This ensures server and client render the same initial state
  useEffect(() => {
    const saved = loadSchedulerState(defaultState);
    if (saved) {
      setWorkers(saved.workers);
      setCarYards(saved.carYards);
      setMaxHoursPerDay(saved.maxHoursPerDay);
      setEarliestStartTime(saved.earliestStartTime);
      setMaxRadius(saved.maxRadius);
      if (saved.radiusMode) {
        setRadiusMode(saved.radiusMode);
      }
    }
  }, []); // Only run once on mount

  // Auto-save state changes to localStorage
  useSchedulerPersistence(
    {
      workers,
      carYards,
      maxHoursPerDay,
      earliestStartTime,
      maxRadius,
      radiusMode,
    },
    defaultState
  );

  const handleUpdateWorker = (
    workerId: number,
    updater: (
      worker: ScheduleRequestPayload["employees"][number]
    ) => ScheduleRequestPayload["employees"][number]
  ) => {
    setWorkers((prev) => {
      return prev.map((worker) => {
        return worker.id === workerId ? updater(worker) : worker;
      });
    });
  };

  const handleGenerateRoster = async () => {
    console.log(earliestStartTime);
    const data: ScheduleRequestPayload = {
      ...payload,
      employees: workers,
      car_yards: carYards,
      days: DAYS_OF_WEEK,
      earliest_start_time: earliestStartTime,
      max_hours_per_day: maxHoursPerDay,
      max_radius: maxRadius,
      radius_mode: radiusMode,
    };

    try {
      setIsLoading(true);
      const loadingToast = toast.loading("Generating roster...", {
        description: "This may take a few seconds",
      });

      const response = await generateRoster(data);
      console.log(response);
      setRosterData(response as ScheduleResponse);
      setRosterDisplayIsOpen(true);

      toast.dismiss(loadingToast);
      toast.success("Roster generated successfully!");
    } catch (error) {
      toast.dismiss();

      const errorMessage =
        error instanceof Error
          ? error.message
          : "Failed to generated roster. Please try again or contact support.";
      console.error("Failed to generate roster:", error);

      toast.error("Failed to generate roster", {
        description: errorMessage,
        duration: 5000,
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleRemoveWorker = (workerId: number) => {
    setWorkers((prev) => prev.filter((worker) => worker.id !== workerId));
  };

  const handleAddWorker = (name: string) => {
    setWorkers((prev) => {
      // Find the maximum existing ID and add 1 to ensure uniqueness
      const maxId = prev.length > 0 ? Math.max(...prev.map((w) => w.id)) : 0;
      const newWorker: Employee = {
        name,
        id: maxId + 1,
        available_days: DAYS_OF_WEEK,
        ranking: "below_average",
        excluded_yards: [],
      };
      return [...prev, newWorker];
    });
  };

  const handleRemoveCardYard = (yardId: number) => {
    setCarYards((prev) => prev.filter((yard) => yard.id !== yardId));
  };

  const handleAddCarYard = (name: string) => {
    setCarYards((prev) => {
      // Find the maximum existing ID and add 1 to ensure uniqueness
      const maxId = prev.length > 0 ? Math.max(...prev.map((y) => y.id)) : 0;
      const newCarYard: CarYard = {
        name,
        id: maxId + 1,
        min_employees: 1,
        max_employees: 4,
        region: "central",
        hours_required: 2,
        priority: "high",
        north_south_position: 15,
      };
      return [...prev, newCarYard];
    });
  };

  const handleUpdateCarYard = (
    yardId: number,
    updater: (
      yard: ScheduleRequestPayload["car_yards"][number]
    ) => ScheduleRequestPayload["car_yards"][number]
  ) => {
    setCarYards((prev) =>
      prev.map((yard) => (yard.id === yardId ? updater(yard) : yard))
    );
  };

  const hasRosterData = rosterData?.roster && rosterData.roster.days.length > 0;
  const hasAssignments =
    rosterData?.assignments && rosterData.assignments.length > 0;
  const canReopenRoster =
    (hasRosterData || hasAssignments) && !rosterDisplayIsOpen;

  return (
    <main className="w-full min-h-screen flex flex-col justify-start items-start max-w-[1200px] mx-auto pb-20 space-y-10 relative">
      <GeneralSettingsDisplay
        maxHoursPerDay={maxHoursPerDay}
        earliestStartTime={earliestStartTime}
        maxRadius={maxRadius}
        radiusMode={radiusMode}
        onMaxHoursPerDayChange={setMaxHoursPerDay}
        onEarliestStartTimeChange={setEarliestStartTime}
        onMaxRadiusChange={setMaxRadius}
        onRadiusModeChange={setRadiusMode}
      />

      <EmployeeAvailabilityDisplay
        workers={workers}
        carYards={carYards}
        onUpdateWorker={handleUpdateWorker}
        onAddWorker={handleAddWorker}
        onRemoveWorker={handleRemoveWorker}
      />
      <CarYardCustomizationDisplay
        carYards={carYards}
        baseStartTime={earliestStartTime}
        onUpdateCarYard={handleUpdateCarYard}
        onAddCarYard={handleAddCarYard}
        numWorkers={workers.length}
        onRemoveCarYard={handleRemoveCardYard}
      />

      <div className="w-full flex justify-center">
        <Button
          size="lg"
          className="min-w-2/3 h-12 px-8 text-lg hover:animate-pulse font-semibold cursor-pointer"
          onClick={handleGenerateRoster}
          disabled={isLoading}
        >
          {isLoading ? (
            <>
              <Loader2 className="h-5 w-5 animate-spin" />
              Generating...
            </>
          ) : (
            "Generate Roster"
          )}
        </Button>
      </div>
      <RosterDisplaySheet
        isOpen={rosterDisplayIsOpen}
        onOpenChange={(newState) => setRosterDisplayIsOpen(newState)}
        rosterData={rosterData}
        employees={workers}
      />
      {canReopenRoster && (
        <Button
          onClick={() => setRosterDisplayIsOpen(true)}
          className="fixed right-4 top-1/2 -translate-y-1/2 z-40 rounded-full shadow-lg h-14 w-14 p-0 hover:scale-110 transition-transform duration-200 cursor-pointer"
          size="icon"
          aria-label="View generated roster"
        >
          <Calendar className="h-6 w-6" />
          <span className="sr-only">View generated roster</span>
        </Button>
      )}
    </main>
  );
};

export default SchedulerPage;
