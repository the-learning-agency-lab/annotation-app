import base64

# Import sympy for LaTeX rendering
import re
from io import BytesIO
from pathlib import Path
from typing import Optional

# Import matplotlib for LaTeX rendering
import matplotlib
import matplotlib.pyplot as plt
from matplotlib import rcParams

# Convert inline LaTeX to SVG
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
    Convert a LaTeX string to an SVG and return as base64-encoded string using matplotlib.

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


def process_latex_in_text(text):
    """
    Find LaTeX expressions in text and replace with SVG images.
    Uses specialized handling for inline variables vs. equations.
    Supports both types of syntax for inline equations.
    """
    # First, temporarily replace escaped dollar signs \$ and escaped parentheses \( \) so they don't match our patterns
    text = re.sub(r'(\\\$)', r'ESCAPED_DOLLAR_PLACEHOLDER', text)
    text = re.sub(r'\\\(', r'ESCAPED_PAREN_PLACEHOLDER_1', text)
    text = re.sub(r'\\\)', r'ESCAPED_PAREN_PLACEHOLDER_2', text)

    # Pattern for inline LaTeX equations with dollar signs: $...$ (but not single variables or currency)
    inline_dollar_pattern = r'\$([^\$]+?)\$'

    # Pattern for inline LaTeX equations with parentheses: \(...\)
    inline_paren_pattern = r'\\\((.+?)\\\)'

    # Process inline LaTeX equations with dollar signs
    def replace_inline_dollar_latex(match):
        latex = match.group(1)
        svg_base64 = latex_to_svg_base64(latex)
        if svg_base64:
            return f'<img class="latex-inline" src="{svg_base64}" alt="{latex}" />'
        return match.group(0)

    # Process inline LaTeX equations with parentheses
    def replace_inline_paren_latex(match):
        latex = match.group(2)
        svg_base64 = latex_to_svg_base64(latex)
        if svg_base64:
            return f'<img class="latex-inline" src="{svg_base64}" alt="{latex}" />'
        return match.group(0)

    # Apply replacements
    text = re.sub(inline_dollar_pattern, replace_inline_dollar_latex, text)
    text = re.sub(inline_paren_pattern, replace_inline_paren_latex, text)

    # Restore escaped characters
    text = text.replace('ESCAPED_DOLLAR_PLACEHOLDER', '$')
    text = text.replace('ESCAPED_PAREN_PLACEHOLDER_1', '(')
    text = text.replace('ESCAPED_PAREN_PLACEHOLDER_2', ')')

    return text


@recipe(
    "select-suggest",
    dataset=Arg(help="Dataset to save answers to"),
    inputs_path=Arg(help="Path to jsonl inputs"),
    display_template_path=Arg(
        "--display-template", "-dp", help="Template for summarizing the arguments"
    ),
    resume=Arg(
        "--resume", "-r", help="Resume from the dataset, replaying the matches in them"
    ),
    nometa=Arg(
        "--no-meta",
        "-nm",
        help="Don't display the meta information at the bottom of the card",
    ),
)
def cat_facts_ner(
    dataset,
    inputs_path: Path,
    display_template_path: Optional[Path] = None,
    resume: bool = False,
    nometa: bool = False,
):
    options = [
        {"id": 3, "text": "😺 Fully correct"},
        {"id": 2, "text": "😼 Partially correct"},
        {"id": 1, "text": "😾 Wrong"},
        {"id": 0, "text": "🙀 Don't know"},
    ]

    def get_stream():
        for item in JSONL(inputs_path):
            question = process_latex_in_text(item["question"])

            yield {"html": question, "options": options}

    # We can use the blocks to override certain config and content, and set
    # "text": None for the choice interface so it doesn't also render the text
    blocks = [
        {"view_id": "choice"},
        {
            "view_id": "text_input",
            "field_rows": 3,
            "field_label": "Explain your decision",
        },
    ]

    stream = get_stream()
    stream = (set_hashes(eg) for eg in stream)
    return {
        "dataset": dataset,  # the dataset to save annotations to
        "view_id": "blocks",  # set the view_id to "blocks"
        "stream": stream,  # the stream of incoming examples
        "config": {
            "blocks": blocks,  # add the blocks to the config
        },
    }
