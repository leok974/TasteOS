"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, ChevronsUpDown, Plus, Settings, Settings2 } from "lucide-react";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
    Command,
    CommandEmpty,
    CommandGroup,
    CommandInput,
    CommandItem,
    CommandList,
    CommandSeparator,
} from "@/components/ui/command";
import {
    Popover,
    PopoverContent,
    PopoverTrigger,
} from "@/components/ui/popover";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

import { useWorkspace } from "./WorkspaceProvider";
import { apiGet, apiPost, Workspace } from "@/lib/api";

export function WorkspaceSwitcher({ className }: { className?: string }) {
    const { workspaceId, setWorkspaceId } = useWorkspace();
    const router = useRouter();
    const [open, setOpen] = useState(false);
    const [showNewWorkspaceDialog, setShowNewWorkspaceDialog] = useState(false);
    const [newWorkspaceName, setNewWorkspaceName] = useState("");
    const queryClient = useQueryClient();

    const { data: workspaces } = useQuery({
        queryKey: ['workspaces'],
        queryFn: () => apiGet<Workspace[]>('/workspaces/'),
    });

    // Auto-select first workspace if none selected
    useEffect(() => {
        if (!workspaceId && workspaces && workspaces.length > 0) {
            setWorkspaceId(workspaces[0].id);
        }
    }, [workspaceId, workspaces, setWorkspaceId]);

    const selectedWorkspace = workspaces?.find(w => w.id === workspaceId) || workspaces?.[0];

    const createMutation = useMutation({
        mutationFn: (name: string) => apiPost<Workspace>('/workspaces/', { name }),
        onSuccess: (newWs) => {
            queryClient.setQueryData(['workspaces'], (old: Workspace[] | undefined) => {
                return old ? [...old, newWs] : [newWs];
            });
            setWorkspaceId(newWs.id);
            setOpen(false);
            setShowNewWorkspaceDialog(false);
            setNewWorkspaceName("");
        }
    });

    const handleCreate = (e: React.FormEvent) => {
        e.preventDefault();
        if (newWorkspaceName.trim()) {
            createMutation.mutate(newWorkspaceName);
        }
    };

    return (
        <Dialog open={showNewWorkspaceDialog} onOpenChange={setShowNewWorkspaceDialog}>
            <Popover open={open} onOpenChange={setOpen}>
                <PopoverTrigger asChild>
                    <Button
                        variant="outline"
                        role="combobox"
                        aria-expanded={open}
                        aria-label="Select a workspace"
                        className={cn("w-[200px] justify-between", className)}
                    >
                        {selectedWorkspace?.name || "Select workspace..."}
                        <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                    </Button>
                </PopoverTrigger>
                <PopoverContent className="w-[200px] p-0">
                    <Command>
                        <CommandInput placeholder="Search workspace..." />
                        <CommandList>
                            <CommandEmpty>No workspace found.</CommandEmpty>
                            <CommandGroup heading="Workspaces">
                                {workspaces?.map((workspace) => (
                                    <CommandItem
                                        key={workspace.id}
                                        value={workspace.name}
                                        onSelect={() => {
                                            setWorkspaceId(workspace.id);
                                            setOpen(false);
                                        }}
                                        className="text-sm"
                                    >
                                        <Check
                                            className={cn(
                                                "mr-2 h-4 w-4",
                                                selectedWorkspace?.id === workspace.id
                                                    ? "opacity-100"
                                                    : "opacity-0"
                                            )}
                                        />
                                        {workspace.name}
                                    </CommandItem>
                                ))}
                            </CommandGroup>
                            <CommandSeparator />
                            <CommandGroup heading="Workspace Settings">
                                <CommandItem
                                    value="settings-units"
                                    onSelect={() => {
                                        setOpen(false);
                                        router.push("/settings/units");
                                    }}
                                >
                                    <Settings className="mr-2 h-4 w-4" />
                                    Units & Measurements
                                </CommandItem>
                            </CommandGroup>
                            <CommandSeparator />
                            <CommandGroup>
                                <CommandItem
                                    value="create-workspace"
                                    onSelect={() => {
                                        setOpen(false);
                                        setShowNewWorkspaceDialog(true);
                                    }}
                                >
                                    <Plus className="mr-2 h-5 w-5" />
                                    Create Workspace
                                </CommandItem>
                            </CommandGroup>
                        </CommandList>
                    </Command>
                </PopoverContent>
            </Popover>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>Create Workspace</DialogTitle>
                    <DialogDescription>
                        Add a new workspace to organize your recipes and plans.
                    </DialogDescription>
                </DialogHeader>
                <form onSubmit={handleCreate}>
                    <div className="space-y-4 py-2 pb-4">
                        <div className="space-y-2">
                            <Label htmlFor="name">Workspace Name</Label>
                            <Input
                                id="name"
                                placeholder="e.g. Family Cookbook"
                                value={newWorkspaceName}
                                onChange={e => setNewWorkspaceName(e.target.value)}
                                autoFocus
                            />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setShowNewWorkspaceDialog(false)} type="button">Cancel</Button>
                        <Button type="submit" disabled={createMutation.isPending} >
                            {createMutation.isPending ? "Creating..." : "Create"}
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
}
