#!/usr/bin/env python3
import os
import subprocess
import sys
import xml.etree.ElementTree as ET

def run_cmd(cmd, cwd=None):
    print(f"\n[EXEC] {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=cwd)

def patch_scatter_for_unlock(scatter_path, token_path):
    print(f"Surgically patching scatter file: {scatter_path}")
    tree = ET.parse(scatter_path)
    root = tree.getroot()
    
    # We target BOTH seccfg and unlock partitions
    # We also disable everything else for safety
    targets = ["seccfg", "unlock"]
    found_partitions = []

    for partition in root.findall(".//partition_index"):
        p_name = partition.find("partition_name").text
        is_dl = partition.find("is_download")
        f_name = partition.find("file_name")
        
        if p_name in targets:
            is_dl.text = "true"
            f_name.text = token_path # Use absolute path to avoid confusion
            found_partitions.append(p_name)
            print(f"  [+] Enabled partition: {p_name} -> {token_path}")
        else:
            is_dl.text = "false"
            # Keep original filename just in case, but SP tool won't flash it
    
    tree.write(scatter_path, encoding="utf-8", xml_declaration=True)
    return list(set(found_partitions))

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    # Force absolute paths for everything
    token_path = os.path.join(base_dir, "assets", "generated_unlock_token.bin")
    mtk_dir = os.path.join(base_dir, "mtkclient")
    spflash_dir = os.path.join(base_dir, "spflash")
    assets_dir = os.path.join(base_dir, "assets")
    scatter_path = os.path.join(assets_dir, "MT6789_Android_scatter.xml")
    flash_xml_path = os.path.join(assets_dir, "flash.xml")
    da_path = os.path.join(assets_dir, "da.auth")

    print("====================================================")
    print("   Lenovo TB351FU One-Click ADVANCED Unlocker")
    print("   (Supports UFS/EMMC & Cross-Device Generation)")
    print("====================================================")
    
    if os.geteuid() != 0:
        print("Error: This tool must be run with sudo.")
        sys.exit(1)

    # Ensure assets directory exists
    os.makedirs(assets_dir, exist_ok=True)

    # Step 1: Generate the unique token
    print("\nSTAGE 1: Generating Unique Hardware Token...")
    print("This will use your tablet's HACC engine to sign the unlock token.")
    print("Hold VOL UP + VOL DOWN and plug in USB.")
    
    # We use mtkclient to generate the signed token
    # We use absolute path for the output file
    cmd_gen = [
        sys.executable, "mtk.py", "da", "seccfg", "unlock",
        "--loader", os.path.join(assets_dir, "DA_BR.bin"),
        "--auth", da_path,
        "--preloader", os.path.join(assets_dir, "DA_BR.bin")
    ]
    
    # Patch MTKClient's v6.py and xflash.py to save to our absolute token_path
    # We do this dynamically before running
    for patch_file in [
        os.path.join(mtk_dir, "mtkclient", "Library", "DA", "xmlflash", "extension", "v6.py"),
        os.path.join(mtk_dir, "mtkclient", "Library", "DA", "xflash", "extension", "xflash.py")
    ]:
        if os.path.exists(patch_file):
            with open(patch_file, "r") as f:
                content = f.read()
            # Find the line where we save the token and replace it
            import re
            content = re.sub(r'open\(.*generated_unlock_token\.bin", "wb"\)\.write\(writedata\)', 
                             f'open("{token_path}", "wb").write(writedata)', content)
            with open(patch_file, "w") as f:
                f.write(content)

    run_cmd(cmd_gen, cwd=mtk_dir)

    if not os.path.exists(token_path):
        print(f"\nError: Token file not found at {token_path}")
        sys.exit(1)

    # Step 2: Patch the scatter file
    found = patch_scatter_for_unlock(scatter_path, token_path)
    if not found:
        print("Error: Critical partitions not found in scatter file.")
        sys.exit(1)

    # Step 3: Flash
    print("\nSTAGE 2: Flashing Hardware-Signed Tokens...")
    print("1. UNPLUG the tablet.")
    print("2. Hold POWER for 20s to reset.")
    print("3. Hold VOL UP + VOL DOWN and plug in.")
    input("Press Enter when ready to flash...")

    cmd_flash = [
        "/bin/sh", "./SPFlashToolV6.sh", 
        "-c", "download", 
        "-f", flash_xml_path,
        "-a", da_path
    ]
    run_cmd(cmd_flash, cwd=spflash_dir)

    print("\n====================================================")
    print("   PROCESS COMPLETE!")
    print("   Check for 'Orange State' on boot.")
    print("   Run 'fastboot getvar unlocked' to verify.")
    print("====================================================")

if __name__ == "__main__":
    main()
