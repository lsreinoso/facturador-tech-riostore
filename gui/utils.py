# gui/utils.py

import os
import customtkinter as ctk
import ctypes
from tkinter import messagebox
from pathlib import Path
from models import Product

# — Maximizar ventana en Windows —
SW_MAXIMIZE = 3
def maximize_window(win):
    win.update_idletasks()
    hwnd = ctypes.windll.user32.GetParent(win.winfo_id())
    ctypes.windll.user32.ShowWindow(hwnd, SW_MAXIMIZE)

# — Directorio de respaldo de PDFs —
_APPDATA = os.getenv("APPDATA") or str(Path.home())
BACKUP_DIR = Path(_APPDATA) / "pdf_backups"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

# — Helpers para hacer cualquier ventana “responsive” —
def make_window_responsive(win):
    """
    Activa redimensionado y configura grid para que el contenido escale.
    """
    win.resizable(True, True)
    win.grid_rowconfigure(0, weight=1)
    win.grid_columnconfigure(0, weight=1)

class ScrollableFrame(ctk.CTkScrollableFrame):
    """
    Frame con scroll vertical automático.
    No hace pack() internamente; el usuario debe grid() o pack() el frame.
    """
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        # Alias para compatibilidad con .scrollable_frame
        self.scrollable_frame = self

# -------------------------------------------------------------------
# ProductForm (sin cambios respecto a tu versión anterior)
# -------------------------------------------------------------------
class ProductForm:
    def __init__(self, master, callback, product_id=None, role="Administrador"):
        """
        master: ventana padre
        callback: función a llamar tras guardar
        product_id: si no es None, cargamos para edición
        role: "Administrador" o "Empleado"
        """
        self.master     = master
        self.callback   = callback
        self.product_id = product_id
        self.role       = role

        # --- Ventana ---
        self.win = ctk.CTkToplevel(master)
        self.win.title("Producto")
        make_window_responsive(self.win)
        self.win.after(50, lambda: maximize_window(self.win))
        self.win.grab_set()

        # --- Contenedor scrollable ---
        scroll = ScrollableFrame(self.win)
        container = scroll.scrollable_frame
        container.grid_columnconfigure(0, weight=1)

        # --- Construcción dinámica de campos ---
        fields = [
            ("Código (opc.)",      "code"),
            ("Nombre",             "name"),
            ("Tipo (Producto/Servicio)", "type"),
            ("Categoría existente","category_cb"),
            ("Nueva categoría",    "category_new"),
            ("Costo",              "cost_price"),
            ("Venta",              "sell_price"),
            ("Stock",              "stock")
        ]
        cats = Product.get_categories()
        self.labels  = {}
        self.widgets = {}

        row = 0
        title = "Editar Producto" if self.product_id else "Agregar Producto"
        ctk.CTkLabel(container, text=title, font=("Arial",24))\
            .grid(row=row, column=0, pady=(20,10), padx=20, sticky="n")
        row += 1

        for lbl_text, key in fields:
            # Label
            lbl = ctk.CTkLabel(container, text=lbl_text)
            lbl.grid(row=row, column=0, sticky="w", padx=20, pady=5)
            self.labels[key] = lbl
            row += 1

            # Widget
            if key == "type":
                cb = ctk.CTkComboBox(container,
                                     values=["Producto","Servicio"],
                                     state="readonly")
                cb.set("Producto")
                cb.grid(row=row, column=0, sticky="ew", padx=20)
                cb.bind("<<ComboboxSelected>>", lambda e: self._on_type_change())
                self.widgets[key] = cb

            elif key == "category_cb":
                cb = ctk.CTkComboBox(container,
                                     values=cats,
                                     state="readonly")
                if cats:
                    cb.set(cats[0])
                cb.grid(row=row, column=0, sticky="ew", padx=20)
                self.widgets[key] = cb

            elif key == "category_new":
                ent = ctk.CTkEntry(container,
                                   placeholder_text="Dejar vacío para usar existente")
                ent.grid(row=row, column=0, sticky="ew", padx=20)
                self.widgets[key] = ent

            else:
                ent = ctk.CTkEntry(container)
                ent.grid(row=row, column=0, sticky="ew", padx=20)
                self.widgets[key] = ent

            row += 1

        # --- Precarga para edición ---
        if self.product_id:
            p = Product.get(self.product_id)
            for k, w in self.widgets.items():
                if k in ("category_cb","type"):
                    w.set(p[k] or "")
                else:
                    w.insert(0, str(p.get(k, "") or ""))

        # --- Si no es Admin en edición, bloqueo stock ---
        if self.product_id and self.role != "Administrador":
            stock_w = self.widgets.get("stock")
            if stock_w:
                stock_w.configure(state="disabled")

        # --- Ajuste inicial según tipo ---
        self._on_type_change()

        # --- Botones al final ---
        btnf = ctk.CTkFrame(container)
        btnf.grid(row=row, column=0, pady=20)
        ctk.CTkButton(btnf, text="Guardar", command=self.save)\
            .pack(side="left", padx=10)
        ctk.CTkButton(btnf, text="Cancelar", command=self.win.destroy)\
            .pack(side="left")

    def _on_type_change(self):
        """Oculta o muestra campos según tipo = Servicio o Producto."""
        is_serv = (self.widgets["type"].get() == "Servicio")
        for key in ("category_cb", "category_new", "cost_price", "stock"):
            lbl = self.labels[key]
            w   = self.widgets[key]
            if is_serv:
                lbl.grid_remove()
                w.grid_remove()
            else:
                lbl.grid()
                w.grid()

    def save(self):
        """Valida, crea/actualiza, refresca y cierra."""
        data = {
            k: (w.get().strip() if isinstance(w, ctk.CTkEntry) else w.get())
            for k, w in self.widgets.items()
        }

        # Validaciones básicas
        if not data["name"]:
            return messagebox.showerror("Error", "El nombre es obligatorio.")
        try:
            sp = float(data["sell_price"])
        except:
            return messagebox.showerror("Error", "Precio de venta inválido.")

        # Si es servicio, forzar valores
        if data["type"] == "Servicio":
            cp = 0.0; st = 0; category = ""
        else:
            try:
                cp = float(data["cost_price"])
                st = int(data["stock"])
            except:
                return messagebox.showerror("Error", "Costo o stock inválido.")
            new_cat = data.pop("category_new", "").strip()
            category = new_cat or data.get("category_cb", "").strip()

        code  = data.get("code") or None
        name  = data.get("name")
        type_ = data.get("type")

        # En edición, verificar permisos de stock
        if self.product_id:
            original = Product.get(self.product_id)
            old_st   = original["stock"]
            if self.role != "Administrador" and st < old_st:
                return messagebox.showerror(
                    "Permiso denegado",
                    "Solo Administradores pueden disminuir stock al editar."
                )
            Product.update(self.product_id, code, name, category,
                           cp, sp, type_, st)
        else:
            Product.create(code, name, category, cp, sp, type_, st)

        # Refrescar lista y cerrar
        self.callback()
        self.win.destroy()

# -------------------------------------------------------------------
# StockForm corregido para que no salga en blanco y aparezca todo
# -------------------------------------------------------------------
class StockForm:
    def __init__(self, master, product_id, role, callback):
        """
        master: ventana padre
        product_id: id del producto a ajustar
        role: rol del usuario ("Administrador"/"Empleado")
        callback: función a llamar tras aplicar
        """
        self.master     = master
        self.product_id = product_id
        self.role       = role
        self.callback   = callback

        # --- Ventana ---
        self.win = ctk.CTkToplevel(master)
        self.win.title("Ajustar Stock")

        # Tamaño fijo y centrado
        self.win.geometry("350x260")
        self.win.resizable(False, False)
        self.win.update_idletasks()
        w = self.win.winfo_width()
        h = self.win.winfo_height()
        x = master.winfo_x() + (master.winfo_width() - w)//2
        y = master.winfo_y() + (master.winfo_height() - h)//2
        self.win.geometry(f"+{x}+{y}")

        # --- Contenedor principal ---
        container = ctk.CTkFrame(self.win, corner_radius=0)
        container.pack(fill="both", expand=True, padx=20, pady=20)

        # Obtengo datos del producto
        p = Product.get(product_id)

        # Etiquetas informativas centradas y en negrita
        lbl_producto = ctk.CTkLabel(container, text="Producto:", font=("Arial", 12, "bold"))
        lbl_producto.pack(pady=(0,5))
        ctk.CTkLabel(container, text=p["name"], font=("Arial", 12)).pack(pady=(0,10))

        lbl_stock = ctk.CTkLabel(container, text=f"Stock actual: {p['stock']}", font=("Arial", 12, "bold"))
        lbl_stock.pack(pady=(0,10))

        lbl_cant = ctk.CTkLabel(container, text="Cantidad (+ ingreso, - egreso):", font=("Arial", 12, "bold"))
        lbl_cant.pack(pady=(0,5))

        # Campo de entrada visible y con tamaño adecuado
        self.qty = ctk.CTkEntry(container, width=120, height=30, font=("Arial", 12))
        self.qty.pack(pady=(0,15))

        # Botones al pie
        btnf = ctk.CTkFrame(container)
        btnf.pack()
        ctk.CTkButton(btnf, text="Aplicar", width=80, command=self.apply).pack(side="left", padx=5)
        ctk.CTkButton(btnf, text="Cancelar", width=80, command=self.win.destroy).pack(side="left")

    def apply(self):
        """Valida, ajusta stock, refresca y cierra."""
        try:
            delta = int(self.qty.get())
        except:
            return messagebox.showerror("Error", "Cantidad inválida.")
        if self.role != "Administrador" and delta < 0:
            return messagebox.showerror(
                "Permiso denegado",
                "Solo Administradores pueden egresar stock."
            )
        Product.adjust_stock(self.product_id, delta)
        self.callback()
        self.win.destroy()
