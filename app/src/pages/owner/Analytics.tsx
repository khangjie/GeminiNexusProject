import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { TrendingUp, ArrowUpRight, Wallet, Clock, Sparkles } from "lucide-react";
import { Card } from "../../components/ui/Card";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { getAnalyticsSummary, queryAnalytics } from "../../lib/api";

function toNumber(value: unknown, fallback = 0): number {
  const parsed = typeof value === "number" ? value : Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

export default function Analytics() {
  const [summary, setSummary] = useState({ total_spend: 0, pending_count: 0, ai_approval_rate: 0 });
  const [lastUpdated, setLastUpdated] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [question, setQuestion] = useState("What are my top spending categories this month?");
  const [answer, setAnswer] = useState("");
  const [chartTitle, setChartTitle] = useState("Analytics Chart");
  const [chartData, setChartData] = useState<Array<{ label: string; value: number }>>([]);

  const loadSummary = () => {
    setLoading(true);
    setError("");
    getAnalyticsSummary()
      .then((data) => {
        setSummary({
          total_spend: toNumber(data?.total_spend),
          pending_count: toNumber(data?.pending_count),
          ai_approval_rate: toNumber(data?.ai_approval_rate),
        });
        setLastUpdated(new Date().toLocaleTimeString());
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load analytics summary"))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadSummary();
  }, []);

  const handleAsk = async () => {
    if (!question.trim()) {
      return;
    }
    setLoading(true);
    setError("");
    try {
      const result = await queryAnalytics(question.trim());
      setAnswer(result.answer);
      setChartTitle(result.chart_title || "Analytics Chart");
      setChartData(result.chart_data || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to run analytics query");
    } finally {
      setLoading(false);
    }
  };

  const chartRows = useMemo(() => chartData.map((row) => ({ name: row.label, value: row.value })), [chartData]);

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8 relative z-10 w-full h-full pb-20">
      <header className="flex justify-between items-end">
        <div>
          <motion.h1 initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="text-3xl font-bold tracking-tight text-slate-900">
            Company Overview
          </motion.h1>
          <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.1 }} className="text-slate-500 mt-1">
            Track spending, pending approvals, and AI performance with live backend data.
          </motion.p>
          {lastUpdated && <p className="text-xs text-slate-400 mt-2">Last updated {lastUpdated}</p>}
        </div>
        <Button variant="outline" className="bg-white" onClick={loadSummary}>Refresh</Button>
      </header>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <KPICard title="Total Spent" amount={`$${summary.total_spend.toFixed(2)}`} icon={Wallet} trend="Live" />
        <KPICard title="Pending Approval" amount={`${summary.pending_count}`} icon={Clock} trend="Queue" />
        <KPICard title="AI Auto-Approved" amount={`${summary.ai_approval_rate}%`} icon={TrendingUp} trend="Rate" />
      </div>

      <Card className="space-y-4">
        <h3 className="text-lg font-semibold text-slate-800 flex items-center gap-2">
          <Sparkles size={18} className="text-primary-600" /> Ask AI Analytics
        </h3>
        <div className="flex gap-3">
          <Input value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="Ask a spending question..." />
          <Button onClick={handleAsk} disabled={loading}>Run</Button>
        </div>
        {answer && (
          <div className="text-sm text-slate-700 bg-slate-50 border border-slate-200 rounded-md p-3">
            {answer}
          </div>
        )}
      </Card>

      <Card className="h-[360px] flex flex-col">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-slate-800">{chartTitle}</h3>
          <Badge variant="secondary">{chartRows.length} points</Badge>
        </div>
        <div className="flex-1 min-h-0">
          {chartRows.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartRows} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: "#64748b" }} dy={10} />
                <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: "#64748b" }} />
                <Tooltip />
                <Bar dataKey="value" fill="#3b82f6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-full flex items-center justify-center text-sm text-slate-500">Run an analytics query to generate chart data.</div>
          )}
        </div>
      </Card>
    </div>
  );
}

function KPICard({ title, amount, icon: Icon, trend }: { title: string; amount: string; icon: React.ComponentType<{ size?: number; className?: string }>; trend: string }) {
  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
      <Card className="hover:shadow-lg transition-shadow duration-300 group">
        <div className="flex justify-between items-start mb-4">
          <div className="p-2 rounded-lg text-primary-600 bg-primary-50">
            <Icon size={20} />
          </div>
          <div className="flex items-center text-xs font-medium px-2 py-1 rounded-full text-slate-600 bg-slate-100">
            <ArrowUpRight size={14} className="mr-1" />
            {trend}
          </div>
        </div>
        <div>
          <h3 className="text-slate-500 text-sm font-medium">{title}</h3>
          <div className="text-2xl font-bold text-slate-900 tracking-tight mt-1 group-hover:scale-[1.02] transition-transform transform origin-left">{amount}</div>
        </div>
      </Card>
    </motion.div>
  );
}
