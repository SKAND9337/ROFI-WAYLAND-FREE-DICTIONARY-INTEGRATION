# ROFI-FREE-DICTIONARY-INTEGRATION
NOTE: Collaborative vibe-coding effort between ChatGPT and Gemini
-----------------------------------------------------------------

Integrates Free Dictionary search in rofi(-wayland) using python accessible through preferred keybind.
[There's a second version that integrates Urban Dictionary API](https://github.com/SKAND9337/ROFI-WAYLAND-URBAN-DICTIONARY-INTEGRATION/tree/main)

## How To Use:
1. Install dependencies:
      `rofi-wayland`, `python-requests`, `python`
      > 1.1. On ARCH LINUX (and based) systems:
      `sudo pacman -S python-requests rofi python`
   
2. Download and place the script as following:
      `~/.local/bin/free-dictionary-rofi.py`
      > Can be downloaded from the RELEASES section or download zip from the uploaded `free-dictionary-rofi` file in this repo.
   
3. Make executable:
      `chmod +x .local/bin/free-dictionary-rofi.py`
   
4. Add a preferred launch keybind
      > 4.1. I'm on Hyprland (0.55) so for me (lua) syntax would be:
   `hl.bind(mainMod .. " + CTRL + U", hl.dsp.exec_cmd("~/.local/bin/free-dictionary-rofi.py"))`

      > This uses SUPER+CTRL+U to open the search plugin, change as necessary
   
5. Enjoy

----------------------------------------------------------------
## IMPORTANT: 
The final look depends heavily on noctalia color scheme!!
If it doesn't work due to theme errors, disable the shown block by commenting it out:
<img width="1761" height="370" alt="image" src="https://github.com/user-attachments/assets/d0f9355b-7133-44b6-a72a-48f0787f1c2c" />

----------------------------------------------------------------
Search History is saved at `~/.local/share/free-dictionary-rofi/history.txt`.

If Free Dictionary API fails, it falls back to Wikitionary.

Recommended to symlink somewhere easier to access, it also appears in rofi when free dictionary script is ran.

----------------------------------------------
Use, modify, republish to your heart's content
----------------------------------------------

PS: rewrite in rust for memory safety xd
