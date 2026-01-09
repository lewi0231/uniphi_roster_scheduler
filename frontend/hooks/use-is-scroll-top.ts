"use client";
import { useEffect, useState } from "react";

export const UseIsScrollTop = () => {
  const [isTop, setIsTop] = useState(true);

  useEffect(() => {
    const handleScrollTop = () => {
      if (window.scrollY === 0) setIsTop(true);
      else setIsTop(false);
    };

    window.addEventListener("scroll", handleScrollTop);

    return () => window.removeEventListener("scroll", handleScrollTop);
  }, []);

  return { isTop };
};
