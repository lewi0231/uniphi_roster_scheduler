import { DayOfWeek } from "./scheduler";

export const DAYS_OF_WEEK: DayOfWeek[] = [
  "monday",
  "tuesday",
  "wednesday",
  "thursday",
  "friday",
  "saturday",
];

export const AVAILABILITY_HEADINGS = [
  ...DAYS_OF_WEEK.map((day) => ({
    heading: day.substring(0, 3),
    tooltip: `Employee availability on ${day}`,
  })),
  {
    heading: "excluded yards",
    tooltip: "Car yards where this employee cannot be rostered",
  },
  {
    heading: "under perform",
    tooltip: "Mark if this employee is underperforming",
  },
] as const;

export const CAR_YARD_HEADINGS = [
  // "yard id",
  {
    heading: "per week",
    tooltip: "Number of visits required per week for this car yard",
  },
  {
    heading: "no. days gap",
    tooltip: "Minimum number of days between visits",
  },
  {
    heading: "region",
    tooltip: "The region where this car yard is located",
  },
  {
    heading: "position",
    tooltip: "North-south position ranking (lower numbers are further north)",
  },
  {
    heading: "min workers",
    tooltip: "Minimum number of workers required for this car yard",
  },
  {
    heading: "max workers",
    tooltip: "Maximum number of workers required for this car yard",
  },
  {
    heading: "length in hours",
    tooltip: "Total hours required to complete work at this car yard",
  },
  {
    heading: "start time",
    tooltip: "Preferred start time for work at this car yard",
  },
  {
    heading: "linked yard",
    tooltip: "Another car yard that is linked to this one",
  },
  {
    heading: "no. days gap",
    tooltip: "Number of days gap between this yard and its linked yard",
  },
  {
    heading: "required days",
    tooltip: "Days of the week when work is required at this car yard",
  },
] as const;
