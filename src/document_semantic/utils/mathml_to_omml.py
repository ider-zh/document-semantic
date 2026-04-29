"""Convert MathML (from latex2mathml) to OMML (Office Math Markup Language).

This module provides a pipeline: LaTeX string → MathML → OMML, enabling
native equation rendering in DOCX files via python-docx.  Word interprets
OMML elements as fully editable math objects — no image placeholders needed.

Key entry points:
- `latex_to_omml(latex_str)` → lxml Element (m:oMath)
- `insert_omml_block(paragraph, latex_str)` → block equation (m:oMathPara)
- `insert_omml_inline(paragraph, latex_str)` → inline equation (m:oMath)
"""

from __future__ import annotations

import logging

from lxml import etree

logger = logging.getLogger(__name__)

# XML namespaces
_MATHML_NS = "http://www.w3.org/1998/Math/MathML"
_OMML_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
_WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

_MATHML_PREFIX = f"{{{_MATHML_NS}}}"
_OMML_PREFIX = f"{{{_OMML_NS}}}"
_WORD_PREFIX = f"{{{_WORD_NS}}}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def latex_to_omml(latex_str: str) -> etree._Element:
    """Convert a LaTeX string to an OMML oMath element.

    Pipeline: LaTeX → latex2mathml → MathML → OMML.
    """
    import latex2mathml.converter

    mathml_str = latex2mathml.converter.convert(latex_str)
    return mathml_to_omml(mathml_str)


def mathml_to_omml(mathml_str: str) -> etree._Element:
    """Convert a MathML string to an OMML oMath element."""
    mathml = etree.fromstring(mathml_str.encode("utf-8"))

    # Unwrap <math> → <mrow> → children
    inner = mathml
    children = list(inner)
    if inner.tag == _MATHML_PREFIX + "math":
        if len(children) == 1 and children[0].tag == _MATHML_PREFIX + "mrow":
            children = list(children[0])
        else:
            children = list(mathml)

    omath = etree.Element(_OMML_PREFIX + "oMath")
    results = [_convert(c) for c in children]
    _absorb_nary_bodies(results)
    _append_children(omath, results)
    return omath


def insert_omml_block(paragraph, latex_str: str) -> None:
    """Insert a block-level OMML equation (m:oMathPara) into a python-docx paragraph.

    The paragraph's existing content is replaced with the equation.
    """
    omath = latex_to_omml(latex_str)
    # Wrap in oMathPara for block display
    omath_para = etree.Element(_OMML_PREFIX + "oMathPara")
    omath_para.append(omath)
    # Append to the paragraph's XML element
    paragraph._element.append(omath_para)


def insert_omml_inline(paragraph, latex_str: str) -> None:
    """Insert an inline OMML equation (m:oMath) into a python-docx paragraph.

    The equation is appended at the end of the paragraph's current content.
    """
    omath = latex_to_omml(latex_str)
    paragraph._element.append(omath)


# ---------------------------------------------------------------------------
# MathML → OMML converter internals
# ---------------------------------------------------------------------------

def _mml_tag(local: str) -> str:
    return _MATHML_PREFIX + local


def _omml_tag(local: str) -> str:
    return _OMML_PREFIX + local


def _convert(elem: etree._Element) -> etree._Element | None:
    """Convert a single MathML element to its OMML equivalent."""
    local = elem.tag.split("}")[1] if "}" in elem.tag else elem.tag

    dispatch = {
        "mrow": _convert_mrow,
        "mi": _convert_mi,
        "mn": _convert_mn,
        "mo": _convert_mo,
        "mtext": _convert_mtext,
        "msub": _convert_msub,
        "msup": _convert_msup,
        "msubsup": _convert_msubsup,
        "mfrac": _convert_mfrac,
        "munderover": lambda e: _convert_nary(e, "subSup"),
        "munder": lambda e: _convert_nary(e, "und"),
        "mover": lambda e: _convert_nary(e, "ovr"),
        "mtable": _convert_mtable,
        "mspace": lambda e: None,
        "math": _convert_math,
    }

    handler = dispatch.get(local)
    if handler:
        return handler(elem)

    # Fallback: extract text content
    text = _extract_text(elem)
    if text:
        return _make_run(text, plain=True)
    return None


def _convert_mrow(elem: etree._Element) -> etree._Element:
    """mrow → expand children into parent context (use CONTAINER marker).

    After a n-ary operator (sum, product, integral), subsequent siblings
    form the body of that operator in OMML.  We absorb them into the
    n-ary's ``m:e`` element so that Word renders the expression correctly.
    """
    container = etree.Element("CONTAINER")
    children = list(elem)
    results = [_convert(c) for c in children]
    _absorb_nary_bodies(results)
    _append_children(container, results)
    return container


def _convert_math(elem: etree._Element) -> etree._Element:
    """Nested <math> → recurse on children with n-ary body absorption."""
    container = etree.Element("CONTAINER")
    children = list(elem)
    results = [_convert(c) for c in children]
    _absorb_nary_bodies(results)
    _append_children(container, results)
    return container


def _convert_mi(elem: etree._Element) -> etree._Element:
    """mi (identifier) → italic run."""
    text = _extract_text(elem)
    return _make_run(text, italic=True)


def _convert_mn(elem: etree._Element) -> etree._Element:
    """mn (number) → plain run."""
    text = _extract_text(elem)
    return _make_run(text, plain=True)


def _convert_mo(elem: etree._Element) -> etree._Element:
    """mo (operator) → plain run."""
    text = _extract_text(elem)
    return _make_run(text, plain=True)


def _convert_mtext(elem: etree._Element) -> etree._Element:
    """mtext → plain run."""
    text = _extract_text(elem)
    return _make_run(text, plain=True)


def _is_nary_char(elem: etree._Element) -> str | None:
    """Check if a MathML element represents a n-ary operator character.

    Returns the operator character string if it is a known n-ary operator,
    or None otherwise. Handles both direct ``mo`` elements and ``mrow``
    wrappers containing a single ``mo``.
    """
    NARY_CHARS = {"∑", "∏", "∫", "∬", "∭", "∮", "∯", "∰", "⊕", "⊗", "⋃", "⋂", "⋀", "⋁"}

    local = elem.tag.split("}")[1] if "}" in elem.tag else elem.tag

    # Direct mo element
    if local == "mo":
        text = _extract_text(elem)
        if text in NARY_CHARS:
            return text
        return None

    # mrow wrapping a single mo
    if local == "mrow":
        children = list(elem)
        if len(children) == 1:
            return _is_nary_char(children[0])
        # mrow with mo + whitespace mspace — find the mo
        for child in children:
            result = _is_nary_char(child)
            if result:
                return result

    return None


def _convert_msub(elem: etree._Element) -> etree._Element:
    """msub → m:nary if base is n-ary operator, else m:s (subscript)."""
    children = list(elem)
    if len(children) < 2:
        return _convert(children[0]) if children else None

    nary_char = _is_nary_char(children[0])
    if nary_char:
        # Construct a synthetic munder for _convert_nary
        synthetic = etree.Element(_mml_tag("munder"))
        synthetic.append(children[0])
        synthetic.append(children[1])
        return _convert_nary(synthetic, "und")

    s = etree.Element(_omml_tag("s"))
    # Base
    e = etree.SubElement(s, _omml_tag("e"))
    _append_children(e, [_convert(children[0])])
    # Subscript
    sub = etree.SubElement(s, _omml_tag("sub"))
    _append_children(sub, [_convert(children[1])])
    return s


def _convert_msup(elem: etree._Element) -> etree._Element:
    """msup → m:nary if base is n-ary operator, else m:s with sub1Hide (superscript only)."""
    children = list(elem)
    if len(children) < 2:
        return _convert(children[0]) if children else None

    nary_char = _is_nary_char(children[0])
    if nary_char:
        # Construct a synthetic mover for _convert_nary
        synthetic = etree.Element(_mml_tag("mover"))
        synthetic.append(children[0])
        synthetic.append(children[1])
        return _convert_nary(synthetic, "ovr")

    s = etree.Element(_omml_tag("s"))
    sPr = etree.SubElement(s, _omml_tag("sPr"))
    # Hide sub position to make it a superscript
    sPr.set(_omml_tag("sub1Hide"), "1")
    ctrlPr = etree.SubElement(sPr, _omml_tag("ctrlPr"))
    _add_run_props(ctrlPr)
    # Base
    e = etree.SubElement(s, _omml_tag("e"))
    _append_children(e, [_convert(children[0])])
    # Superscript
    sup = etree.SubElement(s, _omml_tag("sup"))
    _append_children(sup, [_convert(children[1])])
    return s


def _convert_msubsup(elem: etree._Element) -> etree._Element:
    """msubsup → m:nary if base is n-ary operator, else m:s (both sub and sup)."""
    children = list(elem)
    if len(children) < 3:
        # Fall back to msub if only 2 children
        return _convert_msub(elem) if len(children) >= 2 else None

    nary_char = _is_nary_char(children[0])
    if nary_char:
        # Construct a synthetic munderover for _convert_nary
        synthetic = etree.Element(_mml_tag("munderover"))
        synthetic.append(children[0])
        synthetic.append(children[1])
        synthetic.append(children[2])
        return _convert_nary(synthetic, "subSup")

    s = etree.Element(_omml_tag("s"))
    # Base
    e = etree.SubElement(s, _omml_tag("e"))
    _append_children(e, [_convert(children[0])])
    # Subscript
    sub = etree.SubElement(s, _omml_tag("sub"))
    _append_children(sub, [_convert(children[1])])
    # Superscript
    sup = etree.SubElement(s, _omml_tag("sup"))
    _append_children(sup, [_convert(children[2])])
    return s


def _convert_mfrac(elem: etree._Element) -> etree._Element:
    """mfrac → m:f (fraction)."""
    children = list(elem)
    f = etree.Element(_omml_tag("f"))
    fPr = etree.SubElement(f, _omml_tag("fPr"))
    type_el = etree.SubElement(fPr, _omml_tag("type"))
    type_el.set(_omml_tag("val"), "bar")
    ctrlPr = etree.SubElement(fPr, _omml_tag("ctrlPr"))
    _add_run_props(ctrlPr)

    # Numerator
    num = etree.SubElement(f, _omml_tag("num"))
    if len(children) >= 1:
        _append_children(num, _convert_mrow_contents(children[0]))

    # Denominator
    den = etree.SubElement(f, _omml_tag("den"))
    if len(children) >= 2:
        _append_children(den, _convert_mrow_contents(children[1]))

    return f


def _convert_nary(elem: etree._Element, lim_loc: str) -> etree._Element:
    """munderover/munder/mover → m:nary (n-ary operator like sum, product)."""
    children = list(elem)
    nary = etree.Element(_omml_tag("nary"))
    naryPr = etree.SubElement(nary, _omml_tag("naryPr"))

    # Operator character
    op_char = _extract_text(children[0]) if children else ""
    chr_el = etree.SubElement(naryPr, _omml_tag("chr"))
    chr_el.set(_omml_tag("val"), op_char)

    # Limits location
    limLoc_el = etree.SubElement(naryPr, _omml_tag("limLoc"))
    limLoc_el.set(_omml_tag("val"), lim_loc)

    # Hide sub/sup flags (both visible by default)
    subHide = etree.SubElement(naryPr, _omml_tag("subHide"))
    subHide.set(_omml_tag("val"), "0")
    supHide = etree.SubElement(naryPr, _omml_tag("supHide"))
    supHide.set(_omml_tag("val"), "0")

    # Control properties with Cambria Math font
    ctrlPr = etree.SubElement(naryPr, _omml_tag("ctrlPr"))
    _add_run_props(ctrlPr)

    # Sub (lower limit)
    sub = etree.SubElement(nary, _omml_tag("sub"))
    if lim_loc in ("subSup", "und") and len(children) >= 2:
        _append_children(sub, _convert_mrow_contents(children[1]))

    # Sup (upper limit)
    sup = etree.SubElement(nary, _omml_tag("sup"))
    if lim_loc == "subSup" and len(children) >= 3:
        _append_children(sup, _convert_mrow_contents(children[2]))
    elif lim_loc == "ovr" and len(children) >= 2:
        _append_children(sup, _convert_mrow_contents(children[1]))

    # e (body — typically empty for standalone n-ary)
    e = etree.SubElement(nary, _omml_tag("e"))

    return nary


def _convert_mtable(elem: etree._Element) -> etree._Element:
    """mtable → m:m (matrix)."""
    m = etree.Element(_omml_tag("m"))
    mPr = etree.SubElement(m, _omml_tag("mPr"))
    ctrlPr = etree.SubElement(mPr, _omml_tag("ctrlPr"))
    _add_run_props(ctrlPr)
    rows = elem.findall(_MATHML_PREFIX + "mtr")
    for row in rows:
        mr = etree.SubElement(m, _omml_tag("mr"))
        cols = row.findall(_MATHML_PREFIX + "mtd")
        for col in cols:
            e = etree.SubElement(mr, _omml_tag("e"))
            col_children = [_convert(c) for c in col]
            _append_children(e, col_children)

    return m


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _add_run_props(parent: etree._Element) -> None:
    """Add standard run properties (Cambria Math) to a ctrlPr or rPr element."""
    WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    rPr = etree.SubElement(parent, f"{{{WORD_NS}}}rPr")
    rFonts = etree.SubElement(rPr, f"{{{WORD_NS}}}rFonts")
    rFonts.set(f"{{{WORD_NS}}}ascii", "Cambria Math")
    rFonts.set(f"{{{WORD_NS}}}hAnsi", "Cambria Math")
    rFonts.set(f"{{{WORD_NS}}}eastAsia", "Cambria Math")


def _make_run(text: str, italic: bool = False, plain: bool = False) -> etree._Element:
    """Create an OMML run element (m:r)."""
    r = etree.Element(_omml_tag("r"))
    rPr = etree.SubElement(r, _omml_tag("rPr"))
    sty = etree.SubElement(rPr, _omml_tag("sty"))
    sty.set(_omml_tag("val"), "i" if italic else "p")
    t = etree.SubElement(r, _omml_tag("t"))
    t.text = text
    return r


def _extract_text(elem: etree._Element) -> str:
    """Extract text content from a MathML element (direct text only, not recursive)."""
    if elem.text and elem.text.strip():
        return elem.text.strip()
    # Some elements nest text in child elements
    parts = []
    for child in elem:
        if child.text:
            parts.append(child.text)
    return "".join(parts).strip()


def _convert_mrow_contents(elem: etree._Element) -> list[etree._Element | None]:
    """Convert an mrow's children, or a single element if it's not an mrow."""
    local = elem.tag.split("}")[1] if "}" in elem.tag else elem.tag
    if local == "mrow":
        return [_convert(c) for c in elem]
    else:
        result = _convert(elem)
        return [result] if result is not None else []


def _absorb_nary_bodies(results: list[etree._Element | None]) -> None:
    """Move sibling elements after a n-ary operator into its empty ``m:e`` body.

    In MathML, ``\\sum_{i=0}^{\\infty} x_i`` is represented as a flat sequence
    where the summation limits and the body ``x_i`` are siblings.  In OMML,
    the body must be inside the ``m:nary/m:e`` element.  This function scans
    the converted results list and, for each n-ary with an empty ``m:e``,
    absorbs subsequent siblings into that ``m:e``.
    """
    i = 0
    while i < len(results):
        item = results[i]
        if item is None:
            i += 1
            continue

        # Only process nary elements
        if item.tag != _OMML_PREFIX + "nary":
            i += 1
            continue

        # Find the m:e child
        e_el = item.find(_OMML_PREFIX + "e")
        if e_el is None or len(e_el) > 0:
            # m:e already has content or doesn't exist — skip
            i += 1
            continue

        # Absorb subsequent siblings into m:e
        absorbed = False
        while i + 1 < len(results):
            next_item = results[i + 1]
            if next_item is None:
                results.pop(i + 1)
                continue
            # Stop absorbing at another n-ary operator (different sum/product/etc)
            if next_item.tag == _OMML_PREFIX + "nary":
                break
            # Move the sibling into m:e
            results.pop(i + 1)
            _append_children(e_el, [next_item])
            absorbed = True

        if not absorbed:
            # Ensure m:e has at least an empty run so it's valid OMML
            _append_children(e_el, [_make_run("", plain=True)])

        i += 1


def _append_children(parent: etree._Element, children: list[etree._Element | None]) -> None:
    """Append children to parent, expanding CONTAINER markers (from mrow)."""
    for child in children:
        if child is None:
            continue
        if child.tag == "CONTAINER":
            for c in child:
                parent.append(c)
        else:
            parent.append(child)