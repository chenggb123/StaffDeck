import { describe, expect, it } from 'vitest';

import {
  ENTERPRISE_PERMISSIONS,
  hasAnyEnterpriseManagementPermission,
  userHasPermission,
  type EnterpriseAuthUser,
} from './auth';

function user(role: string, permissions: string[] = []): EnterpriseAuthUser {
  return {
    id: 'user_test',
    tenant_id: 'tenant_demo',
    username: 'test',
    role,
    permissions,
  };
}

describe('auth permissions', () => {
  it('admin always has every permission', () => {
    const admin = user('admin', []);

    expect(hasAnyEnterpriseManagementPermission(admin)).toBe(true);
    expect(userHasPermission(admin, ENTERPRISE_PERMISSIONS.roles)).toBe(true);
  });

  it('member without permissions has no management access', () => {
    const member = user('member', []);

    expect(hasAnyEnterpriseManagementPermission(member)).toBe(false);
    expect(userHasPermission(member, ENTERPRISE_PERMISSIONS.accounts)).toBe(false);
  });

  it('custom role management access follows configured permissions', () => {
    const auditor = user('auditor', [ENTERPRISE_PERMISSIONS.oversight]);

    expect(hasAnyEnterpriseManagementPermission(auditor)).toBe(true);
    expect(userHasPermission(auditor, ENTERPRISE_PERMISSIONS.oversight)).toBe(true);
    expect(userHasPermission(auditor, ENTERPRISE_PERMISSIONS.accounts)).toBe(false);
  });
});
