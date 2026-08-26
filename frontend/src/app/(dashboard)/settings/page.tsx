"use client";

import React, { useEffect, useState, useCallback } from "react";
import { Key, CreditCard, ShieldAlert, Plus, Trash2, Copy, Check, Loader2 } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { billingService } from "@/services/billing";
import { ApiKey } from "@/types";

export default function SettingsPage() {
  const { activeOrganization, updateOrganizationState } = useAuth();
  
  const [apiKeys, setApiKeys] = useState<ApiKey[]>([]);
  const [loadingKeys, setLoadingKeys] = useState(true);
  
  // Key creation state
  const [newKeyName, setNewKeyName] = useState("");
  const [isCreatingKey, setIsCreatingKey] = useState(false);
  const [rawGeneratedKey, setRawGeneratedKey] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  // Billing state
  const [isRedirectingBilling, setIsRedirectingBilling] = useState<string | null>(null);

  const fetchKeys = useCallback(async () => {
    if (!activeOrganization) return;
    setLoadingKeys(true);
    try {
      const keys = await billingService.listKeys(activeOrganization.id);
      setApiKeys(keys);
    } catch (e) {
      console.error("Failed to fetch keys", e);
    } finally {
      setLoadingKeys(false);
    }
  }, [activeOrganization]);

  useEffect(() => {
    fetchKeys();
  }, [fetchKeys]);

  const handleCreateKey = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newKeyName || !activeOrganization) return;
    setIsCreatingKey(true);
    setRawGeneratedKey(null);
    try {
      const response = await billingService.createKey(activeOrganization.id, newKeyName);
      setRawGeneratedKey(response.raw_key);
      setNewKeyName("");
      fetchKeys();
    } catch (e) {
      console.error("Failed to create key", e);
    } finally {
      setIsCreatingKey(false);
    }
  };

  const handleRevokeKey = async (keyId: string) => {
    if (!activeOrganization) return;
    if (!confirm("Are you sure you want to revoke this API Key permanently?")) return;
    try {
      await billingService.revokeKey(keyId, activeOrganization.id);
      fetchKeys();
    } catch (e) {
      console.error("Failed to revoke key", e);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleUpgrade = async (plan: string) => {
    if (!activeOrganization) return;
    setIsRedirectingBilling(plan);
    try {
      const session = await billingService.createCheckoutSession(activeOrganization.id, plan);
      
      if (session.mock) {
        alert(`[Test Mode Upgrade Alert] Simulating Stripe payment completion for organization. Click OK to upgrade subscription to ${plan}!`);
        
        // Trigger the webhook locally using mock session data to simulate immediate Stripe upgrade
        const response = await fetch("/api/v1/billing/webhook", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            type: "checkout.session.completed",
            data: {
              object: {
                customer: `cus_mock_${activeOrganization.id.substring(0,6)}`,
                subscription: `sub_mock_${activeOrganization.id.substring(0,6)}`,
                metadata: {
                  organization_id: activeOrganization.id,
                  plan_tier: plan
                }
              }
            }
          })
        });
        
        if (response.ok) {
          // Update client activeOrganization state
          updateOrganizationState({
            ...activeOrganization,
            plan_tier: plan as any,
            monthly_page_limit: plan === "GROWTH" ? 1000 : 10000
          });
          alert(`Successfully upgraded to ${plan} Plan! Your quota limits have been expanded.`);
        }
      } else {
        // Redirection for live price integrations
        window.location.href = session.checkout_url;
      }
    } catch (e) {
      console.error(e);
      alert("Failed to initiate billing session.");
    } finally {
      setIsRedirectingBilling(null);
    }
  };

  return (
    <div className="space-y-8 max-w-4xl">
      {/* API Keys Configuration */}
      <section className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-6">
        <div className="flex items-center gap-2.5">
          <Key className="h-5 w-5 text-blue-500" />
          <h2 className="text-slate-800 font-bold text-base">Developer API Keys</h2>
        </div>
        
        <p className="text-slate-500 text-xs leading-relaxed max-w-2xl">
          Integrate VellumIQ into your external accounting systems, scanners, or CLI scripts. Authenticate API calls by passing the header <code className="bg-slate-100 px-1 py-0.5 border rounded text-blue-600 font-mono text-[10px]">X-API-Key</code>.
        </p>

        {/* Generate API Key Form */}
        <form onSubmit={handleCreateKey} className="flex gap-3 max-w-md">
          <input
            type="text"
            required
            placeholder="Key name (e.g., Jenkins Ingester)"
            value={newKeyName}
            onChange={(e) => setNewKeyName(e.target.value)}
            disabled={isCreatingKey || !!rawGeneratedKey}
            className="text-xs border border-slate-300 rounded-lg px-3 py-1.5 outline-none focus:ring-2 focus:ring-blue-500/20 flex-1"
          />
          <button
            type="submit"
            disabled={isCreatingKey || !!rawGeneratedKey}
            className="px-4 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold rounded-lg disabled:opacity-50 transition flex items-center gap-1 shrink-0"
          >
            {isCreatingKey ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Plus className="h-3.5 w-3.5" />}
            Generate Key
          </button>
        </form>

        {/* Show Generated Key (Single Visibility) */}
        {rawGeneratedKey && (
          <div className="bg-emerald-50 border border-emerald-100 rounded-xl p-4 space-y-3">
            <div className="flex items-center gap-2 text-emerald-800 font-semibold text-xs">
              <ShieldAlert className="h-5 w-5 text-emerald-600" />
              <span>Copy your new API Key. You will not be able to see it again!</span>
            </div>
            <div className="flex gap-2 max-w-md bg-white border border-emerald-200 rounded-lg p-2.5 items-center justify-between font-mono text-xs">
              <span className="text-slate-700 select-all">{rawGeneratedKey}</span>
              <button
                onClick={() => copyToClipboard(rawGeneratedKey)}
                className="p-1.5 hover:bg-slate-50 text-slate-500 hover:text-slate-700 rounded-md border border-slate-100"
              >
                {copied ? <Check className="h-4 w-4 text-emerald-600" /> : <Copy className="h-4 w-4" />}
              </button>
            </div>
            <button
              onClick={() => setRawGeneratedKey(null)}
              className="text-[10px] font-bold text-emerald-700 hover:underline"
            >
              Done, I have saved it securely
            </button>
          </div>
        )}

        {/* Existing Keys Table */}
        <div className="border border-slate-200 rounded-xl overflow-hidden">
          <table className="w-full text-left border-collapse text-xs text-slate-600">
            <thead className="bg-slate-50 border-b border-slate-200 font-semibold text-slate-700">
              <tr>
                <th className="p-3 pl-4">Key Name</th>
                <th className="p-3">Token Mask</th>
                <th className="p-3">Created</th>
                <th className="p-3 pr-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loadingKeys ? (
                <tr>
                  <td colSpan={4} className="p-6 text-center text-slate-400 font-medium">
                    Loading developer keys...
                  </td>
                </tr>
              ) : apiKeys.length === 0 ? (
                <tr>
                  <td colSpan={4} className="p-6 text-center text-slate-400 font-medium">
                    No active API keys found.
                  </td>
                </tr>
              ) : (
                apiKeys.map((key) => (
                  <tr key={key.id} className="hover:bg-slate-50/50">
                    <td className="p-3 pl-4 font-semibold text-slate-800">{key.name}</td>
                    <td className="p-3 font-mono text-[11px]">{key.masked_key}</td>
                    <td className="p-3 text-slate-400">{new Date(key.created_at).toLocaleDateString()}</td>
                    <td className="p-3 pr-4 text-right">
                      {key.is_active ? (
                        <button
                          onClick={() => handleRevokeKey(key.id)}
                          className="text-[10px] text-rose-600 font-bold hover:bg-rose-50 px-2 py-1 rounded"
                        >
                          Revoke Key
                        </button>
                      ) : (
                        <span className="text-[10px] text-slate-400 font-bold bg-slate-100 px-2 py-0.5 rounded">
                          Revoked
                        </span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>

      {/* Subscription SaaS Billing */}
      {activeOrganization && (
        <section className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-6">
          <div className="flex items-center gap-2.5">
            <CreditCard className="h-5 w-5 text-blue-500" />
            <h2 className="text-slate-800 font-bold text-base">Subscription Plans</h2>
          </div>

          <div className="grid grid-cols-3 gap-4">
            {/* Free Tier */}
            <div className={`border rounded-xl p-5 flex flex-col space-y-3 relative ${
              activeOrganization.plan_tier === "FREE" ? "border-blue-500 bg-blue-50/10 shadow-sm" : "border-slate-200"
            }`}>
              {activeOrganization.plan_tier === "FREE" && (
                <span className="absolute -top-2.5 right-4 bg-blue-600 text-white text-[9px] font-black tracking-widest px-2 py-0.5 border border-blue-600 rounded-full">
                  CURRENT
                </span>
              )}
              <h3 className="text-sm font-bold text-slate-800">Free Starter</h3>
              <p className="text-slate-500 text-xs flex-1 leading-relaxed">
                Perfect for local testing and basic accounting. 100 pages per month.
              </p>
              <div className="text-base font-extrabold text-slate-800">$0 <span className="text-[10px] text-slate-400 font-medium">/ month</span></div>
              <button
                disabled
                className="w-full py-1.5 border border-slate-300 text-slate-400 font-semibold text-xs rounded-lg bg-slate-50"
              >
                {activeOrganization.plan_tier === "FREE" ? "Active Plan" : "N/A"}
              </button>
            </div>

            {/* Growth Tier */}
            <div className={`border rounded-xl p-5 flex flex-col space-y-3 relative ${
              activeOrganization.plan_tier === "GROWTH" ? "border-blue-500 bg-blue-50/10 shadow-sm" : "border-slate-200"
            }`}>
              {activeOrganization.plan_tier === "GROWTH" && (
                <span className="absolute -top-2.5 right-4 bg-blue-600 text-white text-[9px] font-black tracking-widest px-2 py-0.5 border border-blue-600 rounded-full">
                  CURRENT
                </span>
              )}
              <h3 className="text-sm font-bold text-slate-800">Growth Team</h3>
              <p className="text-slate-500 text-xs flex-1 leading-relaxed">
                For medium-sized enterprises. 1,000 pages per month. Programmatic validation checks.
              </p>
              <div className="text-base font-extrabold text-slate-800">$49 <span className="text-[10px] text-slate-400 font-medium">/ month</span></div>
              <button
                onClick={() => handleUpgrade("GROWTH")}
                disabled={activeOrganization.plan_tier === "GROWTH" || isRedirectingBilling !== null}
                className="w-full py-1.5 bg-blue-600 text-white font-semibold text-xs rounded-lg hover:bg-blue-500 transition disabled:opacity-40 disabled:hover:bg-blue-600 flex items-center justify-center gap-1.5"
              >
                {isRedirectingBilling === "GROWTH" && <Loader2 className="h-3 w-3 animate-spin" />}
                {activeOrganization.plan_tier === "GROWTH" ? "Active Plan" : "Upgrade Plan"}
              </button>
            </div>

            {/* Enterprise Tier */}
            <div className={`border rounded-xl p-5 flex flex-col space-y-3 relative ${
              activeOrganization.plan_tier === "ENTERPRISE" ? "border-blue-500 bg-blue-50/10 shadow-sm" : "border-slate-200"
            }`}>
              {activeOrganization.plan_tier === "ENTERPRISE" && (
                <span className="absolute -top-2.5 right-4 bg-blue-600 text-white text-[9px] font-black tracking-widest px-2 py-0.5 border border-blue-600 rounded-full">
                  CURRENT
                </span>
              )}
              <h3 className="text-sm font-bold text-slate-800">Enterprise High-Scale</h3>
              <p className="text-slate-500 text-xs flex-1 leading-relaxed">
                For high-fidelity scale. 10,000 pages per month. High-priority celery execution routing.
              </p>
              <div className="text-base font-extrabold text-slate-800">$199 <span className="text-[10px] text-slate-400 font-medium">/ month</span></div>
              <button
                onClick={() => handleUpgrade("ENTERPRISE")}
                disabled={activeOrganization.plan_tier === "ENTERPRISE" || isRedirectingBilling !== null}
                className="w-full py-1.5 bg-slate-900 text-white font-semibold text-xs rounded-lg hover:bg-slate-800 transition disabled:opacity-40 disabled:hover:bg-slate-900 flex items-center justify-center gap-1.5"
              >
                {isRedirectingBilling === "ENTERPRISE" && <Loader2 className="h-3 w-3 animate-spin" />}
                {activeOrganization.plan_tier === "ENTERPRISE" ? "Active Plan" : "Upgrade Plan"}
              </button>
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
