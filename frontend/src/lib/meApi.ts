import { authedFetch } from "@/lib/auth";

export const meApi = {
  profile: () => authedFetch<MyProfile>("/api/me/profile"),
  goals: () => authedFetch<{ goals: MyGoal[] }>("/api/me/goals"),
  createGoal: (payload: GoalPayload) =>
    authedFetch<{ goal: MyGoal }>("/api/me/goals", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateGoal: (goalId: string, payload: GoalPayload) =>
    authedFetch<{ goal: MyGoal }>(`/api/me/goals/${encodeURIComponent(goalId)}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  deleteGoal: (goalId: string) =>
    authedFetch<{ deleted: string }>(`/api/me/goals/${encodeURIComponent(goalId)}`, {
      method: "DELETE",
    }),
  dailyReports: () => authedFetch<{ reports: MyDailyReport[] }>("/api/me/daily-reports"),
  submitDailyReport: (payload: SubmitDailyPayload) =>
    authedFetch<{ saved: boolean; report: MyDailyReport }>("/api/me/daily-reports", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  draftDailyReport: (payload: { report_date: string; bullet_hints: string[] }) =>
    authedFetch<{ member_id: string; date: string; draft: DraftDaily }>(
      "/api/me/daily-reports/draft",
      { method: "POST", body: JSON.stringify(payload) },
    ),
  oneOnOnes: () => authedFetch<{ one_on_ones: MyOneOnOne[] }>("/api/me/one-on-ones"),
  meetings: () => authedFetch<{ meetings: MyMeeting[] }>("/api/me/meetings"),
  getPrepNotes: () =>
    authedFetch<{ member_id: string; notes: string; updated_at: string | null }>(
      "/api/me/prep-notes",
    ),
  savePrepNotes: (notes: string) =>
    authedFetch<{ member_id: string; notes: string; updated_at: string }>("/api/me/prep-notes", {
      method: "POST",
      body: JSON.stringify({ notes }),
    }),
};

export interface GoalPayload {
  id?: string;
  period: string;
  objective: string;
  key_results: string[];
  progress_pct: number;
  status: string;
}

export interface MyProfile {
  id: string;
  name: string;
  role: string;
  title: string;
  joined_at: string;
  manager_id: string | null;
  skills: string[];
  interests: string[];
  bio: string;
}

export interface MyGoal {
  id: string;
  member_id: string;
  period: string;
  objective: string;
  key_results: string[];
  progress_pct: number;
  status: string;
}

export interface MyDailyReport {
  id: string;
  member_id: string;
  report_date: string;
  yesterday: string;
  today: string;
  blockers: string;
  mood?: number | null;
}

export interface MyOneOnOne {
  id: string;
  em_id: string;
  member_id: string;
  held_at: string;
  topics: string[];
  notes: string;
  todos: string[];
  follow_ups: string[];
}

export interface MyMeeting {
  id: string;
  title: string;
  held_at: string;
  attendees: string[];
  notes: string;
  decisions: string[];
  action_items: string[];
}

export interface SubmitDailyPayload {
  report_date: string;
  yesterday: string;
  today: string;
  blockers: string;
  mood: number | null;
}

export interface DraftDaily {
  yesterday?: string;
  today?: string;
  blockers?: string;
  suggested_mood?: number;
}
