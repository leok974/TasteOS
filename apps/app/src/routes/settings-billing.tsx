/**
 * Billing settings page
 *
 * Shows current plan, upgrade options, and billing portal link
 */

import { useEffect, useState } from 'react';
import { getBillingPlan, startCheckout, getBillingPortal } from '../lib/api';
import { PLAN_LIMITS } from '../lib/planLimits';
import { Button, Badge } from '@tasteos/ui';
import { CreditCard, Zap, Crown } from 'lucide-react';
import type { UserPlan } from '@tasteos/types';

export function SettingsBilling() {
  const [plan, setPlan] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadBillingPlan();
  }, []);

  const loadBillingPlan = async () => {
    try {
      setLoading(true);
      const data = await getBillingPlan();
      setPlan(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load billing plan');
    } finally {
      setLoading(false);
    }
  };

  const handleUpgrade = async (interval: "monthly" | "yearly") => {
    try {
      const { checkout_url, message } = await startCheckout(interval);
      if (message) {
        alert(message);
      } else {
        window.location.href = checkout_url;
      }
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to create checkout session');
    }
  };

  const handleManageBilling = async () => {
    try {
      const { portal_url, message } = await getBillingPortal();
      if (message) {
        alert(message);
      } else {
        window.location.href = portal_url;
      }
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to open billing portal');
    }
  };

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="flex items-center justify-center h-64">
          <div className="text-gray-600">Loading billing information...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800">Error: {error}</p>
        </div>
      </div>
    );
  }

  const currentPlan = plan?.plan as UserPlan || 'free';
  const currentPlanInfo = PLAN_LIMITS[currentPlan];

  return (
    <div className="container mx-auto px-4 py-8 max-w-6xl">
      <h1 className="text-3xl font-bold text-gray-900 mb-8">Billing & Subscription</h1>

      {/* Current Plan */}
      <div className="bg-white border border-gray-200 rounded-lg p-6 mb-8">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">Current Plan</h2>
            <div className="flex items-center gap-3 mt-2">
              <span className="text-2xl font-bold text-blue-600 capitalize">
                {currentPlanInfo?.displayName || currentPlan}
              </span>
              {currentPlan !== 'free' && (
                <Badge variant="default">Active</Badge>
              )}
            </div>
          </div>
          {currentPlan !== 'free' && (
            <Button variant="outline" onClick={handleManageBilling}>
              <CreditCard className="w-4 h-4 mr-2" />
              Manage Billing
            </Button>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
          <div className="bg-gray-50 rounded-lg p-4">
            <p className="text-sm text-gray-600">Daily Variant Quota</p>
            <p className="text-2xl font-bold text-gray-900 mt-1">
              {plan?.dailyVariantQuotaUsed || 0} / {currentPlanInfo?.dailyVariantQuota}
            </p>
            <p className="text-xs text-gray-500 mt-1">Resets daily</p>
          </div>
          <div className="bg-gray-50 rounded-lg p-4">
            <p className="text-sm text-gray-600">Remaining Today</p>
            <p className="text-2xl font-bold text-gray-900 mt-1">
              {plan?.limits?.remaining || 0}
            </p>
          </div>
          <div className="bg-gray-50 rounded-lg p-4">
            <p className="text-sm text-gray-600">Price</p>
            <p className="text-2xl font-bold text-gray-900 mt-1">
              {currentPlanInfo?.price}
            </p>
          </div>
        </div>
      </div>

      {/* Available Plans */}
      <div>
        <h2 className="text-2xl font-semibold text-gray-900 mb-6">Available Plans</h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Free Plan */}
          <div className={`border-2 rounded-lg p-6 ${
            currentPlan === 'free' ? 'border-blue-500 bg-blue-50' : 'border-gray-200'
          }`}>
            <div className="flex items-center gap-2 mb-4">
              <Zap className="w-5 h-5 text-gray-600" />
              <h3 className="text-xl font-bold">Free</h3>
              {currentPlan === 'free' && <Badge>Current</Badge>}
            </div>
            <p className="text-3xl font-bold text-gray-900 mb-2">$0</p>
            <p className="text-gray-600 mb-6">per month</p>
            <ul className="space-y-3 mb-6">
              <li className="flex items-start gap-2 text-sm">
                <span className="text-green-600">✓</span>
                <span>3 variants per day</span>
              </li>
              <li className="flex items-start gap-2 text-sm">
                <span className="text-green-600">✓</span>
                <span>Basic recipe management</span>
              </li>
              <li className="flex items-start gap-2 text-sm">
                <span className="text-green-600">✓</span>
                <span>Community support</span>
              </li>
            </ul>
            {currentPlan !== 'free' && (
              <Button variant="outline" className="w-full" disabled>
                Downgrade (contact support)
              </Button>
            )}
          </div>

          {/* Pro Plan */}
          <div className={`border-2 rounded-lg p-6 relative ${
            currentPlan === 'pro' ? 'border-blue-500 bg-blue-50' : 'border-gray-200'
          }`}>
            {currentPlan === 'free' && (
              <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
                <Badge className="bg-blue-600 text-white">Recommended</Badge>
              </div>
            )}
            <div className="flex items-center gap-2 mb-4">
              <Zap className="w-5 h-5 text-blue-600" />
              <h3 className="text-xl font-bold">Pro</h3>
              {currentPlan === 'pro' && <Badge>Current</Badge>}
            </div>
            <p className="text-3xl font-bold text-gray-900 mb-2">$9.99</p>
            <p className="text-gray-600 mb-6">per month</p>
            <ul className="space-y-3 mb-6">
              <li className="flex items-start gap-2 text-sm">
                <span className="text-green-600">✓</span>
                <span><strong>30 variants per day</strong></span>
              </li>
              <li className="flex items-start gap-2 text-sm">
                <span className="text-green-600">✓</span>
                <span>Advanced recipe features</span>
              </li>
              <li className="flex items-start gap-2 text-sm">
                <span className="text-green-600">✓</span>
                <span>Priority support</span>
              </li>
              <li className="flex items-start gap-2 text-sm">
                <span className="text-green-600">✓</span>
                <span>Export & sharing</span>
              </li>
            </ul>
            {currentPlan === 'free' && (
              <Button
                className="w-full"
                onClick={() => handleUpgrade('monthly')}
              >
                Upgrade to Pro
              </Button>
            )}
          </div>

          {/* Enterprise Plan */}
          <div className={`border-2 rounded-lg p-6 ${
            currentPlan === 'enterprise' ? 'border-purple-500 bg-purple-50' : 'border-gray-200'
          }`}>
            <div className="flex items-center gap-2 mb-4">
              <Crown className="w-5 h-5 text-purple-600" />
              <h3 className="text-xl font-bold">Enterprise</h3>
              {currentPlan === 'enterprise' && <Badge>Current</Badge>}
            </div>
            <p className="text-3xl font-bold text-gray-900 mb-2">Custom</p>
            <p className="text-gray-600 mb-6">Contact us</p>
            <ul className="space-y-3 mb-6">
              <li className="flex items-start gap-2 text-sm">
                <span className="text-green-600">✓</span>
                <span><strong>60+ variants per day</strong></span>
              </li>
              <li className="flex items-start gap-2 text-sm">
                <span className="text-green-600">✓</span>
                <span>Team collaboration</span>
              </li>
              <li className="flex items-start gap-2 text-sm">
                <span className="text-green-600">✓</span>
                <span>Dedicated support</span>
              </li>
              <li className="flex items-start gap-2 text-sm">
                <span className="text-green-600">✓</span>
                <span>Custom integrations</span>
              </li>
            </ul>
            <Button variant="outline" className="w-full">
              Contact Sales
            </Button>
          </div>
        </div>
      </div>

      {/* FAQ */}
      <div className="mt-12 bg-gray-50 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Frequently Asked Questions</h3>
        <div className="space-y-4 text-sm">
          <div>
            <p className="font-medium text-gray-900">When does my daily quota reset?</p>
            <p className="text-gray-600 mt-1">
              Your daily variant quota resets at midnight UTC every day.
            </p>
          </div>
          <div>
            <p className="font-medium text-gray-900">Can I cancel anytime?</p>
            <p className="text-gray-600 mt-1">
              Yes! You can cancel your subscription at any time. You'll keep access until the end of your billing period.
            </p>
          </div>
          <div>
            <p className="font-medium text-gray-900">What payment methods do you accept?</p>
            <p className="text-gray-600 mt-1">
              We accept all major credit cards through Stripe.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
