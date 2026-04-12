"""Copy-paste augmentation for ramp class (class id 2).

This script:
 - Scans a labels directory for ramp boxes (class 2)
 - Crops ramp patches from those images
 - Pastes patches onto randomly selected background images (that may or may not contain other objects)
 - Writes new images and corresponding YOLO-format label files with the pasted ramp bbox

Usage:
 python yolo/copy_paste_augment.py --dataset-root /absolute/path/to/NaviAble_Dataset --out train_aug_cp --num 300
"""
import os
import glob
import random
import argparse
from PIL import Image
import shutil


def yolo_to_xywh_pix(line, w, h):
    parts = line.strip().split()
    if not parts:
        return None
    cid = int(parts[0])
    x_c = float(parts[1]) * w
    y_c = float(parts[2]) * h
    bw = float(parts[3]) * w
    bh = float(parts[4]) * h
    x1 = int(x_c - bw/2)
    y1 = int(y_c - bh/2)
    x2 = int(x_c + bw/2)
    y2 = int(y_c + bh/2)
    return cid, x1, y1, x2, y2


def xywh_pix_to_yolo(x1, y1, x2, y2, w, h):
    bw = x2 - x1
    bh = y2 - y1
    xc = x1 + bw/2
    yc = y1 + bh/2
    return xc / w, yc / h, bw / w, bh / h


def collect_ramp_patches(train_images_dir, train_labels_dir, max_patches=None, pad=0.1):
    patches = []  # tuples (patch_image, original_w, original_h)
    label_files = glob.glob(os.path.join(train_labels_dir, '*.txt'))
    for lf in label_files:
        img_base = os.path.splitext(os.path.basename(lf))[0]
        img_path = None
        for ext in ('.jpg', '.jpeg', '.png'):
            p = os.path.join(train_images_dir, img_base + ext)
            if os.path.exists(p):
                img_path = p
                break
        if img_path is None:
            continue
        img = Image.open(img_path).convert('RGBA')
        w, h = img.size
        for ln in open(lf):
            parts = ln.strip().split()
            if not parts:
                continue
            try:
                cid = int(parts[0])
            except Exception:
                continue
            if cid != 2:
                continue
            res = yolo_to_xywh_pix(ln, w, h)
            if res is None:
                continue
            _, x1, y1, x2, y2 = res
            # add padding
            pw = int((x2 - x1) * pad)
            ph = int((y2 - y1) * pad)
            xa = max(0, x1 - pw)
            ya = max(0, y1 - ph)
            xb = min(w, x2 + pw)
            yb = min(h, y2 + ph)
            try:
                patch = img.crop((xa, ya, xb, yb)).copy()
                patches.append((patch, (xb-xa, yb-ya)))
            except Exception:
                continue
            if max_patches and len(patches) >= max_patches:
                return patches
    return patches


def run_copy_paste(dataset_root, out_dir_name='train_aug_cp', num_new=300, max_patches=100):
    train_images = os.path.join(dataset_root, 'train', 'images')
    train_labels = os.path.join(dataset_root, 'train', 'labels')
    out_images = os.path.join(dataset_root, out_dir_name, 'images')
    out_labels = os.path.join(dataset_root, out_dir_name, 'labels')
    os.makedirs(out_images, exist_ok=True)
    os.makedirs(out_labels, exist_ok=True)

    # Copy originals into out if not already
    for src_dir, dst_dir in [(train_images, out_images), (train_labels, out_labels)]:
        for f in glob.glob(os.path.join(src_dir, '*')):
            dst = os.path.join(dst_dir, os.path.basename(f))
            if not os.path.exists(dst):
                try:
                    shutil.copy2(f, dst)
                except Exception:
                    pass

    print('Collecting ramp patches...')
    patches = collect_ramp_patches(train_images, train_labels, max_patches=max_patches, pad=0.15)
    if not patches:
        print('No ramp patches found. Make sure class id 2 exists in train labels.')
        return
    print(f'Collected {len(patches)} ramp patches. Creating {num_new} synthetic images...')

    # background pool: use train images (could exclude images that already have ramps)
    bg_images = glob.glob(os.path.join(train_images, '*.jpg')) + glob.glob(os.path.join(train_images, '*.png'))
    if not bg_images:
        print('No background images found')
        return

    cnt = 0
    random.seed(0)
    while cnt < num_new:
        patch, (pw, ph) = random.choice(patches)
        bg_path = random.choice(bg_images)
        bg = Image.open(bg_path).convert('RGBA')
        bw, bh = bg.size
        # scale patch randomly between 0.5x and 1.5x
        scale = random.uniform(0.6, 1.2)
        new_w = max(10, int(pw * scale))
        new_h = max(10, int(ph * scale))
        patch_resized = patch.resize((new_w, new_h), resample=Image.BICUBIC)

        # choose random position where patch fully fits
        max_x = bw - new_w
        max_y = bh - new_h
        if max_x <= 0 or max_y <= 0:
            continue
        x = random.randint(0, max_x)
        y = random.randint(0, max_y)

        composite = bg.copy()
        composite.paste(patch_resized, (x, y), patch_resized)
        # convert to RGB and save
        out_basename = f'cp_aug_{cnt:04d}_{os.path.basename(bg_path)}'
        out_img_path = os.path.join(out_images, out_basename)
        # ensure .jpg extension
        if not out_img_path.lower().endswith('.jpg'):
            out_img_path = os.path.splitext(out_img_path)[0] + '.jpg'
        composite.convert('RGB').save(out_img_path, quality=95)

        # compute normalized bbox for pasted patch
        x1 = x
        y1 = y
        x2 = x + new_w
        y2 = y + new_h
        xc, yc, nw, nh = xywh_pix_to_yolo(x1, y1, x2, y2, bw, bh)
        # write label file with class 2 only
        base = os.path.splitext(os.path.basename(out_img_path))[0]
        out_lbl_path = os.path.join(out_labels, base + '.txt')
        with open(out_lbl_path, 'w') as fw:
            fw.write(f"2 {xc:.6f} {yc:.6f} {nw:.6f} {nh:.6f}\n")

        cnt += 1
        if cnt % 50 == 0:
            print(f'Created {cnt}/{num_new}')

    print(f'Copy-paste augmentation complete. Created {cnt} images in {out_images}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset-root', required=True)
    parser.add_argument('--out', default='train_aug_cp')
    parser.add_argument('--num', type=int, default=300)
    parser.add_argument('--max-patches', type=int, default=100)
    args = parser.parse_args()
    run_copy_paste(args.dataset_root, out_dir_name=args.out, num_new=args.num, max_patches=args.max_patches)


if __name__ == '__main__':
    main()

