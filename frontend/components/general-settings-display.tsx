import Header from "@/components/header";
import InputCounter from "@/components/input-counter";
import TimePicker from "@/components/ui/time-picker";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { RadiusMode } from "@/lib/scheduler";

type GeneralSettingsDisplayProps = {
  maxHoursPerDay: number;
  earliestStartTime: string; // Format: "HH:MM"
  maxRadius: number;
  radiusMode: RadiusMode;
  onMaxHoursPerDayChange: (value: number) => void;
  onEarliestStartTimeChange: (value: string) => void;
  onMaxRadiusChange: (value: number) => void;
  onRadiusModeChange: (value: RadiusMode) => void;
};

const GeneralSettingsDisplay = ({
  maxHoursPerDay,
  earliestStartTime,
  maxRadius,
  radiusMode,
  onMaxHoursPerDayChange,
  onEarliestStartTimeChange,
  onMaxRadiusChange,
  onRadiusModeChange,
}: GeneralSettingsDisplayProps) => {
  return (
    <section className="w-full mx-auto border-b pb-4">
      <Header subText="Configure general scheduling parameters that apply across all employees and car yards.">
        General Settings
      </Header>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 pt-10 pb-4">
        <div className="flex flex-col gap-2">
          <label
            htmlFor="max-hours-per-day"
            className="text-sm font-medium text-muted-foreground"
          >
            Max Shift Length (hours)
          </label>
          <div className="flex items-center gap-2 bg-muted/50 py-3 px-3 rounded-md border-2 border-foreground/10">
            <InputCounter
              min={1}
              step={0.5}
              value={maxHoursPerDay}
              onValueChange={onMaxHoursPerDayChange}
              max={24}
              ariaLabel="Maximum hours per day"
              className="max-w-[8rem] border-2 border-foreground/10"
            />
            <span className="text-sm text-muted-foreground ">hours</span>
          </div>
        </div>
        <div className="flex flex-col gap-2">
          <TimePicker
            value={earliestStartTime}
            onChange={onEarliestStartTimeChange}
            label="Base Start Time"
            id="earliest-start-time"
            ariaLabel="Earliest start time for shifts"
            className="max-w-xs"
            labelClassName="text-muted-foreground"
            contentClassName="border-2 border-foreground/10"
            inputClassName="border-2 border-foreground/10"
          />
        </div>
        <div className="flex flex-col gap-2">
          <label
            htmlFor="max-radius"
            className="text-sm font-medium text-muted-foreground"
          >
            Max Position Radius
          </label>
          <div className="flex items-center gap-2 bg-muted/50 py-3 px-3 rounded-md border-2 border-foreground/10">
            <InputCounter
              min={1}
              step={1}
              value={maxRadius}
              onValueChange={onMaxRadiusChange}
              max={100}
              ariaLabel="Maximum position difference between yards that can be scheduled same day"
              className="max-w-[8rem] border-2 border-foreground/10"
            />
            <span className="text-sm text-muted-foreground">units</span>
          </div>
        </div>
        <div className="flex flex-col gap-2">
          <Label
            htmlFor="radius-mode"
            className="text-sm font-medium text-muted-foreground"
          >
            Radius Constraint Mode
          </Label>
          <div className="bg-muted/50 py-3 px-3 rounded-md border-2 border-foreground/10">
            <Select
              value={radiusMode}
              onValueChange={(value) => onRadiusModeChange(value as RadiusMode)}
            >
              <SelectTrigger
                id="radius-mode"
                className="border-2 border-foreground/10 bg-background w-full"
              >
                <SelectValue placeholder="Select mode" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="soft">
                  Soft (Penalize violations)
                </SelectItem>
                <SelectItem value="hard">
                  Hard (Forbid violations)
                </SelectItem>
                <SelectItem value="off">
                  Off (Ignore radius)
                </SelectItem>
              </SelectContent>
            </Select>
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            {radiusMode === "soft" &&
              "Penalizes far-apart yards on same day (may still allow)"}
            {radiusMode === "hard" &&
              "Forbids far-apart yards on same day (may fail if impossible)"}
            {radiusMode === "off" && "Ignores radius constraint entirely"}
          </p>
        </div>
      </div>
    </section>
  );
};

export default GeneralSettingsDisplay;
