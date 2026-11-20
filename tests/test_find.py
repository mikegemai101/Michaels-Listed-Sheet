from app import db


def find(c, term, cols=("sku", "name", "category", "source_price", "listed", "inventory", "price", "status"), **q):
    r = c.post("/api/sheet/find", json={"term": term, "cols": list(cols), **q})
    assert r.status_code == 200, r.text
    return {sku: keys for sku, keys in r.json()["matches"]}


def test_find_reports_every_cell_that_contains_the_text(loaded):
    # names: Acrylic Paint Set 12 Pack, Wooden Frame 8 inch, No Weight Item, Not Amazon
    assert find(loaded, "wooden") == {"SKU-2": ["name"]}                      # ignores case
    assert find(loaded, "FRAME") == {"SKU-2": ["name"]}
    assert find(loaded, "no", cols=["name"]) == {"SKU-3": ["name"], "SKU-4": ["name"]}        # No Weight Item, Not Amazon
    assert find(loaded, "zzz-nothing") == {}
    assert find(loaded, "") == {} and find(loaded, "   ") == {}
    both = find(loaded, "SKU-1")
    assert both == {"SKU-1": ["sku"]}
    # text with a % or _ is searched as typed, not as a wildcard
    assert find(loaded, "%") == {} and find(loaded, "_") == {}


def test_find_matches_money_checkboxes_and_ignores_unknown_columns(loaded):
    db.conn().execute("UPDATE products SET source_price=169.7304 WHERE sku='SKU-1'")
    assert find(loaded, "169.73", cols=["source_price"]) == {"SKU-1": ["source_price"]}          # as it is shown: two decimals
    assert find(loaded, "$169.73", cols=["source_price"]) == {"SKU-1": ["source_price"]}
    db.conn().execute("UPDATE products SET inventory=1 WHERE sku IN ('SKU-1','SKU-2')")
    db.conn().execute("UPDATE products SET inventory=0 WHERE sku IN ('SKU-3','SKU-4')")
    assert set(find(loaded, "true", cols=["inventory"])) == {"SKU-1", "SKU-2"}
    assert set(find(loaded, "false", cols=["inventory"])) == {"SKU-3", "SKU-4"}
    assert find(loaded, "paint", cols=["not_a_column", "img"]) == {}                              # nothing to search in


def test_find_follows_the_filters_of_the_view(loaded):
    db.conn().execute("UPDATE products SET status='High Price', inventory=1 WHERE sku='SKU-1'")
    assert "SKU-1" in find(loaded, "1", cols=["sku"])
    assert find(loaded, "SKU", cols=["sku"], queue="High Price") == {"SKU-1": ["sku"]}           # only the rows of the open queue
    assert find(loaded, "SKU", cols=["sku"], q="Wooden") == {"SKU-2": ["sku"]}
