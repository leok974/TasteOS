import { useRecipeLearnings } from '../hooks';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Lightbulb, History, Tag } from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';

export function RecipeLearningsCard({ recipeId }: { recipeId: string }) {
    const { data: learnings, isLoading } = useRecipeLearnings(recipeId);

    if (isLoading) return <Skeleton className="h-48 w-full rounded-2xl" />;
    
    if (!learnings || 
       (learnings.highlights.length === 0 && learnings.common_tags.length === 0 && learnings.recent_recaps.length === 0)) {
        return null;
    }

    return (
        <Card className="rounded-[2rem] border-purple-100/50 bg-gradient-to-br from-purple-50/30 to-white shadow-sm overflow-hidden">
             <CardHeader className="pb-3">
                <CardTitle className="text-lg flex items-center gap-2 text-purple-900">
                    <Lightbulb className="h-5 w-5 text-purple-600" />
                    Chef's Notes & Learnings
                </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
                
                {/* Highlights */}
                {learnings.highlights.length > 0 && (
                    <div className="space-y-2">
                        <h4 className="text-xs font-bold uppercase tracking-wider text-purple-400">Highlights</h4>
                        <ul className="space-y-2">
                            {learnings.highlights.map((h, i) => (
                                <li key={i} className="text-sm text-stone-700 bg-white/60 p-2 rounded-lg border border-purple-50">
                                    "{h}"
                                </li>
                            ))}
                        </ul>
                    </div>
                )}

                {/* Common Tags */}
                {learnings.common_tags.length > 0 && (
                    <div className="space-y-2">
                        <h4 className="text-xs font-bold uppercase tracking-wider text-purple-400 flex items-center gap-2">
                             <Tag className="h-3 w-3" /> Common Issues / Tags
                        </h4>
                        <div className="flex flex-wrap gap-2">
                            {learnings.common_tags.map(tag => (
                                <Badge key={tag} variant="secondary" className="bg-purple-100/50 text-purple-700 hover:bg-purple-200">
                                    {tag}
                                </Badge>
                            ))}
                        </div>
                    </div>
                )}

                {/* Recaps */}
                {learnings.recent_recaps.length > 0 && (
                     <div className="space-y-2">
                        <h4 className="text-xs font-bold uppercase tracking-wider text-purple-400 flex items-center gap-2">
                             <History className="h-3 w-3" /> Recent Sessions
                        </h4>
                        <div className="space-y-2">
                            {learnings.recent_recaps.map((recap, i) => (
                                <div key={i} className="text-xs text-stone-600 flex justify-between items-center border-b border-purple-50 pb-1 last:border-0">
                                    <span className="truncate max-w-[70%]">{recap.summary}</span>
                                    <span className="text-stone-400 font-mono text-[10px]">
                                        {new Date(recap.created_at).toLocaleDateString()}
                                    </span>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

            </CardContent>
        </Card>
    );
}
