'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Search, Plus, Loader2, AlertCircle, ChefHat } from 'lucide-react';
import { useRecipes, useSeedDev } from '@/features/recipes/hooks';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/cn';
import { ImportRecipeModal } from '@/features/recipes/ImportRecipeModal';
import { IngestRecipeModal } from '@/features/recipes/IngestRecipeModal';

function RecipeCard({ recipe }: { recipe: { id: string; title: string; cuisines: string[] | null; time_minutes: number | null; primary_image_url: string | null } }) {
    return (
        <Link href={`/recipes/${recipe.id}`} className="block">
            <div className="group cursor-pointer rounded-[2rem] border border-amber-100/60 bg-white shadow-sm overflow-hidden hover:shadow-md transition-shadow">
                <div className="aspect-[4/3] bg-amber-50/40 relative">
                    {recipe.primary_image_url ? (
                        <img
                            src={recipe.primary_image_url}
                            alt={recipe.title}
                            className="w-full h-full object-cover"
                        />
                    ) : (
                        <div className="w-full h-full flex items-center justify-center">
                            <ChefHat className="h-12 w-12 text-amber-200" />
                        </div>
                    )}
                </div>
                <div className="p-5">
                    <h3 className="font-bold text-stone-900 tracking-tight line-clamp-2">{recipe.title}</h3>
                    <div className="mt-2 flex flex-wrap gap-2">
                        {recipe.cuisines?.slice(0, 2).map((c) => (
                            <span
                                key={c}
                                className="text-[9px] font-black uppercase tracking-widest text-amber-800 bg-amber-50 px-2 py-1 rounded-lg border border-amber-100"
                            >
                                {c}
                            </span>
                        ))}
                        {recipe.time_minutes && (
                            <span className="text-[9px] font-black uppercase tracking-widest text-stone-500 bg-stone-50 px-2 py-1 rounded-lg border border-stone-100">
                                {recipe.time_minutes}m
                            </span>
                        )}
                    </div>
                </div>
            </div>
        </Link>
    );
}

export default function RecipesPage() {
    const [search, setSearch] = useState('');
    const { data: recipes, isLoading, error } = useRecipes({ search: search || undefined });
    const seedMutation = useSeedDev();

    const handleSeed = () => {
        seedMutation.mutate();
    };

    return (
        <div className="min-h-screen bg-[#FAF9F6]">
            {/* Subtle amber wash */}
            <div className="pointer-events-none fixed inset-0 bg-gradient-to-b from-amber-50/60 via-transparent to-transparent" />

            <div className="relative mx-auto max-w-4xl px-6 pt-12 pb-20">
                {/* Header */}
                <header className="mb-8">
                    <h1 className="text-3xl font-serif text-stone-900 leading-tight">My Recipes.</h1>
                    <p className="mt-1 text-[10px] font-black uppercase tracking-[0.2em] text-stone-400">
                        {recipes?.length ?? 0} recipes
                    </p>
                </header>

                {/* Search + Actions */}
                <div className="mb-8 flex gap-3">
                    <div className="relative flex-1">
                        <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-amber-700/40" size={18} />
                        <input
                            type="text"
                            placeholder="Search recipes..."
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            className="w-full bg-amber-50/40 rounded-2xl py-4 pl-12 pr-4 text-sm font-medium border border-amber-100 focus:bg-white focus:border-amber-200 focus:ring-0 outline-none transition-all shadow-sm"
                        />
                    </div>
                    <IngestRecipeModal />
                    <ImportRecipeModal />
                    <Button
                        variant="default"
                        className="h-14 px-6 rounded-2xl"
                        onClick={handleSeed}
                        disabled={seedMutation.isPending}
                    >
                        {seedMutation.isPending ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                            <>
                                <Plus className="h-4 w-4 mr-2" />
                                Seed Data
                            </>
                        )}
                    </Button>
                </div>

                {/* Content */}
                {isLoading ? (
                    <div className="flex items-center justify-center py-20">
                        <Loader2 className="h-8 w-8 animate-spin text-amber-500" />
                    </div>
                ) : error ? (
                    <div className="rounded-[2rem] border border-red-100 bg-red-50 p-8 text-center">
                        <AlertCircle className="h-8 w-8 text-red-500 mx-auto mb-3" />
                        <p className="font-semibold text-red-800">Failed to load recipes</p>
                        <p className="mt-1 text-sm text-red-600">{error.message}</p>
                        <p className="mt-4 text-xs text-stone-500">
                            Make sure the API is running at localhost:8000 and the database is migrated.
                        </p>
                    </div>
                ) : recipes?.length === 0 ? (
                    <div className="rounded-[2.5rem] border border-amber-100/50 bg-white p-12 text-center shadow-sm">
                        <ChefHat className="h-12 w-12 text-amber-200 mx-auto mb-4" />
                        <h2 className="font-serif text-xl text-stone-900">No recipes yet</h2>
                        <p className="mt-2 text-sm text-stone-600">
                            Click "Seed Data" to add some sample recipes, or create your first recipe.
                        </p>
                        <Button
                            variant="amber"
                            className="mt-6 h-12 px-8 rounded-2xl"
                            onClick={handleSeed}
                            disabled={seedMutation.isPending}
                        >
                            {seedMutation.isPending ? (
                                <Loader2 className="h-4 w-4 animate-spin mr-2" />
                            ) : null}
                            Add Sample Recipes
                        </Button>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                        {recipes?.map((recipe) => (
                            <RecipeCard key={recipe.id} recipe={recipe} />
                        ))}
                    </div>
                )}

                {/* Seed success message */}
                {seedMutation.isSuccess && (
                    <div className="fixed bottom-6 right-6 rounded-2xl border border-green-100 bg-green-50 px-6 py-4 shadow-lg">
                        <p className="font-semibold text-green-800">
                            ✓ {seedMutation.data?.message}
                        </p>
                    </div>
                )}
            </div>
        </div>
    );
}
