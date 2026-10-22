"""Aplicação de ocorrências de retorno aos títulos e conciliação financeira.

Independente do parser físico: recebe ``ReturnDetail`` já interpretado pelo adaptador.
Regra geral: na dúvida, registrar e pedir revisão — nunca presumir liquidação ou baixa.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application import audit
from app.cnab.base import BankLayoutAdapter, ReturnDetail
from app.cnab.occurrence_codes import OccurrenceEffect as E
from app.domain.enums import (
    MovementKind,
    OccurrenceStatus,
    ReconciliationStatus,
    TitleStatus,
)
from app.domain.errors import ConflictError, NotFoundError
from app.domain.services.title_state import can_transition
from app.infrastructure.database.base import utcnow
from app.infrastructure.database.models import (
    BankOccurrence,
    FinancialMovement,
    ReceivableTitle,
    ReconciliationResult,
)
from app.infrastructure.repositories import (
    find_profile_for_detail,
    find_title_by_nosso_numero,
    find_title_by_reference,
)

ZERO = Decimal("0.00")
_SUBMITTED = (TitleStatus.REMITTANCE_GENERATED, TitleStatus.SENT_TO_BANK)


@dataclass
class Outcome:
    status: OccurrenceStatus = OccurrenceStatus.INFORMATIONAL
    messages: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)

    def review(self, reason: str, message: str) -> None:
        self.status = OccurrenceStatus.REVIEW_REQUIRED
        self.reasons.append(reason)
        self.messages.append(message)

    def applied(self, message: str) -> None:
        if self.status is OccurrenceStatus.INFORMATIONAL:
            self.status = OccurrenceStatus.APPLIED
        self.messages.append(message)


def detail_snapshot(detail: ReturnDetail) -> dict[str, Any]:
    def s(value: object) -> object:
        if isinstance(value, (Decimal, date)):
            return str(value)
        return value

    keys = (
        "agency",
        "account",
        "account_dac",
        "wallet",
        "nosso_numero",
        "nosso_numero_dac",
        "company_reference",
        "document_number",
        "occurrence_date",
        "due_date",
        "credit_date",
        "amount",
        "fee_amount",
        "iof_amount",
        "rebate_amount",
        "discount_amount",
        "principal_amount",
        "interest_fine_amount",
        "other_credits",
        "payer_name",
        "liquidation_code",
        "accounting_flag",
        "informational_only",
    )
    data: dict[str, Any] = {k: s(getattr(detail, k)) for k in keys}
    data["message_codes"] = detail.message_codes
    data["issues"] = [i.as_dict() for i in detail.issues]
    data["extra"] = detail.extra
    return data


def apply_detail(
    session: Session,
    adapter: BankLayoutAdapter,
    bank_file_id: int,
    detail: ReturnDetail,
    idempotency_key: str,
    actor: str,
) -> BankOccurrence:
    info = detail.info
    occurrence = BankOccurrence(
        bank_file_id=bank_file_id,
        line_number=detail.line_number,
        raw_line=detail.raw_line,
        idempotency_key=idempotency_key,
        record_type=detail.record_type,
        occurrence_code=detail.occurrence_code,
        occurrence_description=info.description if info else None,
        effect=info.effect.value if info else None,
        occurrence_date=detail.occurrence_date,
        nosso_numero=detail.nosso_numero,
        company_reference=detail.company_reference,
        wallet=detail.wallet,
        amount=detail.amount,
        principal_amount=detail.principal_amount,
        fee_amount=detail.fee_amount,
        processing_status=OccurrenceStatus.INFORMATIONAL.value,
        parsed=detail_snapshot(detail),
    )
    session.add(occurrence)
    session.flush()  # dispara a restrição única de idempotência

    outcome = Outcome()
    title = _resolve(session, adapter, detail, occurrence, outcome)
    if title is None:
        if not detail.is_valid:
            outcome.status = OccurrenceStatus.INVALID
        elif info is not None and info.effect is E.FEE:
            # Débitos de tarifa (ex.: mensais) podem não ter título associado.
            _fee_movement(session, detail, occurrence, None)
            outcome.status = (
                OccurrenceStatus.APPLIED
                if detail.fee_amount > 0
                else OccurrenceStatus.INFORMATIONAL
            )
            outcome.messages = ["Tarifa sem título associado"]
        elif outcome.status is not OccurrenceStatus.INVALID:
            outcome.status = OccurrenceStatus.UNMATCHED
            _reconciliation(
                session,
                occurrence,
                None,
                ReconciliationStatus.UNMATCHED,
                outcome.reasons or ["TITLE_NOT_FOUND"],
            )
        _finish(occurrence, outcome)
        return occurrence

    occurrence.title_id = title.id
    if not detail.is_valid:
        outcome.status = OccurrenceStatus.INVALID
        outcome.messages.append("Registro com campos inválidos; nenhum efeito aplicado")
    elif info is None:
        outcome.status = OccurrenceStatus.UNKNOWN_CODE
        outcome.messages.append(f"Código {detail.occurrence_code} não documentado no manual")
    elif detail.extra.get("split_record"):
        outcome.review("SPLIT_UNSUPPORTED", "Registro de rateio não suportado")
    else:
        _apply_effect(session, title, detail, occurrence, outcome)
        _fee_movement(session, detail, occurrence, title)
    if (
        outcome.status is OccurrenceStatus.REVIEW_REQUIRED
        and not session.scalars(
            select(ReconciliationResult.id).where(
                ReconciliationResult.occurrence_id == occurrence.id
            )
        ).first()
    ):
        _reconciliation(session, occurrence, title, ReconciliationStatus.DIVERGENT, outcome.reasons)
    _finish(occurrence, outcome)
    session.flush()
    if outcome.status in (OccurrenceStatus.APPLIED, OccurrenceStatus.REVIEW_REQUIRED):
        audit.record(
            session,
            actor,
            "occurrence.apply",
            "title",
            title.id,
            {
                "occurrence_id": occurrence.id,
                "code": detail.occurrence_code,
                "status": outcome.status.value,
                "title_status": title.status,
            },
        )
    return occurrence


def _finish(occurrence: BankOccurrence, outcome: Outcome) -> None:
    occurrence.processing_status = outcome.status.value
    occurrence.message = "; ".join(outcome.messages) or None


def _resolve(
    session: Session,
    adapter: BankLayoutAdapter,
    detail: ReturnDetail,
    occurrence: BankOccurrence,
    outcome: Outcome,
) -> ReceivableTitle | None:
    if not (detail.agency and detail.account and detail.account_dac and detail.wallet):
        outcome.status = OccurrenceStatus.INVALID
        outcome.messages.append("Agência/conta/carteira ausentes ou inválidas")
        return None
    profile = find_profile_for_detail(
        session, adapter.bank_code, detail.agency, detail.account, detail.account_dac, detail.wallet
    )
    if profile is None:
        outcome.reasons.append("PROFILE_NOT_FOUND")
        outcome.messages.append("Conta/carteira sem perfil cadastrado")
        return None
    occurrence.profile_id = profile.id
    by_ref = by_nn = None
    if detail.company_reference:
        by_ref = find_title_by_reference(session, detail.company_reference)
        if by_ref is not None and by_ref.profile_id != profile.id:
            by_ref = None
    nn = detail.nosso_numero
    if nn and nn.isdigit() and int(nn):
        by_nn = find_title_by_nosso_numero(session, profile.id, nn)
    if by_ref and by_nn and by_ref.id != by_nn.id:
        outcome.review(
            "IDENTIFIER_CONFLICT",
            f"Uso da empresa aponta o título {by_ref.id}; nosso número, o {by_nn.id}",
        )
        return by_ref
    title = by_ref or by_nn
    if title is None:
        outcome.reasons.append("TITLE_NOT_FOUND")
        outcome.messages.append("Título não localizado por uso da empresa nem nosso número")
    return title


def _move(title: ReceivableTitle, target: TitleStatus, outcome: Outcome) -> bool:
    current = TitleStatus(title.status)
    if current is target:
        return True
    if not can_transition(current, target):
        outcome.review("INVALID_TRANSITION", f"Transição {current} -> {target} não permitida")
        return False
    title.status = target.value
    outcome.applied(f"Status {current} -> {target}")
    return True


def _apply_effect(
    session: Session,
    title: ReceivableTitle,
    detail: ReturnDetail,
    occurrence: BankOccurrence,
    outcome: Outcome,
) -> None:
    assert detail.info is not None
    effect = detail.info.effect
    current = TitleStatus(title.status)
    if detail.message_codes:
        title.last_bank_message = [
            {**m, "occurrence": detail.occurrence_code} for m in detail.message_codes
        ]

    if effect is E.ENTRY_CONFIRMED:
        if current in _SUBMITTED:
            _move(title, TitleStatus.REGISTERED, outcome)
        elif current is not TitleStatus.REGISTERED:
            outcome.review(
                "UNEXPECTED_CONFIRMATION", f"Confirmação de entrada com título {current}"
            )
        nn = detail.nosso_numero
        if nn and nn.isdigit() and int(nn):
            if title.nosso_numero is None:
                title.nosso_numero = nn
                title.nosso_numero_dac = detail.nosso_numero_dac
                outcome.applied(f"Nosso número {nn} atribuído pelo banco")
            elif title.nosso_numero != nn:
                outcome.review(
                    "NOSSO_NUMERO_CONFLICT",
                    f"Banco confirmou nosso número {nn}; título tem {title.nosso_numero}",
                )
    elif effect is E.ENTRY_REJECTED:
        if current in _SUBMITTED:
            _move(title, TitleStatus.REJECTED, outcome)
        else:
            outcome.review("UNEXPECTED_REJECTION", f"Rejeição de entrada com título {current}")
    elif effect is E.SETTLEMENT:
        _settlement(session, title, detail, occurrence, outcome)
    elif effect is E.PARTIAL_SETTLEMENT:
        if detail.informational_only:
            outcome.messages.append("Liquidação parcial informativa (posição 107 = I)")
            return
        _add_movement(
            session,
            occurrence,
            title,
            MovementKind.PARTIAL_SETTLEMENT,
            detail.principal_amount,
            detail,
        )
        _reconciliation(
            session,
            occurrence,
            title,
            ReconciliationStatus.DIVERGENT,
            ["PARTIAL_SETTLEMENT"],
            expected=title.amount,
            received=detail.principal_amount,
        )
        outcome.review("PARTIAL_SETTLEMENT", "Liquidação parcial registrada; revisar saldo")
    elif effect is E.WRITE_OFF:
        if current is TitleStatus.PAID:
            outcome.messages.append("Baixa informada para título já liquidado")
        elif current in (TitleStatus.REGISTERED, TitleStatus.CANCEL_REQUESTED):
            _move(title, TitleStatus.CANCELLED, outcome)
        elif current is not TitleStatus.CANCELLED:
            outcome.review("UNEXPECTED_WRITE_OFF", f"Baixa com título {current}")
    elif effect is E.WRITE_OFF_REJECTED:
        if current is TitleStatus.CANCEL_REQUESTED:
            _move(title, TitleStatus.REGISTERED, outcome)
        else:
            outcome.messages.append("Baixa rejeitada sem pedido de baixa pendente")
    elif effect is E.DUE_DATE_CHANGED:
        if detail.due_date and detail.due_date != title.due_date:
            outcome.applied(f"Vencimento {title.due_date} -> {detail.due_date}")
            title.due_date = detail.due_date
    elif effect is E.REVIEW_REQUIRED:
        outcome.review(f"CODE_{detail.occurrence_code}", detail.info.description)
    elif (
        effect is E.INFORMATIONAL
        and detail.occurrence_code == "10"
        and current is not (TitleStatus.PAID)
    ):
        outcome.review(
            "WRITE_OFF_BY_SETTLEMENT_WITHOUT_SETTLEMENT",
            "Baixa por liquidação sem liquidação registrada no sistema",
        )
    else:
        outcome.messages.append(detail.info.description)


def _settlement(
    session: Session,
    title: ReceivableTitle,
    detail: ReturnDetail,
    occurrence: BankOccurrence,
    outcome: Outcome,
) -> None:
    if detail.informational_only:
        # Indicador 23.2 = 2: a mesma liquidação vem como I (informativo) e C (contábil).
        outcome.messages.append("Liquidação informativa (posição 107 = I); sem lançamento")
        return
    current = TitleStatus(title.status)
    received = detail.principal_amount
    reasons: list[str] = []
    expected_net = (
        title.amount - detail.discount_amount - detail.rebate_amount + detail.interest_fine_amount
    )
    if detail.amount is not None and detail.amount != title.amount:
        reasons.append("NOMINAL_AMOUNT_MISMATCH")
    if received != expected_net:
        reasons.append("NET_AMOUNT_MISMATCH")
    if current is TitleStatus.PAID:
        reasons.append("DUPLICATE_SETTLEMENT")
    elif current is TitleStatus.CANCELLED:
        reasons.append("SETTLED_AFTER_WRITE_OFF")
    _add_movement(session, occurrence, title, MovementKind.SETTLEMENT, received, detail)
    if current is not TitleStatus.PAID:
        if _move(title, TitleStatus.PAID, outcome):
            title.paid_amount = received
            title.paid_at = detail.occurrence_date
            title.credit_date = detail.credit_date
        else:
            reasons.append("INVALID_TRANSITION")
    status = ReconciliationStatus.DIVERGENT if reasons else ReconciliationStatus.MATCHED
    _reconciliation(
        session, occurrence, title, status, reasons, expected=expected_net, received=received
    )
    if reasons:
        outcome.review(reasons[0], "Liquidação com divergência: " + ", ".join(reasons))
    else:
        outcome.applied(f"Liquidação de {received} conciliada")


def _add_movement(
    session: Session,
    occurrence: BankOccurrence,
    title: ReceivableTitle | None,
    kind: MovementKind,
    amount: Decimal,
    detail: ReturnDetail,
) -> None:
    session.add(
        FinancialMovement(
            occurrence_id=occurrence.id,
            title_id=title.id if title else None,
            kind=kind.value,
            amount=amount,
            movement_date=detail.occurrence_date,
            credit_date=detail.credit_date,
        )
    )


def _fee_movement(
    session: Session,
    detail: ReturnDetail,
    occurrence: BankOccurrence,
    title: ReceivableTitle | None,
) -> None:
    """Tarifa/custa informada nas posições 176-188 vira débito (uma vez por ocorrência)."""
    if detail.fee_amount > 0 and not detail.informational_only:
        _add_movement(session, occurrence, title, MovementKind.FEE, -detail.fee_amount, detail)


def _reconciliation(
    session: Session,
    occurrence: BankOccurrence,
    title: ReceivableTitle | None,
    status: ReconciliationStatus,
    reasons: list[str],
    expected: Decimal | None = None,
    received: Decimal | None = None,
) -> None:
    difference = received - expected if expected is not None and received is not None else None
    session.add(
        ReconciliationResult(
            occurrence_id=occurrence.id,
            title_id=title.id if title else None,
            status=status.value,
            expected_amount=expected,
            received_amount=received,
            difference=difference,
            reasons=reasons,
            resolved=status is ReconciliationStatus.MATCHED,
        )
    )
    session.flush()


def resolve(
    session: Session, reconciliation_id: int, note: str, actor: str
) -> ReconciliationResult:
    result = session.get(ReconciliationResult, reconciliation_id)
    if result is None:
        raise NotFoundError(f"Conciliação {reconciliation_id} não encontrada")
    if result.resolved:
        raise ConflictError("Conciliação já resolvida")
    result.resolved = True
    result.resolution_note = note
    result.resolved_by = actor
    audit.record(
        session,
        actor,
        "reconciliation.resolve",
        "reconciliation",
        result.id,
        {"at": utcnow().isoformat()},
    )
    session.flush()
    return result
