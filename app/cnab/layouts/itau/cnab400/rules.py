"""Regras de validação de perfil e de títulos para o Itaú CNAB 400.

Cada ``Issue`` traz ``reference``: página/nota do manual (JANEIRO 2017) ou ``regra interna``.
"""

from __future__ import annotations

import re
from decimal import Decimal

from app.cnab.base import CollectionProfileData, PartyData, RemittanceItemData
from app.cnab.checksums import mod10
from app.cnab.fields import ALLOWED_ALPHA, normalize_text
from app.cnab.layouts.itau.cnab400 import tables as t
from app.domain.enums import FineType, RemittanceCommand
from app.domain.errors import Issue
from app.domain.value_objects import BRAZILIAN_STATES, is_valid_document

INTERNAL = "regra interna"
MAX_AMOUNT = Decimal(t.MAX_TITLE_AMOUNT_TEXT)
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _err(code: str, message: str, field: str, reference: str) -> Issue:
    return Issue(code=code, message=message, field=field, reference=reference)


def _cents_ok(value: Decimal) -> bool:
    return value == value.quantize(Decimal("0.01"))


def _text_ok(value: str) -> bool:
    return all(ch in ALLOWED_ALPHA for ch in normalize_text(value))


def validate_profile(profile: CollectionProfileData) -> list[Issue]:
    issues: list[Issue] = []
    if not (profile.agency.isdigit() and len(profile.agency) == 4):
        issues.append(_err("AGENCY", "Agência deve ter 4 dígitos", "agency", "p.7"))
    if not (profile.account.isdigit() and len(profile.account) == 5):
        issues.append(_err("ACCOUNT", "Conta deve ter 5 dígitos", "account", "p.7"))
    if not (profile.account_dac.isdigit() and len(profile.account_dac) == 1):
        issues.append(_err("ACCOUNT_DAC", "DAC deve ter 1 dígito", "account_dac", "p.7"))
    elif not issues and str(mod10(profile.agency + profile.account)) != profile.account_dac:
        issues.append(
            _err(
                "ACCOUNT_DAC_MISMATCH",
                "DAC não confere com agência/conta (módulo 10)",
                "account_dac",
                "p.49 (7.3.2, posição 41) e Anexo 3 p.55",
            )
        )
    name = normalize_text(profile.company_name)
    if not name or len(name) > 30 or not _text_ok(name):
        issues.append(
            _err(
                "COMPANY_NAME", "Nome da empresa: 1 a 30 caracteres válidos", "company_name", "p.7"
            )
        )
    if not is_valid_document(profile.company_document_type, profile.company_document):
        issues.append(
            _err(
                "COMPANY_DOCUMENT",
                "CPF/CNPJ do beneficiário inválido",
                "company_document",
                "Nota 1 p.18; dígitos: regra interna",
            )
        )
    wallet = t.WALLETS.get(profile.wallet)
    if wallet is None:
        issues.append(_err("WALLET", "Carteira não listada na Nota 5", "wallet", "Nota 5 p.18"))
    elif not wallet.supported:
        issues.append(_err("WALLET_UNSUPPORTED", wallet.reason, "wallet", "Nota 5 p.18"))
    else:
        lo, hi = profile.nosso_numero_min, profile.nosso_numero_max
        if wallet.requires_bank_range and (lo is None or hi is None):
            issues.append(
                _err(
                    "NOSSO_NUMERO_RANGE",
                    "Carteira exige faixa de nosso número definida pelo Itaú",
                    "nosso_numero_min",
                    "Nota 5 obs (D) p.18",
                )
            )
        if (lo is None) != (hi is None) or (
            lo is not None and hi is not None and not 1 <= lo <= hi <= 99_999_999
        ):
            issues.append(
                _err(
                    "NOSSO_NUMERO_RANGE",
                    "Faixa de nosso número inválida",
                    "nosso_numero_min",
                    INTERNAL,
                )
            )
        if wallet.nosso_numero_by_bank and lo is not None:
            issues.append(
                _err(
                    "NOSSO_NUMERO_RANGE",
                    "Carteira escritural: nosso número é atribuído pelo banco",
                    "nosso_numero_min",
                    "Nota 3 p.18",
                )
            )
    if profile.line_terminator not in ("CRLF", "LF"):
        issues.append(_err("LINE_TERMINATOR", "Use CRLF ou LF", "line_terminator", INTERNAL))
    return issues


def _validate_party(party: PartyData, prefix: str, name_max: int) -> list[Issue]:
    issues: list[Issue] = []
    name = normalize_text(party.name)
    if not name:
        issues.append(
            _err("NAME_REQUIRED", "Nome obrigatório", f"{prefix}.name", "Tabela 1 cód. 08 p.26")
        )
    elif len(name) > name_max or not _text_ok(name):
        issues.append(
            _err(
                "NAME", f"Nome: até {name_max} caracteres válidos", f"{prefix}.name", "Nota 15 p.23"
            )
        )
    if not is_valid_document(party.document_type, party.document):
        issues.append(
            _err(
                "DOCUMENT",
                "CPF/CNPJ inválido",
                f"{prefix}.document",
                "Tabela 1 cód. 37 p.26; dígitos: regra interna",
            )
        )
    if not normalize_text(party.street):
        issues.append(
            _err(
                "STREET_REQUIRED",
                "Logradouro obrigatório",
                f"{prefix}.street",
                "Tabela 1 cód. 10 p.26",
            )
        )
    if not (party.zip_code.isdigit() and len(party.zip_code) == 8 and int(party.zip_code) > 0):
        issues.append(
            _err(
                "ZIP_CODE", "CEP deve ter 8 dígitos", f"{prefix}.zip_code", "Tabela 1 cód. 11 p.26"
            )
        )
    if not normalize_text(party.city):
        issues.append(_err("CITY_REQUIRED", "Cidade obrigatória", f"{prefix}.city", INTERNAL))
    if party.state.upper() not in BRAZILIAN_STATES:
        issues.append(_err("STATE", "UF inválida", f"{prefix}.state", "Tabela 1 cód. 04 p.26"))
    for attr in ("street", "district", "city"):
        if not _text_ok(getattr(party, attr)):
            issues.append(
                _err("INVALID_CHARS", "Caracteres não permitidos", f"{prefix}.{attr}", "p.5")
            )
    return issues


def validate_item(profile: CollectionProfileData, item: RemittanceItemData) -> list[Issue]:
    wallet = t.WALLETS.get(profile.wallet)
    if wallet is None or not wallet.supported:
        return [
            _err("WALLET_UNSUPPORTED", "Carteira do perfil não suportada", "wallet", "Nota 5 p.18")
        ]
    issues: list[Issue] = []
    if item.amount <= 0 or not _cents_ok(item.amount):
        issues.append(
            _err("AMOUNT", "Valor deve ser positivo com até 2 casas", "amount", "Nota 8 p.20")
        )
    elif item.amount > MAX_AMOUNT:
        issues.append(
            _err("AMOUNT_MAX", "Valor maior que 10.000.000,00", "amount", "Tabela 1 cód. 07 p.26")
        )
    if item.command is not RemittanceCommand.REGISTER:
        if not (item.nosso_numero and item.nosso_numero.isdigit() and int(item.nosso_numero)):
            issues.append(
                _err(
                    "NOSSO_NUMERO_REQUIRED",
                    "Instrução exige nosso número (título confirmado pelo banco)",
                    "nosso_numero",
                    "Nota 3 p.18; Nota 6 obs (A) p.19",
                )
            )
        if item.command is RemittanceCommand.CHANGE_DUE_DATE and item.new_due_date is None:
            issues.append(
                _err(
                    "NEW_DUE_DATE",
                    "Nova data de vencimento obrigatória",
                    "new_due_date",
                    "Nota 6 p.19",
                )
            )
        return issues
    return issues + _validate_registration(profile, wallet, item)


def _validate_registration(
    profile: CollectionProfileData, wallet: t.Wallet, item: RemittanceItemData
) -> list[Issue]:
    issues: list[Issue] = []
    ref = item.company_reference
    if not ref or len(ref) > 25 or not _text_ok(ref):
        issues.append(
            _err(
                "COMPANY_REFERENCE",
                "Uso da empresa: 1 a 25 caracteres",
                "company_reference",
                "Nota 2 p.18",
            )
        )
    doc = normalize_text(item.document_number)
    if not doc or len(doc) > 10 or not _text_ok(doc):
        issues.append(
            _err(
                "DOCUMENT_NUMBER",
                "Nº do documento: 1 a 10 caracteres",
                "document_number",
                "Nota 18 p.25; Tabela 7 cód. 3491",
            )
        )
    if item.due_date < item.issue_date:
        issues.append(
            _err(
                "DUE_BEFORE_ISSUE",
                "Vencimento anterior à emissão",
                "due_date",
                "Tabela 7 cód. 3434 p.31; regra interna",
            )
        )
    for name, value in (("issue_date", item.issue_date), ("due_date", item.due_date)):
        if not 2000 <= value.year <= 2099:
            issues.append(_err("DATE_RANGE", "Ano fora de 2000-2099 (DDMMAA)", name, "p.8"))
    if item.species not in t.SPECIES:
        issues.append(_err("SPECIES", "Espécie não listada na Nota 10", "species", "Nota 10 p.20"))
    if item.acceptance not in ("A", "N"):
        issues.append(_err("ACCEPTANCE", "Aceite deve ser A ou N", "acceptance", "p.8"))

    issues += _validate_party(item.payer, "payer", 40)
    if item.guarantor is not None:
        issues += _validate_party(item.guarantor, "guarantor", 30)
    if item.payer_email is not None:
        if wallet.modality is not t.Modality.ESCRITURAL:
            issues.append(
                _err(
                    "EMAIL_WALLET",
                    "Envio por e-mail só para carteiras escriturais",
                    "payer.email",
                    "Nota 29 p.37",
                )
            )
        if (
            len(item.payer_email) > 120
            or not _EMAIL.match(item.payer_email)
            or not _text_ok(item.payer_email)
        ):
            issues.append(
                _err("EMAIL", "E-mail inválido (até 120 caracteres)", "payer.email", "Nota 29 p.37")
            )

    issues += _validate_nosso_numero(profile, wallet, item)
    issues += _validate_instructions(item)
    issues += _validate_charges(wallet, item)
    return issues


def _validate_nosso_numero(
    profile: CollectionProfileData, wallet: t.Wallet, item: RemittanceItemData
) -> list[Issue]:
    nn = item.nosso_numero
    if wallet.nosso_numero_by_bank:
        if nn is not None and int(nn or "0"):
            return [
                _err(
                    "NOSSO_NUMERO_BY_BANK",
                    "Carteira escritural: nosso número é enviado zerado e retornado pelo banco",
                    "nosso_numero",
                    "Nota 3 p.18",
                )
            ]
        return []
    if not (nn and nn.isdigit() and len(nn) <= 8 and int(nn) > 0):
        return [
            _err(
                "NOSSO_NUMERO_REQUIRED",
                "Nosso número de 1 a 8 dígitos obrigatório",
                "nosso_numero",
                "Nota 3 p.18",
            )
        ]
    lo, hi = profile.nosso_numero_min, profile.nosso_numero_max
    if lo is not None and hi is not None and not lo <= int(nn) <= hi:
        return [
            _err(
                "NOSSO_NUMERO_RANGE",
                "Nosso número fora da faixa do perfil",
                "nosso_numero",
                "Nota 5 obs (D) p.18; Tabela 1 cód. 42",
            )
        ]
    return []


def _validate_instructions(item: RemittanceItemData) -> list[Issue]:
    issues: list[Issue] = []
    codes = [c for c in (item.instruction1, item.instruction2) if c]
    if item.species == t.PROPOSAL_SPECIES and codes:
        issues.append(
            _err(
                "PROPOSAL_INSTRUCTIONS",
                "Boleto de proposta não aceita instruções",
                "instruction1",
                "Anexo 7 p.62",
            )
        )
    if len(codes) == 2 and codes[0] == codes[1]:
        issues.append(
            _err("INSTRUCTION_DUPLICATED", "Instruções repetidas", "instruction2", INTERNAL)
        )
    uses_days = False
    for index, code in enumerate(codes, start=1):
        instruction = t.INSTRUCTIONS.get(code)
        if instruction is None:
            issues.append(
                _err(
                    "INSTRUCTION",
                    f"Instrução {code} não listada na Nota 11",
                    f"instruction{index}",
                    "Nota 11 p.20-22",
                )
            )
            continue
        if not instruction.supported:
            issues.append(
                _err(
                    "INSTRUCTION_UNSUPPORTED",
                    f"Instrução {code} exige campos ainda não suportados ou é de uso do banco",
                    f"instruction{index}",
                    "Nota 11 p.20-22",
                )
            )
        uses_days = uses_days or instruction.uses_days
    if t.NEGATIVATION_INSTRUCTION in codes and t.PROTEST_INSTRUCTIONS & set(codes):
        issues.append(
            _err(
                "PROTEST_AND_NEGATIVATION",
                "Negativação e protesto simultâneos: o banco considera só a negativação",
                "instruction1",
                "Nota 11 obs (A) p.22",
            )
        )
    if item.protest_days is not None:
        if not 0 <= item.protest_days <= 99:
            issues.append(_err("DAYS", "Prazo entre 0 e 99 dias", "protest_days", "p.8"))
        elif item.protest_days and not uses_days:
            issues.append(
                _err(
                    "DAYS_WITHOUT_INSTRUCTION",
                    "Prazo informado sem instrução que o utilize",
                    "protest_days",
                    "Nota 11 obs (A) p.22",
                )
            )
    return issues


def _validate_charges(wallet: t.Wallet, item: RemittanceItemData) -> list[Issue]:
    issues: list[Issue] = []
    proposal = item.species == t.PROPOSAL_SPECIES
    for name in ("interest_per_day", "discount_amount", "rebate_amount", "iof_amount"):
        value: Decimal | None = getattr(item, name)
        if value is not None and (value < 0 or not _cents_ok(value)):
            issues.append(_err("MONEY", "Valor não negativo com até 2 casas", name, "p.5"))
    if item.interest_per_day and proposal:
        issues.append(
            _err(
                "PROPOSAL_INTEREST",
                "Boleto de proposta não admite juros",
                "interest_per_day",
                "Anexo 7 p.62",
            )
        )
    if item.interest_start_date and not item.interest_per_day:
        issues.append(
            _err(
                "INTEREST_DATE", "Data de mora sem valor de juros", "interest_start_date", INTERNAL
            )
        )
    if item.discount_amount:
        if item.discount_limit_date is None:
            issues.append(
                _err("DISCOUNT_DATE", "Desconto exige data limite", "discount_limit_date", "p.8")
            )
        elif item.discount_limit_date > item.due_date:
            issues.append(
                _err(
                    "DISCOUNT_DATE",
                    "Data limite do desconto após o vencimento",
                    "discount_limit_date",
                    INTERNAL,
                )
            )
        if item.discount_amount > item.amount * Decimal("0.9"):
            issues.append(
                _err(
                    "DISCOUNT_MAX",
                    "Desconto limitado a 90% do valor",
                    "discount_amount",
                    "Nota 13 p.22",
                )
            )
    elif item.discount_limit_date is not None:
        issues.append(
            _err(
                "DISCOUNT_DATE",
                "Data limite sem valor de desconto",
                "discount_limit_date",
                INTERNAL,
            )
        )
    if item.rebate_amount and item.rebate_amount >= item.amount:
        issues.append(
            _err(
                "REBATE",
                "Abatimento igual ou maior que o valor do título",
                "rebate_amount",
                "Tabela 3 cód. 10 p.28",
            )
        )
    if item.iof_amount:
        if "F" not in wallet.obs:
            issues.append(
                _err(
                    "IOF_WALLET",
                    "IOF de uso exclusivo de seguradoras (carteira 188)",
                    "iof_amount",
                    "Nota 14 p.22; Nota 5 obs (F)",
                )
            )
        if item.iof_amount > item.amount * Decimal("0.05"):
            issues.append(
                _err("IOF_MAX", "IOF maior que 5%", "iof_amount", "Tabela 1 cód. 35 p.26")
            )
    fine = item.fine
    if fine is not None:
        if proposal:
            issues.append(
                _err("PROPOSAL_FINE", "Boleto de proposta não admite multa", "fine", "Anexo 7 p.62")
            )
        if fine.start_date < item.due_date:
            issues.append(
                _err(
                    "FINE_DATE",
                    "Data da multa deve ser maior ou igual ao vencimento",
                    "fine.start_date",
                    "Nota 35 p.38",
                )
            )
        if fine.value <= 0 or not _cents_ok(fine.value):
            issues.append(
                _err("FINE_VALUE", "Multa positiva com até 2 casas", "fine.value", "Nota 35 p.38")
            )
        elif fine.type is FineType.FIXED and fine.value >= item.amount:
            issues.append(
                _err(
                    "FINE_VALUE",
                    "Multa igual ou maior que o valor do título",
                    "fine.value",
                    "Nota 35 p.39",
                )
            )
        elif fine.type is FineType.PERCENT and fine.value >= 100:
            issues.append(
                _err(
                    "FINE_VALUE",
                    "Percentual de multa igual ou maior que 100%",
                    "fine.value",
                    "Nota 35 p.39",
                )
            )
    return issues
