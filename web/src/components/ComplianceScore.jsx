import { useMemo } from 'react';

export default function ComplianceScore({ score, size = 120 }) {
  const radius = (size - 12) / 2;
  const circumference = 2 * Math.PI * radius;
  const safeScore = score ?? 0;
  const offset = circumference - (safeScore / 100) * circumference;

  const color = useMemo(() => {
    if (safeScore >= 90) return { stroke: '#10b981', glow: 'rgba(16,185,129,0.3)', text: 'text-success' };
    if (safeScore >= 70) return { stroke: '#f59e0b', glow: 'rgba(245,158,11,0.3)', text: 'text-warning' };
    return { stroke: '#f43f5e', glow: 'rgba(244,63,94,0.3)', text: 'text-danger' };
  }, [safeScore]);

  const label = useMemo(() => {
    if (score == null) return 'N/A';
    if (safeScore >= 90) return 'Compliant';
    if (safeScore >= 70) return 'Partial';
    if (safeScore >= 50) return 'Non-Compliant';
    return 'Severe';
  }, [score, safeScore]);

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="transform -rotate-90">
          <circle cx={size/2} cy={size/2} r={radius} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="6" />
          <circle
            cx={size/2} cy={size/2} r={radius} fill="none"
            stroke={color.stroke}
            strokeWidth="6"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            className="transition-all duration-1000 ease-out"
            style={{ filter: `drop-shadow(0 0 6px ${color.glow})` }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={`text-2xl font-bold ${color.text}`}>{score != null ? Math.round(score) : '—'}</span>
          <span className="text-[10px] text-white/30 font-medium uppercase tracking-wider">{label}</span>
        </div>
      </div>
    </div>
  );
}
