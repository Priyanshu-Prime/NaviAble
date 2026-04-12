"""Auto-relabel candidate ramp files to class id 2 (ramp).

This script is a safe automatic relabeler that:
 - Finds label files whose image base name contains 'ramp' (case-insensitive)
 - Backs them up under labels_backup_ramp_TIMESTAMP/
 - Rewrites those label files so every label line's class id becomes 2
 - Prints a summary and updated per-class counts across train/train_aug/valid

WARNING: this is an automatic heuristic. It changes ALL label lines in matched
files to class id 2. Backups are created; you can restore from the backup
directory if needed.

Defaults are chosen to match the project's layout. You can override paths via
CLI args.
"""
import argparse
import os
import shutil
import glob
import time
import collections


def find_candidate_label_files(labels_dirs, pattern='ramp'):
    pattern = pattern.lower()
    found = []
    for d in labels_dirs:
        if not os.path.isdir(d):
            continue
        for p in glob.glob(os.path.join(d, '*.txt')):
            base = os.path.splitext(os.path.basename(p))[0]
            if pattern in base.lower():
                found.append(p)
    return sorted(found)


def backup_files(files, backup_root):
    os.makedirs(backup_root, exist_ok=True)
    for f in files:
        dst = os.path.join(backup_root, os.path.basename(f))
        shutil.copy2(f, dst)


def relabel_files_to_class(files, new_class_id=2):
    changed = 0
    lines_changed = 0
    for f in files:
        with open(f, 'r') as fr:
            lines = fr.readlines()
        out_lines = []
        modified = False
        for ln in lines:
            s = ln.strip()
            if not s:
                continue
            parts = s.split()
            # Replace first token with new class id
            old = parts[0]
            if old != str(new_class_id):
                parts[0] = str(new_class_id)
                modified = True
                lines_changed += 1
            out_lines.append(' '.join(parts) + '\n')
        if modified:
            with open(f, 'w') as fw:
                fw.writelines(out_lines)
            changed += 1
    return changed, lines_changed


def count_classes(label_dirs, nc=None):
    counts = collections.Counter()
    for d in label_dirs:
        if not os.path.isdir(d):
            continue
        for p in glob.glob(os.path.join(d, '*.txt')):
            for ln in open(p):
                parts = ln.strip().split()
                if not parts:
                    continue
                try:
                    cid = int(parts[0])
                except Exception:
                    continue
                counts[cid] += 1
    return counts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset-root', default='/Users/vedantsunillande/spot-repo/NaviAble/NaviAble/NaviAble_Dataset', help='absolute path to dataset root')
    parser.add_argument('--pattern', default='ramp', help='case-insensitive substring to match in image base names')
    parser.add_argument('--new-class', type=int, default=2, help='target class id to set')
    parser.add_argument('--process', action='store_true', help='actually perform relabeling (default: dry-run)')
    args = parser.parse_args()

    ds = args.dataset_root
    # candidate label dirs to search and to show counts for
    label_dirs = [os.path.join(ds, 'train', 'labels'), os.path.join(ds, 'train_aug', 'labels'), os.path.join(ds, 'valid', 'labels'), os.path.join(ds, 'test', 'labels')]

    print('Dataset root:', ds)
    print('Searching for candidate label files containing "{}" in base name...'.format(args.pattern))
    candidates = find_candidate_label_files(label_dirs, pattern=args.pattern)
    print(f'Found {len(candidates)} candidate label files (showing up to 20):')
    for p in candidates[:20]:
        print('  ', p)
    if not candidates:
        print('No candidates found. Exiting.')
        return

    # show before counts
    before = count_classes([os.path.join(ds, 'train', 'labels'), os.path.join(ds, 'train_aug', 'labels'), os.path.join(ds, 'valid', 'labels')])
    print('Counts before (train/train_aug/valid):', dict(before))

    if not args.process:
        print('\nDry-run mode (no changes). To apply relabeling re-run with --process')
        return

    ts = time.strftime('%Y%m%d_%H%M%S')
    backup_dir = os.path.join(ds, f'labels_backup_ramp_{ts}')
    print('Creating backup directory:', backup_dir)
    backup_files(candidates, backup_dir)
    print(f'Backed up {len(candidates)} files into {backup_dir}')

    print('Relabeling candidate files to class', args.new_class)
    files_changed, lines_changed = relabel_files_to_class(candidates, new_class_id=args.new_class)
    print(f'Files modified: {files_changed}; label lines changed: {lines_changed}')

    after = count_classes([os.path.join(ds, 'train', 'labels'), os.path.join(ds, 'train_aug', 'labels'), os.path.join(ds, 'valid', 'labels')])
    print('Counts after (train/train_aug/valid):', dict(after))
    print('\nDone. If something looks wrong you can restore original label files from:', backup_dir)


if __name__ == '__main__':
    main()

