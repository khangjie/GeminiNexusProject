import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Bot, Sparkles, Plus, Users, Mail, UserX, Trash2 } from "lucide-react";
import { Card } from "../../components/ui/Card";
import { Badge } from "../../components/ui/Badge";
import { Input } from "../../components/ui/Input";
import { Button } from "../../components/ui/Button";
import {
  createPreApprovedItem,
  createRule,
  deletePreApprovedItem,
  deleteRule,
  inviteWorker,
  listPreApprovedItems,
  listRules,
  listWorkers,
  removeWorker,
  updatePreApprovedItem,
  updateRule,
} from "../../lib/api";

type Section = "rules" | "preapproved" | "workers";

interface EditableRule {
  id: string;
  name: string;
  prompt: string;
  applies_to_preapproved: boolean;
  is_active: boolean;
}

interface EditablePreApproved {
  id: string;
  item_name: string;
  amount_limit: number | null;
  note: string | null;
  custom_variables: Array<{ key: string; value: string }>;
  is_active: boolean;
}

function recordToVariableRows(input?: Record<string, string> | null): Array<{ key: string; value: string }> {
  return Object.entries(input || {}).map(([key, value]) => ({ key, value }));
}

function variableRowsToRecord(rows: Array<{ key: string; value: string }>): Record<string, string> {
  const output: Record<string, string> = {};
  rows.forEach((row) => {
    const key = row.key.trim();
    if (!key) {
      return;
    }
    output[key] = row.value;
  });
  return output;
}

export default function AiSettings() {
  const [activeSection, setActiveSection] = useState<Section>("rules");
  const [rules, setRules] = useState<EditableRule[]>([]);
  const [originalRules, setOriginalRules] = useState<Record<string, EditableRule>>({});
  const [preApprovedItems, setPreApprovedItems] = useState<EditablePreApproved[]>([]);
  const [originalPreApprovedItems, setOriginalPreApprovedItems] = useState<Record<string, EditablePreApproved>>({});
  const [workers, setWorkers] = useState<Array<{ id: string; email: string; name: string }>>([]);
  const [newWorkerEmail, setNewWorkerEmail] = useState("");
  const [newWorkerName, setNewWorkerName] = useState("");
  const [newRuleName, setNewRuleName] = useState("");
  const [newRulePrompt, setNewRulePrompt] = useState("");
  const [newRuleAppliesToPreApproved, setNewRuleAppliesToPreApproved] = useState(true);
  const [newPreApprovedName, setNewPreApprovedName] = useState("");
  const [newPreApprovedLimit, setNewPreApprovedLimit] = useState("");
  const [newPreApprovedNote, setNewPreApprovedNote] = useState("");
  const [newVariableKey, setNewVariableKey] = useState("");
  const [newVariableValue, setNewVariableValue] = useState("");
  const [newPreApprovedVariables, setNewPreApprovedVariables] = useState<Array<{ key: string; value: string }>>([]);
  const [error, setError] = useState("");

  const loadData = () => {
    setError("");
    Promise.all([listRules(), listPreApprovedItems(), listWorkers()])
      .then(([rulesResult, preApprovedResult, workersResult]) => {
        const nextRules = rulesResult.map((rule) => ({
          id: rule.id,
          name: rule.name,
          prompt: rule.prompt,
          applies_to_preapproved: rule.applies_to_preapproved,
          is_active: rule.is_active,
        }));
        const nextOriginalRules = Object.fromEntries(nextRules.map((rule) => [rule.id, structuredClone(rule)]));
        setRules(nextRules);
        setOriginalRules(nextOriginalRules);

        const nextPreApproved = preApprovedResult.map((item) => ({
          id: item.id,
          item_name: item.item_name,
          amount_limit: item.amount_limit,
          note: item.note,
          custom_variables: recordToVariableRows(item.custom_variables),
          is_active: item.is_active,
        }));
        const nextOriginalPreApproved = Object.fromEntries(nextPreApproved.map((item) => [item.id, structuredClone(item)]));
        setPreApprovedItems(nextPreApproved);
        setOriginalPreApprovedItems(nextOriginalPreApproved);
        setWorkers(
          workersResult.map((worker) => ({
            id: worker.id,
            email: worker.email,
            name: worker.name,
          })),
        );
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load settings"));
  };

  const isRuleDirty = (rule: EditableRule) => {
    const original = originalRules[rule.id];
    if (!original) {
      return false;
    }
    return (
      original.name !== rule.name ||
      original.prompt !== rule.prompt ||
      original.applies_to_preapproved !== rule.applies_to_preapproved ||
      original.is_active !== rule.is_active
    );
  };

  const isPreApprovedDirty = (item: EditablePreApproved) => {
    const original = originalPreApprovedItems[item.id];
    if (!original) {
      return false;
    }

    return (
      original.item_name !== item.item_name ||
      original.amount_limit !== item.amount_limit ||
      (original.note ?? "") !== (item.note ?? "") ||
      original.is_active !== item.is_active ||
      JSON.stringify(variableRowsToRecord(original.custom_variables)) !== JSON.stringify(variableRowsToRecord(item.custom_variables))
    );
  };

  useEffect(() => {
    loadData();
  }, []);

  const saveRule = async (rule: EditableRule) => {
    try {
      await updateRule(rule.id, {
        name: rule.name,
        prompt: rule.prompt,
        applies_to_preapproved: rule.applies_to_preapproved,
        is_active: rule.is_active,
      });
      loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save rule");
    }
  };

  const addRule = async () => {
    if (!newRuleName.trim() || !newRulePrompt.trim()) {
      return;
    }
    try {
      await createRule({
        name: newRuleName.trim(),
        prompt: newRulePrompt.trim(),
        applies_to_preapproved: newRuleAppliesToPreApproved,
        is_active: true,
      });
      setNewRuleName("");
      setNewRulePrompt("");
      setNewRuleAppliesToPreApproved(true);
      loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create rule");
    }
  };

  const removeRuleItem = async (id: string) => {
    try {
      await deleteRule(id);
      loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete rule");
    }
  };

  const addPreApproved = async () => {
    if (!newPreApprovedName.trim()) {
      return;
    }
    try {
      await createPreApprovedItem({
        item_name: newPreApprovedName.trim(),
        amount_limit: newPreApprovedLimit.trim() ? Number(newPreApprovedLimit) : null,
        note: newPreApprovedNote.trim() || null,
        custom_variables: variableRowsToRecord(newPreApprovedVariables),
        is_active: true,
      });
      setNewPreApprovedName("");
      setNewPreApprovedLimit("");
      setNewPreApprovedNote("");
      setNewVariableKey("");
      setNewVariableValue("");
      setNewPreApprovedVariables([]);
      loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create pre-approved item");
    }
  };

  const savePreApproved = async (item: EditablePreApproved) => {
    try {
      await updatePreApprovedItem(item.id, {
        item_name: item.item_name,
        amount_limit: item.amount_limit,
        note: item.note,
        custom_variables: variableRowsToRecord(item.custom_variables),
        is_active: item.is_active,
      });
      loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save pre-approved item");
    }
  };

  const removePreApproved = async (itemId: string) => {
    try {
      await deletePreApprovedItem(itemId);
      loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete pre-approved item");
    }
  };

  const addNewPreApprovedVariable = () => {
    const key = newVariableKey.trim();
    if (!key) {
      return;
    }
    setNewPreApprovedVariables((prev) => [...prev, { key, value: newVariableValue }]);
    setNewVariableKey("");
    setNewVariableValue("");
  };

  const addWorker = async () => {
    if (!newWorkerEmail.trim()) {
      return;
    }
    try {
      await inviteWorker({
        email: newWorkerEmail.trim(),
        name: newWorkerName.trim() || newWorkerEmail.trim().split("@")[0],
      });
      setNewWorkerEmail("");
      setNewWorkerName("");
      loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to invite worker");
    }
  };

  const deleteWorker = async (workerId: string) => {
    try {
      await removeWorker(workerId);
      loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to remove worker");
    }
  };

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-8 relative z-10 w-full h-full pb-20">
      <header className="flex md:flex-row flex-col gap-4 md:items-end justify-between">
        <div>
          <motion.h1 initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="text-3xl font-bold tracking-tight text-slate-900">
            AI Agent Settings
          </motion.h1>
          <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.1 }} className="text-slate-500 mt-1">
            Configure live rules and worker access for your company.
          </motion.p>
          <p className="text-xs text-slate-400 mt-2">Changes reload automatically after save, add, or delete.</p>
        </div>
      </header>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        <div className="lg:col-span-4 space-y-4">
          <Card className="bg-gradient-to-br from-primary-600 to-purple-700 text-white p-6 shadow-lg border-transparent">
            <div className="w-12 h-12 bg-white/20 rounded-xl flex items-center justify-center mb-4 backdrop-blur-sm">
              <Bot size={28} className="text-white" />
            </div>
            <h3 className="text-xl font-bold tracking-tight">Nexus AI Core</h3>
            <p className="text-white/80 mt-2 text-sm">Rules and workers now persist to your backend data store.</p>
          </Card>

          <div className="flex flex-col gap-2">
            <button
              onClick={() => setActiveSection("rules")}
              className={`flex items-center justify-between p-4 rounded-xl shadow-sm border font-medium transition-all ${activeSection === "rules" ? "bg-white border-primary-200 text-primary-700 font-semibold" : "bg-white/50 hover:bg-white border-slate-200 text-slate-700"}`}
            >
              <div className="flex items-center gap-3">
                <Sparkles size={18} className={activeSection === "rules" ? "text-primary-500" : "text-slate-400"} />
                Auto-Approval Rules
              </div>
              <Badge className="border-none font-bold bg-slate-100 text-slate-500">{rules.length}</Badge>
            </button>

            <button
              onClick={() => setActiveSection("preapproved")}
              className={`flex items-center justify-between p-4 rounded-xl shadow-sm border font-medium transition-all ${activeSection === "preapproved" ? "bg-white border-primary-200 text-primary-700 font-semibold" : "bg-white/50 hover:bg-white border-slate-200 text-slate-700"}`}
            >
              <div className="flex items-center gap-3">
                <Bot size={18} className={activeSection === "preapproved" ? "text-primary-500" : "text-slate-400"} />
                Pre-Approved Items
              </div>
              <Badge className="border-none font-bold bg-slate-100 text-slate-500">{preApprovedItems.length}</Badge>
            </button>

            <button
              onClick={() => setActiveSection("workers")}
              className={`flex items-center justify-between p-4 rounded-xl shadow-sm border font-medium transition-all ${activeSection === "workers" ? "bg-white border-primary-200 text-primary-700 font-semibold" : "bg-white/50 hover:bg-white border-slate-200 text-slate-700"}`}
            >
              <div className="flex items-center gap-3">
                <Users size={18} className={activeSection === "workers" ? "text-primary-500" : "text-slate-400"} />
                Workers
              </div>
              <Badge className="border-none font-bold bg-slate-100 text-slate-500">{workers.length}</Badge>
            </button>
          </div>
        </div>

        <div className="lg:col-span-8 space-y-6">
          {activeSection === "rules" && (
            <Card className="shadow-sm border-slate-200 bg-white">
              <div className="flex justify-between items-center mb-6 pb-4 border-b border-slate-100">
                <div>
                  <h2 className="text-xl font-bold text-slate-800 flex items-center gap-2">
                    <Sparkles className="text-primary-500" size={24} />
                    Auto-Approval Prompt Rules
                  </h2>
                  <p className="text-sm text-slate-500 mt-1">These prompts are used by the decision pipeline.</p>
                </div>
              </div>

              <div className="p-4 rounded-xl border border-primary-100 bg-primary-50/30 mb-6 space-y-3">
                <Input placeholder="Rule name" value={newRuleName} onChange={(e) => setNewRuleName(e.target.value)} className="bg-white" />
                <textarea
                  placeholder="Rule prompt"
                  value={newRulePrompt}
                  onChange={(e) => setNewRulePrompt(e.target.value)}
                  className="w-full h-24 p-3 rounded-lg border border-slate-200 bg-white text-sm text-slate-600 focus:outline-none focus:ring-2 focus:ring-primary-500/50 resize-none"
                />
                <label className="flex items-center gap-2 text-sm text-slate-600">
                  <input
                    type="checkbox"
                    checked={newRuleAppliesToPreApproved}
                    onChange={(e) => setNewRuleAppliesToPreApproved(e.target.checked)}
                    className="h-4 w-4 rounded border-slate-300 text-primary-600 focus:ring-primary-500"
                  />
                  Apply this rule to pre-approved items
                </label>
                <Button onClick={addRule}>
                  <Plus size={16} className="mr-1" /> Add Rule
                </Button>
              </div>

              <div className="space-y-4">
                {rules.map((rule) => (
                  <div key={rule.id} className="p-5 rounded-xl border border-primary-100 bg-slate-50/50">
                    <div className="flex justify-between items-start mb-3">
                      <Input
                        value={rule.name}
                        onChange={(e) => setRules((prev) => prev.map((r) => (r.id === rule.id ? { ...r, name: e.target.value } : r)))}
                        className="font-semibold bg-white w-[300px]"
                      />
                      <div className="flex items-center gap-3">
                        <button
                          className={`px-3 py-1 rounded-md text-xs font-semibold ${rule.is_active ? "bg-emerald-100 text-emerald-700" : "bg-slate-200 text-slate-600"}`}
                          onClick={() => setRules((prev) => prev.map((r) => (r.id === rule.id ? { ...r, is_active: !r.is_active } : r)))}
                        >
                          {rule.is_active ? "Active" : "Inactive"}
                        </button>
                        <button className="text-slate-400 hover:text-red-500 transition-colors" onClick={() => removeRuleItem(rule.id)}>
                          <Trash2 size={18} />
                        </button>
                      </div>
                    </div>

                    <textarea
                      value={rule.prompt}
                      onChange={(e) => setRules((prev) => prev.map((r) => (r.id === rule.id ? { ...r, prompt: e.target.value } : r)))}
                      className="w-full h-24 p-3 rounded-lg border border-slate-200 bg-white text-sm text-slate-600 focus:outline-none focus:ring-2 focus:ring-primary-500/50 resize-none"
                    />
                    <label className="mt-3 flex items-center gap-2 text-sm text-slate-600">
                      <input
                        type="checkbox"
                        checked={rule.applies_to_preapproved}
                        onChange={(e) =>
                          setRules((prev) =>
                            prev.map((r) =>
                              r.id === rule.id ? { ...r, applies_to_preapproved: e.target.checked } : r,
                            ),
                          )
                        }
                        className="h-4 w-4 rounded border-slate-300 text-primary-600 focus:ring-primary-500"
                      />
                      Apply this rule to pre-approved items
                    </label>
                    {isRuleDirty(rule) && (
                      <div className="mt-3">
                        <Button size="sm" onClick={() => saveRule(rule)}>Save Rule</Button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </Card>
          )}

          {activeSection === "preapproved" && (
            <Card className="shadow-sm border-slate-200 bg-white">
              <div className="flex justify-between items-center mb-6 pb-4 border-b border-slate-100">
                <div>
                  <h2 className="text-xl font-bold text-slate-800 flex items-center gap-2">
                    <Bot className="text-primary-500" size={24} />
                    Pre-Approved Item List
                  </h2>
                  <p className="text-sm text-slate-500 mt-1">Items recognized by AI before standard approval rule checks.</p>
                </div>
              </div>

              <div className="p-4 rounded-xl border border-primary-100 bg-primary-50/30 mb-6 space-y-3">
                <Input
                  placeholder="Item name (e.g. Apple)"
                  value={newPreApprovedName}
                  onChange={(e) => setNewPreApprovedName(e.target.value)}
                  className="bg-white"
                />
                <Input
                  placeholder="Amount limit (optional)"
                  value={newPreApprovedLimit}
                  onChange={(e) => setNewPreApprovedLimit(e.target.value)}
                  className="bg-white"
                />
                <textarea
                  placeholder="Note (optional)"
                  value={newPreApprovedNote}
                  onChange={(e) => setNewPreApprovedNote(e.target.value)}
                  className="w-full h-20 p-3 rounded-lg border border-slate-200 bg-white text-sm text-slate-600 focus:outline-none focus:ring-2 focus:ring-primary-500/50 resize-none"
                />

                <div className="grid grid-cols-1 md:grid-cols-[1fr_1fr_auto] gap-2">
                  <Input
                    placeholder="Variable name"
                    value={newVariableKey}
                    onChange={(e) => setNewVariableKey(e.target.value)}
                    className="bg-white"
                  />
                  <Input
                    placeholder="Variable value"
                    value={newVariableValue}
                    onChange={(e) => setNewVariableValue(e.target.value)}
                    className="bg-white"
                  />
                  <Button type="button" variant="outline" className="bg-white" onClick={addNewPreApprovedVariable}>
                    Add Variable
                  </Button>
                </div>

                {newPreApprovedVariables.length > 0 && (
                  <div className="space-y-2 rounded-lg border border-slate-200 bg-white p-3">
                    {newPreApprovedVariables.map((variable, idx) => (
                      <div key={`${variable.key}-${idx}`} className="flex items-center justify-between text-sm">
                        <span className="font-medium text-slate-700">{variable.key}</span>
                        <div className="flex items-center gap-3">
                          <span className="text-slate-600">{variable.value}</span>
                          <button
                            type="button"
                            className="text-red-600 text-xs"
                            onClick={() => setNewPreApprovedVariables((prev) => prev.filter((_, rowIdx) => rowIdx !== idx))}
                          >
                            Remove
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                <Button onClick={addPreApproved}>
                  <Plus size={16} className="mr-1" /> Add Pre-Approved Item
                </Button>
              </div>

              <div className="space-y-4">
                {preApprovedItems.map((item) => (
                  <div key={item.id} className="p-5 rounded-xl border border-primary-100 bg-slate-50/50">
                    <div className="flex justify-between items-start mb-3 gap-3">
                      <Input
                        value={item.item_name}
                        onChange={(e) =>
                          setPreApprovedItems((prev) =>
                            prev.map((x) => (x.id === item.id ? { ...x, item_name: e.target.value } : x)),
                          )
                        }
                        className="font-semibold bg-white"
                      />
                      <div className="flex items-center gap-3">
                        <button
                          className={`px-3 py-1 rounded-md text-xs font-semibold ${item.is_active ? "bg-emerald-100 text-emerald-700" : "bg-slate-200 text-slate-600"}`}
                          onClick={() =>
                            setPreApprovedItems((prev) =>
                              prev.map((x) => (x.id === item.id ? { ...x, is_active: !x.is_active } : x)),
                            )
                          }
                        >
                          {item.is_active ? "Active" : "Inactive"}
                        </button>
                        <button className="text-slate-400 hover:text-red-500 transition-colors" onClick={() => removePreApproved(item.id)}>
                          <Trash2 size={18} />
                        </button>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      <Input
                        placeholder="Amount limit"
                        value={item.amount_limit ?? ""}
                        onChange={(e) =>
                          setPreApprovedItems((prev) =>
                            prev.map((x) =>
                              x.id === item.id
                                ? {
                                    ...x,
                                    amount_limit: e.target.value.trim() ? Number(e.target.value) : null,
                                  }
                                : x,
                            ),
                          )
                        }
                        className="bg-white"
                      />
                      <Input
                        placeholder="Note"
                        value={item.note ?? ""}
                        onChange={(e) =>
                          setPreApprovedItems((prev) =>
                            prev.map((x) => (x.id === item.id ? { ...x, note: e.target.value } : x)),
                          )
                        }
                        className="bg-white"
                      />
                    </div>

                    <div className="mt-3 space-y-2 rounded-lg border border-slate-200 bg-white p-3">
                      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Custom Variables</p>
                      {item.custom_variables.map((variable, idx) => (
                        <div key={`${item.id}-var-${idx}`} className="grid grid-cols-1 md:grid-cols-[1fr_1fr_auto] gap-2">
                          <Input
                            placeholder="Variable name"
                            value={variable.key}
                            onChange={(e) =>
                              setPreApprovedItems((prev) =>
                                prev.map((x) =>
                                  x.id === item.id
                                    ? {
                                        ...x,
                                        custom_variables: x.custom_variables.map((entry, entryIdx) =>
                                          entryIdx === idx ? { ...entry, key: e.target.value } : entry,
                                        ),
                                      }
                                    : x,
                                ),
                              )
                            }
                            className="bg-white"
                          />
                          <Input
                            placeholder="Variable value"
                            value={variable.value}
                            onChange={(e) =>
                              setPreApprovedItems((prev) =>
                                prev.map((x) =>
                                  x.id === item.id
                                    ? {
                                        ...x,
                                        custom_variables: x.custom_variables.map((entry, entryIdx) =>
                                          entryIdx === idx ? { ...entry, value: e.target.value } : entry,
                                        ),
                                      }
                                    : x,
                                ),
                              )
                            }
                            className="bg-white"
                          />
                          <Button
                            type="button"
                            variant="outline"
                            className="bg-white"
                            onClick={() =>
                              setPreApprovedItems((prev) =>
                                prev.map((x) =>
                                  x.id === item.id
                                    ? {
                                        ...x,
                                        custom_variables: x.custom_variables.filter((_, entryIdx) => entryIdx !== idx),
                                      }
                                    : x,
                                ),
                              )
                            }
                          >
                            Remove
                          </Button>
                        </div>
                      ))}

                      <Button
                        type="button"
                        variant="outline"
                        className="bg-white"
                        onClick={() =>
                          setPreApprovedItems((prev) =>
                            prev.map((x) =>
                              x.id === item.id
                                ? {
                                    ...x,
                                    custom_variables: [...x.custom_variables, { key: "", value: "" }],
                                  }
                                : x,
                            ),
                          )
                        }
                      >
                        Add Variable
                      </Button>
                    </div>

                    {isPreApprovedDirty(item) && (
                      <div className="mt-3">
                        <Button size="sm" onClick={() => savePreApproved(item)}>Save Item</Button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </Card>
          )}

          {activeSection === "workers" && (
            <Card className="shadow-sm border-slate-200 bg-white">
              <div className="mb-6 pb-4 border-b border-slate-100">
                <h2 className="text-xl font-bold text-slate-800 flex items-center gap-2">
                  <Users className="text-primary-500" size={24} />
                  Workers
                </h2>
                <p className="text-sm text-slate-500 mt-1">Invite workers by email. They can submit claims once added.</p>
              </div>

              <div className="p-4 rounded-xl border border-primary-100 bg-primary-50/30 mb-6">
                <p className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2"><Mail size={15} /> Invite a New Worker</p>
                <div className="flex flex-col sm:flex-row gap-3">
                  <Input placeholder="worker@company.com" value={newWorkerEmail} onChange={(e) => setNewWorkerEmail(e.target.value)} className="flex-1 bg-white" />
                  <Input placeholder="Display name" value={newWorkerName} onChange={(e) => setNewWorkerName(e.target.value)} className="flex-1 bg-white" />
                  <Button className="bg-primary-600 hover:bg-primary-700 text-white whitespace-nowrap" onClick={addWorker}>
                    <Plus size={16} className="mr-1" /> Add Worker
                  </Button>
                </div>
              </div>

              {workers.length === 0 ? (
                <p className="text-slate-500 text-sm italic text-center py-6">No workers added yet.</p>
              ) : (
                <div className="space-y-2">
                  {workers.map((worker) => (
                    <div key={worker.id} className="flex items-center justify-between p-3 rounded-xl border border-slate-200 bg-slate-50/50">
                      <div className="flex items-center gap-3">
                        <div className="w-9 h-9 rounded-full bg-primary-100 text-primary-700 font-bold flex items-center justify-center text-sm uppercase">
                          {worker.name.charAt(0)}
                        </div>
                        <div>
                          <p className="font-semibold text-slate-800 text-sm">{worker.name}</p>
                          <p className="text-xs text-slate-500">{worker.email}</p>
                        </div>
                      </div>
                      <button onClick={() => deleteWorker(worker.id)} className="text-slate-400 hover:text-red-500 transition-colors" title="Remove worker">
                        <UserX size={18} />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
