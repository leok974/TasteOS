import Link from 'next/link';
import { WorkspaceSwitcher } from '@/features/workspaces/WorkspaceSwitcher';

export function AppHeader() {
    return (
        <header className="border-b bg-white sticky top-0 z-50">
            <div className="container max-w-5xl mx-auto px-4 h-16 flex items-center justify-between">
                <div className="flex items-center gap-8">
                    <Link href="/" className="text-xl font-bold tracking-tight hover:opacity-80 transition-opacity">
                        TasteOS
                    </Link>
                    <nav className="hidden md:flex items-center gap-1 text-sm font-medium text-muted-foreground">
                        <Link href="/plan" className="hover:text-foreground px-3 py-2 transition-colors">Plan</Link>
                        <Link href="/recipes" className="hover:text-foreground px-3 py-2 transition-colors">Recipes</Link>
                        <Link href="/grocery" className="hover:text-foreground px-3 py-2 transition-colors">Grocery</Link>
                        <Link href="/pantry" className="hover:text-foreground px-3 py-2 transition-colors">Pantry</Link>
                    </nav>
                </div>
                <div className="flex items-center gap-4">
                    <WorkspaceSwitcher />
                </div>
            </div>
        </header>
    )
}
