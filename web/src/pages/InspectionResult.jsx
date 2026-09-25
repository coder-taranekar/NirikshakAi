import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, DownloadSimple, CircleNotch, Scales, MapPin, Calendar, Barcode } from '@phosphor-icons/react';
import ComplianceScore from '../components/ComplianceScore';
import DeclarationChecklist from '../components/DeclarationChecklist';
import ViolationCard from '../components/ViolationCard';
import AnnotatedImage from '../components/AnnotatedImage';
import StatusBadge from '../components/StatusBadge';
import client from '../api/client';
import { formatDateTime, formatCurrency } from '../utils/formatters';

const DEMO_RESULT = {
  id: 'demo-1',
  source: 'upload',
  state: 'Maharashtra',
  district: 'Mumbai Suburban',
  score: 45,
  status: 'non_compliant',
  hard_fail_triggered: true,
  penalty_tier: 'first',
  estimated_penalty_min: 10000,
  estimated_penalty_max: 25000,
  created_at: new Date().toISOString(),
  compliance_result: {
    overall_score: 45,
    status: 'non_compliant',
    hard_fail_triggered: true,
    declarations: [
      { field: 'manufacturer_name', status: 'pass', hard_fail: false, rule_reference: 'Rule 6(a)', extracted_value: 'XYZ Foods Pvt Ltd, Mumbai', issue: null },
      { field: 'mrp', status: 'fail', hard_fail: true, rule_reference: 'Rule 6(c)', extracted_value: 'MRP 45', expected_format: 'MRP ₹XX.XX Inclusive of all taxes', issue: 'Missing currency symbol and "Inclusive of all taxes" text', explanation: 'Every packaged product must show MRP as: "MRP ₹XX.XX Inclusive of all taxes". The currency symbol (₹/Rs./INR) and the phrase "Inclusive of all taxes" are mandatory.' },
      { field: 'net_quantity', status: 'pass', hard_fail: false, rule_reference: 'Rule 6(e)', extracted_value: '500g', issue: null },
      { field: 'manufacture_date', status: 'fail', hard_fail: true, rule_reference: 'Rule 6(d)', extracted_value: null, issue: 'Month and year of manufacture not found on label', explanation: 'The month and year of manufacture, packing, or import must be printed on the package.' },
      { field: 'consumer_care', status: 'warning', hard_fail: false, rule_reference: 'Rule 6(f)', extracted_value: 'Contact: 1800-xxx-xxxx', issue: 'Phone found but email and full address missing' },
      { field: 'generic_name', status: 'pass', hard_fail: false, rule_reference: 'Rule 6(b)', extracted_value: 'Glucose Biscuits', issue: null },
    ],
    advanced_checks: {
      font_size_violations: [{ field: 'net_quantity', measured_mm: 1.5, required_mm: 2, rule_reference: 'Rule 7(3)', issue: 'Font height 1.5mm is below required 2mm for 200-500g products' }],
      whitespace_violations: [],
      sticker_fraud_detected: false,
      pack_size_violation: false,
      multilingual_present: true,
    },
    penalty: {
      tier: 'first',
      applicable_section: 'Section 36(1), Legal Metrology Act 2009',
      estimated_range: '₹10,000 – ₹25,000',
      note: 'First recorded offence for this manufacturer',
    },
  },
};

export default function InspectionResult() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetch = async () => {
      try {
        const { data: res } = await client.get(`/inspections/${id}`);
        setData(res);
      } catch {
        setData(DEMO_RESULT);
      } finally {
        setLoading(false);
      }
    };
    fetch();
  }, [id]);

  const handleDownload = async (format) => {
    try {
      const res = await client.get(`/inspections/${id}/report?format=${format}`, { responseType: 'blob' });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement('a');
      a.href = url;
      a.download = `inspection-${id}.${format}`;
      a.click();
    } catch { /* silently fail */ }
  };

  if (loading) return (
    <div className="page-container flex items-center justify-center min-h-[60vh]">
      <CircleNotch size={40} className="text-accent animate-spin" />
    </div>
  );

  const cr = data?.compliance_result || {};
  const declarations = cr.declarations || [];
  const violations = declarations.filter((d) => d.status === 'fail');
  const penalty = cr.penalty;
  const advanced = cr.advanced_checks || {};

  return (
    <div className="page-container max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div className="flex items-center gap-4">
          <button onClick={() => navigate(-1)} className="p-2 rounded-xl text-white/30 hover:text-white/60 hover:bg-white/[0.04] transition-all">
            <ArrowLeft size={20} />
          </button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-xl font-bold text-white">Inspection Result</h1>
              <StatusBadge status={data?.status} />
            </div>
            <div className="flex items-center gap-4 mt-1 text-xs text-white/30">
              {data?.state && <span className="flex items-center gap-1"><MapPin size={12} />{data.state}{data.district ? `, ${data.district}` : ''}</span>}
              <span className="flex items-center gap-1"><Calendar size={12} />{formatDateTime(data?.created_at)}</span>
              <span className="flex items-center gap-1"><Barcode size={12} />Source: {data?.source}</span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {['pdf', 'xlsx', 'docx'].map((fmt) => (
            <button key={fmt} onClick={() => handleDownload(fmt)} className="btn-secondary flex items-center gap-1.5 text-xs py-2 px-3">
              <DownloadSimple size={14} />
              {fmt.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column — Score + Checklist */}
        <div className="space-y-6">
          {/* Score */}
          <div className="glass-card p-6 flex flex-col items-center">
            <ComplianceScore score={data?.score} size={140} />
            {data?.hard_fail_triggered && (
              <div className="mt-4 w-full p-3 rounded-xl bg-danger/10 border border-danger/20 text-center">
                <p className="text-xs text-danger-light font-semibold">⚠ Hard Fail Triggered</p>
                <p className="text-[10px] text-white/30 mt-0.5">Automatic non-compliance regardless of score</p>
              </div>
            )}
          </div>

          {/* Penalty */}
          {penalty && (
            <div className="glass-card p-5 border-warning/10">
              <div className="flex items-center gap-2 mb-3">
                <Scales size={18} weight="duotone" className="text-warning" />
                <h3 className="text-sm font-semibold text-white/80">Penalty Assessment</h3>
              </div>
              <div className="space-y-2">
                <div className="flex justify-between text-xs"><span className="text-white/40">Tier</span><span className="text-warning-light font-semibold capitalize">{penalty.tier}</span></div>
                <div className="flex justify-between text-xs"><span className="text-white/40">Section</span><span className="text-white/60">{penalty.applicable_section}</span></div>
                <div className="flex justify-between text-xs"><span className="text-white/40">Estimated</span><span className="text-warning-light font-semibold">{penalty.estimated_range}</span></div>
                {penalty.note && <p className="text-[10px] text-white/25 pt-1 border-t border-white/[0.04]">{penalty.note}</p>}
              </div>
            </div>
          )}
        </div>

        {/* Center — Declarations + Violations */}
        <div className="space-y-6">
          <div className="glass-card p-5">
            <h3 className="section-title mb-4">Declaration Checklist</h3>
            <DeclarationChecklist declarations={declarations} />
          </div>

          {violations.length > 0 && (
            <div>
              <h3 className="section-title mb-3">Violations ({violations.length})</h3>
              <div className="space-y-3">
                {violations.map((v, i) => <ViolationCard key={i} violation={v} />)}
              </div>
            </div>
          )}

          {(advanced.font_size_violations?.length > 0) && (
            <div className="glass-card p-5">
              <h3 className="text-sm font-semibold text-white/80 mb-3">Advanced Checks</h3>
              <div className="space-y-2">
                {advanced.font_size_violations.map((v, i) => (
                  <div key={i} className="p-3 rounded-xl bg-warning/5 border border-warning/10 text-xs">
                    <p className="text-warning-light font-medium">{v.field}: {v.measured_mm}mm (required: {v.required_mm}mm)</p>
                    <p className="text-white/30 mt-0.5">{v.rule_reference}</p>
                  </div>
                ))}
                {advanced.sticker_fraud_detected && <div className="p-3 rounded-xl bg-danger/10 border border-danger/20 text-xs text-danger-light font-medium">⚠ MRP Sticker Fraud Detected — Multiple MRP values found</div>}
                {advanced.multilingual_present && <div className="p-2 rounded-lg bg-success/5 border border-success/10 text-xs text-success/80">✓ Multilingual text detected</div>}
              </div>
            </div>
          )}
        </div>

        {/* Right — Annotated Image */}
        <div>
          <h3 className="section-title mb-3">Annotated Label</h3>
          <AnnotatedImage src={data?.annotated_image_url} />
        </div>
      </div>
    </div>
  );
}
