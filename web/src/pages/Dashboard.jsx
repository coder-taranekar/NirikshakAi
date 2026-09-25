import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ClipboardText, CheckCircle, Warning, Factory, TrendUp, Eye } from '@phosphor-icons/react';
import StatCard from '../components/StatCard';
import StatusBadge from '../components/StatusBadge';
import TrendChart from '../components/charts/TrendChart';
import ViolationBar from '../components/charts/ViolationBar';
import ComplianceDonut from '../components/charts/ComplianceDonut';
import client from '../api/client';
import { formatDate, formatScore, getScoreColor } from '../utils/formatters';

// Demo data for when backend isn't connected
const DEMO = {
  stats: { total: 1247, compliant: 892, violations: 355, manufacturers: 184 },
  trend: [
    { name: 'Jan', value: 78 }, { name: 'Feb', value: 72 }, { name: 'Mar', value: 80 },
    { name: 'Apr', value: 85 }, { name: 'May', value: 79 }, { name: 'Jun', value: 88 },
    { name: 'Jul', value: 91 }, { name: 'Aug', value: 86 }, { name: 'Sep', value: 90 },
  ],
  violations: [
    { name: 'MRP Format', count: 142 }, { name: 'Net Qty', count: 98 }, { name: 'Manufacturer', count: 76 },
    { name: 'Font Size', count: 65 }, { name: 'Consumer Care', count: 54 }, { name: 'Date', count: 43 },
    { name: 'Pack Size', count: 31 }, { name: 'Sticker Fraud', count: 12 },
  ],
  donut: [
    { name: 'Compliant', value: 892 }, { name: 'Partial', value: 198 },
    { name: 'Non-Compliant', value: 127 }, { name: 'Pending', value: 30 },
  ],
  recent: [
    { id: '1', product_name: 'Parle-G Gold Biscuits', score: 94, status: 'compliant', state: 'Maharashtra', created_at: '2026-09-15T10:30:00Z' },
    { id: '2', product_name: 'Bisleri Mineral Water 1L', score: 45, status: 'non_compliant', state: 'Delhi', created_at: '2026-09-15T09:15:00Z' },
    { id: '3', product_name: 'Amul Butter 500g', score: 88, status: 'compliant', state: 'Gujarat', created_at: '2026-09-14T16:45:00Z' },
    { id: '4', product_name: 'Tata Salt 1kg', score: 72, status: 'non_compliant', state: 'Tamil Nadu', created_at: '2026-09-14T14:20:00Z' },
    { id: '5', product_name: 'Maggi Noodles 70g', score: 96, status: 'compliant', state: 'Karnataka', created_at: '2026-09-14T11:00:00Z' },
  ],
  offenders: [
    { name: 'XYZ Foods Pvt Ltd', violations: 23, states: 4 },
    { name: 'QuickPack Industries', violations: 18, states: 3 },
    { name: 'Budget Beverages', violations: 14, states: 2 },
    { name: 'Metro Packagers', violations: 11, states: 5 },
  ],
};

export default function Dashboard() {
  const [data, setData] = useState(DEMO);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchDashboard = async () => {
      try {
        const [summary, trends, violations] = await Promise.all([
          client.get('/dashboard/summary'),
          client.get('/dashboard/trends'),
          client.get('/dashboard/violations'),
        ]);
        setData({ ...DEMO, ...summary.data, trend: trends.data, violations: violations.data });
      } catch {
        // Use demo data silently
      }
    };
    fetchDashboard();
  }, []);

  return (
    <div className="page-container">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Dashboard</h1>
          <p className="text-sm text-white/30 mt-1">Legal Metrology Compliance Overview</p>
        </div>
        <div className="text-right">
          <p className="text-xs text-white/20">Last updated</p>
          <p className="text-sm text-white/40 font-medium">{new Date().toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })}</p>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        <StatCard icon={ClipboardText} label="Total Inspections" value={data.stats.total.toLocaleString()} trend={12} trendLabel="vs last month" color="accent" />
        <StatCard icon={CheckCircle} label="Compliant" value={data.stats.compliant.toLocaleString()} trend={8} trendLabel={`${Math.round((data.stats.compliant/data.stats.total)*100)}% rate`} color="success" />
        <StatCard icon={Warning} label="Violations Found" value={data.stats.violations.toLocaleString()} trend={-5} trendLabel="vs last month" color="danger" />
        <StatCard icon={Factory} label="Manufacturers Tracked" value={data.stats.manufacturers.toLocaleString()} trend={3} trendLabel="cross-state registry" color="warning" />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <TrendChart data={data.trend} title="Compliance Rate Trend" color="#10b981" />
        <ViolationBar data={data.violations} title="Violations by Declaration Type" />
      </div>

      {/* Bottom Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Compliance Distribution */}
        <ComplianceDonut data={data.donut} />

        {/* Recent Inspections */}
        <div className="glass-card p-5 lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h3 className="section-title">Recent Inspections</h3>
            <button onClick={() => navigate('/inspections')} className="text-xs text-accent hover:text-accent-light transition-colors font-medium">View All →</button>
          </div>
          <div className="space-y-2">
            {data.recent.map((item) => (
              <div key={item.id} onClick={() => navigate(`/inspections/${item.id}`)} className="flex items-center gap-4 p-3 rounded-xl hover:bg-white/[0.03] transition-all duration-200 cursor-pointer group">
                <div className={`w-10 h-10 rounded-xl flex items-center justify-center text-sm font-bold ${item.score >= 90 ? 'bg-success/15 text-success' : item.score >= 70 ? 'bg-warning/15 text-warning' : 'bg-danger/15 text-danger'}`}>
                  {formatScore(item.score)}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-white/80 truncate">{item.product_name}</p>
                  <p className="text-xs text-white/30">{item.state} · {formatDate(item.created_at)}</p>
                </div>
                <StatusBadge status={item.status} />
                <Eye size={16} className="text-white/10 group-hover:text-white/30 transition-colors" />
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Top Offenders */}
      <div className="glass-card p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="section-title">Top Offending Manufacturers</h3>
          <button onClick={() => navigate('/manufacturers')} className="text-xs text-accent hover:text-accent-light transition-colors font-medium">View Registry →</button>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
          {data.offenders.map((m, i) => (
            <div key={i} className="p-4 rounded-xl bg-danger/5 border border-danger/10 hover:border-danger/20 transition-all duration-200">
              <div className="flex items-center gap-2 mb-2">
                <span className="w-6 h-6 rounded-lg bg-danger/15 text-danger text-xs font-bold flex items-center justify-center">#{i + 1}</span>
                <TrendUp size={14} className="text-danger/60" />
              </div>
              <p className="text-sm font-medium text-white/80 mb-1 truncate">{m.name}</p>
              <div className="flex items-center gap-3">
                <span className="text-xs text-danger-light font-semibold">{m.violations} violations</span>
                <span className="text-[10px] text-white/25">{m.states} states</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
