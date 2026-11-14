import { useCallback, useEffect, useRef, useState } from 'react';
import { ArrowDown, ArrowUp, Camera, Check, Eye, EyeOff, Pencil, Plus, Tags, Trash2, X } from 'lucide-react';
import { toast } from 'react-hot-toast';
import { clsx } from 'clsx';
import { errorMessage } from '../../services/billing';
import { assetUrl, resizeImage } from '../../services/platform';
import { categories as api, fallbackImage, type AdminCategory } from '../../services/categories';

const input = "w-full bg-gray-950 border border-gray-800 rounded-xl px-4 py-2.5 text-white placeholder-gray-600 focus:border-brand-500 outline-none";

const Row = ({ category, first, last, onChanged, onMove }: {
    category: AdminCategory; first: boolean; last: boolean;
    onChanged: () => void; onMove: (direction: -1 | 1) => void;
}) => {
    const [editing, setEditing] = useState(false);
    const [name, setName] = useState(category.name);
    const [busy, setBusy] = useState(false);
    const fileInput = useRef<HTMLInputElement>(null);

    const run = async (action: () => Promise<unknown>, done: string, failed: string) => {
        setBusy(true);
        try {
            await action();
            toast.success(done);
            onChanged();
        } catch (error) {
            toast.error(errorMessage(error, failed));
        } finally {
            setBusy(false);
        }
    };

    const rename = (event: React.FormEvent) => {
        event.preventDefault();
        if (name.trim() === category.name) { setEditing(false); return; }
        run(() => api.update(category.id, { name }), 'Category renamed', 'Could not rename').then(() => setEditing(false));
    };

    const chooseImage = async (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        event.target.value = '';
        if (!file) return;
        run(async () => api.uploadImage(category.id, await resizeImage(file, 400)), 'Picture saved', 'Could not upload the picture');
    };

    const remove = () => {
        const used = category.restaurant_count;
        const warning = used
            ? `Delete "${category.name}"? ${used} restaurant${used === 1 ? '' : 's'} use it; they keep their other categories. Hiding it instead can be undone.`
            : `Delete "${category.name}"?`;
        if (window.confirm(warning)) run(() => api.remove(category.id), 'Category deleted', 'Could not delete');
    };

    const picture = category.image_url ? assetUrl(category.image_url) : fallbackImage(category.name);

    return (
        <li className={clsx("flex items-center gap-4 p-4 bg-gray-900 border border-gray-800 rounded-2xl", !category.is_active && "opacity-60", busy && "pointer-events-none opacity-50")}>
            <div className="flex flex-col">
                <button onClick={() => onMove(-1)} disabled={first} aria-label={`Move ${category.name} up`} className="p-1 text-gray-500 hover:text-white disabled:opacity-20"><ArrowUp size={16} /></button>
                <button onClick={() => onMove(1)} disabled={last} aria-label={`Move ${category.name} down`} className="p-1 text-gray-500 hover:text-white disabled:opacity-20"><ArrowDown size={16} /></button>
            </div>

            <button onClick={() => fileInput.current?.click()} className="group relative w-16 h-16 rounded-full overflow-hidden bg-gray-800 flex-shrink-0 flex items-center justify-center" aria-label={`Change picture for ${category.name}`}>
                {picture ? <img src={picture} alt="" className="w-full h-full object-cover" /> : <Tags size={22} className="text-gray-500" />}
                <span className="keep-dark absolute inset-0 bg-black/50 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                    <Camera size={18} className="text-white" />
                </span>
            </button>
            <input ref={fileInput} type="file" accept="image/png,image/jpeg,image/webp" className="hidden" onChange={chooseImage} />

            <div className="flex-1 min-w-0">
                {editing ? (
                    <form onSubmit={rename} className="flex items-center gap-2">
                        <input autoFocus maxLength={40} className={input} value={name} onChange={e => setName(e.target.value)} aria-label="Category name" />
                        <button type="submit" className="p-2.5 rounded-xl bg-brand-500 text-white" aria-label="Save name"><Check size={16} /></button>
                        <button type="button" onClick={() => { setName(category.name); setEditing(false); }} className="p-2.5 rounded-xl bg-gray-800 text-gray-300" aria-label="Cancel"><X size={16} /></button>
                    </form>
                ) : (
                    <>
                        <p className="font-bold truncate">{category.name}{!category.is_active && <span className="ml-2 text-xs font-bold text-gray-500">Hidden</span>}</p>
                        <p className="text-xs text-gray-500">
                            {category.restaurant_count} restaurant{category.restaurant_count === 1 ? '' : 's'}
                            {' · '}
                            {category.image_url ? (
                                <button onClick={() => run(() => api.removeImage(category.id), 'Picture removed', 'Could not remove')} className="text-gray-400 hover:text-white underline">remove picture</button>
                            ) : picture ? 'stock picture until you upload one' : 'no picture yet'}
                        </p>
                    </>
                )}
            </div>

            {!editing && (
                <div className="flex items-center gap-1">
                    <button onClick={() => setEditing(true)} className="p-2.5 rounded-xl text-gray-400 hover:text-white hover:bg-gray-800" aria-label={`Rename ${category.name}`}><Pencil size={16} /></button>
                    <button
                        onClick={() => run(() => api.update(category.id, { is_active: !category.is_active }), category.is_active ? 'Hidden from customers' : 'Visible again', 'Could not update')}
                        className="p-2.5 rounded-xl text-gray-400 hover:text-white hover:bg-gray-800"
                        aria-label={category.is_active ? `Hide ${category.name}` : `Show ${category.name}`}
                        title={category.is_active ? 'Hide' : 'Show'}
                    >
                        {category.is_active ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                    <button onClick={remove} className="p-2.5 rounded-xl text-gray-400 hover:text-red-400 hover:bg-red-500/10" aria-label={`Delete ${category.name}`}><Trash2 size={16} /></button>
                </div>
            )}
        </li>
    );
};

const Categories = () => {
    const [list, setList] = useState<AdminCategory[]>([]);
    const [loading, setLoading] = useState(true);
    const [newName, setNewName] = useState('');
    const [adding, setAdding] = useState(false);

    const load = useCallback(async () => {
        try {
            setList(await api.all());
        } catch (error) {
            toast.error(errorMessage(error, 'Could not load categories'));
        } finally {
            setLoading(false);
        }
    }, []);
    useEffect(() => { load(); }, [load]);

    const add = async (event: React.FormEvent) => {
        event.preventDefault();
        if (!newName.trim()) return;
        setAdding(true);
        try {
            await api.create(newName);
            setNewName('');
            toast.success('Category added. Add a picture so it stands out.');
            load();
        } catch (error) {
            toast.error(errorMessage(error, 'Could not add the category'));
        } finally {
            setAdding(false);
        }
    };

    const move = async (index: number, direction: -1 | 1) => {
        const ids = list.map(c => c.id);
        [ids[index], ids[index + direction]] = [ids[index + direction], ids[index]];
        setList(ids.map(id => list.find(c => c.id === id)!)); // show it straight away
        try {
            setList(await api.reorder(ids));
        } catch (error) {
            toast.error(errorMessage(error, 'Could not save the order'));
            load();
        }
    };

    return (
        <div className="space-y-6 max-w-3xl">
            <div>
                <h1 className="text-2xl font-black">Categories</h1>
                <p className="text-gray-500 text-sm mt-1">
                    The food types customers browse by, shown as picture tiles on their home screen in this order.
                    Restaurants pick up to 3 of these in their settings.
                </p>
            </div>

            <form onSubmit={add} className="flex gap-2">
                <input className={input} maxLength={40} placeholder="New category, e.g. Seafood" value={newName} onChange={e => setNewName(e.target.value)} aria-label="New category name" />
                <button type="submit" disabled={adding || !newName.trim()} className="flex items-center gap-2 px-5 rounded-xl bg-brand-500 hover:bg-brand-600 text-white font-bold disabled:opacity-50 whitespace-nowrap">
                    <Plus size={18} /> Add
                </button>
            </form>

            {loading ? (
                <div className="space-y-3">{[1, 2, 3, 4].map(i => <div key={i} className="h-24 bg-gray-900 rounded-2xl animate-pulse" />)}</div>
            ) : list.length === 0 ? (
                <p className="text-gray-500 text-center py-12">No categories yet. Add the first one above.</p>
            ) : (
                <ul className="space-y-3">
                    {list.map((category, index) => (
                        <Row key={`${category.id}-${category.name}`} category={category} first={index === 0} last={index === list.length - 1}
                            onChanged={load} onMove={direction => move(index, direction)} />
                    ))}
                </ul>
            )}
        </div>
    );
};

export default Categories;
