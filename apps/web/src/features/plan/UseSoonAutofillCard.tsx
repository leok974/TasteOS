"use client";

import { useState } from "react";
import { Sparkles, Calendar, ArrowRight, Check, X, Clock, Leaf } from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { format, parseISO } from "date-fns";

import { Button } from "@/components/ui/button";
import { cva } from "class-variance-authority";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { generateAutofillProposals, applyAutofillProposals, AutofillResponse, AutofillProposal } from "@/lib/api";
import { useToast } from "@/hooks/use-toast";
import { cn } from "@/lib/cn";

export function UseSoonAutofillCard({ weekStart }: { weekStart: string }) {
    const [proposals, setProposals] = useState<AutofillProposal[] | null>(null);
    const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
    const [isDismissed, setIsDismissed] = useState(false);
    const [wasteReductionMode, setWasteReductionMode] = useState(true);

    const { toast } = useToast();
    const queryClient = useQueryClient();

    const generateMutation = useMutation({
        mutationFn: async () => generateAutofillProposals(weekStart, { strictVariety: !wasteReductionMode }),
        onSuccess: (data) => {
            if (data.proposals.length === 0) {
                toast({ title: "No suggestions", description: "Couldn't find good matches for expiring items." });
            } else {
                setProposals(data.proposals);
                // Auto-select all by default
                setSelectedIds(new Set(data.proposals.map(p => p.proposal_id)));
            }
        },
        onError: () => {
            toast({ title: "Error", description: "Failed to generate suggestions.", variant: "destructive" });
        }
    });

    const applyMutation = useMutation({
        mutationFn: async () => {
            if (!proposals) return;
            const changes = proposals
                .filter(p => selectedIds.has(p.proposal_id))
                .map(p => ({
                    plan_entry_id: p.plan_entry_id,
                    recipe_id: p.after.recipe_id
                }));

            return applyAutofillProposals(weekStart, changes);
        },
        onSuccess: (data) => {
            if (data) {
                toast({
                    title: "Plan Updated",
                    description: `Applied ${data.applied} recipe swaps.`,
                    className: "bg-green-600 text-white"
                });
                setProposals(null);
                queryClient.invalidateQueries({ queryKey: ["plan"] });
                queryClient.invalidateQueries({ queryKey: ["grocery"] });
            }
        }
    });

    if (isDismissed) return null;

    if (!proposals) {
        return (
            <Card className="bg-gradient-to-r from-emerald-50 to-teal-50 dark:from-emerald-950/30 dark:to-teal-950/30 border-emerald-100 dark:border-emerald-900">
                <CardContent className="p-4 flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <div className="h-10 w-10 rounded-full bg-emerald-100 dark:bg-emerald-900 flex items-center justify-center text-emerald-600 dark:text-emerald-400">
                            <Leaf className="h-5 w-5" />
                        </div>
                        <div>
                            <h4 className="font-semibold text-emerald-900 dark:text-emerald-100">Reduce Waste & Save Time</h4>
                            <p className="text-sm text-emerald-700 dark:text-emerald-300">
                                Auto-fill empty slots with recipes using your expiring pantry items.
                            </p>
                        </div>
                    </div>
                    <div className="flex items-center gap-4">
                        <div className="flex items-center gap-2">
                            <Checkbox
                                id="waste-mode"
                                checked={wasteReductionMode}
                                onChange={(e) => setWasteReductionMode(e.target.checked)}
                                className="border-emerald-600 data-[state=checked]:bg-emerald-600 data-[state=checked]:text-white"
                            />
                            <label htmlFor="waste-mode" className="text-sm font-medium text-emerald-800 cursor-pointer select-none">
                                Prioritize Waste
                            </label>
                        </div>
                        <Button
                            onClick={() => generateMutation.mutate()}
                            disabled={generateMutation.isPending}
                            className="bg-emerald-600 hover:bg-emerald-700 text-white"
                            data-testid="autofill-generate"
                        >
                            {generateMutation.isPending ? "Scanning..." : "Review Suggestions"}
                            {!generateMutation.isPending && <Sparkles className="ml-2 h-4 w-4" />}
                        </Button>
                    </div>
                </CardContent>
            </Card>
        );
    }

    return (
        <Card className="border-emerald-200 dark:border-emerald-800 shadow-md">
            <CardHeader className="pb-3 border-b border-emerald-100 dark:border-emerald-900/50 bg-emerald-50/50 dark:bg-emerald-950/20">
                <div className="flex justify-between items-start">
                    <div>
                        <CardTitle className="text-lg flex items-center gap-2 text-emerald-800 dark:text-emerald-200">
                            <Sparkles className="h-5 w-5" />
                            Suggested Swaps
                        </CardTitle>
                        <p className="text-sm text-slate-500">
                            We found {proposals.length} ways to use up your ingredients this week.
                        </p>
                    </div>
                    <Button variant="ghost" className="h-8 w-8 p-0" onClick={() => setIsDismissed(true)}>
                        <X className="h-4 w-4" />
                    </Button>
                </div>
            </CardHeader>
            <CardContent className="p-4 space-y-4">
                <div className="grid gap-3">
                    {proposals.map((proposal) => (
                        <div
                            key={proposal.proposal_id}
                            className="flex items-start gap-3 p-3 rounded-lg border bg-card hover:bg-slate-50 dark:hover:bg-slate-900 transition-colors"
                            data-testid={`autofill-proposal-${proposal.proposal_id}`}
                        >
                            <Checkbox
                                checked={selectedIds.has(proposal.proposal_id)}
                                onChange={(e) => {
                                    const checked = e.target.checked;
                                    const next = new Set(selectedIds);
                                    if (checked) next.add(proposal.proposal_id);
                                    else next.delete(proposal.proposal_id);
                                    setSelectedIds(next);
                                }}
                                className="mt-1"
                                data-testid={`autofill-approve-${proposal.proposal_id}`}
                            />

                            <div className="flex-1 space-y-2">
                                <div className="flex justify-between text-sm">
                                    <span className="font-medium text-slate-500">
                                        {format(parseISO(proposal.date), "EEE, MMM d")} • {proposal.meal}
                                    </span>
                                    {proposal.score > 1.5 && (
                                        <Badge variant="secondary" className="bg-emerald-100 text-emerald-800 hover:bg-emerald-100 text-[10px] h-5">
                                            Great Match
                                        </Badge>
                                    )}
                                </div>

                                <div className="flex items-center gap-2">
                                    <div className="flex-1 min-w-0">
                                        <div className="text-sm line-through text-slate-400 truncate">
                                            {proposal.before ? proposal.before.title : "Empty Slot"}
                                        </div>
                                    </div>
                                    <ArrowRight className="h-4 w-4 text-slate-300 flex-shrink-0" />
                                    <div className="flex-1 min-w-0">
                                        <div className="font-semibold truncate text-emerald-700 dark:text-emerald-400">
                                            {proposal.after.title}
                                        </div>
                                    </div>
                                </div>

                                <div className="flex flex-wrap gap-2 pt-1">
                                    {proposal.reasons.map((r, i) => (
                                        <Badge key={i} variant="outline" className="text-xs font-normal bg-slate-50">
                                            {r.kind === "use_soon_match" && <span className="mr-1">🍃 Uses {r.value}</span>}
                                            {r.kind === "expires_in_days" && <span className="mr-1 text-amber-600">⚠ Expires in {r.value}d</span>}
                                            {r.kind === "quick" && <span className="mr-1 flex items-center"><Clock className="w-3 h-3 mr-1" /> {r.value}m</span>}
                                            {r.kind === "duplicate_in_week" && <span className="mr-1 text-orange-600">Repeated Dish</span>}
                                            {r.kind === "waste_reduction_override" && <span className="mr-1 text-red-600 font-medium">Urgent Rescue</span>}
                                        </Badge>
                                    ))}
                                </div>
                            </div>
                        </div>
                    ))}
                </div>

                <div className="flex justify-end gap-3 pt-2">
                    <Button variant="outline" onClick={() => setProposals(null)}>
                        Cancel
                    </Button>
                    <Button
                        onClick={() => applyMutation.mutate()}
                        disabled={selectedIds.size === 0 || applyMutation.isPending}
                        data-testid="autofill-apply"
                    >
                        {applyMutation.isPending ? "Applying..." : `Apply ${selectedIds.size} Changes`}
                    </Button>
                </div>
            </CardContent>
        </Card>
    );
}
