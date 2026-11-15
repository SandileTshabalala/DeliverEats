/**
 * Menu sections ("Mains", "Drinks") and dish options ("Spice level", "Extras").
 * The server checks every pick and works out the price; these helpers only
 * show the customer the same numbers before they order.
 */

export interface OptionChoice {
    id?: string;
    name: string;
    /** added to the dish price; 0 = free choice */
    price: number | string;
    available?: boolean;
}

export interface OptionGroup {
    id?: string;
    name: string;
    /** 0 = optional, 1 = the customer must pick one */
    min_select: number;
    /** 1 = pick one, more = pick up to this many */
    max_select: number;
    choices: OptionChoice[];
}

/** What was picked, as kept on the order line */
export interface PickedOption {
    group: string;
    name: string;
    price: number | string;
}

const cents = (value: number | string | undefined) => Math.round(Number(value || 0) * 100);

/** Dish price plus the extras picked (ids of choices). */
export const unitPrice = (price: number | string, groups: OptionGroup[] | undefined, picked: string[]) => {
    let total = cents(price);
    for (const group of groups ?? []) {
        for (const choice of group.choices) {
            if (choice.id && picked.includes(choice.id)) total += cents(choice.price);
        }
    }
    return total / 100;
};

/** The picks as the order line will show them. */
export const pickedOptions = (groups: OptionGroup[] | undefined, picked: string[]): PickedOption[] =>
    (groups ?? []).flatMap(group => group.choices
        .filter(choice => choice.id && picked.includes(choice.id))
        .map(choice => ({ group: group.name, name: choice.name, price: choice.price })));

/** Groups where the customer still has to choose (to grey out "Add"). */
export const missingChoices = (groups: OptionGroup[] | undefined, picked: string[]) =>
    (groups ?? []).filter(group => group.choices.filter(c => c.id && picked.includes(c.id)).length < group.min_select);

/** "Hot, Extra chips" */
export const describePicks = (picks?: PickedOption[] | null) => (picks ?? []).map(p => p.name).join(', ');

/** One cart line per dish + picks: "Kota, hot" and "Kota, mild" are two lines. */
export const lineKey = (itemId: string, picked: string[] = []) =>
    picked.length ? `${itemId}|${[...picked].sort().join(',')}` : itemId;

/** How a group asks: "Choose 1", "Choose up to 3", "(optional)" */
export const groupRule = (group: OptionGroup) => {
    const many = group.max_select === 1 ? 'Choose 1' : `Choose up to ${group.max_select}`;
    return group.min_select > 0 ? (group.max_select === 1 ? 'Choose 1' : `Choose ${group.min_select}–${group.max_select}`) : `${many} (optional)`;
};

/**
 * Items grouped by section in the restaurant's order. Sections it has not
 * placed come after, in A-Z order; dishes with no section come first under "".
 */
export const bySection = <T extends { section?: string | null }>(items: T[], order: string[] = []) => {
    const groups = new Map<string, T[]>();
    for (const item of items) {
        const name = (item.section ?? '').trim();
        const key = [...groups.keys()].find(k => k.toLowerCase() === name.toLowerCase()) ?? name;
        groups.set(key, [...(groups.get(key) ?? []), item]);
    }
    const rank = (name: string) => {
        if (!name) return -1;
        const index = order.findIndex(o => o.toLowerCase() === name.toLowerCase());
        return index === -1 ? order.length : index;
    };
    return [...groups.entries()]
        .sort(([a], [b]) => rank(a) - rank(b) || a.localeCompare(b))
        .map(([name, sectionItems]) => ({ name, items: sectionItems }));
};

/** Section names in display order (for the restaurant to arrange). */
export const sectionNames = <T extends { section?: string | null }>(items: T[], order: string[] = []) =>
    bySection(items, order).map(s => s.name).filter(Boolean);

/** The problem with the options, if any, before saving. */
export const optionsProblem = (groups: OptionGroup[]): string | null => {
    for (const group of groups) {
        if (!group.name.trim()) return 'Give every option group a name (e.g. "Spice level").';
        const named = group.choices.filter(c => c.name.trim());
        if (named.length === 0) return `Add at least one choice to "${group.name}".`;
        if (named.some(c => Number(c.price) < 0)) return `Prices in "${group.name}" cannot be negative.`;
    }
    return null;
};

/** Drop empty choice rows and send prices as numbers. */
export const cleanOptions = (groups: OptionGroup[]): OptionGroup[] =>
    groups.map(group => {
        const choices = group.choices.filter(c => c.name.trim()).map(c => ({ ...c, name: c.name.trim(), price: Number(c.price) || 0 }));
        return { ...group, name: group.name.trim(), choices, max_select: Math.min(group.max_select, Math.max(1, choices.length)) };
    });
