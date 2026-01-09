import { cn } from "@/lib/utils";

import Flower from "@/public/flower-lotus.svg";
import { Car } from "lucide-react";

const SIZE = {
  sm: {
    icon: "w-3 h-3",
    text: "text-sm",
  },
  lg: {
    icon: "w-6 h-6",
    text: "text-2xl",
  },
};

function Logo({
  size,
  logoText,
  icon,
}: {
  size?: string;
  icon: "car" | "flower";
  logoText: string[];
}) {
  const iconClassName = size ? SIZE[size].icon : SIZE.lg.icon;
  const textClassName = size ? SIZE[size].text : SIZE.lg.text;

  return (
    <div className={cn("flex items-center gap-[4px] justify-center")}>
      {icon === "car" ? (
        <Car size={28} color="white" />
      ) : (
        <Flower className={cn("w-6 h-6 text-[#ffffff] mb-1", iconClassName)} />
      )}
      <div className="flex items-center h-full">
        <h1 className={cn("font-cousine h-full text-secondary", textClassName)}>
          <span className="leading-0 tracking-tighter">{logoText[0]}</span>

          <span className="leading-0 tracking-tighter">{logoText[1]}</span>
        </h1>
      </div>
    </div>
  );
}

export default Logo;
