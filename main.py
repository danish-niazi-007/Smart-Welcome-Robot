"""
main.py - AI Exhibition Smart Greeter
======================================
Run: python main.py
"""

import customtkinter as ctk
from robot_ui import RobotExhibitionApp

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

def main():
    print("=" * 60)
    print("   AI EXHIBITION - SMART GREETER BOT")
    print("=" * 60)
    print("  - Same visitor ko sirf ONCE greet karega")
    print("  - Hat ke wapas aane par dobara greet hoga")
    print("  - Female detection improved")
    print("  - Press Q in camera window to hide camera")
    print("=" * 60)
    root = ctk.CTk()
    app  = RobotExhibitionApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
