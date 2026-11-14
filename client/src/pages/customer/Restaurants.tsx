import { Link } from 'react-router-dom';
import { ChevronLeft } from 'lucide-react';
import RestaurantBrowser from '../../components/RestaurantBrowser';

const Restaurants = () => (
    <div className="space-y-6 animate-in fade-in duration-500">
        <div className="space-y-1">
            <Link to="/customer" className="inline-flex items-center gap-1.5 text-sm font-bold text-gray-500 hover:text-white transition-colors mb-2">
                <ChevronLeft size={16} /> Home
            </Link>
            <h1 className="text-3xl md:text-4xl font-black tracking-tight">Restaurants</h1>
            <p className="text-gray-500 font-medium">Local kitchens near you. Open ones are listed first.</p>
        </div>
        <RestaurantBrowser />
    </div>
);

export default Restaurants;
