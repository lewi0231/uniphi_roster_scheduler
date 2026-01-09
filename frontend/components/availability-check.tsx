import { Checkbox } from "./ui/checkbox";

const daysOfTheWeek = [
  "monday",
  "tuesday",
  "wednesday",
  "thursday",
  "friday",
  "saturday",
];

function AvailabilityCheck() {
  return (
    <div>
      <ul className="grid grid-cols-8 gap-6 border-2 w-1/2">
        <div className="col-span-2"></div>
        {daysOfTheWeek.map((day) => (
          <li
            key={day}
            className="-rotate-90 border-2 w-30 col-span-1 text-muted-foreground mb-12"
          >
            {day}
          </li>
        ))}
      </ul>
      <div className="flex gap-4">
        <div className="flex items-center gap-3">
          <Checkbox id="terms" />
        </div>
      </div>
    </div>
  );
}

export default AvailabilityCheck;
