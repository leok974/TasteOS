"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { setApiWorkspaceId } from "@/lib/api";

interface WorkspaceContextType {
    workspaceId: string | null;
    setWorkspaceId: (id: string | null) => void;
}

const WorkspaceContext = createContext<WorkspaceContextType | undefined>(undefined);

export function WorkspaceProvider({ children }: { children: React.ReactNode }) {
    const [workspaceId, setWorkspaceIdState] = useState<string | null>(null);
    const queryClient = useQueryClient();

    // Load from local storage on mount
    useEffect(() => {
        const stored = localStorage.getItem("tasteos.workspace_id");
        if (stored) {
            setWorkspaceIdState(stored);
            setApiWorkspaceId(stored);
        }
    }, []);

    const setWorkspaceId = (id: string | null) => {
        setWorkspaceIdState(id);
        if (id) {
            localStorage.setItem("tasteos.workspace_id", id);
            setApiWorkspaceId(id);
        } else {
            localStorage.removeItem("tasteos.workspace_id");
            setApiWorkspaceId(null);
        }

        // Invalidate all queries to refresh data for new workspace
        queryClient.invalidateQueries();
    };

    return (
        <WorkspaceContext.Provider value={{ workspaceId, setWorkspaceId }}>
            {children}
        </WorkspaceContext.Provider>
    );
}

export function useWorkspace() {
    const context = useContext(WorkspaceContext);
    if (context === undefined) {
        throw new Error("useWorkspace must be used within a WorkspaceProvider");
    }
    return context;
}
