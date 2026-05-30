/**
 * Tiny IndexedDB-backed key/value store for "offline drafts".
 *
 * Why not a third-party dep:
 *  - We only need {get, set, delete, list keys-with-prefix}.
 *  - Pinning + transitive deps for a 1KB helper is more risk than just
 *    inlining a 60-line wrapper.
 *
 * All public functions swallow errors (private-mode Safari, full disk, etc.)
 * and return safe defaults — losing a local draft is annoying but should never
 * crash the page.
 */

const DB_NAME = "atlaslens";
const DB_VERSION = 1;
const STORE = "drafts";

function isAvailable(): boolean {
  return typeof window !== "undefined" && "indexedDB" in window;
}

function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = window.indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(STORE)) {
        db.createObjectStore(STORE);
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
    req.onblocked = () => reject(new Error("indexedDB open blocked"));
  });
}

function runOnStore<T>(
  mode: IDBTransactionMode,
  fn: (store: IDBObjectStore) => IDBRequest<T>,
): Promise<T> {
  return openDB().then(
    (db) =>
      new Promise<T>((resolve, reject) => {
        const tx = db.transaction(STORE, mode);
        const req = fn(tx.objectStore(STORE));
        req.onsuccess = () => resolve(req.result);
        req.onerror = () => reject(req.error);
        tx.oncomplete = () => db.close();
        tx.onabort = () => db.close();
      }),
  );
}

export async function getDraft<T>(key: string): Promise<T | null> {
  if (!isAvailable()) return null;
  try {
    const result = await runOnStore<T | undefined>("readonly", (s) => s.get(key));
    return (result as T) ?? null;
  } catch {
    return null;
  }
}

export async function setDraft<T>(key: string, value: T): Promise<void> {
  if (!isAvailable()) return;
  try {
    await runOnStore("readwrite", (s) => s.put(value, key));
  } catch {
    /* ignore */
  }
}

export async function deleteDraft(key: string): Promise<void> {
  if (!isAvailable()) return;
  try {
    await runOnStore("readwrite", (s) => s.delete(key));
  } catch {
    /* ignore */
  }
}

export async function listDraftKeys(prefix: string): Promise<string[]> {
  if (!isAvailable()) return [];
  try {
    const keys = await runOnStore<IDBValidKey[]>("readonly", (s) => s.getAllKeys());
    return (keys as string[]).filter(
      (k) => typeof k === "string" && k.startsWith(prefix),
    );
  } catch {
    return [];
  }
}
