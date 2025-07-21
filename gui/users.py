# gui/users.py
import customtkinter as ctk
from tkinter import messagebox, ttk
import ctypes
from models import User

SW_MAXIMIZE = 3
def maximize_window(win):
    win.update_idletasks()
    hwnd = ctypes.windll.user32.GetParent(win.winfo_id())
    ctypes.windll.user32.ShowWindow(hwnd, SW_MAXIMIZE)

class UsersWindow:
    def __init__(self, master, current_user):
        ctk.set_appearance_mode("Light")
        ctk.set_default_color_theme("dark-blue")
        self.master = master
        self.current_user = current_user
        master.after(50, lambda: maximize_window(master))

        # Marco principal
        self.frame = ctk.CTkFrame(master, corner_radius=0)
        self.frame.pack(fill="both", expand=True)

        # Sub-frames
        self.header_frame  = ctk.CTkFrame(self.frame)
        self.table_frame   = ctk.CTkFrame(self.frame)
        self.actions_frame = ctk.CTkFrame(self.frame)
        self.form_frame    = ctk.CTkFrame(self.frame)

        # Header
        self.header_frame.pack(fill="x", pady=(10,0), padx=10)
        ctk.CTkButton(self.header_frame, text="← Menú Principal",
                      width=160, height=32,
                      command=self._back).pack(side="left")
        ctk.CTkLabel(self.header_frame, text="Gestión de Usuarios",
                     font=("Arial",24)).pack(side="left", padx=20)

        # Tabla de usuarios
        self.table_frame.pack(fill="both", expand=True, pady=10, padx=20)
        cols = ("id","full_name","username","role")
        display = ("full_name","username","role")
        headings = {
            "full_name":"Nombre completo",
            "username":"Usuario",
            "role":"Rol"
        }
        self.tree = ttk.Treeview(self.table_frame,
                                 columns=cols,
                                 show="headings",
                                 displaycolumns=display)
        for c in cols:
            self.tree.heading(c,
                              text=headings.get(c,""),
                              command=(lambda _c=c: self.sort_by(_c, False)))
            self.tree.column(c, width=150, anchor="center")
        self.tree.pack(fill="both", expand=True)

        # Botones
        self.actions_frame.pack(fill="x", pady=10, padx=20)
        ctk.CTkButton(self.actions_frame, text="Agregar Usuario",
                      command=lambda: self._open_form(False))\
            .pack(side="left")
        ctk.CTkButton(self.actions_frame, text="Editar Seleccionado",
                      command=lambda: self._open_form(True))\
            .pack(side="left", padx=5)
        ctk.CTkButton(self.actions_frame, text="Eliminar Seleccionado",
                      command=self._delete_user)\
            .pack(side="left", padx=5)

        # Carga inicial
        self._load_users()

    def _load_users(self):
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        for u in User.all():
            self.tree.insert("", "end", values=(
                u["id"], u["full_name"], u["username"], u["role"]
            ))

    def _open_form(self, edit):
        # determina edición
        self.edit_id = None
        if edit:
            sel = self.tree.selection()
            if not sel:
                return messagebox.showerror("Error", "Seleccione un usuario.")
            self.edit_id = self.tree.item(sel[0])["values"][0]

        # oculta tablas y botones
        for f in (self.header_frame, self.table_frame, self.actions_frame):
            f.pack_forget()
        # muestra formulario
        self.form_frame.pack(fill="both", expand=True, pady=20, padx=40)
        for w in self.form_frame.winfo_children():
            w.destroy()

        title = "Editar Usuario" if self.edit_id else "Agregar Usuario"
        ctk.CTkLabel(self.form_frame, text=title,
                     font=("Arial",24)).pack(pady=(0,20))

        labels = ["Nombre completo","Usuario","Contraseña","Confirmar contraseña","Rol"]
        keys   = ["full_name",     "username",  "password",   "password2",             "role"]
        self.widgets = {}
        for lbl, key in zip(labels, keys):
            ctk.CTkLabel(self.form_frame, text=lbl).pack(anchor="w", pady=5)
            if key=="role":
                cb = ctk.CTkComboBox(self.form_frame,
                                     values=["Administrador","Empleado"],
                                     state="readonly")
                cb.set("Empleado")
                cb.pack(fill="x")
                self.widgets[key] = cb
            else:
                show = "*" if "password" in key else None
                ent = ctk.CTkEntry(self.form_frame, show=show)
                ent.pack(fill="x")
                self.widgets[key] = ent

        # precarga en edición (sin contraseña)
        if self.edit_id:
            u = next(u for u in User.all() if u["id"]==self.edit_id)
            self.widgets["full_name"].insert(0, u["full_name"])
            self.widgets["username"].insert(0, u["username"])
            self.widgets["role"].set(u["role"])

        # botones Guardar/Cancelar
        btns = ctk.CTkFrame(self.form_frame)
        btns.pack(pady=20)
        ctk.CTkButton(btns, text="Guardar", command=self._save_user)\
            .pack(side="left", padx=10)
        ctk.CTkButton(btns, text="Cancelar", command=self._cancel_form)\
            .pack(side="left")

    def _save_user(self):
        d = {k: w.get().strip() for k,w in self.widgets.items()}
        # validaciones
        if not d["full_name"] or not d["username"]:
            return messagebox.showerror("Error", "Nombre y usuario son obligatorios.")
        if not self.edit_id or d["password"]:
            if not d["password"] or d["password"]!=d["password2"]:
                return messagebox.showerror("Error", "Contraseñas vacías o no coinciden.")
        try:
            if self.edit_id:
                User.update(self.edit_id,
                            d["full_name"], d["username"],
                            d["role"],
                            password=d["password"] or None)
            else:
                User.create(d["full_name"], d["username"],
                            d["password"], d["role"])
        except Exception as e:
            return messagebox.showerror("Error", str(e))

        self._cancel_form()
        self._load_users()

    def _cancel_form(self):
        self.form_frame.pack_forget()
        self.header_frame.pack(fill="x", pady=(10,0), padx=10)
        self.table_frame.pack(fill="both", expand=True, pady=10, padx=20)
        self.actions_frame.pack(fill="x", pady=10, padx=20)

    def _delete_user(self):
        sel = self.tree.selection()
        if not sel:
            return messagebox.showerror("Error", "Seleccione un usuario.")
        uid = self.tree.item(sel[0])["values"][0]
        if uid == self.current_user["id"]:
            return messagebox.showerror("Error", "No puede borrarse a sí mismo.")
        if not messagebox.askyesno("Confirmar", "¿Eliminar este usuario?"):
            return
        User.delete(uid)
        self._load_users()

    def sort_by(self, col, descending):
        data = [(self.tree.set(k, col).lower(), k)
                for k in self.tree.get_children()]
        data.sort(reverse=descending)
        for idx, (_, k) in enumerate(data):
            self.tree.move(k, "", idx)
        self.tree.heading(col, command=lambda: self.sort_by(col, not descending))

    def _back(self):
        self.frame.destroy()
        from gui.dashboard import DashboardWindow
        DashboardWindow(self.master, self.current_user)
