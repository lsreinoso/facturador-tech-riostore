import os
import platform
import shutil
import tempfile
import threading
import time

import customtkinter as ctk
from tkinter import messagebox, ttk, filedialog
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas

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

        self.master = master
        self.user = user
        master.after(50, lambda: maximize_window(master))

        self.frame = ctk.CTkFrame(master, corner_radius=0)
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
        self.date_str = datetime.now().strftime("%d/%m/%Y/%H/%M")
        ctk.CTkLabel(self.details, text=f"Fecha: {self.date_str}")\
            .grid(row=0, column=0, sticky="w", pady=5)
        ctk.CTkLabel(self.details, text="Cliente:")\
            .grid(row=0, column=1, padx=(20,5))
        self._load_clients_list()
        self.client_cb = ctk.CTkComboBox(
            self.details, values=self.client_values, state="readonly"
        )
        self.client_cb.grid(row=0, column=2, sticky="ew")
        ctk.CTkButton(self.details, text="+", width=30,
                      command=self._add_client_inline)\
            .grid(row=0, column=3, padx=5)

    def _build_table(self):
        self.table_frame.pack(fill="both", expand=True, pady=10, padx=20)
        cols = ("producto","cantidad","unit_price","subtotal")
        self.tree = ttk.Treeview(self.table_frame, columns=cols, show="headings")
        for col in cols:
            self.tree.heading(col, text=col.replace("_"," ").capitalize())
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

    def _build_actions(self):
        self.actf.pack(pady=20)
        ctk.CTkButton(self.actf, text="Guardar PDF",
                      command=self._save_pdf).pack(side="left", padx=10)

    def _load_clients_list(self):
        self.client_objs = Client.all()
        self.client_values = [
            f"{c['full_name']} ({c['cedula'] or '-'})"
            for c in self.client_objs
        ]

    def _show_main(self):
        self.header.pack(fill="x", pady=10, padx=10)
        self.details.pack(fill="x", pady=5, padx=20)
        self.table_frame.pack(fill="both", expand=True, pady=10, padx=20)
        self.linef.pack(fill="x", pady=5, padx=20)
        self.botf.pack(fill="x", pady=10, padx=20)
        self.actf.pack(pady=20)

    # — Inline Cliente — #
    def _add_client_inline(self):
        for w in (self.header, self.details,
                  self.table_frame, self.linef,
                  self.botf, self.actf):
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
        self.client_cb.configure(values=self.client_values)
        self.client_cb.set(self.client_values[-1])

    def _cancel_client_inline(self):
        self.client_form.destroy()
        self._show_main()

    # — Inline Ítem — #
    def _add_item_inline(self):
        for w in (self.header, self.details,
                  self.table_frame, self.linef,
                  self.botf, self.actf):
            w.pack_forget()
        self.item_form = ctk.CTkFrame(self.frame)
        self.item_form.pack(fill="both", expand=True, padx=40, pady=20)
        ctk.CTkLabel(self.item_form, text="Agregar Ítem",
                     font=("Arial",20)).pack(pady=(0,10))
        prods = Product.all()
        self.prod_map = {f"{p['name']} (Stock: {p['stock']})": p for p in prods}
        row = ctk.CTkFrame(self.item_form)
        row.pack(fill="x", pady=5)
        ctk.CTkLabel(row, text="Producto:").pack(side="left", padx=(0,5))
        self.prod_cb = ctk.CTkComboBox(
            row, values=list(self.prod_map.keys()),
            state="readonly",
            command=self._on_prod_select
        )
        self.prod_cb.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(row, text="+", width=30,
                      command=self._add_product_inline_inline)\
            .pack(side="left", padx=(5,0))
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

    def _on_prod_select(self, choice):
        p = self.prod_map.get(choice)
        if p:
            self.price_e.delete(0,"end")
            self.price_e.insert(0,str(p["sell_price"]))

    def _add_product_inline_inline(self):
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
        choice = self.prod_cb.get()
        if not choice:
            return messagebox.showerror("Error","Seleccione producto.")
        p = self.prod_map[choice]
        try:
            qty = int(self.qty_e.get()); price = float(self.price_e.get())
        except:
            return messagebox.showerror("Error","Cantidad/precio inválido.")
        if p["type"] == "Producto" and qty > p["stock"]:
            if not messagebox.askyesno("Atención",
                    f"Stock disponible: {p['stock']}. Continuar?"):
                return
        sub = qty * price
        self.items.append((p["id"], p["name"], qty, price, sub))
        self.tree.insert("", "end", values=(p["name"], qty, price, sub))
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
        key = next(k for k,v in self.prod_map.items() if v["id"] == item[0])
        self.prod_cb.set(key)
        self.qty_e.delete(0,"end");   self.qty_e.insert(0,str(item[2]))
        self.price_e.delete(0,"end"); self.price_e.insert(0,str(item[3]))
        btns = self.item_form.pack_slaves()[-1].pack_slaves()
        btns[0].configure(text="Actualizar",
                          command=lambda i=idx: self._update_item(i))
        btns[1].configure(text="Cancelar",
                          command=self._cancel_item_inline)

    def _update_item(self, idx):
        p = self.prod_map[self.prod_cb.get()]
        try:
            qty = int(self.qty_e.get()); price = float(self.price_e.get())
        except:
            return messagebox.showerror("Error","Cantidad/precio inválido.")
        sub = qty * price
        self.items[idx] = (p["id"], p["name"], qty, price, sub)
        iid = self.tree.get_children()[idx]
        self.tree.item(iid, values=(p["name"], qty, price, sub))
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
        total = sum(it[4] for it in self.items)
        try:
            disc = float(self.disc_e.get())
        except:
            disc = 0.0
        self.total_lbl.configure(text=f"{total - disc:.2f}")

    def _save_pdf(self):
        if not self.client_cb.get():
            return messagebox.showerror("Error","Seleccione cliente.")
        idx = self.client_values.index(self.client_cb.get())
        client_id = self.client_objs[idx]["id"]
        cliente = Client.get(client_id)

        # Guardar registro en BD (sin descontar stock)
        doc_id = Document.create(
            "PROFORMA",
            self.date_str,
            client_id,
            float(self.disc_e.get()),
            float(self.total_lbl.cget("text"))
        )
        for pid, _, qty, unit, sub in self.items:
            DocumentItem.add(doc_id, pid, qty, unit, sub)

        # Diálogo Guardar como...
        default_name = f"Proforma_{cliente['full_name']}_{self.date_str.replace('/','-')}.pdf"
        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("Archivos PDF","*.pdf")],
            title="Guardar Proforma como PDF",
            initialfile=default_name
        )
        if not file_path:
            return

        self._build_pdf(cliente, doc_id, file_path)

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

        # Respaldo automático SIEMPRE EN PDF_BACKUP_DIR
        try:
            backup_name = f"PROFORMA_{doc_id}.pdf"
            backup_path = os.path.join(PDF_BACKUP_DIR, backup_name)
            if os.path.abspath(file_path) != os.path.abspath(backup_path):
                if os.path.exists(file_path):
                    shutil.copyfile(file_path, backup_path)
        except Exception as e:
            print("Error al guardar respaldo de Proforma:", e)

    def _build_pdf(self, cliente, doc_id, path):
        c = canvas.Canvas(path, pagesize=A4)
        W, H = A4
        m = 72    # margen
        line_h = 16  # interlineado

        y_top = H - m
        logo_size = line_h * 7
        if os.path.exists(LOGO_PATH):
            c.drawImage(LOGO_PATH, m, y_top - logo_size, width=logo_size, height=logo_size, mask='auto')
        c.setFont("Helvetica-Bold", 18)
        c.drawCentredString(W / 2, y_top - line_h, BUSINESS_NAME)
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(W / 2, y_top - 2 * line_h, RUC)
        c.setFont("Helvetica", 10)
        c.drawCentredString(W / 2, y_top - 3 * line_h, OWNER_NAME)
        c.drawCentredString(W / 2, y_top - 4 * line_h, ADDRESS_LINE_1)
        c.drawCentredString(W / 2, y_top - 5 * line_h, ADDRESS_LINE_2)
        c.drawCentredString(W / 2, y_top - 6 * line_h, PHONE)
        c.drawCentredString(W / 2, y_top - 7 * line_h, EMAIL)
        y_add = y_top - 8 * line_h
        c.setFont("Helvetica-Oblique", 10)
        c.drawCentredString(W / 2, y_add, ADDITIONAL_TEXT)

        y_title = y_add - 4 * line_h
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(W / 2, y_title, "PROFORMA")
        c.setFont("Helvetica", 10)
        c.drawRightString(W - m, y_title, f"N°: {doc_id:06d}")
        c.drawRightString(W - m, y_title - line_h, f"Fecha: {self.date_str}")

        y0 = y_title - 3 * line_h
        c.setFont("Helvetica-Bold", 10)
        c.drawString(m, y0, "Cliente:")
        c.setFont("Helvetica", 9)
        c.drawString(m, y0 - line_h, f"Nombre: {cliente['full_name']}")
        c.drawString(m, y0 - 2 * line_h, f"Cédula/RUC: {cliente['cedula'] or '-'}")
        c.drawString(m, y0 - 3 * line_h, f"Dirección: {cliente['address'] or '-'}")
        c.drawString(m, y0 - 4 * line_h, f"Contacto: {cliente['contact'] or '-'}")
        c.drawString(m, y0 - 5 * line_h, f"Correo: {cliente.get('email', '-')}")

        y = y0 - 7 * line_h
        c.setFillColorRGB(0.7, 0.9, 1)
        c.rect(m, y, W - 2 * m, line_h + 4, fill=1, stroke=0)
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 9)
        x_desc = m + 5
        x_qty  = m + 200
        x_unit = m + 300
        x_sub  = W - m - 10
        c.drawString(x_desc, y + 4, "Descripción")
        c.drawRightString(x_qty, y + 4, "Cant.")
        c.drawRightString(x_unit, y + 4, "P. Unit.")
        c.drawRightString(x_sub, y + 4, "Subtotal")
        y -= 6
        c.setStrokeColor(colors.grey)
        c.line(m, y, W - m, y)
        y -= line_h
        c.setFont("Helvetica", 9)
        for _, name, qty, price, sub in self.items:
            c.drawString(x_desc, y, name[:50])
            c.drawRightString(x_qty, y, str(qty))
            c.drawRightString(x_unit, y, f"{price:.2f}")
            c.drawRightString(x_sub, y, f"{sub:.2f}")
            y -= line_h
            if y < m + 100:
                c.showPage()
                y = H - m - 50

        y -= line_h
        c.setStrokeColor(colors.black)
        c.line(W - m - 200, y, W - m, y)
        y -= line_h
        c.setFont("Helvetica-Bold", 10)
        subtotal = float(self.total_lbl.cget("text")) + float(self.disc_e.get() or 0)
        c.drawRightString(x_sub, y, f"Subtotal: {subtotal:.2f}")
        if float(self.disc_e.get() or 0) > 0:
            y -= line_h
            c.drawRightString(x_sub, y, f"Descuento: {float(self.disc_e.get()):.2f}")
        y -= line_h
        c.drawRightString(x_sub, y, f"Total: {self.total_lbl.cget('text')}")

        c.save()

    def _print(self):
        pass

    def _back(self):
        self.frame.destroy()
        from gui.dashboard import DashboardWindow
        DashboardWindow(self.master, self.user)
