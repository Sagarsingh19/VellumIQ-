import api from "./api";
import { ApiKey, ApiKeyCreated } from "@/types";

export const billingService = {
  async listKeys(orgId: string): Promise<ApiKey[]> {
    const response = await api.get(`/api-keys?organization_id=${orgId}`);
    return response.data;
  },

  async createKey(orgId: string, name: string): Promise<ApiKeyCreated> {
    const response = await api.post(`/api-keys?organization_id=${orgId}`, { name });
    return response.data;
  },

  async revokeKey(keyId: string, orgId: string): Promise<void> {
    await api.delete(`/api-keys/${keyId}?organization_id=${orgId}`);
  },

  async createCheckoutSession(orgId: string, planTier: string): Promise<{ checkout_url: string; session_id: string; mock: boolean }> {
    const response = await api.post(`/billing/checkout?organization_id=${orgId}&plan_tier=${planTier}`);
    return response.data;
  }
};
