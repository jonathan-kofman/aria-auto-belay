export const ARIA_SERVICE_UUID = '12345678-1234-1234-1234-123456789abc';

export const ARIA_CHARS = {
  STATE: '12345678-1234-1234-1234-000000000001',
  TENSION: '12345678-1234-1234-1234-000000000002',
  ENCODER: '12345678-1234-1234-1234-000000000003',
  ALERT: '12345678-1234-1234-1234-000000000004',
  COMMAND: '12345678-1234-1234-1234-000000000005',
  PROFILE: '12345678-1234-1234-1234-000000000006',
  SESSION: '12345678-1234-1234-1234-000000000007',
} as const;

export function parseARIAPacket(raw: string): { type: string; field: string; value: string } {
  const [type = '', field = '', value = ''] = raw.split(':');
  return { type, field, value };
}
