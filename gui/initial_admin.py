import os
import customtkinter as ctk
from PIL import Image
from tkinter import messagebox
from models import User
from gui.utils import make_window_responsive, ScrollableFrame
from gui.login import LoginWindow

class InitialAdminWindow:
    def __init__(self, master):
        # modo oscuro para creación de admin
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        self.master = master
        make_window_responsive(self.master)
        # configurar grid de la ventana
        self.master.grid_rowconfigure(0, weight=1)
        self.master.grid_columnconfigure(0, weight=1)

        # contenedor scrollable por grid
        scroll = ScrollableFrame(self.master)
        scroll.grid(row=0, column=0, sticky="nsew")
        container = scroll.scrollable_frame
        container.grid_columnconfigure(0, weight=1)

        # Logo centrado
        logo_path = os.path.join(os.path.dirname(__file__),
                                 os.pardir, "resources", "logo.png")
        img = Image.open(logo_path)
        logo_img = ctk.CTkImage(light_image=img,
                                dark_image=img,
                                size=(200,200))
        ctk.CTkLabel(container, image=logo_img, text="")\
            .grid(row=0, column=0, pady=(40,20))

        # Título
        ctk.CTkLabel(container,
                     text="Configurar primer usuario administrador",
                     font=("Arial", 24))\
            .grid(row=1, column=0, pady=(0,20))

        # Campos (ancho fijo 300, centrados)
        self.fullname = ctk.CTkEntry(container,
                                     placeholder_text="Nombre completo",
                                     width=300)
        self.fullname.grid(row=2, column=0, pady=5)

        self.username = ctk.CTkEntry(container,
                                     placeholder_text="Usuario",
                                     width=300)
        self.username.grid(row=3, column=0, pady=5)

        self.pw1 = ctk.CTkEntry(container,
                                placeholder_text="Contraseña",
                                show="*",
                                width=300)
        self.pw1.grid(row=4, column=0, pady=5)

        self.pw2 = ctk.CTkEntry(container,
                                placeholder_text="Confirmar contraseña",
                                show="*",
                                width=300)
        self.pw2.grid(row=5, column=0, pady=5)
        self.pw2.bind("<Return>", lambda e: self.create_admin())

        # Botón
        ctk.CTkButton(container,
                      text="Crear Administrador",
                      command=self.create_admin)\
            .grid(row=6, column=0, pady=20)

        # Pie de página
        ctk.CTkLabel(container,
                     text="By Luis Enrique Reinoso Peñafiel",
                     font=("Arial", 12))\
            .grid(row=7, column=0, pady=(0,20))

    def create_admin(self):
        fullname = self.fullname.get().strip()
        username = self.username.get().strip()
        p1 = self.pw1.get()
        p2 = self.pw2.get()

        if not fullname or not username or not p1:
            messagebox.showerror("Error", "Todos los campos son obligatorios.")
            return
        if p1 != p2:
            messagebox.showerror("Error", "Las contraseñas no coinciden.")
            return

        User.create(fullname, username, p1, role="Administrador")
        messagebox.showinfo("Listo", "Administrador creado.")

        # limpiar todo y mostrar login correctamente
        for w in self.master.winfo_children():
            w.destroy()
        LoginWindow(self.master)
