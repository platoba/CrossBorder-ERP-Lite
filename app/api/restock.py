"""补货建议API端点"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.services.restock_advisor import RestockAdvisor
from app.schemas.restock import RestockRecommendation, RestockSummary, RestockPriority

router = APIRouter(prefix="/restock", tags=["Restock Advisor"])


@router.get("/recommendations", response_model=list[RestockRecommendation])
def get_restock_recommendations(
    priority: Optional[RestockPriority] = Query(None, description="优先级过滤"),
    limit: int = Query(100, ge=1, le=500, description="返回数量限制"),
    db: Session = Depends(get_db)
):
    """
    获取补货建议列表
    
    - 基于销售趋势、库存周转率、供应商交期自动生成
    - 支持按优先级过滤
    - 按优先级和库存天数排序
    """
    advisor = RestockAdvisor(db)
    return advisor.get_all_recommendations(priority_filter=priority, limit=limit)


@router.get("/recommendations/{product_id}", response_model=RestockRecommendation)
def get_product_restock_recommendation(
    product_id: int,
    days_history: int = Query(30, ge=7, le=90, description="历史销售天数"),
    safety_stock_days: int = Query(7, ge=1, le=30, description="安全库存天数"),
    db: Session = Depends(get_db)
):
    """
    获取单个产品的补货建议
    
    - 计算日均销量、补货点、经济订货量
    - 评估库存可用天数和优先级
    """
    advisor = RestockAdvisor(db)
    recommendation = advisor.analyze_product(
        product_id=product_id,
        days_history=days_history,
        safety_stock_days=safety_stock_days
    )
    if not recommendation:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Product not found or no inventory data")
    return recommendation


@router.get("/urgent", response_model=list[RestockRecommendation])
def get_urgent_restocks(db: Session = Depends(get_db)):
    """
    获取紧急补货建议
    
    - 仅返回库存不足7天的产品
    - 需要立即采购
    """
    advisor = RestockAdvisor(db)
    return advisor.get_urgent_restocks()


@router.get("/summary", response_model=RestockSummary)
def get_restock_summary(
    priority: Optional[RestockPriority] = Query(None, description="优先级过滤"),
    db: Session = Depends(get_db)
):
    """
    获取补货汇总报告
    
    - 总成本、总数量、产品数量
    - 包含详细建议列表
    """
    advisor = RestockAdvisor(db)
    recommendations = advisor.get_all_recommendations(priority_filter=priority)
    cost_summary = advisor.calculate_total_restock_cost(recommendations)
    
    return RestockSummary(
        **cost_summary,
        recommendations=recommendations
    )
