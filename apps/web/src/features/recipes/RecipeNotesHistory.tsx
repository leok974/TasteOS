'use client';

import { useState, useEffect } from 'react';
import { format } from 'date-fns';
import { Trash2, Clock, RotateCcw, Search, X, Tag } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input'; 
import { Badge } from '@/components/ui/badge';
import { useRecipeNotesSearch, useDeleteRecipeNote, useRestoreRecipeNote, useRecipeNoteTags } from './hooks';
import { useDebounce } from '@/hooks/use-debounce'; // Assuming this hook exists or I'll inline it

export function RecipeNotesHistory({ recipeId }: { recipeId: string }) {
    // Search State
    const [searchQuery, setSearchQuery] = useState('');
    const debouncedSearch = useDebounce(searchQuery, 300);
    const [selectedTags, setSelectedTags] = useState<string[]>([]);
    
    // Data
    const { data: searchResult, isLoading } = useRecipeNotesSearch(recipeId, debouncedSearch, selectedTags);
    const { data: availableTags } = useRecipeNoteTags(recipeId);
    
    const notes = searchResult?.items || [];
    const deleteMutation = useDeleteRecipeNote();
    const restoreMutation = useRestoreRecipeNote();
    const [lastDeletedId, setLastDeletedId] = useState<string | null>(null);

    useEffect(() => {
        if (lastDeletedId) {
            const timer = setTimeout(() => setLastDeletedId(null), 8000);
            return () => clearTimeout(timer);
        }
    }, [lastDeletedId]);

    const toggleTag = (tag: string) => {
        setSelectedTags(prev => 
            prev.includes(tag) ? prev.filter(t => t !== tag) : [...prev, tag]
        );
    };

    if (isLoading && !notes.length) return <div className="mt-8 text-sm text-stone-400 animate-pulse">Loading history...</div>;

    const handleDelete = async (noteId: string) => {
        try {
            await deleteMutation.mutateAsync({ recipeId, noteId });
            setLastDeletedId(noteId);
        } catch (e) {
            console.error(e);
        }
    };
    
    const handleUndo = async () => {
         if (lastDeletedId) {
             await restoreMutation.mutateAsync({ recipeId, noteId: lastDeletedId });
             setLastDeletedId(null);
         }
    };

// Helper Icon
function CheckIcon(props: any) {
    return (
        <svg
            {...props}
            xmlns="http://www.w3.org/2000/svg"
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
        >
            <polyline points="20 6 9 17 4 12" />
        </svg>
    )
}


    return (
        <div className="space-y-6 mt-10 pt-10 border-t border-stone-100">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <h3 className="text-lg font-serif font-bold text-stone-800 flex items-center gap-2">
                    <Clock className="w-4 h-4 text-stone-400" />
                    Session History
                </h3>
                
                <div className="relative w-full sm:w-64" data-testid="notes-search-input">
                    <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-stone-400" />
                    <Input
                        placeholder="Search notes..."
                        className="pl-9 h-9 text-sm bg-stone-50 border-stone-200"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                    />
                    {searchQuery && (
                        <button 
                            onClick={() => setSearchQuery('')}
                            className="absolute right-2.5 top-2.5 text-stone-400 hover:text-stone-600"
                        >
                            <X className="h-4 w-4" />
                        </button>
                    )}
                </div>
            </div>

            {/* Tags Filter */}
            {availableTags?.tags && availableTags.tags.length > 0 && (
                <div className="flex flex-wrap gap-2 animate-in fade-in">
                    {availableTags.tags.map((t: any) => {
                        const isSelected = selectedTags.includes(t.tag);
                        return (
                            <button
                                key={t.tag}
                                onClick={() => toggleTag(t.tag)}
                                data-testid={`tag-chip-${t.tag}`}
                                className={`
                                    flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border transition-colors
                                    ${isSelected 
                                        ? 'bg-amber-100 border-amber-200 text-amber-900' 
                                        : 'bg-white border-stone-200 text-stone-600 hover:border-stone-300'}
                                `}
                            >
                                {isSelected && <CheckIcon className="w-3 h-3" />}
                                <span>{t.tag.replace('_', ' ')}</span>
                                <span className="opacity-50 ml-0.5 text-[10px]">{t.count}</span>
                            </button>
                        );
                    })}
                    {selectedTags.length > 0 && (
                        <Button 
                            variant="ghost" 
                            size="sm" 
                            onClick={() => setSelectedTags([])}
                            className="h-6 px-2 text-xs text-stone-400 hover:text-stone-600"
                        >
                            Clear
                        </Button>
                    )}
                </div>
            )}

            {lastDeletedId && (
                <div className="flex items-center justify-between p-3 mb-4 bg-stone-900 text-stone-50 rounded-xl text-sm shadow-lg animate-in fade-in slide-in-from-top-2">
                    <span className="font-medium pl-2">Note moved to trash.</span>
                    <Button 
                        variant="ghost" 
                        size="sm" 
                        onClick={handleUndo} 
                        disabled={restoreMutation.isPending}
                        className="h-auto py-1 px-3 text-amber-200 hover:text-white font-bold hover:bg-white/10"
                    >
                        <RotateCcw className="w-3 h-3 mr-2" />
                        {restoreMutation.isPending ? 'Restoring...' : 'Undo'}
                    </Button>
                </div>
            )}

            <div className="relative space-y-8 before:absolute before:inset-0 before:ml-5 before:-translate-x-px before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-stone-200 before:to-transparent">
                {(!notes || notes.length === 0) && (
                    <p className="text-sm text-stone-400 italic pl-10 py-2">No structured history yet. Start a cook session to add notes.</p>
                )}
                {notes?.map(note => (
                    <div key={note.id} className="relative flex gap-6 group">
                         <div className="absolute left-0 ml-5 -translate-x-1/2 translate-y-2 w-2 h-2 rounded-full border border-stone-300 bg-white group-hover:border-amber-400 group-hover:bg-amber-100 transition-colors z-10" />
                        
                        <div className="flex-1">
                            <div className="flex items-center justify-between mb-2">
                                <span className="text-xs font-bold uppercase tracking-wider text-stone-400 bg-white pr-2">
                                    {format(new Date(note.created_at), 'MMM d, yyyy')}
                                </span>
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    className="h-6 w-6 p-0 opacity-0 group-hover:opacity-100 transition-opacity text-stone-300 hover:text-red-500 hover:bg-red-50"
                                    onClick={() => handleDelete(note.id)}
                                >
                                    <Trash2 className="w-3 h-3" />
                                </Button>
                            </div>
                            <div className="text-sm text-stone-600 bg-stone-50/50 p-4 rounded-xl border border-stone-100 hover:border-amber-100/50 hover:bg-amber-50/20 transition-all">
                                {note.content_md.split('\n').map((line, i) => (
                                    <p key={i} className={line.startsWith('-') ? "ml-4 -indent-4 mb-1" : "mb-1"}>
                                        {line.startsWith('-') && <span className="inline-block w-1.5 h-1.5 rounded-full bg-stone-300 mr-2 opacity-60" />}
                                        {line.replace(/^-\s/, '')}
                                    </p>
                                ))}
                                
                                {note.tags && note.tags.length > 0 && (
                                    <div className="flex flex-wrap gap-2 mt-4 pt-3 border-t border-stone-100/50">
                                        {note.tags.map(tag => (
                                            <span 
                                                key={tag} 
                                                className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-stone-100 text-stone-500 uppercase tracking-wide"
                                            >
                                                {tag.replace(/_/g, ' ')}
                                            </span>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
