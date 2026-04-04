#!/usr/bin/env python3
import os
import subprocess
import sys
import xml.etree.ElementTree as ET

def run_cmd(cmd, cwd=None):
    print(f"\n[EXEC] {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=cwd)

def patch_scatter_for_unlock(scatter_path, token_filename):
    print(f"Checking scatter file: {scatter_path}")
    tree = ET.parse(scatter_path)
    root = tree.getroot()
    found = False
    for partition in root.findall(".//partition_index"):
        p_name = partition.find("partition_name").text
        if p_name == "unlock":
            partition.find("is_download").text = "true"
            partition.find("file_name").text = f"../{token_filename}"
            found = True
        else:
            # Disable all other partitions for safety during a "Force Unlock"
            partition.find("is_download").text = "false"
    
    if found:
        tree.write(scatter_path, encoding="utf-8", xml_declaration=True)
        print("  [+] Scatter file successfully patched for hardware-token injection.")
    else:
        print("  [!] Error: Could not find 'unlock' partition in scatter file.")
        sys.exit(1)

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    token_name = "generated_unlock_token.bin"
    token_path = os.path.join(base_dir, token_name)
    mtk_dir = os.path.join(base_dir, "mtkclient")
    spflash_dir = os.path.join(base_dir, "spflash")
    assets_dir = os.path.join(base_dir, "assets")
    scatter_path = os.path.join(assets_dir, "MT6789_Android_scatter.xml")

    print("====================================================")
    print("   Lenovo TB351FU One-Click Universal Unlocker")
    print("====================================================")
    
    if os.geteuid() != 0:
        print("Error: This tool must be run with sudo.")
        sys.exit(1)

    if not os.path.exists(scatter_path):
        print(f"Error: assets/MT6789_Android_scatter.xml not found!")
        sys.exit(1)

    # Step 1: Generate the unique token
    print("\nSTAGE 1: Generating Unique Hardware Token...")
    print("Hold VOL UP and plug in USB.")
    
    cmd_gen = [
        sys.executable, "mtk.py", "da", "seccfg", "unlock",
        "--loader", "../assets/DA_BR.bin",
        "--auth", "../assets/da.auth",
        "--preloader", "../assets/DA_BR.bin"
    ]
    # Patch MTKClient to save to the parent folder
    run_cmd(cmd_gen, cwd=mtk_dir)

    if not os.path.exists(token_path):
        print("\nError: Token generation failed or Device Disconnected. Please ensure the device is properly connected and try again.")
        sys.exit(1)

    # Step 2: Patch the user's provided scatter file
    patch_scatter_for_unlock(scatter_path, token_name)

    # Step 3: Flash
    print("\nSTAGE 3: Flashing the Token...")
    print("1. UNPLUG the tablet. 2. Hold VOL UP and plug in.")
    input("Press Enter when ready to flash...")

    cmd_flash = [
        "/bin/sh", "./SPFlashToolV6.sh", 
        "-c", "download", 
        "-f", os.path.join(assets_dir, "flash.xml"),
        "-a", os.path.join(assets_dir, "da.auth")
    ]
    run_cmd(cmd_flash, cwd=spflash_dir)

    print("\n====================================================")
    print("   PROCESS COMPLETE! DEVICE IS UNLOCKED.")
    print("====================================================")

if __name__ == "__main__":
    main()
