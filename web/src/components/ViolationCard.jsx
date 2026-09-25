import { Warning, Scales } from '@phosphor-icons/react';

export default function ViolationCard({ violation }) {
  const severityColors = {
    high: 'border-danger/20 bg-danger/5',
    medium: 'border-warning/20 bg-warning/5',
    low: 'border-accent/20 bg-accent/5',
  };
  const severity = violation.hard_fail ? 'high' : violation.weight >= 4 ? 'medium' : 'low';

  return (
    <div className={`p-4 rounded-xl border ${severityColors[severity]} animate-slide-up`}>
      <div className="flex items-start gap-3">
        <Warning size={20} weight="duotone" className={severity === 'high' ? 'text-danger' : severity === 'medium' ? 'text-warning' : 'text-accent'} />
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <h4 className="text-sm font-semibold text-white/90 capitalize">{violation.field?.replace(/_/g, ' ')}</h4>
            <span className="text-[10px] font-mono text-white/25 bg-white/[0.05] px-1.5 py-0.5 rounded">{violation.rule_reference}</span>
          </div>
          <p className="text-xs text-white/50 leading-relaxed mb-2">{violation.issue}</p>
          {violation.explanation && (
            <div className="flex items-start gap-2 p-2.5 rounded-lg bg-white/[0.03] border border-white/[0.04]">
              <Scales size={14} className="text-accent/60 mt-0.5 flex-shrink-0" />
              <p className="text-[11px] text-white/35 leading-relaxed">{violation.explanation}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
