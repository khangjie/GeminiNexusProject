import { useEffect, useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { UploadCloud, CheckCircle2, Clock, ChevronDown, ChevronUp, Zap, Receipt as ReceiptIcon } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { Card } from "../../components/ui/Card";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { cn } from "../../lib/utils";
import { listReceipts } from "../../lib/api";
import type { Receipt } from "../../lib/api";
import { getSession } from "../../lib/session";

export default function WorkerDashboard() {
  const navigate = useNavigate();
  const session = getSession();
  const [expandedClaims, setExpandedClaims] = useState<string[]>([]);
  const [claims, setClaims] = useState<Receipt[]>([]);
  const [lastUpdated, setLastUpdated] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const toggleExpand = (id: string) => {
    setExpandedClaims((prev) => (prev.includes(id) ? prev.filter((cId) => cId !== id) : [...prev, id]));
  };

  const loadClaims = () => {
    setLoading(true);
    listReceipts()
      .then((data) => {
        setClaims(data);
        setLastUpdated(new Date().toLocaleTimeString());
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load receipts"))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadClaims();
  }, []);

  const pendingCount = useMemo(() => claims.filter((c) => c.status === "awaiting").length, [claims]);

  const approvedAmount = useMemo(
    () =>
      claims
        .filter((c) => c.status === "approved" || c.status === "ai_approved")
        .reduce((sum, c) => sum + (c.total_amount || 0), 0),
    [claims],
  );

  const aiRate = useMemo(() => {
    const total = claims.filter((c) => c.status !== "awaiting").length;
    if (!total) {
      return 0;
    }
    const aiApproved = claims.filter((c) => c.status === "ai_approved").length;
    return Math.round((aiApproved / total) * 100);
  }, [claims]);

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-8 relative z-10 w-full h-full pb-20">
      <header className="flex md:flex-row flex-col gap-4 md:items-end justify-between">
        <div>
          <motion.h1 initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="text-3xl font-bold tracking-tight text-slate-900">
            Welcome back, {session?.user.name || "Worker"}
          </motion.h1>
          <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.1 }} className="text-slate-500 mt-1">
            Submit expenses and track AI processing status in real time.
          </motion.p>
          {lastUpdated && <p className="text-xs text-slate-400 mt-2">Last updated {lastUpdated}</p>}
        </div>
        <motion.div initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.2 }}>
          <Button size="lg" className="bg-primary-600 hover:bg-primary-700 shadow-lg shadow-primary-500/25 flex gap-2" onClick={() => navigate("/worker/submit")}>
            <UploadCloud size={20} />
            Submit New Claim
          </Button>
        </motion.div>
      </header>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
          <Card className="bg-gradient-to-br from-white to-slate-50 border-slate-200 shadow-sm flex items-center gap-4">
            <div className="w-12 h-12 rounded-full bg-blue-100 flex items-center justify-center text-blue-600">
              <Clock size={24} />
            </div>
            <div>
              <p className="text-sm font-medium text-slate-500">Pending</p>
              <h3 className="text-2xl font-bold text-slate-900">{pendingCount}</h3>
            </div>
          </Card>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}>
          <Card className="bg-gradient-to-br from-white to-emerald-50 border-emerald-100 shadow-sm flex items-center gap-4">
            <div className="w-12 h-12 rounded-full bg-emerald-100 flex items-center justify-center text-emerald-600">
              <CheckCircle2 size={24} />
            </div>
            <div>
              <p className="text-sm font-medium text-emerald-700">Approved</p>
              <h3 className="text-2xl font-bold text-emerald-900">${approvedAmount.toFixed(2)}</h3>
            </div>
          </Card>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }}>
          <Card className="bg-white border-primary-100 overflow-hidden relative">
            <div className="absolute right-[-10px] top-[-10px] opacity-10 text-primary-600 rotate-12">
              <Zap size={100} fill="currentColor" />
            </div>
            <div className="relative z-10">
              <p className="text-sm font-medium text-primary-700 flex items-center gap-1"><Zap size={14} fill="currentColor" /> AI Auto-Approval Rate</p>
              <h3 className="text-2xl font-bold text-primary-900 mt-1">{aiRate}%</h3>
              <p className="text-xs text-primary-600/70 mt-1">Based on processed claims.</p>
            </div>
          </Card>
        </motion.div>
      </div>

      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.6 }} className="space-y-4">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-slate-800 tracking-tight">Recent Activity</h2>
          <Button variant="ghost" size="sm" className="text-slate-500" onClick={loadClaims}>
            Refresh
          </Button>
        </div>

        {loading && <p className="text-sm text-slate-500">Loading receipts...</p>}

        <AnimatePresence mode="popLayout">
          {claims.map((claim) => {
            const isExpanded = expandedClaims.includes(claim.id);
            return (
              <motion.div layout key={claim.id} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, scale: 0.95 }}>
                <Card className={cn("p-0 overflow-hidden transition-all bg-white flex flex-col shadow-sm border-slate-200", isExpanded && "ring-2 ring-primary-500/20 shadow-md")}>
                  <div className="p-5 flex items-center gap-4 hover:bg-slate-50/80 transition-colors cursor-pointer group" onClick={() => toggleExpand(claim.id)}>
                    <div
                      className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${
                        claim.status === "approved" || claim.status === "ai_approved"
                          ? "bg-emerald-100 text-emerald-600"
                          : claim.status === "awaiting"
                            ? "bg-amber-100 text-amber-600"
                            : "bg-red-100 text-red-600"
                      }`}
                    >
                      <ReceiptIcon size={20} />
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <h4 className="font-semibold text-slate-900 truncate">{claim.vendor || "Unknown vendor"}</h4>
                        {claim.status === "ai_approved" && (
                          <Badge variant="success" className="bg-emerald-50 text-emerald-700 border border-emerald-200/50 py-0 flex items-center gap-1 drop-shadow-sm h-5">
                            <Zap size={10} fill="currentColor" /> AI Approved
                          </Badge>
                        )}
                      </div>
                      <div className="flex items-center gap-2 text-sm text-slate-500 mt-0.5">
                        <span>{claim.id.slice(0, 8)}</span>
                        <span>•</span>
                        <span>{new Date(claim.created_at).toLocaleString()}</span>
                      </div>
                    </div>

                    <div className="text-right flex items-center gap-4">
                      <div className="hidden sm:block text-right">
                        <div className="font-bold text-slate-900">${(claim.total_amount || 0).toFixed(2)}</div>
                        <div className="text-xs font-medium capitalize text-slate-600">{claim.status.replace("_", " ")}</div>
                      </div>
                      <div className="text-slate-400">{isExpanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}</div>
                    </div>
                  </div>

                  <AnimatePresence>
                    {isExpanded && (
                      <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="border-t border-slate-100 bg-slate-50/50">
                        <div className="p-6">
                          <div className="flex items-center justify-between mb-4">
                            <h4 className="font-semibold text-slate-800 text-sm uppercase tracking-wider">Itemized Breakdown</h4>
                            <Badge variant="outline" className="text-slate-500 bg-white shadow-sm font-mono">
                              {claim.items.length} item(s)
                            </Badge>
                          </div>

                          <div className="space-y-3 bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
                            {claim.items.map((item) => (
                              <div key={item.id} className="flex justify-between items-center py-2 border-b border-slate-100 last:border-0 last:pb-0">
                                <div className="font-medium text-slate-800">{item.name} {item.quantity && item.quantity > 1 ? `x${item.quantity}` : ""}</div>
                                <div className="font-semibold font-mono text-slate-700">${(item.price || 0).toFixed(2)}</div>
                              </div>
                            ))}
                          </div>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </Card>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </motion.div>
    </div>
  );
}
