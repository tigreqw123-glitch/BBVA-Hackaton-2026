"""Estrategia de despacho por lotes para LOG-8092."""

from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime
from typing import Deque, Dict, Optional, Tuple

from interfaces import (
    BaseDispatcherStrategy,
    CarrierService,
    CarrierSnapshot,
    DeliveryAttemptResult,
    DispatchContext,
    FleetUpgradeDecision,
    MonthlyPlanningContext,
    Shipment,
)


class CandidateStrategy(BaseDispatcherStrategy):
    """Despacha lotes válidos y reintenta sin fijar un carrier inadecuado."""

    def __init__(self, carrier_service: CarrierService) -> None:
        super().__init__(carrier_service)
        self.pending: Deque[Shipment] = deque()
        self.last_carrier_by_shipment: Dict[str, str] = {}
        self.defer_until: Dict[str, datetime] = {}
        self.carriers: Tuple[CarrierSnapshot, ...] = ()

    def on_shipments_available(
        self, now: datetime, shipments: Tuple[Shipment, ...]
    ) -> None:
        del now
        self.pending.extend(shipments)

    def on_dispatch_tick(self, context: DispatchContext) -> None:
        self.carriers = context.carriers
        ready: list[Shipment] = []
        waiting: Deque[Shipment] = deque()
        while self.pending:
            shipment = self.pending.popleft()
            if shipment.ready_at > context.now:
                waiting.append(shipment)
            elif self.defer_until.get(shipment.shipment_id, context.now) > context.now:
                waiting.append(shipment)
            else:
                ready.append(shipment)

        groups: dict[tuple[str, str, int], list[Shipment]] = defaultdict(list)
        for shipment in ready:
            groups[
                (shipment.delivery_cluster_id, shipment.zone, shipment.attempt_number)
            ].append(shipment)

        ordered_groups = sorted(
            groups.values(), key=lambda group: min(item.sla_deadline for item in group)
        )
        for group in ordered_groups:
            remaining = list(sorted(group, key=lambda item: item.shipment_id))
            excluded_carrier_id: Optional[str] = None
            while remaining:
                self.carriers = self.carrier_service.snapshot()
                carrier = self._select_carrier(remaining, excluded_carrier_id)
                if carrier is None:
                    break

                compatible = [
                    item for item in remaining if self._supports(carrier, item)
                ]
                batch = tuple(compatible[: carrier.batch_capacity])
                if not batch:
                    break

                receipt = self.carrier_service.dispatch_batch(
                    carrier.carrier_id, tuple(item.shipment_id for item in batch)
                )
                if not receipt.accepted:
                    self.carriers = self.carrier_service.snapshot()
                    excluded_carrier_id = carrier.carrier_id
                    continue

                dispatched_ids = {item.shipment_id for item in batch}
                for item in batch:
                    self.last_carrier_by_shipment[item.shipment_id] = carrier.carrier_id
                remaining = [
                    item for item in remaining if item.shipment_id not in dispatched_ids
                ]
                excluded_carrier_id = None

            waiting.extend(remaining)

        self.pending = waiting

    def on_delivery_succeeded(self, result: DeliveryAttemptResult) -> None:
        shipment_id = result.shipment.shipment_id
        self.last_carrier_by_shipment.pop(shipment_id, None)
        self.defer_until.pop(shipment_id, None)

    def on_delivery_failed(self, result: DeliveryAttemptResult) -> None:
        shipment_id = result.shipment.shipment_id
        self.last_carrier_by_shipment.pop(shipment_id, None)
        self.defer_until.pop(shipment_id, None)
        if not result.terminal:
            self.pending.append(result.shipment)

    def on_monthly_planning(
        self, context: MonthlyPlanningContext
    ) -> Tuple[FleetUpgradeDecision, ...]:
        self.carriers = context.carriers
        return ()

    @staticmethod
    def _supports(carrier: CarrierSnapshot, shipment: Shipment) -> bool:
        return (
            carrier.available_units > 0
            and carrier.operates_now
            and shipment.zone in carrier.allowed_zones
            and all(
                capability in carrier.capabilities
                for capability in shipment.required_capabilities
            )
        )

    def _select_carrier(
        self,
        shipments: list[Shipment],
        excluded_carrier_id: Optional[str] = None,
    ) -> Optional[CarrierSnapshot]:
        candidates = [
            carrier
            for carrier in self.carriers
            if carrier.carrier_id != excluded_carrier_id
            and any(self._supports(carrier, shipment) for shipment in shipments)
        ]
        if not candidates:
            return None

        preferred_ids = {
            self.last_carrier_by_shipment.get(shipment.shipment_id)
            for shipment in shipments
        }
        return max(
            candidates,
            key=lambda carrier: (
                carrier.carrier_id in preferred_ids,
                carrier.speed_kmh * carrier.speed_multiplier_bps,
                carrier.batch_capacity,
                -carrier.base_fee_cents,
            ),
        )
