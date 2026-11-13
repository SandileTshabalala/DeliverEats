import { toast } from 'react-hot-toast';
import { validateLuhn, validateExpiry, validateCVC } from '../utils/validation';

export interface PaymentDetails {
    cardNumber?: string;
    expiry?: string;
    cvc?: string;
}

/** What POST /payments/ returns. */
export interface PaymentSession {
    id: string;
    status: string;
    provider_name: string;
    amount: number | string;
    /** PayFast: the page to POST `checkout_fields` to. Stripe: the PaymentIntent client secret. */
    checkout_url?: string | null;
    /** PayFast only: the signed form fields. They must be posted exactly as received. */
    checkout_fields?: Record<string, string> | null;
}

export interface PaymentHandler {
    type: 'direct' | 'redirect' | 'offline';
    validate(details: PaymentDetails): { isValid: boolean; error?: string };
    /** Resolves `true` when the browser is leaving for the payment page. */
    process(session: PaymentSession, provider: any): Promise<boolean>;
}

/**
 * Send the customer to a hosted payment page.
 *
 * PayFast expects a form POST of the signed fields. We build a hidden form and
 * submit it, which is the integration PayFast documents. The fields were signed
 * on the server, so nothing here may be added, removed or re-ordered.
 */
export const redirectToHostedCheckout = (url: string, fields?: Record<string, string> | null) => {
    if (!fields || Object.keys(fields).length === 0) {
        window.location.assign(url);
        return;
    }
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = url;
    form.style.display = 'none';
    Object.entries(fields).forEach(([name, value]) => {
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = name;
        input.value = value;
        form.appendChild(input);
    });
    document.body.appendChild(form);
    form.submit();
};

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

    async process(session: PaymentSession) {
        if (session.checkout_url) {
            redirectToHostedCheckout(session.checkout_url, session.checkout_fields);
            return true;
        }
        return false;
    }
}

/**
 * Handler for providers that redirect to an external portal (PayFast, Ozow ...).
 */
class RedirectHandler implements PaymentHandler {
    type = 'redirect' as const;
    validate() {
        return { isValid: true };
    }

    async process(session: PaymentSession, provider: any) {
        if (!session.checkout_url) {
            toast.error(`${provider.display_name} is not available right now. Please choose another payment method.`);
            throw new Error("Missing checkout_url");
        }
        redirectToHostedCheckout(session.checkout_url, session.checkout_fields);
        return true;
    }
}

/**
 * Handler for offline methods (cash / card machine on delivery).
 */
class OfflineHandler implements PaymentHandler {
    type = 'offline' as const;
    validate() {
        return { isValid: true };
    }

    async process() {
        return false; // nothing to pay now
    }
}

export const isOfflineProvider = (providerName: string = '') => {
    const name = providerName.toLowerCase();
    return ['delivery', 'offline', 'cash', 'cod', 'machine', 'terminal', 'pos', 'collection'].some(k => name.includes(k));
};

export const getPaymentHandler = (provider: any): PaymentHandler => {
    if (!provider) return new RedirectHandler(); // Default safety fallback

    const name = (provider.provider_name || '').toLowerCase();

    if (isOfflineProvider(name)) {
        return new OfflineHandler();
    }

    // Hosted gateways
    if (name.includes('stripe') || name.includes('hosted') || name.includes('payfast') || name.includes('ozow') || name.includes('paygate')) {
        return new RedirectHandler();
    }

    // If it's a generic "card" provider (and not delivery), it uses direct entry
    if (name.includes('card')) {
        return new DirectCardHandler();
    }

    return new RedirectHandler();
};
