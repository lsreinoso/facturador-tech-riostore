import customtkinter as ctk
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
