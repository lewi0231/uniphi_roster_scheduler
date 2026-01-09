import { DayOfWeek, ScheduleRequestPayload } from "@/lib/scheduler";
import { Plus } from "lucide-react";
import { useState } from "react";
import { Button } from "./ui/button";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from "./ui/select";

export const workdays = [
  {
    value: "monday",
    label: "Monday",
  },
  {
    value: "tuesday",
    label: "Tuesday",
  },
  {
    value: "wednesday",
    label: "Wednesday",
  },
  {
    value: "thursday",
    label: "Thursday",
  },
  {
    value: "friday",
    label: "Friday",
  },
  {
    value: "saturday",
    label: "Saturday",
  },
] as const;

const SelectDayOfWeek = ({
  worker,
  handleAddAvailability,
}: {
  worker: ScheduleRequestPayload["employees"][number];
  handleAddAvailability: (workerId: number, selectedDay: DayOfWeek) => void;
}) => {
  const [selectedDay, setSelectedDay] = useState<DayOfWeek>();

  return (
    <div className="flex justify-between overflow-hidden mt-4 gap-2">
      <Select onValueChange={(value) => setSelectedDay(value as DayOfWeek)}>
        <SelectTrigger className="w-full">
          <SelectValue placeholder="Select a day" />
        </SelectTrigger>
        <SelectContent>
          <SelectGroup>
            <SelectLabel>Days</SelectLabel>
            {workdays
              .filter((day) => !worker.available_days.includes(day.value))
              .map((day, index) => (
                <SelectItem key={index + worker.id} value={day.value}>
                  {day.label}
                </SelectItem>
              ))}
          </SelectGroup>
        </SelectContent>
      </Select>
      <Button
        className=""
        size="icon"
        onClick={() => {
          if (!selectedDay) return;
          handleAddAvailability(worker.id, selectedDay);
          setSelectedDay(undefined);
        }}
      >
        <Plus />
      </Button>
    </div>
  );
};

export default SelectDayOfWeek;
