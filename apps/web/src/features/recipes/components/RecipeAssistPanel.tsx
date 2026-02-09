import { useState, useRef, useEffect } from "react";
import { useMutation } from "@tanstack/react-query";
import { 
    Send, 
    Sparkles, 
    ChefHat, 
    AlertCircle, 
    Loader2 
} from "lucide-react";
import { cn } from "@/lib/cn";
import { Button } from "@/components/ui/button";
import { 
    assistRecipe, 
    RecipeAssistMessage, 
    RecipeAssistResponse,
    Recipe
} from "@/lib/api";

interface RecipeAssistPanelProps {
    recipeId: string;
    recipe: Recipe;
    className?: string;
    variant?: "default" | "cook";
}

export function RecipeAssistPanel({ recipeId, recipe, className, variant = "default" }: RecipeAssistPanelProps) {
    const [messages, setMessages] = useState<RecipeAssistMessage[]>(() => {
        if (typeof window === "undefined") return [];
        try {
            const key = `tasteos:assist:${recipeId}`;
            const saved = localStorage.getItem(key);
            return saved ? JSON.parse(saved) : [];
        } catch (e) {
            console.error("Failed to load chat history", e);
            return [];
        }
    });

    // Persist messages
    useEffect(() => {
        try {
            const key = `tasteos:assist:${recipeId}`;
            localStorage.setItem(key, JSON.stringify(messages));
        } catch (e) {
            // Ignore storage errors
        }
    }, [recipeId, messages]);

    const [input, setInput] = useState("");
    // To track if AI is unavailable for this session
    const [aiUnavailable, setAiUnavailable] = useState(false);
    
    // Auto-scroll
    const endRef = useRef<HTMLDivElement>(null);
    useEffect(() => {
        endRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    const mutation = useMutation({
        mutationFn: async (msgs: RecipeAssistMessage[]) => {
            try {
                return await assistRecipe(recipeId, { messages: msgs });
            } catch (error: any) {
                // If the API wrapper throws, we catch it here to extract status
                // But our apiPost wrapper likely throws with details.
                // We'll rethrow for onError to handle.
                throw error;
            }
        },
        onSuccess: (data) => {
            setMessages(prev => [
                ...prev, 
                { role: "assistant", content: data.reply }
            ]);
            
            // If the backend returns used_ai: false (mock mode or similar), we can visually indicate it if we want.
            if (data.used_ai === false) {
                // Maybe a toast? or just silent fall back.
            }
        },
        onError: (error: any) => {
            console.error("Assist error:", error);
            // Check for 409 or explicit error message
            // The apiPost wrapper usually returns an Error with message property populate from JSON detail
            // Or the fetch response object if not parsed.
            
            // Assuming our apiPost wrapper throws an error object with a message or status
            const isUnavailable = error?.message?.includes("ai_unavailable") || error?.detail?.error === "ai_unavailable" || error?.status === 409;

            if (isUnavailable) {
                setAiUnavailable(true);
                setMessages(prev => [
                    ...prev,
                    { 
                        role: "assistant", 
                        content: "I'm sorry, I can't connect to the AI chef right now."
                    }
                ]);
            } else {
                 setMessages(prev => [
                    ...prev,
                    { role: "assistant", content: "Sorry, something went wrong. Please try again." }
                ]);
            }
        }
    });

    const handleSend = (text: string) => {
        if (!text.trim()) return;
        
        const newMsg: RecipeAssistMessage = { role: "user", content: text };
        const newHistory = [...messages, newMsg];
        
        setMessages(newHistory);
        setInput("");
        
        mutation.mutate(newHistory);
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSend(input);
        }
    };

    const SUGGESTIONS = [
        "What can I sub for...?",
        "How do I store leftovers?",
        "Can I make this ahead?",
        "Is there a faster way?"
    ];

    const handleViewIngredients = () => {
        const text = "Here are the ingredients:\n\n" + recipe.ingredients.map(i => `• ${i.qty || ''} ${i.unit || ''} ${i.name}`).join("\n");
        setMessages(prev => [...prev, { role: "assistant", content: text }]);
    };
    
    const handleViewSteps = () => {
         const text = "Here is a recap of the steps:\n\n" + recipe.steps.map((s, i) => `${i+1}. ${s.title}\n${(s.bullets || []).map(b => `  - ${b}`).join("\n")}`).join("\n\n");
         setMessages(prev => [...prev, { role: "assistant", content: text }]);
    };

    return (
        <div className={cn(
            "flex flex-col bg-white overflow-hidden",
            variant === "default" && "h-[600px] rounded-2xl border border-amber-100 shadow-sm",
            variant === "cook" && "h-full rounded-none border-0",
            className
        )}>
             {/* Header */}
             <div className="p-4 border-b border-amber-100 bg-amber-50/50 flex items-center justify-between">
                 <div className="flex items-center gap-2">
                     <div className="h-8 w-8 rounded-full bg-amber-100 flex items-center justify-center">
                         <ChefHat className="h-4 w-4 text-amber-600" />
                     </div>
                     <div>
                         <h3 className="font-bold text-sm text-stone-900">Chef Assist</h3>
                         <p className="text-[10px] text-stone-500 uppercase tracking-widest">
                             {aiUnavailable ? "Offline Mode" : "AI Powered"}
                         </p>
                     </div>
                 </div>
                 {aiUnavailable && <AlertCircle className="h-4 w-4 text-stone-400" />}
             </div>

             {/* Messages */}
             <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-[#FAF9F6]">
                 {messages.length === 0 && (
                     <div className="text-center py-10 px-6">
                         <div className="h-16 w-16 bg-amber-100 rounded-full flex items-center justify-center mx-auto mb-4 animate-in zoom-in-50 duration-300">
                             <Sparkles className="h-8 w-8 text-amber-500" />
                         </div>
                         <h4 className="text-lg font-serif text-stone-800 mb-2">
                             Ask about "{recipe.title}"
                         </h4>
                         <p className="text-sm text-stone-500 mb-6">
                             {aiUnavailable 
                                ? "AI is currenty offline. You can view recipe details below." 
                                : "I can help with substitutions, techniques, or troubleshooting."}
                         </p>
                         
                         <div className="grid grid-cols-1 gap-2">
                             {aiUnavailable ? (
                                 <>
                                     <button
                                         onClick={handleViewIngredients}
                                         className="text-xs bg-stone-50 border border-stone-200 py-3 px-4 rounded-xl hover:bg-stone-100 transition-colors text-left text-stone-600 font-medium flex items-center gap-2"
                                     >
                                         <ChefHat className="h-3 w-3" /> Show Ingredients
                                     </button>
                                     <button
                                         onClick={handleViewSteps}
                                         className="text-xs bg-stone-50 border border-stone-200 py-3 px-4 rounded-xl hover:bg-stone-100 transition-colors text-left text-stone-600 font-medium flex items-center gap-2"
                                     >
                                         <Sparkles className="h-3 w-3" /> Show Steps Recap
                                     </button>
                                 </>
                             ) : (
                                 SUGGESTIONS.map(s => (
                                     <button
                                         key={s}
                                         onClick={() => handleSend(s)}
                                         className="text-xs bg-white border border-amber-100 py-3 px-4 rounded-xl hover:bg-amber-50 hover:border-amber-200 transition-colors text-left text-stone-600 font-medium"
                                         disabled={aiUnavailable}
                                     >
                                         {s}
                                     </button>
                                 ))
                             )}
                         </div>
                     </div>
                 )}

                 {messages.map((m, i) => (
                     <div key={i} className={cn("flex animate-in fade-in slide-in-from-bottom-2", m.role === 'user' ? "justify-end" : "justify-start")}>
                         <div className={cn(
                             "max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm",
                             m.role === 'user' 
                                 ? "bg-stone-900 text-white rounded-br-none" 
                                 : "bg-white border border-amber-100 text-stone-800 rounded-bl-none"
                         )}>
                             {m.content}
                         </div>
                     </div>
                 ))}
                 
                 {mutation.isPending && (
                     <div className="flex justify-start animate-in fade-in">
                         <div className="bg-white border border-amber-100 rounded-2xl rounded-bl-none px-4 py-3 shadow-sm flex items-center gap-2">
                             <Loader2 className="h-4 w-4 animate-spin text-amber-500" />
                             <span className="text-xs text-stone-400">Thinking...</span>
                         </div>
                     </div>
                 )}
                 
                 <div ref={endRef} />
             </div>

             {/* Input */}
             <div className="p-3 bg-white border-t border-amber-100">
                 <div className="relative flex items-center gap-2">
                     <textarea
                         value={input}
                         onChange={(e) => setInput(e.target.value)}
                         onKeyDown={handleKeyDown}
                         placeholder={aiUnavailable ? "Chef Assist is unavailable" : "Ask a question..."}
                         disabled={aiUnavailable}
                         className="flex-1 bg-stone-100 border-0 rounded-xl px-4 py-3 text-sm focus:ring-2 focus:ring-amber-200 resize-none h-12 max-h-32 placeholder:text-stone-400"
                         rows={1}
                     />
                     <Button 
                         size="icon" 
                         disabled={!input.trim() || mutation.isPending || aiUnavailable}
                         onClick={() => handleSend(input)}
                         className="h-12 w-12 rounded-xl bg-amber-500 hover:bg-amber-600 text-white shrink-0 shadow-sm"
                     >
                         <Send className="h-5 w-5" />
                     </Button>
                 </div>
             </div>
        </div>
    );
}
