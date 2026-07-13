from __future__ import annotations

def record_search_result(
    query: str,
    db: str,
    result_count: int,
    useful: bool = True,
    feedback_file: str | Path | None = None,
):
    """记录搜索反馈到日志文件, 供 emerge_domains 使用。"""
    fb_path = Path(feedback_file) if feedback_file else (
        Path.cwd() / "logs" / "catalog_feedback.jsonl"
    )
    fb_path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "ts": datetime.now().isoformat(),
        "query": query,
        "db": db,
        "result_count": result_count,
        "useful": useful,
    }
    with open(fb_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def emerge_domains(
    catalog: dict,
    feedback_file: str | Path | None = None,
) -> list[dict]:
    """自组织领域发现 — 分析反馈日志, 发现跨领域DB聚类。

    工作原理:
      1. 将反馈按查询分组 → 找出哪些DB共同出现
      2. 聚类共同出现的DB → 候选领域
      3. 从成功查询中提取共享触发词
      4. 返回带置信度的建议
    """
    fb_path = Path(feedback_file) if feedback_file else (
        Path.cwd() / "logs" / "catalog_feedback.jsonl"
    )
    if not fb_path.exists():
        return []

    # Step 1: 构建 query→DBs 映射
    query_dbs: dict[str, set] = defaultdict(set)
    query_success: dict[str, bool] = {}
    with open(fb_path, encoding="utf-8") as f:
        for line in f:
            try:
                r = json.loads(line.strip())
                q = r["query"]
                query_dbs[q].add(r["db"])
                if r.get("useful"):
                    query_success[q] = True
            except (json.JSONDecodeError, KeyError):
                continue

    if len(query_dbs) < 3:
        return []

    # Step 2: 计算 DB 共现
    db_cooccurrence: dict[tuple[str, str], int] = defaultdict(int)
    for dbs in query_dbs.values():
        db_list = sorted(dbs)
        for i in range(len(db_list)):
            for j in range(i + 1, len(db_list)):
                db_cooccurrence[(db_list[i], db_list[j])] += 1

    # Step 3: 聚类 (简单阈值)
    suggestions: list[dict] = []
    cluster_queries = [q for q, dbs in query_dbs.items() if len(dbs) >= 2]

    for (dom_a, dom_b), count in sorted(
        db_cooccurrence.items(), key=lambda x: -x[1]
    ):
        if count >= 2:  # 至少 2 次共现
            triggers = [
                q for q in cluster_queries
                if dom_a in query_dbs[q] and dom_b in query_dbs[q]
            ][:5]
            dom_a_repr = next(
                (k for k in query_dbs if dom_a in query_dbs[k]),
                dom_a,
            )
            dom_b_repr = next(
                (k for k in query_dbs if dom_b in query_dbs[k]),
                dom_b,
            )
            dom_a_label = catalog.get("domains", {}).get(dom_a_repr, {}).get("label", dom_a_repr)
            dom_b_label = catalog.get("domains", {}).get(dom_b_repr, {}).get("label", dom_b_repr)
            suggestions.append({
                "label": f"{dom_a_label}×{dom_b_label}",
                "triggers": triggers,
                "databases": list({dom_a, dom_b}),
                "confidence": min(1.0, count / 3),
                "evidence": f"{count}次共现于{len(cluster_queries)}次查询",
            })

    return suggestions


# ═══════════════════════════════════════════════════════════
# Part 6: 递归思考框架 (Recursive Thinker)
# 参考: Tiny Recursive Model (Jolicoeur-Martineau 2025)
# ═══════════════════════════════════════════════════════════
