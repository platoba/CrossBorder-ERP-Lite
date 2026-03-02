"""测试智能补货建议引擎"""
import pytest
from datetime import datetime, timedelta
from app.services.restock_advisor import RestockAdvisor
from app.schemas.restock import RestockPriority


def test_analyze_product_needs_restock(db_session, sample_product, sample_inventory, sample_orders):
    """测试产品需要补货的场景"""
    advisor = RestockAdvisor(db_session)
    
    # 设置低库存
    sample_inventory.available_quantity = 10
    db_session.commit()
    
    recommendation = advisor.analyze_product(sample_product.id)
    
    assert recommendation is not None
    assert recommendation.product_id == sample_product.id
    assert recommendation.current_stock == 10
    assert recommendation.needs_restock is True
    assert recommendation.suggested_quantity > 0


def test_analyze_product_sufficient_stock(db_session, sample_product, sample_inventory):
    """测试库存充足的场景"""
    advisor = RestockAdvisor(db_session)
    
    # 设置高库存
    sample_inventory.available_quantity = 1000
    db_session.commit()
    
    recommendation = advisor.analyze_product(sample_product.id)
    
    assert recommendation is not None
    assert recommendation.current_stock == 1000
    assert recommendation.needs_restock is False
    assert recommendation.priority == RestockPriority.LOW


def test_urgent_priority_low_stock(db_session, sample_product, sample_inventory, sample_orders):
    """测试紧急优先级（库存不足7天）"""
    advisor = RestockAdvisor(db_session)
    
    # 设置极低库存
    sample_inventory.available_quantity = 5
    db_session.commit()
    
    recommendation = advisor.analyze_product(sample_product.id, safety_stock_days=7)
    
    assert recommendation.priority == RestockPriority.URGENT
    assert recommendation.days_of_stock <= 7


def test_get_all_recommendations(db_session, sample_products):
    """测试获取所有补货建议"""
    advisor = RestockAdvisor(db_session)
    
    recommendations = advisor.get_all_recommendations(limit=10)
    
    assert isinstance(recommendations, list)
    assert len(recommendations) <= 10


def test_get_urgent_restocks(db_session, sample_product, sample_inventory):
    """测试获取紧急补货建议"""
    advisor = RestockAdvisor(db_session)
    
    sample_inventory.available_quantity = 3
    db_session.commit()
    
    urgent = advisor.get_urgent_restocks()
    
    assert isinstance(urgent, list)
    if urgent:
        assert all(rec.priority == RestockPriority.URGENT for rec in urgent)


def test_calculate_total_restock_cost(db_session):
    """测试计算总补货成本"""
    advisor = RestockAdvisor(db_session)
    
    recommendations = advisor.get_all_recommendations()
    cost_summary = advisor.calculate_total_restock_cost(recommendations)
    
    assert "total_cost" in cost_summary
    assert "total_units" in cost_summary
    assert "product_count" in cost_summary
    assert cost_summary["total_cost"] >= 0


def test_eoq_calculation(db_session, sample_product, sample_inventory):
    """测试经济订货量计算"""
    advisor = RestockAdvisor(db_session)
    
    recommendation = advisor.analyze_product(sample_product.id)
    
    assert recommendation.eoq > 0
    assert isinstance(recommendation.eoq, (int, float))


def test_reorder_point_calculation(db_session, sample_product, sample_inventory, sample_supplier):
    """测试补货点计算"""
    advisor = RestockAdvisor(db_session)
    
    # 设置供应商交期
    sample_supplier.lead_time_days = 14
    db_session.commit()
    
    recommendation = advisor.analyze_product(sample_product.id, safety_stock_days=7)
    
    # 补货点 = (日均销量 * 交期) + 安全库存
    expected_reorder_point = (recommendation.daily_sales_rate * 14) + (recommendation.daily_sales_rate * 7)
    
    assert abs(recommendation.reorder_point - expected_reorder_point) < 1


def test_days_of_stock_calculation(db_session, sample_product, sample_inventory):
    """测试库存可用天数计算"""
    advisor = RestockAdvisor(db_session)
    
    sample_inventory.available_quantity = 100
    db_session.commit()
    
    recommendation = advisor.analyze_product(sample_product.id)
    
    if recommendation.daily_sales_rate > 0:
        expected_days = 100 / recommendation.daily_sales_rate
        assert abs(recommendation.days_of_stock - expected_days) < 0.1


def test_no_sales_history(db_session, sample_product, sample_inventory):
    """测试无销售历史的场景"""
    advisor = RestockAdvisor(db_session)
    
    recommendation = advisor.analyze_product(sample_product.id)
    
    assert recommendation is not None
    assert recommendation.daily_sales_rate == 0
    assert recommendation.days_of_stock == 999  # 默认值


def test_priority_filter(db_session, sample_products):
    """测试优先级过滤"""
    advisor = RestockAdvisor(db_session)
    
    urgent_recs = advisor.get_all_recommendations(priority_filter=RestockPriority.URGENT)
    
    assert all(rec.priority == RestockPriority.URGENT for rec in urgent_recs)


def test_recommendation_sorting(db_session, sample_products):
    """测试建议排序（按优先级和库存天数）"""
    advisor = RestockAdvisor(db_session)
    
    recommendations = advisor.get_all_recommendations()
    
    if len(recommendations) > 1:
        priority_order = {
            RestockPriority.URGENT: 0,
            RestockPriority.HIGH: 1,
            RestockPriority.MEDIUM: 2,
            RestockPriority.LOW: 3
        }
        
        for i in range(len(recommendations) - 1):
            current_priority = priority_order[recommendations[i].priority]
            next_priority = priority_order[recommendations[i + 1].priority]
            
            assert current_priority <= next_priority
