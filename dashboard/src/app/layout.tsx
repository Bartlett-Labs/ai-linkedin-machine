import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Link from "next/link";
import { LayoutDashboard, Bell, BarChart3, Clock, Users, FileText, Target, MessageSquare, Shield, Zap, Calendar } from "lucide-react";

const inter = Inter({ subsets: ["latin"] });
export const metadata: Metadata = { title: "LinkedIn Dashboard", description: "LinkedIn automation engine dashboard" };

const NAV = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/alerts", label: "Alerts", icon: Bell },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/history", label: "History", icon: Clock },
  { type: "divider" as const, label: "Configuration" },
  { href: "/config/engine", label: "Engine", icon: Zap },
  { href: "/config/schedule", label: "Schedule", icon: Calendar },
  { href: "/config/content", label: "Content", icon: FileText },
  { href: "/config/targets", label: "Targets", icon: Target },
  { href: "/config/templates", label: "Templates", icon: MessageSquare },
  { href: "/config/rules", label: "Rules", icon: Shield },
  { href: "/config/personas", label: "Personas", icon: Users },
] as const;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} bg-background text-foreground`}>
        <div className="flex h-screen">
          <aside className="w-60 border-r bg-card flex flex-col">
            <div className="p-4 border-b">
              <h1 className="text-lg font-bold">LinkedIn Engine</h1>
              <p className="text-xs text-muted-foreground">Dashboard v1.0</p>
            </div>
            <nav className="flex-1 p-2 space-y-1 overflow-y-auto">
              {NAV.map((item, i) =>
                "type" in item ? (
                  <p key={i} className="px-3 pt-4 pb-1 text-xs font-semibold text-muted-foreground uppercase tracking-wider">{item.label}</p>
                ) : (
                  <Link key={item.href} href={item.href} className="flex items-center gap-2 px-3 py-2 text-sm rounded-md hover:bg-accent transition-colors">
                    <item.icon className="h-4 w-4" />{item.label}
                  </Link>
                )
              )}
            </nav>
          </aside>
          <main className="flex-1 overflow-y-auto p-6">{children}</main>
        </div>
      </body>
    </html>
  );
}
