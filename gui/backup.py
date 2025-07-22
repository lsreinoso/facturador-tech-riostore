# gui/backup.py
import customtkinter as ctk
from tkinter import filedialog, messagebox
import shutil
import os
from gui.utils import maximize_window

class BackupWindow:
    def __init__(self, master, user):
        ctk.set_appearance_mode("Light")
        ctk.set_default_color_theme("dark-blue")
        self.master = master
        master.after(50, lambda: maximize_window(master))

        self.frame = ctk.CTkFrame(master, corner_radius=0)
        self.frame.pack(fill="both", expand=True)

        header = ctk.CTkFrame(self.frame)
        header.pack(fill="x", pady=10, padx=10)
        ctk.CTkButton(header, text="← Menú Principal", command=self._back).pack(side="left")
        ctk.CTkLabel(header, text="Respaldo / Restauración", font=("Arial",24)).pack(side="left", padx=20)

        # botones exportar/importar
        btf = ctk.CTkFrame(self.frame)
        btf.pack(pady=40)
        ctk.CTkButton(btf, text="Exportar Copia de Seguridad", width=200,
                      command=self._export).pack(pady=10)
        ctk.CTkButton(btf, text="Importar copia existente", width=200,
                      command=self._import).pack(pady=10)

    def _export(self):
        src = "data/riostore.db"
        dst = filedialog.asksaveasfilename(defaultextension=".db",
                                           filetypes=[("SQLite DB","*.db")])
        if not dst: return
        try:
            shutil.copy(src, dst)
            messagebox.showinfo("OK", f"Respaldo guardado en:\n{dst}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _import(self):
        src = filedialog.askopenfilename(filetypes=[("SQLite DB","*.db")])
        if not src: return
        try:
            shutil.copy(src, "data/riostore.db")
            messagebox.showinfo("OK","Base de datos restaurada. Reinicie la app.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _back(self):
        self.frame.destroy()
        from gui.dashboard import DashboardWindow
        DashboardWindow(self.master, {"role":"Administrador","full_name":"", "id":0})
