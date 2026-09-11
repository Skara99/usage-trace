from pathlib import Path

from common import load_profile
from enums import detect_enums, _parse_java_enums, _parse_python_enums, _parse_csharp_enums
from index import ProjectIndex
from render import render
from usage_trace import run

ROOT = Path(__file__).resolve().parent.parent
TMPL = ROOT / "templates" / "report.html.tmpl"
JAVA = ROOT / "tests" / "fixtures" / "java-spring"
PY = ROOT / "tests" / "fixtures" / "python-sqlalchemy"
PROFILES = ROOT / "profiles"


def test_parse_java_enum_with_code_and_label():
    text = Path(
        JAVA / "src/main/java/com/example/enums/OrderStatus.java"
    ).read_text(encoding="utf-8")
    groups = _parse_java_enums(text, "OrderStatus.java")
    enum = next(g for g in groups if g["name"] == "OrderStatus" and g["kind"] == "enum")
    by_name = {v["name"]: v for v in enum["values"]}
    assert by_name["PAID"]["value"] == "PAID"
    assert by_name["PAID"]["label"] == "已支付"
    assert set(by_name) == {"PAID", "CANCELLED", "PENDING"}


def test_parse_python_enum_members():
    text = Path(PY / "app/models/status.py").read_text(encoding="utf-8")
    groups = _parse_python_enums(text, "status.py")
    enum = groups[0]
    assert enum["name"] == "OrderStatus"
    assert {v["name"]: v["value"] for v in enum["values"]} == {
        "PAID": "paid",
        "CANCELLED": "cancelled",
        "PENDING": "pending",
    }


def test_parse_csharp_enum_members():
    groups = _parse_csharp_enums(
        "enum OrderStatus { Paid = 1, Cancelled, Pending = 3 }",
        "OrderStatus.cs",
    )
    assert groups[0]["name"] == "OrderStatus"
    values = {v["name"]: v["value"] for v in groups[0]["values"]}
    assert values["Paid"] == "1"
    assert values["Cancelled"] == "Cancelled"


def test_detect_status_enum_in_java_fixture():
    profile = load_profile("java-spring", PROFILES)
    idx = ProjectIndex()
    idx.build(JAVA, profile)
    groups = detect_enums("status", JAVA, idx)
    names = {g["name"] for g in groups}
    assert "OrderStatus" in names
    paid = next(v for g in groups if g["name"] == "OrderStatus" for v in g["values"] if v["name"] == "PAID")
    assert paid["label"] == "已支付"


def test_store_no_does_not_pick_order_status():
    profile = load_profile("java-spring", PROFILES)
    idx = ProjectIndex()
    idx.build(JAVA, profile)
    groups = detect_enums("storeNo", JAVA, idx)
    assert all(g["name"] != "OrderStatus" for g in groups)


def test_run_status_writes_enums_into_html_and_chain(tmp_path):
    out = tmp_path / "status-report.html"
    chain = tmp_path / "status-chain.json"
    graph = run("status", JAVA, out=out, json_out=chain)
    names = {g["name"] for g in graph.get("field_enums") or []}
    assert "OrderStatus" in names
    html = out.read_text(encoding="utf-8")
    assert "枚举 / 固定取值" in html
    assert "已支付" in html
    assert "PENDING" in html
    payload = __import__("json").loads(chain.read_text(encoding="utf-8"))
    assert payload["counts"]["field_enums"] >= 1


def test_render_includes_enum_panel_and_resizers():
    from common import new_graph, add_node
    from graph import prune_and_layout

    g = new_graph({})
    add_node(g, {"kind": "unit", "label": "OrderService.setStatus", "layer": "Service"})
    g["field_enums"] = [{
        "name": "OrderStatus",
        "kind": "enum",
        "file": "OrderStatus.java",
        "values": [
            {"name": "PAID", "value": "PAID", "label": "已支付"},
            {"name": "CANCELLED", "value": "CANCELLED", "label": "已取消"},
        ],
    }]
    prune_and_layout(g, 50, ["Service"])
    html = render(g, "status", {"project": "demo", "language": "java-spring"}, TMPL)
    assert "枚举 / 固定取值" in html
    assert "已支付" in html
    assert 'id="resize-left"' in html
    assert 'id="resize-right"' in html
    assert "--right-w" in html
    assert "bindResizer" in html


def test_status_enum_lists_usage_scenarios(tmp_path):
    graph = run("status", JAVA, out=tmp_path / "s.html", json_out=tmp_path / "s.json")
    enum = next(g for g in graph["field_enums"] if g["name"] == "OrderStatus")
    paid = next(v for v in enum["values"] if v["name"] == "PAID")
    assert paid["label"] == "已支付"
    assert paid["usages"]
    assert any("markPaid" in (u.get("method") or "") for u in paid["usages"])
    assert any(u.get("trigger") for u in paid["usages"])
    html = (tmp_path / "s.html").read_text(encoding="utf-8")
    assert "使用场景" in html
    assert "如何触发" in html
    assert "支付成功后把订单标为已支付" in html


def test_store_no_chain_has_chinese_and_scenario(tmp_path):
    graph = run("storeNo", JAVA, out=tmp_path / "o.html", json_out=tmp_path / "o.json")
    ctrl = next(n for n in graph["nodes"] if n.get("id") == "OrderController.queryByStoreNo")
    assert ctrl.get("title_zh") == "按门店查询订单"
    assert "GET" in (ctrl.get("api") or "")
    assert graph.get("scenarios")
    html = (tmp_path / "o.html").read_text(encoding="utf-8")
    assert "按门店查询订单" in html
    assert "链路场景" in html
    assert "这条链路做什么" in html
