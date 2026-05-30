/**
 * Schema + key helpers for the daily-report offline draft.
 *
 * Drafts are scoped by (member_id, report_date) so:
 *   - Different members on the same shared device don't bleed into each other.
 *   - Drafts for different dates coexist without clobbering.
 */

export const DAILY_DRAFT_PREFIX = "daily:";

export interface DailyDraft {
  yesterday: string;
  today: string;
  blockers: string;
  hint: string;
  updated_at: string; // ISO timestamp
}

export function dailyDraftKey(memberId: string, reportDate: string): string {
  return `${DAILY_DRAFT_PREFIX}${memberId}:${reportDate}`;
}

export function isDailyDraftDirty(
  draft: Pick<DailyDraft, "yesterday" | "today" | "blockers" | "hint">,
  baseline: Pick<DailyDraft, "yesterday" | "today" | "blockers">,
): boolean {
  return (
    draft.yesterday !== baseline.yesterday ||
    draft.today !== baseline.today ||
    draft.blockers !== baseline.blockers ||
    draft.hint.trim().length > 0
  );
}
