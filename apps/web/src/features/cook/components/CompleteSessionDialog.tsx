import { useState } from "react";
import { Loader2, Utensils, Calendar } from "lucide-react";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { useCookSessionComplete, CookCompleteRequest } from "../hooks";

interface CompleteSessionDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    sessionId: string;
    initialServingsTarget?: number;
    onComplete?: () => void;
}

export function CompleteSessionDialog({ 
    open, 
    onOpenChange, 
    sessionId, 
    initialServingsTarget = 4,
    onComplete 
}: CompleteSessionDialogProps) {
    const [servingsMade, setServingsMade] = useState(initialServingsTarget);
    const [createLeftovers, setCreateLeftovers] = useState(false);
    const [leftoverServings, setLeftoverServings] = useState(2);
    const [notes, setNotes] = useState("");
    
    const completeMutation = useCookSessionComplete();

    const handleSubmit = () => {
        const payload: CookCompleteRequest = {
            servings_made: servingsMade,
            create_leftover: createLeftovers,
            leftover_servings: createLeftovers ? leftoverServings : undefined,
            final_notes: notes
        };

        completeMutation.mutate({ sessionId, payload }, {
            onSuccess: () => {
                onOpenChange(false);
                onComplete?.();
            }
        });
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-md">
                <DialogHeader>
                    <DialogTitle>Finish Cooking</DialogTitle>
                    <DialogDescription>
                        Wrap up your session to save learnings and track leftovers.
                    </DialogDescription>
                </DialogHeader>
                
                <div className="space-y-6 py-4">
                    {/* Servings Made */}
                    <div className="grid grid-cols-2 gap-4 items-center">
                        <div className="space-y-1">
                            <Label htmlFor="servings-made">Servings Made</Label>
                            <p className="text-xs text-muted-foreground">How much did you yield?</p>
                        </div>
                        <Input 
                            id="servings-made" 
                            type="number" 
                            value={servingsMade} 
                            onChange={(e) => setServingsMade(Number(e.target.value))}
                            className="text-right"
                        />
                    </div>

                    {/* Leftovers Toggle */}
                    <div className="flex items-center justify-between space-x-2 rounded-lg border p-4">
                        <div className="space-y-0.5">
                            <Label className="text-base">Create Leftovers</Label>
                            <p className="text-sm text-muted-foreground">
                                Add to pantry automatically
                            </p>
                        </div>
                        <Switch
                            checked={createLeftovers}
                            onCheckedChange={setCreateLeftovers}
                        />
                    </div>

                    {/* Leftover Qty (Conditional) */}
                    {createLeftovers && (
                        <div className="grid grid-cols-2 gap-4 items-center pl-4 border-l-2 border-amber-100">
                             <div className="space-y-1">
                                <Label htmlFor="leftover-qty">Leftover Servings</Label>
                                <p className="text-xs text-muted-foreground">Saved for later</p>
                            </div>
                            <Input 
                                id="leftover-qty" 
                                type="number" 
                                value={leftoverServings} 
                                onChange={(e) => setLeftoverServings(Number(e.target.value))}
                                className="text-right"
                            />
                        </div>
                    )}

                    {/* Final Notes */}
                    <div className="space-y-2">
                        <Label htmlFor="notes">Cook Notes</Label>
                        <Textarea
                            id="notes"
                            placeholder="What went well? Any adjustments? e.g. 'Too salty, added sugar'"
                            value={notes}
                            onChange={(e) => setNotes(e.target.value)}
                            className="h-24 resize-none"
                        />
                    </div>
                </div>

                <DialogFooter>
                    <Button variant="outline" onClick={() => onOpenChange(false)}>
                        Cancel
                    </Button>
                    <Button onClick={handleSubmit} disabled={completeMutation.isPending} className="bg-green-600 hover:bg-green-700">
                        {completeMutation.isPending && (
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        )}
                        Complete Session
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
