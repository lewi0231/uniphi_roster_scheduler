import { ScheduleRequestPayload } from "@/lib/scheduler";
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

type SelectLinkedYardProps = {
  carYards: ScheduleRequestPayload["car_yards"];
  currentYardId: number;
  value?: number; // The linked yard ID
  onSelect?: (yardId: number | undefined) => void;
  placeholder?: string;
  triggerClassName?: string;
};

const SelectLinkedYard = ({
  carYards,
  currentYardId,
  value,
  onSelect,
  placeholder = "None",
  triggerClassName,
}: SelectLinkedYardProps) => {
  // Filter out the current yard (can't link to itself)
  // Allow linking to other yards even if they have links (enables chains)
  const availableYards = carYards.filter((yard) => yard.id !== currentYardId);

  const handleChange = (selectedValue: string) => {
    if (selectedValue === "none") {
      onSelect?.(undefined);
    } else {
      onSelect?.(Number(selectedValue));
    }
  };

  const selectedValue = value?.toString() ?? "none";

  return (
    <div className=" overflow-hidden w-full">
      <Select onValueChange={handleChange} value={selectedValue}>
        <SelectTrigger
          className={cn(
            "w-full h-full border-2 border-foreground/10 cursor-pointer",
            triggerClassName
          )}
        >
          <SelectValue placeholder={placeholder} className="" />
        </SelectTrigger>
        <SelectContent className="">
          <SelectGroup>
            <SelectLabel>Linked Yard</SelectLabel>
            <SelectItem value="none"></SelectItem>
            {availableYards.map((yard) => (
              <SelectItem key={yard.id} value={yard.id.toString()}>
                {yard.name} (ID: {yard.id})
              </SelectItem>
            ))}
          </SelectGroup>
        </SelectContent>
      </Select>
    </div>
  );
};

export default SelectLinkedYard;
