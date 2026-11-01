"""Local checks using real OpenSSH keys; no ACES access or allocation use."""
import contextlib
import io
from pathlib import Path
import runpy
import subprocess
import tempfile
import unittest
from unittest.mock import patch

cli = runpy.run_path(str(Path(__file__).parent / 'skills/slurm-cluster/scripts/aces.py'))
install_pair = cli['install_pair']


class CertificateInstallTest(unittest.TestCase):
    def test_pair_validation_and_backup(self):
        root = Path(tempfile.mkdtemp(prefix='aces-cli-test-'))
        install_pair.__globals__['CREDENTIALS'] = root / 'installed'
        def command(*args):
            subprocess.run(args, check=True, capture_output=True)
        for name in ('ca', 'first', 'second'):
            command('ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(root / name))
        for name in ('first', 'second'):
            command('ssh-keygen', '-q', '-s', str(root / 'ca'), '-I', 'test', '-n', 'test', '-V', '-1m:+1h', str(root / (name + '.pub')))
        with contextlib.redirect_stdout(io.StringIO()):
            install_pair(root / 'first', root / 'first-cert.pub')
            original = (root / 'installed/id_aces_tamu').read_bytes()
            with self.assertRaisesRegex(ValueError, 'do not match'):
                install_pair(root / 'second', root / 'first-cert.pub')
            self.assertEqual((root / 'installed/id_aces_tamu').read_bytes(), original)
            command('ssh-keygen', '-q', '-s', str(root / 'ca'), '-I', 'expired', '-n', 'test', '-V', '-2h:-1h', str(root / 'second.pub'))
            with self.assertRaisesRegex(ValueError, 'not currently valid'):
                install_pair(root / 'second', root / 'second-cert.pub')
            self.assertEqual((root / 'installed/id_aces_tamu').read_bytes(), original)
            command('ssh-keygen', '-q', '-s', str(root / 'ca'), '-I', 'valid', '-n', 'test', '-V', '-1m:+1h', str(root / 'second.pub'))
            install_pair(root / 'second', root / 'second-cert.pub')
        self.assertEqual((root / 'installed/id_aces_tamu.previous').read_bytes(), original)
        self.assertEqual((root / 'installed/id_aces_tamu').stat().st_mode & 0o777, 0o600)
        self.assertEqual((root / 'installed').stat().st_mode & 0o777, 0o700)

    def test_isolated_setup_and_openssh_resolution(self):
        setup = cli['setup_ssh']
        root = Path(tempfile.mkdtemp(prefix='aces-config-test-'))
        setup.__globals__['CREDENTIALS'] = root / 'ssh with spaces'
        with contextlib.redirect_stdout(io.StringIO()):
            setup('u.example')
            setup('u.example')
        config = root / 'ssh with spaces/config'
        resolved = subprocess.run(['ssh', '-G', '-F', str(config), 'aces'], check=True, capture_output=True, text=True).stdout
        self.assertIn('user u.example\n', resolved)
        self.assertIn('hostname login.aces.hprc.tamu.edu\n', resolved)
        self.assertIn('proxyjump aces-jump\n', resolved)
        before = config.read_bytes()
        with self.assertRaisesRegex(ValueError, 'already differs'):
            setup('u.other')
        self.assertEqual(config.read_bytes(), before)
        with self.assertRaisesRegex(ValueError, 'Invalid'):
            setup('user\nProxyCommand bad')

    def test_auto_renew_boundary(self):
        from datetime import datetime, timedelta, timezone
        check = cli['ensure_auth']
        now = datetime.now(timezone.utc)
        for remaining, expected in ((13, 0), (11, 1), (-1, 0)):
            with patch.dict(check.__globals__, {
                'certificate_window': lambda path: ('cert', now - timedelta(days=1), now + timedelta(hours=remaining)),
                'renew': unittest.mock.Mock(),
            }):
                renewal = check.__globals__['renew']
                if remaining < 0:
                    with self.assertRaisesRegex(ValueError, 'expired'):
                        check()
                else:
                    check()
                self.assertEqual(renewal.call_count, expected)

    def test_transfer_arguments_and_submission_stdin(self):
        import shlex
        main = cli['main']
        root = Path(tempfile.mkdtemp(prefix='aces-command-test-'))
        script = root / 'job with spaces.sbatch'
        script.write_text('#!/bin/bash\nprintf done\n')
        remote_path = '/scratch/a folder/$(not-a-command)'
        with patch.dict(main.__globals__, {'run': unittest.mock.Mock()}):
            runner = main.__globals__['run']
            with patch('sys.argv', ['aces', '--host', 'test-cluster', 'upload', str(script), remote_path]):
                main()
            self.assertEqual(runner.call_args.args[0][-2:], [str(script.resolve()), 'test-cluster:' + remote_path])
            with patch('sys.argv', ['aces', '--host', 'test-cluster', 'submit', '--check', '--workdir', remote_path, str(script)]):
                main()
            self.assertEqual(shlex.split(runner.call_args.args[0][-1]), ['sbatch', '--parsable', '--chdir', remote_path, '--test-only'])
            self.assertEqual(runner.call_args.kwargs['input'], script.read_bytes())


if __name__ == '__main__':
    unittest.main()
