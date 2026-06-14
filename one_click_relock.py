#!/usr/bin/env python3
import os
import subprocess
import sys
import xml.etree.ElementTree as ET

def run_cmd(cmd, cwd=None):
    print(f"\n[EXEC] {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=cwd)

def patch_scatter_for_relock(scatter_path, token_path):
    print(f"Surgically patching scatter file: {scatter_path}")
    tree = ET.parse(scatter_path)
    root = tree.getroot()
    
    # Use only the filename for the scatter XML to avoid SP Tool path bugs
    token_filename = os.path.basename(token_path)
    
    targets = ["seccfg", "unlock"]
    found_partitions = []

    for partition in root.findall(".//partition_index"):
        p_name = partition.find("partition_name").text
        is_dl = partition.find("is_download")
        f_name = partition.find("file_name")
        
        if p_name in targets:
            is_dl.text = "true"
            f_name.text = token_filename # Relative to scatter file
            found_partitions.append(p_name)
            print(f"  [+] Enabled partition: {p_name} -> {token_filename}")
        else:
            is_dl.text = "false"
    
    tree.write(scatter_path, encoding="utf-8", xml_declaration=True)
    return list(set(found_partitions))

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.join(base_dir, "assets")
    # We use a distinct name for the relock token to avoid confusion with the unlock token
    token_path = os.path.join(assets_dir, "generated_relock_token.bin")
    mtk_dir = os.path.join(base_dir, "mtkclient")
    spflash_dir = os.path.join(base_dir, "spflash")
    scatter_path = os.path.join(assets_dir, "MT6789_Android_scatter.xml")
    flash_xml_path = os.path.join(assets_dir, "flash.xml")
    da_path = os.path.join(assets_dir, "da.auth")

    print("====================================================")
    print("   Lenovo TB351FU One-Click ADVANCED Relocker")
    print("   (Data-Preserving Relock Mechanism)")
    print("====================================================")
    
    if os.geteuid() != 0:
        print("Error: This tool must be run with sudo.")
        sys.exit(1)

    if not os.path.exists(scatter_path):
        print(f"Error: assets/MT6789_Android_scatter.xml not found!")
        sys.exit(1)

    # Step 1: Generate the unique relock token
    print("\nSTAGE 1: Generating Unique Hardware Relock Token...")
    print("Hold VOL UP + and plug in USB.")
    
    # Use 'lock' flag instead of 'unlock'
    cmd_gen = [
        sys.executable, "mtk.py", "da", "seccfg", "lock",
        "--loader", os.path.join(assets_dir, "DA_BR.bin"),
        "--auth", da_path,
        "--preloader", os.path.join(assets_dir, "DA_BR.bin")
    ]
    
    # Patch MTKClient dynamically to save to our absolute token_path
    # We use a broad regex to catch any previous absolute paths or default filenames
    for patch_file in [
        os.path.join(mtk_dir, "mtkclient", "Library", "DA", "xmlflash", "extension", "v6.py"),
        os.path.join(mtk_dir, "mtkclient", "Library", "DA", "xflash", "extension", "xflash.py")
    ]:
        if os.path.exists(patch_file):
            with open(patch_file, "r") as f:
                content = f.read()
            import re
            # Match open("...", "wb").write(writedata) where ... ends with .bin
            content = re.sub(r'open\("[^"]+?\.bin", "wb"\)\.write\(writedata\)', 
                             f'open("{token_path}", "wb").write(writedata)', content)
            with open(patch_file, "w") as f:
                f.write(content)

    run_cmd(cmd_gen, cwd=mtk_dir)

    if not os.path.exists(token_path):
        print(f"\nError: Relock Token file not found at {token_path}")
        print("Check if mtkclient succeeded in writing the token.")
        sys.exit(1)

    # Step 2: Patch the scatter file to point to the relock token
    patch_scatter_for_relock(scatter_path, token_path)

    # Step 3: Flash the relock token
    print("\nSTAGE 2: Flashing Hardware-Signed Relock Tokens...")
    print("1. UNPLUG the tablet. 2. Hold VOL UP and plug in.")
    input("Press Enter when ready to flash...")

    # We use absolute paths for the XML files themselves
    cmd_flash = [
        "/bin/sh", "./SPFlashToolV6.sh", 
        "-c", "download", 
        "-f", flash_xml_path,
        "-a", da_path
    ]
    run_cmd(cmd_flash, cwd=spflash_dir)

    print("\n====================================================")
    print("   PROCESS COMPLETE! DEVICE SHOULD BE RELOCKED.")
    print("   Userdata has NOT been touched.")
    print("====================================================")

if __name__ == "__main__":
    main()
