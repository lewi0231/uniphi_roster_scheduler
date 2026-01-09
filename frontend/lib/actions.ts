"use server";

/**
 * Server Action for generating rosters
 *
 * Timeout Configuration:
 * - Fetch request timeout: 150 seconds (2.5 minutes) - configurable via ROSTER_REQUEST_TIMEOUT_MS env var
 * - API typically takes up to 2 minutes, so the timeout provides adequate buffer
 * - Server action timeout is controlled by the hosting platform (e.g., Vercel function timeout)
 *   For platforms like Vercel, ensure your function timeout is set to at least 3 minutes
 */

import { EmployeeReliabilityRating, ScheduleRequestPayload } from "./scheduler";

// Mapping from frontend string values to server integer enum values
const RELIABILITY_RATING_MAP: Record<EmployeeReliabilityRating, number> = {
  excellent: 10,
  acceptable: 7,
  below_average: 5,
} as const;

// Transform time string "HH:MM" or "HH:MM:SS" to time object { hours, minutes }
function transformTimeString(
  timeString: string | undefined
): { hours: number; minutes: number } | undefined {
  if (!timeString) return undefined;

  const [hours, minutes] = timeString.split(":").map(Number);
  return { hours, minutes };
}

// Transform the payload to match server API expectations
function transformPayloadForServer(payload: ScheduleRequestPayload) {
  try {
    return {
      ...payload,
      employees: payload.employees.map((employee) => {
        const rankingValue = RELIABILITY_RATING_MAP[employee.ranking];
        if (rankingValue === undefined) {
          throw new Error(
            `Invalid reliability rating "${employee.ranking}" for employee ${
              employee.name
            }. Valid values: ${Object.keys(RELIABILITY_RATING_MAP).join(", ")}`
          );
        }
        return {
          ...employee,
          ranking: rankingValue,
        };
      }),
      earliest_start_time: payload.earliest_start_time,
      car_yards: payload.car_yards.map((yard) => ({
        ...yard,
        startTime: yard.startTime,
      })),
      radius_mode: payload.radius_mode,
    };
  } catch (error) {
    console.error("[Roster] Error transforming payload:", error);
    throw error;
  }
}

export async function generateRoster(payload: ScheduleRequestPayload) {
  try {
    // Validate environment variables
    const baseUrl = process.env.BASE_SCHEDULER_URL;
    const endpoint = process.env.ROSTER_ENDPOINT;

    if (!baseUrl || !endpoint) {
      const missing = [];
      if (!baseUrl) missing.push("BASE_SCHEDULER_URL");
      if (!endpoint) missing.push("ROSTER_ENDPOINT");
      throw new Error(
        `Missing required environment variables: ${missing.join(", ")}`
      );
    }

    // Transform the payload before sending to match server expectations
    const transformedPayload = transformPayloadForServer(payload);

    const url = `${baseUrl}${endpoint}`;
    // Only log in development to avoid exposing URLs in production
    if (process.env.NODE_ENV === "development") {
      console.log("[Roster] Making request to:", url);
    }

    // Create an AbortController for timeout handling
    // Timeout can be configured via environment variable, default to 2.5 minutes (150 seconds)
    // This gives a buffer above the expected 2 minute API response time
    // Note: Next.js server actions have their own timeout (default 60s, must be increased in next.config)
    // This fetch timeout should be less than the server action timeout to provide better error messages
    const timeoutMs =
      parseInt(process.env.ROSTER_REQUEST_TIMEOUT_MS || "150000", 10) || 150000;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    let response;
    try {
      response = await fetch(url, {
        body: JSON.stringify(transformedPayload),
        method: "post",
        headers: {
          "Content-Type": "application/json",
        },
        signal: controller.signal,
      });
      clearTimeout(timeoutId);
    } catch (fetchError) {
      clearTimeout(timeoutId);
      if (fetchError instanceof Error && fetchError.name === "AbortError") {
        throw new Error(
          "Request timeout: The roster generation took too long. Please try again."
        );
      }
      throw new Error(
        `Network error: ${
          fetchError instanceof Error ? fetchError.message : String(fetchError)
        }`
      );
    }

    if (!response.ok) {
      let errorText: string;
      try {
        errorText = await response.text();
      } catch {
        errorText = "Unable to read error response";
      }
      console.error("[Roster] Server error response:", {
        status: response.status,
        statusText: response.statusText,
        body: errorText,
      });
      throw new Error(
        `Failed to generate roster: ${response.status} ${response.statusText}. ${errorText}`
      );
    }

    let data;
    try {
      data = await response.json();
    } catch (jsonError) {
      console.error("[Roster] Failed to parse JSON response:", jsonError);
      throw new Error(
        "Failed to parse roster response: Server returned invalid JSON"
      );
    }

    // Validate that the response is serializable (basic check)
    try {
      JSON.stringify(data);
    } catch (serializeError) {
      console.error(
        "[Roster] Response data is not serializable:",
        serializeError
      );
      throw new Error(
        "Invalid response format: Server returned non-serializable data"
      );
    }

    return data;
  } catch (error) {
    console.error("[Roster] Error generating roster:", error);
    // Re-throw with more context if it's not already an Error
    if (error instanceof Error) {
      throw error;
    }
    throw new Error(`An unexpected error occurred: ${String(error)}`);
  }
}
