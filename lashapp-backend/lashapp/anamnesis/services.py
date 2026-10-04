import logging
import io
from pathlib import Path

from django.core.files.base import ContentFile
from django.template.loader import render_to_string

from anamnesis.models import Anamnesis

logger = logging.getLogger(__name__)


def generate_anamnesis_pdf(anamnesis):
    from weasyprint import HTML

    questions = [
        ("Já fez extensão de cílios antes? Se sim, teve alguma reação?", "had_previous_extension"),
        ("Possui alguma alergia conhecida (esmaltes, cosméticos, cianoacrilato, etc)?", "has_allergies"),
        ("Usa lentes de contato? (Necessário remover durante o procedimento)", "uses_contact_lenses"),
        ("Possui algum problema ocular? (Blefarite, glaucoma, olho seco, conjuntivite recente)", "has_eye_problems"),
        ("Fez cirurgia ocular recente ou procedimento estético na região (Ex: PMU, Botox)?", "recent_eye_procedure"),
        ("Tem problemas de tireoide, alopecia ou está passando por alterações hormonais?", "thyroid_alopecia_hormonal"),
        ("Está gestante, lactante ou em tratamento médico/oncológico?", "pregnant_or_treatment"),
        ("Tem mania de puxar ou esfregar os cílios? Costuma dormir de bruços?", "pulls_lashes_or_sleeps_prone"),
    ]
    context_questions = [
        {"text": text, "answer": getattr(anamnesis, field), "notes": getattr(anamnesis, f"{field}_notes")}
        for text, field in questions
    ]
    signature_uri = Path(anamnesis.signature.path).resolve().as_uri()
    html = render_to_string(
        "anamnesis/anamnesis_pdf.html",
        {"anamnesis": anamnesis, "questions": context_questions, "signature_uri": signature_uri},
    )
    pdf_bytes = HTML(string=html, base_url=str(Path(__file__).resolve().parent)).write_pdf()
    filename = f"anamnesis-{anamnesis.pk}.pdf"
    anamnesis.pdf.save(filename, ContentFile(pdf_bytes), save=False)
    Anamnesis.objects.filter(pk=anamnesis.pk).update(pdf=anamnesis.pdf.name)
    anamnesis.refresh_from_db(fields=["pdf"])


def generate_anamnesis_pdf_safely(anamnesis):
    try:
        generate_anamnesis_pdf(anamnesis)
    except Exception:
        logger.exception("Não foi possível gerar o PDF da ficha %s", anamnesis.pk)
        generate_anamnesis_pdf_fallback(anamnesis)


def generate_anamnesis_pdf_fallback(anamnesis):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    document = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    left = 42
    y = height - 48

    def line(text, size=10, bold=False):
        nonlocal y
        if y < 48:
            document.showPage()
            y = height - 48
        document.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        document.drawString(left, y, str(text)[:115])
        y -= size + 5

    def section(title):
        nonlocal y
        y -= 8
        line(title, 13, True)

    line("FICHA DE ANAMNESE", 18, True)
    line("EXTENSÃO DE CÍLIOS & DESIGN DO OLHAR", 11)
    section("1. DADOS PESSOAIS")
    for label, value in (
        ("Nome completo", anamnesis.full_name),
        ("Data de nascimento", anamnesis.birth_date),
        ("WhatsApp", anamnesis.whatsapp or "Não informado"),
        ("Instagram", anamnesis.instagram or "Não informado"),
        ("Profissão", anamnesis.profession or "Não informado"),
        ("Como nos conheceu", anamnesis.how_met or "Não informado"),
    ):
        line(f"{label}: {value}")

    section("2. QUESTIONÁRIO DE SAÚDE & HISTÓRICO OCULAR")
    questions = [
        ("Já fez extensão de cílios antes? Se sim, teve alguma reação?", "had_previous_extension"),
        ("Possui alguma alergia conhecida (esmaltes, cosméticos, cianoacrilato, etc)?", "has_allergies"),
        ("Usa lentes de contato? (Necessário remover durante o procedimento)", "uses_contact_lenses"),
        ("Possui algum problema ocular? (Blefarite, glaucoma, olho seco, conjuntivite recente)", "has_eye_problems"),
        ("Fez cirurgia ocular recente ou procedimento estético na região (Ex: PMU, Botox)?", "recent_eye_procedure"),
        ("Tem problemas de tireoide, alopecia ou está passando por alterações hormonais?", "thyroid_alopecia_hormonal"),
        ("Está gestante, lactante ou em tratamento médico/oncológico?", "pregnant_or_treatment"),
        ("Tem mania de puxar ou esfregar os cílios? Costuma dormir de bruços?", "pulls_lashes_or_sleeps_prone"),
    ]
    for index, (question, field) in enumerate(questions, 1):
        line(f"{index}. {question}", 9, True)
        line(f"Resposta: {'Sim' if getattr(anamnesis, field) else 'Não'}")
        line(f"Observações: {getattr(anamnesis, f'{field}_notes') or 'Nenhuma'}")

    section("3. TERMO DE RESPONSABILIDADE E CONSENTIMENTO")
    term = ("Estou ciente de que o procedimento de extensão de cílios requer cuidados específicos após a aplicação "
            "(não molhar nas primeiras horas, não usar rímel à prova d'água, não esfregar os olhos e pentear diariamente). "
            "Declaro que todas as informações prestadas acima são verdadeiras e omitir qualquer dado é de minha total responsabilidade. "
            "Autorizo a realização do procedimento, bem como o registro fotográfico dos meus olhos para acompanhamento técnico e divulgação profissional.")
    for start in range(0, len(term), 105):
        line(term[start:start + 105], 9)
    line(f"Data: {anamnesis.signed_date}")
    if anamnesis.signature and anamnesis.signature.storage.exists(anamnesis.signature.name):
        document.drawImage(ImageReader(anamnesis.signature.path), left, max(y - 70, 48), width=180, height=60, preserveAspectRatio=True, mask='auto')
        y -= 78
    line("Assinatura da Cliente", 9)
    document.save()
    buffer.seek(0)
    anamnesis.pdf.save(f"anamnesis-{anamnesis.pk}.pdf", ContentFile(buffer.read()), save=False)
    Anamnesis.objects.filter(pk=anamnesis.pk).update(pdf=anamnesis.pdf.name)
    anamnesis.refresh_from_db(fields=["pdf"])