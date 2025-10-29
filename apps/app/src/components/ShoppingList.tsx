/**
 * ShoppingList component
 *
 * Display grocery items with toggle functionality
 */

import type { GroceryItem } from '../lib/api';
import { togglePurchased } from '../lib/api';
import { Check, ShoppingCart } from 'lucide-react';
import { useState } from 'react';

interface ShoppingListProps {
  items: GroceryItem[];
  onItemToggled: () => void;
}

export function ShoppingList({ items, onItemToggled }: ShoppingListProps) {
  const [toggling, setToggling] = useState<string | null>(null);

  const handleToggle = async (itemId: string) => {
    try {
      setToggling(itemId);
      await togglePurchased(itemId);
      onItemToggled();
    } catch (err) {
      console.error('[TasteOS][ShoppingList] failed to toggle item:', err);
    } finally {
      setToggling(null);
    }
  };

  if (items.length === 0) {
    return (
      <div className="text-center py-12">
        <ShoppingCart className="w-16 h-16 mx-auto text-gray-400 mb-4" />
        <h3 className="text-lg font-medium text-gray-900 mb-2">Shopping list is empty</h3>
        <p className="text-gray-600">
          Generate a shopping list from your meal plan
        </p>
      </div>
    );
  }

  const unpurchasedItems = items.filter(item => !item.purchased);
  const purchasedItems = items.filter(item => item.purchased);

  return (
    <div className="space-y-6">
      {/* Unpurchased Items */}
      {unpurchasedItems.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3">
            To Buy ({unpurchasedItems.length})
          </h3>
          <div className="bg-white border border-gray-200 rounded-lg divide-y divide-gray-100">
            {unpurchasedItems.map((item) => (
              <div
                key={item.id}
                className="flex items-center justify-between p-4 hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-center gap-3 flex-1">
                  <button
                    onClick={() => handleToggle(item.id)}
                    disabled={toggling === item.id}
                    className="w-6 h-6 border-2 border-gray-300 rounded hover:border-blue-500 flex items-center justify-center transition-colors disabled:opacity-50"
                  >
                    {toggling === item.id && (
                      <div className="w-3 h-3 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                    )}
                  </button>
                  <div className="flex-1">
                    <div className="text-sm font-medium text-gray-900">{item.name}</div>
                    {(item.quantity !== null || item.unit) && (
                      <div className="text-xs text-gray-500 mt-0.5">
                        {item.quantity !== null && `${item.quantity} `}
                        {item.unit || ''}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Purchased Items */}
      {purchasedItems.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3">
            Purchased ({purchasedItems.length})
          </h3>
          <div className="bg-white border border-gray-200 rounded-lg divide-y divide-gray-100">
            {purchasedItems.map((item) => (
              <div
                key={item.id}
                className="flex items-center justify-between p-4 hover:bg-gray-50 transition-colors opacity-60"
              >
                <div className="flex items-center gap-3 flex-1">
                  <button
                    onClick={() => handleToggle(item.id)}
                    disabled={toggling === item.id}
                    className="w-6 h-6 bg-green-500 border-2 border-green-500 rounded hover:bg-green-600 flex items-center justify-center transition-colors disabled:opacity-50"
                  >
                    {toggling === item.id ? (
                      <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    ) : (
                      <Check className="w-4 h-4 text-white" />
                    )}
                  </button>
                  <div className="flex-1">
                    <div className="text-sm font-medium text-gray-900 line-through">{item.name}</div>
                    {(item.quantity !== null || item.unit) && (
                      <div className="text-xs text-gray-500 mt-0.5">
                        {item.quantity !== null && `${item.quantity} `}
                        {item.unit || ''}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
