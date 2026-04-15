from pathlib import Path
import pandas as pd
import yaml


def main() -> None:
    root = Path('/Users/vedantsunillande/spot-repo/NaviAble/NaviAble/runs/detect')
    out_csv = Path('/Users/vedantsunillande/spot-repo/NaviAble/NaviAble/image_model_metrics_all_runs.csv')
    out_md = Path('/Users/vedantsunillande/spot-repo/NaviAble/NaviAble/image_model_metrics_summary.md')

    rows = []
    for rf in sorted(root.rglob('results.csv')):
        df = pd.read_csv(rf)
        df.columns = [c.strip() for c in df.columns]
        if 'epoch' in df.columns:
            df['epoch'] = pd.to_numeric(df['epoch'], errors='coerce')

        args = {}
        ap = rf.with_name('args.yaml')
        if ap.exists():
            try:
                args = yaml.safe_load(ap.read_text()) or {}
            except Exception:
                args = {}

        def metric(col: str):
            if col in df.columns:
                return pd.to_numeric(df[col], errors='coerce')
            return pd.Series([float('nan')] * len(df))

        p = metric('metrics/precision(B)')
        r = metric('metrics/recall(B)')
        m50 = metric('metrics/mAP50(B)')
        m5095 = metric('metrics/mAP50-95(B)')

        best_idx = int(m5095.idxmax()) if m5095.notna().any() else int(df.index[-1])
        last_idx = int(df.index[-1])

        rows.append(
            {
                'run': str(rf.parent.relative_to(root)),
                'results_csv': str(rf),
                'epochs_recorded': int(len(df)),
                'data': args.get('data'),
                'imgsz': args.get('imgsz'),
                'batch': args.get('batch'),
                'optimizer': args.get('optimizer'),
                'best_epoch_by_mAP50_95': int(df.loc[best_idx, 'epoch'])
                if 'epoch' in df.columns and pd.notna(df.loc[best_idx, 'epoch'])
                else best_idx,
                'best_precision': float(p.loc[best_idx]),
                'best_recall': float(r.loc[best_idx]),
                'best_mAP50': float(m50.loc[best_idx]),
                'best_mAP50_95': float(m5095.loc[best_idx]),
                'last_epoch': int(df.loc[last_idx, 'epoch'])
                if 'epoch' in df.columns and pd.notna(df.loc[last_idx, 'epoch'])
                else last_idx,
                'last_precision': float(p.loc[last_idx]),
                'last_recall': float(r.loc[last_idx]),
                'last_mAP50': float(m50.loc[last_idx]),
                'last_mAP50_95': float(m5095.loc[last_idx]),
            }
        )

    summary = pd.DataFrame(rows).sort_values('best_mAP50_95', ascending=False)
    summary.to_csv(out_csv, index=False)

    top = summary[
        [
            'run',
            'epochs_recorded',
            'data',
            'imgsz',
            'batch',
            'best_epoch_by_mAP50_95',
            'best_precision',
            'best_recall',
            'best_mAP50',
            'best_mAP50_95',
        ]
    ].head(10)

    lines = [
        '# Image Model Metrics Summary (YOLO runs)',
        '',
        f'- Total runs with `results.csv`: {len(summary)}',
        f'- Full table: `{out_csv.name}`',
        '',
        '## Top 10 by best mAP50-95',
        '',
        top.to_markdown(index=False),
    ]
    out_md.write_text('\n'.join(lines))

    print(f'WROTE_CSV={out_csv}')
    print(f'WROTE_MD={out_md}')
    print(f'TOTAL_RUNS={len(summary)}')
    print(f'BEST_RUN={summary.iloc[0]["run"]}')
    print(f'BEST_mAP50_95={summary.iloc[0]["best_mAP50_95"]}')


if __name__ == '__main__':
    main()

