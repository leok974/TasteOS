/**
 * PlanGuard component
 *
 * Shows upgrade CTA when user hits quota limits
 */

import * as React from 'react';
import { Button } from './button';

interface PlanGuardProps {
  plan: string;
  featureName: string;
  upgradeUrl?: string;
  children?: React.ReactNode;
}

export function PlanGuard({ plan, featureName, upgradeUrl, children }: PlanGuardProps) {
  // Emotional, TasteOS-y messaging for variant limits
  const getMessage = () => {
    if (featureName.toLowerCase().includes('variant')) {
      return plan === 'free'
        ? "You've whipped up your daily 3 variants 🌶️ Upgrade to Pro for 30/day and keep the flavors flowing!"
        : "You've hit today's flavor limit! ⚡ Upgrade to Enterprise for 60 variants per day.";
    }
    return `You've reached your ${featureName} limit on the ${plan} plan.`;
  };

  return (
    <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center bg-gray-50">
      <div className="max-w-md mx-auto space-y-4">
        <div className="text-4xl">🔒</div>
        <h3 className="text-xl font-semibold text-gray-900">
          Keep Cooking?
        </h3>
        <p className="text-gray-600">
          {getMessage()}
        </p>
        {children}
        {upgradeUrl ? (
          <a href={upgradeUrl}>
            <Button className="mt-4">
              Upgrade to Pro
            </Button>
          </a>
        ) : (
          <Button className="mt-4" onClick={() => window.location.href = '/settings/billing'}>
            View Plans
          </Button>
        )}
      </div>
    </div>
  );
}
