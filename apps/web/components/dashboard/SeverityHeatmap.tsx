interface SeverityHeatmapProps {
  critical: number;
  high: number;
  medium: number;
  low: number;
  info: number;
}

const severityConfig = [
  { key: 'critical', label: 'Critical', color: 'bg-red-600',    textColor: 'text-red-400' },
  { key: 'high',     label: 'High',     color: 'bg-orange-500', textColor: 'text-orange-400' },
  { key: 'medium',   label: 'Medium',   color: 'bg-yellow-500', textColor: 'text-yellow-400' },
  { key: 'low',      label: 'Low',      color: 'bg-blue-500',   textColor: 'text-blue-400' },
  { key: 'info',     label: 'Info',     color: 'bg-gray-500',   textColor: 'text-gray-400' },
] as const;

export function SeverityHeatmap({ critical, high, medium, low, info }: SeverityHeatmapProps) {
  const counts: Record<string, number> = { critical, high, medium, low, info };
  const total = critical + high + medium + low + info;

  return (
    <div className="bg-card-bg border border-card-border rounded-lg p-6">
      <h3 className="text-lg font-mono font-bold text-foreground mb-4">Severity Breakdown</h3>

      {total === 0 ? (
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <p className="text-gray-400 font-mono text-sm">No findings yet.</p>
          <p className="text-gray-500 font-mono text-xs mt-1">Run a scan to see severity data.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {severityConfig.map(({ key, label, color, textColor }) => {
            const count = counts[key] ?? 0;
            const pct = total > 0 ? Math.round((count / total) * 100) : 0;

            return (
              <div key={key} className="flex items-center gap-3">
                <span className={`font-mono text-xs w-16 text-right ${textColor}`}>{label}</span>
                <div className="flex-1 bg-background rounded-full h-4 overflow-hidden border border-card-border">
                  <div
                    className={`h-full ${color} rounded-full transition-all duration-500`}
                    style={{ width: `${pct}%` }}
                  />
                </div>
                <span className="font-mono text-xs text-gray-400 w-12 text-right">{count}</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
