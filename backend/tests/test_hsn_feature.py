"""Backend tests for HSN/GST feature on stock items and Purchase Orders.

Covers:
  - GET  /api/admin/stock-items/hsn  (admin-only list with suggestions)
  - PUT  /api/admin/stock-items/hsn  (bulk update)
  - GET  /api/store/items            (hsn_code + mapped gst_rate)
  - POST /api/store/purchase-orders  (gst_rate derived from HSN; client override ignored)
"""
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "https://erp-conveyor.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = "test@test.com"
SALES_EMAIL = "sales@test.com"
PASSWORD = "test123"


def _login(email: str, password: str = PASSWORD) -> str:
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=20)
    assert r.status_code == 200, f"Login failed for {email}: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def admin_token():
    return _login(ADMIN_EMAIL)


@pytest.fixture(scope="module")
def sales_token():
    return _login(SALES_EMAIL)


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def sales_headers(sales_token):
    return {"Authorization": f"Bearer {sales_token}", "Content-Type": "application/json"}


# ---------- GET /api/admin/stock-items/hsn ----------

class TestHSNAdminList:
    def test_admin_can_list(self, admin_headers):
        r = requests.get(f"{BASE_URL}/api/admin/stock-items/hsn", headers=admin_headers, timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "items" in data and "suggestions" in data and "total" in data
        assert isinstance(data["items"], list) and len(data["items"]) > 0
        sample = data["items"][0]
        for k in ("id", "name", "category", "hsn_code"):
            assert k in sample, f"missing key {k} in {sample}"
        # gst_rate present (None when no HSN, else float)
        assert "gst_rate" in sample
        # suggestions shape
        assert isinstance(data["suggestions"], list) and len(data["suggestions"]) > 0
        s0 = data["suggestions"][0]
        assert "hsn" in s0 and "gst_rate" in s0

    def test_admin_list_bearing_has_hsn(self, admin_headers):
        r = requests.get(f"{BASE_URL}/api/admin/stock-items/hsn", headers=admin_headers, timeout=20)
        assert r.status_code == 200
        items = r.json()["items"]
        # Pre-seeded bearing id from the request context
        pre_seeded_id = "69e234e976aa33f380f53d20"
        match = next((it for it in items if it["id"] == pre_seeded_id), None)
        if match is not None:
            assert match.get("hsn_code") == "8482"
            assert match.get("gst_rate") == 18.0

    def test_non_admin_forbidden(self, sales_headers):
        r = requests.get(f"{BASE_URL}/api/admin/stock-items/hsn", headers=sales_headers, timeout=20)
        assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.text}"

    def test_unauthenticated_rejected(self):
        r = requests.get(f"{BASE_URL}/api/admin/stock-items/hsn", timeout=20)
        assert r.status_code in (401, 403)


# ---------- PUT /api/admin/stock-items/hsn ----------

class TestHSNBulkUpdate:
    def test_non_admin_forbidden(self, sales_headers):
        r = requests.put(
            f"{BASE_URL}/api/admin/stock-items/hsn",
            headers=sales_headers,
            json={"items": []},
            timeout=20,
        )
        assert r.status_code == 403

    def test_bulk_update_changes_value(self, admin_headers):
        # Pick an arbitrary item, flip its HSN to 7306 then back to 8483 (both map to 18%)
        listing = requests.get(f"{BASE_URL}/api/admin/stock-items/hsn", headers=admin_headers, timeout=20).json()
        assert listing["items"], "No stock items to test"
        target = listing["items"][0]
        target_id = target["id"]
        original_hsn = target.get("hsn_code") or ""

        # Update to 7306
        r1 = requests.put(
            f"{BASE_URL}/api/admin/stock-items/hsn",
            headers=admin_headers,
            json={"items": [{"id": target_id, "hsn_code": "7306"}]},
            timeout=20,
        )
        assert r1.status_code == 200, r1.text
        body = r1.json()
        assert body.get("updated") == 1
        assert body.get("total") == 1

        # Verify via GET
        listing2 = requests.get(f"{BASE_URL}/api/admin/stock-items/hsn", headers=admin_headers, timeout=20).json()
        updated_row = next(it for it in listing2["items"] if it["id"] == target_id)
        assert updated_row["hsn_code"] == "7306"
        assert updated_row["gst_rate"] == 18.0

        # Restore
        requests.put(
            f"{BASE_URL}/api/admin/stock-items/hsn",
            headers=admin_headers,
            json={"items": [{"id": target_id, "hsn_code": original_hsn}]},
            timeout=20,
        )

    def test_bulk_update_unknown_id_skipped(self, admin_headers):
        r = requests.put(
            f"{BASE_URL}/api/admin/stock-items/hsn",
            headers=admin_headers,
            json={"items": [{"id": f"nonexistent-{uuid.uuid4()}", "hsn_code": "8482"}]},
            timeout=20,
        )
        assert r.status_code == 200
        assert r.json().get("updated") == 0

    def test_bulk_update_multiple_items(self, admin_headers):
        listing = requests.get(f"{BASE_URL}/api/admin/stock-items/hsn", headers=admin_headers, timeout=20).json()
        items = listing["items"][:3]
        originals = [(it["id"], it.get("hsn_code") or "") for it in items]
        payload = {"items": [{"id": iid, "hsn_code": "7318"} for iid, _ in originals]}
        r = requests.put(f"{BASE_URL}/api/admin/stock-items/hsn", headers=admin_headers, json=payload, timeout=20)
        assert r.status_code == 200
        assert r.json().get("updated") == len(originals)
        # restore
        requests.put(
            f"{BASE_URL}/api/admin/stock-items/hsn",
            headers=admin_headers,
            json={"items": [{"id": iid, "hsn_code": h} for iid, h in originals]},
            timeout=20,
        )


# ---------- GET /api/store/items ----------

class TestStoreItemsEnrichment:
    def test_items_include_hsn_and_gst_rate(self, admin_headers):
        r = requests.get(f"{BASE_URL}/api/store/items", headers=admin_headers, timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        items = data.get("items") or data.get("stock_items") or data
        assert isinstance(items, list) and len(items) > 0
        for it in items[:20]:
            assert "hsn_code" in it
            assert "gst_rate" in it
            # If HSN set, gst_rate must be a float. If blank, must be None.
            if it["hsn_code"]:
                assert isinstance(it["gst_rate"], (int, float)), f"bad gst_rate type for {it}"
            else:
                assert it["gst_rate"] is None

    def test_bearing_item_mapped_18(self, admin_headers):
        r = requests.get(f"{BASE_URL}/api/store/items", headers=admin_headers, timeout=20)
        items = r.json().get("items") or r.json().get("stock_items") or r.json()
        bearing = next((it for it in items if it.get("id") == "69e234e976aa33f380f53d20"), None)
        if bearing is not None:
            assert bearing.get("hsn_code") == "8482"
            assert bearing.get("gst_rate") == 18.0


# ---------- POST /api/store/purchase-orders ----------

class TestPurchaseOrderHSNOverride:
    def _get_hsn_item_and_nohsn_item(self, admin_headers):
        r = requests.get(f"{BASE_URL}/api/store/items", headers=admin_headers, timeout=20)
        items = r.json().get("items") or r.json().get("stock_items") or r.json()
        with_hsn = next((it for it in items if it.get("hsn_code")), None)
        without_hsn = next((it for it in items if not it.get("hsn_code")), None)
        return with_hsn, without_hsn

    def _pick_supplier(self, admin_headers):
        r = requests.get(f"{BASE_URL}/api/store/suppliers", headers=admin_headers, timeout=20)
        if r.status_code != 200:
            # try generic suppliers
            r = requests.get(f"{BASE_URL}/api/suppliers", headers=admin_headers, timeout=20)
        assert r.status_code == 200, f"supplier list failed: {r.status_code} {r.text}"
        body = r.json()
        suppliers = body.get("suppliers") or body.get("items") or body
        assert isinstance(suppliers, list) and suppliers, "no suppliers configured"
        return suppliers[0]["id"]

    def test_po_gst_overridden_by_hsn(self, admin_headers):
        with_hsn, _ = self._get_hsn_item_and_nohsn_item(admin_headers)
        assert with_hsn is not None, "No stock item with HSN found - seed at least one"
        supplier_id = self._pick_supplier(admin_headers)
        payload = {
            "supplier_id": supplier_id,
            "interstate": False,
            "items": [
                {
                    "stock_item_id": with_hsn["id"],
                    "qty": 2,
                    "rate": 100,
                    "gst_rate": 5,   # deliberate wrong value; HSN must override to 18
                }
            ],
        }
        r = requests.post(f"{BASE_URL}/api/store/purchase-orders", headers=admin_headers, json=payload, timeout=20)
        assert r.status_code in (200, 201), r.text
        po = r.json()
        # Some endpoints wrap in {"purchase_order": {...}}
        po = po.get("purchase_order", po)
        lines = po.get("items") or []
        assert lines, f"PO has no lines: {po}"
        line = lines[0]
        assert line["hsn_code"] == with_hsn["hsn_code"], f"hsn not set on PO line: {line}"
        assert line["gst_rate"] == 18.0, f"gst_rate should be overridden by HSN mapping, got {line['gst_rate']}"
        # Amounts consistency
        assert line["amount"] == 200.0
        assert line["gst_amount"] == 36.0  # 18%
        assert line["total_line"] == 236.0

    def test_po_falls_back_when_hsn_missing(self, admin_headers):
        _, without_hsn = self._get_hsn_item_and_nohsn_item(admin_headers)
        if without_hsn is None:
            pytest.skip("All items have HSN — cannot test fallback")
        supplier_id = self._pick_supplier(admin_headers)
        payload = {
            "supplier_id": supplier_id,
            "interstate": False,
            "items": [
                {
                    "stock_item_id": without_hsn["id"],
                    "qty": 1,
                    "rate": 50,
                    "gst_rate": 12,   # client-supplied used when no HSN
                }
            ],
        }
        r = requests.post(f"{BASE_URL}/api/store/purchase-orders", headers=admin_headers, json=payload, timeout=20)
        assert r.status_code in (200, 201), r.text
        po = r.json().get("purchase_order", r.json())
        line = po["items"][0]
        assert line["hsn_code"] == ""
        assert line["gst_rate"] == 12.0, f"expected client-supplied 12%, got {line['gst_rate']}"
