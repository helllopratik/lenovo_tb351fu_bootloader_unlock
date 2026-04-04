# Lenovo Tab Plus (TB351FU) One-Click Bootloader Unlocker
    An automated tool to "Force Unlock" the bootloader on the Lenovo TB351FU (Helio G99 / MT6789) by bypassing the hardware-backed RSA signature check.

## 💡 The Logic
    Modern Lenovo tablets use **MediaTek SEJ (Security Engine JTAG)** logic. The bootloader verifies the lock state using a hardware-encrypted hash unique to each chip. Standard Fastboot commands often fail because they require a signed
    `sn.img` from Lenovo's portal, which is frequently unavailable or mismatched.
  
    This tool uses a **Two-Stage Hybrid Bypass**:
    1. **Stage 1 (Generation)**: Uses `mtkclient` and the device's own HACC (Hardware Accelerator) to generate a hardware-unique, signed unlock token.
2. **Stage 2 (Flash)**: Automatically uses `SP Flash Tool V6` to flash that token to the physical UFS `unlock` partition.

   ## ⚠️ Requirements
   To avoid copyright issues, this repository does **not** include proprietary firmware files. You must provide the following files from your official Lenovo stock ROM:

   Place these in the `assets/` folder:
   - `da.auth` (Secure Authentication file)
   - `DA_BR.bin` (Download Agent)
   - `MT6789_Android_scatter.xml` (The scatter map)
   - `flash.xml` (Flashing manifest)
 
  ## 🚀 Usage
  
  1. **Install Dependencies**:
     sudo apt update && sudo apt install python3-pip python3-cryptography libusb-1.0-0
     sudo systemctl stop ModemManager
  
  2. **Run the Unlocker**:
     sudo python3 one_click_unlock.py

  
  3. **Follow On-Screen Instructions**:
       - The script will guide you through the **BROM Handshake** (Hold Vol Up + Vol Down while plugging in USB).
       - It will pause between stages to allow a device reset.
    
  ## 🛠 Hardware Shortcuts
    - **BROM Mode**: Power Off -> Hold Vol Up + Vol Down + Plug USB.
    - **Force Reset**: Hold Power + Vol Down for 25 seconds.
    - **Fastboot**: Power Off -> Hold Vol Down + Power.

 ## ⚖️ Disclaimer
 *Relocking/Unlocking bootloaders involves low-level partition writes. I am not responsible for bricked devices. Always ensure you have a backup of your `nvram` and `proinfo` partitions.*

 ---
 **Developed by helllopratik **
Special thanks to the `mtkclient` project for the BROM exploit logic.
