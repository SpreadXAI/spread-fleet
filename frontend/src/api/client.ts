const API_BASE = '/api'

export type User = {
  id: number
  email: string
  display_name: string
  is_admin: boolean
  active_workspace_id: number | null
  created_at: string
}

export type WorkspacePlan = {
  id: number
  code: string
  name: string
  description: string
  max_accounts: number
  max_members: number
  max_schedules_per_account: number
  price_monthly: number
  enabled: boolean
}

export type Workspace = {
  id: number
  name: string
  owner_user_id: number
  plan: WorkspacePlan | null
  member_count: number
  account_count: number
  created_at: string
}

export type WorkspaceMember = {
  user_id: number
  email: string
  display_name: string
  role: string
  joined_at: string
}

export type WorkspaceInvitation = {
  id: number
  email: string
  status: string
  created_at: string
}

export type AdminOverview = {
  total_users: number
  total_workspaces: number
  total_social_accounts: number
  accounts_available: number
  accounts_assigned: number
  total_plans: number
}

export type AdminWorkspaceDetail = Workspace & {
  members: WorkspaceMember[]
  pending_invites: WorkspaceInvitation[]
  accounts: SocialAccount[]
}

export type SocialAccount = {
  id: number
  platform: string
  handle: string
  display_name: string
  avatar_url: string
  bio: string
  profile_url: string
  tier: 'basic' | 'standard' | 'premium'
  price: number
  followers: number
  status: string
  owner_user_id: number | null
  workspace_id?: number | null
  has_cookie?: boolean
  tactile_agent_id?: number | null
  tactile_last_work_id?: number | null
}

export type DashboardStats = {
  total_accounts_owned: number
  available_market: number
  active_schedules: number
  batch_tasks: number
  recent_logs: number
  workspace_name: string | null
  workspace_members: number
}

export type Schedule = {
  id: number
  account_id: number
  start_time: string
  duration_minutes: number
  enabled: boolean
  created_at: string
}

export type BatchTask = {
  id: number
  name: string
  prompt_text: string
  start_time: string
  duration_minutes: number
  enabled: boolean
  created_at: string
  account_ids: number[]
}

export type ExecutionLog = {
  id: number
  account_id: number
  step: string
  message: string
  screenshot_url: string | null
  status: string
  created_at: string
  account_handle?: string
  tactile_work_id?: number | null
  tactile_session_id?: string | null
}

export type AccountRunResult = {
  log_id: number
  tactile_work_id: number | null
  tactile_session_id: string | null
  status: string
  message: string
}

export type SkillCatalog = {
  platform: SkillCatalogItem[]
  workspace: SkillCatalogItem[]
  mine: SkillCatalogItem[]
  all: SkillCatalogItem[]
}

export type SkillCatalogItem = {
  id: number
  slug: string
  name: string
  description: string
  layer: string
  current_version_id: number | null
  current_version: string | null
  workspace_id: number | null
  readonly?: boolean
}

export type AccountSkillBinding = {
  id: number
  account_id: number
  skill_id: number
  version_id: number
  slug: string
  name: string
  layer: string
  inputs_json: string | null
  outputs_json: string | null
  sort_order: number
  enabled: boolean
  created_at: string
}

function authHeaders(token: string | null): HeadersInit {
  const headers: HeadersInit = { 'Content-Type': 'application/json' }
  if (token) headers.Authorization = `Bearer ${token}`
  return headers
}

async function request<T>(path: string, token: string | null, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { ...authHeaders(token), ...(init?.headers || {}) },
  })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = body.detail || JSON.stringify(body)
    } catch {
      /* ignore */
    }
    throw new Error(typeof detail === 'string' ? detail : 'Request failed')
  }
  if (res.status === 204) return undefined as T
  return res.json()
}

export const api = {
  register: (body: { email: string; password: string }) =>
    request<{ access_token: string; user: User }>('/auth/register', null, {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  login: (body: { email: string; password: string }) =>
    request<{ access_token: string; user: User }>('/auth/login', null, {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  me: (token: string) => request<User>('/auth/me', token),
  updateProfile: (token: string, body: { display_name: string }) =>
    request<User>('/auth/profile', token, { method: 'PUT', body: JSON.stringify(body) }),

  listWorkspaces: (token: string) => request<Workspace[]>('/workspaces', token),
  currentWorkspace: (token: string) => request<Workspace>('/workspaces/current', token),
  switchWorkspace: (token: string, workspaceId: number) =>
    request<Workspace>('/workspaces/switch', token, {
      method: 'POST',
      body: JSON.stringify({ workspace_id: workspaceId }),
    }),
  workspaceMembers: (token: string) => request<WorkspaceMember[]>('/workspaces/current/members', token),
  inviteMember: (token: string, email: string) =>
    request<WorkspaceInvitation>('/workspaces/current/invitations', token, {
      method: 'POST',
      body: JSON.stringify({ email }),
    }),
  pendingInvites: (token: string) =>
    request<WorkspaceInvitation[]>('/workspaces/current/invitations', token),

  dashboard: (token: string) => request<DashboardStats>('/dashboard', token),
  marketAccounts: (token: string, skip = 0, limit = 50) =>
    request<SocialAccount[]>(`/market/accounts?skip=${skip}&limit=${limit}`, token),
  myAccounts: (token: string) => request<SocialAccount[]>('/my/accounts', token),
  purchase: (token: string, accountId: number) =>
    request<SocialAccount>(`/my/accounts/${accountId}/purchase`, token, { method: 'POST' }),
  getPrompt: (token: string, accountId: number) =>
    request<{ persona: string; prompt_text: string } | null>(`/my/accounts/${accountId}/prompt`, token),
  savePrompt: (token: string, accountId: number, body: { persona: string; prompt_text: string }) =>
    request(`/my/accounts/${accountId}/prompt`, token, { method: 'PUT', body: JSON.stringify(body) }),
  saveCookie: (token: string, accountId: number, session_cookie: string) =>
    request<SocialAccount>(`/my/accounts/${accountId}/cookie`, token, {
      method: 'PUT',
      body: JSON.stringify({ session_cookie }),
    }),
  runAccount: (token: string, accountId: number) =>
    request<AccountRunResult>(`/my/accounts/${accountId}/run`, token, { method: 'POST' }),
  skillCatalog: (token: string) => request<SkillCatalog>('/skills/catalog', token),
  accountSkills: (token: string, accountId: number) =>
    request<AccountSkillBinding[]>(`/skills/my/accounts/${accountId}/bindings`, token),
  batchInstallSkill: (
    token: string,
    body: {
      skill_id: number
      version_id: number
      account_ids: number[]
      slug?: string
      name?: string
      inputs_json?: string
      outputs_json?: string
    },
  ) =>
    request<{ skill_id: number; version_id: number; account_ids: number[]; installed_count: number }>(
      '/skills/batch-install',
      token,
      { method: 'POST', body: JSON.stringify(body) },
    ),
  createSkillSession: (
    token: string,
    body: { account_id: number; prompt: string; title?: string },
  ) =>
    request<{
      tactile_work_id: number | null
      tactile_session_id: string | null
      tactile_agent_id: number | null
      account_id: number
      account_handle: string
      message: string
    }>('/skills/create-session', token, { method: 'POST', body: JSON.stringify(body) }),
  listSchedules: (token: string, accountId: number) =>
    request<Schedule[]>(`/my/accounts/${accountId}/schedules`, token),
  createSchedule: (
    token: string,
    accountId: number,
    body: { start_time: string; duration_minutes: number; enabled: boolean },
  ) =>
    request<Schedule>(`/my/accounts/${accountId}/schedules`, token, {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  deleteSchedule: (token: string, accountId: number, scheduleId: number) =>
    request(`/my/accounts/${accountId}/schedules/${scheduleId}`, token, { method: 'DELETE' }),
  batchTasks: (token: string) => request<BatchTask[]>('/batch-tasks', token),
  createBatchTask: (
    token: string,
    body: {
      name: string
      prompt_text: string
      start_time: string
      duration_minutes: number
      account_ids: number[]
      enabled: boolean
    },
  ) =>
    request<BatchTask>('/batch-tasks', token, { method: 'POST', body: JSON.stringify(body) }),
  executionLogs: (token: string) => request<ExecutionLog[]>('/execution-logs', token),

  adminOverview: (token: string) => request<AdminOverview>('/admin/overview', token),
  adminWorkspaces: (token: string) => request<Workspace[]>('/admin/workspaces', token),
  adminWorkspaceDetail: (token: string, id: number) =>
    request<AdminWorkspaceDetail>(`/admin/workspaces/${id}`, token),
  adminPlans: (token: string) => request<WorkspacePlan[]>('/admin/plans', token),
  adminUpdatePlan: (token: string, id: number, body: Partial<WorkspacePlan>) =>
    request<WorkspacePlan>(`/admin/plans/${id}`, token, { method: 'PUT', body: JSON.stringify(body) }),
  adminAssignPlan: (token: string, workspaceId: number, planId: number) =>
    request<Workspace>(`/admin/workspaces/${workspaceId}/plan/${planId}`, token, { method: 'PUT' }),
}
