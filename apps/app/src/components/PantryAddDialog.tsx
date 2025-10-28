/**
 * PantryAddDialog component
 *
 * Modal dialog for adding new pantry items
 */

import { useState } from 'react';
import { addPantryItem, scanPantryItem, type PantryItemCreate } from '../lib/api';
import { Button } from '@tasteos/ui';
import { X, Plus, Sparkles } from 'lucide-react';

interface PantryAddDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onItemAdded: () => void;
}

export function PantryAddDialog({ isOpen, onClose, onItemAdded }: PantryAddDialogProps) {
  const [name, setName] = useState('');
  const [quantity, setQuantity] = useState('');
  const [unit, setUnit] = useState('');
  const [expiresAt, setExpiresAt] = useState('');
  const [tags, setTags] = useState('');
  const [rawText, setRawText] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isParsing, setIsParsing] = useState(false);
  const [showAiHelper, setShowAiHelper] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!name.trim()) {
      alert('Please enter an item name');
      return;
    }

    try {
      setIsSubmitting(true);

      const data: PantryItemCreate = {
        name: name.trim(),
        ...(quantity && { quantity: parseFloat(quantity) }),
        ...(unit.trim() && { unit: unit.trim() }),
        ...(expiresAt && { expires_at: expiresAt }),
        ...(tags && { tags: tags.split(',').map(t => t.trim()).filter(Boolean) }),
      };

      await addPantryItem(data);

      // Reset form
      setName('');
      setQuantity('');
      setUnit('');
      setExpiresAt('');
      setTags('');
      setRawText('');

      onItemAdded();
      onClose();
    } catch (error) {
      console.error('Failed to add item:', error);
      alert('Failed to add item. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleAiParse = async () => {
    if (!rawText.trim()) {
      alert('Please enter a description');
      return;
    }

    try {
      setIsParsing(true);
      const result = await scanPantryItem({ raw_text: rawText.trim() });

      // Populate form with parsed data
      if (result.draft_item) {
        setName(result.draft_item.name || '');
        setQuantity(result.draft_item.quantity?.toString() || '');
        setUnit(result.draft_item.unit || '');
        setTags(result.draft_item.tags?.join(', ') || '');
      }

      setShowAiHelper(false);
      setRawText('');
    } catch (error) {
      console.error('Failed to parse item:', error);
      alert('Failed to parse item. Please try again or enter manually.');
    } finally {
      setIsParsing(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-xl font-semibold text-gray-900">Add Pantry Item</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6">
          {!showAiHelper ? (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Item Name *
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="e.g., Chicken breast"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Quantity
                  </label>
                  <input
                    type="number"
                    step="0.1"
                    value={quantity}
                    onChange={(e) => setQuantity(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="2.5"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Unit
                  </label>
                  <input
                    type="text"
                    value={unit}
                    onChange={(e) => setUnit(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="lb, g, cups"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Expires At
                </label>
                <input
                  type="date"
                  value={expiresAt}
                  onChange={(e) => setExpiresAt(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Tags (comma-separated)
                </label>
                <input
                  type="text"
                  value={tags}
                  onChange={(e) => setTags(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="protein, dairy, fresh"
                />
              </div>

              <div className="flex gap-2 pt-4">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setShowAiHelper(true)}
                  className="flex items-center gap-2"
                >
                  <Sparkles className="w-4 h-4" />
                  AI Helper
                </Button>
                <Button
                  type="submit"
                  disabled={isSubmitting}
                  className="flex-1"
                >
                  <Plus className="w-4 h-4 mr-2" />
                  {isSubmitting ? 'Adding...' : 'Add Item'}
                </Button>
              </div>
            </form>
          ) : (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Describe what you have
                </label>
                <textarea
                  value={rawText}
                  onChange={(e) => setRawText(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  rows={3}
                  placeholder='e.g., "half an onion" or "2 lbs chicken breast"'
                />
                <p className="text-xs text-gray-500 mt-1">
                  AI will parse this into structured data
                </p>
              </div>

              <div className="flex gap-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => {
                    setShowAiHelper(false);
                    setRawText('');
                  }}
                >
                  Cancel
                </Button>
                <Button
                  type="button"
                  onClick={handleAiParse}
                  disabled={isParsing}
                  className="flex-1"
                >
                  <Sparkles className="w-4 h-4 mr-2" />
                  {isParsing ? 'Parsing...' : 'Parse with AI'}
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
