import { useEffect, useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Search, Filter, Download, CheckCircle2, ChevronDown, ChevronUp, Receipt as ReceiptIcon, Image as ImageIcon } from "lucide-react";
import { Card } from "../../components/ui/Card";
import { Badge } from "../../components/ui/Badge";
import { Input } from "../../components/ui/Input";
import { Button } from "../../components/ui/Button";
import { cn } from "../../lib/utils";
import { fetchReceiptImageBlobUrl, listReceipts } from "../../lib/api";
import type { Receipt } from "../../lib/api";

export default function ExpensesManagement() {
  const [viewMode, setViewMode] = useState<"receipt" | "category">("receipt");
  const [expandedReceipts, setExpandedReceipts] = useState<string[]>([]);
  const [receipts, setReceipts] = useState<Receipt[]>([]);
  const [lastUpdated, setLastUpdated] = useState<string>("");
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [previewType, setPreviewType] = useState<string>("");
  const [previewTitle, setPreviewTitle] = useState<string>("");

  const toggleExpand = (id: string) => {
    setExpandedReceipts((prev) => (prev.includes(id) ? prev.filter((rId) => rId !== id) : [...prev, id]));
  };

  const loadReceipts = () => {
    setLoading(true);
    setError("");
    listReceipts()
      .then((rows) => {
        setReceipts(rows.filter((row) => row.status === "approved" || row.status === "ai_approved"));
        setLastUpdated(new Date().toLocaleTimeString());
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load expenses"))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadReceipts();
  }, []);

  const filteredReceipts = useMemo(() => {
    const q = query.trim().toLowerCase();
    const approved = receipts.filter((row) => row.status === "approved" || row.status === "ai_approved");
    const filtered = !q
      ? approved
      : approved.filter(
      (receipt) =>
        (receipt.vendor || "").toLowerCase().includes(q) ||
        receipt.id.toLowerCase().includes(q) ||
        receipt.items.some((item) => item.name.toLowerCase().includes(q)),
    );

    return [...filtered].sort((a, b) => {
      const aDate = new Date(a.receipt_date || a.created_at).getTime();
      const bDate = new Date(b.receipt_date || b.created_at).getTime();
      return bDate - aDate;
    });
  }, [query, receipts]);

  const totalSpend = useMemo(() => filteredReceipts.reduce((sum, receipt) => sum + (receipt.total_amount || 0), 0), [filteredReceipts]);

  const categoryRows = useMemo(() => {
    const grouped: Record<string, Array<{ receiptId: string; itemId: string; name: string; quantity: number; vendor: string; amount: number; date: string }>> = {};

    filteredReceipts.forEach((receipt) => {
      const when = receipt.receipt_date || receipt.created_at;
      receipt.items.forEach((item) => {
        const category = item.category || "Uncategorized";
        if (!grouped[category]) {
          grouped[category] = [];
        }
        grouped[category].push({
          receiptId: receipt.id,
          itemId: item.id,
          name: item.name,
          quantity: item.quantity || 1,
          vendor: receipt.vendor || "Unknown vendor",
          amount: item.price || 0,
          date: when,
        });
      });
    });

    return Object.entries(grouped)
      .map(([category, items]) => {
        const sortedItems = [...items].sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
        const total = sortedItems.reduce((sum, item) => sum + item.amount, 0);
        return { category, items: sortedItems, total };
      })
      .sort((a, b) => b.total - a.total);
  }, [filteredReceipts]);

  const openReceiptPreview = async (receipt: Receipt) => {
    try {
      setError("");
      const next = await fetchReceiptImageBlobUrl(receipt.id);
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl);
      }
      setPreviewUrl(next.url);
      setPreviewType(next.contentType);
      setPreviewTitle(`${receipt.vendor || "Receipt"} • ${receipt.id.slice(0, 8)}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load receipt image");
    }
  };

  const closeReceiptPreview = () => {
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }
    setPreviewUrl(null);
    setPreviewType("");
    setPreviewTitle("");
  };

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8 relative z-10 w-full h-full pb-20">
      <header className="flex md:flex-row flex-col gap-4 md:items-end justify-between">
        <div>
          <motion.h1 initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="text-3xl font-bold tracking-tight text-slate-900">
            Expenses Ledger
          </motion.h1>
          <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.1 }} className="text-slate-500 mt-1">
            Live record of approved expenses.
          </motion.p>
          {lastUpdated && <p className="text-xs text-slate-400 mt-2">Last updated {lastUpdated}</p>}
        </div>

        <div className="flex gap-3">
          <Button variant="outline" className="bg-white" onClick={loadReceipts}>
            <Download size={16} className="mr-2" /> Refresh
          </Button>
        </div>
      </header>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <div className="flex gap-3 my-6">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
          <Input className="pl-9 w-full bg-white shadow-sm" placeholder="Search vendor, item, or receipt ID..." value={query} onChange={(e) => setQuery(e.target.value)} />
        </div>
        <Button variant="outline" className="bg-white" disabled>
          <Filter size={16} className="mr-2" /> Filters
        </Button>
      </div>

      <div className="flex items-center gap-2">
        <Button
          variant={viewMode === "receipt" ? "default" : "outline"}
          className={viewMode === "receipt" ? "" : "bg-white"}
          onClick={() => setViewMode("receipt")}
        >
          By Receipt
        </Button>
        <Button
          variant={viewMode === "category" ? "default" : "outline"}
          className={viewMode === "category" ? "" : "bg-white"}
          onClick={() => setViewMode("category")}
        >
          By Category
        </Button>
      </div>

      <Card className="bg-primary-50/50 border-primary-100 flex items-center justify-between">
        <div>
          <p className="text-sm text-primary-700">Total visible spend</p>
          <p className="text-2xl font-bold text-primary-900">${totalSpend.toFixed(2)}</p>
        </div>
        <Badge variant="success" className="bg-emerald-100 text-emerald-700">
          <CheckCircle2 size={14} className="mr-1" /> {filteredReceipts.length} approved receipts
        </Badge>
      </Card>

      <AnimatePresence mode="wait">
        <motion.div key={viewMode} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} className="space-y-4">
          {loading && <p className="text-sm text-slate-500">Loading receipts...</p>}

          {viewMode === "receipt" &&
            filteredReceipts.map((receipt) => {
              const isExpanded = expandedReceipts.includes(receipt.id);
              return (
                <Card key={receipt.id} className={cn("p-0 overflow-hidden transition-all bg-white flex flex-col shadow-sm border-slate-200", isExpanded && "ring-2 ring-primary-500/20 shadow-md")}>
                  <div className="grid grid-cols-1 md:grid-cols-12 gap-4 p-5 items-center cursor-pointer hover:bg-slate-50/80 transition-colors" onClick={() => toggleExpand(receipt.id)}>
                    <div className="md:col-span-4 flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-slate-100 flex items-center justify-center text-slate-500 shrink-0">
                        <ReceiptIcon size={18} />
                      </div>
                      <div className="min-w-0">
                        <div className="font-semibold text-slate-900 truncate">{receipt.vendor || "Unknown vendor"}</div>
                        <div className="text-xs text-slate-500">{receipt.id.slice(0, 8)} • {new Date(receipt.receipt_date || receipt.created_at).toLocaleDateString()}</div>
                      </div>
                    </div>

                    <div className="md:col-span-3 text-slate-600 capitalize">{receipt.receipt_type.replace("_", " ")}</div>

                    <div className="md:col-span-3 flex items-center gap-2">
                      <Badge variant="success" className="px-2 py-0.5">{receipt.status.replace("_", " ")}</Badge>
                    </div>

                    <div className="md:col-span-1 text-right font-bold text-slate-900">${(receipt.total_amount || 0).toFixed(2)}</div>

                    <div className="md:col-span-1 flex justify-end text-slate-400">{isExpanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}</div>
                  </div>

                  <AnimatePresence>
                    {isExpanded && (
                      <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="border-t border-slate-100 bg-slate-50/50">
                        <div className="p-6">
                          <div className="flex items-center justify-between mb-4">
                            <h4 className="font-semibold text-slate-800 text-sm uppercase tracking-wider">Itemized Breakdown</h4>
                            <Badge variant="outline" className="text-slate-500 bg-white shadow-sm font-mono">{receipt.items.length} item(s)</Badge>
                          </div>

                          <div className="space-y-3 bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
                            {receipt.items.map((item) => (
                              <div key={item.id} className="flex flex-col sm:flex-row sm:justify-between sm:items-center py-2 border-b border-slate-100 last:border-0 last:pb-0 gap-2">
                                <div>
                                  <div className="font-medium text-slate-800">{item.name} {item.quantity && item.quantity > 1 ? `x${item.quantity}` : ""}</div>
                                  <div className="text-xs text-slate-500 mt-0.5">{item.category || "Uncategorized"}</div>
                                </div>
                                <div className="font-semibold font-mono text-slate-700 self-end sm:self-auto">${(item.price || 0).toFixed(2)}</div>
                              </div>
                            ))}
                          </div>

                          <div className="mt-4">
                            <Button variant="outline" className="bg-white" onClick={() => openReceiptPreview(receipt)}>
                              <ImageIcon size={16} className="mr-2" /> View Receipt Image
                            </Button>
                          </div>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </Card>
              );
            })}

          {viewMode === "category" &&
            categoryRows.map((group) => (
              <Card key={group.category} className="bg-white border-slate-200 shadow-sm">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-lg font-semibold text-slate-900">{group.category}</h3>
                  <Badge variant="outline" className="bg-slate-50 text-slate-700">
                    ${group.total.toFixed(2)}
                  </Badge>
                </div>

                <div className="space-y-2">
                  {group.items.map((item) => (
                    <div key={`${item.receiptId}-${item.itemId}`} className="flex items-center justify-between border border-slate-100 rounded-lg p-3 bg-slate-50/50">
                      <div>
                        <p className="font-medium text-slate-800">{item.name} {item.quantity && item.quantity > 1 ? `x${item.quantity}` : ""}</p>
                        <p className="text-xs text-slate-500">
                          {item.vendor} • {new Date(item.date).toLocaleDateString()} • {item.receiptId.slice(0, 8)}
                        </p>
                      </div>
                      <p className="font-semibold text-slate-900">${item.amount.toFixed(2)}</p>
                    </div>
                  ))}
                </div>
              </Card>
            ))}
        </motion.div>
      </AnimatePresence>

      <AnimatePresence>
        {previewUrl && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/60 p-4 flex items-center justify-center"
            onClick={closeReceiptPreview}
          >
            <motion.div
              initial={{ scale: 0.98, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.98, opacity: 0 }}
              className="w-full max-w-4xl max-h-[90vh] bg-white rounded-xl shadow-2xl overflow-hidden"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200">
                <h3 className="text-sm font-semibold text-slate-800 truncate">{previewTitle}</h3>
                <Button variant="outline" className="bg-white" onClick={closeReceiptPreview}>Close</Button>
              </div>
              <div className="p-4 max-h-[80vh] overflow-auto bg-slate-50">
                {previewType.includes("pdf") ? (
                  <iframe src={previewUrl} title={previewTitle} className="w-full h-[75vh] rounded border border-slate-200 bg-white" />
                ) : (
                  <img src={previewUrl} alt={previewTitle} className="mx-auto max-h-[75vh] rounded border border-slate-200 bg-white" />
                )}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
