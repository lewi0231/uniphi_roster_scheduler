"use client";

import { cn } from "@/lib/utils";
import { type Worker } from "@/types/worker";
import { Plus } from "lucide-react";
import { useState } from "react";
import { Button } from "./ui/button";
import { Input } from "./ui/input";

type Props = {
  onAddWorker: (id: number, { name, rate }: Worker) => void;
  id: number;
};

function Worker({ onAddWorker, id }: Props) {
  const [name, setName] = useState<string>("");
  const [rate, setRate] = useState(100);
  const [error, setError] = useState<{
    name: { hasError: boolean; message: string };
    rate: { hasError: boolean; message: string };
  }>({
    name: { hasError: false, message: "" },
    rate: { hasError: false, message: "" },
  });

  const isValid = name.trim() !== "" && !isNaN(rate) && rate > 0 && rate <= 100;
  const hasErrors = error.name.hasError || error.rate.hasError;

  return (
    <div>
      <div className="grid grid-cols-4 mt-6 mb-4 gap-2 sm:gap-4 m-auto items-center">
        <Input
          className={cn(
            "col-span-2 border-2",
            error.name.hasError
              ? " border-red-500 hover:border-red-600"
              : isValid
              ? "border-green-600 hover:border-green-700"
              : "border-gray-400 hover:border-gray-500"
          )}
          value={name}
          onChange={(e) => {
            setName(e.target.value);
            setError((prev) => {
              return { ...prev, name: { hasError: false, message: "" } };
            });
          }}
          placeholder="e.g., John"
        />
        <Input
          placeholder="65"
          className={cn(
            "text-right border-2",

            error.rate.hasError
              ? " border-red-500 hover:border-red-600"
              : isValid
              ? "border-green-600 hover:border-green-700"
              : "border-gray-400 hover:border-gray-500"
          )}
          type="number"
          value={rate}
          min={1}
          max={100}
          step={5}
          onChange={(e) => {
            const parsedRate = parseInt(e.target.value);
            if (isNaN(parsedRate) || parsedRate >= 150) {
              return setError((prev) => {
                return {
                  ...prev,
                  rate: {
                    hasError: true,
                    message: "Rate format incorrect or too large!",
                  },
                };
              });
            }
            setRate(parseInt(e.target.value));
            setError((prev) => {
              return { ...prev, rate: { hasError: false, message: "" } };
            });
          }}
        />
        <Button
          size="icon"
          className={cn(
            "cursor-pointer",
            hasErrors
              ? "bg-red-500 hover:bg-red-600"
              : isValid
              ? "bg-green-500 hover:bg-green-600"
              : "bg-gray-400 hover:bg-gray-500"
          )}
          onClick={() => {
            const onInvalidInput = onValidationError(name, rate);
            if (onInvalidInput.name.hasError || onInvalidInput.rate.hasError) {
              setError(onInvalidInput);
              return;
            }
            onAddWorker(id, { name, rate });
            setName("");
            setRate(100);
            setError({
              name: { hasError: false, message: "" },
              rate: { hasError: false, message: "" },
            });
          }}
          disabled={error.name.hasError || error.rate.hasError}
        >
          <Plus />
        </Button>
      </div>
      {error.name.hasError ? (
        <p className="text-sm text-red-500 ml-2 font-semibold tracking-wide">
          {error.name.message}
        </p>
      ) : error.rate.hasError ? (
        <p className="text-sm text-red-500 ml-2 font-semibold tracking-wide">
          {error.rate.message}
        </p>
      ) : (
        ""
      )}

      <ul className="ml-4 mt-2">
        <li className="text-xs opacity-76 w-3/4 list-decimal">
          Add a worker, where the number represents what rate they achieved
          relative to the expected rate. Expressed as a percentage.
        </li>
      </ul>
    </div>
  );
}

function onValidationError(name: string, rate: number) {
  return {
    name: { hasError: name === "", message: "Name field cannot be empty!" },
    rate: { hasError: isNaN(rate), message: "Please recheck your rate field!" },
  };
}

export default Worker;
