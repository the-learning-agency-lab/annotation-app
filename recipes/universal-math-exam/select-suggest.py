import base64
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


def process_latex_in_text(text):
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


# Custom HTML template for the reset button
reset_button_html = """
<div style="display: flex; justify-content: space-between; align-items: center; margin-top: 0px;">
    <h2 style="margin: 0; font-weight: 600;">Revisions</h2>
    <button
        id="reset-revision-button"
        style="
            line-height: 1;
        "
        onclick="resetRevision()"
    >
        Reset Revisions
    </button>
</div>
"""


@recipe(
    "select-suggest",
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
        display = Template(file_.read(), undefined=DebugUndefined)

    def get_stream():
        for item in JSONL(inputs_path):
            # Store the original revision text to allow resetting
            item["question_orig"] = item["question"]
            item["choice_A_orig"] = item["choice_A"]
            item["choice_B_orig"] = item["choice_B"]
            item["choice_C_orig"] = item["choice_C"]
            item["choice_D_orig"] = item["choice_D"]

            item["display_question"] = process_latex_in_text(item["question"])
            item["display_choice_A"] = process_latex_in_text(item["choice_A"])
            item["display_choice_B"] = process_latex_in_text(item["choice_B"])
            item["display_choice_C"] = process_latex_in_text(item["choice_C"])
            item["display_choice_D"] = process_latex_in_text(item["choice_D"])
            item["html"] = display.render(**item)

            yield item

    # We can use the blocks to override certain config and content, and set
    # "text": None for the choice interface so it doesn't also render the text
    blocks = [
        {"view_id": "html"},
        {
            "view_id": "text_input",
            "field_id": "overall",
            "field_label": "Overall",
            "field_placeholder": "Score from 0 to 3",
            "field_rows": 1,
            "field_suggestions": ["0", "1", "2", "3"],
        },
        {
            "view_id": "text_input",
            "field_id": "topic",
            "field_label": "Topic",
            "field_placeholder": "Score from 0 to 3",
            "field_rows": 1,
            "field_suggestions": ["0", "1", "2", "3"],
        },
        {
            "view_id": "text_input",
            "field_id": "vocabulary",
            "field_label": "Vocabulary",
            "field_placeholder": "Score from 0 to 3",
            "field_rows": 1,
            "field_suggestions": ["0", "1", "2", "3"],
        },
        {
            "view_id": "text_input",
            "field_id": "choices",
            "field_label": "Choices",
            "field_placeholder": "Score from 0 to 3",
            "field_rows": 1,
            "field_suggestions": ["0", "1", "2", "3"],
        },
        {
            "view_id": "html",
            "html_template": reset_button_html,
        },
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

    reset_button_js = (Path(__file__).parent / "reset_button.js").read_text()
    stream = get_stream()
    stream = (set_hashes(eg) for eg in stream)
    return {
        "dataset": dataset,
        "view_id": "blocks",
        "stream": stream,
        "config": {
            "blocks": blocks,
            "javascript": reset_button_js,
        },
    }
