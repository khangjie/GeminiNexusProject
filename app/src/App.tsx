import { useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Login from './pages/Login';
import { DashboardLayout } from './layouts/DashboardLayout';
import OwnerAnalytics from './pages/owner/Analytics';
import OwnerApprovals from './pages/owner/Approvals';
import OwnerExpenses from './pages/owner/Expenses';
import OwnerAiSettings from './pages/owner/AiSettings';
import WorkerDashboard from './pages/worker/Dashboard';
import WorkerSubmitClaim from './pages/worker/SubmitClaim';
import AdminPage from './pages/Admin';
import { getSession, onSessionChanged, type AppSession } from './lib/session';

import './index.css';

function App() {
  const [session, setSession] = useState<AppSession | null>(() => getSession());

  useEffect(() => {
    return onSessionChanged(() => {
      setSession(getSession());
    });
  }, []);

  const ownerAllowed = session?.user.role === 'owner';
  const workerAllowed = session?.user.role === 'worker' || session?.user.role === 'owner';
  const rootElement = ownerAllowed
    ? <Navigate to="/owner" replace />
    : workerAllowed
      ? <Navigate to="/worker" replace />
      : <Login />;

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={rootElement} />
        
        {/* Owner Routes */}
        <Route
          path="/owner"
          element={ownerAllowed ? <DashboardLayout role="owner" /> : <Navigate to="/" replace />}
        >
          <Route index element={<OwnerAnalytics />} />
          <Route path="expenses" element={<OwnerExpenses />} />
          <Route path="approvals" element={<OwnerApprovals />} />
          <Route path="settings" element={<OwnerAiSettings />} />
        </Route>

        {/* Worker Routes */}
        <Route
          path="/worker"
          element={workerAllowed ? <DashboardLayout role="worker" /> : <Navigate to="/" replace />}
        >
          <Route index element={<WorkerDashboard />} />
          <Route path="submit" element={<WorkerSubmitClaim />} />
        </Route>

        {/* Local Admin Route (hard-coded credential in page) */}
        <Route path="/admin" element={<AdminPage />} />

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
