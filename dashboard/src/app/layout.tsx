"use client";

import { Plus_Jakarta_Sans, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard, Bell, BarChart3, Clock, Users, FileText, Target,
  MessageSquare, Shield, Zap, Calendar, ListTodo, Play, AlertTriangle,
  Rss, HeartPulse, Activity, Crosshair, Link2,
} from "lucide-react";

const jakarta = Plus_Jakarta_Sans({
  subsets: ["latin"],
  variable: "--font-jakarta",
  display: "swap",
});

const jetbrains = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains",
  display: "swap",
});

const NAV = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/alerts", label: "Alerts", icon: Bell },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/history", label: "History", icon: Clock },
  { type: "divider" as const, label: "Operations" },
  { href: "/queue", label: "Queue", icon: ListTodo },
  { href: "/runs", label: "Pipeline Runs", icon: Play },
  { href: "/errors", label: "Errors", icon: AlertTriangle },
  { type: "divider" as const, label: "Personas" },
  { href: "/personas/scheduler", label: "Scheduler", icon: HeartPulse },
  { href: "/personas/activity", label: "Activity", icon: Activity },
  { href: "/leads", label: "Leads", icon: Crosshair },
  { href: "/connections", label: "Connections", icon: Link2 },
  { type: "divider" as const, label: "Configuration" },
  { href: "/config/engine", label: "Engine", icon: Zap },
  { href: "/config/schedule", label: "Schedule", icon: Calendar },
  { href: "/config/content", label: "Content", icon: FileText },
  { href: "/config/targets", label: "Targets", icon: Target },
  { href: "/config/templates", label: "Templates", icon: MessageSquare },
  { href: "/config/rules", label: "Rules", icon: Shield },
  { href: "/config/personas", label: "Personas", icon: Users },
  { href: "/config/feeds", label: "Feeds", icon: Rss },
] as const;

function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-60 border-r border-[#2a3138] bg-[#0d0f10] flex flex-col">
      {/* Brand */}
      <div className="px-5 pt-5 pb-4">
        <div className="flex items-center gap-2.5">
          <div className="h-8 w-8 rounded-lg bg-[#06b6d4]/10 border border-[#06b6d4]/20 flex items-center justify-center">
            <Zap className="h-4 w-4 text-[#06b6d4]" />
          </div>
          <div>
            <h1 className="text-sm font-semibold tracking-tight text-[#f3f5f7]">LinkedIn Engine</h1>
            <p className="text-[10px] text-[#73808c] font-mono-data">v1.0 &middot; operator console</p>
          </div>
        </div>
        <div className="mt-4 h-px bg-gradient-to-r from-[#06b6d4]/30 via-[#2a3138] to-transparent" />
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 pb-3 space-y-0.5 overflow-y-auto">
        {NAV.map((item, i) =>
          "type" in item ? (
            <p key={i} className="px-2 pt-5 pb-1.5 text-[10px] font-semibold text-[#73808c] uppercase tracking-[0.08em]">
              {item.label}
            </p>
          ) : (() => {
            const isActive = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-2.5 px-2.5 py-[7px] text-[13px] rounded-md transition-all duration-150 ${
                  isActive
                    ? "bg-[#06b6d4]/8 text-[#06b6d4] border-l-2 border-[#06b6d4] -ml-px pl-[9px] font-medium"
                    : "text-[#a7b0b8] hover:text-[#f3f5f7] hover:bg-[#161a1d]"
                }`}
              >
                <item.icon className={`h-[15px] w-[15px] ${isActive ? "text-[#06b6d4]" : "text-[#73808c]"}`} />
                {item.label}
              </Link>
            );
          })()
        )}
      </nav>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-[#2a3138]">
        <div className="flex items-center gap-2">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#22c55e] opacity-40" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-[#22c55e]" />
          </span>
          <span className="text-[11px] text-[#73808c]">System Online</span>
        </div>
      </div>
    </aside>
  );
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <head>
        <title>LinkedIn Engine — Operator Console</title>
        <meta name="description" content="LinkedIn automation engine dashboard" />
      </head>
      <body className={`${jakarta.variable} ${jetbrains.variable} font-[family-name:var(--font-jakarta)] bg-background text-foreground`}>
        <div className="flex h-screen">
          <Sidebar />
          <main className="flex-1 overflow-y-auto p-6">{children}</main>
        </div>
      </body>
    </html>
  );
}
