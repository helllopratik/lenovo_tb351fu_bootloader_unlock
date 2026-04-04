#!/usr/bin/env python3
import os
import subprocess
import sys
import time

def run_cmd(cmd, cwd=None):
    print(f"\n[EXEC] {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=cwd)

def main():
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
    print("2. When prompted, hold VOL UP and plug in USB.")
    print("   On TB351FU, plugging in the cable while holding VOL UP should enter BROM.")
    input("Press Enter to start Stage 1...")

    cmd_gen = [
        "python3", "mtk.py", "da", "seccfg", "unlock",
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
    print("3. When prompted, unplug usb and re-plug while pressing VOL UP key.")
    input("Press Enter to start Stage 2...")

    # We need to use absolute paths for SP Flash Tool to be stable
    cmd_flash = [
        "./SPFlashToolV6.sh", 
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
