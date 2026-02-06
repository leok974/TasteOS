import { CookShell } from '@/features/cook/components/CookShell';
import { RecipeDetailView } from './RecipeDetailView';

// Server Component (Default in App Router)
export default async function RecipePage({
    params,
    searchParams,
}: {
    params: Promise<{ id: string }>;
    searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}) {
    const resolvedParams = await params;
    const resolvedSearchParams = await searchParams;

    // Check if '?cook=1' is providing
    const isCooking = resolvedSearchParams.cook === '1';

    if (isCooking) {
        return <CookShell recipeId={resolvedParams.id} />;
    }

    return <RecipeDetailView recipeId={resolvedParams.id} />;
}
