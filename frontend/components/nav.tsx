"use client";

import { UseIsScrollTop } from "@/hooks/use-is-scroll-top";
import { cn } from "@/lib/utils";
import Logo from "./logo";

const Nav = () => {
  const { isTop } = UseIsScrollTop();

  return (
    <nav
      className={cn(
        "fixed bg-linear-to-br from-gray-500 to-gray-400 w-full py-6 transition-all duration-500 backdrop-blur-2xl -translate-y-20 left-1/2 -translate-x-1/2 px-10",
        isTop ? "opacity-100 translate-y-0" : "opacity-0"
      )}
    >
      <div className="max-w-[1200px] mx-auto flex items-center justify-start w-full">
        <Logo logoText={["Uni", "Phi"]} icon="car" />
      </div>
    </nav>
  );
};

export default Nav;
