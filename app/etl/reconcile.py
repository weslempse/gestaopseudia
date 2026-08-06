from sqlalchemy import text
from app.db import models

# reconcile fast aggregates vs sisab_counts

def reconcile_period(period):
    with models.engine.begin() as conn:
        # fast aggregates
        fast_agg_q = text("""
            SELECT inep, item_code, COUNT(*) AS fast_count
            FROM fast_actions
            WHERE period = :period
            GROUP BY inep, item_code
        """)
        fast = conn.execute(fast_agg_q, {"period": period}).fetchall()
        # load sisab
        sisab_q = text("SELECT inep, item_code, count FROM sisab_counts WHERE period = :period")
        sisab = conn.execute(sisab_q, {"period": period}).fetchall()
        # convert to dicts
        fast_map = {(r['inep'], r['item_code']): r['fast_count'] for r in fast}
        sisab_map = {(r['inep'], r['item_code']): r['count'] for r in sisab}

        keys = set(fast_map.keys()) | set(sisab_map.keys())
        diffs = []
        for k in keys:
            f = fast_map.get(k, 0)
            s = sisab_map.get(k, 0)
            diffs.append({
                'inep': k[0],
                'item_code': k[1],
                'fast_count': f,
                'sisab_count': s,
                'diff': f - s
            })
    return diffs
