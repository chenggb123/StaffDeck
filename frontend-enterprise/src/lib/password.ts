export function passwordComplexityError(password: string): string | null {
  const value = password.trim();
  if (value.length < 8) return '密码至少需要 8 个字符';
  if (value.length > 128) return '密码不能超过 128 个字符';
  if (!/[a-z]/.test(value)) return '密码需要包含小写字母';
  if (!/[A-Z]/.test(value)) return '密码需要包含大写字母';
  if (!/\d/.test(value)) return '密码需要包含数字';
  if (!/[^A-Za-z0-9]/.test(value)) return '密码需要包含特殊字符';
  return null;
}
