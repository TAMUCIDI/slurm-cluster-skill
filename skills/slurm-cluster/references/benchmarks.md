# LLM benchmark integration

Use this when connecting an evaluator to a model on a Slurm compute node. For XPU runtime selection, read [pvc.md](pvc.md); for authenticated SSH access and service cleanup, read [slurm.md](slurm.md#local-access-to-a-model-api). Keep model inference in the allocated job. A lightweight HTTP client needs no GPU, but place substantial evaluation work according to site policy.

## Match the evaluator to the endpoint

Identify the intended benchmark's interface before deploying a server. Model loading, local reachability, framework-backend integration and a complete scored benchmark are separate results.

| Evaluator requirement | Evidence needed |
|---|---|
| Text/chat generation | A real client call with the expected prompt/chat template, generation parameters and response fields. |
| Likelihood-based scoring | The required token likelihood/logprob operation; a chat-only generation endpoint may not support it. |
| Strict JSON or a schema | Parse and validate the original response against the task contract; HTTP 200 alone is insufficient. |
| Tool calls, streaming, images or concurrent requests | Test that capability explicitly; a single nonstreaming text response provides no evidence for it. |

For an OpenAI-style endpoint, exercise the actual SDK/framework rather than only hand-written HTTP. Check the operations the evaluator uses, including model selection, response/usage fields and relevant authentication or invalid-request errors. A small compatibility endpoint does not establish full OpenAI API conformance.

Keep the model-serving environment separate from the evaluator's dependencies. The tested setup used a private CPU-only `lm_eval[api]`/OpenAI SDK environment to avoid changing the working shared Torch/XPU stack. An HTTP evaluator need not install a second GPU runtime; check the selected package extras and installed dependencies.

## Run a bounded integration check

Use a small set of synthetic fixtures for transport/backend testing when that is the requested scope. Save raw prompts and responses, model ID/revision, chat template, precision/backend, package versions, token limits, stopping/EOS settings and generation parameters. Pass tokenizer attention masks through to generation, especially for padded batches; a singleton check does not validate batching.

Report exactly which layer ran: a backend method receiving fixtures is not a full evaluator/task/scoring run. For an actual benchmark, also retain dataset/split/version, sample selection, scorer, scores and failed cases. GIS-shaped JSON fixtures establish no GIS reasoning accuracy.

Preserve malformed outputs as failures under the original contract. Removing Markdown fences, retrying or changing the prompt changes the evaluated procedure; apply such handling only if the benchmark defines it, and retain the original response. Do not infer constrained decoding or `response_format` support from a prompt requesting JSON.

Separate server generation time from client round-trip time. Compare repeated equivalent token lengths after warmup before reporting steady throughput; mixed cold fixtures are insufficient. Record allocator memory separately from total-board memory and host RAM, and include idle allocation time when reporting service cost.

## Observed ACES pilot, 2026-11-01

One PVC with native Torch 2.7.0+xpu / Transformers 4.51.3 served Qwen2.5-1.5B-Instruct using BF16/SDPA without CPU offload. An unauthenticated Gemma configuration request returned 401, with no configured Hub token or cached Gemma weights, so the alternative was disclosed before use. This was an access limitation, not a Gemma-on-PVC failure. Qwen weights were downloaded directly into the user's cluster scratch directory, not downloaded locally and uploaded.

OpenAI SDK 1.78.1 model-list/chat calls and expected 401/400/404 errors passed. With lm-eval 0.4.13, `LocalChatCompletion.generate_until` processed three synthetic fixtures; authenticated local chat through SSH also passed. No full task/scoring loop or actual GIS benchmark ran. Two JSON fixtures returned Markdown-fenced JSON and failed strict parsing. These results establish generation-backend connectivity and expose a structured-output limitation; likelihood scoring, streaming, tools, constrained JSON, multimodal input and concurrency remained untested.
