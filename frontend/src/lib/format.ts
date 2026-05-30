/**
 * AI レスポンスは JSON モードでもフィールド名が揺れるので、柔軟に文字列化する。
 *
 * 例:
 *  - {text: "..."} / {description: "..."} / {topic: "..."} / {question: "..."} / {blocker: "..."} / {follow_up: "..."}
 *  - {"...": "..."} の単一プロパティオブジェクト
 *  - string
 */
export function pickText(value: unknown): string {
  if (value == null) return "";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  if (Array.isArray(value)) return value.map(pickText).filter(Boolean).join(" / ");
  if (typeof value === "object") {
    const obj = value as Record<string, unknown>;
    for (const key of [
      "text",
      "description",
      "topic",
      "question",
      "blocker",
      "follow_up",
      "task",
      "summary",
      "label",
      "value",
    ]) {
      const v = obj[key];
      if (typeof v === "string" && v.length > 0) return v;
    }
    // 最後の手段: 全 string プロパティを連結
    const stringFields = Object.values(obj).filter(
      (v): v is string => typeof v === "string" && v.length > 0,
    );
    if (stringFields.length > 0) return stringFields.join(" — ");
    return JSON.stringify(obj);
  }
  return String(value);
}

export function pickEvidence(value: unknown): string[] {
  if (value == null) return [];
  if (typeof value !== "object") return [];
  const obj = value as Record<string, unknown>;
  const ev = obj["evidence"];
  if (Array.isArray(ev)) {
    return ev.map((e) => (typeof e === "string" ? e : pickText(e))).filter(Boolean);
  }
  return [];
}

/**
 * AI が返す内部 ID を人間が読めるラベルに変換する。
 *
 * 変換例:
 *   daily-mem001-2026-05-08  → 佐藤 美咲の日報（5/8）
 *   1on1-mem001-2026-05-06   → 佐藤 美咲との1on1（5/6）
 *   g-mem001-1               → 佐藤 美咲のOKR
 *   mtg-2026-05-07           → 会議メモ（5/7）
 *
 * memberIndex は { memberId: memberName } の辞書。省略時はIDをそのまま返す。
 */
export function humanizeEvidenceId(
  id: string,
  memberIndex: Record<string, string> = {},
): string {
  // daily-{memberId}-{YYYY-MM-DD}
  const daily = id.match(/^daily-([^-]+(?:-[^-]+)?)-(\d{4})-(\d{2})-(\d{2})$/);
  if (daily) {
    const name = memberIndex[daily[1]] ?? daily[1];
    return `${name}の日報（${parseInt(daily[3])}/${parseInt(daily[4])}）`;
  }

  // 1on1-{memberId}-{YYYY-MM-DD}
  const ono = id.match(/^1on1-([^-]+(?:-[^-]+)?)-(\d{4})-(\d{2})-(\d{2})$/);
  if (ono) {
    const name = memberIndex[ono[1]] ?? ono[1];
    return `${name}との1on1（${parseInt(ono[3])}/${parseInt(ono[4])}）`;
  }

  // g-{memberId}-{n}
  const goal = id.match(/^g-([^-]+(?:-[^-]+)?)-\d+$/);
  if (goal) {
    const name = memberIndex[goal[1]] ?? goal[1];
    return `${name}のOKR`;
  }

  // mtg-{YYYY-MM-DD}
  const mtg = id.match(/^mtg-\d{4}-(\d{2})-(\d{2})/);
  if (mtg) {
    return `会議メモ（${parseInt(mtg[1])}/${parseInt(mtg[2])}）`;
  }

  return id;
}
