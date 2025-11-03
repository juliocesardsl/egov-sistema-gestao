import bcrypt
import customtkinter as ctk
import tkinter as tk
from tkinter import ttk
from customtkinter import CTkImage
from tkinter import messagebox
from datetime import datetime
from tkinter.ttk import *
from tkinter import *
from tkcalendar import Calendar
import sqlite3
import subprocess
import os
import sys
import re
from tkinter import filedialog
import pandas as pd
from customtkinter import CTkScrollableFrame
from database_manager import execute_query
from gerar_empenho import gerar_documento_empenho
from gerar_rendimento import gerar_comprovante_rendimentos_pdf, resource_path


usuario_logado = ""
id_usuario_logado = None
perfil_usuario_logado = ""

#==========================================================================================#

BANCOS = {
    "001": "Banco do Brasil",
    "033": "Santander",
    "070": "Banco de Brasília",
    "077": "Banco Inter",
    "104": "Caixa Econômica Federal",
    "237": "Bradesco",
    "260": "Nu Pagamentos S.A. (Nubank)",
    "341": "Itaú Unibanco",
}

#==========================================================================================#

def atualizarListaUsuarios(frame):
    for widget in frame.winfo_children():
        widget.destroy()

    query = """
        SELECT 
            u.id_usuario, 
            u.nome_usuario, 
            u.status
        FROM users u
        """
    usuarios = execute_query(query, fetch='all')
    if not usuarios: usuarios = []

    # Botão para cadastrar novo usuário
    botao_cadastro = tk.Button(frame, text="Cadastrar Novo Usuário", command=lambda: abrirCadastroUsuario(frame))
    botao_cadastro.grid(row=0, column=0, columnspan=4, pady=10)

    for idx, (id_usuario, nome_usuario, status) in enumerate(usuarios, start=1):
        label = tk.Label(
            frame,
            text=f"{nome_usuario} - {status}",
            anchor="w",
            font=("Calibri", 10, "bold")
        )
        label.grid(row=idx, column=0, padx=10, pady=5, sticky="w")


        botao_status = tk.Button(
            frame, text="Desativar" if status == "ATIVO" else "Ativar",
            command=lambda id_usuario=id_usuario, status=status: alterarStatusUsuario(id_usuario, frame, status)
        )
        botao_status.grid(row=idx, column=1, padx=10, pady=5)

        botao_editar = tk.Button(
            frame, text="Editar",
            command=lambda id_usuario=id_usuario, nome_atual=nome_usuario: editarUsuario(id_usuario, nome_atual, frame)
        )
        botao_editar.grid(row=idx, column=2, padx=10, pady=5)

def alterarStatusUsuario(id_usuario, frame, status_atual):
    novo_status = "DESATIVADO" if status_atual == "ATIVO" else "ATIVO"
    execute_query("UPDATE users SET status = ? WHERE id_usuario = ?", (novo_status, id_usuario))
    atualizarListaUsuarios(frame)

def hash_senha(senha):
    """Gera um hash seguro para a senha."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(senha.encode('utf-8'), salt).decode('utf-8')

def cadastrarUsuario(nome_usuario, senha, nome_completo, num_matr, perfil, janela, frame):
    if not (nome_usuario.strip() and senha.strip() and nome_completo.strip() and num_matr.strip() and perfil.strip()):
        messagebox.showerror("Erro", "Todos os campos são obrigatórios!")
        return
    
    senha_hash = hash_senha(senha)  # Criptografa a senha antes de salvar

    query = '''INSERT INTO users (nome_usuario, senha, status, nome_completo, num_matr, perfil) 
                      VALUES (?, ?, 'ATIVO', ?, ?, ?)''', 
    params = (nome_usuario, senha_hash, nome_completo, num_matr, perfil)
    execute_query(query, params)

    messagebox.showinfo("Sucesso", "Usuário cadastrado com sucesso!")
    janela.destroy()
    atualizarListaUsuarios(frame)

def editarUsuario(id_usuario, nome_atual, frame):
    # Buscar os dados atuais do usuário
    query = "SELECT nome_usuario, senha, nome_completo, num_matr, perfil, status FROM users WHERE id_usuario = ?"
    usuario = execute_query(query, (id_usuario,), fetch='one')

    if not usuario:
        messagebox.showerror("Erro", "Usuário não encontrado!")
        return

    nome_atual, senha_atual, nome_completo_atual, num_matr_atual, perfil_atual, status_atual = usuario

    # Criar janela de edição
    janela_editar = tk.Toplevel()
    janela_editar.title("Editar Usuário")
    janela_editar.geometry('350x450')

    # Campos de edição
    tk.Label(janela_editar, text="Nome de usuário:").pack(pady=5)
    entrada_nome = tk.Entry(janela_editar, width=30)
    entrada_nome.insert(0, nome_atual)
    entrada_nome.pack(pady=5)

    tk.Label(janela_editar, text="Senha:").pack(pady=5)
    entrada_senha = tk.Entry(janela_editar, width=30, show="*")
    entrada_senha.pack(pady=5)

    tk.Label(janela_editar, text="Nome Completo:").pack(pady=5)
    entrada_nome_completo = tk.Entry(janela_editar, width=30)
    entrada_nome_completo.insert(0, nome_completo_atual)
    entrada_nome_completo.pack(pady=5)

    tk.Label(janela_editar, text="Número de Matrícula:").pack(pady=5)
    entrada_matr = tk.Entry(janela_editar, width=30)
    entrada_matr.insert(0, num_matr_atual)
    entrada_matr.pack(pady=5)

    # Combobox para Perfil
    tk.Label(janela_editar, text="Perfil:").pack(pady=5)
    entrada_perfil = ttk.Combobox(janela_editar, values=["1 - Administrador", "2 - Usuário Padrão"], state="readonly", width=27)
    entrada_perfil.pack(pady=5)
    
    # Selecionar o perfil atual do usuário
    if perfil_atual == "1":
        entrada_perfil.current(0)  # Administrador
    elif perfil_atual == "2":
        entrada_perfil.current(1)  # Usuário Padrão

    # Combobox para Status
    tk.Label(janela_editar, text="Status:").pack(pady=5)
    status_combo = ttk.Combobox(janela_editar, values=["ATIVO", "DESATIVADO"], state="readonly")
    status_combo.set(status_atual)
    status_combo.pack(pady=5)

    def salvar_edicao():
        novo_nome = entrada_nome.get().strip()
        nova_senha = entrada_senha.get().strip()
        novo_nome_completo = entrada_nome_completo.get().strip()
        novo_matr = entrada_matr.get().strip()
        novo_perfil = entrada_perfil.get().split(" - ")[0]  # Pegando apenas o número do perfil
        novo_status = status_combo.get()

        if not (novo_nome and novo_nome_completo and novo_matr and novo_perfil):
            messagebox.showerror("Erro", "Todos os campos são obrigatórios!")
            return

        senha_hash = hash_senha(nova_senha) if nova_senha else senha_atual  # Só altera a senha se o campo não estiver vazio

        query_update = """
            UPDATE users 
            SET nome_usuario = ?, senha = ?, nome_completo = ?, num_matr = ?, perfil = ?, status = ?
            WHERE id_usuario = ?
        """
        params_update = (novo_nome, senha_hash, novo_nome_completo, novo_matr, novo_perfil, novo_status, id_usuario)
        execute_query(query_update, params_update)

        messagebox.showinfo("Sucesso", "Usuário atualizado com sucesso!")
        janela_editar.destroy()
        atualizarListaUsuarios(frame)

    # Botões
    tk.Button(janela_editar, text="Salvar Alterações", command=salvar_edicao).pack(pady=10)
    tk.Button(janela_editar, text="Cancelar", command=janela_editar.destroy).pack(pady=5)

def abrirCadastroUsuario(frame):
    janela_cadastro = tk.Toplevel()
    janela_cadastro.title("Cadastrar Novo Usuário")
    janela_cadastro.geometry("300x400")

    tk.Label(janela_cadastro, text="Nome de usuário:").pack(pady=5)
    entrada_nome = tk.Entry(janela_cadastro, width=30)
    entrada_nome.pack(pady=5)

    tk.Label(janela_cadastro, text="Senha:").pack(pady=5)
    entrada_senha = tk.Entry(janela_cadastro, width=30, show="*")
    entrada_senha.pack(pady=5)

    tk.Label(janela_cadastro, text="Nome Completo:").pack(pady=5)
    entrada_nome_completo = tk.Entry(janela_cadastro, width=30)
    entrada_nome_completo.pack(pady=5)

    tk.Label(janela_cadastro, text="Número de Matrícula:").pack(pady=5)
    entrada_matr = tk.Entry(janela_cadastro, width=30)
    entrada_matr.pack(pady=5)

    tk.Label(janela_cadastro, text="Perfil:").pack(pady=5)
    entrada_perfil = ttk.Combobox(janela_cadastro, values=["1 - Administrador", "2 - Usuário Padrão"], state="readonly", width=27)
    entrada_perfil.pack(pady=5)
    entrada_perfil.current(1)  # Define a opção padrão como "Usuário Padrão"

    botao_cadastrar = tk.Button(janela_cadastro, text="Cadastrar", 
                                command=lambda: cadastrarUsuario(
                                    entrada_nome.get(), entrada_senha.get(), 
                                    entrada_nome_completo.get(), entrada_matr.get(), 
                                    entrada_perfil.get().split(" - ")[0],  # Pegando apenas o número do perfil
                                    janela_cadastro, frame))
    botao_cadastrar.pack(pady=10)

    tk.Button(janela_cadastro, text="Cancelar", command=janela_cadastro.destroy).pack(pady=5)

def abrirTelaUsuarios():
    janela_usuarios = tk.Toplevel()
    janela_usuarios.title("Usuários do Sistema")
    janela_usuarios.geometry("500x400")
    janela_usuarios.resizable(False, False)

    frame_usuarios = CTkScrollableFrame(janela_usuarios, width=480, height=340, corner_radius=10)
    frame_usuarios.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    atualizarListaUsuarios(frame_usuarios)
    
#==========================================================================================#

def configurar_estilo_treeview():
    """Configura um estilo global para todos os Treeviews da aplicação."""
    style = ttk.Style()
    # Usar um tema que permita customização (clam, alt, default)
    style.theme_use("default")
    
    # Configuração do estilo principal do Treeview
    style.configure("Treeview",
                    background="#ffffff",
                    foreground="black",
                    rowheight=25,
                    fieldbackground="#ffffff")
    
    # Cor de seleção
    style.map('Treeview', background=[('selected', "#49089e")])

    # Configuração do cabeçalho
    style.configure("Treeview.Heading", font=('Calibri', 10, 'bold'))

#==========================================================================================#

def verificar_credenciais_no_banco(usuario, senha):
    query = "SELECT id_usuario, senha, perfil FROM users WHERE nome_usuario = ? AND status = 'ATIVO'"
    resultado = execute_query(query, (usuario,), fetch='one')
    if resultado:
        id_usuario, senha_hash, perfil = resultado
        if bcrypt.checkpw(senha.encode('utf-8'), senha_hash.encode('utf-8')):
            return id_usuario, perfil
    return None, None

#==========================================================================================#

def login():
    def verificar_credenciais():
        global usuario_logado, id_usuario_logado, perfil_usuario_logado
        usuario = entry_usuario.get()
        senha = entry_senha.get()
        id_usuario, perfil_usuario = verificar_credenciais_no_banco(usuario, senha)
        if id_usuario is not None:
            usuario_logado = usuario
            id_usuario_logado = id_usuario
            perfil_usuario_logado = perfil_usuario
            messagebox.showinfo("Sucesso", f"Login realizado com sucesso!\nPerfil: {perfil_usuario_logado}")
            janela_login.destroy()
            exibir_janela_principal()
        else:
            messagebox.showerror("Erro", "Usuário ou senha incorretos!")
            
    def pressionar_enter(event):
        verificar_credenciais()
        
    def fechar_app_login():
        janela_login.destroy()
        sys.exit()
        
    janela_login = ctk.CTk()
    janela_login.title("Login")
    janela_login.geometry("380x340")
    janela_login.resizable(False, False)
    # Paleta personalizada de azul e cinza
    ctk.set_default_color_theme("blue")  # Mantém o tema azul base

    # Frame centralizado para o formulário
    frame_login = ctk.CTkFrame(janela_login, fg_color="#f0f4f8")  # Cinza claro
    frame_login.pack(expand=True, fill="both")

    # Título
    lb_titulo = ctk.CTkLabel(
        frame_login, 
        text="Bem-vindo ao Sistema",
        font=('Calibri', 22, 'bold'),
        text_color="#49089e"  
    )
    lb_titulo.pack(pady=(30, 30))

    # Subtítulo
    lb_sub = ctk.CTkLabel(frame_login, text="Informe suas credenciais", font=('Calibri', 14, 'italic'), text_color="#000000")
    lb_sub.pack(pady=(0, 15))

    # icon_usuario = PhotoImage(file="icons_usuario.png")  # Certifique-se de que o caminho está correto
    # icon_usuario = icon_usuario.subsample(2, 2)  # Reduz o tamanho da imagem
    
    # Usuário
    ctk.CTkLabel(frame_login, text="Usuário:", font=('Calibri', 14), text_color="#000000").pack(pady=(0, 3))
    entry_usuario = ctk.CTkEntry(frame_login, width=220, fg_color="#e3eafc", text_color="#222222", border_color="#6a0ca1")
    entry_usuario.pack(pady=(0, 10))

    # Senha
    ctk.CTkLabel(frame_login, text="Senha:", font=('Calibri', 14), text_color="#000000").pack(pady=(0, 3))
    entry_senha = ctk.CTkEntry(frame_login, show="*", width=220, fg_color="#e3eafc", text_color="#222222", border_color="#6a0ca1")
    entry_senha.pack(pady=(0, 15))

    
    # Botão Login
    ctk.CTkButton(
        frame_login, 
        text="Entrar", 
        command=verificar_credenciais, 
        width=120, 
        fg_color="#49089e", 
        hover_color="#49089e", 
        text_color="#fff", corner_radius=18
    ).pack(pady=(0, 10))

    # Rodapé
    lb_rodape = ctk.CTkLabel(frame_login, text="© 2025 julio.slima - SEEC", font=('Calibri', 10, 'italic'), text_color="#49089e")
    lb_rodape.pack(side="bottom", pady=(10, 0))

    janela_login.bind("<Return>", pressionar_enter)
    janela_login.protocol("WM_DELETE_WINDOW", fechar_app_login)
    janela_login.mainloop()

#==========================================================================================

#/*===============================================================
  
#    ███████╗██╗███████╗███████╗███████╗███████╗██║     ██║        ██╗
#    ██╔════╝██║██╔════╝██╔════╝██╔════╝██║  ██║ ██║   ██║         ██║
#    ███████╗██║███████╗█████╗  ██║ ███╗██║  ██║  ██║ ██║          ██║                               
#    ╚════██║██║╚════██║██╔══╝  ██║ ╚██║██║  ██║   ████║      ██║  ██║  ██║
#    ███████║██║███████║███████╗███████║███████║    ██║         ██║██║██║  
#    ╚══════╝╚═╝╚══════╝╚══════╝╚══════╝╚══════╝    ╚═╝            ██║   
#      >> SisEsc  —  Sistema da Escola de Governo <<


def exibir_janela_principal():
    janelaPrincipal = ctk.CTk()  # Troque CTkToplevel() por CTk()
    janelaPrincipal.title("Sistema EGOV")
    janelaPrincipal.geometry("720x500")
    ctk.set_default_color_theme("blue")  # Mantém o tema azul base
    configurar_estilo_treeview()

    menuBarra = Menu(janelaPrincipal)
    
    menuCadastro = Menu(menuBarra, tearoff=0)
    menuFerramentas = Menu(menuBarra, tearoff=0)
    

    menuCadastro.add_command(label="Cadastrar Usuário", command=abrirTelaUsuarios)
    
    menuFerramentas.add_command(label="Cadastrar Cargo Efetivo", command=cadastrar_cargo_efetivo)
    menuFerramentas.add_command(label="Cadastrar Orgâo de Origem", command=cadastrar_orgao_origem)
    menuFerramentas.add_command(label="Cadastrar Valores do Imposto", command=cadastrar_valores_imposto)
    menuFerramentas.add_command(label="Gerar Pagamento de Instrutor", command=abrir_gerar_pagamento_instrutor)
    menuFerramentas.add_command(label="Gerar Documento de Empenho", command=abrir_gerar_doc_empenho)
    menuFerramentas.add_command(label="Gerar Comprovante de Rendimentos", command=abrir_gerar_comprovante_rendimentos)
    menuFerramentas.add_command(label="Gerar Fita de Crédito", command=janela_gerar_txt_fita_credito)
    menuFerramentas.add_separator()
    menuFerramentas.add_command(label="Listar Pagamentos Gerados", command=listar_pagamentos_gerados)
    menuFerramentas.add_command(label="Listar Cargos Efetivos", command=listar_cargos_efetivos)
    menuFerramentas.add_command(label="Listar Órgãos de Origem", command=listar_orgaos_de_origem)
    menuFerramentas.add_command(label="Gerenciar Tetos de Hora/Aula", command=gerenciar_tetos_hora_aula)
    menuFerramentas.add_command(label="Listar Impostos", command=listar_impostos)

    
    if str(perfil_usuario_logado) == "1":
        menuCadastro.entryconfig("Cadastrar Usuário", state="normal")
        print("passou pelo if")
    else:
        menuCadastro.entryconfig("Cadastrar Usuário", state="disabled")
        print("passou pelo else", perfil_usuario_logado)
        
    menuBarra.add_cascade(label="Cadastro", menu=menuCadastro)
    menuBarra.add_cascade(label="Ferramentas", menu=menuFerramentas)
    
    janelaPrincipal.config(menu=menuBarra)
    
    frame_central = ctk.CTkFrame(janelaPrincipal, fg_color="#f0f4f8")
    frame_central.pack(expand=True, fill="both", padx=1, pady=1)

    # Título centralizado
    lb_titulo = ctk.CTkLabel(
        frame_central,
        text="Painel Inicial",
        font=('Calibri', 22, 'bold'),
        text_color="#49089e"
    )
    lb_titulo.pack(pady=(50, 10))

    # # Usuário logado
    lb_usuario = ctk.CTkLabel(
        frame_central,
        text=f"Usuário logado: 👤 {usuario_logado}",
        font=('Calibri', 14, 'bold'),
        text_color="#000000"
    )
    lb_usuario.pack(pady=(0, 20))

    
    def fechar_app():
        if messagebox.askokcancel("Sair", "Você tem certeza que deseja sair?"):
            janelaPrincipal.destroy()
            sys.exit()
            
    def trocar_usuario():
        if messagebox.askokcancel("Trocar de Usuário", "Você deseja trocar de usuário?"):
            janelaPrincipal.destroy()
            login()
            
    frame_adicionar = ctk.CTkFrame(frame_central, fg_color="transparent")
    frame_adicionar.pack(pady=10)
    
    frame_adicionar2 = ctk.CTkFrame(frame_central, fg_color="transparent")
    frame_adicionar2.pack(pady=10)
    
    frame_sair = ctk.CTkFrame(frame_central, fg_color="transparent")
    frame_sair.pack(pady=50)
    
    
    btn_cadastro_servidor = ctk.CTkButton(frame_adicionar, text="Cadastro de Servidor", width=30, command=cadastro_servidor, fg_color="#49089e", hover_color="#8A2BE2", text_color="#fff", corner_radius=18)
    btn_cadastro_servidor.grid(row=0, column=0, padx=10, pady=5)
    
    
    btn_listar_servidores = ctk.CTkButton(frame_adicionar, text="Listar Servidores", width=30, command=listar_servidores, fg_color="#49089e", hover_color="#8A2BE2", text_color="#fff", corner_radius=18)
    btn_listar_servidores.grid(row=1, column=0, padx=10, pady=5)
    
    btn_listar_impostos = ctk.CTkButton(frame_adicionar2, text="Listar Impostos", width=30, command=listar_impostos, fg_color="#3E3C41", hover_color="#5A565E", text_color="#fff", corner_radius=18)
    btn_listar_impostos.grid(row=0, column=0, padx=10, pady=5)
        
    btn_trocar_usuario = ctk.CTkButton(frame_sair, text="Trocar de Usuário", width=30, command=trocar_usuario, fg_color="#6C2DC7", hover_color="#8A2BE2", text_color="#fff", corner_radius=18)
    btn_trocar_usuario.grid(row=0, column=0, padx=10, pady=5)
    
    
    lb_rodape = ctk.CTkLabel(
        frame_central, text="© 2025 julio.slima - SEEC", font=('Calibri', 10, 'italic'), text_color="#49089e"
    )
    lb_rodape.pack(side="bottom", pady=(10, 0))
    
    janelaPrincipal.protocol("WM_DELETE_WINDOW", fechar_app)
    janelaPrincipal.mainloop()

#==========================================================================================#

def cadastro_servidor():
    def salvar_servidor():
        nome = entry_nome.get().strip()
        cpf = entry_cpf.get().strip()
        identidade = entry_identidade.get().strip()
        orgao_emissor = entry_orgao_emissor.get().strip()
        email = entry_email.get().strip()
        endereco = entry_endereco.get().strip()
        cep = entry_cep.get().strip()
        telefone = entry_telefone.get().strip()
        numero_banco = entry_numero_banco.get().strip()
        descricao_banco = entry_descricao_banco.get().strip()
        agencia = entry_agencia.get().strip()
        numero_conta = entry_numero_conta.get().strip()
        processo_sei = entry_processo_sei.get().strip()
        grau_instrucao = combo_grau_instrucao.get().strip()
        cargo = combo_cargo.get().strip()
        numero_orgao_origem = entry_numero_orgao.get().strip()
        orgao_origem = entry_descricao_orgao.get().strip()
        observacoes = entry_observacoes.get("1.0", tk.END).strip()

        if not nome or not cpf:
            messagebox.showerror("Erro", "Os campos Nome Completo e CPF são obrigatórios!")
            return

        query = '''INSERT INTO servidores (
                nome, cpf, identidade, orgao_emissor, email, endereco, cep, telefone,
                numero_banco, descricao_banco, agencia, numero_conta,
                processo_sei, grau_instrucao, cargo_efetivo, numero_orgao_origem, orgao_de_origem, observacoes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'''
        params = (
                nome, cpf, identidade, orgao_emissor, email, endereco, cep, telefone,
                numero_banco, descricao_banco, agencia, numero_conta, processo_sei, grau_instrucao, cargo, numero_orgao_origem, orgao_origem, observacoes
            )
        
        try:
            execute_query(query, params)
            messagebox.showinfo("Sucesso", "Servidor salvo com sucesso!", parent=janelaServidor)
            janelaServidor.destroy()
        except sqlite3.IntegrityError as e:
            messagebox.showerror("Erro", f"Erro de integridade: O CPF '{cpf}' já pode estar cadastrado.", parent=janelaServidor)
    
    janelaServidor = ctk.CTkToplevel()
    janelaServidor.title("Cadastro de Servidor")
    janelaServidor.geometry("450x700")
    janelaServidor.wm_attributes('-topmost', True)
    ctk.set_default_color_theme("blue")
    
    
    scroll_frame = ctk.CTkScrollableFrame(janelaServidor, width=420, height=650)
    scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)
    
    ctk.CTkLabel(scroll_frame, text="*Nome Completo:").pack(pady=3)
    entry_nome = ctk.CTkEntry(scroll_frame, width=200)
    entry_nome.pack(pady=2)

    ctk.CTkLabel(scroll_frame, text="*CPF:").pack(pady=3)
    entry_cpf = ctk.CTkEntry(scroll_frame, width=200)
    entry_cpf.pack(pady=2)

    ctk.CTkLabel(scroll_frame, text="Identidade:").pack(pady=3)
    entry_identidade = ctk.CTkEntry(scroll_frame, width=200)
    entry_identidade.pack(pady=2)

    ctk.CTkLabel(scroll_frame, text="Órgão Emissor:").pack(pady=3)
    entry_orgao_emissor = ctk.CTkEntry(scroll_frame, width=200)
    entry_orgao_emissor.pack(pady=2)
    
    ctk.CTkLabel(scroll_frame, text="Email:").pack(pady=3)
    entry_email = ctk.CTkEntry(scroll_frame, width=200)
    entry_email.pack(pady=2)

    ctk.CTkLabel(scroll_frame, text="Endereço:").pack(pady=3)
    entry_endereco = ctk.CTkEntry(scroll_frame, width=200)
    entry_endereco.pack(pady=2)

    ctk.CTkLabel(scroll_frame, text="CEP:").pack(pady=3)
    entry_cep = ctk.CTkEntry(scroll_frame, width=200)
    entry_cep.pack(pady=2)

    ctk.CTkLabel(scroll_frame, text="Telefone:").pack(pady=3)
    entry_telefone = ctk.CTkEntry(scroll_frame, width=200)
    entry_telefone.pack(pady=2)

    ctk.CTkLabel(scroll_frame, text="Número do Banco:").pack(pady=3)
    entry_numero_banco = ctk.CTkEntry(scroll_frame, width=200)
    entry_numero_banco.pack(pady=2)
    
    def preencher_agencia(event=None):
        numero_banco = entry_numero_banco.get().strip()
        nome_banco = BANCOS.get(numero_banco, "")
        entry_descricao_banco.delete(0, tk.END)
        entry_descricao_banco.insert(0, nome_banco)
        
    ctk.CTkLabel(scroll_frame, text="Descrição do banco:").pack(pady=3)
    entry_descricao_banco = ctk.CTkEntry(scroll_frame, width=200)
    entry_descricao_banco.pack(pady=2)
    
    ctk.CTkLabel(scroll_frame, text="Agência:").pack(pady=3)
    entry_agencia = ctk.CTkEntry(scroll_frame, width=200)
    entry_agencia.pack(pady=2)
    
    ctk.CTkLabel(scroll_frame, text="Número da Conta:").pack(pady=3)
    entry_numero_conta = ctk.CTkEntry(scroll_frame, width=200)
    entry_numero_conta.pack(pady=2)
    
    ctk.CTkLabel(scroll_frame, text="Grau de Instrução:").pack(pady=3)
    combo_grau_instrucao = ctk.CTkComboBox(scroll_frame, values=["Nível Médio", "Graduação", "Pós-graduação", "Mestrado", "Doutorado"], width=200)
    combo_grau_instrucao.pack(pady=2)
    
    ctk.CTkLabel(scroll_frame, text="Cargo Efetivo:").pack(pady=3)
    # Carrega cargos efetivos do banco para popular o combo
    cargos_rows = execute_query("SELECT descricao_cargo FROM Cargo_Efetivo ORDER BY descricao_cargo", fetch='all')
    cargos = [row[0] for row in cargos_rows] if cargos_rows else []

    if not cargos:
        cargos = ["-- Nenhum cargo cadastrado --"]

    combo_cargo = ctk.CTkComboBox(scroll_frame, values=cargos, width=200)
    combo_cargo.pack(pady=2)
    
    ctk.CTkLabel(scroll_frame, text="Nº Órgão de origem:").pack(pady=3)
    entry_numero_orgao = ctk.CTkEntry(scroll_frame, width=200)
    entry_numero_orgao.pack(pady=2)

    ctk.CTkLabel(scroll_frame, text="Descrição do Órgão:").pack(pady=3)
    entry_descricao_orgao = ctk.CTkEntry(scroll_frame, width=200)
    entry_descricao_orgao.pack(pady=2)

    ctk.CTkLabel(scroll_frame, text="Nº Processo SEI:").pack(pady=3)
    entry_processo_sei = ctk.CTkEntry(scroll_frame, width=200)
    entry_processo_sei.pack(pady=2)

    ctk.CTkLabel(scroll_frame, text="Observação:").pack(pady=3)
    entry_observacoes = tk.Text(scroll_frame, width=38, height=4)
    entry_observacoes.pack(pady=2)

    ctk.CTkButton(scroll_frame, text="Salvar", command=salvar_servidor, width=100, fg_color="#49089e", hover_color="#49089e", text_color="#fff", corner_radius=18).pack(pady=20)
    ctk.CTkButton(scroll_frame, text="Cancelar", width=100, fg_color="#49089e", hover_color="#49089e", text_color="#fff", corner_radius=18, command=janelaServidor.destroy).pack(pady=5)

    def preencher_descricao_orgao(event=None):
        numero = entry_numero_orgao.get().strip()
        if not numero:
            entry_descricao_orgao.delete(0, tk.END)
            return

        row = execute_query("SELECT descricao_orgao FROM orgao_de_origem WHERE numero_orgao = ?", (numero,), fetch='one')
        if row and row[0]:
            entry_descricao_orgao.delete(0, tk.END)
            entry_descricao_orgao.insert(0, str(row[0]))
        else:
            entry_descricao_orgao.delete(0, tk.END)

    entry_numero_orgao.bind("<KeyRelease>", preencher_descricao_orgao)

    def aplicar_mascara_cpf(event):
        valor = entry_cpf.get().replace(".", "").replace("-", "")[:11]
        novo = ""
        if len(valor) > 0:
            novo += valor[:3]
        if len(valor) > 3:
            novo += "." + valor[3:6]
        if len(valor) > 6:
            novo += "." + valor[6:9]
        if len(valor) > 9:
            novo += "-" + valor[9:11]
        entry_cpf.delete(0, tk.END)
        entry_cpf.insert(0, novo)

    def aplicar_mascara_cep(event):
        valor = entry_cep.get().replace("-", "")[:8]
        novo = ""
        if len(valor) > 0:
            novo += valor[:5]
        if len(valor) > 5:
            novo += "-" + valor[5:8]
        entry_cep.delete(0, tk.END)
        entry_cep.insert(0, novo)

    def aplicar_mascara_telefone(event):
        valor = entry_telefone.get().replace("(", "").replace(")", "").replace("-", "").replace(" ", "")[:11]
        novo = ""
        if len(valor) > 0:
            novo += "(" + valor[:2] + ") "
        if len(valor) > 2 and len(valor) <= 7:
            novo += valor[2:6] + "-" + valor[6:10]
        elif len(valor) > 7:
            novo += valor[2:7] + "-" + valor[7:11]
        entry_telefone.delete(0, tk.END)
        entry_telefone.insert(0, novo)

    def aplicar_mascara_numero_banco(event):
        valor = entry_numero_banco.get().replace("-", "")[:3]
        novo = ""
        if len(valor) > 0:
            novo += valor[:3]
        entry_numero_banco.delete(0, tk.END)
        entry_numero_banco.insert(0, novo)
    
    entry_numero_banco.bind("<KeyRelease>", preencher_agencia)
    entry_cpf.bind("<KeyRelease>", aplicar_mascara_cpf)
    entry_cep.bind("<KeyRelease>", aplicar_mascara_cep)
    entry_telefone.bind("<KeyRelease>", aplicar_mascara_telefone)
    entry_numero_banco.bind("<KeyRelease>", aplicar_mascara_numero_banco)
    
    
def listar_servidores():
    query = """
        SELECT 
            id, nome, cpf, identidade, orgao_emissor, email, endereco, cep, telefone,
            numero_banco, descricao_banco, agencia, numero_conta, grau_instrucao, cargo_efetivo, numero_orgao_origem,
            orgao_de_origem, processo_sei, observacoes
        FROM servidores 
    """
    servidores = execute_query(query, fetch='all')
    if not servidores: servidores = []
    
    if not servidores:
        messagebox.showinfo("Info", "Nenhum servidor cadastrado.")
        return
    
    janelaListarServidores = ctk.CTkToplevel()
    janelaListarServidores.title("Lista de Servidores")
    janelaListarServidores.geometry("1100x550")
    janelaListarServidores.wm_attributes('-topmost', True)
    ctk.set_default_color_theme("blue")
    
    main_frame = ctk.CTkFrame(janelaListarServidores)
    main_frame.pack(fill="both", expand=True, padx=10, pady=10)
    main_frame.grid_rowconfigure(0, weight=1)
    main_frame.grid_columnconfigure(0, weight=1)
    
    tree_frame = ctk.CTkFrame(main_frame)
    tree_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
    tree_frame.grid_rowconfigure(0, weight=1)
    tree_frame.grid_columnconfigure(0, weight=1)
    
    style = ttk.Style()
    style.theme_use("default")
    style.configure("Treeview",
                    background="#ffffff",
                    foreground="black",
                    rowheight=25,
                    fieldbackground="#ffffff")
    style.map('Treeview', background=[('selected', "#49089e")])
    style.configure("Treeview.Heading", font=('Calibri', 10, 'bold'))
    
    columns = (
        "ID", "Nome", "CPF", "Identidade", "Órgão Emissor", "Email", "Endereço", "CEP", "Telefone",
        "Número do Banco", "Descrição do Banco", "Agência", "Número da Conta", "Grau de Instrução", "Cargo Efetivo", "Nº Órgão de Origem", "Descrição do Órgão", "Nº Processo SEI", "Observações"
    )
    tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
    
    for col in columns:
        tree.heading(col, text=col, command=lambda c=col: sort_by_column(tree, c, False))
        tree.column(col, width=100, anchor="center")
        
    scrollbar_v = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
    scrollbar_h = ttk.Scrollbar(tree_frame, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=scrollbar_v.set, xscrollcommand=scrollbar_h.set)
    tree.grid(row=0, column=0, sticky="nsew")
    scrollbar_v.grid(row=0, column=1, sticky="ns")
    scrollbar_h.grid(row=1, column=0, sticky="ew")
    
    tree.tag_configure('oddrow', background='#f0f4f8')
    tree.tag_configure('evenrow', background='#ffffff')
    
    for i, servidor in enumerate(servidores):
        servidor = ["" if valor is None else valor for valor in servidor]
        tree.insert("", tk.END, values=servidor, tags=('evenrow' if i % 2 == 0 else 'oddrow',))
        
    def carregar_processos():
        for item in tree.get_children():
            tree.delete(item)
            
        servidores_db = execute_query("""
            SELECT 
                id, nome, cpf, identidade, orgao_emissor, email, endereco, cep, telefone,
                numero_banco, descricao_banco, agencia, numero_conta, grau_instrucao, cargo_efetivo, 
                numero_orgao_origem, orgao_de_origem, processo_sei, observacoes
            FROM servidores ORDER BY nome
        """, fetch='all')
        if not servidores_db:
            return
        
        for i, servidor in enumerate(servidores_db):
            processo_tratado = tuple("" if valor is None else valor for valor in servidor)
            tag = 'evenrow' if i % 2 == 0 else 'oddrow'
            tree.insert("", "end", values=processo_tratado, tags=(tag,))
                
    controls_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
    controls_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=(5,0))
    
    ctk.CTkLabel(controls_frame, text="Filtrar:", font=('Calibri', 12)).pack(side="left", padx=(0,5))
    entry_filtro = ctk.CTkEntry(controls_frame)
    entry_filtro.pack(side="left", fill="x", expand=True)
    
    btn_editar = ctk.CTkButton(controls_frame, text="Editar Selecionado", state="disabled", width=140, fg_color="#FFA500", text_color="black", hover_color="#FF8C00")
    btn_editar.pack(side="right", padx=(10,0))
    
    def double_click_editar(event):
        item_selecionado = tree.selection()
        if not item_selecionado:
            return
        id_servidor = tree.item(item_selecionado[0], "values")[0]
        editar_servidor(id_servidor, carregar_processos)
        
    tree.bind("<Double-1>", double_click_editar)
    
    def exportar_servidores_excel():
        """Exporta os dados dos servidores visíveis na Treeview para um arquivo Excel."""
        colunas = tree["columns"]
        dados = []
        for item_id in tree.get_children():
            dados.append(tree.item(item_id)["values"])

        if not dados:
            messagebox.showinfo("Info", "Não há dados para exportar.", parent=janelaListarServidores)
            return

        df = pd.DataFrame(dados, columns=colunas)

        try:
            filepath = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Arquivos Excel", "*.xlsx"), ("Todos os arquivos", "*.*")],
                title="Salvar Lista de Servidores",
                initialfile="Lista_de_Servidores.xlsx"
            )

            if not filepath:
                return

            df.to_excel(filepath, index=False)
            messagebox.showinfo("Sucesso", f"Dados exportados com sucesso para:\n{filepath}", parent=janelaListarServidores)
        except Exception as e:
            messagebox.showerror("Erro ao Exportar", f"Ocorreu um erro ao salvar o arquivo:\n{e}", parent=janelaListarServidores)

    btn_exportar = ctk.CTkButton(controls_frame, text="Exportar para Excel", command=exportar_servidores_excel, width=140, fg_color="#107C41", hover_color="#149950")
    btn_exportar.pack(side="right", padx=(10,0))

    btn_atualizar = ctk.CTkButton(controls_frame, text="Atualizar", command=carregar_processos, width=100)
    btn_atualizar.pack(side="right", padx=(10,0))

    def abrir_edicao_servidor():
        item_selecionado = tree.selection()
        if not item_selecionado:
            messagebox.showwarning("Aviso", "Selecione um servidor na lista para editar.", parent=janelaListarServidores)
            return
        id_servidor = tree.item(item_selecionado[0], "values")[0]
        editar_servidor(id_servidor, carregar_processos)

    btn_editar.configure(command=abrir_edicao_servidor)

    def filtrar_servidor(event=None):
        filtro = entry_filtro.get().strip().lower()
        carregar_processos() # Recarrega para garantir que todos os itens estão visíveis antes de filtrar
        for item in tree.get_children():
            valores_linha = tree.item(item, "values")
            if not any(filtro in str(valor).lower() for valor in valores_linha):
                tree.detach(item)
                
                
    entry_filtro.bind("<KeyRelease>", filtrar_servidor)
    
    def sort_by_column(tree, col , descending):
        data = [(tree.set(child, col), child) for child in tree.get_children('')]
        
        try:
            data.sort(key=lambda t: float(t[0]) if t[0].replace('.','',1).isdigit() else t[0].lower(), reverse=descending)
        except ValueError:
            data.sort(key=lambda t: t[0].lower(), reverse=descending)
            
        for index, (val, child) in enumerate(data):
            tree.move(child, '', index)
            
        tree.heading(col, command=lambda: sort_by_column(tree, col, not descending))
        
    def on_tree_select(event):
        """Habilita o botão de editar quando um item é selecionado."""
        if tree.selection():
            btn_editar.configure(state="normal")
        else:
            btn_editar.configure(state="disabled")
    tree.bind("<<TreeviewSelect>>", on_tree_select)

def editar_servidor(id_servidor, callback_atualizar):
    # 1. Buscar os dados do servidor no banco
    query_select = """
        SELECT 
            nome, cpf, identidade, orgao_emissor, email, endereco, cep, telefone, 
            numero_banco, descricao_banco, agencia, numero_conta, grau_instrucao, cargo_efetivo, 
            numero_orgao_origem, orgao_de_origem, processo_sei, observacoes
        FROM servidores 
        WHERE id = ?
    """
    dados = execute_query(query_select, (id_servidor,), fetch='one')
    
    if not dados:
        messagebox.showerror("Erro", "Servidor não encontrado!")
        return
    
    # Desempacota os dados para usar na janela de edição
    nome, cpf, identidade, orgao_emissor, email, endereco, cep, telefone, numero_banco, descricao_banco, agencia, numero_conta, grau_instrucao, cargo, numero_orgao, descricao_orgao, processo_sei, observacoes = dados
    
    janelaEditarServidor = ctk.CTkToplevel()
    janelaEditarServidor.title("Editar Servidor")
    janelaEditarServidor.geometry("450x700")
    janelaEditarServidor.wm_attributes('-topmost', True)
    janelaEditarServidor.grab_set()
    ctk.set_default_color_theme("blue")

    def salvar_edicoes():
        novo_nome = entry_nome.get().strip()
        novo_cpf = entry_cpf.get().strip()
        novo_identidade = entry_identidade.get().strip()
        novo_orgao_emissor = entry_orgao_emissor.get().strip()
        novo_email = entry_email.get().strip()
        novo_endereco = entry_endereco.get().strip()
        novo_cep = entry_cep.get().strip()
        novo_telefone = entry_telefone.get().strip()
        novo_numero_banco = entry_numero_banco.get().strip()
        novo_descricao_banco = entry_descricao_banco.get().strip()
        novo_agencia = entry_agencia.get().strip()
        novo_numero_conta = entry_numero_conta.get().strip()
        novo_grau_instrucao = combo_grau_instrucao.get().strip()
        novo_cargo = combo_cargo.get().strip()
        novo_numero_orgao = entry_numero_orgao.get().strip()
        novo_descricao_orgao = entry_descricao_orgao.get().strip()
        novo_processo_sei = entry_processo_sei.get().strip()
        novo_observacoes = entry_observacoes.get("1.0", tk.END).strip()

        if not novo_nome or not novo_cpf:
            messagebox.showerror("Erro", "Os campos Nome Completo e CPF são obrigatórios!", parent=janelaEditarServidor)
            return
        
        query_update = """
            UPDATE servidores SET
                nome = ?, cpf = ?, identidade = ?, orgao_emissor = ?, email = ?, endereco = ?, cep = ?, telefone = ?,
                numero_banco = ?, descricao_banco = ?, agencia = ?, numero_conta = ?, grau_instrucao = ?, cargo_efetivo = ?,
                numero_orgao_origem = ?, orgao_de_origem = ?,
                processo_sei = ?, observacoes = ?
            WHERE id = ?
        """
        params_update = (
            novo_nome, novo_cpf, novo_identidade, novo_orgao_emissor, novo_email, novo_endereco, novo_cep, novo_telefone,
            novo_numero_banco, novo_descricao_banco, novo_agencia, novo_numero_conta, novo_grau_instrucao, novo_cargo,
            novo_numero_orgao, novo_descricao_orgao,
            novo_processo_sei, novo_observacoes, id_servidor
        )

        try:
            execute_query(query_update, params_update)
            messagebox.showinfo("Sucesso", "Servidor atualizado com sucesso!", parent=janelaEditarServidor)
            janelaEditarServidor.destroy()
            callback_atualizar()  # Atualiza a lista após a edição
        except sqlite3.IntegrityError as e:
            messagebox.showerror("Erro", f"Erro ao atualizar servidor: {e}", parent=janelaEditarServidor)
            janelaEditarServidor.destroy()
    
    scroll_frame_edit = ctk.CTkScrollableFrame(janelaEditarServidor, width=420, height=650)
    scroll_frame_edit.pack(fill="both", expand=True, padx=10, pady=10)
    
    ctk.CTkLabel(scroll_frame_edit, text="*Nome Completo:").pack(pady=3)
    entry_nome = ctk.CTkEntry(scroll_frame_edit, width=200)
    entry_nome.insert(0, str(nome) if nome is not None else "")
    entry_nome.pack(pady=2)

    ctk.CTkLabel(scroll_frame_edit, text="*CPF:").pack(pady=3)
    entry_cpf = ctk.CTkEntry(scroll_frame_edit, width=200)
    entry_cpf.insert(0, str(cpf) if cpf is not None else "")
    entry_cpf.pack(pady=2)

    ctk.CTkLabel(scroll_frame_edit, text="Identidade:").pack(pady=3)
    entry_identidade = ctk.CTkEntry(scroll_frame_edit, width=200)
    entry_identidade.insert(0, str(identidade) if identidade is not None else "")
    entry_identidade.pack(pady=2)

    ctk.CTkLabel(scroll_frame_edit, text="Órgão Emissor:").pack(pady=3)
    entry_orgao_emissor = ctk.CTkEntry(scroll_frame_edit, width=200)
    entry_orgao_emissor.insert(0, str(orgao_emissor) if orgao_emissor is not None else "")
    entry_orgao_emissor.pack(pady=2)
    
    ctk.CTkLabel(scroll_frame_edit, text="Email:").pack(pady=3)
    entry_email = ctk.CTkEntry(scroll_frame_edit, width=200)
    entry_email.insert(0, str(email) if email is not None else "")
    entry_email.pack(pady=2)

    ctk.CTkLabel(scroll_frame_edit, text="Endereço:").pack(pady=3)
    entry_endereco = ctk.CTkEntry(scroll_frame_edit, width=200)
    entry_endereco.insert(0, str(endereco) if endereco is not None else "")
    entry_endereco.pack(pady=2)

    ctk.CTkLabel(scroll_frame_edit, text="CEP:").pack(pady=3)
    entry_cep = ctk.CTkEntry(scroll_frame_edit, width=200)
    entry_cep.insert(0, str(cep) if cep is not None else "")
    entry_cep.pack(pady=2)

    ctk.CTkLabel(scroll_frame_edit, text="Telefone:").pack(pady=3)
    entry_telefone = ctk.CTkEntry(scroll_frame_edit, width=200)
    entry_telefone.insert(0, str(telefone) if telefone is not None else "")
    entry_telefone.pack(pady=2)

    ctk.CTkLabel(scroll_frame_edit, text="Número do Banco:").pack(pady=3)
    entry_numero_banco = ctk.CTkEntry(scroll_frame_edit, width=200)
    entry_numero_banco.insert(0, str(numero_banco) if numero_banco is not None else "")
    entry_numero_banco.pack(pady=2)
    
    def preencher_agencia(event=None):
        numero_banco_val = entry_numero_banco.get().strip()
        nome_banco = BANCOS.get(numero_banco_val, "")
        entry_descricao_banco.delete(0, tk.END)
        entry_descricao_banco.insert(0, nome_banco)
        
    ctk.CTkLabel(scroll_frame_edit, text="Descrição do banco:").pack(pady=3)
    entry_descricao_banco = ctk.CTkEntry(scroll_frame_edit, width=200)
    entry_descricao_banco.insert(0, str(descricao_banco) if descricao_banco is not None else "")
    entry_descricao_banco.pack(pady=2)
    
    ctk.CTkLabel(scroll_frame_edit, text="Agência:").pack(pady=3)
    entry_agencia = ctk.CTkEntry(scroll_frame_edit, width=200)
    entry_agencia.insert(0, str(agencia) if agencia is not None else "")
    entry_agencia.pack(pady=2)
    
    ctk.CTkLabel(scroll_frame_edit, text="Número da Conta:").pack(pady=3)
    entry_numero_conta = ctk.CTkEntry(scroll_frame_edit, width=200)
    entry_numero_conta.insert(0, str(numero_conta) if numero_conta is not None else "")
    entry_numero_conta.pack(pady=2)
    
    ctk.CTkLabel(scroll_frame_edit, text="Grau de Instrução:").pack(pady=3)
    combo_grau_instrucao = ctk.CTkComboBox(scroll_frame_edit, values=["Nível Médio", "Graduação", "Pós-graduação", "Mestrado", "Doutorado"], width=200)
    combo_grau_instrucao.set(grau_instrucao if grau_instrucao is not None else "")
    combo_grau_instrucao.pack(pady=2)
    
    ctk.CTkLabel(scroll_frame_edit, text="Cargo Efetivo:").pack(pady=3)
    cargos_rows = execute_query("SELECT descricao_cargo FROM Cargo_Efetivo ORDER BY descricao_cargo", fetch='all')
    cargos = [row[0] for row in cargos_rows] if cargos_rows else []
    if not cargos:
        cargos = ["-- Nenhum cargo cadastrado --"]
    combo_cargo = ctk.CTkComboBox(scroll_frame_edit, values=cargos, width=200)
    combo_cargo.set(cargo if cargo is not None else "")
    combo_cargo.pack(pady=2)
    
    ctk.CTkLabel(scroll_frame_edit, text="Nº Órgão de origem:").pack(pady=3)
    entry_numero_orgao = ctk.CTkEntry(scroll_frame_edit, width=200)
    entry_numero_orgao.insert(0, str(numero_orgao) if numero_orgao is not None else "")
    entry_numero_orgao.pack(pady=2)
    
    ctk.CTkLabel(scroll_frame_edit, text="Descrição do Órgão:").pack(pady=3)
    entry_descricao_orgao = ctk.CTkEntry(scroll_frame_edit, width=200)
    entry_descricao_orgao.insert(0, str(descricao_orgao) if descricao_orgao is not None else "")
    entry_descricao_orgao.pack(pady=2)
    
    ctk.CTkLabel(scroll_frame_edit, text="Nº Processo SEI:").pack(pady=3)
    entry_processo_sei = ctk.CTkEntry(scroll_frame_edit, width=200)
    entry_processo_sei.insert(0, str(processo_sei) if processo_sei is not None else "")
    entry_processo_sei.pack(pady=2)
    
    ctk.CTkLabel(scroll_frame_edit, text="Observação:").pack(pady=3)
    entry_observacoes = tk.Text(scroll_frame_edit, width=38, height=4)
    entry_observacoes.insert("1.0", observacoes or "")
    entry_observacoes.pack(pady=2)
    
    ctk.CTkButton(scroll_frame_edit, text="Salvar", command=salvar_edicoes, width=100, fg_color="#49089e", hover_color="#49089e", text_color="#fff", corner_radius=18).pack(pady=20)
    ctk.CTkButton(scroll_frame_edit, text="Cancelar", width=100, fg_color="#49089e", hover_color="#49089e", text_color="#fff", corner_radius=18, command=janelaEditarServidor.destroy).pack(pady=5)
    
    def preencher_descricao_orgao(event=None):
        numero = entry_numero_orgao.get().strip()
        if not numero:
            entry_descricao_orgao.delete(0, tk.END)
            return
        
        row = execute_query("SELECT descricao_orgao FROM orgao_de_origem WHERE numero_orgao = ?", (numero,), fetch='one')
        if row and row[0]:
            entry_descricao_orgao.delete(0, tk.END)
            entry_descricao_orgao.insert(0, str(row[0]))
        else:
            entry_descricao_orgao.delete(0, tk.END)
    
    def aplicar_mascara_cpf(event):
        valor = entry_cpf.get().replace(".", "").replace("-", "")[:11]
        novo = ""
        if len(valor) > 0: novo += valor[:3]
        if len(valor) > 3: novo += "." + valor[3:6]
        if len(valor) > 6: novo += "." + valor[6:9]
        if len(valor) > 9: novo += "-" + valor[9:11]
        entry_cpf.delete(0, tk.END)
        entry_cpf.insert(0, novo)
        
    def aplicar_mascara_cep(event):
        valor = entry_cep.get().replace("-", "")[:8]
        novo = ""
        if len(valor) > 0: novo += valor[:5]
        if len(valor) > 5: novo += "-" + valor[5:8]
        entry_cep.delete(0, tk.END)
        entry_cep.insert(0, novo)
        
    def aplicar_mascara_telefone(event):
        valor = entry_telefone.get().replace("(", "").replace(")", "").replace("-", "").replace(" ", "")[:11]
        novo = ""
        if len(valor) > 0: novo += "(" + valor[:2] + ") "
        if len(valor) > 2 and len(valor) <= 7: novo += valor[2:6] + "-" + valor[6:10]
        elif len(valor) > 7: novo += valor[2:7] + "-" + valor[7:11]
        entry_telefone.delete(0, tk.END)
        entry_telefone.insert(0, novo)
        
    def aplicar_mascara_numero_banco(event):
        valor = entry_numero_banco.get().replace("-", "")[:3]
        novo = ""
        if len(valor) > 0: novo += valor[:3]
        entry_numero_banco.delete(0, tk.END)
        entry_numero_banco.insert(0, novo)
        
    entry_cpf.bind("<KeyRelease>", aplicar_mascara_cpf)
    entry_cep.bind("<KeyRelease>", aplicar_mascara_cep)
    entry_telefone.bind("<KeyRelease>", aplicar_mascara_telefone)
    entry_numero_banco.bind("<KeyRelease>", aplicar_mascara_numero_banco, add="+")
    entry_numero_banco.bind("<KeyRelease>", preencher_agencia, add="+")
    entry_numero_orgao.bind("<KeyRelease>", preencher_descricao_orgao)


def listar_impostos():
    impostos = execute_query("SELECT id, valor_minimo, valor_maximo, incidencia, valor_deducao, data_vigencia FROM imposto_de_renda", fetch='all')
    if not impostos: impostos = []

    if not impostos:
        messagebox.showinfo("Info", "Nenhum imposto cadastrado.")
        return
    
    janelaListarImpostos = ctk.CTkToplevel()
    janelaListarImpostos.title("Lista de Impostos")
    janelaListarImpostos.geometry("700x400")
    janelaListarImpostos.wm_attributes('-topmost', True)
    ctk.set_default_color_theme("blue")
    
    main_frame = ctk.CTkFrame(janelaListarImpostos)
    main_frame.pack(fill="both", expand=True, padx=10, pady=10)
    main_frame.grid_rowconfigure(0, weight=1)
    main_frame.grid_columnconfigure(0, weight=1)
    
    tree_frame = ctk.CTkFrame(main_frame)
    tree_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
    tree_frame.grid_rowconfigure(0, weight=1)
    tree_frame.grid_columnconfigure(0, weight=1)
    
    style = ttk.Style()
    style.theme_use("default")
    style.configure("Treeview",
                    background="#ffffff",
                    foreground="black",
                    rowheight=25,
                    fieldbackground="#ffffff")
    style.map('Treeview', background=[('selected', "#49089e")])
    style.configure("Treeview.Heading", font=('Calibri', 10, 'bold'))
    
    columns = ("ID", "Valor Mínimo", "Valor Máximo", "Incidência", "Valor Dedução", "Data de Vigência")
    tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
    
    for col in columns:
        tree.heading(col, text=col, command=lambda c=col: sort_by_column(tree, c, False))
        tree.column(col, width=100, anchor="center")
        
    scrollbar_v = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
    scrollbar_h = ttk.Scrollbar(tree_frame, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=scrollbar_v.set, xscrollcommand=scrollbar_h.set)
    tree.grid(row=0, column=0, sticky="nsew")
    scrollbar_v.grid(row=0, column=1, sticky="ns")
    scrollbar_h.grid(row=1, column=0, sticky="ew")
    
    tree.tag_configure('oddrow', background='#f0f4f8')
    tree.tag_configure('evenrow', background='#ffffff')
    
    def sort_by_column(tree, col, descending):
        data = [(tree.set(child, col), child) for child in tree.get_children('')]
        
        try:
            data.sort(key=lambda t: float(t[0]) if t[0].replace('.','',1).isdigit() else t[0].lower(), reverse=descending)
        except ValueError:
            data.sort(key=lambda t: t[0].lower(), reverse=descending)
            
        for index, (val, child) in enumerate(data):
            tree.move(child, '', index)
            
        tree.heading(col, command=lambda: sort_by_column(tree, col, not descending))
        
    def carregar_impostos():
        for item in tree.get_children():
            tree.delete(item)
            
        impostos_db = execute_query("SELECT id, valor_minimo, valor_maximo, incidencia, valor_deducao, data_vigencia FROM imposto_de_renda ORDER BY valor_minimo", fetch='all')
        if not impostos_db:
            return

        for i, imposto in enumerate(impostos_db):
            id_val, min_val, max_val, inc_val, ded_val, vig_val = imposto
            min_f = f"R$ {min_val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if min_val is not None else ""
            max_f = f"R$ {max_val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if max_val is not None else ""
            inc_f = f"{inc_val:.2f}%".replace('.', ',') if inc_val is not None else ""
            ded_f = f"R$ {ded_val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if ded_val is not None else ""
            
            imposto_tratado = (id_val, min_f, max_f, inc_f, ded_f, vig_val)
            tag = 'evenrow' if i % 2 == 0 else 'oddrow'
            tree.insert("", "end", values=imposto_tratado, tags=(tag,))

    def mascara_valor(event):
        widget = event.widget
        raw = re.sub(r"\D", "", widget.get())
        if not raw: return
        while len(raw) < 3: raw = "0" + raw
        reais = f"{int(raw[:-2]):,}".replace(",", ".")
        valor_formatado = f"R$ {reais},{raw[-2:]}"
        widget.delete(0, tk.END)
        widget.insert(0, valor_formatado)

    def mascara_incidencia(event):
        widget = event.widget
        raw = re.sub(r"\D", "", widget.get())
        if not raw: return
        while len(raw) < 3: raw = "0" + raw
        valor_formatado = f"{raw[:-2]},{raw[-2:]}%"
        widget.delete(0, tk.END)
        widget.insert(0, valor_formatado)

    def on_double_click_imposto(event):
        item_selecionado = tree.selection()
        if not item_selecionado:
            return
        item_id = tree.item(item_selecionado[0], "values")[0]
        editar_imposto(item_id, janelaListarImpostos, carregar_impostos)
    tree.bind("<Double-1>", on_double_click_imposto)
                
    controls_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
    controls_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=(5,0))
    
    ctk.CTkLabel(controls_frame, text="Filtrar:", font=('Calibri', 12)).pack(side="left", padx=(0,5))
    entry_filtro = ctk.CTkEntry(controls_frame)
    entry_filtro.pack(side="left", fill="x", expand=True)

    btn_editar = ctk.CTkButton(controls_frame, text="Editar Selecionado", state="disabled", width=140, fg_color="#FFA500", text_color="black", hover_color="#FF8C00")
    btn_editar.pack(side="right", padx=(10,0))
    
    btn_atualizar = ctk.CTkButton(controls_frame, text="Atualizar", command=carregar_impostos, width=100)
    btn_atualizar.pack(side="right", padx=(10,0))

    def abrir_edicao_imposto():
        item_selecionado = tree.selection()
        if not item_selecionado:
            messagebox.showwarning("Aviso", "Selecione uma faixa de imposto para editar.", parent=janelaListarImpostos)
            return
        item_id = tree.item(item_selecionado[0], "values")[0]
        editar_imposto(item_id, janelaListarImpostos, carregar_impostos)

    btn_editar.configure(command=abrir_edicao_imposto)
    
    def filtrar_imposto(event=None):
        filtro = entry_filtro.get().strip().lower()
        carregar_impostos() # Recarrega para garantir que todos os itens estão visíveis antes de filtrar
        for item in tree.get_children():
            valores_linha = tree.item(item, "values")
            if any(filtro in str(valor).lower() for valor in valores_linha):
                tree.reattach(item, '', 'end')
            else:
                tree.detach(item)
                
    entry_filtro.bind("<KeyRelease>", filtrar_imposto)

    def on_tree_select_imposto(event):
        """Habilita o botão de editar quando um item é selecionado."""
        if tree.selection():
            btn_editar.configure(state="normal")
        else:
            btn_editar.configure(state="disabled")
    tree.bind("<<TreeviewSelect>>", on_tree_select_imposto)

    carregar_impostos() # Carga inicial

def editar_imposto(item_id, parent_window, callback_atualizar):
    dados_imposto = execute_query("SELECT valor_minimo, valor_maximo, incidencia, valor_deducao, data_vigencia FROM imposto_de_renda WHERE id = ?", (item_id,), fetch='one')

    if not dados_imposto:
        messagebox.showerror("Erro", "Faixa de imposto não encontrada.", parent=parent_window)
        return

    janela_edicao = ctk.CTkToplevel(parent_window)
    janela_edicao.title("Editar Faixa de Imposto")
    janela_edicao.wm_attributes('-topmost', True)
    janela_edicao.geometry("350x450")
    janela_edicao.grab_set()

    min_val, max_val, inc_val, ded_val, vig_val = dados_imposto

    ctk.CTkLabel(janela_edicao, text="Valor Mínimo:").pack(pady=(10, 2))
    entry_min = ctk.CTkEntry(janela_edicao, width=250)
    entry_min.insert(0, f"{min_val:.2f}".replace('.', ',') if min_val is not None else "")
    entry_min.pack()

    ctk.CTkLabel(janela_edicao, text="Valor Máximo:").pack(pady=(10, 2))
    entry_max = ctk.CTkEntry(janela_edicao, width=250)
    entry_max.insert(0, f"{max_val:.2f}".replace('.', ',') if max_val is not None else "")
    entry_max.pack()

    ctk.CTkLabel(janela_edicao, text="Incidência (%):").pack(pady=(10, 2))
    entry_inc = ctk.CTkEntry(janela_edicao, width=250)
    entry_inc.insert(0, f"{inc_val:.2f}".replace('.', ',') if inc_val is not None else "")
    entry_inc.pack()

    ctk.CTkLabel(janela_edicao, text="Valor Dedução:").pack(pady=(10, 2))
    entry_ded = ctk.CTkEntry(janela_edicao, width=250)
    entry_ded.insert(0, f"{ded_val:.2f}".replace('.', ',') if ded_val is not None else "")
    entry_ded.pack()

    ctk.CTkLabel(janela_edicao, text="Data Vigência (MM/AAAA):").pack(pady=(10, 2))
    entry_vig = ctk.CTkEntry(janela_edicao, width=250)
    entry_vig.insert(0, vig_val or "")
    entry_vig.pack()

    def salvar_edicao():
        novo_min_str = entry_min.get().strip()
        novo_max_str = entry_max.get().strip()
        novo_inc_str = entry_inc.get().strip()
        novo_ded_str = entry_ded.get().strip()
        nova_vig = entry_vig.get().strip()

        if not all([novo_min_str, novo_max_str, novo_inc_str, novo_ded_str, nova_vig]):
            messagebox.showerror("Erro", "Todos os campos são obrigatórios.", parent=janela_edicao)
            return

        try:
            novo_min = float(re.sub(r'[R$\s.]', '', novo_min_str).replace(',', '.'))
            novo_max = float(re.sub(r'[R$\s.]', '', novo_max_str).replace(',', '.'))
            novo_inc = float(re.sub(r'[%\s]', '', novo_inc_str).replace(',', '.'))
            novo_ded = float(re.sub(r'[R$\s.]', '', novo_ded_str).replace(',', '.'))
        except ValueError:
            messagebox.showerror("Erro", "Valores numéricos inválidos.", parent=janela_edicao)
            return

        query_update = """
            UPDATE imposto_de_renda 
            SET valor_minimo = ?, valor_maximo = ?, incidencia = ?, valor_deducao = ?, data_vigencia = ?
            WHERE id = ?
        """
        params = (novo_min, novo_max, novo_inc, novo_ded, nova_vig, item_id)
        execute_query(query_update, params)
        
        messagebox.showinfo("Sucesso", "Faixa de imposto atualizada com sucesso!", parent=janela_edicao)
        janela_edicao.destroy()
        callback_atualizar()

    ctk.CTkButton(janela_edicao, text="Salvar", command=salvar_edicao).pack(pady=20)

    def mascara_valor_edicao(event):
        widget = event.widget
        raw = re.sub(r"\D", "", widget.get())
        if not raw: return
        while len(raw) < 3: raw = "0" + raw
        reais = f"{int(raw[:-2]):,}".replace(",", ".")
        valor_formatado = f"R$ {reais},{raw[-2:]}"
        widget.delete(0, tk.END)
        widget.insert(0, valor_formatado)

    def mascara_incidencia_edicao(event):
        widget = event.widget
        raw = re.sub(r"\D", "", widget.get())
        if not raw: return
        while len(raw) < 3: raw = "0" + raw
        valor_formatado = f"{raw[:-2]},{raw[-2:]}%"
        widget.delete(0, tk.END)
        widget.insert(0, valor_formatado)

    entry_min.bind("<KeyRelease>", mascara_valor_edicao)
    entry_max.bind("<KeyRelease>", mascara_valor_edicao)
    entry_ded.bind("<KeyRelease>", mascara_valor_edicao)
    entry_inc.bind("<KeyRelease>", mascara_incidencia_edicao)

def cadastrar_cargo_efetivo():
    def salvar_cargo():
        cargo = entry_cargo.get().strip()
        valor_vencimento = entry_valor_vencimento.get().strip()
        
        if not cargo or not valor_vencimento:
            messagebox.showerror("Erro", "Os campos Cargo e Valor do maior vencimento são obrigatórios!")
            return

        # Limpa o valor para salvar no banco (ex: "R$ 1.234,56" -> 1234.56)
        valor_limpo = re.sub(r'[^\d,]', '', valor_vencimento).replace(',', '.')
        
        try:
            query = "INSERT INTO Cargo_Efetivo (descricao_cargo, valor_maior_vencimento) VALUES (?, ?)"
            params = (cargo, float(valor_limpo))
            execute_query(query, params)
            messagebox.showinfo("Sucesso", "Cargo Efetivo salvo com sucesso!")
            janela.destroy()
        except sqlite3.IntegrityError as e:
            messagebox.showerror("Erro", f"O cargo '{cargo}' já está cadastrado.", parent=janela)
        except (ValueError, TypeError):
            messagebox.showerror("Erro", "O valor do vencimento informado é inválido.", parent=janela)

    janela = ctk.CTkToplevel()
    janela.title("Cadastrar Cargo Efetivo")
    janela.geometry("400x400")
    janela.wm_attributes('-topmost', True)
    ctk.set_default_color_theme("blue")
    
    ctk.CTkLabel(janela, text="Cargo Efetivo", font=('Calibri', 16, 'bold'), text_color="#49089e").pack(pady=10)
    ctk.CTkLabel(janela, text="Este é um placeholder para a funcionalidade de cadastro de cargo efetivo.", font=('Calibri', 12), text_color="#000000", wraplength=350).pack(pady=20)
    
    ctk.CTkLabel(janela, text="Descrição do cargo:", font=('Calibri', 14), text_color="#000000").pack(pady=(10, 3))
    entry_cargo = ctk.CTkEntry(janela, width=220, fg_color="#e3eafc", text_color="#222222", border_color="#6a0ca1")
    entry_cargo.pack(pady=(0, 10))
    
    ctk.CTkLabel(janela, text="Valor do maior vencimento:", font=('Calibri', 14), text_color="#000000").pack(pady=(10, 3))
    entry_valor_vencimento = ctk.CTkEntry(janela, width=220, fg_color="#e3eafc", text_color="#222222", border_color="#6a0ca1")
    entry_valor_vencimento.pack(pady=(0, 10))
    
    ctk.CTkButton(janela, text="Salvar", width=100, fg_color="#49089e", hover_color="#49089e", text_color="#fff", corner_radius=18, command=salvar_cargo).pack(pady=20)

    
    def mascara_valor(event):
        # Captura apenas dígitos (tratamos como centavos)
        raw = re.sub(r"\D", "", entry_valor_vencimento.get())

        if raw == "":
            entry_valor_vencimento.delete(0, tk.END)
            return

        # Garantir pelo menos 3 dígitos para evitar problemas ao formatar (ex: '1' -> 0,01)
        while len(raw) < 3:
            raw = "0" + raw

        reais_part = raw[:-2]
        centavos_part = raw[-2:]

        try:
            reais_int = int(reais_part)
        except ValueError:
            reais_int = 0

        # Formatar milhares com pontos (ex: 1234 -> 1.234)
        reais_formatado = f"{reais_int:,}".replace(",", ".")
        valor_formatado = f"R$ {reais_formatado},{centavos_part}"

        # Atualiza campo (cursor fica no fim)
        entry_valor_vencimento.delete(0, tk.END)
        entry_valor_vencimento.insert(0, valor_formatado)
            
            
    entry_valor_vencimento.bind("<KeyRelease>", mascara_valor)
    
#=====================================================================================================================#


def abrir_gerar_comprovante_rendimentos():
    """Abre a janela para o usuário selecionar o beneficiário e o ano para gerar o comprovante."""
    
    # Busca a lista de beneficiários para popular o combobox
    try:
        with sqlite3.connect(resource_path('banco.db')) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, nome FROM servidores ORDER BY nome")
            beneficiarios_db = cursor.fetchall()
        
        mapa_beneficiarios = {nome: id for id, nome in beneficiarios_db}
        nomes_beneficiarios = list(mapa_beneficiarios.keys())
        if not nomes_beneficiarios:
            messagebox.showinfo("Informação", "Nenhum beneficiário ativo encontrado para gerar comprovante.")
            return
    except sqlite3.Error as e:
        messagebox.showerror("Erro de Banco de Dados", f"Não foi possível carregar a lista de beneficiários:\n{e}")
        return

    def gerar_comprovante():
        # Coleta os dados da interface
        nome_selecionado = combo_beneficiarios.get()
        ano_selecionado = entry_ano_calendario.get().strip()

        if not nome_selecionado:
            messagebox.showerror("Erro", "Por favor, selecione um beneficiário.", parent=janela)
            return
        if not (ano_selecionado.isdigit() and len(ano_selecionado) == 4):
            messagebox.showerror("Erro", "Por favor, insira um ano válido (ex: 2024).", parent=janela)
            return

        beneficiario_id = mapa_beneficiarios.get(nome_selecionado)
        
        # Chama a função especialista em gerar o documento PDF
        gerar_comprovante_rendimentos_pdf(beneficiario_id, ano_selecionado, id_usuario_logado, parent_window=janela)

    janela = ctk.CTkToplevel()
    janela.title("Gerar Comprovante de Rendimentos")
    janela.geometry("400x400")
    janela.transient()
    janela.grab_set()

    frame = ctk.CTkFrame(janela, fg_color="transparent")
    frame.pack(expand=True, padx=20, pady=20)

    ctk.CTkLabel(frame, text="Gerar Comprovante de Rendimentos", font=('Calibri', 16, 'bold')).pack(pady=(0, 10))
    ctk.CTkLabel(frame, text="Selecione o servidor e o ano-calendário\npara gerar o documento para o Imposto de Renda.", justify="center").pack(pady=(0, 20))

    ctk.CTkLabel(frame, text="Servidor:").pack(pady=5)
    search_var = tk.StringVar()
    entry_search = ctk.CTkEntry(frame, width=150, placeholder_text="Pesquisar servidor...", textvariable=search_var)
    entry_search.pack(pady=(0, 4))
    
    combo_beneficiarios = ctk.CTkComboBox(frame, width=300, values=nomes_beneficiarios)
    combo_beneficiarios.pack(pady=2)

    ctk.CTkLabel(frame, text="Ano-Calendário:").pack(pady=(10, 5))
    entry_ano_calendario = ctk.CTkEntry(frame, width=150, justify="center")
    entry_ano_calendario.insert(0, str(datetime.now().year - 1))
    entry_ano_calendario.pack(pady=2)
    
    def atualizar_opcoes_combo(termo=""):
        termo = termo.strip().lower()
        if termo == "":
            filtrar = nomes_beneficiarios
        else:
            filtrar = [n for n in nomes_beneficiarios if termo in n.lower()]
        combo_beneficiarios.configure(values=filtrar)
        atual = combo_beneficiarios.get()
        if atual not in filtrar:
            combo_beneficiarios.set("")
        else:
            combo_beneficiarios.set(atual)
            
    def on_search_var_change(*args):
        atualizar_opcoes_combo(search_var.get())
        
    search_var.trace_add("write", on_search_var_change)


    ctk.CTkButton(frame, text="Gerar Comprovante", command=gerar_comprovante, fg_color="#4a0483", hover_color="#7710ca", text_color="#fff", corner_radius=18).pack(pady=(20, 5))
    ctk.CTkButton(frame, text="Cancelar", command=janela.destroy, fg_color="#6c757d", hover_color="#5a6268", text_color="#fff", corner_radius=18).pack()
    
    
#=====================================================================================================================#
    
def cadastrar_orgao_origem():
    def salvar_orgao():
        orgao = entry_orgao.get().strip()
        descricao = entry_descricao.get().strip()
        
        if not orgao or not descricao:
            messagebox.showerror("Erro", "Os campos Nome do órgão e Descrição são obrigatórios!")
            return

        try:
            query = "INSERT INTO orgao_de_origem (numero_orgao, descricao_orgao) VALUES (?, ?)"
            params = (orgao, descricao)
            execute_query(query, params)
            messagebox.showinfo("Sucesso", "Órgão de Origem salvo com sucesso!")
            janela.destroy()
        except sqlite3.IntegrityError as e:
            messagebox.showerror("Erro", f"O órgão com número '{orgao}' já está cadastrado.", parent=janela)
    
    janela = ctk.CTkToplevel()
    janela.title("Cadastrar Órgão de Origem")
    janela.geometry("400x400")
    janela.wm_attributes('-topmost', True)
    # ctk.set_default_color_theme("blue") # Removido para manter consistência
    
    ctk.CTkLabel(janela, text="Órgão de Origem", font=('Calibri', 16, 'bold'), text_color="#49089e").pack(pady=10)
    ctk.CTkLabel(janela, text="Este é um placeholder para a funcionalidade de cadastro de órgão de origem.", font=('Calibri', 12), text_color="#000000", wraplength=350).pack(pady=20)
    
    ctk.CTkLabel(janela, text="Número do órgão:", font=('Calibri', 14), text_color="#000000").pack(pady=(10, 3))
    entry_orgao = ctk.CTkEntry(janela, width=220, fg_color="#e3eafc", text_color="#222222", border_color="#6a0ca1")
    entry_orgao.pack(pady=(0, 10))
    
    ctk.CTkLabel(janela, text="Descrição:", font=('Calibri', 14), text_color="#000000").pack(pady=(10, 3))
    entry_descricao = ctk.CTkEntry(janela, width=220, fg_color="#e3eafc", text_color="#222222", border_color="#6a0ca1")
    entry_descricao.pack(pady=(0, 10))
    
    ctk.CTkButton(janela, text="Salvar", width=100, fg_color="#49089e", hover_color="#49089e", text_color="#fff", corner_radius=18, command=salvar_orgao).pack(pady=20)


def cadastrar_valores_imposto():
    def salvar_valores():
        valor_minimo = entry_valor_minimo.get().strip()
        valor_maximo = entry_valor_maximo.get().strip()
        incidencia = entry_incidencia.get().strip()
        valor_deducao = entry_valor_deducao.get().strip()
        data_vigencia = entry_data_vigencia.get().strip()
        
        if not valor_minimo or not valor_maximo or not incidencia or not valor_deducao:
            messagebox.showerror("Erro", "Todos os campos são obrigatórios!")
            return

        # Limpa os valores monetários e de porcentagem
        valor_min_limpo = re.sub(r'[R$\s.]', '', valor_minimo).replace(',', '.')
        valor_max_limpo = re.sub(r'[R$\s.]', '', valor_maximo).replace(',', '.')
        incidencia_limpa = re.sub(r'[%\s]', '', incidencia).replace(',', '.')
        deducao_limpa = re.sub(r'[R$\s.]', '', valor_deducao).replace(',', '.')

        try:
            query = "INSERT INTO imposto_de_renda (valor_minimo, valor_maximo, incidencia, valor_deducao, data_vigencia) VALUES (?, ?, ?, ?, ?)"
            params = (
                float(valor_min_limpo),
                float(valor_max_limpo),
                float(incidencia_limpa),
                float(deducao_limpa),
                data_vigencia
            )
            execute_query(query, params)
            messagebox.showinfo("Sucesso", "Faixa de imposto salva com sucesso!")
            janela.destroy()
        except (sqlite3.Error, ValueError, TypeError) as e:
            messagebox.showerror("Erro", f"Erro ao salvar valores de imposto: {e}", parent=janela)
    
    janela = ctk.CTkToplevel()
    janela.title("Cadastrar Valores de Imposto")
    janela.geometry("400x400")
    janela.wm_attributes('-topmost', True)
    # ctk.set_default_color_theme("blue") # Removido para manter consistência
    
    scrollframe = ctk.CTkScrollableFrame(janela, width=380, height=380)
    scrollframe.pack(fill="both", expand=True, padx=10, pady=10)
    
    ctk.CTkLabel(scrollframe, text="Valores de Imposto", font=('Calibri', 16, 'bold'), text_color="#49089e").pack(pady=10)
    ctk.CTkLabel(scrollframe, text="Este é um placeholder para a funcionalidade de cadastro de valores de imposto.", font=('Calibri', 12), text_color="#000000", wraplength=350).pack(pady=20)
    
    ctk.CTkLabel(scrollframe, text="Valor mínimo:", font=('Calibri', 14), text_color="#000000").pack(pady=(10, 3))
    entry_valor_minimo = ctk.CTkEntry(scrollframe, width=220, fg_color="#e3eafc", text_color="#222222", border_color="#6a0ca1")
    entry_valor_minimo.pack(pady=(0, 10))
    
    ctk.CTkLabel(scrollframe, text="Valor máximo:", font=('Calibri', 14), text_color="#000000").pack(pady=(10, 3))
    entry_valor_maximo = ctk.CTkEntry(scrollframe, width=220, fg_color="#e3eafc", text_color="#222222", border_color="#6a0ca1")
    entry_valor_maximo.pack(pady=(0, 10))
    
    ctk.CTkLabel(scrollframe, text="Incidência (%):", font=('Calibri', 14), text_color="#000000").pack(pady=(10, 3))
    entry_incidencia = ctk.CTkEntry(scrollframe, width=220, fg_color="#e3eafc", text_color="#222222", border_color="#6a0ca1")
    entry_incidencia.pack(pady=(0, 10))
    
    ctk.CTkLabel(scrollframe, text="Valor Dedução:", font=('Calibri', 14), text_color="#000000").pack(pady=(10, 3))
    entry_valor_deducao = ctk.CTkEntry(scrollframe, width=220, fg_color="#e3eafc", text_color="#222222", border_color="#6a0ca1")
    entry_valor_deducao.pack(pady=(0, 10))
    
    ctk.CTkLabel(scrollframe, text="Data Vigência (MM/AAAA):", font=('Calibri', 14), text_color="#000000").pack(pady=(10, 3))
    entry_data_vigencia = ctk.CTkEntry(scrollframe, width=220, fg_color="#e3eafc", text_color="#222222", border_color="#6a0ca1")
    entry_data_vigencia.pack(pady=(0, 10))
    
    ctk.CTkButton(scrollframe, text="Salvar", width=100, fg_color="#49089e", hover_color="#49089e", text_color="#fff", corner_radius=18, command=salvar_valores).pack(pady=20)

    def mascara_data_vigencia(event):
        valor = entry_data_vigencia.get().replace("/", "")[:6]
        novo = ""
        if len(valor) > 0:
            novo += valor[:2]
        if len(valor) > 2:
            novo += "/" + valor[2:6]
        entry_data_vigencia.delete(0, tk.END)
        entry_data_vigencia.insert(0, novo)
        
        
    entry_data_vigencia.bind("<KeyRelease>", mascara_data_vigencia)
    
    def mascara_valor_minimo(event):
        # Captura apenas dígitos (tratamos como centavos)
        raw = re.sub(r"\D", "", entry_valor_minimo.get())

        if raw == "":
            entry_valor_minimo.delete(0, tk.END)
            return

        # Garantir pelo menos 3 dígitos para evitar problemas ao formatar (ex: '1' -> 0,01)
        while len(raw) < 3:
            raw = "0" + raw

        reais_part = raw[:-2]
        centavos_part = raw[-2:]

        try:
            reais_int = int(reais_part)
        except ValueError:
            reais_int = 0

        # Formatar milhares com pontos (ex: 1234 -> 1.234)
        reais_formatado = f"{reais_int:,}".replace(",", ".")
        valor_formatado = f"R$ {reais_formatado},{centavos_part}"

        # Atualiza campo (cursor fica no fim)
        entry_valor_minimo.delete(0, tk.END)
        entry_valor_minimo.insert(0, valor_formatado)
        
    entry_valor_minimo.bind("<KeyRelease>", mascara_valor_minimo)
    
    def mascara_valor_maximo(event):
        # Captura apenas dígitos (tratamos como centavos)
        raw = re.sub(r"\D", "", entry_valor_maximo.get())

        if raw == "":
            entry_valor_maximo.delete(0, tk.END)
            return

        # Garantir pelo menos 3 dígitos para evitar problemas ao formatar (ex: '1' -> 0,01)
        while len(raw) < 3:
            raw = "0" + raw

        reais_part = raw[:-2]
        centavos_part = raw[-2:]

        try:
            reais_int = int(reais_part)
        except ValueError:
            reais_int = 0

        # Formatar milhares com pontos (ex: 1234 -> 1.234)
        reais_formatado = f"{reais_int:,}".replace(",", ".")
        valor_formatado = f"R$ {reais_formatado},{centavos_part}"

        # Atualiza campo (cursor fica no fim)
        entry_valor_maximo.delete(0, tk.END)
        entry_valor_maximo.insert(0, valor_formatado)
        
    entry_valor_maximo.bind("<KeyRelease>", mascara_valor_maximo)
    
    
    def mascara_valor_deducao(event):
        # Captura apenas dígitos (tratamos como centavos)
        raw = re.sub(r"\D", "", entry_valor_deducao.get())

        if raw == "":
            entry_valor_deducao.delete(0, tk.END)
            return

        # Garantir pelo menos 3 dígitos para evitar problemas ao formatar (ex: '1' -> 0,01)
        while len(raw) < 3:
            raw = "0" + raw

        reais_part = raw[:-2]
        centavos_part = raw[-2:]

        try:
            reais_int = int(reais_part)
        except ValueError:
            reais_int = 0

        # Formatar milhares com pontos (ex: 1234 -> 1.234)
        reais_formatado = f"{reais_int:,}".replace(",", ".")
        valor_formatado = f"R$ {reais_formatado},{centavos_part}"

        # Atualiza campo (cursor fica no fim)
        entry_valor_deducao.delete(0, tk.END)
        entry_valor_deducao.insert(0, valor_formatado)
        
    entry_valor_deducao.bind("<KeyRelease>", mascara_valor_deducao)
    
def listar_cargos_efetivos():
    """Abre uma janela para listar, filtrar e editar os cargos efetivos."""
    janela_listar_cargos = ctk.CTkToplevel()
    janela_listar_cargos.title("Lista de Cargos Efetivos")
    janela_listar_cargos.geometry("700x500")
    janela_listar_cargos.grab_set()

    main_frame = ctk.CTkFrame(janela_listar_cargos)
    main_frame.pack(fill="both", expand=True, padx=10, pady=10)

    tree_frame = ctk.CTkFrame(main_frame)
    tree_frame.pack(fill="both", expand=True, pady=5)

    colunas = ("ID", "Descrição do Cargo", "Valor Maior Vencimento")
    tree = ttk.Treeview(tree_frame, columns=colunas, show="headings")

    tree.heading("ID", text="ID")
    tree.heading("Descrição do Cargo", text="Descrição do Cargo")
    tree.heading("Valor Maior Vencimento", text="Valor Maior Vencimento")

    tree.column("ID", width=50, anchor="center")
    tree.column("Descrição do Cargo", width=300)
    tree.column("Valor Maior Vencimento", width=150, anchor="e")

    scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    tree.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    def carregar_cargos():
        for item in tree.get_children():
            tree.delete(item)
        
        cargos = execute_query("SELECT id, descricao_cargo, valor_maior_vencimento FROM Cargo_Efetivo ORDER BY descricao_cargo", fetch='all')
        if not cargos:
            return

        for i, cargo in enumerate(cargos):
            id_cargo, desc, valor = cargo
            # Garantir que `valor` seja numérico antes de aplicar formatação
            if valor is None or valor == "":
                valor_num = 0.0
            else:
                try:
                    # Pode vir como string (ex: '1000.00') ou número
                    valor_num = float(valor)
                except (TypeError, ValueError):
                    # Se não for possível converter, usar 0.0 como fallback
                    valor_num = 0.0

            valor_formatado = f"R$ {valor_num:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            tree.insert("", "end", values=(id_cargo, desc, valor_formatado), tags=('evenrow' if i % 2 == 0 else 'oddrow',))

    def editar_cargo(event):
        item_selecionado = tree.selection()
        if not item_selecionado:
            return
        
        item_id = tree.item(item_selecionado[0], "values")[0]
        dados_cargo = execute_query("SELECT descricao_cargo, valor_maior_vencimento FROM Cargo_Efetivo WHERE id = ?", (item_id,), fetch='one')

        if not dados_cargo:
            messagebox.showerror("Erro", "Cargo não encontrado.", parent=janela_listar_cargos)
            return

        janela_edicao = ctk.CTkToplevel(janela_listar_cargos)
        janela_edicao.title("Editar Cargo Efetivo")
        janela_edicao.geometry("350x300")
        janela_edicao.grab_set()

        ctk.CTkLabel(janela_edicao, text="Descrição do Cargo:").pack(pady=(10, 2))
        entry_desc = ctk.CTkEntry(janela_edicao, width=250)
        entry_desc.insert(0, dados_cargo[0])
        entry_desc.pack()

        ctk.CTkLabel(janela_edicao, text="Valor Maior Vencimento:").pack(pady=(10, 2))
        entry_valor = ctk.CTkEntry(janela_edicao, width=250)
        # Garantir que o valor vindo do banco seja convertido para float antes de formatar
        try:
            valor_exibicao = float(dados_cargo[1]) if dados_cargo[1] is not None and dados_cargo[1] != "" else 0.0
        except (TypeError, ValueError):
            valor_exibicao = 0.0

        entry_valor.insert(0, f"{valor_exibicao:.2f}".replace('.', ','))
        entry_valor.pack()

        def salvar_edicao():
            nova_desc = entry_desc.get().strip()
            novo_valor_str = entry_valor.get().strip()
            
            if not nova_desc or not novo_valor_str:
                messagebox.showerror("Erro", "Todos os campos são obrigatórios.", parent=janela_edicao)
                return

            valor_limpo = re.sub(r'[^\d,]', '', novo_valor_str).replace(',', '.')
            try:
                novo_valor = float(valor_limpo)
            except ValueError:
                messagebox.showerror("Erro", "Valor do vencimento inválido.", parent=janela_edicao)
                return

            execute_query("UPDATE Cargo_Efetivo SET descricao_cargo = ?, valor_maior_vencimento = ? WHERE id = ?", (nova_desc, novo_valor, item_id))
            messagebox.showinfo("Sucesso", "Cargo atualizado com sucesso!", parent=janela_edicao)
            janela_edicao.destroy()
            carregar_cargos()

        ctk.CTkButton(janela_edicao, text="Salvar", command=salvar_edicao).pack(pady=20)

    tree.bind("<Double-1>", editar_cargo)
    carregar_cargos()

def listar_orgaos_de_origem():
    """Abre uma janela para listar, filtrar e editar os órgãos de origem."""
    janela_listar_orgaos = ctk.CTkToplevel()
    janela_listar_orgaos.title("Lista de Órgãos de Origem")
    janela_listar_orgaos.geometry("700x500")
    janela_listar_orgaos.grab_set()

    main_frame = ctk.CTkFrame(janela_listar_orgaos)
    main_frame.pack(fill="both", expand=True, padx=10, pady=10)

    tree_frame = ctk.CTkFrame(main_frame)
    tree_frame.pack(fill="both", expand=True, pady=5)

    colunas = ("ID", "Número do Órgão", "Descrição do Órgão")
    tree = ttk.Treeview(tree_frame, columns=colunas, show="headings")

    tree.heading("ID", text="ID")
    tree.heading("Número do Órgão", text="Número do Órgão")
    tree.heading("Descrição do Órgão", text="Descrição do Órgão")

    tree.column("ID", width=50, anchor="center")
    tree.column("Número do Órgão", width=150, anchor="center")
    tree.column("Descrição do Órgão", width=300)

    scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    tree.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    def carregar_orgaos():
        for item in tree.get_children():
            tree.delete(item)
        
        orgaos = execute_query("SELECT id, numero_orgao, descricao_orgao FROM orgao_de_origem ORDER BY descricao_orgao", fetch='all')
        if not orgaos:
            return

        for i, orgao in enumerate(orgaos):
            tree.insert("", "end", values=orgao, tags=('evenrow' if i % 2 == 0 else 'oddrow',))

    def editar_orgao(event):
        item_selecionado = tree.selection()
        if not item_selecionado:
            return
        
        item_id = tree.item(item_selecionado[0], "values")[0]
        dados_orgao = execute_query("SELECT numero_orgao, descricao_orgao FROM orgao_de_origem WHERE id = ?", (item_id,), fetch='one')

        if not dados_orgao:
            messagebox.showerror("Erro", "Órgão não encontrado.", parent=janela_listar_orgaos)
            return

        janela_edicao = ctk.CTkToplevel(janela_listar_orgaos)
        janela_edicao.title("Editar Órgão de Origem")
        janela_edicao.geometry("350x300")
        janela_edicao.grab_set()

        ctk.CTkLabel(janela_edicao, text="Número do Órgão:").pack(pady=(10, 2))
        entry_num = ctk.CTkEntry(janela_edicao, width=250)
        entry_num.insert(0, dados_orgao[0])
        entry_num.pack()

        ctk.CTkLabel(janela_edicao, text="Descrição do Órgão:").pack(pady=(10, 2))
        entry_desc = ctk.CTkEntry(janela_edicao, width=250)
        entry_desc.insert(0, dados_orgao[1])
        entry_desc.pack()

        def salvar_edicao():
            novo_num = entry_num.get().strip()
            nova_desc = entry_desc.get().strip()
            
            if not novo_num or not nova_desc:
                messagebox.showerror("Erro", "Todos os campos são obrigatórios.", parent=janela_edicao)
                return

            try:
                execute_query("UPDATE orgao_de_origem SET numero_orgao = ?, descricao_orgao = ? WHERE id = ?", (novo_num, nova_desc, item_id))
                messagebox.showinfo("Sucesso", "Órgão atualizado com sucesso!", parent=janela_edicao)
                janela_edicao.destroy()
                carregar_orgaos()
            except sqlite3.IntegrityError:
                messagebox.showerror("Erro", f"O número de órgão '{novo_num}' já existe.", parent=janela_edicao)

        ctk.CTkButton(janela_edicao, text="Salvar", command=salvar_edicao).pack(pady=20)

    tree.bind("<Double-1>", editar_orgao)
    carregar_orgaos()

def abrir_gerar_pagamento_instrutor():
    """Abre a janela para calcular e gerar o pagamento de um instrutor."""
    janela_pagamento = ctk.CTkToplevel()
    janela_pagamento.title("Gerar Pagamento de Instrutor")
    janela_pagamento.geometry("450x600")
    janela_pagamento.grab_set()

    # --- Carregar dados necessários ---
    servidores_db = execute_query("SELECT id, nome FROM servidores ORDER BY nome", fetch='all')
    if not servidores_db:
        messagebox.showerror("Erro", "Nenhum servidor cadastrado. Cadastre um servidor primeiro.", parent=janela_pagamento)
        janela_pagamento.destroy()
        return
    
    mapa_servidores = {nome: id for id, nome in servidores_db}
    nomes_servidores = list(mapa_servidores.keys())

    # --- Variáveis de controle ---
    valor_bruto_var = tk.StringVar(value="R$ 0,00")
    valor_ir_var = tk.StringVar(value="R$ 0,00")
    valor_liquido_var = tk.StringVar(value="R$ 0,00")
    dados_calculo = {} # Dicionário para armazenar os resultados do cálculo

    def mascara_mes_ref(event):
        """Aplica a máscara MM/AAAA no campo de mês de referência."""
        valor = entry_mes_ref.get().replace("/", "")[:6]
        novo = ""
        if len(valor) > 0: novo += valor[:2]
        if len(valor) > 2: novo += "/" + valor[2:6]
        
        entry_mes_ref.delete(0, tk.END)
        entry_mes_ref.insert(0, novo)

    def calcular_pagamento():
        """Função acionada pelo botão 'Calcular'."""
        nome_servidor = combo_servidor.get()
        horas_aula_str = entry_horas.get().strip()

        if not nome_servidor or nome_servidor == "-- Selecione --":
            messagebox.showerror("Erro", "Selecione um servidor.", parent=janela_pagamento)
            return
        if not horas_aula_str.isdigit() or int(horas_aula_str) <= 0:
            messagebox.showerror("Erro", "Informe um número válido de horas/aula.", parent=janela_pagamento)
            return
        
        mes_ref = entry_mes_ref.get().strip()
        if not re.match(r'^\d{2}/\d{4}$', mes_ref):
            messagebox.showerror("Erro", "O formato do Mês de Referência deve ser MM/AAAA.", parent=janela_pagamento)
            return

        servidor_id = mapa_servidores.get(nome_servidor)
        horas_aula = int(horas_aula_str)
        mes_ref = entry_mes_ref.get().strip()

        # Buscar o valor do vencimento do cargo do servidor
        # E também o grau de instrução
        query = """
            SELECT c.valor_maior_vencimento, s.grau_instrucao
            FROM servidores s
            JOIN Cargo_Efetivo c ON s.cargo_efetivo = c.descricao_cargo
            WHERE s.id = ?
        """
        resultado = execute_query(query, (servidor_id,), fetch='one')

        if not resultado:
            messagebox.showerror("Erro", "Não foi possível encontrar os dados do servidor.", parent=janela_pagamento)
            return

        valor_vencimento, grau_instrucao = resultado

        if valor_vencimento is None:
            messagebox.showerror("Erro", "Não foi possível encontrar o valor do vencimento para o cargo deste servidor.", parent=janela_pagamento)
            return
        
        # --- Lógica de cálculo do valor da hora/aula com teto ---
        valor_base_hora_aula = valor_vencimento * 0.022  # 2.2% do maior vencimento

        # Buscar o teto para o grau de instrução
        teto_query = "SELECT valor_teto FROM teto_hora_aula WHERE grau_instrucao = ?"
        resultado_teto = execute_query(teto_query, (grau_instrucao,), fetch='one')

        valor_hora_aula = valor_base_hora_aula
        if resultado_teto and resultado_teto[0] is not None:
            teto = resultado_teto[0]
            valor_hora_aula = min(valor_base_hora_aula, teto) # Usa o menor valor entre o calculado e o teto

        if not resultado or resultado[0] is None:
            messagebox.showerror("Erro", "Não foi possível encontrar o valor do vencimento para o cargo deste servidor.", parent=janela_pagamento)
            return

        valor_vencimento = resultado[0]
        
        # Lógica de cálculo (conforme regras)
        valor_bruto = valor_hora_aula * horas_aula # Agora usa o valor_hora_aula já com o teto aplicado

        # --- Lógica de cálculo do Imposto de Renda com base na vigência ---
        # Converte o mês de referência para um formato comparável (AAAA/MM)
        mes, ano = mes_ref.split('/')
        mes_ref_comparavel = f"{ano}/{mes}"

        # Encontra a faixa de IR correta, respeitando a data de vigência mais recente
        # que seja anterior ou igual ao mês de referência do pagamento.
        ir_query = """
            SELECT CAST(incidencia AS REAL), CAST(valor_deducao AS REAL)
            FROM imposto_de_renda
            WHERE ? BETWEEN CAST(valor_minimo AS REAL) AND CAST(valor_maximo AS REAL)
            AND data_vigencia = (
                SELECT data_vigencia FROM imposto_de_renda
                WHERE (SUBSTR(data_vigencia, 4, 4) || '/' || SUBSTR(data_vigencia, 1, 2)) <= ?
                ORDER BY (SUBSTR(data_vigencia, 4, 4) || '/' || SUBSTR(data_vigencia, 1, 2)) DESC
                LIMIT 1
            )
        """
        ir_faixa = execute_query(ir_query, (valor_bruto, mes_ref_comparavel), fetch='one')

        if ir_faixa:
            aliquota, deducao = ir_faixa
            valor_ir_retido = (valor_bruto * (aliquota / 100)) - deducao
        else:
            # Se não encontrar faixa (valor abaixo do mínimo), o imposto é zero
            aliquota, deducao, valor_ir_retido = 0.0, 0.0, 0.0
        
        # Garante que o imposto não seja negativo
        valor_ir_retido = max(0, valor_ir_retido)
        valor_liquido = valor_bruto - valor_ir_retido

        # Armazena os dados para poder salvar depois
        nonlocal dados_calculo
        dados_calculo = {
            "servidor_id": servidor_id,
            "cpf_servidor": execute_query("SELECT cpf FROM servidores WHERE id = ?", (servidor_id,), fetch='one')[0],
            "nome_servidor": nome_servidor,
            "mes_referencia": mes_ref,
            "horas_aula": horas_aula,
            "valor_hora_aula": valor_hora_aula,
            "valor_bruto": valor_bruto,
            "base_calculo_ir": valor_bruto, # Base de cálculo é o valor bruto
            "aliquota_ir": aliquota,
            "deducao_ir": deducao,
            "valor_ir_retido": valor_ir_retido,
            "valor_liquido": valor_liquido,
        }

        # Atualiza a interface
        valor_bruto_var.set(f"R$ {valor_bruto:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        valor_ir_var.set(f"R$ {valor_ir_retido:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        valor_liquido_var.set(f"R$ {valor_liquido:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        
        # Habilita o botão de salvar
        btn_salvar.configure(state="normal")

    def salvar_pagamento():
        """Função para salvar o pagamento calculado no banco de dados."""
        if not dados_calculo:
            messagebox.showerror("Erro", "Nenhum cálculo foi realizado. Clique em 'Calcular' primeiro.", parent=janela_pagamento)
            return

        # --- VERIFICAÇÃO DE DUPLICIDADE ---
        servidor_id_check = dados_calculo["servidor_id"]
        mes_ref_check = dados_calculo["mes_referencia"]
        
        query_check = "SELECT id FROM pagamentos_instrutores WHERE servidor_id = ? AND mes_referencia = ?"
        pagamento_existente = execute_query(query_check, (servidor_id_check, mes_ref_check), fetch='one')
        
        if pagamento_existente:
            confirmar = messagebox.askyesno(
                "Pagamento Existente",
                f"Já existe um pagamento para este instrutor na referência '{mes_ref_check}'.\n\nDeseja sobrescrevê-lo com os novos valores?",
                parent=janela_pagamento
            )
            if confirmar:
                # Se o usuário confirmar, exclui o registro antigo antes de inserir o novo
                execute_query("DELETE FROM pagamentos_instrutores WHERE id = ?", (pagamento_existente[0],))
            else:
                return # Se o usuário cancelar, a operação é abortada

        query_insert = """
            INSERT INTO pagamentos_instrutores (
                servidor_id, cpf_servidor, nome_servidor, mes_referencia, horas_aula, 
                valor_hora_aula, valor_bruto, base_calculo_ir, aliquota_ir, deducao_ir, 
                valor_ir_retido, valor_liquido, data_geracao, usuario_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            dados_calculo["servidor_id"],
            dados_calculo["cpf_servidor"],
            dados_calculo["nome_servidor"],
            dados_calculo["mes_referencia"],
            dados_calculo["horas_aula"],
            dados_calculo["valor_hora_aula"],
            dados_calculo["valor_bruto"],
            dados_calculo["base_calculo_ir"],
            dados_calculo["aliquota_ir"],
            dados_calculo["deducao_ir"],
            dados_calculo["valor_ir_retido"],
            dados_calculo["valor_liquido"],
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            id_usuario_logado
        )
        execute_query(query_insert, params)
        messagebox.showinfo("Sucesso", "Pagamento salvo com sucesso!", parent=janela_pagamento)
        janela_pagamento.destroy()

    # --- Interface Gráfica ---
    frame = ctk.CTkFrame(janela_pagamento, fg_color="transparent")
    frame.pack(expand=True, fill="both", padx=20, pady=20)

    ctk.CTkLabel(frame, text="Gerar Pagamento", font=('Calibri', 18, 'bold')).pack(pady=(0, 20))

    ctk.CTkLabel(frame, text="Selecione o Instrutor:").pack()
    combo_servidor = ctk.CTkComboBox(frame, values=["-- Selecione --"] + nomes_servidores, width=300)
    combo_servidor.pack(pady=(0, 10))

    ctk.CTkLabel(frame, text="Mês de Referência (MM/AAAA):").pack()
    entry_mes_ref = ctk.CTkEntry(frame, width=150, justify="center")
    entry_mes_ref.pack(pady=(0, 10))
    entry_mes_ref.bind("<KeyRelease>", mascara_mes_ref)

    ctk.CTkLabel(frame, text="Total de Horas/Aula no Mês:").pack()
    entry_horas = ctk.CTkEntry(frame, width=150, justify="center")
    entry_horas.pack(pady=(0, 20))

    ctk.CTkButton(frame, text="Calcular Pagamento", command=calcular_pagamento).pack(pady=10)

    # --- Frame de Resultados ---
    result_frame = ctk.CTkFrame(frame, fg_color="#e9e9e9")
    result_frame.pack(pady=20, padx=10, fill="x")

    ctk.CTkLabel(result_frame, text="Valor Bruto:", font=('Calibri', 14, 'bold')).grid(row=0, column=0, padx=10, pady=5, sticky="w")
    ctk.CTkLabel(result_frame, textvariable=valor_bruto_var, font=('Calibri', 14)).grid(row=0, column=1, padx=10, pady=5, sticky="e")
    ctk.CTkLabel(result_frame, text="Imposto de Renda Retido:", font=('Calibri', 14, 'bold')).grid(row=1, column=0, padx=10, pady=5, sticky="w")
    ctk.CTkLabel(result_frame, textvariable=valor_ir_var, font=('Calibri', 14)).grid(row=1, column=1, padx=10, pady=5, sticky="e")
    ctk.CTkLabel(result_frame, text="Valor Líquido a Pagar:", font=('Calibri', 16, 'bold')).grid(row=2, column=0, padx=10, pady=10, sticky="w")
    ctk.CTkLabel(result_frame, textvariable=valor_liquido_var, font=('Calibri', 16, 'bold')).grid(row=2, column=1, padx=10, pady=10, sticky="e")

    btn_salvar = ctk.CTkButton(frame, text="Salvar Pagamento", command=salvar_pagamento, state="disabled", fg_color="green", hover_color="#006400")
    btn_salvar.pack(pady=10)

def gerenciar_tetos_hora_aula():
    """Abre uma janela para visualizar e editar os tetos de hora/aula."""
    janela_tetos = ctk.CTkToplevel()
    janela_tetos.title("Gerenciar Tetos de Hora/Aula")
    janela_tetos.geometry("500x400")
    janela_tetos.grab_set()

    main_frame = ctk.CTkFrame(janela_tetos)
    main_frame.pack(fill="both", expand=True, padx=10, pady=10)

    tree_frame = ctk.CTkFrame(main_frame)
    tree_frame.pack(fill="both", expand=True, pady=5)

    colunas = ("Grau de Instrução", "Valor Teto")
    tree = ttk.Treeview(tree_frame, columns=colunas, show="headings")

    tree.heading("Grau de Instrução", text="Grau de Instrução")
    tree.heading("Valor Teto", text="Valor Teto")

    tree.column("Grau de Instrução", width=200)
    tree.column("Valor Teto", width=150, anchor="e")

    scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    tree.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    def carregar_tetos():
        for item in tree.get_children():
            tree.delete(item)
        
        tetos = execute_query("SELECT grau_instrucao, valor_teto FROM teto_hora_aula ORDER BY valor_teto DESC", fetch='all')
        if not tetos:
            return

        for i, teto in enumerate(tetos):
            grau, valor = teto
            valor_formatado = f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if valor is not None else "R$ 0,00"
            tree.insert("", "end", values=(grau, valor_formatado), tags=('evenrow' if i % 2 == 0 else 'oddrow',))

    def editar_teto(event):
        item_selecionado = tree.selection()
        if not item_selecionado:
            return
        
        grau_instrucao = tree.item(item_selecionado[0], "values")[0]
        dados_teto = execute_query("SELECT valor_teto FROM teto_hora_aula WHERE grau_instrucao = ?", (grau_instrucao,), fetch='one')

        if not dados_teto:
            messagebox.showerror("Erro", "Teto não encontrado.", parent=janela_tetos)
            return

        janela_edicao = ctk.CTkToplevel(janela_tetos)
        janela_edicao.title(f"Editar Teto - {grau_instrucao}")
        janela_edicao.geometry("300x200")
        janela_edicao.grab_set()

        ctk.CTkLabel(janela_edicao, text=f"Novo Valor Teto para {grau_instrucao}:").pack(pady=(10, 2))
        entry_valor = ctk.CTkEntry(janela_edicao, width=200)
        entry_valor.insert(0, f"{dados_teto[0]:.2f}".replace('.', ','))
        entry_valor.pack()

        def salvar_edicao():
            novo_valor_str = entry_valor.get().strip()
            valor_limpo = re.sub(r'[^\d,]', '', novo_valor_str).replace(',', '.')
            try:
                novo_valor = float(valor_limpo)
            except ValueError:
                messagebox.showerror("Erro", "Valor do teto inválido.", parent=janela_edicao)
                return

            execute_query("UPDATE teto_hora_aula SET valor_teto = ? WHERE grau_instrucao = ?", (novo_valor, grau_instrucao))
            messagebox.showinfo("Sucesso", "Teto atualizado com sucesso!", parent=janela_edicao)
            janela_edicao.destroy()
            carregar_tetos()

        ctk.CTkButton(janela_edicao, text="Salvar", command=salvar_edicao).pack(pady=20)

    tree.bind("<Double-1>", editar_teto)
    carregar_tetos()

def listar_pagamentos_gerados():
    """Abre uma janela para listar todos os pagamentos de instrutores gerados."""
    janela_listar = ctk.CTkToplevel()
    janela_listar.title("Histórico de Pagamentos Gerados")
    janela_listar.geometry("1200x600")
    janela_listar.grab_set()

    main_frame = ctk.CTkFrame(janela_listar)
    main_frame.pack(fill="both", expand=True, padx=10, pady=10)
    main_frame.grid_rowconfigure(0, weight=1)
    main_frame.grid_columnconfigure(0, weight=1)

    tree_frame = ctk.CTkFrame(main_frame)
    tree_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
    tree_frame.grid_rowconfigure(0, weight=1)
    tree_frame.grid_columnconfigure(0, weight=1)

    colunas = (
        "ID", "Nome do Instrutor", "CPF", "Mês Ref.", "Horas/Aula", "Valor H/A",
        "Valor Bruto", "Alíquota IR", "IR Retido", "Valor Líquido", "Data Geração"
    )
    tree = ttk.Treeview(tree_frame, columns=colunas, show="headings")

    for col in colunas:
        tree.heading(col, text=col)
    
    # Ajuste de largura das colunas
    tree.column("ID", width=40, anchor="center")
    tree.column("Nome do Instrutor", width=250)
    tree.column("CPF", width=110, anchor="center")
    tree.column("Mês Ref.", width=80, anchor="center")
    tree.column("Horas/Aula", width=80, anchor="center")
    tree.column("Valor H/A", width=100, anchor="e")
    tree.column("Valor Bruto", width=120, anchor="e")
    tree.column("Alíquota IR", width=80, anchor="center")
    tree.column("IR Retido", width=120, anchor="e")
    tree.column("Valor Líquido", width=120, anchor="e")
    tree.column("Data Geração", width=130, anchor="center")

    scrollbar_v = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
    scrollbar_h = ttk.Scrollbar(tree_frame, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=scrollbar_v.set, xscrollcommand=scrollbar_h.set)
    tree.grid(row=0, column=0, sticky="nsew")
    scrollbar_v.grid(row=0, column=1, sticky="ns")
    scrollbar_h.grid(row=1, column=0, sticky="ew")

    tree.tag_configure('oddrow', background='#f0f4f8')
    tree.tag_configure('evenrow', background='#ffffff')

    def formatar_data(data_str):
        if not data_str: return ""
        try:
            return datetime.fromisoformat(data_str).strftime('%d/%m/%Y %H:%M')
        except (ValueError, TypeError):
            return data_str

    def carregar_pagamentos():
        for item in tree.get_children():
            tree.delete(item)
        
        pagamentos = execute_query("""
            SELECT id, nome_servidor, cpf_servidor, mes_referencia, horas_aula, 
                   valor_hora_aula, valor_bruto, aliquota_ir, valor_ir_retido, valor_liquido, data_geracao 
            FROM pagamentos_instrutores ORDER BY data_geracao DESC
        """, fetch='all')
        
        if not pagamentos:
            return

        for i, pg in enumerate(pagamentos):
            id_pg, nome, cpf, mes, horas, vlr_ha, bruto, aliquota, ir, liquido, data = pg
            vlr_ha_f = f"R$ {vlr_ha:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            bruto_f = f"R$ {bruto:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            aliquota_f = f"{aliquota:.2f}%".replace('.', ',') if aliquota is not None else "0,00%"
            ir_f = f"R$ {ir:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            liquido_f = f"R$ {liquido:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            data_f = formatar_data(data)
            
            valores_linha = (id_pg, nome, cpf, mes, horas, vlr_ha_f, bruto_f, aliquota_f, ir_f, liquido_f, data_f)
            tree.insert("", "end", values=valores_linha, tags=('evenrow' if i % 2 == 0 else 'oddrow',))

    controls_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
    controls_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=(5,0))

    ctk.CTkLabel(controls_frame, text="Filtrar:", font=('Calibri', 12)).pack(side="left", padx=(0,5))
    entry_filtro = ctk.CTkEntry(controls_frame)
    entry_filtro.pack(side="left", fill="x", expand=True)

    def exportar_para_excel():
        """Função para exportar os dados visíveis na Treeview para um arquivo Excel."""
        colunas = tree["columns"]
        dados = []
        # Pega apenas os itens visíveis (não desanexados pelo filtro)
        for item_id in tree.get_children():
            dados.append(tree.item(item_id)["values"])

        if not dados:
            messagebox.showinfo("Info", "Não há dados para exportar.", parent=janela_listar)
            return

        df = pd.DataFrame(dados, columns=colunas)

        try:
            filepath = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Arquivos Excel", "*.xlsx"), ("Todos os arquivos", "*.*")],
                title="Salvar Relatório de Pagamentos",
                initialfile="Relatorio_Pagamentos.xlsx"
            )

            if not filepath:
                return # Usuário cancelou a operação

            df.to_excel(filepath, index=False)
            messagebox.showinfo("Sucesso", f"Dados exportados com sucesso para:\n{filepath}", parent=janela_listar)

        except Exception as e:
            messagebox.showerror("Erro ao Exportar", f"Ocorreu um erro ao salvar o arquivo:\n{e}", parent=janela_listar)

    btn_exportar = ctk.CTkButton(controls_frame, text="Exportar para Excel", command=exportar_para_excel, width=140, fg_color="#107C41", hover_color="#149950")
    btn_exportar.pack(side="right", padx=(10,0))
    
    btn_atualizar = ctk.CTkButton(controls_frame, text="Atualizar", command=carregar_pagamentos, width=100)
    btn_atualizar.pack(side="right", padx=(10,0))

    def filtrar_pagamentos(event=None):
        filtro = entry_filtro.get().strip().lower()
        carregar_pagamentos() # Recarrega os dados para garantir que o filtro seja aplicado sobre a lista completa
        for item in tree.get_children():
            valores_linha = tree.item(item, "values")
            if not any(filtro in str(valor).lower() for valor in valores_linha):
                tree.detach(item)

    entry_filtro.bind("<KeyRelease>", filtrar_pagamentos)
    carregar_pagamentos()


#===========================================================================================================================#


def abrir_gerar_doc_empenho():
    from gerar_empenho import gerar_documento_empenho

    def gerar():
        mes_inicial = entry_data_inicial.get().strip()
        mes_final = entry_data_final.get().strip()
        save_path = entry_caminho_pasta.get().strip()

        # Validações
        if not (re.match(r"^(0[1-9]|1[0-2])/[0-9]{4}$", mes_inicial) and re.match(r"^(0[1-9]|1[0-2])/[0-9]{4}$", mes_final)):
            messagebox.showerror("Erro de Formato", "Formato da data de referência inválido. Use MM/AAAA.", parent=janela)
            return
        
        if not save_path:
            messagebox.showerror("Erro de Validação", "Por favor, selecione uma pasta para salvar o documento.", parent=janela)
            return

        try:
            data_inicial_dt = datetime.strptime(mes_inicial, "%m/%Y")
            data_final_dt = datetime.strptime(mes_final, "%m/%Y")
            if data_final_dt < data_inicial_dt:
                messagebox.showerror("Erro de Validação", "A data final não pode ser anterior à data inicial.", parent=janela)
                return
        except ValueError:
            messagebox.showerror("Erro de Formato", "As datas devem estar no formato MM/AAAA.", parent=janela)
            return

        # Chama a função de geração do documento
        status = gerar_documento_empenho(mes_inicial, mes_final, save_path)
        
        if status == "SUCCESS":
            # A mensagem de sucesso já é exibida pela função de geração
            janela.destroy()
        elif status == "NO_DATA":
            # A mensagem de "sem dados" já é exibida
            pass # Não fecha a janela para o usuário tentar outro período
        else: # ERROR
            # A mensagem de erro já é exibida
            pass

    def selecionar_pasta():
        caminho = filedialog.askdirectory(title="Selecione a pasta para salvar o documento", parent=janela)
        if caminho:
            entry_caminho_pasta.delete(0, tk.END)
            entry_caminho_pasta.insert(0, caminho)

    janela = ctk.CTkToplevel()
    janela.title("Gerar Documento de Empenho")
    janela.geometry("450x600")
    janela.wm_attributes("-topmost", True)
    janela.resizable(False, False)

    frame = ctk.CTkFrame(janela, fg_color="transparent")
    frame.pack(expand=True, padx=20, pady=20)

    ctk.CTkLabel(frame, text="Gerar Documento de Empenho", font=('Calibri', 16, 'bold')).pack(pady=(0, 10))
    ctk.CTkLabel(frame, text="Gera um documento PDF formal para empenho\ndos pagamentos do período selecionado.", justify="center").pack(pady=(0, 20))

    ctk.CTkLabel(frame, text="Referência Inicial (MM/AAAA):").pack(pady=5)
    entry_data_inicial = ctk.CTkEntry(frame, width=150, justify="center")
    entry_data_inicial.pack(pady=2)

    ctk.CTkLabel(frame, text="Referência Final (MM/AAAA):").pack(pady=5)
    entry_data_final = ctk.CTkEntry(frame, width=150, justify="center")
    entry_data_final.pack(pady=2)

    data_atual = datetime.now().strftime("%m/%Y")
    entry_data_inicial.insert(0, data_atual)
    entry_data_final.insert(0, data_atual)

    ctk.CTkLabel(frame, text="Salvar Documento em:").pack(pady=(15, 5))
    entry_caminho_pasta = ctk.CTkEntry(frame, width=300)
    entry_caminho_pasta.pack(pady=2)
    btn_selecionar_pasta = ctk.CTkButton(frame, text="Selecionar Pasta...", command=selecionar_pasta, width=150)
    btn_selecionar_pasta.pack(pady=5)
    
    def mascara_data_referencia(event):
        widget = event.widget
        digits = "".join(filter(str.isdigit, widget.get()))[:6]
        if len(digits) > 2:
            formatted_text = f"{digits[:2]}/{digits[2:]}"
        else:
            formatted_text = digits
        widget.delete(0, tk.END)
        widget.insert(0, formatted_text)
        widget.icursor(tk.END)

    entry_data_inicial.bind("<KeyRelease>", mascara_data_referencia)
    entry_data_final.bind("<KeyRelease>", mascara_data_referencia)

    ctk.CTkButton(frame, text="Gerar Documento", command=gerar, width=150, fg_color="#3a078d", hover_color="#560aac", text_color="#fff", corner_radius=18).pack(pady=(20, 5))
    ctk.CTkButton(frame, text="Cancelar", command=janela.destroy, fg_color="#6c757d", hover_color="#5a6268", text_color="#fff", corner_radius=18).pack()

#===========================================================================================================================#

def janela_gerar_txt_fita_credito():
    def gerar_txt():
        mes_ref = entry_data_referencia.get().strip()
        if not re.match(r"^(0[1-9]|1[0-2])/[0-9]{4}$", mes_ref):
            messagebox.showerror("Erro", "Formato do mês inválido. Use MM/AAAA.", parent=janelaFita)
            return
        pasta_saida = filedialog.askdirectory(
            title="Selecione a pasta para salvar a fita de crédito",
            parent=janelaFita
        )
        if not pasta_saida:
            return
        try:
            from gerar_fita_credito import gerar_fita_credito_txt
            gerar_fita_credito_txt(mes_ref, pasta_saida)
            nome_arquivo = f"Fita_Credito_{mes_ref.replace('/', '')}.txt"
            caminho_completo = os.path.join(pasta_saida, nome_arquivo)
            messagebox.showinfo("Sucesso", f"Fita de crédito gerada:\n{caminho_completo}", parent=janelaFita)
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao gerar TXT:\n{e}", parent=janelaFita)
        janelaFita.destroy()

    janelaFita = ctk.CTkToplevel()
    janelaFita.title("Gerar Fita de Crédito")
    janelaFita.geometry("400x400")
    janelaFita.grab_set()

    frame = ctk.CTkFrame(janelaFita, fg_color="transparent")
    frame.pack(expand=True, padx=20, pady=20)

    ctk.CTkLabel(frame, text="Indique o Mês de Referência", font=('Calibri', 14, 'bold')).pack(pady=(0, 10))
    ctk.CTkLabel(frame, text="Esta ferramenta gera o arquivo TXT da fita de crédito\ncom base nos pagamentos já existentes no banco.", justify="center").pack(pady=(0, 20))
    ctk.CTkLabel(frame, text="Mês de Referência (MM/AAAA):").pack(pady=5)

    entry_data_referencia = ctk.CTkEntry(frame, width=150, justify="center")
    entry_data_referencia.pack(pady=2)

    ctk.CTkButton(frame, text="Gerar Fita de Crédito", command=gerar_txt, fg_color="#400881", hover_color="#500ac0", text_color="#fff").pack(pady=(20, 5))
    ctk.CTkButton(frame, text="Cancelar", command=janelaFita.destroy, fg_color="#6c757d", hover_color="#5a6268", text_color="#fff").pack()

    def mascara_data_referencia(event):
        widget = event.widget
        digits = "".join(filter(str.isdigit, widget.get()))[:6]
        if len(digits) > 2:
            formatted_text = f"{digits[:2]}/{digits[2:]}"
        else:
            formatted_text = digits
        widget.delete(0, tk.END)
        widget.insert(0, formatted_text)
        widget.icursor(tk.END)

    entry_data_referencia.bind("<KeyRelease>", mascara_data_referencia)


#===========================================================================================================================#

def executar_migracao_db():
    """
    Garante que todas as tabelas necessárias para o SisEGOV existam no banco de dados.
    Cria as tabelas se elas não existirem.
    """
    print("Verificando a estrutura do banco de dados do SisEGOV...")

    # 1. Tabela de Usuários (users)
    execute_query("""
        CREATE TABLE IF NOT EXISTS users (
            id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_usuario TEXT UNIQUE,
            senha TEXT,
            status TEXT DEFAULT 'ATIVO',
            nome_completo TEXT,
            num_matr TEXT,
            perfil TEXT
        )
    """)

    # 2. Tabela de Servidores/Instrutores (servidores)
    execute_query("""
        CREATE TABLE IF NOT EXISTS servidores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            cpf TEXT UNIQUE,
            identidade TEXT,
            orgao_emissor TEXT,
            email TEXT,
            endereco TEXT,
            cep TEXT,
            telefone TEXT,
            numero_banco TEXT,
            descricao_banco TEXT,
            agencia TEXT,
            numero_conta TEXT,
            processo_sei TEXT,
            grau_instrucao TEXT,
            cargo_efetivo TEXT,
            numero_orgao_origem TEXT,
            orgao_de_origem TEXT,
            link_declaracao_funcional TEXT,
            observacoes TEXT
        )
    """)

    # 3. Tabela de Cargos Efetivos
    execute_query("""
        CREATE TABLE IF NOT EXISTS Cargo_Efetivo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            descricao_cargo TEXT UNIQUE,
            valor_maior_vencimento REAL
        )
    """)

    # 4. Tabela de Órgãos de Origem
    execute_query("""
        CREATE TABLE IF NOT EXISTS orgao_de_origem (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_orgao TEXT UNIQUE,
            descricao_orgao TEXT
        )
    """)

    # 5. Tabela de Imposto de Renda
    execute_query("""
        CREATE TABLE IF NOT EXISTS imposto_de_renda (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            valor_minimo REAL,
            valor_maximo REAL,
            incidencia REAL,
            valor_deducao REAL,
            data_vigencia TEXT
        )
    """)

    # 6. Tabela de Pagamentos Gerados para Instrutores
    execute_query("""
        CREATE TABLE IF NOT EXISTS pagamentos_instrutores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            servidor_id INTEGER,
            cpf_servidor TEXT,
            nome_servidor TEXT,
            mes_referencia TEXT,
            horas_aula INTEGER,
            valor_hora_aula REAL,
            valor_bruto REAL,
            base_calculo_ir REAL,
            aliquota_ir REAL,
            deducao_ir REAL,
            valor_ir_retido REAL,
            valor_liquido REAL,
            data_geracao TEXT,
            usuario_id INTEGER
        )
    """)

    # 7. Tabela de Teto de Hora/Aula
    execute_query("""
        CREATE TABLE IF NOT EXISTS teto_hora_aula (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            grau_instrucao TEXT UNIQUE,
            valor_teto REAL
        )
    """)

    # Pre-popula a tabela de tetos se estiver vazia
    count = execute_query("SELECT COUNT(*) FROM teto_hora_aula", fetch='one')
    if count and count[0] == 0:
        print("Populando a tabela 'teto_hora_aula' com valores iniciais...")
        tetos_iniciais = [
            ('Nível Médio', 88.00),
            ('Graduação', 126.00),
            ('Pós-graduação', 176.00),
            ('Mestrado', 214.00),
            ('Doutorado', 239.00)
        ]
        for grau, valor in tetos_iniciais:
            execute_query("INSERT INTO teto_hora_aula (grau_instrucao, valor_teto) VALUES (?, ?)", (grau, valor))
        print("Tabela 'teto_hora_aula' populada.")

    print("Verificação do banco de dados concluída.")

# --- CHAMADA DA FUNÇÃO ---
executar_migracao_db()
login()