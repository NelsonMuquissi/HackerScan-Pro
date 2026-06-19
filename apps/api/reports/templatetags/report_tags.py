from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter(name='markdown')
def markdown_filter(text):
    """
    Renders markdown text to HTML.
    """
    if not text:
        return ""
    
    try:
        import markdown as md
    except ImportError:
        return text # Fallback to plain text if markdown is missing
    
    # Configure markdown with common extensions
    html = md.markdown(text, extensions=[
        'fenced_code',
        'tables',
        'nl2br',
        'toc'
    ])
    return mark_safe(html)
