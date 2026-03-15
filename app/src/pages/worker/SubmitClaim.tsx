import { useMemo, useRef, useState } from "react";
import { motion } from "framer-motion";
import { AlertCircle, CheckCircle2, UploadCloud } from "lucide-react";
import { Card } from "../../components/ui/Card";
import { Button } from "../../components/ui/Button";
import { Badge } from "../../components/ui/Badge";
import { uploadReceipt } from "../../lib/api";

export default function SubmitClaim() {
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const dropRef = useRef<HTMLDivElement>(null);
  const [receiptType, setReceiptType] = useState<"paid_expense" | "proposal">("paid_expense");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<Awaited<ReturnType<typeof uploadReceipt>> | null>(null);

  const canSubmit = useMemo(() => !!file && !loading, [file, loading]);

  // Drag-and-drop and paste handlers
  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handlePaste = (e: React.ClipboardEvent<HTMLDivElement>) => {
    const items = e.clipboardData.items;
    for (let i = 0; i < items.length; i++) {
      if (items[i].type.startsWith("image/")) {
        const file = items[i].getAsFile();
        if (file) {
          handleFile(file);
          break;
        }
      }
    }
  };

  const handleFile = (file: File) => {
    setFile(file);
    if (file.type.startsWith("image/")) {
      const url = URL.createObjectURL(file);
      setPreviewUrl(url);
    } else {
      setPreviewUrl(null);
    }
  };

  const handleSubmit = async () => {
    if (!file) {
      return;
    }
    setLoading(true);
    setError("");
    try {
      const response = await uploadReceipt(file, receiptType);
      setResult(response);
      setFile(null);
      setPreviewUrl(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-6 relative z-10 w-full h-full pb-20">
      <header>
        <motion.h1 initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="text-3xl font-bold tracking-tight text-slate-900">
          Submit Expense Claim
        </motion.h1>
        <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.1 }} className="text-slate-500 mt-1">
          Upload a receipt to trigger OCR and the ADK approval pipeline.
        </motion.p>
      </header>

      <Card className="space-y-4">
        <div>
          <label className="text-sm font-medium text-slate-700 mb-2 block">Receipt File</label>
          <div
            ref={dropRef}
            tabIndex={0}
            onDrop={handleDrop}
            onDragOver={(e) => e.preventDefault()}
            onPaste={handlePaste}
            className="flex flex-col items-center justify-center border-2 border-dashed border-primary-300 rounded-lg p-6 bg-primary-50/30 cursor-pointer transition hover:bg-primary-100/40 focus:outline-none"
            style={{ minHeight: 160 }}
            onClick={() => (dropRef.current?.querySelector('input[type=file]') as HTMLInputElement | null)?.click()}
          >
            {previewUrl ? (
              <img src={previewUrl} alt="Preview" className="max-h-32 mb-2 rounded shadow" />
            ) : (
              <>
                <UploadCloud size={36} className="text-primary-400 mb-2" />
                <span className="text-slate-600 text-sm">Drag & drop, paste, or click to select a receipt image or PDF</span>
              </>
            )}
            <input
              type="file"
              accept="image/*,.pdf"
              style={{ display: "none" }}
              onChange={(e) => {
                if (e.target.files?.[0]) handleFile(e.target.files[0]);
              }}
              tabIndex={-1}
            />
            {file && (
              <div className="mt-2 text-xs text-slate-500">{file.name}</div>
            )}
          </div>
        </div>

        <div>
          <label className="text-sm font-medium text-slate-700 mb-2 block">Receipt Type</label>
          <select
            value={receiptType}
            onChange={(e) => setReceiptType(e.target.value as "paid_expense" | "proposal")}
            className="flex h-10 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
          >
            <option value="paid_expense">Paid Expense</option>
            <option value="proposal">Proposal</option>
          </select>
        </div>

        {error && (
          <div className="text-sm text-red-600 flex items-center gap-2">
            <AlertCircle size={16} /> {error}
          </div>
        )}

        <Button className="w-full" disabled={!canSubmit} onClick={handleSubmit}>
          <UploadCloud size={16} className="mr-2" />
          {loading ? "Processing..." : "Upload & Process"}
        </Button>
      </Card>

      {result && (
        <Card className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xl font-bold text-slate-800">Processed Receipt</h3>
            <Badge variant="success" className="bg-emerald-100 text-emerald-700">
              <CheckCircle2 size={14} className="mr-1" /> Completed
            </Badge>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            <div><span className="font-medium">Vendor:</span> {result.receipt.vendor || "Unknown"}</div>
            <div><span className="font-medium">Amount:</span> {result.receipt.total_amount ?? 0}</div>
            <div><span className="font-medium">Status:</span> {result.receipt.status}</div>
            <div><span className="font-medium">AI Verdict:</span> {result.receipt.ai_verdict || "N/A"}</div>
          </div>

          {result.receipt.ai_reason && (
            <div className="text-sm text-slate-700 bg-slate-50 border border-slate-200 rounded-md p-3">
              <span className="font-medium">Reason:</span> {result.receipt.ai_reason}
            </div>
          )}

          <div>
            <h4 className="text-sm font-semibold text-slate-700 mb-2">Items</h4>
            <div className="space-y-2">
              {result.receipt.items.map((item) => (
                <div key={item.id} className="flex justify-between text-sm border rounded-md p-2">
                  <span>{item.name} {item.quantity && item.quantity > 1 ? `x${item.quantity}` : ""}</span>
                  <span>{item.price ?? 0}</span>
                </div>
              ))}
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}
