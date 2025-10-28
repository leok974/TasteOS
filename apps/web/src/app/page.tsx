import { Button } from '@tasteos/ui'
import Link from 'next/link'

export default function HomePage() {
  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <h1 className="text-2xl font-bold text-brand-orange">TasteOS</h1>
          </div>
          <nav className="hidden md:flex items-center space-x-6">
            <Link href="/recipes" className="text-foreground hover:text-brand-orange">
              Recipes
            </Link>
            <Link href="/pricing" className="text-foreground hover:text-brand-orange">
              Pricing
            </Link>
            <Link href="/blog" className="text-foreground hover:text-brand-orange">
              Blog
            </Link>
          </nav>
          <div className="flex items-center space-x-4">
            <Link href="/login">
              <Button variant="ghost">Sign In</Button>
            </Link>
            <Link href="/signup">
              <Button variant="brand">Get Started</Button>
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="py-20 text-center">
        <div className="container mx-auto px-4">
          <h1 className="text-6xl font-bold mb-6 text-display-2xl">
            Your AI <span className="text-brand-orange">Cooking</span> Companion
          </h1>
          <p className="text-xl text-muted-foreground mb-8 max-w-3xl mx-auto">
            Transform your cooking with AI-powered recipe variants, intelligent suggestions,
            and personalized culinary experiences that adapt to your tastes and kitchen.
          </p>
          <div className="flex items-center justify-center space-x-4">
            <Link href="/signup">
              <Button size="lg" variant="brand" className="text-lg px-8 py-4">
                Start Cooking Smarter
              </Button>
            </Link>
            <Link href="/recipes">
              <Button size="lg" variant="outline" className="text-lg px-8 py-4">
                Explore Recipes
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 bg-brand-cream dark:bg-brand-charcoal/10">
        <div className="container mx-auto px-4">
          <h2 className="text-4xl font-bold text-center mb-12">
            Revolutionize Your Kitchen
          </h2>
          <div className="grid md:grid-cols-3 gap-8">
            <div className="text-center">
              <div className="w-16 h-16 bg-brand-orange rounded-full mx-auto mb-4 flex items-center justify-center">
                <span className="text-2xl">🤖</span>
              </div>
              <h3 className="text-xl font-semibold mb-2">AI Recipe Variants</h3>
              <p className="text-muted-foreground">
                Generate infinite recipe variations adapted to your dietary needs,
                preferences, and available ingredients.
              </p>
            </div>
            <div className="text-center">
              <div className="w-16 h-16 bg-brand-orange rounded-full mx-auto mb-4 flex items-center justify-center">
                <span className="text-2xl">👨‍🍳</span>
              </div>
              <h3 className="text-xl font-semibold mb-2">Intelligent Cooking</h3>
              <p className="text-muted-foreground">
                Real-time cooking guidance with step-by-step assistance and
                smart timing that adapts to your pace.
              </p>
            </div>
            <div className="text-center">
              <div className="w-16 h-16 bg-brand-orange rounded-full mx-auto mb-4 flex items-center justify-center">
                <span className="text-2xl">📱</span>
              </div>
              <h3 className="text-xl font-semibold mb-2">Seamless Experience</h3>
              <p className="text-muted-foreground">
                Beautiful interface that works across all your devices,
                from planning to plating.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t py-12">
        <div className="container mx-auto px-4 text-center">
          <p className="text-muted-foreground">
            © 2025 TasteOS. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  )
}
