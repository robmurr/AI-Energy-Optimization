import os, time, glob, argparse, torch
from PIL import Image
from transformers import AutoImageProcessor, ResNetForImageClassification

MODEL_ID = "microsoft/resnet-50"

def load_model(device):
    proc = AutoImageProcessor.from_pretrained(MODEL_ID)
    model = ResNetForImageClassification.from_pretrained(MODEL_ID).to(device).eval()
    print("Loaded:", model.config._name_or_path)
    return proc, model

def load_images(img_dir, limit=None):
    paths = sorted(glob.glob(os.path.join(img_dir, "*.jpg")))
    if limit:
        paths = paths[:limit]
    imgs = [Image.open(p).convert("RGB") for p in paths]
    return paths, imgs

@torch.inference_mode()
def run_batch(proc, model, images, device):
    inputs = proc(images=images, return_tensors="pt")
    inputs = {k: v.to(device) for k, v in inputs.items()}
    logits = model(**inputs).logits
    probs = torch.softmax(logits, dim=-1)
    vals, idxs = torch.topk(probs, k=5, dim=-1)
    return vals.cpu(), idxs.cpu()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--limit", type=int, default=100)
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--warmup", type=int, default=1)
    args = ap.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print("Device:", device)
    proc, model = load_model(device)

    paths, imgs = load_images(args.dir, args.limit)
    if not imgs:
        raise SystemExit(f"No .jpg in {args.dir}")
    batches = [imgs[i:i + args.batch] for i in range(0, len(imgs), args.batch)]

    # warmup
    for _ in range(args.warmup):
        for b in batches:
            run_batch(proc, model, b, device)
        if device == "cuda":
            torch.cuda.synchronize()

    # timed runs
    t0 = time.time()
    for _ in range(args.runs):
        for b in batches:
            run_batch(proc, model, b, device)
        if device == "cuda":
            torch.cuda.synchronize()
    t1 = time.time()

    n = len(imgs) * args.runs
    dt = t1 - t0
    print(f"Images: {len(imgs)} | Batch: {args.batch} | Runs: {args.runs}")
    print(f"Total: {dt:.3f}s | imgs/s: {n/dt:.2f} | ms/img: {1000*dt/n:.2f}")

    # show top-5 for first image
    vals, idxs = run_batch(proc, model, batches[0], device)
    id2label = model.config.id2label
    print("\nTop-5 for first image:")
    for i, p in zip(idxs[0].tolist(), vals[0].tolist()):
        print(f"  {id2label[i]}: {float(p):.4f}")

if __name__ == "__main__":
    main()
