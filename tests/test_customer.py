"""Tests for customer management service."""

import pytest

from app.services.customer import CustomerData, CustomerManager, InteractionData


@pytest.fixture
def mgr():
    return CustomerManager()


@pytest.fixture
def mgr_with_customers(mgr):
    mgr.create_customer(CustomerData(email="alice@example.com", name="Alice", country="US", city="NYC"))
    mgr.create_customer(CustomerData(email="bob@example.com", name="Bob", country="CN", tier="vip"))
    mgr.create_customer(CustomerData(email="charlie@example.com", name="Charlie", country="DE"))
    return mgr


class TestCustomerCRUD:
    def test_create_customer(self, mgr):
        c = mgr.create_customer(CustomerData(email="test@example.com", name="Test"))
        assert c["email"] == "test@example.com"
        assert c["name"] == "Test"
        assert c["tier"] == "regular"
        assert c["id"] is not None

    def test_create_all_fields(self, mgr):
        c = mgr.create_customer(CustomerData(
            email="full@example.com", name="Full User", phone="+1234",
            country="US", city="LA", address="123 Main",
            tier="wholesale", tags=["bulk"], platform_ids={"amazon": "A123"},
            notes="Important",
        ))
        assert c["tier"] == "wholesale"
        assert c["tags"] == ["bulk"]
        assert c["platform_ids"]["amazon"] == "A123"

    def test_create_invalid_tier(self, mgr):
        with pytest.raises(ValueError, match="Invalid tier"):
            mgr.create_customer(CustomerData(email="x@x.com", tier="gold"))

    def test_create_empty_email(self, mgr):
        with pytest.raises(ValueError, match="Email"):
            mgr.create_customer(CustomerData(email=""))

    def test_update_existing(self, mgr):
        mgr.create_customer(CustomerData(email="test@example.com", name="Old"))
        c = mgr.create_customer(CustomerData(email="test@example.com", name="New", tags=["updated"]))
        assert c["name"] == "New"
        assert "updated" in c["tags"]

    def test_get_customer(self, mgr_with_customers):
        c = mgr_with_customers.get_customer("alice@example.com")
        assert c is not None
        assert c["name"] == "Alice"

    def test_get_nonexistent(self, mgr):
        assert mgr.get_customer("nope@nope.com") is None

    def test_get_by_id(self, mgr):
        c = mgr.create_customer(CustomerData(email="test@example.com"))
        found = mgr.get_customer_by_id(c["id"])
        assert found["email"] == "test@example.com"

    def test_get_by_id_nonexistent(self, mgr):
        assert mgr.get_customer_by_id("no-such-id") is None

    def test_deactivate(self, mgr_with_customers):
        assert mgr_with_customers.deactivate_customer("alice@example.com")
        c = mgr_with_customers.get_customer("alice@example.com")
        assert c["is_active"] is False

    def test_deactivate_nonexistent(self, mgr):
        assert not mgr.deactivate_customer("nope@nope.com")


class TestTierAndTags:
    def test_set_tier(self, mgr_with_customers):
        c = mgr_with_customers.set_tier("alice@example.com", "vip")
        assert c["tier"] == "vip"

    def test_set_invalid_tier(self, mgr_with_customers):
        with pytest.raises(ValueError, match="Invalid tier"):
            mgr_with_customers.set_tier("alice@example.com", "gold")

    def test_set_tier_nonexistent(self, mgr):
        with pytest.raises(ValueError, match="not found"):
            mgr.set_tier("nope@nope.com", "vip")

    def test_add_tags(self, mgr_with_customers):
        c = mgr_with_customers.add_tags("alice@example.com", ["repeat", "loyal"])
        assert "repeat" in c["tags"]
        assert "loyal" in c["tags"]

    def test_add_tags_deduplicate(self, mgr_with_customers):
        mgr_with_customers.add_tags("alice@example.com", ["tag1"])
        c = mgr_with_customers.add_tags("alice@example.com", ["tag1", "tag2"])
        assert c["tags"].count("tag1") == 1

    def test_add_tags_nonexistent(self, mgr):
        with pytest.raises(ValueError, match="not found"):
            mgr.add_tags("nope@nope.com", ["tag"])


class TestOrderTracking:
    def test_record_order(self, mgr_with_customers):
        c = mgr_with_customers.record_order("alice@example.com", 49.99)
        assert c["total_orders"] == 1
        assert c["total_spent"] == 49.99
        assert c["avg_order_value"] == 49.99
        assert c["first_order_at"] is not None

    def test_multiple_orders(self, mgr_with_customers):
        mgr_with_customers.record_order("alice@example.com", 20.0)
        c = mgr_with_customers.record_order("alice@example.com", 30.0)
        assert c["total_orders"] == 2
        assert c["total_spent"] == 50.0
        assert c["avg_order_value"] == 25.0

    def test_auto_vip_upgrade_by_orders(self, mgr_with_customers):
        for i in range(10):
            mgr_with_customers.record_order("alice@example.com", 10.0)
        c = mgr_with_customers.get_customer("alice@example.com")
        assert c["tier"] == "vip"
        assert "auto_upgraded" in c["tags"]

    def test_auto_vip_upgrade_by_spend(self, mgr_with_customers):
        mgr_with_customers.record_order("alice@example.com", 1000.0)
        c = mgr_with_customers.get_customer("alice@example.com")
        assert c["tier"] == "vip"

    def test_no_downgrade_from_vip(self, mgr_with_customers):
        # Bob is already VIP
        mgr_with_customers.record_order("bob@example.com", 1.0)
        c = mgr_with_customers.get_customer("bob@example.com")
        assert c["tier"] == "vip"

    def test_record_return(self, mgr_with_customers):
        c = mgr_with_customers.record_return("alice@example.com")
        assert c["total_returns"] == 1

    def test_record_order_nonexistent(self, mgr):
        with pytest.raises(ValueError, match="not found"):
            mgr.record_order("nope@nope.com", 10.0)


class TestListAndSearch:
    def test_list_all(self, mgr_with_customers):
        assert len(mgr_with_customers.list_customers()) == 3

    def test_list_by_tier(self, mgr_with_customers):
        vips = mgr_with_customers.list_customers(tier="vip")
        assert len(vips) == 1
        assert vips[0]["name"] == "Bob"

    def test_list_by_country(self, mgr_with_customers):
        us = mgr_with_customers.list_customers(country="US")
        assert len(us) == 1

    def test_list_active_only(self, mgr_with_customers):
        mgr_with_customers.deactivate_customer("alice@example.com")
        active = mgr_with_customers.list_customers(active_only=True)
        assert len(active) == 2

    def test_list_by_tag(self, mgr_with_customers):
        mgr_with_customers.add_tags("alice@example.com", ["vip_candidate"])
        result = mgr_with_customers.list_customers(tag="vip_candidate")
        assert len(result) == 1

    def test_list_min_orders(self, mgr_with_customers):
        mgr_with_customers.record_order("alice@example.com", 50.0)
        result = mgr_with_customers.list_customers(min_orders=1)
        assert len(result) == 1

    def test_list_sort_by(self, mgr_with_customers):
        mgr_with_customers.record_order("alice@example.com", 100.0)
        mgr_with_customers.record_order("charlie@example.com", 200.0)
        result = mgr_with_customers.list_customers(sort_by="total_spent")
        assert result[0]["name"] == "Charlie"

    def test_list_limit(self, mgr_with_customers):
        result = mgr_with_customers.list_customers(limit=2)
        assert len(result) == 2

    def test_search_by_name(self, mgr_with_customers):
        result = mgr_with_customers.search_customers("alice")
        assert len(result) == 1

    def test_search_by_email(self, mgr_with_customers):
        result = mgr_with_customers.search_customers("bob@")
        assert len(result) == 1

    def test_search_case_insensitive(self, mgr_with_customers):
        result = mgr_with_customers.search_customers("ALICE")
        assert len(result) == 1


class TestInteractions:
    def test_create_interaction(self, mgr_with_customers):
        i = mgr_with_customers.create_interaction(InteractionData(
            customer_email="alice@example.com",
            interaction_type="inquiry",
            subject="Where's my order?",
            content="Order ORD-001 hasn't arrived",
        ))
        assert i["interaction_type"] == "inquiry"
        assert i["status"] == "open"

    def test_invalid_type(self, mgr_with_customers):
        with pytest.raises(ValueError, match="Invalid type"):
            mgr_with_customers.create_interaction(InteractionData(
                customer_email="alice@example.com", interaction_type="invalid",
            ))

    def test_invalid_sentiment(self, mgr_with_customers):
        with pytest.raises(ValueError, match="Invalid sentiment"):
            mgr_with_customers.create_interaction(InteractionData(
                customer_email="alice@example.com", interaction_type="inquiry",
                sentiment="angry",
            ))

    def test_nonexistent_customer(self, mgr):
        with pytest.raises(ValueError, match="not found"):
            mgr.create_interaction(InteractionData(
                customer_email="nope@nope.com", interaction_type="inquiry",
            ))

    def test_update_status(self, mgr_with_customers):
        i = mgr_with_customers.create_interaction(InteractionData(
            customer_email="alice@example.com", interaction_type="support",
        ))
        updated = mgr_with_customers.update_interaction_status(i["id"], "resolved")
        assert updated["status"] == "resolved"

    def test_update_invalid_status(self, mgr_with_customers):
        i = mgr_with_customers.create_interaction(InteractionData(
            customer_email="alice@example.com", interaction_type="support",
        ))
        with pytest.raises(ValueError, match="Invalid status"):
            mgr_with_customers.update_interaction_status(i["id"], "invalid")

    def test_update_nonexistent(self, mgr):
        with pytest.raises(ValueError, match="not found"):
            mgr.update_interaction_status("no-id", "resolved")

    def test_list_interactions(self, mgr_with_customers):
        mgr_with_customers.create_interaction(InteractionData(
            customer_email="alice@example.com", interaction_type="inquiry",
        ))
        mgr_with_customers.create_interaction(InteractionData(
            customer_email="alice@example.com", interaction_type="complaint",
            sentiment="negative",
        ))
        mgr_with_customers.create_interaction(InteractionData(
            customer_email="bob@example.com", interaction_type="review",
        ))
        assert len(mgr_with_customers.list_interactions()) == 3
        assert len(mgr_with_customers.list_interactions(customer_email="alice@example.com")) == 2
        assert len(mgr_with_customers.list_interactions(interaction_type="complaint")) == 1
        assert len(mgr_with_customers.list_interactions(sentiment="negative")) == 1

    def test_all_interaction_types(self, mgr_with_customers):
        for itype in CustomerManager.VALID_INTERACTION_TYPES:
            i = mgr_with_customers.create_interaction(InteractionData(
                customer_email="alice@example.com", interaction_type=itype,
            ))
            assert i["interaction_type"] == itype


class TestHealthScore:
    def test_base_score(self, mgr_with_customers):
        h = mgr_with_customers.customer_health_score("alice@example.com")
        assert h["score"] == 50  # base, no orders

    def test_orders_boost(self, mgr_with_customers):
        for _ in range(5):
            mgr_with_customers.record_order("alice@example.com", 20.0)
        h = mgr_with_customers.customer_health_score("alice@example.com")
        assert h["score"] > 50

    def test_spending_boost(self, mgr_with_customers):
        mgr_with_customers.record_order("alice@example.com", 600.0)
        h = mgr_with_customers.customer_health_score("alice@example.com")
        assert h["score"] > 60

    def test_returns_penalty(self, mgr_with_customers):
        mgr_with_customers.record_order("alice@example.com", 10.0)
        mgr_with_customers.record_return("alice@example.com")  # 100% return rate
        h = mgr_with_customers.customer_health_score("alice@example.com")
        assert h["score"] < 60

    def test_vip_bonus(self, mgr_with_customers):
        h = mgr_with_customers.customer_health_score("bob@example.com")
        assert h["score"] == 55  # 50 base + 5 vip

    def test_blacklisted_penalty(self, mgr_with_customers):
        mgr_with_customers.set_tier("alice@example.com", "blacklisted")
        h = mgr_with_customers.customer_health_score("alice@example.com")
        assert h["score"] == 20  # 50 - 30

    def test_negative_interactions(self, mgr_with_customers):
        for _ in range(3):
            mgr_with_customers.create_interaction(InteractionData(
                customer_email="alice@example.com", interaction_type="complaint",
                sentiment="negative",
            ))
        h = mgr_with_customers.customer_health_score("alice@example.com")
        assert h["score"] < 50

    def test_positive_interactions(self, mgr_with_customers):
        for _ in range(3):
            mgr_with_customers.create_interaction(InteractionData(
                customer_email="alice@example.com", interaction_type="review",
                sentiment="positive",
            ))
        h = mgr_with_customers.customer_health_score("alice@example.com")
        assert h["score"] > 50

    def test_score_clamped(self, mgr_with_customers):
        # Lots of negatives
        mgr_with_customers.set_tier("alice@example.com", "blacklisted")
        for _ in range(10):
            mgr_with_customers.create_interaction(InteractionData(
                customer_email="alice@example.com", interaction_type="complaint",
                sentiment="negative",
            ))
        h = mgr_with_customers.customer_health_score("alice@example.com")
        assert h["score"] >= 0

    def test_label(self, mgr_with_customers):
        h = mgr_with_customers.customer_health_score("alice@example.com")
        assert h["label"] in ("excellent", "good", "fair", "at_risk")

    def test_nonexistent(self, mgr):
        with pytest.raises(ValueError, match="not found"):
            mgr.customer_health_score("nope@nope.com")


class TestStats:
    def test_empty_stats(self, mgr):
        s = mgr.stats()
        assert s["total"] == 0

    def test_stats(self, mgr_with_customers):
        mgr_with_customers.record_order("alice@example.com", 100.0)
        mgr_with_customers.record_order("bob@example.com", 200.0)
        s = mgr_with_customers.stats()
        assert s["total"] == 3
        assert s["active"] == 3
        assert s["total_revenue"] == 300.0
        assert s["avg_ltv"] == 100.0
        assert s["by_tier"]["regular"] == 2
        assert s["by_tier"]["vip"] == 1
