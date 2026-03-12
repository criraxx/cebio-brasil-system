"""
CEBIO Brasil - Geração de Relatórios PDF
Gera relatórios PDF de projetos com histórico completo.
"""
from io import BytesIO
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT


def generate_project_pdf(project, versions=None, comments=None):
    """
    Gera PDF de um projeto com todas as informações.
    
    Args:
        project: Objeto Project do SQLAlchemy
        versions: Lista de ProjectVersion (opcional)
        comments: Lista de ProjectComment (opcional)
    
    Returns:
        BytesIO: Buffer com o PDF gerado
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
    
    # Estilos
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1b7a3a'),
        spaceAfter=12,
        alignment=TA_CENTER
    )
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#1b7a3a'),
        spaceAfter=8,
        spaceBefore=12
    )
    normal_style = styles['Normal']
    
    # Elementos do documento
    elements = []
    
    # Título
    elements.append(Paragraph("CEBIO Brasil - Relatório de Projeto", title_style))
    elements.append(Spacer(1, 0.5*cm))
    
    # Informações básicas
    elements.append(Paragraph("Informações do Projeto", heading_style))
    
    info_data = [
        ['Título:', project.title or '—'],
        ['Categoria:', project.category or '—'],
        ['Nível Acadêmico:', project.academic_level or '—'],
        ['Status:', _format_status(project.status)],
        ['Responsável:', project.owner.name if project.owner else '—'],
        ['Data de Criação:', _format_date(project.created_at)],
        ['Última Atualização:', _format_date(project.updated_at)],
    ]
    
    if project.start_date:
        info_data.append(['Data de Início:', _format_date(project.start_date)])
    if project.end_date:
        info_data.append(['Data de Término:', _format_date(project.end_date)])
    if project.submitted_at:
        info_data.append(['Data de Submissão:', _format_date(project.submitted_at)])
    
    info_table = Table(info_data, colWidths=[5*cm, 12*cm])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 0.5*cm))
    
    # Resumo
    if project.summary:
        elements.append(Paragraph("Resumo", heading_style))
        elements.append(Paragraph(project.summary, normal_style))
        elements.append(Spacer(1, 0.5*cm))
    
    # Público-alvo
    if project.target_audience:
        elements.append(Paragraph("Público-Alvo", heading_style))
        elements.append(Paragraph(project.target_audience, normal_style))
        elements.append(Spacer(1, 0.5*cm))
    
    # Autores
    if project.authors and len(project.authors) > 0:
        elements.append(Paragraph("Autores", heading_style))
        authors_data = [['Nome', 'Instituição', 'Nível', 'Papel']]
        for author in project.authors:
            authors_data.append([
                author.name or '—',
                author.institution or '—',
                author.academic_level or '—',
                author.role or '—'
            ])
        
        authors_table = Table(authors_data, colWidths=[5*cm, 5*cm, 3*cm, 4*cm])
        authors_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1b7a3a')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(authors_table)
        elements.append(Spacer(1, 0.5*cm))
    
    # Histórico de versões
    if versions and len(versions) > 0:
        elements.append(Paragraph("Histórico de Versões", heading_style))
        versions_data = [['Versão', 'Tipo', 'Descrição', 'Autor', 'Data']]
        for v in versions[:10]:  # Limitar a 10 versões mais recentes
            versions_data.append([
                f"#{v.version_number}",
                _format_change_type(v.change_type),
                (v.description or '—')[:50] + ('...' if len(v.description or '') > 50 else ''),
                v.author.name if v.author else '—',
                _format_date(v.created_at)
            ])
        
        versions_table = Table(versions_data, colWidths=[1.5*cm, 2.5*cm, 7*cm, 3*cm, 3*cm])
        versions_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1b7a3a')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(versions_table)
        elements.append(Spacer(1, 0.5*cm))
    
    # Comentários de revisão
    if comments and len(comments) > 0:
        elements.append(Paragraph("Comentários de Revisão", heading_style))
        for comment in comments[:5]:  # Limitar a 5 comentários mais recentes
            comment_text = f"<b>{comment.author.name if comment.author else 'Desconhecido'}</b> "
            comment_text += f"({_format_date(comment.created_at)}): "
            comment_text += comment.content or '—'
            elements.append(Paragraph(comment_text, normal_style))
            elements.append(Spacer(1, 0.2*cm))
    
    # Rodapé
    elements.append(Spacer(1, 1*cm))
    footer_text = f"Relatório gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M')}"
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey,
        alignment=TA_CENTER
    )
    elements.append(Paragraph(footer_text, footer_style))
    
    # Gerar PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer


def _format_date(dt):
    """Formata data para exibição no PDF."""
    if not dt:
        return '—'
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        except:
            return dt
    return dt.strftime('%d/%m/%Y %H:%M')


def _format_status(status):
    """Formata status para exibição no PDF."""
    status_map = {
        'rascunho': 'Rascunho',
        'pendente': 'Pendente',
        'em_submissao': 'Em Submissão',
        'em_revisao': 'Em Revisão',
        'aprovado': 'Aprovado',
        'rejeitado': 'Rejeitado'
    }
    return status_map.get(status, status or '—')


def _format_change_type(change_type):
    """Formata tipo de mudança para exibição no PDF."""
    type_map = {
        'criacao': 'Criação',
        'conteudo': 'Conteúdo',
        'status': 'Status',
        'arquivos': 'Arquivos',
        'backup': 'Backup',
        'restauracao': 'Restauração'
    }
    return type_map.get(change_type, change_type or '—')
