import { cn } from '@/lib/utils';
import { LucideIcon } from 'lucide-react';

interface MetricCardProps {
  title: string;
  value: string | number;
  icon: LucideIcon;
  subtext?: string;
  color?: 'green' | 'red' | 'yellow';
}

export function MetricCard({ title, value, icon: Icon, subtext, color = 'green' }: MetricCardProps) {
  const colorClasses = {
    green: 'text-neon-green border-neon-green',
    red: 'text-neon-red border-neon-red',
    yellow: 'text-neon-yellow border-neon-yellow',
  };

  return (
    <div className="bg-card-bg border border-card-border p-6 rounded-lg flex flex-col hover:border-neon-green transition-colors group">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-mono text-gray-400 group-hover:text-gray-300 transition-colors">{title}</h3>
        <Icon className={cn("w-5 h-5", colorClasses[color].split(' ')[0])} />
      </div>
      <div className="flex items-baseline gap-2">
        <span className="text-3xl font-mono font-bold text-foreground">{value}</span>
        {subtext && <span className="text-xs font-mono text-gray-500">{subtext}</span>}
      </div>
    </div>
  );
}
