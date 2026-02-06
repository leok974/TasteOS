import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Mic, Send, Sparkles, ChefHat, AlertTriangle, Clock } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useCookStepHelp, CookStepHelpResponse } from '../hooks';
import { Badge } from '@/components/ui/badge';

interface StepHelpDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  sessionId: string;
  stepIndex: number;
  onAddTimer?: (label: string, seconds: number) => void;
}

const COMMON_QUESTIONS = [
  "How do I know this is done?",
  "What if it's too dry?",
  "Can I skip this?",
  "Substitute for this ingredient?",
  "Why do I need to do this?"
];

export function StepHelpDrawer({ isOpen, onClose, sessionId, stepIndex, onAddTimer }: StepHelpDrawerProps) {
  const [question, setQuestion] = useState("");
  const [response, setResponse] = useState<CookStepHelpResponse | null>(null);
  
  const helpMutation = useCookStepHelp(sessionId);

  const handleSubmit = async (q: string) => {
    if (!q.trim()) return;
    setQuestion(q);
    setResponse(null); // Clear previous
    
    try {
      const result = await helpMutation.mutateAsync({
        step_index: stepIndex,
        question: q,
        context: {
           // Could pull from local storage or context if we had it easily accessible
        }
      });
      setResponse(result);
    } catch (e) {
      console.error(e);
      // Basic error handling visual
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 0.5 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black z-[190]"
          />
          
          {/* Drawer Panel */}
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className="fixed right-0 top-0 bottom-0 w-full md:w-[400px] bg-background border-l z-[200] shadow-xl flex flex-col"
          >
            {/* Header */}
            <div className="p-4 border-b flex items-center justify-between bg-muted/30">
              <div className="flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-purple-500" />
                <h2 className="font-semibold text-lg">Step Helper</h2>
              </div>
              <Button variant="ghost" size="sm" className="h-9 w-9 px-0" onClick={onClose}>
                <X className="h-5 w-5" />
              </Button>
            </div>

            {/* Content Area */}
            <ScrollArea className="flex-1 p-4">
              <div className="space-y-6">
                
                {/* Initial State / Empty State */}
                {!response && !helpMutation.isPending && (
                  <div className="space-y-4">
                    <p className="text-muted-foreground text-sm">
                      Ask anything about the current step. I have verify context from your recipe and notes.
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {COMMON_QUESTIONS.map((q) => (
                        <Button 
                          key={q} 
                          variant="outline" 
                          size="sm" 
                          className="rounded-full text-xs"
                          onClick={() => handleSubmit(q)}
                        >
                          {q}
                        </Button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Loading State */}
                {helpMutation.isPending && (
                  <div className="flex flex-col items-center justify-center py-10 space-y-4">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
                    <p className="text-sm text-muted-foreground animate-pulse">Thinking...</p>
                  </div>
                )}

                {/* Response State */}
                {response && (
                  <div className="space-y-4 animate-in fade-in slide-in-from-bottom-4 duration-500">
                    
                    {/* Source Badge */}
                    <div className="flex items-center gap-2">
                      <Badge variant={response.source === 'ai' ? 'default' : 'secondary'} className="text-[10px] uppercase tracking-wider">
                         {response.source === 'ai' ? <Sparkles className="w-3 h-3 mr-1" /> : <ChefHat className="w-3 h-3 mr-1" />}
                         {response.source === 'ai' ? 'Gemini AI' : 'Heuristic'}
                      </Badge>
                      <span className="text-xs text-muted-foreground">
                        Confidence: {response.confidence}
                      </span>
                    </div>

                    {/* Question Bubble */}
                    <div className="bg-muted/50 p-3 rounded-lg text-sm italic border-l-2 border-primary">
                      "{question}"
                    </div>

                    {/* Answer Bullets */}
                    <div className="space-y-2">
                        {response.bullets.map((bullet, idx) => (
                            <div key={idx} className="flex gap-2 items-start text-sm">
                                <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-primary flex-shrink-0" />
                                <span>{bullet}</span>
                            </div>
                        ))}
                    </div>

                    {/* Markdown Detail */}
                    {response.answer_md && (
                         <div className="text-sm prose dark:prose-invert prose-sm bg-muted/20 p-3 rounded-md">
                            <ReactMarkdown>{response.answer_md}</ReactMarkdown>
                         </div>
                    )}

                    {/* Safety Warnings */}
                    {response.safety.contains_food_safety && (
                        <div className="bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-900 rounded-md p-3 flex gap-3">
                            <AlertTriangle className="h-5 w-5 text-amber-600 dark:text-amber-500 flex-shrink-0" />
                            <div className="text-xs text-amber-800 dark:text-amber-200">
                                <strong>Safety Check:</strong> Ensure proper temperatures and hygiene.
                            </div>
                        </div>
                    )}

                    {/* Timer Suggestion CTA */}
                    {response.timer_suggestion && onAddTimer && (
                        <div className="mt-4 border border-blue-200 dark:border-blue-900 bg-blue-50 dark:bg-blue-950/20 rounded-lg p-3">
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                    <Clock className="w-4 h-4 text-blue-500" />
                                    <div className="text-sm font-medium">
                                        Suggest: {response.timer_suggestion.label} ({Math.round(response.timer_suggestion.seconds / 60)}m)
                                    </div>
                                </div>
                                <Button size="sm" variant="outline" className="bg-white hover:bg-white/80" onClick={() => onAddTimer(response.timer_suggestion!.label, response.timer_suggestion!.seconds)}>
                                    Create Timer
                                </Button>
                            </div>
                            <p className="text-xs text-muted-foreground mt-1 ml-6">
                                {response.timer_suggestion.rationale}
                            </p>
                        </div>
                    )}

                  </div>
                )}
              </div>
            </ScrollArea>

            {/* Input Area */}
            <div className="p-4 border-t bg-background">
              <form 
                onSubmit={(e) => { e.preventDefault(); handleSubmit(question); }}
                className="flex gap-2"
              >
                <Input 
                  placeholder="Ask a question..." 
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  className="flex-1"
                />
                <Button type="submit" size="sm" className="h-9 w-9 px-0" disabled={helpMutation.isPending || !question.trim()}>
                  <Send className="h-4 w-4" />
                </Button>
              </form>
            </div>

          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
