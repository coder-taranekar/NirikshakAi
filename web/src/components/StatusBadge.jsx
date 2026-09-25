import { getStatusConfig } from '../utils/formatters';

export default function StatusBadge({ status }) {
  const config = getStatusConfig(status);
  return <span className={config.class}>{config.label}</span>;
}
