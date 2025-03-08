import base64
import random
import re
from io import BytesIO
from pathlib import Path

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
    ab = ["a", "b"]
    random.shuffle(ab)

    for key in keys:
        d[f"{ab[0]}_{key}"] = process_latex(d[f"{key}_orig"])
        d[f"{ab[1]}_{key}"] = process_latex(d[key])
        if d[f"{key}_orig"] != d[key]:
            modified.append(key)

    d["modified"] = modified

    return d


@recipe(
    "adjudicate",
    dataset=Arg(help="Dataset to save answers to"),
    inputs_path=Arg(help="Path to jsonl inputs"),
)
def adjudicate(
    dataset,
    inputs_path: Path,
):
    mcq_template_path = Path(__file__).parent / "mcq.jinja2"
    with mcq_template_path.open("r", encoding="utf8") as file_:
        mcq_template = Template(file_.read(), undefined=DebugUndefined)

    def get_stream():
        for item in JSONL(inputs_path):
            item = render_items(item)
            item["html"] = mcq_template.render(**item)

            yield item

    blocks = [
        {"view_id": "html"},
        {
            "view_id": "text_input",
            "field_id": "question",
            "field_rows": 6,
            "field_label": "Question Stem:",
        },
        {
            "view_id": "text_input",
            "field_id": "choice_A",
            "field_rows": 2,
            "field_label": "Option A:",
        },
        {
            "view_id": "text_input",
            "field_id": "choice_B",
            "field_rows": 2,
            "field_label": "Option B:",
        },
        {
            "view_id": "text_input",
            "field_id": "choice_C",
            "field_rows": 2,
            "field_label": "Option C:",
        },
        {
            "view_id": "text_input",
            "field_id": "choice_D",
            "field_rows": 2,
            "field_label": "Option D:",
        },
    ]

    stream = get_stream()
    stream = [set_hashes(eg, input_keys=["idx"]) for eg in stream]

    print("Length of stream: ", len(stream))
    print(
        "Unique input hashes in stream: ",
        len(set([eg["_input_hash"] for eg in stream]))
    )

    return {
        "dataset": dataset,
        "view_id": "blocks",
        "stream": stream,
        "config": {
            "blocks": blocks,
        },
    }
