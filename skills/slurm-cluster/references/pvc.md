# Intel PVC / XPU adaptation

PVC on ACES is Intel Data Center GPU Max 1100 (48 GB per physical GPU). Request `--partition=pvc --gres=gpu:pvc:1`; a Slurm request selects hardware, not a compatible runtime. Inspect current resources instead of assuming PVC is always idle. Default to one GPU for environment validation; scale only after a working workload and explicit budget.

## Choose the environment from evidence

Within an authorized allocation, check GPU visibility, PyTorch version, device name, BF16 support, driver and glibc. Use [../assets/pvc-probe.sbatch](../assets/pvc-probe.sbatch) and upload [../scripts/xpu_probe.py](../scripts/xpu_probe.py) to its working directory. It runs a small forward/backward/optimizer step, checks a parameter update and checkpoint roundtrip, and fails if XPU is unavailable. This is a runtime probe, not LLM validation. It still consumes a small allocation and must be within the user's authorization.

Observed 2026-11-01 on one ACES node (revalidate permissions/paths/runtime for each user):

- Documented Torch 2.1/IPEX shared environment failed to detect XPU; exact driver/runtime cause was not established.
- Existing `/scratch/data/uv_envs/max_llama/bin/python` (Torch 2.7.0+xpu) worked with `module purge; module load GCC/13.2.0; module load Python/3.11.5`. Directly invoking its interpreter avoided a stale hard-coded path in `bin/activate`. Without the Python module, inspection encountered missing libffi.so.8. Do not blindly source the shared activation script.
- A single-PVC CIFAR-10 CNN completed training, changed weights, reduced loss and reloaded a checkpoint. This does not validate Transformers/PEFT/bitsandbytes, large-model memory, multi-GPU communication, or LLM quality/throughput.

Prefer a readable compatible existing environment; never pip-install into shared environments. If unavailable, build a user-owned environment or a site-supported container after checking compute-node drivers, glibc and versions. Do not prescribe a CUDA wheel or assume a container fixes an incompatible host driver. The login node's glibc 2.28 does not establish the compute node's ABI. bitsandbytes 0.50.2 XPU wheels require PyTorch >=2.6 and glibc >=2.34; QLoRA needs its own compatibility check.

## Inspect the code before changing it

Search for `.cuda(`, `torch.cuda`, CUDA device strings, `nccl`, `flash_attn`, `bitsandbytes`, `triton`, fused optimizers and custom extensions. Read each usage: do not replace every `cuda` string mechanically.

| Workload | Smallest appropriate change |
|---|---|
| Modern Transformers Trainer | Compatible XPU packages may suffice; confirm `training_args.device` is XPU. |
| Custom PyTorch | Move model/batches to `xpu`; use XPU autocast, synchronize and memory APIs where needed. |
| CUDA-only kernels/optimizers | Select a supported standard PyTorch/SDPA/optimizer implementation or a verified XPU build. |
| Multi-GPU | Use the distributed backend supported by the installed version; modern XPU uses XCCL, older IPEX stacks differ. Validate one process per allocated device. |

Keep CPU portability if the original application needs it, but reject CPU fallback in a requested GPU experiment. Respect scheduler masks; do not hard-code `ZE_AFFINITY_MASK=0` to try to fix visibility. Do not mix old IPEX/oneAPI activation recipes into a native XPU environment without a demonstrated need.

## LLM pilot

1. Choose the user's model/data and a tiny reproducible training subset. Check model license/access and disk capacity before downloads; use existing cached models where possible.
2. Establish a single-XPU BF16 LoRA baseline with supported PyTorch/Transformers/PEFT. Check BF16 support; tune sequence length, microbatch and gradient accumulation to measured memory. LoRA reduces trainable-state memory but does not remove model/activation memory.
3. Prefer standard SDPA initially. Do not claim all FlashAttention is CUDA-only: newer XPU variants exist, but a specific CUDA wheel is not portable. Confirm the implementation and installed versions.
4. Run a few steps: loss finite, adapter weights change, checkpoint reload works, inference works afterward. Record synchronized step/tokens throughput and peak allocated/reserved memory; these exclude some runtime/driver memory.
5. Only then try QLoRA or multiple GPUs if required. Test quantization operators on XPU explicitly. `device_map='auto'` inference sharding is not a replacement for a distributed training strategy. Multiple GPUs do not automatically pool memory.

If a CUDA-only dependency blocks the user's chosen method, report the concrete dependency and smallest alternative. Do not silently change model, precision, training objective or evaluation to declare success. An H100/A30 queue may be the better choice when adaptation costs exceed expected queue savings.

Sources (check installed versions against current docs):
- https://hprc.tamu.edu/kb/User-Guides/ACES/Intel_PVCs/
- https://huggingface.co/docs/transformers/intel_gpu
- https://huggingface.co/docs/bitsandbytes/v0.50.2/installation#intel-xpu
