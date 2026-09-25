export function formatDate(dateStr) {
  if (!dateStr) return '—';
  return new Date(dateStr).toLocaleDateString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric',
  });
}

export function formatDateTime(dateStr) {
  if (!dateStr) return '—';
  return new Date(dateStr).toLocaleString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

export function formatScore(score) {
  if (score == null) return '—';
  return Math.round(score);
}

export function getScoreColor(score) {
  if (score == null) return 'text-white/40';
  if (score >= 90) return 'text-success';
  if (score >= 70) return 'text-warning';
  return 'text-danger';
}

export function getScoreBg(score) {
  if (score == null) return 'bg-white/10';
  if (score >= 90) return 'bg-success/15';
  if (score >= 70) return 'bg-warning/15';
  return 'bg-danger/15';
}

export function getStatusConfig(status) {
  const map = {
    compliant: { label: 'Compliant', class: 'badge-success' },
    non_compliant: { label: 'Non-Compliant', class: 'badge-danger' },
    pending: { label: 'Pending', class: 'badge-warning' },
  };
  return map[status] || { label: status, class: 'badge-neutral' };
}

export function truncate(str, len = 40) {
  if (!str) return '—';
  return str.length > len ? str.slice(0, len) + '…' : str;
}

export function formatCurrency(amount) {
  if (amount == null) return '—';
  return `₹${Number(amount).toLocaleString('en-IN')}`;
}
