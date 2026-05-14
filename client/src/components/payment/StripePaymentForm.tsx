import { useState } from 'react';
import { PaymentElement, useStripe, useElements } from '@stripe/react-stripe-js';
import { toast } from 'react-hot-toast';
import { ArrowRight, ShieldCheck } from 'lucide-react';

interface StripePaymentFormProps {
    clientSecret: string;
    onSuccess: () => void;
    totalPrice: number;
}

export const StripePaymentForm = ({ clientSecret, onSuccess, totalPrice }: StripePaymentFormProps) => {
    const stripe = useStripe();
    const elements = useElements();
    const [isLoading, setIsLoading] = useState(false);
    const [errorMessage, setErrorMessage] = useState<string | null>(null);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!stripe || !elements) {
            return;
        }

        setIsLoading(true);
        setErrorMessage(null);

        const { error } = await stripe.confirmPayment({
            elements,
            confirmParams: {
                // Return to orders page on success (redirect fallback)
                // In a SPA, we might want to handle this without redirect if possible, 
                // but confirmPayment generally redirects unless redirect: 'if_required' is used.
                return_url: `${window.location.origin}/customer/orders?payment=success`,
            },
            redirect: 'if_required'
        });

        if (error) {
            setErrorMessage(error.message || "Payment failed");
            toast.error(error.message || "Payment failed");
        } else {
            // Payment succeeded directly
            onSuccess();
        }

        setIsLoading(false);
    };

    return (
        <form onSubmit={handleSubmit} className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="bg-gray-950 border border-gray-800 rounded-xl p-4">
                <PaymentElement
                    options={{
                        layout: 'tabs',
                        paymentMethodOrder: ['card'],
                    }}
                />
            </div>

            {errorMessage && (
                <div className="text-red-500 text-xs font-bold uppercase tracking-widest text-center">
                    {errorMessage}
                </div>
            )}

            <button
                type="submit"
                disabled={isLoading || !stripe || !elements}
                className="w-full bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed text-white py-4 rounded-xl font-black uppercase tracking-widest shadow-xl shadow-blue-600/20 active:scale-[0.98] transition-all flex items-center justify-center space-x-3 group"
            >
                {isLoading ? (
                    <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                    <>
                        <span>Pay R {totalPrice}</span>
                        <ArrowRight size={20} className="group-hover:translate-x-1 transition-transform" />
                    </>
                )}
            </button>
            <div className="flex items-center justify-center space-x-2 text-gray-500">
                <ShieldCheck size={14} />
                <span className="text-[10px] font-black uppercase tracking-widest">Secured by Stripe</span>
            </div>
        </form>
    );
};
