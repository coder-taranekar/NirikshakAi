import { CheckCircle, XCircle, Warning } from '@phosphor-icons/react';

export default function DeclarationChecklist({ declarations = [] }) {
  if (!declarations.length) return <p className="text-white/30 text-sm">No declaration data available.</p>;

  return (
    <div className="space-y-2">
      {declarations.map((d, i) => {
        const isPassed = d.status === 'pass';
        const isWarning = d.status === 'warning';
        return (
          <div key={i} className={`flex items-start gap-3 p-3 rounded-xl border transition-all duration-200 ${
            isPassed ? 'bg-success/5 border-success/10' : isWarning ? 'bg-warning/5 border-warning/10' : 'bg-danger/5 border-danger/10'
          }`}>
            <div className="mt-0.5">
              {isPassed ? <CheckCircle size={18} weight="duotone" className="text-success" /> :
               isWarning ? <Warning size={18} weight="duotone" className="text-warning" /> :
               <XCircle size={18} weight="duotone" className="text-danger" />}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-0.5">
                <span className="text-sm font-medium text-white/80 capitalize">{d.field?.replace(/_/g, ' ')}</span>
                {d.rule_reference && <span className="text-[10px] text-white/25 font-mono">{d.rule_reference}</span>}
              </div>
              {d.issue && <p className="text-xs text-white/40 leading-relaxed">{d.issue}</p>}
              {d.extracted_value && <p className="text-xs text-white/20 mt-1 font-mono">Found: "{d.extracted_value}"</p>}
            </div>
            {d.hard_fail && <span className="badge-danger text-[10px]">Hard Fail</span>}
          </div>
        );
      })}
    </div>
  );
}
