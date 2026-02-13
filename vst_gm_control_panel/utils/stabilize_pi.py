#!/usr/bin/env python3
'''
stabilize_pi.py - Raspberry Pi System Optimization Script

- Cleans user caches (pip, poetry, cursor; prunes old VS Code Server builds)
- Vacuums systemd journals (retains 3 days)
- Ensures dphys-swapfile & earlyoom are installed if missing
- Ensures swap size (CONF_SWAPSIZE=4096, CONF_MAXSWAP=8192) and only rebuilds if needed
  (probes dphys-swapfile first; skips if "keeping it", and ensures swap is active)
- Sets vm.swappiness=60
- Enables earlyoom
- Prints a final status snapshot

Author: VST
License: Proprietary
'''

import os
import sys
import pwd
import shutil
import subprocess
import tempfile
from pathlib import Path

# Kivy imports
from kivy.logger import Logger

# ================= Configuration =================

DEFAULT_SWAP_SIZE_MB = 4096
MAX_SWAP_SIZE_MB = 8192
JOURNAL_RETENTION_DAYS = '3d'
SWAPPINESS_VALUE = 60
CACHE_DIRS = [
    '.cache/pip',
    '.cache/pypoetry',
    '.cursor-server',
]

# ================= Elevation =====================

def ensure_root():
    if os.geteuid() != 0:
        script_path = str(Path(__file__).resolve())
        os.execvp('sudo', ['sudo', '-E', sys.executable, script_path, *sys.argv[1:]])

# ================= Utilities =====================

def run(cmd, use_sudo=False, capture=False):
    full = cmd[:]
    if use_sudo and os.geteuid() != 0:
        full = ['sudo'] + full
    if capture:
        return subprocess.run(
            full, check=False, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        ).stdout.strip()
    subprocess.run(full, check=False)
    return ''

def safe_rm(path):
    try:
        if path.exists():
            Logger.info(f'Removing: {path}')
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
            else:
                try:
                    path.unlink()
                except FileNotFoundError:
                    pass
    except Exception as e:
        Logger.error(f'Failed to remove {path}: {e}')

def _install_text_atomic(dest_path, text):
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile('w', delete=False) as tf:
            tf.write(text)
            if not text.endswith('\n'):
                tf.write('\n')
            tmp_path = tf.name
        run(['mkdir', '-p', str(Path(dest_path).parent)], use_sudo=True)
        run(['install', '-m', '644', tmp_path, str(dest_path)], use_sudo=True)
    finally:
        if tmp_path:
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except Exception:
                pass

def edit_kv(conf_path, key, val):
    try:
        line = f'{key}={val}'
        Logger.info(f'Ensuring in {conf_path}: {line}')
        try:
            content = conf_path.read_text().splitlines() if conf_path.exists() else []
        except Exception:
            out = run(['cat', str(conf_path)], use_sudo=True, capture=True)
            content = out.splitlines() if out else []
        for i, l in enumerate(content):
            if l.strip().startswith(f'{key}='):
                content[i] = line
                break
        else:
            content.append(line)
        _install_text_atomic(conf_path, '\n'.join(content))
    except Exception as e:
        Logger.error(f'Failed to edit {conf_path}: {e}')
        raise

def read_conf_val(conf_path, key, default=None):
    try:
        txt = conf_path.read_text() if conf_path.exists() else ''
    except Exception:
        txt = run(['cat', str(conf_path)], use_sudo=True, capture=True) or ''
    for raw in txt.splitlines():
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith(f'{key}='):
            return line.split('=', 1)[1].strip()
    return default

# ================= Core tasks ====================

def prune_old_vscode_servers(user_home):
    try:
        servers_dir = user_home / '.vscode-server' / 'cli' / 'servers'
        if not servers_dir.exists():
            Logger.info(f'No VS Code servers found at {servers_dir}.')
            return
        subdirs = [d for d in servers_dir.iterdir() if d.is_dir()]
        if len(subdirs) <= 1:
            Logger.info('0 or 1 VS Code server found; nothing to prune.')
            return
        subdirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        keep = subdirs[0]
        Logger.info(f'Keeping newest VS Code server: {keep.name}')
        for d in subdirs[1:]:
            Logger.info(f'Deleting old VS Code server: {d.name}')
            safe_rm(d)
    except Exception as e:
        Logger.error(f'Failed to prune VS Code servers: {e}')

def clean_user_caches(user_home):
    try:
        for rel in CACHE_DIRS:
            safe_rm(user_home / rel)
        prune_old_vscode_servers(user_home)
    except Exception as e:
        Logger.error(f'Failed to clean user caches: {e}')

def cleanup_journals():
    try:
        Logger.info(f'Vacuuming old system logs (keep last {JOURNAL_RETENTION_DAYS})...')
        out = run(['journalctl', f'--vacuum-time={JOURNAL_RETENTION_DAYS}'], use_sudo=True, capture=True)
        if out:
            Logger.info(out)
    except Exception as e:
        Logger.error(f'Failed to cleanup journals: {e}')

def is_pkg_installed(pkg: str) -> bool:
    """
    Return True if a Debian package appears installed.
    Uses dpkg-query (no network).
    """
    out = run(['dpkg-query', '-W', '-f=${Status}', pkg], capture=True)
    return out.strip().endswith('installed')

def ensure_packages_if_missing():
    """
    Ensure dphys-swapfile and earlyoom are installed.
    No weekly gating; apt-get is run only if something is missing.
    """
    try:
        needed = [p for p in ('dphys-swapfile', 'earlyoom') if not is_pkg_installed(p)]
        if not needed:
            Logger.info('Required packages already present: dphys-swapfile, earlyoom')
            return
        Logger.info(f'Installing required packages: {" ".join(needed)}')
        run(['apt-get', 'update', '-y'], use_sudo=True)
        run(['apt-get', 'install', '-y', *needed], use_sudo=True)
    except Exception as e:
        Logger.error(f'Failed to ensure packages: {e}')
        # Non-fatal: the rest may still work if already present

def ensure_swap_sizes_and_apply_if_needed(target_mb=DEFAULT_SWAP_SIZE_MB, max_mb=MAX_SWAP_SIZE_MB):
    '''
    Ensure CONF_SWAPSIZE and CONF_MAXSWAP are set.
    Probe dphys-swapfile to see if a rebuild is needed; only rebuild if not "keeping it".
    If skipping rebuild, ensure swap is active (swapon) using CONF_SWAPFILE (default /var/swap).
    '''
    if target_mb <= 0 or max_mb <= 0:
        raise ValueError('Swap sizes must be positive')
    if target_mb > max_mb:
        raise ValueError('Target swap size cannot exceed maximum')

    conf = Path('/etc/dphys-swapfile')
    if not conf.exists():
        raise SystemExit('ERROR: /etc/dphys-swapfile not found. Is dphys-swapfile installed?')

    # Ensure config values
    edit_kv(conf, 'CONF_SWAPSIZE', str(target_mb))
    edit_kv(conf, 'CONF_MAXSWAP', str(max_mb))

    # Probe first (no teardown yet)
    Logger.info('Checking if swap rebuild is needed...')
    probe = run(['dphys-swapfile', 'setup'], use_sudo=True, capture=True)
    if probe:
        Logger.info(probe)

    swapfile_path = read_conf_val(conf, 'CONF_SWAPFILE', '/var/swap')

    # If it's keeping the existing file, skip disruptive steps but make sure swap is active
    if 'keeping it' in (probe or ''):
        Logger.info('Swapfile size already matches effective target; no rebuild needed.')
        # If swap is off for some reason, turn it on
        run(['swapon', swapfile_path], use_sudo=True)
        Logger.info(run(['swapon', '--show'], capture=True))
        return

    # Otherwise, rebuild: swapoff -> setup -> swapon
    Logger.info('Recreating swapfile to apply new size (no reboot)...')
    run(['dphys-swapfile', 'swapoff'], use_sudo=True)
    setup_out = run(['dphys-swapfile', 'setup'], use_sudo=True, capture=True)
    if setup_out:
        Logger.info(setup_out)
    run(['dphys-swapfile', 'swapon'], use_sudo=True)
    Logger.info(run(['swapon', '--show'], capture=True))

def set_swappiness(value=SWAPPINESS_VALUE):
    if not 0 <= value <= 100:
        raise ValueError('Swappiness value must be between 0 and 100')
    try:
        conf = Path('/etc/sysctl.d/99-swappiness.conf')
        Logger.info(f'Setting vm.swappiness={value} ...')
        _install_text_atomic(conf, f'vm.swappiness={value}\n')
        run(['sysctl', '-p', str(conf)], use_sudo=True)
    except Exception as e:
        Logger.error(f'Failed to set swappiness: {e}')
        raise

def enable_earlyoom():
    try:
        Logger.info('Enabling earlyoom service...')
        run(['systemctl', 'enable', '--now', 'earlyoom'], use_sudo=True)
    except Exception as e:
        Logger.error(f'Failed to enable earlyoom: {e}')
        raise

def final_report():
    try:
        Logger.info('== Final status ==')
        Logger.info(run(['df', '-h', '/'], capture=True))
        Logger.info(run(['free', '-h'], capture=True))
        Logger.info(run(['swapon', '--show'], capture=True))
        vcg = shutil.which('vcgencmd')
        if vcg:
            Logger.info(f'Throttling: {run([vcg, "get_throttled"], capture=True)}')
    except Exception as e:
        Logger.error(f'Failed to generate final report: {e}')

# ================= Entry point ===================

def main():
    ensure_root()
    try:
        sudo_user = os.environ.get('SUDO_USER')
        if sudo_user and sudo_user != 'root':
            user_home = Path(pwd.getpwnam(sudo_user).pw_dir)
        else:
            user_home = Path.home()

        Logger.info(f'Running stabilize_pi.py for user {user_home}')

        clean_user_caches(user_home)
        cleanup_journals()
        ensure_packages_if_missing()           # << no weekly stamp; installs only if missing
        ensure_swap_sizes_and_apply_if_needed()  # probe-first, ensure active
        set_swappiness()
        enable_earlyoom()
        final_report()

        Logger.info('System optimization completed successfully')
    except Exception as e:
        Logger.error(f'System optimization failed: {e}')
        raise SystemExit(1)

if __name__ == '__main__':
    main()