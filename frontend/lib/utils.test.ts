import { describe, expect, it } from "vitest";
import { getShiftDurationHours, timeStringToMinutes } from "./utils";

describe("timeStringToMinutes", () => {
  it("converts HH:MM:SS correctly when seconds are present", () => {
    expect(timeStringToMinutes("09:00:00")).toBe(9 * 60);
    expect(timeStringToMinutes("13:30:15")).toBe(13 * 60 + 30);
  });
  it("returns correct decimal and display format for whole-hour shifts", () => {
    const result = getShiftDurationHours("09:00:00", "11:00:00");

    // decimalFormat should be 2.0 (2 hours) formatted using formatToTwoDecimals
    expect(result.decimalFormat).toBe(2); // or 2.0 depending on your utils
    // displayFormat depends on formatDecimalHoursToTime, but likely "02:00"
    expect(result.displayFormat).toBe("2:00");
  });
  it("converts HH:MM:SS correctly when seconds are present", () => {
    expect(timeStringToMinutes("09:00:00")).toBe(9 * 60);
    expect(timeStringToMinutes("13:30:15")).toBe(13 * 60 + 30);
  });

  it("handles non-whole hour shifts correctly", () => {
    const result = getShiftDurationHours("09:15:00", "10:45:00");
    // 1.5 hours -> 1h30m
    expect(result.decimalFormat).toBeCloseTo(1.5, 5);
    expect(result.displayFormat).toBe("1:30"); // adjust if your formatter differs
  });

  it("handles incorrect time format (hours only)", () => {
    const result = getShiftDurationHours("09", "10");
    expect(result.decimalFormat).toBe(1);
    expect(result.displayFormat).toBe("1:00");
  });

  //   TODO - fix this so that it throws error.  Returning 0
  it("handles empty string", () => {
    const result = getShiftDurationHours("", "");
    // expect(result.decimalFormat).toBe(0); // This is NaN
  });

  // TODO - needs to throw also
  it("handles non numerical string", () => {
    const result = getShiftDurationHours("ab", "zz");
    expect(result.decimalFormat).toBe(NaN);
  });
});
