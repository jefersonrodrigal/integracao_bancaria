"""Gera docs/itau_cnab400_campos.md a partir das definições de leiaute (fonte única).

Uso: python -m scripts.export_layout_doc
"""

from __future__ import annotations

from pathlib import Path

from app.cnab.layouts.itau.cnab400 import records, tables

OUTPUT = Path(__file__).parents[1] / "docs" / "itau_cnab400_campos.md"


def render() -> str:
    out = [
        "# Itaú CNAB 400 — campos e posições",
        "",
        f"Gerado por `scripts/export_layout_doc.py` a partir de `app/cnab/layouts/itau/cnab400/"
        f"records.py`. Manual: *{tables.MANUAL_TITLE}*, versão {tables.MANUAL_VERSION}. "
        "A coluna Referência indica página/nota do manual. Não edite à mão.",
        "",
    ]
    for layout in records.ALL_LAYOUTS:
        out += [
            f"## `{layout.name}` ({layout.reference})",
            "",
            "| Campo | Posição | Picture | Conteúdo fixo | Referência |",
            "|---|---|---|---|---|",
        ]
        for f in layout.fields:
            fixed = f"`{f.constant.strip() or '(brancos)'}`" if f.constant is not None else ""
            out.append(
                f"| {f.name} | {f.start:03d}-{f.end:03d} | {f.picture} | {fixed} | {f.reference} |"
            )
        out.append("")
    out += [
        "## Carteiras (Nota 5, p.18)",
        "",
        "| Carteira | Código (pos. 108) | Modalidade | Descrição | Obs | Suportada | Motivo |",
        "|---|---|---|---|---|---|---|",
    ]
    for w in tables.WALLETS.values():
        modality = w.modality.value if w.modality else "—"
        out.append(
            f"| {w.number} | {w.code} | {modality} | {w.description} | "
            f"{','.join(sorted(w.obs))} | {'sim' if w.supported else 'não'} | {w.reason} |"
        )
    out += [
        "",
        "## Ocorrências de retorno (Nota 17, p.23-25) e efeito aplicado",
        "",
        "O **efeito** é regra interna da aplicação (ver `docs/itau_cnab400.md`).",
        "",
        "| Código | Descrição (manual) | Efeito interno |",
        "|---|---|---|",
    ]
    for o in tables.RETURN_OCCURRENCES.values():
        out.append(f"| {o.code} | {o.description} | {o.effect.value} |")
    out.append("")
    return "\n".join(out)


def main() -> None:
    OUTPUT.write_text(render(), encoding="utf-8", newline="\n")
    print(f"Escrito {OUTPUT}")


if __name__ == "__main__":
    main()
