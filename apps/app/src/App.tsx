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
import InviteOwnerPage from './routes/invite'
import JoinHouseholdPage from './routes/join'
import LandingPage from './routes/landing'
import { CreditCard, BookOpen, FileUp, Package, CalendarDays, ShoppingCart, LayoutDashboard, UserPlus, Users } from 'lucide-react'

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
                <Link to="/invite">
                  <Button variant="ghost" size="sm">
                    <UserPlus className="w-4 h-4 mr-2" />
                    Invite
                  </Button>
                </Link>
                <Link to="/join">
                  <Button variant="ghost" size="sm">
                    <Users className="w-4 h-4 mr-2" />
                    Join
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
          <Route path="/" element={<LandingPage />} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <DashboardPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/invite"
            element={
              <ProtectedRoute>
                <InviteOwnerPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/join"
            element={
              <ProtectedRoute>
                <JoinHouseholdPage />
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

export default App
