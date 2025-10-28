/**
 * Shopping page
 *
 * Generate and manage shopping lists
 */

import { useState, useEffect } from 'react';
import { getShoppingList, generateShoppingList, exportShoppingList, type GroceryItem } from '../lib/api';
import { ShoppingList } from '../components/ShoppingList';
import { ShoppingControls } from '../components/ShoppingControls';
import { Loader2, ShoppingCart } from 'lucide-react';

export function ShoppingPage() {
  const [items, setItems] = useState<GroceryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);

  useEffect(() => {
    loadShoppingList();
  }, []);

  const loadShoppingList = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getShoppingList();
      setItems(data);
    } catch (err: any) {
      console.error('Failed to load shopping list:', err);
      setError(err.message || 'Failed to load shopping list');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerate = async (planId?: string) => {
    try {
      setIsGenerating(true);
      setError(null);
      if (planId) {
        await generateShoppingList(planId);
      } else {
        // Generate from latest plan (you may need to implement getting the latest plan ID)
        setError('Please specify a plan ID or generate from a specific meal plan');
        return;
      }
      await loadShoppingList();
    } catch (err: any) {
      console.error('Failed to generate shopping list:', err);
      setError(err.message || 'Failed to generate shopping list');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleExport = async () => {
    try {
      const csv = await exportShoppingList();
      // Create a download link
      const blob = new Blob([csv], { type: 'text/csv' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `shopping-list-${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      console.error('Failed to export shopping list:', err);
      setError(err.message || 'Failed to export shopping list');
    }
  };

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
          <span className="ml-3 text-gray-600">Loading shopping list...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
          <ShoppingCart className="w-8 h-8" />
          Shopping List
        </h1>
        <p className="text-gray-600 mt-1">
          Manage your grocery shopping based on meal plans
        </p>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-red-800">{error}</p>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Controls */}
        <div className="lg:col-span-1">
          <ShoppingControls
            onGenerate={handleGenerate}
            onExport={handleExport}
            isGenerating={isGenerating}
            hasItems={items.length > 0}
          />

          {/* Stats */}
          <div className="mt-6 bg-white border border-gray-200 rounded-lg p-4">
            <h3 className="text-sm font-semibold text-gray-700 mb-3">Statistics</h3>
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Total Items:</span>
                <span className="font-medium text-gray-900">{items.length}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Purchased:</span>
                <span className="font-medium text-green-600">
                  {items.filter(i => i.purchased).length}
                </span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Remaining:</span>
                <span className="font-medium text-blue-600">
                  {items.filter(i => !i.purchased).length}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Shopping List */}
        <div className="lg:col-span-2">
          <ShoppingList items={items} onItemToggled={loadShoppingList} />
        </div>
      </div>
    </div>
  );
}
