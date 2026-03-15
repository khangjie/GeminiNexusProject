import { useEffect, useMemo, useState } from "react"
import { motion } from "framer-motion"
import { Link, useNavigate } from "react-router-dom"
import { Hexagon, Building2, UserCircle2, PlusCircle } from "lucide-react"
import { Card } from "../components/ui/Card"
import { Input } from "../components/ui/Input"
import { Button } from "../components/ui/Button"
import { createCompany, devLogin, listCompanies } from "../lib/api"
import type { Company } from "../lib/api"
import { getSession, setSession } from "../lib/session"

export default function Login() {
  const navigate = useNavigate()
  const [email, setEmail] = useState("")
  const [name, setName] = useState("")
  const [role, setRole] = useState<"owner" | "worker">("owner")
  const [companies, setCompanies] = useState<Company[]>([])
  const [selectedCompanyId, setSelectedCompanyId] = useState("")
  const [newCompanyName, setNewCompanyName] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")

  useEffect(() => {
    let active = true

    listCompanies()
      .then((items) => {
        if (!active) {
          return
        }
        setCompanies(items)
        if (items.length > 0) {
          setSelectedCompanyId(items[0].id)
        }
      })
      .catch(() => {
        if (!active) {
          return
        }
        setCompanies([])
      })

    return () => {
      active = false
    }
  }, [])

  const canLogin = useMemo(() => {
    if (!email.trim() || !name.trim()) {
      return false
    }
    if (role === "worker") {
      return selectedCompanyId.length > 0
    }
    return true
  }, [email, name, role, selectedCompanyId])

  const handleSignIn = async () => {
    if (!canLogin) {
      return
    }
    setLoading(true)
    setError("")
    try {
      const result = await devLogin({
        email: email.trim(),
        name: name.trim(),
        role,
        company_id: role === "worker" ? selectedCompanyId : undefined,
      })
      setSession({
        accessToken: result.access_token,
        user: result.user,
      })

      navigate(result.user.role === "owner" ? "/owner" : "/worker")
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to sign in")
    } finally {
      setLoading(false)
    }
  }

  const handleCreateCompany = async () => {
    if (!newCompanyName.trim()) {
      return
    }
    setLoading(true)
    setError("")
    try {
      const loginResult = await devLogin({
        email: email.trim(),
        name: name.trim(),
        role: "owner",
      })

      setSession({
        accessToken: loginResult.access_token,
        user: loginResult.user,
      })

      await createCompany(newCompanyName.trim())
      const refreshedOwner = await devLogin({
        email: email.trim(),
        name: name.trim(),
        role: "owner",
      })
      setSession({
        accessToken: refreshedOwner.access_token,
        user: refreshedOwner.user,
      })
      navigate("/owner")
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create company")
    } finally {
      setLoading(false)
    }
  }

  const bgOrbs = (
    <>
      <div className="absolute top-[-20%] left-[-10%] w-[60%] h-[60%] rounded-full bg-primary-300/20 blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-20%] right-[-10%] w-[60%] h-[60%] rounded-full bg-purple-300/20 blur-[120px] pointer-events-none" />
      <div className="absolute inset-0 opacity-20 pointer-events-none mix-blend-overlay" />
    </>
  )

  const logo = (
    <div className="flex flex-col items-center mb-8">
      <motion.div
        initial={{ scale: 0.8 }}
        animate={{ scale: 1 }}
        transition={{ type: "spring", stiffness: 200, damping: 15 }}
        className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary-600 to-purple-600 text-white flex items-center justify-center shadow-xl shadow-primary-500/30 mb-4"
      >
        <Hexagon size={36} className="fill-white/20" />
      </motion.div>
      <h1 className="text-3xl font-bold tracking-tight text-slate-900">NexusHub</h1>
      <p className="text-slate-500 mt-2 text-center">AI Expense Operations Platform</p>
    </div>
  )

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center p-4 relative overflow-hidden">
      {bgOrbs}

      <motion.div
        key="main"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        className="w-full max-w-md z-10"
      >
        {logo}
        <Card className="p-8 backdrop-blur-2xl bg-white/60 border-white/80 shadow-2xl">
          <h2 className="text-xl font-semibold text-center mb-6 text-slate-800">Sign in for development</h2>
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium text-slate-700 mb-1.5 block">Name</label>
              <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Your name" />
            </div>
            <div>
              <label className="text-sm font-medium text-slate-700 mb-1.5 block">Email</label>
              <Input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@company.com" />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={() => setRole("owner")}
                className={`w-full group flex items-center p-3 rounded-xl border-2 transition-all text-left ${role === "owner" ? "border-primary-500 bg-primary-50/60" : "border-slate-200 hover:border-primary-300"}`}
              >
                <Building2 size={18} className="text-primary-600" />
                <span className="ml-2 font-medium text-slate-800">Owner</span>
              </button>
              <button
                onClick={() => setRole("worker")}
                className={`w-full group flex items-center p-3 rounded-xl border-2 transition-all text-left ${role === "worker" ? "border-purple-500 bg-purple-50/60" : "border-slate-200 hover:border-purple-300"}`}
              >
                <UserCircle2 size={18} className="text-purple-600" />
                <span className="ml-2 font-medium text-slate-800">Worker</span>
              </button>
            </div>

            {role === "worker" && (
              <div>
                <label className="text-sm font-medium text-slate-700 mb-1.5 block">Company</label>
                <select
                  value={selectedCompanyId}
                  onChange={(e) => setSelectedCompanyId(e.target.value)}
                  className="flex h-10 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
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

            <Button className="w-full" disabled={!canLogin || loading} onClick={handleSignIn}>
              {loading ? "Signing in..." : "Continue"}
            </Button>

            <div className="text-center">
              <Link to="/admin" className="text-sm text-primary-700 hover:underline">
                Open Admin User Page
              </Link>
            </div>

            <div className="pt-4 border-t border-slate-200">
              <p className="text-sm font-medium text-slate-700 mb-2 flex items-center gap-2">
                <PlusCircle size={14} /> Create company (owner)
              </p>
              <div className="flex gap-2">
                <Input
                  placeholder="e.g. Acme Sdn Bhd"
                  value={newCompanyName}
                  onChange={(e) => setNewCompanyName(e.target.value)}
                />
                <Button
                  className="bg-emerald-600 hover:bg-emerald-700 text-white"
                  disabled={loading || !newCompanyName.trim() || !email.trim() || !name.trim()}
                  onClick={handleCreateCompany}
                >
                  Create
                </Button>
              </div>
            </div>
          </div>
        </Card>
      </motion.div>
    </div>
  )
}
