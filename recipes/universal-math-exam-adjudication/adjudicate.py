import base64
import random
import re
from io import BytesIO
from pathlib import Path
from typing import Optional

import matplotlib
import matplotlib.pyplot as plt
from jinja2 import DebugUndefined, Template
from matplotlib import rcParams
from prodigy import set_hashes
from prodigy.components.loaders import JSONL
from prodigy.core import Arg, recipe

# Configure matplotlib for LaTeX rendering
matplotlib.use('Agg')  # Use non-interactive backend
rcParams['text.usetex'] = False
rcParams['text.latex.preamble'] = r'\usepackage{amsmath,amssymb,amsfonts}'
rcParams['mathtext.fontset'] = 'cm'  # Computer Modern font (TeX-like)


def latex_to_svg_base64(latex_str):
    """
    Convert a LaTeX string to an SVG and return as base64-encoded
    string using matplotlib.

    Args:
        latex_str: The LaTeX string to render
        is_variable: Whether this is a single variable (for better inline alignment)

    Returns:
        Base64 encoded SVG image
    """
    try:
        fig = plt.figure(figsize=(0.1, 0.3), dpi=100, frameon=False)
        fontsize = 14

        # Eliminate all margins
        plt.subplots_adjust(0, 0, 1, 1)
        ax = fig.add_subplot(111)
        ax.axis('off')

        # For equations, ensure proper math formatting
        ax.text(0.5, 0.5, f"${latex_str}$",
                size=fontsize,
                ha='center', va='center',
                transform=ax.transAxes)

        # Tightest possible bbox with minimal padding
        buffer = BytesIO()
        plt.savefig(buffer, format='svg', bbox_inches='tight',
                    pad_inches=0.01, transparent=True)
        plt.close(fig)

        # Convert to base64
        buffer.seek(0)
        svg_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        return f'data:image/svg+xml;base64,{svg_base64}'
    except Exception as e:
        print(f"Error rendering LaTeX: {latex_str} - {str(e)}")
        return None


def process_latex(text):
    """
    Find LaTeX expressions in text and replace with SVG images.
    Uses specialized handling for inline variables vs. equations.
    Supports both types of syntax for inline equations.
    """
    # First, temporarily replace escaped dollar signs \$ and
    # escaped parentheses \( \) so they don't match our patterns
    text = re.sub(r'(\\\$)', r'ESCAPED_DOLLAR_PLACEHOLDER', text)

    # Replace "\le" and "\ge" with their LaTeX equivalents
    text = text.replace(r'\le', r'\leq')
    text = text.replace(r'\ge', r'\geq')

    # Pattern for inline LaTeX equations with dollar signs: $...$
    # (but not single variables or currency)
    inline_dollar_pattern = r'\$([^\$]+?)\$'

    # Pattern for inline LaTeX equations with parentheses: \(...\)
    inline_paren_pattern = r'\\\((.+?)\\\)'

    # Process inline LaTeX equations with dollar signs
    def replace_inline_latex(match):
        latex = match.group(1)
        svg_base64 = latex_to_svg_base64(latex)
        if svg_base64:
            return f'<img class="latex-inline" src="{svg_base64}" alt="{latex}" />'
        return match.group(0)

    # Apply replacements
    text = re.sub(inline_dollar_pattern, replace_inline_latex, text)
    text = re.sub(inline_paren_pattern, replace_inline_latex, text)

    # Fix whitespace
    text = text.replace(r'\n', '<br>')

    # Restore escaped characters
    text = text.replace('ESCAPED_DOLLAR_PLACEHOLDER', '$')

    return text


def render_items(d):
    keys = ["question", "choice_A", "choice_B", "choice_C", "choice_D"]
    modified = []  # List of items that differ between versions
    orig = {}
    revised = {}
    for key in keys:
        orig[f"display_{key}"] = process_latex(d[f"{key}_orig"])
        revised[f"display_{key}"] = process_latex(d[key])
        if d[f"{key}_orig"] != d[key]:
            modified.append(key)

    orig["modified"] = modified
    revised["modified"] = modified

    orig["correct_answer"] = d["correct_answer"]
    revised["correct_answer"] = d["correct_answer"]

    return orig, revised


@recipe(
    "adjudicate",
    dataset=Arg(help="Dataset to save answers to"),
    inputs_path=Arg(help="Path to jsonl inputs"),
    display_template_path=Arg(
        "--display-template", "-dp", help="Template for summarizing the arguments"
    )
)
def select_suggest(
    dataset,
    inputs_path: Path,
    display_template_path: Optional[Path] = None
):

    with display_template_path.open("r", encoding="utf8") as file_:
        mcq_display = Template(file_.read(), undefined=DebugUndefined)

    info_template = Template("""
<div class="header-info">
    <div class="task-domain-container">
        <div class="domain-info">
            <span class="label">Domain:</span>
            <span class="domain-text">{{ domain }}</span>
        </div>
        <div class="label-info">
            <span class="label">Label:</span>
            <span class="label-text">{{ label }}</span>
        </div>
        <div class="task-info">
            <span class="label">Task:</span>
            <span class="task-text">{{ task }}</span>
        </div>
    </div>
    <div class="id-container">
        <span class="id-text">ID: {{ idx }}</span>
    </div>
</div>""")

    def get_stream():
        for item in JSONL(inputs_path):
            item["html"] = info_template.render(**item)

            orig, revised = render_items(item)

            options = [
                {"id": "orig", "html": mcq_display.render(**orig)},
                {"id": "revised", "html": mcq_display.render(**revised)},
            ]
            random.shuffle(options)
            item["options"] = options
            yield item

    # We can use the blocks to override certain config and content, and set
    # "text": None for the choice interface so it doesn't also render the text
    blocks = [
        {"view_id": "choice", "text": None, "label": None},
        {"view_id": "text_input", "field_rows": 3, "field_label": "Notes:"},
    ]

    stream = get_stream()
    stream = (set_hashes(eg) for eg in stream)
    return {
        "dataset": dataset,
        "view_id": "blocks",
        "stream": stream,
        "config": {
            "blocks": blocks,
        },
    }
