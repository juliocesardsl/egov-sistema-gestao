import unidecode
import sqlite3
import os
import sys

# ================================================================================================= #
# FUNÇÃO AUXILIAR PARA CAMINHOS DE ARQUIVOS (PARA O EXECUTÁVEL)
# ================================================================================================= #
def resource_path(relative_path):
    """ Obtém o caminho absoluto para o recurso, funciona para dev e para PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def gerar_fita_credito_txt(mes_referencia, save_path):

    def remover_acentos_e_cedilha(texto):
        if not texto:
            return ""
        return unidecode.unidecode(texto)

    nome_arquivo = f"Fita_Credito_{mes_referencia.replace('/', '')}.txt"
    caminho_completo = os.path.join(save_path, nome_arquivo)

    conn = sqlite3.connect(resource_path('banco.db'))
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            '32098',
            '000',
            '1', 
            '2',
            b.identidade,
            b.nome,
            p.valor_liquido,
            SUBSTR(b.numero_conta, 1, LENGTH(b.numero_conta)-1), 
            SUBSTR(b.numero_conta, -1), 
            NULL,                      
            NULL,
            b.numero_banco,
            b.agencia,
            NULL,
            b.cpf
        FROM pagamentos_instrutores p
        JOIN servidores b ON p.servidor_id = b.id
        WHERE p.mes_referencia = ?
    """, (mes_referencia,))
    registros = cursor.fetchall()
    
    # Debug: Print the first record to see what we're getting
    if registros:
        print("Primeiro registro encontrado:")
        print(f"Campos 8 (conta) e 9 (dígito): {registros[0][7]}, {registros[0][8]}")
        print(f"Registro completo: {registros[0]}")
    conn.close()

    if registros:
        qtd_registros = len(registros)
        valor_total_creditos = sum(
            float(r[6]) if r[6] not in (None, '', ' ') else 0.0
            for r in registros
        )
        cabecalho = (
            "32098" +                                       # Código do Órgão (5)
            "001" +                                         # Código da Folha (3)
            '1' +                                           # Informa "1" (1)
            str(mes_referencia[:2]).zfill(2) +              # Mês de referência (2)
            str(mes_referencia[-4:]).zfill(4) +             # Ano de referência (4)
            "01" +                                          # Tipo de Pagamento (2)
            "GEEC INSTRUTORIA".ljust(20) +                  # Descrição do Pagamento (20)
            str(qtd_registros).zfill(6) +                   # Quantidade de registro (6)
            str(int(valor_total_creditos * 100)).zfill(14) + # Valor total do crédito (14)
            ''.ljust(38)                                    # Informar brancos (38)
        )
    else:
        cabecalho = ""
        registros = []

    with open(caminho_completo, "w", encoding="ascii", errors="ignore") as f:
        if cabecalho:
            f.write(cabecalho + "\n")

        for reg in registros:
            valor = reg[6] if reg[6] is not None else 0
            nome_sem_acentos = remover_acentos_e_cedilha(reg[5])

            linha = (
                "32098" +                                               # Código do órgão (5)
                "001" +                                                 # Código da folha (3)
                '2' +                                                   # Informa "2" (1)
                '00000000' +                                            # Matrícula do servidor (8)
                nome_sem_acentos.ljust(37)[:37] +                       # Nome do servidor (37)
                str(int(float(valor) * 100)).zfill(10) +                # Valor do pagamento (10)
                str(reg[7] or '').replace(' ', '').replace('-', '').replace('.', '').zfill(9) +  # Número da conta corrente (9)
                str(reg[8] or '').replace(' ', '').replace('-', '').replace('.', '').zfill(1) +  # Dígito da conta corrente (1)
                '0' +                                                   # Tipo da conta corrente (1)
                '070' +                                                 # Banco de pagamento (3)
                str(reg[12] or '0212').zfill(4) +                      # Agência de pagamento (4)
                'DF' +                                                  # UF da agência de pagamento (2)
                str(reg[14] or '').replace(".", "").replace("-", "").zfill(11) # CPF do servidor (11)
            )
            f.write(linha + "\n")

        if registros:
            valor_total_creditos = sum(float(r[6]) if r[6] not in (None, '', ' ') else 0.0 for r in registros)
            trailer = (
                "32098" +                                       # Código do órgão (5)
                "001" +                                         # Código da folha (3)
                '3' +                                           # Informa "3" (1)
                str(len(registros)).zfill(6) +                  # Quantidade de registros (6)
                str(int(valor_total_creditos * 100)).zfill(14) + # Valor total dos créditos (14)
                ''.ljust(66)                                    # Informar brancos (66)
            )
            f.write(trailer + "\n")

    print(f"Fita de crédito gerada: {caminho_completo}")