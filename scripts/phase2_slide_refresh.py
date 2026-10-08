"""
One-shot refresh for slides/phase2_status_update.html:
- Rebuild Architecture slide from slides/assets/*.svg (inline for file://).
- Merge Phase 1 deltas into title slide; remove redundant slides.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "slides" / "phase2_status_update.html"
SVG_PIPE = ROOT / "slides" / "assets" / "beacon_pipeline_phase2.svg"
SVG_SESS = ROOT / "slides" / "assets" / "beacon_session_phase2.svg"

CSS_ARCH = """
    .arch-slide .arch-slide-lead { font-size: .95rem; margin-bottom: 2px; max-width: 58rem; }
    .arch-diagrams { display: flex; flex-direction: column; gap: 8px; margin-top: 6px; }
    .pipeline-figure--arch { margin-top: 0; }
    .pipeline-figure--arch svg { max-width: 100%; }
    .pipeline-figure--second { margin-top: 0; }
    .arch-slide-cap { margin-top: 6px; font-size: .84rem; }
    .hero-delta { margin-top: 10px; }
    .hero-delta .card--compact { padding: 10px 12px; }
    .hero-delta .card--compact h3 { margin: 0 0 5px; font-size: .88rem; }
    .hero-delta .card--compact ul { font-size: .8rem; padding-left: 15px; margin: 0; }
    .hero-delta .card--compact li + li { margin-top: 3px; }
"""

HERO_DELTA = """
          <div class="grid two hero-delta">
            <div class="card card--compact">
              <h3>Since Phase 1</h3>
              <ul>
                <li>Cached search index; corpus rebuild detection; tighter UI limits.</li>
                <li>Python webpage refresh path; smoke + API tests in <code>tests/</code>.</li>
              </ul>
            </div>
            <div class="card card--compact">
              <h3>Answers</h3>
              <ul>
                <li>Cleaner citations; better sparse-PDF behavior.</li>
                <li>Phase 2 JSON aligns with institute refusal checks.</li>
              </ul>
            </div>
          </div>"""


def main() -> None:
    # Normalize Windows CRLF so string anchors match and the file stays LF in git.
    html = HTML.read_text(encoding="utf-8").replace("\r\n", "\n")
    svg1 = SVG_PIPE.read_text(encoding="utf-8").strip()
    svg2 = SVG_SESS.read_text(encoding="utf-8").strip()

    def tag_svg(s: str) -> str:
        if s.startswith("<svg "):
            return s.replace("<svg ", '<svg class="pipeline-diagram" preserveAspectRatio="xMidYMid meet" ', 1)
        return s

    svg1 = tag_svg(svg1)
    svg2 = tag_svg(svg2)

    arch_section = f"""  <section class="slide">
    <div class="frame arch-slide">
      <div class="eyebrow">Architecture</div>
      <h2>Corpus, retrieval, and web sessions</h2>
      <p class="lead arch-slide-lead">Top: offline index build. Bottom: each question uses the same lexical path (UI or CLI). Second diagram: in-memory session and guardrails in <code>serve_ui.py</code> before the worker runs.</p>
      <div class="arch-diagrams">
        <figure class="pipeline-figure pipeline-figure--arch">
{svg1}
        </figure>
        <figure class="pipeline-figure pipeline-figure--arch pipeline-figure--second">
{svg2}
        </figure>
      </div>
      <p class="cap arch-slide-cap">Diagrams are embedded for local <code>file://</code> viewing. Standalone copies: <code>slides/assets/beacon_pipeline_phase2.svg</code>, <code>slides/assets/beacon_session_phase2.svg</code>.</p>
    </div>
  </section>"""

    arch_re = re.compile(
        r"<section class=\"slide\">\s*<div class=\"frame[^\"]*\">\s*<div class=\"eyebrow\">Architecture</div>[\s\S]*?</section>\s*(?=\s*<section class=\"slide\">\s*<div class=\"frame\">\s*<div class=\"eyebrow\">Evidence</div>)",
        re.MULTILINE,
    )
    m = arch_re.search(html)
    if not m:
        raise SystemExit("Architecture section pattern not found")
    html = arch_re.sub(arch_section + "\n\n", html, count=1)

    if ".arch-slide" not in html:
        needle = "    .pipeline-figure .cap {\n"
        if needle not in html:
            raise SystemExit("CSS anchor not found")
        html = html.replace(
            needle,
            needle + CSS_ARCH + "\n",
            1,
        )

    # Merge hero delta into title slide (after stat-strip, before closing first hero column div)
    stat_anchor = """            <div class="stat"><span class="big">32/32</span><span class="lbl">Support / refusal<br>expectations met</span></div>
          </div>
        </div>
        <div class="team-card">"""
    # Do not key off the substring "hero-delta" — it already appears in CSS (.hero-delta).
    if '<div class="grid two hero-delta">' not in html and stat_anchor in html:
        html = html.replace(
            stat_anchor,
            """            <div class="stat"><span class="big">32/32</span><span class="lbl">Support / refusal<br>expectations met</span></div>
          </div>"""
            + HERO_DELTA
            + """
        </div>
        <div class="team-card">""",
            1,
        )

    # Remove "What changed" slide entirely
    html = re.sub(
        r"\s*<section class=\"slide\">\s*<div class=\"frame\">\s*<div class=\"eyebrow\">What changed</div>[\s\S]*?</section>",
        "",
        html,
        count=1,
    )

    # Remove Live system slide
    html = re.sub(
        r"\s*<section class=\"slide\">\s*<div class=\"frame\">\s*<div class=\"eyebrow\">Live system</div>[\s\S]*?</section>",
        "",
        html,
        count=1,
    )

    # Remove Eval design (32 questions four types) slide
    html = re.sub(
        r"\s*<section class=\"slide\">\s*<div class=\"frame\">\s*<div class=\"eyebrow\">Eval design</div>[\s\S]*?</section>",
        "",
        html,
        count=1,
    )

    # Remove standalone HPC slide
    html = re.sub(
        r"\s*<section class=\"slide\">\s*<div class=\"frame\">\s*<h2>Why HPC matters this week</h2>[\s\S]*?</section>",
        "",
        html,
        count=1,
    )

    # Evidence slide: add compact Phase 2 mix line after h2 if not present
    ev_marker = '<h2>Four suites, same discipline</h2>\n      <p class="lead">'
    ev_insert = (
        '<h2>Four suites, same discipline</h2>\n'
        '      <p class="lead" style="font-size:.9rem;margin-top:-6px;margin-bottom:6px">'
        'Phase 2 mix (32 Q in <code>eval/phase2_eval_32_candidate.json</code>): '
        "factual, exploratory, ambiguous, plus one unsupported prompt.</p>\n"
        "      <p class=\"lead\">"
    )
    if "Phase 2 mix (32 Q" not in html and ev_marker in html:
        html = html.replace(ev_marker, ev_insert, 1)

    # Timeline: add HPC bullet to Apr 27-May 3 card
    tim_anchor = """              <p class="timeline-time">Apr 27-May 3</p>
              <h3 class="timeline-title">Integrate HPC checkpoint</h3>
              <ul>
                <li>Smoke-submit the Slurm eval job and verify environment paths.</li>
                <li>Capture logs and artifacts so reruns are presenter-ready.</li>
              </ul>"""
    tim_new = """              <p class="timeline-time">Apr 27-May 3</p>
              <h3 class="timeline-title">Integrate HPC checkpoint</h3>
              <ul>
                <li>Smoke-submit <code>hpc/submit_phase2_eval.sbatch</code>; confirm <code>pwsh</code> and module paths per <code>hpc/README.md</code>.</li>
                <li>Capture logs and artifacts so grading reruns are presenter-ready.</li>
              </ul>"""
    if tim_anchor in html:
        html = html.replace(tim_anchor, tim_new, 1)

    HTML.write_text(html, encoding="utf-8")
    print("Updated", HTML.relative_to(ROOT))


if __name__ == "__main__":
    main()
