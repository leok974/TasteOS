/**
 * ShoppingControls component
 *
 * Controls for generating and exporting shopping lists
 */

import { useState } from 'react';
import { Button } from '@tasteos/ui';
import { Download, Loader2, Plus, ShoppingBag } from 'lucide-react';

interface ShoppingControlsProps {
  onGenerate: (planId?: string) => void;
  onExport: () => void;
  isGenerating?: boolean;
  hasItems?: boolean;
}

export function ShoppingControls({
  onGenerate,
  onExport,
  isGenerating = false,
  hasItems = false,
}: ShoppingControlsProps) {
  const [planId, setPlanId] = useState('');
  const [showPlanInput, setShowPlanInput] = useState(false);

  const handleGenerate = () => {
    if (showPlanInput && planId.trim()) {
      onGenerate(planId.trim());
    } else {
      onGenerate();
    }
    setPlanId('');
    setShowPlanInput(false);
  };

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
        <ShoppingBag className="w-5 h-5 text-blue-500" />
        Shopping List Actions
      </h2>

      <div className="space-y-4">
        {/* Generate Section */}
        <div>
          <div className="flex items-center gap-2 mb-2">
            <Button
              onClick={handleGenerate}
              disabled={isGenerating}
              className="flex-1"
            >
              {isGenerating ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  <Plus className="w-4 h-4 mr-2" />
                  Generate from Latest Plan
                </>
              )}
            </Button>
            <Button
              variant="outline"
              onClick={() => setShowPlanInput(!showPlanInput)}
            >
              {showPlanInput ? 'Cancel' : 'From Specific Plan'}
            </Button>
          </div>

          {showPlanInput && (
            <div className="flex gap-2">
              <input
                type="text"
                value={planId}
                onChange={(e) => setPlanId(e.target.value)}
                placeholder="Enter plan ID"
                className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
              <Button onClick={handleGenerate} disabled={!planId.trim() || isGenerating}>
                Generate
              </Button>
            </div>
          )}

          <p className="text-xs text-gray-600 mt-2">
            Generate a shopping list by comparing your meal plan with your pantry inventory
          </p>
        </div>

        {/* Export Section */}
        <div className="border-t border-gray-200 pt-4">
          <Button
            variant="outline"
            onClick={onExport}
            disabled={!hasItems}
            className="w-full"
          >
            <Download className="w-4 h-4 mr-2" />
            Export as CSV
          </Button>
          <p className="text-xs text-gray-600 mt-2">
            Download your shopping list to print or view offline
          </p>
        </div>
      </div>
    </div>
  );
}
