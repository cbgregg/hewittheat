"""Makes a tangent-space normal map (tex/b/<name>_n.jpg) for every building texture in tex/b, from the
picture's own light and dark: mortar lines, panel joints and window frames become relief."""
import glob, os, numpy as np
from PIL import Image, ImageFilter
for f in sorted(glob.glob(os.path.dirname(os.path.abspath(__file__)) + '/../tex/b/*.jpg')):
    if f.endswith('_n.jpg'):
        continue
    im = Image.open(f).convert('L').resize((512, 512), Image.LANCZOS)
    h = np.asarray(im.filter(ImageFilter.GaussianBlur(0.8)), np.float32) / 255.0
    h2 = np.asarray(im.filter(ImageFilter.GaussianBlur(3.0)), np.float32) / 255.0
    h = h * 0.6 + h2 * 0.8                      # fine grain plus broader forms (frames, sills)
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.5
    k = 9.0
    n = np.dstack([-dx * k, dy * k, np.ones_like(h)])
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    Image.fromarray(((n * 0.5 + 0.5) * 255).astype(np.uint8)).save(f[:-4] + '_n.jpg', quality=88)
print('normal maps', len(glob.glob(os.path.dirname(os.path.abspath(__file__)) + '/../tex/b/*_n.jpg')))
