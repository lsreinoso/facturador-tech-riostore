# gui/inventory.py
import customtkinter as ctk
from tkinter import messagebox, ttk
import ctypes
from models import Product, db
from gui.utils import StockForm

SW_MAXIMIZE = 3
def maximize_window(win):
    win.update_idletasks()
    hwnd = ctypes.windll.user32.GetParent(win.winfo_id())
    ctypes.windll.user32.ShowWindow(hwnd, SW_MAXIMIZE)

class InventoryWindow:
    def __init__(self, master, current_user):
        # Tema y maximizado
        ctk.set_appearance_mode("Light")
        ctk.set_default_color_theme("dark-blue")
        self.master = master
        self.current_user = current_user
        master.after(50, lambda: maximize_window(master))

        # Contenedor principal
        self.frame = ctk.CTkFrame(master, corner_radius=0)
        self.frame.pack(fill="both", expand=True)

        # --- Subframes ---
        self.header_frame  = ctk.CTkFrame(self.frame)
        self.filter_frame  = ctk.CTkFrame(self.frame)
        self.search_frame  = ctk.CTkFrame(self.frame)
        self.table_frame   = ctk.CTkFrame(self.frame)
        self.actions_frame = ctk.CTkFrame(self.frame)
        self.form_frame    = ctk.CTkFrame(self.frame)  # oculto al inicio

        # 1) Header
        self.header_frame.pack(fill="x", pady=(10,0), padx=10)
        ctk.CTkButton(self.header_frame, text="← Menú Principal",
                      width=160, height=32,
                      command=self._back).pack(side="left")
        ctk.CTkLabel(self.header_frame, text="Inventario",
                     font=("Arial",24)).pack(side="left", padx=20)

        # 2) Filtro por categoría
        self.filter_frame.pack(fill="x", pady=10, padx=20)
        ctk.CTkLabel(self.filter_frame, text="Filtrar categoría:").pack(side="left")
        self.cat_var = ctk.StringVar()
        cats = ["Todos"] + Product.get_categories()
        self.cat_cb = ctk.CTkComboBox(self.filter_frame,
                                      values=cats,
                                      variable=self.cat_var,
                                      state="readonly",
                                      command=lambda _: self.load_products())
        self.cat_cb.set("Todos")
        self.cat_cb.pack(side="left", padx=(5,0))

        # 3) Búsqueda
        self.search_frame.pack(fill="x", pady=10, padx=20)
        self.search_var = ctk.StringVar()
        ctk.CTkEntry(self.search_frame,
                     placeholder_text="Buscar por nombre o código...",
                     textvariable=self.search_var)\
            .pack(side="left", fill="x", expand=True)
        ctk.CTkButton(self.search_frame, text="Buscar",
                      command=self.load_products)\
            .pack(side="left", padx=5)
        ctk.CTkButton(self.search_frame, text="Limpiar",
                      command=self._reset_filters)\
            .pack(side="left")

        # 4) Tabla (ocultando la columna id)
        self.table_frame.pack(fill="both", expand=True, pady=10, padx=20)
        cols = ("id","code","name","category","cost_price",
                "sell_price","type","stock","margin","margin_pct")
        display = ("code","name","category","cost_price",
                   "sell_price","type","stock","margin","margin_pct")
        headings = {
            "code":"Código","name":"Nombre","category":"Categoría",
            "cost_price":"Costo","sell_price":"Venta","type":"Tipo",
            "stock":"Stock","margin":"Ganancia","margin_pct":"Porcentaje"
        }
        self.tree = ttk.Treeview(self.table_frame,
                                 columns=cols,
                                 show="headings",
                                 displaycolumns=display)
        for c in cols:
            self.tree.heading(c,
                text=headings.get(c,""),
                command=(lambda _c=c: self.sort_by(_c, False))
            )
            self.tree.column(c, width=100, anchor="center")
        self.tree.tag_configure("out_of_stock", background="#FFCCCC")
        self.tree.tag_configure("low_stock", background="#FFFFCC")
        self.tree.pack(fill="both", expand=True)

        # 5) Botones
        self.actions_frame.pack(fill="x", pady=10, padx=20)
        ctk.CTkButton(self.actions_frame, text="Agregar Producto",
                      command=lambda: self._open_form(edit=False))\
            .pack(side="left")
        ctk.CTkButton(self.actions_frame, text="Editar Seleccionado",
                      command=lambda: self._open_form(edit=True))\
            .pack(side="left", padx=5)
        ctk.CTkButton(self.actions_frame, text="Eliminar Seleccionado",
                      command=self.delete_product)\
            .pack(side="left", padx=5)
        ctk.CTkButton(self.actions_frame, text="Ajustar Stock",
                      command=self.adjust_stock)\
            .pack(side="left", padx=5)
        if self.current_user["role"] == "Administrador":
            ctk.CTkButton(self.actions_frame, text="Eliminar Categoría",
                          command=self._delete_category)\
                .pack(side="left", padx=5)

        # carga inicial
        self.load_products()

    def load_products(self):
        for r in self.tree.get_children():
            self.tree.delete(r)
        term = self.search_var.get().strip()
        cat  = self.cat_var.get()
        if term:
            items = Product.search(term)
        elif cat and cat != "Todos":
            items = Product.by_category(cat)
        else:
            items = Product.all()
        for p in items:
            margin = p["sell_price"] - p["cost_price"]
            if p["type"] == "Servicio":
                pct = 100.0
                tag = ""
            else:
                pct = (margin / p["cost_price"] * 100) if p["cost_price"] else 0
                tag = ("out_of_stock" if p["stock"]==0
                       else "low_stock" if p["stock"]==1 else "")
            self.tree.insert("", "end", values=(
                p["id"], p["code"] or "", p["name"], p["category"] or "",
                p["cost_price"], p["sell_price"], p["type"], p["stock"],
                round(margin,2), f"{round(pct,2)}%"
            ), tags=(tag,))

    def _reset_filters(self):
        self.search_var.set("")
        self.cat_cb.set("Todos")
        self.load_products()

    def _open_form(self, edit=False):
        # determina si es edición y obtiene id
        self.edit_id = None
        if edit:
            sel = self.tree.selection()
            if not sel:
                return messagebox.showerror("Error","Seleccione un producto.")
            self.edit_id = self.tree.item(sel[0])["values"][0]

        # oculta los paneles principales
        for f in (self.header_frame, self.filter_frame,
                  self.search_frame, self.table_frame,
                  self.actions_frame):
            f.pack_forget()
        # muestra el formulario
        self.form_frame.pack(fill="both", expand=True,
                             pady=20, padx=40)
        # limpia y construye el form
        for w in self.form_frame.winfo_children():
            w.destroy()
        title = "Editar Producto" if self.edit_id else "Agregar Producto"
        ctk.CTkLabel(self.form_frame, text=title,
                     font=("Arial",24)).pack(pady=(0,20))

        # campos
        fields = [
            ("Código (opc.)",     "code"),
            ("Nombre",            "name"),
            ("Tipo (Producto/Servicio)", "type"),
            ("Categoría existente","category_cb"),
            ("Nueva categoría",   "category_new"),
            ("Costo",             "cost_price"),
            ("Venta",             "sell_price"),
            ("Stock",             "stock")
        ]
        cats = Product.get_categories()
        self.widgets = {}
        for lbl_text, key in fields:
            ctk.CTkLabel(self.form_frame,
                         text=lbl_text).pack(anchor="w", pady=5)
            if key == "type":
                cb = ctk.CTkComboBox(self.form_frame,
                                     values=["Producto","Servicio"],
                                     state="readonly")
                cb.set("Producto")
                cb.pack(fill="x")
                cb.bind("<<ComboboxSelected>>",
                        lambda e: self._on_type_change())
                self.widgets[key] = cb
            elif key == "category_cb":
                cb = ctk.CTkComboBox(self.form_frame,
                                     values=cats,
                                     state="readonly")
                cb.set(cats[0] if cats else "")
                cb.pack(fill="x")
                self.widgets[key] = cb
            elif key == "category_new":
                ent = ctk.CTkEntry(self.form_frame,
                                   placeholder_text="Dejar vacío para usar existente")
                ent.pack(fill="x")
                self.widgets[key] = ent
            else:
                ent = ctk.CTkEntry(self.form_frame)
                ent.pack(fill="x")
                self.widgets[key] = ent

        # precarga datos si edit
        if self.edit_id:
            p = Product.get(self.edit_id)
            self.widgets["code"].insert(0, p["code"] or "")
            self.widgets["name"].insert(0, p["name"])
            self.widgets["type"].set(p["type"])
            self.widgets["category_cb"].set(p["category"] or "")
            self.widgets["cost_price"].insert(0, str(p["cost_price"]))
            self.widgets["sell_price"].insert(0, str(p["sell_price"]))
            self.widgets["stock"].insert(0, str(p["stock"]))

        # ajustar visibilidad según tipo
        self._on_type_change()

        # ** NUEVA SECCIÓN ** deshabilitar stock si es edición y no Administrador
        if self.edit_id and self.current_user["role"] != "Administrador":
            stock_widget = self.widgets.get("stock")
            if stock_widget:
                stock_widget.configure(state="disabled")

        # botones Guardar/Cancelar
        btnf = ctk.CTkFrame(self.form_frame)
        btnf.pack(pady=20)
        ctk.CTkButton(btnf, text="Guardar",
                      command=self._save).pack(side="left", padx=10)
        ctk.CTkButton(btnf, text="Cancelar",
                      command=self._cancel).pack(side="left")

    def _on_type_change(self):
        is_serv = (self.widgets["type"].get() == "Servicio")
        for key in ("category_cb","category_new","cost_price","stock"):
            # encuentra todos los CTkLabel cuyo texto comienza con la clave
            for widget in self.form_frame.winfo_children():
                if (isinstance(widget, ctk.CTkLabel) and
                    widget.cget("text").lower().startswith(key.replace("_",""))):
                    if is_serv:
                        widget.pack_forget()
                    else:
                        widget.pack(anchor="w", pady=5)
            w = self.widgets.get(key)
            if w:
                if is_serv:
                    w.pack_forget()
                else:
                    w.pack(fill="x")

    def _save(self):
        d = {k: w.get() for k,w in self.widgets.items()}
        type_ = d["type"]
        # manejar categoría
        category = ""
        if type_ == "Producto":
            new_cat = d.pop("category_new").strip()
            old_cat = ""
            if self.edit_id:
                old_cat = Product.get(self.edit_id)["category"] or ""
            if new_cat:
                cats = Product.get_categories()
                if new_cat in cats and new_cat != old_cat:
                    return messagebox.showerror("Error","La categoría ya existe.")
                if old_cat:
                    db.execute("UPDATE products SET category=? WHERE category=?",
                               (new_cat, old_cat))
                category = new_cat
            else:
                category = d.pop("category_cb","")
        try:
            cost  = float(d["cost_price"]) if type_=="Producto" else 0.0
            price = float(d["sell_price"])
            stock = int(d["stock"])      if type_=="Producto" else 0
        except:
            return messagebox.showerror("Error","Datos numéricos inválidos.")
        code = d["code"] or None
        name = d["name"]

        if self.edit_id:
            Product.update(self.edit_id, code, name, category,
                           cost, price, type_, stock)
        else:
            Product.create(code, name, category,
                           cost, price, type_, stock)

        # refrescar categorías y tabla
        self.cat_cb.configure(values=["Todos"]+Product.get_categories())
        self._cancel()
        self._reset_filters()

    def _cancel(self):
        self.form_frame.pack_forget()
        self.header_frame.pack(fill="x", pady=(10,0), padx=10)
        self.filter_frame.pack(fill="x", pady=10, padx=20)
        self.search_frame.pack(fill="x", pady=10, padx=20)
        self.table_frame.pack(fill="both", expand=True, pady=10, padx=20)
        self.actions_frame.pack(fill="x", pady=10, padx=20)

    def delete_product(self):
        sel = self.tree.selection()
        if not sel:
            return messagebox.showerror("Error","Seleccione un producto.")
        pid = self.tree.item(sel[0])["values"][0]
        if self.current_user["role"]!="Administrador":
            return messagebox.showerror("Permiso","Solo Admin puede eliminar.")
        if not messagebox.askyesno("Confirmar","Eliminar?"):
            return
        Product.delete(pid)
        self.load_products()

    def adjust_stock(self):
        sel = self.tree.selection()
        if not sel:
            return messagebox.showerror("Error","Seleccione un producto.")
        pid = self.tree.item(sel[0])["values"][0]
        StockForm(self.master,
                  product_id=pid,
                  role=self.current_user["role"],
                  callback=self.load_products)

    def _delete_category(self):
        cat = self.cat_var.get()
        if cat=="Todos":
            return messagebox.showerror("Error","Seleccione categoría.")
        if not messagebox.askyesno("Confirmar",
                                   f"Eliminar categoría '{cat}'?"):
            return
        db.execute("UPDATE products SET category='' WHERE category=?", (cat,))
        self.cat_cb.configure(values=["Todos"]+Product.get_categories())
        self._reset_filters()

    def sort_by(self, col, descending):
        data = []
        for iid in self.tree.get_children():
            val = self.tree.set(iid, col).rstrip('%')
            try:
                key = float(val) if col not in ("name","category") else val[0].lower()
            except:
                key = val.lower()
            data.append((key, iid))
        data.sort(reverse=descending)
        for index, (_, iid) in enumerate(data):
            self.tree.move(iid, "", index)
        self.tree.heading(col, 
            command=lambda: self.sort_by(col, not descending))

    def _back(self):
        self.frame.destroy()
        from gui.dashboard import DashboardWindow
        DashboardWindow(self.master, self.current_user)
