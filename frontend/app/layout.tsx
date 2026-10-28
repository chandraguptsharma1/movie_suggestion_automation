import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Movie Suggestion Automation | Group Shorts Studio",
  description: "AI-driven thematic movie suggestions, Devanagari Hindi Shorts scripts, Sarvam neural voiceovers, and viral Shiro Bro thumbnails.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="bg-slate-950 text-slate-100 antialiased">{children}</body>
    </html>
  );
}
