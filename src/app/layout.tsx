import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { ThemeProvider } from "next-themes";
import "./globals.css";
import { Toaster } from "@/components/ui/toaster";
import { BookmarksProvider } from "@/components/acos/bookmarks";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "ACOS — Avadhan Cognitive Operating System",
  description:
    "The Operating System for Cognitive Intelligence. A next-generation cognitive computing platform featuring Orthogonal Thread Memory, Hierarchical Binary Tree Attention, and Neuro-Symbolic reasoning.",
  keywords: [
    "ACOS",
    "AFM",
    "Cognitive OS",
    "Avadhan",
    "Orthogonal Thread Memory",
    "Neuro-Symbolic",
    "Continuous Learning",
  ],
  authors: [{ name: "Brahm AI Research Initiative" }],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning className="dark">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased bg-background text-foreground`}
      >
        <ThemeProvider
          attribute="class"
          defaultTheme="dark"
          enableSystem
          disableTransitionOnChange
        >
          <BookmarksProvider>
            {children}
            <Toaster />
          </BookmarksProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
