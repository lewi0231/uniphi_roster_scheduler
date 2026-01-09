import { clsx, type ClassValue } from "clsx";
import ExcelJS from "exceljs";
import { saveAs } from "file-saver";
import { twMerge } from "tailwind-merge";
import { DAYS_OF_WEEK } from "./constants";
import { DayRoster, YardSchedule } from "./scheduler";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export const formatToTwoDecimals = (value: number): number => {
  return parseFloat(value.toFixed(2));
};

/**
 * Converts decimal hours to "hours:minutes" format (e.g., 2.5 -> "2:30")
 * @param decimalHours - The hours in decimal format (e.g., 2.5 for 2 hours 30 minutes)
 * @returns Formatted string in "hours:minutes" format
 */
export const formatDecimalHoursToTime = (decimalHours: number): string => {
  if (decimalHours <= 0) {
    return "00:00";
  }

  const totalMinutes = Math.round(decimalHours * 60);
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;

  return `${hours}:${minutes.toString().padStart(2, "0")}`;
};

export const timeStringToMinutes = (timeValue: string) => {
  const [hours = "0", minutes = "0"] = timeValue.split(":");
  return parseInt(hours, 10) * 60 + parseInt(minutes, 10);
};

export function getShiftDurationHours(startTime: string, endTime: string) {
  const startMinutes = timeStringToMinutes(startTime);
  const endMinutes = timeStringToMinutes(endTime);
  const totalMinutes = endMinutes - startMinutes;

  if (totalMinutes <= 0) {
    return { displayFormat: "00:00", decimalFormat: 0 };
  }

  const decimalValue = formatToTwoDecimals(totalMinutes / 60);
  const displayFormat = formatDecimalHoursToTime(decimalValue);

  return {
    displayFormat,
    decimalFormat: decimalValue,
  };
}

/**
 * Formats a time string (HH:MM:SS or HH:MM) to a readable format (HH:MM)
 */
function formatTime(timeString: string): string {
  const [hours, minutes] = timeString.split(":").slice(0, 2);
  return `${hours}:${minutes}`;
}

/**
 * Capitalizes the first letter of a day name for display
 */
function capitalizeDay(day: string): string {
  return day.charAt(0).toUpperCase() + day.slice(1);
}

export async function downloadExcel(data: DayRoster[]) {
  const rosterName = "Roster-" + new Date().toISOString().split("T")[0];

  const workbook = new ExcelJS.Workbook();
  const worksheet = workbook.addWorksheet(rosterName);

  // Set up column headers (days of week)
  worksheet.columns = DAYS_OF_WEEK.map((day) => ({
    header: capitalizeDay(day),
    key: day,
    width: 30,
    style: {
      alignment: { vertical: "top", wrapText: true },
    },
  }));

  // Style the header row
  const headerRow = worksheet.getRow(1);
  headerRow.font = { bold: true };
  headerRow.alignment = { horizontal: "center", vertical: "middle" };
  headerRow.fill = {
    type: "pattern",
    pattern: "solid",
    fgColor: { argb: "FFE0E0E0" },
  };
  headerRow.height = 30;

  // Create a map of day -> yards for efficient lookup
  const dayMap = new Map<string, YardSchedule[]>();
  data.forEach((dayRoster) => {
    dayMap.set(dayRoster.day, dayRoster.yards);
  });

  // Find the maximum number of yards scheduled on any single day
  let maxYardsPerDay = 0;
  DAYS_OF_WEEK.forEach((day) => {
    const yards = dayMap.get(day) || [];
    maxYardsPerDay = Math.max(maxYardsPerDay, yards.length);
  });

  // If no yards scheduled, just add the headers
  if (maxYardsPerDay === 0) {
    const buffer = await workbook.xlsx.writeBuffer();
    const blob = new Blob([buffer], {
      type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    });
    saveAs(blob, `${rosterName}.xlsx`);
    return;
  }

  // Populate rows - each row represents a yard slot (index 0 to maxYardsPerDay - 1)
  for (let rowIndex = 0; rowIndex < maxYardsPerDay; rowIndex++) {
    const row = worksheet.getRow(rowIndex + 2); // +2 because row 1 is header
    row.height = 60;

    DAYS_OF_WEEK.forEach((day, colIndex) => {
      const yards = dayMap.get(day) || [];
      const yard = yards[rowIndex];

      if (yard) {
        // Format: Yard Name\nTime: Start - Finish\nWorkers: Worker1, Worker2
        const timeRange = `${formatTime(yard.start_time)} - ${formatTime(
          yard.finish_time
        )}`;
        const workersList =
          yard.workers.length > 0 ? yard.workers.join(", ") : "None";

        const cellValue = `${yard.car_yard_name}\nWorkers: ${workersList}`;

        row.getCell(colIndex + 1).value = cellValue;
        row.getCell(colIndex + 1).alignment = {
          vertical: "top",
          wrapText: true,
        };
        row.getCell(colIndex + 1).font = { size: 10 };
      }
    });
  }

  // Write and download
  const buffer = await workbook.xlsx.writeBuffer();
  const blob = new Blob([buffer], {
    type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  });
  saveAs(blob, `${rosterName}.xlsx`);
}
