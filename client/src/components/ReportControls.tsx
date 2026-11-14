import { useState } from 'react';
import { Download, FileSpreadsheet, FileText } from 'lucide-react';
import { clsx } from 'clsx';
import { downloadFile, PERIODS } from '../services/download';
import type { Period } from '../services/download';

const input = "bg-gray-950 border border-gray-800 rounded-xl px-3 py-2.5 text-white focus:border-brand-500 outline-none";

/** From / to dates with quick choices. */
export const PeriodPicker = ({ period, onChange }: { period: Period; onChange: (period: Period) => void }) => {
    const active = PERIODS.find(choice => {
        const made = choice.make();
        return made.from === period.from && made.to === period.to;
    })?.label;
    return (
        <div className="space-y-3">
            <div className="flex flex-wrap gap-2">
                {PERIODS.map(choice => (
                    <button
                        key={choice.label}
                        type="button"
                        aria-pressed={active === choice.label}
                        onClick={() => onChange(choice.make())}
                        className={clsx(
                            "px-4 py-2 rounded-xl text-sm font-bold transition-colors",
                            active === choice.label ? "bg-white text-black" : "bg-gray-950 border border-gray-800 text-gray-400 hover:text-white"
                        )}
                    >
                        {choice.label}
                    </button>
                ))}
            </div>
            <div className="flex flex-wrap items-end gap-3">
                <label className="text-xs font-bold text-gray-500 uppercase tracking-widest space-y-1.5">
                    <span className="block">From</span>
                    <input type="date" className={input} value={period.from} max={period.to} onChange={e => onChange({ ...period, from: e.target.value })} />
                </label>
                <label className="text-xs font-bold text-gray-500 uppercase tracking-widest space-y-1.5">
                    <span className="block">To</span>
                    <input type="date" className={input} value={period.to} min={period.from} onChange={e => onChange({ ...period, to: e.target.value })} />
                </label>
            </div>
        </div>
    );
};

/** One downloadable report: what it is, and a button. */
export const ReportButton = ({ title, detail, path, period, kind, fallbackName }: {
    title: string; detail: string; path: string; period?: Period; kind: 'pdf' | 'csv'; fallbackName: string;
}) => {
    const [busy, setBusy] = useState(false);
    const go = async () => {
        setBusy(true);
        await downloadFile(path, period ? { from: period.from, to: period.to } : {}, fallbackName);
        setBusy(false);
    };
    const Icon = kind === 'pdf' ? FileText : FileSpreadsheet;
    return (
        <div className="flex flex-wrap items-center justify-between gap-4 p-4 rounded-2xl bg-gray-950 border border-gray-800">
            <div className="flex items-start space-x-3 min-w-0">
                <Icon size={22} className="text-brand-500 mt-0.5 flex-shrink-0" />
                <div className="min-w-0">
                    <p className="font-bold text-white">{title}</p>
                    <p className="text-sm text-gray-500">{detail}</p>
                </div>
            </div>
            <button
                onClick={go}
                disabled={busy}
                className="flex items-center space-x-2 px-4 py-2.5 bg-brand-600 hover:bg-brand-500 disabled:opacity-60 text-white font-bold rounded-xl text-sm"
            >
                <Download size={16} /><span>{busy ? 'Preparing...' : `Download ${kind.toUpperCase()}`}</span>
            </button>
        </div>
    );
};

/** Small "Invoice" download link for lists. */
export const InvoiceButton = ({ path, fallbackName, label = 'Invoice' }: { path: string; fallbackName: string; label?: string }) => {
    const [busy, setBusy] = useState(false);
    return (
        <button
            type="button"
            onClick={async event => {
                event.stopPropagation();
                setBusy(true);
                await downloadFile(path, {}, fallbackName);
                setBusy(false);
            }}
            disabled={busy}
            className="inline-flex items-center space-x-1.5 px-3 py-2 bg-gray-800 hover:bg-gray-700 disabled:opacity-60 text-white font-bold rounded-lg text-xs"
        >
            <Download size={14} /><span>{busy ? '...' : label}</span>
        </button>
    );
};
