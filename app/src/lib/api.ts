import { getSession } from "./session";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined) || "http://localhost:8000/api/v1";

export interface ApiUser {
  id: string;
  email: string;
  name: string;
  role: "owner" | "worker";
  company_id: string | null;
}

export interface AdminUser extends ApiUser {
  created_at: string;
  owned_company_id: string | null;
  receipt_count: number;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: ApiUser;
}

export interface Company {
  id: string;
  name: string;
  owner_id: string;
  created_at: string;
}

export interface ReceiptItem {
  id: string;
  name: string;
  quantity: number | null;
  price: number | null;
  category: string | null;
  is_strikethrough: boolean;
  is_replacement: boolean;
  replacement_vendor: string | null;
  sort_order: number;
}

export interface RuleCheckResult {
  id: string;
  rule_id: string | null;
  rule_text: string;
  passed: boolean;
  explanation: string | null;
}

export interface Receipt {
  id: string;
  company_id: string;
  worker_id: string;
  vendor: string | null;
  total_amount: number | null;
  receipt_type: string;
  status: string;
  receipt_image_url: string | null;
  ai_verdict: string | null;
  ai_reason: string | null;
  rejection_reason: string | null;
  is_duplicate: boolean;
  duplicate_of_id: string | null;
  receipt_date: string | null;
  created_at: string;
  updated_at: string;
  items: ReceiptItem[];
  rule_check_results: RuleCheckResult[];
}

export interface ReceiptProcessResult {
  receipt: Receipt;
  duplicate_warning: string | null;
}

export interface AnalyticsSummary {
  total_spend: number;
  pending_count: number;
  ai_approval_rate: number;
}

export interface AnalyticsQueryResponse {
  answer: string;
  chart_type: string | null;
  chart_title: string | null;
  chart_data: Array<{ label: string; value: number }> | null;
}

export interface ApprovalRule {
  id: string;
  name: string;
  prompt: string;
  applies_to_preapproved: boolean;
  is_active: boolean;
}

export interface PreApprovedItem {
  id: string;
  item_name: string;
  amount_limit: number | null;
  note: string | null;
  custom_variables?: Record<string, string> | null;
  is_active: boolean;
}

export interface ProposalAlternativeItem {
  vendor: string;
  price: number;
  rating: number | null;
  review_summary: string | null;
  product_url: string;
  source: "online" | "company_history";
}

export interface ProposalAlternativeList {
  receipt_item_id: string;
  item_name: string;
  alternatives: ProposalAlternativeItem[];
}

async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers || {});
  const hasBody = init.body !== undefined && !(init.body instanceof FormData);
  if (hasBody) {
    headers.set("Content-Type", "application/json");
  }

  const session = getSession();
  if (session?.accessToken) {
    headers.set("Authorization", `Bearer ${session.accessToken}`);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
  });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const payload = (await response.json()) as { detail?: string };
      if (payload.detail) {
        detail = payload.detail;
      }
    } catch {
      // No JSON payload available.
    }
    throw new Error(detail || `Request failed with status ${response.status}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export function devLogin(payload: {
  email: string;
  role: "owner" | "worker";
  name: string;
  company_id?: string | null;
}): Promise<TokenResponse> {
  return apiFetch<TokenResponse>("/auth/dev-login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function listCompanies(): Promise<Company[]> {
  return apiFetch<Company[]>("/companies/");
}

export function createCompany(name: string): Promise<Company> {
  return apiFetch<Company>("/companies/", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export function listReceipts(filters?: { receipt_type?: string; status?: string }): Promise<Receipt[]> {
  const params = new URLSearchParams();
  if (filters?.receipt_type) {
    params.set("receipt_type", filters.receipt_type);
  }
  if (filters?.status) {
    params.set("status", filters.status);
  }
  const suffix = params.toString() ? `?${params.toString()}` : "";
  return apiFetch<Receipt[]>(`/receipts/${suffix}`);
}

export function uploadReceipt(file: File, receiptType: "proposal" | "paid_expense"): Promise<ReceiptProcessResult> {
  const body = new FormData();
  body.append("file", file);
  body.append("receipt_type", receiptType);
  return apiFetch<ReceiptProcessResult>("/receipts/upload", {
    method: "POST",
    body,
  });
}

export async function fetchReceiptImageBlobUrl(receiptId: string): Promise<{ url: string; contentType: string }> {
  const session = getSession();
  const headers = new Headers();
  if (session?.accessToken) {
    headers.set("Authorization", `Bearer ${session.accessToken}`);
  }

  const response = await fetch(`${API_BASE_URL}/receipts/${receiptId}/image`, {
    method: "GET",
    headers,
  });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const payload = (await response.json()) as { detail?: string };
      if (payload.detail) {
        detail = payload.detail;
      }
    } catch {
      // No JSON payload available.
    }
    throw new Error(detail || `Request failed with status ${response.status}`);
  }

  const blob = await response.blob();
  return {
    url: URL.createObjectURL(blob),
    contentType: blob.type || response.headers.get("content-type") || "application/octet-stream",
  };
}

export function listApprovals(queue?: string, receiptType?: string): Promise<Receipt[]> {
  const params = new URLSearchParams();
  if (queue) {
    params.set("queue", queue);
  }
  if (receiptType) {
    params.set("receipt_type", receiptType);
  }
  const suffix = params.toString() ? `?${params.toString()}` : "";
  return apiFetch<Receipt[]>(`/approvals/${suffix}`);
}

export function decideApproval(receiptId: string, decision: "approved" | "rejected", reason?: string): Promise<Receipt> {
  return apiFetch<Receipt>(`/approvals/${receiptId}/decide`, {
    method: "POST",
    body: JSON.stringify({ decision, reason: reason || null }),
  });
}

export function getItemAlternatives(receiptId: string, itemId: string, searchName?: string): Promise<ProposalAlternativeList> {
  const params = new URLSearchParams();
  if (searchName) {
    params.set("search_name", searchName);
  }
  const suffix = params.toString() ? `?${params.toString()}` : "";
  return apiFetch<ProposalAlternativeList>(`/receipts/${receiptId}/items/${itemId}/alternatives${suffix}`, {
    method: "POST",
  });
}

export function applyProposalReplacement(receiptId: string, itemId: string, vendor: string, newPrice: number): Promise<Receipt> {
  const params = new URLSearchParams();
  params.set("vendor", vendor);
  params.set("new_price", String(newPrice));
  return apiFetch<Receipt>(`/receipts/${receiptId}/items/${itemId}/apply-replacement?${params.toString()}`, {
    method: "POST",
  });
}

export function getAnalyticsSummary(): Promise<AnalyticsSummary> {
  return apiFetch<AnalyticsSummary>("/analytics/summary");
}

export function queryAnalytics(question: string): Promise<AnalyticsQueryResponse> {
  return apiFetch<AnalyticsQueryResponse>("/analytics/query", {
    method: "POST",
    body: JSON.stringify({ question }),
  });
}

export function listRules(): Promise<ApprovalRule[]> {
  return apiFetch<ApprovalRule[]>("/settings/rules");
}

export function createRule(payload: { name: string; prompt: string; applies_to_preapproved?: boolean; is_active?: boolean }): Promise<ApprovalRule> {
  return apiFetch<ApprovalRule>("/settings/rules", {
    method: "POST",
    body: JSON.stringify({
      name: payload.name,
      prompt: payload.prompt,
      applies_to_preapproved: payload.applies_to_preapproved ?? true,
      is_active: payload.is_active ?? true,
    }),
  });
}

export function updateRule(ruleId: string, payload: Partial<{ name: string; prompt: string; applies_to_preapproved: boolean; is_active: boolean }>): Promise<ApprovalRule> {
  return apiFetch<ApprovalRule>(`/settings/rules/${ruleId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function deleteRule(ruleId: string): Promise<void> {
  return apiFetch<void>(`/settings/rules/${ruleId}`, { method: "DELETE" });
}

export function listPreApprovedItems(): Promise<PreApprovedItem[]> {
  return apiFetch<PreApprovedItem[]>("/settings/pre-approved");
}

export function createPreApprovedItem(payload: {
  item_name: string;
  amount_limit?: number | null;
  note?: string | null;
  custom_variables?: Record<string, string> | null;
  is_active?: boolean;
}): Promise<PreApprovedItem> {
  return apiFetch<PreApprovedItem>("/settings/pre-approved", {
    method: "POST",
    body: JSON.stringify({
      item_name: payload.item_name,
      amount_limit: payload.amount_limit ?? null,
      note: payload.note ?? null,
      custom_variables: payload.custom_variables ?? null,
      is_active: payload.is_active ?? true,
    }),
  });
}

export function updatePreApprovedItem(
  itemId: string,
  payload: Partial<{
    item_name: string;
    amount_limit: number | null;
    note: string | null;
    custom_variables: Record<string, string> | null;
    is_active: boolean;
  }>,
): Promise<PreApprovedItem> {
  return apiFetch<PreApprovedItem>(`/settings/pre-approved/${itemId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function deletePreApprovedItem(itemId: string): Promise<void> {
  return apiFetch<void>(`/settings/pre-approved/${itemId}`, { method: "DELETE" });
}

export function listWorkers(): Promise<ApiUser[]> {
  return apiFetch<ApiUser[]>("/workers/");
}

export function inviteWorker(payload: { email: string; name: string }): Promise<ApiUser> {
  return apiFetch<ApiUser>("/workers/invite", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function removeWorker(workerId: string): Promise<void> {
  return apiFetch<void>(`/workers/${workerId}`, { method: "DELETE" });
}

export function listAdminUsers(adminUsername: string, adminPassword: string): Promise<AdminUser[]> {
  return apiFetch<AdminUser[]>("/auth/dev-admin/users", {
    headers: {
      "X-Admin-Username": adminUsername,
      "X-Admin-Password": adminPassword,
    },
  });
}

export function deleteAdminUser(userId: string, adminUsername: string, adminPassword: string): Promise<void> {
  return apiFetch<void>(`/auth/dev-admin/users/${userId}`, {
    method: "DELETE",
    headers: {
      "X-Admin-Username": adminUsername,
      "X-Admin-Password": adminPassword,
    },
  });
}
