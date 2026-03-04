import { CheckCircle, XCircle, Info, X } from 'lucide-react';
import clsx from 'clsx';
import { useAppContext } from '../../context/AppContext';
import type { ToastMessage } from '../../types';

const icons: Record<ToastMessage['type'], React.ReactNode> = {
    success: <CheckCircle className="w-5 h-5 text-emerald-400 shrink-0" />,
    error: <XCircle className="w-5 h-5 text-red-400 shrink-0" />,
    info: <Info className="w-5 h-5 text-indigo-400 shrink-0" />,
};

const colors: Record<ToastMessage['type'], string> = {
    success: 'border-emerald-500/40 bg-emerald-950/80',
    error: 'border-red-500/40 bg-red-950/80',
    info: 'border-indigo-500/40 bg-indigo-950/80',
};

function Toast({ toast }: { toast: ToastMessage }) {
    const { removeToast } = useAppContext();
    return (
        <div
            className={clsx(
                'toast-enter flex items-start gap-3 rounded-xl border px-4 py-3 shadow-2xl backdrop-blur-xl max-w-sm w-full',
                colors[toast.type]
            )}
        >
            {icons[toast.type]}
            <p className="text-sm text-slate-200 flex-1 leading-snug">{toast.message}</p>
            <button
                onClick={() => removeToast(toast.id)}
                className="text-slate-500 hover:text-slate-300 transition-colors shrink-0"
            >
                <X className="w-4 h-4" />
            </button>
        </div>
    );
}

export function ToastContainer() {
    const { toasts } = useAppContext();
    return (
        <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-3 items-end pointer-events-none">
            {toasts.map((t) => (
                <div key={t.id} className="pointer-events-auto">
                    <Toast toast={t} />
                </div>
            ))}
        </div>
    );
}
