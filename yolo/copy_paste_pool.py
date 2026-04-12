"""Copy-paste augmentation using a pooled set of ramp patches with extra transforms.

This script collects ramp patches (class id 2) from one or more source folders
and pastes them onto background images selected from one or more background
folders. It applies random transforms to each pasted patch to increase visual
diversity (scaling, rotation, brightness/contrast/color jitter).

Usage example:
 python yolo/copy_paste_pool.py \
   --patch-dirs NaviAble_Dataset/train_aug_cp2/labels:NaviAble_Dataset/train_aug_cp/labels \
   --img-dirs NaviAble_Dataset/train_aug_cp2/images:NaviAble_Dataset/train/images \
   --out NaviAble_Dataset/train_aug_cp3 --num 1200
"""
import os
import glob
import random
import argparse
from PIL import Image, ImageEnhance, ImageFilter
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
    x1 = int(max(0, x_c - bw/2))
    y1 = int(max(0, y_c - bh/2))
    x2 = int(min(w, x_c + bw/2))
    y2 = int(min(h, y_c + bh/2))
    return cid, x1, y1, x2, y2


def xywh_pix_to_yolo(x1, y1, x2, y2, w, h):
    bw = x2 - x1
    bh = y2 - y1
    if bw <= 0 or bh <= 0:
        return None
    xc = x1 + bw/2
    yc = y1 + bh/2
    return xc / w, yc / h, bw / w, bh / h


def collect_patches(patch_dirs, max_patches=None, pad=0.1):
    patches = []  # list of (PIL.Image RGBA, (w,h))
    for d in patch_dirs:
        lbls = glob.glob(os.path.join(d, '*.txt'))
        img_dir = os.path.dirname(d).replace('/labels', '/images') if d.endswith('/labels') else None
        for lf in lbls:
            base = os.path.splitext(os.path.basename(lf))[0]
            # try common image extensions
            img_path = None
            if img_dir:
                for ext in ('.jpg', '.jpeg', '.png'):
                    p = os.path.join(img_dir, base + ext)
                    if os.path.exists(p):
                        img_path = p
                        break
            if img_path is None:
                # fallback: search near the label dir
                for ext in ('.jpg', '.jpeg', '.png'):
                    p = os.path.join(os.path.dirname(lf).replace('/labels','/images'), base + ext)
                    if os.path.exists(p):
                        img_path = p
                        break
            if img_path is None:
                continue
            try:
                img = Image.open(img_path).convert('RGBA')
            except Exception:
                continue
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


def apply_transforms(patch, scale, rotate_deg, bright, contrast, color, blur):
    # patch is RGBA
    w, h = patch.size
    new_w = max(8, int(w * scale))
    new_h = max(8, int(h * scale))
    p = patch.resize((new_w, new_h), resample=Image.BICUBIC)
    if rotate_deg:
        p = p.rotate(rotate_deg, expand=True)
    # color transforms (convert to RGB for enhancers)
    rgb = p.convert('RGBA')
    # split alpha to keep it
    alpha = rgb.split()[-1]
    rgb = rgb.convert('RGB')
    if bright != 1.0:
        rgb = ImageEnhance.Brightness(rgb).enhance(bright)
    if contrast != 1.0:
        rgb = ImageEnhance.Contrast(rgb).enhance(contrast)
    if color != 1.0:
        rgb = ImageEnhance.Color(rgb).enhance(color)
    if blur > 0:
        rgb = rgb.filter(ImageFilter.GaussianBlur(radius=blur))
    rgba = Image.new('RGBA', rgb.size)
    rgba.paste(rgb, (0,0))
    rgba.putalpha(alpha.resize(rgb.size))
    return rgba


def run_pool_copy_paste(patch_dirs, bg_dirs, out_dir, num_new=1000, max_patches=1000, pad=0.12,
                       scale_min=0.5, scale_max=1.4, rotate_max=15, bright_range=(0.8,1.2),
                       contrast_range=(0.9,1.1), color_range=(0.9,1.1), blur_max=1.0):
    out_images = os.path.join(out_dir, 'images')
    out_labels = os.path.join(out_dir, 'labels')
    os.makedirs(out_images, exist_ok=True)
    os.makedirs(out_labels, exist_ok=True)

    print('Collecting ramp patches from patch dirs...')
    patches = collect_patches(patch_dirs, max_patches=max_patches, pad=pad)
    if not patches:
        print('No ramp patches found in provided patch directories')
        return
    print(f'Collected {len(patches)} patches')

    # build background pool
    bg_images = []
    for d in bg_dirs:
        for ext in ('.jpg', '.jpeg', '.png'):
            bg_images += glob.glob(os.path.join(d, f'*{ext}'))
    if not bg_images:
        print('No background images found in bg_dirs')
        return

    random.seed(0)
    cnt = 0
    while cnt < num_new:
        patch_img, (pw, ph) = random.choice(patches)
        scale = random.uniform(scale_min, scale_max)
        rotate = random.uniform(-rotate_max, rotate_max) if rotate_max else 0
        bright = random.uniform(*bright_range)
        contrast = random.uniform(*contrast_range)
        color = random.uniform(*color_range)
        blur = random.uniform(0, blur_max)
        patch_t = apply_transforms(patch_img, scale, rotate, bright, contrast, color, blur)

        bg_path = random.choice(bg_images)
        try:
            bg = Image.open(bg_path).convert('RGBA')
        except Exception:
            continue
        bw, bh = bg.size
        pw2, ph2 = patch_t.size
        if pw2 >= bw or ph2 >= bh:
            # scale down to fit
            scale_fit = min((bw-10)/pw2, (bh-10)/ph2)
            if scale_fit <= 0:
                continue
            new_w = max(8, int(pw2 * scale_fit))
            new_h = max(8, int(ph2 * scale_fit))
            patch_t = patch_t.resize((new_w, new_h), resample=Image.BICUBIC)
            pw2, ph2 = patch_t.size

        max_x = bw - pw2
        max_y = bh - ph2
        if max_x <= 0 or max_y <= 0:
            continue
        x = random.randint(0, max_x)
        y = random.randint(0, max_y)

        composite = bg.copy()
        composite.paste(patch_t, (x, y), patch_t)

        base = f'cp_pool_{cnt:05d}_{os.path.basename(bg_path)}'
        out_img = os.path.join(out_images, base)
        if not out_img.lower().endswith('.jpg'):
            out_img = os.path.splitext(out_img)[0] + '.jpg'
        composite.convert('RGB').save(out_img, quality=95)

        # prepare label: include existing bg labels if present
        lbl_base = os.path.splitext(os.path.basename(bg_path))[0]
        bg_lbl = None
        for ext in ('.txt',):
            candidate = os.path.join(os.path.dirname(bg_path).replace('/images','/labels'), lbl_base + ext)
            if os.path.exists(candidate):
                bg_lbl = candidate
                break
        out_lbl_path = os.path.join(out_labels, os.path.splitext(os.path.basename(out_img))[0] + '.txt')
        with open(out_lbl_path, 'w') as fw:
            if bg_lbl and os.path.exists(bg_lbl):
                try:
                    fw.write(open(bg_lbl).read())
                except Exception:
                    pass
            # write pasted ramp bbox as class 2
            yolo_box = xywh_pix_to_yolo(x, y, x + pw2, y + ph2, bw, bh)
            if yolo_box:
                xc, yc, nw, nh = yolo_box
                fw.write(f"2 {xc:.6f} {yc:.6f} {nw:.6f} {nh:.6f}\n")

        cnt += 1
        if cnt % 100 == 0:
            print(f'Created {cnt}/{num_new}')

    print(f'Created {cnt} images in {out_images}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--patch-dirs', required=True, help='colon-separated list of label dirs to collect patches from')
    parser.add_argument('--img-dirs', required=True, help='colon-separated list of image dirs to use as backgrounds')
    parser.add_argument('--out', default='train_aug_cp3')
    parser.add_argument('--num', type=int, default=1000)
    parser.add_argument('--max-patches', type=int, default=1000)
    parser.add_argument('--pad', type=float, default=0.12)
    parser.add_argument('--scale-min', type=float, default=0.5)
    parser.add_argument('--scale-max', type=float, default=1.4)
    parser.add_argument('--rotate-max', type=float, default=15)
    parser.add_argument('--bright-min', type=float, default=0.8)
    parser.add_argument('--bright-max', type=float, default=1.2)
    parser.add_argument('--contrast-min', type=float, default=0.9)
    parser.add_argument('--contrast-max', type=float, default=1.1)
    parser.add_argument('--color-min', type=float, default=0.9)
    parser.add_argument('--color-max', type=float, default=1.1)
    parser.add_argument('--blur-max', type=float, default=1.0)
    args = parser.parse_args()

    patch_dirs = [p for p in args.patch_dirs.split(':') if p]
    img_dirs = [p for p in args.img_dirs.split(':') if p]
    run_pool_copy_paste(patch_dirs, img_dirs, args.out, num_new=args.num, max_patches=args.max_patches,
                       pad=args.pad, scale_min=args.scale_min, scale_max=args.scale_max,
                       rotate_max=args.rotate_max, bright_range=(args.bright_min, args.bright_max),
                       contrast_range=(args.contrast_min, args.contrast_max), color_range=(args.color_min, args.color_max),
                       blur_max=args.blur_max)


if __name__ == '__main__':
    main()

