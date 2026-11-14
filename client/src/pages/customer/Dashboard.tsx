import { Link } from 'react-router-dom';
import { MapPin } from 'lucide-react';
import RestaurantBrowser from '../../components/RestaurantBrowser';
import { useAuth } from '../../context/AuthContext';
import { addressLabel, useDeliveryAddress } from '../../hooks/useDeliveryAddress';

const greeting = () => {
    const hour = new Date().getHours();
    return hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening';
};

const Dashboard = () => {
    const { user } = useAuth();
    const { chosen, loading: addressLoading } = useDeliveryAddress();

    return (
        <div className="space-y-6 animate-in fade-in duration-500">
            <header className="space-y-5">
                <div>
                    <p className="text-gray-400 font-medium">{greeting()}{user?.name ? `, ${user.name}` : ''}</p>
                    <h1 className="text-3xl md:text-4xl font-black tracking-tight">What are you craving?</h1>
                </div>

                {!addressLoading && !chosen && (
                    <Link to="/customer/profile" className="flex items-center gap-3 p-4 rounded-2xl bg-brand-500/10 border border-brand-500/20 text-sm">
                        <MapPin size={18} className="text-brand-500 flex-shrink-0" />
                        <span><span className="font-bold text-white">Add your delivery address</span> <span className="text-gray-400">to see who delivers to you and what delivery costs.</span></span>
                    </Link>
                )}
                {chosen && (
                    <p className="flex items-center gap-2 text-sm text-gray-400">
                        <MapPin size={16} className="text-brand-500" />
                        Delivering to <span className="font-bold text-white">{addressLabel(chosen)}</span>
                    </p>
                )}
            </header>

            <RestaurantBrowser />
        </div>
    );
};

export default Dashboard;
