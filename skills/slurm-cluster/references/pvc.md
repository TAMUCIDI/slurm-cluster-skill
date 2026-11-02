# Intel PVC / XPU adaptation

PVC on ACES is Intel Data Center GPU Max 1100 (48 GB per physical GPU). Request `--partition=pvc --gres=gpu:pvc:1`; a Slurm request selects hardware, not a compatible runtime. Inspect current resources instead of assuming PVC is always idle. Default to one GPU for environment validation; scale only after a working workload and explicit budget.

## Choose the environment from evidence

Within an authorized allocation, check GPU visibility, PyTorch version, device name, BF16 support, driver and glibc. Use [../assets/pvc-probe.sbatch](../assets/pvc-probe.sbatch) and upload [../scripts/xpu_probe.py](../scripts/xpu_probe.py) to its working directory. It runs a small forward/backward/optimizer step, checks a parameter update and checkpoint roundtrip, and fails if XPU is unavailable. This is a runtime probe, not LLM validation. It still consumes a small allocation and must be within the user's authorization.

Observed 2026-11-01 on one ACES node (revalidate permissions/paths/runtime for each user):

- Documented Torch 2.1/IPEX shared environment failed to detect XPU; exact driver/runtime cause was not established.
- Existing `/scratch/data/uv_envs/max_llama/bin/python` (Torch 2.7.0+xpu) worked with `module purge; module load GCC/13.2.0; module load Python/3.11.5`. Directly invoking its interpreter avoided a stale hard-coded path in `bin/activate`. Without the Python module, inspection encountered missing libffi.so.8. Do not blindly source the shared activation script.
- A single-PVC CIFAR-10 CNN completed training, changed weights, reduced loss and reloaded a checkpoint. This does not validate Transformers/PEFT/bitsandbytes, large-model memory, multi-GPU communication, or LLM quality/throughput.
- A separate single-PVC pilot ran cached CodeLlama-7b-Python-hf with BF16/SDPA, Transformers 4.51.3 and PEFT 0.15.2. It generated code, updated rank-8 q_proj/v_proj LoRA adapters for six 128-token, batch-one steps, saved/reloaded matching adapter weights, and generated afterward. A temporary authenticated API was called from a local machine through SSH. These checks establish this workload's execution, not model-quality improvement, vLLM, quantization, long-context or concurrent serving compatibility.
- A later Qwen2.5-1.5B-Instruct BF16/SDPA pilot served real OpenAI SDK chat calls and an lm-eval generation backend on one PVC. Read [benchmark integration](benchmarks.md) for the tested scope and structured-output failure; this did not run a scored GIS benchmark.

The shared XPU venv may have no pip. If a needed pure-Python dependency is absent, inspect its requirements against the installed stack, then use a compatible module Python's pip to install a pinned version into a user-owned `--target` directory and add that directory to `PYTHONPATH`. Use `--no-deps` only after checking those requirements; never upgrade the shared stack to satisfy an incidental import. This was sufficient for the pilot's PEFT overlay.

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

1. Match the user's requested operation: inference, fine-tuning, or local API access. Check model license/access and disk capacity before downloads; prefer readable cached weights. Record whether weights came from a shared cache, a direct cluster download or a local upload, and pin the model revision. A gated Hub response may require the user's access/license setup; it is not proof that PVC cannot run that architecture. Do not accept terms or substitute a named model silently. Confirm whether the model is a base/code-completion or instruction/chat model before choosing prompts or an endpoint. A code-completion check is not a chat-quality evaluation.
2. Establish single-XPU BF16 inference first when it is relevant. Check BF16 support and ensure model parameters actually reside on XPU without CPU offload. For a fully cached model, `local_files_only=True` avoids accidental Hub access. Prefer standard SDPA initially. Newer FlashAttention XPU variants exist, but a CUDA wheel is not portable.
3. Separate imports/model-loading time, cold generation, and warmed generation. Repeat comparable prompt/output lengths with XPU synchronization. An eight-token warmup did not eliminate a much slower first 64-token generation in the pilot; later equal-length repetitions agreed closely. Do not average cold compilation into steady throughput or label total `generate()` time as time-to-first-token/decode-only speed. Record actual prompt/output token counts, precision, backend, and allocated/reserved memory; allocator counters exclude some driver/runtime memory.
4. For fine-tuning, use a tiny reproducible subset and supported Transformers/PEFT. Start with ordinary LoRA; tune sequence length, microbatch and gradient accumulation to measured memory. Verify finite loss, changed adapter weights, saved/reloaded adapter equality and post-reload inference. Tiny repeated-sample loss reduction is an execution check, not generalization evidence; saving adapters alone does not validate optimizer-state resume.
5. Inspect automatic device detection when reloading adapters. PEFT 0.15.2 with Accelerate 1.7.0 called `infer_device()` and imported an installed IPEX extension during reload, registering XPU kernels even though the inference/training code had not imported IPEX. That pilot's reload/API still passed. When the device is already known, this PEFT version accepts `torch_device='xpu:0'` to avoid that inference branch; revalidate behavior in the installed version. Do not compare timings across an unnoticed runtime change. Reload into an appropriate base model or use the existing PEFT model's adapter-loading method, and check saved tensor values rather than treating a warning-free load as proof.
6. For local API access, follow [the SSH forwarding checks](slurm.md#local-access-to-a-model-api). Only then try QLoRA or multiple GPUs if required. Test quantization operators on XPU explicitly. `device_map='auto'` inference sharding is not a replacement for a distributed training strategy. Multiple GPUs do not automatically pool memory.

If a CUDA-only dependency blocks the user's chosen method, report the concrete dependency and smallest alternative. Do not silently change model, precision, training objective or evaluation to declare success. An H100/A30 queue may be the better choice when adaptation costs exceed expected queue savings.

Sources (check installed versions against current docs):
- https://hprc.tamu.edu/kb/User-Guides/ACES/Intel_PVCs/
- https://huggingface.co/docs/transformers/intel_gpu
- https://huggingface.co/docs/bitsandbytes/v0.50.2/installation#intel-xpu
