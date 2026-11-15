import { Plus, Trash2, X } from 'lucide-react';
import type { OptionGroup } from '../../utils/menu';

/** Ready-made groups a township kitchen often needs; the owner can change everything after. */
const STARTERS: { label: string; group: OptionGroup }[] = [
    {
        label: 'Spice level',
        group: { name: 'Spice level', min_select: 1, max_select: 1, choices: [{ name: 'Mild', price: 0 }, { name: 'Hot', price: 0 }, { name: 'Extra hot', price: 0 }] },
    },
    {
        label: 'Extras',
        group: { name: 'Extras', min_select: 0, max_select: 3, choices: [{ name: 'Extra chips', price: 10 }, { name: 'Cheese', price: 6 }, { name: 'Egg', price: 5 }] },
    },
    {
        label: 'Choice of drink',
        group: { name: 'Drink', min_select: 1, max_select: 1, choices: [{ name: 'Coke', price: 0 }, { name: 'Fanta', price: 0 }, { name: 'Sprite', price: 0 }] },
    },
];

type Kind = 'must_one' | 'may_one' | 'many';
const kindOf = (group: OptionGroup): Kind =>
    group.max_select > 1 ? 'many' : group.min_select > 0 ? 'must_one' : 'may_one';

const field = 'w-full bg-gray-950 border border-gray-800 rounded-xl px-3 py-2.5 text-sm text-white outline-none focus:ring-1 focus:ring-brand-500 placeholder-gray-600';

/**
 * The choices on a dish: "Spice level (choose 1)", "Extras (choose up to 3)".
 * Prices here are ADDED to the dish price (0 = no extra charge).
 */
const OptionsEditor = ({ groups, onChange }: { groups: OptionGroup[]; onChange: (groups: OptionGroup[]) => void }) => {
    const update = (index: number, changes: Partial<OptionGroup>) =>
        onChange(groups.map((group, i) => (i === index ? { ...group, ...changes } : group)));

    const setKind = (index: number, kind: Kind) => {
        const group = groups[index];
        if (kind === 'must_one') update(index, { min_select: 1, max_select: 1 });
        if (kind === 'may_one') update(index, { min_select: 0, max_select: 1 });
        if (kind === 'many') update(index, { min_select: 0, max_select: Math.max(2, group.choices.length) });
    };

    const updateChoice = (index: number, choiceIndex: number, changes: Partial<OptionGroup['choices'][number]>) =>
        update(index, { choices: groups[index].choices.map((c, i) => (i === choiceIndex ? { ...c, ...changes } : c)) });

    return (
        <div className="space-y-4">
            {groups.map((group, index) => {
                const kind = kindOf(group);
                return (
                    <div key={group.id ?? `new-${index}`} className="p-4 bg-gray-950 border border-gray-800 rounded-2xl space-y-3">
                        <div className="flex items-center gap-2">
                            <input
                                aria-label="Group name"
                                value={group.name}
                                maxLength={40}
                                onChange={e => update(index, { name: e.target.value })}
                                placeholder="e.g. Spice level"
                                className={`${field} font-bold`}
                            />
                            <button type="button" aria-label={`Remove ${group.name || 'group'}`}
                                onClick={() => onChange(groups.filter((_, i) => i !== index))}
                                className="p-2.5 text-gray-500 hover:text-red-500 rounded-xl shrink-0">
                                <Trash2 size={18} />
                            </button>
                        </div>

                        <div className="flex flex-wrap items-center gap-2">
                            <select aria-label="How customers choose" value={kind} onChange={e => setKind(index, e.target.value as Kind)} className={`${field} w-auto`}>
                                <option value="must_one">Customer must choose 1</option>
                                <option value="may_one">Customer may choose 1 (optional)</option>
                                <option value="many">Customer may choose several</option>
                            </select>
                            {kind === 'many' && (
                                <label className="flex items-center gap-2 text-sm text-gray-400">
                                    up to
                                    <input type="number" min={2} max={Math.max(2, group.choices.length)} value={group.max_select}
                                        onChange={e => update(index, { max_select: Math.max(2, Math.min(group.choices.length || 2, Number(e.target.value) || 2)) })}
                                        className={`${field} w-16`} />
                                </label>
                            )}
                        </div>

                        <div className="space-y-2">
                            {group.choices.map((choice, choiceIndex) => (
                                <div key={choice.id ?? `c-${choiceIndex}`} className="flex items-center gap-2">
                                    <input aria-label="Choice" value={choice.name} maxLength={60}
                                        onChange={e => updateChoice(index, choiceIndex, { name: e.target.value })}
                                        placeholder="e.g. Hot" className={field} />
                                    <div className="relative w-28 shrink-0">
                                        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-xs text-gray-500">+R</span>
                                        <input aria-label="Extra price" type="number" min={0} step="0.50"
                                            value={choice.price === 0 || choice.price === '0.00' ? '' : choice.price}
                                            onChange={e => updateChoice(index, choiceIndex, { price: e.target.value === '' ? 0 : e.target.value })}
                                            placeholder="0" className={`${field} pl-8`} />
                                    </div>
                                    <label title="Uncheck when it runs out" className="flex items-center gap-1 text-xs text-gray-500 shrink-0 cursor-pointer">
                                        <input type="checkbox" checked={choice.available !== false}
                                            onChange={e => updateChoice(index, choiceIndex, { available: e.target.checked })}
                                            className="accent-brand-600" />
                                        In stock
                                    </label>
                                    <button type="button" aria-label={`Remove ${choice.name || 'choice'}`}
                                        onClick={() => update(index, { choices: group.choices.filter((_, i) => i !== choiceIndex) })}
                                        className="p-2 text-gray-600 hover:text-red-500 shrink-0">
                                        <X size={16} />
                                    </button>
                                </div>
                            ))}
                            <button type="button" onClick={() => update(index, { choices: [...group.choices, { name: '', price: 0 }] })}
                                className="text-sm font-bold text-brand-500 hover:text-brand-400 flex items-center gap-1">
                                <Plus size={14} /> Add a choice
                            </button>
                        </div>
                    </div>
                );
            })}

            <div className="flex flex-wrap items-center gap-2">
                <button type="button" onClick={() => onChange([...groups, { name: '', min_select: 1, max_select: 1, choices: [{ name: '', price: 0 }] }])}
                    className="px-3.5 py-2 rounded-xl bg-gray-800 hover:bg-gray-700 text-white text-sm font-bold flex items-center gap-1">
                    <Plus size={14} /> Add options
                </button>
                {STARTERS.filter(s => !groups.some(g => g.name.toLowerCase() === s.group.name.toLowerCase())).map(starter => (
                    <button key={starter.label} type="button"
                        onClick={() => onChange([...groups, structuredClone(starter.group)])}
                        className="px-3 py-2 rounded-xl border border-gray-800 hover:border-gray-600 text-gray-400 text-sm font-bold">
                        + {starter.label}
                    </button>
                ))}
            </div>
        </div>
    );
};

export default OptionsEditor;
