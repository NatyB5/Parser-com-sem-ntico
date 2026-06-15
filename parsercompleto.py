class token():
    def __init__(self, tipo, valor, linha, coluna):
        self.tipo = tipo
        self.valor = valor
        self.linha = linha
        self.coluna = coluna

class entrada_tabela():
    def __init__(self, nome, tipo, linha, coluna, vglobal, vlocal, bloco):
        self.nome    = nome
        self.tipo    = tipo
        self.linha   = linha
        self.coluna  = coluna
        self.vglobal = vglobal   
        self.vlocal  = vlocal    
        self.bloco   = bloco     

def separar_linha(linha):
    partes = []
    atual = ""
    dentro_aspas = False
    for caractere in linha:
        if caractere == "'":
            dentro_aspas = not dentro_aspas
            continue
        if caractere == "," and not dentro_aspas:
            partes.append(atual.strip())
            atual = ""
        else:
            atual += caractere
    partes.append(atual.strip())
    return partes


erros_semanticos  = []
warnings_semanticos = []

def erro_semantico(msg, linha, coluna):
    texto = f"ERRO SEMÂNTICO   | Linha {linha}, Coluna {coluna} | {msg}"
    erros_semanticos.append(texto)
    print(texto)

def warning_semantico(msg, linha, coluna):
    texto = f"WARNING SEMÂNTICO| Linha {linha}, Coluna {coluna} | {msg}"
    warnings_semanticos.append(texto)
    print(texto)

TIPOS_NUMERICOS = {"int", "float", "double"}

def tipos_compativeis(tipo1, tipo2):
    if tipo1 == tipo2:
        return True
    if tipo1 in TIPOS_NUMERICOS and tipo2 in TIPOS_NUMERICOS:
        return True
    return False

def tipo_do_token(t, tabela):
    if t.tipo == "NUM_INT":        return "int"
    if t.tipo == "NUM_FLOAT":      return "float"
    if t.tipo == "STRING_LITERAL": return "string"
    if t.tipo == "ID":
        entrada = buscar_variavel(tabela, t.valor)
        if entrada:
            return entrada.tipo
    return None
def buscar_variavel(tabela, nome):
    for entrada in reversed(tabela):
        if entrada.nome == nome:
            return entrada
    return None

def buscar_no_bloco(tabela, nome, numero_bloco):
    for entrada in tabela:
        if entrada.nome == nome and entrada.bloco == numero_bloco:
            return entrada
    return None

def checar_redeclaracao(tabela, nome, numero_bloco, pilha_blocos, linha, coluna):
    eh_global = (numero_bloco == 0)

    if eh_global:
        for entrada in tabela:
            if entrada.nome == nome and entrada.vglobal:
                erro_semantico(
                    f"Variável global '{nome}' já declarada (linha {entrada.linha})",
                    linha, coluna
                )
                return False
    else:
        existente = buscar_no_bloco(tabela, nome, numero_bloco)
        if existente:
            erro_semantico(
                f"Variável local '{nome}' já declarada neste bloco (linha {existente.linha})",
                linha, coluna
            )
            return False
        for entrada in tabela:
            if entrada.nome == nome and entrada.vglobal:
                warning_semantico(
                    f"Variável local '{nome}' esconde a variável global de mesmo nome "
                    f"(declarada na linha {entrada.linha})",
                    linha, coluna
                )
                break
    return True

def checar_uso(tabela, nome, pilha_blocos, linha, coluna):
    for nome_bloco in reversed(pilha_blocos):
        numero = 0 if nome_bloco == "Bloco Principal" else int(nome_bloco.split()[1])
        encontrado = buscar_no_bloco(tabela, nome, numero)
        if encontrado:
            return encontrado
    erro_semantico(f"Variável '{nome}' usada sem declaração", linha, coluna)
    return None

def analisar_semantico(vetor):
    tabela       = []        
    pilha_blocos = ["Bloco Principal"] 
    contador_bloco = [0]     

    pos = 0
    while pos < len(vetor):
        t = vetor[pos]
        if t.tipo == "DELIMITADORES" and t.valor == "{":
            contador_bloco[0] += 1
            pilha_blocos.append("Bloco " + str(contador_bloco[0]))
            pos += 1
            continue
        if t.tipo == "DELIMITADORES" and t.valor == "}":
            if len(pilha_blocos) > 1:
                pilha_blocos.pop()
            pos += 1
            continue
        if t.tipo == "PALAVRA_CHAVE" and t.valor in ("int", "float", "double", "string"):
            tipo_declarado = t.valor
            pos += 1

            while pos < len(vetor) and vetor[pos].tipo == "ID":
                nome_var   = vetor[pos].valor
                linha_var  = vetor[pos].linha
                coluna_var = vetor[pos].coluna
                nome_bloco_atual = pilha_blocos[-1]
                num_bloco_atual  = 0 if nome_bloco_atual == "Bloco Principal" else int(nome_bloco_atual.split()[1])
                eh_global        = (num_bloco_atual == 0)

                ok = checar_redeclaracao(tabela, nome_var, num_bloco_atual, pilha_blocos, linha_var, coluna_var)
                if ok:
                    tabela.append(entrada_tabela(
                        nome_var, tipo_declarado, linha_var, coluna_var,
                        vglobal = eh_global,
                        vlocal  = not eh_global,
                        bloco   = num_bloco_atual
                    ))
                pos += 1
                if pos < len(vetor) and vetor[pos].tipo == "ATRIBUICAO":
                    pos += 1
                    tipo_expr, pos = avaliar_expressao(vetor, pos, tabela, pilha_blocos)
                    if tipo_expr and not tipos_compativeis(tipo_declarado, tipo_expr):
                        erro_semantico(
                            f"Tipo incompatível: '{nome_var}' é '{tipo_declarado}' "
                            f"mas recebe valor do tipo '{tipo_expr}'",
                            linha_var, coluna_var
                        )
                    elif (tipo_declarado in TIPOS_NUMERICOS and tipo_expr in TIPOS_NUMERICOS
                          and tipo_declarado != tipo_expr):
                        warning_semantico(
                            f"Conversão implícita: '{tipo_expr}' → '{tipo_declarado}' em '{nome_var}'",
                            linha_var, coluna_var
                        )

                if pos < len(vetor) and vetor[pos].tipo == "DELIMITADORES" and vetor[pos].valor == ",":
                    pos += 1
                else:
                    break

            if pos < len(vetor) and vetor[pos].tipo == "DELIMITADORES" and vetor[pos].valor == ";":
                pos += 1
            continue
        if t.tipo == "ID":
            prox = vetor[pos + 1] if pos + 1 < len(vetor) else None
            if prox and prox.tipo == "ATRIBUICAO":
                entrada = checar_uso(tabela, t.valor, pilha_blocos, t.linha, t.coluna)
                pos += 2  
                tipo_expr, pos = avaliar_expressao(vetor, pos, tabela, pilha_blocos)
                if entrada and tipo_expr and not tipos_compativeis(entrada.tipo, tipo_expr):
                    erro_semantico(
                        f"Tipo incompatível: '{t.valor}' é '{entrada.tipo}' "
                        f"mas recebe valor do tipo '{tipo_expr}'",
                        t.linha, t.coluna
                    )
                elif (entrada and tipo_expr
                      and entrada.tipo in TIPOS_NUMERICOS and tipo_expr in TIPOS_NUMERICOS
                      and entrada.tipo != tipo_expr):
                    warning_semantico(
                        f"Conversão implícita: '{tipo_expr}' → '{entrada.tipo}' em '{t.valor}'",
                        t.linha, t.coluna
                    )
                if pos < len(vetor) and vetor[pos].tipo == "DELIMITADORES" and vetor[pos].valor == ";":
                    pos += 1
                continue
            checar_uso(tabela, t.valor, pilha_blocos, t.linha, t.coluna)
            pos += 1
            continue

        pos += 1

    print()
    if erros_semanticos:
        print(f"Análise semântica : erros ={len(erros_semanticos)}  e warnings = {len(warnings_semanticos)} ")
    else:
        print(f"Análise semântica warnings = ({len(warnings_semanticos)})")


def avaliar_expressao(vetor, pos, tabela, pilha_blocos):
    tipo_resultado = None
    while pos < len(vetor):
        t = vetor[pos]
        if t.tipo == "DELIMITADORES" and t.valor in (";", ")", "]", ","):
            break
        if t.tipo == "ID":
            entrada = checar_uso(tabela, t.valor, pilha_blocos, t.linha, t.coluna)
            if entrada:
                tipo_token = entrada.tipo
                if tipo_resultado is None:
                    tipo_resultado = tipo_token
                elif not tipos_compativeis(tipo_resultado, tipo_token):
                    erro_semantico(
                        f"Operação entre tipos incompatíveis: '{tipo_resultado}' e '{tipo_token}'",
                        t.linha, t.coluna
                    )
        elif t.tipo in ("NUM_INT", "NUM_FLOAT", "STRING_LITERAL"):
            tipo_token = tipo_do_token(t, tabela)
            if tipo_resultado is None:
                tipo_resultado = tipo_token
            elif not tipos_compativeis(tipo_resultado, tipo_token):
                erro_semantico(
                    f"Operação entre tipos incompatíveis: '{tipo_resultado}' e '{tipo_token}'",
                    t.linha, t.coluna
                )
        elif t.tipo == "DELIMITADORES" and t.valor == "(":
            pos += 1
            tipo_sub, pos = avaliar_expressao(vetor, pos, tabela, pilha_blocos)
            if tipo_sub:
                if tipo_resultado is None:
                    tipo_resultado = tipo_sub
                elif not tipos_compativeis(tipo_resultado, tipo_sub):
                    erro_semantico(
                        f"Operação entre tipos incompatíveis: '{tipo_resultado}' e '{tipo_sub}'",
                        t.linha, t.coluna
                    )
            if pos < len(vetor) and vetor[pos].tipo == "DELIMITADORES" and vetor[pos].valor == ")":
                pos += 1
            continue
        pos += 1
    return tipo_resultado, pos
erros = []

def registrar_erro(vetor, pos, esperado):
    if pos < len(vetor):
        t = vetor[pos]
        msg = (f"ERRO SINTÁTICO | Linha {t.linha}, Coluna {t.coluna} "
               f"| Encontrado: '{t.valor}' (tipo: {t.tipo}) "
               f"| Esperado: {esperado}")
    else:
        msg = f"ERRO SINTÁTICO | Fim inesperado do arquivo | Esperado: {esperado}"
    erros.append(msg)
    print(msg)

def recuperar(vetor, pos):
    while pos < len(vetor):
        if vetor[pos].tipo == "DELIMITADORES" and vetor[pos].valor == ";":
            return pos + 1
        pos += 1
    return pos
def termo(vetor, pos):
    if pos >= len(vetor):
        registrar_erro(vetor, pos, "expressão")
        return pos
    t = vetor[pos]
    if t.tipo in ("NUM_INT", "NUM_FLOAT", "STRING_LITERAL"):
        return pos + 1
    elif t.tipo == "ID":
        pos += 1
        if pos < len(vetor) and vetor[pos].tipo == "DELIMITADORES" and vetor[pos].valor == "[":
            pos += 1
            pos = expressao(vetor, pos)
            if pos < len(vetor) and vetor[pos].tipo == "DELIMITADORES" and vetor[pos].valor == "]":
                pos += 1
            else:
                registrar_erro(vetor, pos, "']'")
                pos = recuperar(vetor, pos)
        return pos
    elif t.tipo == "DELIMITADORES" and t.valor == "(":
        pos += 1
        pos = expressao(vetor, pos)
        if pos < len(vetor) and vetor[pos].tipo == "DELIMITADORES" and vetor[pos].valor == ")":
            return pos + 1
        else:
            registrar_erro(vetor, pos, "')'")
            return recuperar(vetor, pos)
    else:
        registrar_erro(vetor, pos, "valor, identificador ou '('")
        return recuperar(vetor, pos)

def expressao(vetor, pos):
    pos = termo(vetor, pos)
    while pos < len(vetor) and vetor[pos].tipo in ("OPERADORES", "LOGICOS"):
        pos += 1
        pos = termo(vetor, pos)
    return pos

def declaracao(vetor, pos):
    pos += 1
    if pos >= len(vetor) or vetor[pos].tipo != "ID":
        registrar_erro(vetor, pos, "identificador após tipo")
        return recuperar(vetor, pos)
    pos += 1
    while pos < len(vetor) and vetor[pos].tipo == "DELIMITADORES" and vetor[pos].valor == ",":
        pos += 1
        if pos >= len(vetor) or vetor[pos].tipo != "ID":
            registrar_erro(vetor, pos, "identificador após ','")
            return recuperar(vetor, pos)
        pos += 1
    if pos < len(vetor) and vetor[pos].tipo == "ATRIBUICAO":
        pos += 1
        pos = expressao(vetor, pos)
    if pos < len(vetor) and vetor[pos].tipo == "DELIMITADORES" and vetor[pos].valor == ";":
        return pos + 1
    else:
        registrar_erro(vetor, pos, "';'")
        return recuperar(vetor, pos)

def atribuicao(vetor, pos):
    pos += 1
    if pos < len(vetor) and vetor[pos].tipo == "DELIMITADORES" and vetor[pos].valor == "[":
        pos += 1
        pos = expressao(vetor, pos)
        if pos < len(vetor) and vetor[pos].tipo == "DELIMITADORES" and vetor[pos].valor == "]":
            pos += 1
        else:
            registrar_erro(vetor, pos, "']'")
            return recuperar(vetor, pos)
    if pos >= len(vetor) or vetor[pos].tipo != "ATRIBUICAO":
        registrar_erro(vetor, pos, "'='")
        return recuperar(vetor, pos)
    pos += 1
    pos = expressao(vetor, pos)
    if pos < len(vetor) and vetor[pos].tipo == "DELIMITADORES" and vetor[pos].valor == ";":
        return pos + 1
    else:
        registrar_erro(vetor, pos, "';'")
        return recuperar(vetor, pos)

def condicional(vetor, pos):
    pos += 1
    if pos >= len(vetor) or not (vetor[pos].tipo == "DELIMITADORES" and vetor[pos].valor == "("):
        registrar_erro(vetor, pos, "'('")
        return recuperar(vetor, pos)
    pos += 1
    pos = expressao(vetor, pos)
    if pos >= len(vetor) or not (vetor[pos].tipo == "DELIMITADORES" and vetor[pos].valor == ")"):
        registrar_erro(vetor, pos, "')'")
        return recuperar(vetor, pos)
    pos += 1
    if pos >= len(vetor) or not (vetor[pos].tipo == "DELIMITADORES" and vetor[pos].valor == "{"):
        registrar_erro(vetor, pos, "'{'")
        return recuperar(vetor, pos)
    pos += 1
    return pos

def repeticao(vetor, pos):
    tipo_laco = vetor[pos].valor
    pos += 1
    if pos >= len(vetor) or not (vetor[pos].tipo == "DELIMITADORES" and vetor[pos].valor == "("):
        registrar_erro(vetor, pos, "'('")
        return recuperar(vetor, pos)
    pos += 1
    if tipo_laco == "while":
        pos = expressao(vetor, pos)
    else:
        if pos < len(vetor) and not (vetor[pos].tipo == "DELIMITADORES" and vetor[pos].valor == ";"):
            t = vetor[pos]
            if t.tipo == "PALAVRA_CHAVE" and t.valor in ("int", "float", "string", "double"):
                pos += 1
                if pos < len(vetor) and vetor[pos].tipo == "ID":
                    pos += 1
                if pos < len(vetor) and vetor[pos].tipo == "ATRIBUICAO":
                    pos += 1
                    pos = expressao(vetor, pos)
            elif t.tipo == "ID":
                pos += 1
                if pos < len(vetor) and vetor[pos].tipo == "ATRIBUICAO":
                    pos += 1
                    pos = expressao(vetor, pos)
        if pos >= len(vetor) or not (vetor[pos].tipo == "DELIMITADORES" and vetor[pos].valor == ";"):
            registrar_erro(vetor, pos, "';' após init do for")
            return recuperar(vetor, pos)
        pos += 1
        if pos < len(vetor) and not (vetor[pos].tipo == "DELIMITADORES" and vetor[pos].valor == ";"):
            pos = expressao(vetor, pos)
        if pos >= len(vetor) or not (vetor[pos].tipo == "DELIMITADORES" and vetor[pos].valor == ";"):
            registrar_erro(vetor, pos, "';' após condição do for")
            return recuperar(vetor, pos)
        pos += 1
        if pos < len(vetor) and not (vetor[pos].tipo == "DELIMITADORES" and vetor[pos].valor == ")"):
            pos = expressao(vetor, pos)
    if pos >= len(vetor) or not (vetor[pos].tipo == "DELIMITADORES" and vetor[pos].valor == ")"):
        registrar_erro(vetor, pos, "')'")
        return recuperar(vetor, pos)
    pos += 1
    if pos >= len(vetor) or not (vetor[pos].tipo == "DELIMITADORES" and vetor[pos].valor == "{"):
        registrar_erro(vetor, pos, "'{'")
        return recuperar(vetor, pos)
    pos += 1
    return pos

def validacao(vetor):
    pos = 0
    while pos < len(vetor):
        tipo_atual  = vetor[pos].tipo
        valor_atual = vetor[pos].valor
        prox_tipo   = vetor[pos + 1].tipo  if pos + 1 < len(vetor) else None
        prox_valor  = vetor[pos + 1].valor if pos + 1 < len(vetor) else None

        if tipo_atual == "PALAVRA_CHAVE":
            if valor_atual in ("int", "float", "string", "double") and prox_tipo == "ID":
                pos = declaracao(vetor, pos)
            elif valor_atual in ("int", "float", "string", "double") and prox_tipo == "ATRIBUICAO":
                pos = declaracao(vetor, pos)
            elif valor_atual in ("int", "float", "string", "double") and prox_tipo == "DELIMITADORES":
                registrar_erro(vetor, pos, "identificador após tipo")
                pos = recuperar(vetor, pos)
            elif valor_atual in ("int", "float", "string", "double") and prox_tipo == "OPERADORES":
                registrar_erro(vetor, pos, "identificador após tipo")
                pos = recuperar(vetor, pos)
            elif valor_atual in ("for", "while") and prox_tipo == "DELIMITADORES":
                pos = repeticao(vetor, pos)
            elif valor_atual == "if" and prox_tipo == "DELIMITADORES":
                pos = condicional(vetor, pos)
            elif valor_atual == "else":
                pos += 1
                if pos < len(vetor) and vetor[pos].tipo == "PALAVRA_CHAVE" and vetor[pos].valor == "if":
                    pos = condicional(vetor, pos)
                elif pos < len(vetor) and vetor[pos].tipo == "DELIMITADORES" and vetor[pos].valor == "{":
                    pos += 1
                else:
                    registrar_erro(vetor, pos, "'{' ou 'if' após 'else'")
                    pos = recuperar(vetor, pos)
            elif valor_atual == "return":
                pos += 1
                if pos < len(vetor) and not (vetor[pos].tipo == "DELIMITADORES" and vetor[pos].valor == ";"):
                    pos = expressao(vetor, pos)
                if pos < len(vetor) and vetor[pos].tipo == "DELIMITADORES" and vetor[pos].valor == ";":
                    pos += 1
                else:
                    registrar_erro(vetor, pos, "';'")
                    pos = recuperar(vetor, pos)
            else:
                registrar_erro(vetor, pos, "instrução válida")
                pos = recuperar(vetor, pos)
        elif tipo_atual == "ID":
            pos = atribuicao(vetor, pos)
        elif tipo_atual == "DELIMITADORES" and valor_atual in ("{", "}"):
            pos += 1
        else:
            registrar_erro(vetor, pos, "início de instrução")
            pos = recuperar(vetor, pos)

    if not erros:
        print("\nSem erros")
def main():
    tokens = []
    try:
        with open("tokens.txt", "r") as arquivo:
            for linha in arquivo:
                linha = linha.strip().replace("(", "").replace(")", "")
                partes = separar_linha(linha)
                tipo, valor, linha_num, coluna_num = partes
                tokens.append(token(tipo, valor, int(linha_num), int(coluna_num)))
                print(f"Token: {tipo}, Valor: {valor}, Linha: {linha_num}, Coluna: {coluna_num}")
    except Exception as e:
        print(f"Erro: {e}")
        return
    validacao(tokens)
    analisar_semantico(tokens)


if __name__ == "__main__":
    main()