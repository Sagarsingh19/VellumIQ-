"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { KeyRound, Mail, Building2, CheckCircle2, AlertTriangle, Loader2 } from "lucide-react";
import { authService } from "@/services/auth";

export default function SignupPage() {
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [orgName, setOrgName] = useState("");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await authService.signup({
        email,
        password,
        organization_name: orgName,
      });
      setSuccess(true);
      setTimeout(() => {
        router.push("/login");
      }, 2000);
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || "Registration failed. Try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 p-4">
      <div className="w-full max-w-md bg-white border border-slate-200 rounded-2xl shadow-xl p-8 space-y-6">
        <div className="text-center space-y-1.5">
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">VellumIQ</h1>
          <p className="text-sm text-slate-500 font-medium">Create and register a new workspace</p>
        </div>

        {success ? (
          <div className="bg-emerald-50 border border-emerald-100 rounded-xl p-6 flex flex-col items-center gap-3 text-center text-emerald-800 text-sm font-medium">
            <CheckCircle2 className="h-10 w-10 text-emerald-600" />
            <span className="font-bold text-base">Registration Complete!</span>
            <span>Organization created. Redirecting to login...</span>
          </div>
        ) : (
          <>
            {error && (
              <div className="bg-rose-50 border border-rose-100 rounded-xl p-4 flex gap-3 text-rose-800 text-sm font-medium">
                <AlertTriangle className="h-5 w-5 text-rose-600 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-bold text-slate-700 uppercase tracking-wider">Email Address</label>
                <div className="relative">
                  <Mail className="absolute left-3 top-2.5 h-4.5 w-4.5 text-slate-400" />
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full text-sm border border-slate-300 rounded-xl pl-10 pr-4 py-2 outline-none focus:ring-2 focus:ring-blue-500/20"
                    placeholder="name@domain.com"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-bold text-slate-700 uppercase tracking-wider">Organization Name</label>
                <div className="relative">
                  <Building2 className="absolute left-3 top-2.5 h-4.5 w-4.5 text-slate-400" />
                  <input
                    type="text"
                    required
                    value={orgName}
                    onChange={(e) => setOrgName(e.target.value)}
                    className="w-full text-sm border border-slate-300 rounded-xl pl-10 pr-4 py-2 outline-none focus:ring-2 focus:ring-blue-500/20"
                    placeholder="Acme Corp"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-bold text-slate-700 uppercase tracking-wider">Password</label>
                <div className="relative">
                  <KeyRound className="absolute left-3 top-2.5 h-4.5 w-4.5 text-slate-400" />
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full text-sm border border-slate-300 rounded-xl pl-10 pr-4 py-2 outline-none focus:ring-2 focus:ring-blue-500/20"
                    placeholder="••••••••"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-2.5 bg-slate-900 hover:bg-slate-800 text-white font-semibold rounded-xl transition disabled:opacity-50 flex items-center justify-center gap-2 text-sm shadow-md"
              >
                {loading ? (
                  <>
                    <Loader2 className="h-4.5 w-4.5 animate-spin" />
                    Creating account...
                  </>
                ) : (
                  "Create Workspace"
                )}
              </button>
            </form>

            <div className="text-center text-xs text-slate-500 font-medium">
              Already registered?{" "}
              <Link href="/login" className="text-blue-600 font-bold hover:underline">
                Sign In
              </Link>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
