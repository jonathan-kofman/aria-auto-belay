export function formatTension(
  kn: number,
  unitSystem: 'metric' | 'imperial' = 'metric'
): string {
  if (unitSystem === 'imperial') {
    const lbf = kn * 224.809;
    return `${lbf.toFixed(0)} lbf`;
  }
  return `${kn.toFixed(1)} kN`;
}

export function formatHeight(
  meters: number,
  unitSystem: 'metric' | 'imperial' = 'metric'
): string {
  if (unitSystem === 'imperial') {
    const ft = meters * 3.28084;
    return `${ft.toFixed(1)} ft`;
  }
  return `${meters.toFixed(1)} m`;
}

export function formatDuration(seconds: number): string {
  if (seconds >= 3600) {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    return `${h}h ${m}m`;
  }
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}m ${s}s`;
}

export function formatDate(date: Date, locale?: string): string {
  return new Intl.DateTimeFormat(locale ?? undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date);
}
