# gui/dashboard.py
import os
import ctypes
import customtkinter as ctk
from PIL import Image
from gui.login import LoginWindow

SW_MAXIMIZE = 3
def maximize_window(win):
    win.update_idletasks()
    hwnd = ctypes.windll.user32.GetParent(win.winfo_id())
    ctypes.windll.user32.ShowWindow(hwnd, SW_MAXIMIZE)

class DashboardWindow:
    def __init__(self, master, user):
        # modo oscuro y tema base
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        self.master = master
        self.user = user
        master.after(50, lambda: maximize_window(master))

        # contenedor principal con fondo oscuro
        self.frame = ctk.CTkFrame(master, corner_radius=0, fg_color="#1f1f1f")
        self.frame.pack(fill="both", expand=True)

        # --- Cabecera ---
        header = ctk.CTkFrame(self.frame, corner_radius=0, fg_color="#1f1f1f")
        header.pack(fill="x", pady=(20, 10))
        title = f"Bienvenido a Tech RioStore, {user['full_name']}"
        ctk.CTkLabel(
            header,
            text=title,
            font=("Arial", 28, "bold"),
            text_color="white"
        ).pack()

        # --- Logo debajo del título ---
        logo_path = os.path.join(
            os.path.dirname(__file__),
            os.pardir, "resources", "logo.png"
        )
        if os.path.exists(logo_path):
            img = Image.open(logo_path)
            logo_img = ctk.CTkImage(light_image=img, dark_image=img, size=(180, 180))
            ctk.CTkLabel(self.frame, image=logo_img, text="").pack(pady=(0, 20))

        # --- Botones de módulos en grid ---
        grid_frame = ctk.CTkFrame(self.frame, corner_radius=0, fg_color="#1f1f1f")
        grid_frame.pack(padx=60, pady=10)

        btns = []
        if user["role"] == "Administrador":
            btns.append(("Usuarios", self.open_users))
        btns.append(("Documentos", self.open_documents))   # <-- Botón solo admins
        btns += [
            ("Clientes",       self.open_clients),
            ("Inventario",     self.open_inventory),
            ("Proformas",      self.open_proformas),
            ("Notas de Venta", self.open_notas),
        ]

        # celeste suave → azul moderado
        accent       = ("#66CCFF", "#3399FF")
        hover_accent = ("#5BB8E6", "#2E86E0")

        for idx, (text, cmd) in enumerate(btns):
            r, c = divmod(idx, 3)
            btn = ctk.CTkButton(
                grid_frame,
                text=text,
                width=180, height=70,
                fg_color=accent,
                hover_color=hover_accent,
                text_color="white",
                font=("Arial", 14, "bold"),
                corner_radius=8,
                command=cmd
            )
            btn.grid(row=r, column=c, padx=20, pady=20)

        # --- Botón de Cerrar Sesión centrado abajo ---
        bottom = ctk.CTkFrame(self.frame, corner_radius=0, fg_color="#1f1f1f")
        bottom.pack(side="bottom", pady=30)
        ctk.CTkButton(
            bottom,
            text="Cerrar Sesión",
            width=220, height=50,
            fg_color="#B22222",    # rojo moderado
            hover_color="#8B0000", # rojo más intenso al pasar
            text_color="white",
            font=("Arial", 14, "bold"),
            corner_radius=8,
            command=self.logout
        ).pack()

    def open_users(self):
        self.frame.destroy()
        from gui.users import UsersWindow
        UsersWindow(self.master, self.user)

    def open_documents(self):
        self.frame.destroy()
        from gui.document import DocumentWindow
        DocumentWindow(self.master, self.user)

    def open_clients(self):
        self.frame.destroy()
        from gui.clients import ClientsWindow
        ClientsWindow(self.master, self.user)

    def open_inventory(self):
        self.frame.destroy()
        from gui.inventory import InventoryWindow
        InventoryWindow(self.master, self.user)

    def open_proformas(self):
        self.frame.destroy()
        from gui.proforma import ProformaWindow
        ProformaWindow(self.master, self.user)

    def open_notas(self):
        self.frame.destroy()
        from gui.nota_venta import NotaVentaWindow
        NotaVentaWindow(self.master, self.user)

    
    def logout(self):
        self.frame.destroy()
        LoginWindow(self.master)
