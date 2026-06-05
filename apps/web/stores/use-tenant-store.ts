"use client";

import { create } from "zustand";

type TenantStore = {
  tenantId: string;
  companyId: string;
  setTenantId: (value: string) => void;
  setCompanyId: (value: string) => void;
};

export const useTenantStore = create<TenantStore>((set) => ({
  tenantId: "",
  companyId: "",
  setTenantId: (tenantId) => set({ tenantId }),
  setCompanyId: (companyId) => set({ companyId }),
}));
