import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Search, Filter, AlertTriangle, ChevronDown, ChevronUp, Check, Info, Image as ImageIcon, CircleCheck, CircleX } from "lucide-react";
import { Card } from "../../components/ui/Card";
import { Badge } from "../../components/ui/Badge";
import { Input } from "../../components/ui/Input";
import { Button } from "../../components/ui/Button";
import { cn } from "../../lib/utils";
import { applyProposalReplacement, decideApproval, fetchReceiptImageBlobUrl, getItemAlternatives, listApprovals } from "../../lib/api";
import type { ProposalAlternativeItem, Receipt, ReceiptItem } from "../../lib/api";

type QueueTab = "awaiting" | "ai_approved" | "ai_rejected";

type TypeFilter = "all" | "proposal" | "paid_expense";

type AlternativesModalState = {
  receiptId: string;
  itemId: string;
  itemName: string;
  searchName: string;
  alternatives: ProposalAlternativeItem[];
  hasSearched: boolean;
  isSearching: boolean;
};

export default function ApprovalsQueue() {
  const [activeTab, setActiveTab] = useState<QueueTab>("awaiting");
  const [typeFilter, setTypeFilter] = useState<TypeFilter>("all");
  const [expandedReceipts, setExpandedReceipts] = useState<string[]>([]);
  const [receipts, setReceipts] = useState<Receipt[]>([]);
  const [queueCounts, setQueueCounts] = useState<Record<QueueTab, number>>({
    awaiting: 0,
    ai_approved: 0,
    ai_rejected: 0,
  });
  const [lastUpdated, setLastUpdated] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [previewType, setPreviewType] = useState<string>("");
  const [previewTitle, setPreviewTitle] = useState<string>("");
  const [alternativesModal, setAlternativesModal] = useState<AlternativesModalState | null>(null);
  const [applyingReplacementKey, setApplyingReplacementKey] = useState<string | null>(null);

  const toggleExpand = (id: string) => {
    setExpandedReceipts((prev) => (prev.includes(id) ? prev.filter((rId) => rId !== id) : [...prev, id]));
  };

  const loadApprovals = () => {
    setLoading(true);
    setError("");
    Promise.all([
      listApprovals(activeTab, typeFilter === "all" ? undefined : typeFilter),
      listApprovals("awaiting"),
      listApprovals("ai_approved"),
      listApprovals("ai_rejected"),
    ])
      .then(([activeRows, awaitingRows, aiApprovedRows, aiRejectedRows]) => {
        setReceipts(activeRows);
        setQueueCounts({
          awaiting: awaitingRows.length,
          ai_approved: aiApprovedRows.length,
          ai_rejected: aiRejectedRows.length,
        });
        setLastUpdated(new Date().toLocaleTimeString());
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load approvals"))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadApprovals();
  }, [activeTab, typeFilter]);

  const handleDecision = async (receiptId: string, decision: "approved" | "rejected") => {
    try {
      await decideApproval(receiptId, decision);
      loadApprovals();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update decision");
    }
  };

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

  const openAlternatives = (receiptId: string, item: ReceiptItem) => {
    setError("");
    setAlternativesModal({
      receiptId,
      itemId: item.id,
      itemName: item.name,
      searchName: item.name,
      alternatives: [],
      hasSearched: false,
      isSearching: false,
    });
  };

  const runAlternativesSearch = async () => {
    if (!alternativesModal) {
      return;
    }

    const nextSearchName = alternativesModal.searchName.trim();
    if (!nextSearchName) {
      setError("Please enter an item name before searching");
      return;
    }

    try {
      setError("");
      setAlternativesModal((prev) => (prev ? { ...prev, isSearching: true } : prev));
      const result = await getItemAlternatives(
        alternativesModal.receiptId,
        alternativesModal.itemId,
        nextSearchName,
      );
      setAlternativesModal((prev) => {
        if (!prev) {
          return prev;
        }
        return {
          ...prev,
          itemName: result.item_name,
          alternatives: result.alternatives,
          hasSearched: true,
          isSearching: false,
        };
      });
    } catch (err) {
      setAlternativesModal((prev) => (prev ? { ...prev, isSearching: false } : prev));
      setError(err instanceof Error ? err.message : "Failed to load alternatives");
    }
  };

  const closeAlternativesModal = () => {
    setAlternativesModal(null);
    setApplyingReplacementKey(null);
  };

  const applyReplacement = async (alternative: ProposalAlternativeItem) => {
    if (!alternativesModal) {
      return;
    }
    const key = `${alternative.vendor}-${alternative.price}`;
    try {
      setError("");
      setApplyingReplacementKey(key);
      await applyProposalReplacement(
        alternativesModal.receiptId,
        alternativesModal.itemId,
        alternative.vendor,
        alternative.price,
      );
      closeAlternativesModal();
      loadApprovals();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to apply replacement");
    } finally {
      setApplyingReplacementKey(null);
    }
  };

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8 relative z-10 w-full h-full pb-20">
      <header className="flex md:flex-row flex-col gap-4 md:items-end justify-between">
        <div>
          <motion.h1 initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="text-3xl font-bold tracking-tight text-slate-900">
            Review AI Decisions
          </motion.h1>
          <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.1 }} className="text-slate-500 mt-1">
            Manage receipts, inspect rule checks, and approve or reject.
          </motion.p>
          {lastUpdated && <p className="text-xs text-slate-400 mt-2">Last updated {lastUpdated}</p>}
        </div>

        <div className="flex gap-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
            <Input className="pl-9 w-[250px]" placeholder="Search receipts..." disabled />
          </div>
          <Button variant="outline" className="bg-white" onClick={loadApprovals}>
            <Filter size={16} className="mr-2" /> Refresh
          </Button>
        </div>
      </header>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <div className="flex border-b border-slate-200">
        {([
          { key: "awaiting", label: "Awaiting" },
          { key: "ai_approved", label: "AI Approved" },
          { key: "ai_rejected", label: "AI Rejected" },
        ] as const).map((tab) => (
          <button
            key={tab.key}
            onClick={() => {
              setActiveTab(tab.key);
              setTypeFilter("all");
            }}
            className={cn(
              "px-6 py-3 font-medium text-sm transition-colors border-b-2",
              activeTab === tab.key ? "border-primary-600 text-primary-700 bg-primary-50/50" : "border-transparent text-slate-500 hover:text-slate-800 hover:bg-slate-50",
            )}
          >
            {tab.label}
            <Badge variant="secondary" className="ml-2 bg-slate-100 text-slate-600 border-none font-bold">
              {queueCounts[tab.key]}
            </Badge>
          </button>
        ))}
      </div>

      {activeTab === "awaiting" && (
        <div className="flex items-center gap-2 pt-1">
          <span className="text-xs font-medium text-slate-500 mr-1">Filter by type:</span>
          {([
            { key: "all", label: "All" },
            { key: "proposal", label: "Proposal" },
            { key: "paid_expense", label: "Paid Expense" },
          ] as const).map((item) => (
            <button
              key={item.key}
              onClick={() => setTypeFilter(item.key)}
              className={cn(
                "px-3 py-1 rounded-full text-xs font-semibold border transition-colors",
                typeFilter === item.key ? "bg-primary-100 text-primary-700 border-primary-300" : "bg-white text-slate-500 border-slate-200 hover:bg-slate-50",
              )}
            >
              {item.label}
            </button>
          ))}
        </div>
      )}

      <div className="space-y-4">
        {loading && <p className="text-sm text-slate-500">Loading approvals...</p>}

        <AnimatePresence mode="popLayout">
          {receipts.length === 0 && !loading && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="text-center py-16 text-slate-500">
              No receipts found in this category.
            </motion.div>
          )}

          {receipts.map((receipt, i) => {
            const isExpanded = expandedReceipts.includes(receipt.id);
            return (
              <motion.div layout key={receipt.id} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, scale: 0.95 }} transition={{ delay: i * 0.04 }}>
                <Card className={cn("p-0 overflow-hidden transition-all bg-white flex flex-col shadow-sm border-slate-200", isExpanded && "ring-2 ring-primary-500/20 shadow-md")}>
                  <div className="p-5 flex-1 grid grid-cols-1 md:grid-cols-12 gap-6 items-center hover:bg-slate-50/50 cursor-pointer transition-colors" onClick={() => toggleExpand(receipt.id)}>
                    <div className="md:col-span-3">
                      <div className="font-semibold text-slate-900 flex items-center gap-2">{receipt.vendor || "Unknown vendor"}</div>
                      <div className="text-xs text-slate-500">{receipt.id.slice(0, 8)} • {new Date(receipt.created_at).toLocaleDateString()}</div>
                    </div>

                    <div className="md:col-span-2">
                      <span className="text-xs font-medium text-slate-500">{receipt.receipt_type}</span>
                    </div>

                    <div className="md:col-span-5 flex items-center gap-2">
                      {receipt.status === "ai_rejected" ? (
                        <X size={16} className="text-red-500 flex-shrink-0" />
                      ) : receipt.status === "ai_approved" ? (
                        <Check size={16} className="text-emerald-500 flex-shrink-0" />
                      ) : receipt.receipt_type === "proposal" ? (
                        <Info size={16} className="text-blue-500 flex-shrink-0" />
                      ) : (
                        <AlertTriangle size={16} className="text-amber-500 flex-shrink-0" />
                      )}
                      <Badge variant="secondary" className="bg-slate-100 text-slate-700 border-none">
                        {receipt.ai_verdict || "Pending"}
                      </Badge>
                    </div>

                    <div className="md:col-span-2 flex justify-end gap-2 items-center text-slate-400">{isExpanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}</div>
                  </div>

                  <AnimatePresence>
                    {isExpanded && (
                      <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="border-t border-slate-100 bg-slate-50/40">
                        <div className="p-5 space-y-4">
                          <div className="text-sm text-slate-700">
                            <strong>Total:</strong> ${(receipt.total_amount || 0).toFixed(2)}
                          </div>

                          <div className="text-sm text-slate-700 bg-white border border-slate-200 rounded-md p-3 whitespace-pre-wrap break-words">
                            <strong>AI Feedback:</strong> {receipt.ai_reason || "No detailed explanation"}
                          </div>

                          <div className="space-y-2">
                            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">AI Requirement Checklist</p>
                            {receipt.rule_check_results.length === 0 && (
                              <div className="border rounded-md p-2 text-sm text-slate-500 bg-white">No rule checks returned.</div>
                            )}
                            {receipt.rule_check_results.map((rule) => (
                              <div key={rule.id} className="border rounded-md p-3 text-sm bg-white">
                                <div className="flex items-start justify-between gap-3">
                                  <div className="flex items-start gap-2 min-w-0">
                                    {rule.passed ? (
                                      <CircleCheck size={16} className="text-emerald-600 mt-0.5 flex-shrink-0" />
                                    ) : (
                                      <CircleX size={16} className="text-amber-600 mt-0.5 flex-shrink-0" />
                                    )}
                                    <span className="text-slate-800 break-words">{rule.rule_text}</span>
                                  </div>
                                  <Badge variant={rule.passed ? "success" : "warning"}>{rule.passed ? "Pass" : "Fail"}</Badge>
                                </div>
                                {rule.explanation && (
                                  <p className="mt-2 text-xs text-slate-600 pl-6">{rule.explanation}</p>
                                )}
                              </div>
                            ))}
                          </div>

                          {receipt.receipt_type === "proposal" && (
                            <div className="space-y-2">
                              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Proposal Items</p>
                              {receipt.items.length === 0 && (
                                <div className="border rounded-md p-2 text-sm text-slate-500 bg-white">No items extracted.</div>
                              )}
                              {receipt.items.map((item) => (
                                <div key={item.id} className="border rounded-md p-3 bg-white">
                                  <div className="flex items-start justify-between gap-3">
                                    <div className="min-w-0">
                                      <p className={cn("text-sm font-medium text-slate-900 break-words", item.is_strikethrough && "line-through text-slate-400")}>
                                        {item.name}
                                      </p>
                                      <div className="mt-1 text-xs text-slate-500 flex items-center gap-2 flex-wrap">
                                        <span>Qty: {item.quantity ?? 1}</span>
                                        <span>Price: ${Number(item.price || 0).toFixed(2)}</span>
                                        {item.is_replacement && <Badge variant="success">Replacement</Badge>}
                                        {item.replacement_vendor && <Badge variant="outline">{item.replacement_vendor}</Badge>}
                                      </div>
                                    </div>
                                    {!item.is_replacement && (
                                      <Button
                                        variant="outline"
                                        size="sm"
                                        onClick={() => openAlternatives(receipt.id, item)}
                                      >
                                        Find alternatives
                                      </Button>
                                    )}
                                  </div>
                                </div>
                              ))}
                            </div>
                          )}

                          <div className="flex gap-3">
                            <Button variant="outline" className="bg-white" onClick={() => openReceiptPreview(receipt)}>
                              <ImageIcon size={16} className="mr-2" /> View Receipt Image
                            </Button>
                          </div>

                          <div className="flex gap-3">
                            <Button className="bg-emerald-600 hover:bg-emerald-700" onClick={() => handleDecision(receipt.id, "approved")}>
                              Approve
                            </Button>
                            <Button variant="danger" onClick={() => handleDecision(receipt.id, "rejected")}>
                              Reject
                            </Button>
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
      </div>

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

      <AnimatePresence>
        {alternativesModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/60 p-4 flex items-center justify-center"
            onClick={closeAlternativesModal}
          >
            <motion.div
              initial={{ scale: 0.98, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.98, opacity: 0 }}
              className="w-full max-w-2xl max-h-[90vh] bg-white rounded-xl shadow-2xl overflow-hidden"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200">
                <h3 className="text-sm font-semibold text-slate-800 truncate">Alternatives for {alternativesModal.itemName}</h3>
                <Button variant="outline" className="bg-white" onClick={closeAlternativesModal}>Close</Button>
              </div>

              <div className="p-4 max-h-[70vh] overflow-auto bg-slate-50 space-y-3">
                <div className="border rounded-md p-3 bg-white space-y-2">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Search item name</p>
                  <div className="flex gap-2">
                    <Input
                      value={alternativesModal.searchName}
                      onChange={(e) => setAlternativesModal((prev) => (prev ? { ...prev, searchName: e.target.value } : prev))}
                      placeholder="Edit item name before searching"
                    />
                    <Button onClick={runAlternativesSearch} disabled={alternativesModal.isSearching}>
                      {alternativesModal.isSearching ? "Searching..." : "Search"}
                    </Button>
                  </div>
                  <p className="text-xs text-slate-500">You can customize the query before AI searches for alternatives.</p>
                </div>

                {alternativesModal.hasSearched && alternativesModal.alternatives.length === 0 && (
                  <div className="border rounded-md p-3 text-sm text-slate-600 bg-white">No alternatives found.</div>
                )}

                {alternativesModal.alternatives.map((alternative) => {
                  const rowKey = `${alternative.vendor}-${alternative.price}`;
                  const isApplying = applyingReplacementKey === rowKey;
                  return (
                    <div key={rowKey} className="border rounded-md p-3 bg-white">
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <p className="text-sm font-semibold text-slate-900">{alternative.vendor}</p>
                          <div className="mt-1 text-xs text-slate-600 space-y-1">
                            <p>Price: ${Number(alternative.price).toFixed(2)}</p>
                            {typeof alternative.rating === "number" && <p>Rating: {alternative.rating.toFixed(1)} / 5</p>}
                            {alternative.review_summary && <p className="break-words">{alternative.review_summary}</p>}
                            <p>
                              <a
                                href={alternative.product_url}
                                target="_blank"
                                rel="noreferrer"
                                className="text-blue-600 hover:text-blue-700 underline break-all"
                              >
                                View product link
                              </a>
                            </p>
                          </div>
                          <Badge variant="secondary" className="mt-2">{alternative.source === "company_history" ? "Company history" : "Online"}</Badge>
                        </div>

                        <Button
                          size="sm"
                          onClick={() => applyReplacement(alternative)}
                          disabled={isApplying}
                        >
                          {isApplying ? "Applying..." : "Apply replacement"}
                        </Button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
