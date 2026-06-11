import io
import base64
from datetime import datetime, timedelta
from collections import OrderedDict
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib import colors


def format_brl_pdf(v):
    try:
        v = float(v)
    except Exception:
        return "-"
    sinal = "-" if v < 0 else ""
    v = abs(v)
    inteiro_str, dec_str = f"{v:.2f}".split(".")
    inteiro_grp = "{:,}".format(int(inteiro_str)).replace(",", ".")
    return f"{sinal}{inteiro_grp},{dec_str}"


def fmt_pdf(x):
    try:
        x = float(x)
    except Exception:
        return "-"
    if x <= 0:
        return "-"
    return f"{x:.2f}".replace(".", ",")


def wrap_text(texto, fonte, tamanho, largura_max, c_obj):
    from reportlab.pdfbase import pdfmetrics
    palavras = str(texto).split()
    linhas = []
    atual = ""
    for palavra in palavras:
        teste = (atual + " " + palavra).strip()
        if pdfmetrics.stringWidth(teste, fonte, tamanho) <= largura_max:
            atual = teste
        else:
            if atual:
                linhas.append(atual)
            atual = palavra
    if atual:
        linhas.append(atual)
    return linhas or [""]


def gerar_pdf_orcamento(
    nome_cliente, endereco_obra, data_orcamento, itens,
    numero_orcamento, forma_pagamento, mostrar_nota=True,
    logo_base64="", ocultar_valores_itens=False,
    desconto_tipo="fixo", desconto_valor=0
):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    largura, altura = A4

    logo_img = None
    if logo_base64:
        try:
            from reportlab.lib.utils import ImageReader
            img_data = base64.b64decode(logo_base64)
            logo_img = ImageReader(io.BytesIO(img_data))
        except Exception:
            logo_img = None

    def desenhar_cabecalho(completo=True):
        topo = altura - 20 * mm

        if logo_img:
            try:
                logo_larg = 70 * mm
                logo_alt = 30 * mm
                x_logo = 20 * mm
                y_logo = topo - logo_alt + 12 * mm
                c.drawImage(logo_img, x_logo, y_logo,
                            width=logo_larg, height=logo_alt,
                            preserveAspectRatio=True, mask="auto")
            except Exception:
                pass

        x_txt = 95 * mm
        y_txt = topo + 3 * mm
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(x_txt, y_txt, "MARMORARIA EBENEZER MARMORES E GRANITOS")
        y_txt -= 5 * mm
        c.setFont("Helvetica", 9)
        c.drawString(x_txt, y_txt, "RUA SAFIRA, 842 - RECREIO CAMPESTRE JOIA - INDAIATUBA/SP")
        y_txt -= 4 * mm
        c.drawString(x_txt, y_txt, "Telefone(s): (19) 99514-0294 / (19) 99118-6672")
        y_txt -= 4 * mm
        c.drawString(x_txt, y_txt, "E-mail: ebenezermarmoraria2020@gmail.com")
        y_txt -= 4 * mm
        c.drawString(x_txt, y_txt, "CNPJ: 35.639.338/0001-72")

        if completo:
            y = topo - 25 * mm
            c.setFont("Helvetica-Bold", 9)
            c.drawString(15 * mm, y, f"CLIENTE: {nome_cliente}")
            c.drawString(120 * mm, y, f"DATA: {data_orcamento or datetime.now().strftime('%d/%m/%Y')}")
            y -= 6 * mm
            c.setFont("Helvetica", 9)
            c.drawString(15 * mm, y, f"ENDEREÇO: {endereco_obra}")
            y -= 10 * mm

            try:
                num_orc = f"{int(numero_orcamento):03d}"
            except Exception:
                num_orc = str(numero_orcamento)

            x0 = 15 * mm
            x1 = largura - 15 * mm
            altura_barra = 8 * mm
            c.setFont("Helvetica-Bold", 12)
            c.rect(x0, y - altura_barra, (x1 - x0), altura_barra, stroke=1, fill=0)
            c.drawCentredString((x0 + x1) / 2, y - altura_barra + 3 * mm, f"ORÇAMENTO N.{num_orc}")
            y -= altura_barra + 5 * mm
        else:
            y = topo - 35 * mm

        x0 = 15 * mm
        x1 = largura - 15 * mm
        return y, x0, x1

    # Agrupar por ambiente
    grupos = OrderedDict()
    for item in itens:
        nome_amb = item.get("ambiente") or item.get("nome", "")
        if nome_amb not in grupos:
            grupos[nome_amb] = []
        grupos[nome_amb].append(item)

    y, x0, x1 = desenhar_cabecalho(completo=True)
    row_h = 7 * mm
    total_geral = 0.0

    col_qtd = x0 + 7 * mm
    col_desc = x0 + 27 * mm
    col_mat = x0 + 85 * mm
    col_comp = x0 + 112 * mm
    col_larg = x0 + 127 * mm
    col_ml = x0 + 140 * mm
    col_m2 = x0 + 154 * mm
    col_total = x1 - 3 * mm

    def desenhar_cabecalho_tabela(c_obj, x0, x1, y):
        c_obj.setStrokeColor(colors.black)
        c_obj.setFillColor(colors.red)
        c_obj.rect(x0, y - row_h, (x1 - x0), row_h, stroke=1, fill=1)
        c_obj.setFillColor(colors.black)
        c_obj.setFont("Helvetica-Bold", 7.8)
        base_y = y - row_h + 2.5 * mm
        c_obj.drawCentredString(col_qtd, base_y, "QUANT.")
        c_obj.drawCentredString(col_desc, base_y, "DESCRIÇÃO")
        c_obj.drawCentredString(col_mat, base_y, "MATERIAL")
        c_obj.drawCentredString(col_comp, base_y, "COMP.")
        c_obj.drawCentredString(col_larg, base_y, "LARG.")
        c_obj.drawCentredString(col_ml, base_y, "ML")
        c_obj.drawCentredString(col_m2, base_y, "M²")
        c_obj.drawRightString(col_total, base_y, "VALOR (R$)")
        return y - row_h

    for nome_amb, grupo_itens in grupos.items():
        altura_bloco = (len(grupo_itens) + 2) * row_h + 10 * mm
        if y - altura_bloco < 25 * mm:
            c.showPage()
            y, x0, x1 = desenhar_cabecalho(completo=False)

        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(colors.black)
        c.drawString(x0, y, f"AMBIENTE: {nome_amb}")
        y -= 4 * mm
        y = desenhar_cabecalho_tabela(c, x0, x1, y)

        subtotal = 0.0
        c.setFont("Helvetica", 8.5)

        for item in grupo_itens:
            descricao = item.get("descricao") or nome_amb
            qtd_item = item.get("qtd", 1)
            material = item.get("material", "-")

            linhas_desc = wrap_text(descricao, "Helvetica", 8.5, 48 * mm, c)
            linhas_mat = wrap_text(material, "Helvetica", 8.5, 48 * mm, c)
            max_linhas = max(len(linhas_desc), len(linhas_mat), 1)

            altura_linha_txt = 4.8 * mm
            item_row_h = max(row_h, (max_linhas * altura_linha_txt) + 3.5 * mm)

            if y - item_row_h < 25 * mm:
                c.showPage()
                y, x0, x1 = desenhar_cabecalho(completo=False)
                c.setFont("Helvetica-Bold", 9)
                c.drawString(x0, y, f"AMBIENTE: {nome_amb} - CONTINUAÇÃO")
                y -= 4 * mm
                y = desenhar_cabecalho_tabela(c, x0, x1, y)
                c.setFont("Helvetica", 8.5)

            c.setFillColor(colors.whitesmoke)
            c.rect(x0, y - item_row_h, (x1 - x0), item_row_h, stroke=1, fill=1)
            c.setFillColor(colors.black)
            c.setFont("Helvetica", 8.5)

            py = y - 5 * mm
            desc_x = x0 + 14 * mm

            c.drawCentredString(col_qtd, py, f"{float(qtd_item):.0f}")
            for i, linha in enumerate(linhas_desc):
                c.drawString(desc_x, py - i * altura_linha_txt, linha)
            for i, linha in enumerate(linhas_mat):
                c.drawCentredString(col_mat, py - i * altura_linha_txt, linha)

            ml_txt = fmt_pdf(item.get("ml", 0))
            if ml_txt == "-":
                ml_txt = ""

            c.drawCentredString(col_comp, py, fmt_pdf(item.get("comp", 0)))
            c.drawCentredString(col_larg, py, fmt_pdf(item.get("larg", 0)))
            c.drawCentredString(col_ml, py, ml_txt)
            c.drawCentredString(col_m2, py, fmt_pdf(item.get("area", 0)))

            total_item = float(item.get("total", 0))
            if ocultar_valores_itens or item.get("ocultar_valor_pdf"):
                c.drawRightString(col_total, py, "-")
            else:
                c.drawRightString(col_total, py, format_brl_pdf(total_item))

            subtotal += total_item
            total_geral += total_item
            y -= item_row_h

        c.setFillColor(colors.lightgrey)
        c.rect(x0, y - row_h, (x1 - x0), row_h, stroke=1, fill=1)
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 8.5)
        base_y = y - row_h + 2.5 * mm
        c.drawString(x0 + 5 * mm, base_y, "SUBTOTAL")
        c.drawRightString(col_total, base_y, f"R$ {format_brl_pdf(subtotal)}")
        y -= row_h + 5 * mm

    if y < 75 * mm:
        c.showPage()
        y, x0, x1 = desenhar_cabecalho(completo=False)
        y -= 5 * mm

    desconto_valor = float(desconto_valor or 0)
    if desconto_tipo == "pct" and desconto_valor > 0:
        desconto_real = total_geral * desconto_valor / 100
    elif desconto_tipo == "fixo" and desconto_valor > 0:
        desconto_real = desconto_valor
    else:
        desconto_real = 0
    total_final = total_geral - desconto_real
    total_com_nota = total_final * 1.08

    total_x_right = 195 * mm
    total_top_y = y - 1 * mm

    c.setStrokeColor(colors.black)
    c.setLineWidth(1)
    c.line(142 * mm, total_top_y + 4 * mm, total_x_right, total_top_y + 4 * mm)
    c.setFillColor(colors.black)

    if desconto_real > 0:
        c.setFont("Helvetica", 10)
        c.drawRightString(total_x_right, total_top_y - 2 * mm, f"SUBTOTAL: R$ {format_brl_pdf(total_geral)}")
        total_top_y -= 7 * mm
        if desconto_tipo == "pct":
            desc_label = f"DESCONTO ({desconto_valor:.2g}%): -R$ {format_brl_pdf(desconto_real)}"
        else:
            desc_label = f"DESCONTO: -R$ {format_brl_pdf(desconto_real)}"
        c.setFont("Helvetica-Bold", 10)
        c.drawRightString(total_x_right, total_top_y - 2 * mm, desc_label)
        total_top_y -= 8 * mm

    c.setFont("Helvetica-Bold", 13)
    c.drawRightString(total_x_right, total_top_y - 2 * mm, f"TOTAL: R$ {format_brl_pdf(total_final)}")

    y = total_top_y - 10 * mm
    c.setStrokeColor(colors.black)
    c.setLineWidth(1.2)
    c.line(15 * mm, y, 195 * mm, y)
    y -= 6 * mm

    try:
        dt_base = datetime.strptime(data_orcamento, "%d/%m/%Y")
        validade = (dt_base + timedelta(days=3)).strftime("%d/%m/%Y")
    except Exception:
        validade = ""

    box_x0 = 15 * mm
    box_x1 = 195 * mm
    line_h = 5 * mm
    max_w = (box_x1 - box_x0) - 6 * mm

    from reportlab.pdfbase import pdfmetrics

    def wrap_lines(texto, fonte, tamanho, lmax):
        palavras = texto.split()
        linhas = []
        atual = ""
        for p in palavras:
            teste = (atual + " " + p).strip()
            if pdfmetrics.stringWidth(teste, fonte, tamanho) <= lmax:
                atual = teste
            else:
                if atual:
                    linhas.append(atual)
                atual = p
        if atual:
            linhas.append(atual)
        return linhas

    itens_nota = [
        ("TOTAL COM ENCARGOS", "Helvetica-Bold", True),
        (f"Encargos fiscais, pagos contra emissão de NFE (8%)", "Helvetica-Bold", True),
        ("Mármores e Granitos, por natureza estão sujeitos a variações de cores etc. não podendo ser devolvidos por este motivo.", "Helvetica", False),
        (f"Validade: {validade}", "Helvetica-Bold", False),
        ("NÃO INCLUSO MATERIAIS PARA INSTALAÇÃO, TAIS COMO ARGAMASSA E REJUNTE.", "Helvetica-Bold", True),
        ("MATERIAIS IMPORTADOS HÁ VARIAÇÕES DE VALORES CONFORME COTAÇÃO DO DÓLAR.", "Helvetica", False),
        ("Caso os itens necessários para corte e instalação não estejam disponíveis no local na data agendada, será cobrada uma taxa adicional para retorno.", "Helvetica", False),
    ]

    linhas = []
    for texto, fonte, cinza in itens_nota:
        for l in wrap_lines(texto, fonte, 9.5, max_w):
            linhas.append((l, fonte, cinza))

    box_h = (line_h * len(linhas)) + 4 * mm
    box_top = y - 1 * mm

    c.setFillColor(colors.lightgrey)
    for i, (_, _, cinza) in enumerate(linhas):
        if cinza:
            c.rect(box_x0 + 0.6 * mm,
                   box_top - ((i + 1) * line_h) - 1 * mm,
                   (box_x1 - box_x0) - 1.2 * mm,
                   line_h, stroke=0, fill=1)

    c.setFillColor(colors.black)
    c.setStrokeColor(colors.black)
    c.setLineWidth(1)
    c.rect(box_x0, box_top - box_h, box_x1 - box_x0, box_h, stroke=1, fill=0)

    for i, (txt, fonte, _) in enumerate(linhas):
        ty = box_top - (i * line_h) - 4.5 * mm
        c.setFont(fonte, 9.5)
        c.drawString(box_x0 + 2 * mm, ty, txt)
        if i == 1 and mostrar_nota:
            c.setFont("Helvetica-Bold", 9)
            c.drawRightString(box_x1 - 2 * mm, ty, f"R$ {format_brl_pdf(total_com_nota)}")

    y = box_top - box_h - 9 * mm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(15 * mm, y, f"Forma de pagamento: {forma_pagamento}")
    c.drawRightString(195 * mm, y, "PRAZO PARA INSTALAÇÃO A COMBINAR")

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.read()


def gerar_pdf_montador(nome_cliente, data_orcamento, itens, total_geral, logo_base64=""):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    largura, altura = A4

    logo_img = None
    if logo_base64:
        try:
            from reportlab.lib.utils import ImageReader
            img_data = base64.b64decode(logo_base64)
            logo_img = ImageReader(io.BytesIO(img_data))
        except Exception:
            logo_img = None

    def cabecalho():
        y = altura - 15 * mm
        if logo_img:
            try:
                c.drawImage(logo_img, 15 * mm, y - 18 * mm,
                            width=40 * mm, height=18 * mm,
                            preserveAspectRatio=True, mask="auto")
                y -= 22 * mm
            except Exception:
                pass
        c.setFont("Helvetica-Bold", 11)
        c.drawString(15 * mm, y, "MARMORARIA EBENEZER MARMORES E GRANITOS")
        y -= 5 * mm
        c.setFont("Helvetica", 9)
        c.drawString(15 * mm, y, "RUA SAFIRA, 842 - INDAIATUBA/SP")
        y -= 4 * mm
        c.drawString(15 * mm, y, "Telefone: (19) 99514-0294 / (19) 99118-6672")
        y -= 9 * mm
        c.setFont("Helvetica-Bold", 9)
        c.drawString(15 * mm, y, f"CLIENTE: {nome_cliente}")
        c.drawString(120 * mm, y, f"DATA: {data_orcamento}")
        y -= 10 * mm
        return y

    y = cabecalho()
    c.setFont("Helvetica-Bold", 12)
    c.rect(15 * mm, y - 8 * mm, (largura - 30 * mm), 8 * mm, stroke=1, fill=0)
    c.drawCentredString(largura / 2, y - 6.5 * mm, "SERVIÇO DE MONTADOR TERCEIRIZADO")
    y -= 14 * mm

    c.setFont("Helvetica-Bold", 9)
    c.drawString(15 * mm, y, "DESCRIÇÃO")
    c.drawString(90 * mm, y, "ML")
    c.drawString(110 * mm, y, "VALOR/ML (R$)")
    c.drawString(145 * mm, y, "VALOR FIXO (R$)")
    c.drawRightString(195 * mm, y, "TOTAL (R$)")
    y -= 6 * mm

    c.setFont("Helvetica", 8)
    for item in itens:
        if y < 40 * mm:
            c.showPage()
            y = cabecalho()
        c.drawString(15 * mm, y, item.get("descricao", ""))
        c.drawString(90 * mm, y, fmt_pdf(item.get("ml", 0)))
        c.drawString(110 * mm, y, format_brl_pdf(item.get("valor_ml", 0)))
        c.drawString(145 * mm, y, format_brl_pdf(item.get("valor_fixo", 0)))
        c.drawRightString(195 * mm, y, format_brl_pdf(item.get("total", 0)))
        y -= 5 * mm

    y -= 10 * mm
    c.setStrokeColor(colors.black)
    c.setLineWidth(1)
    c.line(135 * mm, y + 6 * mm, 195 * mm, y + 6 * mm)
    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(195 * mm, y, f"TOTAL: R$ {format_brl_pdf(total_geral)}")

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.read()
