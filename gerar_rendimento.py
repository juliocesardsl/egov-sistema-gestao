import sqlite3
import os
import sys
import tkinter as tk
from tkinter import messagebox
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.lib import colors
from reportlab.lib.units import cm, inch
from reportlab.pdfgen import canvas
from pdf_utils import draw_header, default_titles
from datetime import datetime
import locale

def resource_path(relative_path):
    """ Obtém o caminho absoluto para o recurso, funciona para dev e para PyInstaller """
    try:
        # PyInstaller cria uma pasta temp e armazena o caminho em _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def gerar_comprovante_rendimentos_pdf(beneficiario_id, ano_calendario, id_usuario_logado, parent_window):
    """Gera o arquivo PDF do comprovante de rendimentos."""
    try:
        with sqlite3.connect(resource_path('banco.db')) as conn:
            cursor = conn.cursor()
            # 1. Buscar informações do beneficiário
            cursor.execute("SELECT nome, cpf FROM servidores WHERE id = ?", (beneficiario_id,))
            beneficiario = cursor.fetchone()
            if not beneficiario:
                messagebox.showerror("Erro", "Servidor não encontrado.", parent=parent_window)
                return

            # 2. Calcular os rendimentos do ano
            cursor.execute("""
                SELECT 
                    SUM(valor_bruto) as total_bruto,
                    SUM(CASE WHEN mes_referencia LIKE '%13%' THEN valor_bruto ELSE 0 END) as decimo_terceiro,
                    SUM(valor_ir_retido) as ir_retido,
                    SUM(valor_liquido) as total_liquido
                FROM pagamentos_instrutores
                WHERE servidor_id = ? 
                AND substr(mes_referencia, 4, 4) = ?
            """, (beneficiario_id, ano_calendario))
            rendimentos = cursor.fetchone()

            # 3. Buscar informações do responsável
            cursor.execute("SELECT nome_completo FROM users WHERE id_usuario = ?", (id_usuario_logado,))
            responsavel = cursor.fetchone()

        nome_beneficiario, cpf_beneficiario = beneficiario
        
        # Processar os rendimentos
        if rendimentos:
            total_bruto = rendimentos[0] or 0
            decimo_terceiro = rendimentos[1] or 0
            ir_retido = rendimentos[2] or 0
            total_liquido = rendimentos[3] or 0
            
            # Debug para verificar os valores encontrados
            print(f"Dados encontrados para {nome_beneficiario} em {ano_calendario}:")
            print(f"Total Bruto: {total_bruto}")
            print(f"13º: {decimo_terceiro}")
            print(f"IR Retido: {ir_retido}")
            print(f"Total Líquido: {total_liquido}")
        else:
            total_bruto = decimo_terceiro = ir_retido = total_liquido = 0
            print(f"Nenhum dado encontrado para {nome_beneficiario} em {ano_calendario}")

        # O total de rendimentos é o valor bruto menos o 13º
        total_rendimentos_sem_13 = total_bruto - decimo_terceiro

        nome_responsavel = responsavel[0] if responsavel else "Usuário do Sistema"

        # 4. Pedir ao usuário onde salvar o arquivo
        save_path = tk.filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            title="Salvar Comprovante de Rendimentos",
            initialfile=f"Comprovante_Rendimentos_{nome_beneficiario.replace(' ', '_')}_{ano_calendario}.pdf",
            parent=parent_window
        )
        if not save_path:
            return

        # 5. Gerar o PDF
        c = canvas.Canvas(save_path, pagesize=letter)
        width, height = letter

        # Desenha cabeçalho padrão
        content_start_y = draw_header(c, width, height, logo_path=os.path.join(os.path.dirname(__file__), 'Brasão_do_Distrito_Federal_Brasil.png'), title_lines=["Governo do Distrito Federal", "Escola de Governo do Distrito Federal", "Gerência de Pagamento de Servidores"]) 

        story = []
        # Título (mantemos espaçamento relativo ao content_start_y original)
        header_data = [
            [Paragraph("RESUMO DOS PAGAMENTOS DOS SERVIDORES", style=ParagraphStyle(name='CenterBold', alignment=TA_CENTER, fontName='Helvetica-Bold'))]
        ]
        story.append(Table(header_data, colWidths=[19*cm]))
        story.append(Spacer(1, 0.5*cm))

        # Seções
        # Reposiciona todo o bloco relativo ao início do conteúdo após o cabeçalho
        y = content_start_y - 0.9*cm

        c.setFont("Helvetica-Bold", 10)
        c.drawString(2*cm, y, "1-FONTE PAGADORA PESSOA JURÍDICA"); c.drawString(13*cm, y, "2-NÚMERO DO CNPJ")
        c.setFont("Helvetica", 9)
        y -= 0.5*cm
        c.drawString(2*cm, y, "Razão Social/Nome")
        c.setFont("Helvetica-Bold", 9)
        y -= 0.5*cm
        c.drawString(2*cm, y, "PRO-GESTAO")
        c.setFont("Helvetica", 9)

        # --- AJUSTE DO CNPJ ---
        # Desenha o retângulo (borda) e o texto do CNPJ mais à direita
        c.rect(13*cm, y - 0.1*cm, 4.5*cm, 0.7*cm, stroke=1, fill=0)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(13.2*cm, y + 0.2*cm, "05.140.324/0001-49")
        c.setFont("Helvetica", 9)
        y -= 0.7*cm
        c.drawString(2*cm, y, "Endereço")
        c.setFont("Helvetica-Bold", 9)
        y -= 0.5*cm
        c.drawString(2*cm, y, "ANEXO DO PALACIO DO BURITI - EIXO MONUMENTAL - SALA 601")
        c.setFont("Helvetica", 9)
        y -= 0.5*cm
        c.drawString(2*cm, y, "Cidade") 
        c.drawString(13*cm, y, "UF")
        c.setFont("Helvetica-Bold", 9)
        y -= 0.5*cm
        c.drawString(2*cm, y, "BRASILIA") 
        c.drawString(13*cm, y, "DF")

        c.setFont("Helvetica-Bold", 10)
        y -= 1.0*cm
        c.drawString(2*cm, y, "3-PESSOA FÍSICA BENEFICIÁRIA DO PAGAMENTO");
        c.setFont("Helvetica", 9)
        y -= 0.5*cm
        c.drawString(2*cm, y, "Ano Base"); c.drawString(5*cm, y, "CPF"); c.drawString(9*cm, y, "Nome Completo")
        c.setFont("Helvetica-Bold", 9)
        y -= 0.5*cm
        c.drawString(2*cm, y, str(ano_calendario))
        c.drawString(5*cm, y, str(cpf_beneficiario))
        c.drawString(9*cm, y, str(nome_beneficiario))
        c.setFont("Helvetica", 9)
        y -= 1.0*cm
        c.drawString(2*cm, y, "Natureza do Rendimento")
        c.setFont("Helvetica-Bold", 9)
        y -= 0.5*cm
        c.drawString(2*cm, y, "PAGAMENTOS DE SERVIDORES PÚBLICOS EFETIVOS E TEMPORÁRIOS")

        c.setFont("Helvetica-Bold", 10)
        y -= 1.0*cm
        c.drawString(2*cm, y, "4-DETALHAMENTO DOS RENDIMENTOS"); c.drawString(16*cm, y, "Em R$")
        c.setFont("Helvetica", 9)
        y -= 0.5*cm
        c.drawString(2*cm, y, "01 - VALOR BRUTO DO PERÍODO")
        c.setFont("Helvetica-Bold", 9)
        c.drawRightString(18*cm, y, f"{total_bruto:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        c.setFont("Helvetica", 9)
        y -= 0.5*cm
        c.drawString(2*cm, y, "02 - IR RETIDO NO PERÍODO")
        c.setFont("Helvetica-Bold", 9)
        c.drawRightString(18*cm, y, f"{ir_retido:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        y -= 0.5*cm
        c.drawString(2*cm, y, "03 - VALOR LÍQUIDO NO PERÍODO")
        c.setFont("Helvetica-Bold", 9)
        c.drawRightString(18*cm, y, f"{total_liquido:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        c.setFont("Helvetica", 9)

        c.setFont("Helvetica-Bold", 10)
        y -= 1.0*cm
        c.drawString(2*cm, y, "5-RESPONSÁVEL PELAS INFORMAÇÕES")
        c.setFont("Helvetica", 9)
        y -= 0.5*cm
        c.drawString(2*cm, y, "NOME"); c.drawString(12*cm, y, "DATA")
        c.setFont("Helvetica-Bold", 9)
        y -= 0.5*cm
        c.drawString(2*cm, y, str(nome_responsavel)); c.drawString(12*cm, y, datetime.now().strftime("%d/%m/%Y"))

        # Salva o PDF e informa sucesso
        c.save()
        messagebox.showinfo("Sucesso", f"Comprovante de rendimentos salvo em:\n{save_path}", parent=parent_window)
        parent_window.destroy()
        return "SUCCESS"
    except sqlite3.Error as e:
        messagebox.showerror("Erro de Banco de Dados", f"Ocorreu um erro ao acessar o banco de dados: {e}", parent=parent_window)
        return "ERROR"
    except Exception as e:
        messagebox.showerror("Erro Inesperado", f"Ocorreu um erro ao gerar o comprovante: {e}", parent=parent_window)
        return "ERROR"