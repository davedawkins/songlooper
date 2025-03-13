import tkinter as tk
from app import GuitarPracticeApp

def main():
    root = tk.Tk()
    app = GuitarPracticeApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()
