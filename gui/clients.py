# gui/clients.py
import customtkinter as ctk
from tkinter import messagebox, ttk
import ctypes
from models import Client

SW_MAXIMIZE = 3
def maximize_window(win):
    win.update_idletasks()
    hwnd = ctypes.windll.user32.GetParent(win.winfo_id())
    ctypes.windll.user32.ShowWindow(hwnd, SW_MAXIMIZE)

class ClientsWindow:
    def __init__(self, master, current_user, return_to="dashboard", open_form=False):
        """
        return_to: "dashboard", "proforma" or "nota"
        open_form: if True, immediately open the add-client form
        """
        ctk.set_appearance_mode("Light")
        ctk.set_default_color_theme("dark-blue")
        self.master = master
        self.current_user = current_user
        self.return_to = return_to
        master.after(50, lambda: maximize_window(master))

        self.frame = ctk.CTkFrame(master, corner_radius=0)
        self.frame.pack(fill="both", expand=True)

        # subframes
        self.header_frame  = ctk.CTkFrame(self.frame)
        self.search_frame  = ctk.CTkFrame(self.frame)
        self.table_frame   = ctk.CTkFrame(self.frame)
        self.actions_frame = ctk.CTkFrame(self.frame)
        self.form_frame    = ctk.CTkFrame(self.frame)

        # 1) Header
        self.header_frame.pack(fill="x", pady=(10,0), padx=10)
        ctk.CTkButton(self.header_frame, text="← Volver",
                      width=160, height=32,
                      command=self._back).pack(side="left")
        ctk.CTkLabel(self.header_frame, text="Gestión de Clientes",
                     font=("Arial",24)).pack(side="left", padx=20)

        # 2) Search
        self.search_frame.pack(fill="x", pady=10, padx=20)
        self.search_var = ctk.StringVar()
        ctk.CTkEntry(self.search_frame,
                     placeholder_text="Buscar por nombre o cédula/RUC...",
                     textvariable=self.search_var)\
            .pack(side="left", fill="x", expand=True)
        ctk.CTkButton(self.search_frame, text="Buscar",
                      command=self._load_clients).pack(side="left", padx=5)
        ctk.CTkButton(self.search_frame, text="Limpiar",
                      command=self._reset_search).pack(side="left")

        # 3) Table
        self.table_frame.pack(fill="both", expand=True, pady=10, padx=20)
        cols = ("id","full_name","cedula","contact","address","email")
        display = ("full_name","cedula","contact","address","email")
        heads = {
            "full_name":"Nombre completo",
            "cedula":"Cédula/RUC",
            "contact":"Contacto",
            "address":"Dirección",
            "email":"Email"
        }
        self.tree = ttk.Treeview(self.table_frame,
                                 columns=cols, show="headings",
                                 displaycolumns=display)
        for c in cols:
            self.tree.heading(c, text=heads.get(c,""),
                              command=lambda _c=c: self.sort_by(_c, False))
            self.tree.column(c, width=150, anchor="center")
        self.tree.pack(fill="both", expand=True)

        # 4) Actions
        self.actions_frame.pack(fill="x", pady=10, padx=20)
        ctk.CTkButton(self.actions_frame, text="Agregar Cliente",
                      command=lambda: self._open_form(False))\
            .pack(side="left")
        ctk.CTkButton(self.actions_frame, text="Editar Seleccionado",
                      command=lambda: self._open_form(True))\
            .pack(side="left", padx=5)
        ctk.CTkButton(self.actions_frame, text="Eliminar Seleccionado",
                      command=self._delete_client)\
            .pack(side="left", padx=5)

        # initial load
        self._load_clients()

        # optionally open add form immediately
        if open_form:
            self._open_form(False)

    def _load_clients(self):
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        term = self.search_var.get().strip()
        items = Client.search(term) if term else Client.all()
        for c in items:
            self.tree.insert("", "end", values=(
                c["id"], c["full_name"], c["cedula"] or "",
                c["contact"] or "", c["address"] or "", c["email"] or ""
            ))

    def _reset_search(self):
        self.search_var.set("")
        self._load_clients()

    def _open_form(self, edit):
        self.edit_id = None
        if edit:
            sel = self.tree.selection()
            if not sel:
                return messagebox.showerror("Error","Seleccione un cliente.")
            self.edit_id = self.tree.item(sel[0])["values"][0]

        # hide listing frames
        for f in (self.header_frame, self.search_frame,
                  self.table_frame, self.actions_frame):
            f.pack_forget()
        self.form_frame.pack(fill="both", expand=True, pady=20, padx=40)
        for w in self.form_frame.winfo_children():
            w.destroy()

        title = "Editar Cliente" if self.edit_id else "Agregar Cliente"
        ctk.CTkLabel(self.form_frame, text=title,
                     font=("Arial",24)).pack(pady=(0,20))

        labels = ["Nombre completo","Cédula/RUC","Contacto","Dirección","Email"]
        keys   = ["full_name","cedula","contact","address","email"]
        self.widgets = {}
        for lbl, key in zip(labels, keys):
            ctk.CTkLabel(self.form_frame, text=lbl).pack(anchor="w", pady=5)
            ent = ctk.CTkEntry(self.form_frame)
            ent.pack(fill="x")
            self.widgets[key] = ent

        if self.edit_id:
            cli = Client.get(self.edit_id)
            for key in keys:
                self.widgets[key].insert(0, cli.get(key) or "")

        btns = ctk.CTkFrame(self.form_frame)
        btns.pack(pady=20)
        ctk.CTkButton(btns, text="Guardar", command=self._save_client)\
            .pack(side="left", padx=10)
        ctk.CTkButton(btns, text="Cancelar", command=self._cancel_form)\
            .pack(side="left")

    def _save_client(self):
        d = {k: w.get().strip() for k,w in self.widgets.items()}
        if not d["full_name"]:
            return messagebox.showerror("Error","El nombre es obligatorio.")
        existing = [c["cedula"] for c in Client.all() if c["cedula"]]
        if d["cedula"] and d["cedula"] in existing:
            if not (self.edit_id and Client.get(self.edit_id)["cedula"]==d["cedula"]):
                return messagebox.showerror("Error","Cédula/RUC ya registrado.")
        # commit
        if self.edit_id:
            Client.update(self.edit_id,
                          d["full_name"], d["cedula"],
                          d["contact"], d["address"], d["email"])
        else:
            Client.create(d["full_name"], d["cedula"],
                          d["contact"], d["address"], d["email"])

        # after save, if called from Proforma/Nota, go back; else refresh list
        if self.return_to in ("proforma","nota"):
            self._back()
        else:
            self._cancel_form()
            self._load_clients()

    def _cancel_form(self):
        if self.return_to in ("proforma","nota"):
            return self._back()
        self.form_frame.pack_forget()
        self.header_frame.pack(fill="x", pady=(10,0), padx=10)
        self.search_frame.pack(fill="x", pady=10, padx=20)
        self.table_frame.pack(fill="both", expand=True, pady=10, padx=20)
        self.actions_frame.pack(fill="x", pady=10, padx=20)

    def _delete_client(self):
        sel = self.tree.selection()
        if not sel:
            return messagebox.showerror("Error","Seleccione un cliente.")
        cid = self.tree.item(sel[0])["values"][0]
        if not messagebox.askyesno("Confirmar","¿Eliminar este cliente?"):
            return
        Client.delete(cid)
        self._load_clients()

    def sort_by(self, col, descending):
        data = [(self.tree.set(k, col).lower(), k)
                for k in self.tree.get_children()]
        data.sort(reverse=descending)
        for idx, (_, k) in enumerate(data):
            self.tree.move(k, "", idx)
        self.tree.heading(col,
            command=lambda: self.sort_by(col, not descending))

    def _back(self):
        self.frame.destroy()
        if self.return_to == "proforma":
            from gui.proforma import ProformaWindow
            ProformaWindow(self.master, self.current_user)
        elif self.return_to == "nota":
            from gui.nota_venta import NotaVentaWindow
            NotaVentaWindow(self.master, self.current_user)
        else:
            from gui.dashboard import DashboardWindow
            DashboardWindow(self.master, self.current_user)
