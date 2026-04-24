import { useAuthStore } from '@/store/useAuthStore';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/v1';

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export async function fetchApi<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers || {});
  headers.set('Content-Type', 'application/json');

  // Always attach the JWT from the Zustand store (persisted in localStorage)
  // EXCEPT for auth endpoints which should be public
  const isAuthEndpoint = endpoint.startsWith('/auth/');
  const token = useAuthStore.getState().token;
  if (token && !isAuthEndpoint) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    // On 401: clear stale auth and redirect to login
    if (response.status === 401 && !isAuthEndpoint) {
      useAuthStore.getState().logout();
      if (typeof window !== 'undefined') {
        window.location.href = '/login';
      }
    }

    let errorData;
    try {
      errorData = await response.json();
    } catch (e) {
      errorData = { message: `API error: ${response.status}` };
    }
    const error = new Error(errorData.message || errorData.detail || `API error: ${response.status}`);
    (error as any).data = errorData;
    (error as any).status = response.status;
    throw error;
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

// Auth API
export async function registerUser(data: any): Promise<{ message: string }> {
  return fetchApi<{ message: string }>('/auth/register/', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function loginUser(data: any): Promise<{ access: string; refresh: string }> {
  return fetchApi<{ access: string; refresh: string }>('/auth/login/', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function getMe(): Promise<any> {
  return fetchApi<any>('/users/me/');
}

// Scans & Targets API
export async function listTargets(workspaceId?: string): Promise<any[]> {
  const url = workspaceId && workspaceId !== 'undefined' ? `/scans/targets/?workspace_id=${workspaceId}` : '/scans/targets/';
  return fetchApi<any[]>(url);
}

export async function createTarget(data: any): Promise<any> {
  return fetchApi<any>('/scans/targets/', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function startScan(
  targetUrl: string, 
  scanType: string = 'quick', 
  workspaceId?: string, 
  pluginIds: string[] = []
): Promise<{ scan_id: string; status: string; target_host: string }> {
  return fetchApi<{ scan_id: string; status: string; target_host: string }>('/scans/quick/', {
    method: 'POST',
    body: JSON.stringify({ 
      target_url: targetUrl, 
      scan_type: scanType,
      workspace_id: workspaceId,
      plugin_ids: pluginIds
    }),
  });
}

export async function listPlugins(): Promise<any[]> {
  return fetchApi<any[]>('/scans/plugins/');
}

// Scheduling API
export async function listSchedules(workspaceId?: string): Promise<any[]> {
  const url = workspaceId && workspaceId !== 'undefined' ? `/scans/schedules/?workspace_id=${workspaceId}` : '/scans/schedules/';
  return fetchApi<any[]>(url);
}

export async function createSchedule(data: any): Promise<any> {
  return fetchApi<any>('/scans/schedules/', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateSchedule(id: string, data: any): Promise<any> {
  return fetchApi<any>(`/scans/schedules/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

export async function deleteSchedule(id: string): Promise<void> {
  return fetchApi<void>(`/scans/schedules/${id}/`, {
    method: 'DELETE',
  });
}

export async function getScan(id: string): Promise<any> {
  return fetchApi<any>(`/scans/${id}/`);
}

export async function getFindings(scanId: string): Promise<any[] | PaginatedResponse<any>> {
  return fetchApi<any[] | PaginatedResponse<any>>(`/scans/${scanId}/findings/`);
}

export async function generateReport(scanId: string, format: string = 'PDF', reportType: string = 'TECHNICAL'): Promise<any> {
  return fetchApi<any>(`/reports/scans/${scanId}/report/`, {
    method: 'POST',
    body: JSON.stringify({
      format: format,
      type: reportType,
    }),
  });
}

export async function listReports(): Promise<any[] | PaginatedResponse<any>> {
  return fetchApi<any[] | PaginatedResponse<any>>('/reports/');
}

export async function getReport(id: string): Promise<any> {
  return fetchApi<any>(`/reports/${id}/`);
}

export async function deleteReport(id: string): Promise<void> {
  return fetchApi<void>(`/reports/${id}/`, {
    method: 'DELETE',
  });
}

// Notifications API
export async function getNotifications(): Promise<any[] | PaginatedResponse<any>> {
  return fetchApi<any[] | PaginatedResponse<any>>('/notifications/');
}

export async function markNotificationAsRead(id: string): Promise<void> {
  return fetchApi<void>(`/notifications/${id}/mark_as_read/`, {
    method: 'POST',
  });
}

export async function markAllNotificationsAsRead(): Promise<void> {
  return fetchApi<void>('/notifications/mark_all_as_read/', {
    method: 'POST',
  });
}

// Dashboard & Scan List
export interface DashboardStats {
  active_scans: number;
  total_scans: number;
  total_findings: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  info_count: number;
  recent_scans: any[];
}

export async function getDashboardStats(): Promise<DashboardStats> {
  return fetchApi<DashboardStats>('/scans/dashboard/');
}

export async function listScans(): Promise<any[] | PaginatedResponse<any>> {
  return fetchApi<any[] | PaginatedResponse<any>>('/scans/');
}

// Billing API
export interface Plan {
  id: string;
  name: string;
  description: string;
  price_monthly: string;
  price_yearly: string;
  stripe_price_id_monthly: string;
  stripe_price_id_yearly: string;
  features: any;
  is_active: boolean;
}

export async function getPlans(): Promise<Plan[]> {
  return fetchApi<Plan[]>('/billing/plans/');
}

export async function getSubscription(): Promise<any> {
  return fetchApi<any>('/billing/subscription/');
}

export async function createCheckoutSession(data: {
  plan_id: string;
  billing_cycle: 'MONTHLY' | 'YEARLY';
  success_url: string;
  cancel_url: string;
}): Promise<{ checkout_url: string }> {
  return fetchApi<{ checkout_url: string }>('/billing/subscription/', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function getUsage(): Promise<any> {
  return fetchApi<any>('/billing/usage/');
}

export async function createPortalSession(returnUrl: string): Promise<{ portal_url: string }> {
  return fetchApi<{ portal_url: string }>('/billing/portal/', {
    method: 'POST',
    body: JSON.stringify({ return_url: returnUrl }),
  });
}

// API Keys API
export async function listApiKeys(): Promise<any[] | PaginatedResponse<any>> {
  return fetchApi<any[] | PaginatedResponse<any>>('/users/me/api-keys/');
}

export async function createApiKey(name: string): Promise<any> {
  return fetchApi<any>('/users/me/api-keys/', {
    method: 'POST',
    body: JSON.stringify({ name }),
  });
}

export async function revokeApiKey(id: string): Promise<void> {
  return fetchApi<void>(`/users/me/api-keys/${id}/`, {
    method: 'DELETE',
  });
}

// Preferences API
export async function getNotificationPreferences(): Promise<any[] | PaginatedResponse<any>> {
  return fetchApi<any[] | PaginatedResponse<any>>('/notifications/preferences/');
}

export async function updateNotificationPreference(id: string, data: any): Promise<any> {
  return fetchApi<any>(`/notifications/preferences/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

// AI Analysis API
export async function explainFindingAI(findingId: string): Promise<{ explanation: string }> {
  return fetchApi<{ explanation: string }>(`/ai/findings/${findingId}/explain/`, {
    method: 'POST',
  });
}

export async function remediateFindingAI(findingId: string): Promise<{ remediation: string }> {
  return fetchApi<{ remediation: string }>(`/ai/findings/${findingId}/remediate/`, {
    method: 'POST',
  });
}

export async function getScanAIPrediction(scanId: string): Promise<{ prediction: string }> {
  return fetchApi<{ prediction: string }>(`/ai/scans/${scanId}/prediction/`, {
    method: 'POST',
  });
}

// Integrations (Webhooks) API
export async function listWebhooks(): Promise<any[]> {
  return fetchApi<any[]>('/integrations/webhooks/');
}

export async function createWebhook(data: any): Promise<any> {
  return fetchApi<any>('/integrations/webhooks/', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateWebhook(id: string, data: any): Promise<any> {
  return fetchApi<any>(`/integrations/webhooks/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

export async function deleteWebhook(id: string): Promise<void> {
  return fetchApi<void>(`/integrations/webhooks/${id}/`, {
    method: 'DELETE',
  });
}

export async function resetWebhookSecret(id: string): Promise<{ secret_token: string }> {
  return fetchApi<{ secret_token: string }>(`/integrations/webhooks/${id}/reset_secret/`, {
    method: 'POST',
  });
}

export async function testWebhook(id: string): Promise<{ message: string }> {
  return fetchApi<{ message: string }>(`/integrations/webhooks/${id}/test/`, {
    method: 'POST',
  });
}

// Bounty API
export async function getPublicBountyPrograms(): Promise<any[] | PaginatedResponse<any>> {
  return fetchApi<any[] | PaginatedResponse<any>>('/bounty/programs/');
}

export async function getBountyProgram(id: string): Promise<any> {
  return fetchApi<any>(`/bounty/programs/${id}/`);
}

export async function submitFinding(data: any): Promise<any> {
  return fetchApi<any>('/bounty/submissions/', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function getResearcherSubmissions(): Promise<any[] | PaginatedResponse<any>> {
  return fetchApi<any[] | PaginatedResponse<any>>('/bounty/submissions/');
}

export async function verifySubmissionProof(id: string): Promise<any> {
  return fetchApi<any>(`/bounty/submissions/${id}/verify_proof/`, {
    method: 'POST',
  });
}

export async function getWorkspaceBountyPrograms(workspaceId: string): Promise<any[] | PaginatedResponse<any>> {
  const url = workspaceId && workspaceId !== 'undefined' ? `/bounty/workspace-management/?workspace_id=${workspaceId}` : '/bounty/workspace-management/';
  return fetchApi<any[] | PaginatedResponse<any>>(url);
}

export async function getWorkspaceSubmissions(workspaceId: string): Promise<any[] | PaginatedResponse<any>> {
  const url = workspaceId && workspaceId !== 'undefined' ? `/bounty/workspace-submissions/?workspace_id=${workspaceId}` : '/bounty/workspace-submissions/';
  return fetchApi<any[] | PaginatedResponse<any>>(url);
}

export async function triageSubmission(id: string, data: { severity?: string, payout_amount?: number, internal_notes?: string }): Promise<any> {
  return fetchApi<any>(`/bounty/workspace-submissions/${id}/triage/`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function resolveSubmission(id: string): Promise<any> {
  return fetchApi<any>(`/bounty/workspace-submissions/${id}/resolve/`, {
    method: 'POST',
  });
}

export async function createBountyProgram(data: any): Promise<any> {
  return fetchApi<any>('/bounty/workspace-management/', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}
// Marketplace API
export async function listMarketplaceModules(workspaceId?: string): Promise<any[] | PaginatedResponse<any>> {
  const url = workspaceId && workspaceId !== 'undefined' ? `/marketplace/modules/?workspace_id=${workspaceId}` : '/marketplace/modules/';
  return fetchApi<any[] | PaginatedResponse<any>>(url);
}

export async function createModuleCheckout(slug: string, workspaceId: string, data: any): Promise<{ checkout_url: string }> {
  const cleanWorkspaceId = workspaceId === 'undefined' ? undefined : workspaceId;
  return fetchApi<{ checkout_url: string }>(`/marketplace/modules/${slug}/checkout/`, {
    method: 'POST',
    body: JSON.stringify({ ...data, workspace_id: cleanWorkspaceId }),
  });
}

// AI Credit System API
export async function getAIWallet(workspaceId: string): Promise<any> {
  const url = workspaceId && workspaceId !== 'undefined' ? `/ai/wallet/?workspace_id=${workspaceId}` : '/ai/wallet/';
  return fetchApi<any>(url);
}

export async function listAIPackages(): Promise<any[]> {
  return fetchApi<any[]>('/ai/packages/');
}

export async function createAICheckoutSession(packageId: string, workspaceId: string): Promise<{ checkout_url: string }> {
  return fetchApi<{ checkout_url: string }>('/ai/checkout/', {
    method: 'POST',
    body: JSON.stringify({ package_id: packageId, workspace_id: workspaceId }),
  });
}

export async function listAITransactions(workspaceId: string): Promise<any[] | PaginatedResponse<any>> {
  const url = workspaceId && workspaceId !== 'undefined' ? `/ai/transactions/?workspace_id=${workspaceId}` : '/ai/transactions/';
  return fetchApi<any[] | PaginatedResponse<any>>(url);
}

export async function listAIAchievements(workspaceId: string): Promise<any[]> {
  const url = workspaceId && workspaceId !== 'undefined' ? `/ai/achievements/?workspace_id=${workspaceId}` : '/ai/achievements/';
  return fetchApi<any[]>(url);
}

export async function getAIExplanation(findingId: string, express: boolean = false): Promise<{ explanation: string }> {
  return fetchApi<{ explanation: string }>(`/ai/explanation/${findingId}/`, {
    method: 'POST',
    body: JSON.stringify({ express }),
  });
}

export async function getAIRemediation(findingId: string, express: boolean = false): Promise<{ remediation: string }> {
  return fetchApi<{ remediation: string }>(`/ai/remediation/${findingId}/`, {
    method: 'POST',
    body: JSON.stringify({ express }),
  });
}

export async function getAIScanPrediction(scanId: string, express: boolean = false): Promise<{ prediction: string }> {
  return fetchApi<{ prediction: string }>(`/ai/predict/${scanId}/`, {
    method: 'POST',
    body: JSON.stringify({ express }),
  });
}
