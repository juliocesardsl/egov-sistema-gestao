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

# Configura o locale para português do Brasil para formatar a data
try:
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_TIME, 'Portuguese_Brazil.1252')
    except locale.Error:
        print("Locale pt_BR não encontrado, usando o padrão do sistema.")

# ================================================================================================= #
# FUNÇÃO AUXILIAR PARA CAMINHOS DE ARQUIVOS (PARA O EXECUTÁVEL)
# ================================================================================================= #
def resource_path(relative_path):
    """ Obtém o caminho absoluto para o recurso, funciona para dev e para PyInstaller """
    try:
        # PyInstaller cria uma pasta temp e armazena o caminho em _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def gerar_documento_empenho(mes_inicial, mes_final, save_path):
    """
    Gera um documento PDF com o Resumo de Despesa Pessoal, seguindo o modelo fornecido.
    """
    conn = None
    try:
        ref_inicial_fmt = f"{mes_inicial[3:7]}/{mes_inicial[0:2]}"
        ref_final_fmt = f"{mes_final[3:7]}/{mes_final[0:2]}"

        conn = sqlite3.connect(resource_path('banco.db')) 
        cursor = conn.cursor()

        cursor.execute("""
            SELECT 
                SUM(valor_bruto) as valor_bruto,
                SUM(valor_ir_retido) as ir_retido,
                SUM(valor_liquido) as valor_liquido
            FROM pagamentos_instrutores
            WHERE
                (SUBSTR(mes_referencia, -4) || '/' || SUBSTR(mes_referencia, 1, 2)) BETWEEN ? AND ?
        """, (ref_inicial_fmt, ref_final_fmt))

        dados_agregados = cursor.fetchone()

        if not dados_agregados or dados_agregados[0] is None:
            messagebox.showinfo("Sem Dados", f"Nenhum pagamento encontrado no período de {mes_inicial} a {mes_final}.")
            return "NO_DATA"

        # Query 2: Buscar os dados detalhados para o anexo
        cursor.execute("""
            SELECT
                s.nome as nome_servidor,
                p.valor_liquido as valor,
                s.cpf,
                '0' as menor_ou_incapaz,
                s.agencia,
                s.numero_conta,
                s.numero_banco,
                'C' as tipo_conta,
                NULL as rep_nome,
                NULL as rep_cpf,
                NULL as rep_agencia,
                NULL as rep_conta,
                NULL as rep_banco,
                NULL as rep_tipo_conta
            FROM pagamentos_instrutores p
            JOIN servidores s ON p.servidor_id = s.id
            WHERE (SUBSTR(p.mes_referencia, 4, 4) || '/' || SUBSTR(p.mes_referencia, 1, 2)) BETWEEN ? AND ?
            ORDER BY s.nome
        """, (ref_inicial_fmt, ref_final_fmt))
        pagamentos_detalhados = cursor.fetchall()

        total_bruto, total_ir, total_liquido = [val or 0.0 for val in dados_agregados]
        total_descontos = total_ir  # IR é o único desconto no sistema atual

        def format_value(value):
            return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

        nome_arquivo = f"Documento_Empenho_{mes_inicial.replace('/', '-')}_a_{mes_final.replace('/', '-')}.pdf"
        caminho_completo = os.path.join(save_path, nome_arquivo)
        doc = SimpleDocTemplate(caminho_completo, pagesize=letter, topMargin=3*cm, bottomMargin=1*cm, leftMargin=1*cm, rightMargin=1*cm)
        
        styles = getSampleStyleSheet()
        style_center_bold = ParagraphStyle(name='CenterBold', parent=styles['Normal'], alignment=TA_CENTER, fontName='Helvetica-Bold')
        style_center = ParagraphStyle(name='Center', parent=styles['Normal'], alignment=TA_CENTER)
        style_left = ParagraphStyle(name='Left', parent=styles['Normal'], alignment=TA_LEFT)
        style_right = ParagraphStyle(name='Right', parent=styles['Normal'], alignment=TA_RIGHT)
        style_right_bold = ParagraphStyle(name='RightBold', parent=styles['Normal'], alignment=TA_RIGHT, fontName='Helvetica-Bold')

        story = []

        # Cabeçalho
        header_data = [
            [Paragraph("RESUMO DE DESPESA PESSOAL E ENCARGOS SOCIAIS", style_center_bold)]
        ]
        story.append(Table(header_data, colWidths=[19*cm]))
        story.append(Spacer(1, 0.5*cm))

        # Informações da Folha
        mes_competencia = mes_inicial if mes_inicial == mes_final else f"{mes_inicial} a {mes_final}"
        info_data = [
            [Paragraph("UNIDADE: SEEC", style_left), Paragraph(f"MÊS DE COMPETÊNCIA: {mes_competencia}", style_center),],
            [Paragraph("PAGAMENTO DE INSTRUTORES", style_left), Paragraph(f"MÊS DE APROPRIAÇÃO: {mes_competencia}", style_center),]
        ]
        story.append(Table(info_data, colWidths=[6.3*cm, 6.4*cm, 6.3*cm]))
        story.append(Spacer(1, 0.5*cm))

        # Valores Resumidos
        valores_resumo_data = [
            [Paragraph("VALOR BRUTO", style_left), Paragraph(f"R$ {format_value(total_bruto)}", style_right_bold)],
            [Paragraph("SALDO A EMPENHAR", style_left), Paragraph(f"R$ {format_value(total_liquido)}", style_right_bold)],
            [Paragraph("VALOR A LIBERAR", style_left), Paragraph(f"R$ {format_value(total_liquido)}", style_right_bold)]
        ]
        story.append(Table(valores_resumo_data, colWidths=[15*cm, 4*cm]))
        story.append(Spacer(1, 0.5*cm))

        # Título movido para cima, conforme solicitado
        story.append(Paragraph("DEMONSTRATIVO DE APROPRIAÇÃO DA DESPESA", style_center_bold))
        story.append(Spacer(1, 0.5*cm))

        # Tabelas de Elementos
        elementos_data = [
            [Paragraph("<b>ELEMENTO</b>", style_center), Paragraph("<b>VALOR</b>", style_center), Paragraph("<b>FTE</b>", style_center)],
            
            ["339014/93", format_value(total_liquido), "100"],
            ["339018/19/48", "0,00", "0"],
            ["339033/49",    "0,00", "0"],
            ["339036",       "0,00", "0"],
            ["339046/47",    "0,00", "0"],
            ["339091/92",    "0,00", "0"]
        ]
        # Largura da coluna FTE ajustada para 1.5cm para evitar quebra de linha
        tabela_elementos = Table(elementos_data, colWidths=[2.5*cm, 2*cm, 1.5*cm] * 3, hAlign='CENTER')
        tabela_elementos.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 1, colors.black),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(tabela_elementos)
        story.append(Spacer(1, 1*cm))

        # Tabela unificada de Detalhamento, Totais e Responsável
        story.append(Paragraph("DETALHAMENTO DA FOLHA DE PAGAMENTO", style_center))
        story.append(Spacer(1, 0.5*cm))

        # --- Célula [0,0]: Detalhes da folha ---
        detalhes_content = [
            [Paragraph("VALOR BRUTO", style_left), Paragraph(format_value(total_bruto), style_right)],
            [Paragraph("IR RETIDO", style_left), Paragraph(format_value(total_ir), style_right)],
            [Paragraph("TOTAL DE DESCONTOS", style_left), Paragraph(format_value(total_descontos), style_right)],
            [Paragraph("TOTAL LÍQUIDO", style_left), Paragraph(format_value(total_liquido), style_right)],
        ]
        detalhes_table = Table(detalhes_content, colWidths=[6.5*cm, 2.5*cm])

        # --- Célula [0,1]: Pagamento indevido ---
        # indevido_content = [[Paragraph("PAGAMENTO INDEVIDO", style_left), Paragraph("0,00", style_right)]]
        # indevido_table = Table(indevido_content, colWidths=[6.5*cm, 2.5*cm])

        # --- Célula [1,0]: IR Retido ---
        ir_table = Table([[Paragraph("<b>IR RETIDO</b>", style_center)], [Paragraph(format_value(total_ir), style_center)]], colWidths=[9*cm])

        # --- Célula [1,1]: Total Líquido ---
        liquido_content = [
            [Paragraph("<b>TOTAL LÍQUIDO</b>", style_center)],
            [Paragraph(format_value(total_liquido), style_center)]
        ]
        liquido_table = Table(liquido_content, colWidths=[9*cm])

        # --- Célula [2,0] (mesclada): Responsável e Telefone ---
        responsavel_table = Table([[Paragraph("RESPONSÁVEL:", style_left), Paragraph("TELEFONE:", style_right)]], colWidths=[9.5*cm, 9.5*cm])

        # --- Montagem da tabela principal ---
        tabela_principal_data = [
            [detalhes_table],
            [ir_table, liquido_table],
            [responsavel_table, '']
        ]
        tabela_principal = Table(tabela_principal_data, colWidths=[9.5*cm, 9.5*cm], rowHeights=[3*cm, 2*cm, 1*cm])
        tabela_principal.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 1, colors.black),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('SPAN', (0,2), (1,2)), # Mescla a última linha
            ('VALIGN', (0,2), (0,2), 'MIDDLE'),
        ]))
        story.append(tabela_principal)

        # --- ANEXO COM DETALHAMENTO ---
        if pagamentos_detalhados:
            story.append(PageBreak())

            # Estilos específicos para o anexo com fonte menor
            style_anexo_header = ParagraphStyle(name='AnexoHeader', parent=styles['Normal'], alignment=TA_CENTER, fontName='Helvetica-Bold', fontSize=7)
            style_anexo_left = ParagraphStyle(name='AnexoLeft', parent=styles['Normal'], alignment=TA_LEFT, fontSize=7)
            style_anexo_center = ParagraphStyle(name='AnexoCenter', parent=styles['Normal'], alignment=TA_CENTER, fontSize=7)
            style_anexo_right = ParagraphStyle(name='AnexoRight', parent=styles['Normal'], alignment=TA_RIGHT, fontSize=7)

            # Título do anexo
            story.append(Paragraph("ANEXO - DETALHAMENTO PARA CRÉDITO EM CONTA", style_center_bold))
            story.append(Spacer(1, 0.5*cm))

            # Montagem da tabela de detalhes
            dados_detalhes = []
            header_detalhes = [
                Paragraph("<b>Nome do Servidor</b>", style_anexo_header),
                Paragraph("<b>CPF</b>", style_anexo_header),
                Paragraph("<b>Banco</b>", style_anexo_header),
                Paragraph("<b>Agência</b>", style_anexo_header),
                Paragraph("<b>Conta</b>", style_anexo_header),
                Paragraph("<b>Tipo Conta</b>", style_anexo_header),
                Paragraph("<b>Valor (R$)</b>", style_anexo_header)
            ]
            dados_detalhes.append(header_detalhes)

            for p in pagamentos_detalhados:
                (nome_servidor, valor, cpf, menor, ag, conta, banco, tipo_conta,
                 _, _, _, _, _, _) = p

                dados_detalhes.append([
                    Paragraph(nome_servidor or '', style_anexo_left),
                    Paragraph(cpf or 'N/A', style_anexo_center),
                    Paragraph(banco or 'N/A', style_anexo_center),
                    Paragraph(ag or 'N/A', style_anexo_center),
                    Paragraph(conta or 'N/A', style_anexo_center),
                    Paragraph(tipo_conta or 'N/A', style_anexo_center),
                    Paragraph(format_value(valor or 0.0), style_anexo_right)
                ])

            # Larguras ajustadas para que a tabela se ajuste à largura da página (A4 retrato)
            col_widths = [6*cm, 3*cm, 2*cm, 2*cm, 2*cm, 1.5*cm, 2.5*cm]
            tabela_detalhes = Table(dados_detalhes, colWidths=col_widths, hAlign='CENTER')
            tabela_detalhes.setStyle(TableStyle([
                ('GRID', (0,0), (-1,-1), 1, colors.black),
                ('BACKGROUND', (0,0), (-1,0), colors.grey),
                ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('ALIGN', (0,1), (1,-1), 'LEFT'),
                ('ALIGN', (2,1), (-2,-1), 'CENTER'), # Alinha do CPF até a penúltima
                ('ALIGN', (-1,1), (-1,-1), 'RIGHT'), # Alinha a última (Valor)
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey]),
            ]))
            story.append(tabela_detalhes)

        # Callback para desenhar cabeçalho nas páginas geradas pelo Platypus
        def _on_page(canvas_obj, doc_obj):
            # desenha o cabeçalho e retorna y para conteúdo (não usado aqui diretamente)
            draw_header(canvas_obj, doc_obj.pagesize[0], doc_obj.pagesize[1], logo_path=os.path.join(os.path.dirname(__file__), 'Brasão_do_Distrito_Federal_Brasil.png'), title_lines=default_titles())

        doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
        
        messagebox.showinfo("Sucesso", f"Documento de empenho gerado com sucesso em:\n{caminho_completo}")
        return "SUCCESS"
    except sqlite3.Error as e:
        messagebox.showerror("Erro de Banco de Dados", f"Ocorreu um erro ao acessar o banco de dados: {e}")
        return "ERROR"
    except Exception as e:
        messagebox.showerror("Erro Inesperado", f"Ocorreu um erro ao gerar o documento: {e}")
        return "ERROR"
    finally:
        if conn:
            conn.close()