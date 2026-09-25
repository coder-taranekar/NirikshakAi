import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { MagnifyingGlass, Funnel, Eye, CaretLeft, CaretRight } from '@phosphor-icons/react';
import StatusBadge from '../components/StatusBadge';
import client from '../api/client';
import { formatDate, formatScore, getScoreColor } from '../utils/formatters';

const DEMO_INSPECTIONS = Array.from({ length: 15 }, (_, i) => ({
  id: `demo-${i + 1}`,
  source: i % 3 === 0 ? 'url' : 'upload',
  state: ['Maharashtra', 'Delhi', 'Gujarat', 'Tamil Nadu', 'Karnataka'][i % 5],
  score: Math.round(30 + Math.random() * 70),
  status: i % 3 === 0 ? 'non_compliant' : i % 5 === 0 ? 'pending' : 'compliant',
  hard_fail_triggered: i % 4 === 0,
  penalty_tier: i % 3 === 0 ? 'first' : null,
  created_at: new Date(Date.now() - i * 86400000).toISOString(),
  product_name: ['Parle-G Biscuits', 'Bisleri Water 1L', 'Amul Butter', 'Tata Salt', 'Maggi Noodles', 'Haldiram Namkeen', 'Britannia Bread', 'Dabur Honey', 'Colgate Toothpaste', 'Surf Excel', 'Vim Liquid', 'Dettol Soap', 'Clinic Plus', 'Head & Shoulders', 'Lifebuoy'][i % 15],
}));

export default function InspectionHistory() {
  const navigate = useNavigate();
  const [inspections, setInspections] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const pageSize = 10;

  useEffect(() => {
    const fetch = async () => {
      setLoading(true);
      try {
        const params = { page, page_size: pageSize };
        if (statusFilter) params.status = statusFilter;
        if (search) params.search = search;
        const { data } = await client.get('/inspections', { params });
        setInspections(data.items);
        setTotal(data.total);
      } catch {
        setInspections(DEMO_INSPECTIONS);
        setTotal(DEMO_INSPECTIONS.length);
      } finally {
        setLoading(false);
      }
    };
    fetch();
  }, [page, statusFilter, search]);

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="page-container">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Inspections</h1>
          <p className="text-sm text-white/30 mt-1">{total} records</p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="relative flex-1 max-w-sm">
          <MagnifyingGlass size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-white/20" />
          <input value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }} placeholder="Search inspections..." className="glass-input w-full pl-10 py-2.5 text-sm" />
        </div>
        <div className="flex items-center gap-1.5">
          <Funnel size={14} className="text-white/20" />
          {['', 'compliant', 'non_compliant', 'pending'].map((s) => (
            <button key={s} onClick={() => { setStatusFilter(s); setPage(1); }}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${statusFilter === s ? 'bg-accent/15 text-accent-light border border-accent/20' : 'text-white/30 hover:text-white/50 border border-transparent'}`}>
              {s ? s.replace('_', '-') : 'All'}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="glass-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-white/[0.06]">
                {['Product', 'State', 'Score', 'Status', 'Source', 'Date', ''].map((h) => (
                  <th key={h} className="text-left text-[11px] text-white/30 font-semibold uppercase tracking-wider px-4 py-3">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {inspections.map((item) => (
                <tr key={item.id} onClick={() => navigate(`/inspections/${item.id}`)} className="border-b border-white/[0.03] hover:bg-white/[0.02] transition-colors cursor-pointer group">
                  <td className="px-4 py-3">
                    <p className="text-sm font-medium text-white/80">{item.product_name || '—'}</p>
                  </td>
                  <td className="px-4 py-3 text-sm text-white/40">{item.state || '—'}</td>
                  <td className="px-4 py-3">
                    <span className={`text-sm font-bold ${getScoreColor(item.score)}`}>{formatScore(item.score)}</span>
                  </td>
                  <td className="px-4 py-3"><StatusBadge status={item.status} /></td>
                  <td className="px-4 py-3 text-xs text-white/30 capitalize">{item.source}</td>
                  <td className="px-4 py-3 text-xs text-white/30">{formatDate(item.created_at)}</td>
                  <td className="px-4 py-3">
                    <Eye size={16} className="text-white/10 group-hover:text-white/30 transition-colors" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-white/[0.06]">
            <p className="text-xs text-white/25">Page {page} of {totalPages}</p>
            <div className="flex items-center gap-1">
              <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page <= 1} className="p-1.5 rounded-lg text-white/30 hover:text-white/60 hover:bg-white/[0.04] disabled:opacity-30 transition-all"><CaretLeft size={16} /></button>
              <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page >= totalPages} className="p-1.5 rounded-lg text-white/30 hover:text-white/60 hover:bg-white/[0.04] disabled:opacity-30 transition-all"><CaretRight size={16} /></button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
