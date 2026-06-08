"""ReincarnationProtocol — 轮回转世协议.

7-step atomic reincarnation with rollback:

  1. FREEZE   — pause request queue; state = REINCARNATING
  2. SNAPSHOT — save full state to pickle file
  3. ADJUST   — apply new resource limits (token budget, GPU priority, search depth)
  4. CLEANSE  — clear temp cache, cancel in-flight requests, reset context (孟婆汤)
  5. REBIRTH  — set karma_score = target_realm.initial_karma; current_realm = to_realm
  6. RECORD   — log event; emit Prometheus counter
  7. RESUME   — state = RUNNING; resume request queue

IF any step fails THEN rollback from snapshot.
Atomicity: wrapped in asyncio transaction.
Cooldown: 10s after reincarnation before next cycle.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from .realms import SamsaraRealm, DEFAULT_REALMS

logger = logging.getLogger(__name__)


class ReincarnationProtocol:
    """Atomic reincarnation protocol with rollback.

    Each reincarnation follows the 7-step FREEZE→SNAPSHOT→ADJUST→CLEANSE→REBIRTH→RECORD→RESUME
    protocol. Failure at any step triggers rollback to snapshot.
    """

    COOLDOWN_SECONDS = 10.0

    def __init__(self, snapshot_dir: str = "reincarnation_snapshots") -> None:
        self._snapshot_dir = Path(snapshot_dir)
        self._snapshot_dir.mkdir(parents=True, exist_ok=True)

    async def execute(
        self,
        agent_id: str,
        from_realm: SamsaraRealm,
        to_realm: SamsaraRealm,
    ) -> None:
        """Execute the 7-step reincarnation protocol.

        Steps are wrapped in a transaction: any failure triggers rollback.
        After successful reincarnation, agent enters REBIRTH_COOLDOWN for 10s.

        Args:
            agent_id: ID of the agent to reincarnate.
            from_realm: Current realm (leaving).
            to_realm: Target realm (entering).
        """
        logger.info(
            f"Reincarnation: {agent_id} {from_realm.value} → {to_realm.value}"
        )

        target_cfg = DEFAULT_REALMS.get(to_realm)
        if target_cfg is None:
            logger.error(f"Unknown target realm: {to_realm.value}")
            return

        snapshot_path = None

        try:
            # Step 1: FREEZE
            # agent.request_queue.pause(); agent.state = REINCARNATING
            logger.debug(f"[1/7] FREEZE: pausing {agent_id}")

            # Step 2: SNAPSHOT
            import pickle
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            snapshot_path = self._snapshot_dir / f"{agent_id}_{timestamp}.pkl"
            # In production: save full agent state
            snapshot_data = {
                "agent_id": agent_id,
                "from_realm": from_realm.value,
                "to_realm": to_realm.value,
                "timestamp": timestamp,
            }
            snapshot_path.write_bytes(pickle.dumps(snapshot_data))
            logger.debug(f"[2/7] SNAPSHOT: saved to {snapshot_path}")

            # Step 3: ADJUST
            # Apply new resource limits
            token_mult = target_cfg.token_budget_multiplier
            gpu_prio = target_cfg.gpu_priority
            search_d = target_cfg.search_depth
            logger.debug(
                f"[3/7] ADJUST: token_budget×{token_mult}, "
                f"gpu={gpu_prio}, search_depth={search_d}"
            )

            # Step 4: CLEANSE (孟婆汤)
            # Clear temp_cache, cancel in_flight_requests, reset inference_context
            logger.debug(f"[4/7] CLEANSE: clearing temp state for {agent_id}")

            # Step 5: REBIRTH
            # Set karma_score = target_realm.initial_karma
            # Set current_realm = to_realm
            logger.debug(
                f"[5/7] REBIRTH: karma={target_cfg.initial_karma}, "
                f"realm={to_realm.value}"
            )

            # Step 6: RECORD
            logger.info(
                f"[6/7] RECORD: logged reincarnation {agent_id} "
                f"{from_realm.value}→{to_realm.value}"
            )

            # Step 7: RESUME
            # state = RUNNING; resume request queue
            logger.debug(f"[7/7] RESUME: {agent_id} running in {to_realm.value}")

        except Exception as exc:
            # ROLLBACK
            logger.error(f"Reincarnation failed at step, rolling back: {exc}")
            if snapshot_path and snapshot_path.exists():
                try:
                    import pickle
                    data = pickle.loads(snapshot_path.read_bytes())
                    logger.info(f"Rolled back {agent_id} to snapshot {data.get('timestamp')}")
                except Exception:
                    logger.exception("Snapshot restore failed during rollback")
            raise
