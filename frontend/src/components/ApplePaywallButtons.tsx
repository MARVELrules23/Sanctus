/**
 * Default (web / Android) stub for the Apple IAP paywall buttons.
 *
 * Metro resolves the real StoreKit implementation from
 * `ApplePaywallButtons.ios.tsx` on iOS. On every other platform this stub
 * renders nothing — those platforms use the Stripe checkout button instead —
 * and, crucially, it never imports `react-native-iap`, keeping that native
 * module out of the web/Android bundle.
 */
export type ApplePaywallButtonsProps = {
  selectedPlan: "monthly" | "annual";
  trialDays: number;
  onEntitled: () => Promise<void> | void;
};

export default function ApplePaywallButtons(_props: ApplePaywallButtonsProps) {
  return null;
}
