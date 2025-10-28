/**
 * Pantry page
 *
 * Manage pantry inventory with add/delete functionality
 */

import { useState, useEffect } from 'react';
import { getPantry, type PantryItem } from '../lib/api';
import { PantryTable } from '../components/PantryTable';
import { PantryAddDialog } from '../components/PantryAddDialog';
import { Button } from '@tasteos/ui';
import { Plus, Loader2, Package } from 'lucide-react';

export function PantryPage() {
  const [items, setItems] = useState<PantryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);

  useEffect(() => {
    loadPantry();
  }, []);

  const loadPantry = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getPantry();
      setItems(data);
    } catch (err: any) {
      console.error('Failed to load pantry:', err);
      setError(err.message || 'Failed to load pantry items');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
          <span className="ml-3 text-gray-600">Loading pantry...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800">Error: {error}</p>
          <Button onClick={loadPantry} className="mt-4" variant="outline">
            Try Again
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
            <Package className="w-8 h-8" />
            My Pantry
          </h1>
          <p className="text-gray-600 mt-1">
            Track your ingredients and manage inventory
          </p>
        </div>
        <Button onClick={() => setIsAddDialogOpen(true)}>
          <Plus className="w-5 h-5 mr-2" />
          Add Item
        </Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="text-sm text-gray-600">Total Items</div>
          <div className="text-2xl font-bold text-gray-900 mt-1">{items.length}</div>
        </div>
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="text-sm text-gray-600">Expiring Soon</div>
          <div className="text-2xl font-bold text-orange-600 mt-1">
            {items.filter(item => {
              if (!item.expires_at) return false;
              const expiryDate = new Date(item.expires_at);
              const threeDaysFromNow = new Date();
              threeDaysFromNow.setDate(threeDaysFromNow.getDate() + 3);
              return expiryDate <= threeDaysFromNow;
            }).length}
          </div>
        </div>
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="text-sm text-gray-600">Low Stock</div>
          <div className="text-2xl font-bold text-yellow-600 mt-1">
            {items.filter(item => item.quantity !== null && item.quantity < 1).length}
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        <PantryTable items={items} onItemDeleted={loadPantry} />
      </div>

      {/* Add Dialog */}
      <PantryAddDialog
        isOpen={isAddDialogOpen}
        onClose={() => setIsAddDialogOpen(false)}
        onItemAdded={loadPantry}
      />
    </div>
  );
}
