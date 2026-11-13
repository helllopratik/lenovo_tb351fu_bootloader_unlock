#!/usr/bin/env python3
import os
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

def run_cmd(cmd, cwd=None):
    print(f"\n[EXEC] {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=cwd)

def ensure_venv():
    """Relaunch under the bundled venv so mtkclient's deps (e.g. pycryptodome) are found.

    Running this script with sudo makes the shebang resolve to the system python,
    which does not have mtkclient's dependencies installed.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    venv_dir = os.path.join(base_dir, "venv")
    venv_python = os.path.join(venv_dir, "bin", "python3")
    if os.path.exists(venv_python) and os.path.realpath(sys.prefix) != os.path.realpath(venv_dir):
        print(f"[*] Switching to bundled interpreter: {venv_python}", flush=True)
        sys.stdout.flush()
        os.execv(venv_python, [venv_python, os.path.abspath(__file__), *sys.argv[1:]])

def backup_once(path):
    """Keep a pristine copy of the scatter file so it can be restored later."""
    bak = path + ".stock.bak"
    if os.path.exists(path) and not os.path.exists(bak):
        shutil.copyfile(path, bak)
        print(f"[*] Backed up original scatter to: {os.path.basename(bak)}")
    return bak

def patch_scatter_for_unlock(scatter_path, token_filename, targets=("seccfg", "unlock")):
    """Enable ONLY the token partitions in the scatter file.

    The stock scatter marks the whole firmware as downloadable, which makes
    SP Flash Tool try to flash images (preloader, boot, super, ...) that are not
    present in assets/. That fails with the misleading error
    "<unspecified file>(1): expected <". For unlocking we only want to write
    the generated token to seccfg/unlock.
    """
    tree = ET.parse(scatter_path)
    root = tree.getroot()
    found = []

    for partition in root.iter("partition_index"):
        name_el = partition.find("partition_name")
        dl_el = partition.find("is_download")
        fn_el = partition.find("file_name")
        if name_el is None or dl_el is None or fn_el is None:
            continue

        name = (name_el.text or "").strip()
        if name in targets:
            dl_el.text = "true"
            fn_el.text = token_filename
            found.append(name)
        else:
            dl_el.text = "false"

    tree.write(scatter_path, encoding="utf-8", xml_declaration=True)
    return found

def main():
    ensure_venv()
    base_dir = os.path.dirname(os.path.abspath(__file__))
    token_path = os.path.join(base_dir, "generated_unlock_token.bin")
    mtk_dir = os.path.join(base_dir, "mtkclient")
    spflash_dir = os.path.join(base_dir, "spflash")
    assets_dir = os.path.join(base_dir, "assets")

    print("====================================================")
    print("   Lenovo TB351FU Foolproof Bootloader Unlocker")
    print("====================================================")
    
    # Check if we are root
    if os.geteuid() != 0:
        print("Error: This tool must be run with sudo.")
        sys.exit(1)

    # Step 1: Generate the unique token
    print("\nSTAGE 1: Generating Unique Hardware Token...")
    print("1. Ensure tablet is UNPLUGGED and POWERED OFF.")
    print("2. When prompted, hold VOL UP + VOL DOWN and plug in USB.")
    input("Press Enter to start Stage 1...")

    cmd_gen = [
        sys.executable, "mtk.py", "da", "seccfg", "unlock",
        "--loader", "../assets/DA_BR.bin",
        "--auth", "../assets/da.auth",
        "--preloader", "../assets/DA_BR.bin" # Using DA as PL often helps handshake
    ]
    
    # We expect this to fail at the end, but the file should be created
    run_cmd(cmd_gen, cwd=mtk_dir)

    if not os.path.exists(token_path):
        print("\nError: Hardware token generation failed. Ensure your tablet connected correctly.")
        sys.exit(1)

    print("\nSuccess: Hardware-Unique Token Generated.")
    print("----------------------------------------------------")

    # Step 2: Flash the token
    print("\nSTAGE 2: Flashing the Token...")
    print("1. UNPLUG the tablet.")
    print("2. Hold POWER for 20 seconds to reset from previous stage.")
    print("3. When prompted, hold VOL UP + VOL DOWN and plug in USB.")
    input("Press Enter to start Stage 2...")

    # The token must live next to the scatter file, because SP Flash Tool
    # resolves the scatter's <file_name> entries relative to the scatter itself.
    scatter_path = os.path.join(assets_dir, "MT6789_Android_scatter.xml")
    if not os.path.exists(scatter_path):
        print(f"\nError: assets/MT6789_Android_scatter.xml not found!")
        sys.exit(1)

    token_filename = os.path.basename(token_path)
    assets_token = os.path.join(assets_dir, token_filename)
    if os.path.abspath(assets_token) != os.path.abspath(token_path):
        shutil.copyfile(token_path, assets_token)
    print(f"[*] Token staged for flashing: assets/{token_filename}")

    # Make sure only the seccfg/unlock partitions get written.
    backup_once(scatter_path)
    enabled = patch_scatter_for_unlock(scatter_path, token_filename)
    if not enabled:
        print("\nError: could not find a 'seccfg' or 'unlock' partition in the scatter file.")
        sys.exit(1)
    print(f"[*] Scatter patched. Partitions enabled for download: {', '.join(sorted(set(enabled)))}")

    # We need to use absolute paths for SP Flash Tool to be stable
    cmd_flash = [
        "bash", "./SPFlashToolV6.sh", 
        "-c", "download", 
        "-f", os.path.join(assets_dir, "flash.xml"),
        "-a", os.path.join(assets_dir, "da.auth")
    ]
    
    run_cmd(cmd_flash, cwd=spflash_dir)

    print("\n====================================================")
    print("   PROCESS COMPLETE!")
    print("   Reboot your tablet to Fastboot Mode.")
    print("   Run 'fastboot getvar unlocked' to verify.")
    print("====================================================")

if __name__ == "__main__":
    main()
