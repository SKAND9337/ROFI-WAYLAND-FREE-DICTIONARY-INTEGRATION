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
Search History is saved at `~/.local/share/free-dictionary-rofi/history.txt`
Recommended to symlink somewhere easier to access, it also appears in rofi when free dictionary script is ran.

----------------------------------------------
Use, modify, republish to your heart's content
----------------------------------------------

PS: rewrite in rust for memory safety xd
