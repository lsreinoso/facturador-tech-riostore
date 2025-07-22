import os
import platform
import tempfile
import shutil
import threading
import time

import customtkinter as ctk
from tkinter import messagebox, filedialog
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors

from models import Document, DocumentItem, Client, Product
from gui.proforma import ProformaWindow
from gui.utils import maximize_window
from paths import get_pdf_backup_dir
from pathlib import Path
from customtkinter import CTkScrollableFrame


# — DIRECTORIO DE RESPALDO CORRECTO UNIVERSAL —
BACKUP_DIR = Path(get_pdf_backup_dir())

# — Datos de la empresa —
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

class NotaVentaWindow(ProformaWindow):
    def __init__(self, master, user):
        super().__init__(master, user)
        # Cambiar el título
        hdr = self.frame.winfo_children()[0]
        hdr.winfo_children()[1].configure(text="Nota de Venta")
        # Solo botón “Guardar PDF” (quitamos “Imprimir”)
        for w in self.actf.winfo_children():
            w.destroy()
        ctk.CTkButton(self.actf, text="Guardar PDF",
                      command=self._save_pdf).pack(side="left", padx=10)

    def _save_pdf(self):
        if not self.client_cb.get():
            return messagebox.showerror("Error", "Seleccione cliente.")
        idx = self.client_values.index(self.client_cb.get())
        client_id = self.client_objs[idx]["id"]
        cliente = Client.get(client_id)

        # Guardar en BD y descontar stock
        doc_id = Document.create(
            "NOTA",
            self.date_str,
            client_id,
            float(self.disc_e.get()),
            float(self.total_lbl.cget("text"))
        )
        for pid, _, qty, unit, sub in self.items:
            DocumentItem.add(doc_id, pid, qty, unit, sub)
            Product.adjust_stock(pid, -qty)

        # Diálogo Guardar como...
        default_name = f"NotaVenta_{cliente['full_name']}_{self.date_str.replace('/','-')}.pdf"
        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("Archivos PDF","*.pdf")],
            title="Guardar Nota de Venta como PDF",
            initialfile=default_name
        )
        if not file_path:
            return

        # Generar PDF con el nuevo diseño
        self._build_pdf_nota(cliente, doc_id, file_path)

        # ¿Abrir PDF?
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

        messagebox.showinfo("Listo", "Nota de Venta guardada correctamente.")

        # Respaldo automático (usa siempre el directorio universal pdf_backups)
        try:
            backup_path = BACKUP_DIR / f"NOTA_{doc_id}.pdf"
            if os.path.abspath(file_path) != str(backup_path):
                shutil.copyfile(file_path, backup_path)
        except Exception as e:
            print("Error al guardar respaldo de Nota de Venta:", e)

    def _build_pdf_nota(self, cliente, doc_id, path):
        # Usamos A4 y márgenes comunes (1" = 72pt)
        c = canvas.Canvas(path, pagesize=A4)
        W, H = A4
        m = 72  # margen
        line_h = 16  # interlineado

        # — ENCABEZADO —
        y_top = H - m
        # Ajuste logo proporcional a datos: 6 líneas de interlineado
        logo_size = line_h * 7  # aprox. 96pt
        if os.path.exists(LOGO_PATH):
            c.drawImage(LOGO_PATH, m, y_top - logo_size, width=logo_size, height=logo_size, mask='auto')
        # Nombre empresa
        c.setFont("Helvetica-Bold", 18)
        c.drawCentredString(W / 2, y_top - line_h, BUSINESS_NAME)
        # RUC empresa en negrita, menor tamaño
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(W / 2, y_top - 2 * line_h, RUC)
        # Resto de datos a continuación
        c.setFont("Helvetica", 10)
        c.drawCentredString(W / 2, y_top - 3 * line_h, OWNER_NAME)
        c.drawCentredString(W / 2, y_top - 4 * line_h, ADDRESS_LINE_1)
        c.drawCentredString(W / 2, y_top - 5 * line_h, ADDRESS_LINE_2)
        # Teléfonos y correo en líneas separadas
        c.drawCentredString(W / 2, y_top - 6 * line_h, PHONE)
        c.drawCentredString(W / 2, y_top - 7 * line_h, EMAIL)
        # Texto adicional con mayor tamaño y espaciado ajustado
        y_add = y_top - 8 * line_h
        c.setFont("Helvetica-Oblique", 10)
        c.drawCentredString(W / 2, y_add, ADDITIONAL_TEXT)

        # — TÍTULO NOTA DE VENTA —
        y_title = y_add - 4 * line_h
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(W / 2, y_title, "NOTA DE VENTA")
        # Número de nota alineado a la derecha
        c.setFont("Helvetica", 10)
        c.drawRightString(W - m, y_title, f"N°: {doc_id:06d}")
        # Fecha un nivel abajo, alineada con el mismo x que N°
        c.drawRightString(W - m, y_title - line_h, f"Fecha: {self.date_str}")

        # — DATOS DEL CLIENTE —
        y0 = y_title - 3 * line_h
        c.setFont("Helvetica-Bold", 10)
        c.drawString(m, y0, "Cliente:")
        c.setFont("Helvetica", 9)
        c.drawString(m, y0 - line_h, f"Nombre: {cliente['full_name']}")
        c.drawString(m, y0 - 2 * line_h, f"Cédula/RUC: {cliente['cedula'] or '-'}")
        c.drawString(m, y0 - 3 * line_h, f"Dirección: {cliente['address'] or '-'}")
        c.drawString(m, y0 - 4 * line_h, f"Contacto: {cliente['contact'] or '-'}")
        c.drawString(m, y0 - 5 * line_h, f"Correo: {cliente.get('email', '-')}")

        # — TABLA DE ÍTEMS —
        y = y0 - 7 * line_h
        c.setFillColorRGB(0.7, 0.9, 1)
        c.rect(m, y, W - 2 * m, line_h + 4, fill=1, stroke=0)
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 9)
        x_desc = m + 5
        x_qty = m + 200
        x_unit = m + 300
        x_sub = W - m - 10
        c.drawString(x_desc, y + 4, "Descripción")
        c.drawRightString(x_qty, y + 4, "Cant.")
        c.drawRightString(x_unit, y + 4, "P. Unit.")
        c.drawRightString(x_sub, y + 4, "Subtotal")
        c.setFillColor(colors.black)
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

        # — RESUMEN DE TOTALES —
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

        # — FIRMAS AL FINAL —
        y_sign = m + 60
        c.setFont("Helvetica", 9)
        c.line(m, y_sign, m + 200, y_sign)
        c.drawString(m + 5, y_sign - 14, "Firma autorizada")
        c.line(W - m - 200, y_sign, W - m, y_sign)
        c.drawString(W - m - 195, y_sign - 14, "Firma del cliente")

        c.save()

    # anulamos la acción de imprimir heredada
    def _print(self):
        pass
