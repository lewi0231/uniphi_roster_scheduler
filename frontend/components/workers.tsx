"use client";

import { type Worker as WorkerType } from "@/types/worker";
import { LucideTrash } from "lucide-react";
import { useEffect, useState } from "react";
import DisplayWorker from "./display-worker";
import { Button } from "./ui/button";
import Worker from "./worker";

function Workers({
  defaultRate,
  shiftLength,
}: {
  defaultRate: number;
  shiftLength: { decimalFormat: number; displayFormat: string };
}) {
  const [workers, setWorkers] = useState<Worker[]>([]);

  const handleUpdateWorker = (index: number, updates: Partial<Worker>) => {
    setWorkers((prev) =>
      prev.map((worker, i) => {
        if (i !== index) return worker;

        const workerShiftLength =
          updates?.shiftLength !== undefined
            ? Math.min(updates.shiftLength, shiftLength.decimalFormat)
            : worker.shiftLength;

        return { ...worker, ...updates, shiftLength: workerShiftLength };
      })
    );
  };

  const onAddWorker = (id: number, { name, rate }: WorkerType) => {
    setWorkers((prev) => {
      return [...prev, { name, rate, shiftLength: shiftLength.decimalFormat }];
    });
  };

  const onRemoveWorker = (id: number) => {
    if (id < 0 || id >= workers?.length) {
      console.error("Invalid worker index:", id);
      return;
    }

    setWorkers((prev) => {
      return prev.filter((worker, index) => index !== id);
    });
  };

  useEffect(() => {
    const handleShiftLengthUpdate = async () => {
      setWorkers((prev) => {
        return prev.map((worker) => ({
          ...worker,
          shiftLength: shiftLength.decimalFormat,
        }));
      });
    };
    handleShiftLengthUpdate();
  }, [shiftLength]);

  return (
    <div>
      {workers?.length > 0 ? (
        <div className="grid grid-cols-5 ga-4 my-4 pt-6 m-auto font-semibold text-sm">
          <h2 className="text-left">Name</h2>
          <h2 className="text-right">Shift Length</h2>

          <h2 className="text-right">% of Expected</h2>
          <h2 className="text-right">Relative %</h2>
          <h2 className="text-right">Delete</h2>
        </div>
      ) : (
        ""
      )}

      {workers?.length > 0
        ? calculatePercentages(
            workers,
            defaultRate,
            shiftLength.decimalFormat
          ).map((worker, index) => {
            console.log(worker.name, index);
            return (
              <DisplayWorker
                key={index + worker.name}
                index={index}
                onRemoveWorker={onRemoveWorker}
                worker={worker}
                onUpdateWorker={handleUpdateWorker}
              />
            );
          })
        : ""}
      {workers?.length > 0 ? (
        <div className="mt-4 flex justify-end">
          <Button
            variant="secondary"
            className="cursor-pointer"
            onClick={() => {
              setWorkers([]);
            }}
          >
            <LucideTrash />
          </Button>
        </div>
      ) : (
        ""
      )}

      <Worker id={workers?.length ?? 0} onAddWorker={onAddWorker} />
    </div>
  );
}

const calculatePercentages = (
  workers: Worker[],
  defaultRate: number,
  defaultShiftLength: number
) => {
  let totalActualContributions = 0;
  const amendedWorkers = [...workers];

  workers.forEach((worker, index) => {
    const ratePerHour = (worker.rate / 100) * defaultRate;
    const expectedContribution = ratePerHour * defaultShiftLength;
    const actualContribution = ratePerHour * worker.shiftLength;

    amendedWorkers[index] = {
      ...worker,
      actualRate: ratePerHour,
      expectedContribution,
      actualContribution,
    };
    totalActualContributions += actualContribution;
  });

  amendedWorkers.forEach((worker, index) => {
    const percentage =
      totalActualContributions > 0
        ? roundToDecimal(
            (worker.actualContribution / totalActualContributions) * 100,
            2
          )
        : 0;

    amendedWorkers[index] = {
      ...worker,
      percentage,
    };
  });
  return amendedWorkers;
};

function roundToDecimal(number: number, decimals: number) {
  const multiplier = Math.pow(10, decimals);
  return Math.round(number * multiplier) / multiplier;
}

export default Workers;
