"""process: a closed adapter to the notation engine."""

from draw_schema import validate as validate_contract


def validate(spec):
    return validate_contract(spec, "process")


def render(spec):
    from draw_page import render as render_page

    validate(spec)
    return render_page(spec)


def layout(spec):
    from draw_engine import layout as layout_boxes

    return layout_boxes(spec)


def mermaid(spec):
    from draw_page import mermaid as mermaid_source

    return mermaid_source(spec)
