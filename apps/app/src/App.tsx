import { Routes, Route, Navigate, Link } from 'react-router-dom'
import { Button } from '@tasteos/ui'
import { isAuthenticated } from './lib/auth'
import { isPantryEnabled, isPlannerEnabled, isShoppingEnabled } from './lib/flags'
import { Login } from './routes/login'
import { Recipes } from './routes/recipes'
import { RecipeDetailPage } from './routes/recipe-detail'
import { SettingsBilling } from './routes/settings-billing'
import ImportRecipe from './routes/import'
import { PantryPage } from './routes/pantry'
import { PlannerPage } from './routes/planner'
import { ShoppingPage } from './routes/shopping'
import DashboardPage from './routes/dashboard'
import { CreditCard, BookOpen, FileUp, Package, CalendarDays, ShoppingCart, LayoutDashboard } from 'lucide-react'

function App() {
  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-white">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <Link to="/">
              <h1 className="text-2xl font-bold text-blue-600">TasteOS Dashboard</h1>
            </Link>

            {isAuthenticated() && (
              <nav className="flex items-center gap-4">
                <Link to="/dashboard">
                  <Button variant="ghost" size="sm">
                    <LayoutDashboard className="w-4 h-4 mr-2" />
                    Dashboard
                  </Button>
                </Link>
                <Link to="/recipes">
                  <Button variant="ghost" size="sm">
                    <BookOpen className="w-4 h-4 mr-2" />
                    Recipes
                  </Button>
                </Link>
                <Link to="/import">
                  <Button variant="ghost" size="sm">
                    <FileUp className="w-4 h-4 mr-2" />
                    Import
                  </Button>
                </Link>
                {isPantryEnabled() && (
                  <Link to="/pantry">
                    <Button variant="ghost" size="sm">
                      <Package className="w-4 h-4 mr-2" />
                      Pantry
                    </Button>
                  </Link>
                )}
                {isPlannerEnabled() && (
                  <Link to="/planner">
                    <Button variant="ghost" size="sm">
                      <CalendarDays className="w-4 h-4 mr-2" />
                      Planner
                    </Button>
                  </Link>
                )}
                {isShoppingEnabled() && (
                  <Link to="/shopping">
                    <Button variant="ghost" size="sm">
                      <ShoppingCart className="w-4 h-4 mr-2" />
                      Shopping
                    </Button>
                  </Link>
                )}
                <Link to="/settings/billing">
                  <Button variant="ghost" size="sm">
                    <CreditCard className="w-4 h-4 mr-2" />
                    Billing
                  </Button>
                </Link>
              </nav>
            )}
          </div>
        </div>
      </header>

      <main>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <DashboardHome />
              </ProtectedRoute>
            }
          />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <DashboardPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/recipes"
            element={
              <ProtectedRoute>
                <Recipes />
              </ProtectedRoute>
            }
          />
          <Route
            path="/recipes/:id"
            element={
              <ProtectedRoute>
                <RecipeDetailPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/import"
            element={
              <ProtectedRoute>
                <ImportRecipe />
              </ProtectedRoute>
            }
          />
          <Route
            path="/settings/billing"
            element={
              <ProtectedRoute>
                <SettingsBilling />
              </ProtectedRoute>
            }
          />
          {isPantryEnabled() && (
            <Route
              path="/pantry"
              element={
                <ProtectedRoute>
                  <PantryPage />
                </ProtectedRoute>
              }
            />
          )}
          {isPlannerEnabled() && (
            <Route
              path="/planner"
              element={
                <ProtectedRoute>
                  <PlannerPage />
                </ProtectedRoute>
              }
            />
          )}
          {isShoppingEnabled() && (
            <Route
              path="/shopping"
              element={
                <ProtectedRoute>
                  <ShoppingPage />
                </ProtectedRoute>
              }
            />
          )}
        </Routes>
      </main>
    </div>
  )
}

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  if (!isAuthenticated()) {
    return <Navigate to="/login" replace />
  }
  return <>{children}</>
}

function DashboardHome() {
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="space-y-6">
        <h1 className="text-4xl font-bold">Welcome to TasteOS</h1>
        <p className="text-xl text-gray-600">
          Your AI-powered cooking companion is ready to help transform your kitchen experience.
        </p>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 mt-8">
          <Link to="/recipes" className="block">
            <div className="bg-white border rounded-lg p-6 hover:shadow-lg transition-shadow">
              <h2 className="text-xl font-semibold mb-2">Recipe Library</h2>
              <p className="text-gray-600 mb-4">Browse and manage your collection of recipes</p>
              <Button variant="default">View Recipes</Button>
            </div>
          </Link>
          <Link to="/recipes" className="block">
            <div className="bg-white border rounded-lg p-6 hover:shadow-lg transition-shadow">
              <h2 className="text-xl font-semibold mb-2">AI Variants</h2>
              <p className="text-gray-600 mb-4">Generate recipe variations with AI assistance</p>
              <Button variant="outline">Generate Variants</Button>
            </div>
          </Link>
          <Link to="/settings/billing" className="block">
            <div className="bg-white border rounded-lg p-6 hover:shadow-lg transition-shadow">
              <h2 className="text-xl font-semibold mb-2">Subscription</h2>
              <p className="text-gray-600 mb-4">Manage your plan and billing</p>
              <Button variant="outline">Billing Settings</Button>
            </div>
          </Link>
        </div>
      </div>
    </div>
  )
}

export default App
