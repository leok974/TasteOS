/**
 * PantryTable component
 *
 * Displays user's pantry items in a table with freshness indicators
 */

import { useState } from 'react';
import type { PantryItem } from '../lib/api';
import { deletePantryItem } from '../lib/api';
import { Badge, Button } from '@tasteos/ui';
import { Trash2, AlertCircle, Clock } from 'lucide-react';

interface PantryTableProps {
  items: PantryItem[];
  onItemDeleted: () => void;
}

export function PantryTable({ items, onItemDeleted }: PantryTableProps) {
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this item?')) {
      return;
    }

    try {
      setDeletingId(id);
      await deletePantryItem(id);
      onItemDeleted();
    } catch (error) {
      console.error('Failed to delete item:', error);
      alert('Failed to delete item. Please try again.');
    } finally {
      setDeletingId(null);
    }
  };

  const isExpiringSoon = (expiresAt: string | null): boolean => {
    if (!expiresAt) return false;
    const expiryDate = new Date(expiresAt);
    const threeDaysFromNow = new Date();
    threeDaysFromNow.setDate(threeDaysFromNow.getDate() + 3);
    return expiryDate <= threeDaysFromNow;
  };

  const isLowStock = (quantity: number | null): boolean => {
    if (quantity === null) return false;
    return quantity < 1;
  };

  const formatDate = (dateString: string | null): string => {
    if (!dateString) return 'No expiry';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  };

  if (items.length === 0) {
    return (
      <div className="text-center py-12 border-2 border-dashed border-gray-300 rounded-lg">
        <p className="text-gray-600">Your pantry is empty</p>
        <p className="text-sm text-gray-500 mt-1">
          Add items to start tracking your ingredients
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Item
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Quantity
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Expires
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Tags
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Status
            </th>
            <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
              Actions
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {items.map((item) => (
            <tr key={item.id} className="hover:bg-gray-50">
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="text-sm font-medium text-gray-900">{item.name}</div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="text-sm text-gray-900">
                  {item.quantity !== null ? (
                    <>
                      {item.quantity} {item.unit || ''}
                    </>
                  ) : (
                    <span className="text-gray-400">—</span>
                  )}
                </div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="text-sm text-gray-900">
                  {formatDate(item.expires_at)}
                </div>
              </td>
              <td className="px-6 py-4">
                <div className="flex flex-wrap gap-1">
                  {item.tags && item.tags.length > 0 ? (
                    item.tags.map((tag) => (
                      <Badge key={tag} variant="outline" className="text-xs">
                        {tag}
                      </Badge>
                    ))
                  ) : (
                    <span className="text-sm text-gray-400">—</span>
                  )}
                </div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="flex gap-2">
                  {isExpiringSoon(item.expires_at) && (
                    <Badge variant="destructive" className="text-xs flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      Expiring Soon
                    </Badge>
                  )}
                  {isLowStock(item.quantity) && (
                    <Badge variant="warning" className="text-xs flex items-center gap-1 bg-yellow-100 text-yellow-800 border-yellow-200">
                      <AlertCircle className="w-3 h-3" />
                      Low
                    </Badge>
                  )}
                  {!isExpiringSoon(item.expires_at) && !isLowStock(item.quantity) && (
                    <span className="text-sm text-gray-400">—</span>
                  )}
                </div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleDelete(item.id)}
                  disabled={deletingId === item.id}
                  className="text-red-600 hover:text-red-900"
                >
                  <Trash2 className="w-4 h-4" />
                </Button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
