from tkinterdnd2 import TkinterDnD
from modules.ui import SoundboardApp

if __name__ == "__main__":
    app = SoundboardApp(root_class=TkinterDnD.Tk)
    app.run()