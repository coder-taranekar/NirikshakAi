import { ArrowUp, ArrowDown } from '@phosphor-icons/react';

export default function StatCard({ icon: Icon, label, value, trend, trendLabel, color = 'accent' }) {
  const colorMap = {
    accent: 'from-accent/20 to-accent/5 border-accent/20 text-accent-light',
    success: 'from-success/20 to-success/5 border-success/20 text-success-light',
    danger: 'from-danger/20 to-danger/5 border-danger/20 text-danger-light',
    warning: 'from-warning/20 to-warning/5 border-warning/20 text-warning-light',
  };
  const isPositive = trend > 0;

  return (
    <div className={`glass-card p-5 bg-gradient-to-br ${colorMap[color]} animate-slide-up`}>
      <div className="flex items-start justify-between mb-3">
        <div className={`p-2.5 rounded-xl bg-${color}/10`}>
          <Icon size={22} weight="duotone" className={`text-${color}-light`} />
        </div>
        {trend != null && (
          <div className={`flex items-center gap-1 text-xs font-semibold ${isPositive ? 'text-success' : 'text-danger'}`}>
            {isPositive ? <ArrowUp size={12} weight="bold" /> : <ArrowDown size={12} weight="bold" />}
            {Math.abs(trend)}%
          </div>
        )}
      </div>
      <p className="text-2xl font-bold text-white mb-1">{value}</p>
      <p className="text-xs text-white/40 font-medium">{label}</p>
      {trendLabel && <p className="text-[10px] text-white/25 mt-1">{trendLabel}</p>}
    </div>
  );
}
