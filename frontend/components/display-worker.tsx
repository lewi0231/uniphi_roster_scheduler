"use client";

import { formatDecimalHoursToTime, formatToTwoDecimals } from "@/lib/utils";
import { Worker } from "@/types/worker";
import { Minus, Plus } from "lucide-react";
import { Button } from "./ui/button";

type Props = {
  onRemoveWorker: (id: number) => void;
  onUpdateWorker: (id: number, updates: Partial<Worker>) => void;
  worker: Worker;
  index: number;
};

function DisplayWorker({
  index,
  worker,
  onRemoveWorker,
  onUpdateWorker,
}: Props) {
  const ADD_SUBTRACT_VALUE = 0.083;

  const incrementShift = () => {
    const newShiftLength = worker.shiftLength + ADD_SUBTRACT_VALUE;
    onUpdateWorker(index, { shiftLength: newShiftLength });
  };

  const decrementShift = () => {
    const newShiftLength = worker.shiftLength - ADD_SUBTRACT_VALUE;
    if (newShiftLength <= 0) return;
    onUpdateWorker(index, { shiftLength: newShiftLength });
  };

  return (
    <div className="grid grid-cols-5 text-sm my-2">
      <p className="text-left">{worker.name}</p>

      <div className="flex items-center justify-end gap-2">
        <Button
          size="sm"
          variant="outline"
          className="h-5 w-5"
          onClick={decrementShift}
        >
          <Minus className="" />
        </Button>
        <span className="min-w-[2rem] text-right">
          {formatDecimalHoursToTime(worker.shiftLength ?? 0)}
        </span>
        <Button
          size="sm"
          variant="outline"
          className="h-5 w-5"
          onClick={incrementShift}
        >
          <Plus className="" />
        </Button>
      </div>

      <p className="text-right">{worker.rate}</p>
      <p className=" text-right">
        {formatToTwoDecimals(worker?.percentage ?? 0)}
      </p>
      <div className="text-right">
        <Button
          className="cursor-pointer "
          size="sm"
          variant="secondary"
          onClick={() => onRemoveWorker(index)}
        >
          <Minus className="" />
        </Button>
      </div>
    </div>
  );
}

export default DisplayWorker;
