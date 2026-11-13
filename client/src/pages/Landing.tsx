import { Link } from 'react-router-dom';
import {
    UtensilsCrossed,
    ArrowRight,
    Star,
    Flame,
    ChevronDown,
    Instagram,
    Facebook,
    Twitter
} from 'lucide-react';
import { motion } from 'framer-motion';
import images from '../constant/images';

const Landing = () => {
    return (
        <div className="min-h-screen bg-gray-950 text-white font-sans selection:bg-brand-500/30 overflow-x-hidden">
            {/* Navigation */}
            <nav className="fixed top-0 left-0 right-0 z-50 bg-gray-950/40 backdrop-blur-2xl border-b border-white/5">
                <div className="max-w-7xl mx-auto px-6 h-24 flex justify-between items-center">
                    <div className="flex items-center space-x-4 group cursor-pointer">
                        <div className="w-12 h-12 bg-brand-600 rounded-2xl flex items-center justify-center shadow-2xl shadow-brand-600/40 group-hover:rotate-12 transition-transform duration-500">
                            <UtensilsCrossed className="text-white w-7 h-7" />
                        </div>
                        <div className="flex flex-col -space-y-1">
                            <span className="text-3xl font-black tracking-tighter uppercase italic text-white">L'vovo</span>
                            <span className="text-[10px] font-black uppercase tracking-[0.3em] text-brand-500">Premium Grill</span>
                        </div>
                    </div>

                    <div className="hidden md:flex items-center space-x-12">
                        {['Menu', 'About', 'Locations', 'Reviews'].map((item) => (
                            <a key={item} href={`#${item.toLowerCase()}`} className="text-[10px] font-black uppercase tracking-widest text-gray-400 hover:text-white transition-colors">
                                {item}
                            </a>
                        ))}
                    </div>

                    <div className="flex items-center space-x-6">
                        <Link to="/login" className="text-xs font-black uppercase tracking-widest text-white hover:text-brand-500 transition-colors">Sign In</Link>
                        <Link
                            to="/register"
                            className="px-8 py-4 bg-white text-black text-[10px] font-black uppercase tracking-[0.2em] rounded-2xl hover:bg-brand-600 hover:text-white transition-all shadow-2xl active:scale-95"
                        >
                            Order Now
                        </Link>
                    </div>
                </div>
            </nav>

            {/* Immersive Hero Section */}
            <header className="relative h-screen flex items-center justify-center overflow-hidden">
                {/* Visual Asset: Hero Image */}
                <div className="absolute inset-0 z-0">
                    <img
                        src={images.grilledChicken}
                        alt="Signature Charcoal Grilled Chicken"
                        loading="lazy"
                        className="w-full h-full object-cover scale-105"
                    />
                    <div className="absolute inset-0 bg-linear-gradient-to-t from-gray-950 via-gray-950/40 to-transparent"></div>
                    <div className="absolute inset-0 bg-black/40"></div>
                </div>

                <div className="relative z-10 max-w-6xl mx-auto px-6 text-center space-y-12">
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="inline-flex items-center space-x-3 px-6 py-2 bg-white/5 backdrop-blur-md border border-white/10 rounded-full"
                    >
                        <Flame size={16} className="text-brand-500 fill-current" />
                        <span className="text-[10px] font-black uppercase tracking-[0.4em] text-white">Est. 2024 • Matafini Masterpiece</span>
                    </motion.div>

                    <motion.div
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ delay: 0.1, duration: 0.8 }}
                    >
                        <h1 className="text-7xl md:text-[10rem] font-black tracking-tighter leading-[0.8] uppercase italic drop-shadow-2xl">
                            Fire <br />
                            <span className="text-transparent border-t-2 border-b-2 border-white/20 px-8 py-2 bg-clip-text bg-linear-gradient-to-t from-brand-500 to-brand-400">Forged</span>
                        </h1>
                    </motion.div>

                    <motion.p
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.4 }}
                        className="max-w-2xl mx-auto text-gray-300 text-lg md:text-2xl font-medium leading-relaxed italic"
                    >
                        "The soul of the street, served with the elegance of a masterpiece."
                    </motion.p>

                    <motion.div
                        initial={{ opacity: 0, y: 30 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.6 }}
                        className="flex flex-col sm:flex-row items-center justify-center gap-8 pt-6"
                    >
                        <Link
                            to="/register"
                            className="w-full sm:w-auto px-12 py-6 bg-brand-600 text-white font-black uppercase tracking-[0.2em] text-xs rounded-2xl shadow-[0_20px_50px_rgba(242,100,24,0.3)] hover:bg-brand-500 hover:scale-110 active:scale-95 transition-all group flex items-center space-x-4"
                        >
                            <span>Start Your Order</span>
                            <ArrowRight size={20} className="group-hover:translate-x-1 transition-transform" />
                        </Link>
                        <div className="flex -space-x-4 items-center">
                            {[1, 2, 3, 4].map(i => (
                                <div key={i} className="w-12 h-12 rounded-full border-4 border-gray-950 bg-gray-800 overflow-hidden shadow-2xl">
                                    <div className="w-full h-full bg-brand-600/20 flex items-center justify-center text-[10px] font-black">USER</div>
                                </div>
                            ))}
                            <span className="ml-8 text-xs font-black uppercase tracking-widest text-white">Loved by 2k+ Daily</span>
                        </div>
                    </motion.div>
                </div>

                <motion.div
                    animate={{ y: [0, 10, 0] }}
                    transition={{ repeat: Infinity, duration: 2 }}
                    className="absolute bottom-12 left-1/2 -translate-x-1/2 text-gray-500 border border-white/10 p-2 rounded-full backdrop-blur-md"
                >
                    <ChevronDown size={24} />
                </motion.div>
            </header>

            {/* Atmosphere Section */}
            <section className="py-40 px-6 relative overflow-hidden bg-gray-950">
                <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-24 items-center">
                    <div className="space-y-12 relative z-10">
                        <div className="space-y-4">
                            <h2 className="text-xs font-black text-brand-500 uppercase tracking-[0.5em]">The Craft</h2>
                            <h3 className="text-5xl md:text-8xl font-black uppercase tracking-tighter italic leading-[0.85]">Taste the <br /> <span className="text-gray-400">Tradition</span></h3>
                        </div>

                        <div className="space-y-8 text-gray-400 text-lg leading-relaxed">
                            <p>
                                At L'vovo, we don't just grill chicken; we orchestrate a symphony of smoke, flame, and spice. Every bird is marinated for 24 hours in our secret Matafini blend before meeting the intense heat of raw charcoal.
                            </p>
                            <p className="italic text-white font-bold border-l-4 border-brand-600 pl-8">
                                "It's not just food—it's the heartbeat of our streets brought to life on your plate."
                            </p>
                        </div>

                        <div className="grid grid-cols-2 gap-12 pt-8">
                            <div>
                                <p className="text-4xl font-black italic text-white mb-1 tracking-tighter">100%</p>
                                <p className="text-[10px] font-black uppercase tracking-widest text-gray-500">Natural Charcoal</p>
                            </div>
                            <div>
                                <p className="text-4xl font-black italic text-white mb-1 tracking-tighter">Local</p>
                                <p className="text-[10px] font-black uppercase tracking-widest text-gray-500">Premium Produce</p>
                            </div>
                        </div>
                    </div>

                    <div className="relative group">
                        {/* Visual Asset: Atmosphere Image */}
                        <div className="absolute -inset-4 bg-brand-600/20 blur-2xl rounded-[60px] opacity-0 group-hover:opacity-100 transition-opacity duration-700"></div>
                        <div className="relative rounded-[60px] overflow-hidden border border-white/10 shadow-3xl">
                            <img
                                src={images.halfchicken}
                                alt="Authentic Grill Atmosphere"
                                loading="lazy"
                                className="w-full h-full object-cover grayscale-[0.3] group-hover:grayscale-0 group-hover:scale-105 transition-all duration-700"
                            />
                        </div>

                        {/* Floating Badge */}
                        <div className="absolute -bottom-10 -right-10 w-44 h-44 bg-brand-600 rounded-full flex flex-col items-center justify-center p-6 text-center shadow-2xl rotate-12 group-hover:rotate-0 transition-transform duration-500">
                            <p className="text-2xl font-black italic uppercase leading-none text-white">Chef's</p>
                            <p className="text-[10px] font-black uppercase tracking-widest text-brand-100">Choice 2024</p>
                        </div>
                    </div>
                </div>
            </section>

            {/* Signature Platters Section */}
            <section className="py-40 bg-gray-900/30 border-y border-white/5 px-6 overflow-hidden">
                <div className="max-w-7xl mx-auto space-y-24">
                    <div className="flex flex-col items-center text-center space-y-6">
                        <h2 className="text-xs font-black text-brand-500 uppercase tracking-[0.5em]">The Showcase</h2>
                        <h3 className="text-4xl md:text-7xl font-black uppercase tracking-tighter italic">Signature <br className="md:hidden" /> Platters</h3>
                        <div className="w-24 h-1 bg-brand-600/30 rounded-full"></div>
                    </div>

                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
                        <div className="relative order-2 lg:order-1 transition-all duration-700 hover:rotate-2">
                            {/* Visual Asset: Platter Image */}
                            <img
                                src={images.coleslaw}
                                alt="L'vovo Family Platter"
                                loading="lazy"
                                className="rounded-[40px] shadow-3xl border border-white/5"
                            />
                        </div>

                        <div className="space-y-10 order-1 lg:order-2">
                            <div className="space-y-4">
                                <h4 className="text-3xl font-black uppercase italic tracking-tighter leading-none">The Matafini <br /> Family Feast</h4>
                                <p className="text-gray-400 text-lg leading-relaxed">
                                    Our most popular selection. Featuring a whole charcoal-grilled chicken, six varieties of house-made chakalaka, velvet pap, and our signature peri-peri flame dip.
                                </p>
                            </div>

                            <ul className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                {[
                                    '24h Brined Chicken',
                                    'House Chakalaka',
                                    'Traditional Pap',
                                    'Golden Corn',
                                    'Flame Peri-Peri',
                                    'Rustic Fries'
                                ].map((item) => (
                                    <li key={item} className="flex items-center space-x-3 text-sm font-black uppercase tracking-widest text-gray-300">
                                        <div className="w-1.5 h-1.5 bg-brand-500 rounded-full"></div>
                                        <span>{item}</span>
                                    </li>
                                ))}
                            </ul>

                            <button className="flex items-center space-x-4 text-brand-500 font-bold group">
                                <span className="uppercase tracking-[0.3em] text-[10px]">View the full experience</span>
                                <div className="p-3 bg-brand-600/10 rounded-xl group-hover:bg-brand-600/20 transition-colors">
                                    <ArrowRight size={18} />
                                </div>
                            </button>
                        </div>
                    </div>
                </div>
            </section>

            {/* Testimonials Grid */}
            <section className="py-40 px-6">
                <div className="max-w-7xl mx-auto">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                        {[
                            { name: "Thabo M.", role: "Local Foodie", text: "Finally, a platform that respects the craft of street grilling. The best chicken in the province, delivered hot." },
                            { name: "Sindi L.", role: "Chef", text: "The smoke Profile is incredible. You can taste the authenticity in every single bite. A true Matafini gem." },
                            { name: "John D.", role: "Regular", text: "Fast delivery, premium packaging, and that unmistakable charcoal flavor. L'vovo is in a league of its own." }
                        ].map((review, i) => (
                            <div key={i} className="p-12 bg-gray-900 border border-white/5 rounded-[40px] space-y-8 hover:border-brand-500/30 transition-all group">
                                <div className="flex text-brand-500">
                                    {[1, 2, 3, 4, 5].map(star => <Star key={star} size={14} className="fill-current" />)}
                                </div>
                                <p className="text-xl font-bold italic text-white leading-relaxed">"{review.text}"</p>
                                <div className="flex items-center space-x-4 pt-4 border-t border-white/5">
                                    <div className="w-10 h-10 bg-gray-800 rounded-full"></div>
                                    <div>
                                        <p className="text-sm font-black uppercase italic tracking-tight">{review.name}</p>
                                        <p className="text-[10px] font-black uppercase tracking-widest text-gray-600">{review.role}</p>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* Final CTA */}
            <section className="py-20 px-6">
                <div className="max-w-7xl mx-auto relative group">
                    <div className="absolute -inset-1 bg-linear-gradient-to-t from-brand-600 to-brand-600 rounded-[80px] blur opacity-20 group-hover:opacity-40 transition duration-1000"></div>
                    <div className="relative bg-gray-950 border border-white/10 rounded-[80px] p-12 md:p-32 flex flex-col items-center text-center space-y-12 overflow-hidden shadow-3xl">
                        <div className="absolute top-0 right-0 p-24 opacity-5 pointer-events-none">
                            <UtensilsCrossed size={300} className="text-white" />
                        </div>

                        <h2 className="text-5xl md:text-8xl font-black tracking-tighter leading-none uppercase italic relative z-10 text-white">
                            The Table <br /> is <span className="text-brand-500">Ready.</span>
                        </h2>
                        <p className="max-w-xl text-gray-400 text-lg md:text-xl font-medium relative z-10 leading-relaxed">Join the inner circle of flavor. Get access to exclusive dishes and priority deliveries in Matafini.</p>

                        <div className="flex flex-col sm:flex-row gap-6 relative z-10 w-full justify-center">
                            <Link
                                to="/register"
                                className="px-14 py-7 bg-white text-black font-black uppercase tracking-[0.2em] text-[10px] rounded-2xl shadow-2xl hover:bg-brand-600 hover:text-white transition-all transform hover:scale-105 active:scale-95"
                            >
                                Secure My Spot
                            </Link>
                            <Link
                                to="/login"
                                className="px-14 py-7 bg-gray-900 border border-white/10 text-white font-black uppercase tracking-[0.2em] text-[10px] rounded-2xl hover:border-brand-500 transition-all"
                            >
                                Member Login
                            </Link>
                        </div>
                    </div>
                </div>
            </section>

            {/* Footer */}
            <footer className="py-32 px-6 border-t border-white/5 bg-gray-950">
                <div className="max-w-7xl mx-auto">
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-20">
                        <div className="col-span-1 md:col-span-2 space-y-8">
                            <div className="flex items-center space-x-4">
                                <UtensilsCrossed className="text-brand-600 w-10 h-10" />
                                <span className="text-4xl font-black tracking-tighter uppercase italic">L'vovo</span>
                            </div>
                            <p className="max-w-xs text-gray-500 font-medium leading-relaxed">
                                Redefining South African street food through premium craft and modern technology. Born in Matafini, bred for the bold.
                            </p>
                            <div className="flex space-x-6 text-gray-500">
                                <Instagram size={20} className="hover:text-brand-500 cursor-pointer transition-colors" />
                                <Facebook size={20} className="hover:text-brand-500 cursor-pointer transition-colors" />
                                <Twitter size={20} className="hover:text-brand-500 cursor-pointer transition-colors" />
                            </div>
                        </div>

                        <div className="space-y-6">
                            <h4 className="text-[10px] font-black uppercase tracking-[0.4em] text-white">Experience</h4>
                            <ul className="space-y-4 text-[10px] font-black uppercase tracking-widest text-gray-500">
                                <li className="hover:text-brand-500 cursor-pointer transition-colors">Digital Menu</li>
                                <li className="hover:text-brand-500 cursor-pointer transition-colors">Our Grillers</li>
                                <li className="hover:text-brand-500 cursor-pointer transition-colors">Matafini HQ</li>
                                <li className="hover:text-brand-500 cursor-pointer transition-colors">Sustainability</li>
                            </ul>
                        </div>

                        <div className="space-y-6">
                            <h4 className="text-[10px] font-black uppercase tracking-[0.4em] text-white">Contact</h4>
                            <ul className="space-y-4 text-[10px] font-black uppercase tracking-widest text-gray-500">
                                <li className="hover:text-brand-500 cursor-pointer transition-colors">hello@lvovo.com</li>
                                <li className="hover:text-brand-500 cursor-pointer transition-colors">+27 (0) 13 456 7890</li>
                                <li className="hover:text-brand-500 cursor-pointer transition-colors">Matafini Main Rd</li>
                            </ul>
                        </div>
                    </div>

                    <div className="pt-20 mt-20 border-t border-white/5 flex flex-col md:flex-row justify-between items-center gap-8">
                        <p className="text-[10px] font-black uppercase tracking-[0.5em] text-gray-600">&copy; 2024 L'vovo Technologies. All Rights Reserved.</p>
                        <div className="flex space-x-12 text-[10px] font-black uppercase tracking-[0.5em] text-gray-600">
                            <a href="#" className="hover:text-white transition-colors">Privacy</a>
                            <a href="#" className="hover:text-white transition-colors">Terms</a>
                            <span className="text-gray-700">|</span>
                            <span className="text-gray-700 hover:text-white transition-colors cursor-default">Map data © OpenStreetMap contributors</span>
                        </div>
                    </div>
                </div>
            </footer>
        </div>
    );
};

export default Landing;
