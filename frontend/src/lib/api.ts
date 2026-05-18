import { authedFetch } from "@/lib/auth";

export const api = {
  listMembers: () => authedFetch<{ members: MemberSummary[] }>("/api/members"),
  getMember: (id: string) => authedFetch<MemberDetail>(`/api/members/${id}`),
  memberInsights: (id: string) =>
    authedFetch<{ insights: Insights }>(`/api/members/${id}/insights`, {
      method: "POST",
    }),
  getOneOnOnePacket: (memberId: string) =>
    authedFetch<OneOnOnePacket>(`/api/one-on-ones/packet/${memberId}`),
  draftMinutes: (input: { member_id: string; raw_notes: string }) =>
    authedFetch<DraftedMinutes>("/api/one-on-ones/draft-minutes", {
      method: "POST",
      body: JSON.stringify(input),
    }),
  saveOneOnOneRecord: (input: OneOnOneRecord) =>
    authedFetch<{ saved: boolean; record: OneOnOne }>("/api/one-on-ones/records", {
      method: "POST",
      body: JSON.stringify(input),
    }),
  teamSummary: (date: string) =>
    authedFetch<TeamSummary>(`/api/daily-pulse/team-summary?report_date=${date}`),
  simulate: (change: StructureChange) =>
    authedFetch<SimulationResult>("/api/simulator/simulate", {
      method: "POST",
      body: JSON.stringify({ change }),
    }),
  alignment: () => authedFetch<AlignmentReport>("/api/goals/alignment"),
  teamHealth: () => authedFetch<TeamHealth>("/api/health/team"),
  chat: (input: {
    messages: ChatMessage[];
    style?: string;
    style_instructions?: string;
  }) =>
    authedFetch<ChatReply>("/api/chat", {
      method: "POST",
      body: JSON.stringify(input),
    }),
  chatStyles: () =>
    authedFetch<{ styles: { key: string; label: string }[] }>("/api/chat/styles"),
};

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ToolCallTrace {
  name: string;
  arguments: Record<string, unknown>;
  result_preview: string;
  elapsed_ms: number;
}

export interface ChatReply {
  reply: string;
  style?: string;
  tool_calls: ToolCallTrace[];
}

// ---- types ----
export interface MemberSummary {
  id: string;
  name: string;
  role: string;
  title: string;
  manager_id: string | null;
  skills: string[];
}

export interface MemberDetail {
  profile: MemberSummary & { bio: string; interests: string[]; joined_at: string };
  goals: Goal[];
  recent_daily_reports: DailyReport[];
  recent_one_on_ones: OneOnOne[];
  recent_meetings: Meeting[];
  insights?: Insights;
}

export interface Goal {
  id: string;
  member_id: string;
  period: string;
  objective: string;
  key_results: string[];
  progress_pct: number;
  status: string;
}

export interface DailyReport {
  id: string;
  member_id: string;
  report_date: string;
  yesterday: string;
  today: string;
  blockers: string;
  mood?: number | null;
}

export interface OneOnOne {
  id: string;
  em_id: string;
  member_id: string;
  held_at: string;
  topics: string[];
  notes: string;
  todos: string[];
  follow_ups: string[];
}

export interface Meeting {
  id: string;
  title: string;
  held_at: string;
  attendees: string[];
  notes: string;
  decisions: string[];
  action_items: string[];
}

export interface Insights {
  highlights?: unknown[];
  risks?: unknown[];
  growth_signals?: unknown[];
  suggested_questions?: unknown[];
  raw?: string;
  parse_error?: boolean;
}

export interface OneOnOnePacket {
  member_id: string;
  packet: {
    opening_check_in?: string;
    discussion_topics?: unknown[];
    growth_questions?: unknown[];
    blockers_to_surface?: unknown[];
    follow_ups_from_last_time?: unknown[];
  };
}

export interface DraftedMinutes {
  structured: {
    summary?: string;
    key_topics?: string[];
    decisions?: string[];
    todos?: Array<{ task: string; owner?: string; due?: string }>;
    follow_ups_for_next_time?: string[];
  };
}

export interface TeamSummary {
  date: string;
  report_count: number;
  summary: {
    tldr?: string[];
    highlights?: Record<string, unknown>;
    blockers_to_surface?: Record<string, unknown>;
    themes?: string[];
  };
}

export interface StructureChange {
  kind: string;
  description: string;
  parameters?: Record<string, string | string[]>;
}

export interface SimulationResult {
  change: StructureChange;
  impact: any;
  members: Record<string, string>;
}

export interface AlignmentReport {
  members?: Array<{
    member_id: string;
    analysis: { overall?: string; [k: string]: unknown };
  }>;
}

export interface OneOnOneRecord {
  member_id: string;
  held_on: string;
  topics: string[];
  notes: string;
  todos: string[];
  follow_ups: string[];
}

export interface TeamHealth {
  as_of: string;
  members: Array<{
    member_id: string;
    name: string;
    daily_reports_last_14d: number;
    blockers_mentioned_last_14d: number;
    meetings_attended_last_14d: number;
    days_since_last_one_on_one: number | null;
    facts_for_em: string[];
  }>;
}
