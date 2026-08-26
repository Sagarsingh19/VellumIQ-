"use client";

import React, { useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { LayoutDashboard, Settings2, LogOut, Loader2, Building, ShieldAlert } from "lucide-react";
import { useAuth } from "@/context/AuthContext";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { user, activeOrganization, loading, logoutUser } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.push("/login");
    }
  }, [user, loading, router]);

  if (loading || !user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-10 w-10 text-blue-500 animate-spin" />
          <p className="text-slate-500 text-sm font-semibold">Loading session workspace...</p>
        </div>
      </div>
    );
  }

  const getPlanBadgeColor = (plan: string) => {
    switch (plan) {
      case "GROWTH":
        return "bg-purple-100 text-purple-700 border-purple-200";
      case "ENTERPRISE":
        return "bg-blue-100 text-blue-700 border-blue-200";
      default:
        return "bg-slate-100 text-slate-700 border-slate-200";
    }
  };

  return (
    <div className="flex min-h-screen bg-slate-50">
      {/* Sidebar Navigation */}
      <aside className="w-64 bg-white border-r border-slate-200 flex flex-col fixed inset-y-0 left-0 z-30 shadow-sm">
        <div className="h-16 flex items-center px-6 border-b border-slate-200 gap-2.5">
          <div className="h-8 w-8 rounded-lg bg-blue-600 flex items-center justify-center text-white font-extrabold shadow-md">
            V
          </div>
          <span className="font-extrabold text-slate-800 tracking-tight text-lg">VellumIQ</span>
        </div>

        {/* Workspace org context details */}
        {activeOrganization && (
          <div className="p-4 mx-3 my-4 bg-slate-50 border border-slate-100 rounded-xl space-y-1.5 shadow-sm">
            <div className="flex items-center gap-1.5 text-xs font-bold text-slate-700">
              <Building className="h-4.5 w-4.5 text-slate-400" />
              <span className="truncate">{activeOrganization.name}</span>
            </div>
            <div className="flex items-center gap-1">
              <span className={`text-[10px] font-bold border rounded px-1.5 py-0.5 tracking-wider ${getPlanBadgeColor(activeOrganization.plan_tier)}`}>
                {activeOrganization.plan_tier}
              </span>
            </div>
          </div>
        )}

        <nav className="flex-1 px-4 space-y-1">
          <Link
            href="/"
            className="flex items-center gap-3 px-3 py-2 text-sm font-semibold rounded-lg text-slate-700 hover:bg-slate-50 hover:text-slate-900 transition-colors"
          >
            <LayoutDashboard className="h-4.5 w-4.5 text-slate-500" />
            Dashboard
          </Link>
          
          <Link
            href="/settings"
            className="flex items-center gap-3 px-3 py-2 text-sm font-semibold rounded-lg text-slate-700 hover:bg-slate-50 hover:text-slate-900 transition-colors"
          >
            <Settings2 className="h-4.5 w-4.5 text-slate-500" />
            Developer & Billing
          </Link>
        </nav>

        {/* Footer profile & logout */}
        <div className="p-4 border-t border-slate-200 mt-auto bg-white flex flex-col gap-2">
          <div className="px-2 py-1">
            <p className="text-xs font-bold text-slate-800 truncate">{user.email}</p>
            <p className="text-[10px] text-slate-400 font-medium">Active Member</p>
          </div>
          <button
            onClick={logoutUser}
            className="flex items-center gap-3 w-full px-3 py-2 text-xs font-bold text-rose-600 hover:bg-rose-50 rounded-lg transition"
          >
            <LogOut className="h-4 w-4" />
            Disconnect
          </button>
        </div>
      </aside>

      {/* Main Content Pane */}
      <div className="flex-1 pl-64 flex flex-col min-h-screen">
        <header className="h-16 border-b border-slate-200 bg-white flex items-center justify-between px-8 sticky top-0 z-20 shadow-sm">
          <div className="flex items-center gap-3">
            <h1 className="text-slate-800 font-extrabold text-lg tracking-tight">SaaS Workspace Console</h1>
          </div>
        </header>

        <main className="flex-1 p-8">
          {children}
        </main>
      </div>
    </div>
  );
}
