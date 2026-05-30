import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Building2, Key, Pencil, Plus, Trash2, Users } from "lucide-react";

import {
  adminApi,
  type AdminMember,
  type Department,
  type Division,
  type MemberPayload,
  type Team,
} from "@/lib/adminApi";
import { PageHeader } from "@/components/ui";

type Tab = "org" | "members";

export default function AdminPage() {
  const [tab, setTab] = useState<Tab>("org");

  return (
    <div className="grid gap-6">
      <PageHeader
        title="アカウント / 組織管理"
        subtitle="Admin だけがアクセスできるページです。組織階層とメンバー全件をここで CRUD します。"
      />
      <nav className="flex gap-2">
        <TabButton
          active={tab === "org"}
          onClick={() => setTab("org")}
          icon={<Building2 size={14} />}
        >
          組織ツリー
        </TabButton>
        <TabButton
          active={tab === "members"}
          onClick={() => setTab("members")}
          icon={<Users size={14} />}
        >
          メンバー
        </TabButton>
      </nav>
      {tab === "org" ? <OrgPanel /> : <MembersPanel />}
    </div>
  );
}

function TabButton({
  active,
  onClick,
  icon,
  children,
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`px-3 py-1.5 rounded-full text-sm border flex items-center gap-1 transition ${
        active
          ? "bg-brand text-white border-brand"
          : "bg-white text-slate-700 border-slate-300 hover:bg-slate-100"
      }`}
    >
      {icon}
      {children}
    </button>
  );
}

// ============================================================
// Org tree
// ============================================================

function OrgPanel() {
  const qc = useQueryClient();
  const orgQ = useQuery({ queryKey: ["admin", "org"], queryFn: adminApi.getOrg });
  const invalidate = () => qc.invalidateQueries({ queryKey: ["admin", "org"] });

  const memberIndex = useMemo(() => {
    const idx: Record<string, AdminMember> = {};
    for (const m of orgQ.data?.members ?? []) idx[m.id] = m;
    return idx;
  }, [orgQ.data]);

  if (orgQ.isLoading) return <p className="text-slate-500">読み込み中…</p>;
  if (orgQ.isError) return <p className="text-rose-700">取得失敗</p>;
  if (!orgQ.data) return null;

  return (
    <div className="grid gap-3">
      {orgQ.data.companies.map((company) => (
        <CompanyCard
          key={company.id}
          companyName={company.name}
          divisions={company.divisions}
          memberIndex={memberIndex}
          onChanged={invalidate}
        />
      ))}
    </div>
  );
}

function CompanyCard({
  companyName,
  divisions,
  memberIndex,
  onChanged,
}: {
  companyName: string;
  divisions: Division[];
  memberIndex: Record<string, AdminMember>;
  onChanged: () => void;
}) {
  const [showNewDiv, setShowNewDiv] = useState(false);

  return (
    <section className="card">
      <header className="flex items-center justify-between mb-2">
        <h2 className="font-semibold flex items-center gap-1">
          <Building2 size={16} />
          {companyName}
        </h2>
        <button
          onClick={() => setShowNewDiv(true)}
          className="btn-ghost text-xs flex items-center gap-1"
        >
          <Plus size={12} /> 事業部
        </button>
      </header>
      {showNewDiv && (
        <DivisionForm
          mode="create"
          onClose={() => setShowNewDiv(false)}
          onChanged={onChanged}
        />
      )}
      <div className="grid gap-2">
        {divisions.map((div) => (
          <DivisionRow
            key={div.id}
            division={div}
            memberIndex={memberIndex}
            onChanged={onChanged}
          />
        ))}
      </div>
    </section>
  );
}

function DivisionRow({
  division,
  memberIndex,
  onChanged,
}: {
  division: Division;
  memberIndex: Record<string, AdminMember>;
  onChanged: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [showNewDept, setShowNewDept] = useState(false);
  const head = division.head_member_id ? memberIndex[division.head_member_id] : null;
  const delM = useMutation({
    mutationFn: () => adminApi.deleteDivision(division.id),
    onSuccess: onChanged,
  });

  return (
    <div className="border border-slate-200 rounded p-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-medium">{division.name}</span>
        {head && <span className="pill bg-slate-100 text-slate-600">部長: {head.name}</span>}
        <div className="ml-auto flex gap-1">
          <button onClick={() => setEditing((v) => !v)} className="btn-ghost text-xs flex items-center gap-1">
            <Pencil size={12} /> 編集
          </button>
          <button onClick={() => setShowNewDept(true)} className="btn-ghost text-xs flex items-center gap-1">
            <Plus size={12} /> 課
          </button>
          <button
            onClick={() => {
              if (confirm(`「${division.name}」を削除しますか？`)) delM.mutate();
            }}
            className="btn-ghost text-xs text-rose-700 flex items-center gap-1"
          >
            <Trash2 size={12} /> 削除
          </button>
        </div>
      </div>
      {editing && (
        <div className="mt-3">
          <DivisionForm
            mode="edit"
            initial={division}
            onClose={() => setEditing(false)}
            onChanged={onChanged}
          />
        </div>
      )}
      {showNewDept && (
        <div className="mt-3">
          <DepartmentForm
            mode="create"
            divisionId={division.id}
            onClose={() => setShowNewDept(false)}
            onChanged={onChanged}
          />
        </div>
      )}
      <div className="mt-3 grid gap-2 pl-4 border-l border-slate-200">
        {(division.departments ?? []).map((dept) => (
          <DepartmentRow
            key={dept.id}
            department={dept}
            memberIndex={memberIndex}
            onChanged={onChanged}
          />
        ))}
      </div>
    </div>
  );
}

function DepartmentRow({
  department,
  memberIndex,
  onChanged,
}: {
  department: Department;
  memberIndex: Record<string, AdminMember>;
  onChanged: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [showNewTeam, setShowNewTeam] = useState(false);
  const head = department.head_member_id ? memberIndex[department.head_member_id] : null;
  const delM = useMutation({
    mutationFn: () => adminApi.deleteDepartment(department.id),
    onSuccess: onChanged,
  });

  return (
    <div className="border border-slate-100 rounded p-2 bg-slate-50">
      <div className="flex flex-wrap items-center gap-2">
        <span>{department.name}</span>
        {head && <span className="pill bg-white text-slate-600">課長: {head.name}</span>}
        <div className="ml-auto flex gap-1">
          <button onClick={() => setEditing((v) => !v)} className="btn-ghost text-xs flex items-center gap-1">
            <Pencil size={12} /> 編集
          </button>
          <button onClick={() => setShowNewTeam(true)} className="btn-ghost text-xs flex items-center gap-1">
            <Plus size={12} /> チーム
          </button>
          <button
            onClick={() => {
              if (confirm(`「${department.name}」を削除しますか？`)) delM.mutate();
            }}
            className="btn-ghost text-xs text-rose-700 flex items-center gap-1"
          >
            <Trash2 size={12} /> 削除
          </button>
        </div>
      </div>
      {editing && (
        <div className="mt-2">
          <DepartmentForm
            mode="edit"
            divisionId={department.division_id}
            initial={department}
            onClose={() => setEditing(false)}
            onChanged={onChanged}
          />
        </div>
      )}
      {showNewTeam && (
        <div className="mt-2">
          <TeamForm
            mode="create"
            departmentId={department.id}
            onClose={() => setShowNewTeam(false)}
            onChanged={onChanged}
          />
        </div>
      )}
      <div className="mt-2 grid gap-1 pl-4">
        {(department.teams ?? []).map((team) => (
          <TeamRow key={team.id} team={team} memberIndex={memberIndex} onChanged={onChanged} />
        ))}
      </div>
    </div>
  );
}

function TeamRow({
  team,
  memberIndex,
  onChanged,
}: {
  team: Team;
  memberIndex: Record<string, AdminMember>;
  onChanged: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const manager = team.manager_member_id ? memberIndex[team.manager_member_id] : null;
  const members = team.member_ids
    .map((id) => memberIndex[id])
    .filter(Boolean);
  const delM = useMutation({
    mutationFn: () => adminApi.deleteTeam(team.id),
    onSuccess: onChanged,
  });

  return (
    <div className="border border-slate-100 rounded p-2 bg-white">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-medium text-sm">{team.name}</span>
        {manager && (
          <span className="pill bg-brand/10 text-brand">管理者: {manager.name}</span>
        )}
        {members.length > 0 && (
          <span className="text-xs text-slate-500">
            メンバー: {members.map((m) => m.name).join(", ")}
          </span>
        )}
        <div className="ml-auto flex gap-1">
          <button onClick={() => setEditing((v) => !v)} className="btn-ghost text-xs flex items-center gap-1">
            <Pencil size={12} /> 編集
          </button>
          <button
            onClick={() => {
              if (confirm(`「${team.name}」を削除しますか？`)) delM.mutate();
            }}
            className="btn-ghost text-xs text-rose-700 flex items-center gap-1"
          >
            <Trash2 size={12} /> 削除
          </button>
        </div>
      </div>
      {editing && (
        <div className="mt-2">
          <TeamForm
            mode="edit"
            departmentId={team.department_id}
            initial={team}
            onClose={() => setEditing(false)}
            onChanged={onChanged}
          />
        </div>
      )}
    </div>
  );
}

// ----- Forms -----

function DivisionForm({
  mode,
  initial,
  onClose,
  onChanged,
}: {
  mode: "create" | "edit";
  initial?: Division;
  onClose: () => void;
  onChanged: () => void;
}) {
  const [name, setName] = useState(initial?.name ?? "");
  const [head, setHead] = useState(initial?.head_member_id ?? "");
  const memberOpts = useMemberOptions();
  const saveM = useMutation({
    mutationFn: () =>
      mode === "create"
        ? adminApi.createDivision({
            company_id: initial?.company_id ?? "atlascorp",
            name,
            head_member_id: head || null,
          })
        : adminApi.updateDivision(initial!.id, {
            company_id: initial!.company_id,
            name,
            head_member_id: head || null,
          }),
    onSuccess: () => {
      onChanged();
      onClose();
    },
  });
  return (
    <FormShell title={mode === "create" ? "事業部を作成" : "事業部を編集"} onCancel={onClose} onSave={() => saveM.mutate()} saving={saveM.isPending}>
      <Field label="名前">
        <input value={name} onChange={(e) => setName(e.target.value)} className="input" />
      </Field>
      <Field label="部長 (任意)">
        <select value={head} onChange={(e) => setHead(e.target.value)} className="input">
          <option value="">— なし —</option>
          {memberOpts.map((m) => (
            <option key={m.id} value={m.id}>{m.name}</option>
          ))}
        </select>
      </Field>
    </FormShell>
  );
}

function DepartmentForm({
  mode,
  divisionId,
  initial,
  onClose,
  onChanged,
}: {
  mode: "create" | "edit";
  divisionId: string;
  initial?: Department;
  onClose: () => void;
  onChanged: () => void;
}) {
  const [name, setName] = useState(initial?.name ?? "");
  const [head, setHead] = useState(initial?.head_member_id ?? "");
  const memberOpts = useMemberOptions();
  const saveM = useMutation({
    mutationFn: () =>
      mode === "create"
        ? adminApi.createDepartment({ division_id: divisionId, name, head_member_id: head || null })
        : adminApi.updateDepartment(initial!.id, { division_id: divisionId, name, head_member_id: head || null }),
    onSuccess: () => {
      onChanged();
      onClose();
    },
  });
  return (
    <FormShell title={mode === "create" ? "課を作成" : "課を編集"} onCancel={onClose} onSave={() => saveM.mutate()} saving={saveM.isPending}>
      <Field label="名前">
        <input value={name} onChange={(e) => setName(e.target.value)} className="input" />
      </Field>
      <Field label="課長 (任意)">
        <select value={head} onChange={(e) => setHead(e.target.value)} className="input">
          <option value="">— なし —</option>
          {memberOpts.map((m) => (
            <option key={m.id} value={m.id}>{m.name}</option>
          ))}
        </select>
      </Field>
    </FormShell>
  );
}

function TeamForm({
  mode,
  departmentId,
  initial,
  onClose,
  onChanged,
}: {
  mode: "create" | "edit";
  departmentId: string;
  initial?: Team;
  onClose: () => void;
  onChanged: () => void;
}) {
  const [name, setName] = useState(initial?.name ?? "");
  const [manager, setManager] = useState(initial?.manager_member_id ?? "");
  const [memberIds, setMemberIds] = useState<string[]>(initial?.member_ids ?? []);
  const memberOpts = useMemberOptions();
  const saveM = useMutation({
    mutationFn: () =>
      mode === "create"
        ? adminApi.createTeam({
            department_id: departmentId,
            name,
            manager_member_id: manager || null,
            member_ids: memberIds,
          })
        : adminApi.updateTeam(initial!.id, {
            department_id: departmentId,
            name,
            manager_member_id: manager || null,
            member_ids: memberIds,
          }),
    onSuccess: () => {
      onChanged();
      onClose();
    },
  });

  const toggle = (id: string) =>
    setMemberIds((prev) => (prev.includes(id) ? prev.filter((m) => m !== id) : [...prev, id]));

  return (
    <FormShell title={mode === "create" ? "チームを作成" : "チームを編集"} onCancel={onClose} onSave={() => saveM.mutate()} saving={saveM.isPending}>
      <Field label="名前">
        <input value={name} onChange={(e) => setName(e.target.value)} className="input" />
      </Field>
      <Field label="管理者 (任意)">
        <select value={manager} onChange={(e) => setManager(e.target.value)} className="input">
          <option value="">— なし —</option>
          {memberOpts.map((m) => (
            <option key={m.id} value={m.id}>{m.name}</option>
          ))}
        </select>
      </Field>
      <Field label="メンバー (複数選択)">
        <div className="flex flex-wrap gap-1">
          {memberOpts.map((m) => {
            const active = memberIds.includes(m.id);
            return (
              <button
                key={m.id}
                type="button"
                onClick={() => toggle(m.id)}
                className={`px-2 py-1 rounded-full text-xs border ${
                  active
                    ? "bg-brand text-white border-brand"
                    : "bg-white text-slate-700 border-slate-300"
                }`}
              >
                {m.name}
              </button>
            );
          })}
        </div>
      </Field>
    </FormShell>
  );
}

function useMemberOptions() {
  const q = useQuery({ queryKey: ["admin", "members"], queryFn: adminApi.listMembers });
  return q.data?.members ?? [];
}

// ============================================================
// Members table
// ============================================================

function MembersPanel() {
  const qc = useQueryClient();
  const membersQ = useQuery({ queryKey: ["admin", "members"], queryFn: adminApi.listMembers });
  const teamsQ = useQuery({ queryKey: ["admin", "org"], queryFn: adminApi.getOrg });
  const [editingId, setEditingId] = useState<string | "new" | null>(null);
  const [pwReveal, setPwReveal] = useState<{ memberId: string; password: string } | null>(null);

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["admin", "members"] });
    qc.invalidateQueries({ queryKey: ["admin", "org"] });
  };

  const resetM = useMutation({
    mutationFn: (id: string) => adminApi.resetPassword(id),
    onSuccess: (data) => setPwReveal({ memberId: data.member_id, password: data.new_password }),
  });
  const delM = useMutation({
    mutationFn: (id: string) => adminApi.deleteMember(id),
    onSuccess: invalidate,
  });

  const teamsById = useMemo(() => {
    const map: Record<string, { name: string }> = {};
    for (const c of teamsQ.data?.companies ?? []) {
      for (const div of c.divisions) {
        for (const dept of div.departments ?? []) {
          for (const team of dept.teams ?? []) {
            map[team.id] = { name: `${dept.name} / ${team.name}` };
          }
        }
      }
    }
    return map;
  }, [teamsQ.data]);

  return (
    <div className="grid gap-3">
      <div className="flex items-center justify-between">
        <span className="text-sm text-slate-500">
          全 {membersQ.data?.members.length ?? 0} 名
        </span>
        {editingId !== "new" && (
          <button onClick={() => setEditingId("new")} className="btn-primary flex items-center gap-1">
            <Plus size={14} /> 新規メンバー
          </button>
        )}
      </div>

      {pwReveal && (
        <div className="card bg-amber-50 border-amber-300">
          <p className="text-sm font-medium text-amber-800">
            <Key size={14} className="inline" />{" "}
            {pwReveal.memberId} の新しい初期パスワード:
          </p>
          <p className="mt-1 font-mono text-base">{pwReveal.password}</p>
          <p className="text-xs text-amber-700 mt-1">
            この値は再表示できません。EMからメンバーへ安全に伝えてください。
          </p>
          <button onClick={() => setPwReveal(null)} className="btn-ghost mt-2 text-xs">
            閉じる
          </button>
        </div>
      )}

      {editingId === "new" && (
        <MemberForm
          mode="create"
          teamOptions={teamsById}
          onClose={() => setEditingId(null)}
          onSaved={(initialPw) => {
            invalidate();
            setEditingId(null);
            if (initialPw) setPwReveal({ memberId: "新規メンバー", password: initialPw });
          }}
        />
      )}

      <div className="grid gap-2">
        {membersQ.data?.members.map((m) =>
          editingId === m.id ? (
            <MemberForm
              key={m.id}
              mode="edit"
              initial={m}
              teamOptions={teamsById}
              onClose={() => setEditingId(null)}
              onSaved={() => {
                invalidate();
                setEditingId(null);
              }}
            />
          ) : (
            <article key={m.id} className="card">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-medium">{m.name}</span>
                <span className="text-xs text-slate-500">{m.title}</span>
                {m.is_admin && <span className="pill bg-rose-100 text-rose-700">Admin</span>}
                {m.manages_team_id && <span className="pill bg-brand/10 text-brand">管理者</span>}
                {m.team_id && (
                  <span className="text-xs text-slate-500">
                    所属: {teamsById[m.team_id]?.name ?? m.team_id}
                  </span>
                )}
                {m.email && <span className="text-xs text-slate-400">{m.email}</span>}
                <div className="ml-auto flex gap-1">
                  <button
                    onClick={() => setEditingId(m.id)}
                    className="btn-ghost text-xs flex items-center gap-1"
                  >
                    <Pencil size={12} /> 編集
                  </button>
                  {m.email && (
                    <button
                      onClick={() => {
                        if (confirm(`${m.name} のパスワードをリセットしますか？`))
                          resetM.mutate(m.id);
                      }}
                      className="btn-ghost text-xs flex items-center gap-1"
                    >
                      <Key size={12} /> PWリセット
                    </button>
                  )}
                  <button
                    onClick={() => {
                      if (confirm(`${m.name} を削除しますか？`)) delM.mutate(m.id);
                    }}
                    className="btn-ghost text-xs text-rose-700 flex items-center gap-1"
                  >
                    <Trash2 size={12} /> 削除
                  </button>
                </div>
              </div>
            </article>
          ),
        )}
      </div>
    </div>
  );
}

function MemberForm({
  mode,
  initial,
  teamOptions,
  onClose,
  onSaved,
}: {
  mode: "create" | "edit";
  initial?: AdminMember;
  teamOptions: Record<string, { name: string }>;
  onClose: () => void;
  onSaved: (initialPassword: string | null) => void;
}) {
  const [name, setName] = useState(initial?.name ?? "");
  const [email, setEmail] = useState(initial?.email ?? "");
  const [role, setRole] = useState(initial?.role ?? "mid");
  const [title, setTitle] = useState(initial?.title ?? "");
  const [teamId, setTeamId] = useState(initial?.team_id ?? "");
  const [managesTeamId, setManagesTeamId] = useState(initial?.manages_team_id ?? "");
  const [isAdmin, setIsAdmin] = useState(initial?.is_admin ?? false);
  const [skills, setSkills] = useState((initial?.skills ?? []).join(", "));
  const [bio, setBio] = useState(initial?.bio ?? "");

  const payload: MemberPayload = {
    name,
    email: email || null,
    role,
    title,
    team_id: teamId || null,
    manages_team_id: managesTeamId || null,
    is_admin: isAdmin,
    skills: skills.split(",").map((s) => s.trim()).filter(Boolean),
    interests: initial?.interests ?? [],
    bio,
  };

  const saveM = useMutation({
    mutationFn: async () => {
      if (mode === "create") return adminApi.createMember(payload);
      const res = await adminApi.updateMember(initial!.id, payload);
      return { ...res, initial_password: null as string | null };
    },
    onSuccess: (data: any) => onSaved(data.initial_password ?? null),
  });

  return (
    <FormShell
      title={mode === "create" ? "新規メンバー" : "メンバーを編集"}
      onCancel={onClose}
      onSave={() => saveM.mutate()}
      saving={saveM.isPending}
    >
      <div className="grid sm:grid-cols-2 gap-3">
        <Field label="名前">
          <input value={name} onChange={(e) => setName(e.target.value)} className="input" />
        </Field>
        <Field label="メール (任意。ある場合はログイン可能)">
          <input value={email} onChange={(e) => setEmail(e.target.value)} className="input" />
        </Field>
        <Field label="ロール">
          <select value={role} onChange={(e) => setRole(e.target.value)} className="input">
            <option value="em">EM</option>
            <option value="tech_lead">Tech Lead</option>
            <option value="senior">Senior</option>
            <option value="mid">Mid</option>
            <option value="junior">Junior</option>
            <option value="admin">Admin</option>
          </select>
        </Field>
        <Field label="タイトル">
          <input value={title} onChange={(e) => setTitle(e.target.value)} className="input" />
        </Field>
        <Field label="所属チーム">
          <select value={teamId} onChange={(e) => setTeamId(e.target.value)} className="input">
            <option value="">— 未所属 —</option>
            {Object.entries(teamOptions).map(([id, t]) => (
              <option key={id} value={id}>{t.name}</option>
            ))}
          </select>
        </Field>
        <Field label="管理するチーム (任意)">
          <select value={managesTeamId} onChange={(e) => setManagesTeamId(e.target.value)} className="input">
            <option value="">— なし —</option>
            {Object.entries(teamOptions).map(([id, t]) => (
              <option key={id} value={id}>{t.name}</option>
            ))}
          </select>
        </Field>
      </div>
      <Field label="スキル (カンマ区切り)">
        <input value={skills} onChange={(e) => setSkills(e.target.value)} className="input" placeholder="go, kubernetes, terraform" />
      </Field>
      <Field label="自己紹介">
        <textarea value={bio} onChange={(e) => setBio(e.target.value)} className="input h-16" />
      </Field>
      <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" checked={isAdmin} onChange={(e) => setIsAdmin(e.target.checked)} />
        Admin 権限を付与する
      </label>
    </FormShell>
  );
}

// ----- generic small helpers -----

function FormShell({
  title,
  children,
  onCancel,
  onSave,
  saving,
}: {
  title: string;
  children: React.ReactNode;
  onCancel: () => void;
  onSave: () => void;
  saving: boolean;
}) {
  return (
    <div className="card border-brand grid gap-2">
      <h3 className="font-medium text-sm text-brand">{title}</h3>
      {children}
      <div className="flex items-center gap-2 pt-2">
        <button onClick={onSave} disabled={saving} className="btn-primary">
          {saving ? "保存中…" : "保存"}
        </button>
        <button onClick={onCancel} className="btn-ghost">キャンセル</button>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="grid gap-1">
      <span className="text-xs text-slate-500">{label}</span>
      {children}
    </label>
  );
}
