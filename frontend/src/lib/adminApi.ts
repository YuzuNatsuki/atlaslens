import { authedFetch } from "@/lib/auth";

export const adminApi = {
  getOrg: () => authedFetch<OrgResponse>("/api/admin/org"),

  createDivision: (p: DivisionPayload) =>
    authedFetch<{ division: Division }>("/api/admin/divisions", {
      method: "POST",
      body: JSON.stringify(p),
    }),
  updateDivision: (id: string, p: DivisionPayload) =>
    authedFetch<{ division: Division }>(`/api/admin/divisions/${id}`, {
      method: "PUT",
      body: JSON.stringify(p),
    }),
  deleteDivision: (id: string) =>
    authedFetch<{ deleted: string }>(`/api/admin/divisions/${id}`, { method: "DELETE" }),

  createDepartment: (p: DepartmentPayload) =>
    authedFetch<{ department: Department }>("/api/admin/departments", {
      method: "POST",
      body: JSON.stringify(p),
    }),
  updateDepartment: (id: string, p: DepartmentPayload) =>
    authedFetch<{ department: Department }>(`/api/admin/departments/${id}`, {
      method: "PUT",
      body: JSON.stringify(p),
    }),
  deleteDepartment: (id: string) =>
    authedFetch<{ deleted: string }>(`/api/admin/departments/${id}`, { method: "DELETE" }),

  createTeam: (p: TeamPayload) =>
    authedFetch<{ team: Team }>("/api/admin/teams", {
      method: "POST",
      body: JSON.stringify(p),
    }),
  updateTeam: (id: string, p: TeamPayload) =>
    authedFetch<{ team: Team }>(`/api/admin/teams/${id}`, {
      method: "PUT",
      body: JSON.stringify(p),
    }),
  deleteTeam: (id: string) =>
    authedFetch<{ deleted: string; detached_members: string[] }>(
      `/api/admin/teams/${id}`,
      { method: "DELETE" },
    ),

  listMembers: () => authedFetch<{ members: AdminMember[] }>("/api/admin/members"),
  createMember: (p: MemberPayload) =>
    authedFetch<{ member: AdminMember; initial_password: string | null }>(
      "/api/admin/members",
      { method: "POST", body: JSON.stringify(p) },
    ),
  updateMember: (id: string, p: MemberPayload) =>
    authedFetch<{ member: AdminMember }>(`/api/admin/members/${id}`, {
      method: "PUT",
      body: JSON.stringify(p),
    }),
  deleteMember: (id: string) =>
    authedFetch<{ deleted: string }>(`/api/admin/members/${id}`, { method: "DELETE" }),
  resetPassword: (id: string) =>
    authedFetch<{ member_id: string; new_password: string }>(
      `/api/admin/members/${id}/reset-password`,
      { method: "POST" },
    ),
};

export interface OrgResponse {
  companies: Company[];
  members: AdminMember[];
}

export interface Company {
  id: string;
  name: string;
  divisions: Division[];
}

export interface Division {
  id: string;
  company_id: string;
  name: string;
  head_member_id: string | null;
  departments?: Department[];
}

export interface Department {
  id: string;
  division_id: string;
  name: string;
  head_member_id: string | null;
  teams?: Team[];
}

export interface Team {
  id: string;
  department_id: string;
  name: string;
  manager_member_id: string | null;
  member_ids: string[];
}

export interface AdminMember {
  id: string;
  name: string;
  role: string;
  title: string;
  joined_at: string;
  team_id: string | null;
  manages_team_id: string | null;
  is_admin: boolean;
  skills: string[];
  interests: string[];
  bio: string;
  email: string | null;
  password_hash?: string | null;
  manager_id?: string | null;
}

export interface DivisionPayload {
  id?: string;
  company_id?: string;
  name: string;
  head_member_id: string | null;
}
export interface DepartmentPayload {
  id?: string;
  division_id: string;
  name: string;
  head_member_id: string | null;
}
export interface TeamPayload {
  id?: string;
  department_id: string;
  name: string;
  manager_member_id: string | null;
  member_ids: string[];
}
export interface MemberPayload {
  id?: string;
  name: string;
  role: string;
  title: string;
  joined_at?: string;
  team_id: string | null;
  manages_team_id: string | null;
  is_admin: boolean;
  skills: string[];
  interests: string[];
  bio: string;
  email?: string | null;
}
