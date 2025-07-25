import os
import platform
import shutil
import tempfile
import threading
import time

import customtkinter as ctk
from reportlab.lib.utils import simpleSplit
from tkinter import messagebox, ttk, filedialog
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch


from models import Document, DocumentItem, Product, Client
from gui.utils import maximize_window
from paths import get_pdf_backup_dir

# — Datos de la empresa (idénticos a nota_venta.py) —
LOGO_PATH      = os.path.join(os.path.dirname(__file__), os.pardir, "resources", "logo2.png")
BUSINESS_NAME  = "Tech RioStore"
OWNER_NAME     = "Luis Enrique Reinoso Peñafiel"
ADDRESS_LINE_1 = "Mayor Ruiz 28-33 y Venezuela"
ADDRESS_LINE_2 = "Riobamba – Chimborazo – Ecuador"
RUC            = "RUC: 0603918426001"
PHONE          = "0997927337 / 0984616768"
EMAIL          = "luis_enrique_reinoso@hotmail.com"
FACEBOOK       = "facebook.com/TechRioStore"
ADDITIONAL_TEXT = "Contribuyente Negocio Popular - Régimen RIMPE"

PDF_BACKUP_DIR = get_pdf_backup_dir()
os.makedirs(PDF_BACKUP_DIR, exist_ok=True)

class ProformaWindow:
    def __init__(self, master, user):
        ctk.set_appearance_mode("Light")
        ctk.set_default_color_theme("blue")
        # —— SECCIÓN ADICIONAL: campos "Información Adicional" y "Método de pago" ——
        self.additional_info = ""        # para el PDF
        self.payment_method  = ""        # para el PDF

        self.master = master
        self.user   = user
        master.after(50, lambda: maximize_window(master))

        self.frame       = ctk.CTkFrame(master, corner_radius=0)
        self.frame.pack(fill="both", expand=True)

        self.header      = ctk.CTkFrame(self.frame)
        self.details     = ctk.CTkFrame(self.frame)
        self.table_frame = ctk.CTkFrame(self.frame)
        self.linef       = ctk.CTkFrame(self.frame)
        self.botf        = ctk.CTkFrame(self.frame)
        self.actf        = ctk.CTkFrame(self.frame)

        self._build_header()
        self._build_details()
        self._build_table()
        self._build_line_buttons()
        self._build_bottom()
        self._build_extra()     # <–– sólo **una** vez
        self._build_actions()

        self.items = []
        self._recalc_total()

    def _build_header(self):
        self.header.pack(fill="x", pady=10, padx=10)
        ctk.CTkButton(self.header, text="← Menú Principal", width=140,
                      command=self._back).pack(side="left")
        ctk.CTkLabel(self.header, text="Proforma", font=("Arial", 24))\
            .pack(side="left", padx=20)

    def _build_details(self):
        self.details.pack(fill="x", pady=5, padx=20)
        # ACTUALIZAR FECHA CADA VEZ QUE SE MUESTRE LA PANTALLA
        self._update_date()
        ctk.CTkLabel(self.details, text=f"Fecha: {self.date_str}")\
            .grid(row=0, column=0, sticky="w", pady=5)
        ctk.CTkLabel(self.details, text="Cliente:")\
            .grid(row=0, column=1, padx=(20,5))
        self._load_clients_list()
        
        # Frame para cliente con dropdown
        client_frame = ctk.CTkFrame(self.details)
        client_frame.grid(row=0, column=2, sticky="ew")
        
        # Entry de búsqueda de clientes
        self.client_search = ctk.CTkEntry(client_frame, placeholder_text="Buscar cliente...")
        self.client_search.pack(side="left", fill="x", expand=True)
        self.client_search.bind("<KeyRelease>", self._filter_clients)
        
        # Botón flecha para mostrar/ocultar lista
        self.client_dropdown_btn = ctk.CTkButton(
            client_frame, text="▼", width=30,
            command=self._toggle_client_dropdown
        )
        self.client_dropdown_btn.pack(side="right")
        
        ctk.CTkButton(self.details, text="+", width=30,
                      command=self._add_client_inline)\
            .grid(row=0, column=3, padx=5)
        
        # Frame para la lista desplegable de clientes
        self.client_dropdown_frame = ctk.CTkFrame(self.details)
        
        # Listbox para resultados de búsqueda de clientes con scroll
        self.client_listbox = ttk.Treeview(self.client_dropdown_frame, show="tree", height=6)
        self.client_listbox.pack(side="left", fill="both", expand=True)
        self.client_listbox.bind("<ButtonRelease-1>", self._select_client_from_search)  # CAMBIO: UN SOLO CLICK
        
        # Scrollbar para clientes
        client_scrollbar = ttk.Scrollbar(self.client_dropdown_frame, orient="vertical", command=self.client_listbox.yview)
        client_scrollbar.pack(side="right", fill="y")
        self.client_listbox.configure(yscrollcommand=client_scrollbar.set)
        
        self._populate_client_list()
        self.client_dropdown_visible = False

    def _update_date(self):
        """Actualizar la fecha y hora actual"""
        self.date_str = datetime.now().strftime("%d/%m/%Y/%H:%M")

    def _toggle_client_dropdown(self):
        """Mostrar/ocultar dropdown de clientes"""
        if self.client_dropdown_visible:
            self.client_dropdown_frame.grid_forget()
            self.client_dropdown_btn.configure(text="▼", fg_color=["#3a7ebf", "#1f538d"])  # Color normal
            self.client_dropdown_visible = False
        else:
            self.client_dropdown_frame.grid(row=1, column=2, sticky="ew", pady=5)
            self.client_dropdown_btn.configure(text="▲", fg_color="red")  # CAMBIO: Color rojo cuando apunta arriba
            self.client_dropdown_visible = True
            self._populate_client_list()

    def _load_clients_list(self):
        self.client_objs = Client.all()
        self.client_values = [
            f"{c['full_name']} ({c['cedula'] or '-'})"
            for c in self.client_objs
        ]
        self.client_map = {}
        for i, client in enumerate(self.client_objs):
            display_text = self.client_values[i]
            self.client_map[display_text] = client

    def _populate_client_list(self):
        """Poblar lista con todos los clientes"""
        for item in self.client_listbox.get_children():
            self.client_listbox.delete(item)
        for display_text in self.client_values:
            self.client_listbox.insert("", "end", text=display_text)

    def _filter_clients(self, event=None):
        """Filtrar clientes por búsqueda"""
        if not self.client_dropdown_visible:
            return
            
        search_term = self.client_search.get().lower()
        
        # Limpiar listbox
        for item in self.client_listbox.get_children():
            self.client_listbox.delete(item)
        
        # Filtrar y mostrar coincidencias
        for display_text, client in self.client_map.items():
            nombre = client['full_name'].lower()
            cedula = (client['cedula'] or '').lower()
            if (search_term in nombre or 
                search_term in cedula or 
                search_term == ''):
                self.client_listbox.insert("", "end", text=display_text)

    def _select_client_from_search(self, event=None):
        """Seleccionar cliente de la lista de búsqueda con un solo click"""
        selection = self.client_listbox.selection()
        if selection:
            display_text = self.client_listbox.item(selection[0])['text']
            self.client_search.delete(0, 'end')
            self.client_search.insert(0, display_text)
            # Contraer dropdown automáticamente
            self._toggle_client_dropdown()

    def _build_table(self):
        self.table_frame.pack(fill="both", expand=True, pady=10, padx=20)
        cols = ("codigo","producto","cantidad","unit_price","subtotal")
        self.tree = ttk.Treeview(self.table_frame, columns=cols, show="headings")
        headers = ["Código", "Producto", "Cantidad", "P. Unit.", "Subtotal"]
        for col, header in zip(cols, headers):
            self.tree.heading(col, text=header)
            if col == "codigo":
                self.tree.column(col, anchor="center", width=80)
            elif col == "producto":
                self.tree.column(col, anchor="w", width=200)
            else:
                self.tree.column(col, anchor="center", width=100)
        self.tree.pack(fill="both", expand=True, side="left")
        vs = ttk.Scrollbar(self.table_frame, orient="vertical",
                           command=self.tree.yview)
        vs.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=vs.set)

    def _build_line_buttons(self):
        self.linef.pack(fill="x", pady=5, padx=20)
        ctk.CTkButton(self.linef, text="Agregar Ítem",
                      command=self._add_item_inline).pack(side="left")
        ctk.CTkButton(self.linef, text="Editar Ítem",
                      command=self._edit_item_inline).pack(side="left", padx=10)
        ctk.CTkButton(self.linef, text="Quitar Ítem",
                      command=self._remove_item).pack(side="left", padx=10)

    def _build_bottom(self):
        self.botf.pack(fill="x", pady=10, padx=20)
        ctk.CTkLabel(self.botf, text="Descuento:").pack(side="left")
        self.disc_e = ctk.CTkEntry(self.botf, width=80)
        self.disc_e.insert(0, "0")
        self.disc_e.pack(side="left", padx=(5,20))
        ctk.CTkLabel(self.botf, text="Total:").pack(side="left")
        self.total_lbl = ctk.CTkLabel(self.botf, text="0.00")
        self.total_lbl.pack(side="left", padx=5)
        self.disc_e.bind("<KeyRelease>", lambda e: self._recalc_total())

    def _build_extra(self):
        """Frame con Información Adicional y Método de pago."""
        self.extraf = ctk.CTkFrame(self.frame)
        self.extraf.pack(fill="x", pady=5, padx=20)
        
        # 1) Información adicional
        ctk.CTkLabel(self.extraf, text="Información Adicional:", font=("Helvetica-Bold", 12)).pack(anchor="w")
        self.additional_e = ctk.CTkEntry(self.extraf)
        self.additional_e.pack(fill="x", pady=(0,10))
        
        # 2) Método de pago
        row = ctk.CTkFrame(self.extraf)
        row.pack(fill="x", pady=(0,10))
        ctk.CTkLabel(row, text="Método de pago:").pack(side="left")
        self.pay_cb = ctk.CTkComboBox(
            row,
            values=["Efectivo","Transferencia","Tarjeta de Crédito","Otro"],
            state="readonly",
            command=lambda *_: self._on_pay_method()
        )
        self.pay_cb.pack(side="left", padx=(5,0))
        
        # ComboBox para tipo de tarjeta de crédito
        self.credit_type_cb = ctk.CTkComboBox(
            row,
            values=["Corriente","Diferido 3 meses","Diferido 6 meses","Diferido 12 meses","Diferido 24 meses"],
            state="readonly",
            width=150
        )
        self.credit_type_cb.pack(side="left", padx=(5,0))
        self.credit_type_cb.pack_forget()  # Ocultar inicialmente
        
        # Entrada para "Otro"
        self.other_pay = ctk.CTkEntry(self.extraf, placeholder_text="Describe otro método")
        self.other_pay.pack_forget()

    def _on_pay_method(self):
        """Muestra/oculta campos según método de pago."""
        metodo = self.pay_cb.get()
        
        # Ocultar todos los campos extra primero
        self.other_pay.pack_forget()
        self.credit_type_cb.pack_forget()
        
        if metodo == "Otro":
            self.other_pay.pack(fill="x", pady=(0,10))
        elif metodo == "Tarjeta de Crédito":
            # Mostrar el ComboBox de tipo de tarjeta en la misma fila
            self.credit_type_cb.pack(side="left", padx=(5,0))
            self.credit_type_cb.set("Corriente")  # Valor por defecto

    def _build_actions(self):
        self.actf.pack(pady=20)
        # CAMBIO: Botón con hover verde
        self.save_pdf_btn = ctk.CTkButton(
            self.actf, 
            text="Guardar PDF",
            command=self._save_pdf,
            hover_color="green"  # Color verde al hacer hover
        )
        self.save_pdf_btn.pack(side="left", padx=10)

    def _show_main(self):
        self.header.pack(fill="x", pady=10, padx=10)
        self.details.pack(fill="x", pady=5, padx=20)
        self.table_frame.pack(fill="both", expand=True, pady=10, padx=20)
        self.linef.pack(fill="x", pady=5, padx=20)
        self.botf.pack(fill="x", pady=10, padx=20)
        self.extraf.pack(fill="x", pady=5, padx=20)
        self.actf.pack(pady=20)

    # — Inline Cliente — #
    def _add_client_inline(self):
        # Contraer dropdown si está visible
        if self.client_dropdown_visible:
            self._toggle_client_dropdown()
            
        for w in (self.header, self.details,
                  self.table_frame, self.linef,
                  self.botf, self.extraf, self.actf):
            w.pack_forget()
        self.client_form = ctk.CTkFrame(self.frame)
        self.client_form.pack(fill="both", expand=True, padx=40, pady=20)
        ctk.CTkLabel(self.client_form, text="Agregar Cliente",
                     font=("Arial",20)).pack(pady=(0,10))
        labels = ["Nombre completo","Cédula/RUC","Contacto","Dirección","Email"]
        keys   = ["full_name","cedula","contact","address","email"]
        self.client_widgets = {}
        for lbl, key in zip(labels, keys):
            ctk.CTkLabel(self.client_form, text=lbl).pack(anchor="w", pady=5)
            ent = ctk.CTkEntry(self.client_form)
            ent.pack(fill="x")
            self.client_widgets[key] = ent
        btnf = ctk.CTkFrame(self.client_form)
        btnf.pack(pady=20)
        ctk.CTkButton(btnf, text="Guardar",
                      command=self._save_client_inline).pack(side="left", padx=10)
        ctk.CTkButton(btnf, text="Cancelar",
                      command=self._cancel_client_inline).pack(side="left")

    def _save_client_inline(self):
        data = {k: w.get().strip() for k, w in self.client_widgets.items()}
        if not data["full_name"]:
            return messagebox.showerror("Error","El nombre es obligatorio.")
        existing = [c["cedula"] for c in Client.all() if c["cedula"]]
        if data["cedula"] and data["cedula"] in existing:
            return messagebox.showerror("Error","Cédula/RUC ya registrado.")
        Client.create(data["full_name"], data["cedula"],
                      data["contact"], data["address"], data["email"])
        self.client_form.destroy()
        self._show_main()
        self._load_clients_list()
        self._populate_client_list()
        
        # CORRECCIÓN: Seleccionar correctamente el cliente recién creado
        if self.client_values:
            # Buscar el cliente recién creado por nombre
            nuevo_cliente_nombre = data["full_name"]
            for display_text in self.client_values:
                if nuevo_cliente_nombre in display_text:
                    self.client_search.delete(0, 'end')
                    self.client_search.insert(0, display_text)
                    break

    def _cancel_client_inline(self):
        self.client_form.destroy()
        self._show_main()

    # — Inline Ítem — #
    def _add_item_inline(self):
        for w in (self.header, self.details,
                  self.table_frame, self.linef,
                  self.botf, self.extraf, self.actf):
            w.pack_forget()
        self.item_form = ctk.CTkFrame(self.frame)
        self.item_form.pack(fill="both", expand=True, padx=40, pady=20)
        ctk.CTkLabel(self.item_form, text="Agregar Ítem",
                     font=("Arial",20)).pack(pady=(0,10))
        prods = Product.all()
        self.prod_map = {}
        for p in prods:
            codigo = p['code'] or 'SIN-COD'
            display_text = f"[{codigo}] {p['name']} (Stock: {p['stock']})"
            self.prod_map[display_text] = p
        
        row = ctk.CTkFrame(self.item_form)
        row.pack(fill="x", pady=5)
        ctk.CTkLabel(row, text="Producto:").pack(side="left", padx=(0,5))
        
        # Frame para producto con dropdown
        prod_frame = ctk.CTkFrame(row)
        prod_frame.pack(side="left", fill="x", expand=True, padx=(0,5))
        
        # Entry para búsqueda
        self.prod_search = ctk.CTkEntry(prod_frame, placeholder_text="Buscar por código o nombre...")
        self.prod_search.pack(side="left", fill="x", expand=True)
        self.prod_search.bind("<KeyRelease>", self._filter_products)
        
        # Botón flecha para mostrar/ocultar lista de productos
        self.prod_dropdown_btn = ctk.CTkButton(
            prod_frame, text="▼", width=30,
            command=self._toggle_product_dropdown
        )
        self.prod_dropdown_btn.pack(side="right")
        
        ctk.CTkButton(row, text="+", width=30,
                      command=self._add_product_inline_inline)\
            .pack(side="right", padx=(5,0))
        
        # Frame para la lista desplegable de productos
        self.prod_dropdown_frame = ctk.CTkFrame(self.item_form)
        
        # Listbox para mostrar resultados de búsqueda con scroll
        self.search_listbox = ttk.Treeview(self.prod_dropdown_frame, show="tree", height=8)
        self.search_listbox.pack(side="left", fill="both", expand=True)
        self.search_listbox.bind("<ButtonRelease-1>", self._select_from_search)  # CAMBIO: UN SOLO CLICK
        
        # Scrollbar para productos
        prod_scrollbar = ttk.Scrollbar(self.prod_dropdown_frame, orient="vertical", command=self.search_listbox.yview)
        prod_scrollbar.pack(side="right", fill="y")
        self.search_listbox.configure(yscrollcommand=prod_scrollbar.set)
        
        self._populate_search_list()
        self.prod_dropdown_visible = False
        
        ctk.CTkLabel(self.item_form, text="Cantidad:").pack(anchor="w", pady=5)
        self.qty_e = ctk.CTkEntry(self.item_form)
        self.qty_e.insert(0, "1")
        self.qty_e.pack(fill="x")
        ctk.CTkLabel(self.item_form, text="Precio unitario:").pack(anchor="w", pady=5)
        self.price_e = ctk.CTkEntry(self.item_form)
        self.price_e.pack(fill="x")
        btnf = ctk.CTkFrame(self.item_form)
        btnf.pack(pady=20)
        ctk.CTkButton(btnf, text="Guardar",
                      command=self._save_item_inline).pack(side="left", padx=10)
        ctk.CTkButton(btnf, text="Cancelar",
                      command=self._cancel_item_inline).pack(side="left")

    def _toggle_product_dropdown(self):
        """Mostrar/ocultar dropdown de productos"""
        if self.prod_dropdown_visible:
            self.prod_dropdown_frame.pack_forget()
            self.prod_dropdown_btn.configure(text="▼", fg_color=["#3a7ebf", "#1f538d"])  # Color normal
            self.prod_dropdown_visible = False
        else:
            self.prod_dropdown_frame.pack(fill="x", pady=5)
            self.prod_dropdown_btn.configure(text="▲", fg_color="red")  # CAMBIO: Color rojo cuando apunta arriba
            self.prod_dropdown_visible = True
            self._populate_search_list()

    def _populate_search_list(self):
        """Poblar lista con todos los productos"""
        for item in self.search_listbox.get_children():
            self.search_listbox.delete(item)
        for display_text in self.prod_map.keys():
            self.search_listbox.insert("", "end", text=display_text)

    def _filter_products(self, event=None):
        """Filtrar productos por búsqueda"""
        if not self.prod_dropdown_visible:
            return
            
        search_term = self.prod_search.get().lower()
        
        # Limpiar listbox
        for item in self.search_listbox.get_children():
            self.search_listbox.delete(item)
        
        # Filtrar y mostrar coincidencias
        for display_text, product in self.prod_map.items():
            codigo = product['code'] or ''
            nombre = product['name'] or ''
            if (search_term in codigo.lower() or 
                search_term in nombre.lower() or 
                search_term == ''):
                self.search_listbox.insert("", "end", text=display_text)

    def _select_from_search(self, event=None):
        """Seleccionar producto de la lista de búsqueda con un solo click"""
        selection = self.search_listbox.selection()
        if selection:
            display_text = self.search_listbox.item(selection[0])['text']
            self.prod_search.delete(0, 'end')
            self.prod_search.insert(0, display_text)
            self._on_prod_select(display_text)
            # Contraer dropdown automáticamente
            self._toggle_product_dropdown()

    def _on_prod_select(self, choice):
        p = self.prod_map.get(choice)
        if p:
            self.price_e.delete(0,"end")
            self.price_e.insert(0,str(p["sell_price"]))

    def _add_product_inline_inline(self):
        # Contraer dropdown si está visible
        if hasattr(self, 'prod_dropdown_visible') and self.prod_dropdown_visible:
            self._toggle_product_dropdown()
            
        self.item_form.pack_forget()
        self.prod_form = ctk.CTkFrame(self.frame)
        self.prod_form.pack(fill="both", expand=True, padx=40, pady=20)
        ctk.CTkLabel(self.prod_form, text="Nuevo Producto",
                     font=("Arial",20)).pack(pady=(0,10))

        campos = [
            ("Código (opcional)", "code"),
            ("Nombre", "name"),
            ("Categoría existente", "category_cb"),
            ("Nueva categoría", "category_new"),
            ("Precio de compra", "cost_price"),
            ("Precio de venta", "sell_price"),
            ("Tipo (Producto/Servicio)", "type_"),
            ("Stock inicial", "stock"),
        ]
        cats = Product.get_categories()
        self.prod_widgets = {}
        for lbl, key in campos:
            ctk.CTkLabel(self.prod_form, text=lbl).pack(anchor="w", pady=5)
            if key == "category_cb":
                cb = ctk.CTkComboBox(self.prod_form,
                                     values=cats,
                                     state="readonly")
                if cats: cb.set(cats[0])
                cb.pack(fill="x")
                self.prod_widgets[key] = cb
            elif key == "category_new":
                ent = ctk.CTkEntry(self.prod_form,
                                   placeholder_text="Dejar vacío para usar existente")
                ent.pack(fill="x")
                self.prod_widgets[key] = ent
            elif key == "type_":
                cb = ctk.CTkComboBox(self.prod_form,
                                     values=["Producto","Servicio"],
                                     state="readonly")
                cb.set("Producto")
                cb.pack(fill="x")
                cb.bind("<<ComboboxSelected>>", lambda e: self._on_type_change_inline())
                self.prod_widgets[key] = cb
            else:
                ent = ctk.CTkEntry(self.prod_form)
                ent.pack(fill="x")
                self.prod_widgets[key] = ent

        btnf = ctk.CTkFrame(self.prod_form)
        btnf.pack(pady=20)
        ctk.CTkButton(btnf, text="Guardar",
                      command=self._save_product_inline).pack(side="left", padx=10)
        ctk.CTkButton(btnf, text="Cancelar",
                      command=self._cancel_product_inline).pack(side="left")

        self._on_type_change_inline()

    def _on_type_change_inline(self):
        is_serv = (self.prod_widgets["type_"].get() == "Servicio")
        for key in ("cost_price","stock"):
            w = self.prod_widgets[key]
            lbl = w.master.pack_slaves()[w.master.pack_slaves().index(w)-1]
            if is_serv:
                lbl.pack_forget(); w.pack_forget()
            else:
                lbl.pack(anchor="w", pady=5); w.pack(fill="x")
        for key in ("category_cb","category_new"):
            w = self.prod_widgets[key]
            lbl = w.master.pack_slaves()[w.master.pack_slaves().index(w)-1]
            if is_serv:
                lbl.pack_forget(); w.pack_forget()
            else:
                lbl.pack(anchor="w", pady=5); w.pack(fill="x")

    def _save_product_inline(self):
        data = {}
        try:
            for k, w in self.prod_widgets.items():
                val = w.get().strip() if isinstance(w, ctk.CTkEntry) else w.get()
                data[k] = val or None
            data["cost_price"] = float(data.get("cost_price") or 0)
            data["sell_price"] = float(data["sell_price"])
            data["stock"]      = int(data.get("stock") or 0)
        except:
            return messagebox.showerror("Error","Datos del producto inválidos.")
        cat_new = data.pop("category_new") or ""
        category = cat_new or data.pop("category_cb", "")
        Product.create(
            data["code"], data["name"], category,
            data["cost_price"], data["sell_price"],
            data["type_"], data["stock"]
        )
        messagebox.showinfo("Listo","Producto creado.")
        self.prod_form.destroy()
        self._add_item_inline()

    def _cancel_product_inline(self):
        self.prod_form.destroy()
        self._add_item_inline()

    def _save_item_inline(self):
        # Obtener selección del campo de búsqueda
        search_text = self.prod_search.get().strip()
        if not search_text:
            return messagebox.showerror("Error","Seleccione producto.")
        
        # Buscar el producto correspondiente
        p = self.prod_map.get(search_text)
        if not p:
            return messagebox.showerror("Error","Producto no válido.")
            
        try:
            qty = int(self.qty_e.get()); price = float(self.price_e.get())
        except:
            return messagebox.showerror("Error","Cantidad/precio inválido.")
        if p["type"] == "Producto" and qty > p["stock"]:
            if not messagebox.askyesno("Atención",
                    f"Stock disponible: {p['stock']}. Continuar?"):
                return
        sub = qty * price
        codigo = p['code'] or 'SIN-COD'
        self.items.append((p["id"], codigo, p["name"], qty, price, sub))
        self.tree.insert("", "end", values=(codigo, p["name"], qty, price, sub))
        self._recalc_total()
        self.item_form.destroy()
        self._show_main()

    def _cancel_item_inline(self):
        self.item_form.destroy()
        self._show_main()

    def _edit_item_inline(self):
        sel = self.tree.selection()
        if not sel:
            return messagebox.showerror("Error","Seleccione un ítem.")
        idx = self.tree.index(sel[0])
        item = self.items[idx]
        self._add_item_inline()
        
        # Buscar el display text correcto
        key = None
        for display_text, product in self.prod_map.items():
            if product["id"] == item[0]:
                key = display_text
                break
        
        if key:
            self.prod_search.delete(0, 'end')
            self.prod_search.insert(0, key)
        self.qty_e.delete(0,"end");   self.qty_e.insert(0,str(item[3]))
        self.price_e.delete(0,"end"); self.price_e.insert(0,str(item[4]))
        btns = self.item_form.pack_slaves()[-1].pack_slaves()
        btns[0].configure(text="Actualizar",
                          command=lambda i=idx: self._update_item(i))
        btns[1].configure(text="Cancelar",
                          command=self._cancel_item_inline)

    def _update_item(self, idx):
        search_text = self.prod_search.get().strip()
        p = self.prod_map.get(search_text)
        if not p:
            return messagebox.showerror("Error","Producto no válido.")
        try:
            qty = int(self.qty_e.get()); price = float(self.price_e.get())
        except:
            return messagebox.showerror("Error","Cantidad/precio inválido.")
        sub = qty * price
        codigo = p['code'] or 'SIN-COD'
        self.items[idx] = (p["id"], codigo, p["name"], qty, price, sub)
        iid = self.tree.get_children()[idx]
        self.tree.item(iid, values=(codigo, p["name"], qty, price, sub))
        self._recalc_total()
        self.item_form.destroy()
        self._show_main()

    def _remove_item(self):
        sel = self.tree.selection()
        if sel:
            idx = self.tree.index(sel[0])
            self.tree.delete(sel[0])
            del self.items[idx]
            self._recalc_total()

    def _recalc_total(self):
        total = sum(it[5] for it in self.items)  # Cambio índice a 5 por el código agregado
        try:
            disc = float(self.disc_e.get())
        except:
            disc = 0.0
        self.total_lbl.configure(text=f"{total - disc:.2f}")

    def _reset_all_fields(self):
        """Resetear todos los campos después de guardar PDF"""
        # 1) Limpiar lista de ítems y tabla
        self.items.clear()
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        
        # 2) Resetear descuento y total
        self.disc_e.delete(0,"end")
        self.disc_e.insert(0,"0")
        self.total_lbl.configure(text="0.00")
        
        # 3) Resetear cliente
        self.client_search.delete(0,"end")
        
        # 4) Resetear método de pago
        self.pay_cb.set("")
        self.credit_type_cb.pack_forget()
        self.other_pay.pack_forget()
        
        # 5) Limpiar información adicional
        self.additional_e.delete(0,"end")
        
        # 6) Limpiar campo "otro" método de pago si existe
        self.other_pay.delete(0,"end")
        self.credit_type_cb.set("")
        
        # 7) Contraer dropdowns si están visibles
        if self.client_dropdown_visible:
            self._toggle_client_dropdown()
        
        # 8) CAMBIO IMPORTANTE: Actualizar fecha para nuevos documentos
        self._update_date()
        # Actualizar el label de fecha en la interfaz
        fecha_label = self.details.grid_slaves(row=0, column=0)[0]
        fecha_label.configure(text=f"Fecha: {self.date_str}")

    def _save_pdf(self):
        if not self.client_search.get():
            return messagebox.showerror("Error","Seleccione cliente.")
        
        # — Validación obligatoria del método de pago —
        metodo = self.pay_cb.get()
        if not metodo:
            return messagebox.showerror("Error","Selecciona un método de pago.")
        
        # Construir método de pago para PDF
        if metodo == "Otro":
            detalle = self.other_pay.get().strip()
            if not detalle:
                return messagebox.showerror("Error","Describe el método de pago.")
            self.payment_method = detalle
        elif metodo == "Tarjeta de Crédito":
            tipo_credito = self.credit_type_cb.get()
            if not tipo_credito:
                return messagebox.showerror("Error","Selecciona el tipo de pago con tarjeta.")
            self.payment_method = f"Tarjeta de Crédito - {tipo_credito}"
        else:
            self.payment_method = metodo
        
        # Captura texto adicional
        self.additional_info = self.additional_e.get().strip()

        # Buscar cliente seleccionado
        client_text = self.client_search.get()
        cliente_obj = self.client_map.get(client_text)
        if not cliente_obj:
            return messagebox.showerror("Error","Cliente no válido.")

        # Guardar registro en BD (sin descontar stock)
        doc_id = Document.create(
            "PROFORMA",
            self.date_str,
            cliente_obj["id"],
            float(self.disc_e.get()),
            float(self.total_lbl.cget("text"))
        )
        for pid, _, _, qty, unit, sub in self.items:  # Ajuste para el código agregado
            DocumentItem.add(doc_id, pid, qty, unit, sub)

        # CAMBIO: Usar fecha actual para nombre de archivo
        current_date = datetime.now().strftime("%d-%m-%Y-%H-%M")
        cliente = Client.get(cliente_obj["id"])
        default_name = f"Proforma_{cliente['full_name']}_{current_date}.pdf"
        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("Archivos PDF","*.pdf")],
            title="Guardar Proforma como PDF",
            initialfile=default_name
        )
        if not file_path:
            return

        # Numeración independiente
        seq = len([d for d in Document.all() if d["type"]=="PROFORMA"])
        # Generar PDF
        self._build_pdf(cliente, doc_id, file_path, seq, self.additional_info, self.payment_method)

        # Ofrecer abrir
        if messagebox.askyesno("Abrir PDF", "¿Deseas abrir el PDF ahora?"):
            try:
                if os.name == "nt":
                    os.startfile(file_path)
                elif platform.system() == "Darwin":
                    os.system(f"open '{file_path}'")
                else:
                    os.system(f"xdg-open '{file_path}'")
            except Exception as e:
                messagebox.showerror("Error al abrir PDF", str(e))

        messagebox.showinfo("Listo", "Proforma guardada correctamente.")
        
        # Respaldo automático
        try:
            backup_name = f"PROFORMA_{doc_id}.pdf"
            backup_path = os.path.join(PDF_BACKUP_DIR, backup_name)
            if os.path.abspath(file_path) != os.path.abspath(backup_path):
                shutil.copyfile(file_path, backup_path)
        except Exception as e:
            print("Error al guardar respaldo de Proforma:", e)

        # Resetear todos los campos automáticamente
        self._reset_all_fields()

    def _build_pdf(self, cliente, doc_id, path, seq, info_adicional, metodo_pago):
        c = canvas.Canvas(path, pagesize=A4)
        W, H = A4
        
        # Márgenes estándar A4: 2.54 cm = 72.288 puntos ≈ 72 puntos
        MARGIN_TOP = 72
        MARGIN_BOTTOM = 72
        MARGIN_LEFT = 72
        MARGIN_RIGHT = 72
        
        usable_width = W - MARGIN_LEFT - MARGIN_RIGHT
        usable_height = H - MARGIN_TOP - MARGIN_BOTTOM
        line_h = 16        # interlineado

        def nueva_pagina():
            """Función para crear nueva página manteniendo configuración"""
            c.showPage()
            # Restablecer configuraciones de fuente para nueva página
            c.setFont("Helvetica", 9)
            c.setFillColor(colors.black)
            c.setStrokeColor(colors.black)
            return H - MARGIN_TOP

        # — ENCABEZADO —
        y_cursor = H - MARGIN_TOP
        # MANTENER EL TAMAÑO ORIGINAL DEL LOGO (mismo que nota_venta.py)
        logo_size = line_h * 7
        
        if os.path.exists(LOGO_PATH):
            c.drawImage(LOGO_PATH, MARGIN_LEFT, y_cursor - logo_size, 
                       width=logo_size, height=logo_size, mask='auto')
        
        # MANTENER LOS DATOS DE EMPRESA IDÉNTICOS (mismo que nota_venta.py)
        c.setFont("Helvetica-Bold", 18)
        c.drawCentredString(W/2, y_cursor - line_h, BUSINESS_NAME)
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(W/2, y_cursor - 2*line_h, RUC)
        c.setFont("Helvetica", 10)
        
        empresa_info = [OWNER_NAME, ADDRESS_LINE_1, ADDRESS_LINE_2, PHONE, EMAIL]
        for i, txt in enumerate(empresa_info, start=3):
            c.drawCentredString(W/2, y_cursor - i*line_h, txt)
        
        y_cursor -= (len(empresa_info) + 3) * line_h
        c.setFont("Helvetica-Oblique", 10)
        c.drawCentredString(W/2, y_cursor, ADDITIONAL_TEXT)

        # — TÍTULO PROFORMA —
        y_cursor -= 3*line_h
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(W/2, y_cursor, "PROFORMA")
        c.setFont("Helvetica", 10)
        c.drawRightString(W - MARGIN_RIGHT, y_cursor, f"N°: {seq:06d}")
        c.drawRightString(W - MARGIN_RIGHT, y_cursor - line_h, f"Fecha: {self.date_str}")

        # — DATOS DEL CLIENTE —
        y_cursor -= 3*line_h
        if y_cursor < MARGIN_BOTTOM + 6*line_h:
            y_cursor = nueva_pagina()
            
        c.setFont("Helvetica-Bold", 10)
        c.drawString(MARGIN_LEFT, y_cursor, "Cliente:")
        c.setFont("Helvetica", 9)
        
        cliente_info = [
            f"Nombre: {cliente['full_name']}",
            f"Cédula/RUC: {cliente['cedula'] or '-'}",
            f"Dirección: {cliente['address'] or '-'}",
            f"Contacto: {cliente['contact'] or '-'}",
            f"Correo: {cliente.get('email','-')}"
        ]
        
        for i, fld in enumerate(cliente_info, start=1):
            if y_cursor - i*line_h < MARGIN_BOTTOM:
                y_cursor = nueva_pagina()
                i = 1
            c.setFont("Helvetica", 9)  # Mantener fuente consistente
            c.drawString(MARGIN_LEFT, y_cursor - i*line_h, fld)

        # — TABLA DE ÍTEMS —
        y_cursor -= (len(cliente_info) + 2) * line_h
        if y_cursor < MARGIN_BOTTOM + 4*line_h:
            y_cursor = nueva_pagina()
            
        # Encabezado de tabla
        c.setFillColorRGB(0.7,0.9,1)
        c.rect(MARGIN_LEFT, y_cursor - line_h - 4, usable_width, line_h+4, fill=1, stroke=0)
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 9)
        
        # Columnas ajustadas
        x_cod = MARGIN_LEFT + 5
        x_desc = MARGIN_LEFT + 80
        x_qty = MARGIN_LEFT + 300
        x_unit = MARGIN_LEFT + 380
        x_sub = W - MARGIN_RIGHT - 5
        
        c.drawString(x_cod, y_cursor - line_h, "Código")
        c.drawString(x_desc, y_cursor - line_h, "Descripción")
        c.drawRightString(x_qty, y_cursor - line_h, "Cant.")
        c.drawRightString(x_unit, y_cursor - line_h, "P. Unit.")
        c.drawRightString(x_sub, y_cursor - line_h, "Subtotal")
        
        y_cursor -= line_h + 6
        c.setStrokeColor(colors.grey)
        c.line(MARGIN_LEFT, y_cursor, W - MARGIN_RIGHT, y_cursor)
        
        # Items
        for _, codigo, name, qty, price, sub in self.items:
            y_cursor -= line_h
            if y_cursor < MARGIN_BOTTOM + line_h:
                y_cursor = nueva_pagina()
                
            c.setFont("Helvetica", 9)  # Mantener fuente consistente
            c.drawString(x_cod, y_cursor, str(codigo)[:12])
            c.drawString(x_desc, y_cursor, name[:35])
            c.drawRightString(x_qty, y_cursor, str(qty))
            c.drawRightString(x_unit, y_cursor, f"{price:.2f}")
            c.drawRightString(x_sub, y_cursor, f"{sub:.2f}")

        # — RESUMEN DE TOTALES —
        y_cursor -= 2*line_h
        if y_cursor < MARGIN_BOTTOM + 3*line_h:
            y_cursor = nueva_pagina()
            
        c.setStrokeColor(colors.black)
        c.line(W - MARGIN_RIGHT - 200, y_cursor, W - MARGIN_RIGHT, y_cursor)
        
        c.setFont("Helvetica-Bold", 10)
        subtotal = float(self.total_lbl.cget("text")) + float(self.disc_e.get() or 0)
        
        y_cursor -= line_h
        c.drawRightString(x_sub, y_cursor, f"Subtotal: {subtotal:.2f}")
        
        if float(self.disc_e.get() or 0) > 0:
            y_cursor -= line_h
            c.drawRightString(x_sub, y_cursor, f"Descuento: {float(self.disc_e.get()):.2f}")
            
        y_cursor -= line_h
        c.drawRightString(x_sub, y_cursor, f"Total: {self.total_lbl.cget('text')}")

        # — INFORMACIÓN ADICIONAL (si la hay) —
        if info_adicional:
            y_cursor -= 2 * line_h
            if y_cursor < MARGIN_BOTTOM + 4 * line_h:
                y_cursor = nueva_pagina()

            c.setFont("Helvetica-Bold", 9)
            c.drawString(MARGIN_LEFT, y_cursor, "Información Adicional:")
            y_cursor -= line_h

            c.setFont("Helvetica", 9)
            text_obj = c.beginText(MARGIN_LEFT + 10, y_cursor)
            
            # Dividir texto respetando márgenes
            for ln in simpleSplit(info_adicional, "Helvetica", 9, usable_width - 10):
                if text_obj.getY() < MARGIN_BOTTOM + line_h:
                    c.drawText(text_obj)
                    y_cursor = nueva_pagina()
                    text_obj = c.beginText(MARGIN_LEFT + 10, y_cursor)
                text_obj.textLine(ln)
            c.drawText(text_obj)
            y_cursor = text_obj.getY() - line_h

        # — MÉTODO DE PAGO —
        y_cursor -= line_h
        if y_cursor < MARGIN_BOTTOM + 2*line_h:
            y_cursor = nueva_pagina()
            
        c.setFont("Helvetica-Bold", 9)
        c.drawString(MARGIN_LEFT, y_cursor, "Método de pago:")
        c.setFont("Helvetica", 9)
        
        # Manejar método de pago largo que puede necesitar múltiples líneas
        metodo_lines = simpleSplit(metodo_pago, "Helvetica", 9, usable_width - 100)
        for i, line in enumerate(metodo_lines):
            if y_cursor - i*line_h < MARGIN_BOTTOM:
                y_cursor = nueva_pagina()
                i = 0
            c.drawString(MARGIN_LEFT + 100, y_cursor - i*line_h, line)

        c.save()

    def _print(self):
        pass

    def _back(self):
        self.frame.destroy()
        from gui.dashboard import DashboardWindow
        DashboardWindow(self.master, self.user)