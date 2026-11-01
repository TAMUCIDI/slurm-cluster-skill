#!/usr/bin/env python3
"""Run only inside an allocated XPU job using its intended Python environment."""
import io
import json
import os
import platform

import torch


def main():
    if not os.environ.get('SLURM_JOB_ID'):
        raise RuntimeError('Run this probe in a Slurm allocation')
    if not hasattr(torch, 'xpu') or not torch.xpu.is_available():
        raise RuntimeError('XPU unavailable; refusing CPU fallback')
    torch.manual_seed(42)
    model = torch.nn.Linear(8, 1).to('xpu')
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.01)
    inputs = torch.randn(16, 8, device='xpu')
    before = model.weight.detach().clone()
    loss = model(inputs).square().mean()
    loss.backward()
    optimizer.step()
    torch.xpu.synchronize()
    if not torch.isfinite(loss).item() or torch.equal(before, model.weight):
        raise RuntimeError('Nonfinite loss or no weight update')
    checkpoint = io.BytesIO()
    torch.save(model.state_dict(), checkpoint)
    checkpoint.seek(0)
    restored = torch.nn.Linear(8, 1).to('xpu')
    restored.load_state_dict(torch.load(checkpoint, map_location='xpu', weights_only=True))
    with torch.no_grad():
        torch.testing.assert_close(model(inputs), restored(inputs))
    print(json.dumps({
        'job_id': os.environ['SLURM_JOB_ID'], 'torch': torch.__version__,
        'libc': platform.libc_ver(), 'device': torch.xpu.get_device_name(0),
        'device_count': torch.xpu.device_count(), 'bf16': torch.xpu.is_bf16_supported(),
        'loss': loss.item(), 'weight_update': True, 'checkpoint_reload': True,
        'peak_allocated_bytes': torch.xpu.max_memory_allocated(),
        'peak_reserved_bytes': torch.xpu.max_memory_reserved(),
    }, indent=2))


if __name__ == '__main__':
    main()
