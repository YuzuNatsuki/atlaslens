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
