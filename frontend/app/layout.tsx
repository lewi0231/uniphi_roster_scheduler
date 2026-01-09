import Footer from "@/components/footer";
import Nav from "@/components/nav";
import { cn } from "@/lib/utils";
import React from "react";
import { Toaster } from "sonner";
import "./global.css";

import { Bebas_Neue, Cousine } from "next/font/google";

const bebas = Bebas_Neue({
  variable: "--font-bebas-neue",
  subsets: ["latin"],
  weight: ["400"],
});

const cousine = Cousine({
  variable: "--font-cousine",
  subsets: ["latin"],
  weight: ["400", "700"],
});

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
      </head>
      <body
        className={cn(
          "min-h-screen flex flex-col bg-gray-200",
          bebas.variable,
          cousine.variable
        )}
      >
        <Nav />
        <main className="flex-grow mt-32">{children}</main>
        <Footer />
        <Toaster position="top-center" richColors />
      </body>
    </html>
  );
}
