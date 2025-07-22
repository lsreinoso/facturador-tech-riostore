import os
import customtkinter as ctk
from PIL import Image
from tkinter import messagebox
from models import User
from gui.utils import make_window_responsive, ScrollableFrame

class LoginWindow:
    def __init__(self, master):
        # modo oscuro para login
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        # si no hay admin, creación
        if not User.exists_any():
            from gui.initial_admin import InitialAdminWindow
            InitialAdminWindow(master)
            return

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

        # Títulos
        ctk.CTkLabel(container,
                     text="Login - Tech RioStore",
                     font=("Arial", 30))\
            .grid(row=0, column=0, pady=(20,10))
        ctk.CTkLabel(container,
                     text="By Luis Enrique Reinoso Peñafiel",
                     font=("Arial", 18))\
            .grid(row=1, column=0, pady=(0,20))

        # Logo
        logo_path = os.path.join(os.path.dirname(__file__),
                                 os.pardir, "resources", "logo.png")
        img = Image.open(logo_path)
        self.logo_img = ctk.CTkImage(light_image=img,
                                     dark_image=img,
                                     size=(250,250))
        ctk.CTkLabel(container, image=self.logo_img, text="")\
            .grid(row=2, column=0, pady=(20,40))

        # Usuario (ancho fijo, centrado)
        self.username = ctk.CTkEntry(container,
                                     placeholder_text="Usuario",
                                     width=300)
        self.username.grid(row=3, column=0, pady=10)
        self.username.focus()
        self.username.bind("<Return>", lambda e: self.login())

        # Contraseña
        self.password = ctk.CTkEntry(container,
                                     placeholder_text="Contraseña",
                                     show="*",
                                     width=300)
        self.password.grid(row=4, column=0, pady=10)
        self.password.bind("<Return>", lambda e: self.login())

        # Botón
        ctk.CTkButton(container,
                      text="Iniciar sesión",
                      command=self.login)\
            .grid(row=5, column=0, pady=20)

    def login(self):
        user = User.authenticate(self.username.get(),
                                 self.password.get())
        if not user:
            messagebox.showerror("Error",
                                 "Usuario o contraseña incorrectos.")
            return
        # limpiar todo y abrir Dashboard
        for w in self.master.winfo_children():
            w.destroy()
        from gui.dashboard import DashboardWindow
        DashboardWindow(self.master, user)
