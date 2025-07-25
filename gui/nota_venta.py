import os
import platform
import tempfile
import shutil
import threading
import time

import customtkinter as ctk
from reportlab.lib.utils import simpleSplit
from tkinter import messagebox, filedialog
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import inch




from models import Document, DocumentItem, Client, Product
from gui.proforma import ProformaWindow
from gui.utils import maximize_window
from paths import get_pdf_backup_dir
from pathlib import Path


# — DIRECTORIO DE RESPALDO CORRECTO —
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
        # Reemplazar botón "Guardar PDF" con hover verde
        for w in self.actf.winfo_children():
            w.destroy()
        self.save_pdf_btn = ctk.CTkButton(
            self.actf, 
            text="Guardar PDF",
            command=self._save_pdf,
            hover_color="green"  # CAMBIO: Color verde al hacer hover
        )
        self.save_pdf_btn.pack(side="left", padx=10)

    def _save_pdf(self):
        if not self.client_search.get():
            return messagebox.showerror("Error", "Seleccione cliente.")
        
        # — Validación obligatoria del método de pago —
        metodo = self.pay_cb.get()
        if not metodo:
            return messagebox.showerror("Error","Selecciona método de pago.")
        
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
            
        # info adicional
        self.additional_info = self.additional_e.get().strip()

        # Buscar cliente seleccionado
        client_text = self.client_search.get()
        cliente_obj = self.client_map.get(client_text)
        if not cliente_obj:
            return messagebox.showerror("Error","Cliente no válido.")

        # Guardar en BD y descontar stock
        doc_id = Document.create(
            "NOTA",
            self.date_str,
            cliente_obj["id"],
            float(self.disc_e.get()),
            float(self.total_lbl.cget("text"))
        )
        for pid, _, _, qty, unit, sub in self.items:  # Ajuste para el código agregado
            DocumentItem.add(doc_id, pid, qty, unit, sub)
            Product.adjust_stock(pid, -qty)

        # CAMBIO: Usar fecha actual para nombre de archivo
        current_date = datetime.now().strftime("%d-%m-%Y-%H-%M")
        default_name = f"NotaVenta_{cliente_obj['full_name']}_{current_date}.pdf"
        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("Archivos PDF","*.pdf")],
            title="Guardar Nota de Venta como PDF",
            initialfile=default_name
        )
        if not file_path:
            return

        # Numeración independiente
        seq = len([d for d in Document.all() if d["type"]=="NOTA"])
        # Generar PDF
        cliente = Client.get(cliente_obj["id"])
        self._build_pdf_nota(cliente, doc_id, file_path, seq, self.additional_info, self.payment_method)

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

        try:
            backup_path = BACKUP_DIR / f"NOTA_{doc_id}.pdf"
            if os.path.abspath(file_path) != str(backup_path):
                shutil.copyfile(file_path, str(backup_path))
        except Exception as e:
            print("Error al guardar respaldo de Nota de Venta:", e)

        # Resetear todos los campos automáticamente
        self._reset_all_fields()

    def _build_pdf_nota(self, cliente, doc_id, path, seq, info_adicional, metodo_pago):
        c = canvas.Canvas(path, pagesize=A4)
        W, H = A4
        
        # Márgenes estándar A4: 2.54 cm = 72.288 puntos ≈ 72 puntos
        MARGIN_TOP = 72
        MARGIN_BOTTOM = 72
        MARGIN_LEFT = 72
        MARGIN_RIGHT = 72
        
        usable_width = W - MARGIN_LEFT - MARGIN_RIGHT
        usable_height = H - MARGIN_TOP - MARGIN_BOTTOM
        line_h = 16

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
        # MANTENER EL TAMAÑO ORIGINAL DEL LOGO
        logo_size = line_h * 7
        
        if os.path.exists(LOGO_PATH):
            c.drawImage(LOGO_PATH, MARGIN_LEFT, y_cursor - logo_size, 
                       width=logo_size, height=logo_size, mask='auto')
        
        # MANTENER LOS DATOS DE EMPRESA IDÉNTICOS
        c.setFont("Helvetica-Bold", 18)
        c.drawCentredString(W/2, y_cursor - line_h, BUSINESS_NAME)
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(W/2, y_cursor - 2*line_h, RUC)
        c.setFont("Helvetica", 10)
        
        empresa_info = [OWNER_NAME, ADDRESS_LINE_1, ADDRESS_LINE_2, PHONE, EMAIL]
        for i, txt in enumerate(empresa_info, start=3):
            c.drawCentredString(W/2, y_cursor - i*line_h, txt)
        
        y_cursor -= (len(empresa_info) + 3) * line_h

        # — TÍTULO NOTA DE VENTA —
        y_cursor -= 3*line_h
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(W/2, y_cursor, "NOTA DE VENTA")
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

        # — FIRMAS —
        y_cursor -= 2*line_h
        y_sign = MARGIN_BOTTOM + 60
        if y_cursor - 40 < y_sign:
            y_cursor = nueva_pagina()
            y_sign = MARGIN_BOTTOM + 60
            
        c.setFont("Helvetica", 9)
        c.line(MARGIN_LEFT, y_sign, MARGIN_LEFT + 200, y_sign)
        c.drawString(MARGIN_LEFT + 5, y_sign - 14, "Firma autorizada")
        c.line(W - MARGIN_RIGHT - 200, y_sign, W - MARGIN_RIGHT, y_sign)
        c.drawString(W - MARGIN_RIGHT - 195, y_sign - 14, "Firma del cliente")

        c.save()