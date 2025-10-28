/**
 * VariantApproveButton component
 *
 * Handles variant approval with success toast
 */

import { useState } from 'react';
import { approveVariant } from '../lib/api';
import { Button } from '@tasteos/ui';
import { Check, CheckCircle } from 'lucide-react';

interface VariantApproveButtonProps {
  variantId: string;
  isApproved: boolean;
  onApprove?: () => void;
}

export function VariantApproveButton({
  variantId,
  isApproved,
  onApprove,
}: VariantApproveButtonProps) {
  const [loading, setLoading] = useState(false);
  const [approved, setApproved] = useState(isApproved);
  const [showToast, setShowToast] = useState(false);

  const handleApprove = async () => {
    if (approved) return;

    try {
      setLoading(true);
      await approveVariant(variantId);
      setApproved(true);
      setShowToast(true);

      // Hide toast after 3 seconds
      setTimeout(() => setShowToast(false), 3000);

      if (onApprove) {
        onApprove();
      }
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to approve variant');
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <Button
        onClick={handleApprove}
        disabled={loading || approved}
        variant={approved ? 'outline' : 'default'}
        size="sm"
        className={approved ? 'cursor-default' : ''}
      >
        {approved ? (
          <>
            <CheckCircle className="w-4 h-4 mr-2 text-green-600" />
            Approved
          </>
        ) : (
          <>
            <Check className="w-4 h-4 mr-2" />
            {loading ? 'Approving...' : 'Approve'}
          </>
        )}
      </Button>

      {/* Success Toast */}
      {showToast && (
        <div className="fixed bottom-4 right-4 bg-green-600 text-white rounded-lg shadow-lg p-4 flex items-center gap-3 animate-slide-in">
          <CheckCircle className="w-5 h-5" />
          <p className="font-medium">Saved to your cookbook!</p>
        </div>
      )}
    </>
  );
}
