"""Case knowledge graph projection (#86): evidence on every edge, no inferred clinical edges."""

from kadi.graph import EntityRecord, PendingLink, StayInfo, build_case_graph


def _entities():
    return [
        EntityRecord(
            id="H1",
            name="Lifeline Multispeciality Hospital",
            type="hospital",
            meta={
                "source_file": "bill.txt",
                "mentions": [
                    {"name": "Lifeline Multispeciality Hospital", "source_file": "bill.txt"},
                    {"name": "लाइफलाइन मल्टीस्पेशालिटी हॉस्पिटल", "source_file": "abdm_import:1"},
                ],
            },
        ),
        EntityRecord(id="D1", name="Acute Appendicitis", type="diagnosis", meta={"source_file": "bill.txt"}),
        EntityRecord(id="D2", name="Appendicitis", type="diagnosis", meta={"source_file": "abdm_import:1"}),
        EntityRecord(id="P1", name="Appendectomy", type="procedure", meta={"source_file": "bill.txt"}),
        EntityRecord(id="B1", name="Appendectomy", type="billing_item", value="45000", meta={"source_file": "bill.txt"}),
        EntityRecord(id="B2", name="Appendectomy", type="billing_item", value="45000", meta={"source_file": "estimate.txt"}),
        EntityRecord(id="M1", name="Dolo 650", type="medicine", meta={"source_file": "rx.txt"}),
        EntityRecord(id="B3", name="Dolo 500", type="billing_item", value="30", meta={"source_file": "rx.txt"}),
        EntityRecord(id="T1", name="Document Text Excerpt", type="document_text", meta={"source_file": "bill.txt"}),
    ]


def _graph():
    return build_case_graph(
        StayInfo(case_id="CASE-1"),
        _entities(),
        pending=[PendingLink(decision_id="RES-1", mention_entity_id="D2", candidate_entity_id="D1", confidence=0.81)],
    )


def test_every_edge_carries_evidence():
    graph = _graph()
    assert graph.edges
    assert all(edge.evidence for edge in graph.edges)


def test_stay_is_linked_to_each_entity_with_unknown_dates_disclosed():
    graph = _graph()
    stay = graph.nodes[0]
    assert stay.kind == "hospital_stay"
    assert stay.attributes["dates_status"] == "UNKNOWN"
    relations = {(e.target, e.relation) for e in graph.edges if e.source == stay.id}
    assert ("H1", "AT_HOSPITAL") in relations
    assert ("D1", "RECORDED_DIAGNOSIS") in relations
    assert ("P1", "RECORDED_PROCEDURE") in relations
    assert ("M1", "RECORDED_MEDICINE") in relations


def test_document_text_is_not_a_graph_node():
    assert "T1" not in {n.id for n in _graph().nodes}


def test_billed_as_requires_same_document_and_no_conflict():
    billed = [(e.source, e.target) for e in _graph().edges if e.relation == "BILLED_AS"]
    assert billed == [("P1", "B1")]  # not B2 (other document), not B3 (650 vs 500)
    edge = next(e for e in _graph().edges if e.relation == "BILLED_AS")
    assert edge.evidence[0].kind == "name_match_same_document"
    assert edge.evidence[0].source_files == ["bill.txt"]


def test_pending_resolution_becomes_a_possibly_same_as_edge():
    [edge] = [e for e in _graph().edges if e.relation == "POSSIBLY_SAME_AS"]
    assert (edge.source, edge.target) == ("D2", "D1")
    assert edge.evidence[0].score == 0.81


def test_cross_script_aliases_are_attached_to_the_node():
    hospital = next(n for n in _graph().nodes if n.id == "H1")
    assert hospital.aliases == ["लाइफलाइन मल्टीस्पेशालिटी हॉस्पिटल"]
    assert hospital.source_files == ["bill.txt", "abdm_import:1"]


def test_no_clinical_relationships_are_inferred():
    allowed = {"AT_HOSPITAL", "RECORDED_DIAGNOSIS", "RECORDED_PROCEDURE", "RECORDED_MEDICINE", "BILLED_ITEM", "BILLED_AS", "POSSIBLY_SAME_AS"}
    graph = _graph()
    assert {e.relation for e in graph.edges} <= allowed
    assert any("No clinical relationships" in limitation for limitation in graph.limitations)


def test_stats_count_nodes_and_edges():
    graph = _graph()
    assert graph.stats["nodes"] == len(graph.nodes) == 9
    assert graph.stats["nodes.billing_item"] == 3
    assert graph.stats["edges.BILLED_AS"] == 1
