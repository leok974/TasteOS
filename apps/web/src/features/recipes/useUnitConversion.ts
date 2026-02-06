import { useMutation, useQueryClient } from "@tanstack/react-query";
import { API_BASE } from "@/lib/api";

type UnitType = "mass" | "volume" | "count" | "unknown";

interface ConvertRequest {
    qty: number;
    from_unit: number | string; // Handle legacy numeric or string
    to_unit?: string;
    target_system?: "metric" | "us_customary" | "imperial";
    ingredient_name?: string;
    force_cross_type?: boolean;
}

interface ConvertResponse {
    qty: number;
    unit: string;
    confidence: "high" | "medium" | "low" | "none";
    note?: string;
    is_approx: boolean;
}

async function fetchConversion(req: ConvertRequest): Promise<ConvertResponse> {
    const headers = new Headers();
    headers.set('Content-Type', 'application/json');
    const wsId = typeof window !== 'undefined' ? localStorage.getItem('tasteos.workspace_id') : null;
    if (wsId) headers.set('X-Workspace-Id', wsId);

    const res = await fetch(`${API_BASE}/units/convert`, {
        method: 'POST',
        headers,
        body: JSON.stringify(req),
    });

    if (!res.ok) throw new Error('Conversion failed');
    return res.json();
}

/**
 * Hook to convert a single ingredient quantity.
 */
export function useUnitConversion() {
    return useMutation({
        mutationFn: fetchConversion
    });
}
