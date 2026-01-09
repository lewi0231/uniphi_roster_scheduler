import { CarYardRegion, ScheduleRequestPayload } from "@/lib/scheduler";
import { cn } from "@/lib/utils";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from "./ui/select";

const CAR_YARD_REGION: CarYardRegion[] = ["south", "north", "central"];

type SelectCarYardRegionProps = {
  worker?: ScheduleRequestPayload["employees"][number];
  handleSelectRegion?: (workerId: number, region: CarYardRegion) => void;
  value?: CarYardRegion;
  onSelect?: (region: CarYardRegion) => void;
  placeholder?: string;
  triggerClassName?: string;
  handleUpdateWorker?: (
    region: CarYardRegion,
    updater: (
      worker: ScheduleRequestPayload["employees"][number]
    ) => ScheduleRequestPayload["employees"][number]
  ) => void;
};

const SelectCarYardRegion = ({
  worker,
  handleSelectRegion,
  value,
  onSelect,
  placeholder = "Select region",
  triggerClassName,
}: SelectCarYardRegionProps) => {
  const selectedRegion = worker?.not_region ?? value;

  const handleChange = (region: string) => {
    const castedRegion = region as CarYardRegion;
    if (worker && handleSelectRegion) {
      handleSelectRegion(worker.id, castedRegion);
    }

    onSelect?.(castedRegion);
  };

  return (
    <div className="w-full overflow-hidden">
      <Select onValueChange={handleChange} value={selectedRegion}>
        <SelectTrigger
          className={cn(
            "w-full border-2 border-foreground/10",
            triggerClassName
          )}
        >
          <SelectValue placeholder={placeholder} />
        </SelectTrigger>
        <SelectContent className="">
          <SelectGroup className="">
            <SelectLabel>Region</SelectLabel>
            {CAR_YARD_REGION.map((region) => (
              <SelectItem key={region} value={region}>
                {region.charAt(0).toUpperCase() + region.substring(1)}
              </SelectItem>
            ))}
          </SelectGroup>
        </SelectContent>
      </Select>
    </div>
  );
};

export default SelectCarYardRegion;
