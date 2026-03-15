import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ShieldCheck, Trash2 } from "lucide-react";

import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Input } from "../components/ui/Input";
import { deleteAdminUser, devLogin, listAdminUsers, listCompanies, type AdminUser, type Company } from "../lib/api";

const ADMIN_USERNAME = "admin";
const ADMIN_PASSWORD = "Admin@123";
const ADMIN_AUTH_KEY = "nexushub_admin_authed";

export default function AdminPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [isAuthed, setIsAuthed] = useState(false);

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<"owner" | "worker">("worker");
  const [companies, setCompanies] = useState<Company[]>([]);
  const [selectedCompanyId, setSelectedCompanyId] = useState("");
  const [users, setUsers] = useState<AdminUser[]>([]);

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    const existing = localStorage.getItem(ADMIN_AUTH_KEY);
    if (existing === "true") {
      setIsAuthed(true);
    }
  }, []);

  useEffect(() => {
    if (!isAuthed) {
      return;
    }

    Promise.all([
      listCompanies(),
      listAdminUsers(ADMIN_USERNAME, ADMIN_PASSWORD),
    ])
      .then(([items, userItems]) => {
        setCompanies(items);
        setUsers(userItems);
        if (items.length > 0) {
          setSelectedCompanyId(items[0].id);
        }
      })
      .catch(() => {
        setCompanies([]);
        setUsers([]);
      });
  }, [isAuthed]);

  const companyNameById = useMemo(
    () => Object.fromEntries(companies.map((company) => [company.id, company.name])),
    [companies],
  );

  const refreshUsers = async () => {
    const nextUsers = await listAdminUsers(ADMIN_USERNAME, ADMIN_PASSWORD);
    setUsers(nextUsers);
  };

  const canSubmitUser = useMemo(() => {
    if (!name.trim() || !email.trim()) {
      return false;
    }
    if (role === "worker") {
      return selectedCompanyId.length > 0;
    }
    return true;
  }, [name, email, role, selectedCompanyId]);

  const handleAdminLogin = () => {
    setError("");
    setSuccess("");

    if (username === ADMIN_USERNAME && password === ADMIN_PASSWORD) {
      localStorage.setItem(ADMIN_AUTH_KEY, "true");
      setIsAuthed(true);
      return;
    }

    setError("Invalid admin credential");
  };

  const handleAdminLogout = () => {
    localStorage.removeItem(ADMIN_AUTH_KEY);
    setIsAuthed(false);
    setUsername("");
    setPassword("");
    setSuccess("");
    setError("");
  };

  const handleCreateOrUpdateUser = async () => {
    if (!canSubmitUser) {
      return;
    }

    setBusy(true);
    setError("");
    setSuccess("");

    try {
      const result = await devLogin({
        name: name.trim(),
        email: email.trim(),
        role,
        company_id: role === "worker" ? selectedCompanyId : undefined,
      });

      setSuccess(`User ready: ${result.user.name} (${result.user.role})`);
      setName("");
      setEmail("");
      await refreshUsers();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create user");
    } finally {
      setBusy(false);
    }
  };

  const handleDeleteUser = async (userId: string) => {
    setBusy(true);
    setError("");
    setSuccess("");
    try {
      await deleteAdminUser(userId, ADMIN_USERNAME, ADMIN_PASSWORD);
      setSuccess("User deleted");
      await refreshUsers();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to delete user");
    } finally {
      setBusy(false);
    }
  };

  if (!isAuthed) {
    return (
      <div className="min-h-screen bg-slate-50 p-4 flex items-center justify-center">
        <Card className="w-full max-w-md p-6">
          <div className="flex items-center gap-2 mb-4">
            <ShieldCheck className="w-5 h-5 text-slate-700" />
            <h1 className="text-lg font-semibold text-slate-900">Admin Login</h1>
          </div>

          <p className="text-sm text-slate-500 mb-4">
            Hard-coded credential: admin / Admin@123
          </p>

          <div className="space-y-3">
            <div>
              <label className="text-sm font-medium text-slate-700">Username</label>
              <Input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="admin" />
            </div>
            <div>
              <label className="text-sm font-medium text-slate-700">Password</label>
              <Input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Admin@123"
              />
            </div>

            {error && <p className="text-sm text-red-600">{error}</p>}

            <Button className="w-full" onClick={handleAdminLogin}>
              Enter Admin
            </Button>

            <Link to="/" className="block text-center text-sm text-primary-600 hover:underline">
              Back to Login
            </Link>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 p-4 md:p-8">
      <div className="max-w-4xl mx-auto space-y-4">
        <Card className="p-6">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h1 className="text-xl font-semibold text-slate-900">Admin User Manager</h1>
              <p className="text-sm text-slate-500">Create or update owner/worker users for dev testing.</p>
            </div>
            <Button className="bg-slate-700 hover:bg-slate-800 text-white" onClick={handleAdminLogout}>
              Logout Admin
            </Button>
          </div>
        </Card>

        <Card className="p-6 space-y-4">
          <h2 className="text-lg font-semibold text-slate-900">Create User</h2>

          <div>
            <label className="text-sm font-medium text-slate-700">Name</label>
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="User full name" />
          </div>

          <div>
            <label className="text-sm font-medium text-slate-700">Email</label>
            <Input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="user@company.com" />
          </div>

          <div>
            <label className="text-sm font-medium text-slate-700">Role</label>
            <select
              value={role}
              onChange={(e) => setRole(e.target.value as "owner" | "worker")}
              className="mt-1 flex h-10 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm"
            >
              <option value="worker">worker</option>
              <option value="owner">owner</option>
            </select>
          </div>

          {role === "worker" && (
            <div>
              <label className="text-sm font-medium text-slate-700">Company</label>
              <select
                value={selectedCompanyId}
                onChange={(e) => setSelectedCompanyId(e.target.value)}
                className="mt-1 flex h-10 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm"
              >
                {companies.length === 0 ? (
                  <option value="">No companies available</option>
                ) : (
                  companies.map((company) => (
                    <option key={company.id} value={company.id}>
                      {company.name}
                    </option>
                  ))
                )}
              </select>
            </div>
          )}

          {error && <p className="text-sm text-red-600">{error}</p>}
          {success && <p className="text-sm text-emerald-700">{success}</p>}

          <Button className="w-full" disabled={!canSubmitUser || busy} onClick={handleCreateOrUpdateUser}>
            {busy ? "Saving..." : "Create / Update User"}
          </Button>
        </Card>

        <Card className="p-6 space-y-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold text-slate-900">User List</h2>
              <p className="text-sm text-slate-500">Delete only works when the user does not own a company and has no receipts.</p>
            </div>
            <Button variant="outline" className="bg-white" disabled={busy} onClick={refreshUsers}>
              Reload Users
            </Button>
          </div>

          <div className="space-y-3">
            {users.length === 0 && <p className="text-sm text-slate-500">No users found.</p>}

            {users.map((user) => (
              <div key={user.id} className="rounded-xl border border-slate-200 bg-white p-4 flex flex-col md:flex-row md:items-center md:justify-between gap-3">
                <div className="min-w-0">
                  <p className="font-medium text-slate-900 truncate">{user.name}</p>
                  <p className="text-sm text-slate-500 truncate">{user.email}</p>
                  <div className="flex flex-wrap gap-2 mt-2 text-xs text-slate-600">
                    <span className="rounded-full bg-slate-100 px-2 py-1">role: {user.role}</span>
                    <span className="rounded-full bg-slate-100 px-2 py-1">
                      company: {user.company_id ? companyNameById[user.company_id] || user.company_id : "none"}
                    </span>
                    <span className="rounded-full bg-slate-100 px-2 py-1">receipts: {user.receipt_count}</span>
                    {user.owned_company_id && <span className="rounded-full bg-amber-100 px-2 py-1 text-amber-700">owns company</span>}
                  </div>
                </div>

                <Button
                  variant="danger"
                  disabled={busy || !!user.owned_company_id || user.receipt_count > 0}
                  onClick={() => handleDeleteUser(user.id)}
                >
                  <Trash2 size={16} className="mr-2" /> Delete
                </Button>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}
