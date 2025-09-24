import { getRequest, postRequest } from "./api";
import useSetting from "@/composables/setting";

const setting = useSetting();

// Centralize the new backend prefix once
const BASE = "/api/responses";


export interface CreditSummary {
  total_available: number;
  total_granted: number;
  total_used: number;
}

export interface CreditSummary {
  total_available: number;
  total_granted: number;
  total_used: number;
}

export const creditSummary = async (): Promise<CreditSummary> => {
  return await getRequest({
    url: `${BASE}/credit_summary`,
  });
};