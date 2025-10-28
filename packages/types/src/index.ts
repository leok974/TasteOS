// Base Entity Types
export interface BaseEntity {
  id: string
  createdAt: Date
  updatedAt: Date
}

// User and Authentication Types
export interface User extends BaseEntity {
  email: string
  name: string
  avatar?: string
  plan: UserPlan
  preferences: UserPreferences
}

export type UserPlan = 'free' | 'pro' | 'enterprise'

export interface UserPreferences {
  dietaryRestrictions: string[]
  allergies: string[]
  favoriteIngredients: string[]
  dislikedIngredients: string[]
  cookingLevel: 'beginner' | 'intermediate' | 'advanced'
  preferredCuisines: string[]
  defaultServingSize: number
}

// Recipe Core Types
export interface Recipe extends BaseEntity {
  title: string
  description: string
  servings: number
  prepTime: number // minutes
  cookTime: number // minutes
  totalTime: number // minutes
  difficulty: 'easy' | 'medium' | 'hard'
  cuisine: string
  tags: string[]
  ingredients: Ingredient[]
  instructions: Instruction[]
  nutrition?: NutritionInfo
  images: string[]
  source?: RecipeSource
  rating?: number
  reviews?: Review[]
  authorId?: string
  isPublic: boolean
  variants: RecipeVariant[]
}

export interface Ingredient {
  id: string
  name: string
  amount: number
  unit: string
  category: IngredientCategory
  preparation?: string // "diced", "minced", etc.
  optional: boolean
  notes?: string
}

export type IngredientCategory =
  | 'protein'
  | 'vegetable'
  | 'fruit'
  | 'grain'
  | 'dairy'
  | 'spice'
  | 'herb'
  | 'oil'
  | 'condiment'
  | 'baking'
  | 'other'

export interface Instruction {
  id: string
  stepNumber: number
  description: string
  duration?: number // minutes
  temperature?: number // celsius
  equipment?: string[]
  images?: string[]
  tips?: string[]
}

export interface NutritionInfo {
  calories: number
  protein: number // grams
  carbohydrates: number // grams
  fat: number // grams
  fiber: number // grams
  sugar: number // grams
  sodium: number // milligrams
  servingSize: string
}

export interface RecipeSource {
  type: 'url' | 'book' | 'personal' | 'ai_generated'
  url?: string
  bookTitle?: string
  page?: number
  author?: string
}

export interface Review extends BaseEntity {
  userId: string
  recipeId: string
  rating: number // 1-5
  comment?: string
  images?: string[]
  helpful: number
}

// Recipe Variant Types
export interface RecipeVariant extends BaseEntity {
  parentRecipeId: string
  title: string
  description: string
  variantType: VariantType
  changes: RecipeChange[]
  metadata: VariantMetadata
  status: VariantStatus
  feedback?: VariantFeedback[]
}

export type VariantType =
  | 'dietary' // vegan, gluten-free, etc.
  | 'cuisine' // transform to different cuisine
  | 'technique' // different cooking method
  | 'ingredient' // substitute ingredients
  | 'serving' // change serving size
  | 'time' // quick vs slow version
  | 'equipment' // different cooking equipment
  | 'custom' // user-defined modification

export interface RecipeChange {
  type: ChangeType
  target: string // ingredient ID, instruction ID, or property name
  operation: 'add' | 'remove' | 'modify' | 'replace'
  oldValue?: any
  newValue?: any
  reason: string
}

export type ChangeType =
  | 'ingredient'
  | 'instruction'
  | 'timing'
  | 'technique'
  | 'equipment'
  | 'metadata'

export interface VariantMetadata {
  difficultyChange: number // -1 to 1 (easier to harder)
  timeChange: number // percentage change in total time
  costChange: number // percentage change in estimated cost
  nutritionImpact: Record<string, number> // changes to nutrition values
  confidenceScore: number // 0-1 AI confidence in variant
  tags: string[]
}

export type VariantStatus = 'draft' | 'generated' | 'reviewed' | 'tested' | 'approved'

export interface VariantFeedback extends BaseEntity {
  userId: string
  variantId: string
  rating: number // 1-5
  feedback: string
  improvements?: string[]
  wouldTryAgain: boolean
}

// Recipe Comparison and Diff Types
export interface RecipeDiff {
  original: Recipe
  variant: Recipe
  changes: DiffChange[]
  summary: DiffSummary
}

export interface DiffChange {
  type: 'ingredient' | 'instruction' | 'metadata'
  action: 'added' | 'removed' | 'modified'
  path: string
  oldValue?: any
  newValue?: any
  impact: 'low' | 'medium' | 'high'
}

export interface DiffSummary {
  totalChanges: number
  ingredientChanges: number
  instructionChanges: number
  difficultyImpact: 'easier' | 'same' | 'harder'
  timeImpact: string // "+15 minutes", "-30 minutes", "same"
  majorChanges: string[]
}

// AI Agent Types
export interface AgentRequest {
  type: AgentRequestType
  recipeId?: string
  parameters: Record<string, any>
  userId: string
  priority: 'low' | 'normal' | 'high'
}

export type AgentRequestType =
  | 'generate_variant'
  | 'suggest_improvements'
  | 'analyze_nutrition'
  | 'find_substitutions'
  | 'scale_recipe'
  | 'estimate_cost'

export interface AgentResponse {
  requestId: string
  status: 'pending' | 'processing' | 'completed' | 'error'
  result?: any
  error?: string
  metadata: {
    processingTime: number
    model: string
    confidence: number
    cost?: number
  }
}

// Pantry and Inventory Types
export interface PantryItem extends BaseEntity {
  userId: string
  ingredient: Ingredient
  quantity: number
  unit: string
  expirationDate?: Date
  location: string // "pantry", "fridge", "freezer"
  notes?: string
}

export interface ShoppingList extends BaseEntity {
  userId: string
  name: string
  items: ShoppingListItem[]
  completed: boolean
  estimatedCost?: number
}

export interface ShoppingListItem {
  id: string
  ingredient: Ingredient
  quantity: number
  unit: string
  obtained: boolean
  actualCost?: number
  notes?: string
}

// Cooking Session Types
export interface CookingSession extends BaseEntity {
  userId: string
  recipeId: string
  variantId?: string
  status: CookingStatus
  startedAt: Date
  completedAt?: Date
  currentStep: number
  notes: CookingNote[]
  modifications: SessionModification[]
  rating?: SessionRating
}

export type CookingStatus = 'not_started' | 'prep' | 'cooking' | 'completed' | 'abandoned'

export interface CookingNote {
  id: string
  stepNumber: number
  note: string
  timestamp: Date
  type: 'tip' | 'modification' | 'issue' | 'success'
}

export interface SessionModification {
  id: string
  stepNumber: number
  originalInstruction: string
  modifiedInstruction: string
  reason: string
  timestamp: Date
}

export interface SessionRating {
  overall: number // 1-5
  difficulty: number // 1-5 (1 = much easier than expected)
  taste: number // 1-5
  instructions: number // 1-5 (clarity)
  wouldMakeAgain: boolean
  feedback: string
  improvements: string[]
}

// Subscription and Billing Types
export interface Subscription extends BaseEntity {
  userId: string
  plan: UserPlan
  status: SubscriptionStatus
  currentPeriodStart: Date
  currentPeriodEnd: Date
  cancelAtPeriodEnd: boolean
  stripeSubscriptionId?: string
  stripeCustomerId?: string
}

export type SubscriptionStatus =
  | 'active'
  | 'canceled'
  | 'past_due'
  | 'unpaid'
  | 'trialing'

export interface Usage extends BaseEntity {
  userId: string
  period: string // YYYY-MM
  variantsGenerated: number
  recipesImported: number
  cookingSessions: number
  features: Record<string, number>
}

// Feature Flag Types
export interface FeatureFlag {
  key: string
  enabled: boolean
  rolloutPercentage: number
  conditions?: FeatureFlagCondition[]
  metadata?: Record<string, any>
}

export interface FeatureFlagCondition {
  type: 'user_plan' | 'user_id' | 'random'
  operator: 'equals' | 'in' | 'not_in' | 'greater_than' | 'less_than'
  value: any
}

// API Response Types
export interface ApiResponse<T = any> {
  success: boolean
  data?: T
  error?: string
  message?: string
  pagination?: PaginationInfo
}

export interface PaginationInfo {
  page: number
  limit: number
  total: number
  totalPages: number
  hasNext: boolean
  hasPrev: boolean
}

// Search and Filter Types
export interface SearchFilters {
  query?: string
  cuisine?: string[]
  difficulty?: ('easy' | 'medium' | 'hard')[]
  maxTime?: number
  ingredients?: string[]
  tags?: string[]
  dietary?: string[]
  sortBy?: 'relevance' | 'rating' | 'time' | 'difficulty' | 'recent'
  sortOrder?: 'asc' | 'desc'
}

export interface SearchResult<T> {
  items: T[]
  total: number
  facets: SearchFacets
  suggestions?: string[]
}

export interface SearchFacets {
  cuisines: FacetCount[]
  difficulties: FacetCount[]
  tags: FacetCount[]
  cookTimes: FacetCount[]
}

export interface FacetCount {
  value: string
  count: number
}

// Event and Analytics Types
export interface UserEvent {
  userId: string
  sessionId: string
  eventType: string
  eventData: Record<string, any>
  timestamp: Date
  source: 'web' | 'app' | 'api'
}

export interface AnalyticsData {
  event: string
  properties: Record<string, any>
  userId?: string
  timestamp: Date
}
