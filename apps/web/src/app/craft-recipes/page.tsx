"use client";

import * as React from "react";
import Link from 'next/link';
import { ChevronLeft, Loader2, Sparkles, ChefHat, User, Send } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { chefChat, type ChefChatResponse, type RecipeDraft } from "@/features/craft-recipes/api";
import { RecipeDraftPreview } from "@/features/craft-recipes/RecipeDraftPreview";
import { apiPost } from "@/lib/api";
import { useRouter } from "next/navigation";

type Msg = {
  id: string;
  role: "user" | "assistant";
  content: string;
  meta?: { source?: string; model_id?: string };
};

function uid() {
  return Math.random().toString(16).slice(2);
}

export default function CraftRecipesPage() {
  // TODO: replace with real workspace id source
  const workspaceId = "local";
  const router = useRouter();

  const [threadId, setThreadId] = React.useState<string | undefined>(undefined);
  const [messages, setMessages] = React.useState<Msg[]>([
    {
      id: uid(),
      role: "assistant",
      content:
        "Bonjour! I am your personal Executive Chef. Tell me what ingredients you have, or what you're craving, and I shall craft a masterpiece for you.",
      meta: { source: "ai" },
    },
  ]);

  const [input, setInput] = React.useState("");
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const [draft, setDraft] = React.useState<RecipeDraft | null>(null);
  const [suggestedLabel, setSuggestedLabel] = React.useState<string | undefined>(undefined);
  const [tab, setTab] = React.useState<"recipe" | "storage" | "reheat" | "macros">("recipe");

  // refine context (v1)
  const [mode, setMode] = React.useState<"create" | "refine">("create");
  const [recipeId, setRecipeId] = React.useState<string | undefined>(undefined);
  const [baseVariantId, setBaseVariantId] = React.useState<string | undefined>(undefined);
  
  // Auto-scroll to bottom of chat
  const scrollRef = React.useRef<HTMLDivElement>(null);
  React.useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, loading]);

  async function onSend() {
    const text = input.trim();
    if (!text || loading) return;

    setError(null);
    setInput("");
    setMessages((m) => [...m, { id: uid(), role: "user", content: text }]);
    setLoading(true);

    try {
      const res: ChefChatResponse = await chefChat({
        workspace_id: workspaceId,
        thread_id: threadId,
        message: text,
        mode,
        recipe_id: mode === "refine" ? recipeId : undefined,
        base_variant_id: mode === "refine" ? baseVariantId : undefined,
      });

      if (res.thread_id && !threadId) setThreadId(res.thread_id);

      setMessages((m) => [
        ...m,
        {
          id: uid(),
          role: "assistant",
          content: res.assistant_message || "(No message returned)",
          meta: { source: res.source, model_id: res.model_id },
        },
      ]);

      if (res.recipe_draft) {
        setDraft(res.recipe_draft);
        setSuggestedLabel(res.suggested_label);
        setTab("recipe");
      }
    } catch (e: any) {
      setError(e?.message ?? "Failed to chat with chef agent.");
    } finally {
      setLoading(false);
    }
  }

  // --- Save actions (wired via apiPost) ---
  async function saveAsNewRecipe() {
    if (!draft) return;

    try {
      const res = await apiPost<{ id: string }>("/recipes/from-draft", {
        workspace_id: workspaceId,
        draft: draft,
        label: suggestedLabel || "Original",
      });
      // Redirect to the new recipe
      router.push(`/recipes/${res.id}`);
    } catch (err: any) {
      alert(`Failed to save recipe: ${err.message}`);
    }
  }

  async function saveAsNewVersion() {
    if (!draft || !recipeId) return;

    try {
      await apiPost(`/recipes/${recipeId}/variants/from-draft`, {
        workspace_id: workspaceId,
        draft: draft,
        label: suggestedLabel || "AI Revision",
        base_variant_id: baseVariantId,
      });
      // Redirect back to the recipe page
      router.push(`/recipes/${recipeId}`);
    } catch (err: any) {
      alert(`Failed to save version: ${err.message}`);
    }
  }

  return (
    <div className="min-h-screen bg-[#FAF9F6] flex flex-col">
        {/* Header */}
        <header className="bg-white/80 backdrop-blur-md border-b border-amber-100 sticky top-0 z-10">
            <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
                <Link href="/recipes" className="flex items-center text-stone-500 hover:text-stone-900 transition-colors">
                    <ChevronLeft size={20} />
                    <span className="ml-1 font-medium text-sm">Back to Recipes</span>
                </Link>
                <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-full bg-amber-100 flex items-center justify-center">
                        <ChefHat size={16} className="text-amber-600" />
                    </div>
                    <span className="font-serif font-bold text-stone-900">Chef de Cuisine</span>
                </div>
                
                {/* Mode Selector */}
                <div className="flex items-center gap-2">
                    <select
                        value={mode}
                        onChange={(e) => setMode(e.target.value as any)}
                        className="rounded-xl border border-stone-200 bg-white px-3 py-1.5 text-xs font-medium text-stone-600 focus:outline-none focus:ring-2 focus:ring-amber-500/20"
                    >
                        <option value="create">New Creation</option>
                        <option value="refine">Refine Existing</option>
                    </select>
                </div>
            </div>
        </header>

      <div className="flex-1 overflow-hidden">
        <div className="max-w-7xl mx-auto h-full grid lg:grid-cols-[1.2fr_0.8fr] gap-0 lg:gap-8 p-0 lg:p-6">
            
            {/* Left Column: Chat */}
            <div className="flex flex-col h-full bg-transparent lg:bg-white/60 lg:backdrop-blur lg:rounded-[2rem] lg:border lg:border-amber-100/50 overflow-hidden">
                {/* Chat Area */}
                <div className="flex-1 overflow-y-auto p-4 space-y-6" ref={scrollRef}>
                    {messages.map((m) => (
                        <div 
                            key={m.id} 
                            className={`flex gap-4 ${m.role === 'user' ? 'flex-row-reverse' : ''}`}
                        >
                            <div className={`
                                w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0
                                ${m.role === 'assistant' ? 'bg-amber-100' : 'bg-stone-200'}
                            `}>
                                {m.role === 'assistant' ? (
                                    <ChefHat size={16} className="text-amber-600" />
                                ) : (
                                    <User size={16} className="text-stone-600" />
                                )}
                            </div>
                            <div className={`
                                px-6 py-4 rounded-[2rem] max-w-[85%] leading-relaxed shadow-sm whitespace-pre-wrap
                                ${m.role === 'assistant' 
                                    ? 'bg-white border border-amber-100/50 text-stone-800 rounded-tl-none' 
                                    : 'bg-stone-900 text-stone-50 rounded-tr-none'
                                }
                            `}>
                                {m.content}
                                {m.role === 'assistant' && (m.meta?.source || m.meta?.model_id) ? (
                                    <div className="mt-3 pt-3 border-t border-stone-100 flex gap-2 text-[10px] uppercase tracking-wider text-stone-400 font-medium">
                                        {m.meta?.source && <span>{m.meta.source}</span>}
                                        {m.meta?.model_id && <span>• {m.meta.model_id}</span>}
                                    </div>
                                ) : null}
                            </div>
                        </div>
                    ))}
                    
                    {loading && (
                        <div className="flex gap-4">
                            <div className="w-8 h-8 rounded-full bg-amber-100 flex items-center justify-center flex-shrink-0">
                                <ChefHat size={16} className="text-amber-600" />
                            </div>
                            <div className="bg-white border border-amber-100/50 px-6 py-4 rounded-[2rem] rounded-tl-none shadow-sm flex items-center gap-2">
                                <Loader2 className="h-4 w-4 animate-spin text-amber-500" />
                                <span className="text-sm text-stone-500">Chef is thinking...</span>
                            </div>
                        </div>
                    )}
                    
                    {error && (
                        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800 flex gap-2 items-center">
                           <span className="text-xl">⚠️</span> {error}
                        </div>
                    )}
                </div>

                {/* Input Area */}
                <div className="p-4 bg-white/50 backdrop-blur border-t border-amber-100">
                    <div className="relative">
                        <textarea
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={(e) => {
                                if (e.key === "Enter" && !e.shiftKey) {
                                    e.preventDefault();
                                    onSend();
                                }
                            }}
                            placeholder="e.g. I have chicken, lemon, and thyme... or 'Make this vegetarian'"
                            className="w-full bg-white border border-stone-200 rounded-2xl py-4 pl-6 pr-14 text-stone-900 placeholder:text-stone-400 focus:outline-none focus:ring-2 focus:ring-amber-500/20 focus:border-amber-300 transition-all shadow-sm resize-none h-[60px]"
                        />
                        <Button
                            size="icon"
                            className="absolute right-2 top-2 h-11 w-11 rounded-xl bg-amber-500 hover:bg-amber-600 text-white shadow-sm"
                            onClick={onSend}
                            disabled={!input.trim() || loading}
                        >
                            <Send size={18} />
                        </Button>
                    </div>
                </div>
            </div>

            {/* Right Column: Draft Preview */}
            <div className="hidden lg:flex flex-col h-full overflow-hidden">
                {draft ? (
                    <div className="h-full flex flex-col space-y-4">
                         <div className="flex flex-wrap gap-2 items-center justify-between">
                            <h3 className="text-sm font-bold uppercase tracking-wider text-stone-500">Current Draft</h3>
                            <div className="flex gap-2">
                                <Button
                                    variant="outline"
                                    onClick={saveAsNewVersion}
                                    disabled={mode !== "refine" || !recipeId}
                                    className="h-9 text-xs rounded-xl"
                                >
                                    Save Version
                                </Button>
                                <Button
                                    onClick={saveAsNewRecipe}
                                    className="h-9 text-xs bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl shadow-sm border-none"
                                >
                                    Save Recipe
                                </Button>
                            </div>
                        </div>
                        
                        <div className="flex-1 overflow-hidden">
                             <RecipeDraftPreview draft={draft} activeTab={tab} onTabChange={setTab} />
                        </div>
                        
                        {suggestedLabel && (
                             <div className="bg-amber-50 border border-amber-100 rounded-xl px-4 py-3 flex items-center gap-2">
                                <Sparkles className="h-4 w-4 text-amber-500" />
                                <span className="text-xs text-amber-800 font-medium">Suggested Label: </span>
                                <span className="text-xs text-stone-600 bg-white px-2 py-0.5 rounded border border-amber-100">{suggestedLabel}</span>
                             </div>
                        )}
                    </div>
                ) : (
                    <div className="h-full rounded-[2rem] border border-stone-100 bg-stone-50/50 flex flex-col items-center justify-center text-center p-8">
                        <div className="w-16 h-16 rounded-full bg-amber-50 flex items-center justify-center mb-4">
                            <Sparkles className="h-8 w-8 text-amber-300" />
                        </div>
                        <h3 className="font-serif text-xl text-stone-400">No Draft Yet</h3>
                        <p className="mt-2 text-sm text-stone-400 max-w-xs">
                            Start chatting with the Chef to generate your first recipe draft. It will appear here.
                        </p>
                    </div>
                )}
            </div>
        </div>
      </div>
    </div>
  );
}
