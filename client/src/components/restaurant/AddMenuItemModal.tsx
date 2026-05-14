import React, { useState, useEffect } from 'react';
import { X, Loader2, UtensilsCrossed, AlignLeft, Banknote, Image as ImageIcon } from 'lucide-react';
import { restaurantService, type MenuItem } from '../../services/restaurant';
import { toast } from 'react-hot-toast';

interface AddMenuItemModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSuccess: () => void;
    restaurantId: string;
    itemToEdit?: MenuItem | null;
}

const AddMenuItemModal: React.FC<AddMenuItemModalProps> = ({ isOpen, onClose, onSuccess, restaurantId, itemToEdit }) => {
    const [name, setName] = useState('');
    const [description, setDescription] = useState('');
    const [price, setPrice] = useState('');
    const [imageUrl, setImageUrl] = useState('');
    const [isAvailable, setIsAvailable] = useState(true);
    const [isSubmitting, setIsSubmitting] = useState(false);

    useEffect(() => {
        if (itemToEdit) {
            setName(itemToEdit.name);
            setDescription(itemToEdit.description || '');
            setPrice(itemToEdit.price.toString());
            setImageUrl(itemToEdit.image_url || '');
            setIsAvailable(itemToEdit.is_available);
        } else {
            setName('');
            setDescription('');
            setPrice('');
            setImageUrl('');
            setIsAvailable(true);
        }
    }, [itemToEdit, isOpen]);

    if (!isOpen) return null;

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!name || !price) {
            toast.error('Name and Price are required');
            return;
        }

        try {
            setIsSubmitting(true);
            const payload = {
                name,
                description,
                price: parseFloat(price),
                image_url: imageUrl || null,
                is_available: isAvailable
            };

            if (itemToEdit) {
                await restaurantService.updateMenuItem(itemToEdit.id, payload);
                toast.success('Menu item updated successfully');
            } else {
                await restaurantService.createMenuItem(restaurantId, payload);
                toast.success('Menu item added successfully');
            }
            onSuccess();
            onClose();
        } catch (error) {
            toast.error(itemToEdit ? 'Failed to update item' : 'Failed to add menu item');
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            {/* Backdrop */}
            <div
                className="absolute inset-0 bg-black/60 backdrop-blur-sm animate-in fade-in duration-300"
                onClick={onClose}
            ></div>

            {/* Modal */}
            <div className="bg-gray-900 border border-gray-800 w-full max-w-lg rounded-3xl overflow-hidden shadow-2xl relative z-10 animate-in zoom-in-95 duration-200">
                <div className="p-6 border-b border-gray-800 flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                        <div className="w-10 h-10 bg-blue-500/10 rounded-xl flex items-center justify-center text-blue-500">
                            <UtensilsCrossed size={20} />
                        </div>
                        <h2 className="text-xl font-bold text-white tracking-tighter">
                            {itemToEdit ? 'Edit Dish' : 'Add New Dish'}
                        </h2>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 hover:bg-gray-800 rounded-full text-gray-400 hover:text-white transition-colors"
                    >
                        <X size={20} />
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="p-6 space-y-5">
                    <div className="space-y-2">
                        <label className="text-xs font-bold text-gray-500 uppercase tracking-widest flex items-center space-x-2">
                            <UtensilsCrossed size={14} className="text-blue-500/50" />
                            <span>Dish Name</span>
                        </label>
                        <input
                            type="text"
                            required
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            placeholder="e.g. Signature Chicken Dust"
                            className="w-full bg-gray-950 border border-gray-800 rounded-2xl px-4 py-3 text-white outline-none focus:ring-1 focus:ring-blue-500 transition-all placeholder-gray-600"
                        />
                    </div>

                    <div className="space-y-2">
                        <label className="text-xs font-bold text-gray-500 uppercase tracking-widest flex items-center space-x-2">
                            <AlignLeft size={14} className="text-blue-500/50" />
                            <span>Description</span>
                        </label>
                        <textarea
                            value={description}
                            onChange={(e) => setDescription(e.target.value)}
                            placeholder="Describe your dish..."
                            rows={3}
                            className="w-full bg-gray-950 border border-gray-800 rounded-2xl px-4 py-3 text-white outline-none focus:ring-1 focus:ring-blue-500 transition-all placeholder-gray-600 resize-none"
                        ></textarea>
                    </div>

                    <div className="space-y-2">
                        <label className="text-xs font-bold text-gray-500 uppercase tracking-widest flex items-center space-x-2">
                            <Banknote size={14} className="text-blue-500/50" />
                            <span>Price (R)</span>
                        </label>
                        <input
                            type="number"
                            step="0.01"
                            required
                            value={price}
                            onChange={(e) => setPrice(e.target.value)}
                            placeholder="0.00"
                            className="w-full bg-gray-950 border border-gray-800 rounded-2xl px-4 py-3 text-white outline-none focus:ring-1 focus:ring-blue-500 transition-all placeholder-gray-600"
                        />
                    </div>

                    <div className="space-y-2">
                        <label className="text-xs font-bold text-gray-500 uppercase tracking-widest flex items-center space-x-2">
                            <ImageIcon size={14} className="text-blue-500/50" />
                            <span>Image URL (Optional)</span>
                        </label>
                        <input
                            type="url"
                            value={imageUrl}
                            onChange={(e) => setImageUrl(e.target.value)}
                            placeholder="https://example.com/item.jpg"
                            className="w-full bg-gray-950 border border-gray-800 rounded-2xl px-4 py-3 text-white outline-none focus:ring-1 focus:ring-blue-500 transition-all placeholder-gray-600"
                        />
                    </div>

                    <div className="flex items-center space-x-3 p-4 bg-gray-950 border border-gray-800 rounded-2xl">
                        <input
                            type="checkbox"
                            id="isAvailable"
                            checked={isAvailable}
                            onChange={(e) => setIsAvailable(e.target.checked)}
                            className="w-5 h-5 rounded border-gray-800 bg-gray-900 text-blue-600 focus:ring-blue-500 transition-all hover:scale-110"
                        />
                        <label htmlFor="isAvailable" className="text-sm font-bold text-gray-400 cursor-pointer select-none">
                            Item is available for order
                        </label>
                    </div>

                    <div className="pt-4 flex gap-4">
                        <button
                            type="button"
                            onClick={onClose}
                            className="flex-1 py-3 bg-gray-800 hover:bg-gray-700 text-white font-bold rounded-2xl transition-all"
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            disabled={isSubmitting}
                            className="flex-1 py-3 bg-blue-600 hover:bg-blue-500 text-white font-bold rounded-2xl transition-all shadow-lg shadow-blue-600/20 active:scale-95 disabled:opacity-50 flex items-center justify-center space-x-2"
                        >
                            {isSubmitting ? (
                                <>
                                    <Loader2 size={20} className="animate-spin" />
                                    <span>{itemToEdit ? 'Updating...' : 'Adding...'}</span>
                                </>
                            ) : (
                                <span>{itemToEdit ? 'Update Dish' : 'Save Dish'}</span>
                            )}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default AddMenuItemModal;
