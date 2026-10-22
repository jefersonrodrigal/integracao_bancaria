"""Adaptador Itaú CNAB 400 de cobrança (manual JANEIRO 2017)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from typing import Any

from app.cnab.base import (
    CollectionProfileData,
    GeneratedFile,
    LayoutFamily,
    ParsedReturn,
    RemittanceItemData,
    ReturnDetail,
    ValidationReport,
)
from app.cnab.checksums import mod10
from app.cnab.fields import Field, FieldFormatError, FieldType, RecordLayout
from app.cnab.layouts.itau.cnab400 import records as r
from app.cnab.layouts.itau.cnab400 import rules
from app.cnab.layouts.itau.cnab400 import tables as t
from app.cnab.occurrence_codes import OccurrenceInfo
from app.cnab.validators import TERMINATORS, check_sequence, split_records
from app.domain.enums import DocumentType, FineType, RemittanceCommand
from app.domain.errors import Issue, ValidationFailed
from app.domain.value_objects import BRAZILIAN_STATES

RECORD_LENGTH = 400
ZERO = Decimal("0")
_INSCRIPTION = {DocumentType.CPF: "01", DocumentType.CNPJ: "02"}  # Nota 1 / p.8
_COMMAND_CODES = {
    RemittanceCommand.REGISTER: "01",
    RemittanceCommand.WRITE_OFF: "02",
    RemittanceCommand.CHANGE_DUE_DATE: "06",
}
_GENERATED_CODES = frozenset(_COMMAND_CODES.values())
_FINE_CODES = {FineType.FIXED: "1", FineType.PERCENT: "2"}
# Anexo 4 (p.56) cita 126-131-146-150-168; a Nota 23 (p.34) cita 126-131-145-150-168.
# Ambos mantidos; nenhuma destas carteiras é suportada para emissão nesta versão.
_DAC_WALLET_ONLY = frozenset({"126", "131", "145", "146", "150", "168"})
_D6 = Field("data", 1, 6, FieldType.DATE_DDMMYY)


class ItauCnab400Adapter:
    layout_id = t.LAYOUT_ID
    bank_code = "341"
    family = LayoutFamily.CNAB400
    manual_version = t.MANUAL_VERSION

    # ------------------------------------------------------------------ regras
    def validate_profile(self, profile: CollectionProfileData) -> list[Issue]:
        return rules.validate_profile(profile)

    def nosso_numero_assigned_by_bank(self, wallet: str) -> bool:
        info = t.WALLETS.get(wallet)
        return bool(info and info.nosso_numero_by_bank)

    def validate_item(
        self, profile: CollectionProfileData, item: RemittanceItemData
    ) -> list[Issue]:
        return rules.validate_item(profile, item)

    def describe_occurrence(self, code: str) -> OccurrenceInfo | None:
        return t.RETURN_OCCURRENCES.get(code)

    def nosso_numero_dac(self, agency: str, account: str, wallet: str, nosso_numero: str) -> str:
        """Nota 23 (p.34) / Anexo 4 (p.56)."""
        info = t.WALLETS.get(wallet)
        escritural = info is not None and info.modality is t.Modality.ESCRITURAL
        nn = nosso_numero.zfill(8)
        if escritural or wallet in _DAC_WALLET_ONLY:
            return str(mod10(wallet + nn))
        return str(mod10(agency + account + wallet + nn))

    # ------------------------------------------------------------------ remessa
    def generate_remittance(
        self,
        profile: CollectionProfileData,
        items: Sequence[RemittanceItemData],
        generated_on: date,
    ) -> GeneratedFile:
        issues = list(self.validate_profile(profile))
        if not items:
            issues.append(Issue("EMPTY_REMITTANCE", "Remessa sem títulos"))
        seen_refs: set[str] = set()
        seen_nn: set[str] = set()
        for item in items:
            context = {"title_id": item.reference_id}
            for issue in self.validate_item(profile, item):
                issues.append(
                    Issue(
                        issue.code,
                        issue.message,
                        issue.severity,
                        issue.field,
                        reference=issue.reference,
                        context=context,
                    )
                )
            nn = (item.nosso_numero or "").lstrip("0")
            if nn:
                key = f"{nn}:{item.command}"
                if key in seen_nn:
                    issues.append(
                        Issue(
                            "NOSSO_NUMERO_DUPLICATED",
                            "Nosso número repetido para o mesmo comando no arquivo",
                            field="nosso_numero",
                            reference="Tabela 1 cód. 15 p.26",
                            context=context,
                        )
                    )
                seen_nn.add(key)
            if item.command is RemittanceCommand.REGISTER:
                if item.company_reference in seen_refs:
                    issues.append(
                        Issue(
                            "REFERENCE_DUPLICATED",
                            "Uso da empresa repetido",
                            field="company_reference",
                            reference=rules.INTERNAL,
                            context=context,
                        )
                    )
                seen_refs.add(item.company_reference)
        if issues:
            raise ValidationFailed(issues, "Remessa não pode ser gerada")

        wallet = t.WALLETS[profile.wallet]
        ordered = list(items)
        if wallet.booklet:
            # Nota 5 obs (C) p.18: carnês ordenados por pagador e vencimento.
            ordered.sort(key=lambda i: (i.payer.document, i.due_date))

        warnings: list[str] = []
        lines: list[str] = []
        positions: dict[str, int] = {}

        def add(layout: RecordLayout, values: dict[str, object]) -> None:
            values["numero_sequencial"] = len(lines) + 1
            lines.append(layout.render(values, warnings))

        add(
            r.REMITTANCE_HEADER,
            {
                "agencia": profile.agency,
                "conta": profile.account,
                "dac": profile.account_dac,
                "nome_empresa": profile.company_name,
                "data_geracao": generated_on,
            },
        )
        for item in ordered:
            positions[f"{item.company_reference}:{item.command}"] = len(lines) + 1
            add(r.REMITTANCE_DETAIL, self._detail_values(profile, wallet, item))
            if item.command is RemittanceCommand.REGISTER:
                if item.fine is not None:
                    add(
                        r.REMITTANCE_FINE,
                        {
                            "codigo_multa": _FINE_CODES[item.fine.type],
                            "data_multa": item.fine.start_date,
                            "multa": item.fine.value,
                        },
                    )
                if item.payer_email or item.guarantor:
                    add(r.REMITTANCE_EMAIL_GUARANTOR, self._type5_values(item))
        add(r.REMITTANCE_TRAILER, {})

        terminator = TERMINATORS[profile.line_terminator].decode()
        content = "".join(line + terminator for line in lines).encode("ascii")
        return GeneratedFile(
            content=content,
            record_count=len(lines),
            line_numbers=positions,
            warnings=[Issue("TRUNCATED", w, "warning") for w in warnings],
        )

    def _detail_values(
        self, profile: CollectionProfileData, wallet: t.Wallet, item: RemittanceItemData
    ) -> dict[str, object]:
        values: dict[str, object] = {
            "agencia": profile.agency,
            "conta": profile.account,
            "dac": profile.account_dac,
            "nosso_numero": item.nosso_numero.zfill(8) if item.nosso_numero else None,
            "numero_carteira": wallet.number,
            "codigo_carteira": wallet.code,
            "codigo_ocorrencia": _COMMAND_CODES[item.command],
            "valor_titulo": item.amount,
        }
        if item.command is RemittanceCommand.CHANGE_DUE_DATE:
            # Nota 6 obs (A): demais campos com zeros/brancos; vencimento é o dado alterado.
            values["vencimento"] = item.new_due_date
            return values
        if item.command is RemittanceCommand.WRITE_OFF:
            return values
        payer = item.payer
        values.update(
            {
                "codigo_inscricao": _INSCRIPTION[profile.company_document_type],
                "numero_inscricao": profile.company_document,
                "uso_empresa": item.company_reference,
                "numero_documento": item.document_number,
                "vencimento": item.due_date,
                "especie": item.species,
                "aceite": item.acceptance,
                "data_emissao": item.issue_date,
                "instrucao_1": item.instruction1,
                "instrucao_2": item.instruction2,
                "juros_1_dia": item.interest_per_day,
                "desconto_ate": item.discount_limit_date if item.discount_amount else None,
                "valor_desconto": item.discount_amount,
                "valor_iof": item.iof_amount,
                "abatimento": item.rebate_amount,
                "codigo_inscricao_pagador": _INSCRIPTION[payer.document_type],
                "numero_inscricao_pagador": payer.document,
                "nome_pagador": payer.name,
                "logradouro": payer.street,
                "bairro": payer.district,
                "cep": payer.zip_code,
                "cidade": payer.city,
                "estado": payer.state.upper(),
                "sacador_avalista": item.guarantor.name if item.guarantor else None,
                "data_mora": item.interest_start_date,
                "prazo": item.protest_days,
            }
        )
        return values

    @staticmethod
    def _type5_values(item: RemittanceItemData) -> dict[str, object]:
        g = item.guarantor
        values: dict[str, object] = {"email": item.payer_email}
        if g is None:
            values["codigo_inscricao_sacador"] = "00"  # Nota 30: 00 = não há sacador
            return values
        values.update(
            {
                "codigo_inscricao_sacador": _INSCRIPTION[g.document_type],
                "numero_inscricao_sacador": g.document,
                "logradouro_sacador": g.street,
                "bairro_sacador": g.district,
                "cep_sacador": g.zip_code,
                "cidade_sacador": g.city,
                "estado_sacador": g.state.upper(),
            }
        )
        return values

    def validate_remittance(self, content: bytes) -> ValidationReport:
        report = ValidationReport()
        raw_lines = split_records(content, report, RECORD_LENGTH)
        if not raw_lines:
            return report
        lines: list[tuple[int, str]] = []
        for raw in raw_lines:
            try:
                lines.append((raw.number, raw.data.decode("ascii")))
            except UnicodeDecodeError:
                report.error(
                    "NON_ASCII", "Caracteres fora de ASCII", line=raw.number, reference="p.5"
                )
        if not report.is_valid:
            return report

        sequence: list[tuple[int, str | None]] = []
        header: dict[str, Any] = {}
        current: dict[str, Any] | None = None
        group_types: list[str] = []
        detail_count = 0
        for index, (number, line) in enumerate(lines):
            kind = line[0]
            last = index == len(lines) - 1
            if index == 0:
                if kind != "0":
                    report.error(
                        "HEADER_MISSING",
                        "Primeiro registro deve ser o header (0)",
                        line=number,
                        reference="p.5",
                    )
                    return report
                header = self._parse_into(r.REMITTANCE_HEADER, line, number, report)
            elif last:
                if kind != "9":
                    report.error(
                        "TRAILER_MISSING",
                        "Último registro deve ser o trailer (9)",
                        line=number,
                        reference="p.5",
                    )
                else:
                    self._parse_into(r.REMITTANCE_TRAILER, line, number, report)
            elif kind == "1":
                detail_count += 1
                current = self._parse_into(r.REMITTANCE_DETAIL, line, number, report)
                group_types = []
                self._check_detail(current, header, number, report)
            elif kind in ("2", "4", "5"):
                if current is None:
                    report.error(
                        "ORPHAN_RECORD",
                        f"Registro {kind} sem registro 1 anterior",
                        line=number,
                        reference="p.9; p.12",
                    )
                elif kind == "2":
                    if "2" in group_types:
                        report.error(
                            "DUPLICATED_FINE",
                            "Mais de um registro 2 para o título",
                            line=number,
                            reference="p.9",
                        )
                    values = self._parse_into(r.REMITTANCE_FINE, line, number, report)
                    self._check_fine(values, current, number, report)
                elif kind == "5":
                    values = self._parse_into(r.REMITTANCE_EMAIL_GUARANTOR, line, number, report)
                    self._check_type5(values, number, report)
                else:
                    report.warning(
                        "SPLIT_NOT_VALIDATED",
                        "Registro 4 (rateio) não é validado nesta versão",
                        line=number,
                        reference="p.10-11",
                    )
                group_types.append(kind)
            elif kind == "0":
                report.error(
                    "DUPLICATED_HEADER",
                    "Mais de um header no arquivo",
                    line=number,
                    reference="p.5; indicador 04.2 p.40",
                )
            else:
                report.error(
                    "UNKNOWN_RECORD",
                    f"Tipo de registro {kind!r} não previsto",
                    line=number,
                    reference="p.5",
                )
            sequence.append((number, line[394:400]))
        if len(lines) < 2:
            report.error("TRAILER_MISSING", "Arquivo sem trailer", reference="p.5")
        if detail_count == 0:
            report.error("NO_DETAILS", "Remessa sem registros de detalhe", reference="p.5")
        check_sequence(sequence, report)
        return report

    @staticmethod
    def _parse_into(
        layout: RecordLayout, line: str, number: int, report: ValidationReport
    ) -> dict[str, Any]:
        values, errors = layout.parse(line)
        for error in errors:
            field = layout.field(error.field)
            report.error(
                "FIELD_FORMAT",
                error.message,
                line=number,
                field=error.field,
                reference=field.reference,
            )
        return values

    def _check_detail(
        self, v: dict[str, Any], header: dict[str, Any], number: int, report: ValidationReport
    ) -> None:
        def err(code: str, message: str, field: str, reference: str) -> None:
            report.error(code, message, line=number, field=field, reference=reference)

        for name in ("agencia", "conta", "dac"):
            if v.get(name) != header.get(name):
                err("ACCOUNT_MISMATCH", "Agência/conta difere do header", name, "p.7-8")
        code = v.get("codigo_ocorrencia")
        if code not in t.REMITTANCE_OCCURRENCES:
            err(
                "OCCURRENCE",
                f"Código de ocorrência {code!r} não listado",
                "codigo_ocorrencia",
                "Nota 6 p.19",
            )
            return
        if code not in _GENERATED_CODES:
            report.warning(
                "OCCURRENCE_NOT_VALIDATED",
                f"Ocorrência {code} sem validação semântica nesta versão",
                line=number,
                field="codigo_ocorrencia",
                reference="Nota 6 p.19",
            )
        wallet = t.WALLETS.get(v.get("numero_carteira") or "")
        if wallet is None:
            err("WALLET", "Carteira não listada", "numero_carteira", "Nota 5 p.18")
        elif v.get("codigo_carteira") != wallet.code:
            err(
                "WALLET_CODE",
                f"Código da carteira deve ser {wallet.code}",
                "codigo_carteira",
                "Nota 5 p.18",
            )
        if v.get("qtde_moeda") not in (None, ZERO):
            err(
                "CURRENCY_QTY",
                "Quantidade de moeda deve ser zero para Real",
                "qtde_moeda",
                "Nota 4 p.18",
            )
        if v.get("agencia_cobradora") not in (None, "00000"):
            err(
                "COLLECTING_AGENCY",
                "Agência cobradora deve ser zeros",
                "agencia_cobradora",
                "Nota 9 p.20",
            )
        if code not in ("35", "38") and v.get("instrucao_alegacao") not in (None, "0000"):
            err(
                "INSTRUCTION_CANCEL",
                "Deve ser zeros fora das ocorrências 35/38",
                "instrucao_alegacao",
                "Nota 27 p.36",
            )
        amount = v.get("valor_titulo")
        if code in ("01", "02", "06") and not (isinstance(amount, Decimal) and amount > 0):
            err("AMOUNT", "Valor do título obrigatório", "valor_titulo", "Nota 6 obs (A); Nota 8")
        nn = v.get("nosso_numero") or "00000000"
        if code != "01":
            if int(nn) == 0:
                err("NOSSO_NUMERO", "Nosso número obrigatório", "nosso_numero", "Nota 6 obs (A)")
            if code == "06" and v.get("vencimento") is None:
                err("DUE_DATE", "Vencimento obrigatório", "vencimento", "Nota 6 p.19")
            return
        if wallet is not None and wallet.nosso_numero_by_bank and int(nn):
            err(
                "NOSSO_NUMERO",
                "Carteira escritural: enviar nosso número zerado",
                "nosso_numero",
                "Nota 3 p.18",
            )
        if wallet is not None and not wallet.nosso_numero_by_bank and not int(nn):
            err(
                "NOSSO_NUMERO",
                "Carteira direta: nosso número obrigatório",
                "nosso_numero",
                "Nota 3 p.18",
            )
        if isinstance(amount, Decimal) and amount > rules.MAX_AMOUNT:
            err("AMOUNT_MAX", "Valor maior que 10.000.000,00", "valor_titulo", "Tabela 1 cód. 07")
        if v.get("codigo_inscricao") not in ("01", "02", "03", "04"):
            err("INSCRIPTION", "Tipo de inscrição inválido", "codigo_inscricao", "Nota 1 p.18")
        if not int(v.get("numero_inscricao") or "0"):
            err("INSCRIPTION", "Inscrição da empresa obrigatória", "numero_inscricao", "Nota 1")
        if v.get("vencimento") is None:
            err("DUE_DATE", "Vencimento obrigatório", "vencimento", "Nota 7 p.20")
        if v.get("data_emissao") is None:
            err("ISSUE_DATE", "Data de emissão obrigatória", "data_emissao", "Nota 31 p.37")
        if v.get("especie") not in t.SPECIES:
            err("SPECIES", "Espécie inválida", "especie", "Nota 10 p.20")
        if v.get("aceite") not in ("A", "N"):
            err("ACCEPTANCE", "Aceite deve ser A ou N", "aceite", "p.8")
        if v.get("codigo_inscricao_pagador") not in ("01", "02"):
            err(
                "PAYER_INSCRIPTION",
                "Tipo de inscrição do pagador inválido",
                "codigo_inscricao_pagador",
                "p.8",
            )
        if not int(v.get("numero_inscricao_pagador") or "0"):
            err(
                "PAYER_DOCUMENT",
                "CPF/CNPJ do pagador igual a zeros",
                "numero_inscricao_pagador",
                "Tabela 1 cód. 37",
            )
        if not v.get("nome_pagador"):
            err("PAYER_NAME", "Nome do pagador não informado", "nome_pagador", "Tabela 1 cód. 08")
        if not v.get("logradouro"):
            err("STREET", "Logradouro não informado", "logradouro", "Tabela 1 cód. 10")
        if not int(v.get("cep") or "0"):
            err("ZIP_CODE", "CEP inválido", "cep", "Tabela 1 cód. 11")
        if v.get("estado") not in BRAZILIAN_STATES:
            err("STATE", "UF inválida", "estado", "Tabela 1 cód. 04")
        for name in ("instrucao_1", "instrucao_2"):
            code_i = v.get(name)
            if code_i and code_i not in t.INSTRUCTIONS:
                err("INSTRUCTION", f"Instrução {code_i!r} não listada", name, "Nota 11 p.20")

    @staticmethod
    def _check_fine(
        v: dict[str, Any], detail: dict[str, Any], number: int, report: ValidationReport
    ) -> None:
        code = v.get("codigo_multa")
        if code not in t.FINE_CODES:
            report.error(
                "FINE_CODE",
                "Código da multa deve ser 0, 1 ou 2",
                line=number,
                field="codigo_multa",
                reference="Nota 35 p.38",
            )
            return
        if code == "0":
            return
        fine_date, due = v.get("data_multa"), detail.get("vencimento")
        if fine_date is None or (due is not None and fine_date < due):
            report.error(
                "FINE_DATE",
                "Data da multa ausente ou anterior ao vencimento",
                line=number,
                field="data_multa",
                reference="Nota 35 p.38",
            )
        value, amount = v.get("multa"), detail.get("valor_titulo")
        limit = Decimal(100) if code == "2" else amount
        if not isinstance(value, Decimal) or value <= 0 or (limit is not None and value >= limit):
            report.error(
                "FINE_VALUE",
                "Multa zerada ou acima do limite",
                line=number,
                field="multa",
                reference="Nota 35 p.39",
            )

    @staticmethod
    def _check_type5(v: dict[str, Any], number: int, report: ValidationReport) -> None:
        code = v.get("codigo_inscricao_sacador")
        if code not in ("00", "01", "02"):
            report.error(
                "GUARANTOR_INSCRIPTION",
                "Tipo de inscrição do sacador inválido",
                line=number,
                field="codigo_inscricao_sacador",
                reference="Nota 30 p.37",
            )
        elif code != "00":
            if not int(v.get("numero_inscricao_sacador") or "0"):
                report.error(
                    "GUARANTOR_DOCUMENT",
                    "Inscrição do sacador obrigatória",
                    line=number,
                    field="numero_inscricao_sacador",
                    reference="Nota 30 p.37",
                )
            if v.get("estado_sacador") not in BRAZILIAN_STATES:
                report.error(
                    "GUARANTOR_STATE",
                    "UF do sacador inválida",
                    line=number,
                    field="estado_sacador",
                    reference="Nota 30 p.37",
                )

    # ------------------------------------------------------------------ retorno
    def looks_like_return(self, content: bytes) -> bool:
        first = content.split(b"\n", 1)[0].rstrip(b"\r")
        return (
            len(first) == RECORD_LENGTH
            and first[0:2] == b"02"
            and first[2:9] == b"RETORNO"
            and first[76:79] == b"341"
        )

    def validate_return(self, content: bytes) -> ValidationReport:
        return self.parse_return(content).report

    def parse_return(self, content: bytes) -> ParsedReturn:
        report = ValidationReport()
        parsed = ParsedReturn(report=report)
        raw_lines = split_records(content, report, RECORD_LENGTH)
        if not raw_lines or not report.is_valid:
            return parsed
        # O manual não define encoding; latin-1 preserva 1 byte = 1 posição.
        lines = [(raw.number, raw.data.decode("latin-1")) for raw in raw_lines]
        if any(ch > "\x7f" for _, line in lines for ch in line):
            report.warning("NON_ASCII", "Arquivo contém bytes fora de ASCII (lidos como latin-1)")
        sequence: list[tuple[int, str | None]] = []
        type1_count = 0
        for index, (number, line) in enumerate(lines):
            kind = line[0]
            sequence.append((number, line[394:400]))
            if index == 0:
                if kind != "0":
                    report.error(
                        "HEADER_MISSING",
                        "Primeiro registro deve ser o header (0)",
                        line=number,
                        reference="p.13",
                    )
                    return parsed
                parsed.header = self._parse_into(r.RETURN_HEADER, line, number, report)
                if parsed.header.get("literal_servico") != "COBRANCA":
                    report.warning(
                        "SERVICE_LITERAL",
                        "Literal de serviço diferente de COBRANCA",
                        line=number,
                        reference="p.13",
                    )
            elif index == len(lines) - 1:
                if kind != "9":
                    report.error(
                        "TRAILER_MISSING",
                        "Último registro deve ser o trailer (9)",
                        line=number,
                        reference="p.17",
                    )
                else:
                    parsed.trailer = self._parse_into(r.RETURN_TRAILER, line, number, report)
            elif kind in ("1", "4"):
                type1_count += kind == "1"
                parsed.details.append(self._interpret(number, line))
            else:
                report.error(
                    "UNKNOWN_RECORD",
                    f"Tipo de registro {kind!r} não previsto no "
                    "retorno (múltiplos headers/trailers não são suportados)",
                    line=number,
                    reference="p.5; indicador 04.2 p.40",
                )
        if len(lines) < 2:
            report.error("TRAILER_MISSING", "Arquivo sem trailer", reference="p.17")
        check_sequence(sequence, report)
        declared = parsed.trailer.get("qtde_detalhes")
        if declared is not None and int(declared) != type1_count:
            report.warning(
                "DETAIL_COUNT",
                f"Trailer informa {int(declared)} registros de transação; arquivo tem "
                f"{type1_count} registros tipo 1 (semântica do campo não detalhada)",
                reference="p.17",
            )
        for detail in parsed.details:
            for issue in detail.issues:
                if issue.severity == "error":
                    report.warning(
                        "INVALID_DETAIL",
                        issue.message,
                        line=detail.line_number,
                        field=issue.field,
                        reference=issue.reference,
                    )
        return parsed

    def _interpret(self, number: int, line: str) -> ReturnDetail:
        kind = line[0]
        code = line[108:110]
        if kind == "4":
            layout = r.RETURN_SPLIT
        elif code in ("69", "76"):
            layout = r.RETURN_CHEQUE
        else:
            layout = r.RETURN_DETAIL
        values, errors = layout.parse(line)
        detail = ReturnDetail(
            line_number=number,
            raw_line=line,
            record_type=kind,
            occurrence_code=code,
        )
        for error in errors:
            detail.issues.append(
                Issue(
                    "FIELD_FORMAT",
                    error.message,
                    field=error.field,
                    line=number,
                    reference=layout.field(error.field).reference,
                )
            )
        detail.agency = values.get("agencia")
        detail.account = values.get("conta")
        detail.account_dac = values.get("dac")
        detail.wallet = values.get("numero_carteira")
        detail.nosso_numero = values.get("nosso_numero")
        detail.nosso_numero_dac = values.get("dac_nosso_numero")
        detail.company_reference = values.get("uso_empresa") or None
        detail.document_number = values.get("numero_documento") or None
        detail.occurrence_date = values.get("data_ocorrencia")
        detail.info = self.describe_occurrence(code)
        detail.extra["layout"] = layout.name
        if kind == "4":
            detail.extra["split_record"] = True
            detail.issues.append(
                Issue(
                    "SPLIT_UNSUPPORTED",
                    "Registro 4 (rateio de crédito) não suportado nesta versão",
                    "warning",
                    reference="p.16-17",
                )
            )
            return detail

        detail.amount = values.get("valor_titulo")
        if layout is r.RETURN_CHEQUE:
            detail.extra["cheque_account"] = values.get("agencia_conta_cheque")
            detail.extra["cheque_amount"] = str(values.get("valor_cheque") or ZERO)
            reason = values.get("motivo_devolucao") or ""
            if reason:
                detail.message_codes.append(
                    {
                        "code": reason,
                        "table": "Tabela 9",
                        "description": t.TABLE_9_CHEQUE_RETURN.get(
                            reason, "CÓDIGO NÃO DOCUMENTADO"
                        ),
                    }
                )
            self._check_nosso_numero_dac(detail)
            return detail

        detail.due_date = values.get("vencimento")
        detail.fee_amount = values.get("tarifa_cobranca") or ZERO
        detail.iof_amount = values.get("valor_iof") or ZERO
        detail.rebate_amount = values.get("valor_abatimento") or ZERO
        detail.discount_amount = values.get("valor_desconto") or ZERO
        detail.principal_amount = values.get("valor_principal") or ZERO
        detail.interest_fine_amount = values.get("juros_mora_multa") or ZERO
        detail.other_credits = values.get("outros_creditos") or ZERO
        detail.payer_name = values.get("nome_pagador") or None
        detail.accounting_flag = values.get("indicador_lancamento") or None
        detail.informational_only = detail.accounting_flag == "I"
        liquidation = values.get("codigo_liquidacao") or None
        detail.liquidation_code = liquidation
        if liquidation:
            desc, resource = t.LIQUIDATION_CODES.get(liquidation, ("NÃO DOCUMENTADO", ""))
            detail.extra["liquidation"] = {"description": desc, "resource": resource}
        detail.extra["species"] = values.get("especie")
        detail.extra["dda"] = values.get("boleto_dda") or None
        agency = values.get("agencia_cobradora")
        if agency in t.COLLECTING_AGENCY_CODES:
            detail.extra["collecting_agency"] = {
                "code": agency,
                "meaning": t.COLLECTING_AGENCY_CODES[agency],
            }
        detail.credit_date = self._loose_date(values.get("data_credito"), "data_credito", detail)

        if code in t.MESSAGE_TABLE_BY_OCCURRENCE:
            table_name, table = t.MESSAGE_TABLE_BY_OCCURRENCE[code]
            text = values.get("erros_mensagem") or ""
            for i in range(0, 8, 2):
                part = text[i : i + 2].strip()
                if part and part != "00":
                    detail.message_codes.append(
                        {
                            "code": part,
                            "table": table_name,
                            "description": table.get(part, "CÓDIGO NÃO DOCUMENTADO"),
                        }
                    )
        elif values.get("erros_mensagem"):
            detail.extra["raw_message_field"] = values.get("erros_mensagem")
        if code in t.COMPLEMENT_TABLE_BY_OCCURRENCE:
            table_name, table = t.COMPLEMENT_TABLE_BY_OCCURRENCE[code]
            comp = (values.get("instrucao_cancelada") or "").strip()
            if comp and comp != "0000":
                detail.message_codes.append(
                    {
                        "code": comp,
                        "table": table_name,
                        "description": table.get(comp, "CÓDIGO NÃO DOCUMENTADO"),
                    }
                )
            if code in ("24", "25"):
                comp_date = self._loose_date(
                    values.get("complemento_data"), "complemento_data", detail
                )
                if comp_date:
                    detail.extra["complement_date"] = comp_date.isoformat()
                raw_value = values.get("complemento_valor") or ""
                if raw_value.isdigit() and int(raw_value):
                    detail.extra["complement_value"] = str(Decimal(raw_value).scaleb(-2))
        self._check_nosso_numero_dac(detail)
        return detail

    def _check_nosso_numero_dac(self, detail: ReturnDetail) -> None:
        if not (
            detail.agency
            and detail.account
            and detail.wallet
            and detail.nosso_numero
            and detail.nosso_numero_dac
            and int(detail.nosso_numero)
        ):
            return
        expected = self.nosso_numero_dac(
            detail.agency, detail.account, detail.wallet, detail.nosso_numero
        )
        if expected != detail.nosso_numero_dac:
            detail.issues.append(
                Issue(
                    "NOSSO_NUMERO_DAC",
                    f"DAC do nosso número {detail.nosso_numero_dac} difere do calculado {expected}",
                    "warning",
                    field="dac_nosso_numero",
                    reference="Nota 23 p.34",
                )
            )

    @staticmethod
    def _loose_date(raw: object, name: str, detail: ReturnDetail) -> date | None:
        """Datas em campos X(06) (ex.: data de crédito): brancos/zeros = ausente."""
        text = str(raw or "").strip()
        if not text or text.strip("0") == "":
            return None
        try:
            value = _D6.parse(text.zfill(6))
        except FieldFormatError:
            detail.issues.append(
                Issue(
                    "FIELD_FORMAT",
                    f"Data inválida: {text!r}",
                    field=name,
                    line=detail.line_number,
                    reference="p.14",
                )
            )
            return None
        return value if isinstance(value, date) else None
