import customtkinter as ctk

# ——— Monkey‑patch para colorear botones según su texto ———
# Guardamos la implementación original de CTkButton
_OrigButton = ctk.CTkButton

# Creamos una subclase que ajusta colores si el texto es "Guardar" o "Cancelar"
class ColorCTkButton(_OrigButton):
    def __init__(self, master=None, *args, text="", **kwargs):
        if text == "Guardar":
            # Verde estilo Bootstrap
            kwargs.setdefault("fg_color", "#28a745")
            kwargs.setdefault("hover_color", "#218838")
        elif text == "Cancelar":
            # Rojo estilo Bootstrap
            kwargs.setdefault("fg_color", "#dc3545")
            kwargs.setdefault("hover_color", "#c82333")
        super().__init__(master, *args, text=text, **kwargs)

# Reemplazamos CTkButton globalmente
ctk.CTkButton = ColorCTkButton
# —————————————————————————————————————————————————————

from gui.login import LoginWindow

def main():
    # Tema
    ctk.set_default_color_theme("dark-blue")
    ctk.set_appearance_mode("Light")

    # Ventana principal
    root = ctk.CTk()
    root.title("Tech RioStore")

    # — Forzar maximizada —
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    root.geometry(f"{sw}x{sh}+0+0")
    try:
        root.state("zoomed")
    except:
        root.attributes("-zoomed", True)

    # — Escalado basado en DPI de la pantalla —
    dpi = root.winfo_fpixels('1i')                # píxeles por pulgada
    scale = dpi / 96                              # factor de Windows (96 DPI = 1×)
    ctk.set_widget_scaling(scale)
    ctk.set_window_scaling(scale)

    # Iniciar flujo
    LoginWindow(root)
    root.mainloop()

if __name__ == "__main__":
    main()


