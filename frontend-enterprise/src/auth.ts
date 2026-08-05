export type EnterpriseAuthUser = {
  id: string;
  tenant_id: string;
  username: string;
  display_name?: string;
  role: string;
  role_display_name?: string;
  permissions: string[];
  avatar_url?: string;
};

export type EnterpriseAuthSession = {
  token: string;
  user: EnterpriseAuthUser;
};

export const ENTERPRISE_AUTH_STORAGE_KEY = 'ultrarag_auth';

export function getEnterpriseAuthSession(): EnterpriseAuthSession | null {
  return readStoredSession(ENTERPRISE_AUTH_STORAGE_KEY);
}

export function setEnterpriseAuthSession(session: EnterpriseAuthSession): void {
  try {
    window.localStorage.setItem(ENTERPRISE_AUTH_STORAGE_KEY, JSON.stringify(session));
  } catch {
    // 存储超限等异常(极端情况):降级为不带头像字段的最小会话再试一次
    try {
      const minimal: EnterpriseAuthSession = {
        ...session,
        user: { ...session.user, avatar_url: undefined },
      };
      window.localStorage.setItem(ENTERPRISE_AUTH_STORAGE_KEY, JSON.stringify(minimal));
    } catch {
      // 抛出真实原因,避免被登录流程误报为账号/密码错误
      throw new Error('浏览器存储空间不足，请清理站点数据后重试');
    }
  }
}

export function clearEnterpriseAuthSession(): void {
  window.localStorage.removeItem(ENTERPRISE_AUTH_STORAGE_KEY);
}

function readStoredSession(key: string): EnterpriseAuthSession | null {
  const raw = window.localStorage.getItem(key);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as EnterpriseAuthSession;
    if (!parsed.token || !parsed.user?.id) return null;
    return parsed;
  } catch {
    return null;
  }
}

export function isEnterpriseAdmin(user?: EnterpriseAuthUser | null): boolean {
  // 全局管理特权:内置管理员角色恒真,或角色配置了全局数字员工管理权限
  return userHasPermission(user, ENTERPRISE_PERMISSIONS.agentsGlobal);
}

// 严格身份判断:是否挂在内置管理员角色上(仅用于展示类文案,不做鉴权)
export function isAdminRole(user?: EnterpriseAuthUser | null): boolean {
  return user?.role === 'admin';
}

// 权限点常量与后端 PERMISSION_CATALOG 保持一致
export const ENTERPRISE_PERMISSIONS = {
  accounts: 'accounts.manage',
  roles: 'roles.manage',
  modelConfigs: 'model_configs.manage',
  channels: 'channels.manage',
  mcp: 'mcp.manage',
  systemSettings: 'system_settings.manage',
  agentsGlobal: 'agents.manage_global',
  scheduledTasks: 'scheduled_tasks.manage',
  chatOps: 'chat_ops.manage',
  oversight: 'oversight.view',
} as const;

export function userHasPermission(
  user: EnterpriseAuthUser | null | undefined,
  permission: string,
): boolean {
  if (!user) return false;
  // 内置管理员恒拥有全部权限(兼容旧会话缓存里没有 permissions 字段的情况)
  if (user.role === 'admin') return true;
  return Array.isArray(user.permissions) && user.permissions.includes(permission);
}

export function hasAnyEnterpriseManagementPermission(
  user: EnterpriseAuthUser | null | undefined,
): boolean {
  return Object.values(ENTERPRISE_PERMISSIONS).some((permission) =>
    userHasPermission(user, permission),
  );
}

export function isGalleryEmployee(agent?: { metadata?: Record<string, unknown> } | null): boolean {
  return agent?.metadata?.published_to_gallery === true;
}

export function isEmployeeOwnedBy(
  agent: { metadata?: Record<string, unknown> },
  user?: EnterpriseAuthUser | null,
): boolean {
  if (!user) return false;
  const metadata = agent.metadata || {};
  const ownerUserId = metadata.owner_user_id;
  return ownerUserId === user.id;
}
