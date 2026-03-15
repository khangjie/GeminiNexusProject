import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { LayoutDashboard, Receipt, CheckSquare, Settings, UploadCloud, LogOut, Hexagon } from 'lucide-react';
import { cn } from '../lib/utils';
import { motion } from 'framer-motion';
import { clearSession, getSession } from '../lib/session';

export function DashboardLayout({ role }: { role: 'owner' | 'worker' }) {
  const navigate = useNavigate();
  const session = getSession();
  const userName = session?.user.name || (role === 'owner' ? 'Company Owner' : 'Worker Name');
  const userEmail = session?.user.email || (role === 'owner' ? 'owner@company.com' : 'worker@company.com');

  const handleLogout = () => {
    clearSession();
    navigate('/');
  };

  const ownerLinks = [
    { to: '/owner', icon: LayoutDashboard, label: 'Analytics' },
    { to: '/owner/expenses', icon: Receipt, label: 'Expenses' },
    { to: '/owner/approvals', icon: CheckSquare, label: 'Approvals' },
    { to: '/owner/settings', icon: Settings, label: 'Settings' },
  ];

  const workerLinks = [
    { to: '/worker', icon: LayoutDashboard, label: 'Dashboard' },
    { to: '/worker/submit', icon: UploadCloud, label: 'Submit Claim' },
  ];

  const links = role === 'owner' ? ownerLinks : workerLinks;

  return (
    <div className="flex h-screen overflow-hidden bg-slate-50/50">
      {/* Sidebar */}
      <motion.aside 
        initial={{ x: -280 }}
        animate={{ x: 0 }}
        className="w-64 flex-shrink-0 border-r border-slate-200 bg-white/80 glass hidden md:flex flex-col"
      >
        <div className="h-16 flex items-center px-6 border-b border-slate-100">
          <div className="flex items-center gap-2 text-primary-600 font-bold text-xl tracking-tight">
            <Hexagon className="w-6 h-6 fill-primary-600/20" />
            <span>NexusHub</span>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto py-6 px-4 flex flex-col gap-1">
          <div className="mb-4 px-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">
            {role === 'owner' ? 'Owner Portal' : 'Worker Portal'}
          </div>
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.to === '/owner' || link.to === '/worker'}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200",
                  isActive
                    ? "bg-primary-50 text-primary-700 shadow-sm ring-1 ring-primary-100"
                    : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                )
              }
            >
              {({ isActive }) => (
                <>
                  <link.icon className={cn("w-5 h-5 transition-colors", isActive ? "text-primary-600" : "text-slate-400")} />
                  {link.label}
                </>
              )}
            </NavLink>
          ))}
        </div>

        <div className="p-4 border-t border-slate-100">
          <div className="flex items-center gap-3 px-3 py-3 rounded-lg hover:bg-slate-50 transition-colors cursor-pointer text-sm text-slate-700">
            <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-primary-500 to-primary-300 text-white flex items-center justify-center font-bold">
              {role === 'owner' ? 'O' : 'W'}
            </div>
            <div className="flex-1 overflow-hidden">
              <p className="font-medium truncate">{userName}</p>
              <p className="text-xs text-slate-500 truncate">{userEmail}</p>
            </div>
          </div>
          <button 
            onClick={handleLogout}
            className="mt-2 w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-sm font-medium text-slate-600 hover:bg-red-50 hover:text-red-600 transition-colors"
          >
            <LogOut className="w-4 h-4" />
            Sign Out
          </button>
        </div>
      </motion.aside>

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto w-full relative">
        <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-20 pointer-events-none mix-blend-overlay"></div>
        <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] rounded-full bg-primary-200/30 blur-[100px] pointer-events-none"></div>
        <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] rounded-full bg-purple-200/30 blur-[100px] pointer-events-none"></div>
        
        <Outlet />
      </main>
    </div>
  );
}
