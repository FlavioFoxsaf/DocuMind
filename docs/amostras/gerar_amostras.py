"""Gera os PDFs de demonstração do DocuMind.

Todo o conteúdo é fictício e escrito para este projeto, portanto pode ser
usado livremente no vídeo e nos testes. Cada página traz fatos fáceis de
conferir; o gabarito com a página de cada fato está em FATOS.md.

Uso (a partir da pasta DocuMind):
    .venv\\Scripts\\python docs\\amostras\\gerar_amostras.py
"""

from datetime import datetime, timezone
from pathlib import Path

from fpdf import FPDF

PASTA = Path(__file__).resolve().parent

REGULAMENTO = [
    (
        "Regulamento Interno do Condomínio Residencial Jardim das Palmeiras",
        [
            "Documento fictício criado para demonstração do DocuMind.",
            "Capítulo I - Disposições gerais",
            "Art. 1º O Condomínio Residencial Jardim das Palmeiras é formado por "
            "48 unidades residenciais distribuídas em 3 blocos, identificados "
            "como Bloco A, Bloco B e Bloco C, com 16 apartamentos em cada bloco.",
            "Art. 2º A administração do condomínio cabe à síndica eleita em "
            "assembleia, com mandato de 2 anos, permitida uma reeleição. A "
            "síndica atual é Marta Figueiredo.",
            "Art. 3º Este regulamento vale para moradores, visitantes, "
            "prestadores de serviço e funcionários.",
        ],
    ),
    (
        "Capítulo II - Horários de silêncio e obras",
        [
            "Art. 4º O horário de silêncio vai das 22h às 7h de domingo a "
            "quinta-feira. Nas noites de sexta-feira e sábado, o silêncio vai "
            "das 23h às 8h.",
            "Art. 5º Obras e reformas com ruído são permitidas de segunda a "
            "sexta-feira, das 8h às 17h, e aos sábados, das 9h às 13h. Obras "
            "com ruído são proibidas aos domingos e feriados.",
            "Art. 6º Toda obra deve ser comunicada à administração com pelo "
            "menos 5 dias úteis de antecedência, acompanhada do nome do "
            "responsável técnico.",
        ],
    ),
    (
        "Capítulo III - Áreas comuns",
        [
            "Art. 7º A piscina funciona de terça-feira a domingo, das 8h às "
            "21h. Às segundas-feiras a piscina permanece fechada para limpeza.",
            "Art. 8º Crianças menores de 12 anos só podem usar a piscina "
            "acompanhadas de um adulto responsável.",
            "Art. 9º O salão de festas deve ser reservado com no mínimo 15 dias "
            "de antecedência. A taxa de reserva é de R$ 150,00, a capacidade "
            "máxima é de 60 pessoas e os eventos devem terminar até 1h da manhã. "
            "Os eventos no salão de festas são uma exceção ao horário de "
            "silêncio do Art. 4º, desde que o som seja mantido em volume baixo "
            "a partir das 22h.",
            "Art. 10. A churrasqueira deve ser reservada com no mínimo 7 dias "
            "de antecedência. A taxa de reserva é de R$ 80,00, a capacidade "
            "máxima é de 20 pessoas e o uso deve terminar até as 22h.",
            "Art. 11. A quadra poliesportiva funciona todos os dias, das 8h às "
            "22h. Cada unidade pode reservar a quadra por no máximo 1 hora por "
            "dia.",
            "Art. 12. A academia funciona todos os dias, das 6h às 22h.",
            "Art. 13. A brinquedoteca atende crianças de até 10 anos, das 8h às "
            "20h, sempre com um adulto responsável presente.",
            "Art. 14. O salão de festas e a churrasqueira devem ser devolvidos "
            "limpos. Se a limpeza for feita pelo condomínio, será cobrada da "
            "unidade uma taxa de limpeza de R$ 90,00. Danos às áreas comuns "
            "serão cobrados da unidade responsável pelo valor do conserto.",
        ],
    ),
    (
        "Capítulo IV - Garagem e animais de estimação",
        [
            "Art. 15. Cada unidade tem direito a 1 vaga de garagem, sendo "
            "proibido alugar a vaga para pessoas que não moram no condomínio.",
            "Art. 16. Veículos de visitantes podem permanecer na área de carga "
            "e descarga por no máximo 30 minutos.",
            "Art. 17. Animais de estimação devem circular nas áreas comuns "
            "com coleira e usar exclusivamente o elevador de serviço. É "
            "proibida a permanência de animais na piscina e na academia.",
        ],
    ),
    (
        "Capítulo V - Mudanças e coleta de lixo",
        [
            "Art. 18. Mudanças são permitidas de segunda-feira a sábado, das "
            "8h às 18h, com aviso à portaria com 48 horas de antecedência.",
            "Art. 19. O condomínio adota coleta seletiva. O lixo orgânico deve "
            "ser levado ao depósito do térreo até as 20h. Materiais recicláveis "
            "devem ser separados em papel, plástico, metal e vidro.",
        ],
    ),
    (
        "Capítulo VI - Penalidades",
        [
            "Art. 20. A primeira infração a este regulamento gera advertência "
            "por escrito.",
            "Art. 21. Na reincidência, será aplicada multa equivalente a 1 "
            "(uma) taxa condominial mensal vigente. Uma nova reincidência no "
            "período de 12 meses gera multa equivalente a 2 taxas condominiais.",
            "Art. 22. Danos intencionais às áreas comuns geram, além da "
            "cobrança do conserto, multa equivalente a 3 taxas condominiais, "
            "sem necessidade de advertência prévia.",
            "Art. 23. O pagamento da taxa condominial após o vencimento, no dia "
            "10 de cada mês, gera multa de 2% sobre o valor devido e juros de 1% "
            "ao mês. Essa multa por atraso não depende de advertência.",
            "Art. 24. As notificações de advertência e multa são entregues por "
            "escrito na portaria ou enviadas ao e-mail cadastrado da unidade.",
            "Art. 25. O condômino multado pode recorrer à assembleia no prazo "
            "de 15 dias contados do recebimento da notificação.",
            "Art. 26. Os valores arrecadados com multas são destinados ao fundo "
            "de reserva do condomínio.",
        ],
    ),
]

ATA = [
    (
        "Ata da Assembleia Geral Ordinária de 2026",
        [
            "Documento fictício criado para demonstração do DocuMind.",
            "Condomínio Residencial Jardim das Palmeiras. Data: 14 de março de "
            "2026, às 19h30, no salão de festas.",
            "Presença: 31 das 48 unidades, atingindo o quórum necessário.",
            "Item 1 - Taxa condominial. Aprovado o reajuste da taxa condominial "
            "mensal de R$ 620,00 para R$ 680,00, com vigência a partir de maio "
            "de 2026.",
            "Item 2 - Prestação de contas. Aprovadas por unanimidade as contas "
            "do exercício de 2025.",
        ],
    ),
    (
        "Ata da Assembleia Geral Ordinária de 2026 (continuação)",
        [
            "Item 3 - Reforma da piscina. Aprovado o orçamento de R$ 42.000,00 "
            "para a reforma da piscina, pago em 6 parcelas mensais. A piscina "
            "ficará fechada de 1º a 30 de junho de 2026 para a reforma.",
            "Item 4 - Conselho fiscal. Eleitos para o conselho fiscal os "
            "moradores Paulo Andrade (Bloco A), Renata Lima (Bloco B) e "
            "Jorge Tavares (Bloco C).",
            "Nada mais havendo a tratar, a síndica Marta Figueiredo encerrou a "
            "assembleia às 21h10.",
        ],
    ),
]


COM_PAGINA_EM_BRANCO = [
    (
        "Aviso da administração",
        [
            "Documento fictício criado para demonstração do DocuMind.",
            "A manutenção dos elevadores do Bloco B será feita no dia 20 de "
            "outubro de 2026, das 9h às 15h.",
        ],
    ),
    None,  # página intencionalmente em branco
    (
        "Aviso da administração (continuação)",
        [
            "Durante a manutenção, os moradores do Bloco B devem usar as "
            "escadas ou o elevador do Bloco A pela passagem do térreo.",
        ],
    ),
]

# Data fixa para que PDFs regerados sejam idênticos byte a byte.
DATA_CRIACAO = datetime(2026, 9, 27, tzinfo=timezone.utc)


def novo_pdf() -> FPDF:
    pdf = FPDF(format="A4")
    pdf.set_creation_date(DATA_CRIACAO)
    return pdf


def gerar_pdf_textual(paginas, destino: Path) -> None:
    pdf = novo_pdf()
    pdf.set_margins(20, 20, 20)
    pdf.set_auto_page_break(auto=False)
    for pagina in paginas:
        pdf.add_page()
        if pagina is None:
            continue
        titulo, paragrafos = pagina
        pdf.set_font("Helvetica", "B", 14)
        pdf.multi_cell(0, 8, titulo)
        pdf.ln(4)
        pdf.set_font("Helvetica", size=11)
        for paragrafo in paragrafos:
            pdf.multi_cell(0, 6, paragrafo)
            pdf.ln(3)
    pdf.output(str(destino))


def gerar_pdf_sem_texto(destino: Path) -> None:
    """Simula um PDF digitalizado: só desenhos, sem camada de texto."""
    pdf = novo_pdf()
    pdf.add_page()
    pdf.set_fill_color(200, 200, 200)
    for linha in range(12):
        pdf.rect(20, 30 + linha * 12, 170 - (linha % 3) * 25, 6, style="F")
    pdf.output(str(destino))


def main() -> None:
    gerar_pdf_textual(REGULAMENTO, PASTA / "regulamento_condominio.pdf")
    gerar_pdf_textual(ATA, PASTA / "ata_assembleia_2026.pdf")
    gerar_pdf_textual(COM_PAGINA_EM_BRANCO, PASTA / "aviso_com_pagina_em_branco.pdf")
    gerar_pdf_sem_texto(PASTA / "digitalizado_sem_texto.pdf")
    print(f"PDFs gerados em {PASTA}")


if __name__ == "__main__":
    main()
