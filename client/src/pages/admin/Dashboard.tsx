import {
    Users,
    ShoppingBag,
    TrendingUp,
    Clock,
    ArrowUpRight,
    ArrowDownRight
} from 'lucide-react';
import { motion } from 'framer-motion';

const stats = [
    { label: 'Total Revenue', value: 'R 124,500', change: '+12.5%', icon: TrendingUp, positive: true },
    { label: 'Total Orders', value: '1,240', change: '+5.2%', icon: ShoppingBag, positive: true },
    { label: 'Active Users', value: '842', change: '-2.1%', icon: Users, positive: false },
    { label: 'Avg. Delivery', value: '24 min', change: '+1.4%', icon: Clock, positive: true },
];

const Dashboard = () => {
    return (
        <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
            {/* Welcome Section */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold text-white tracking-tight">Overview</h1>
                    <p className="text-gray-400 mt-1">Welcome back, here's what's happening today.</p>
                </div>
                <div className="flex items-center space-x-3">
                    <div className="flex -space-x-2">
                        {[1, 2, 3].map((i) => (
                            <div key={i} className="w-8 h-8 rounded-full border-2 border-gray-950 bg-gray-800 flex items-center justify-center overflow-hidden">
                                <img src={`https://i.pravatar.cc/150?u=${i}`} alt="user" className="w-full h-full object-cover" />
                            </div>
                        ))}
                        <div className="w-8 h-8 rounded-full border-2 border-gray-950 bg-gray-800 flex items-center justify-center text-[10px] font-bold text-gray-400">
                            +12
                        </div>
                    </div>
                    <span className="text-sm text-gray-400 font-medium">Active users right now</span>
                </div>
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                {stats.map((stat, index) => (
                    <motion.div
                        key={stat.label}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: index * 0.1 }}
                        className="group p-6 bg-gray-900/40 backdrop-blur-xl border border-gray-800 rounded-2xl hover:border-brand-500/30 transition-all duration-300"
                    >
                        <div className="flex items-start justify-between">
                            <div className="p-2 bg-gray-800/50 rounded-lg group-hover:bg-brand-500/10 transition-colors">
                                <stat.icon className="text-gray-400 group-hover:text-brand-400 transition-colors" size={24} />
                            </div>
                            <div className={`flex items-center space-x-1 px-2 py-1 rounded-full text-xs font-bold ${stat.positive ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'
                                }`}>
                                {stat.positive ? <ArrowUpRight size={12} /> : <ArrowDownRight size={12} />}
                                <span>{stat.change}</span>
                            </div>
                        </div>
                        <div className="mt-4">
                            <p className="text-sm font-medium text-gray-500">{stat.label}</p>
                            <p className="text-2xl font-bold text-white mt-1">{stat.value}</p>
                        </div>
                    </motion.div>
                ))}
            </div>

            {/* Charts / Activity Section (Simulated) */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-2 p-6 bg-gray-900/40 backdrop-blur-xl border border-gray-800 rounded-2xl">
                    <div className="flex items-center justify-between mb-8">
                        <h3 className="text-lg font-bold text-white">Order Volume</h3>
                        <select className="bg-gray-800 border-none rounded-lg text-xs font-bold text-gray-300 focus:ring-1 focus:ring-brand-500">
                            <option>Last 7 Days</option>
                            <option>Last 30 Days</option>
                        </select>
                    </div>

                    <div className="h-64 flex items-end justify-between gap-2 px-2">
                        {[45, 60, 42, 75, 55, 90, 65].map((height, i) => (
                            <div key={i} className="flex-1 flex flex-col items-center gap-2 group">
                                <div
                                    className="w-full bg-brand-500/20 group-hover:bg-brand-500/40 transition-all duration-500 rounded-t-lg relative"
                                    style={{ height: `${height}%` }}
                                >
                                    <div className="absolute -top-8 left-1/2 -translate-x-1/2 bg-gray-800 text-white text-[10px] px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity">
                                        {height * 10}
                                    </div>
                                </div>
                                <span className="text-[10px] font-bold text-gray-500">Day {i + 1}</span>
                            </div>
                        ))}
                    </div>
                </div>

                <div className="p-6 bg-gray-900/40 backdrop-blur-xl border border-gray-800 rounded-2xl">
                    <h3 className="text-lg font-bold text-white mb-6">Recent Activity</h3>
                    <div className="space-y-6">
                        {[
                            { user: 'John Doe', action: 'placed an order', time: '2 min ago', type: 'order' },
                            { user: 'Burger King', action: 'updated their menu', time: '15 min ago', type: 'update' },
                            { user: 'Alice Smith', action: 'joined the platform', time: '1 hour ago', type: 'user' },
                            { user: 'Robert Fox', action: 'completed delivery', time: '2 hours ago', type: 'delivery' },
                        ].map((item, i) => (
                            <div key={i} className="flex items-start space-x-3">
                                <div className="w-8 h-8 rounded-full bg-gray-800 flex-shrink-0 flex items-center justify-center overflow-hidden border border-gray-700">
                                    <img src={`https://i.pravatar.cc/150?u=${i + 10}`} alt="avatar" />
                                </div>
                                <div className="flex-1 min-w-0">
                                    <p className="text-sm font-medium text-white truncate">
                                        <span className="font-bold">{item.user}</span> {item.action}
                                    </p>
                                    <p className="text-xs text-gray-500 mt-0.5">{item.time}</p>
                                </div>
                            </div>
                        ))}
                    </div>
                    <button className="w-full mt-6 py-2.5 bg-gray-800/50 hover:bg-gray-800 text-xs font-bold text-brand-500 rounded-xl transition-colors border border-gray-700">
                        View All Activity
                    </button>
                </div>
            </div>
        </div>
    );
};

export default Dashboard;
