"""Controlled vocabularies used by the classifier, the database and the dashboard.

Root causes are an internal, network-agnostic taxonomy. Each one maps to the
closest Visa (VCR) and Mastercard chargeback reason code. The mapping is
*indicative* - a real chargeback team chooses the final code with transaction
data (entry mode, auth, etc.) that a CFPB narrative does not contain.
"""
from enum import Enum


class RootCause(str, Enum):
    UNAUTHORIZED_CARD_NOT_PRESENT = "unauthorized_card_not_present"
    UNAUTHORIZED_CARD_PRESENT = "unauthorized_card_present"
    ACCOUNT_TAKEOVER = "account_takeover"
    MERCHANDISE_NOT_RECEIVED = "merchandise_not_received"
    NOT_AS_DESCRIBED = "not_as_described_or_defective"
    CREDIT_NOT_PROCESSED = "credit_not_processed"
    CANCELLED_RECURRING = "cancelled_recurring"
    DUPLICATE_PROCESSING = "duplicate_processing"
    INCORRECT_AMOUNT = "incorrect_amount"
    PAID_BY_OTHER_MEANS = "paid_by_other_means"
    DISPUTE_PROCESS_FAILURE = "issuer_dispute_process_failure"
    OTHER = "other"


class Priority(str, Enum):
    P1 = "P1"  # regulatory / fraud-in-progress / large loss / vulnerable consumer
    P2 = "P2"  # clear chargeback right, money owed, standard SLA
    P3 = "P3"  # low value, informational, or already resolved


# root cause -> (Visa reason code, Mastercard reason code, human label)
REASON_CODES: dict[RootCause, tuple[str, str, str]] = {
    RootCause.UNAUTHORIZED_CARD_NOT_PRESENT: ("10.4", "4837", "Other Fraud - Card-Absent"),
    RootCause.UNAUTHORIZED_CARD_PRESENT: ("10.3", "4837", "Other Fraud - Card-Present"),
    RootCause.ACCOUNT_TAKEOVER: ("10.4", "4837", "Fraud - Account Takeover"),
    RootCause.MERCHANDISE_NOT_RECEIVED: ("13.1", "4853", "Merchandise/Services Not Received"),
    RootCause.NOT_AS_DESCRIBED: ("13.3", "4853", "Not as Described or Defective"),
    RootCause.CREDIT_NOT_PROCESSED: ("13.6", "4853", "Credit Not Processed"),
    RootCause.CANCELLED_RECURRING: ("13.2", "4841", "Cancelled Recurring Transaction"),
    RootCause.DUPLICATE_PROCESSING: ("12.6.1", "4834", "Duplicate Processing"),
    RootCause.INCORRECT_AMOUNT: ("12.5", "4834", "Incorrect Amount"),
    RootCause.PAID_BY_OTHER_MEANS: ("12.6.2", "4834", "Paid by Other Means"),
    RootCause.DISPUTE_PROCESS_FAILURE: ("N/A", "N/A", "Issuer handling (Reg Z / Reg E) - no chargeback"),
    RootCause.OTHER: ("N/A", "N/A", "Unclassified"),
}

ROOT_CAUSE_DESCRIPTIONS: dict[RootCause, str] = {
    RootCause.UNAUTHORIZED_CARD_NOT_PRESENT: "Consumer did not make an online/phone/in-app charge; card details stolen or used remotely.",
    RootCause.UNAUTHORIZED_CARD_PRESENT: "Consumer did not make an in-person charge; lost/stolen/skimmed physical card.",
    RootCause.ACCOUNT_TAKEOVER: "Fraudster took over the account (changed contact info, added user, new card issued) or new account opened in consumer's name.",
    RootCause.MERCHANDISE_NOT_RECEIVED: "Consumer authorized the purchase but goods/services never arrived or were never provided.",
    RootCause.NOT_AS_DESCRIBED: "Goods/services received but defective, counterfeit, or materially different from description.",
    RootCause.CREDIT_NOT_PROCESSED: "Merchant promised a refund/return credit that never posted.",
    RootCause.CANCELLED_RECURRING: "Subscription/recurring charge continued after the consumer cancelled.",
    RootCause.DUPLICATE_PROCESSING: "Same transaction posted more than once.",
    RootCause.INCORRECT_AMOUNT: "Charged amount differs from the agreed amount.",
    RootCause.PAID_BY_OTHER_MEANS: "Consumer paid the merchant by another method but the card was also charged.",
    RootCause.DISPUTE_PROCESS_FAILURE: "Main grievance is the issuer's handling of a dispute (ignored, denied without investigation, provisional credit reversed, missed Reg Z/Reg E timelines).",
    RootCause.OTHER: "Not a card transaction dispute or fraud complaint (fees, rates, credit reporting, etc.).",
}

FRAUD_ROOT_CAUSES = {
    RootCause.UNAUTHORIZED_CARD_NOT_PRESENT,
    RootCause.UNAUTHORIZED_CARD_PRESENT,
    RootCause.ACCOUNT_TAKEOVER,
}


def reason_codes_for(root_cause: RootCause) -> dict[str, str]:
    visa, mc, label = REASON_CODES[root_cause]
    return {"visa_reason_code": visa, "mastercard_reason_code": mc, "reason_code_label": label}
