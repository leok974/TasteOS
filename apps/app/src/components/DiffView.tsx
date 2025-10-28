/**
 * DiffView component
 *
 * Displays differences between original recipe and variant
 */

import { useEffect, useState } from 'react';
import type { RecipeDiff } from '@tasteos/types';
import { getVariantDiff } from '../lib/api';
import { Plus, Minus, ArrowRight } from 'lucide-react';

interface DiffViewProps {
  variantId: string;
}

export function DiffView({ variantId }: DiffViewProps) {
  const [diff, setDiff] = useState<RecipeDiff | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadDiff();
  }, [variantId]);

  const loadDiff = async () => {
    try {
      setLoading(true);
      const data = await getVariantDiff(variantId);
      setDiff(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load diff');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-gray-50 rounded-lg p-4">
        <p className="text-gray-600 text-sm">Loading diff...</p>
      </div>
    );
  }

  if (error || !diff) {
    return (
      <div className="bg-red-50 rounded-lg p-4">
        <p className="text-red-800 text-sm">Error: {error || 'Failed to load diff'}</p>
      </div>
    );
  }

  const { changes } = diff;

  // Group changes by type
  const ingredientChanges = changes.filter((c: any) => c.type === 'ingredient');
  const instructionChanges = changes.filter((c: any) => c.type === 'instruction');

  return (
    <div className="bg-gray-50 rounded-lg p-6 space-y-6">
      {/* Rationale */}
      {diff.summary && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <h4 className="font-semibold text-blue-900 mb-2">Rationale</h4>
          <p className="text-sm text-blue-800">{diff.summary.majorChanges.join('. ')}</p>
        </div>
      )}

      {/* Ingredient Changes */}
      {ingredientChanges.length > 0 && (
        <div>
          <h4 className="font-semibold text-gray-900 mb-3">Ingredient Changes</h4>
          <div className="space-y-2">
            {ingredientChanges.map((change: any, idx: number) => (
              <div
                key={idx}
                className={`rounded-lg p-3 ${
                  change.action === 'added'
                    ? 'bg-green-50 border border-green-200'
                    : change.action === 'removed'
                    ? 'bg-red-50 border border-red-200'
                    : 'bg-yellow-50 border border-yellow-200'
                }`}
              >
                <div className="flex items-start gap-2">
                  {change.action === 'added' && <Plus className="w-4 h-4 text-green-600 flex-shrink-0 mt-0.5" />}
                  {change.action === 'removed' && <Minus className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" />}
                  {change.action === 'modified' && <ArrowRight className="w-4 h-4 text-yellow-600 flex-shrink-0 mt-0.5" />}

                  <div className="flex-1">
                    {change.action === 'added' && (
                      <p className="text-sm text-green-800 font-medium">{change.newValue}</p>
                    )}
                    {change.action === 'removed' && (
                      <p className="text-sm text-red-800 line-through">{change.oldValue}</p>
                    )}
                    {change.action === 'modified' && (
                      <div className="text-sm">
                        <p className="text-red-800 line-through">{change.oldValue}</p>
                        <p className="text-green-800 font-medium mt-1">{change.newValue}</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Instruction Changes */}
      {instructionChanges.length > 0 && (
        <div>
          <h4 className="font-semibold text-gray-900 mb-3">Instruction Changes</h4>
          <div className="space-y-2">
            {instructionChanges.map((change: any, idx: number) => (
              <div
                key={idx}
                className={`rounded-lg p-3 ${
                  change.action === 'added'
                    ? 'bg-green-50 border border-green-200'
                    : change.action === 'removed'
                    ? 'bg-red-50 border border-red-200'
                    : 'bg-yellow-50 border border-yellow-200'
                }`}
              >
                <div className="flex items-start gap-2">
                  {change.action === 'added' && <Plus className="w-4 h-4 text-green-600 flex-shrink-0 mt-0.5" />}
                  {change.action === 'removed' && <Minus className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" />}
                  {change.action === 'modified' && <ArrowRight className="w-4 h-4 text-yellow-600 flex-shrink-0 mt-0.5" />}

                  <div className="flex-1">
                    <p className="text-xs text-gray-600 mb-1">Step {change.path}</p>
                    {change.action === 'added' && (
                      <p className="text-sm text-green-800">{change.newValue}</p>
                    )}
                    {change.action === 'removed' && (
                      <p className="text-sm text-red-800 line-through">{change.oldValue}</p>
                    )}
                    {change.action === 'modified' && (
                      <div className="text-sm space-y-2">
                        <p className="text-red-800 line-through">{change.oldValue}</p>
                        <p className="text-green-800">{change.newValue}</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Confidence Score */}
      {(diff as any).confidence_score !== undefined && (
        <div className="text-sm text-gray-600 pt-4 border-t border-gray-200">
          <span className="font-medium">AI Confidence:</span>{' '}
          {Math.round((diff as any).confidence_score * 100)}%
        </div>
      )}
    </div>
  );
}
