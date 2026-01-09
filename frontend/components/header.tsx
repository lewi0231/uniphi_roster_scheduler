import { cn } from "@/lib/utils";

function Header({
  children,
  textClassName,
  subText,
}: {
  children: string;
  textClassName?: string;
  subText?: string;
}) {
  return (
    <header className="flex justify-center flex-col items-start w-1/2">
      <h2
        className={cn(
          "text-5xl py-6 text-left w-full tracking-tight",
          textClassName
        )}
      >
        {children}
      </h2>
      <p className="text-sm text-muted-foreground">{subText}</p>
    </header>
  );
}

export default Header;
