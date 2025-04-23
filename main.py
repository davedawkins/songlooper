import tkinter as tk
from app import GuitarPracticeApp

    
def main():
    root = tk.Tk()
    app = GuitarPracticeApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)

    def bring_to_front():
        root.lift()
        root.attributes('-topmost', True)
        root.attributes('-topmost', False)
        root.focus_force()


    root.after(10, lambda: bring_to_front())
    root.mainloop()

if __name__ == "__main__":
    main()
