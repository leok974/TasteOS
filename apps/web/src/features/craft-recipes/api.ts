import { apiPost } from "@/lib/api";

export type ChatRole = "user" | "assistant";

export type RecipeDraft = {
  title: string;
  yield?: {
    servings?: number;
    servings_min?: number;
    servings_max?: number;
    unit?: string;
    notes?: string;
  };
  tags?: string[];
  equipment?: string[];
  ingredients: Array<{
    section?: string | null;
    quantity?: number | string | null;
    unit?: string | null;
    item: string;
    notes?: string | null;
  }>;
  steps: string[];
  storage?: Array<{ type?: string; duration?: string; instructions: string }>;
  reheat?: Array<{ method?: string; instructions?: string; notes?: string }>;
  nutrition_estimate?: any; // keep flexible; you already have multiple shapes
};

export type ChefChatRequest = {
  workspace_id: string;
  thread_id?: string;
  message: string;
  mode: "create" | "refine";
  recipe_id?: string;
  base_variant_id?: string;
};

export type ChefChatResponse = {
  assistant_message: string;
  recipe_draft?: RecipeDraft;
  suggested_label?: string;
  source: "ai" | "heuristic" | "user";
  model_id?: string;
  prompt_version?: string;
  thread_id?: string;
};

export async function chefChat(req: ChefChatRequest): Promise<ChefChatResponse> {
  return apiPost<ChefChatResponse>("/ai/chef/chat", req);
}
