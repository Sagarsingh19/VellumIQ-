"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { User, Membership, Organization } from "@/types";
import { authService } from "@/services/auth";

interface AuthContextType {
  user: User | null;
  activeMembership: Membership | null;
  activeOrganization: Organization | null;
  loading: boolean;
  loginUser: (email: string, password: string) => Promise<void>;
  logoutUser: () => void;
  updateOrganizationState: (updatedOrg: Organization) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [activeMembership, setActiveMembership] = useState<Membership | null>(null);
  const [activeOrganization, setActiveOrganization] = useState<Organization | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Read session on mount
    const savedUser = localStorage.getItem("user");
    const token = localStorage.getItem("token");
    if (savedUser && token) {
      try {
        const u: User = JSON.parse(savedUser);
        setUser(u);
        // Default to first membership organization
        const savedUserFull = localStorage.getItem("user");
        // For simplicity: fetch organizations from active token / user meta
        // Let's retrieve organization meta saved during login.
        const orgMeta = localStorage.getItem("active_org");
        const memberMeta = localStorage.getItem("active_membership");
        if (orgMeta) {
          const parsedOrg = JSON.parse(orgMeta);
          parsedOrg.plan_tier = "FREE";
          parsedOrg.monthly_page_limit = 100;
          setActiveOrganization(parsedOrg);
        }
        if (memberMeta) setActiveMembership(JSON.parse(memberMeta));
      } catch (e) {
        console.error("Failed to restore session", e);
        authService.logout();
      }
    }
    setLoading(false);
  }, []);

  const loginUser = async (email: string, password: string) => {
    setLoading(true);
    try {
      const response = await authService.login({ email, password });
      setUser(response.user);
      
      if (response.memberships && response.memberships.length > 0) {
        const primaryMember = response.memberships[0];
        const primaryOrg = primaryMember.organization || {
          id: primaryMember.organization_id,
          name: "My Organization",
          plan_tier: "FREE",
          monthly_page_limit: 100,
          subscription_active: true
        };
        
        setActiveMembership(primaryMember);
        setActiveOrganization(primaryOrg);
        
        localStorage.setItem("active_org", JSON.stringify(primaryOrg));
        localStorage.setItem("active_membership", JSON.stringify(primaryMember));
      }
    } finally {
      setLoading(false);
    }
  };

  const logoutUser = () => {
    setUser(null);
    setActiveMembership(null);
    setActiveOrganization(null);
    authService.logout();
  };

  const updateOrganizationState = (updatedOrg: Organization) => {
    setActiveOrganization(updatedOrg);
    localStorage.setItem("active_org", JSON.stringify(updatedOrg));
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        activeMembership,
        activeOrganization,
        loading,
        loginUser,
        logoutUser,
        updateOrganizationState
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
