import { useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { ShieldCheck } from 'lucide-react';

import AppHeader from '@/components/AppHeader';
import { ConfirmDialog } from '@/components/ConfirmDialog';
import { DataTable, type DataTableColumn } from '@/components/DataTable';
import { Paginator } from '@/components/Paginator';
import {
  Checkbox,
  Dialog,
  DialogContent,
  DialogTitle,
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  Input,
} from '@/components/ui';
import { Textarea } from '@/components/ui/textarea';
import { Button as UIButton } from '@/components/ui/button';
import { notify } from '@/components/ui/app-toast';
import { cn } from '@/lib/utils';
import { MENU_CONTENT_CLASS, MENU_ITEM_CLASS, MENU_ITEM_DANGER_CLASS, MOBILE_CARD_CLASS, formatDateTime } from '@/lib/enterprise-ui';

import { api, TENANT_ID } from '../api/client';
import IconRoles from '../assets/icons/sys-roles.svg?react';
import IconAdd from '../assets/icons/add.svg?react';
import IconClear from '../assets/icons/field-clear.svg?react';
import IconEdit from '../assets/icons/edit.svg?react';
import IconMore from '../assets/icons/more.svg?react';
import IconRefresh from '../assets/icons/refresh.svg?react';
import IconSearch from '../assets/icons/search.svg?react';
import IconTrash from '../assets/icons/trash.svg?react';
import type { EnterpriseAuthUser } from '../auth';
import { useClientPagination } from '../hooks/useClientPagination';
import { StatusBadge } from './scheduled-tasks/StatusBadge';

type RoleRead = {
  id: string;
  tenant_id: string;
  display_name: string;
  description?: string;
  is_builtin: boolean;
  permissions: string[];
  user_count: number;
  created_at?: string;
  updated_at?: string;
};

type PermissionDef = {
  key: string;
  name: string;
  group: string;
  description: string;
};

type RoleDraft = {
  displayName: string;
  description: string;
  permissions: string[];
};

const ROLE_PAGE_SIZE = 10;
const ADMIN_ROLE_ID = 'admin';

const EMPTY_DRAFT: RoleDraft = { displayName: '', description: '', permissions: [] };

export default function RolesPage({
  currentUser,
  onLogout,
}: {
  currentUser?: EnterpriseAuthUser;
  onLogout?: () => void;
} = {}) {
  const [rows, setRows] = useState<RoleRead[]>([]);
  const [catalog, setCatalog] = useState<PermissionDef[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [editing, setEditing] = useState<RoleRead | null>(null);
  const [draft, setDraft] = useState<RoleDraft>(EMPTY_DRAFT);
  const [saving, setSaving] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<RoleRead | null>(null);
  const [deleting, setDeleting] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const [roleRows, catalogResponse] = await Promise.all([
        api.get<RoleRead[]>(`/api/enterprise/roles?tenant_id=${TENANT_ID}`),
        api.get<{ permissions: PermissionDef[] }>(
          `/api/enterprise/roles/permissions/catalog?tenant_id=${TENANT_ID}`,
        ),
      ]);
      setRows(roleRows);
      setCatalog(catalogResponse.permissions || []);
    } catch (error) {
      notify.error(error instanceof Error ? error.message : '加载角色失败');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  const permissionNameByKey = useMemo(() => {
    const map = new Map<string, string>();
    catalog.forEach((item) => map.set(item.key, item.name));
    return map;
  }, [catalog]);

  const filteredRows = useMemo(() => {
    const keyword = searchText.trim().toLowerCase();
    if (!keyword) return rows;
    return rows.filter((row) =>
      [row.display_name, row.description || '']
        .some((value) => value.toLowerCase().includes(keyword)),
    );
  }, [rows, searchText]);

  const pagination = useClientPagination(filteredRows, ROLE_PAGE_SIZE, searchText);

  function openCreate() {
    setDraft(EMPTY_DRAFT);
    setCreateOpen(true);
  }

  function openEdit(row: RoleRead) {
    setEditing(row);
    setDraft({
      displayName: row.display_name,
      description: row.description || '',
      permissions: [...row.permissions],
    });
  }

  async function saveCreate() {
    const displayName = draft.displayName.trim();
    if (!displayName) {
      notify.error('请填写角色名称');
      return;
    }
    setCreating(true);
    try {
      await api.post('/api/enterprise/roles', {
        tenant_id: TENANT_ID,
        display_name: displayName,
        description: draft.description.trim() || undefined,
        permissions: draft.permissions,
      });
      notify.success('角色已创建');
      setCreateOpen(false);
      await load();
    } catch (error) {
      notify.error(error instanceof Error ? error.message : '创建角色失败');
    } finally {
      setCreating(false);
    }
  }

  async function saveEdit() {
    if (!editing) return;
    const displayName = draft.displayName.trim();
    if (!displayName) {
      notify.error('请填写角色名称');
      return;
    }
    setSaving(true);
    try {
      await api.put(`/api/enterprise/roles/${editing.id}`, {
        tenant_id: TENANT_ID,
        display_name: displayName,
        description: draft.description.trim() || undefined,
        permissions: draft.permissions,
      });
      notify.success('角色已更新');
      setEditing(null);
      await load();
    } catch (error) {
      notify.error(error instanceof Error ? error.message : '保存角色失败');
    } finally {
      setSaving(false);
    }
  }

  async function confirmDelete() {
    const row = deleteTarget;
    if (!row) return;
    setDeleting(true);
    try {
      await api.delete(`/api/enterprise/roles/${row.id}?tenant_id=${TENANT_ID}`);
      notify.success('角色已删除');
      setDeleteTarget(null);
      await load();
    } catch (error) {
      notify.error(error instanceof Error ? error.message : '删除角色失败');
    } finally {
      setDeleting(false);
    }
  }

  function renderPermissionSummary(row: RoleRead) {
    if (row.id === ADMIN_ROLE_ID) {
      return <span className="text-[12px] text-[#858b9c]">全部权限</span>;
    }
    if (row.permissions.length === 0) {
      return <span className="text-[12px] text-[#c0c6d4]">未配置权限</span>;
    }
    const names = row.permissions
      .map((key) => permissionNameByKey.get(key) || key)
      .slice(0, 3);
    const rest = row.permissions.length - names.length;
    return (
      <span className="flex flex-wrap items-center gap-[4px]">
        {names.map((name) => (
          <span
            key={name}
            className="inline-flex items-center rounded-[6px] bg-[#f2f3f7] px-[6px] py-[2px] text-[11px] leading-none text-[#464c5e]"
          >
            {name}
          </span>
        ))}
        {rest > 0 && <span className="text-[11px] text-[#858b9c]">+{rest}</span>}
      </span>
    );
  }

  function renderActions(row: RoleRead) {
    if (row.id === ADMIN_ROLE_ID) return null;
    return (
      <DropdownMenu>
        <DropdownMenuTrigger
          aria-label="角色操作"
          className="ml-auto grid size-7 place-items-center rounded-[8px] text-[#1a71ff] transition-colors outline-none hover:bg-black/5 hover:text-[#4a8dff] focus-visible:bg-black/5"
        >
          <IconMore className="size-3.5" />
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className={MENU_CONTENT_CLASS}>
          <DropdownMenuItem className={MENU_ITEM_CLASS} onSelect={() => openEdit(row)}>
            <IconEdit />
            编辑
          </DropdownMenuItem>
          <DropdownMenuSeparator className="my-[2px] bg-[#eef0f4]" />
          <DropdownMenuItem
            variant="destructive"
            className={MENU_ITEM_DANGER_CLASS}
            disabled={row.is_builtin}
            onSelect={() => setDeleteTarget(row)}
          >
            <IconTrash />
            删除
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    );
  }

  const columns: DataTableColumn<RoleRead>[] = [
    {
      key: 'display_name',
      title: '角色名称',
      width: 220,
      className: 'text-[#18181a]',
      render: (row) => (
        <span className="flex min-w-0 items-center gap-[8px]">
          <span className="grid size-[24px] shrink-0 place-items-center rounded-full bg-[#eef1fb] text-[#7e96dc]">
            <ShieldCheck className="size-[14px]" />
          </span>
          <span className="truncate font-medium">{row.display_name}</span>
          {row.is_builtin && <StatusBadge tone="gray">内置</StatusBadge>}
        </span>
      ),
    },
    {
      key: 'description',
      title: '描述',
      width: 240,
      render: (row) => (
        <span className="block truncate text-[#464c5e]">{row.description || '-'}</span>
      ),
    },
    {
      key: 'permissions',
      title: '权限配置',
      width: 260,
      render: (row) => renderPermissionSummary(row),
    },
    {
      key: 'user_count',
      title: '成员数',
      width: 90,
      render: (row) => <span>{row.user_count}</span>,
    },
    {
      key: 'updated',
      title: '最近更新',
      width: 170,
      render: (row) => formatDateTime(row.updated_at),
    },
    {
      key: 'actions',
      title: '操作',
      width: 70,
      align: 'right',
      render: (row) => renderActions(row),
    },
  ];

  const renderMobileCard = (row: RoleRead) => (
    <article className={MOBILE_CARD_CLASS} key={row.id}>
      <div className="flex min-w-0 items-start justify-between gap-[10px]">
        <span className="flex min-w-0 items-center gap-[8px]">
          <span className="grid size-[28px] shrink-0 place-items-center rounded-full bg-[#eef1fb] text-[#7e96dc]">
            <ShieldCheck className="size-[15px]" />
          </span>
          <span className="min-w-0">
            <strong className="block truncate text-[14px] font-semibold text-[#18181a]">
              {row.display_name}
            </strong>
            <span className="mt-[2px] block truncate text-[12px] text-[#858b9c]">
              {row.description || '暂无描述'}
            </span>
            <span className="mt-[6px] block">{renderPermissionSummary(row)}</span>
          </span>
        </span>
        {renderActions(row)}
      </div>
      <div className="mt-[10px] flex items-center justify-between gap-[10px] text-[12px] text-[#858b9c]">
        <span>成员数 {row.user_count}</span>
        <span>更新 {formatDateTime(row.updated_at)}</span>
      </div>
    </article>
  );

  return (
    <div className="min-h-full box-border px-[48px] pt-[32px] pb-[43px] max-[900px]:px-[16px]" aria-busy={loading}>
      <AppHeader onLogout={onLogout} userName={currentUser?.username} title="角色权限" />

      <div className="mt-[20px] mb-[16px] flex items-center justify-end gap-[12px]">
        <UIButton
          variant="outline"
          onClick={() => void load()}
          disabled={loading}
          className="h-[34px] gap-[4px] rounded-[10px] border-[0.5px] border-[#e3e7f1] bg-white px-[20px] text-[12px] font-normal text-[#757f9c] hover:border-[#cbd3e6] hover:bg-white hover:text-[#18181a]"
        >
          <IconRefresh className={cn('size-[14px]', loading && 'animate-spin')} />
          刷新
        </UIButton>
        <UIButton
          onClick={openCreate}
          className="h-[34px] gap-[4px] rounded-[10px] bg-[#18181a] px-[20px] text-[12px] font-normal text-white hover:bg-[#303030]"
        >
          <IconAdd className="size-[14px]" />
          新建角色
        </UIButton>
      </div>

      <div className="flex flex-col gap-[24px] rounded-[20px_20px_0_0] bg-white p-[18px_18px_24px_18px] shadow-[0_-4px_16px_0_rgba(0,0,0,0.05)]">
        <div className="flex flex-col gap-[18px]">
          <div className="flex items-center gap-[6px] px-[12px] text-[#757f9c]">
            <IconRoles className="size-[14px] shrink-0" />
            <span className="text-[14px] font-normal leading-none">角色列表</span>
          </div>

          <label className="flex h-[34px] w-[300px] items-center gap-[8px] overflow-hidden rounded-[10px] border-[0.5px] border-[#e3e7f1] bg-white px-[12px] transition-colors focus-within:border-[#18181a] max-[900px]:w-full">
            <IconSearch className="size-[14px] shrink-0 text-[#858b9c]" />
            <input
              autoComplete="off"
              value={searchText}
              placeholder="搜索角色名称"
              onChange={(event) => setSearchText(event.target.value)}
              className="h-full min-w-0 flex-1 bg-transparent text-[12px] text-[#17191f] outline-none placeholder:text-[#c0c6d4]"
            />
            {searchText && (
              <button
                type="button"
                aria-label="清除搜索"
                onClick={() => setSearchText('')}
                className="grid size-[16px] shrink-0 place-items-center text-[#c0c6d4] hover:text-[#858b9c]"
              >
                <IconClear className="size-[14px]" />
              </button>
            )}
          </label>

          <div className="grid gap-[10px] md:hidden">
            {filteredRows.length ? (
              pagination.pagedItems.map(renderMobileCard)
            ) : (
              <div className="py-[40px] text-center text-[13px] text-[#858b9c]">暂无角色</div>
            )}
          </div>

          <div className="hidden md:block">
            <DataTable
              aria-label="角色列表"
              columns={columns}
              data={pagination.pagedItems}
              rowKey={(row) => row.id}
              loading={loading}
              emptyText="暂无角色"
            />
          </div>

          {filteredRows.length > 0 && (
            <Paginator
              aria-label="角色分页"
              className="mt-0 mb-[6px]"
              page={pagination.page}
              pageCount={pagination.pageCount}
              onChange={pagination.setPage}
            />
          )}
        </div>
      </div>

      <RoleDialog
        open={createOpen}
        title="新建角色"
        loading={creating}
        submitText="创建"
        draft={draft}
        onDraftChange={setDraft}
        catalog={catalog}
        onClose={() => setCreateOpen(false)}
        onSubmit={() => void saveCreate()}
      />

      <RoleDialog
        open={Boolean(editing)}
        title={editing ? `编辑角色：${editing.display_name}` : '编辑角色'}
        loading={saving}
        submitText="保存"
        draft={draft}
        onDraftChange={setDraft}
        catalog={catalog}
        onClose={() => setEditing(null)}
        onSubmit={() => void saveEdit()}
      />

      <ConfirmDialog
        open={Boolean(deleteTarget)}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
        loading={deleting}
        title={deleteTarget ? `删除角色「${deleteTarget.display_name}」？` : ''}
        description="删除前请先将该角色名下的账号改派到其他角色。"
        onConfirm={() => void confirmDelete()}
      />
    </div>
  );
}

function RoleDialog({
  open,
  title,
  loading,
  submitText,
  draft,
  onDraftChange,
  catalog,
  onClose,
  onSubmit,
}: {
  open: boolean;
  title: string;
  loading: boolean;
  submitText: string;
  draft: RoleDraft;
  onDraftChange: (next: RoleDraft) => void;
  catalog: PermissionDef[];
  onClose: () => void;
  onSubmit: () => void;
}) {
  const groups = useMemo(() => {
    const order: string[] = [];
    const byGroup = new Map<string, PermissionDef[]>();
    catalog.forEach((item) => {
      if (!byGroup.has(item.group)) {
        byGroup.set(item.group, []);
        order.push(item.group);
      }
      byGroup.get(item.group)!.push(item);
    });
    return order.map((group) => ({ group, items: byGroup.get(group)! }));
  }, [catalog]);

  function togglePermission(key: string) {
    const selected = new Set(draft.permissions);
    if (selected.has(key)) selected.delete(key);
    else selected.add(key);
    onDraftChange({
      ...draft,
      permissions: catalog.filter((item) => selected.has(item.key)).map((item) => item.key),
    });
  }

  return (
    <Dialog open={open} onOpenChange={(next) => !next && onClose()}>
      <DialogContent
        aria-describedby={undefined}
        className="flex w-[calc(100%-2rem)] flex-col gap-[16px] overflow-hidden rounded-[14px] px-[20px] py-[16px] sm:max-w-[520px]"
      >
        <div className="flex items-center gap-[6px] px-[12px] text-[#757f9c]">
          <IconRoles className="size-[14px] shrink-0" />
          <DialogTitle className="text-[14px] font-normal leading-none text-[#757f9c]">
            {title}
          </DialogTitle>
        </div>

        <div className="flex max-h-[60vh] flex-col gap-[14px] overflow-y-auto px-[12px]">
          <LabeledField label="角色名称">
            <Input
              value={draft.displayName}
              placeholder="例如 客服主管"
              maxLength={40}
              onChange={(event) => onDraftChange({ ...draft, displayName: event.target.value })}
            />
          </LabeledField>
          <LabeledField label="描述">
            <Textarea
              value={draft.description}
              placeholder="选填，说明该角色的职责范围"
              maxLength={200}
              className="min-h-[64px] resize-y"
              onChange={(event) => onDraftChange({ ...draft, description: event.target.value })}
            />
          </LabeledField>
          <div className="flex flex-col gap-[10px]">
            <span className="text-[12px] font-medium text-[#464c5e]">权限配置</span>
            {groups.map(({ group, items }) => (
              <fieldset
                key={group}
                className="flex flex-col gap-[6px] rounded-[10px] border-[0.5px] border-[#eef0f4] p-[10px]"
              >
                <legend className="px-[6px] text-[11px] text-[#858b9c]">{group}</legend>
                {items.map((item) => {
                  const checked = draft.permissions.includes(item.key);
                  return (
                    <label
                      key={item.key}
                      className="flex cursor-pointer items-start gap-[8px] rounded-[8px] px-[6px] py-[4px] transition-colors hover:bg-[#f6f6f6]"
                    >
                      <Checkbox
                        checked={checked}
                        onCheckedChange={() => togglePermission(item.key)}
                        className="mt-[2px]"
                      />
                      <span className="flex min-w-0 flex-col gap-[2px]">
                        <span className="text-[12px] leading-none text-[#18181a]">{item.name}</span>
                        <span className="text-[11px] leading-[16px] text-[#858b9c]">
                          {item.description}
                        </span>
                      </span>
                    </label>
                  );
                })}
              </fieldset>
            ))}
          </div>
        </div>

        <div className="flex items-center justify-end gap-[8px] px-[12px]">
          <UIButton
            variant="outline"
            disabled={loading}
            onClick={onClose}
            className="h-[32px] w-[80px] rounded-[10px] border-[#e3e7f1] bg-white px-[12px] text-[14px] font-normal text-[#464c5e] hover:border-[#e3e7f1] hover:bg-[#f6f6f6] hover:text-[#18181a]"
          >
            取消
          </UIButton>
          <UIButton
            disabled={loading}
            onClick={onSubmit}
            className="h-[32px] w-[80px] rounded-[10px] bg-[#18181a] px-[12px] text-[14px] font-normal text-white hover:bg-[#303030]"
          >
            {submitText}
          </UIButton>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function LabeledField({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="flex flex-col gap-[6px]">
      <span className="text-[12px] font-medium text-[#464c5e]">{label}</span>
      {children}
    </label>
  );
}
