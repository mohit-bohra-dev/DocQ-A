import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, FileText, AlertTriangle, CheckCircle2, X } from 'lucide-react';
import clsx from 'clsx';
import { apiClient } from '../../services/api';
import { useAppContext } from '../../context/AppContext';
import { useQueryClient } from '@tanstack/react-query';
import { Spinner } from '../ui/Spinner';

const MAX_SIZE_MB = 50;
const MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024;

function formatBytes(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

type UploadStage = 'idle' | 'ready' | 'duplicate' | 'uploading' | 'done' | 'error';

export function UploadZone() {
    const { addToast } = useAppContext();
    const queryClient = useQueryClient();
    const [file, setFile] = useState<File | null>(null);
    const [stage, setStage] = useState<UploadStage>('idle');
    const [progress, setProgress] = useState(0);
    const [errorMsg, setErrorMsg] = useState('');
    const [replaceChecked, setReplaceChecked] = useState(false);

    const existingDocs: string[] = (queryClient.getQueryData(['documents']) as any[] ?? []).map((d: any) => d.document_name);

    const onDrop = useCallback(
        (accepted: File[]) => {
            if (!accepted.length) return;
            const f = accepted[0];
            setFile(f);
            setErrorMsg('');
            setProgress(0);
            setReplaceChecked(false);
            const isDuplicate = existingDocs.includes(f.name);
            setStage(isDuplicate ? 'duplicate' : 'ready');
        },
        [existingDocs]
    );

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept: { 'application/pdf': ['.pdf'] },
        maxFiles: 1,
        maxSize: MAX_SIZE_BYTES,
        onDropRejected: (rejections) => {
            const msg = rejections[0]?.errors[0]?.message ?? 'Invalid file.';
            setErrorMsg(msg);
            setStage('error');
        },
    });

    async function handleUpload() {
        if (!file) return;
        setStage('uploading');
        setProgress(0);

        const result = await apiClient.uploadDocument(file, replaceChecked, setProgress);

        if (result.success) {
            setStage('done');
            addToast('success', replaceChecked ? 'Document replaced successfully!' : 'Document uploaded and processed!');
            queryClient.invalidateQueries({ queryKey: ['documents'] });
            queryClient.invalidateQueries({ queryKey: ['health'] });
            setTimeout(() => { setFile(null); setStage('idle'); }, 2500);
        } else if (result.duplicate) {
            setStage('duplicate');
            addToast('info', 'Document already exists. Enable "Replace" to overwrite.');
        } else {
            setStage('error');
            setErrorMsg(result.error ?? 'Upload failed.');
            addToast('error', result.error ?? 'Upload failed.');
        }
    }

    function reset() {
        setFile(null);
        setStage('idle');
        setErrorMsg('');
        setProgress(0);
        setReplaceChecked(false);
    }

    return (
        <div className="space-y-3">
            {/* Dropzone */}
            {(stage === 'idle' || stage === 'error') && (
                <div
                    {...getRootProps()}
                    className={clsx(
                        'border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all duration-200',
                        isDragActive
                            ? 'border-indigo-500 bg-indigo-500/10 scale-[1.01]'
                            : 'border-white/10 hover:border-indigo-500/50 hover:bg-white/[0.02]'
                    )}
                >
                    <input {...getInputProps()} />
                    <div className="flex flex-col items-center gap-3">
                        <div className={clsx(
                            'w-14 h-14 rounded-2xl flex items-center justify-center transition-colors',
                            isDragActive ? 'bg-indigo-500/20' : 'bg-white/5'
                        )}>
                            <Upload className={clsx('w-7 h-7 transition-colors', isDragActive ? 'text-indigo-400' : 'text-slate-500')} />
                        </div>
                        <div>
                            <p className="text-sm font-medium text-slate-300">
                                {isDragActive ? 'Drop it here!' : 'Drag & drop a PDF'}
                            </p>
                            <p className="text-xs text-slate-600 mt-1">or click to browse · max {MAX_SIZE_MB}MB</p>
                        </div>
                    </div>
                    {stage === 'error' && errorMsg && (
                        <div className="mt-3 flex items-center gap-2 justify-center text-red-400 text-xs">
                            <AlertTriangle className="w-4 h-4" />
                            {errorMsg}
                        </div>
                    )}
                </div>
            )}

            {/* File ready / duplicate */}
            {(stage === 'ready' || stage === 'duplicate') && file && (
                <div className="glass-card p-4 space-y-3">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-indigo-500/15 flex items-center justify-center shrink-0">
                            <FileText className="w-5 h-5 text-indigo-400" />
                        </div>
                        <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-slate-200 truncate">{file.name}</p>
                            <p className="text-xs text-slate-500">{formatBytes(file.size)}</p>
                        </div>
                        <button onClick={reset} className="btn-ghost p-1.5 rounded-lg">
                            <X className="w-4 h-4" />
                        </button>
                    </div>

                    {stage === 'duplicate' && (
                        <div className="flex items-start gap-2 p-3 rounded-lg bg-amber-950/50 border border-amber-500/30">
                            <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                            <div className="flex-1">
                                <p className="text-xs font-medium text-amber-400">Document already exists</p>
                                <label className="flex items-center gap-2 mt-1.5 cursor-pointer">
                                    <input
                                        type="checkbox"
                                        className="accent-indigo-500 w-3.5 h-3.5"
                                        checked={replaceChecked}
                                        onChange={(e) => setReplaceChecked(e.target.checked)}
                                    />
                                    <span className="text-xs text-amber-300">Replace existing document</span>
                                </label>
                            </div>
                        </div>
                    )}

                    <button
                        onClick={handleUpload}
                        disabled={stage === 'duplicate' && !replaceChecked}
                        className="btn-accent w-full py-2.5"
                    >
                        {stage === 'duplicate' && replaceChecked ? 'Replace & Process' : 'Upload & Process'}
                    </button>
                </div>
            )}

            {/* Uploading */}
            {stage === 'uploading' && (
                <div className="glass-card p-4 space-y-3">
                    <div className="flex items-center gap-3">
                        <Spinner size="sm" />
                        <p className="text-sm text-slate-300">Processing document…</p>
                        <span className="ml-auto text-xs text-indigo-400 font-medium">{progress}%</span>
                    </div>
                    <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
                        <div
                            className="h-full bg-gradient-to-r from-indigo-500 to-violet-500 rounded-full transition-all duration-300"
                            style={{ width: `${Math.max(progress, 5)}%` }}
                        />
                    </div>
                </div>
            )}

            {/* Done */}
            {stage === 'done' && (
                <div className="glass-card p-4 flex items-center gap-3 fade-in-up border-emerald-500/30">
                    <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
                    <p className="text-sm text-emerald-400 font-medium">Upload complete!</p>
                </div>
            )}
        </div>
    );
}
