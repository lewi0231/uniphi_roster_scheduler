import { ScheduleRequestPayload } from "@/lib/scheduler";
import { cn } from "@/lib/utils";
import { X } from "lucide-react";
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

type SelectExcludedYardsProps = {
  worker: ScheduleRequestPayload["employees"][number];
  carYards: ScheduleRequestPayload["car_yards"];
  onUpdateWorker: (
    updater: (
      worker: ScheduleRequestPayload["employees"][number]
    ) => ScheduleRequestPayload["employees"][number]
  ) => void;
};

const SelectExcludedYards = ({
  worker,
  carYards,
  onUpdateWorker,
}: SelectExcludedYardsProps) => {
  const excludedYardIds = worker.excluded_yards ?? [];
  const [selectValue, setSelectValue] = useState<string>("none");

  // Filter out already excluded yards from available options
  const availableYards = carYards.filter(
    (yard) => !excludedYardIds.includes(yard.id)
  );

  const handleAddYard = (yardIdStr: string) => {
    if (yardIdStr === "none") {
      setSelectValue("none");
      return;
    }
    const yardId = Number(yardIdStr);
    const updatedExcludedYards = [...excludedYardIds, yardId];
    onUpdateWorker((current) => ({
      ...current,
      excluded_yards:
        updatedExcludedYards.length > 0 ? updatedExcludedYards : undefined,
    }));
    // Reset select to "none" after adding
    setSelectValue("none");
  };

  const handleRemoveYard = (yardId: number) => {
    const updatedExcludedYards = excludedYardIds.filter((id) => id !== yardId);
    onUpdateWorker((current) => ({
      ...current,
      excluded_yards:
        updatedExcludedYards.length > 0 ? updatedExcludedYards : undefined,
    }));
  };

  const getYardName = (yardId: number) => {
    return (
      carYards.find((yard) => yard.id === yardId)?.name ?? `Yard ${yardId}`
    );
  };

  return (
    <div className="w-full flex flex-col gap-2 p-2">
      {excludedYardIds.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {excludedYardIds.map((yardId) => (
            <div
              key={yardId}
              className="inline-flex items-center gap-1.5 px-2 py-1 text-xs rounded-md bg-secondary text-secondary-foreground border border-border"
            >
              <span>{getYardName(yardId)}</span>
              <Button
                variant="ghost"
                size="icon"
                className="h-4 w-4 p-0 hover:bg-destructive/20 hover:text-destructive rounded-full"
                onClick={() => handleRemoveYard(yardId)}
                aria-label={`Remove ${getYardName(yardId)} from excluded yards`}
              >
                <X className="h-3 w-3" />
              </Button>
            </div>
          ))}
        </div>
      )}
      <Select
        onValueChange={handleAddYard}
        value={selectValue}
        disabled={availableYards.length === 0}
      >
        <SelectTrigger
          className={cn(
            "w-full border-2 border-foreground/10 h-8 text-xs",
            availableYards.length === 0 && "opacity-50 cursor-not-allowed"
          )}
        >
          <SelectValue
            placeholder={
              availableYards.length === 0
                ? "No yards available"
                : "Add yard to exclude"
            }
          />
        </SelectTrigger>
        <SelectContent>
          <SelectGroup>
            <SelectLabel>Exclude Yard</SelectLabel>
            {availableYards.length === 0 ? (
              <SelectItem value="none" disabled>
                All yards excluded
              </SelectItem>
            ) : (
              <>
                <SelectItem value="none">Select a yard...</SelectItem>
                {availableYards.map((yard) => (
                  <SelectItem key={yard.id} value={yard.id.toString()}>
                    {yard.name} (ID: {yard.id})
                  </SelectItem>
                ))}
              </>
            )}
          </SelectGroup>
        </SelectContent>
      </Select>
    </div>
  );
};

export default SelectExcludedYards;
