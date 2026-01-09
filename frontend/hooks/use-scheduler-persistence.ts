import { CarYard, Employee, RadiusMode } from "@/lib/scheduler";
import { useEffect, useRef } from "react";

const STORAGE_KEY = "scheduler-state";

export interface SchedulerState {
  workers: Employee[];
  carYards: CarYard[];
  maxHoursPerDay: number;
  earliestStartTime: string;
  maxRadius: number;
  radiusMode?: RadiusMode;
}

/**
 * Custom hook to persist scheduler state to localStorage
 * Automatically saves state changes (debounced)
 */
export function useSchedulerPersistence(
  state: SchedulerState,
  defaultState: SchedulerState
) {
  const isInitialMount = useRef(true);
  const saveTimeoutRef = useRef<ReturnType<typeof setTimeout> | undefined>(
    undefined
  );

  // Save state to localStorage whenever it changes (debounced)
  useEffect(() => {
    // Skip saving on initial mount
    if (isInitialMount.current) {
      isInitialMount.current = false;
      return;
    }

    // Clear existing timeout
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
    }

    // Debounce saves to avoid excessive writes
    saveTimeoutRef.current = setTimeout(() => {
      // Only save if we're in browser environment
      if (!isBrowser()) {
        return;
      }

      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
      } catch (error) {
        console.warn("Failed to save scheduler state to localStorage:", error);
        // Handle quota exceeded error
        if (
          error instanceof DOMException &&
          error.name === "QuotaExceededError"
        ) {
          console.error(
            "localStorage quota exceeded. Consider clearing old data."
          );
        }
      }
    }, 300); // 300ms debounce

    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
      }
    };
  }, [state]);

  // Return a function to manually clear saved state
  return {
    clearSavedState: () => {
      if (isBrowser()) {
        try {
          localStorage.removeItem(STORAGE_KEY);
        } catch (error) {
          console.warn(
            "Failed to clear scheduler state from localStorage:",
            error
          );
        }
      }
    },
  };
}

/**
 * Check if we're in a browser environment
 */
function isBrowser(): boolean {
  return typeof window !== "undefined" && typeof localStorage !== "undefined";
}

/**
 * Load scheduler state from localStorage
 * Returns null if no saved state exists or if there's an error
 * Safe to call during SSR - will return null if localStorage is not available
 */
export function loadSchedulerState(
  defaultState: SchedulerState
): SchedulerState | null {
  // Check if we're in a browser environment
  if (!isBrowser()) {
    return null;
  }

  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (!saved) return null;

    const parsed = JSON.parse(saved) as Partial<SchedulerState>;

    // Validate and merge with defaults
    return {
      workers: Array.isArray(parsed.workers)
        ? parsed.workers
        : defaultState.workers,
      carYards: Array.isArray(parsed.carYards)
        ? parsed.carYards
        : defaultState.carYards,
      maxHoursPerDay:
        typeof parsed.maxHoursPerDay === "number"
          ? parsed.maxHoursPerDay
          : defaultState.maxHoursPerDay,
      earliestStartTime:
        typeof parsed.earliestStartTime === "string"
          ? parsed.earliestStartTime
          : defaultState.earliestStartTime,
      maxRadius:
        typeof parsed.maxRadius === "number"
          ? parsed.maxRadius
          : defaultState.maxRadius,
      radiusMode:
        parsed.radiusMode && ["soft", "hard", "off"].includes(parsed.radiusMode)
          ? (parsed.radiusMode as RadiusMode)
          : defaultState.radiusMode,
    };
  } catch (error) {
    console.warn("Failed to load scheduler state from localStorage:", error);
    // Only try to remove if we're in browser
    if (isBrowser()) {
      try {
        localStorage.removeItem(STORAGE_KEY);
      } catch {
        // Ignore errors when removing
      }
    }
    return null;
  }
}
