import { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import {
  House, MagnifyingGlass, ClipboardText, Package, Factory,
  Users, SignOut, CaretLeft, CaretRight, ShieldCheck,
} from '@phosphor-icons/react';
import useAuthStore from '../store/authStore';

const navItems = [
  { to: '/', icon: House, label: 'Dashboard', adminOnly: true },
  { to: '/scan', icon: MagnifyingGlass, label: 'Scan Label', adminOnly: false },
  { to: '/inspections', icon: ClipboardText, label: 'Inspections', adminOnly: false },
  { to: '/products', icon: Package, label: 'Products', adminOnly: false },
  { to: '/manufacturers', icon: Factory, label: 'Manufacturers', adminOnly: false },
  { to: '/users', icon: Users, label: 'Users', adminOnly: true },
];

export default function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const isAdmin = user?.role === 'admin';

  const handleLogout = () => { logout(); navigate('/login'); };

  const filtered = navItems.filter((item) => !item.adminOnly || isAdmin);

  return (
    <aside className={`${collapsed ? 'w-[72px]' : 'w-64'} h-screen bg-surface-900/80 backdrop-blur-xl border-r border-white/[0.06] flex flex-col transition-all duration-300 ease-out fixed left-0 top-0 z-40`}>
      {/* Logo */}
      <div className="h-16 flex items-center gap-3 px-4 border-b border-white/[0.06]">
        <div className="w-9 h-9 rounded-xl bg-accent/20 flex items-center justify-center flex-shrink-0">
          <ShieldCheck size={22} weight="duotone" className="text-accent-light" />
        </div>
        {!collapsed && (
          <div className="animate-fade-in">
            <h1 className="text-sm font-bold tracking-wide text-white">NirikshakAI</h1>
            <p className="text-[10px] text-white/30 font-medium">Legal Metrology</p>
          </div>
        )}
      </div>

      {/* Nav */}
      <nav className="flex-1 py-4 px-2 space-y-1 overflow-y-auto">
        {filtered.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-200 group ${
                isActive
                  ? 'bg-accent/15 text-accent-light border border-accent/20'
                  : 'text-white/50 hover:text-white/80 hover:bg-white/[0.04] border border-transparent'
              }`
            }
          >
            <Icon size={20} weight="duotone" className="flex-shrink-0" />
            {!collapsed && <span className="text-sm font-medium">{label}</span>}
          </NavLink>
        ))}
      </nav>

      {/* User + Collapse */}
      <div className="border-t border-white/[0.06] p-3 space-y-2">
        {!collapsed && user && (
          <div className="px-2 py-2 animate-fade-in">
            <p className="text-sm font-medium text-white/80 truncate">{user.name}</p>
            <p className="text-xs text-white/30 capitalize">{user.role}</p>
          </div>
        )}
        <div className="flex items-center gap-2">
          <button onClick={handleLogout} className="flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-xl text-white/40 hover:text-danger-light hover:bg-danger/10 transition-all duration-200" title="Logout">
            <SignOut size={18} />
            {!collapsed && <span className="text-xs font-medium">Logout</span>}
          </button>
          <button onClick={() => setCollapsed(!collapsed)} className="p-2 rounded-xl text-white/30 hover:text-white/60 hover:bg-white/[0.04] transition-all duration-200" title={collapsed ? 'Expand' : 'Collapse'}>
            {collapsed ? <CaretRight size={16} /> : <CaretLeft size={16} />}
          </button>
        </div>
      </div>
    </aside>
  );
}
