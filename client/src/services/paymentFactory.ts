import { toast } from 'react-hot-toast';
import { validateLuhn, validateExpiry, validateCVC } from '../utils/validation';

export interface PaymentDetails {
    cardNumber?: string;
    expiry?: string;
    cvc?: string;
}

export interface PaymentHandler {
    type: 'direct' | 'redirect' | 'offline';
    validate(details: PaymentDetails): { isValid: boolean; error?: string };
    process(orderId: string, amount: number, provider: any, checkoutUrl?: string): Promise<void>;
}

/**
 * Handler for providers that require direct card entry on our site.
 */
class DirectCardHandler implements PaymentHandler {
    type = 'direct' as const;
    validate(details: PaymentDetails) {
        if (!details.cardNumber || !validateLuhn(details.cardNumber)) {
            return { isValid: false, error: 'Invalid card number' };
        }
        if (!details.expiry || !validateExpiry(details.expiry)) {
            return { isValid: false, error: 'Invalid expiry date (MM/YY)' };
        }
        if (!details.cvc || !validateCVC(details.cvc)) {
            return { isValid: false, error: 'Invalid CVC' };
        }
        return { isValid: true };
    }

    async process(orderId: string, amount: number, provider: any, checkoutUrl?: string) {
        console.log(`Processing direct card payment for order ${orderId} via ${provider.display_name}`);

        if (checkoutUrl) {
            toast.loading(`Redirecting to secure ${provider.display_name} session...`);
            window.location.href = checkoutUrl;
        } else {
            toast.success(`Processing ${provider.display_name} payment (Offline)...`);
        }
    }
}

/**
 * Handler for providers that redirect to an external portal.
 */
class RedirectHandler implements PaymentHandler {
    type = 'redirect' as const;
    validate() {
        return { isValid: true };
    }

    async process(orderId: string, amount: number, provider: any, checkoutUrl?: string) {
        console.log(`Redirecting to ${provider.display_name} portal for order ${orderId}`);

        if (checkoutUrl) {
            toast.loading(`Redirecting to ${provider.display_name}...`);
            window.location.href = checkoutUrl;
        } else {
            toast.error(`Error: No redirect URL received for ${provider.display_name}.`);
            throw new Error("Missing checkout_url");
        }
    }
}

/**
 * Handler for offline methods.
 */
class OfflineHandler implements PaymentHandler {
    type = 'offline' as const;
    validate() {
        return { isValid: true };
    }

    async process(orderId: string, amount: number, provider: any) {
        console.log(`Offline payment via ${provider.display_name}`);
    }
}

export const getPaymentHandler = (provider: any): PaymentHandler => {
    if (!provider) return new RedirectHandler(); // Default safety fallback

    const name = (provider.provider_name || '').toLowerCase();

    // Logic to determine pattern
    if (name.includes('delivery') || name.includes('offline') || name.includes('cash') || name.includes('cod') || name.includes('machine') || name.includes('terminal') || name.includes('pos') || name.includes('collection')) {
        return new OfflineHandler();
    }

    // Stripe (now handled via Elements or Redirect) and Hosted Gateways
    if (name.includes('stripe') || name.includes('hosted') || name.includes('payfast') || name.includes('ozow') || name.includes('paygate')) {
        return new RedirectHandler();
    }

    // If it's a generic "card" provider (and not delivery), it uses direct entry
    if (name.includes('card')) {
        return new DirectCardHandler();
    }

    // Default to Redirect for other online gateways (PayFast, Ozow, etc.)
    return new RedirectHandler();
};
