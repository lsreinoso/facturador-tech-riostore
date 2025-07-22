# gui/document.py

import os
import platform
import subprocess
from pathlib import Path

import customtkinter as ctk
from tkinter import ttk, messagebox
from models import Document, Client, DocumentItem
from gui.utils import maximize_window
from paths import get_pdf_backup_dir


# RUTA UNIVERSAL DE RESPALDO DE PDFs
BACKUP_DIR = Path(get_pdf_backup_dir())

# Lista de meses para el filtro
MONTHS = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]

class DocumentWindow:
    def __init__(self, master, user):
        ctk.set_appearance_mode("Light")
        ctk.set_default_color_theme("blue")
        self.master = master
        self.user   = user  # {'id':…, 'role':…}

        master.after(50, lambda: maximize_window(master))
        self.frame = ctk.CTkFrame(master, corner_radius=0)
        self.frame.pack(fill="both", expand=True)

        # — Cabecera —
        header = ctk.CTkFrame(self.frame)
        header.pack(fill="x", pady=10, padx=10)
        ctk.CTkButton(header, text="← Menú Principal", width=140,
                      command=self._back).pack(side="left")
        ctk.CTkLabel(header, text="Documentos", font=("Arial", 24))\
            .pack(side="left", padx=20)

        # — Filtros —
        filterf = ctk.CTkFrame(self.frame)
        filterf.pack(fill="x", pady=5, padx=20)

        # Filtro por tipo
        ctk.CTkLabel(filterf, text="Tipo:").pack(side="left", padx=(0,5))
        self.tipo_cb = ctk.CTkComboBox(
            filterf,
            values=["Todos", "PROFORMA", "NOTA"],
            state="readonly",
            command=lambda _: self._refresh_table()
        )
        self.tipo_cb.set("Todos")
        self.tipo_cb.pack(side="left", padx=(0,15))

        # Filtro por cliente
        ctk.CTkLabel(filterf, text="Cliente:").pack(side="left", padx=(0,5))
        self._load_clients()
        self.cliente_cb = ctk.CTkComboBox(
            filterf,
            values=["Todos"] + self.client_values,
            state="readonly",
            command=lambda _: self._refresh_table()
        )
        self.cliente_cb.set("Todos")
        self.cliente_cb.pack(side="left", padx=(0,15))

        # --- NUEVO: filtro por mes ---
        ctk.CTkLabel(filterf, text="Mes:").pack(side="left", padx=(0,5))
        self.month_cb = ctk.CTkComboBox(
            filterf,
            values=["Todos"] + MONTHS,
            state="readonly",
            command=lambda _: self._refresh_table()
        )
        self.month_cb.set("Todos")
        self.month_cb.pack(side="left", padx=(0,5))

        # — Botón de búsqueda adicional (opcional) —
        ctk.CTkButton(filterf, text="Filtrar", command=self._refresh_table)\
            .pack(side="left", padx=(15,0))

        # — Tabla de documentos —
        self.tablef = ctk.CTkFrame(self.frame)
        self.tablef.pack(fill="both", expand=True, padx=20, pady=10)
        cols = ("tipo", "fecha", "cliente", "total", "id")
        self.tree = ttk.Treeview(
            self.tablef,
            columns=cols,
            show="headings",
            height=18
        )
        # Configuro columnas
        for col, txt, w in [
            ("tipo",    "Tipo",    80),
            ("fecha",   "Fecha",   100),
            ("cliente", "Cliente", 200),
            ("total",   "Total",   80),
            ("id",      "ID",      0),
        ]:
            self.tree.heading(col, text=txt)
            self.tree.column(col, anchor="center", width=w, stretch=(col!="id"))
        self.tree.pack(side="left", fill="both", expand=True)
        vs = ttk.Scrollbar(self.tablef,
                           orient="vertical",
                           command=self.tree.yview)
        vs.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=vs.set)

        # — Botones de acción —
        actions = ctk.CTkFrame(self.frame)
        actions.pack(fill="x", padx=20, pady=10)
        # Abrir PDF
        ctk.CTkButton(actions, text="Abrir PDF", width=120,
                      command=self._open_doc).pack(side="left")
        # Eliminar solo Admin
        if self.user.get("role") == "Administrador":
            ctk.CTkButton(
                actions,
                text="Eliminar seleccionado",
                fg_color="red",
                width=160,
                command=self._delete_docs
            ).pack(side="right")

        # Cargo la tabla inicialmente
        self._refresh_table()

    def _load_clients(self):
        self.client_objs  = Client.all()
        self.client_map   = {
            f"{c['full_name']} ({c['cedula'] or '-'})": c["id"]
            for c in self.client_objs
        }
        self.client_values = list(self.client_map.keys())

    def _refresh_table(self):
        # Limpio
        for iid in self.tree.get_children():
            self.tree.delete(iid)

        tipo    = self.tipo_cb.get()
        cliente = self.cliente_cb.get()
        mes_sel = self.month_cb.get()  # nombre del mes
        search  = ""  # no hay búsqueda libre aquí

        # Re-cargo documentos
        self._load_clients()
        docs = Document.all()  # ORDER BY date DESC

        for d in docs:
            # — filtro tipo —
            if tipo != "Todos" and d["type"] != tipo:
                continue

            # — filtro cliente —
            cli = Client.get(d["client_id"])
            cli_disp = f"{cli['full_name']} ({cli['cedula'] or '-'})"
            if cliente != "Todos" and cli_disp != cliente:
                continue

            # — filtro mes —
            if mes_sel != "Todos":
                # d["date"] viene en "DD/MM/YYYY/..." → extraigo el mes
                try:
                    mes_num = int(d["date"].split("/")[1])
                except:
                    mes_num = None
                if mes_num is None or MONTHS[mes_num-1] != mes_sel:
                    continue

            # inserto, guardo id oculto
            self.tree.insert(
                "", "end",
                values=(
                    d["type"],
                    d["date"],
                    cli_disp,
                    f"{d['total']:.2f}",
                    d["id"]
                )
            )

    def _open_doc(self):
        sel = self.tree.selection()
        if not sel:
            return messagebox.showinfo("Abrir PDF", "Seleccione un documento.")
        vals   = self.tree.item(sel[0])["values"]
        doc_ty = vals[0]
        doc_id = vals[4]

        # Busca siempre en la carpeta universal de respaldos
        f1 = BACKUP_DIR / f"{doc_ty}_{doc_id}.pdf"
        f2 = BACKUP_DIR / f"{doc_ty}_{doc_id:06d}.pdf"
        backup_file = f1 if f1.exists() else (f2 if f2.exists() else None)

        if not backup_file:
            return messagebox.showerror(
                "Error",
                f"No se encontró el PDF de respaldo:\n{f1}\nni\n{f2}"
            )
        try:
            if os.name == "nt":
                os.startfile(str(backup_file))
            elif platform.system() == "Darwin":
                subprocess.run(["open", str(backup_file)])
            else:
                subprocess.run(["xdg-open", str(backup_file)])
        except Exception as e:
            messagebox.showerror("Error al abrir PDF", str(e))

    def _delete_docs(self):
        # Solo Admin
        if self.user.get("role") != "Administrador":
            return messagebox.showerror(
                "Permiso denegado",
                "Solo administradores pueden eliminar documentos."
            )
        sels = self.tree.selection()
        if not sels:
            return messagebox.showinfo("Eliminar", "Seleccione al menos un documento.")
        if not messagebox.askyesno(
            "Confirmar eliminación",
            f"¿Eliminar {len(sels)} documento(s)?"
        ):
            return

        for iid in sels:
            vals   = self.tree.item(iid)["values"]
            doc_ty = vals[0]
            doc_id = vals[4]
            # Borro en BD
            DocumentItem.delete_by_document(doc_id)
            Document.delete(doc_id)
            # Borro respaldos
            for fn in (
                BACKUP_DIR / f"{doc_ty}_{doc_id}.pdf",
                BACKUP_DIR / f"{doc_ty}_{doc_id:06d}.pdf"
            ):
                if fn.exists():
                    try: fn.unlink()
                    except: pass
            # Quito de la tabla
            self.tree.delete(iid)

        messagebox.showinfo("Eliminar", "Documento(s) eliminado(s) correctamente.")

    def _back(self):
        self.frame.destroy()
        from gui.dashboard import DashboardWindow
        DashboardWindow(self.master, self.user)
