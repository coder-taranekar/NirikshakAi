import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';

export default function AppLayout() {
  return (
    <div className="min-h-screen bg-surface-950 flex">
      <Sidebar />
      <main className="flex-1 ml-64 min-h-screen transition-all duration-300">
        <Outlet />
      </main>
    </div>
  );
}
