# Slurm Cluster Agent Skill

让 agent 通过 SSH 使用 ACES 和其他 Slurm 集群。Skill 负责操作流程和 PVC/XPU 适配知识，标准库 Python CLI 负责配置、续期、传输和任务操作。支持 macOS/Linux；Windows 请使用 WSL。运行依赖：Python 3.9+、OpenSSH 9+。

```bash
git clone https://github.com/jz0204/slurm-cluster-skill.git
cd slurm-cluster-skill
```

## 交给 agent

直接告诉 agent：

> 阅读这个 repo 的 `skills/slurm-cluster/SKILL.md`，帮助我配置自己的 ACES 账号，并按里面的流程使用集群。

支持标准 skills 的 agent 可以安装整个 `skills/slurm-cluster` 文件夹。Codex 示例（在 repo 根目录运行；已有同名 skill 时先检查，不要覆盖）：

```bash
mkdir -p ~/.codex/skills
ln -s "$PWD/skills/slurm-cluster" ~/.codex/skills/slurm-cluster
```

重启/刷新 agent 的技能发现后调用 `$slurm-cluster`。仅下载 repo 不一定会被 agent 自动发现；也可以明确让它读取 SKILL.md。Skill 文件夹自包含，可单独分享，不依赖本机历史实验。

## 首次使用 ACES

```bash
./aces setup --user YOUR_ACES_USERNAME
# 首次到 ACES portal 登录并下载自己的配套私钥/证书
./aces install-cert /path/to/id_aces_tamu /path/to/id_aces_tamu-cert.pub
```

自动写入独立的 `~/.ssh/aces/config`，不修改全局 SSH 配置。首次连接仍需按 HPRC 指引确认主机密钥；使用 `ssh -F ~/.ssh/aces/config aces`。每人需要自己的账号和 allocation，本 repo 不提供公共账号或凭据。

首次登录或证书已经过期时，需要 portal/SSO/MFA。有效期内无需网页：每次 ACES 远程操作前检查证书，剩余不足 12 小时自动续期。长期不用、电脑休眠或不调用 CLI 时不会后台续期。`--no-renew` 禁用本次自动续期；`./aces renew` 可手动提前续期。保留旧凭据和受保护的暂存目录以便恢复，不安装定时任务。

## 日常使用

```bash
./aces auth
./aces resources gpu                 # gpu / cpu / partitions / projects
./aces mkdir /absolute/remote/run
./aces upload ./train.py /absolute/remote/run/train.py
./aces submit --check --workdir /absolute/remote/run train.sbatch
./aces submit --workdir /absolute/remote/run train.sbatch -- --account=YOUR_PROJECT
./aces jobs
./aces jobs 1234567
./aces logs /absolute/remote/run/train-1234567.out
./aces download /absolute/remote/run/results.json ./results.json
./aces cancel 1234567
```

`submit` 只上传本地 sbatch 脚本并提交；训练代码和数据需先传输。`--check` 不提交任务。任务被 Slurm 接受后独立运行，不需要 agent 保持连接。复制可能覆盖同名目标；使用独立 run 目录。提交响应丢失时先查队列，不要盲目重试。详见 [Slurm 操作](skills/slurm-cluster/references/slurm.md)。

其他集群使用已有 SSH alias：

```bash
./aces --host OTHER_CLUSTER resources partitions
./aces --host OTHER_CLUSTER jobs
./aces --host OTHER_CLUSTER submit --workdir /remote/run train.sbatch
```

通用模式复用标准 Slurm/SCP，不使用 ACES 证书续期，也不替用户猜测该集群的 account、分区、环境和额度。CLI 保留 `aces` 名称以兼容原有调用。

## PVC 不只是改提交参数

[PVC 指南](skills/slurm-cluster/references/pvc.md) 教 agent 判断 CUDA 依赖、选择 XPU 环境、验证前反向传播和 checkpoint，再尝试单卡 LoRA、QLoRA 或多卡。包含一个小型 [XPU 探针](skills/slurm-cluster/scripts/xpu_probe.py) 和 [Slurm 模板](skills/slurm-cluster/assets/pvc-probe.sbatch)，运行前需确认资源预算。

已有本地实测：ACES 官方脚本可经 SSH 续期；Torch 2.7 XPU 环境完成单卡 CNN 训练。旧 Torch 2.1/IPEX 路径曾无法识别 XPU。共享路径和软件版本可能变化，skill 要求重新核实。CNN 成功不代表任意 LLM、量化算子和分布式训练都兼容。

## 验证与分发

```bash
python3 -m unittest -v test_aces.py
```

测试使用真实 OpenSSH 密钥/证书，检查导入、过期/不匹配拒绝、备份、权限、SSH 配置解析及自动续期分支。CLI 不依赖 PyYAML；官方 skill 验证器需要它，可在独立开发环境运行。

分发 `skills/slurm-cluster/` 或其压缩包即可。现有 HANDOFF、analysis、benchmarks 是本机调查/实验记录，含用户账号等信息，已被 `.gitignore` 排除；不要整体打包工作目录公开分享。尚未指定开源许可证。
