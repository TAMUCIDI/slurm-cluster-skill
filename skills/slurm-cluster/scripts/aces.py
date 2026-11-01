#!/usr/bin/env python3
"""Small local ACES client using the existing ssh aces configuration."""
import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

CREDENTIALS = Path.home() / '.ssh' / 'aces'
KEY = 'id_aces_tamu'
PORTAL = 'https://portal-aces.hprc.tamu.edu/pun/sys/sshca'
HOST = 'aces'


def main():
    global HOST
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default='aces', help='Existing SSH alias; non-ACES hosts use generic Slurm commands')
    parser.add_argument('--no-renew', action='store_true', help='Skip automatic renewal for this command')
    commands = parser.add_subparsers(dest='command', required=True)
    setup = commands.add_parser('setup', help='Create isolated ACES SSH configuration (no credentials generated)')
    setup.add_argument('--user', required=True, help='Your ACES resource username')
    commands.add_parser('auth', help='Show local certificate validity')
    commands.add_parser('renew', help='Renew over SSH before expiry; install and verify the new pair')
    install = commands.add_parser('install-cert', help='Install a pair downloaded from the portal')
    install.add_argument('key', type=Path)
    install.add_argument('certificate', type=Path)
    resources = commands.add_parser('resources', help='Show current resources or allocations')
    resources.add_argument('kind', choices=['gpu', 'cpu', 'partitions', 'projects'], default='gpu', nargs='?')
    jobs = commands.add_parser('jobs', help='Show your queue, or accounting for one job')
    jobs.add_argument('job_id', type=job_id, nargs='?')
    submit = commands.add_parser('submit', help='Send a local batch script to sbatch over SSH')
    submit.add_argument('--workdir', required=True, help='Existing absolute directory on ACES')
    submit.add_argument('--check', action='store_true', help='sbatch --test-only; do not submit')
    submit.add_argument('script', type=Path)
    submit.add_argument('sbatch_args', nargs=argparse.REMAINDER, help='Extra sbatch options after --')
    cancel = commands.add_parser('cancel', help='Cancel a job')
    cancel.add_argument('job_id', type=job_id)
    logs = commands.add_parser('logs', help='Tail a remote output file')
    logs.add_argument('path')
    for name in ('upload', 'download'):
        transfer = commands.add_parser(name, help='Copy a file/directory using SCP (existing files may be overwritten)')
        transfer.add_argument('source')
        transfer.add_argument('destination')
    directory = commands.add_parser('mkdir', help='Create a remote working directory')
    directory.add_argument('path')
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', args.host):
        parser.error('--host must be an SSH host alias')
    HOST = args.host
    if HOST != 'aces' and args.command in ('setup', 'auth', 'renew', 'install-cert'):
        parser.error('Certificate operations and setup are ACES-specific')
    if args.command not in ('setup', 'auth', 'renew', 'install-cert') and HOST == 'aces' and not args.no_renew:
        ensure_auth()

    if args.command == 'setup':
        setup_ssh(args.user)
    elif args.command == 'auth':
        run(['ssh-keygen', '-L', '-f', str(CREDENTIALS / (KEY + '-cert.pub'))])
    elif args.command == 'renew':
        renew()
    elif args.command == 'install-cert':
        install_pair(args.key, args.certificate)
        remote('true')
    elif args.command == 'resources':
        if HOST == 'aces':
            remote({'gpu': 'gpuavail', 'cpu': 'cpuavail', 'partitions': 'sinfo', 'projects': 'myproject'}[args.kind])
        elif args.kind == 'projects':
            remote('sacctmgr -nP show assoc where user="$USER" format=Cluster,Account,Partition,QOS')
        else:
            remote('sinfo -N -o "%N %P %t %G %C %m"')
    elif args.command == 'jobs':
        if args.job_id:
            remote(shlex.join(['sacct', '-j', args.job_id, '--parsable2', '--format=JobID,JobName,State,ExitCode,Elapsed,AllocTRES']))
        else:
            remote('squeue -u "$USER" -o "%.18i %.30j %.12P %.12T %.10M %.6D %R"')
    elif args.command == 'submit':
        if not args.workdir.startswith('/'):
            parser.error('--workdir must be an absolute remote path')
        script = args.script.read_bytes()
        if not script.startswith(b'#!'):
            parser.error('batch script must start with a shebang (e.g. #!/bin/bash)')
        options = args.sbatch_args
        if options[:1] == ['--']:
            options = options[1:]
        command = ['sbatch', '--parsable', '--chdir', args.workdir]
        if args.check:
            command.append('--test-only')
        remote(shlex.join(command + options), input=script)
    elif args.command == 'cancel':
        remote(shlex.join(['scancel', args.job_id]))
    elif args.command == 'logs':
        remote(shlex.join(['tail', '-n', '100', '--', args.path]))
    elif args.command == 'mkdir':
        remote(shlex.join(['mkdir', '-p', '--', absolute_remote(args.path)]))
    elif args.command in ('upload', 'download'):
        if args.command == 'upload':
            source = str(Path(args.source).expanduser().resolve())
            destination = HOST + ':' + absolute_remote(args.destination)
        else:
            source = HOST + ':' + absolute_remote(args.source)
            destination = str(Path(args.destination).expanduser().resolve())
        run(['scp', *ssh_options(), '-r', source, destination])


def job_id(value):
    if not re.fullmatch(r'[0-9]+(?:_[0-9]+)?', value):
        raise argparse.ArgumentTypeError('expected a numeric job ID or job_array-task ID')
    return value


def run(command, **kwargs):
    return subprocess.run(command, check=True, **kwargs)


def remote(command, **kwargs):
    return run(['ssh', *ssh_options(), HOST, command], **kwargs)


def ssh_options():
    options = ['-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15']
    config = CREDENTIALS / 'config'
    if HOST == 'aces' and config.exists():
        options += ['-F', str(config)]
    return options


def absolute_remote(value):
    if not value.startswith('/') or '\n' in value or '\x00' in value:
        raise ValueError('Use an absolute remote path without newlines')
    return value


def setup_ssh(user):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', user):
        raise ValueError('Invalid ACES resource username')
    CREDENTIALS.mkdir(mode=0o700, parents=True, exist_ok=True)
    CREDENTIALS.chmod(0o700)
    config = CREDENTIALS / 'config'
    content = f'''Host aces-jump
  HostName aces-jump.hprc.tamu.edu
  Port 8822

Host aces
  HostName login.aces.hprc.tamu.edu
  ProxyJump aces-jump

Host aces aces-jump
  User {user}
  IdentityFile "{CREDENTIALS / KEY}"
  IdentitiesOnly yes
  ConnectTimeout 15
'''
    if config.exists() and config.read_text() != content:
        raise ValueError(f'{config} already differs; inspect/edit it explicitly instead of overwriting')
    config.write_text(content)
    config.chmod(0o600)
    print(f'Created {config}; existing ~/.ssh/config unchanged. Import your portal pair with install-cert.')
    print(f'First connection: ssh -F {shlex.quote(str(config))} aces (verify host keys when prompted).')


def certificate_window(certificate):
    description = run(['ssh-keygen', '-L', '-f', str(certificate)], capture_output=True, text=True,
                      env={**os.environ, 'TZ': 'UTC'}).stdout
    validity = re.search(r'Valid: from (\S+) to (\S+)', description)
    if ' user certificate' not in description or not validity:
        raise ValueError('Expected a finite-validity SSH user certificate')
    start, end = (datetime.fromisoformat(value).replace(tzinfo=timezone.utc) for value in validity.groups())
    return description, start, end


def ensure_auth():
    _, start, end = certificate_window(CREDENTIALS / (KEY + '-cert.pub'))
    now = datetime.now(timezone.utc)
    if not start <= now < end:
        raise ValueError(f'Certificate expired/not yet valid. Sign in at {PORTAL}, then install-cert.')
    if (end - now).total_seconds() < 12 * 3600:
        print('Certificate expires within 12h; renewing before this command.', file=sys.stderr)
        # Keep job-ID stdout clean when a submit triggers renewal.
        import contextlib
        with contextlib.redirect_stdout(sys.stderr):
            renew()


def install_pair(key, certificate):
    CREDENTIALS.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(CREDENTIALS, 0o700)
    # Stage and validate both files before replacing working credentials.
    stage = Path(tempfile.mkdtemp(prefix='renew-', dir=CREDENTIALS))
    staged_key = stage / KEY
    staged_cert = stage / (KEY + '-cert.pub')
    shutil.copyfile(key, staged_key)
    shutil.copyfile(certificate, staged_cert)
    staged_key.chmod(0o600)
    staged_cert.chmod(0o600)
    public = run(['ssh-keygen', '-y', '-P', '', '-f', str(staged_key)], capture_output=True).stdout
    key_fp = run(['ssh-keygen', '-lf', '-'], input=public, capture_output=True).stdout.split()[1]
    cert_fp = run(['ssh-keygen', '-lf', str(staged_cert)], capture_output=True).stdout.split()[1]
    if key_fp != cert_fp:
        raise ValueError('Key and certificate do not match; active credentials unchanged')
    description, start, end = certificate_window(staged_cert)
    if not start <= datetime.now(timezone.utc) < end:
        raise ValueError('Certificate is not currently valid; active credentials unchanged')
    for name in (KEY, KEY + '-cert.pub'):
        target = CREDENTIALS / name
        if target.exists():
            shutil.copyfile(target, CREDENTIALS / (name + '.previous'))
            (CREDENTIALS / (name + '.previous')).chmod(0o600)
        os.replace(stage / name, target)
    print(description, end='')


def renew():
    result = remote('/usr/local/bin/gen_ssh_cert.sh', capture_output=True, text=True)
    # The official script can return exit 0 on failure; inspect its success marker.
    if 'Certificated signed pubkey' not in result.stdout or 'Error' in result.stdout:
        raise ValueError(result.stdout.strip() or 'Certificate generation did not report success')
    CREDENTIALS.mkdir(mode=0o700, parents=True, exist_ok=True)
    download = Path(tempfile.mkdtemp(prefix='download-', dir=CREDENTIALS))
    for name in (KEY, KEY + '-cert.pub'):
        run(['scp', '-q', *ssh_options(), 'aces:.ssh/aces/' + name, str(download / name)])
        (download / name).chmod(0o600)
    install_pair(download / KEY, download / (KEY + '-cert.pub'))
    remote('true')
    print('Renewed and verified a new SSH connection. Previous pair retained as *.previous.')


if __name__ == '__main__':
    try:
        main()
    except subprocess.CalledProcessError as error:
        # Do not echo captured output: renewal transfers authentication material.
        print(f'Command failed (exit {error.returncode}). If SSH authentication expired, sign in at {PORTAL} and use install-cert.', file=sys.stderr)
        sys.exit(error.returncode or 1)
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
