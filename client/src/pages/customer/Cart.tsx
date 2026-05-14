import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import {
    ShoppingBag,
    Trash2,
    Plus,
    Minus,
    ArrowRight,
    CreditCard,
    MapPin,
    Truck,
    ShieldCheck,
    Banknote,
    HandCoins,
    Wallet
} from 'lucide-react';
import { useCart } from '../../context/CartContext';
import { useAuth } from '../../context/AuthContext';
import { toast } from 'react-hot-toast';
import { motion, AnimatePresence } from 'framer-motion';
import api from '../../services/api';
import { clsx } from 'clsx';

interface PaymentProvider {
    provider_name: string;
    display_name: string;
    public_key: string | null;
    enabled: boolean;
}

import { getPaymentHandler } from '../../services/paymentFactory';
import { validateLuhn } from '../../utils/validation';
import { loadStripe } from '@stripe/stripe-js';
import { Elements } from '@stripe/react-stripe-js';
import { StripePaymentForm } from '../../components/payment/StripePaymentForm';

const Cart = () => {
    const { items, updateQuantity, removeFromCart, totalPrice, clearCart } = useCart();
    const { user } = useAuth();
    const navigate = useNavigate();
    const [providers, setProviders] = useState<PaymentProvider[]>([]);
    const [selectedProvider, setSelectedProvider] = useState<string>('');

    const [cardDetails, setCardDetails] = useState({
        number: '',
        expiry: '',
        cvc: ''
    });
    const [errors, setErrors] = useState<{ [key: string]: string }>({});

    const [addresses, setAddresses] = useState<any[]>([]);
    const [selectedAddressId, setSelectedAddressId] = useState<string>('');
    const [loadingAddresses, setLoadingAddresses] = useState(true);

    // Stripe State
    const [clientSecret, setClientSecret] = useState<string>('');
    const [stripePromise, setStripePromise] = useState<any>(null);

    const handleCardNumberChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const value = e.target.value.replace(/\D/g, '');
        if (value.length > 19) return;

        // Add spaces every 4 digits
        const formatted = value.replace(/(\d{4})/g, '$1 ').trim();
        setCardDetails(prev => ({ ...prev, number: formatted }));

        // Real-time Luhn feedback: only show error if length is a standard "complete" length
        const isCompleteLength = value.length === 15 || value.length === 16 || value.length === 19;

        if (isCompleteLength) {
            if (!validateLuhn(value)) {
                setErrors(prev => ({ ...prev, number: 'Invalid card number' }));
            } else {
                setErrors(prev => {
                    const { number, ...rest } = prev;
                    return rest;
                });
            }
        } else if (value.length < 13) {
            // Clear error while starting to type a new number
            setErrors(prev => {
                const { number, ...rest } = prev;
                return rest;
            });
        }
    };

    const handleExpiryChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        let value = e.target.value.replace(/\D/g, '');
        if (value.length > 4) return;

        if (value.length >= 2) {
            value = value.slice(0, 2) + '/' + value.slice(2);
        }
        setCardDetails(prev => ({ ...prev, expiry: value }));
        setErrors(prev => {
            const { expiry, ...rest } = prev;
            return rest;
        });
    };

    const handleCvcChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const value = e.target.value.replace(/\D/g, '');
        if (value.length > 4) return;
        setCardDetails(prev => ({ ...prev, cvc: value }));
        setErrors(prev => {
            const { cvc, ...rest } = prev;
            return rest;
        });
    };

    useEffect(() => {
        fetchPaymentConfig();
        fetchUserAddresses();
    }, []);

    const fetchUserAddresses = async () => {
        try {
            const response = await api.get('/users/me');
            const fetchedAddresses = response.data.addresses || [];
            setAddresses(fetchedAddresses);
            const defaultAddr = fetchedAddresses.find((a: any) => a.is_default);
            if (defaultAddr) {
                setSelectedAddressId(defaultAddr.id);
            } else if (fetchedAddresses.length > 0) {
                setSelectedAddressId(fetchedAddresses[0].id);
            }
        } catch (error) {
            console.error('Failed to fetch addresses');
        } finally {
            setLoadingAddresses(false);
        }
    };

    const fetchPaymentConfig = async () => {
        try {
            const response = await api.get('/payments/config');
            setProviders(response.data);
            if (response.data.length > 0) {
                setSelectedProvider(response.data[0].provider_name);
            }
            // Initialize Stripe if available and not already loaded
            const stripeProvider = response.data.find((p: any) => p.provider_name.toLowerCase().includes('stripe'));
            if (stripeProvider && stripeProvider.public_key && !stripePromise) {
                setStripePromise(loadStripe(stripeProvider.public_key));
            }
        } catch (error) {
            console.error('Failed to fetch payment config');
        }
    };

    const getPaymentIcon = (name: string) => {
        const n = name.toLowerCase();
        if (n.includes('card') && n.includes('delivery')) return <HandCoins size={18} />;
        if (n.includes('cash') || n.includes('delivery')) return <Banknote size={18} />;
        if (n.includes('stripe') || n.includes('payfast') || n.includes('card')) return <CreditCard size={18} />;
        return <Wallet size={18} />;
    };

    const handleCheckout = async () => {
        const providerObj = providers.find(p => p.provider_name === selectedProvider);
        if (!providerObj) {
            toast.error("Please select a payment method");
            return;
        }

        if (!selectedAddressId) {
            toast.error("Please select a delivery address");
            navigate('/customer/profile');
            return;
        }

        // 0. Validate Payment
        const handler = getPaymentHandler(providerObj);
        const validation = handler.validate({
            cardNumber: cardDetails.number,
            expiry: cardDetails.expiry,
            cvc: cardDetails.cvc
        });

        if (!validation.isValid) {
            toast.error(validation.error || "Invalid payment details");
            return;
        }

        try {
            toast.loading("Processing your delicious order...");

            // 1. Create the Order
            const orderPayload = {
                restaurant_id: items[0]?.restaurant_id || "default-restaurant-id",
                customer_id: (user as any)?.id,
                address_id: selectedAddressId,
                items: items.map(i => ({
                    menu_item_id: i.id,
                    quantity: i.quantity
                })),
                total: totalPrice
            };

            const orderResponse = await api.post('/orders/', orderPayload);
            const orderId = orderResponse.data.id;

            // 2. Create the Payment record in DB
            const paymentPayload = {
                order_id: orderId,
                amount: totalPrice,
                provider_name: selectedProvider
            };

            const paymentResponse = await api.post('/payments/', paymentPayload);
            const checkoutUrl = paymentResponse.data.checkout_url;

            // 3. Process via Handler (Redirection if needed)
            // If it's Stripe (client_secret returned), we set state to render Elements
            const isStripe = providerObj.provider_name.toLowerCase().includes('stripe');

            if (isStripe && checkoutUrl) {
                // checkoutUrl here is the client_secret from PaymentIntent
                setClientSecret(checkoutUrl);
                toast.dismiss();
                return; // Stop here, render the form
            }

            await handler.process(orderId, Number(totalPrice), providerObj, checkoutUrl);

            // If it's an offline method, it won't redirect, so we finish here
            if (!checkoutUrl) {
                toast.dismiss();
                toast.success("Order placed successfully! Getting it ready...");
                clearCart();
                navigate('/customer/orders');
            }
        } catch (error: any) {
            toast.dismiss();
            console.error("Checkout error:", error);
            const msg = error.response?.data?.detail || "Failed to place order. Please try again.";
            toast.error(msg);
        }
    };

    if (items.length === 0) {
        return (
            <div className="min-h-[60vh] flex flex-col items-center justify-center space-y-8 animate-in fade-in zoom-in duration-500">
                <div className="relative">
                    <div className="absolute inset-0 bg-blue-500 rounded-full blur-[80px] opacity-20 animate-pulse"></div>
                    <div className="w-32 h-32 bg-gray-900 border border-gray-800 rounded-[40px] flex items-center justify-center relative z-10 shadow-2xl">
                        <ShoppingBag size={48} className="text-gray-700" />
                    </div>
                </div>
                <div className="text-center space-y-2">
                    <h2 className="text-3xl font-black uppercase tracking-tighter italic">Your cart is empty</h2>
                    <p className="text-gray-500 font-medium max-w-xs mx-auto text-lg leading-tight">Looks like you haven't added any charcoal grilled goodness yet.</p>
                </div>
                <Link
                    to="/customer"
                    className="flex items-center space-x-3 px-8 py-4 bg-blue-600 hover:bg-blue-500 text-white font-black uppercase tracking-widest text-xs rounded-2xl shadow-xl shadow-blue-600/20 active:scale-95 transition-all"
                >
                    <span>Start Ordering</span>
                    <ArrowRight size={18} />
                </Link>
            </div>
        );
    }

    return (
        <div className="max-w-6xl mx-auto space-y-12 animate-in fade-in duration-500">
            <div className="flex items-center justify-between">
                <h1 className="text-4xl font-black uppercase tracking-tighter italic">Your Selection</h1>
                <Link to="/customer" className="hidden md:flex items-center space-x-2 text-blue-500 font-bold hover:text-blue-400">
                    <Plus size={18} />
                    <span className="uppercase tracking-widest text-xs">Add more items</span>
                </Link>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-12">
                {/* Cart Items List */}
                <div className="lg:col-span-2 space-y-6">
                    <AnimatePresence mode="popLayout">
                        {items.map((item) => (
                            <motion.div
                                layout
                                initial={{ opacity: 0, x: -20 }}
                                animate={{ opacity: 1, x: 0 }}
                                exit={{ opacity: 0, scale: 0.95 }}
                                key={item.id}
                                className="bg-gray-900/50 border border-gray-800 rounded-[32px] p-6 flex items-center group transition-all"
                            >
                                <div className="w-24 h-24 bg-gray-800 rounded-2xl overflow-hidden relative border border-gray-800 flex-shrink-0">
                                    {item.image_url ? (
                                        <img src={item.image_url} alt={item.name} className="w-full h-full object-cover" />
                                    ) : (
                                        <div className="w-full h-full flex items-center justify-center text-gray-700">
                                            <ShoppingBag size={32} />
                                        </div>
                                    )}
                                </div>
                                <div className="ml-6 flex-1 pr-4">
                                    <div className="flex justify-between">
                                        <h3 className="text-xl font-black uppercase tracking-tight italic group-hover:text-blue-500 transition-colors truncate pr-4">{item.name}</h3>
                                        <p className="font-black text-white text-lg whitespace-nowrap">R {item.price * item.quantity}</p>
                                    </div>
                                    <p className="text-gray-500 text-sm font-medium h-5 truncate mb-4">Each: R {item.price}</p>

                                    <div className="flex items-center justify-between">
                                        <div className="flex items-center bg-gray-950 border border-gray-800 rounded-xl p-1">
                                            <button
                                                onClick={() => updateQuantity(item.id, -1)}
                                                className="p-2 hover:bg-gray-800 rounded-lg transition-colors text-gray-400 hover:text-white"
                                            >
                                                <Minus size={14} />
                                            </button>
                                            <span className="w-10 text-center font-black">{item.quantity}</span>
                                            <button
                                                onClick={() => updateQuantity(item.id, 1)}
                                                className="p-2 hover:bg-gray-800 rounded-lg transition-colors text-gray-400 hover:text-white"
                                            >
                                                <Plus size={14} />
                                            </button>
                                        </div>
                                        <button
                                            onClick={() => removeFromCart(item.id)}
                                            className="p-2 hover:bg-red-500/10 text-gray-600 hover:text-red-500 rounded-xl transition-all"
                                        >
                                            <Trash2 size={20} />
                                        </button>
                                    </div>
                                </div>
                            </motion.div>
                        ))}
                    </AnimatePresence>
                </div>

                {/* Summary / Sidebar */}
                <div className="space-y-8">
                    <div className="bg-gray-900 border border-gray-800 rounded-[40px] p-8 space-y-8 shadow-2xl relative overflow-hidden">
                        <div className="absolute top-0 right-0 p-8 opacity-5 pointer-events-none">
                            <CreditCard size={120} className="text-blue-500" />
                        </div>

                        <h3 className="text-2xl font-black uppercase tracking-tighter italic relative z-10">Order Summary</h3>

                        <div className="space-y-4 relative z-10">
                            <div className="flex justify-between text-gray-400 font-bold uppercase tracking-widest text-xs">
                                <span>Subtotal</span>
                                <span className="text-white">R {totalPrice}</span>
                            </div>
                            <div className="flex justify-between text-gray-400 font-bold uppercase tracking-widest text-xs">
                                <span>Delivery Fee</span>
                                <span className="text-blue-500">FREE</span>
                            </div>
                            <div className="pt-4 border-t border-gray-800 flex justify-between">
                                <span className="text-xl font-black uppercase tracking-tighter italic">Total Amount</span>
                                <span className="text-2xl font-black text-blue-500">R {totalPrice}</span>
                            </div>
                        </div>

                        <div className="space-y-4 pt-4">
                            <div className="flex items-center justify-between">
                                <p className="text-[10px] font-black uppercase tracking-widest text-gray-500">Delivery Address</p>
                                <Link to="/customer/profile" className="text-[10px] font-black uppercase tracking-widest text-blue-500">Edit</Link>
                            </div>

                            {loadingAddresses ? (
                                <div className="animate-pulse flex items-center space-x-3 text-gray-500">
                                    <div className="w-4 h-4 bg-gray-800 rounded-full"></div>
                                    <div className="h-2 w-24 bg-gray-800 rounded"></div>
                                </div>
                            ) : addresses.length === 0 ? (
                                <Link to="/customer/profile" className="flex items-center space-x-3 text-red-500 hover:text-red-400 group">
                                    <MapPin size={18} />
                                    <span className="text-xs font-bold uppercase tracking-wider underline">Add Address Required</span>
                                </Link>
                            ) : (
                                <div className="space-y-2">
                                    {addresses.map((addr) => (
                                        <button
                                            key={addr.id}
                                            onClick={() => setSelectedAddressId(addr.id)}
                                            className={clsx(
                                                "w-full flex items-start space-x-3 p-3 rounded-xl border transition-all text-left",
                                                selectedAddressId === addr.id
                                                    ? "bg-blue-600/10 border-blue-500 text-white"
                                                    : "bg-gray-950 border-gray-800 text-gray-500 hover:border-gray-700"
                                            )}
                                        >
                                            <MapPin size={18} className={clsx(selectedAddressId === addr.id ? "text-blue-500" : "text-gray-600")} />
                                            <div className="flex-1 overflow-hidden">
                                                <p className="text-[10px] font-black uppercase tracking-tight truncate">{addr.suburb || 'My Spot'}</p>
                                                <p className="text-[8px] font-medium truncate">{addr.formatted_address}</p>
                                            </div>
                                            {selectedAddressId === addr.id && <ShieldCheck size={14} className="text-blue-500 flex-shrink-0" />}
                                        </button>
                                    ))}
                                </div>
                            )}

                            <div className="flex items-center space-x-3 text-gray-500">
                                <Truck size={18} className="text-blue-500" />
                                <span className="text-xs font-bold uppercase tracking-wider">Fast Delivery (25 mins)</span>
                            </div>
                        </div>

                        {providers.length > 0 && (
                            <div className="space-y-3 pt-2">
                                <p className="text-[10px] font-black uppercase tracking-widest text-gray-500">Select Payment Method</p>
                                <div className="grid grid-cols-1 gap-2">
                                    {providers.map((p) => (
                                        <button
                                            key={p.provider_name}
                                            onClick={() => {
                                                setSelectedProvider(p.provider_name);
                                                setErrors({}); // Clear errors
                                                setClientSecret(''); // Clear Stripe state
                                                // We don't necessarily clear cardDetails so user doesn't lose progress if switching back,
                                                // but we MUST clear errors to unblock submission of other forms.
                                            }}
                                            className={clsx(
                                                "w-full flex items-center justify-between px-4 py-3 rounded-xl border transition-all",
                                                selectedProvider === p.provider_name
                                                    ? "bg-blue-600/10 border-blue-500 text-white shadow-lg shadow-blue-500/10"
                                                    : "bg-gray-950 border-gray-800 text-gray-500 hover:border-gray-700"
                                            )}
                                        >
                                            <div className="flex items-center space-x-4">
                                                <div className={clsx(
                                                    "w-10 h-10 rounded-xl flex items-center justify-center transition-all",
                                                    selectedProvider === p.provider_name
                                                        ? "bg-blue-600 text-white shadow-lg shadow-blue-500/20"
                                                        : "bg-gray-800 text-gray-400"
                                                )}>
                                                    {getPaymentIcon(p.provider_name)}
                                                </div>
                                                <span className="text-xs font-bold uppercase tracking-wider">{p.display_name}</span>
                                            </div>
                                            {selectedProvider === p.provider_name && <ShieldCheck size={18} className="text-blue-500 animate-in zoom-in duration-300" />}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Card Input Form for Online Payments (ONLY if using direct entry) */}
                        {selectedProvider && getPaymentHandler(providers.find(p => p.provider_name === selectedProvider)).type === 'direct' && (
                            <div className="space-y-4 animate-in slide-in-from-top-4 fade-in duration-500 border-t border-gray-800 pt-4">
                                <div className="space-y-2">
                                    <label className="text-[10px] font-black uppercase tracking-widest text-gray-500">Card Number</label>
                                    <div className="relative">
                                        <input
                                            type="text"
                                            value={cardDetails.number}
                                            onChange={handleCardNumberChange}
                                            placeholder="0000 0000 0000 0000"
                                            className={clsx(
                                                "w-full bg-gray-950 border rounded-xl px-4 py-3 text-white placeholder-gray-600 outline-none transition-all font-mono",
                                                errors.number ? "border-red-500 focus:border-red-500" : "border-gray-800 focus:border-blue-500"
                                            )}
                                        />
                                        <CreditCard size={16} className={clsx("absolute right-4 top-1/2 -translate-y-1/2", errors.number ? "text-red-500" : "text-gray-600")} />
                                    </div>
                                    {errors.number && <p className="text-[10px] text-red-500 font-bold uppercase tracking-widest">{errors.number}</p>}
                                </div>
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="space-y-2">
                                        <label className="text-[10px] font-black uppercase tracking-widest text-gray-500">Expiry Date</label>
                                        <input
                                            type="text"
                                            value={cardDetails.expiry}
                                            onChange={handleExpiryChange}
                                            placeholder="MM/YY"
                                            className={clsx(
                                                "w-full bg-gray-950 border rounded-xl px-4 py-3 text-white placeholder-gray-600 outline-none transition-all font-mono",
                                                errors.expiry ? "border-red-500 focus:border-red-500" : "border-gray-800 focus:border-blue-500"
                                            )}
                                        />
                                    </div>
                                    <div className="space-y-2">
                                        <label className="text-[10px] font-black uppercase tracking-widest text-gray-500">CVC</label>
                                        <input
                                            type="text"
                                            value={cardDetails.cvc}
                                            onChange={handleCvcChange}
                                            placeholder="123"
                                            className={clsx(
                                                "w-full bg-gray-950 border rounded-xl px-4 py-3 text-white placeholder-gray-600 outline-none transition-all font-mono",
                                                errors.cvc ? "border-red-500 focus:border-red-500" : "border-gray-800 focus:border-blue-500"
                                            )}
                                        />
                                    </div>
                                </div>
                            </div>
                        )}

                        {clientSecret && stripePromise ? (
                            <Elements stripe={stripePromise} options={{ clientSecret }}>
                                <StripePaymentForm
                                    clientSecret={clientSecret}
                                    totalPrice={Number(totalPrice)}
                                    onSuccess={() => {
                                        toast.success("Payment successful!");
                                        clearCart();
                                        navigate('/customer/orders');
                                    }}
                                />
                            </Elements>
                        ) : (

                            <button
                                onClick={handleCheckout}
                                className="w-full bg-blue-600 hover:bg-blue-500 text-white py-5 rounded-2xl font-black uppercase tracking-widest shadow-xl shadow-blue-600/20 active:scale-[0.98] transition-all flex items-center justify-center space-x-3 group"
                            >
                                <span>
                                    {selectedProvider && !selectedProvider.includes('delivery')
                                        ? `Pay R ${totalPrice}`
                                        : 'Place Order'
                                    }
                                </span>
                                <ArrowRight size={20} className="group-hover:translate-x-1 transition-transform" />
                            </button>
                        )}
                        <div className="flex items-center justify-center space-x-2 text-gray-600 pt-2">
                            <ShieldCheck size={14} />
                            <span className="text-[10px] font-black uppercase tracking-widest">Secure Checkout</span>
                        </div>
                    </div>

                    <Link to="/customer" className="md:hidden w-full flex items-center justify-center space-x-2 text-blue-500 font-bold p-4 bg-gray-900 border border-gray-800 rounded-2xl">
                        <Plus size={18} />
                        <span className="uppercase tracking-widest text-xs">Find more flavors</span>
                    </Link>
                </div>
            </div>
        </div >

    );
};

export default Cart;
